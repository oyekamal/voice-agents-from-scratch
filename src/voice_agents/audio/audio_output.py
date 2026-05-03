"""Speaker playback."""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf


def _remove_dc_mono(samples: np.ndarray) -> np.ndarray:
    """Subtract mean — neural TTS sometimes has DC offset; fades then miss true zero (clicks)."""
    x = np.asarray(samples, dtype=np.float32, copy=True)
    if x.size < 2:
        return x
    x -= np.float32(np.mean(x, dtype=np.float64))
    return x


def _apply_edge_fades(samples: np.ndarray, sample_rate: int, fade_ms: float = 8.0) -> np.ndarray:
    """Fade in/out to reduce clicks. Long cosine fade-out — linear ramps still snap at the last sample."""
    x = np.asarray(samples, dtype=np.float32, copy=True)
    n = int(x.shape[0])
    if n < 16:
        return x
    fade_in = max(1, int(sample_rate * fade_ms / 1000.0))
    # Long cosine decay — residual cracks often trace to DC + short fades + tiny PortAudio blocks.
    fade_out = max(1, int(sample_rate * max(90.0, fade_ms * 4.5) / 1000.0))
    fade_in = min(fade_in, max(1, n - 2))
    fade_out = min(fade_out, max(1, n - fade_in))
    if fade_in > 0:
        theta = np.linspace(0.0, np.pi / 2, fade_in, dtype=np.float32)
        ramp_in = np.sin(theta)
        x[:fade_in] *= ramp_in
    if fade_out > 0:
        theta = np.linspace(0.0, np.pi / 2, fade_out, dtype=np.float32)
        ramp_out = np.cos(theta)
        x[-fade_out:] *= ramp_out
    return x


def play_wav_file(
    path: str | Path,
    *,
    on_playback_start: Callable[[], None] | None = None,
    edge_fade_ms: float = 8.0,
) -> None:
    data, sr = sf.read(str(path), always_2d=False)
    play_float_mono(
        np.asarray(data, dtype=np.float32),
        int(sr),
        on_playback_start=on_playback_start,
        edge_fade_ms=edge_fade_ms,
    )


def play_float_mono(
    samples: np.ndarray,
    sample_rate: int,
    *,
    on_playback_start: Callable[[], None] | None = None,
    edge_fade_ms: float = 8.0,
) -> None:
    """Play mono float audio (shape ``(n,)``)."""
    x = np.asarray(samples, dtype=np.float32)
    if x.ndim > 1:
        x = x[:, 0]
    x = _remove_dc_mono(x)
    x = _apply_edge_fades(x, sample_rate, fade_ms=edge_fade_ms)
    np.clip(x, -1.0, 1.0, out=x)
    # Extra trailing zeros so PortAudio finishes near silence before teardown (reduces end snap).
    tail = max(0, int(sample_rate * 0.080))
    if tail:
        x = np.concatenate([x, np.zeros(tail, dtype=np.float32)])
    if on_playback_start is not None:
        on_playback_start()
    # Larger blocks reduce callback-rate glitches that sound like random cracks under load.
    try:
        sd.play(x, sample_rate, latency="high", blocksize=2048)
    except (sd.PortAudioError, ValueError, OSError):
        sd.play(x, sample_rate, latency="high")
    sd.wait()
    # Brief settle time before the next chunk or device reuse (helps some CoreAudio/WASAPI paths).
    time.sleep(0.003)

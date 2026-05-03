"""Chapter 06 only: microphone capture and chunked speaker playback (no ``voice_agents``)."""

from __future__ import annotations

import threading
import time

import numpy as np
import sounddevice as sd

_SR_DEFAULT = 16_000


def record_mono_seconds(duration_s: float, *, sample_rate: int = _SR_DEFAULT) -> tuple[np.ndarray, int]:
    """Record mono float32 audio (same shape contract as chapter 01 / 05)."""
    frames = int(sample_rate * duration_s)
    audio = sd.rec(
        frames,
        samplerate=sample_rate,
        channels=1,
        dtype="float32",
    )
    sd.wait()
    return np.squeeze(audio), sample_rate


def play_chunked(
    samples: np.ndarray,
    sample_rate: int,
    *,
    cancel: threading.Event | None = None,
    chunk_frames: int = 2048,
) -> bool:
    """
    Play mono samples in chunks; optionally abort between chunks.

    Returns True if playback finished, False if cancelled or ``cancel`` set.
    """
    x = np.asarray(samples, dtype=np.float32).squeeze()
    if x.ndim > 1:
        x = x[:, 0]
    n = len(x)
    i = 0
    while i < n:
        if cancel is not None and cancel.is_set():
            sd.stop()
            return False
        end = min(i + chunk_frames, n)
        sd.play(x[i:end], sample_rate, latency="high", blocksize=min(chunk_frames, end - i))
        sd.wait()
        i = end
    if cancel is not None and cancel.is_set():
        sd.stop()
        return False
    time.sleep(0.003)
    return True


def play_cancellable_stream(
    samples: np.ndarray,
    sample_rate: int,
    *,
    cancel: threading.Event | None = None,
    blocksize: int = 2048,
) -> bool:
    """
    Play mono float32 in one continuous output callback stream.

    Prefer this over many chained ``sd.play`` calls for long TTS, which often
    sound choppy at chunk boundaries. Returns True if all samples were played,
    False if ``cancel`` was set before the end.
    """
    x = np.asarray(samples, dtype=np.float32).squeeze()
    if x.ndim > 1:
        x = x[:, 0]
    n = len(x)
    pos = 0

    def callback(outdata: np.ndarray, frames: int, t, status) -> None:  # noqa: ARG001
        nonlocal pos
        if cancel is not None and cancel.is_set():
            outdata.fill(0)
            raise sd.CallbackStop
        remaining = n - pos
        if remaining <= 0:
            outdata.fill(0)
            raise sd.CallbackStop
        c = min(frames, remaining)
        if outdata.ndim == 1:
            outdata[:c] = x[pos : pos + c]
            if c < frames:
                outdata[c:] = 0
        else:
            outdata[:c, 0] = x[pos : pos + c]
            if c < frames:
                outdata[c:, 0] = 0
        pos += c

    with sd.OutputStream(
        channels=1,
        samplerate=sample_rate,
        dtype="float32",
        callback=callback,
        blocksize=blocksize,
        latency="high",
    ) as stream:
        # ``with`` starts the stream; there is no ``OutputStream.wait()`` — block until inactive.
        while stream.active:
            time.sleep(0.01)
    if cancel is not None and cancel.is_set():
        return False
    return pos >= n

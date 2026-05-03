"""Barge-in demo: Kokoro plays long audio in chunks; mic RMS can cancel (no ``voice_agents``).

Headphones recommended  -  speaker bleed into the mic can false-trigger cancel.
"""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

import numpy as np
import sounddevice as sd
from kokoro_onnx import Kokoro
from rich.console import Console

_CH06 = Path(__file__).resolve().parents[1]
if str(_CH06) not in sys.path:
    sys.path.insert(0, str(_CH06))

from _audio_chunks import play_cancellable_stream  # noqa: E402
from _model_paths import KOKORO_ONNX, KOKORO_VOICES  # noqa: E402

SR_MIC = 16_000
BLOCK = 512
# Barge-in only after lead-in so speaker bleed does not instantly cancel playback.
LEAD_IN_S = 1.25
# Loud blocks in a row (~128 ms at 16 kHz / 512) after lead-in; brief dips use HOLD_FRAC so words do not reset the streak.
SUSTAIN_BLOCKS = 4
# Many laptop / headset mics stay well below 0.11 RMS even when shouting; tune for “clear stop” not studio levels.
THRESH_RMS = 0.042
# Consonants (e.g. “stop”) often show higher peak than short-window RMS in one block.
PEAK_FACTOR = 2.35
# If RMS dips slightly between syllables but is still “speech-ish”, keep the streak (do not reset to 0).
HOLD_FRAC = 0.38
# Very loud peaks for a few blocks → cancel (works when RMS never crosses THRESH_RMS on quiet gain).
SHOUT_PEAK = 0.13
SHOUT_BLOCKS = 3


def rms_energy(block: np.ndarray) -> float:
    v = block.reshape(-1).astype(np.float32)
    return float(np.sqrt(np.mean(np.square(v))))


def peak_abs(block: np.ndarray) -> float:
    v = block.reshape(-1).astype(np.float32)
    return float(np.max(np.abs(v)))


def main() -> None:
    console = Console()
    if not KOKORO_ONNX.is_file() or not KOKORO_VOICES.is_file():
        console.print("Missing Kokoro models under models/kokoro/  -  run 00_start_here/download_models.py")
        raise SystemExit(1)

    k = Kokoro(str(KOKORO_ONNX), str(KOKORO_VOICES))
    voices = k.get_voices()
    voice = "af_heart" if "af_heart" in voices else voices[0]

    long_text = (
        "This playback runs several seconds. Speak into the microphone while you hear this voice. "
        * 12
    )
    console.print(
        "[bold]Two steps:[/] \n[cyan](1)[/] Kokoro builds one long audio clip from text\n"
        "[cyan](2)[/] that clip plays while the mic watches for [bold]your[/] loud speech to cancel playback.\n"
        "[dim]Use headphones if you can: the playing voice can leak into the mic and look like “speech”.[/]"
    )
    console.print(
        "[dim]You are on step 1 only. Wait until you hear audio; do not speak yet "
        "(the mic is not used for cancel until playback starts).[/]\n"
    )
    with console.status(
        "[bold yellow]Step 1/2:[/] Synthesizing speech with Kokoro… "
        "[dim](CPU-bound; can take a while  -  spinner shows it is still working)[/]"
    ):
        samples, play_sr = k.create(long_text, voice=voice, speed=1.0)
    console.print("[green]Step 1 done.[/] [bold]Step 2/2:[/] opening mic stream and starting playback…\n")
    audio = np.asarray(samples, dtype=np.float32).squeeze()
    if audio.ndim > 1:
        audio = audio[:, 0]

    cancel = threading.Event()
    playback_on = threading.Event()
    mic_blocks = {"rms": 0.0, "peak": 0.0}
    sustain = {"n": 0}
    shout = {"n": 0}
    arm_cancel_at = {"t": 0.0}

    def mic_cb(indata, frames, t, status) -> None:  # noqa: ARG001
        if not playback_on.is_set():
            return
        now = time.monotonic()
        if now < arm_cancel_at["t"]:
            sustain["n"] = 0
            shout["n"] = 0
            return
        r = rms_energy(indata)
        pk = peak_abs(indata)
        mic_blocks["rms"] = r
        mic_blocks["peak"] = pk

        loud = r >= THRESH_RMS or pk >= THRESH_RMS * PEAK_FACTOR
        if loud:
            sustain["n"] += 1
        elif r >= THRESH_RMS * HOLD_FRAC:
            pass
        else:
            sustain["n"] = 0

        if pk >= SHOUT_PEAK:
            shout["n"] += 1
        else:
            shout["n"] = 0

        if sustain["n"] >= SUSTAIN_BLOCKS or shout["n"] >= SHOUT_BLOCKS:
            cancel.set()

    console.print(
        f"[bold]Duplex demo[/]   -   after [cyan]{LEAD_IN_S:.1f}s[/] of playback, speak toward the mic to stop  |  "
        f"barge-in: RMS ≥ [cyan]{THRESH_RMS}[/] or peak ≥ [cyan]{THRESH_RMS * PEAK_FACTOR:.3f}[/], "
        f"[cyan]{SUSTAIN_BLOCKS}[/] blocks (brief dips OK) [bold]or[/] peak ≥ [cyan]{SHOUT_PEAK}[/] for [cyan]{SHOUT_BLOCKS}[/] blocks  |  "
        f"[dim]prefer headphones[/]"
    )

    def runner() -> None:
        sustain["n"] = 0
        shout["n"] = 0
        arm_cancel_at["t"] = time.monotonic() + LEAD_IN_S
        playback_on.set()
        finished = play_cancellable_stream(audio, int(play_sr), cancel=cancel)
        playback_on.clear()
        if cancel.is_set():
            console.print(
                "[yellow]Interrupted[/]  -  sustained loud mic input crossed the threshold "
                "(see printed settings; headphones reduce false stops from speaker bleed)."
            )
        elif finished:
            console.print("[green]Finished[/] playback without interrupt.")

    with sd.InputStream(
        channels=1,
        samplerate=SR_MIC,
        blocksize=BLOCK,
        callback=mic_cb,
        dtype="float32",
    ):
        t = threading.Thread(target=runner)
        t.start()
        t.join()

    console.print(
        f"[dim]last mic RMS / peak:[/] {mic_blocks['rms']:.5f} / {mic_blocks['peak']:.5f}  "
        f"[dim](if both stay tiny, raise OS input gain or move closer; thresholds are in the script constants)[/]"
    )


if __name__ == "__main__":
    main()

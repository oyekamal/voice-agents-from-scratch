"""Cooperative cancel via Rich prompt while playback runs (no ``voice_agents``).

Loads ``tmp/latency_response.wav`` from the repo root (generate with chapter 05 ``debug_latency``).
Uses a single ``OutputStream`` (``play_cancellable_stream``) so audio is not chopped by repeated
``sd.play``. Uses ``Confirm.ask`` (bool), not ``Prompt.ask`` (str), so ``y``/``n`` are not misread as truthy strings.
Distinct from ``duplex_conversation``: human confirms cancel instead of mic RMS.
"""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

import numpy as np
import soundfile as sf
from rich.console import Console
from rich.prompt import Confirm

_CH06 = Path(__file__).resolve().parents[1]
if str(_CH06) not in sys.path:
    sys.path.insert(0, str(_CH06))

from _audio_chunks import play_cancellable_stream  # noqa: E402
from _model_paths import TMP_LATENCY_WAV  # noqa: E402


def main() -> None:
    console = Console()
    if not TMP_LATENCY_WAV.is_file():
        console.print(
            "Missing tmp/latency_response.wav  -  run:\n"
            "  uv run python 05_full_voice_loop/debug_latency/debug_latency.py"
        )
        raise SystemExit(1)

    data, sr = sf.read(str(TMP_LATENCY_WAV), dtype="float32")
    x = np.squeeze(np.asarray(data, dtype=np.float32))
    cancel = threading.Event()
    playback_exc: list[Exception] = []

    def runner() -> None:
        try:
            play_cancellable_stream(x, int(sr), cancel=cancel)
        except Exception as e:
            playback_exc.append(e)

    console.print(
        "[bold]interruption_handling[/]   -  cooperative barge-in (stop playback without killing the driver).\n"
        "Playback runs in a [bold]background thread[/] via one continuous output stream; this thread asks a question.\n"
        "• [bold]y[/]: set a shared cancel flag → playback stops at the next audio block boundary.\n"
        "• [bold]n[/]: let the WAV play to the end.\n"
        "[dim]Default is n (Enter) so you can hear the clip cleanly once; answer y to simulate barge-in.[/]"
    )

    t = threading.Thread(target=runner, daemon=True)
    t.start()
    time.sleep(0.5)
    if Confirm.ask("Stop playback now?", default=False):
        cancel.set()
    t.join(timeout=60)
    if playback_exc:
        console.print(f"[red]Playback failed:[/] {playback_exc[0]}")
        console.print(
            "[dim]Typical causes: no default output device (headless/SSH), or PortAudio could not open the stream.[/]"
        )
        raise SystemExit(1)
    if cancel.is_set():
        console.print("[dim]Done (playback cancelled cooperatively).[/]")
    else:
        console.print("[dim]Done (full clip played).[/]")


if __name__ == "__main__":
    main()

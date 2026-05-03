"""Live RMS energy gate on the default mic (chapter 06  -  no ``voice_agents`` imports)."""

from __future__ import annotations

import argparse
import sys
import threading
import time

import numpy as np
import sounddevice as sd
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

SR = 16_000
BLOCK = 512


def rms_energy(block: np.ndarray) -> float:
    v = block.reshape(-1).astype(np.float32)
    return float(np.sqrt(np.mean(np.square(v))))


def main() -> None:
    parser = argparse.ArgumentParser(description="RMS voice-activity style counts / live meter.")
    parser.add_argument(
        "thresh",
        type=float,
        nargs="?",
        default=0.02,
        help="RMS threshold (default 0.02)",
    )
    parser.add_argument(
        "--seconds",
        type=float,
        default=5.0,
        help="Capture duration (default 5)",
    )
    args = parser.parse_args()
    thresh = args.thresh
    duration = args.seconds

    stats: dict[str, float | int] = {"total": 0, "speech": 0, "last_rms": 0.0}
    lock = threading.Lock()

    def callback(indata, frames, t, status) -> None:  # noqa: ARG001
        if status:
            pass
        r = rms_energy(indata)
        with lock:
            stats["total"] += 1
            stats["last_rms"] = r
            if r >= thresh:
                stats["speech"] += 1

    console = Console()
    console.print(f"[bold]RMS threshold[/] {thresh}  |  [bold]{duration}s[/] capture  |  block {BLOCK} @ {SR} Hz")

    end = time.monotonic() + duration

    def render_panel() -> Panel:
        with lock:
            total = int(stats["total"])
            speech = int(stats["speech"])
            last = float(stats["last_rms"])
        pct = min(1.0, last / max(thresh * 4, 1e-6))
        bar_w = 40
        filled = int(bar_w * pct)
        bar = "#" * filled + "-" * (bar_w - filled)
        lines = Group(
            Text.assemble(
                ("last RMS ", "bold"),
                (f"{last:.5f}", "cyan"),
                ("  speech-ish blocks ", "bold"),
                (f"{speech}", "green"),
                (" / ", "dim"),
                (f"{total}", "yellow"),
            ),
            Text(bar, style="green" if last >= thresh else "dim"),
        )
        return Panel(lines, title="voice_activity_detection", border_style="cyan")

    with sd.InputStream(
        channels=1,
        samplerate=SR,
        blocksize=BLOCK,
        callback=callback,
        dtype="float32",
    ):
        with Live(render_panel(), refresh_per_second=12, console=console) as live:
            while time.monotonic() < end:
                live.update(render_panel())
                time.sleep(1 / 12)

    with lock:
        total = int(stats["total"])
        speech = int(stats["speech"])
    console.print(f"[bold]Speech-ish blocks:[/] {speech}/{total}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.", file=sys.stderr)

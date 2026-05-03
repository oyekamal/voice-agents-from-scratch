# Voice activity detection (energy / RMS)

Before neural VAD or cloud APIs, many pipelines use **energy**: **root mean square (RMS)** amplitude per short block of samples. If RMS is above a **threshold**, the block is treated as **speech-ish** (or at least “not silence”). Wrong threshold → everything counts as speech, or nothing does  -  so you tune for **mic gain** and **room noise**.

Run **[`voice_activity_detection.py`](./voice_activity_detection.py)** for a **Rich Live** RMS meter and **`Speech-ish blocks: a/b`** summary over **`--seconds`** (positional optional threshold).

This is **not** endpointing or ASR; it only answers **“is this block loud enough?”** That signal often **feeds** decisions like **speech_end** (see [turn-taking](../turn_taking/CODE.md)). For extra mic playground material, see [`vad_debug`](../../01_audio_io/vad_debug/CODE.md) in chapter 01.

```bash
uv run python 06_real_time_systems/voice_activity_detection/voice_activity_detection.py
uv run python 06_real_time_systems/voice_activity_detection/voice_activity_detection.py 0.03 --seconds 8
```

---

## Code walkthrough (`voice_activity_detection.py`)

### 1. CLI  -  threshold and duration

Optional positional **`thresh`** (default **`0.02`**) and **`--seconds`** for capture length:

```python
parser.add_argument(
    "thresh",
    type=float,
    nargs="?",
    default=0.02,
    help="RMS threshold (default 0.02)",
)
parser.add_argument("--seconds", type=float, default=5.0, help="Capture duration (default 5)")
```

### 2. Shared counters + lock

PortAudio calls **`callback`** on its thread; Rich reads **`stats`** on the main thread  -  use a **lock**:

```python
stats: dict[str, float | int] = {"total": 0, "speech": 0, "last_rms": 0.0}
lock = threading.Lock()
```

### 3. RMS from one block

Single scalar loudness = **`√(mean(samples²))`**:

```python
def rms_energy(block: np.ndarray) -> float:
    v = block.reshape(-1).astype(np.float32)
    return float(np.sqrt(np.mean(np.square(v))))
```

### 4. Audio callback  -  count blocks “above threshold”

Every **`BLOCK`** samples (~512 @ 16 kHz):

```python
def callback(indata, frames, t, status) -> None:
    r = rms_energy(indata)
    with lock:
        stats["total"] += 1
        stats["last_rms"] = r
        if r >= thresh:
            stats["speech"] += 1
```

### 5. Live meter  -  bar + numbers

**`render_panel()`** copies **`stats`** under the lock, maps **`last_rms`** to a bar fill **`pct`**, builds **`Text`** lines + **`Panel`**:

```python
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
```

### 6. Mic stream + Rich Live loop

Open **`InputStream`**, then spin **`Live.update`** until **`duration`** elapses:

```python
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
```

### 7. Final summary

After the stream exits:

```python
console.print(f"[bold]Speech-ish blocks:[/] {speech}/{total}")
```

---


## Constants that matter

| Symbol | Typical value | Role |
|--------|----------------|------|
| **Sample rate** | 16 000 Hz | Common for speech front-ends; matches much STT. |
| **Block size** | 512 samples | At 16 kHz → ~32 ms per callback block (latency vs stability tradeoff). |

---

## RMS gate

For a block of samples **x** (1-D array of amplitudes):

**RMS(x) = √( mean(x²) )**

Same thing in NumPy terms: `np.sqrt(np.mean(np.square(x)))`  -  which is what **`rms_vad`** does after flattening to **`float32`**.

Classify a block as “active” when **RMS ≥ thresh**. Default **`thresh`** in the sketch below is **`0.02`** (typical float32 nominal range); raise **`thresh`** if background noise counts as speech, lower it if real speech is missed.

---

## Reference sketch (`sounddevice` + callback)

Conceptually: open an **`InputStream`**, count blocks for a fixed duration (e.g. **5 s**), increment **`speech_blocks`** when **`rms_vad`** is true, then print **`speech_blocks/total`**.

```python
from __future__ import annotations

import sys
import time

import numpy as np
import sounddevice as sd

SR = 16_000
BLOCK = 512


def rms_vad(block: np.ndarray, thresh: float) -> bool:
    v = block.reshape(-1).astype(np.float32)
    return float(np.sqrt(np.mean(np.square(v)))) >= thresh


def main() -> None:
    thresh = float(sys.argv[1]) if len(sys.argv) > 1 else 0.02
    print(f"RMS threshold={thresh}, 5s capture…")
    speech_blocks = 0
    total = 0

    def cb(indata, frames, t, status):
        nonlocal speech_blocks, total
        total += 1
        if rms_vad(indata, thresh):
            speech_blocks += 1

    with sd.InputStream(
        channels=1,
        samplerate=SR,
        blocksize=BLOCK,
        callback=cb,
        dtype="float32",
    ):
        time.sleep(5)
    print(f"Speech-ish blocks: {speech_blocks}/{total}")


if __name__ == "__main__":
    main()
```

Optional CLI **`0.03`** etc. raises the bar when background noise triggers false “speech.”

---

## See also

- [`vad_debug`](../../01_audio_io/vad_debug/CODE.md)  -  runnable mic callback exploration (chapter 01).
- [`interruption_handling`](../interruption_handling/CODE.md)  -  **cooperative cancel** on playback ([chapter 06](../README.md#suggested-order)).
- [Duplex conversation](../duplex_conversation/CODE.md)  -  where a monitor thread might consume VAD-like signals.

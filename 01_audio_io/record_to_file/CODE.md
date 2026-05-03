# `record_to_file.py`  -  code walkthrough

## Purpose

Combine **blocking capture** with **writing a WAV** so you get a file under `tmp/` you can open in an editor or pass to [`02_speech_to_text/transcribe_once/transcribe_once.py`](../../02_speech_to_text/transcribe_once/transcribe_once.py) (or other chapter 02 scripts).

## Run

```bash
uv run python 01_audio_io/record_to_file/record_to_file.py       # 3 s default
uv run python 01_audio_io/record_to_file/record_to_file.py 5     # 5 s
```

## Dependencies

| Symbol | Location |
|--------|----------|
| [`AudioInputConfig`](../../src/voice_agents/audio/audio_input.py) | Uses defaults (`sample_rate` etc.) when constructing `AudioInputConfig()` with no args - still mono float capture consistent with the library. |
| [`record_seconds`](../../src/voice_agents/audio/audio_input.py) | Records `sec` seconds. |
| [`save_wav`](../../src/voice_agents/audio/audio_input.py) | Writes float32 mono PCM to a WAV path (creates parent dirs if needed - check implementation). |

## Code walkthrough

Full listing:

```python
"""Record to ``tmp/recorded.wav``."""

from __future__ import annotations

from pathlib import Path

import sys

from voice_agents.audio.audio_input import AudioInputConfig, record_seconds, save_wav

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "tmp" / "recorded.wav"

if __name__ == "__main__":
    sec = float(sys.argv[1]) if len(sys.argv) > 1 else 3.0
    print(f"Recording {sec}s to {OUT}…")
    audio, sr = record_seconds(sec, config=AudioInputConfig())
    save_wav(OUT, audio, sr)
    print("Done.")
```

### Repo-root paths (`ROOT`, `OUT`)

`Path(__file__).resolve().parents[2]` walks **two levels up** (`record_to_file/` → `01_audio_io/` → repository root), then joins **`tmp/recorded.wav`**. Anything expecting `tmp/` beside the top-level `README.md` keeps working after nesting this script in a subfolder.

### CLI duration (`sec`)

Optional first argument sets seconds (e.g. `5`); otherwise **3.0**. The print shows exactly where the file will land.

### Capture and persist (`record_seconds`, `save_wav`)

- **`AudioInputConfig()`**  -  Library defaults for sample rate and channels (see [`audio_input.py`](../../src/voice_agents/audio/audio_input.py)).
- **`save_wav(OUT, audio, sr)`**  -  Writes the recorded samples to disk; parent **`tmp/`** is created if missing.

Same **record → NumPy array → WAV** pattern as the full voice agent; chapter 02 can consume `tmp/recorded.wav`.

## Failure modes

Device issues behave like `mic_input`. If the file path fails, check disk permissions on `tmp/`. See [Troubleshooting](../README.md#troubleshooting).

## Try next

- Point chapter 02’s `transcribe_once` (or similar) at `tmp/recorded.wav` after recording speech.

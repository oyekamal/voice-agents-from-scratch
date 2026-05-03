# `mic_input.py`  -  code walkthrough

## Purpose

Record a **fixed-duration** clip from the default microphone using the shared blocking API, then print simple **level statistics** so you know the mic is live.

## Run

```bash
uv run python 01_audio_io/mic_input/mic_input.py
```

## Dependencies

| Symbol | Location |
|--------|----------|
| [`AudioInputConfig`](../../src/voice_agents/audio/audio_input.py) | Wraps sample rate, channels, dtype (`record_seconds` reads these defaults - here 16 kHz is set explicitly). |
| [`record_seconds`](../../src/voice_agents/audio/audio_input.py) | Opens the mic, reads exactly `3.0` seconds, returns `(numpy_array, sample_rate)`. |

## Code walkthrough

The whole script fits on one screen: record, compute two level metrics, print.

```python
"""Record a few seconds from the default mic and print peak level."""

from __future__ import annotations

import numpy as np

from voice_agents.audio.audio_input import AudioInputConfig, record_seconds

if __name__ == "__main__":
    print("Recording 3 seconds…")
    audio, sr = record_seconds(3.0, config=AudioInputConfig(sample_rate=16_000))
    peak = float(np.max(np.abs(audio)))
    rms = float(np.sqrt(np.mean(np.square(audio))))
    print(f"Sample rate: {sr} Hz, samples: {len(audio)}, peak: {peak:.4f}, RMS: {rms:.4f}")
```

### Blocking capture (`record_seconds`)

- **`record_seconds(3.0, …)`**  -  Opens the default input device and records exactly **3 seconds** of mono audio. The call **blocks** until capture finishes.
- **`AudioInputConfig(sample_rate=16_000)`**  -  Pins capture to **16 kHz** so results align with other chapter scripts.

Returns **`audio`** (NumPy vector, length ≈ `3 × sr`) and **`sr`** (typically 16000).

### Peak (`np.max(np.abs(audio))`)

Answers “what was the loudest sample?”  -  useful for spotting clipping or taps on the mic.

### RMS (`sqrt(mean(square(samples)))`)

Overall energy for the clip: \(\sqrt{\frac{1}{N}\sum_i x_i^2}\). Same RMS definition as [`stream_basics`](../stream_basics/CODE.md) and [`vad_debug`](../vad_debug/CODE.md), so you can compare values across examples.

There is **no WAV file** here - only printed stats.

### Understanding the printed line

After recording finishes, Python prints **one summary line** (built by the `print(f"Sample rate: …")` at the end of the script). Here is a **real example**:

```text
Recording 3 seconds…
Sample rate: 16000 Hz, samples: 48000, peak: 0.0481, RMS: 0.0060
```

What each field means:

| Field | Example | What it tells you |
|--------|---------|-------------------|
| **Sample rate** | `16000 Hz` | How many samples per second the capture used - here **16 kHz**, matching `AudioInputConfig(sample_rate=16_000)`. |
| **samples** | `48000` | How many audio samples are in `audio`. For a steady rate, **samples ≈ duration × sample rate** → \(3 \times 16000 = 48000\). If this does not match, something odd happened with timing or the stream. |
| **peak** | `0.0481` | The **largest absolute value** any single sample reached in the clip (after `np.abs`). With normalized float audio, **1.0** is typically “full scale”; values near **0** mean silence or a dead input; values approaching **1.0** mean very loud or clipping risk. |
| **RMS** | `0.0060` | **Average loudness** over the whole recording (see formula above). RMS is usually **smaller than peak** for speech/noise mixes because peak catches brief spikes while RMS averages energy. |

How to read it quickly:

- **Both peak and RMS tiny (e.g. 0.0001)** while you expect speech → wrong mic, permission denied, or gain too low - see [Troubleshooting](../README.md#troubleshooting).
- **Peak near 1.0** → input may be clipping; lower OS or hardware gain.
- **Reasonable non‑zero values** (like the example) → the mic delivered signal for those 3 seconds; louder speech or closer mic generally raises peak and RMS together.

The exact numbers depend on **your mic gain**, **distance**, and **room noise**; compare runs before and after you change volume or device.

## Failure modes

Peak and RMS near **zero** while you speak → wrong input device, permission denied, or muted mic. See [Troubleshooting](../README.md#troubleshooting).

## Try next

- Temporarily change `3.0` to another duration (still blocking - the script waits longer).

# `speaker_output.py`  -  code walkthrough

## Purpose

Prove that **playback** from Python works: either a short synthetic tone or an existing WAV file, routed through the same helper the rest of the repo uses for speakers.

## Run

From the repository root:

```bash
uv run python 01_audio_io/speaker_output/speaker_output.py
uv run python 01_audio_io/speaker_output/speaker_output.py path/to/file.wav
```

## Dependencies

| Import | Role |
|--------|------|
| `numpy` | Build the sine tone as a float array. |
| `soundfile` | Read WAV files when you pass a path. |
| [`play_float_mono`](../../src/voice_agents/audio/audio_output.py) | Push mono float samples to the default output device via PortAudio. |

The tone path never touches [`audio_input`](../../src/voice_agents/audio/audio_input.py); it only exercises [`audio_output`](../../src/voice_agents/audio/audio_output.py).

## Code walkthrough

### Imports and sample rate

The script pulls in NumPy, SoundFile for WAV I/O, and [`play_float_mono`](../../src/voice_agents/audio/audio_output.py). Note: `sounddevice` is imported but unused here - playback goes entirely through the shared helper.

```python
from voice_agents.audio.audio_output import play_float_mono

SR = 16_000
```

**Why `SR = 16_000`:** Sixteen kHz is enough for speech demos and matches other tutorials in this repo, so levels and timing stay comparable when you jump between chapters.

---

### Branch A  -  play a WAV file from the command line

When you pass a path, SoundFile reads samples and sample rate from disk. `always_2d=False` keeps mono as a 1-D array instead of shape `(N, 1)`.

```python
if len(sys.argv) > 1:
    p = Path(sys.argv[1])
    data, sr = sf.read(p, always_2d=False)
    play_float_mono(np.asarray(data, dtype=np.float32), int(sr))
```

The explicit `float32` cast matches what [`play_float_mono`](../../src/voice_agents/audio/audio_output.py) expects: normalized float samples (roughly −1…1). If your WAV is stereo, behaviour depends on how [`soundfile`](https://python-soundfile.readthedocs.io/) returns it - you may need to downmix for mono playback depending on the helper’s contract.

---

### Branch B  -  synthetic 440 Hz tone (default)

No arguments → generate a short sine wave in memory and play it.

```python
else:
    t = np.linspace(0, 0.3, int(0.3 * SR), dtype=np.float32)
    tone = 0.1 * np.sin(2 * np.pi * 440.0 * t)
    play_float_mono(tone, SR)
    print("Played 440 Hz tone. Pass a .wav path to play a file instead.")
```

- **`np.linspace(0, 0.3, int(0.3 * SR))`**  -  Time stamps from 0 to 0.3 seconds; there are `0.3 × 16000 = 4800` samples.
- **`0.1 * np.sin(2 * np.pi * 440.0 * t)`**  -  Standard sine at **440 Hz**; amplitude **0.1** keeps the tone audible but not harsh.
- **`play_float_mono(tone, SR)`**  -  Blocking playback: the call returns when the tone has finished playing.

## Failure modes

Output silence usually means wrong default device or muted/app volume. See the chapter [README](../README.md#troubleshooting).

## Try next

- Change `440.0` to another frequency or lengthen the 0.3 s window.
- Pass a stereo WAV and observe how mono conversion might differ (the helper may still expect mono float arrays - check [`audio_output.py`](../../src/voice_agents/audio/audio_output.py)).

# `latency_optimization.py` — code walkthrough

## Purpose

The script runs **one** blocking **`Kokoro.create`** call with a fixed phrase, then prints a small table. Each row answers a different question:

| Row | Meaning |
|-----|---------|
| **Audio duration** | How long the generated PCM would take to **play back** at the model’s sample rate. Computed as `len(audio) / sample_rate` seconds. This is the length of the **utterance**, not a timer running during synthesis. |
| **Synthesis wall time** | **Wall-clock** seconds from just before to just after **`create`** returns: ONNX inference and neural vocoding for that text, on your CPU (or whatever execution provider ONNX uses). It does **not** include writing a WAV or playing to speakers. |
| **RTF (real-time factor)** | **Synthesis wall time ÷ audio duration** — how many **seconds of compute** you spent for each **second of playable audio**. |

**Interpreting RTF:** If RTF is **below 1**, you produced the audio in **less** wall time than it takes to **listen** to it at 1× speed. You have **headroom**: a voice agent can often generate the next reply before the user would finish hearing an utterance of similar length, which is what you want for responsive dialogue. If RTF is **above 1**, synthesis took **longer** than the clip’s playback duration — for that text length and load, the machine is **not** keeping up with “generate one second of audio per second of wall clock,” so streaming or long replies may stall or stutter unless you shorten text, lighten load, or use faster hardware.

**Example (typical table):**

```
┃ Audio duration        │   3.904 │   ← ~3.9 s of audio at native SR
┃ Synthesis wall time   │   1.450 │   ← ~1.45 s on the CPU for that call
┃ RTF                   │   0.371 │   ← 1.450 / 3.904 ≈ 0.371 (faster than real time)
```

Here RTF **0.371** means you synthesized **about 2.7×** faster than real time (1 / 0.371 ≈ 2.7): roughly **2.7 seconds of audio per 1 second of wall clock** for this utterance.

**What this benchmark fixes:** The script uses **`speed=1.0`**, the **first** voice id from **`get_voices()`**, and a built-in **`text`** string. It does **not** sweep voices, speeds, or quantization — so it **reports** how this stack behaves on **your** machine under **current** OS load, for **that** phrase length, not an optimized production configuration.

## Run

```bash
uv run python 03_text_to_speech/latency_optimization/latency_optimization.py
```

## Dependencies

| Piece | Role |
|-------|------|
| **`kokoro_onnx.Kokoro`** | **`create`** returns **`(audio, sample_rate)`** for one string. |
| **Rich `Table`** | Pretty console metrics. |

## Code walkthrough

### Timing and RTF

```python
t0 = time.perf_counter()
audio, sr = k.create(text, voice=voice, speed=1.0)
synth_s = time.perf_counter() - t0
dur_s = len(audio) / float(sr)
rtf = synth_s / dur_s if dur_s > 0 else 0.0
```

- **`synth_s`** — matches **Synthesis wall time** in the table (same interval as **`create`**).
- **`dur_s`** — matches **Audio duration**: **`len(audio) / sr`**.
- **`rtf`** — **`synth_s / dur_s`**; see **Purpose** for how to read it.

**`voice`** is the first id returned by **`get_voices()`** - deterministic for benchmarking, not necessarily your favourite timbre.

### Paths

```python
ROOT = Path(__file__).resolve().parents[2]
```

Same **`parents[2]`** convention as other nested chapter scripts.

## Failure modes

Missing model files → [README troubleshooting](../README.md#troubleshooting).

## Try next

- Change **`text`** to a longer paragraph and watch RTF (often rises with length on CPU).

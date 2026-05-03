# `vad_debug.py`  -  code walkthrough

## Purpose

Apply a **fixed RMS threshold** per streaming block to label moments as “speech-like” vs “quiet.” This is a **debug toy**, not robust voice activity detection - it mirrors the *idea* used before dedicated VAD models (see chapter 06).

## Run

```bash
uv run python 01_audio_io/vad_debug/vad_debug.py
```

## Dependencies

Same streaming stack as [`stream_basics`](../stream_basics/CODE.md): `sounddevice.InputStream`, `numpy` for RMS. No library VAD - only `THRESH`.

Same **RMS block** idea is documented for agents in [chapter 06 voice activity detection](../../06_real_time_systems/voice_activity_detection/CODE.md) (reference snippet; this chapter stays the hands-on mic playground).

## Voice activity detection (VAD) and RMS

### What is VAD?

**Voice activity detection** means deciding, for each moment (here: each small chunk of audio), **whether speech is present or not**. Pipelines use that decision to:

- **Skip silence** so speech-to-text and other models run only when audio likely contains words (saves CPU and latency).
- **Segment utterances** - where turns start and stop - in conversational agents.
- **Wake** higher-level logic only when someone is actually talking.

Real products rarely rely on volume alone. They may use **learned models**, spectral features, or hybrid rules so that typing, HVAC rumble, or a cough are not always labelled “speech.” This script intentionally stays minimal: one scalar per block (**RMS**) and one cutoff (**`THRESH`**). That pattern is sometimes called **energy-based VAD** or **energy gating** - fine for checking that your mic levels make sense; easy to get wrong in noisy rooms because **anything loud enough** can count as `SPEECH`.

### What is RMS?

**RMS** stands for **root mean square**. For a block of samples it is:

$$
\text{RMS} = \sqrt{\frac{1}{N}\sum_{i=1}^{N} m_i^2}
$$

Same computation as in [`mic_input`](../mic_input/CODE.md) and [`stream_basics`](../stream_basics/CODE.md):

```python
rms = float(np.sqrt(np.mean(np.square(m))))
```

Intuition:

| Situation | Typical RMS |
|-----------|----------------|
| Silence or near‑silence | Close to **0** |
| Speech or other loud sound at the mic | **Higher** |

So RMS is a cheap **“how energetic is this slice?”** meter. It does **not** know phonemes or words - it only sees amplitude. A sustained hiss or traffic rumble can yield RMS similar to quiet speech if gains are wrong.

### How this script combines them

For **every** callback block, the script computes **RMS**, then compares it to **`THRESH`**:

- `rms >= THRESH` → print **`SPEECH`** (speech‑like *energy* for that slice).
- otherwise → print **`silence`**.

Adjust **`THRESH`** using what you learned from [`mic_input`](../mic_input/CODE.md) (typical RMS while speaking vs background). If everything reads `silence`, lower **`THRESH`** or raise gain; if nothing reads `silence`, raise **`THRESH`** or reduce noise.

## Code walkthrough

### Tunables shared with `stream_basics`

```python
SR = 16_000
BLOCK = 1024
THRESH = 0.015
```

Same **16 kHz** mono capture and **1024‑sample** blocks as [`stream_basics`](../stream_basics/stream_basics.py). **`THRESH`** is the only knob that turns RMS into a speech/silence label: RMS **≥** `THRESH` counts as “speech‑like” for debug prints.

---

### Callback: RMS then compare to threshold

```python
    def cb(indata, frames, t, status):
        m = indata.copy().reshape(-1)
        rms = float(np.sqrt(np.mean(np.square(m)))) if m.size else 0.0
        tag = "SPEECH" if rms >= THRESH else "silence"
        print(f"  {tag:7}  rms={rms:.4f}")
```

- **`copy()` / `reshape(-1)`**  -  Same defensive flattening as [`stream_basics`](../stream_basics/CODE.md).
- **RMS**  -  Same formula as elsewhere; compare numeric ranges with [`mic_input`](../mic_input/CODE.md).
- **`tag`**  -  Binary energy gate only - not phonetic detection.

Unlike `stream_basics`, there is **no `\r` overwrite**: each block prints **one new line**, so you get a scrollable trace of labels over time.

---

### Stream lifetime

```python
    with sd.InputStream(
        channels=1,
        samplerate=SR,
        blocksize=BLOCK,
        callback=cb,
        dtype="float32",
    ):
        import time

        time.sleep(6)
```

**Six seconds** of capture (vs **eight** in `stream_basics`). Same pattern: **`with`** opens the stream; **`sleep`** keeps the process alive while callbacks run; exiting the **`with`** stops capture.

For **live RMS bars** without speech/silence labels, see [`stream_basics/CODE.md`](../stream_basics/CODE.md).

## Failure modes

Everything `silence` → threshold too high or signal too quiet. Everything `SPEECH` → threshold too low or noisy environment. Device problems match [Troubleshooting](../README.md#troubleshooting).

## Try next

- Adjust `THRESH` up/down until labels match your intuition for your space.

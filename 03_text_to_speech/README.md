# Chapter 03 - Text to speech

This chapter turns **text into audio** using **Kokoro** (**ONNX**, fully **local**). After [chapter 02](../02_speech_to_text/) gave you transcripts, the agent pipeline needs **TTS** so replies are spoken aloud - the same stack appears in [chapter 00](../00_start_here/).

You will use **`voice_agents.tts`** helpers ([`streaming_tts.py`](../src/voice_agents/tts/streaming_tts.py)) plus **direct `kokoro_onnx`** where streaming or benchmarking is clearer without wrappers.

---

## Table of Contents

- [At a glance](#at-a-glance)
- [PCM and WAV output](#pcm-and-wav-output)
- [What this folder is for](#what-this-folder-is-for)
- [Prerequisites](#prerequisites)
- [Models](#models)
- [Suggested order to run the scripts](#suggested-order-to-run-the-scripts)
- [What each example does](#what-each-example-does)
- [Troubleshooting](#troubleshooting)
- [How this ties to the library](#how-this-ties-to-the-library)
- [Previous](#previous)
- [Next](#next)

---

## At a glance

| | |
|---|---|
| **Dependencies** | `uv sync` plus Kokoro assets under **`models/kokoro/`** (see [Models](#models) and [00_start_here/download_models.py](../00_start_here/download_models.py)). |
| **Done looks like** | A **`tmp/`** WAV from **`basic_tts`**, a **profile resolution table** from **`voice_profiles`**, **heard streaming speech** from **`streaming_tts`**, and an **RTF table** from **`latency_optimization`**. |

---

## PCM and WAV output

TTS models emit **PCM**: a sequence of **float** (or quantized) **samples** at a fixed **sample rate**. Kokoro targets **~24 kHz** mono for speech quality.

- **`basic_tts`** writes **float WAV** via **`soundfile`** ([`synthesize_to_wav`](../src/voice_agents/tts/streaming_tts.py)).
- **`streaming_tts`** feeds PCM **chunks** straight to **`sounddevice`** - no intermediate file unless you add one.

Chapter 02 explained PCM **into** the pipeline; here PCM goes **out** to disk or speakers.

---

## What this folder is for

| What you practice | Why it matters later |
|-------------------|----------------------|
| **Synthesize to a WAV file** | Easiest debugging - inspect **`tmp/tts_basic.wav`** in any player. |
| **Map personas to voices** | Keeps “assistant personality” decoupled from raw Kokoro ids. |
| **Stream chunks to speakers** | Matches responsive agents: play audio **before** the full sentence is synthesized. |
| **Measure RTF / latency** | Know whether your CPU can sustain **interactive** reply playback. |

---

## Prerequisites

From the repo root (after `uv sync`):

1. **Download Kokoro**  -  Run [00_start_here/download_models.py](../00_start_here/download_models.py) so **`kokoro-v1.0.onnx`** and **`voices-v1.0.bin`** exist under **`models/kokoro/`**.
2. **Audio output**  -  For **`streaming_tts`**, speakers or headphones must work ([chapter 01](../01_audio_io/) if you need to verify routing).

**Optional  -  Piper:** For a Piper CLI workflow, install the **`piper`** binary from [rhasspy/piper releases](https://github.com/rhasspy/piper/releases) and supply ONNX voices manually; **this repo standardizes on Kokoro** for pip-only tutorials.

Run examples with:

```bash
uv run python 03_text_to_speech/<folder>/<script>.py
```

---

## Models

| Asset | Role | Rough size (see [00 models table](../00_start_here/README.md)) |
|-------|------|----------------------------------------------------------------|
| **`kokoro-v1.0.onnx`** | Kokoro inference graph | ~on order of **310 MB** combined with voices in docs |
| **`voices-v1.0.bin`** | Voice embeddings / ids | bundled footprint with ONNX in docs |

Paths used in code: **`ROOT / models / kokoro / …`** with **`ROOT`** at the **repository root**.

---

## Suggested order to run the scripts

| Order | Script | One-line purpose | Success check |
|------:|--------|------------------|----------------|
| 1 | [`basic_tts/basic_tts.py`](./basic_tts/basic_tts.py) | Text → **WAV** on disk. | Console shows **`Wrote …/tmp/tts_basic.wav`**. |
| 2 | [`voice_profiles/voice_profiles.py`](./voice_profiles/voice_profiles.py) | Print **profile → voice + speed**. | Lines like **`calm → …`** |
| 3 | [`streaming_tts/streaming_tts.py`](./streaming_tts/streaming_tts.py) | **Stream** synthesis to speakers. | You **hear** speech from default output device. |
| 4 | [`latency_optimization/latency_optimization.py`](./latency_optimization/latency_optimization.py) | **RTF** benchmark table. | Rich **table** with duration, wall time, RTF. |

---

## What each example does

### `basic_tts/basic_tts.py`

**Source:** [`basic_tts.py`](./basic_tts/basic_tts.py)  -  **Learning deeper:** [`CODE.md`](./basic_tts/CODE.md)

Uses [`TTSConfig`](../src/voice_agents/tts/streaming_tts.py), [`pick_voice`](../src/voice_agents/tts/streaming_tts.py), and [`synthesize_to_wav`](../src/voice_agents/tts/streaming_tts.py). Writes **`tmp/tts_basic.wav`**.

```bash
uv run python 03_text_to_speech/basic_tts/basic_tts.py
echo "Hello from the pipe." | uv run python 03_text_to_speech/basic_tts/basic_tts.py
```

The first line uses a built-in demo phrase. For **your own words**, pipe text on stdin (second line). **`Synthesizing:`** shows what Kokoro speaks.

---

### `voice_profiles/voice_profiles.py`

**Source:** [`voice_profiles.py`](./voice_profiles/voice_profiles.py)  -  **Learning deeper:** [`CODE.md`](./voice_profiles/CODE.md)

Defines **`PROFILES`** and prints resolved **`TTSConfig`** fields for each - no audio file written.

```bash
uv run python 03_text_to_speech/voice_profiles/voice_profiles.py
```

---

### `streaming_tts/streaming_tts.py`

**Source:** [`streaming_tts.py`](./streaming_tts/streaming_tts.py)  -  **Learning deeper:** [`CODE.md`](./streaming_tts/CODE.md)

**Async** **`create_stream`** loop + **`sounddevice`** playback; optional CLI text.

```bash
uv run python 03_text_to_speech/streaming_tts/streaming_tts.py
uv run python 03_text_to_speech/streaming_tts/streaming_tts.py Streaming playback demo.
```

---

### `latency_optimization/latency_optimization.py`

**Source:** [`latency_optimization.py`](./latency_optimization/latency_optimization.py) — **Learning deeper:** [`CODE.md`](./latency_optimization/CODE.md)

One **`Kokoro.create`** call wrapped in **`perf_counter`**. The Rich table shows **audio duration** (playback length of the PCM at the model sample rate), **synthesis wall time** (compute only, no disk or speaker), and **RTF** = wall time ÷ duration (below 1 means faster than real-time playback). Full definitions and a worked example are in [`CODE.md`](./latency_optimization/CODE.md).

```bash
uv run python 03_text_to_speech/latency_optimization/latency_optimization.py
```

---

## Troubleshooting

- **“Download Kokoro models first” / missing ONNX or voices**  -  Run [download_models.py](../00_start_here/download_models.py); confirm **`models/kokoro/`** contains both files.
- **No sound from `streaming_tts`**  -  Wrong default output device or muted - see [chapter 01 Troubleshooting](../01_audio_io/README.md#troubleshooting).
- **First run slow, later runs faster**  -  ONNX session warm-up; normal on CPU.
- **Permission errors writing `tmp/`**  -  Ensure the repo **`tmp/`** directory is writable.
- **Always hear the demo phrase from `basic_tts`**  -  Custom wording must be **piped** into the script (`echo "…" | uv run python …`), not passed after the script path. See [above](#basic_ttsbasic_ttspy).

---

## How this ties to the library

- **[`voice_agents.tts.streaming_tts`](../src/voice_agents/tts/streaming_tts.py)**  -  [`TTSConfig`](../src/voice_agents/tts/streaming_tts.py), [`synthesize_to_wav`](../src/voice_agents/tts/streaming_tts.py), [`pick_voice`](../src/voice_agents/tts/streaming_tts.py), [`list_voices`](../src/voice_agents/tts/streaming_tts.py) power **`basic_tts`** and **`voice_profiles`**.
- **`kokoro_onnx.Kokoro`**  -  Used **directly** in **`streaming_tts`** (`create_stream`) and **`latency_optimization`** (`create`) so you see the raw API alongside the helpers.

---

## Previous

[Chapter 02 - Speech to text](../02_speech_to_text/README.md)  -  Whisper transcripts from WAV or mic.

---

## Next

[Chapter 04 - Agent core](../04_agent_core/README.md)  -  prompts, memory, and reply loops around an LLM.

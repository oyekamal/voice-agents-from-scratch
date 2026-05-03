# Chapter 05 - Full voice loop

This chapter connects **microphone → speech-to-text → local LLM → text-to-speech → speakers** end-to-end  -  the same stack introduced in [chapter 00](../00_start_here/), but with **two styles**: **blocking** (simplest timeline) and **streaming** (start speaking before the full reply is generated). A third script **`debug_latency`** prints **stage timings** so you can see where latency comes from on your hardware.

**Previous:** [Chapter 04 - Agent core](../04_agent_core/README.md)  -  prompts and LLM without audio.

---

## Table of Contents

- [At a glance](#at-a-glance)
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
| **Dependencies** | `uv sync`, working **microphone** and **speakers/headphones** ([chapter 01](../01_audio_io/)), and downloaded assets under **`models/`** (see [Models](#models)). |
| **Done looks like** | **`tmp/blocking_*.wav`** from **`blocking_voice_agent`**, **heard chunked speech** from **`streaming_voice_agent`**, and a **Rich latency table** + **`tmp/latency_response.wav`** from **`debug_latency`**. |

---

## What this folder is for

| What you practice | Why it matters later |
|-------------------|----------------------|
| **Blocking pipeline** | Easiest to reason about  -  matches “record → think → speak” mental model. |
| **Streaming LLM → chunked TTS** | Closer to **responsive** products: user hears the first sentence sooner. |
| **Per-stage timings** | Optimize what actually dominates **your** CPU (STT vs LLM vs TTS). |

---

## Prerequisites

From the repo root (after `uv sync`):

1. **Download models**  -  [00_start_here/download_models.py](../00_start_here/download_models.py) (**Whisper**, **Qwen GGUF**, **Kokoro**).
2. **Audio**  -  Verify mic and default output ([chapter 01](../01_audio_io/) troubleshooting if needed).

Run examples with:

```bash
uv run python 05_full_voice_loop/<folder>/<script>.py
```

---

## Models

| Asset | Role |
|-------|------|
| **Whisper** cache under **`models/whisper/`** | STT ([`transcribe_samples`](../src/voice_agents/stt/streaming_stt.py)). |
| **`qwen2.5-0.5b-instruct-q4_k_m.gguf`** | Local LLM ([`AgentCore`](../src/voice_agents/agent/agent_core.py)). |
| **`kokoro-v1.0.onnx`** + **`voices-v1.0.bin`** | Kokoro TTS. |

Paths in scripts use **`ROOT / models / …`** with **`ROOT`** at the **repository root** (**`parents[2]`**).

---

## Suggested order to run the scripts

| Order | Script | One-line purpose | Success check |
|------:|--------|------------------|----------------|
| 1 | [`blocking_voice_agent/blocking_voice_agent.py`](./blocking_voice_agent/blocking_voice_agent.py) | Linear **record → STT → LLM → WAV → play**. | You hear the assistant; **`tmp/blocking_input.wav`** / **`blocking_response.wav`** exist. |
| 2 | [`streaming_voice_agent/streaming_voice_agent.py`](./streaming_voice_agent/streaming_voice_agent.py) | **Stream** tokens; speak **sentence chunks**. | Speech starts **during** generation for longer answers (CLI text optional). |
| 3 | [`debug_latency/debug_latency.py`](./debug_latency/debug_latency.py) | **Timed** stages + **`tmp/latency_response.wav`**. | Rich **Latency stages** table with colored rows. |

---

## What each example does

### `blocking_voice_agent/blocking_voice_agent.py`

**Source:** [`blocking_voice_agent.py`](./blocking_voice_agent/blocking_voice_agent.py)  -  **Learning deeper:** [`CODE.md`](./blocking_voice_agent/CODE.md)

Confirm-record prompt, then full blocking pipeline. Optional **`--seconds`** for clip length.

```bash
uv run python 05_full_voice_loop/blocking_voice_agent/blocking_voice_agent.py
uv run python 05_full_voice_loop/blocking_voice_agent/blocking_voice_agent.py --seconds 10
```

---

### `streaming_voice_agent/streaming_voice_agent.py`

**Source:** [`streaming_voice_agent.py`](./streaming_voice_agent/streaming_voice_agent.py)  -  **Learning deeper:** [`CODE.md`](./streaming_voice_agent/CODE.md)

With **no extra arguments**, records **5 s** and transcribes. With **arguments**, skips the mic and uses that text as the user message.

```bash
uv run python 05_full_voice_loop/streaming_voice_agent/streaming_voice_agent.py
uv run python 05_full_voice_loop/streaming_voice_agent/streaming_voice_agent.py "What is the speed of light?"
```

---

### `debug_latency/debug_latency.py`

**Source:** [`debug_latency.py`](./debug_latency/debug_latency.py)  -  **Learning deeper:** [`CODE.md`](./debug_latency/CODE.md)

**3 s** recording (no yes/no prompt), then STT → LLM → TTS → playback with timings.

```bash
uv run python 05_full_voice_loop/debug_latency/debug_latency.py
```

---

## Troubleshooting

- **Missing model paths**  -  Run [download_models.py](../00_start_here/download_models.py); confirm **`models/whisper/`**, **`models/llm/`**, **`models/kokoro/`**.
- **Empty `You:` / no assistant reply**  -  Silence or noise during recording; try again or use **`streaming_voice_agent`** with CLI text.
- **No playback**  -  Wrong output device or muted  -  [chapter 01](../01_audio_io/README.md#troubleshooting).
- **First run slow**  -  Whisper / LLM / ONNX warm-up; normal.

---

## How this ties to the library

- **[`voice_agents.audio`](../src/voice_agents/audio/)**  -  capture, WAV I/O, playback.
- **[`voice_agents.stt.streaming_stt`](../src/voice_agents/stt/streaming_stt.py)**  -  Whisper transcription.
- **[`voice_agents.agent`](../src/voice_agents/agent/)**  -  [`AgentCore`](../src/voice_agents/agent/agent_core.py) **`complete`** vs **`stream_tokens`**.
- **[`voice_agents.tts.streaming_tts`](../src/voice_agents/tts/streaming_tts.py)**  -  Kokoro helpers; **`streaming_voice_agent`** also calls **`kokoro_onnx`** directly for chunked **`create`**.

---

## Previous

[Chapter 04 - Agent core](../04_agent_core/README.md)  -  LLM and prompts without audio.

---

## Next

[Chapter 06 - Real-time systems](../06_real_time_systems/README.md)  -  raw-stack scripts (no `voice_agents`): [suggested order](../06_real_time_systems/README.md#suggested-order); full loop + Rich panel in [`turn_taking/turn_taking.py`](../06_real_time_systems/turn_taking/turn_taking.py).

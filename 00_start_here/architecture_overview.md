# Architecture overview (chapter 00)

This chapter runs a **blocking** pipeline: each stage finishes before the next starts. Later chapters add **streaming** and **full-duplex** behavior.

**What each stage does (one line each):**

| Label | Meaning |
|-------|---------|
| **Microphone** | Captures sound as **PCM** (numbers per sample at a fixed rate, often 16 kHz mono). |
| **STT** | **Speech-to-text** (here: Whisper via faster-whisper) turns that audio into a text string. |
| **LLM** | **Large language model** (here: a local GGUF via llama-cpp-python) reads the text and generates a reply string. |
| **TTS** | **Text-to-speech** (here: Kokoro) turns the reply into audio samples (PCM float, typically 24 kHz). |
| **Speaker** | Plays those samples; the demo usually streams to the device without requiring a WAV file on disk. |

## Data flow (high level)

![data-flow.png](../diagrams/data-flow.png)

## Sequence: `run_first_voice_agent.py`

![sequence.png](../diagrams/sequence.png)

## Library layout (`src/voice_agents/`)

| Area | Role |
|------|------|
| `audio/` | Record + play |
| `stt/` | `faster-whisper` wrappers |
| `tts/` | Kokoro → PCM/float audio (helpers can also write WAV for debugging) |
| `agent/` | Qwen-style chat prompt + `llama-cpp-python` |
| `tools/` | Pydantic + JSON Schema (chapter 07) |

## State and memory

Chapter 00 uses a **single turn** (one recording). `PromptEngine` in the library can hold **short memory strings** for multi-turn demos in later chapters. A **TTL session store** (`SessionStore`) supports future web / multi-user flows (chapter 10).

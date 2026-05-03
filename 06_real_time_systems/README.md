# Chapter 06 - Real-time systems

This chapter uses **the same models as chapter 05** (Whisper, Qwen GGUF, Kokoro) but **does not import [`voice_agents`](../src/voice_agents/)**  -  each script wires **faster-whisper**, **llama-cpp-python**, **kokoro-onnx**, and **sounddevice** explicitly so you see the control flow (threads, RMS gate, chunked playback, FSM).

Shared helpers live only under this chapter: [`_model_paths.py`](./_model_paths.py), [`_audio_chunks.py`](./_audio_chunks.py).

**Previous:** [Chapter 05 - Full voice loop](../05_full_voice_loop/README.md).

---

## Table of Contents

- [At a glance](#at-a-glance)
- [Prerequisites](#prerequisites)
- [Suggested order](#suggested-order)
- [What each example does](#what-each-example-does)
- [Troubleshooting](#troubleshooting)
- [How this ties to the library](#how-this-ties-to-the-library)
- [Previous](#previous)
- [Next](#next)

---

## At a glance

| | |
|---|---|
| **Dependencies** | `uv sync`. Models from [chapter 00](../00_start_here/). **Mic** for VAD + duplex + turn-taking; **speakers/headphones** for duplex + interruption + turn-taking. **Headphones** recommended for duplex / barge-in (speaker bleed). |
| **Done looks like** | Live RMS meter (`voice_activity_detection`); Kokoro playback interrupted by mic (`duplex_conversation`) or by prompt (`interruption_handling`); full **LISTENING → THINKING → SPEAKING** loop with optional Rich panel (`turn_taking`). |

---

## Prerequisites

1. **Models**  -  Run [`00_start_here/download_models.py`](../00_start_here/download_models.py) if `models/` is incomplete.
2. **Audio devices**  -  [Chapter 01](../01_audio_io/) if capture/playback fails.
3. **`tmp/latency_response.wav`**  -  For **`interruption_handling`** only, generate once with [`debug_latency`](../05_full_voice_loop/debug_latency/debug_latency.py).

---

## Suggested order

| Order | Script | Purpose |
|------:|--------|---------|
| 1 | [`voice_activity_detection/voice_activity_detection.py`](./voice_activity_detection/voice_activity_detection.py) | Live RMS meter + speech-ish block counts (`--seconds`, optional threshold). |
| 2 | [`duplex_conversation/duplex_conversation.py`](./duplex_conversation/duplex_conversation.py) | Long Kokoro utterance; mic RMS can **cancel** chunked playback (barge-in). |
| 3 | [`interruption_handling/interruption_handling.py`](./interruption_handling/interruption_handling.py) | Same WAV as latency debug; **Rich prompt** cooperatively cancels playback. |
| 4 | [`turn_taking/turn_taking.py`](./turn_taking/turn_taking.py) | Full raw stack + FSM + session **Rich Live** panel (`--plain`, `--dry-run`, `--no-barge-in`). |

---

## What each example does

From the **repository root** (after `uv sync` and models from [chapter 00](../00_start_here/)).

### `voice_activity_detection/voice_activity_detection.py`

**Source:** [`voice_activity_detection.py`](./voice_activity_detection/voice_activity_detection.py)  -  **Learning deeper:** [`voice_activity_detection/CODE.md`](./voice_activity_detection/CODE.md)

Live **Rich** RMS meter and **`Speech-ish blocks: a/b`** summary; optional positional **threshold**; **`--seconds`** for capture length.

```bash
uv run python 06_real_time_systems/voice_activity_detection/voice_activity_detection.py
uv run python 06_real_time_systems/voice_activity_detection/voice_activity_detection.py 0.03 --seconds 8
```

---

### `duplex_conversation/duplex_conversation.py`

**Source:** [`duplex_conversation.py`](./duplex_conversation/duplex_conversation.py)  -  **Learning deeper:** [`duplex_conversation/CODE.md`](./duplex_conversation/CODE.md)

Long **Kokoro** utterance played in chunks; **mic RMS** can cooperative-cancel playback (barge-in). Prefer **headphones** to reduce speaker bleed.

```bash
uv run python 06_real_time_systems/duplex_conversation/duplex_conversation.py
```

---

### `interruption_handling/interruption_handling.py`

**Source:** [`interruption_handling.py`](./interruption_handling/interruption_handling.py)  -  **Learning deeper:** [`interruption_handling/CODE.md`](./interruption_handling/CODE.md)

Loads **`tmp/latency_response.wav`**; **Rich** yes/no prompt sets **`cancel`** while chunked playback runs in a thread.

```bash
uv run python 05_full_voice_loop/debug_latency/debug_latency.py
uv run python 06_real_time_systems/interruption_handling/interruption_handling.py
```

---

### `turn_taking/turn_taking.py`

**Source:** [`turn_taking.py`](./turn_taking/turn_taking.py)  -  **Learning deeper:** [`turn_taking/CODE.md`](./turn_taking/CODE.md)

**LISTENING → THINKING → SPEAKING** with **faster-whisper**, **Llama**, **Kokoro**, and optional **barge-in** during **SPEAKING**. Session fields in a **`dict`** + **Rich Live** unless **`--plain`**.

```bash
uv run python 06_real_time_systems/turn_taking/turn_taking.py
uv run python 06_real_time_systems/turn_taking/turn_taking.py --seconds 4 --plain
uv run python 06_real_time_systems/turn_taking/turn_taking.py --dry-run --plain
```

---

## Troubleshooting

- **Missing models**  -  Download script in chapter 00; paths are checked at startup for **`turn_taking`**.
- **Mic busy / PortAudio errors**  -  Do not open two exclusive streams on the same device; **`turn_taking`** records with **`sd.rec`** while monitoring uses **`InputStream`** only during **SPEAKING** (see code).
- **`interruption_handling` missing WAV**  -  Run **`debug_latency`** once.
- **Duplex false interrupts**  -  Lower playback volume, raise RMS threshold in code, or **use headphones**.

---

## How this ties to the library

- **[`voice_agents`](../src/voice_agents/)**  -  Same ideas (`play_float_mono`, `AgentCore`, etc.) with cleaner abstractions; chapter 06 shows the **unpackaged** wiring.
- **`SessionStore`**  -  Not used here; **`turn_taking`** uses a plain **`dict`** + Rich panel instead.

---

## Previous

[Chapter 05 - Full voice loop](../05_full_voice_loop/README.md)

---

## Next

[Chapter 07 - Tools](../07_tools/README.md)

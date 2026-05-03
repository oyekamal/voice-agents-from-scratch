# Chapter 09 - Projects

**Why this chapter exists:** Earlier chapters built **layers** (audio, STT, LLM, TTS, tools, persona). Chapter 09 shows **composition**: each subfolder demonstrates **one glue skill** - how to attach the library pieces into something product-shaped **without** fine-tuning weights.

**How to read the diagram:** boxes are **prior chapters**; arrows show **what each capstone imports or mirrors**.

```mermaid
flowchart LR
  ch04[ch.04 PromptEngine + AgentCore]
  ch05[ch.05 streaming voice loop]
  ch08[ch.08 hint_from_text idea]
  ch07[ch.07 ToolRegistry + chapter_registry]
  tutor[voice_tutor]
  interviewer[voice_interviewer]
  therapist[therapist_bot]
  cli[cli_assistant]
  capstone[Together cover composition]

  ch04 --> interviewer
  ch04 --> therapist
  ch04 --> cli
  ch04 --> tutor
  ch05 --> tutor
  ch08 --> therapist
  ch07 --> cli

  interviewer -->|"memory across turns"| capstone
  therapist -->|"dynamic persona"| capstone
  cli -->|"tools dispatch"| capstone
  tutor -->|"mic STT + stream + Kokoro"| capstone
```

**Composition matrix**  -  each row is one lesson; together they cover how a voice-agent codebase usually grows.

| Project | Memory | Dynamic persona | Tools | Mic + STT + TTS |
|---------|:---:|:---:|:---:|:---:|
| [`voice_interviewer`](#voice_interviewervoice_interviewerpy) | yes |  -  |  -  |  -  |
| [`therapist_bot`](#therapist_bottherapist_botpy) | yes | yes |  -  |  -  |
| [`cli_assistant`](#cli_assistantcli_assistantpy) |  -  |  -  | yes |  -  |
| [`voice_tutor`](#voice_tutorvoice_tutorpy) |  -  |  -  |  -  | yes |

**`therapist_bot` disclaimer:** the script is a **teaching sketch** for prompts + memory. It is **not** therapy, crisis support, or medical advice.

**Previous:** [Chapter 08 - Personality](../08_personality/README.md).

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
| **Dependencies** | `uv sync`. **LLM** GGUF under **`models/llm/`** for all four. **`voice_tutor`** also needs **Whisper** + **Kokoro** (see [chapter 00](../00_start_here/README.md)). **`cli_assistant`** may use **network** for **`weather`** / **`search`** tools. |
| **Done looks like** | **`voice_interviewer`:** multi-turn interview until empty line / quit. **`therapist_bot`:** REPL with **`(hint -> …)`** each turn. **`cli_assistant`:** each **`>`** line prints router JSON, tool output, then summary. **`voice_tutor`:** you speak (or `--text`), hear streamed tutor speech. |

---

## Prerequisites

1. **Environment**  -  From the repository root: `uv sync`.
2. **Models**  -  Run [`00_start_here/download_models.py`](../00_start_here/download_models.py). At minimum every script needs **`qwen2.5-0.5b-instruct-q4_k_m.gguf`**. **`voice_tutor`** also needs Whisper cache + Kokoro ONNX/voices under **`models/`**.
3. **Optional reads**  -  [`PromptEngine`](../src/voice_agents/agent/prompt_engine.py), [`AgentCore`](../src/voice_agents/agent/agent_core.py), [`chapter_registry.py`](../07_tools/chapter_registry.py).

---

## Suggested order

Smallest new concept first; **`voice_tutor`** last as the full **audio** capstone.

| Order | Script | Composition skill |
|------:|--------|---------------------|
| 1 | [`voice_interviewer/voice_interviewer.py`](./voice_interviewer/voice_interviewer.py) | Shared **`PromptEngine`** → **`memory_lines`** across turns |
| 2 | [`therapist_bot/therapist_bot.py`](./therapist_bot/therapist_bot.py) | Same engine + **rewrite `system_prompt`** each turn (`hint_from_text`) |
| 3 | [`cli_assistant/cli_assistant.py`](./cli_assistant/cli_assistant.py) | **`chapter_registry`** + router JSON + **`reg.call`** + summarizer |
| 4 | [`voice_tutor/voice_tutor.py`](./voice_tutor/voice_tutor.py) | Chapter **05** streaming loop + **tutor** persona only |

---

## What each example does

From the **repository root** (after `uv sync`).

### `voice_interviewer/voice_interviewer.py`

**Source:** [`voice_interviewer.py`](./voice_interviewer/voice_interviewer.py)  -  **Learning deeper:** [`voice_interviewer/CODE.md`](./voice_interviewer/CODE.md)

Behavioral interview REPL. **`Candidate`** prompt; **`Interviewer`** replies use earlier turns via **`PromptEngine.build_user_message`**.

```bash
uv run python 09_projects/voice_interviewer/voice_interviewer.py
```

---

### `therapist_bot/therapist_bot.py`

**Source:** [`therapist_bot.py`](./therapist_bot/therapist_bot.py)  -  **Learning deeper:** [`therapist_bot/CODE.md`](./therapist_bot/CODE.md)

Supportive-listener **sketch** (not clinical). Each turn shows **`(hint -> …)`** from a toy keyword map (same idea as [chapter 08 `emotional_responses`](../08_personality/emotional_responses/emotional_responses.py)).

```bash
uv run python 09_projects/therapist_bot/therapist_bot.py
```

---

### `cli_assistant/cli_assistant.py`

**Source:** [`cli_assistant.py`](./cli_assistant/cli_assistant.py)  -  **Learning deeper:** [`cli_assistant/CODE.md`](./cli_assistant/CODE.md)

Tools REPL: model emits **one JSON tool call** → **`ToolRegistry.call`** → second completion summarizes. **`--calc-only`** registers **calc** only (easier for tiny models).

```bash
uv run python 09_projects/cli_assistant/cli_assistant.py
uv run python 09_projects/cli_assistant/cli_assistant.py --calc-only
```

---

### `voice_tutor/voice_tutor.py`

**Source:** [`voice_tutor.py`](./voice_tutor/voice_tutor.py)  -  **Learning deeper:** [`voice_tutor/CODE.md`](./voice_tutor/CODE.md)

Default: **5 s** recording → Whisper → streaming LLM → Kokoro playback by sentence. **`--text`** skips the mic.

```bash
uv run python 09_projects/voice_tutor/voice_tutor.py
uv run python 09_projects/voice_tutor/voice_tutor.py --text "Explain recursion with a tiny example."
```

---

## Troubleshooting

- **Missing GGUF**  -  Run [`download_models.py`](../00_start_here/download_models.py); confirm **`models/llm/qwen2.5-0.5b-instruct-q4_k_m.gguf`** exists.
- **`voice_tutor`: missing Whisper/Kokoro paths**  -  Same as [chapter 05](../05_full_voice_loop/README.md): full **`models/`** download from chapter 00.
- **No mic / bad recording**  -  Use **`--text`**; see [chapter 01](../01_audio_io/README.md) if you want to debug capture.
- **No playback / wrong device**  -  [chapter 01](../01_audio_io/README.md) output troubleshooting.
- **`cli_assistant` slow per line**  -  Two **`complete`** calls (router + summary). **`--calc-only`** shrinks router schema; tiny models may still emit invalid JSON - compare with [`07_tools/llm_tool_loop`](../07_tools/llm_tool_loop/llm_tool_loop.py).
- **`cli_assistant` HTTP / tool errors**  -  **`weather`** / **`search`** need network; failures surface from the tool implementation.
- **`ModuleNotFoundError: voice_agents`**  -  Run with **`uv run python ...`** from repo root.
- **`Import` / `chapter_registry` issues**  -  Script inserts **`07_tools/`** on **`sys.path`** (same pattern as chapter 07); run paths as shown above.

---

## How this ties to the library

- **[`PromptEngine`](../src/voice_agents/agent/prompt_engine.py)**  -  **`system_prompt`**, **`memory_lines`**, **`build_user_message`**.
- **[`AgentCore`](../src/voice_agents/agent/agent_core.py)**  -  **`complete`** (interviewer, therapist, CLI) and **`stream_tokens`** (**`voice_tutor`**).
- **Audio / STT**  -  [`record_seconds`](../src/voice_agents/audio/audio_input.py), [`transcribe_samples`](../src/voice_agents/stt/streaming_stt.py), [`play_float_mono`](../src/voice_agents/audio/audio_output.py).
- **Tools**  -  [`ToolRegistry`](../src/voice_agents/tools/registry.py), [`07_tools/chapter_registry.py`](../07_tools/chapter_registry.py), reference loop [`07_tools/llm_tool_loop/llm_tool_loop.py`](../07_tools/llm_tool_loop/llm_tool_loop.py).
- **Persona / tone toy**  -  [`08_personality/emotional_responses/emotional_responses.py`](../08_personality/emotional_responses/emotional_responses.py) (`hint_from_text` source for **`therapist_bot`**).

---

## Previous

[Chapter 08 - Personality](../08_personality/README.md)

---

## Next

[Chapter 10 - Deployment](../10_deployment/README.md)

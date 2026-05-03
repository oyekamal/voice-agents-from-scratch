# Chapter 04 - Agent core

This chapter runs the **local GGUF** LLM (**Qwen2.5 instruct**) with the same **chat template** and **[`PromptEngine`](../src/voice_agents/agent/prompt_engine.py)** stack used in [chapter 00](../00_start_here/) and [chapter 05](../05_full_voice_loop/)  -  **without microphone or speaker**. You practice **prompt construction**, **one-shot and REPL** completions, **memory context**, and **prompt inspection** before wiring STT and TTS.

---

## Table of Contents

- [At a glance](#at-a-glance)
- [Why text-only](#why-text-only)
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
| **Dependencies** | `uv sync` plus **`llama-cpp-python`** and the **Qwen2.5** GGUF under **`models/llm/`** (see [Models](#models) and [00_start_here/download_models.py](../00_start_here/download_models.py)). |
| **Done looks like** | Printed **message preview** from **`prompt_engine`**, a **single reply** from **`simple_agent`**, **`>` prompts + answers** (or **one piped answer**) from **`response_loop`**, a **multi-turn session** from **`memory`**, and a **prompt tail + reply** from **`debug_flow`**. |

---

## Why text-only

STT and TTS add latency and moving parts. Here every script reads **plain text** (CLI, stdin, or typed input) and prints to the console so you can focus on **what the model receives** and **how [`PromptEngine`](../src/voice_agents/agent/prompt_engine.py) shapes it**. [Chapter 05](../05_full_voice_loop/) reuses the same **[`AgentCore`](../src/voice_agents/agent/agent_core.py)** pattern with audio.

---

## What this folder is for

| What you practice | Why it matters later |
|-------------------|----------------------|
| **Build user messages with memory** | Voice agents need **context** across turns; **`build_user_message`** is the same idea as “what goes into the LLM after VAD + ASR.” |
| **One-shot and REPL completions** | Debug **replies and templates** before debugging sample rates and buffers. |
| **Inspect the Qwen prompt string** | When replies look wrong, verify **system + user** formatting (`debug_flow`) before blaming Whisper or Kokoro. |

---

## Prerequisites

From the repo root (after `uv sync`):

1. **Download the LLM**  -  Run [00_start_here/download_models.py](../00_start_here/download_models.py) so **`qwen2.5-0.5b-instruct-q4_k_m.gguf`** exists under **`models/llm/`**.
2. **`llama-cpp-python`**  -  If install fails, use the [wheel index](https://abetlen.github.io/llama-cpp-python/) described in the root [README.md](../README.md).

Run examples with:

```bash
uv run python 04_agent_core/<folder>/<script>.py
```

**Exception:** **`prompt_engine`** does **not** load the GGUF (prompt-only demo).

---

## Models

| Asset | Role | Notes |
|-------|------|--------|
| **`qwen2.5-0.5b-instruct-q4_k_m.gguf`** | Qwen2.5 **instruct** weights for **llama.cpp** | Quantized **Q4_K_M**; path in code is **`ROOT / models / llm / …`** with **`ROOT`** at the **repository root**. |

---

## Suggested order to run the scripts

| Order | Script | One-line purpose | Success check |
|------:|--------|------------------|----------------|
| 1 | [`prompt_engine/prompt_engine.py`](./prompt_engine/prompt_engine.py) | **`PromptEngine`** preview (no LLM load). | Printed **Built user message preview** block. |
| 2 | [`simple_agent/simple_agent.py`](./simple_agent/simple_agent.py) | Single **`complete`** + optional CLI question. | One **assistant** paragraph on stdout. |
| 3 | [`response_loop/response_loop.py`](./response_loop/response_loop.py) | **Interactive `>`** turns or **one pipe** = one answer. | You see **`>`**, answers, **empty Enter** exits; pipe prints once. |
| 4 | [`memory/memory.py`](./memory/memory.py) | Chat after **`You:`**; model prompted to remember facts. | **`Assistant`** replies each turn; **`quit`** exits. |
| 5 | [`debug_flow/debug_flow.py`](./debug_flow/debug_flow.py) | **Prompt tail** + **`complete`**. | **`Prompt tail`** section then **`Reply:`**. |

---

## What each example does

### `prompt_engine/prompt_engine.py`

**Source:** [`prompt_engine.py`](./prompt_engine/prompt_engine.py)  -  **Learning deeper:** [`CODE.md`](./prompt_engine/CODE.md)

Uses only [`PromptEngine`](../src/voice_agents/agent/prompt_engine.py): custom **system** text, **`add_memory`**, **`build_user_message`**. No GGUF.

```bash
uv run python 04_agent_core/prompt_engine/prompt_engine.py
```

---

### `simple_agent/simple_agent.py`

**Source:** [`simple_agent.py`](./simple_agent/simple_agent.py)  -  **Learning deeper:** [`CODE.md`](./simple_agent/CODE.md)

[`AgentCore`](../src/voice_agents/agent/agent_core.py) + default [`PromptEngine`](../src/voice_agents/agent/prompt_engine.py). Optional arguments become the user question.

```bash
uv run python 04_agent_core/simple_agent/simple_agent.py
uv run python 04_agent_core/simple_agent/simple_agent.py "What is 2+2?"
```

---

### `response_loop/response_loop.py`

**Source:** [`response_loop.py`](./response_loop/response_loop.py)  -  **Learning deeper:** [`CODE.md`](./response_loop/CODE.md)

**Interactive:** run the command, wait for **`>`**, type a question, press **Enter**, read the answer, repeat. **Exit:** press **Enter** on an empty line at **`>`** (no text typed), or **Ctrl+C**. **Pipe:** `echo "…" | uv run python …` sends one question and exits without prompts.

```bash
uv run python 04_agent_core/response_loop/response_loop.py
echo "Hello" | uv run python 04_agent_core/response_loop/response_loop.py
```

---

### `memory/memory.py`

**Source:** [`memory.py`](./memory/memory.py)  -  **Learning deeper:** [`CODE.md`](./memory/CODE.md)

After **`You:`**, type normal sentences to the assistant (examples appear when you run it). Ask follow-up questions that need remembering earlier lines. **`quit`** / **`exit`** ends the session.

```bash
uv run python 04_agent_core/memory/memory.py
```

---

### `debug_flow/debug_flow.py`

**Source:** [`debug_flow.py`](./debug_flow/debug_flow.py)  -  **Learning deeper:** [`CODE.md`](./debug_flow/CODE.md)

Prints the **last 400 characters** of the full **Qwen-style** prompt ([`qwen25_chat_prompt`](../src/voice_agents/agent/agent_core.py)), then runs **`complete`**. **Text-only**  -  no STT/TTS in this script; it isolates the **LLM** stage for debugging.

```bash
uv run python 04_agent_core/debug_flow/debug_flow.py
uv run python 04_agent_core/debug_flow/debug_flow.py Say hello in two words.
```

---

## Troubleshooting

- **“Download LLM first” / missing GGUF**  -  Run [download_models.py](../00_start_here/download_models.py); confirm **`models/llm/qwen2.5-0.5b-instruct-q4_k_m.gguf`** exists.
- **`llama-cpp-python` build failure**  -  Use the [extra wheel index](https://abetlen.github.io/llama-cpp-python/) (see root [README.md](../README.md)).
- **First reply slow**  -  First **`Llama`** load **mmap**s the GGUF; later **`complete`** calls are faster on the same process.
- **Garbled or empty output**  -  Try lowering **`max_tokens`** or temperature in your own edits; small models can ramble or stop oddly with long prompts.

---

## How this ties to the library

- **[`voice_agents.agent.agent_core`](../src/voice_agents/agent/agent_core.py)**  -  [`AgentCore`](../src/voice_agents/agent/agent_core.py) (**GGUF**, **`complete`**, **[`qwen25_chat_prompt`](../src/voice_agents/agent/agent_core.py)**).
- **[`voice_agents.agent.prompt_engine`](../src/voice_agents/agent/prompt_engine.py)**  -  [`PromptEngine`](../src/voice_agents/agent/prompt_engine.py) (**system prompt**, **memory lines**, **`build_user_message`**).
- **Tools + LLM**  -  A reference **model → tool JSON → `ToolRegistry.call`** path (same **`AgentCore`** / **`PromptEngine`** stack) lives in [chapter 07 `llm_tool_loop`](../07_tools/llm_tool_loop/llm_tool_loop.py); this chapter stays text-first so you can debug prompts before adding **`schema_list()`** noise.

Chapter scripts are thin **demos**; production voice code imports the same modules from **`src/voice_agents`**.

---

## Previous

[Chapter 03 - Text to speech](../03_text_to_speech/README.md)  -  Kokoro TTS and RTF.

---

## Next

[Chapter 05 - Full voice loop](../05_full_voice_loop/README.md)  -  STT + LLM + TTS end-to-end.

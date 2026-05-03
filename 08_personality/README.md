# Chapter 08 - Personality

**Why layer personality on prompts?** The same weights can sound **stiff**, **verbose**, or **cold** depending only on **system text** and **how** you chunk output for TTS. Most product “personalities” are not secret fine-tunes - they are **modifiers** (style tags, tone hints, pacing) applied **before** the LLM and **after** it. This chapter keeps those layers **small and inspectable** so you can compose them with [chapter 04](../04_agent_core/README.md) and [chapter 03](../03_text_to_speech/README.md) without hiding logic in the model.

**Why keyword tone hints?** Real **sentiment** belongs to a classifier or a dedicated pass; [`emotional_responses`](./emotional_responses/emotional_responses.py) shows the **contract**: map user text → short **instruction** string → append to **`PromptEngine.system_prompt`**. Swap the toy **`hint_from_text`** for something production-grade when you are ready.

**Why chunk text for TTS?** Streaming playback and **natural pauses** need **clause boundaries**. [`pacing_and_pauses`](./pacing_and_pauses/pacing_and_pauses.py) splits on sentence-ending punctuation and respects a **`max_chars`** budget so Kokoro (or similar) gets human-sized segments.

**Why `personality.json`?** Named **style tags** in JSON are easy to edit without touching Python; [`voice_style_engine`](./voice_style_engine/voice_style_engine.py) uses an in-code **`STYLES`** map - you can wire **`personality.json`** into your own loader as the next step. **[Unlike chapter 06](../06_real_time_systems/README.md)** (raw stack, no library), **these scripts import [`voice_agents`](../src/voice_agents/)** on purpose: the lesson is **`PromptEngine`** as the shared hook for persona text.

**Previous:** [Chapter 07 - Tools](../07_tools/README.md).

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
| **Dependencies** | `uv sync`. **`--llm`** on **`emotional_responses`** or **`voice_style_engine`** needs the **Qwen GGUF** under **`models/llm/`** (see [chapter 00](../00_start_here/README.md)). **`pacing_and_pauses`**: **`re`** only. |
| **Done looks like** | **`voice_style_engine`**: baseline + each **`STYLES`** tag; optional LLM A/B. **`emotional_responses`**: explained keyword → **SYSTEM** path; optional **`--llm`** reply. **TTS chunks**; **`personality.json`** stub. |

---

## Prerequisites

1. **Environment**  -  From the repository root: `uv sync` so the **`voice_agents`** package resolves.
2. **Prompt layer**  -  Optional read: [`src/voice_agents/agent/prompt_engine.py`](../src/voice_agents/agent/prompt_engine.py) for **`system_prompt`**, **`memory_lines`**, and **`build_user_message`**.
3. **Voice stack context**  -  [Chapter 03](../03_text_to_speech/README.md) for Kokoro profiles; [chapter 07](../07_tools/README.md) for keeping **named behaviour** in registries and config.
4. **`--llm` on this chapter**  -  **`emotional_responses`** and **`voice_style_engine`** use the same Qwen checkpoint as [chapter 04](../04_agent_core/README.md): run [`00_start_here/download_models.py`](../00_start_here/download_models.py) if **`models/llm/`** is empty.

---

## Suggested order

| Order | Script | Purpose |
|------:|--------|---------|
| 1 | [`voice_style_engine/voice_style_engine.py`](./voice_style_engine/voice_style_engine.py) | Baseline + every **`STYLES`** tag; **`--llm`** (compact A/B + **`MODEL OUTPUT`**); **`--show-style-grid`** prints full grid before LLM. |
| 2 | [`emotional_responses/emotional_responses.py`](./emotional_responses/emotional_responses.py) | Explained pipeline + **`--llm`** sample reply (keyword → **SYSTEM** → model). |
| 3 | [`pacing_and_pauses/pacing_and_pauses.py`](./pacing_and_pauses/pacing_and_pauses.py) | Explained **`chunks_for_tts`**: same demo with **`max_chars`** 120 vs 45. |

---

## What each example does

From the **repository root** (after `uv sync`).

### `voice_style_engine/voice_style_engine.py`

**Source:** [`voice_style_engine.py`](./voice_style_engine/voice_style_engine.py)  -  **Learning deeper:** [`voice_style_engine/CODE.md`](./voice_style_engine/CODE.md)

Without **`--llm`:** baseline plus **each** key in **`STYLES`** (**`kind`**, **`concise`**, **`teacher`**), same **USER** every time. With **`--llm`:** a short **[A]/[B]** system reminder, then two completions with **`MODEL OUTPUT [A]`** / **`[B]`** headers. **`--show-style-grid`** with **`--llm`** prints that **full** baseline + all tags grid again before the model so every example system prompt is on screen before **[A]/[B]**.

```bash
uv run python 08_personality/voice_style_engine/voice_style_engine.py
uv run python 08_personality/voice_style_engine/voice_style_engine.py --llm
uv run python 08_personality/voice_style_engine/voice_style_engine.py --llm --show-style-grid
uv run python 08_personality/voice_style_engine/voice_style_engine.py --llm --base-system "You are a patient tutor."
```

---

### `emotional_responses/emotional_responses.py`

**Source:** [`emotional_responses.py`](./emotional_responses/emotional_responses.py)  -  **Learning deeper:** [`emotional_responses/CODE.md`](./emotional_responses/CODE.md)

Prints what each piece is for (sample **USER**, keyword **hint**, merged **SYSTEM**). **`--llm`** runs one **`AgentCore`** completion with that **`PromptEngine`** so you see tone in the assistant text. **`--user "..."`** tries another line (e.g. positive keywords).

```bash
uv run python 08_personality/emotional_responses/emotional_responses.py
uv run python 08_personality/emotional_responses/emotional_responses.py --llm
```

---

### `pacing_and_pauses/pacing_and_pauses.py`

**Source:** [`pacing_and_pauses.py`](./pacing_and_pauses/pacing_and_pauses.py)  -  **Learning deeper:** [`pacing_and_pauses/CODE.md`](./pacing_and_pauses/CODE.md)

Explains sentence-split + **`max_chars`** merge, then shows the same demo paragraph with **`max_chars=120`** (often one chunk) and **`max_chars=45`** (several chunks). Each printed line is one TTS “utterance” with a natural pause before the next.

```bash
uv run python 08_personality/pacing_and_pauses/pacing_and_pauses.py
```

---

### `personality.json`

Starter JSON (**`name`**, **`style_tags`**, **`notes`**) at [`personality.json`](./personality.json). No chapter script loads it yet - copy the pattern into your agent bootstrap when you want file-driven personas.

---

## Troubleshooting

- **`ModuleNotFoundError: voice_agents`**  -  Run from repo root with **`uv run python ...`** so the editable install is on **`sys.path`**.
- **Chunks feel too long or short**  -  Tune **`max_chars`** in **`chunks_for_tts`**; consider language-specific sentence rules for production.
- **Tone hints misfire**  -  The keyword lists are intentional toys; replace **`hint_from_text`** with a classifier or LLM summary when behaviour matters.
- **`emotional_responses` / `voice_style_engine --llm` exits with “No GGUF”**  -  Run [`00_start_here/download_models.py`](../00_start_here/download_models.py). **`--llm`** answers can look similar on a **0.5B** model; lower **`temperature`** in code or try a larger instruct model if you need crisper separation.

---

## How this ties to the library

- **[`PromptEngine`](../src/voice_agents/agent/prompt_engine.py)**  -  Holds **`system_prompt`** and optional **`memory_lines`**; **`build_user_message`** is where you inject retrieved context (see [chapter 04](../04_agent_core/README.md)).
- **[`personality.json`](./personality.json)**  -  Illustrates **config-driven tags** alongside **`STYLES`** in code; merge both in a real **`AgentCore`** wrapper.
- **TTS**  -  Use **`chunks_for_tts`** output as the queue you feed to streaming or sequential playback in **`voice_agents.audio`** or your chapter 05/06 loops.

---

## Previous

[Chapter 07 - Tools](../07_tools/README.md)

---

## Next

[Chapter 09 - Projects](../09_projects/README.md)

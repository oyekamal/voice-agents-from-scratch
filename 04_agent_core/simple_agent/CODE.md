# `simple_agent.py`  -  code walkthrough

## Purpose

### What this script is

This is the **smallest “agent brain” demo** in the course: you send **one question as text**, the **local LLM** produces **one answer**, and the program prints it **once** and exits. There is **no microphone, no speech recognition, no text-to-speech**  -  only the middle step people often call the **“agent”** or **“LLM step”**: *given instructions + user words → model → assistant reply*.

If you are new to agents, think of it as three layers:

1. **Instructions** (“who you are / how to behave”)  -  here handled by [`PromptEngine`](../../src/voice_agents/agent/prompt_engine.py) (default system prompt).
2. **User message**  -  your CLI words, or a built-in demo question if you pass nothing.
3. **Model run**  -  [`AgentCore.complete`](../../src/voice_agents/agent/agent_core.py) builds a **Qwen2.5 chat-style** text blob, runs **`llama-cpp-python`** on your downloaded **GGUF** file, and returns the assistant’s continuation as a string.

Later chapters wrap this same idea with audio (chapter 05): **your speech → transcript becomes the user message**, then **this kind of reply → spoken audio**. Running **`simple_agent`** first lets you verify **prompts and answers** without debugging sound hardware.

### What “blocking” means

**Blocking** means: Python calls **`complete(...)`** and **waits** until the model finishes generating text **before** printing. Nothing streams to the screen token-by-token in this script (streaming is a separate pattern). Your terminal may sit quietly for a moment while the CPU runs inference  -  that is normal.

### Why “agent” and [`AgentCore`](../../src/voice_agents/agent/agent_core.py)?

In this repo, **`AgentCore`** is not a separate AI product  -  it is a **thin helper** that knows how to:

- Load one **GGUF** model with **`llama-cpp-python`**.
- Wrap your user text with the **chat template** [`qwen25_chat_prompt`](../../src/voice_agents/agent/agent_core.py) expects for **Qwen2.5 instruct**.
- Call **`complete`** so you get a single string back.

So **`simple_agent.py`** is mostly **“construct [`AgentCore`] + [`PromptEngine`] + call `complete` once”**  -  the pattern every voice script here reuses.

### What [`PromptEngine`](../../src/voice_agents/agent/prompt_engine.py) does here

[`PromptEngine`](../../src/voice_agents/agent/prompt_engine.py) holds:

- A **system prompt** (default: helpful concise assistant  -  see library source).
- Optional **memory lines** (not filled interactively in this script).

Even on this one-shot run, **[`complete`](../../src/voice_agents/agent/agent_core.py)** **records** the exchange into the engine’s memory list **after** generation (user line + assistant line). That matters when you reuse the same **`PromptEngine`** across multiple **`complete`** calls in other demos  -  here it only runs once, so you mainly see the **default instruction behavior**.

---

## Run

```bash
uv run python 04_agent_core/simple_agent/simple_agent.py
uv run python 04_agent_core/simple_agent/simple_agent.py "What is the capital of France?"
```

Optional **CLI words** after the script path become the **user question** (joined with spaces). With **no extra arguments**, the script asks a short built-in test question (`What is 2+2? …`).

---

## Dependencies

| Symbol | Role |
|--------|------|
| [`AgentCore`](../../src/voice_agents/agent/agent_core.py) | Loads the **GGUF** file from **`models/llm/`** via **llama-cpp-python**. **`complete`** builds the prompt with [`qwen25_chat_prompt`](../../src/voice_agents/agent/agent_core.py) and runs inference. |
| [`PromptEngine`](../../src/voice_agents/agent/prompt_engine.py) | Supplies **system** behavior and **`build_user_message`**; [`complete`](../../src/voice_agents/agent/agent_core.py) appends **User:** / **Assistant:** lines to memory after each call. |

---

## Code walkthrough

### Paths

```python
ROOT = Path(__file__).resolve().parents[2]
LLM = ROOT / "models" / "llm" / "qwen2.5-0.5b-instruct-q4_k_m.gguf"
```

**`parents[2]`** is the **repository root** (the script lives under **`simple_agent/`**, one level deeper than old flat layouts).

### Single turn

```python
agent = AgentCore(model_path=str(LLM))
engine = PromptEngine()
out = agent.complete(q, engine=engine, max_tokens=128)
console.print(out)
```

**`max_tokens=128`** caps how long the reply can grow; raise it if answers truncate mid-thought (trade-off: slower run and more RAM use inside context).

---

## Failure modes

Missing GGUF → run [00_start_here/download_models.py](../../00_start_here/download_models.py). **`llama-cpp-python`** install issues → see root [README.md](../../README.md).

---

## Try next

- [`response_loop`](../response_loop/CODE.md)  -  same stack in a **loop** or **stdin pipe** so you can hold a longer text-only session.
- [`memory`](../memory/CODE.md)  -  system prompt tuned for **remembering** what the user said across turns.

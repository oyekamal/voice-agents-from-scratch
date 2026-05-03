# `memory.py`  -  code walkthrough

## Purpose

This script is a **practice chat** in the terminal: you talk to the assistant **several times in a row**, and the model is instructed (via **system prompt**) to **remember facts you tell it**. Under the hood, [`AgentCore.complete`](../../src/voice_agents/agent/agent_core.py) also **appends** each user line and assistant reply to [`PromptEngine`](../../src/voice_agents/agent/prompt_engine.py) **memory**, so later prompts can include **“Context from earlier…”**  -  that is what “memory” means here (in RAM for this run only; nothing is saved to disk).

---

## Run

```bash
uv run python 04_agent_core/memory/memory.py
```

### What to type after **You:**

**You:** is **not** a shell prompt  -  it means **you are playing the user**. Type ordinary English (or your language), like a message to a chatbot:

| Try this | Why |
|----------|-----|
| `My name is Sam.` | Gives the model a fact to remember. |
| `What is my name?` on the next turn | Checks whether earlier context appears in the prompt. |
| `I live in Berlin.` then `Where did I say I live?` | Same idea with a different fact. |

Press **Enter** after each line to send it. The script prints **`Assistant`** and the model’s reply before asking **You:** again.

**To leave:** type **`quit`** or **`exit`** at **You:** and press **Enter** (or **Ctrl+C**).

First reply may be slow while the model loads; later turns are usually quicker.

---

## Dependencies

| Piece | Role |
|-------|------|
| [`Prompt.ask`](https://rich.readthedocs.io/en/stable/prompt.html) | Shows **You:** and reads one line from you. |
| [`AgentCore`](../../src/voice_agents/agent/agent_core.py) / [`PromptEngine`](../../src/voice_agents/agent/prompt_engine.py) | Same stack as [`simple_agent`](../simple_agent/CODE.md). |

---

## Code walkthrough

```python
engine = PromptEngine(system_prompt="You are a concise assistant. Remember facts the user states.")
reply = agent.complete(user, engine=engine, max_tokens=256)
```

When **`memory_lines`** is non-empty, [`build_user_message`](../../src/voice_agents/agent/prompt_engine.py) wraps your next line with **Context from earlier in the conversation** plus past lines.

---

## Failure modes

GGUF missing → [download_models.py](../../00_start_here/download_models.py).

---

## Try next

- [`debug_flow`](../debug_flow/CODE.md) to print the **raw Qwen** prompt tail before [chapter 05](../../05_full_voice_loop/).

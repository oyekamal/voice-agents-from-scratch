# `response_loop.py`  -  code walkthrough

## Purpose

This script lets you **chat with the local LLM in your terminal**  -  several turns in a row  -  **without** building a voice pipeline yet. Each time you send one line of text, the model sends back one block of text (same **`AgentCore.complete`** path as [`simple_agent`](../simple_agent/CODE.md)).

There is **no memory-focused tutorial** in this file (unlike [`memory`](../memory/CODE.md)); the library still **stores** each user/assistant pair inside [`PromptEngine`](../../src/voice_agents/agent/prompt_engine.py) after each call, but you do not edit prompts here  -  you only practice **typing → answer → typing again**.

---

## Run (two ways)

### A  -  Interactive terminal (what most learners use)

From the repo root:

```bash
uv run python 04_agent_core/response_loop/response_loop.py
```

**What you should see:**

1. A short gray explanation line (how `>` works and how to quit).
2. A prompt **`>`** with a **blinking cursor**. That is where you type.

**What you do:**

1. Type a question (for example: `What is 2+2?`) and press **Enter**.
2. Wait  -  the model may pause a few seconds while it thinks on CPU.
3. Your answer appears **as plain text** below (no special formatting).
4. Repeat: another **`>`** appears  -  ask another question.
5. **To quit:** press **Enter** when **`>`** is showing **and you have typed nothing** on that line. That sends an **empty line** and exits the loop. You can also press **Ctrl+C** or **Ctrl+D** (EOF).

If nothing happens after `>` except a blank feel  -  you might still be loading the model on first question; wait for the first reply.

### B  -  One question from a pipe (no typing)

If stdin is **not** a TTY (for example you **pipe** text in), the script reads **one blob of text**, runs **`complete` once**, prints the answer, and exits:

```bash
echo "Hello in one sentence." | uv run python 04_agent_core/response_loop/response_loop.py
```

Use this when you want a quick check from a script or CI without an interactive session.

---

## Dependencies

Same stack as [`simple_agent`](../simple_agent/CODE.md): [`AgentCore`](../../src/voice_agents/agent/agent_core.py), [`PromptEngine`](../../src/voice_agents/agent/prompt_engine.py), and the GGUF under **`models/llm/`**.

---

## Code walkthrough

**Pipe vs keyboard:** if **`stdin` is not a terminal**, read all stdin once and return; otherwise show instructions and loop with **`input("> ")`**.

```python
if not sys.stdin.isatty():
    text = sys.stdin.read().strip()
    print(agent.complete(text, engine=engine))
    return
# Interactive: loop until empty line or Ctrl+C / Ctrl+D
while True:
    line = input("> ").strip()
    if not line:
        break
    print(agent.complete(line, engine=engine))
```

---

## Failure modes

Missing GGUF → run [00_start_here/download_models.py](../../00_start_here/download_models.py) (same as [`simple_agent/CODE.md`](../simple_agent/CODE.md)).

---

## Try next

- [`memory`](../memory/CODE.md)  -  same idea, but with Rich prompts and a system prompt aimed at **remembering** facts across turns.

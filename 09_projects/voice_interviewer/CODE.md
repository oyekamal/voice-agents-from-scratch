# Voice interviewer (memory across turns)

One shared [`PromptEngine`](../../src/voice_agents/agent/prompt_engine.py) instance is passed to every [`AgentCore.complete`](../../src/voice_agents/agent/agent_core.py) call. **`complete`** appends **`User:`** / **`Assistant:`** lines to **`engine.memory_lines`**; the next turn’s user message is wrapped by **`build_user_message`** with a **“Context from earlier in the conversation”** block - no separate history list in this script.

This is the same **memory mechanism** as [`04_agent_core/memory/memory.py`](../../04_agent_core/memory/memory.py), but with a **hiring-manager** system prompt and Rich **`Prompt.ask("Candidate")`**.

---

## Runnable

```bash
uv run python 09_projects/voice_interviewer/voice_interviewer.py
```

Answer after **`Candidate`**. **Empty line**, **`quit`**, or **`exit`** stops the loop. At exit the script prints how many **`memory_lines`** accumulated.

---

## Code walkthrough (`voice_interviewer.py`)

### 1. One engine for the whole session

```python
engine = PromptEngine(
    system_prompt=(
        "You are a hiring manager running a behavioral interview. "
        "Ask one focused follow-up at a time. Use earlier turns to dig deeper, "
        "not to repeat questions."
    )
)
```

**Takeaway:** if you create a **new** `PromptEngine` each turn, memory resets - here we deliberately reuse **one** object.

---

### 2. What `AgentCore` stores

After each `complete`, see [`agent_core.py`](../../src/voice_agents/agent/agent_core.py): **`add_memory`** records both sides of the turn. The instruct model’s **user** slot gets **`build_user_message(latest_line)`**, so earlier turns appear as **context**, not as separate chat messages in the Qwen template.

---

### 3. Adding spoken input/output

This chapter stays **text-only** so the memory idea stays visible. To layer audio, reuse the **record → transcribe** and **TTS** pieces from [`05_full_voice_loop/streaming_voice_agent`](../../05_full_voice_loop/streaming_voice_agent/streaming_voice_agent.py): replace **`Prompt.ask`** with STT text and print with optional Kokoro playback.

---

### 4. Next steps

- **Explicit rubrics or scoring JSON** are a fine exercise - this repo stops at **plain text** personas (no production evaluation pipeline).

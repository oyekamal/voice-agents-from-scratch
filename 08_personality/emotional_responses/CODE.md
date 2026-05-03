# Emotional tone hints (keyword toy)

Real **sentiment** needs a classifier or LLM pass; this script shows the **shape** of the idea: read the user string, map coarse **keywords** to a short **instruction** you append to the system prompt so the main model steers tone.

It uses [`PromptEngine`](../../src/voice_agents/agent/prompt_engine.py) from the library so the same object you use in [chapter 04](../../04_agent_core/README.md) picks up **`system_prompt`** changes before you ever call an LLM.

---

## Runnable

Default run prints a short **what/why** (STT → keywords → hint → **SYSTEM**), then the full **`system_prompt`**. Add **`--llm`** for one **Qwen** completion with that engine (same GGUF as [chapter 04](../../04_agent_core/README.md)).

```bash
uv run python 08_personality/emotional_responses/emotional_responses.py
uv run python 08_personality/emotional_responses/emotional_responses.py --llm
uv run python 08_personality/emotional_responses/emotional_responses.py --user "Thanks, that helped!"
```

---

## Code walkthrough (`emotional_responses.py`)

### 1. Normalize once, then scan with `any`

The user line is lowercased a single time. Each branch checks whether **any** trigger substring appears in that string - simple and fast, but coarse (false positives if a word appears in another context).

```python
def hint_from_text(user: str) -> str:
    low = user.lower()
    if any(w in low for w in ("sad", "sorry", "worried")):
        return "Respond with empathy and reassurance."
    if any(w in low for w in ("great", "awesome", "thanks")):
        return "Match the user's positive energy briefly."
    return "Stay neutral and helpful."
```

**Takeaway:** order matters - first matching branch wins. In production you would replace this with scores, intents, or a small classifier; here the goal is a clear **string → hint** pipeline.

---

### 2. Glue the hint into `PromptEngine.system_prompt`

The demo stacks a **fixed persona** (“supportive colleague”) and the **dynamic hint** as two paragraphs in one `system_prompt` string. That is exactly what a voice loop would rebuild each turn after STT.

```python
engine = PromptEngine(
    system_prompt=(
        "You are a supportive colleague.\n\n" + hint_from_text(user)
    ).strip()
)
```

**Takeaway:** `PromptEngine` does not interpret the hint - it only stores text. The LLM does the emotional work; your code only **selects** which instruction block to attach.

---

### 3. CLI: explanation, then optional **`--llm`**

**`_print_explanation`** shows the sample **USER** line, the **hint** line alone, then the merged **SYSTEM** so the pipeline is obvious. **`_run_llm`** loads **`AgentCore`** only when asked, prints a **`MODEL OUTPUT`** banner, then **`complete(user, engine=engine, ...)`**.

---

### 4. Where this sits in a full agent

After speech-to-text you have `user_text: str`. A real loop would do:

```python
hint = hint_from_text(user_text)
engine = PromptEngine(
    system_prompt=f"You are a supportive colleague.\n\n{hint}"
)
# then: agent.complete(user_text, engine=engine, ...)
```

**Takeaway:** personality here is **deterministic string surgery** on prompts, not a second model.

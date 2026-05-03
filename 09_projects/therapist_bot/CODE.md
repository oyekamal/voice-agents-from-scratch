# Therapist bot sketch (dynamic persona per turn)

**Not therapy.** This REPL demonstrates **two ideas** together:

1. **Toy tone routing**  -  `hint_from_text` is copied verbatim from [`08_personality/emotional_responses/emotional_responses.py`](../../08_personality/emotional_responses/emotional_responses.py) (keyword → short instruction). Real sentiment needs a classifier or a second model pass; here the shape of the pipeline is the lesson.

2. **Mutable `system_prompt`**  -  before each `complete`, the script sets `engine.system_prompt = BASE_PERSONA + "\n\n" + hint`. The same **`PromptEngine`** instance still keeps **`memory_lines`** from earlier turns, so the listener **remembers** prior user/assistant lines while the **persona line** changes.

---

## Runnable

```bash
uv run python 09_projects/therapist_bot/therapist_bot.py
```

Type after **`You`**. **Empty line**, **`quit`**, or **`exit`** stops. Each turn prints **`(hint -> …)`** so you see which branch fired.

---

## Code walkthrough (`therapist_bot.py`)

### 1. `hint_from_text` (toy)

```python
def hint_from_text(user: str) -> str:
    low = user.lower()
    if any(w in low for w in ("sad", "sorry", "worried")):
        return "Respond with empathy and reassurance."
    if any(w in low for w in ("great", "awesome", "thanks")):
        return "Match the user's positive energy briefly."
    return "Stay neutral and helpful."
```

**Takeaway:** string surgery on **system** text is deterministic and cheap; swap this function when you outgrow keywords.

---

### 2. Merge base persona + hint every turn

```python
hint = hint_from_text(user)
engine.system_prompt = f"{BASE_PERSONA}\n\n{hint}"
```

**Takeaway:** chapter 08’s standalone demo prints the merged **SYSTEM** block; this script **runs** it every turn.

---

### 3. Memory + dynamic persona

[`AgentCore.complete`](../../src/voice_agents/agent/agent_core.py) still appends to **`memory_lines`** after each reply. Mutating **`system_prompt`** does not clear **`memory_lines`** - same dataclass instance.

---

### 4. Next steps

- Full walkthrough of the keyword demo: [`emotional_responses/CODE.md`](../../08_personality/emotional_responses/CODE.md).
- **Crisis handling** in real products is out of scope here; this repo only shows **prompt + memory** mechanics.

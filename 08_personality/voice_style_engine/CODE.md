# Voice style tags → prompt suffixes

**Style** is stored as named **tags** (`kind`, `concise`, `teacher`) mapped to short **rules** appended to the system prompt. That matches how many products implement “personas” without fine-tuning: one base instruction plus a **modifier block**.

Optional **[`personality.json`](../personality.json)** in the chapter root is a **JSON starter** (name, tags, notes) - load it in your own code and map **`style_tags`** into calls to **`engine_with_style`** or a richer loader.

---

## Runnable

**Default:** one **baseline** SYSTEM block, then one block per key in **`STYLES`** (**`kind`**, **`concise`**, **`teacher`**). **USER** is always **`What is asyncio?`** each time.

**`--llm`:** short **[A]/[B] SYSTEM** reminder, then two completions with **`# MODEL OUTPUT [A]`** / **`# MODEL OUTPUT [B]`** banners. **`--show-style-grid`** with **`--llm`** prints that same full grid (baseline + every tag) before loading the model so every example system prompt appears before the A/B run.

```bash
uv run python 08_personality/voice_style_engine/voice_style_engine.py
uv run python 08_personality/voice_style_engine/voice_style_engine.py --llm
uv run python 08_personality/voice_style_engine/voice_style_engine.py --llm --show-style-grid
```

---

## Code walkthrough (`voice_style_engine.py`)

### 1. `STYLES`: tag → extra system text

Keys are stable identifiers (from UI, config, or **`personality.json`**). Values are plain English instructions the instruct model should follow.

```python
STYLES: dict[str, str] = {
    "kind": "Be warm and encouraging.",
    "concise": "Use at most two short sentences.",
    "teacher": "Explain briefly, then give one concrete example.",
}
```

**Takeaway:** this is the same “name → behaviour” idea as tool names in [chapter 07](../../07_tools/README.md), except the payload is **prompt prose**, not a Python function.

---

### 2. `engine_with_style`: merge base + suffix

**`STYLES.get(style, "")`** returns **`""`** for unknown tags, so you do not crash on typos - you simply get the base system string only. **`strip()`** removes stray blank lines if **`extra`** is empty.

```python
def engine_with_style(base_system: str, style: str) -> PromptEngine:
    extra = STYLES.get(style, "")
    return PromptEngine(system_prompt=f"{base_system}\n\n{extra}".strip())
```

**Takeaway:** every style is a **new `PromptEngine` instance** with a different **`system_prompt`**; the user message string can stay identical across runs.

---

### 3. Repo-relative model path (for `--llm`)

The script lives at **`08_personality/voice_style_engine/voice_style_engine.py`**. **`parents[2]`** walks up to the **repository root** so the default GGUF path matches [`simple_agent` in chapter 04](../../04_agent_core/simple_agent/simple_agent.py).

```python
_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_GGUF = _REPO_ROOT / "models" / "llm" / "qwen2.5-0.5b-instruct-q4_k_m.gguf"
```

**Takeaway:** keep path math next to **`__file__`** so `uv run python …/voice_style_engine.py` works from any cwd.

---

### 4. `_run_llm_compare`: same user, two engines

Two fresh **`PromptEngine`** instances share the same **`user`** string. **`AgentCore.complete`** builds the Qwen chat template from each engine’s **`system_prompt`** (see [`agent_core.py`](../../src/voice_agents/agent/agent_core.py) **`qwen25_chat_prompt`**). Lower **`temperature`** makes A/B answers easier to compare on a tiny model.

```python
agent = AgentCore(model_path=str(model_path))
plain = PromptEngine(system_prompt=base_system)
concise = engine_with_style(base_system, "concise")
out_plain = agent.complete(user, engine=plain, max_tokens=140, temperature=0.35)
out_concise = agent.complete(user, engine=concise, max_tokens=140, temperature=0.35)
```

**Takeaway:** the only variable between the two calls is **`system_prompt`**; that is what **`--llm`** is meant to prove.

---

### 5. `main`: CLI branches

**`_print_prompt_demo`** always walks **`STYLES`** so **`kind`** is not skipped - baseline first, then **`for tag in STYLES`**. With **`--llm`** and no **`--show-style-grid`**, only **`_print_llm_preamble_compact`** runs before **`_run_llm_compare`**.

```python
if args.llm:
    if args.show_style_grid:
        _print_prompt_demo(base_system=base)
    else:
        _print_llm_preamble_compact(base_system=base)
    _run_llm_compare(model_path=args.model, base_system=base)
else:
    _print_prompt_demo(base_system=base)
```

**Takeaway:** the grid is the single source of truth for “every **`STYLES`** tag”; **`--show-style-grid`** exists so **`--llm`** runs can show that full list immediately before the two model outputs.

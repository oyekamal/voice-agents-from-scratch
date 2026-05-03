# CLI assistant (tools REPL  -  chapter 07 pattern)

Each **`>`** line runs **two** LLM steps, matching [`07_tools/llm_tool_loop/llm_tool_loop.py`](../../07_tools/llm_tool_loop/llm_tool_loop.py):

1. **Router**  -  strict **JSON** with **`name`** and **`arguments`** (schemas injected into **`PromptEngine.system_prompt`**).
2. **`ToolRegistry.call`**  -  Pydantic-validated dispatch via [`chapter_registry.build_registry()`](../../07_tools/chapter_registry.py) (**`calc`**, **`time`**, **`weather`**, **`search`**).
3. **Summarizer**  -  second **`PromptEngine`** turns raw tool output into a short user-facing answer.

**Why duplicate helpers here?** Same **`_extract_json_object`** / **`_coerce_tool_arguments`** as **`llm_tool_loop`** so this file stays runnable and readable in isolation; see chapter 07 for the detailed commentary on coercion.

---

## Runnable

```bash
uv run python 09_projects/cli_assistant/cli_assistant.py
```

If the tiny model struggles with a large schema:

```bash
uv run python 09_projects/cli_assistant/cli_assistant.py --calc-only
```

**Empty line**, **`quit`**, or **`exit`** leaves the loop. **Network** may be needed for **`weather`** / **`search`**.

---

## Code walkthrough (`cli_assistant.py`)

### 1. Import `chapter_registry` from `07_tools/`

```python
_CH07 = ROOT / "07_tools"
if str(_CH07) not in sys.path:
    sys.path.insert(0, str(_CH07))
from chapter_registry import build_registry
```

**Takeaway:** same **`sys.path`** trick as [`tool_router`](../../07_tools/tool_router/tool_router.py) / **`llm_tool_loop`** so subfolder modules resolve.

---

### 2. Two engines, one `AgentCore`

- **`router_engine`**  -  long system text + embedded JSON Schemas.
- **`summary_engine`**  -  short “summarize tool output” rules.

Both **`memory_lines`** lists are **cleared** before each respective **`complete`** so one REPL turn does not leak prior router JSON into the next route (or prior summaries into the next summary).

---

### 3. Parse → coerce → call

**`_extract_json_object`** strips accidental markdown fences; **`_coerce_tool_arguments`** fixes common small-model nesting before **`reg.call`**.

---

### 4. Next steps

- Single-shot reference with printed stages: [`llm_tool_loop`](../../07_tools/llm_tool_loop/llm_tool_loop.py).
- **Registry source:** [`ToolRegistry`](../../src/voice_agents/tools/registry.py), [`chapter_registry.py`](../../07_tools/chapter_registry.py).

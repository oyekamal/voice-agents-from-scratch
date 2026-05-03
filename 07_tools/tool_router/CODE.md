# Tool router (registry + demos)

**[`ToolRegistry`](../../src/voice_agents/tools/registry.py)** is the small library type that ties three things together per tool: a **string name**, a **Pydantic model** (for arguments + JSON Schema), and a **Python callable**. This script prints what an LLM would see as **tool definitions** and runs a few **`reg.call`** invocations with plain dicts.

Tool implementations are registered in [`chapter_registry.py`](../chapter_registry.py) (**`build_registry`**) so **`llm_tool_loop`** and **`tool_router`** stay in sync.

---

## Runnable

Run **[`tool_router.py`](./tool_router.py)** from the repository root. **Weather** needs network access; **calc** and **time** do not.

```bash
uv run python 07_tools/tool_router/tool_router.py
```

---

## Code walkthrough (`tool_router.py`)

### 1. Chapter root on `sys.path`

**`Path(__file__).resolve().parent.parent`** is **`07_tools/`** so **`chapter_registry`** (and its **`calculator_tool`** imports) resolve when the script lives under **`tool_router/`**.

```python
_CH07 = Path(__file__).resolve().parent.parent
if str(_CH07) not in sys.path:
    sys.path.insert(0, str(_CH07))
```

---

### 2. Import shared `build_registry`

```python
from chapter_registry import build_registry
```

**Takeaway:** avoid duplicating **`r.register(...)`** in every script that needs the same demo tools.

---

### 3. `main`: schema dump + dict-based `call`

**`schema_list()`** returns one object per tool with **`name`** and **`parameters`**. The **`demo`** tuples show **`reg.call(name, dict)`** coercing dicts through **`model_validate`**.

```python
def main() -> None:
    console = Console()
    reg = build_registry()
    console.print("[bold]Registered tools:[/]")
    pprint(reg.schema_list())

    demo = [
        ("weather", {"town": "Berlin"}),
        ("calc", {"expression": "21 * 2"}),
        ("time", {"fmt": "%H:%M"}),
    ]
    for name, args in demo:
        out = reg.call(name, args)
        console.print(f"[green]{name}[/] => {out}")
```

**Takeaway:** the same **`dict`** shape is what you build after parsing a model’s tool JSON in [`llm_tool_loop`](../llm_tool_loop/CODE.md).

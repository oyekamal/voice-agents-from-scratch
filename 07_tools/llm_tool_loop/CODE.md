# LLM tool loop (reference bridge)

This script loads the same **Qwen** stack as [chapter 04](../../04_agent_core/README.md), injects **`schema_list()`** into the router system prompt, parses **one JSON object** with **`name`** and **`arguments`**, runs **`ToolRegistry.call`**, then runs a **second** **`AgentCore.complete`** to produce a user-facing sentence.

**Default** uses the full [`chapter_registry`](../chapter_registry.py). The **model** chooses the tool; **`_coerce_tool_arguments`** only repairs **argument shape** (nested fields, wrong keys) - not which tool was picked.

---

## Runnable

Requires **`models/llm/qwen2.5-0.5b-instruct-q4_k_m.gguf`** (see [chapter 00](../../00_start_here/README.md)).

```bash
uv run python 07_tools/llm_tool_loop/llm_tool_loop.py
uv run python 07_tools/llm_tool_loop/llm_tool_loop.py "What is a voice agent?"
uv run python 07_tools/llm_tool_loop/llm_tool_loop.py --calc-only "What is 15 times 4?"
```

---

## Code walkthrough (`llm_tool_loop.py`)

### 1. Chapter root on `sys.path` and GGUF path

The script lives under **`07_tools/llm_tool_loop/`**; **`parent.parent`** is **`07_tools/`**. Inserting it on **`sys.path`** lets **`from chapter_registry import build_registry`** and the per-tool packages resolve. **`REPO`** is the git root so **`LLM`** points at the same GGUF path as chapter 04.

```python
_CH07 = Path(__file__).resolve().parent.parent
if str(_CH07) not in sys.path:
    sys.path.insert(0, str(_CH07))

REPO = _CH07.parent
LLM = REPO / "models" / "llm" / "qwen2.5-0.5b-instruct-q4_k_m.gguf"
```

**Takeaway:** run from the repo root with **`uv run python 07_tools/llm_tool_loop/llm_tool_loop.py`** so relative model paths stay consistent.

---

### 2. Registry: full chapter vs `--calc-only`

**`build_registry()`** pulls every demo tool from [`chapter_registry.py`](../chapter_registry.py). **`--calc-only`** swaps in a one-tool registry so the JSON schema block is tiny (easier for very small models, harder to pick **`weather`** by accident).

```python
reg = _calc_only_registry() if args.calc_only else build_registry()
schema_block = json.dumps(reg.schema_list(), indent=2)
system = _tool_router_system_prompt(schema_block, calc_only=args.calc_only)
router_engine = PromptEngine(system_prompt=system)
```

**Takeaway:** the **same** **`PromptEngine`** pattern as chapter 04 - only **`system_prompt`** is swapped for the router role.

---

### 3. Router system prompt + first `complete`

**`_tool_router_system_prompt`** concatenates fixed instructions, optional routing hints (when not **`calc_only`**), and the **pretty-printed** **`schema_list()`** JSON. **`AgentCore.complete`** uses low **temperature** to reduce rambling; output is still **free text** (no **`grammar=`** on **`Llama`**).

```python
def _tool_router_system_prompt(schema_block: str, *, calc_only: bool) -> str:
    base = (
        "You are a strict tool router. The user will ask a question.\n"
        "You must respond with exactly ONE JSON object and nothing else - no markdown fences, "
        "no code blocks, no explanation before or after.\n"
        "The JSON object must have two keys: \"name\" (string) and \"arguments\" (object).\n"
        "Put ONLY the parameter keys required by that tool - no extra keys. "
        'For tool \"calc\", arguments must be a flat object like {\"expression\":\"21*2\"}  -  '
        "the value of \"expression\" must be a string, never an object.\n"
    )
    if not calc_only:
        base += (
            "\nRouting (pick the best tool from the schemas below):\n"
            "- **search** – ALL general knowledge questions (people, geography, capitals, definitions, "
            "history, GDP, etc.). Default tool unless the query clearly matches another tool.\n"
            "- **weather** – ONLY if the user explicitly asks about temperature, forecast, climate, "
            "or conditions (e.g., weather, temperature, rain, forecast). DO NOT use for general "
            "place questions.\n"
            "- **time** - current local time / formatted clock string.\n"
            "- **calc** - pure arithmetic expressions only.\n"
            "- If unsure, ALWAYS use **search**. \n"
        )
    base += "\nAvailable tools (JSON Schema list):\n" + schema_block + "\n"
    return base
```

```python
    raw = agent.complete(
        user_task,
        engine=router_engine,
        max_tokens=256,
        temperature=0.05,
    )
```

**Takeaway:** stricter tool JSON usually needs **`grammar`** or a tool-calling API; here the contract is **prompt-only**.

---

### 4. Parse JSON: fences and brace fallback

**`_extract_json_object`** strips leading **\`\`\`json** fences, then **`json.loads`**. If that fails, it slices from the **first `{`** to the **last `}`** so a model that adds a preamble can still recover an object.

```python
def _extract_json_object(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```\s*$", "", text)
        text = text.strip()
    try:
        out = json.loads(text)
    except json.JSONDecodeError:
        i = text.find("{")
        j = text.rfind("}")
        if i < 0 or j <= i:
            raise
        out = json.loads(text[i : j + 1])
    if not isinstance(out, dict):
        raise ValueError("tool call JSON must be an object")
    return out
```

**Takeaway:** this is a **tutorial** parser - production code would validate **`name`** against an allow-list before **`reg.call`**.

---

### 5. `_coerce_tool_arguments` and `_unwrap_string_field`

Small models nest **`{"expression": {"expression": "2+2"}}`** or send **`query`** on **`weather`**. **`_unwrap_string_field`** walks a few dict levels; per-tool branches return a clean **`dict`** for **`model_validate`**.

```python
def _unwrap_string_field(value: Any, *, inner_keys: tuple[str, ...]) -> str | None:
    """If the model nested {\"expression\": {\"expression\": \"2+2\"}}, peel to a string."""
    cur: Any = value
    for _ in range(4):
        if isinstance(cur, str):
            return cur
        if isinstance(cur, (int, float)):
            return str(cur)
        if not isinstance(cur, dict):
            return None
        for k in inner_keys:
            if k in cur:
                cur = cur[k]
                break
        else:
            if len(cur) == 1:
                cur = next(iter(cur.values()))
            else:
                return None
    return None
```

```python
def _coerce_tool_arguments(name: str, arguments: Any) -> dict[str, Any]:
    """Best-effort repair before Pydantic (small models nest fields or use wrong keys)."""
    if not isinstance(arguments, dict):
        raise TypeError(f'"arguments" must be a JSON object, got {type(arguments).__name__}')

    if name == "calc":
        ex = arguments.get("expression")
        flat = _unwrap_string_field(ex, inner_keys=("expression",))
        if flat is None:
            raise ValueError(f'Could not coerce calc "expression" to a string from {ex!r}')
        return {"expression": flat}

    if name == "time":
        fmt = arguments.get("fmt", "%Y-%m-%d %H:%M:%S")
        flat = _unwrap_string_field(fmt, inner_keys=("fmt",))
        if flat is not None:
            return {"fmt": flat}
        if isinstance(fmt, str):
            return {"fmt": fmt}
        raise ValueError(f'Could not coerce time "fmt" from {fmt!r}')

    if name == "search":
        q = arguments.get("query")
        if q is None and arguments.get("q") is not None:
            q = arguments["q"]
        if q is None and arguments.get("town") is not None:
            q = arguments["town"]
        flat = _unwrap_string_field(q, inner_keys=("query", "q")) if q is not None else None
        if flat is None and isinstance(q, str):
            flat = q.strip()
        if flat is None:
            raise ValueError(f'Could not coerce search "query" from {arguments!r}')
        return {"query": flat}

    if name == "weather":
        out: dict[str, Any] = {}
        for k in ("town", "latitude", "longitude"):
            if k in arguments and arguments[k] is not None:
                out[k] = arguments[k]
        has_coords = out.get("latitude") is not None and out.get("longitude") is not None
        town_empty = not (out.get("town") and str(out["town"]).strip())
        if town_empty and not has_coords:
            for alt in ("query", "q", "location", "place"):
                if arguments.get(alt) is None:
                    continue
                v = arguments[alt]
                if isinstance(v, str) and v.strip():
                    out["town"] = v.strip()
                    break
                flat = _unwrap_string_field(v, inner_keys=(alt, "town", "query"))
                if flat and flat.strip():
                    out["town"] = flat.strip()
                    break
        if out.get("town") is not None:
            flat = _unwrap_string_field(out["town"], inner_keys=("town",))
            if flat is not None:
                out["town"] = flat.strip()
        for key in ("latitude", "longitude"):
            if key not in out:
                continue
            v = out[key]
            if isinstance(v, str) and v.strip():
                try:
                    out[key] = float(v)
                except ValueError:
                    del out[key]
        return out

    return dict(arguments)
```

**Takeaway:** coercion fixes **keys and nesting**, not **wrong tool name** - if the model says **`weather`** for a GDP question, **`weather_current_c`** still runs (and may raise).

---

### 6. `reg.call` and tool failures

**`reg.call`** applies Pydantic and invokes the registered lambda. **Any** **`ValueError`** (geocode), **`ValidationError`**, **`KeyError`**, or **`TypeError`** is printed and exits **1** - the script does **not** silently switch tools.

```python
    try:
        tool_out = reg.call(name, coerced)
    except (KeyError, ValidationError, TypeError, ValueError) as e:
        console.print(f"[red]Tool execution failed:[/] {e}")
        raise SystemExit(1) from e
```

**Takeaway:** treat failures as feedback to improve prompts, models, or add **`grammar`** / structured outputs.

---

### 7. Second `complete` (summarizer)

The follow-up user message embeds the **original question** and the **tool output** string. **`_SUMMARY_SYSTEM`** forbids inventing facts beyond the tool text and bans meta prefixes like “The final reply is”.

```python
    follow = (
        f"The user asked:\n{user_task}\n\n"
        f"The tool {name} returned:\n{tool_out}\n\n"
        "Write the final reply for the user following the system rules."
    )
    summary_engine = PromptEngine(system_prompt=_SUMMARY_SYSTEM)
    answer = agent.complete(follow, engine=summary_engine, max_tokens=160, temperature=0.35)
```

**Takeaway:** two **`PromptEngine`** instances (router vs summarizer) share one **`AgentCore`** and one GGUF load.

---

### 8. CLI: remainder task + `--calc-only`

**`argparse.REMAINDER`** collects everything after flags so multi-word questions work without extra quoting layers. **`--calc-only`** toggles the registry only.

```python
    ap.add_argument(
        "--calc-only",
        action="store_true",
        help="Register only calc (smaller schema for tiny models). Default: full chapter registry.",
    )
    ap.add_argument("task", nargs=argparse.REMAINDER, help="User question (remainder).")
    args = ap.parse_args()
    user_task = " ".join(args.task).strip() or (
        "What is 21 times 2? Reply with only one JSON object with keys \"name\" and \"arguments\" "
        "for the appropriate tool."
    )
```

**Takeaway:** for arguments that start with **`-`**, use **`--`** before the remainder or quote the whole task string.

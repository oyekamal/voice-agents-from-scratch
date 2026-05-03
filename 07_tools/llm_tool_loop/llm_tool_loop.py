"""One-turn local LLM emits tool JSON; we validate, call ToolRegistry, then summarize.

Uses **`AgentCore`** raw completion (Qwen chat template + **`llama_cpp.Llama.__call__`**). Tool
**choice** comes from the model's JSON only (no keyword reroutes). **`_coerce_tool_arguments`**
only fixes common **argument-shape** mistakes (nested fields, wrong key names) before Pydantic.
For production, prefer native tool-calling APIs or **`grammar=`** on **`Llama`** via an extended
**`AgentCore`**.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

_CH07 = Path(__file__).resolve().parent.parent
if str(_CH07) not in sys.path:
    sys.path.insert(0, str(_CH07))

from pydantic import ValidationError
from rich.console import Console

from voice_agents.agent.agent_core import AgentCore
from voice_agents.agent.prompt_engine import PromptEngine
from voice_agents.tools.registry import ToolRegistry

from calculator_tool.calculator_tool import CalcParams, calculator_eval
from chapter_registry import build_registry

REPO = _CH07.parent
LLM = REPO / "models" / "llm" / "qwen2.5-0.5b-instruct-q4_k_m.gguf"


def _calc_only_registry() -> ToolRegistry:
    r = ToolRegistry()
    r.register("calc", CalcParams, lambda m: calculator_eval(m))
    return r


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
            "- **search** – ALL general knowledge questions (people, geography, capitals, definitions, history, GDP, etc.). Default tool unless the query clearly matches another tool.\n"
            "- **weather** – ONLY if the user explicitly asks about temperature, forecast, climate, or conditions (e.g., weather, temperature, rain, forecast). DO NOT use for general place questions.\n"
            "- **time** - current local time / formatted clock string.\n"
            "- **calc** - pure arithmetic expressions only.\n"
            "- If unsure, ALWAYS use **search**. \n"
        )
    base += "\nAvailable tools (JSON Schema list):\n" + schema_block + "\n"
    return base


_SUMMARY_SYSTEM = """You summarize tool output for the user.

Rules:
- Never invent facts that are not supported by the tool output.
- If the tool output does not answer the user's question, say so honestly in one or two sentences.
- If it does answer the question, reply briefly and directly.
- Do not mention JSON, tool names, or internal steps unless the user asks.
- Do not prefix with meta phrases like \"The final reply is\" - answer directly."""


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


def main() -> None:
    console = Console()
    if not LLM.is_file():
        console.print("[red]Missing GGUF.[/] Run [cyan]00_start_here/download_models.py[/] first.")
        raise SystemExit(1)

    ap = argparse.ArgumentParser(
        description="LLM chooses tool JSON → ToolRegistry.call → summary (no keyword routing)."
    )
    ap.add_argument(
        "--calc-only",
        action="store_true",
        help="Register only calc (smaller schema for tiny models). Default: full chapter registry.",
    )
    ap.add_argument(
        "task",
        nargs=argparse.REMAINDER,
        help="User question (remainder).",
    )
    args = ap.parse_args()
    user_task = " ".join(args.task).strip() or (
        "What is 21 times 2? Reply with only one JSON object with keys \"name\" and \"arguments\" "
        "for the appropriate tool."
    )

    reg = _calc_only_registry() if args.calc_only else build_registry()
    schema_block = json.dumps(reg.schema_list(), indent=2)
    system = _tool_router_system_prompt(schema_block, calc_only=args.calc_only)
    router_engine = PromptEngine(system_prompt=system)

    agent = AgentCore(model_path=str(LLM), n_ctx=2048)
    console.print("[dim]Step 1: model chooses tool (JSON only)…[/]")
    raw = agent.complete(
        user_task,
        engine=router_engine,
        max_tokens=256,
        temperature=0.05,
    )
    console.print("[dim]Raw model output:[/]\n", raw, sep="")

    try:
        spec = _extract_json_object(raw)
        name = str(spec["name"])
        arguments = spec["arguments"]
    except (KeyError, json.JSONDecodeError, ValueError, TypeError) as e:
        console.print(f"[red]Could not parse tool JSON:[/] {e}")
        raise SystemExit(1) from e

    try:
        coerced = _coerce_tool_arguments(name, arguments)
    except (TypeError, ValueError) as e:
        console.print(f"[red]Could not normalize tool arguments:[/] {e}")
        raise SystemExit(1) from e
    if coerced != arguments:
        console.print(f"[dim]Normalized arguments to[/] {coerced!r}")

    console.print(f"\n[bold]Calling tool[/] [green]{name}[/] with {coerced!r}")
    try:
        tool_out = reg.call(name, coerced)
    except (KeyError, ValidationError, TypeError, ValueError) as e:
        console.print(f"[red]Tool execution failed:[/] {e}")
        raise SystemExit(1) from e

    console.print(f"\n[bold]Tool result[/]\n{tool_out}\n")

    console.print("[dim]Step 2: model summarizes tool result for the user…[/]")
    follow = (
        f"The user asked:\n{user_task}\n\n"
        f"The tool {name} returned:\n{tool_out}\n\n"
        "Write the final reply for the user following the system rules."
    )
    summary_engine = PromptEngine(system_prompt=_SUMMARY_SYSTEM)
    answer = agent.complete(follow, engine=summary_engine, max_tokens=160, temperature=0.35)
    console.print(f"\n[bold]Assistant[/]\n{answer}")


if __name__ == "__main__":
    main()

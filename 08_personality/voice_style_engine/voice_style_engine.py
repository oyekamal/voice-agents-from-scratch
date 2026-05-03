"""Map simple style tags to system prompt suffixes."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from voice_agents.agent.prompt_engine import PromptEngine

STYLES: dict[str, str] = {
    "kind": "Be warm and encouraging.",
    "concise": "Use at most two short sentences.",
    "teacher": "Explain briefly, then give one concrete example.",
}

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_GGUF = _REPO_ROOT / "models" / "llm" / "qwen2.5-0.5b-instruct-q4_k_m.gguf"

_DEMO_USER = "What is asyncio?"
_RULE = "-" * 56


def engine_with_style(base_system: str, style: str) -> PromptEngine:
    extra = STYLES.get(style, "")
    return PromptEngine(system_prompt=f"{base_system}\n\n{extra}".strip())


def _print_chat_turn(heading: str, engine: PromptEngine, user: str) -> None:
    print(f"\n### {heading}\n{_RULE}")
    print("SYSTEM:")
    print(engine.system_prompt)
    print("\nUSER (unchanged across styles below):")
    print(user)


def _print_prompt_demo(*, base_system: str) -> None:
    print(
        "\nStyle tags only change SYSTEM; USER stays the same.\n"
        "Below: baseline, then every tag in STYLES (same USER each time).\n"
        "Try:  --llm  (two completions: baseline vs concise).\n"
    )
    u = _DEMO_USER
    n = 1
    _print_chat_turn(f"{n}  -  Baseline (no STYLES suffix)", PromptEngine(system_prompt=base_system), u)
    for tag in STYLES:
        n += 1
        _print_chat_turn(f'{n}  -  + tag "{tag}"', engine_with_style(base_system, tag), u)


def _print_llm_preamble_compact(*, base_system: str) -> None:
    """Short context before model runs (--llm default)."""
    u = _DEMO_USER
    b = engine_with_style(base_system, "concise")
    print(
        f"\nSame USER for both runs:  {u}\n"
        f"{_RULE}\n"
        "[A] SYSTEM (baseline)\n"
        f"{base_system}\n"
        f"\n[B] SYSTEM (+ concise)\n"
        f"{b.system_prompt}\n"
        f"{_RULE}"
    )


def _run_llm_compare(*, model_path: Path, base_system: str) -> None:
    if not model_path.is_file():
        print(
            f"\nNo GGUF at:\n  {model_path}\n"
            "Run: uv run python 00_start_here/download_models.py\n"
            "(Same model as chapter 04 simple_agent.)",
            file=sys.stderr,
        )
        raise SystemExit(1)
    from voice_agents.agent.agent_core import AgentCore

    user = _DEMO_USER
    print("\nLoading model…", flush=True)
    agent = AgentCore(model_path=str(model_path))
    plain = PromptEngine(system_prompt=base_system)
    concise = engine_with_style(base_system, "concise")
    out_plain = agent.complete(user, engine=plain, max_tokens=140, temperature=0.35)
    out_concise = agent.complete(user, engine=concise, max_tokens=140, temperature=0.35)

    banner = "#" * 56
    print(f"\n{banner}\n#  MODEL OUTPUT  [A]  baseline SYSTEM only\n{banner}\n")
    print(out_plain)
    print(f"\n{banner}\n#  MODEL OUTPUT  [B]  SYSTEM + concise style\n{banner}\n")
    print(out_concise)
    print(f"\n{_RULE}\n[A] = baseline SYSTEM; [B] = + concise (same USER for both).")


def main() -> None:
    p = argparse.ArgumentParser(description="Map style tags to PromptEngine system_prompt suffixes.")
    p.add_argument(
        "--llm",
        action="store_true",
        help="Load Qwen GGUF: two completions, baseline vs concise (same user text).",
    )
    p.add_argument(
        "--show-style-grid",
        action="store_true",
        help="With --llm: print baseline + every STYLES tag before the model (verbose).",
    )
    p.add_argument(
        "--model",
        type=Path,
        default=_DEFAULT_GGUF,
        help=f"GGUF path (default: {_DEFAULT_GGUF.name} under models/llm/).",
    )
    p.add_argument(
        "--base-system",
        default="You are a helpful assistant.",
        help="Base system string before style suffix (default: helpful assistant).",
    )
    args = p.parse_args()
    base = args.base_system.strip()

    if args.llm:
        if args.show_style_grid:
            _print_prompt_demo(base_system=base)
        else:
            _print_llm_preamble_compact(base_system=base)
        _run_llm_compare(model_path=args.model, base_system=base)
    else:
        _print_prompt_demo(base_system=base)


if __name__ == "__main__":
    main()

"""Keyword-based tone hint (toy example - real sentiment needs a classifier)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from voice_agents.agent.prompt_engine import PromptEngine

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_GGUF = _REPO_ROOT / "models" / "llm" / "qwen2.5-0.5b-instruct-q4_k_m.gguf"
_RULE = "-" * 56


def hint_from_text(user: str) -> str:
    low = user.lower()
    if any(w in low for w in ("sad", "sorry", "worried")):
        return "Respond with empathy and reassurance."
    if any(w in low for w in ("great", "awesome", "thanks")):
        return "Match the user's positive energy briefly."
    return "Stay neutral and helpful."


def _print_explanation(*, user: str, engine: PromptEngine) -> None:
    hint = hint_from_text(user)
    print(
        "\nKeyword tone hint (toy)\n"
        f"{_RULE}\n"
        "In a voice loop, STT gives you a user string. This demo maps coarse keywords\n"
        "to an extra instruction line, then appends it to a fixed persona in SYSTEM.\n"
        "The model reads SYSTEM first, then answers the USER message.\n"
        f"\n{_RULE}\n"
        "Sample USER line (as if from speech-to-text):\n"
        f"  {user}\n"
        f"\n{_RULE}\n"
        "Keyword-derived hint (what we add under the persona):\n"
        f"  {hint}\n"
        f"\n{_RULE}\n"
        "Full SYSTEM prompt (persona + hint  -  this steers tone before the reply):\n"
    )
    print(engine.system_prompt)
    print(_RULE)


def _run_llm(*, user: str, engine: PromptEngine, model_path: Path) -> None:
    if not model_path.is_file():
        print(
            f"\nNo GGUF at:\n  {model_path}\n"
            "Run: uv run python 00_start_here/download_models.py\n"
            "Then: uv run python 08_personality/emotional_responses/emotional_responses.py --llm",
            file=sys.stderr,
        )
        raise SystemExit(1)
    from voice_agents.agent.agent_core import AgentCore

    print("\nLoading model…", flush=True)
    agent = AgentCore(model_path=str(model_path))
    reply = agent.complete(user, engine=engine, max_tokens=160, temperature=0.45)
    banner = "#" * 56
    print(f"\n{banner}\n#  MODEL OUTPUT (assistant)\n{banner}\n")
    print(reply)


def main() -> None:
    p = argparse.ArgumentParser(description="Keyword-based tone hints merged into PromptEngine.")
    p.add_argument(
        "--llm",
        action="store_true",
        help="Load Qwen GGUF and print one assistant reply using the engineered SYSTEM prompt.",
    )
    p.add_argument(
        "--model",
        type=Path,
        default=_DEFAULT_GGUF,
        help=f"GGUF path (default: {_DEFAULT_GGUF.name} under models/llm/).",
    )
    p.add_argument(
        "--user",
        default="I'm worried about the deadline.",
        help='Sample user line (default: worried colleague line).',
    )
    args = p.parse_args()
    user = args.user.strip()
    engine = PromptEngine(
        system_prompt=(
            "You are a supportive colleague.\n\n" + hint_from_text(user)
        ).strip()
    )

    _print_explanation(user=user, engine=engine)

    if args.llm:
        _run_llm(user=user, engine=engine, model_path=args.model)
    else:
        print(
            "\nTip: same script with  --llm  prints a sample assistant reply\n"
            "     (needs the Qwen GGUF under models/llm/, same as chapter 04).\n"
        )


if __name__ == "__main__":
    main()

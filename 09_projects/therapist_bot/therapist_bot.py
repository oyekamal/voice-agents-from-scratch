"""Supportive-listener REPL with a **toy** keyword hint mutating system text each turn.

**Not** therapy, crisis support, or medical advice  -  a teaching sketch only.

The ``hint_from_text`` function matches
``08_personality/emotional_responses/emotional_responses.py`` (copy here so you see
per-turn ``engine.system_prompt = ...`` without import path tricks).
"""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.prompt import Prompt

from voice_agents.agent.agent_core import AgentCore
from voice_agents.agent.prompt_engine import PromptEngine

ROOT = Path(__file__).resolve().parents[2]
LLM = ROOT / "models" / "llm" / "qwen2.5-0.5b-instruct-q4_k_m.gguf"

# Base boundaries (see also full emotional_responses demo in chapter 08)
BASE_PERSONA = (
    "You are a supportive listener. Reflect briefly, avoid medical claims, "
    "and suggest professional help if a crisis is mentioned."
)


def hint_from_text(user: str) -> str:
    # Copied from 08_personality/emotional_responses/emotional_responses.py
    low = user.lower()
    if any(w in low for w in ("sad", "sorry", "worried")):
        return "Respond with empathy and reassurance."
    if any(w in low for w in ("great", "awesome", "thanks")):
        return "Match the user's positive energy briefly."
    return "Stay neutral and helpful."


def main() -> None:
    console = Console()
    if not LLM.is_file():
        console.print("Download models first (chapter 00).")
        raise SystemExit(1)

    agent = AgentCore(model_path=str(LLM))
    engine = PromptEngine(system_prompt=BASE_PERSONA)
    console.print(
        "[dim]Listener sketch  -  not a substitute for real support. "
        "Empty line, [bold]quit[/], or [bold]exit[/] to stop. "
        "Watch the [dim](hint -> …)[/] line each turn.[/]"
    )
    while True:
        user = Prompt.ask("You")
        if not user.strip() or user.strip().lower() in {"quit", "exit"}:
            break
        hint = hint_from_text(user)
        engine.system_prompt = f"{BASE_PERSONA}\n\n{hint}"
        console.print(f"[dim](hint -> {hint})[/]")
        reply = agent.complete(user, engine=engine, max_tokens=180, temperature=0.5)
        console.print(f"[bold]Assistant[/] {reply}")


if __name__ == "__main__":
    main()

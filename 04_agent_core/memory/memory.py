"""PromptEngine memory lines across multiple turns (still in-process)."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.prompt import Prompt

from voice_agents.agent.agent_core import AgentCore
from voice_agents.agent.prompt_engine import PromptEngine

ROOT = Path(__file__).resolve().parents[2]
LLM = ROOT / "models" / "llm" / "qwen2.5-0.5b-instruct-q4_k_m.gguf"


def main() -> None:
    console = Console()
    if not LLM.is_file():
        console.print("Download LLM first.")
        raise SystemExit(1)
    agent = AgentCore(model_path=str(LLM))
    engine = PromptEngine(system_prompt="You are a concise assistant. Remember facts the user states.")
    console.print(
        "[dim]After [/][bold]You:[/][dim], type what you want to say to the assistant  -  "
        "full sentences are fine (same as texting). Try stating a fact, then asking about it later "
        "(e.g. first: [/][bold]My favorite color is blue.[/][dim] then: [/][bold]What color did I mention?[/][dim]). "
        "Type [/][bold]quit[/][dim] or [/][bold]exit[/][dim] and press Enter to leave.[/]"
    )
    while True:
        user = Prompt.ask("You")
        if user.strip().lower() in {"quit", "exit"}:
            break
        reply = agent.complete(user, engine=engine, max_tokens=256)
        console.print(f"[bold]Assistant[/] {reply}")


if __name__ == "__main__":
    main()

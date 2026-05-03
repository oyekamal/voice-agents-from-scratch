"""Hiring-manager interview with memory across turns (one shared ``PromptEngine``).

``AgentCore.complete`` appends each user/assistant line to ``engine.memory_lines``; the
next call builds a user message with "Context from earlier in the conversation"  -  no
extra state variable. Type an empty line, **quit**, or **exit** to stop.
"""

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
        console.print("Download models first (chapter 00).")
        raise SystemExit(1)

    agent = AgentCore(model_path=str(LLM))
    engine = PromptEngine(
        system_prompt=(
            "You are a hiring manager running a behavioral interview. "
            "Ask one focused follow-up at a time. Use earlier turns to dig deeper, "
            "not to repeat questions."
        )
    )
    console.print(
        "[dim]Behavioral interview  -  type your answer after [bold]Candidate[/]. "
        "Empty line, [bold]quit[/], or [bold]exit[/] to stop.[/]"
    )
    while True:
        user = Prompt.ask("Candidate")
        if not user.strip() or user.strip().lower() in {"quit", "exit"}:
            break
        reply = agent.complete(user, engine=engine, max_tokens=200)
        console.print(f"[bold]Interviewer[/] {reply}")
    console.print(
        f"\n[dim]Lines in PromptEngine.memory_lines: {len(engine.memory_lines)} "
        f"(user + assistant alternation from AgentCore).[/]"
    )


if __name__ == "__main__":
    main()

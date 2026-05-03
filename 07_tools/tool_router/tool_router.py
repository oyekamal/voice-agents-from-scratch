"""Register tools and invoke by name with JSON-like dict args."""

from __future__ import annotations

import sys
from pathlib import Path

_CH07 = Path(__file__).resolve().parent.parent
if str(_CH07) not in sys.path:
    sys.path.insert(0, str(_CH07))

from rich.console import Console
from rich.pretty import pprint

from chapter_registry import build_registry


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


if __name__ == "__main__":
    main()

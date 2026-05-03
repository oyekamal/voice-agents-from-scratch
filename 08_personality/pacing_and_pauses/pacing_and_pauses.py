"""Split assistant text into clauses for staggered TTS (pause markers)."""

from __future__ import annotations

import re

_SPLIT = re.compile(r"(?<=[.!?])\s+")

_RULE = "-" * 56

_DEMO = "Hello. This is one thought! And here is another - with care."


def chunks_for_tts(text: str, max_chars: int = 120) -> list[str]:
    parts = _SPLIT.split(text.strip())
    out: list[str] = []
    buf = ""
    for p in parts:
        if len(buf) + len(p) > max_chars and buf:
            out.append(buf.strip())
            buf = p
        else:
            buf = (buf + " " + p).strip()
    if buf:
        out.append(buf)
    return out


def _print_chunk_run(*, label: str, text: str, max_chars: int) -> None:
    chunks = chunks_for_tts(text, max_chars=max_chars)
    print(f"\n{label}")
    print(f"  max_chars={max_chars!r}  →  {len(chunks)} chunk(s)\n")
    for i, c in enumerate(chunks):
        tail = (
            "then pause before speaking chunk "
            f"{i + 1}."
            if i < len(chunks) - 1
            else "then finish (or wait for user) - no further chunks."
        )
        print(f"  Chunk {i} - one TTS utterance; {tail}\n    {c}\n")


def main() -> None:
    print(
        "\nPacing for TTS (text side)\n"
        f"{_RULE}\n"
        "Assistant replies are plain text. This helper:\n"
        "  1) splits on sentence endings (. ? !),\n"
        "  2) merges sentences until adding the next would exceed max_chars,\n"
        "  3) returns a list - each item is something you can feed to TTS as one block,\n"
        "     with a natural pause between blocks (clause boundaries).\n"
        f"\nDemo assistant text:\n  {_DEMO!r}\n"
        f"\n{_RULE}"
    )
    _print_chunk_run(
        label="A - generous max_chars (default 120)",
        text=_DEMO,
        max_chars=120,
    )
    print(
        "If everything fits under the limit, you get a single chunk (still valid for TTS).\n"
        f"{_RULE}"
    )
    _print_chunk_run(
        label="B - tight max_chars (45) on the same text",
        text=_DEMO,
        max_chars=45,
    )
    print(
        "Same sentences; smaller max_chars forces more splits so you see staggered playback.\n"
        "Hook these strings into your Kokoro loop from chapter 03 / full loop from chapter 05.\n"
    )


if __name__ == "__main__":
    main()

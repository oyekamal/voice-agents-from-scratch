"""Very small HTML fetch + DuckDuckGo lite result parsing - **not** a production search API."""

from __future__ import annotations

import html
import re
import textwrap

import httpx
from pydantic import BaseModel, Field

# DuckDuckGo lite HTML layout (fragile): table rows with result-link + result-snippet.
_RE_TITLE = re.compile(r"""class=['"]result-link['"]>([^<]*)</a>""", re.IGNORECASE)
_RE_SNIPPET = re.compile(
    r"""<td\s+class=['"]result-snippet['"]\s*>\s*(.*?)\s*</td>""",
    re.IGNORECASE | re.DOTALL,
)

_MAX_RESULTS = 5
_MAX_SNIPPET_CHARS = 320


class SearchParams(BaseModel):
    query: str = Field(..., min_length=1, description="Search query")


def _strip_tags(fragment: str) -> str:
    t = re.sub(r"<[^>]+>", " ", fragment)
    t = html.unescape(t)
    return re.sub(r"\s+", " ", t).strip()


def _parse_lite_results(page: str) -> list[tuple[str, str]]:
    titles = [html.unescape(s.strip()) for s in _RE_TITLE.findall(page)]
    snippets_raw = _RE_SNIPPET.findall(page)
    snippets = [_strip_tags(s) for s in snippets_raw]
    pairs: list[tuple[str, str]] = []
    for title, snip in zip(titles, snippets):
        if title or snip:
            pairs.append((title, snip))
    return pairs


def web_search_lite(params: SearchParams) -> str:
    """Fetch DuckDuckGo lite HTML and extract title/snippet pairs (layout-specific)."""
    url = "https://lite.duckduckgo.com/lite/"
    r = httpx.post(
        url,
        data={"q": params.query},
        headers={"User-Agent": "voice-agents-tutorial/0.1"},
        timeout=15.0,
        follow_redirects=True,
    )
    r.raise_for_status()
    pairs = _parse_lite_results(r.text)
    header = f"Search: {params.query}\n"

    if not pairs:
        return (
            header
            + "No result blocks matched (DuckDuckGo may have changed their HTML). "
            + "Try again later or use a real search API."
        )

    lines: list[str] = [header.rstrip(), ""]
    for i, (title, snip) in enumerate(pairs[:_MAX_RESULTS], start=1):
        if len(snip) > _MAX_SNIPPET_CHARS:
            snip = snip[: _MAX_SNIPPET_CHARS - 1].rsplit(" ", 1)[0] + "…"
        block = f"{i}. {title}\n   {textwrap.fill(snip, width=88, subsequent_indent='   ')}"
        lines.append(block)
        lines.append("")
    return "\n".join(lines).rstrip()


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="DuckDuckGo lite result scrape (tutorial-only).")
    p.add_argument(
        "query_pos",
        nargs="?",
        default=None,
        help="Search string (positional). Ignored if --query is set.",
    )
    p.add_argument(
        "-q",
        "--query",
        dest="query_opt",
        default=None,
        metavar="TEXT",
        help="Search string (use for queries that start with '-' )",
    )
    args = p.parse_args()
    q = args.query_opt if args.query_opt is not None else (args.query_pos if args.query_pos is not None else "python asyncio")
    print(web_search_lite(SearchParams(query=q)))

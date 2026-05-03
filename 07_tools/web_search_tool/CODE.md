# Web search lite (HTML scrape)

Production stacks call a **search API** with structured hits. This tutorial script **POST**s to **DuckDuckGo lite** and parses **their** HTML table: each row exposes a **`result-link`** title and a **`result-snippet`** blurb. That skips the huge region-selector block at the top of the page (what you saw when we naïvely stripped the whole document to **400** characters).

If DuckDuckGo changes class names or table layout, **`_parse_lite_results`** returns nothing and you get an explicit fallback message - that is still the **scraping is fragile** lesson.

---

## Runnable

Optional **positional** query, or **`--query` / `-q`** (handy if the string starts with **`-`**). Default query: **`python asyncio`**.

```bash
uv run python 07_tools/web_search_tool/web_search_tool.py
uv run python 07_tools/web_search_tool/web_search_tool.py "who is prime minister in germany"
uv run python 07_tools/web_search_tool/web_search_tool.py -q "open meteo api"
```

---

## Code walkthrough (`web_search_tool.py`)

### 1. `SearchParams`: guard empty queries before HTTP

**`min_length=1`** rejects **`""`** at validation time. The **`description`** feeds the tool JSON Schema for the LLM.

```python
class SearchParams(BaseModel):
    query: str = Field(..., min_length=1, description="Search query")
```

**Takeaway:** validate cheaply in Pydantic so **`web_search_lite`** always receives a non-empty **`query`**.

---

### 2. POST lite endpoint

Same transport as before: form **`q`**, **`User-Agent`**, redirects, timeout, **`raise_for_status()`**.

```python
    url = "https://lite.duckduckgo.com/lite/"
    r = httpx.post(
        url,
        data={"q": params.query},
        headers={"User-Agent": "voice-agents-tutorial/0.1"},
        timeout=15.0,
        follow_redirects=True,
    )
    r.raise_for_status()
```

**Takeaway:** failures here are **HTTP-layer**; your agent can catch **`httpx.HTTPError`** and return a short error string to the model.

---

### 3. Regex hooks on DuckDuckGo’s result table

Titles come from **`class='result-link'`** (or double quotes - patterns allow both). Snippets are the inner HTML of **`td.result-snippet`**, then inner tags are stripped and entities decoded with **`html.unescape`**.

```python
_RE_TITLE = re.compile(r"""class=['"]result-link['"]>([^<]*)</a>""", re.IGNORECASE)
_RE_SNIPPET = re.compile(
    r"""<td\s+class=['"]result-snippet['"]\s*>\s*(.*?)\s*</td>""",
    re.IGNORECASE | re.DOTALL,
)

def _parse_lite_results(page: str) -> list[tuple[str, str]]:
    titles = [html.unescape(s.strip()) for s in _RE_TITLE.findall(page)]
    snippets_raw = _RE_SNIPPET.findall(page)
    snippets = [_strip_tags(s) for s in snippets_raw]
    pairs: list[tuple[str, str]] = []
    for title, snip in zip(titles, snippets):
        if title or snip:
            pairs.append((title, snip))
    return pairs
```

**Takeaway:** this is **not** a DOM tree walk - regex is brittle, but keeps the chapter dependency-free. A real app would use **`html.parser`**, **`lxml`**, or an API.

---

### 4. Human-readable bundle for the LLM

The first line repeats **`Search: …`** so it is obvious which query produced the block (fixes the “did it use my string?” confusion when reading logs). Up to **`_MAX_RESULTS`** hits; long snippets are truncated on a word boundary where possible.

```python
    header = f"Search: {params.query}\n"

    if not pairs:
        return (
            header
            + "No result blocks matched (DuckDuckGo may have changed their HTML). "
            + "Try again later or use a real search API."
        )

    lines: list[str] = [header.rstrip(), ""]
    for i, (title, snip) in enumerate(pairs[:_MAX_RESULTS], start=1):
        ...
        block = f"{i}. {title}\n   {textwrap.fill(snip, width=88, subsequent_indent='   ')}"
```

**Takeaway:** voice agents and small LLMs benefit from **labeled, numbered** text instead of one flat soup of navigation chrome.

---

### 5. CLI: positional or `-q` / `--query`

**`--query` wins** over the positional so scripts and shells behave predictably; if neither is set, the default string is **`python asyncio`**.

```python
    p.add_argument("query_pos", nargs="?", default=None, ...)
    p.add_argument("-q", "--query", dest="query_opt", default=None, metavar="TEXT", ...)
    args = p.parse_args()
    q = args.query_opt if args.query_opt is not None else (
        args.query_pos if args.query_pos is not None else "python asyncio"
    )
    print(web_search_lite(SearchParams(query=q)))
```

**Takeaway:** for a query like **`-v python`**, use **`--query '-v python'`** or **`-- -v python`** with the positional.

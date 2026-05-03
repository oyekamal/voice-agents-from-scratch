# Pacing and pauses for TTS

Long assistant replies sound robotic if you stream or play them as one blob. Splitting on **sentence boundaries** gives natural **pause points** between Kokoro (or other) utterances - see [chapter 03](../../03_text_to_speech/README.md) for playback; this module is the **text** side only.

---

## Runnable

Run **[`pacing_and_pauses.py`](./pacing_and_pauses.py)**; it explains the pipeline, runs **`chunks_for_tts`** on one demo string with **two** **`max_chars`** values (default **120** vs **45**) so you see one chunk vs several.

```bash
uv run python 08_personality/pacing_and_pauses/pacing_and_pauses.py
```

---

## Code walkthrough (`pacing_and_pauses.py`)

### 1. Sentence split with a lookbehind regex

`_SPLIT` matches **whitespace that follows** sentence-ending punctuation. The **`(?<=...)`** lookbehind keeps the `.?!` on the left chunk instead of eating them.

```python
import re

_SPLIT = re.compile(r"(?<=[.!?])\s+")
```

For input like `Hello. Next sentence!` you get `["Hello.", "Next sentence!"]`. A clause joined only by **dashes** (no `.?!`) stays inside one segment - see the demo string’s last part.

**Takeaway:** this is English-centric; other languages need different segmenters for production.

---

### 2. Merge sentences up to `max_chars`

The loop walks **`parts`**, appending to **`buf`**. If adding the next part would exceed **`max_chars`** and **`buf`** is non-empty, **`buf`** is flushed to **`out`** and the current part starts a new buffer. Trailing space is normalized with **`.strip()`** when appending.

```python
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
```

**Takeaway:** you get **at most one forced break** per “over budget” event, still aligned to sentence boundaries from `_SPLIT` whenever possible.

---

### 3. `main()`: explain, then two **`max_chars`** runs

**`main()`** prints a short intro, then **`_print_chunk_run`** twice on the same **`_DEMO`** string so you see **one** playback-sized chunk when the limit is loose and **several** when **`max_chars`** is tight.

```python
_print_chunk_run(label="A  -  generous max_chars (default 120)", text=_DEMO, max_chars=120)
_print_chunk_run(label="B  -  tight max_chars (45) on the same text", text=_DEMO, max_chars=45)
```

**Takeaway:** combine this with [emotional_responses](../emotional_responses/CODE.md) in order: pick **tone** in the system prompt first, then **chunk** the assistant reply for playback.

# Time tool (strftime)

This is intentionally boring: the model often needs **“what time is it?”** without you baking clocks into the prompt. The tool returns **`datetime.now()`** formatted with a **`strftime`** pattern. There is **no** network and **no** shell: a few lines of code you can audit in a code review.

Because **`fmt`** has a **default** on the Pydantic model, the JSON Schema marks it as optional—handy when you smoke-test **`ToolRegistry.call`** with an empty **`{}`** for the time tool.

---

## Runnable

Run **[`time_tool.py`](./time_tool.py)**; **`__main__`** uses default **`fmt`** and prints one line.

```bash
uv run python 07_tools/time_tool/time_tool.py
```

---

## Code walkthrough (`time_tool.py`)

### 1. Params: optional format string with a sensible default

Callers may pass **`{"fmt": "%H:%M"}`** for a short clock readout, or omit **`fmt`** entirely. Pydantic fills in **`"%Y-%m-%d %H:%M:%S"`** before **`time_now`** runs.

```python
class TimeParams(BaseModel):
    fmt: str = "%Y-%m-%d %H:%M:%S"
```

**Takeaway:** defaults on **`BaseModel`** fields are a simple way to keep tool arguments ergonomic for both humans and smaller LLMs.

---

### 2. Single-line implementation

The entire behavior is **`strftime`**: no I/O, no globals, no timezone handling (local wall clock only). That makes failures almost impossible except for an invalid format string, which **`strftime`** would raise on—something you could map to a user-visible error in a larger agent.

```python
def time_now(params: TimeParams) -> str:
    return datetime.now().strftime(params.fmt)
```

**Takeaway:** the smallest possible tool is still useful in integration tests: if **`time`** works but **`weather`** fails, you know the registry and HTTP layers are separate concerns.

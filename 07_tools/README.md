# Chapter 07 - Tools

In a **voice** agent, the user’s words become text after **STT** (speech-to-text); from there the pipeline is the same as text chat: the LLM may still need **tools** (weather, time, search) for anything that is not in its weights or context. This chapter is about that **text-side** contract - validate JSON, run trusted code, return facts - so your voice stack stays safe and debuggable.

**Why tools at all?** A language model only has weights and context window text; it cannot *know* today’s weather, your wall clock, or the result of `21 * 2` unless you **give it a path to the real world**. **Tools** are that path: the model proposes a **name** and **arguments** (usually JSON); your code **validates**, **runs** a small trusted function, and **returns** a string the model can read in the next turn. Without that contract, you either hallucinate facts or paste fragile natural language into shells.

**Why Pydantic and JSON Schema?** The model’s output is untrusted text. You need a **hard boundary**: parse JSON, reject unknown fields and bad types, then call Python. **Pydantic** models are both runtime validators and **JSON Schema** generators - exactly what you attach to prompts so the model knows the **shape** of each tool. [`ToolRegistry`](../src/voice_agents/tools/registry.py) is the thin layer that keeps **name → schema → callable** in one place so dispatch stays boring and safe.

**Why separate tool plumbing from the LLM?** Most of the chapter is **deterministic**: you can run **`calculator_tool`** and **`tool_router`** without loading a GGUF, and when something breaks you know whether it is **HTTP**, **validation**, or **dispatch** - not “bad JSON vs bad prompt vs small model.” In production the LLM is the **noisy client** of this API; here you learn the API first, then **[`llm_tool_loop`](./llm_tool_loop/llm_tool_loop.py)** shows **model → JSON → `reg.call` → summary** with the **full** registry by default (optional **`--calc-only`** for a minimal **calc** schema when debugging tiny models).

This chapter builds that idea with small **example tools** (calculator, clock, weather, HTML “search”). **Unlike [chapter 06](../06_real_time_systems/README.md)** - where examples deliberately **omit** [`voice_agents`](../src/voice_agents/) so you see every audio thread and buffer - **here** the scripts **import** the library on purpose: the lesson is **how validation and dispatch stay centralized** so agent code does not sprawl.

**Why defer most LLM wiring?** **LLM → tool JSON → execute** depends on chat templates, stop rules, and model size. [`llm_tool_loop`](./llm_tool_loop/llm_tool_loop.py) is the reference bridge; extending the text loop from [chapter 04](../04_agent_core/README.md) with the same registry pattern remains the natural DIY exercise.

**Previous:** [Chapter 06 - Real-time systems](../06_real_time_systems/README.md).

---

## Table of Contents

- [At a glance](#at-a-glance)
- [Prerequisites](#prerequisites)
- [Suggested order](#suggested-order)
- [What each example does](#what-each-example-does)
- [Troubleshooting](#troubleshooting)
- [How this ties to the library](#how-this-ties-to-the-library)
- [Previous](#previous)
- [Next](#next)

---

## At a glance

| | |
|---|---|
| **Dependencies** | `uv sync`. **Network** for `weather_tool` and `web_search_tool` (HTTP). **`llm_tool_loop`** needs the **Qwen GGUF** under **`models/llm/`** (see [chapter 00](../00_start_here/README.md)). |
| **Done looks like** | Standalone tools + **`tool_router`**; optional **`llm_tool_loop`** runs **two** LLM turns (tool JSON, then a short user-facing summary). |

---

## Prerequisites

1. **Environment**  -  From the repository root: `uv sync` so `httpx`, `pydantic`, and `voice_agents` resolve.
2. **Registry source**  -  Optional read: [`src/voice_agents/tools/registry.py`](../src/voice_agents/tools/registry.py) for `register`, `schema_list`, and `call`.
3. **LLM demo**  -  For **`llm_tool_loop`**, run [`00_start_here/download_models.py`](../00_start_here/download_models.py) so **`qwen2.5-0.5b-instruct-q4_k_m.gguf`** exists (same requirement as [chapter 04](../04_agent_core/README.md)).

---

## Suggested order

| Order | Script | Purpose |
|------:|--------|---------|
| 1 | [`calculator_tool/calculator_tool.py`](./calculator_tool/calculator_tool.py) | Offline **AST**-limited arithmetic; Pydantic **`CalcParams`**. |
| 2 | [`time_tool/time_tool.py`](./time_tool/time_tool.py) | Offline **`datetime.now`** with a **`fmt`** string. |
| 3 | [`weather_tool/weather_tool.py`](./weather_tool/weather_tool.py) | **Open-Meteo** current temperature; **`town`** (geocoded) or **`latitude`** / **`longitude`**. |
| 4 | [`web_search_tool/web_search_tool.py`](./web_search_tool/web_search_tool.py) | **DuckDuckGo lite**: parse title/snippet rows into a short numbered list (tutorial-only). |
| 5 | [`tool_router/tool_router.py`](./tool_router/tool_router.py) | Build **`ToolRegistry`** (via [`chapter_registry.py`](./chapter_registry.py)), print JSON Schemas, run demo **`reg.call`** loop. |
| 6 | [`llm_tool_loop/llm_tool_loop.py`](./llm_tool_loop/llm_tool_loop.py) | **`AgentCore`** emits tool JSON → **`reg.call`** → second completion summarizes (default **full** registry; **`--calc-only`** for **calc** only). |

---

## What each example does

From the **repository root** (after `uv sync`).

### `calculator_tool/calculator_tool.py`

**Source:** [`calculator_tool.py`](./calculator_tool/calculator_tool.py)  -  **Learning deeper:** [`calculator_tool/CODE.md`](./calculator_tool/CODE.md)

Parses a single **`expression`** with **`ast.parse(..., mode="eval")`** and evaluates a tiny allowed subset (numbers, `+ - * / **`, unary `-`).

```bash
uv run python 07_tools/calculator_tool/calculator_tool.py
```

---

### `time_tool/time_tool.py`

**Source:** [`time_tool.py`](./time_tool/time_tool.py)  -  **Learning deeper:** [`time_tool/CODE.md`](./time_tool/CODE.md)

Returns **`datetime.now().strftime(params.fmt)`**; default format is ISO-like.

```bash
uv run python 07_tools/time_tool/time_tool.py
```

---

### `weather_tool/weather_tool.py`

**Source:** [`weather_tool.py`](./weather_tool/weather_tool.py)  -  **Learning deeper:** [`weather_tool/CODE.md`](./weather_tool/CODE.md)

**GET** Open-Meteo forecast with **`current=temperature_2m`**. Pass **`town`** for geocoding (label in the reply) or **`latitude`** + **`longitude`** together (label shows rounded coordinates).

```bash
uv run python 07_tools/weather_tool/weather_tool.py
uv run python 07_tools/weather_tool/weather_tool.py Paris
uv run python 07_tools/weather_tool/weather_tool.py --lat 52.52 --lon 13.41
```

---

### `web_search_tool/web_search_tool.py`

**Source:** [`web_search_tool.py`](./web_search_tool/web_search_tool.py)  -  **Learning deeper:** [`web_search_tool/CODE.md`](./web_search_tool/CODE.md)

**POST** to DuckDuckGo lite, then parses **`result-link`** / **`result-snippet`** rows (not raw page noise). Optional positional **`query`** or **`--query` / `-q`**; default **`python asyncio`**. Layout-specific - can return a “no blocks matched” message if HTML changes.

```bash
uv run python 07_tools/web_search_tool/web_search_tool.py
uv run python 07_tools/web_search_tool/web_search_tool.py -q "What is a voice agent?"  
```

---

### `tool_router/tool_router.py`

**Source:** [`tool_router.py`](./tool_router/tool_router.py)  -  **Learning deeper:** [`tool_router/CODE.md`](./tool_router/CODE.md)

Inserts **`07_tools/`** on **`sys.path`** so subfolder modules resolve, registers **`weather`**, **`search`**, **`calc`**, and **`time`**, prints **`schema_list()`**, then **`reg.call`** on demo dicts (the demo omits **`search`** but it is still registered).

```bash
uv run python 07_tools/tool_router/tool_router.py
```

---

### `llm_tool_loop/llm_tool_loop.py`

**Source:** [`llm_tool_loop.py`](./llm_tool_loop/llm_tool_loop.py)  -  **Learning deeper:** [`llm_tool_loop/CODE.md`](./llm_tool_loop/CODE.md)

Loads the **Qwen** GGUF via **`AgentCore`** (plain **`Llama`** completion, not OpenAI-style **`tools=`** or grammar-constrained JSON). Injects **`schema_list()`**, parses one JSON tool call, runs **`reg.call`**, then summarizes. **Default** exposes all chapter tools; the **model** picks **`name`**. **`--calc-only`** narrows the registry to **calc** for small-model experiments. **`_coerce_tool_arguments`** only fixes argument shape (not tool choice). Tool failures (e.g. geocoding) **exit 1** with the real exception.

```bash
uv run python 07_tools/llm_tool_loop/llm_tool_loop.py
uv run python 07_tools/llm_tool_loop/llm_tool_loop.py "What is 15 times 4?"
uv run python 07_tools/llm_tool_loop/llm_tool_loop.py "What is a voice agent?"
uv run python 07_tools/llm_tool_loop/llm_tool_loop.py --calc-only "What is 8 * 7?"
```

---

## Troubleshooting

- **HTTP errors / timeouts**  -  Check network; increase **`timeout`** in **`httpx`** calls if needed.
- **`web_search_lite` empty or weird**  -  DuckDuckGo may change HTML; this helper is intentionally minimal.
- **Import errors from `tool_router`**  -  Run with the path **`07_tools/tool_router/tool_router.py`** from repo root so **`_CH07`** points at **`07_tools/`**.
- **`llm_tool_loop` “Could not parse tool JSON”**  -  Tiny models drift into prose or invalid JSON; retry with a clearer question or use **`--calc-only`** for a smaller schema.
- **`Tool execution failed`**  -  Wrong tool or bad args (e.g. geocode miss); fix the model output or use a larger model / native tool-calling API.
- **`Failed to create llama_context`**  -  Close other GGUF processes; try freeing RAM or lowering **`n_ctx`** in the script if you edit it locally.

---

## How this ties to the library

- **[`ToolRegistry`](../src/voice_agents/tools/registry.py)**  -  **`register(name, params_model, fn)`** stores a Pydantic model class and callable; **`call`** validates dict arguments with **`model_validate`** then invokes **`fn`**.
- **[`chapter_registry.py`](./chapter_registry.py)**  -  Shared **`build_registry()`** for **`tool_router`**, **`llm_tool_loop`**, and projects that import it from **`07_tools/`** on **`sys.path`**.
- **LLM loop**  -  See **[`llm_tool_loop`](./llm_tool_loop/llm_tool_loop.py)** for a reference **model → tool JSON → `reg.call` → summary** flow; [chapter 04](../04_agent_core/README.md) remains the place to practice **`AgentCore`** and prompts without tools.

---

## Previous

[Chapter 06 - Real-time systems](../06_real_time_systems/README.md)

---

## Next

[Chapter 08 - Personality](../08_personality/README.md)

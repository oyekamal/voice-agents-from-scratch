# `prompt_engine.py`  -  code walkthrough

## Purpose

Demonstrate [`PromptEngine`](../../src/voice_agents/agent/prompt_engine.py) **without loading an LLM**: custom **system prompt**, **`add_memory`** lines, and how **`build_user_message`** stitches memory into the string that would be sent to the model.

## Run

From the repository root:

```bash
uv run python 04_agent_core/prompt_engine/prompt_engine.py
```

No **GGUF** required  -  this script only prints a preview.

## Dependencies

| Symbol | Role |
|--------|------|
| [`PromptEngine`](../../src/voice_agents/agent/prompt_engine.py) | **`system_prompt`**, **`memory_lines`**, **`add_memory`**, **`build_user_message`**. |

## Code walkthrough

```python
pe = PromptEngine(system_prompt="Answer like a pirate.")
pe.add_memory("User said they like sailing.")
msg = pe.build_user_message("Suggest a weekend hobby.")
```

**Memory cap:** [`PromptEngine.add_memory`](../../src/voice_agents/agent/prompt_engine.py) keeps at most **20** lines, dropping older ones.

## Failure modes

None specific  -  no disk paths or network.

## Try next

- [`simple_agent`](../simple_agent/CODE.md) for the first real **`AgentCore.complete`** call.

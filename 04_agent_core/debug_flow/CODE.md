# `debug_flow.py`  -  code walkthrough

## Purpose

**Inspect** what the LLM actually sees: build the full **user** message with [`PromptEngine.build_user_message`](../../src/voice_agents/agent/prompt_engine.py), run [`qwen25_chat_prompt`](../../src/voice_agents/agent/agent_core.py) for **system + user**, print the **last 400 characters** of that string, then call **`complete`** and print the reply. Text-only  -  **no STT/TTS** here; this mirrors the **LLM prompt shape** used in [chapter 05](../../05_full_voice_loop/) when audio is added around the same stack.

## Run

```bash
uv run python 04_agent_core/debug_flow/debug_flow.py
uv run python 04_agent_core/debug_flow/debug_flow.py Say hello in French.
```

Optional **CLI args** after the script become the user utterance; otherwise a default phrase is used.

## Dependencies

| Symbol | Role |
|--------|------|
| [`qwen25_chat_prompt`](../../src/voice_agents/agent/agent_core.py) | Open-format **Qwen2.5 instruct** template (`<|im_start|>system` / `user` / `assistant`). |
| [`AgentCore`](../../src/voice_agents/agent/agent_core.py) | Same **`complete`** path as other scripts. |

## Code walkthrough

```python
full_user = engine.build_user_message(user)
prompt = qwen25_chat_prompt(engine.system_prompt, full_user)
console.print(prompt[-400:])
out = agent.complete(user, engine=engine)
```

The **tail** preview matches how long prompts are usually inspected in logs.

## Failure modes

Missing GGUF → [download_models.py](../../00_start_here/download_models.py).

## Try next

- [Chapter 05  -  Full voice loop](../../05_full_voice_loop/README.md): **`blocking_voice_agent`** wires STT + this prompt style + TTS.

# Voice tutor (chapter 05 audio + tutor persona)

This script is the same **streaming** path as [`05_full_voice_loop/streaming_voice_agent/streaming_voice_agent.py`](../../05_full_voice_loop/streaming_voice_agent/streaming_voice_agent.py): **record (or `--text`) → STT → `stream_tokens` → sentence chunks → Kokoro → `play_float_mono`**. The only product change is the [`PromptEngine`](../../src/voice_agents/agent/prompt_engine.py) **system** string: a **patient tutor** instead of the default voice assistant line.

**Takeaway:** in a from-scratch build, “adding a product” is often **one prompt** plus the same I/O glue you already debugged in chapter 05.

---

## Runnable

**Default:** 5 s recording, Whisper transcript, then you hear the tutor stream by sentence.

**No mic / CI:** pass `--text`.

```bash
uv run python 09_projects/voice_tutor/voice_tutor.py
uv run python 09_projects/voice_tutor/voice_tutor.py --text "What is a Python list comprehension?"
```

Requires Whisper + LLM + Kokoro assets from [chapter 00](../../00_start_here/README.md).

---

## Code walkthrough (`voice_tutor.py`)

### 1. `--text` bypasses the microphone

[`argparse`](https://docs.python.org/3/library/argparse.html) keeps the default path **audio-first** while still giving a deterministic string for tests or headless runs.

---

### 2. Tutor persona is only `PromptEngine(system_prompt=...)`

```python
engine = PromptEngine(
    system_prompt=(
        "You are a patient tutor. Give a short explanation then one practice question. "
        "Keep replies under three sentences."
    )
)
```

Compare to [`streaming_voice_agent`](../../05_full_voice_loop/streaming_voice_agent/streaming_voice_agent.py), which uses `PromptEngine()` with the library default.

---

### 3. `stream_tokens` + sentence regex + Kokoro

[`AgentCore.stream_tokens`](../../src/voice_agents/agent/agent_core.py) yields token pieces; the script buffers until `_SENTENCE_END` matches (`.?!` + space), then calls **`Kokoro.create`** and **[`play_float_mono`](../../src/voice_agents/audio/audio_output.py)** - same chunking idea as chapter 05.

**Takeaway:** TTS starts **before** the full reply exists; pauses align with **clause boundaries**, not arbitrary token cuts.

---

### 4. Next steps

- **Duplex / barge-in:** [chapter 06](../../06_real_time_systems/README.md).
- **Richer clause splitting:** [`08_personality/pacing_and_pauses`](../../08_personality/pacing_and_pauses/pacing_and_pauses.py) (`chunks_for_tts`) if you want merge-by-`max_chars` logic instead of regex-only.

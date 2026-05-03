# `streaming_voice_agent.py`  -  code walkthrough

## Purpose

### What “streaming” means here

This script still does **STT → LLM → TTS → speakers**, but the **LLM output is streamed token-by-token** via [`AgentCore.stream_tokens`](../../src/voice_agents/agent/agent_core.py). As text accumulates, the script looks for **sentence endings** (`.` `!` `?` plus space) or a **length cap**, then calls **`Kokoro.create`** on that chunk and plays it via **[`play_float_mono`](../../src/voice_agents/audio/audio_output.py)** **before** the full answer is finished (same cosine fades + trailing silence as **`blocking_voice_agent`**, not raw **`sd.play`** on PCM).

So you often **hear the first sentence sooner** than in the fully blocking [`blocking_voice_agent`](../blocking_voice_agent/CODE.md) (which waits for one big **`complete`** then one WAV).

This is **not** full-duplex (no barge-in, no overlapping mic while speaking)  -  see [chapter 06](../../06_real_time_systems/) for that.

### Two ways to give “user text”

| Mode | What happens |
|------|----------------|
| **No CLI args** | Records **5 seconds** from the mic, runs Whisper, uses that as **`You:`** text. |
| **Words after the script path** | Skips recording  -  those words are **`You:`** text directly (good for quick tests without noise). |

Example: `uv run python …/streaming_voice_agent.py What is 2+2?`

---

## Run

```bash
uv run python 05_full_voice_loop/streaming_voice_agent/streaming_voice_agent.py
uv run python 05_full_voice_loop/streaming_voice_agent/streaming_voice_agent.py Say hello in one short sentence.
```

---

## Dependencies

| Piece | Role |
|-------|------|
| [`AgentCore.stream_tokens`](../../src/voice_agents/agent/agent_core.py) | Yields **text chunks** as the model generates. |
| **`kokoro_onnx.Kokoro`** | **`create`** per sentence chunk (direct API, not only **`synthesize_to_wav`**). |
| [`play_float_mono`](../../src/voice_agents/audio/audio_output.py) | Per-chunk playback with **fade-out / silence tail** so sentence clips don’t snap at the end. |
| [`record_seconds`](../../src/voice_agents/audio/audio_input.py), [`transcribe_samples`](../../src/voice_agents/stt/streaming_stt.py) | Mic path when no CLI text. |

---

## Code walkthrough

### Repository paths and models

```python
ROOT = Path(__file__).resolve().parents[2]
WHISPER_ROOT = ROOT / "models" / "whisper"
LLM_PATH = ROOT / "models" / "llm" / "qwen2.5-0.5b-instruct-q4_k_m.gguf"
KOKORO_MODEL = ROOT / "models" / "kokoro" / "kokoro-v1.0.onnx"
KOKORO_VOICES = ROOT / "models" / "kokoro" / "voices-v1.0.bin"
```

**`parents[2]`** is the **repository root** because the script lives under **`streaming_voice_agent/`**. The three checks (`LLM_PATH`, Kokoro ONNX, voices bundle) mirror other chapters: everything is loaded from **`models/`** after [download_models.py](../../00_start_here/download_models.py).

---

### Where **`You:`** text comes from

```python
user_q = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else None
if user_q is None:
    audio, sr = record_seconds(5.0, config=AudioInputConfig())
    text = transcribe_samples(audio, sr, config=TranscribeConfig(download_root=str(WHISPER_ROOT)))
else:
    text = user_q
```

| Branch | Meaning |
|--------|---------|
| **CLI words** | Joined with spaces  -  easy way to test **streaming + TTS** without mic noise or VAD. |
| **No args** | **5.0 s** recording, then Whisper  -  same STT stack as [`blocking_voice_agent`](../blocking_voice_agent/CODE.md), fixed duration. |

If **`text`** is empty after STT, the script exits before loading the LLM.

---

### LLM streaming (token iterator)

```python
agent = AgentCore(model_path=str(LLM_PATH))
engine = PromptEngine()
for piece in agent.stream_tokens(text, engine=engine, max_tokens=256):
```

[`AgentCore.stream_tokens`](../../src/voice_agents/agent/agent_core.py) calls **`llama-cpp-python`** with **`stream=True`**. Each **`piece`** is a **small string fragment** (often a few characters) from the assistant continuation  -  **not** a full sentence. The script **concatenates** those fragments into a growing **`buf`** so it can look for **sentence boundaries** in accumulated text.

[`PromptEngine`](../../src/voice_agents/agent/prompt_engine.py) supplies the **system prompt** and **memory** rules; after the stream finishes, **`stream_tokens`** appends the usual **`User:`** / **`Assistant:`** lines to memory (same contract as **`complete`**).

---

### Kokoro instance and voice id

```python
k = Kokoro(str(KOKORO_MODEL), str(KOKORO_VOICES))
voice = "af_heart" if "af_heart" in k.get_voices() else k.get_voices()[0]
```

One **`Kokoro`** object is reused for every **`create`** call  -  avoids reloading ONNX for each sentence chunk. **`af_heart`** is preferred when present; otherwise the **first** voice id from the bundle is used (deterministic fallback).

---

### Sentence splitting and why the **`while`** loop

```python
_SENTENCE_END = re.compile(r"([.!?]\s+)")
# ...
buf += piece
while True:
    m = _SENTENCE_END.search(buf)
    if not m:
        break
    chunk = buf[: m.end()].strip()
    buf = buf[m.end() :]
    if chunk:
        _play_kokoro(k, voice, chunk)
```

- **Pattern `[.!?]\s+`** means: punctuation that ends a sentence **plus** at least one whitespace character (space, newline, etc.). You need that whitespace so **`3.14`** does not flush after **`3.`** alone. Abbreviations (**`Dr.`**) can still flush early  -  this tutorial keeps the regex simple on purpose.

- **`buf[: m.end()]`** is only the text **through** that delimiter  -  **not** the start of the next sentence still arriving from the LLM. Earlier versions cleared **`buf`** entirely on each match and fed **everything** to Kokoro, which included **half of the next sentence** and sounded like a **garbled word** between clips.

- **`buf[m.end():]`** keeps the **remainder** (next sentence fragment) for more tokens.

- The **`while`** can run **multiple times per token** if **`buf`** already holds **two or more** complete sentences (e.g. the model emitted **`"Hello. Fine."`** in one piece).

---

### Length safeguard (`len(buf) > 200`)

```python
if len(buf) > 200:
    chunk = buf.strip()
    buf = ""
    if chunk:
        _play_kokoro(k, voice, chunk)
```

If the model **never** hits **`[.!?]\s+`** (long run-on sentence, unusual formatting), **`buf`** could grow without bound. This branch **forces** one spoken chunk and clears **`buf`**. Playback may start **mid-sentence**  -  acceptable escape hatch for stability.

---

### Final remainder

```python
if buf.strip():
    _play_kokoro(k, voice, buf.strip())
```

After the LLM stream ends, anything left in **`buf`** (last sentence **without** trailing space after the period, or text that never matched the regex) is spoken once so nothing is dropped.

---

### Playback helper (`_play_kokoro`)

```python
audio, sr = k.create(text, voice=voice, speed=1.0)
play_float_mono(audio, int(sr))
```

**`Kokoro.create`** returns **mono float samples** and the sample rate (same idea as in **`synthesize_to_wav`**, but no WAV file). **[`play_float_mono`](../../src/voice_agents/audio/audio_output.py)** applies **DC removal**, **cosine fades**, **trailing silence**, and stable **`sounddevice`** settings  -  **not** raw **`sd.play`**, so chunk boundaries behave like **[`blocking_voice_agent`](../blocking_voice_agent/CODE.md)** playback.

---

### Blocking vs this script (mental model)

| | [`blocking_voice_agent`](../blocking_voice_agent/CODE.md) | **`streaming_voice_agent`** |
|--|--|--|
| LLM call | **`complete`**  -  one blocking generation | **`stream_tokens`**  -  many small **`piece`** strings |
| TTS | One **`synthesize_to_wav`** then **`play_wav_file`** | Many **`Kokoro.create`** + **`play_float_mono`** per sentence |
| When you hear speech | After **full** reply + full WAV | Often **before** the model finishes all tokens (first sentences first) |

---

## Failure modes

Missing models → [download_models.py](../../00_start_here/download_models.py). Empty **`You:`** text → exit. **No audio** → chapter [01](../../01_audio_io/README.md).

---

## Try next

- [`debug_latency`](../debug_latency/CODE.md) to **measure** stage times for comparison.

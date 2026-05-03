# `blocking_voice_agent.py` — code walkthrough

## Purpose

### What “blocking” means here

The script runs the **full voice pipeline in order**, and **each step finishes before the next starts**:

1. **Record** your voice for a fixed number of seconds (default **5**).
2. **Speech-to-text** — Whisper turns the recording into text (**you see `You:`** and the transcript).
3. **LLM** — [`AgentCore.complete`](../../src/voice_agents/agent/agent_core.py) generates the assistant reply (**you see `Assistant:`**).
4. **Text-to-speech** — Kokoro writes **`tmp/blocking_response.wav`**.
5. **Playback** — the WAV plays through your default output device.

Nothing streams “live” during the LLM step: you wait until the **whole** reply exists before TTS runs. That makes debugging easy (same idea as [chapter 00](../../00_start_here/) demo), but **time-to-first-sound** is higher than in [`streaming_voice_agent`](../streaming_voice_agent/CODE.md).

### Files on disk

- **`tmp/blocking_input.wav`** — your microphone capture (debuggable in any player).
- **`tmp/blocking_response.wav`** — synthesized reply.

---

## Run

From the repository root:

```bash
uv run python 05_full_voice_loop/blocking_voice_agent/blocking_voice_agent.py
uv run python 05_full_voice_loop/blocking_voice_agent/blocking_voice_agent.py --seconds 3
```

You get a **Rich** yes/no prompt before recording (`Record Ns?`). Answer **y**, speak when recording runs, then listen for playback.

---

## Dependencies

| Piece | Role |
|-------|------|
| [`record_seconds`](../../src/voice_agents/audio/audio_input.py), [`save_wav`](../../src/voice_agents/audio/audio_input.py) | Capture PCM from default mic; save input WAV. |
| [`transcribe_samples`](../../src/voice_agents/stt/streaming_stt.py) | Whisper **faster-whisper** via **`TranscribeConfig`**. |
| [`AgentCore`](../../src/voice_agents/agent/agent_core.py), [`PromptEngine`](../../src/voice_agents/agent/prompt_engine.py) | Local **GGUF** completion with Qwen chat template. |
| [`TTSConfig`](../../src/voice_agents/tts/streaming_tts.py), [`pick_voice`](../../src/voice_agents/tts/streaming_tts.py), [`synthesize_to_wav`](../../src/voice_agents/tts/streaming_tts.py) | Kokoro → float WAV. |
| [`play_wav_file`](../../src/voice_agents/audio/audio_output.py) | Play WAV through speakers/headphones (wraps **`play_float_mono`**). |

---

## Code walkthrough

### Repository paths and models

```python
ROOT = Path(__file__).resolve().parents[2]
MODELS = ROOT / "models"
WHISPER_ROOT = MODELS / "whisper"
LLM_PATH = MODELS / "llm" / "qwen2.5-0.5b-instruct-q4_k_m.gguf"
KOKORO_MODEL = MODELS / "kokoro" / "kokoro-v1.0.onnx"
KOKORO_VOICES = MODELS / "kokoro" / "voices-v1.0.bin"
OUT_WAV = ROOT / "tmp" / "blocking_response.wav"
```

**`parents[2]`** is the **repository root** (script lives under **`blocking_voice_agent/`**). **`MODELS`** keeps Whisper cache, GGUF, and Kokoro paths in one place. **`OUT_WAV`** is always the same output path each run — it **overwrites** the previous synthesized reply.

---

### CLI: recording length

```python
ap = argparse.ArgumentParser()
ap.add_argument("--seconds", type=float, default=5.0, help="Recording length")
args = ap.parse_args()
```

**`--seconds`** only affects **mic capture** — not STT model size or LLM **`max_tokens`**. Shorter clips reduce wait time but give Whisper less audio context (fine for short questions).

---

### Preflight: files must exist

```python
for p in (LLM_PATH, KOKORO_MODEL, KOKORO_VOICES):
    if not p.exists():
        ...
```

Whisper weights live under **`WHISPER_ROOT`** but are checked indirectly when **`transcribe_samples`** runs; this loop only verifies **LLM + Kokoro** paths up front so you fail fast with a clear message ([download_models.py](../../00_start_here/download_models.py)).

---

### Confirm before recording

```python
if not Confirm.ask(f"Record {args.seconds}s?", default=True):
    raise SystemExit(0)
```

**Rich** asks for **y/n** so you can abort without touching the mic. **`default=True`** means Enter alone accepts the prompt.

---

### Capture and save input audio

```python
audio, sr = record_seconds(args.seconds, config=AudioInputConfig())
save_wav(ROOT / "tmp/blocking_input.wav", audio, sr)
```

[`record_seconds`](../../src/voice_agents/audio/audio_input.py) returns **float32 PCM** and **sample rate** from the **default input device** ([`AudioInputConfig`](../../src/voice_agents/audio/audio_input.py) defaults). [`save_wav`](../../src/voice_agents/audio/audio_input.py) writes **`tmp/blocking_input.wav`** so you can **replay or inspect** what Whisper heard — essential when debugging bad transcripts.

---

### Speech-to-text

```python
stt = TranscribeConfig(download_root=str(WHISPER_ROOT))
text = transcribe_samples(audio, sr, config=stt)
console.print("[bold]You:[/]", text)
```

[`TranscribeConfig`](../../src/voice_agents/stt/streaming_stt.py) points **faster-whisper** at **`models/whisper/`** for downloaded weights. [`transcribe_samples`](../../src/voice_agents/stt/streaming_stt.py) runs ASR on the in-memory buffer (same audio you saved). Whatever string comes back is treated as the **user utterance** for the LLM — there is no separate “intent” layer in this script.

---

### Empty transcript guard

```python
if not text.strip():
    raise SystemExit(0)
```

Silence, noise-only audio, or STT failure may yield **empty** text. The script **exits before** loading **`AgentCore`** so you do not pay LLM startup for a useless turn.

---

### LLM: one blocking completion

```python
reply = AgentCore(model_path=str(LLM_PATH)).complete(
    text, engine=PromptEngine(), max_tokens=256
)
console.print("[bold]Assistant:[/]", reply)
```

- A **new** [`AgentCore`](../../src/voice_agents/agent/agent_core.py) is constructed for this call — simple for teaching (each run is self-contained). In production you would typically **reuse** one instance to avoid reloading the GGUF.

- **[`PromptEngine()`](../../src/voice_agents/agent/prompt_engine.py)** uses the library **default system prompt**; no multi-turn session — **`complete`** still **appends** user/assistant lines to that engine’s memory after the call (harmless for a single shot).

- **`max_tokens=256`** caps reply length; raise it if answers truncate.

[`qwen25_chat_prompt`](../../src/voice_agents/agent/agent_core.py) formatting is applied **inside** **`complete`** — same contract as [chapter 04](../../04_agent_core/).

---

### TTS: Kokoro to WAV

```python
cfg = TTSConfig(str(KOKORO_MODEL), str(KOKORO_VOICES), voice="af_heart")
cfg.voice = pick_voice(cfg, cfg.voice)
synthesize_to_wav(reply, OUT_WAV, config=cfg)
```

[`TTSConfig`](../../src/voice_agents/tts/streaming_tts.py) bundles ONNX path, voices bundle, **`af_heart`** preference, speed, language. [`pick_voice`](../../src/voice_agents/tts/streaming_tts.py) ensures **`cfg.voice`** is an id that exists in the voices file (fallback if **`af_heart`** missing).

[`synthesize_to_wav`](../../src/voice_agents/tts/streaming_tts.py) calls **`Kokoro.create`** once for the **full** reply string and writes **mono float WAV** at Kokoro’s native rate via **soundfile**.

---

### Playback

```python
play_wav_file(OUT_WAV)
```

[`play_wav_file`](../../src/voice_agents/audio/audio_output.py) reads the WAV and calls **`play_float_mono`**: **DC removal**, **cosine fades**, **trailing silence**, and **`sounddevice`** with **`latency="high"`** — same smoothing as [**`streaming_voice_agent`**](../streaming_voice_agent/CODE.md) chunk playback.

---

### Pipeline summary (order matters)

| Step | Function / API | Output |
|------|----------------|--------|
| 1 | [`record_seconds`](../../src/voice_agents/audio/audio_input.py) | PCM + SR |
| 2 | [`save_wav`](../../src/voice_agents/audio/audio_input.py) | **`tmp/blocking_input.wav`** |
| 3 | [`transcribe_samples`](../../src/voice_agents/stt/streaming_stt.py) | **`text`** str |
| 4 | [`AgentCore.complete`](../../src/voice_agents/agent/agent_core.py) | **`reply`** str |
| 5 | [`synthesize_to_wav`](../../src/voice_agents/tts/streaming_tts.py) | **`tmp/blocking_response.wav`** |
| 6 | [`play_wav_file`](../../src/voice_agents/audio/audio_output.py) | speakers |

---

### Compared to [`streaming_voice_agent`](../streaming_voice_agent/CODE.md)

| | **Blocking (this script)** | **Streaming** |
|--|--|--|
| User input | Always **mic** + fixed seconds | **Mic** or **CLI text** |
| LLM | **`complete`** — whole reply at once | **`stream_tokens`** — fragments |
| TTS | One **`synthesize_to_wav`** | Many **`Kokoro.create`** per sentence |
| When speech starts | After **full** pipeline stage 4–5 | Often **during** generation |

---

## Failure modes

- Missing **Whisper / LLM / Kokoro** files → [download_models.py](../../00_start_here/download_models.py).
- **Empty transcript** (silence or noise) → script exits after `You:` with no assistant audio.
- **No sound** → [chapter 01](../../01_audio_io/README.md) output device / mute.

---

## Try next

- [`streaming_voice_agent`](../streaming_voice_agent/CODE.md) for **sentence-level** TTS while tokens stream.
- [`debug_latency`](../debug_latency/CODE.md) for a **timing table** over the same stages.

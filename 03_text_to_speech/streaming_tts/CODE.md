# `streaming_tts.py`  -  code walkthrough

## Purpose

Play speech **as it is synthesized**: **`kokoro_onnx`** exposes **`create_stream`**, an **async** generator that yields audio chunks; this script pushes each chunk to **sounddevice** so you hear output without waiting for the whole utterance to finish - closer to the [chapter 00](../../00_start_here/) agent than writing one giant WAV.

Contrast with [`basic_tts`](../basic_tts/CODE.md), which calls the library helper that writes a **single file**.

## Run

```bash
uv run python 03_text_to_speech/streaming_tts/streaming_tts.py
uv run python 03_text_to_speech/streaming_tts/streaming_tts.py Your words here.
```

## Dependencies

| Piece | Role |
|-------|------|
| **`kokoro_onnx.Kokoro`** | Same ONNX + voices as elsewhere; here you call **`create_stream`**. |
| **`asyncio`** | Drives **`async for`** over the stream. |
| **`sounddevice.play` / `wait`** | Plays each float32 chunk at **`SAMPLE_RATE`** from Kokoro (see package docs). |

[`streaming_tts.py`](../../src/voice_agents/tts/streaming_tts.py) in **`voice_agents`** focuses on **WAV + optional shared `Kokoro`** for sentence loops; this tutorial script uses the **raw API** to show streaming explicitly.

## Code walkthrough

### Paths

```python
ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / "models" / "kokoro" / "kokoro-v1.0.onnx"
VOICES = ROOT / "models" / "kokoro" / "voices-v1.0.bin"
```

### Async playback loop

```python
async def play_stream(text: str, voice: str) -> None:
    k = Kokoro(str(MODEL), str(VOICES))
    if voice not in k.get_voices():
        voice = k.get_voices()[0]
    gen = k.create_stream(text, voice=voice, speed=1.0, lang="en-us")
    async for chunk, _sr in gen:
        x = np.asarray(chunk, dtype=np.float32).reshape(-1)
        sd.play(x, SAMPLE_RATE)
        sd.wait()
```

Each **`chunk`** is a short slice of PCM; **`sd.wait()`** blocks until that slice finishes playing so chunks stay ordered.

### Entry

```python
asyncio.run(play_stream(text, voice))
```

## Failure modes

No ONNX file, or **no audio output** (wrong output device / muted) - see [Troubleshooting](../README.md#troubleshooting) and [chapter 01 audio](../../01_audio_io/README.md#troubleshooting).

## Try next

- Compare perceived latency with [`latency_optimization`](../latency_optimization/CODE.md) RTF numbers.

# `basic_tts.py`  -  code walkthrough

## Purpose

Synthesize **one utterance** with Kokoro and write **mono float WAV** to **`tmp/tts_basic.wav`** using [`synthesize_to_wav`](../../src/voice_agents/tts/streaming_tts.py). Same stack as [chapter 00](../../00_start_here/).

## Run

From the repository root:

```bash
uv run python 03_text_to_speech/basic_tts/basic_tts.py
echo "Hello from the pipe." | uv run python 03_text_to_speech/basic_tts/basic_tts.py
```

With **no pipe**, stdin is a TTY and the script uses a short **default sentence**. To speak **custom text**, pipe that text on **stdin** (one command as in the second line above).

**`Synthesizing:`** prints the exact string sent to Kokoro.

## Dependencies

| Symbol | Role |
|--------|------|
| [`TTSConfig`](../../src/voice_agents/tts/streaming_tts.py) | ONNX + voices paths, default **`af_heart`**, speed, language. |
| [`pick_voice`](../../src/voice_agents/tts/streaming_tts.py) | Picks a valid voice id from the bundle. |
| [`synthesize_to_wav`](../../src/voice_agents/tts/streaming_tts.py) | **`Kokoro.create`** → float samples → **soundfile** at Kokoro’s rate (~24 kHz). |

## Code walkthrough

### Paths

```python
ROOT = Path(__file__).resolve().parents[2]
MODEL = ROOT / "models" / "kokoro" / "kokoro-v1.0.onnx"
VOICES = ROOT / "models" / "kokoro" / "voices-v1.0.bin"
OUT = ROOT / "tmp" / "tts_basic.wav"
```

**`parents[2]`** is the **repository root** (script lives under **`basic_tts/`**).

### Phrase

```python
def _phrase() -> str:
    if not sys.stdin.isatty():
        s = sys.stdin.read().strip()
        if s:
            return s
    return _DEFAULT
```

### Synthesize

```python
text = _phrase()
cfg = TTSConfig(model_path=str(MODEL), voices_path=str(VOICES), voice="af_heart")
cfg.voice = pick_voice(cfg, cfg.voice)
synthesize_to_wav(text, OUT, config=cfg)
```

For **chunked playback** without a single WAV, see [`streaming_tts/CODE.md`](../streaming_tts/CODE.md).

## Failure modes

Missing models or **`tmp/`** not writable → chapter [README](../README.md#troubleshooting).

## Try next

- Open **`tmp/tts_basic.wav`**, then try [`voice_profiles`](../voice_profiles/CODE.md).

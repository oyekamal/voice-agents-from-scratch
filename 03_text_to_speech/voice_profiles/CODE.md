# `voice_profiles.py`  -  code walkthrough

## Purpose

Map **friendly profile names** (`default`, `calm`, `direct`) to **Kokoro voice ids** and **speed** overrides. Other scripts can call **`resolve(config, profile)`** so persona lives in one place - similar to how [08_personality](../../08_personality/) will layer behaviour later.

Running as **`__main__`** prints the resolved voice + speed for each profile (sanity check without synthesis).

## Run

```bash
uv run python 03_text_to_speech/voice_profiles/voice_profiles.py
```

## Dependencies

| Piece | Role |
|-------|------|
| `VoiceProfile` dataclass | **`name`**, **`kokoro_voice`**, **`speed`**. |
| **`PROFILES`** dict | Edit these strings to taste - voice ids must exist in your **`voices-v1.0.bin`**. |
| **`resolve`** | Uses [`list_voices`](../../src/voice_agents/tts/streaming_tts.py) to validate ids and builds a fresh [`TTSConfig`](../../src/voice_agents/tts/streaming_tts.py). |

## Code walkthrough

### Building `TTSConfig` from a profile

```python
def resolve(config: TTSConfig, profile: str) -> TTSConfig:
    available = set(list_voices(config))
    p = PROFILES.get(profile, PROFILES["default"])
    voice = p.kokoro_voice if p.kokoro_voice in available else next(iter(available))
    return TTSConfig(
        model_path=config.model_path,
        voices_path=config.voices_path,
        voice=voice,
        speed=p.speed,
        lang=config.lang,
    )
```

If the chosen Kokoro id is missing, **`resolve`** falls back to **`next(iter(available))`** so the script never passes an unknown voice string.

### `__main__` demo

```python
ROOT = Path(__file__).resolve().parents[2]
cfg = TTSConfig(
    model_path=str(ROOT / "models/kokoro/kokoro-v1.0.onnx"),
    voices_path=str(ROOT / "models/kokoro/voices-v1.0.bin"),
)
for name in PROFILES:
    r = resolve(cfg, name)
    print(name, "→", r.voice, r.speed)
```

**`parents[2]`** keeps paths aligned with the nested folder layout.

Wire **`resolve`** into [`basic_tts`](../basic_tts/CODE.md) by replacing manual **`TTSConfig`** construction if you want profiles end-to-end.

## Failure modes

Empty voice list or wrong model paths → [Troubleshooting](../README.md#troubleshooting).

## Try next

- Add a new key to **`PROFILES`**, then **`uv run`** again to confirm it resolves.

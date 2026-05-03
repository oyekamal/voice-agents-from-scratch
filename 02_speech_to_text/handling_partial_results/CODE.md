# `handling_partial_results.py` — code walkthrough

## Purpose

Show how **faster-whisper** exposes **segments**: each piece has **`start`**, **`end`**, and **`text`**. That is closer to how captions and partial UI updates work than one merged string.

The tutorials often call [`transcribe_file`](../../src/voice_agents/stt/streaming_stt.py), which **joins** segments for convenience. This script imports **`WhisperModel`** directly so you can **iterate** `segments` and print timestamps yourself.

## Run

```bash
uv run python 02_speech_to_text/handling_partial_results/handling_partial_results.py
uv run python 02_speech_to_text/handling_partial_results/handling_partial_results.py path/to.wav
```

Default WAV is **`tmp/recorded.wav`** at the repo root (same convention as [`transcribe_once`](../transcribe_once/CODE.md)).

**What you should see** — often a **ctranslate2** log line first, then one line per segment (green timestamps in the terminal). Example:

```text
[2026-05-02 20:17:17.425] [ctranslate2] [thread …] [warning] The compute type inferred from the saved model is float16, but the target device or backend do not support efficient float16 computation. The model weights have been automatically converted to use the float32 compute type instead.
0.00–3.00s Hello, my name is…
```

The **timestamp line** is the script’s real output. The **warning** is explained below.

## Dependencies

| Symbol | Role |
|--------|------|
| [`WhisperModel`](https://github.com/SYSTRAN/faster-whisper) (`tiny.en`) | Loaded with **`download_root`** under **`models/whisper`**. |
| **`soundfile.read`** | Decodes WAV (or other formats **soundfile** supports) to float samples. |
| **`model.transcribe(audio, …)`** | Returns **`segments`** (generator) plus **`info`**; this script only uses **`segments`**. |

[`streaming_stt.py`](../../src/voice_agents/stt/streaming_stt.py) wraps the same model API but merges text—compare implementations while reading.

### ctranslate2 warning (float16 vs float32)

**faster-whisper** uses **CTranslate2** under the hood. On many **CPU-only** or **no efficient FP16** setups, the library may print a **warning** that the model was stored as **float16** but the runtime will use **float32** instead.

- **It is expected** and **safe to ignore** for this tutorial: you still get a valid transcript.
- **Why it appears** — the backend picks a **compute type** the current device can run reliably; automatic conversion avoids silent broken math on hardware that does not like FP16.
- **If you want to tune later** — you can pass explicit options to [`WhisperModel`](https://github.com/SYSTRAN/faster-whisper) (e.g. `compute_type`, `device`) to match your machine; [`TranscribeConfig`](../../src/voice_agents/stt/streaming_stt.py) in other scripts defaults to **`int8`** for speed/size tradeoffs on CPU.

## Code walkthrough

### Paths

```python
ROOT = Path(__file__).resolve().parents[2]
WHISPER_ROOT = ROOT / "models" / "whisper"
```

**`parents[2]`** keeps **`ROOT`** on the repository root so **`ROOT / tmp / recorded.wav`** and **`models/whisper`** resolve correctly from this nested folder.

### Load audio from disk

```python
audio, sr = sf.read(wav, dtype="float32")
audio = np.squeeze(audio)
```

**`squeeze`** drops a singleton channel dimension so mono becomes shape **`(N,)`**, which **`WhisperModel.transcribe`** expects as a numpy array.

### Model and transcribe

```python
model = WhisperModel("tiny.en", download_root=str(WHISPER_ROOT))
segments, _ = model.transcribe(audio, language="en", beam_size=5)
```

**`beam_size`** matches the helpers in [`streaming_stt.py`](../../src/voice_agents/stt/streaming_stt.py). The second return value (**info**) is intentionally ignored here.

### Iterate segments

```python
for seg in segments:
    console.print(f"[green]{seg.start:.2f}–{seg.end:.2f}s[/] {seg.text.strip()}")
```

Each **`seg`** covers part of the timeline—useful for subtitles, diarization-style hooks later, or debugging **where** Whisper heard something.

### Comparison with `transcribe_once`

| Script | API | Output |
|--------|-----|--------|
| [`transcribe_once`](../transcribe_once/CODE.md) | [`transcribe_file`](../../src/voice_agents/stt/streaming_stt.py) | Single merged transcript |
| **This script** | **`WhisperModel.transcribe`** + loop | Lines with **time ranges** |

## Failure modes

Missing WAV or model issues → [Troubleshooting](../README.md#troubleshooting).

## Try next

- Compare segment boundaries when you change speaking pace or add long pauses inside `tmp/recorded.wav`.

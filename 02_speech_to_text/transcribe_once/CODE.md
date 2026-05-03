# `transcribe_once.py`  -  code walkthrough

## Purpose

Transcribe a **whole WAV file** in one shot using the shared helper [`transcribe_file`](../../src/voice_agents/stt/streaming_stt.py). This is the simplest STT entry point: load audio from disk, run Whisper once, print a single transcript string.

## Run

From the repository root (default input is `tmp/recorded.wav` from chapter 01):

```bash
uv run python 02_speech_to_text/transcribe_once/transcribe_once.py
uv run python 02_speech_to_text/transcribe_once/transcribe_once.py path/to/your.wav
```

## Dependencies

| Symbol | Role |
|--------|------|
| [`TranscribeConfig`](../../src/voice_agents/stt/streaming_stt.py) | Model name (`tiny.en` by default), device, `compute_type`, `download_root`, language. |
| [`transcribe_file`](../../src/voice_agents/stt/streaming_stt.py) | Loads [`faster-whisper`](https://github.com/SYSTRAN/faster-whisper) internally, runs `model.transcribe` on the file path, joins segment texts into one string. |

Weights resolve under **`ROOT / models / whisper`** where **`ROOT`** is the repo root (two levels up from this file).

## Code walkthrough

### STT (speech-to-text)

**STT** means **speech-to-text**: turning **spoken audio** (PCM in a WAV file) into **written text**. It is the inverse direction of TTS (text-to-speech). In this repo, STT lives under the **`voice_agents.stt`** package - see [`streaming_stt.py`](../../src/voice_agents/stt/streaming_stt.py).

This script does **non-streaming** STT on a **whole file**: read the file path, run the Whisper model once over that audio, get back **one string**. That matches how many agents first wire up STT (“give me the words from this recording”) before adding live chunking or partial results.

### Repo paths and config

```python
ROOT = Path(__file__).resolve().parents[2]
WHISPER_ROOT = ROOT / "models" / "whisper"

cfg = TranscribeConfig(download_root=str(WHISPER_ROOT))
```

**`parents[2]`** jumps from `transcribe_once/transcribe_once.py` → `02_speech_to_text/` → **repository root**, so `models/whisper` stays stable after nesting this script in a subfolder.

### CLI and default WAV

```python
wav = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "tmp" / "recorded.wav"
```

No argument → use the clip from [`record_to_file`](../../01_audio_io/record_to_file/record_to_file.py). Pass any SoundFile-supported path otherwise.

### Transcribe and print

```python
text = transcribe_file(wav, config=cfg)
console.print("[bold]Transcript:[/]", text)
```

[`transcribe_file`](../../src/voice_agents/stt/streaming_stt.py) merges all Whisper **segments** into one space-separated string - you do **not** see per-segment timestamps here (see [`handling_partial_results`](../handling_partial_results/CODE.md)).

## Failure modes

Missing file → friendly error suggesting chapter 01 recording. Model/download issues → chapter [README](../README.md#troubleshooting).

## Try next

- Run [`handling_partial_results`](../handling_partial_results/CODE.md) on the same WAV to see **timestamped segments**.

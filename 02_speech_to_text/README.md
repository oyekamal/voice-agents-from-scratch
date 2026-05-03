# Chapter 02 - Speech to text

This chapter turns **audio into text** using **Whisper** via [`faster-whisper`](https://github.com/SYSTRAN/faster-whisper), entirely **local** - no cloud API. You already moved sound between mic and files in [chapter 01](../01_audio_io/); here those PCM buffers become transcripts that later chapters feed into an LLM.

You will use helpers in **`voice_agents.stt`** ([`streaming_stt.py`](../src/voice_agents/stt/streaming_stt.py)) plus one script that calls **`faster-whisper`** directly to expose **timestamped segments**.

---

## Table of Contents

- [At a glance](#at-a-glance)
- [What this folder is for](#what-this-folder-is-for)
- [PCM in brief](#pcm-in-brief)
- [Prerequisites](#prerequisites)
- [Models](#models)
- [Suggested order to run the scripts](#suggested-order-to-run-the-scripts)
- [What each example does](#what-each-example-does)
- [Troubleshooting](#troubleshooting)
- [How this ties to the library](#how-this-ties-to-the-library)
- [Previous](#previous)
- [Next](#next)

---

## At a glance

| | |
|---|---|
| **Dependencies** | `uv sync` plus Whisper weights under **`models/whisper/`** (see [Models](#models)). Optional: **`tmp/recorded.wav`** from [chapter 01](../01_audio_io/) for file-based scripts. |
| **Done looks like** | You see a **full transcript** from a WAV, **timestamped lines** per segment, or a **repeating mic loop** that prints timing + text for each window. |

---

## What this folder is for

| What you practice | Why it matters later |
|-------------------|----------------------|
| **Transcribe a file** | Same pattern as “user recorded → STT → agent”: one shot, one string. |
| **Windowed mic transcription** | Rough sketch of **continuous** listening (chunk → transcribe → repeat); real pipelines add overlap, VAD, and streaming decoders. |
| **Segments with timestamps** | Captions, partial UIs, and debugging **where** in time Whisper placed words - more structure than a single merged string. |

---

## PCM in brief

**PCM** (pulse-code modulation) is the usual way **digital audio** represents sound: an analog waveform is **sampled** many times per second, and each sample is stored as a **number** (air pressure or voltage quantized to a discrete step).

- **Sample rate**  -  How many samples fit in one second (hertz). Chapter scripts often use **16 kHz** (16,000 samples per second), which is enough for speech.
- **Samples in memory**  -  In Python you mostly see PCM as a **NumPy array** of floats or integers (`float32` after decode is common here).
- **WAV files**  -  A `.wav` file is typically **PCM audio inside a simple container** (plus metadata). Decoding with **soundfile** or letting **faster-whisper** read the path yields PCM for Whisper.
- **What Whisper sees**  -  The model does not receive analog sound; it receives those **numeric samples** (or an equivalent tensor). Garbage in (silence, clipping, wrong mic) hurts transcripts just like bad lighting hurts vision models.

Chapter 01 moved PCM between mic, memory, and disk; this chapter **interprets** that PCM as text.

---

## Prerequisites

From the repo root (after `uv sync`):

1. **Download models**  -  Whisper (and other) weights are pulled into **`models/`** by [00_start_here/download_models.py](../00_start_here/download_models.py). You need at least **`tiny.en`** under **`models/whisper/`** for these scripts.
2. **Optional WAV**  -  Record **`tmp/recorded.wav`** with [`01_audio_io/record_to_file/record_to_file.py`](../01_audio_io/record_to_file/record_to_file.py) so the default paths in `transcribe_once` and `handling_partial_results` work without arguments.

Run examples with:

```bash
uv run python 02_speech_to_text/<folder>/<script>.py
```

---

## Models

| Setting | Value |
|---------|--------|
| **Default model** | **`tiny.en`** (English, small, fast on CPU - matches [`TranscribeConfig`](../src/voice_agents/stt/streaming_stt.py)) |
| **On disk** | Cached under **`models/whisper/`** (see [`WHISPER_ROOT`](../src/voice_agents/stt/streaming_stt.py) usage via `download_root`) |
| **Rough size** | On the order of **~75 MB** for `tiny.en` (see [00_start_here README](../00_start_here/README.md) model table) |

First transcription pays **load + compile** cost; later runs in the same process are faster.

---

## Suggested order to run the scripts

Shortest path first: file → segments → live loop.

| Order | Script | One-line purpose | Success check |
|------:|--------|------------------|----------------|
| 1 | [`transcribe_once/transcribe_once.py`](./transcribe_once/transcribe_once.py) | One WAV → **one transcript string**. | **`Transcript:`** line with your spoken words. |
| 2 | [`handling_partial_results/handling_partial_results.py`](./handling_partial_results/handling_partial_results.py) | Same WAV → **lines with start–end times**. | Green **timestamp ranges** plus text per segment. |
| 3 | [`streaming_transcription/streaming_transcription.py`](./streaming_transcription/streaming_transcription.py) | **Mic** → 4 s windows → transcript each chunk until Ctrl+C. | Repeating lines **`Xs - …`** with partial text; **Ctrl+C** stops cleanly. |

---

## What each example does

### `transcribe_once/transcribe_once.py`

**Source:** [`transcribe_once.py`](./transcribe_once/transcribe_once.py)  -  **Learning deeper:** [`CODE.md`](./transcribe_once/CODE.md)

Uses [`transcribe_file`](../src/voice_agents/stt/streaming_stt.py) with [`TranscribeConfig(download_root=…)`](../src/voice_agents/stt/streaming_stt.py) pointing at **`models/whisper`**. Defaults to **`tmp/recorded.wav`** at the repo root if you do not pass a path.

```bash
uv run python 02_speech_to_text/transcribe_once/transcribe_once.py
uv run python 02_speech_to_text/transcribe_once/transcribe_once.py path/to/audio.wav
```

---

### `handling_partial_results/handling_partial_results.py`

**Source:** [`handling_partial_results.py`](./handling_partial_results/handling_partial_results.py)  -  **Learning deeper:** [`CODE.md`](./handling_partial_results/CODE.md)

Loads **`WhisperModel`** directly, reads the WAV with **soundfile**, runs **`model.transcribe`**, then **prints each segment** with **`start`**–**`end`** seconds. Same default WAV as above.

```bash
uv run python 02_speech_to_text/handling_partial_results/handling_partial_results.py
uv run python 02_speech_to_text/handling_partial_results/handling_partial_results.py path/to/audio.wav
```

---

### `streaming_transcription/streaming_transcription.py`

**Source:** [`streaming_transcription.py`](./streaming_transcription/streaming_transcription.py)  -  **Learning deeper:** [`CODE.md`](./streaming_transcription/CODE.md)

Records **`WINDOW_S` (4 s)** chunks from the default mic at **16 kHz** using **`sounddevice.rec`**, then **[`transcribe_samples`](../src/voice_agents/stt/streaming_stt.py)** on each buffer. Prints inference time and text in a loop.

This is a **windowed live demo**, not full streaming ASR inside Whisper: simple to read, easy to experiment with window length.

```bash
uv run python 02_speech_to_text/streaming_transcription/streaming_transcription.py
```

Stop with **Ctrl+C**.

---

## Troubleshooting

- **Missing WAV**  -  Record first or pass an explicit path. Error text names [`01_audio_io/record_to_file/record_to_file.py`](../01_audio_io/record_to_file/record_to_file.py).
- **First run slow**  -  Model load + optional download; wait once, then retries are faster.
- **`(silence)` every line in the streaming script**  -  Wrong or muted mic, or gain too low; fix defaults and permissions ([chapter 01 audio troubleshooting](../01_audio_io/README.md#troubleshooting)).
- **Empty transcript on a WAV**  -  Near-silent file, wrong sample rate path, or unsupported format - confirm the file plays in another tool.
- **Download / disk errors**  -  Ensure **`models/whisper/`** is writable and you ran **`download_models`** from **00_start_here**.
- **ctranslate2 warning (float16 → float32)** — Common when running Whisper on **CPU** (or without efficient FP16): the runtime uses **float32** instead of half precision. **Harmless** for learning; see [`handling_partial_results/CODE.md`](./handling_partial_results/CODE.md#ctranslate2-warning-float16-vs-float32).

---

## How this ties to the library

The chapter mostly uses **`voice_agents.stt`**:

- **[`TranscribeConfig`](../src/voice_agents/stt/streaming_stt.py)**  -  Model id, device, compute type, `download_root`, language.
- **[`transcribe_file`](../src/voice_agents/stt/streaming_stt.py)**  -  Path in → merged transcript string (used by **`transcribe_once`**).
- **[`transcribe_samples`](../src/voice_agents/stt/streaming_stt.py)**  -  NumPy float audio + sample rate → merged string (used by **`streaming_transcription`**).

**`handling_partial_results`** bypasses those wrappers so you can iterate **`segments`** from **`faster-whisper`** directly - compare with how [`transcribe_file`](../src/voice_agents/stt/streaming_stt.py) joins segment text internally.

---

## Previous

[Chapter 01 - Audio I/O](../01_audio_io/README.md)  -  capture and playback; produce **`tmp/recorded.wav`** for this chapter.

---

## Next

[Chapter 03 - Text to speech](../03_text_to_speech/README.md): synthesize replies as audio with Kokoro.

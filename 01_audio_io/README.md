# Chapter 01 - Audio I/O

This chapter is the **foundation for everything downstream**: speech-to-text, agents, and playback all assume you can move **sound between the microphone, your code, and the speakers** reliably. Here you practice capturing audio, saving it, streaming it in small blocks (how real-time systems work), and applying a toy **voice-activity** rule so you can tell speech-like audio from silence.

You will use **`sounddevice`** (PortAudio) for capture and playback and the shared helpers in **`src/voice_agents/audio/`** (`record_seconds`, `save_wav`, `play_float_mono`). Nothing here calls Whisper or an LLM - that starts in [chapter 02](../02_speech_to_text/).

---

## Table of Contents

- [At a glance](#at-a-glance)
- [What this folder is for](#what-this-folder-is-for)
- [Prerequisites](#prerequisites)
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
| **Dependencies** | Python deps from `uv sync` only - **no Whisper or model downloads** for this chapter. |
| **Done looks like** | You **hear** a test tone from the speakers. When you speak, **printed numbers or bars move** so you know the microphone is working. A **recording file** appears under `tmp/`. The streaming demos show a **loudness bar** that reacts to your voice, and the last script **labels each moment as speech-like or quiet** - the same idea voice-activity tools build on later. |

---

## What this folder is for

This chapter is only about **getting sound into and out of Python reliably**. You do not need to understand WAV internals, “samples,” or digital signal processing yet.

| What you practice | Why it matters later |
|-------------------|----------------------|
| **Play sound from Python** | You need to hear **computer-generated speech** when the agent replies, and you need a quick way to check volume and routing. |
| **Record a few seconds** | The full voice agent records your voice the same way (same helper under the hood). |
| **Read the microphone in short, repeated slices** | Later chapters that **listen in real time** (speech-to-text, voice activity) work on **many short pieces of audio in a row**, not one enormous recording held in memory. |
| **See how loud each slice is** | A crude “how loud is this slice?” check is the first step toward **voice activity detection** - telling speech from silence - which you refine in chapter 06. |

---

## Prerequisites

From the repo root (after `uv sync`):

- Microphone and speakers or headphones allowed by the OS.
- Optional: complete [00_start_here](../00_start_here/) so models and `uv` are set up; this chapter only needs Python deps, not Whisper weights.

Run examples with:

```bash
uv run python 01_audio_io/<folder>/<script>.py
```

---

## Suggested order to run the scripts

The list below is the **recommended learning order**: shortest checks first, then building complexity. You can run any script on its own if you already know the basics.

| Order | Script | One-line purpose | Success check |
|------:|--------|------------------|----------------|
| 1 | [`speaker_output/speaker_output.py`](./speaker_output/speaker_output.py) | Verify **output** path (tone or WAV). | You **hear** the tone or the WAV plays. |
| 2 | [`mic_input/mic_input.py`](./mic_input/mic_input.py) | **Blocking** mic capture + numeric levels. | **Peak/RMS non-zero** while you speak (not stuck at 0). |
| 3 | [`record_to_file/record_to_file.py`](./record_to_file/record_to_file.py) | Record and **save** a WAV under `tmp/`. | **`tmp/recorded.wav`** appears at the repo root. |
| 4 | [`stream_basics/stream_basics.py`](./stream_basics/stream_basics.py) | **Streaming** mic + live RMS meter (~8 s). | **RMS bar moves** when you speak. |
| 5 | [`vad_debug/vad_debug.py`](./vad_debug/vad_debug.py) | Per-block **speech vs silence** using a fixed RMS threshold (~6 s). | Labels **flip between SPEECH and silence** with your voice. |

---

## What each example does

### `speaker_output/speaker_output.py`

**Source:** [`speaker_output.py`](./speaker_output/speaker_output.py)  -  **Learning deeper:** [`CODE.md`](./speaker_output/CODE.md)

- **Default:** plays a short **440 Hz** sine tone at 16 kHz so you can confirm speakers/levels.
- **With an argument:** plays an existing WAV file through the same playback helper used elsewhere in the repo.

```bash
uv run python 01_audio_io/speaker_output/speaker_output.py
uv run python 01_audio_io/speaker_output/speaker_output.py path/to/file.wav
```

Use this first if you are unsure whether output routing or volume is wrong before debugging the microphone.

---

### `mic_input/mic_input.py`

**Source:** [`mic_input.py`](./mic_input/mic_input.py)  -  **Learning deeper:** [`CODE.md`](./mic_input/CODE.md)

Records **3 seconds** from the default input device using `record_seconds` (mono, **16 kHz** by explicit config). Prints sample rate, sample count, **peak**, and **RMS** so you can see whether the mic is live and how loud you are.

```bash
uv run python 01_audio_io/mic_input/mic_input.py
```

---

### `record_to_file/record_to_file.py`

**Source:** [`record_to_file.py`](./record_to_file/record_to_file.py)  -  **Learning deeper:** [`CODE.md`](./record_to_file/CODE.md)

Records for a chosen duration (default **3 seconds**) and writes **`tmp/recorded.wav`** at the project root (mono, 16 kHz via `AudioInputConfig` defaults). Useful to capture a clip you can open in another tool or feed manually into later chapters.

```bash
uv run python 01_audio_io/record_to_file/record_to_file.py       # 3 s
uv run python 01_audio_io/record_to_file/record_to_file.py 5      # 5 s
```

---

### `stream_basics/stream_basics.py`

**Source:** [`stream_basics.py`](./stream_basics/stream_basics.py)  -  **Learning deeper:** [`CODE.md`](./stream_basics/CODE.md)

Opens an **`InputStream`** with a callback that runs every **1024 samples** (~64 ms at 16 kHz). It prints a live **RMS** bar for **8 seconds**  -  no transcription, just proof that streaming capture works and how loud the signal is block-by-block.

```bash
uv run python 01_audio_io/stream_basics/stream_basics.py
```

Stop early with **Ctrl+C** if needed.

---

### `vad_debug/vad_debug.py`

**Source:** [`vad_debug.py`](./vad_debug/vad_debug.py)  -  **Learning deeper:** [`CODE.md`](./vad_debug/CODE.md)

Same streaming setup as `stream_basics.py`, but each block is labeled **`SPEECH`** or **`silence`** by comparing RMS to a constant **`THRESH`** (default `0.015` in the script). Runs for **6 seconds**. This is a **debug toy**, not production VAD: tweak `THRESH` if everything reads as silence or everything reads as speech.

```bash
uv run python 01_audio_io/vad_debug/vad_debug.py
```

---

## Troubleshooting

The usual failure mode in this chapter is a **wrong or blocked audio device** (Bluetooth routing, corporate docks, or OS permissions). PortAudio may report **“Error querying device”** or streams may open but stay silent.

- **Permissions:** On macOS, Windows, and Linux, allow the **microphone** (and playback if prompted) for your terminal app, IDE, or `python` in **Privacy** / **Security** settings.
- **Default device:** Set the mic and speakers you intend as the **system default** input and output; Bluetooth sometimes grabs the wrong profile until you reconnect or pick the headset explicitly.
- **List devices:** From the repo root, run `uv run python -m sounddevice` to print devices and default indices (see [sounddevice](https://python-sounddevice.readthedocs.io/) / PortAudio). Use that to confirm Python sees the same hardware you expect.
- **Silent vs crash:** **Zero RMS, flat bars, or all silence** usually means wrong input, muted mic, or denied permission - fix routing and levels first. **Errors or hangs when opening a stream** often mean an invalid or busy device - try another default, another sample rate, or reconnect USB audio.

---

## How this ties to the library

The tutorials call into **`voice_agents.audio`**:

- **[`record_seconds`](../src/voice_agents/audio/audio_input.py)** / **[`AudioInputConfig`](../src/voice_agents/audio/audio_input.py)**  -  blocking capture used in [`mic_input/mic_input.py`](./mic_input/mic_input.py) and [`record_to_file/record_to_file.py`](./record_to_file/record_to_file.py).
- **[`save_wav`](../src/voice_agents/audio/audio_input.py)**  -  write float32 mono PCM to WAV ([`record_to_file/record_to_file.py`](./record_to_file/record_to_file.py)).
- **[`play_float_mono`](../src/voice_agents/audio/audio_output.py)**  -  play a numpy array ([`speaker_output/speaker_output.py`](./speaker_output/speaker_output.py)).

Streaming examples use **`sounddevice.InputStream`** directly so you can see callbacks and block sizes without hiding details.

---

## Previous

[00_start_here](../00_start_here/README.md)  -  environment setup (`uv`, optional models). This chapter needs only Python dependencies.

---

## Next

[Chapter 02 - Speech-to-text](../02_speech_to_text/README.md): turn these PCM buffers into text with Whisper.

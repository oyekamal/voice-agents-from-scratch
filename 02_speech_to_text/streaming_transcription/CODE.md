# `streaming_transcription.py`  -  code walkthrough

## Purpose

Demonstrate **repeated transcription from the live microphone**: record a fixed-length window, run Whisper on that chunk, print latency and text, repeat until **Ctrl+C**.

This is **not** Whisper’s internal streaming decoder - it is a **windowed loop** (`sounddevice` capture → [`transcribe_samples`](../../src/voice_agents/stt/streaming_stt.py)). Production streaming ASR uses overlapping buffers and partial hypotheses; this script stays small so you see the control flow clearly.

## Run

```bash
uv run python 02_speech_to_text/streaming_transcription/streaming_transcription.py
```

Press **Ctrl+C** to exit the loop.

## Dependencies

| Piece | Role |
|-------|------|
| [`sounddevice`](https://python-sounddevice.readthedocs.io/) **`sd.rec` / `sd.wait`** | Blocking capture of **`WINDOW_S`** seconds at **`SR`** Hz, mono float32. |
| [`transcribe_samples`](../../src/voice_agents/stt/streaming_stt.py) | Same Whisper stack as file transcription, but audio lives in a NumPy array. |
| [`TranscribeConfig`](../../src/voice_agents/stt/streaming_stt.py) | `download_root` points at **`ROOT / models / whisper`**. |

## Code walkthrough

### ASR (automatic speech recognition)

**ASR** means **automatic speech recognition**: the **task** of mapping **spoken audio** to **text**. It is the same problem people often call [**STT** (speech-to-text)](../transcribe_once/CODE.md#stt-speech-to-text) - papers and benchmarks usually say “ASR”; application code often says “STT.” Whisper is an **ASR model**; **[`transcribe_samples`](../../src/voice_agents/stt/streaming_stt.py)** is the **ASR inference** step for one chunk of PCM in memory.

In **production “streaming ASR”**, the system usually emits **partial transcripts** while audio still arrives (different architectures: neural streaming, chunked endpoints, etc.). **This script** does **windowed ASR** instead: wait until **`WINDOW_S`** seconds are captured, run **one full Whisper pass** on that buffer, print the result, then **start the next window**. So each loop iteration is **batch ASR on a short clip**, repeated forever - not Whisper’s built-in incremental streaming mode. That trade-off keeps the script easy to read while still demonstrating **continuous mic → repeated transcripts**.

### Tunables

```python
ROOT = Path(__file__).resolve().parents[2]
WHISPER_ROOT = ROOT / "models" / "whisper"
SR = 16_000
WINDOW_S = 4.0
```

**`ROOT`** uses **`parents[2]`** so `models/` stays at the repo root. **`WINDOW_S`** - length of each mic slice before transcription; increase for more context, decrease for quicker turns (with worse boundary behaviour).

### Capture loop

```python
frames = int(WINDOW_S * SR)
buf = np.zeros(frames, dtype=np.float32)
while True:
    audio = sd.rec(frames, samplerate=SR, channels=1, dtype="float32")
    sd.wait()
    buf[:] = audio.reshape(-1)
```

**`sd.rec`** schedules **`frames`** samples; **`sd.wait()`** blocks until the buffer is full - classic blocking capture, same family as chapter 01, longer window than `stream_basics`.

### Transcribe and report

```python
    t0 = time.perf_counter()
    text = transcribe_samples(buf, SR, config=cfg)
    dt = time.perf_counter() - t0
    console.print(f"[cyan]{dt:.2f}s[/] - {text or '(silence)'}")
```

**`dt`** is Whisper inference time for that window (model may already be warm after the first iteration). Empty **`text`** prints **`(silence)`** - quiet rooms or mistaken input device.

### Interrupt

```python
except KeyboardInterrupt:
    console.print("\nStopped.")
```

Clean exit when you press **Ctrl+C**.

For **segment timestamps** on a file instead of a live loop, see [`handling_partial_results/CODE.md`](../handling_partial_results/CODE.md).

## Failure modes

Silent **`(silence)`** every window → check mic default and permissions ([chapter 01 audio troubleshooting](../../01_audio_io/README.md#troubleshooting)). First window slow → model cold start. See also [chapter README](../README.md#troubleshooting).

## Try next

- Adjust **`WINDOW_S`** (e.g. `3.0` vs `5.0`) and observe latency vs transcript quality.

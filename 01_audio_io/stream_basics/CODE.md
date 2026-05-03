# `stream_basics.py`  -  code walkthrough

## Purpose

Show **streaming** capture: the microphone is read in repeated **small blocks** inside a callback, while the main thread sleeps. This mirrors how real-time STT/VAD pipelines see audio - as a sequence of chunks, not one giant buffer.

## Run

```bash
uv run python 01_audio_io/stream_basics/stream_basics.py
```

Press **Ctrl+C** to stop early if needed (interrupt unwinds the `InputStream` context).

## Dependencies

| Piece | Role |
|-------|------|
| `sounddevice.InputStream` | PortAudio wrapper; invokes `callback` every `blocksize` frames. |
| `numpy` | RMS and reshaping (`reshape(-1)` flattens mono frames). |

No `voice_agents` imports - deliberately low-level so you see callbacks.

## Code walkthrough

### Tunables: sample rate and block size

```python
SR = 16_000
BLOCK = 1024
```

At **16 kHz**, **1024 samples** per callback ⇒ \(1024 / 16000 \approx 0.064\) **seconds** (~64 ms) between invocations of `cb`. Smaller `BLOCK` → callbacks fire more often (more CPU); larger `BLOCK` → chunkier updates.

---

### The streaming callback

PortAudio delivers **one block at a time** into `cb`. You must return quickly; heavy work here can glitch the stream.

```python
    def cb(indata, frames, t, status):
        if status:
            print(status, file=sys.stderr)
        m = indata.copy().reshape(-1)
        rms = float(np.sqrt(np.mean(np.square(m)))) if m.size else 0.0
        bar = "█" * min(40, int(rms * 400))
        print(f"\rRMS: {rms:.4f} {bar:<40}", end="", flush=True)
```

- **`status`**  -  Non‑empty when PortAudio reports underflow/overflow; echoed to **stderr** so it does not fight the `\r` bar on stdout.
- **`indata.copy()`**  -  Copy before using the buffer after return (avoid referencing PortAudio’s memory).
- **`reshape(-1)`**  -  Flatten to 1-D mono samples.
- **RMS**  -  Same formula as [`mic_input`](../mic_input/CODE.md).
- **`bar`**  -  Heuristic: scale RMS by **400**, cap width at **40** characters; tweak the multiplier if your mic is too quiet or loud on screen.
- **`\r` … `end=""` … `flush=True`**  -  Overwrite one terminal line so you see a live meter instead of thousands of lines.

---

### Opening the stream and keeping it alive

```python
    with sd.InputStream(
        channels=1,
        samplerate=SR,
        blocksize=BLOCK,
        callback=cb,
        dtype="float32",
    ):
        import time

        time.sleep(8)
    print()
```

- **`InputStream`**  -  Starts capture; **`callback=cb`** runs on each block.
- **`time.sleep(8)`**  -  Main thread does almost nothing for **8 seconds** while PortAudio delivers blocks to `cb`. When sleep ends, the **`with`** block exits and the stream closes cleanly.
- Final **`print()`**  -  Newline after the `\r` progress line.

For the **speech vs silence** labelling variant, see [`vad_debug/CODE.md`](../vad_debug/CODE.md).

## Failure modes

Silent RMS → device routing or permission issues ([Troubleshooting](../README.md#troubleshooting)). Callback errors often include sample-rate or device mismatches.

## Try next

- Change `BLOCK` and observe how often the callback runs (smaller blocks ⇒ more frequent updates, more CPU).

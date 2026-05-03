# Interruption handling (barge-in on playback)

**Barge-in** often means: while the agent **plays** TTS (or a WAV), something else (VAD, push-to-talk, UI) decides the user **interrupted**, and you **stop playback** cooperatively  -  checking a flag **between chunks** so you never rely on killing the OS driver blindly.

Run **[`interruption_handling.py`](./interruption_handling.py)**  -  loads **`tmp/latency_response.wav`**, plays via [`play_cancellable_stream`](../_audio_chunks.py) in a background thread (one continuous stream, not many chained **`sd.play`** calls), and asks **“Stop playback now?”** with **`Confirm.ask`** (yes/no → real **`bool`**, not **`Prompt.ask`** strings that are always truthy) on the main thread to **`cancel.set()`**. Same cooperative-cancel idea as chunking, but without boundary glitches.

```bash
uv run python 05_full_voice_loop/debug_latency/debug_latency.py   # once, if WAV missing
uv run python 06_real_time_systems/interruption_handling/interruption_handling.py
```

---

## Code walkthrough (`interruption_handling.py`)

### 1. Imports + WAV path

Same **`sys.path`** trick as duplex; **`TMP_LATENCY_WAV`** points at **`tmp/latency_response.wav`** (see [**`_model_paths`**](../_model_paths.py)).

### 2. Fail fast if the WAV is missing

```python
if not TMP_LATENCY_WAV.is_file():
    console.print(
        "Missing tmp/latency_response.wav  -  run:\n"
        "  uv run python 05_full_voice_loop/debug_latency/debug_latency.py"
    )
    raise SystemExit(1)
```

### 3. Load float mono samples

```python
data, sr = sf.read(str(TMP_LATENCY_WAV), dtype="float32")
x = np.squeeze(np.asarray(data, dtype=np.float32))
```

### 4. Shared cancel flag + playback thread

```python
cancel = threading.Event()

def runner() -> None:
    play_cancellable_stream(x, int(sr), cancel=cancel)

t = threading.Thread(target=runner, daemon=True)
t.start()
```

### 5. Let audio start, then ask on the main thread

Short delay so the output stream has opened before **`Confirm.ask`**:

```python
time.sleep(0.5)
if Confirm.ask("Stop playback now?", default=False):
    cancel.set()
t.join(timeout=60)
```

**Yes** → **`cancel.set()`** → the stream callback sees the event on the next block and stops cleanly.

### 6. Duplex vs this script

| | **`duplex_conversation`** | **`interruption_handling`** |
|---|---|---|
| What sets **`cancel`** | Mic RMS while **`playback_on`** | **`Confirm.ask`** (your choice) |

---

## Prerequisite audio file

**`tmp/latency_response.wav`** at the repo root  -  produced by [`debug_latency`](../../05_full_voice_loop/debug_latency/debug_latency.py) in chapter 05.

---

## Cooperative cancellation (concept)

1. Load PCM samples from disk (**`soundfile`**).
2. **`threading.Event`** **`cancel`** shared between playback thread and UI.
3. **`play_cancellable_stream`** feeds an **`OutputStream`**; the callback checks **`cancel`** each block and raises **`CallbackStop`** if set.

[`duplex_conversation`](../duplex_conversation/CODE.md) swaps the **prompt** for **mic RMS** during playback.

---

## See also

- [Duplex conversation](../duplex_conversation/CODE.md)  -  RMS-driven cancel on Kokoro audio.
- [`debug_latency` CODE.md](../../05_full_voice_loop/debug_latency/CODE.md)  -  creates **`tmp/latency_response.wav`**.
- [Chapter 06 README](../README.md#suggested-order)

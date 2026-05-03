# Duplex conversation (cooperative cancel)

While the agent **speaks**, you often still want the **microphone path** alive so you can detect **barge-in**: the user starts talking and you **stop TTS** early.

## Runnable

**[`duplex_conversation.py`](./duplex_conversation.py)** synthesizes a **long** Kokoro utterance, plays it with **chunked** `sounddevice`, and runs an **`InputStream`** RMS monitor. When RMS stays above a threshold **during playback**, it sets **`threading.Event`** and stops — **real audio**, not prints.

```bash
uv run python 06_real_time_systems/duplex_conversation/duplex_conversation.py
```

**Headphones** strongly recommended: speaker bleed into the mic can false-trigger cancel.

---

## Code walkthrough (`duplex_conversation.py`)

### 1. Chapter-local imports (no `voice_agents`)

```python
_CH06 = Path(__file__).resolve().parents[1]
if str(_CH06) not in sys.path:
    sys.path.insert(0, str(_CH06))

from _audio_chunks import play_chunked
from _model_paths import KOKORO_ONNX, KOKORO_VOICES
```

### 2. Kokoro + one long line of speech

Guard models, load **`Kokoro`**, repeat one sentence so **`create`** returns **seconds** of audio:

```python
if not KOKORO_ONNX.is_file() or not KOKORO_VOICES.is_file():
    ...
k = Kokoro(str(KOKORO_ONNX), str(KOKORO_VOICES))
voice = "af_heart" if "af_heart" in voices else voices[0]

long_text = (
    "This playback runs several seconds. Speak into the microphone while you hear this voice. "
    * 12
)
samples, play_sr = k.create(long_text, voice=voice, speed=1.0)
audio = np.asarray(samples, dtype=np.float32).squeeze()
```

### 3. Events — cancel playback vs “should mic matter?”

```python
thresh = 0.06
cancel = threading.Event()
playback_on = threading.Event()
```

**`playback_on`** avoids treating room noise as barge-in **before** TTS starts.

### 4. Mic callback — only while `playback_on`

```python
def mic_cb(indata, frames, t, status) -> None:
    if not playback_on.is_set():
        return
    r = rms_energy(indata)
    mic_blocks["rms"] = r
    if r >= thresh:
        cancel.set()
```

### 5. Playback thread — chunked play respects `cancel`

```python
def runner() -> None:
    playback_on.set()
    finished = play_chunked(audio, int(play_sr), cancel=cancel)
    playback_on.clear()
    if cancel.is_set():
        console.print("[yellow]Interrupted[/] ...")
    elif finished:
        console.print("[green]Finished[/] ...")
```

### 6. Main — mic stream wraps playback thread

```python
with sd.InputStream(
    channels=1,
    samplerate=SR_MIC,
    blocksize=BLOCK,
    callback=mic_cb,
    dtype="float32",
):
    t = threading.Thread(target=runner)
    t.start()
    t.join()
```

The **`InputStream`** stays open for the whole **`join`**, so **`mic_cb`** can fire during **`play_chunked`**.

---

## Pattern (still useful when reading the source)

1. **`threading.Event`** (`cancel`) shared between playback and monitor.
2. **Mic callback** computes RMS; playback thread runs **`play_chunked`** from [`_audio_chunks.py`](../_audio_chunks.py).
3. Cooperative cancel **between chunks** — same idea as [`interruption_handling`](../interruption_handling/CODE.md), which uses a **prompt** instead of RMS.

---

## Appendix: `play_chunked` in [`_audio_chunks.py`](../_audio_chunks.py)

Used by duplex, interruption, and **`turn_taking`**:

```python
def play_chunked(
    samples: np.ndarray,
    sample_rate: int,
    *,
    cancel: threading.Event | None = None,
    chunk_frames: int = 2048,
) -> bool:
    x = np.asarray(samples, dtype=np.float32).squeeze()
    if x.ndim > 1:
        x = x[:, 0]
    n = len(x)
    i = 0
    while i < n:
        if cancel is not None and cancel.is_set():
            sd.stop()
            return False
        end = min(i + chunk_frames, n)
        sd.play(x[i:end], sample_rate, latency="high", blocksize=min(chunk_frames, end - i))
        sd.wait()
        i = end
    if cancel is not None and cancel.is_set():
        sd.stop()
        return False
    time.sleep(0.003)
    return True
```

**`record_mono_seconds`** (same file) — **`LISTENING`** in **`turn_taking`**:

```python
def record_mono_seconds(duration_s: float, *, sample_rate: int = _SR_DEFAULT) -> tuple[np.ndarray, int]:
    frames = int(sample_rate * duration_s)
    audio = sd.rec(frames, samplerate=sample_rate, channels=1, dtype="float32")
    sd.wait()
    return np.squeeze(audio), sample_rate
```

---

## See also

- [Chapter 06 README](../README.md)
- [`interruption_handling`](../interruption_handling/CODE.md) — WAV + **Rich** prompt cancel.

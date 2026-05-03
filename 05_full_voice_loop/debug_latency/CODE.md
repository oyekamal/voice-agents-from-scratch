# `debug_latency.py`  -  code walkthrough

## Purpose

Runs a **fixed** voice pipeline (similar ingredients to [`blocking_voice_agent`](../blocking_voice_agent/CODE.md)) and prints a **Rich table** of **how long each stage took** on your machine: mic capture (**3 s** fixed), **STT**, **LLM**, **TTS** (writes **`tmp/latency_response.wav`**), then **playback** from that file.

Use it to see **where time goes** (CPU-bound Whisper vs LLM vs Kokoro vs I/O), not to optimize production settings  -  chapter scripts keep parameters simple on purpose.

**Downstream:** [chapter 06 interruption handling](../../06_real_time_systems/interruption_handling/CODE.md) documents **`tmp/latency_response.wav`** from this script for the cooperative-cancel playback snippet.

---

## Run

```bash
uv run python 05_full_voice_loop/debug_latency/debug_latency.py
```

There is **no** confirmation prompt  -  recording starts when the script runs (**3 seconds**). Speak during that window.

---

## Dependencies

Same families as [`blocking_voice_agent`](../blocking_voice_agent/CODE.md): [`record_seconds`](../../src/voice_agents/audio/audio_input.py), [`transcribe_samples`](../../src/voice_agents/stt/streaming_stt.py), [`AgentCore`](../../src/voice_agents/agent/agent_core.py), [`synthesize_to_wav`](../../src/voice_agents/tts/streaming_tts.py), [`play_float_mono`](../../src/voice_agents/audio/audio_output.py). **`soundfile`** is imported inside the playback step to read the WAV back.

---

## Code walkthrough

### Why `perf_counter` and a row list

The script does **not** print transcripts or replies  -  it only measures **elapsed seconds per stage**. Each stage follows the same pattern:

1. **`t0 = time.perf_counter()`** right before work begins.
2. Run one blocking step (mic, STT, LLM, TTS, or playback).
3. **`rows.append((label, time.perf_counter() - t0, color))`** so the Rich table can color each row.

**`time.perf_counter()`** is monotonic and suitable for intervals (unlike **`time.time()`**, which can jump). A separate **`t_wall`** wraps the **entire** `main()` so the table’s **Wall total** includes gaps between stages (tiny, unless you pause in a debugger).

---

### Repository paths and output file

```python
ROOT = Path(__file__).resolve().parents[2]
WHISPER_ROOT = ROOT / "models" / "whisper"
LLM_PATH = ROOT / "models" / "llm" / "qwen2.5-0.5b-instruct-q4_k_m.gguf"
KOKORO_MODEL = ROOT / "models" / "kokoro" / "kokoro-v1.0.onnx"
KOKORO_VOICES = ROOT / "models" / "kokoro" / "voices-v1.0.bin"
OUT = ROOT / "tmp" / "latency_response.wav"
```

**`parents[2]`** is the **repository root** (script lives under **`debug_latency/`**). Paths match [`blocking_voice_agent`](../blocking_voice_agent/CODE.md) except the output WAV name: **`tmp/latency_response.wav`** avoids overwriting **`blocking_response.wav`** if you run both scripts in one session. This script does **not** preflight-check model files or save **`blocking_input.wav`**  -  failures surface when STT/LLM/TTS load (see [Failure modes](#failure-modes)).

---

### `main()`: table setup and wall clock

```python
def main() -> None:
    console = Console()
    rows: list[tuple[str, float, str]] = []
    t_wall = time.perf_counter()
```

**`rows`** holds **`(stage name, seconds, Rich color tag)`** for each timed segment. Colors are cosmetic  -  they make the table scannable in a terminal (green mic, cyan STT, magenta LLM, yellow TTS, blue playback).

---

### Stage 1  -  Mic capture (fixed 3 seconds)

```python
t0 = time.perf_counter()
audio, sr = record_seconds(3.0, config=AudioInputConfig())
rows.append(("Mic capture (fixed 3s)", time.perf_counter() - t0, "green"))
```

Unlike [`blocking_voice_agent`](../blocking_voice_agent/CODE.md), there is **no** **`--seconds`** flag and **no** Rich confirmation  -  recording starts as soon as the process reaches this line. **`3.0`** means the **Mic capture** row is always **about three seconds** of wall time (plus OS/audio startup), independent of how long you spoke. That stabilizes comparisons across runs when you care about **STT / LLM / TTS** only.

[`record_seconds`](../../src/voice_agents/audio/audio_input.py) returns **float32 mono PCM** and **sample rate** from the default input device via [`AudioInputConfig`](../../src/voice_agents/audio/audio_input.py).

---

### Stage 2  -  Speech-to-text

```python
t0 = time.perf_counter()
stt = TranscribeConfig(download_root=str(WHISPER_ROOT))
text = transcribe_samples(audio, sr, config=stt)
rows.append(("STT", time.perf_counter() - t0, "cyan"))
```

[`TranscribeConfig`](../../src/voice_agents/stt/streaming_stt.py) points faster-whisper at **`models/whisper/`**. [`transcribe_samples`](../../src/voice_agents/stt/streaming_stt.py) runs ASR on the full buffer  -  this row usually dominates when the model is cold or the CPU is busy. **STT** time includes **model load** for this process if weights were not already cached in memory.

---

### Stage 3  -  LLM (empty transcript → `"hello"`)

```python
t0 = time.perf_counter()
reply = AgentCore(model_path=str(LLM_PATH)).complete(
    text or "hello", engine=PromptEngine(), max_tokens=128
)
rows.append(("LLM", time.perf_counter() - t0, "magenta"))
```

**`text or "hello"`** ensures a non-empty user message so the pipeline always reaches TTS and playback  -  useful for **latency profiling** when the mic picked up silence or STT returned `""`. For a realistic “what did I say?” measurement, speak clearly; otherwise the **LLM** row still reflects a short completion from **`hello`**.

A **new** [`AgentCore`](../../src/voice_agents/agent/agent_core.py) is constructed each run (same teaching style as blocking). **`max_tokens=128`** is slightly lower than blocking’s **256**  -  enough for a short reply while keeping the LLM segment bounded.

---

### Stage 4  -  TTS to WAV

```python
t0 = time.perf_counter()
cfg = TTSConfig(str(KOKORO_MODEL), str(KOKORO_VOICES))
cfg.voice = pick_voice(cfg, "af_heart")
synthesize_to_wav(reply, OUT, config=cfg)
rows.append(("TTS (WAV)", time.perf_counter() - t0, "yellow"))
```

[`TTSConfig`](../../src/voice_agents/tts/streaming_tts.py) and [`pick_voice`](../../src/voice_agents/tts/streaming_tts.py) match the other chapter scripts. [`synthesize_to_wav`](../../src/voice_agents/tts/streaming_tts.py) writes **`tmp/latency_response.wav`** (overwritten each run). The label **TTS (WAV)** separates **synthesis** from **playback**  -  Kokoro time is separate from reading the file and pushing samples to the device.

---

### Stage 5  -  Playback (soundfile + `play_float_mono`)

```python
t0 = time.perf_counter()
import soundfile as sf

data, ssr = sf.read(OUT, dtype="float32")
play_float_mono(np.squeeze(data), int(ssr))
rows.append(("Playback", time.perf_counter() - t0, "blue"))
```

**`soundfile`** is imported **inside** this block so the dependency is only pulled when playback runs. The WAV is read as **float32**, **`np.squeeze`** drops a singleton dimension if needed, and [`play_float_mono`](../../src/voice_agents/audio/audio_output.py) plays through the default output device (same low-level path as other chapters). **Playback** includes **disk read**, **decode**, and **audio output**  -  useful when comparing to [`play_wav_file`](../../src/voice_agents/audio/audio_output.py) in blocking, which wraps the same stack.

---

### Wall total and Rich table

```python
total = time.perf_counter() - t_wall
tb = Table(title="Latency stages")
tb.add_column("Stage", style="bold")
tb.add_column("Seconds", justify="right")
for name, sec, color in rows:
    tb.add_row(f"[{color}]{name}[/]", f"{sec:.3f}")
tb.add_row("[bold]Wall total[/]", f"{total:.3f}")
console.print(tb)
```

The sum of the five stage rows can be **slightly less** than **Wall total** if there is any overhead between **`perf_counter()`** calls; usually they match within rounding. Use the table to see **which stage to optimize first** (often STT or LLM on CPU-only setups).

---

### Compared to [`blocking_voice_agent`](../blocking_voice_agent/CODE.md)

| | **debug_latency (this script)** | **blocking_voice_agent** |
|--|--|--|
| Recording length | Fixed **3 s** | **`--seconds`** (default **5**) |
| Before recording | None  -  starts immediately | Rich **Confirm** |
| Input WAV on disk | Not saved | **`tmp/blocking_input.wav`** |
| Output WAV | **`tmp/latency_response.wav`** | **`tmp/blocking_response.wav`** |
| Empty STT | **`hello`** fallback → full pipeline | **Exit** before LLM |
| **`max_tokens`** | **128** | **256** |
| UX | Timing **table** only | **`You:`** / **`Assistant:`** + playback |

---

### Pipeline summary (order matters)

| Step | Function / API | Timed row label |
|------|----------------|------------------|
| 1 | [`record_seconds`](../../src/voice_agents/audio/audio_input.py) | Mic capture (fixed 3s) |
| 2 | [`transcribe_samples`](../../src/voice_agents/stt/streaming_stt.py) | STT |
| 3 | [`AgentCore.complete`](../../src/voice_agents/agent/agent_core.py) | LLM |
| 4 | [`synthesize_to_wav`](../../src/voice_agents/tts/streaming_tts.py) | TTS (WAV) |
| 5 | **`sf.read`** + [`play_float_mono`](../../src/voice_agents/audio/audio_output.py) | Playback |

---

## Failure modes

Missing models → [download_models.py](../../00_start_here/download_models.py). If STT returns empty string, the LLM still runs with **`hello`**  -  totals are still meaningful but not a realistic user utterance.

---

## Try next

- [Chapter 06  -  Real-time systems](../../06_real_time_systems/README.md): interruption, VAD, duplex.

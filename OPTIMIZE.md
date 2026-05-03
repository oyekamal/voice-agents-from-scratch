## macOS GPU = Apple Silicon Metal + CoreML

Each component in your stack has its own path to the GPU. Assuming you have an M-series Mac (M1/M2/M3/M4):

---

### 1. LLM - llama-cpp-python with Metal

Uninstall the CPU build and reinstall with Metal enabled:

```bash
uv pip uninstall llama-cpp-python

CMAKE_ARGS="-DGGML_METAL=on" \
uv pip install llama-cpp-python --no-cache-dir
```

To verify it's using Metal, set `verbose=True` in your `AgentCore` init once - you should see `ggml_metal_init` in the output. Then set it back to `False`.

Metal offloads all transformer layers to the GPU by default. For your `qwen2.5-0.5b` model this alone will cut LLM token generation time significantly.

---

### 2. Whisper - swap to `mlx-whisper`

`faster-whisper` uses CTranslate2 which **does not support Metal**. The drop-in replacement for Apple Silicon is `mlx-whisper`, which runs natively on the GPU via Apple's MLX framework:

```bash
uv pip uninstall faster-whisper
uv pip install mlx-whisper
```

Update your `streaming_stt.py` wrapper:

```python
import mlx_whisper

def transcribe_samples(audio: np.ndarray, sr: int, config: TranscribeConfig) -> str:
    # mlx-whisper expects float32 normalized audio, same as faster-whisper
    result = mlx_whisper.transcribe(
        audio,
        path_or_hf_repo="mlx-community/whisper-tiny.en-mlx",
        language="en",
    )
    return result["text"].strip()
```

The first call downloads the MLX-converted weights from HuggingFace (~75MB, same size as before). After that it's cached locally. You can swap `tiny.en` for `small.en` or `base.en` with minimal latency impact on M-series since the Neural Engine handles it.

---

### 3. Kokoro - ONNX Runtime with CoreML

ONNX Runtime has a CoreML execution provider that routes inference to the GPU and Neural Engine. Install the CoreML-enabled build:

```bash
uv pip uninstall onnxruntime
uv pip install onnxruntime-silicon
```

`kokoro-onnx` will automatically pick up CoreML if it's available. You can confirm by checking which providers are active:

```python
import onnxruntime as ort
print(ort.get_available_providers())
# Should include: ['CoreMLExecutionProvider', 'CPUExecutionProvider']
```

If `kokoro-onnx` doesn't expose provider selection directly, you can patch it at the session level:

```python
from kokoro_onnx import Kokoro
import onnxruntime as ort

# Force CoreML provider when creating the session
sess_options = ort.SessionOptions()
kokoro = Kokoro.__new__(Kokoro)
kokoro.session = ort.InferenceSession(
    str(KOKORO_MODEL),
    sess_options=sess_options,
    providers=["CoreMLExecutionProvider", "CPUExecutionProvider"],
)
```

---

### 4. `requirements.txt` - GPU variant

Keep a separate file for Apple Silicon:

```
# requirements-apple-silicon.txt
llama-cpp-python          # reinstall with CMAKE_ARGS above
mlx-whisper
onnxruntime-silicon
kokoro-onnx
sounddevice
numpy
rich
```

---

### Expected speedup

| Component | CPU time | Metal/CoreML | Notes |
|---|---|---|---|
| Whisper tiny.en | ~200ms | ~60–90ms | MLX uses Neural Engine |
| LLM first sentence | ~350ms | ~100–180ms | Metal offloads all layers |
| Kokoro sentence | ~180ms | ~80–120ms | CoreML + Neural Engine |
| **First audio** | **~700ms** | **~250–400ms** | Into the "feels instant" range |

On an M2 or better you should consistently land under 400ms first-audio latency, which is solidly within natural conversation pacing.

---

### One thing to watch

Metal and CoreML both have a **first-call JIT compilation cost** - the first inference after launch compiles Metal shaders or a CoreML model graph. This is why the warm-up calls in your startup sequence matter even more on GPU than on CPU. Keep them exactly as they are.
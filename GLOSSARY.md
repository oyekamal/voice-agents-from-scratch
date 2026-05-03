# Glossary (voice and audio)

Short definitions for terms used across the tutorials. Chapters go deeper where it matters.

| Term | Meaning |
|------|---------|
| **PCM** | Pulse-code modulation: digital audio as a sequence of numeric **samples** (often `float32` in this repo). Analog sound is sampled many times per second; each sample is one amplitude step. |
| **Sample rate** | Samples per second (Hz). Speech pipelines here often use **16 kHz** for capture/STT and **24 kHz** for Kokoro output. |
| **Mono / stereo** | **Mono** = one channel (one waveform). **Stereo** = two channels. Voice agents usually use mono for speech. |
| **RMS** | Root mean square: a single number describing **average loudness** of a block of samples. Used for level meters and simple “speech vs silence” gates. |
| **STT** | Speech-to-text: audio → text (here: **Whisper** via faster-whisper). |
| **LLM** | Large language model: predicts text given a prompt; here a **local GGUF** via llama-cpp-python, not a remote API. |
| **TTS** | Text-to-speech: text → audio (here: **Kokoro**). |
| **VAD** | Voice activity detection: deciding **when** someone is speaking vs silence or noise. Chapter 01 uses a toy RMS threshold; later material may use richer models (e.g. Silero in the stack). |
| **GGUF** | A file format for **quantized** LLM weights used by **llama.cpp** / **llama-cpp-python**. Smaller quantizations run faster but can change quality. |
| **ONNX** | A common format for neural network graphs; **Kokoro** runs as an ONNX model with an ONNX Runtime session. |
| **RTF** | Real-time factor: synthesis **wall time ÷ audio duration**. Below 1 means you synthesized faster than real-time playback - headroom for responsive dialogue. |
| **Blocking pipeline** | Each stage finishes before the next starts (record → transcribe → reply → speak). Simple to understand; higher perceived latency. |
| **Streaming** | Overlapping work: e.g. speak the first sentence while the LLM is still generating the rest. |
| **Barge-in** | The user starts speaking **while the agent is playing** TTS; the system **cancels** playback and may start a new turn. |
| **Duplex** | Both directions active in principle: listening while speaking (with engineering needed to avoid echo and false triggers). |
| **Full-duplex** | Same idea as duplex; often used for “natural conversation” UX with overlap and interruption. |
| **Chat template** | The exact string format (role tags, turns) wrapping user/assistant text for an **instruct** model. Must match the model family (e.g. Qwen vs Llama). |

For the end-to-end picture, see [00_start_here/architecture_overview.md](00_start_here/architecture_overview.md).

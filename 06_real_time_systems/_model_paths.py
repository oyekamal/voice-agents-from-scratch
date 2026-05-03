"""Chapter 06 only: repository model paths (no ``voice_agents`` imports).

Scripts in this chapter resolve weights the same way as chapter 05; paths stay
centralized here so each demo file stays readable.
"""

from __future__ import annotations

from pathlib import Path

_CH06 = Path(__file__).resolve().parent
REPO_ROOT = _CH06.parent
MODELS = REPO_ROOT / "models"

WHISPER_DOWNLOAD_ROOT = str(MODELS / "whisper")
LLM_GGUF = MODELS / "llm" / "qwen2.5-0.5b-instruct-q4_k_m.gguf"
KOKORO_ONNX = MODELS / "kokoro" / "kokoro-v1.0.onnx"
KOKORO_VOICES = MODELS / "kokoro" / "voices-v1.0.bin"
TMP_LATENCY_WAV = REPO_ROOT / "tmp" / "latency_response.wav"

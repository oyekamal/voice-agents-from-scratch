"""Patient tutor persona over the chapter 05 streaming voice loop (mic + Kokoro).

Same glue as ``05_full_voice_loop/streaming_voice_agent/streaming_voice_agent.py``  -  only
the ``PromptEngine.system_prompt`` changes. Swap one string and you change the product.

Use ``--text`` when you have no microphone or want deterministic runs.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from kokoro_onnx import Kokoro
from rich.console import Console

from voice_agents.agent.agent_core import AgentCore
from voice_agents.agent.prompt_engine import PromptEngine
from voice_agents.audio.audio_output import play_float_mono
from voice_agents.audio.audio_input import AudioInputConfig, record_seconds
from voice_agents.stt.streaming_stt import TranscribeConfig, transcribe_samples

ROOT = Path(__file__).resolve().parents[2]
WHISPER_ROOT = ROOT / "models" / "whisper"
LLM_PATH = ROOT / "models" / "llm" / "qwen2.5-0.5b-instruct-q4_k_m.gguf"
KOKORO_MODEL = ROOT / "models" / "kokoro" / "kokoro-v1.0.onnx"
KOKORO_VOICES = ROOT / "models" / "kokoro" / "voices-v1.0.bin"

_SENTENCE_END = re.compile(r"([.!?]\s+)")


def _play_kokoro(k: Kokoro, voice: str, text: str) -> None:
    audio, sr = k.create(text, voice=voice, speed=1.0)
    play_float_mono(audio, int(sr))


def main() -> None:
    ap = argparse.ArgumentParser(description="Streaming tutor voice reply (chapter 05 glue + persona).")
    ap.add_argument(
        "--text",
        default=None,
        help="Skip mic; use this user question text (STT bypass).",
    )
    args = ap.parse_args()

    console = Console()
    if not all(path.exists() for path in (LLM_PATH, KOKORO_MODEL, KOKORO_VOICES)):
        console.print("Download models from chapter 00 first (Whisper + LLM + Kokoro).")
        raise SystemExit(1)

    if args.text is not None:
        text = args.text.strip()
    else:
        console.print("[dim]Recording 5s…[/]")
        audio, sr = record_seconds(5.0, config=AudioInputConfig())
        text = transcribe_samples(audio, sr, config=TranscribeConfig(download_root=str(WHISPER_ROOT)))

    console.print("[bold]You:[/]", text)
    if not text.strip():
        raise SystemExit(0)

    agent = AgentCore(model_path=str(LLM_PATH))
    engine = PromptEngine(
        system_prompt=(
            "You are a patient tutor. Give a short explanation then one practice question. "
            "Keep replies under three sentences."
        )
    )
    k = Kokoro(str(KOKORO_MODEL), str(KOKORO_VOICES))
    voice = "af_heart" if "af_heart" in k.get_voices() else k.get_voices()[0]

    buf = ""
    for piece in agent.stream_tokens(text, engine=engine, max_tokens=256):
        buf += piece
        while True:
            m = _SENTENCE_END.search(buf)
            if not m:
                break
            chunk = buf[: m.end()].strip()
            buf = buf[m.end() :]
            if chunk:
                _play_kokoro(k, voice, chunk)
        if len(buf) > 200:
            chunk = buf.strip()
            buf = ""
            if chunk:
                _play_kokoro(k, voice, chunk)
    if buf.strip():
        _play_kokoro(k, voice, buf.strip())


if __name__ == "__main__":
    main()

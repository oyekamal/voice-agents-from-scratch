"""
Optimized voice agent - no disk I/O in the TTS→playback hot path.
"""

from __future__ import annotations

import queue
import re
import threading
import time
from pathlib import Path

import numpy as np
import sounddevice as sd
from rich.console import Console
from rich.prompt import Confirm

from kokoro_onnx import Kokoro

from voice_agents.agent.agent_core import AgentCore
from voice_agents.agent.prompt_engine import PromptEngine
from voice_agents.audio.audio_input import AudioInputConfig, record_seconds
from voice_agents.stt.streaming_stt import TranscribeConfig, transcribe_samples
from voice_agents.tts.streaming_tts import TTSConfig, pick_voice

ROOT          = Path(__file__).resolve().parent.parent
MODELS        = ROOT / "models"
LLM_PATH      = MODELS / "llm"    / "qwen2.5-0.5b-instruct-q4_k_m.gguf"
KOKORO_MODEL  = MODELS / "kokoro" / "kokoro-v1.0.onnx"
KOKORO_VOICES = MODELS / "kokoro" / "voices-v1.0.bin"
WHISPER_ROOT  = MODELS / "whisper"

KOKORO_SR = 24_000          # Kokoro always outputs 24 kHz
_SENTENCE_END = re.compile(r"(?<=[.!?])(?:\s+|$)")


def _flush_sentences(buf: str) -> tuple[list[str], str]:
    parts = _SENTENCE_END.split(buf)
    if len(parts) == 1:
        return [], buf
    complete = [s.strip() for s in parts[:-1] if s.strip()]
    return complete, parts[-1]


def streaming_tts_play(
    token_iter,
    kokoro: Kokoro,
    tts_cfg: TTSConfig,
    console: Console,
) -> tuple[float | None, str]:
    """
    Synthesize sentence-by-sentence into numpy arrays.
    Play through a single persistent OutputStream - no per-chunk device init,
    no disk I/O, no crackle.
    """
    # numpy arrays go in; None is the sentinel
    audio_q: queue.Queue[np.ndarray | None] = queue.Queue(maxsize=4)
    t_first: list[float | None] = [None]
    full_tokens: list[str] = []

    # ── synthesis thread ──────────────────────────────────────────────────────
    def synthesize_worker() -> None:
        buf = ""
        for token in token_iter:
            full_tokens.append(token)
            buf += token
            sentences, buf = _flush_sentences(buf)
            for sent in sentences:
                samples, _sr = kokoro.create(
                    sent,
                    voice=tts_cfg.voice,
                    speed=tts_cfg.speed,
                    lang="en-us",
                )
                # Kokoro returns float32 in [-1, 1] - ready for sounddevice
                audio_q.put(samples.astype(np.float32))
        if buf.strip():
            samples, _sr = kokoro.create(
                buf.strip(),
                voice=tts_cfg.voice,
                speed=tts_cfg.speed,
                lang="en-us",
            )
            audio_q.put(samples.astype(np.float32))
        audio_q.put(None)

    thread = threading.Thread(target=synthesize_worker, daemon=True)
    thread.start()

    # ── playback: one open stream for the entire response ────────────────────
    with sd.OutputStream(
        samplerate=KOKORO_SR,
        channels=1,
        dtype="float32",
        # blocksize: small enough for low latency, large enough to avoid
        # underruns. 2048 samples @ 24 kHz ≈ 85 ms - a safe sweet spot.
        blocksize=2048,
    ) as stream:
        while True:
            chunk = audio_q.get()
            if chunk is None:
                break
            if t_first[0] is None:
                t_first[0] = time.perf_counter()
            stream.write(chunk)   # blocks only until the buffer accepts data

    thread.join()
    return t_first[0], "".join(full_tokens)


def main() -> None:
    console = Console()

    for p in (LLM_PATH, KOKORO_MODEL, KOKORO_VOICES):
        if not p.exists():
            console.print(f"[red]Missing model:[/] {p}")
            raise SystemExit(1)

    # ── pre-load ──────────────────────────────────────────────────────────────
    console.print("[dim]Pre-loading LLM…[/]")
    engine = PromptEngine()
    agent  = AgentCore(model_path=str(LLM_PATH), n_ctx=2048, verbose=False)
    agent.preload()

    console.print("[dim]Pre-loading Whisper…[/]")
    stt_cfg = TranscribeConfig(
        model_size="tiny.en",
        download_root=str(WHISPER_ROOT),
        language="en",
    )
    transcribe_samples(np.zeros(16_000, dtype=np.float32), 16_000, config=stt_cfg)

    console.print("[dim]Pre-loading Kokoro…[/]")
    kokoro = Kokoro(str(KOKORO_MODEL), str(KOKORO_VOICES))
    tts_cfg = TTSConfig(
        model_path=str(KOKORO_MODEL),
        voices_path=str(KOKORO_VOICES),
        voice="af_heart",
        speed=1.0,
    )
    tts_cfg.voice = pick_voice(tts_cfg, tts_cfg.voice)

    # Warm up Kokoro ONNX session (first inference is always slower)
    console.print("[dim]Warming up Kokoro ONNX session…[/]")
    kokoro.create("Hello.", voice=tts_cfg.voice, speed=1.0, lang="en-us")

    console.print("[green]All models ready.[/]")

    # ── record ────────────────────────────────────────────────────────────────
    if not Confirm.ask("Record ~5 s of speech when ready", default=True):
        raise SystemExit(0)

    console.print("[dim]Recording 5 s… speak now.[/]")
    audio, sr = record_seconds(5.0, config=AudioInputConfig(sample_rate=16_000))
    t_after_recording = time.perf_counter()

    # ── STT ───────────────────────────────────────────────────────────────────
    text = transcribe_samples(audio, sr, config=stt_cfg)
    console.print("[bold]You said:[/]", text or "[dim](empty)[/]")
    if not text.strip():
        raise SystemExit(0)

    # ── stream LLM → TTS → play ───────────────────────────────────────────────
    console.print("[dim]Streaming reply…[/]")
    token_stream = agent.stream_tokens(
        text, engine=engine, max_tokens=256, temperature=0.7
    )

    t_first_audio, reply = streaming_tts_play(
        token_stream, kokoro, tts_cfg, console
    )
    console.print("[bold]Assistant:[/]", reply)

    # ── latency report ────────────────────────────────────────────────────────
    if t_first_audio is None:
        console.print("[yellow]No audio produced.[/]")
        return

    latency_ms = (t_first_audio - t_after_recording) * 1000
    console.print(f"\n[bold]Latency:[/] {latency_ms:.0f} ms")
    console.print(
        "[dim]Target: <700 ms feels conversational. "
        "With model warm-up and sentence-level streaming the first audio chunk "
        "typically arrives after STT + LLM-first-sentence + TTS-first-chunk "
        "rather than STT + full-LLM + full-TTS.[/]"
    )


if __name__ == "__main__":
    main()
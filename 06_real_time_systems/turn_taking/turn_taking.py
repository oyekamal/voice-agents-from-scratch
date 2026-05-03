"""LISTENING → THINKING → SPEAKING voice loop without ``voice_agents`` (raw stack + FSM).

Uses faster-whisper, llama-cpp-python, Kokoro, and sounddevice only. Session snapshot in Rich
unless ``--plain``. ``--dry-run`` skips model load and uses stub text.

**Streaming:** the LLM is read with ``stream=True`` (token chunks). Kokoro uses ``create_stream``
(async phoneme batches) per sentence so synthesis overlaps less with wall time than one giant
``create``; playback is still one ``OutputStream`` per spoken sentence (``play_cancellable_stream``).
"""

from __future__ import annotations

import argparse
import asyncio
import ctypes
import re
import sys
import threading
import time
from pathlib import Path
from typing import Any

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from kokoro_onnx import SAMPLE_RATE, Kokoro
from llama_cpp import Llama, llama_log_callback, llama_log_set
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

_CH06 = Path(__file__).resolve().parents[1]
if str(_CH06) not in sys.path:
    sys.path.insert(0, str(_CH06))

from _audio_chunks import play_cancellable_stream, record_mono_seconds  # noqa: E402
from _model_paths import (  # noqa: E402
    KOKORO_ONNX,
    KOKORO_VOICES,
    LLM_GGUF,
    WHISPER_DOWNLOAD_ROOT,
)

_IM_END = "<|" + "im_end" + "|>"
# Punctuation then spaces, or punctuation at end of buffer (so "Really?" at EOS is a sentence).
_SENTENCE_END = re.compile(r"([.!?])(?:\s+|$)")


@llama_log_callback
def _silence_llama_logs(level: int, text: object, user_data: object) -> None:
    del level, text, user_data


llama_log_set(_silence_llama_logs, ctypes.c_void_p())


def qwen25_chat_prompt(system: str, user: str) -> str:
    return (
        f"<|im_start|>system\n{system}{_IM_END}\n"
        f"<|im_start|>user\n{user}{_IM_END}\n"
        f"<|im_start|>assistant\n"
    )


SYSTEM_PROMPT = "You are a helpful, concise voice assistant."

SR_MIC = 16_000
BLOCK = 512
# Barge-in: same idea as duplex_conversation — lead-in ignores speaker bleed; sustained loud blocks
# avoids one noisy sample cancelling the rest of the reply.
LEAD_IN_S = 1.0
SUSTAIN_BLOCKS = 4
RMS_THRESH_BARGE = 0.055


def rms_energy(block: np.ndarray) -> float:
    v = block.reshape(-1).astype(np.float32)
    return float(np.sqrt(np.mean(np.square(v))))


def transcribe_audio(model: WhisperModel, audio: np.ndarray, sample_rate: int) -> str:
    audio = np.asarray(audio, dtype=np.float32).squeeze()
    segments, _ = model.transcribe(audio, language="en", beam_size=5)
    parts = [seg.text.strip() for seg in segments]
    return " ".join(p for p in parts if p).strip()


def llm_stream_text_chunks(llm: Llama, user_text: str, *, max_tokens: int = 256):
    prompt = qwen25_chat_prompt(SYSTEM_PROMPT, user_text)
    stream = llm(
        prompt,
        max_tokens=max_tokens,
        temperature=0.7,
        stop=[_IM_END, "<|endoftext|>"],
        stream=True,
    )
    for chunk in stream:
        if not chunk or "choices" not in chunk:
            continue
        piece = chunk["choices"][0].get("text", "")
        if piece:
            yield piece


async def _kokoro_stream_to_mono(kokoro: Kokoro, text: str, voice: str) -> tuple[np.ndarray, int]:
    chunks: list[np.ndarray] = []
    sr = SAMPLE_RATE
    async for audio, sr in kokoro.create_stream(text, voice=voice, speed=1.0, lang="en-us"):
        x = np.asarray(audio, dtype=np.float32).squeeze()
        if x.ndim > 1:
            x = x[:, 0]
        chunks.append(x)
    if not chunks:
        return np.array([], dtype=np.float32), int(sr)
    return np.concatenate(chunks), int(sr)


def synthesize_sentence_stream(kokoro: Kokoro, text: str, voice: str) -> tuple[np.ndarray, int]:
    """Run Kokoro ``create_stream`` to completion and return mono float32 + sample rate."""
    return asyncio.run(_kokoro_stream_to_mono(kokoro, text, voice))


def render_session(session: dict[str, Any]) -> Panel:
    body = Group(
        Text.assemble(("state", "bold"), " ", (str(session.get("state", "")), "cyan")),
        Text.assemble(("last_transcript", "bold"), " ", (str(session.get("last_transcript", "")), "green")),
        Text.assemble(("last_reply", "bold"), " ", (str(session.get("last_reply", "")), "yellow")),
    )
    return Panel(body, title="turn_taking (session)", border_style="magenta")


def speak_with_optional_barge_in(
    pcm: np.ndarray,
    ksr: int,
    *,
    use_barge_in: bool,
) -> bool:
    """Play audio; optional mic RMS monitor can set cancel (same pattern as duplex_conversation)."""
    if not use_barge_in:
        return play_cancellable_stream(pcm, ksr, cancel=None)

    cancel = threading.Event()
    playback_on = threading.Event()
    gate = {"arm_at": float("inf"), "loud_streak": 0}

    def mic_cb(indata, frames, t, status) -> None:  # noqa: ARG001
        if not playback_on.is_set():
            return
        now = time.monotonic()
        if now < gate["arm_at"]:
            gate["loud_streak"] = 0
            return
        if rms_energy(indata) >= RMS_THRESH_BARGE:
            gate["loud_streak"] += 1
        else:
            gate["loud_streak"] = 0
        if gate["loud_streak"] >= SUSTAIN_BLOCKS:
            cancel.set()

    def player() -> None:
        gate["arm_at"] = time.monotonic() + LEAD_IN_S
        gate["loud_streak"] = 0
        play_cancellable_stream(pcm, ksr, cancel=cancel)

    th = threading.Thread(target=player)
    th.start()
    playback_on.set()
    with sd.InputStream(
        channels=1,
        samplerate=SR_MIC,
        blocksize=BLOCK,
        callback=mic_cb,
        dtype="float32",
    ):
        th.join()
    playback_on.clear()
    return not cancel.is_set()


def main() -> None:
    ap = argparse.ArgumentParser(description="FSM voice loop without voice_agents package.")
    ap.add_argument("--seconds", type=float, default=5.0, help="Recording length for LISTENING")
    ap.add_argument("--plain", action="store_true", help="Log text only (no Rich Live panel)")
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Stub STT/LLM/TTS; exercise FSM and UI only",
    )
    ap.add_argument("--no-barge-in", action="store_true", help="Disable mic cancel during SPEAKING")
    args = ap.parse_args()

    console = Console()

    if not args.dry_run:
        for p in (LLM_GGUF, KOKORO_ONNX, KOKORO_VOICES):
            if not p.is_file():
                console.print(f"Missing model: {p}  -  run 00_start_here/download_models.py")
                raise SystemExit(1)

    whisper = None
    llm = None
    kokoro = None
    voice = "af_heart"

    if not args.dry_run:
        console.print("[dim]Loading Whisper (tiny.en)…[/]")
        whisper = WhisperModel(
            "tiny.en",
            device="auto",
            compute_type="int8",
            download_root=WHISPER_DOWNLOAD_ROOT,
        )
        console.print("[dim]Loading Llama (GGUF)…[/]")
        llm = Llama(model_path=str(LLM_GGUF), n_ctx=4096, verbose=False)
        console.print("[dim]Loading Kokoro…[/]")
        kokoro = Kokoro(str(KOKORO_ONNX), str(KOKORO_VOICES))
        voices = kokoro.get_voices()
        voice = "af_heart" if "af_heart" in voices else voices[0]

    session: dict[str, Any] = {
        "state": "INIT",
        "last_transcript": "",
        "last_reply": "",
    }

    def refresh_ui(live: Live | None) -> None:
        if args.plain:
            console.print(
                f"[bold]{session['state']}[/] | "
                f"you: {session['last_transcript']!r} | "
                f"reply: {session['last_reply']!r}"
            )
        elif live is not None:
            live.update(render_session(session))

    console.print(
        "[bold]Turn-taking loop[/]  -  Ctrl+C to exit. "
        "States: LISTENING → THINKING → SPEAKING  |  "
        "[dim]Streaming LLM tokens and Kokoro create_stream per sentence (see module docstring).[/]"
    )

    def run_turn(live: Live | None) -> None:
        session["state"] = "LISTENING"
        refresh_ui(live)
        audio, sr = record_mono_seconds(args.seconds, sample_rate=SR_MIC)
        session["state"] = "THINKING"
        refresh_ui(live)

        if args.dry_run:
            text = "(dry-run user)"
            reply = "(dry-run assistant reply)"
            session["last_transcript"] = text
            session["last_reply"] = reply
        else:
            assert whisper is not None and llm is not None and kokoro is not None
            text = transcribe_audio(whisper, audio, sr)
            session["last_transcript"] = text
            refresh_ui(live)
            if not text.strip():
                console.print("[yellow]No speech detected  -  listen again.[/]")
                return

            session["last_reply"] = ""
            refresh_ui(live)

            cumulative = ""
            sentence_buf = ""
            spoken_any = False
            barge_stopped = False
            use_barge = not args.no_barge_in

            for piece in llm_stream_text_chunks(llm, text):
                cumulative += piece
                sentence_buf += piece
                session["last_reply"] = cumulative[:800]
                refresh_ui(live)

                while True:
                    m = _SENTENCE_END.search(sentence_buf)
                    if not m:
                        break
                    sentence = sentence_buf[: m.end()].strip()
                    sentence_buf = sentence_buf[m.end() :]
                    if not sentence:
                        continue
                    if not spoken_any:
                        session["state"] = "SPEAKING"
                        spoken_any = True
                        refresh_ui(live)
                    pcm, ksr = synthesize_sentence_stream(kokoro, sentence, voice)
                    if pcm.size == 0:
                        continue
                    finished = speak_with_optional_barge_in(pcm, ksr, use_barge_in=use_barge)
                    if not finished:
                        console.print("[yellow]Playback interrupted (barge-in).[/]")
                        barge_stopped = True
                        break
                if barge_stopped:
                    break

                if len(sentence_buf) > 200:
                    chunk = sentence_buf.strip()
                    sentence_buf = ""
                    if chunk:
                        if not spoken_any:
                            session["state"] = "SPEAKING"
                            spoken_any = True
                            refresh_ui(live)
                        pcm, ksr = synthesize_sentence_stream(kokoro, chunk, voice)
                        if pcm.size > 0:
                            finished = speak_with_optional_barge_in(pcm, ksr, use_barge_in=use_barge)
                            if not finished:
                                console.print("[yellow]Playback interrupted (barge-in).[/]")
                                barge_stopped = True
                                break

            if not barge_stopped and sentence_buf.strip():
                if not spoken_any:
                    session["state"] = "SPEAKING"
                    spoken_any = True
                    refresh_ui(live)
                pcm, ksr = synthesize_sentence_stream(kokoro, sentence_buf.strip(), voice)
                if pcm.size > 0:
                    finished = speak_with_optional_barge_in(pcm, ksr, use_barge_in=use_barge)
                    if not finished:
                        console.print("[yellow]Playback interrupted (barge-in).[/]")

            session["last_reply"] = cumulative[:500] if cumulative else ""

        if args.dry_run:
            session["state"] = "SPEAKING"
            refresh_ui(live)
            time.sleep(0.3)
        session["state"] = "LISTENING"
        refresh_ui(live)

    try:
        if args.plain:
            while True:
                run_turn(None)
        else:
            with Live(render_session(session), refresh_per_second=8, console=console) as live:
                while True:
                    run_turn(live)

    except KeyboardInterrupt:
        console.print("\n[dim]Exiting.[/]")


if __name__ == "__main__":
    main()

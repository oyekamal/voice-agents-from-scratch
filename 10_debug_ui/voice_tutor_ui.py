"""Voice tutor with a live browser debug console.

Same mic -> Whisper -> Llama -> Kokoro loop as ``09_projects/voice_tutor``, but
every step (state changes, what STT heard, LLM tokens as they stream, TTS
timing, per-turn latency) is broadcast over a WebSocket to a browser page
instead of only printing to the terminal — so you can *see* what the agent
is doing/hearing while you talk to it, for debugging and iterating on
prompts/STT settings.

Run:

    uv sync --extra serve
    uv run python 10_debug_ui/voice_tutor_ui.py
    # open http://localhost:8000

The voice loop runs in a background thread (it's the same blocking
sounddevice/whisper/llama.cpp calls as the terminal version); a queue-drain
task on the asyncio side rebroadcasts each event to every connected
WebSocket client. No frontend build step — one static HTML file.
"""

from __future__ import annotations

import asyncio
import queue
import re
import sys
import threading
from contextlib import asynccontextmanager
import time
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

_CH09 = Path(__file__).resolve().parent.parent / "09_projects"
if str(_CH09) not in sys.path:
    sys.path.insert(0, str(_CH09))
from llama_gguf import resolve_llama_instruct_gguf  # noqa: E402

from voice_agents.agent.agent_core import AgentCore  # noqa: E402
from voice_agents.agent.prompt_engine import PromptEngine  # noqa: E402
from voice_agents.audio.audio_input import AudioInputConfig, record_seconds  # noqa: E402
from voice_agents.audio.audio_output import play_float_mono  # noqa: E402
from voice_agents.stt.streaming_stt import TranscribeConfig, transcribe_samples  # noqa: E402
from kokoro_onnx import Kokoro  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
WHISPER_ROOT = ROOT / "models" / "whisper"
KOKORO_MODEL = ROOT / "models" / "kokoro" / "kokoro-v1.0.onnx"
KOKORO_VOICES = ROOT / "models" / "kokoro" / "voices-v1.0.bin"
RECORD_SECONDS = 6.0

_SENTENCE_END = re.compile(r"([.!?]\s+)")

# Thread-safe: the voice loop (background thread) puts events here;
# an asyncio task on the main loop drains it and broadcasts to clients.
_events: "queue.Queue[dict[str, Any]]" = queue.Queue()
_clients: set[WebSocket] = set()


def _emit(kind: str, **fields: Any) -> None:
    _events.put({"type": kind, "ts": time.time(), **fields})


def _voice_loop() -> None:
    """The actual mic -> STT -> LLM -> TTS loop. Runs in a background thread."""
    _emit("status", text="Loading Whisper (base.en)…")
    tcfg = TranscribeConfig(model_size="base.en", download_root=str(WHISPER_ROOT), device="cpu")
    warm = np.zeros(int(0.25 * 16_000), dtype=np.float32)
    from faster_whisper import WhisperModel

    whisper = WhisperModel(
        tcfg.model_size, device=tcfg.device, compute_type=tcfg.compute_type,
        download_root=tcfg.download_root,
    )
    transcribe_samples(warm, 16_000, config=tcfg, whisper_model=whisper)

    _emit("status", text="Loading Llama (GGUF mmap)…")
    llm_path = resolve_llama_instruct_gguf(ROOT)
    if llm_path is None:
        _emit("error", text="No Llama 3.x instruct GGUF under models/llm/.")
        return
    agent = AgentCore(model_path=str(llm_path), chat_template="llama3", n_ctx=8192)
    agent.preload()
    engine = PromptEngine(
        system_prompt=(
            "You are a patient tutor. Give a short explanation then one practice question. "
            "Keep replies under three sentences. Remember what the learner already asked "
            "when they follow up."
        )
    )

    _emit("status", text="Loading Kokoro…")
    k = Kokoro(str(KOKORO_MODEL), str(KOKORO_VOICES))
    voice = "af_heart" if "af_heart" in k.get_voices() else k.get_voices()[0]
    k.create("Hi.", voice=voice, speed=1.0)

    _emit("ready")

    turn = 0
    while True:
        turn += 1
        _emit("state", value="listening", turn=turn, seconds=RECORD_SECONDS)
        audio, sr = record_seconds(RECORD_SECONDS, config=AudioInputConfig())
        t_recorded = time.perf_counter()

        _emit("state", value="thinking", turn=turn)
        text = transcribe_samples(audio, sr, config=tcfg, whisper_model=whisper).strip()
        t_stt = time.perf_counter()
        _emit("transcript", turn=turn, text=text or "(no speech detected)", stt_ms=round((t_stt - t_recorded) * 1000))

        if not text:
            continue
        if text.lower() in {"quit", "exit", "goodbye"}:
            _emit("status", text="Session ended.")
            break

        _emit("state", value="speaking", turn=turn)
        buf = ""
        full_reply = ""
        t_first_token: float | None = None
        for piece in agent.stream_tokens(text, engine=engine, max_tokens=256):
            if t_first_token is None:
                t_first_token = time.perf_counter()
                _emit("llm_first_token", turn=turn, ms=round((t_first_token - t_stt) * 1000))
            buf += piece
            full_reply += piece
            _emit("llm_token", turn=turn, token=piece)
            while True:
                m = _SENTENCE_END.search(buf)
                if not m:
                    break
                chunk = buf[: m.end()].strip()
                buf = buf[m.end():]
                if chunk:
                    samples, ksr = k.create(chunk, voice=voice, speed=1.0)
                    play_float_mono(samples, int(ksr))
            if len(buf) > 200:
                chunk = buf.strip()
                buf = ""
                if chunk:
                    samples, ksr = k.create(chunk, voice=voice, speed=1.0)
                    play_float_mono(samples, int(ksr))
        if buf.strip():
            samples, ksr = k.create(buf.strip(), voice=voice, speed=1.0)
            play_float_mono(samples, int(ksr))

        t_done = time.perf_counter()
        _emit(
            "turn_complete",
            turn=turn,
            reply=full_reply.strip(),
            total_ms=round((t_done - t_recorded) * 1000),
        )


@asynccontextmanager
async def _lifespan(app: FastAPI):
    threading.Thread(target=_voice_loop, daemon=True).start()
    drain_task = asyncio.create_task(_drain_events())
    yield
    drain_task.cancel()


app = FastAPI(lifespan=_lifespan)
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    _clients.add(websocket)
    try:
        while True:
            await websocket.receive_text()  # client sends nothing meaningful; just keep the connection open
    except WebSocketDisconnect:
        _clients.discard(websocket)


async def _drain_events() -> None:
    while True:
        try:
            while True:
                event = _events.get_nowait()
                dead = []
                for ws in _clients:
                    try:
                        await ws.send_json(event)
                    except Exception:
                        dead.append(ws)
                for ws in dead:
                    _clients.discard(ws)
        except queue.Empty:
            pass
        await asyncio.sleep(0.05)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

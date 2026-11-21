import asyncio
import json
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import config
import db
import prompts
import services


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_db()
    yield


app = FastAPI(title="Voice Role-Play Coach", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class SessionConfig(BaseModel):
    scenario: Literal["laptops", "saas", "car"]
    personality: Literal["friendly", "skeptical", "impatient", "indecisive", "analytical"]
    difficulty: Literal["easy", "medium", "hard"]
    budget: int = Field(gt=0, le=10_000_000)


@app.get("/api/health")
def health():
    return {"status": "ok", "groq_key_set": bool(config.GROQ_API_KEY)}


@app.get("/api/options")
def get_options():
    return prompts.options()


@app.post("/api/sessions")
async def create_session(cfg: SessionConfig):
    return {"session_id": await db.create_session(cfg.model_dump())}


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    session = await db.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return jsonable_encoder(session)


@app.post("/api/sessions/{session_id}/evaluate")
async def evaluate_session(session_id: str):
    session = await db.get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    if not session["messages"]:
        raise HTTPException(400, "Nothing to evaluate yet: have a conversation first.")
    try:
        result = await services.evaluate(session["config"], session["messages"])
    except services.ConfigError as e:
        raise HTTPException(500, str(e))
    except Exception as e:
        raise HTTPException(502, f"Evaluation failed: {e}")
    await db.save_evaluation(session_id, result)
    return result


async def run_turn(ws: WebSocket, session_id: str, system: str, user_text: str) -> None:
    """One conversation turn: history -> streamed LLM -> TTS per sentence -> client -> save."""
    session = await db.get_session(session_id)
    history = [{"role": m["role"], "content": m["content"]} for m in session["messages"]]
    history = history[-config.MAX_HISTORY_MESSAGES :] + [{"role": "user", "content": user_text}]

    # The producer writes sentences and starts TTS for each immediately, in the background,
    # while the consumer below sends results to the browser in order.
    queue: asyncio.Queue = asyncio.Queue()

    async def produce():
        try:
            async for sentence in services.stream_sentences(system, history):
                task = asyncio.create_task(services.synthesize(sentence))
                tts_tasks.append(task)
                queue.put_nowait((sentence, task))
        finally:
            queue.put_nowait(None)  # always signal the end, even on error

    producer = asyncio.create_task(produce())
    reply: list[str] = []
    tts_tasks: list[asyncio.Task] = []
    try:
        while (item := await queue.get()) is not None:
            sentence, tts_task = item
            reply.append(sentence)
            await ws.send_json({"type": "reply_text", "text": sentence})
            await ws.send_bytes(await tts_task)
        await producer  # re-raises any LLM error
    finally:
        # Don't leave orphaned background work if the LLM failed or the client left.
        producer.cancel()
        for t in tts_tasks:
            t.cancel()
        await asyncio.gather(producer, *tts_tasks, return_exceptions=True)

    await db.add_messages(session_id, [("user", user_text), ("assistant", " ".join(reply))])
    await ws.send_json({"type": "done"})


@app.websocket("/ws/{session_id}")
async def conversation(ws: WebSocket, session_id: str):
    """Client sends: binary audio frames then {"type":"end_audio","ext":"webm"},
    or {"type":"text","text":"..."}.
    Server sends: transcript, reply_text (+ binary MP3 frame), done, error."""
    await ws.accept()
    session = await db.get_session(session_id)
    if not session:
        await ws.send_json({"type": "error", "message": "Session not found"})
        await ws.close()
        return
    system = prompts.customer_prompt(session["config"])
    audio = bytearray()

    try:
        while True:
            msg = await ws.receive()
            if msg["type"] == "websocket.disconnect":
                break
            if msg.get("bytes"):
                audio.extend(msg["bytes"])
                continue
            if not msg.get("text"):
                continue
            data = json.loads(msg["text"])
            try:
                user_text = ""
                if data.get("type") == "end_audio":
                    chunk, audio = bytes(audio), bytearray()
                    if chunk:
                        user_text = await services.transcribe(chunk, data.get("ext", "webm"))
                elif data.get("type") == "text":
                    user_text = str(data.get("text", "")).strip()[:1000]
                if not user_text:
                    await ws.send_json({"type": "error", "message": "I didn't catch that. Try again."})
                    await ws.send_json({"type": "done"})
                    continue
                await ws.send_json({"type": "transcript", "text": user_text})
                await run_turn(ws, session_id, system, user_text)
            except WebSocketDisconnect:
                raise
            except Exception as e:  # report the problem but keep the connection open
                await ws.send_json({"type": "error", "message": str(e)})
                await ws.send_json({"type": "done"})
    except WebSocketDisconnect:
        pass

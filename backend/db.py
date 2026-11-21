"""Session storage. Uses MongoDB, falling back to memory if MongoDB is unreachable."""
import copy
import uuid
from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorClient

import config

_client = AsyncIOMotorClient(config.MONGO_URI, serverSelectionTimeoutMS=2000)
_sessions = _client[config.MONGO_DB]["sessions"]
_memory: dict[str, dict] = {}
_use_memory = False


async def init_db() -> None:
    global _use_memory
    try:
        await _client.admin.command("ping")
        print("MongoDB connected.")
    except Exception as e:
        _use_memory = True
        print(f"WARNING: MongoDB unavailable ({type(e).__name__}). Using in-memory storage; data is lost on restart.")


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def create_session(cfg: dict) -> str:
    doc = {
        "_id": uuid.uuid4().hex,
        "config": cfg,
        "messages": [],
        "created_at": _now(),
        "evaluation": None,
    }
    if _use_memory:
        _memory[doc["_id"]] = doc
    else:
        await _sessions.insert_one(doc)
    return doc["_id"]


async def get_session(session_id: str) -> dict | None:
    if _use_memory:
        doc = _memory.get(session_id)
        return copy.deepcopy(doc) if doc else None
    return await _sessions.find_one({"_id": session_id})


async def add_messages(session_id: str, role_texts: list[tuple[str, str]]) -> None:
    msgs = [{"role": r, "content": t, "ts": _now()} for r, t in role_texts]
    if _use_memory:
        _memory[session_id]["messages"].extend(msgs)
    else:
        await _sessions.update_one({"_id": session_id}, {"$push": {"messages": {"$each": msgs}}})


async def save_evaluation(session_id: str, evaluation: dict) -> None:
    if _use_memory:
        _memory[session_id]["evaluation"] = evaluation
    else:
        await _sessions.update_one({"_id": session_id}, {"$set": {"evaluation": evaluation, "ended_at": _now()}})

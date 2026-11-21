"""External AI services: speech-to-text, LLM (streaming), text-to-speech, evaluation."""
import json
import re
from typing import AsyncIterator

import edge_tts
from openai import AsyncOpenAI

import config
import prompts

# Groq exposes an OpenAI-compatible API, so the openai package works with a different base_url.
_client = AsyncOpenAI(api_key=config.GROQ_API_KEY or "missing", base_url=config.GROQ_BASE_URL)

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
_AUDIO_EXTS = {"webm", "ogg", "mp4", "m4a", "wav", "mp3"}


class ConfigError(Exception):
    pass


def _require_key() -> None:
    if not config.GROQ_API_KEY:
        raise ConfigError("GROQ_API_KEY is not set. Add it to backend/.env and restart the server.")


async def transcribe(audio: bytes, ext: str = "webm") -> str:
    """Speech -> text."""
    _require_key()
    ext = ext if ext in _AUDIO_EXTS else "webm"
    result = await _client.audio.transcriptions.create(
        model=config.STT_MODEL, file=(f"speech.{ext}", audio), language="en"
    )
    return result.text.strip()


async def stream_sentences(system: str, history: list[dict]) -> AsyncIterator[str]:
    """Stream the LLM reply and yield each COMPLETE sentence as soon as it forms,
    so text-to-speech can start before the whole reply is written."""
    _require_key()
    stream = await _client.chat.completions.create(
        model=config.LLM_MODEL,
        messages=[{"role": "system", "content": system}, *history],
        max_tokens=200,
        temperature=0.8,
        stream=True,
    )
    buf = ""
    async for chunk in stream:
        if not chunk.choices:
            continue
        buf += chunk.choices[0].delta.content or ""
        parts = _SENTENCE_END.split(buf)
        for sentence in parts[:-1]:
            if sentence.strip():
                yield sentence.strip()
        buf = parts[-1]
    if buf.strip():
        yield buf.strip()


async def synthesize(text: str) -> bytes:
    """Text -> speech (MP3 bytes) using Microsoft Edge voices via edge-tts (free)."""
    out = bytearray()
    async for chunk in edge_tts.Communicate(text, config.TTS_VOICE).stream():
        if chunk["type"] == "audio":
            out.extend(chunk["data"])
    if not out:
        raise RuntimeError("Text-to-speech returned no audio.")
    return bytes(out)


def _clamp(value, default=5) -> int:
    try:
        return max(1, min(10, int(value)))
    except (TypeError, ValueError):
        return default


async def evaluate(cfg: dict, messages: list[dict]) -> dict:
    """Ask the LLM to grade the salesperson, then normalise the JSON it returns."""
    _require_key()
    transcript = "\n".join(
        f"{'Salesperson' if m['role'] == 'user' else 'Customer'}: {m['content']}" for m in messages
    )
    resp = await _client.chat.completions.create(
        model=config.LLM_MODEL,
        messages=[{"role": "user", "content": prompts.evaluation_prompt(cfg, transcript)}],
        temperature=0.3,
        response_format={"type": "json_object"},
    )
    try:
        raw = json.loads(resp.choices[0].message.content)
    except json.JSONDecodeError:
        raw = {}
    keys = ["rapport", "discovery", "value_presentation", "objection_handling", "closing"]
    scores = {k: _clamp((raw.get("scores") or {}).get(k)) for k in keys}
    return {
        "scores": scores,
        "overall": _clamp(raw.get("overall"), round(sum(scores.values()) / len(scores))),
        "outcome": str(raw.get("outcome", "")),
        "strengths": [str(s) for s in raw.get("strengths", [])][:4],
        "improvements": [str(s) for s in raw.get("improvements", [])][:4],
        "summary": str(raw.get("summary", "")),
    }

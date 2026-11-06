import asyncio
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from voxwire.core.auth import rate_limit, require_api_key
from voxwire.core.config import settings
from voxwire.core import store
from voxwire.core.ice_config import get_ice_config
from voxwire.core.session_manager import make_token, sessions
from voxwire.services.providers import resolve_provider
from voxwire.services.recorder import recording_path

router = APIRouter(dependencies=[Depends(require_api_key)])


class Tool(BaseModel):
    name: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    description: str = ""
    parameters: dict = Field(default_factory=lambda: {"type": "object", "properties": {}})


class SessionCreate(BaseModel):
    system_prompt: Optional[str] = Field(default=None, max_length=20_000)
    provider: Optional[Literal["gemini", "openai", "echo"]] = None
    voice: Optional[str] = None
    model: Optional[str] = None
    ttl_seconds: Optional[int] = Field(default=None, ge=10, le=86_400)
    metadata: dict = Field(default_factory=dict)
    tools: list[Tool] = Field(default_factory=list, max_length=64)
    tool_webhook_url: Optional[str] = None
    webhook_url: Optional[str] = None
    record: bool = False


def new_session(req: SessionCreate, key: str, channel: str = "webrtc"):
    """Shared by the REST API and phone calls: checks limits, then creates the session."""
    rate_limit(key)
    if sessions.active_count() >= settings.MAX_CONCURRENT_CALLS:
        raise HTTPException(429, "server is at its concurrent call limit")
    if req.provider and resolve_provider(req.provider) != req.provider:
        raise HTTPException(422, f"provider {req.provider!r} is not configured on this server")
    if req.tools and not req.tool_webhook_url:
        raise HTTPException(422, "tools need a tool_webhook_url")
    if req.record and not settings.RECORDINGS_DIR:
        raise HTTPException(422, "recording is disabled on this server (set RECORDINGS_DIR)")
    fields = req.model_dump(exclude={"ttl_seconds"})
    fields["tools"] = [t.model_dump() for t in req.tools]
    fields["webhook_url"] = req.webhook_url or settings.WEBHOOK_URL or None
    fields["provider"] = resolve_provider(req.provider)
    return sessions.create(ttl_seconds=req.ttl_seconds, api_key=key, channel=channel, **fields)


@router.post("/session")
async def create_session(req: SessionCreate, key: str = Depends(require_api_key)):
    s = new_session(req, key)
    return {**s.public(), "token": make_token(s.id, s.expires_at), "ice_servers": get_ice_config()["iceServers"]}


def _live(session_id: str, key: str):
    """A session this key owns that is still in memory, or None. Keys never see each other's calls."""
    s = sessions.get(session_id)
    return s if s and (key == "dev" or s.api_key == key) else None


def _any(session_id: str, key: str) -> dict:
    """Live session, else the call log. 404 if neither."""
    s = _live(session_id, key)
    if s:
        return {**s.public(), "transcript": s.transcript}
    row = store.get(session_id, key)
    if not row:
        raise HTTPException(404, "session not found")
    return row


@router.get("/sessions")
async def list_sessions(limit: int = 50, key: str = Depends(require_api_key)):
    """Recent ended calls (from the call log) plus calls still in progress."""
    live = [s.public() for s in sessions.all() if key == "dev" or s.api_key == key]
    return {"active": [s for s in live if s["status"] != "ended"], "recent": store.recent(key, min(limit, 500))}


@router.get("/usage")
async def get_usage(days: int = 30, key: str = Depends(require_api_key)):
    return {**store.usage(key, min(days, 365)), "active_calls": sessions.active_count()}


@router.get("/session/{session_id}")
async def get_session(session_id: str, key: str = Depends(require_api_key)):
    data = _any(session_id, key)
    data.pop("transcript", None)
    return data


@router.get("/session/{session_id}/transcript")
async def get_transcript(session_id: str, key: str = Depends(require_api_key)):
    data = _any(session_id, key)
    return {"session_id": session_id, "status": data["status"], "transcript": data["transcript"]}


@router.get("/session/{session_id}/recording/{side}")
async def get_recording(session_id: str, side: Literal["user", "ai"], key: str = Depends(require_api_key)):
    _any(session_id, key)  # ownership check
    path = recording_path(session_id, side)
    if not path or not path.exists():
        raise HTTPException(404, "no recording")
    return FileResponse(path, media_type="audio/wav")


@router.delete("/session/{session_id}")
async def delete_session(session_id: str, key: str = Depends(require_api_key)):
    s = _live(session_id, key)
    if not s:
        raise HTTPException(404, "session not found")
    if s.ws is not None:
        # Don't await the close handshake: an unresponsive client would hang this request.
        # signaling's finally block does the cleanup once the socket drops.
        asyncio.create_task(s.ws.close(code=4000, reason="ended by API"))
    sessions.finish(s, reason="api")
    return {"ok": True}

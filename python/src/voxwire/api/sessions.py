import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from voxwire.core.auth import rate_limit, require_api_key
from voxwire.core.config import settings
from voxwire.core.session_manager import make_token, sessions

router = APIRouter(dependencies=[Depends(require_api_key)])


class SessionCreate(BaseModel):
    system_prompt: Optional[str] = Field(default=None, max_length=20_000)
    voice: Optional[str] = None
    model: Optional[str] = None
    ttl_seconds: Optional[int] = Field(default=None, ge=10, le=86_400)
    metadata: dict = Field(default_factory=dict)


@router.post("/session")
async def create_session(req: SessionCreate, key: str = Depends(require_api_key)):
    rate_limit(key)
    if sessions.active_count() >= settings.MAX_CONCURRENT_CALLS:
        raise HTTPException(429, "server is at its concurrent call limit")
    s = sessions.create(req.system_prompt, req.voice, req.model, req.metadata, req.ttl_seconds)
    return {**s.public(), "token": make_token(s.id, s.expires_at)}


@router.get("/session/{session_id}")
async def get_session(session_id: str):
    s = sessions.get(session_id)
    if not s:
        raise HTTPException(404, "session not found")
    return s.public()


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    s = sessions.get(session_id)
    if not s:
        raise HTTPException(404, "session not found")
    if s.ws is not None:
        # Don't await the close handshake: an unresponsive client would hang this request.
        # signaling's finally block does the cleanup once the socket drops.
        asyncio.create_task(s.ws.close(code=4000, reason="ended by API"))
    sessions.finish(s)
    return {"ok": True}

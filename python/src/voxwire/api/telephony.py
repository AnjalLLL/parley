"""Phone calls through Twilio: inbound webhook, media stream WebSocket, outbound calls."""
import asyncio
import json
import logging
from urllib.parse import parse_qsl

import aiohttp
from fastapi import APIRouter, Depends, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from pydantic import Field

from voxwire.api.sessions import SessionCreate, new_session
from voxwire.core.auth import require_api_key
from voxwire.core.config import settings
from voxwire.core.session_manager import make_token, sessions, verify_token
from voxwire.services.audio_pipeline import AudioPipeline
from voxwire.services.twilio_bridge import TwilioBridge, stream_twiml, valid_signature

router = APIRouter()
logger = logging.getLogger(__name__)


def _require_phone():
    if not (settings.TWILIO_AUTH_TOKEN and settings.PUBLIC_URL):
        raise HTTPException(503, "phone calls are not configured (TWILIO_AUTH_TOKEN, PUBLIC_URL)")


@router.post("/twilio/voice")
async def inbound_call(request: Request):
    """Point your Twilio number's voice webhook here."""
    _require_phone()
    params = dict(parse_qsl((await request.body()).decode()))
    url = settings.PUBLIC_URL.rstrip("/") + "/twilio/voice"
    if not valid_signature(url, params, request.headers.get("X-Twilio-Signature", "")):
        raise HTTPException(403, "bad Twilio signature")
    req = SessionCreate(
        system_prompt=settings.PHONE_SYSTEM_PROMPT,
        metadata={"from": params.get("From"), "to": params.get("To"), "call_sid": params.get("CallSid")},
    )
    s = new_session(req, key="twilio", channel="phone")
    return Response(stream_twiml(s.id, make_token(s.id, s.expires_at)), media_type="application/xml")


class OutboundCall(SessionCreate):
    to: str = Field(pattern=r"^\+[1-9]\d{6,14}$")  # E.164


@router.post("/api/call", tags=["Phone"])
async def outbound_call(req: OutboundCall, key: str = Depends(require_api_key)):
    """Have the AI call a phone number."""
    _require_phone()
    if not (settings.TWILIO_ACCOUNT_SID and settings.TWILIO_FROM_NUMBER):
        raise HTTPException(503, "set TWILIO_ACCOUNT_SID and TWILIO_FROM_NUMBER for outbound calls")
    s = new_session(SessionCreate(**req.model_dump(exclude={"to"})), key=key, channel="phone")
    s.metadata = {**s.metadata, "to": req.to}
    url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Calls.json"
    twiml = stream_twiml(s.id, make_token(s.id, s.expires_at))
    form = {"To": req.to, "From": settings.TWILIO_FROM_NUMBER, "Twiml": twiml}
    auth = aiohttp.BasicAuth(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as http:
        async with http.post(url, data=form, auth=auth) as resp:
            body = await resp.json(content_type=None)
            if resp.status >= 300:
                sessions.finish(s, "dial_failed")
                raise HTTPException(502, f"Twilio refused the call: {body.get('message', body)}")
    s.metadata["call_sid"] = body.get("sid")
    return s.public()


@router.websocket("/twilio/stream/{session_id}")
async def media_stream(websocket: WebSocket, session_id: str):
    await websocket.accept()
    session = sessions.get(session_id)
    bridge = TwilioBridge(websocket)
    pipeline, reason = None, "hangup"
    try:
        # Twilio sends "connected" then "start"; the token arrives in start.customParameters.
        while bridge.stream_sid is None:
            msg = json.loads(await websocket.receive_text())
            if msg.get("event") == "start":
                bridge.stream_sid = msg["start"]["streamSid"]
                token = msg["start"].get("customParameters", {}).get("token")
        if not session or session.status != "waiting" or not verify_token(session_id, token):
            await websocket.close(code=4401, reason="invalid session or token")
            return
        sessions.start(session, websocket)
        pipeline = AudioPipeline(session, bridge, websocket)
        asyncio.create_task(pipeline.run())
        deadline = asyncio.get_running_loop().time() + settings.MAX_CALL_SECONDS
        while True:
            timeout = deadline - asyncio.get_running_loop().time()
            msg = json.loads(await asyncio.wait_for(websocket.receive_text(), timeout))
            if msg.get("event") == "media":
                bridge.feed(msg["media"]["payload"])
            elif msg.get("event") == "stop":
                break
    except asyncio.TimeoutError:
        reason = "max_duration"
        await websocket.close()
    except (WebSocketDisconnect, RuntimeError):
        pass
    except Exception as e:
        logger.error(f"[{session_id}] phone stream error: {e}")
    finally:
        bridge.close()
        if pipeline:
            if pipeline.failed:
                sessions.ai_errors_total += 1
                reason = "ai_error"
            await pipeline.stop()
        if session and session.status == "active":
            sessions.finish(session, reason)

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from voxwire.core.config import settings
from voxwire.core.session_manager import sessions, verify_token
from voxwire.services.audio_pipeline import AudioPipeline
from voxwire.services.pion_client import PionClient

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/ws/signaling/{session_id}")
async def signaling(websocket: WebSocket, session_id: str):
    await websocket.accept()
    session = sessions.get(session_id)
    if not session or session.status != "waiting":
        await websocket.close(code=4404, reason="unknown, expired or used session")
        return
    if not verify_token(session_id, websocket.query_params.get("token")):
        await websocket.close(code=4401, reason="invalid token")
        return
    if sessions.active_count() >= settings.MAX_CONCURRENT_CALLS:
        await websocket.close(code=4429, reason="concurrent call limit reached")
        return

    sessions.start(session, websocket)
    logger.info(f"[{session_id}] WebSocket connected")
    pion = PionClient()
    pipeline = None

    async def hang_up_at_limit():
        await asyncio.sleep(settings.MAX_CALL_SECONDS)
        logger.info(f"[{session_id}] max call duration reached")
        await websocket.close(code=4408, reason="max call duration reached")

    limit_task = asyncio.create_task(hang_up_at_limit())
    try:
        try:
            await pion.create_session(session_id)
        except Exception as e:
            logger.error(f"[{session_id}] SFU unavailable: {e}")
            await websocket.close(code=1011, reason="media server unavailable")
            return
        while True:
            msg = json.loads(await websocket.receive_text())
            if msg["type"] == "offer" and pipeline is None:
                answer_sdp = await pion.process_offer(session_id, msg["sdp"])
                await websocket.send_json({"type": "answer", "sdp": answer_sdp})
                pipeline = AudioPipeline(session_id, pion, websocket, system_prompt=session.system_prompt)
                asyncio.create_task(pipeline.run())
                logger.info(f"[{session_id}] audio pipeline started")
            elif msg["type"] == "ice-candidate":
                await pion.add_ice_candidate(session_id, msg["candidate"])
    except (WebSocketDisconnect, RuntimeError):
        logger.info(f"[{session_id}] WebSocket disconnected")
    except Exception as e:
        logger.error(f"[{session_id}] signaling error: {e}")
    finally:
        limit_task.cancel()
        if pipeline:
            if pipeline.failed:
                sessions.ai_errors_total += 1
            await pipeline.stop()
        await pion.end_session(session_id)
        await pion.close()
        sessions.finish(session)

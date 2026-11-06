import json
import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from services.pion_client import PionClient
from services.audio_pipeline import AudioPipeline
from core.session_manager import SessionManager

router = APIRouter()
logger = logging.getLogger(__name__)

@router.websocket("/ws/signaling/{session_id}")
async def signaling(websocket: WebSocket, session_id: str):
    await websocket.accept()
    logger.info(f"WebSocket connected for session: {session_id}")
    
    pion = PionClient()
    pipeline = None

    try:
        # Create session in Pion
        await pion.create_session(session_id)
        
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            logger.debug(f"Received message: {msg['type']}")

            if msg["type"] == "offer" and pipeline is None:
                answer_sdp = await pion.process_offer(session_id, msg["sdp"])
                await websocket.send_json({"type": "answer", "sdp": answer_sdp})
                
                # Start the audio pipeline
                pipeline = AudioPipeline(session_id, pion, websocket)
                asyncio.create_task(pipeline.run())
                logger.info(f"Audio pipeline started for session: {session_id}")

            elif msg["type"] == "ice-candidate":
                await pion.add_ice_candidate(session_id, msg["candidate"])

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session: {session_id}")
    except Exception as e:
        logger.error(f"Error in signaling: {e}")
    finally:
        if pipeline:
            await pipeline.stop()
        await pion.end_session(session_id)
        await pion.close()

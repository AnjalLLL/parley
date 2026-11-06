import grpc
import json
import logging
from voxwire.proto import sfu_pb2, sfu_pb2_grpc
from voxwire.core.config import settings

logger = logging.getLogger(__name__)

class PionClient:
    def __init__(self):
        self.channel = grpc.aio.insecure_channel(settings.PION_GRPC_URL)
        self.stub = sfu_pb2_grpc.SFUServiceStub(self.channel)
        # Unary calls only; the audio streams live as long as the call.
        self.timeout = settings.SFU_TIMEOUT_SECONDS

    async def create_session(self, session_id: str):
        req = sfu_pb2.CreateSessionRequest(session_id=session_id)
        return await self.stub.CreateSession(req, timeout=self.timeout)

    async def process_offer(self, session_id: str, sdp: str) -> str:
        req = sfu_pb2.OfferRequest(session_id=session_id, sdp=sdp)
        res = await self.stub.ProcessOffer(req, timeout=self.timeout)
        return res.sdp

    async def add_ice_candidate(self, session_id: str, candidate: dict):
        candidate_json = json.dumps(candidate)
        req = sfu_pb2.IceCandidateRequest(session_id=session_id, candidate_json=candidate_json)
        await self.stub.AddIceCandidate(req, timeout=self.timeout)

    async def stream_audio_to_pion(self, session_id: str, pcm_stream, sample_rate: int):
        """Send TTS/AI PCM audio to Pion for WebRTC playback"""
        async def request_generator():
            async for chunk in pcm_stream:
                yield sfu_pb2.AudioChunk(
                    session_id=session_id,
                    pcm_data=chunk,
                    sample_rate=sample_rate
                )
        try:
            await self.stub.StreamAudioToPion(request_generator())
        except Exception as e:
            logger.error(f"Error streaming audio to Pion: {e}")

    async def stream_audio_from_pion(self, session_id: str):
        """Receive user PCM audio from Pion"""
        req = sfu_pb2.SessionID(session_id=session_id)
        try:
            async for chunk in self.stub.StreamAudioFromPion(req):
                yield chunk.pcm_data
        except Exception as e:
            logger.error(f"Error streaming audio from Pion: {e}")

    async def end_session(self, session_id: str):
        try:
            await self.stub.EndSession(sfu_pb2.SessionID(session_id=session_id), timeout=self.timeout)
        except Exception as e:
            logger.error(f"Error ending Pion session: {e}")

    async def close(self):
        await self.channel.close()

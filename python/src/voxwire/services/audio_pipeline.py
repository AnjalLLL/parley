import asyncio
import logging
from voxwire.services.pion_client import PionClient
from voxwire.services.gemini_client import make_ai_client

logger = logging.getLogger(__name__)


class AudioPipeline:
    def __init__(self, session_id: str, pion: PionClient, ws, system_prompt: str | None = None, ai=None):
        self.session_id = session_id
        self.system_prompt = system_prompt
        self.failed = False
        self.pion = pion
        self.ws = ws
        self.ai = ai or make_ai_client()
        self._tasks = []

    async def run(self):
        try:
            if self.system_prompt:
                await self.ai.connect(system_prompt=self.system_prompt)
            else:
                await self.ai.connect()
            self._tasks = [
                asyncio.create_task(self._user_audio_loop()),
                asyncio.create_task(self._ai_audio_loop()),
            ]
            await asyncio.gather(*self._tasks)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.failed = True
            logger.error(f"[{self.session_id}] audio pipeline failed: {e}")
            await self.ws.close(code=1011)

    async def _user_audio_loop(self):
        """Pion -> AI: stream user audio (16kHz PCM)"""
        async for pcm_chunk in self.pion.stream_audio_from_pion(self.session_id):
            await self.ai.send_audio(pcm_chunk)

    async def _ai_audio_loop(self):
        """AI -> Pion: one long-lived gRPC stream; Pion paces playback in real time"""
        async def chunks():
            while True:
                yield await self.ai.get_response_audio()

        await self.pion.stream_audio_to_pion(self.session_id, chunks(), self.ai.output_rate)

    async def stop(self):
        for task in self._tasks:
            task.cancel()
        await self.ai.close()
        logger.info("Audio pipeline stopped")

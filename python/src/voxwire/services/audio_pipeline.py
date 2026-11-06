import asyncio
import logging

from voxwire.core.session_manager import Session, sessions
from voxwire.services import webhooks
from voxwire.services.providers import make_ai_client
from voxwire.services.recorder import Recorder

logger = logging.getLogger(__name__)


class AudioPipeline:
    """Moves audio between a media transport (Pion SFU or a phone bridge) and the AI provider.

    The transport needs stream_audio_from_pion(session_id) -> async iter of 16 kHz PCM, and
    stream_audio_to_pion(session_id, async iter of PCM, sample_rate).
    """

    def __init__(self, session: Session, transport, ws, ai=None):
        self.session = session
        self.session_id = session.id
        self.pion = transport
        self.ws = ws
        self.failed = False
        self.ai = ai or make_ai_client(
            session.provider,
            model=session.model,
            voice=session.voice,
            tools=session.tools,
            on_tool_call=self._tool_call if session.tools else None,
            on_transcript=lambda role, text: sessions.add_transcript(session, role, text),
        )
        self.recorder = Recorder(session.id, self.ai.output_rate) if session.record else None
        self._tasks = []

    async def _tool_call(self, name: str, args: dict) -> dict:
        logger.info(f"[{self.session_id}] tool call {name}")
        return await webhooks.call_tool(self.session.tool_webhook_url, self.session_id, name, args)

    async def run(self):
        try:
            if self.session.system_prompt:
                await self.ai.connect(system_prompt=self.session.system_prompt)
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
        """Transport -> AI: user audio (16kHz PCM)"""
        async for pcm_chunk in self.pion.stream_audio_from_pion(self.session_id):
            if self.recorder:
                self.recorder.write("user", pcm_chunk)
            await self.ai.send_audio(pcm_chunk)

    async def _ai_audio_loop(self):
        """AI -> transport: one long-lived stream; the transport paces playback in real time"""
        async def chunks():
            while True:
                chunk = await self.ai.get_response_audio()
                if self.recorder:
                    self.recorder.write("ai", chunk)
                yield chunk

        await self.pion.stream_audio_to_pion(self.session_id, chunks(), self.ai.output_rate)

    async def stop(self):
        for task in self._tasks:
            task.cancel()
        await self.ai.close()
        if self.recorder:
            self.recorder.close()
        logger.info(f"[{self.session_id}] audio pipeline stopped")

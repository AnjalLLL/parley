import asyncio
import contextlib
import logging
from google import genai
from google.genai import types
from voxwire.core.config import settings

logger = logging.getLogger(__name__)

GEMINI_OUTPUT_RATE = 24000


class GeminiLiveClient:
    """Gemini Live: send 16kHz PCM in, get 24kHz PCM out. Gemini's server-side VAD handles turns and barge-in."""

    output_rate = GEMINI_OUTPUT_RATE

    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY, http_options={"api_version": "v1beta"})
        self.session = None
        self._stack = contextlib.AsyncExitStack()
        self._response_queue: asyncio.Queue = asyncio.Queue()
        self._recv_task = None

    async def connect(self, system_prompt: str = "You are a helpful AI assistant on a voice call."):
        logger.info(f"Connecting to Gemini Live API with model {settings.GEMINI_MODEL}")
        # live.connect() is an async context manager, not an awaitable
        self.session = await self._stack.enter_async_context(
            self.client.aio.live.connect(
                model=settings.GEMINI_MODEL,
                config=types.LiveConnectConfig(
                    response_modalities=[types.Modality.AUDIO],
                    system_instruction=system_prompt,
                ),
            )
        )
        self._recv_task = asyncio.create_task(self._receive_loop())
        logger.info("Connected to Gemini Live API")

    async def _receive_loop(self):
        try:
            while True:  # receive() ends after each turn, so loop forever
                async for message in self.session.receive():
                    if message.data:
                        await self._response_queue.put(message.data)
                    sc = message.server_content
                    if sc and sc.interrupted:
                        self._clear_queue()  # user barged in: drop unplayed AI audio
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in Gemini receive loop: {e}")

    def _clear_queue(self):
        while not self._response_queue.empty():
            self._response_queue.get_nowait()

    async def send_audio(self, pcm_16khz: bytes):
        try:
            await self.session.send_realtime_input(
                audio=types.Blob(data=pcm_16khz, mime_type="audio/pcm;rate=16000")
            )
        except Exception as e:
            logger.error(f"Error sending audio to Gemini: {e}")

    async def get_response_audio(self) -> bytes:
        return await self._response_queue.get()

    async def close(self):
        if self._recv_task:
            self._recv_task.cancel()
        await self._stack.aclose()
        logger.info("Gemini session closed")


class EchoClient:
    """No-API-key stand-in: plays the caller's own audio back. Tests WebRTC + gRPC + codec path end to end."""

    output_rate = 16000

    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()

    async def connect(self, system_prompt: str = ""):
        logger.warning("GEMINI_API_KEY not set: running in ECHO mode (you will hear yourself)")

    async def send_audio(self, pcm_16khz: bytes):
        await self._queue.put(pcm_16khz)

    async def get_response_audio(self) -> bytes:
        return await self._queue.get()

    async def close(self):
        pass


def make_ai_client():
    key = settings.GEMINI_API_KEY
    return GeminiLiveClient() if key and key != "your_key_here" else EchoClient()

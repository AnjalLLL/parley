"""OpenAI Realtime over WebSocket: 24 kHz PCM both ways (we upsample the 16 kHz input)."""
import asyncio
import base64
import json
import logging

import websockets

from voxwire.core.config import settings
from voxwire.utils.audio_codec import resample_pcm16

logger = logging.getLogger(__name__)

OPENAI_RATE = 24000


class OpenAIRealtimeClient:
    output_rate = OPENAI_RATE

    def __init__(self, model=None, voice=None, tools=None, on_tool_call=None, on_transcript=None):
        self.model = model or settings.OPENAI_REALTIME_MODEL
        self.voice = voice or "alloy"
        self.tools = tools or []
        self.on_tool_call = on_tool_call
        self.on_transcript = on_transcript
        self.ws = None
        self._queue: asyncio.Queue = asyncio.Queue()
        self._recv_task = None

    def session_config(self, system_prompt: str) -> dict:
        audio_fmt = {"type": "audio/pcm", "rate": OPENAI_RATE}
        return {
            "type": "session.update",
            "session": {
                "type": "realtime",
                "instructions": system_prompt,
                "audio": {
                    "input": {"format": audio_fmt, "turn_detection": {"type": "server_vad"},
                              "transcription": {"model": "whisper-1"}},
                    "output": {"format": audio_fmt, "voice": self.voice},
                },
                "tools": [{"type": "function", **t} for t in self.tools],
            },
        }

    async def connect(self, system_prompt: str = "You are a helpful AI assistant on a voice call."):
        logger.info(f"Connecting to OpenAI Realtime with model {self.model}")
        self.ws = await websockets.connect(
            f"wss://api.openai.com/v1/realtime?model={self.model}",
            additional_headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
            max_size=None,
        )
        await self.ws.send(json.dumps(self.session_config(system_prompt)))
        self._recv_task = asyncio.create_task(self._receive_loop())

    async def _receive_loop(self):
        try:
            async for raw in self.ws:
                await self.handle(json.loads(raw))
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in OpenAI receive loop: {e}")

    async def handle(self, ev: dict):
        t = ev.get("type", "")
        if t in ("response.output_audio.delta", "response.audio.delta"):
            await self._queue.put(base64.b64decode(ev["delta"]))
        elif t == "input_audio_buffer.speech_started":
            while not self._queue.empty():  # barge-in: drop unplayed AI audio
                self._queue.get_nowait()
        elif t == "conversation.item.input_audio_transcription.completed" and self.on_transcript:
            self.on_transcript("user", ev.get("transcript", ""))
        elif t in ("response.output_audio_transcript.done", "response.audio_transcript.done") and self.on_transcript:
            self.on_transcript("ai", ev.get("transcript", ""))
        elif t == "response.function_call_arguments.done" and self.on_tool_call:
            asyncio.create_task(self._run_tool(ev))
        elif t == "error":
            logger.error(f"OpenAI error: {ev.get('error')}")

    async def _run_tool(self, ev: dict):
        try:
            args = json.loads(ev.get("arguments") or "{}")
        except json.JSONDecodeError:
            args = {}
        result = await self.on_tool_call(ev["name"], args)
        await self.ws.send(json.dumps({
            "type": "conversation.item.create",
            "item": {"type": "function_call_output", "call_id": ev["call_id"], "output": json.dumps(result)},
        }))
        await self.ws.send(json.dumps({"type": "response.create"}))

    async def send_audio(self, pcm_16khz: bytes):
        pcm = resample_pcm16(pcm_16khz, 16000, OPENAI_RATE)
        try:
            audio = base64.b64encode(pcm).decode()
            await self.ws.send(json.dumps({"type": "input_audio_buffer.append", "audio": audio}))
        except Exception as e:
            logger.error(f"Error sending audio to OpenAI: {e}")

    async def get_response_audio(self) -> bytes:
        return await self._queue.get()

    async def close(self):
        if self._recv_task:
            self._recv_task.cancel()
        if self.ws:
            await self.ws.close()

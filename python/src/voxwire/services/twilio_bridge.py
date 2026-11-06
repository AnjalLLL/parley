"""Twilio Media Streams <-> AudioPipeline transport (8 kHz mu-law on the phone side)."""
import asyncio
import base64
import hashlib
import hmac
from xml.sax.saxutils import quoteattr

from voxwire.core.config import settings
from voxwire.utils.audio_codec import pcm16_to_ulaw, resample_pcm16, ulaw_to_pcm16


class TwilioBridge:
    """Same interface the pipeline uses for the Pion SFU, so phone calls reuse AudioPipeline."""

    def __init__(self, ws):
        self.ws = ws
        self.stream_sid = None
        self._in: asyncio.Queue = asyncio.Queue()

    def feed(self, payload_b64: str) -> None:
        pcm8k = ulaw_to_pcm16(base64.b64decode(payload_b64))
        self._in.put_nowait(resample_pcm16(pcm8k, 8000, 16000))

    def close(self) -> None:
        self._in.put_nowait(None)

    async def stream_audio_from_pion(self, session_id: str):
        while (chunk := await self._in.get()) is not None:
            yield chunk

    async def stream_audio_to_pion(self, session_id: str, pcm_stream, sample_rate: int):
        # shortcut: audio is sent as fast as the AI makes it and Twilio buffers it, so barge-in
        # doesn't cut audio already sent; send {"event": "clear"} on interruption to fix.
        async for chunk in pcm_stream:
            payload = base64.b64encode(pcm16_to_ulaw(resample_pcm16(chunk, sample_rate, 8000))).decode()
            await self.ws.send_json({"event": "media", "streamSid": self.stream_sid, "media": {"payload": payload}})


def stream_twiml(session_id: str, token: str) -> str:
    """TwiML connecting call audio to our WebSocket. Twilio forbids query strings, so the token is a Parameter."""
    ws_url = settings.PUBLIC_URL.replace("https://", "wss://").replace("http://", "ws://").rstrip("/")
    return (
        '<?xml version="1.0" encoding="UTF-8"?><Response><Connect>'
        f"<Stream url={quoteattr(f'{ws_url}/twilio/stream/{session_id}')}>"
        f"<Parameter name=\"token\" value={quoteattr(token)}/>"
        "</Stream></Connect></Response>"
    )


def valid_signature(url: str, params: dict, signature: str) -> bool:
    """Twilio's X-Twilio-Signature: base64(HMAC-SHA1(auth_token, url + sorted key+value pairs))."""
    data = url + "".join(k + params[k] for k in sorted(params))
    expected = base64.b64encode(hmac.new(settings.TWILIO_AUTH_TOKEN.encode(), data.encode(), hashlib.sha1).digest())
    return hmac.compare_digest(expected.decode(), signature or "")

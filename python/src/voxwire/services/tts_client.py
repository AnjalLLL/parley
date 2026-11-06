import aiohttp
import logging
from voxwire.core.config import settings

logger = logging.getLogger(__name__)

class TTSClient:
    def __init__(self):
        self.api_key = settings.ELEVENLABS_API_KEY
        self.voice_id = settings.ELEVENLABS_VOICE_ID

    async def synthesize(self, text: str):
        """Synthesize text to PCM 24kHz using ElevenLabs (example)"""
        if not self.api_key:
            logger.warning("ELEVENLABS_API_KEY not set, skipping TTS")
            return None

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}/stream"
        headers = {
            "Accept": "audio/mpeg",
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
        }
        data = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.5,
            }
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, headers=headers) as response:
                if response.status == 200:
                    # Note: ElevenLabs returns MP3. We need PCM 24kHz for Pion.
                    # For this microservice, Gemini native audio is preferred.
                    # This is a stub showing how it would look.
                    return await response.read()
                else:
                    logger.error(f"TTS failed: {response.status}")
                    return None

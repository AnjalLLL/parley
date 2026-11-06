import asyncio

from voxwire.services.audio_pipeline import AudioPipeline
from voxwire.services.gemini_client import EchoClient


class FakePion:
    """Feeds fixed PCM chunks in and records what the pipeline plays back."""

    def __init__(self, chunks):
        self.chunks, self.played = chunks, []

    async def stream_audio_from_pion(self, session_id):
        for c in self.chunks:
            yield c
        await asyncio.sleep(3600)  # caller keeps the line open

    async def stream_audio_to_pion(self, session_id, pcm_stream, sample_rate):
        assert sample_rate == 16000
        async for c in pcm_stream:
            self.played.append(c)


class RecordingEcho(EchoClient):
    async def connect(self, system_prompt: str = ""):
        self.prompt = system_prompt


def test_echo_pipeline_round_trip_and_prompt():
    async def run():
        pion = FakePion([b"\x01\x02", b"\x03\x04"])
        ai = RecordingEcho()
        p = AudioPipeline("s1", pion, ws=None, system_prompt="be brief", ai=ai)
        task = asyncio.create_task(p.run())
        for _ in range(100):
            if len(pion.played) == 2:
                break
            await asyncio.sleep(0.01)
        await p.stop()
        task.cancel()
        return pion.played, ai.prompt

    played, prompt = asyncio.run(run())
    assert played == [b"\x01\x02", b"\x03\x04"]
    assert prompt == "be brief"

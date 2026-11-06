"""Optional per-call recording: one mono WAV per side (user 16 kHz, AI at the provider's rate)."""
import wave
from pathlib import Path
from typing import Optional

from voxwire.core.config import settings


def recording_path(session_id: str, side: str) -> Optional[Path]:
    if not settings.RECORDINGS_DIR or "/" in session_id or ".." in session_id:
        return None
    return Path(settings.RECORDINGS_DIR) / f"{session_id}-{side}.wav"


class Recorder:
    def __init__(self, session_id: str, ai_rate: int):
        Path(settings.RECORDINGS_DIR).mkdir(parents=True, exist_ok=True)
        self._files = {}
        for side, rate in (("user", 16000), ("ai", ai_rate)):
            w = wave.open(str(recording_path(session_id, side)), "wb")
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            self._files[side] = w

    def write(self, side: str, pcm: bytes) -> None:
        self._files[side].writeframes(pcm)

    def close(self) -> None:
        for w in self._files.values():
            w.close()

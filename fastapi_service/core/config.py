from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    GEMINI_API_KEY: Optional[str] = None  # unset = echo mode
    GEMINI_MODEL: str = "gemini-2.5-flash-native-audio-preview-09-2025"

    PION_GRPC_URL: str = "localhost:50051"

    ELEVENLABS_API_KEY: Optional[str] = None
    ELEVENLABS_VOICE_ID: str = "21m00Tcm4TlvDq8ikWAM"

    STUN_SERVER: str = "stun:stun.l.google.com:19302"
    TURN_ENABLED: bool = False
    TURN_URL: str = ""
    TURN_USERNAME: str = ""
    TURN_CREDENTIAL: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()

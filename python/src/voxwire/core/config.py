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

    # Comma-separated API keys for the REST API. Empty = dev mode (no auth, loud warning).
    VOXWIRE_API_KEYS: str = ""
    # Signs per-call tokens. Empty = random per process (tokens die on restart); set it in production.
    VOXWIRE_SECRET: str = ""
    VOXWIRE_CORS_ORIGINS: str = "*"

    MAX_CONCURRENT_CALLS: int = 20
    MAX_CALL_SECONDS: int = 1800
    SESSION_TTL_SECONDS: int = 600
    SESSION_CREATE_PER_MINUTE: int = 60
    LOG_FORMAT: str = "text"  # "text" or "json"

    @property
    def api_keys(self) -> set[str]:
        return {k.strip() for k in self.VOXWIRE_API_KEYS.split(",") if k.strip()}

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()

import secrets
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    GEMINI_API_KEY: Optional[str] = None  # unset = echo mode
    GEMINI_MODEL: str = "gemini-2.5-flash-native-audio-preview-09-2025"

    PION_GRPC_URL: str = "localhost:50051"
    SFU_TIMEOUT_SECONDS: float = 5.0

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

    OPENAI_API_KEY: Optional[str] = None
    OPENAI_REALTIME_MODEL: str = "gpt-realtime"
    DEFAULT_PROVIDER: Optional[str] = None  # gemini / openai / echo; unset = first provider with a key

    WEBHOOK_URL: str = ""  # default events URL when a session doesn't set webhook_url
    RECORDINGS_DIR: str = ""  # empty = recording disabled
    DATA_DIR: str = "data"  # sqlite call log lives here

    # Phone calls (Twilio Media Streams)
    PUBLIC_URL: str = ""  # https://voice.example.com, reachable by Twilio
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = ""
    PHONE_SYSTEM_PROMPT: str = "You are a helpful assistant answering a phone call. Keep answers short."

    # TURN: static creds (TURN_USERNAME/CREDENTIAL) or time-limited ones from a shared secret (coturn use-auth-secret)
    TURN_SECRET: str = ""

    @property
    def api_keys(self) -> set[str]:
        return {k.strip() for k in self.VOXWIRE_API_KEYS.split(",") if k.strip()}

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()

# Signs call tokens and webhook bodies. Random per process when unset (dev).
SECRET = (settings.VOXWIRE_SECRET or secrets.token_hex(32)).encode()

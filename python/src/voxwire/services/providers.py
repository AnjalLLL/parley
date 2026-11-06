"""Pick the AI provider for a call. Every client has the same shape:
connect(system_prompt) / send_audio(pcm16k) / get_response_audio() / close() / output_rate.
"""
from voxwire.core.config import settings
from voxwire.services.gemini_client import EchoClient, GeminiLiveClient
from voxwire.services.openai_client import OpenAIRealtimeClient

PROVIDERS = {"gemini": GeminiLiveClient, "openai": OpenAIRealtimeClient, "echo": EchoClient}


def _has_key(name: str) -> bool:
    key = {"gemini": settings.GEMINI_API_KEY, "openai": settings.OPENAI_API_KEY}.get(name)
    return bool(key) and key != "your_key_here"


def resolve_provider(requested: str | None = None) -> str:
    """Requested provider if it has a key, else DEFAULT_PROVIDER, else the first configured one, else echo."""
    for name in (requested, settings.DEFAULT_PROVIDER, "gemini", "openai"):
        if name == "echo":
            return "echo"
        if name and _has_key(name):
            return name
    return "echo"


def make_ai_client(provider: str | None = None, **kwargs):
    return PROVIDERS[resolve_provider(provider)](**kwargs)

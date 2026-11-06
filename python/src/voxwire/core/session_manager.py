"""In-memory session store, per-call tokens and call limits.

shortcut: single-process memory store; move to Redis for multi-node (plans phase 04).
"""
import hashlib
import hmac
import secrets
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from voxwire.core.config import settings

_SECRET = (settings.VOXWIRE_SECRET or secrets.token_hex(32)).encode()


@dataclass
class Session:
    id: str
    system_prompt: Optional[str]
    voice: Optional[str]
    model: Optional[str]
    metadata: dict
    expires_at: float
    created_at: float = field(default_factory=time.time)
    status: str = "waiting"  # waiting -> active -> ended
    started_at: Optional[float] = None
    ended_at: Optional[float] = None
    ws: Any = None  # live WebSocket while active, so DELETE can hang up

    @property
    def duration(self) -> float:
        if not self.started_at:
            return 0.0
        return round((self.ended_at or time.time()) - self.started_at, 1)

    def public(self) -> dict:
        return {
            "session_id": self.id,
            "status": self.status,
            "duration_seconds": self.duration,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "metadata": self.metadata,
        }


def make_token(session_id: str, expires_at: float) -> str:
    exp = str(int(expires_at))
    sig = hmac.new(_SECRET, f"{session_id}.{exp}".encode(), hashlib.sha256).hexdigest()
    return f"{exp}.{sig}"


def verify_token(session_id: str, token: Optional[str]) -> bool:
    if not token or "." not in token:
        return False
    exp, sig = token.split(".", 1)
    if not exp.isdigit() or int(exp) < time.time():
        return False
    good = hmac.new(_SECRET, f"{session_id}.{exp}".encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, good)


class SessionManager:
    def __init__(self):
        self._sessions: dict[str, Session] = {}
        # counters for /metrics
        self.calls_total = 0
        self.ai_errors_total = 0
        self.call_seconds_sum = 0.0

    def create(self, system_prompt=None, voice=None, model=None, metadata=None, ttl_seconds=None) -> Session:
        self.sweep()
        ttl = ttl_seconds or settings.SESSION_TTL_SECONDS
        s = Session(str(uuid.uuid4()), system_prompt, voice, model, metadata or {}, time.time() + ttl)
        self._sessions[s.id] = s
        return s

    def get(self, session_id: str) -> Optional[Session]:
        s = self._sessions.get(session_id)
        if s and s.status == "waiting" and s.expires_at < time.time():
            return None
        return s

    def active_count(self) -> int:
        return sum(1 for s in self._sessions.values() if s.status == "active")

    def start(self, s: Session, ws) -> None:
        s.status, s.started_at, s.ws = "active", time.time(), ws
        self.calls_total += 1

    def finish(self, s: Session) -> None:
        s.ended_at = time.time()
        if s.status == "active":
            self.call_seconds_sum += s.duration
        s.status, s.ws = "ended", None

    def sweep(self) -> None:
        """Drop expired unused sessions and ended ones older than an hour."""
        now = time.time()
        for sid, s in list(self._sessions.items()):
            if (s.status == "waiting" and s.expires_at < now) or (s.status == "ended" and now - s.ended_at > 3600):
                del self._sessions[sid]


sessions = SessionManager()

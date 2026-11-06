"""In-memory session store, per-call tokens and call limits.

shortcut: single-process memory store; move to Redis for multi-node (plans phase 04).
"""
import hashlib
import hmac
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from voxwire.core.config import SECRET, settings
from voxwire.core import store
from voxwire.services import webhooks



@dataclass
class Session:
    id: str
    expires_at: float
    system_prompt: Optional[str] = None
    voice: Optional[str] = None
    model: Optional[str] = None
    provider: Optional[str] = None  # gemini / openai / echo; None = pick from configured keys
    tools: list = field(default_factory=list)  # [{name, description, parameters}]
    tool_webhook_url: Optional[str] = None
    webhook_url: Optional[str] = None
    record: bool = False
    metadata: dict = field(default_factory=dict)
    api_key: str = "dev"
    channel: str = "webrtc"  # webrtc / phone
    transcript: list = field(default_factory=list)  # [{role, text, t}]
    end_reason: Optional[str] = None
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
            "provider": self.provider,
            "channel": self.channel,
            "end_reason": self.end_reason,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "metadata": self.metadata,
        }


def make_token(session_id: str, expires_at: float) -> str:
    exp = str(int(expires_at))
    sig = hmac.new(SECRET, f"{session_id}.{exp}".encode(), hashlib.sha256).hexdigest()
    return f"{exp}.{sig}"


def verify_token(session_id: str, token: Optional[str]) -> bool:
    if not token or "." not in token:
        return False
    exp, sig = token.split(".", 1)
    if not exp.isdigit() or int(exp) < time.time():
        return False
    good = hmac.new(SECRET, f"{session_id}.{exp}".encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, good)


class SessionManager:
    def __init__(self):
        self._sessions: dict[str, Session] = {}
        # counters for /metrics
        self.calls_total = 0
        self.ai_errors_total = 0
        self.call_seconds_sum = 0.0

    def create(self, ttl_seconds=None, **fields) -> Session:
        self.sweep()
        ttl = ttl_seconds or settings.SESSION_TTL_SECONDS
        s = Session(str(uuid.uuid4()), time.time() + ttl, **fields)
        self._sessions[s.id] = s
        return s

    def get(self, session_id: str) -> Optional[Session]:
        s = self._sessions.get(session_id)
        if s and s.status == "waiting" and s.expires_at < time.time():
            return None
        return s

    def all(self) -> list[Session]:
        return list(self._sessions.values())

    def active_count(self) -> int:
        return sum(1 for s in self._sessions.values() if s.status == "active")

    def start(self, s: Session, ws) -> None:
        s.status, s.started_at, s.ws = "active", time.time(), ws
        self.calls_total += 1
        webhooks.send_event(s.webhook_url, "call.started", s.public())

    def add_transcript(self, s: Session, role: str, text: str) -> None:
        """Providers stream text in fragments; merge consecutive fragments from the same speaker."""
        if s.transcript and s.transcript[-1]["role"] == role:
            s.transcript[-1]["text"] += text
        else:
            t = round(time.time() - (s.started_at or time.time()), 1)
            s.transcript.append({"role": role, "text": text, "t": t})

    def finish(self, s: Session, reason: str = "hangup") -> None:
        if s.status == "ended":
            return
        s.end_reason = reason
        s.ended_at = time.time()
        was_active = s.status == "active"
        s.status, s.ws = "ended", None
        store.save(s)
        if was_active:
            self.call_seconds_sum += s.duration
            webhooks.send_event(s.webhook_url, "call.ended", s.public())
            if s.transcript:
                webhooks.send_event(s.webhook_url, "transcript.ready", {"session_id": s.id, "transcript": s.transcript})

    def sweep(self) -> None:
        """Drop expired unused sessions and ended ones older than an hour."""
        now = time.time()
        for sid, s in list(self._sessions.items()):
            if (s.status == "waiting" and s.expires_at < now) or (s.status == "ended" and now - s.ended_at > 3600):
                del self._sessions[sid]


sessions = SessionManager()

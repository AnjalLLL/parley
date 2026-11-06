"""API-key auth and a per-key rate limit for the REST API."""
import logging
import time
from collections import defaultdict, deque

from fastapi import Header, HTTPException

from voxwire.core.config import settings

logger = logging.getLogger(__name__)
_hits: dict[str, deque] = defaultdict(deque)


def require_api_key(authorization: str = Header(default="")) -> str:
    keys = settings.api_keys
    if not keys:
        return "dev"  # dev mode; app startup logs a warning
    key = authorization.removeprefix("Bearer ").strip()
    if key not in keys:
        raise HTTPException(401, "invalid or missing API key")
    return key


def rate_limit(key: str) -> None:
    """Sliding one-minute window per API key. shortcut: per-process memory, fine for one node."""
    window, now = _hits[key], time.monotonic()
    while window and now - window[0] > 60:
        window.popleft()
    if len(window) >= settings.SESSION_CREATE_PER_MINUTE:
        raise HTTPException(429, "too many sessions created, slow down")
    window.append(now)

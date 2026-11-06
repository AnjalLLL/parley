"""Small client for a running Voxwire server (self-hosted or managed).

Standard library only, so `from voxwire import VoxwireClient` works in any app
without pulling the server's dependencies into the request path.
"""
import json
import urllib.error
import urllib.request
from typing import Optional


class VoxwireError(Exception):
    """Raised when the server returns an error or cannot be reached."""


class VoxwireClient:
    def __init__(self, base_url: str = "http://localhost:8000", api_key: Optional[str] = None, timeout: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _request(self, method: str, path: str, body: Optional[dict] = None) -> dict:
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base_url + path, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        if self.api_key:
            req.add_header("Authorization", f"Bearer {self.api_key}")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read() or b"{}")
        except urllib.error.HTTPError as e:
            raise VoxwireError(f"{method} {path} failed: {e.code} {e.read().decode(errors='replace')}") from e
        except urllib.error.URLError as e:
            raise VoxwireError(f"cannot reach {self.base_url}: {e.reason}") from e

    def health(self) -> dict:
        return self._request("GET", "/api/health")

    def create_session(self, system_prompt: Optional[str] = None, **options) -> dict:
        """Create a call. options: voice, model, ttl_seconds, metadata.

        Returns the session plus `token` and `signaling_url`; give signaling_url to the browser.
        """
        session = self._request("POST", "/api/session", {"system_prompt": system_prompt, **options})
        session["signaling_url"] = self.signaling_url(session["session_id"], session.get("token"))
        return session

    def get_session(self, session_id: str) -> dict:
        return self._request("GET", f"/api/session/{session_id}")

    def end_session(self, session_id: str) -> dict:
        return self._request("DELETE", f"/api/session/{session_id}")

    def signaling_url(self, session_id: str, token: Optional[str] = None) -> str:
        scheme, _, host = self.base_url.partition("://")
        ws = ("wss://" if scheme == "https" else "ws://") + host
        url = f"{ws}/ws/signaling/{session_id}"
        return f"{url}?token={token}" if token else url

from typing import Dict, Any

class SessionManager:
    _sessions: Dict[str, Any] = {}

    @classmethod
    async def get_or_create(cls, session_id: str):
        if session_id not in cls._sessions:
            cls._sessions[session_id] = {"id": session_id}
        return cls._sessions[session_id]

    @classmethod
    async def end(cls, session_id: str):
        if session_id in cls._sessions:
            del cls._sessions[session_id]

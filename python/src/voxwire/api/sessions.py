from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
import uuid

router = APIRouter()

class SessionCreate(BaseModel):
    system_prompt: Optional[str] = None

@router.post("/session")
async def create_session(req: SessionCreate):
    session_id = str(uuid.uuid4())
    # In a real app, you'd store this in a database or cache
    return {"session_id": session_id}

@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    return {"ok": True}

from fastapi import APIRouter
from voxwire.core.config import settings

router = APIRouter()

@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "pion_url": settings.PION_GRPC_URL,
        "gemini_model": settings.GEMINI_MODEL
    }

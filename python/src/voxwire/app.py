import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from voxwire import __version__
from voxwire.api import health, sessions, signaling, telephony
from voxwire.core.config import settings
from voxwire.utils.logger import configure_logging

configure_logging(settings.LOG_FORMAT)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting Voxwire {__version__} (SFU at {settings.PION_GRPC_URL})")
    if not settings.api_keys:
        logger.warning("VOXWIRE_API_KEYS is empty: the API is OPEN (dev mode). Set keys before exposing this server.")
    if not settings.VOXWIRE_SECRET:
        logger.warning("VOXWIRE_SECRET is empty: using a random secret; call tokens stop working on restart.")
    yield


app = FastAPI(title="Voxwire", version=__version__, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.VOXWIRE_CORS_ORIGINS.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(signaling.router, tags=["Signaling"])
app.include_router(sessions.router, prefix="/api", tags=["Sessions"])
app.include_router(health.router, tags=["Health"])
app.include_router(telephony.router, tags=["Phone"])

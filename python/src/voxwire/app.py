import logging
from fastapi import FastAPI
from voxwire import __version__
from fastapi.middleware.cors import CORSMiddleware
from voxwire.api import signaling, sessions, health
from voxwire.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Voxwire", version=__version__)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(signaling.router, tags=["Signaling"])
app.include_router(sessions.router, prefix="/api", tags=["Sessions"])
app.include_router(health.router, prefix="/api", tags=["Health"])

@app.on_event("startup")
async def startup_event():
    logger.info("Starting Voxwire...")
    logger.info(f"Pion gRPC URL: {settings.PION_GRPC_URL}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Voxwire...")

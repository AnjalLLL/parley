import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import signaling, sessions, health
from core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Parley")

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
    logger.info("Starting AI Video Call Microservice...")
    logger.info(f"Pion gRPC URL: {settings.PION_GRPC_URL}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down AI Video Call Microservice...")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

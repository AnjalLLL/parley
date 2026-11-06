from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from voxwire import __version__
from voxwire.core.session_manager import sessions

router = APIRouter()


@router.get("/api/health")
async def health_check():
    return {"status": "ok", "version": __version__, "active_calls": sessions.active_count()}


@router.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    """Prometheus text format. shortcut: hand-written counters; switch to prometheus-client if we need histograms."""
    return (
        "# TYPE voxwire_active_calls gauge\n"
        f"voxwire_active_calls {sessions.active_count()}\n"
        "# TYPE voxwire_calls_total counter\n"
        f"voxwire_calls_total {sessions.calls_total}\n"
        "# TYPE voxwire_ai_errors_total counter\n"
        f"voxwire_ai_errors_total {sessions.ai_errors_total}\n"
        "# TYPE voxwire_call_duration_seconds_sum counter\n"
        f"voxwire_call_duration_seconds_sum {sessions.call_seconds_sum}\n"
    )

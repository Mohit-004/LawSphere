"""FastAPI entry point for the LawSphere local service."""

from fastapi import FastAPI

from app.core.config import settings
from app.schemas.system import SystemStatus

app = FastAPI(
    title="LawSphere AI Engine",
    version=settings.app_version,
    description="Local API foundation for the LawSphere legal assistant.",
)


@app.get("/api/v1/system/status", response_model=SystemStatus, tags=["system"])
def get_system_status() -> SystemStatus:
    """Report API availability without implying model/runtime readiness."""
    return SystemStatus(
        app_name=settings.app_name,
        version=settings.app_version,
        status="ok",
        offline_mode=True,
        ollama="not_checked",
    )

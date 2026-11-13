"""FastAPI entry point for the LawSphere local service."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.database.session import initialize_database
from app.models.ollama import get_ollama_status
from app.schemas.system import ModelList, SystemStatus


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="LawSphere AI Engine",
    version=settings.app_version,
    description="Local API foundation for the LawSphere legal assistant.",
    lifespan=lifespan,
)


@app.get("/api/v1/system/status", response_model=SystemStatus, tags=["system"])
def get_system_status() -> SystemStatus:
    """Report API, database, and local model-runtime availability."""
    ollama = get_ollama_status()
    return SystemStatus(
        app_name=settings.app_name,
        version=settings.app_version,
        status="ok",
        offline_mode=True,
        sqlite="ready",
        ollama="available" if ollama.available else "unavailable",
        installed_model_count=len(ollama.models),
    )


@app.get("/api/v1/models", response_model=ModelList, tags=["models"])
def list_local_models() -> ModelList:
    """List models already installed in the local Ollama runtime."""
    ollama = get_ollama_status()
    return ModelList(
        ollama="available" if ollama.available else "unavailable",
        models=ollama.models,
    )

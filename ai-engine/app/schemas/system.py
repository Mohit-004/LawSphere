"""System status response contract."""

from typing import Literal

from pydantic import BaseModel


class SystemStatus(BaseModel):
    app_name: str
    version: str
    status: Literal["ok"]
    offline_mode: bool
    sqlite: Literal["ready"]
    ollama: Literal["available", "unavailable"]
    installed_model_count: int


class ModelList(BaseModel):
    ollama: Literal["available", "unavailable"]
    models: list[str]

"""System status response contract."""

from typing import Literal

from pydantic import BaseModel


class SystemStatus(BaseModel):
    app_name: str
    version: str
    status: Literal["ok"]
    offline_mode: bool
    sqlite: Literal["ready"]
    ollama: Literal["not_checked"]

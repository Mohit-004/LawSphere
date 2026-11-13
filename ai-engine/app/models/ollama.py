"""Small HTTP adapter for checking a local Ollama installation."""

import json
from dataclasses import dataclass
from urllib.error import URLError
from urllib.request import urlopen

from app.core.config import settings


@dataclass(frozen=True)
class OllamaStatus:
    available: bool
    models: list[str]


def get_ollama_status() -> OllamaStatus:
    """Fetch installed model names from Ollama's local tags endpoint."""
    url = f"{settings.ollama_base_url.rstrip('/')}/api/tags"
    try:
        with urlopen(url, timeout=settings.ollama_timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, OSError, ValueError):
        return OllamaStatus(available=False, models=[])

    raw_models = payload.get("models") if isinstance(payload, dict) else None
    if not isinstance(raw_models, list):
        return OllamaStatus(available=False, models=[])

    names = [
        model["name"]
        for model in raw_models
        if isinstance(model, dict) and isinstance(model.get("name"), str)
    ]
    return OllamaStatus(available=True, models=names)

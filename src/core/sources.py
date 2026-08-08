from __future__ import annotations

import json
from pathlib import Path


DEFAULT_CONFIG = Path("config/sources.json")


def load_sources(config_path: Path = DEFAULT_CONFIG) -> list[dict]:
    if not config_path.exists():
        raise FileNotFoundError(f"No se encuentra la configuración de fuentes: {config_path}")

    with config_path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    sources = payload.get("sources", [])
    return [source for source in sources if source.get("enabled", True)]


def list_sources(config_path: Path = DEFAULT_CONFIG) -> list[dict]:
    return load_sources(config_path)


def get_source(source_id: str, config_path: Path = DEFAULT_CONFIG) -> dict:
    for source in load_sources(config_path):
        if source.get("id") == source_id:
            return source
    raise ValueError(f"Fuente no disponible: {source_id}")

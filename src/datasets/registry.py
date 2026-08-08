from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

REGISTRY_PATH = Path("data/metadata/datasets.json")


def load_registry(path: Path = REGISTRY_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    return payload.get("datasets", [])


def register_dataset(record: dict[str, Any], path: Path = REGISTRY_PATH) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    datasets = load_registry(path)
    enriched = {
        "registered_at": datetime.now().isoformat(timespec="seconds"),
        **record,
    }
    datasets.append(enriched)
    with path.open("w", encoding="utf-8") as file:
        json.dump({"datasets": datasets}, file, ensure_ascii=False, indent=2)
    return enriched

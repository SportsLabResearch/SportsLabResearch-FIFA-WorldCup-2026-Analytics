from __future__ import annotations

from src.core.sources import list_sources


def discover_configured_sources() -> list[dict]:
    """Devuelve las fuentes habilitadas registradas en la configuración."""
    return list_sources()

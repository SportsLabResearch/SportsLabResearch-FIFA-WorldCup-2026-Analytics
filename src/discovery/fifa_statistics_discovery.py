from __future__ import annotations
import json, re
from dataclasses import dataclass, asdict
from html import unescape
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlparse
import requests

BASE_URL = "https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026"

@dataclass(frozen=True)
class StatisticsBlock:
    id: str
    name: str
    url: str
    description: str
    source: str = "detected"
    def to_dict(self) -> dict:
        return asdict(self)

class FIFAStatisticsDiscovery:
    FALLBACK_BLOCKS = [
        StatisticsBlock("player_statistics", "Estadísticas de jugadores", f"{BASE_URL}/statistics/player-statistics", "Goles, asistencias, apariciones, minutos y rendimiento individual.", "verified_catalog"),
        StatisticsBlock("team_statistics", "Estadísticas de selecciones", f"{BASE_URL}/statistics/team-statistics", "Goles, posesión, precisión de pase y rendimiento colectivo.", "verified_catalog"),
        StatisticsBlock("standings", "Clasificación y cuadro", f"{BASE_URL}/standings", "Grupos, puntos, diferencia de goles y eliminatorias.", "verified_catalog"),
        StatisticsBlock("matches", "Partidos, calendario y resultados", f"{BASE_URL}/matches", "Partidos, fechas, fases, marcadores y resultados.", "verified_catalog"),
        StatisticsBlock("teams", "Selecciones y plantillas", f"{BASE_URL}/teams", "Plantillas, perfiles de selección y estadísticas asociadas.", "verified_catalog"),
        StatisticsBlock("power_rankings", "FIFA Power Rankings", f"{BASE_URL}/articles/power-rankings", "Clasificación de rendimiento de jugadores durante el torneo.", "verified_catalog"),
    ]
    KEYWORDS = {
        "player_statistics": ("player-statistics", "player stats"),
        "team_statistics": ("team-statistics", "team stats"),
        "standings": ("standings", "group tables", "bracket"),
        "matches": ("matches", "fixtures", "results", "schedule"),
        "teams": ("/teams", "squads", "squad"),
        "power_rankings": ("power-rankings", "power rankings"),
    }
    LABELS = {b.id: b for b in FALLBACK_BLOCKS}
    def __init__(self, page_url: str = BASE_URL, timeout: int = 25):
        self.page_url = page_url.rstrip("/")
        self.timeout = timeout
        self.last_mode = "not_run"
        self.last_error = ""
    def _fetch_html(self) -> str:
        r = requests.get(self.page_url, timeout=self.timeout, headers={"User-Agent":"Mozilla/5.0","Accept-Language":"es-ES,es;q=0.9,en;q=0.8"})
        r.raise_for_status()
        return r.text
    @staticmethod
    def _extract_candidate_urls(html: str, base_url: str) -> list[str]:
        decoded = unescape(html).replace("\\/", "/")
        patterns = [r'href=["\']([^"\']+)["\']', r'"url"\s*:\s*"([^"]+)"', r'https://www\.fifa\.com/[^"\s<>]+']
        urls=set()
        for pattern in patterns:
            for item in re.findall(pattern, decoded, flags=re.I):
                absolute=urljoin(base_url+"/", item.split("#",1)[0])
                p=urlparse(absolute)
                if p.netloc.endswith("fifa.com") and "/canadamexicousa2026" in p.path:
                    urls.add(f"{p.scheme}://{p.netloc}{p.path}".rstrip("/"))
        return sorted(urls)
    def _classify(self, urls: Iterable[str]) -> list[StatisticsBlock]:
        found={}
        for url in urls:
            low=url.lower()
            for block_id, terms in self.KEYWORDS.items():
                if any(t in low for t in terms):
                    if "/articles/" in low and block_id != "power_rankings":
                        continue
                    template=self.LABELS[block_id]
                    candidate=StatisticsBlock(block_id, template.name, url, template.description, "detected")
                    if block_id not in found or len(url) < len(found[block_id].url):
                        found[block_id]=candidate
        return [found[k] for k in self.LABELS if k in found]
    def discover(self) -> list[dict]:
        try:
            blocks=self._classify(self._extract_candidate_urls(self._fetch_html(), self.page_url))
            if blocks:
                self.last_mode="live_page"
                return [b.to_dict() for b in blocks]
            self.last_error="La página respondió, pero no expuso enlaces estadísticos analizables."
        except Exception as exc:
            self.last_error=str(exc)
        self.last_mode="verified_catalog"
        return [b.to_dict() for b in self.FALLBACK_BLOCKS]
    def save_inventory(self, blocks: list[dict], output: Path) -> Path:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps({"page_url":self.page_url,"discovery_mode":self.last_mode,"error":self.last_error,"blocks":blocks}, ensure_ascii=False, indent=2), encoding="utf-8")
        return output

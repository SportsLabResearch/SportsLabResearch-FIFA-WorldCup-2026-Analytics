from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from html import unescape
from io import StringIO
from typing import Any
from urllib.parse import urljoin, urlparse

import pandas as pd
import requests


@dataclass
class ExtractedBlockData:
    url: str
    title: str
    tables: list[pd.DataFrame]
    links: pd.DataFrame
    endpoints: pd.DataFrame
    text_sections: pd.DataFrame
    discovery_mode: str
    error: str = ""

    @property
    def row_count(self) -> int:
        return sum(len(df) for df in self.tables)


class FIFABlockDataExtractor:
    """Extrae datos de páginas FIFA renderizadas dinámicamente.

    Flujo: petición HTTP -> navegador Chrome/Selenium -> captura de respuestas JSON.
    """

    def __init__(self, timeout: int = 45, browser_wait: int = 12):
        self.timeout = timeout
        self.browser_wait = browser_wait
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/149 Safari/537.36",
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
        }

    def fetch(self, url: str) -> tuple[str, str]:
        response = requests.get(url, timeout=self.timeout, headers=self.headers)
        response.raise_for_status()
        return response.text, response.headers.get("content-type", "")

    @staticmethod
    def _clean_frame(df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        if isinstance(out.columns, pd.MultiIndex):
            out.columns = [" | ".join(str(x) for x in col if str(x) != "nan").strip(" |") for col in out.columns]
        out.columns = [str(c).strip() or f"columna_{i+1}" for i, c in enumerate(out.columns)]
        out = out.dropna(axis=0, how="all").dropna(axis=1, how="all")
        out = out.loc[:, ~out.columns.duplicated()].reset_index(drop=True)
        return out

    def _html_tables(self, html: str) -> list[pd.DataFrame]:
        try:
            frames = pd.read_html(StringIO(html))
        except (ValueError, ImportError):
            return []
        return [self._clean_frame(df) for df in frames if not df.empty]

    @staticmethod
    def _json_candidates(html: str) -> list[Any]:
        decoded = unescape(html).replace("\\/", "/")
        candidates: list[Any] = []
        patterns = [
            r'<script[^>]+type=["\']application/(?:ld\+)?json["\'][^>]*>(.*?)</script>',
            r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
        ]
        for pattern in patterns:
            for raw in re.findall(pattern, decoded, flags=re.I | re.S):
                try:
                    candidates.append(json.loads(raw.strip()))
                except Exception:
                    continue
        return candidates

    @staticmethod
    def _scalar_ratio(records: list[dict]) -> float:
        if not records:
            return 0.0
        values = [v for row in records[:10] for v in row.values()]
        if not values:
            return 0.0
        scalar = sum(v is None or isinstance(v, (str, int, float, bool)) for v in values)
        return scalar / len(values)

    def _walk_json(self, value: Any, path: str = "root") -> list[tuple[str, list[dict]]]:
        found: list[tuple[str, list[dict]]] = []
        if isinstance(value, list):
            rows = [x for x in value if isinstance(x, dict)]
            if len(rows) >= 2 and self._scalar_ratio(rows) >= 0.50:
                found.append((path, rows))
            for i, item in enumerate(value[:500]):
                found.extend(self._walk_json(item, f"{path}[{i}]"))
        elif isinstance(value, dict):
            for key, item in value.items():
                found.extend(self._walk_json(item, f"{path}.{key}"))
        return found

    def _payload_tables(self, payloads: list[Any]) -> list[pd.DataFrame]:
        ranked: list[tuple[int, str, pd.DataFrame]] = []
        seen: set[tuple] = set()
        keywords = ("player", "team", "match", "standing", "stat", "goal", "assist", "rank", "fixture", "result", "squad")
        for payload in payloads:
            for path, records in self._walk_json(payload):
                try:
                    df = self._clean_frame(pd.json_normalize(records, sep="."))
                except Exception:
                    continue
                if df.empty or len(df.columns) < 2:
                    continue
                signature = (tuple(df.columns), len(df))
                if signature in seen:
                    continue
                seen.add(signature)
                score = len(df) + 20 * sum(k in path.lower() for k in keywords)
                ranked.append((score, path, df))
        ranked.sort(key=lambda x: x[0], reverse=True)
        return [df for _, _, df in ranked[:30]]

    def _json_tables(self, html: str) -> list[pd.DataFrame]:
        return self._payload_tables(self._json_candidates(html))

    @staticmethod
    def _extract_links(html: str, base_url: str) -> pd.DataFrame:
        decoded = unescape(html).replace("\\/", "/")
        rows = []
        seen = set()
        for href, label in re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', decoded, flags=re.I | re.S):
            url = urljoin(base_url, href.split("#", 1)[0])
            text = re.sub(r"<[^>]+>", " ", label)
            text = re.sub(r"\s+", " ", text).strip()
            if urlparse(url).netloc.endswith("fifa.com") and url not in seen:
                seen.add(url); rows.append({"texto": text or "Enlace FIFA", "url": url})
        return pd.DataFrame(rows, columns=["texto", "url"])

    @staticmethod
    def _extract_endpoints(html: str, base_url: str) -> pd.DataFrame:
        decoded = unescape(html).replace("\\/", "/")
        candidates = set(re.findall(r'https?://[^"\'\s<>]+', decoded, flags=re.I))
        candidates.update(urljoin(base_url, x) for x in re.findall(r'["\'](/[^"\']*(?:api|graphql|json|stats|statistics)[^"\']*)["\']', decoded, flags=re.I))
        rows = []
        for url in sorted(candidates):
            low = url.lower()
            if any(k in low for k in ("api", "graphql", ".json", "statistics", "/stats")):
                rows.append({"tipo": "posible_endpoint", "url": url.rstrip("),;")})
        return pd.DataFrame(rows, columns=["tipo", "url"])

    @staticmethod
    def _text_sections(html: str) -> pd.DataFrame:
        clean = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", html, flags=re.I | re.S)
        rows, seen = [], set()
        for tag, content in re.findall(r"<(h1|h2|h3|p)[^>]*>(.*?)</\1>", clean, flags=re.I | re.S):
            text = re.sub(r"<[^>]+>", " ", content)
            text = re.sub(r"\s+", " ", unescape(text)).strip()
            if len(text) >= 3 and text not in seen:
                seen.add(text); rows.append({"tipo": tag.lower(), "texto": text})
        return pd.DataFrame(rows[:500], columns=["tipo", "texto"])

    def _browser_capture(self, url: str) -> tuple[str, list[Any], pd.DataFrame]:
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
        except ImportError as exc:
            raise RuntimeError("Falta Selenium. Ejecute: pip install selenium") from exc

        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument(f"--user-agent={self.headers['User-Agent']}")
        options.set_capability("goog:loggingPrefs", {"performance": "ALL"})

        driver = webdriver.Chrome(options=options)
        payloads: list[Any] = []
        endpoint_rows: list[dict] = []
        try:
            driver.execute_cdp_cmd("Network.enable", {})
            driver.get(url)
            time.sleep(self.browser_wait)
            html = driver.page_source
            logs = driver.get_log("performance")
            seen_requests = set()
            for entry in logs:
                try:
                    message = json.loads(entry["message"])["message"]
                    if message.get("method") != "Network.responseReceived":
                        continue
                    params = message.get("params", {})
                    response = params.get("response", {})
                    request_id = params.get("requestId")
                    response_url = response.get("url", "")
                    mime = response.get("mimeType", "").lower()
                    if not request_id or request_id in seen_requests:
                        continue
                    if not any(x in mime for x in ("json", "javascript")) and not any(x in response_url.lower() for x in ("api", "graphql", "stat", "match", "team", "player")):
                        continue
                    seen_requests.add(request_id)
                    endpoint_rows.append({"tipo": mime or "respuesta_red", "url": response_url})
                    try:
                        body = driver.execute_cdp_cmd("Network.getResponseBody", {"requestId": request_id}).get("body", "")
                        if body:
                            payloads.append(json.loads(body))
                    except Exception:
                        continue
                except Exception:
                    continue
            return html, payloads, pd.DataFrame(endpoint_rows, columns=["tipo", "url"]).drop_duplicates()
        finally:
            driver.quit()

    @staticmethod
    def _select_relevant_tables(tables: list[pd.DataFrame], title: str) -> list[pd.DataFrame]:
        """Conserva solo tablas deportivas coherentes con el bloque solicitado."""
        title_low = title.lower()
        common = {"rank", "team", "player", "name", "matches", "goals", "assists", "points", "position", "minutes", "played", "won", "draw", "lost"}
        block_terms = {
            "jugador": {"player", "playerid", "firstname", "lastname", "shortname", "goals", "assists", "minutes", "position"},
            "seleccion": {"team", "squad", "country", "goals", "possession", "passes", "matches"},
            "partido": {"match", "matchid", "hometeam", "awayteam", "date", "score", "stadium"},
            "clasific": {"group", "team", "played", "won", "draw", "lost", "points", "goaldifference"},
            "ranking": {"rank", "ranking", "team", "points", "confederation"},
        }
        wanted = set(common)
        for key, terms in block_terms.items():
            if key in title_low: wanted |= terms
        scored = []
        junk = {"identifier", "pageurl", "themepaletteentryid", "resourceType", "documents", "images", "audios"}
        for df in tables:
            if df.empty or len(df.columns) < 2: continue
            cols = {re.sub(r"[^a-z0-9]", "", str(c).lower()) for c in df.columns}
            if len(cols & {re.sub(r"[^a-z0-9]", "", x.lower()) for x in junk}) >= 2: continue
            hits = sum(any(term in c for term in wanted) for c in cols)
            density = min(len(df), 500) / 500
            score = hits * 10 + density
            if hits >= 2 or (hits >= 1 and len(df) >= 20): scored.append((score, df))
        scored.sort(key=lambda x: x[0], reverse=True)
        selected=[]; seen=set()
        for _, df in scored:
            sig=(tuple(map(str,df.columns)), len(df))
            if sig not in seen:
                seen.add(sig); selected.append(df)
            if len(selected) >= 6: break
        return selected

    def extract_from_html(self, html: str, url: str, title: str = "", payloads: list[Any] | None = None, endpoints: pd.DataFrame | None = None, mode: str = "live_data") -> ExtractedBlockData:
        tables = self._html_tables(html)
        tables.extend(self._json_tables(html))
        if payloads:
            tables.extend(self._payload_tables(payloads))
        # Deduplicar tablas por columnas y filas
        unique, seen = [], set()
        for df in tables:
            sig = (tuple(df.columns), len(df))
            if sig not in seen:
                seen.add(sig); unique.append(df)
        endpoint_df = self._extract_endpoints(html, url)
        if endpoints is not None and not endpoints.empty:
            endpoint_df = pd.concat([endpoint_df, endpoints], ignore_index=True).drop_duplicates()
        useful = self._select_relevant_tables(unique, title)
        return ExtractedBlockData(url, title, useful, self._extract_links(html, url), endpoint_df, self._text_sections(html), mode)

    def extract(self, block: dict) -> ExtractedBlockData:
        errors = []
        try:
            html, content_type = self.fetch(block["url"])
            if "json" in content_type.lower():
                payload = json.loads(html)
                return ExtractedBlockData(block["url"], block["name"], self._payload_tables([payload]), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), "live_json")
            static_result = self.extract_from_html(html, block["url"], block["name"])
            if static_result.row_count > 0:
                return static_result
        except Exception as exc:
            errors.append(f"HTTP: {exc}")

        try:
            html, payloads, endpoints = self._browser_capture(block["url"])
            result = self.extract_from_html(html, block["url"], block["name"], payloads, endpoints, "browser_network")
            if result.row_count == 0:
                result.error = "La página cargó, pero FIFA no devolvió registros estructurados para este bloque."
            return result
        except Exception as exc:
            errors.append(f"Navegador: {exc}")

        return ExtractedBlockData(
            block["url"], block["name"], [],
            pd.DataFrame(columns=["texto", "url"]),
            pd.DataFrame(columns=["tipo", "url"]),
            pd.DataFrame(columns=["tipo", "texto"]),
            "failed", " | ".join(errors),
        )

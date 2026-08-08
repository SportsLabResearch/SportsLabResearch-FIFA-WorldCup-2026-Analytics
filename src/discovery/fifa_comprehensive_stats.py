from __future__ import annotations

import re
import time
import unicodedata
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Literal
from urllib.parse import urlencode

import pandas as pd
import requests

from src.reports.variable_dictionary import build_variable_dictionary

from src.discovery.fifa_statistics_discovery import BASE_URL
from src.importers.fifa_pdf import extract_fifa_squads

Entity = Literal["players", "teams"]

SQUADS_PDF_URL = "https://fdp.fifa.org/assetspublic/ce281/pdf/SquadLists-English.pdf"
SQUADS_PDF_LOCAL = Path("data/raw/SquadLists-English.pdf")
TOURNAMENT_START = pd.Timestamp("2026-06-11")


@dataclass(frozen=True)
class StatCategory:
    id: str
    name: str


CATEGORIES = [
    StatCategory("attack", "Ataque"),
    StatCategory("distribution", "Distribución"),
    StatCategory("defending", "Defensa"),
    StatCategory("discipline", "Disciplina"),
    StatCategory("goalkeeping", "Portería"),
    StatCategory("movement", "Movimiento"),
    StatCategory("physical", "Físico"),
]


class FIFAComprehensiveStatistics:
    """Descarga exhaustiva de estadísticas FIFA World Cup 2026.

    FIFA usa identificadores de grupo distintos según la entidad:
    - jugadores: gcp_*
    - selecciones: gct_*

    Para jugadores, las estadísticas se enriquecen con la lista oficial FIFA
    de 1.248 convocados, que contiene fecha de nacimiento y metadatos de plantilla.
    """

    def __init__(self, wait: int = 2, max_scrolls: int = 8, page_timeout: int = 18):
        self.wait = wait
        self.max_scrolls = max_scrolls
        self.page_timeout = page_timeout
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0 Safari/537.36"
        )

    @staticmethod
    def _page_path(entity: Entity) -> str:
        return "player-statistics" if entity == "players" else "team-statistics"

    @staticmethod
    def _group_id(entity: Entity, category_id: str) -> str:
        prefix = "gcp" if entity == "players" else "gct"
        return f"{prefix}_{category_id}"

    def category_url(self, entity: Entity, category_id: str) -> str:
        query = urlencode({
            "group": self._group_id(entity, category_id),
            "sort": "desc",
        })
        return f"{BASE_URL}/statistics/{self._page_path(entity)}?{query}"

    def _http_html(self, url: str) -> str:
        """Intenta primero una descarga HTTP normal, más estable que Selenium."""
        response = requests.get(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
            timeout=18,
        )
        response.raise_for_status()
        return response.text

    @staticmethod
    def _minimum_rows(entity: Entity, category_id: str) -> int:
        if entity == "teams":
            return 48
        if category_id == "goalkeeping":
            return 20
        return 100

    def _valid_category_table(self, df: pd.DataFrame, entity: Entity, category_id: str) -> bool:
        if df.empty:
            return False
        key = self._find_key_column(df, entity)
        if key is None:
            return False
        return len(df.dropna(subset=[key])) >= self._minimum_rows(entity, category_id)

    @staticmethod
    def _flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        if isinstance(out.columns, pd.MultiIndex):
            out.columns = [
                " | ".join(str(v) for v in col if str(v).lower() != "nan").strip(" |")
                for col in out.columns
            ]
        out.columns = [re.sub(r"\s+", " ", str(c)).strip() for c in out.columns]
        out = out.dropna(axis=0, how="all").dropna(axis=1, how="all")
        out = out.loc[:, ~out.columns.duplicated()].reset_index(drop=True)
        return out

    @staticmethod
    def _find_key_column(df: pd.DataFrame, entity: Entity) -> str | None:
        wanted = (
            ("player", "futbolista", "jugador")
            if entity == "players"
            else ("team", "equipo", "selección", "selection")
        )
        for col in df.columns:
            low = str(col).lower()
            if any(term in low for term in wanted):
                return str(col)
        return None

    @staticmethod
    def _clean_player_label(value: object) -> tuple[object, object, object]:
        """Devuelve (jugador, selección, posición) desde la etiqueta visible de FIFA."""
        if not isinstance(value, str):
            return value, pd.NA, pd.NA

        text = re.sub(r"\s+", " ", value).strip()
        text = re.sub(r"^Image", "", text, flags=re.I).strip()

        match = re.match(
            r"^(.*?)(?:Image:\s*)?([A-Z]{3})(?:[A-Z]{3})?\s+([A-Z]{3})\s+(GK|DF|MF|FW)$",
            text,
        )
        if match:
            name = re.sub(r"Image$", "", match.group(1), flags=re.I).strip()
            team = match.group(3)
            position = match.group(4)
            return name, team, position

        match = re.match(r"^(.*?)\s+([A-Z]{3})\s+(GK|DF|MF|FW)$", text)
        if match:
            return match.group(1).strip(), match.group(2), match.group(3)

        text = re.sub(r"Image(?::)?", " ", text, flags=re.I)
        text = re.sub(r"\s+", " ", text).strip()
        return text, pd.NA, pd.NA

    @staticmethod
    def _clean_team_label(value: object) -> object:
        if not isinstance(value, str):
            return value
        text = re.sub(r"^Image", "", value, flags=re.I)
        text = re.sub(r"Image(?::)?", " ", text, flags=re.I)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _normalise_name(value: object) -> str:
        if not isinstance(value, str):
            return ""
        text = unicodedata.normalize("NFKD", value)
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        text = re.sub(r"[^A-Za-z0-9]+", " ", text).upper()
        return re.sub(r"\s+", " ", text).strip()

    @classmethod
    def _roster_match_name(cls, player_name: object) -> str:
        """Convierte 'MBAPPE Kylian' en 'KYLIAN MBAPPE' para cruzar con estadísticas."""
        if not isinstance(player_name, str):
            return ""
        parts = player_name.split()
        if len(parts) < 2:
            return cls._normalise_name(player_name)
        # En el PDF FIFA PLAYER NAME se presenta como apellido(s) + nombre de uso.
        return cls._normalise_name(" ".join(parts[1:] + parts[:1]))

    def _download_squads_pdf(self) -> Path:
        if SQUADS_PDF_LOCAL.exists() and SQUADS_PDF_LOCAL.stat().st_size > 100_000:
            return SQUADS_PDF_LOCAL

        SQUADS_PDF_LOCAL.parent.mkdir(parents=True, exist_ok=True)
        response = requests.get(
            SQUADS_PDF_URL,
            headers={"User-Agent": self.user_agent},
            timeout=45,
        )
        response.raise_for_status()
        content_type = response.headers.get("content-type", "").lower()
        if "pdf" not in content_type and not response.content.startswith(b"%PDF"):
            raise RuntimeError("FIFA no devolvió el PDF oficial de plantillas.")
        SQUADS_PDF_LOCAL.write_bytes(response.content)
        return SQUADS_PDF_LOCAL

    def official_players(self) -> pd.DataFrame:
        pdf_path = self._download_squads_pdf()
        squads = extract_fifa_squads(pdf_path).copy()
        if len(squads) != 1248 or squads["team"].nunique() != 48:
            raise RuntimeError(
                f"Plantilla FIFA incompleta: {len(squads)} jugadores / "
                f"{squads['team'].nunique()} selecciones."
            )

        birth = pd.to_datetime(squads["birth_date"], errors="coerce")
        age_days = (TOURNAMENT_START - birth).dt.days
        squads["Edad_inicio_torneo"] = (age_days / 365.2425).round(2)
        squads["Año_nacimiento"] = birth.dt.year.astype("Int64")
        squads["Mes_nacimiento"] = birth.dt.month.astype("Int64")
        squads["Trimestre_nacimiento"] = pd.cut(
            squads["Mes_nacimiento"],
            bins=[0, 3, 6, 9, 12],
            labels=["Q1", "Q2", "Q3", "Q4"],
        ).astype("string")

        squads["_match_name"] = squads["player_name"].map(self._roster_match_name)
        squads["_match_name_original"] = squads["player_name"].map(self._normalise_name)
        squads["_match_team"] = squads["team_code"].astype("string").str.upper()

        return squads.rename(columns={
            "player_name": "Nombre_FIFA_plantilla",
            "team": "Selección_nombre",
            "team_code": "Selección",
            "position": "Posición",
            "squad_number": "Dorsal",
            "birth_date": "Fecha_nacimiento",
            "club": "Club",
            "height_cm": "Altura_cm",
            "caps": "Internacionalidades",
            "goals": "Goles_selección",
            "first_names": "Nombre(s)",
            "last_names": "Apellido(s)",
            "shirt_name": "Nombre_camiseta",
        })

    def _best_table(self, html: str, entity: Entity) -> pd.DataFrame:
        try:
            frames = pd.read_html(StringIO(html))
        except (ValueError, ImportError):
            return pd.DataFrame()

        candidates: list[tuple[float, pd.DataFrame]] = []
        for raw in frames:
            df = self._flatten_columns(raw)
            if df.empty or len(df.columns) < 2:
                continue
            key = self._find_key_column(df, entity)
            if key is None:
                continue
            score = len(df) * 10 + len(df.columns)
            candidates.append((score, df))

        if not candidates:
            return pd.DataFrame()
        candidates.sort(key=lambda item: item[0], reverse=True)
        return candidates[0][1]

    def _browser_html(self, url: str) -> str:
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
        except ImportError as exc:
            raise RuntimeError("Falta Selenium. Ejecute: pip install selenium") from exc

        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--lang=en-US")
        options.add_argument(f"--user-agent={self.user_agent}")

        driver = webdriver.Chrome(options=options)
        try:
            driver.set_page_load_timeout(self.page_timeout)
            try:
                driver.get(url)
            except Exception:
                try:
                    driver.execute_script("window.stop();")
                except Exception:
                    pass
            time.sleep(self.wait)

            labels = (
                "show more", "load more", "view more", "see more",
                "mostrar más", "ver más", "cargar más",
            )
            deadline = time.monotonic() + self.page_timeout
            stable_rounds = 0
            last_height = -1

            for _ in range(self.max_scrolls):
                if time.monotonic() >= deadline:
                    break
                try:
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                except Exception:
                    break
                time.sleep(0.35)

                clicked = False
                try:
                    elements = driver.find_elements(By.XPATH, "//button | //a")
                except Exception:
                    elements = []
                for element in elements[:120]:
                    if time.monotonic() >= deadline:
                        break
                    try:
                        text = (element.text or "").strip().lower()
                        if text and any(label in text for label in labels) and element.is_displayed() and element.is_enabled():
                            driver.execute_script("arguments[0].click();", element)
                            time.sleep(0.35)
                            clicked = True
                            break
                    except Exception:
                        continue

                try:
                    height = driver.execute_script("return document.body.scrollHeight")
                except Exception:
                    height = last_height
                if not clicked and height == last_height:
                    stable_rounds += 1
                else:
                    stable_rounds = 0
                last_height = height
                if stable_rounds >= 2:
                    break
            return driver.page_source
        finally:
            try:
                driver.quit()
            except Exception:
                pass

    def download_category(self, entity: Entity, category: StatCategory) -> pd.DataFrame:
        url = self.category_url(entity, category.id)
        attempts: list[str] = []

        # 1) HTML directo. Suele contener una tabla más completa y evita depender
        #    de cómo Chrome cargue elementos virtualizados.
        try:
            html = self._http_html(url)
            df = self._best_table(html, entity)
            if not self._valid_category_table(df, entity, category.id):
                attempts.append(f"HTTP: {len(df)} filas")
                df = pd.DataFrame()
        except Exception as exc:
            attempts.append(f"HTTP: {exc}")
            df = pd.DataFrame()

        # 2) Navegador real como respaldo. Se hace scroll y se pulsan botones
        #    de carga adicional antes de leer la tabla.
        if df.empty:
            try:
                html = self._browser_html(url)
                df = self._best_table(html, entity)
                if not self._valid_category_table(df, entity, category.id):
                    attempts.append(f"Navegador: {len(df)} filas")
                    df = pd.DataFrame()
            except Exception as exc:
                attempts.append(f"Navegador: {exc}")
                df = pd.DataFrame()

        if df.empty:
            detail = " | ".join(attempts)
            raise RuntimeError(
                f"FIFA no devolvió una tabla completa para {category.name}. {detail}. URL: {url}"
            )

        key = self._find_key_column(df, entity)
        if key is None:
            raise RuntimeError(f"No se identificó la columna principal en {category.name}")

        if entity == "players":
            parsed = df[key].map(self._clean_player_label)
            df["Jugador"] = parsed.map(lambda x: x[0])
            df["Selección"] = parsed.map(lambda x: x[1])
            df["Posición"] = parsed.map(lambda x: x[2])
            df = df.drop(columns=[key])
            main_key = "Jugador"
        else:
            df[key] = df[key].map(self._clean_team_label)
            if key != "Selección":
                df = df.rename(columns={key: "Selección"})
            main_key = "Selección"

        df = df.dropna(subset=[main_key]).drop_duplicates(subset=[main_key], keep="first")

        rename: dict[str, str] = {}
        for rank_col in ("Rank", "Puesto"):
            if rank_col in df.columns:
                rename[rank_col] = f"Puesto_{category.name}"
        df = df.rename(columns=rename)

        protected = {main_key, "Selección", "Posición"}
        new_columns: dict[str, str] = {}
        for col in df.columns:
            if col in protected or str(col).startswith("Puesto_"):
                continue
            new_columns[str(col)] = f"{category.name} · {col}"
        df = df.rename(columns=new_columns)

        id_cols = [c for c in ("Jugador", "Selección", "Posición") if c in df.columns]
        other_cols = [c for c in df.columns if c not in id_cols]
        return df[id_cols + other_cols]

    @staticmethod
    def _merge_categories(frames: list[pd.DataFrame], entity: Entity) -> pd.DataFrame:
        key = "Jugador" if entity == "players" else "Selección"
        merged: pd.DataFrame | None = None
        for df in frames:
            if merged is None:
                merged = df.copy()
                continue

            # Solo en jugadores hay metadatos repetidos que deben evitarse.
            common_meta = []
            if entity == "players":
                common_meta = [
                    c for c in ("Selección", "Posición")
                    if c in merged.columns and c in df.columns
                ]
            df_merge = df.drop(columns=common_meta, errors="ignore")
            merged = merged.merge(df_merge, on=key, how="outer")

        if merged is None:
            return pd.DataFrame()
        return merged.sort_values(key, kind="stable").reset_index(drop=True)

    def _enrich_players(self, stats: pd.DataFrame) -> pd.DataFrame:
        roster = self.official_players()

        roster_columns = [
            "Nombre_FIFA_plantilla", "Nombre(s)", "Apellido(s)", "Nombre_camiseta",
            "Selección", "Selección_nombre", "Posición", "Dorsal", "Fecha_nacimiento",
            "Año_nacimiento", "Mes_nacimiento", "Trimestre_nacimiento",
            "Edad_inicio_torneo", "Club", "Altura_cm", "Internacionalidades",
            "Goles_selección", "source_page", "_match_name", "_match_name_original", "_match_team",
        ]
        roster = roster[roster_columns].copy()

        if stats.empty:
            out = roster.rename(columns={"Nombre_FIFA_plantilla": "Jugador"})
            return out.drop(columns=["_match_name", "_match_team"], errors="ignore")

        stats = stats.copy()
        stats["_match_name"] = stats["Jugador"].map(self._normalise_name)
        stats["_match_team"] = stats["Selección"].astype("string").str.upper()

        # El PDF FIFA no usa un único patrón de PLAYER NAME: normalmente aparece
        # apellido + nombre, pero algunos nombres deportivos (p. ej. VINICIUS JUNIOR)
        # ya están en el mismo orden que en las estadísticas. Probamos ambos alias.
        roster = roster.reset_index(drop=True)
        roster["_roster_id"] = roster.index
        alias_reversed = roster[["_roster_id", "_match_team", "_match_name"]].copy()
        alias_original = roster[["_roster_id", "_match_team", "_match_name_original"]].rename(
            columns={"_match_name_original": "_match_name"}
        )
        aliases = pd.concat([alias_reversed, alias_original], ignore_index=True).drop_duplicates()

        stat_payload = stats.drop(columns=["Selección", "Posición"], errors="ignore")
        matched = aliases.merge(
            stat_payload, on=["_match_name", "_match_team"], how="inner"
        ).drop_duplicates(subset=["_roster_id"], keep="first")
        matched = matched.drop(columns=["_match_name", "_match_team"], errors="ignore")
        merged = roster.merge(matched, on="_roster_id", how="left", suffixes=("", "_stat"))

        # El nombre visible de estadísticas prevalece; si falta, se usa el oficial del PDF.
        if "Jugador" in merged.columns:
            merged["Jugador"] = merged["Jugador"].fillna(merged["Nombre_FIFA_plantilla"])
        else:
            merged["Jugador"] = merged["Nombre_FIFA_plantilla"]

        first = [
            "Jugador", "Selección", "Selección_nombre", "Posición", "Dorsal",
            "Fecha_nacimiento", "Año_nacimiento", "Mes_nacimiento",
            "Trimestre_nacimiento", "Edad_inicio_torneo", "Club", "Altura_cm",
            "Internacionalidades", "Goles_selección", "Nombre(s)", "Apellido(s)",
            "Nombre_camiseta",
        ]
        first = [c for c in first if c in merged.columns]
        rest = [
            c for c in merged.columns
            if c not in first and c not in {
                "Nombre_FIFA_plantilla", "_match_name", "_match_name_original",
                "_match_team", "_roster_id"
            }
        ]
        return merged[first + rest].sort_values(
            ["Selección", "Dorsal"], kind="stable", na_position="last"
        ).reset_index(drop=True)

    def download_all(self, entity: Entity, progress=None) -> tuple[pd.DataFrame, dict[str, pd.DataFrame], list[str]]:
        frames: list[pd.DataFrame] = []
        by_category: dict[str, pd.DataFrame] = {}
        errors: list[str] = []

        if entity == "players":
            if progress:
                progress("Plantilla oficial", 0, len(CATEGORIES), "cargando 1.248 jugadores...")
            roster_check = self.official_players()
            if progress:
                progress("Plantilla oficial", 0, len(CATEGORIES),
                         f"OK · {len(roster_check)} jugadores · {roster_check['Fecha_nacimiento'].notna().sum()} fechas")

        for index, category in enumerate(CATEGORIES, 1):
            if progress:
                progress(category.name, index, len(CATEGORIES), "descargando...")
            try:
                df = self.download_category(entity, category)
                by_category[category.name] = df
                frames.append(df)
                if progress:
                    progress(category.name, index, len(CATEGORIES), f"OK · {len(df)} registros")
            except Exception as exc:
                errors.append(f"{category.name}: {exc}")
                if progress:
                    progress(category.name, index, len(CATEGORIES), "sin datos completos; continúa")

        merged = self._merge_categories(frames, entity)
        if entity == "players":
            # La plantilla oficial es la base maestra: nunca se guarda un Excel
            # de jugadores sin los 1.248 convocados y sus fechas de nacimiento.
            merged = self._enrich_players(merged)
            if len(merged) != 1248:
                raise RuntimeError(f"Salida de jugadores incompleta: {len(merged)}/1248.")
            if merged["Fecha_nacimiento"].isna().any():
                raise RuntimeError("Hay jugadores sin fecha de nacimiento en la salida final.")
        elif entity == "teams" and not merged.empty:
            if merged["Selección"].nunique() < 48:
                errors.append(
                    f"Selecciones incompletas: {merged['Selección'].nunique()}/48. "
                    "No se considera una descarga completa."
                )

        return merged, by_category, errors

    @staticmethod
    def _excel_safe_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """Elimina caracteres de control no permitidos por XML/Excel."""
        if df.empty:
            return df.copy()
        out = df.copy()
        illegal = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")

        def clean(value):
            if isinstance(value, str):
                return illegal.sub("", value)
            return value

        for col in out.columns:
            if out[col].dtype == object or pd.api.types.is_string_dtype(out[col].dtype):
                out[col] = out[col].map(clean)
        return out

    @staticmethod
    def save_excel(
        entity: Entity,
        merged: pd.DataFrame,
        categories: dict[str, pd.DataFrame],
        errors: list[str],
        output: Path,
    ) -> Path:
        output.parent.mkdir(parents=True, exist_ok=True)
        temp_output = output.with_name(output.stem + "__tmp.xlsx")
        if temp_output.exists():
            temp_output.unlink()

        merged_safe = FIFAComprehensiveStatistics._excel_safe_dataframe(merged)
        categories_safe = {
            name: FIFAComprehensiveStatistics._excel_safe_dataframe(df)
            for name, df in categories.items()
        }
        control_safe = FIFAComprehensiveStatistics._excel_safe_dataframe(
            pd.DataFrame({"Incidencias": errors or ["Ninguna"]})
        )

        try:
            with pd.ExcelWriter(temp_output, engine="openpyxl") as writer:
                merged_safe.to_excel(writer, sheet_name="Todos_los_datos", index=False)
                build_variable_dictionary(merged_safe.columns).to_excel(
                    writer, sheet_name="Diccionario_variables", index=False
                )
                for category_name, df in categories_safe.items():
                    df.to_excel(writer, sheet_name=category_name[:31], index=False)
                control_safe.to_excel(writer, sheet_name="Control", index=False)

            for ws in writer.book.worksheets:
                ws.freeze_panes = "A2"
                ws.sheet_view.showGridLines = False
                if ws.max_row >= 1:
                    ws.auto_filter.ref = ws.dimensions
                for cell in ws[1]:
                    cell.font = cell.font.copy(bold=True)
                for col in ws.columns:
                    letter = col[0].column_letter
                    width = min(
                        max((len(str(cell.value)) if cell.value is not None else 0) for cell in col) + 2,
                        45,
                    )
                    ws.column_dimensions[letter].width = max(10, width)

                # Formato de fecha real en Excel.
                header = {cell.value: cell.column for cell in ws[1]}
                if "Fecha_nacimiento" in header:
                    col_idx = header["Fecha_nacimiento"]
                    for row in range(2, ws.max_row + 1):
                        ws.cell(row=row, column=col_idx).number_format = "dd/mm/yyyy"

            temp_output.replace(output)
        except Exception:
            if temp_output.exists():
                temp_output.unlink()
            raise
        return output

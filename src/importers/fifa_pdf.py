from pathlib import Path
import re
import warnings
import logging

import pandas as pd
import pdfplumber

logging.getLogger("pdfminer").setLevel(logging.ERROR)

PLAYER_COLUMNS = [
    "squad_number", "position", "player_name", "first_names", "last_names",
    "shirt_name", "birth_date", "club", "height_cm", "caps", "goals"
]


def _team_from_text(text: str) -> tuple[str, str]:
    for line in (text or "").splitlines():
        match = re.fullmatch(r"\s*(.+?)\s+\(([A-Z]{3})\)\s*", line)
        if match:
            return match.group(1).strip(), match.group(2)
    raise ValueError("No se ha podido identificar la selección en una página del PDF.")


def _compact_row(row: list) -> list[str]:
    return [str(value).strip() for value in row if value is not None]


def extract_fifa_squads(pdf_path: Path) -> pd.DataFrame:
    records: list[dict] = []
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Could not get FontBBox")
        with pdfplumber.open(pdf_path) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                team, team_code = _team_from_text(text)
                tables = page.extract_tables()
                if not tables:
                    raise ValueError(f"No se encontró la tabla de jugadores en la página {page_number}.")

                table = tables[0]
                for raw_row in table[1:]:
                    row = _compact_row(raw_row)
                    # Las filas de jugadores tienen 11 campos tras eliminar columnas vacías.
                    if len(row) != 11 or not row[0].isdigit() or row[1] not in {"GK", "DF", "MF", "FW"}:
                        continue
                    values = dict(zip(PLAYER_COLUMNS, row))
                    values.update({
                        "team": team,
                        "team_code": team_code,
                        "source_page": page_number,
                    })
                    records.append(values)

    if not records:
        raise ValueError("No se extrajeron jugadores del PDF.")

    df = pd.DataFrame(records)
    numeric_cols = ["squad_number", "height_cm", "caps", "goals", "source_page"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    df["birth_date"] = pd.to_datetime(df["birth_date"], dayfirst=True, errors="coerce")
    return df

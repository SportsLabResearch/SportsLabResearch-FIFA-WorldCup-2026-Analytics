import re
import unicodedata
from datetime import date
import pandas as pd

COLUMN_ALIASES = {
    "player_name": {"player", "jugador", "name", "player_name", "nombre", "nombre_jugador"},
    "team": {"team", "selection", "seleccion", "national_team", "country", "pais"},
    "birth_date": {"birth_date", "fecha_nacimiento", "date_of_birth", "dob", "birthday"},
    "position": {"position", "posicion", "playing_position", "pos"},
    "club": {"club", "current_club", "equipo", "team_club"},
}


def _normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value))
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.lower().strip()
    return re.sub(r"[^a-z0-9]+", "_", value).strip("_")


def _rename_columns(df: pd.DataFrame) -> pd.DataFrame:
    normalized = {_normalize_text(col): col for col in df.columns}
    rename_map = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if _normalize_text(alias) in normalized:
                rename_map[normalized[_normalize_text(alias)]] = canonical
                break
    return df.rename(columns=rename_map)


def _calculate_age(birth_date: pd.Timestamp, reference: date) -> float:
    if pd.isna(birth_date):
        return float("nan")
    years = reference.year - birth_date.year
    return years - int((reference.month, reference.day) < (birth_date.month, birth_date.day))


def prepare_players(df: pd.DataFrame, reference_date: date | None = None) -> pd.DataFrame:
    reference_date = reference_date or date.today()
    df = _rename_columns(df.copy())
    required = ["player_name", "team", "birth_date", "position", "club"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError("Faltan columnas obligatorias: " + ", ".join(missing))

    text_cols = [c for c in ["player_name", "first_names", "last_names", "shirt_name", "team", "team_code", "position", "club"] if c in df]
    for col in text_cols:
        df[col] = (df[col].astype("string")
                   .str.replace(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", regex=True)
                   .str.strip())

    df["birth_date"] = pd.to_datetime(df["birth_date"], dayfirst=True, errors="coerce")
    df["age"] = df["birth_date"].apply(lambda value: _calculate_age(value, reference_date)).astype("Int64")
    df["birth_month"] = df["birth_date"].dt.month.astype("Int64")
    df["birth_quarter"] = pd.cut(df["birth_month"], bins=[0, 3, 6, 9, 12], labels=["Q1", "Q2", "Q3", "Q4"])
    df["birth_semester"] = pd.cut(df["birth_month"], bins=[0, 6, 12], labels=["S1", "S2"])
    df["birth_year"] = df["birth_date"].dt.year.astype("Int64")

    df = df.drop_duplicates(subset=["player_name", "team", "birth_date"], keep="first")
    preferred = [
        "team", "team_code", "squad_number", "position", "player_name", "first_names",
        "last_names", "shirt_name", "birth_date", "birth_year", "birth_month",
        "birth_quarter", "birth_semester", "age", "club", "height_cm", "caps",
        "goals", "source_page"
    ]
    return df[[c for c in preferred if c in df.columns]].reset_index(drop=True)

from __future__ import annotations

import pandas as pd

REQUIRED_PLAYER_COLUMNS = ("player_name", "team", "birth_date", "position", "club")


def validate_player_schema(df: pd.DataFrame) -> dict:
    missing = [column for column in REQUIRED_PLAYER_COLUMNS if column not in df.columns]
    duplicated_rows = int(df.duplicated().sum())
    empty = len(df) == 0
    return {
        "valid": not missing and not empty,
        "rows": len(df),
        "columns": len(df.columns),
        "missing_required_columns": missing,
        "duplicated_rows": duplicated_rows,
        "empty_dataset": empty,
    }

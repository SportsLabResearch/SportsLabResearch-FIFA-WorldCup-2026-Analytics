from pathlib import Path
import pandas as pd


def load_player_file(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()

    if suffix == ".csv":
        return pd.read_csv(path)

    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)

    raise ValueError("Formato no compatible. Utilice CSV, XLSX o XLS.")

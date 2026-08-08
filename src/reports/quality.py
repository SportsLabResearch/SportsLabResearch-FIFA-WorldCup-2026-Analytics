import pandas as pd


def build_quality_report(df: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for column in df.columns:
        missing = int(df[column].isna().sum())
        rows.append({
            "variable": column,
            "records": len(df),
            "missing": missing,
            "missing_pct": round((missing / len(df) * 100), 2) if len(df) else 0,
            "unique_values": int(df[column].nunique(dropna=True)),
        })

    return pd.DataFrame(rows)

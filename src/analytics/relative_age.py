from __future__ import annotations

import pandas as pd

QUARTERS = ["Q1", "Q2", "Q3", "Q4"]


def build_relative_age_summary(df: pd.DataFrame) -> pd.DataFrame:
    if "birth_quarter" not in df.columns:
        return pd.DataFrame(columns=["team", "n", "Q1", "Q2", "Q3", "Q4", "Q1_pct", "Q4_pct", "Q1_Q4_ratio"])

    counts = (
        df.assign(birth_quarter=df["birth_quarter"].astype("string"))
        .groupby(["team", "birth_quarter"], dropna=False)
        .size()
        .unstack(fill_value=0)
        .reindex(columns=QUARTERS, fill_value=0)
    )
    counts["n"] = counts.sum(axis=1)
    counts["Q1_pct"] = (counts["Q1"] / counts["n"] * 100).round(2)
    counts["Q4_pct"] = (counts["Q4"] / counts["n"] * 100).round(2)
    counts["Q1_Q4_ratio"] = counts.apply(
        lambda row: round(row["Q1"] / row["Q4"], 3) if row["Q4"] else None,
        axis=1,
    )
    result = counts.reset_index()
    return result[["team", "n", "Q1", "Q2", "Q3", "Q4", "Q1_pct", "Q4_pct", "Q1_Q4_ratio"]].sort_values(
        ["Q1_Q4_ratio", "team"], ascending=[False, True], na_position="last"
    )

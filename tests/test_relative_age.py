import pandas as pd
from src.analytics.relative_age import build_relative_age_summary


def test_relative_age_summary():
    df = pd.DataFrame({"team": ["A", "A", "A", "B"], "birth_quarter": ["Q1", "Q1", "Q4", "Q2"]})
    result = build_relative_age_summary(df)
    row = result[result["team"] == "A"].iloc[0]
    assert row["Q1"] == 2
    assert row["Q4"] == 1
    assert row["Q1_Q4_ratio"] == 2.0

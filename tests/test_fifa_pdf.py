from pathlib import Path
from src.importers.fifa_pdf import extract_fifa_squads


def test_extract_official_fifa_pdf_if_available():
    path = Path("data/raw/SquadLists-English.pdf")
    if not path.exists():
        return
    df = extract_fifa_squads(path)
    assert len(df) == 1248
    assert df["team"].nunique() == 48

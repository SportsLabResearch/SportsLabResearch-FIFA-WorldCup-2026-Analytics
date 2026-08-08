import pandas as pd

from src.discovery.fifa_comprehensive_stats import FIFAComprehensiveStatistics


def test_team_categories_merge_keeps_selection_key():
    a = pd.DataFrame({"Selección": ["France", "Spain"], "Ataque · Goals": [20, 14]})
    b = pd.DataFrame({"Selección": ["France", "Spain"], "Defensa · Clean Sheets": [4, 7]})
    out = FIFAComprehensiveStatistics._merge_categories([a, b], "teams")
    assert list(out["Selección"]) == ["France", "Spain"]
    assert "Ataque · Goals" in out.columns
    assert "Defensa · Clean Sheets" in out.columns


def test_player_roster_contains_birth_dates_if_official_pdf_available():
    engine = FIFAComprehensiveStatistics()
    roster = engine.official_players()
    assert len(roster) == 1248
    assert roster["Selección"].nunique() == 48
    assert roster["Fecha_nacimiento"].notna().all()
    assert "Trimestre_nacimiento" in roster.columns


def test_player_enrichment_matches_normal_and_stage_names():
    engine = FIFAComprehensiveStatistics()
    stats = pd.DataFrame({
        "Jugador": ["Kylian Mbappe", "Vinicius Junior"],
        "Selección": ["FRA", "BRA"],
        "Posición": ["FW", "FW"],
        "Ataque · Goles": [10, 4],
    })
    out = engine._enrich_players(stats)
    mbappe = out[(out["Selección"] == "FRA") & (out["Ataque · Goles"] == 10)]
    vini = out[(out["Selección"] == "BRA") & (out["Ataque · Goles"] == 4)]
    assert len(mbappe) == 1
    assert len(vini) == 1
    assert mbappe["Fecha_nacimiento"].notna().all()
    assert vini["Fecha_nacimiento"].notna().all()

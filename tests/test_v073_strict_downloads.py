import pandas as pd
import pytest
from src.discovery.fifa_comprehensive_stats import FIFAComprehensiveStatistics, StatCategory


def test_player_category_rejects_tiny_table(monkeypatch):
    engine = FIFAComprehensiveStatistics()
    tiny = pd.DataFrame({"Futbolista": [f"P{i} FRA FW" for i in range(16)], "Goles": range(16)})
    html = tiny.to_html(index=False)
    monkeypatch.setattr(engine, "_http_html", lambda url: html)
    monkeypatch.setattr(engine, "_browser_html", lambda url: html)
    with pytest.raises(RuntimeError):
        engine.download_category("players", StatCategory("attack", "Ataque"))


def test_team_category_requires_all_48(monkeypatch):
    engine = FIFAComprehensiveStatistics()
    tiny = pd.DataFrame({"Equipo": [f"Team{i}" for i in range(16)], "Goles": range(16)})
    html = tiny.to_html(index=False)
    monkeypatch.setattr(engine, "_http_html", lambda url: html)
    monkeypatch.setattr(engine, "_browser_html", lambda url: html)
    with pytest.raises(RuntimeError):
        engine.download_category("teams", StatCategory("attack", "Ataque"))


def test_player_output_is_always_official_roster(monkeypatch):
    engine = FIFAComprehensiveStatistics()
    roster = pd.DataFrame({
        "Nombre_FIFA_plantilla": [f"PLAYER {i}" for i in range(1248)],
        "Nombre(s)": ["X"]*1248,
        "Apellido(s)": ["Y"]*1248,
        "Nombre_camiseta": ["Z"]*1248,
        "Selección": [f"T{i//26:02d}" for i in range(1248)],
        "Selección_nombre": [f"Team {i//26}" for i in range(1248)],
        "Posición": ["MF"]*1248,
        "Dorsal": [(i%26)+1 for i in range(1248)],
        "Fecha_nacimiento": pd.to_datetime(["2000-01-01"]*1248),
        "Año_nacimiento": [2000]*1248,
        "Mes_nacimiento": [1]*1248,
        "Trimestre_nacimiento": ["Q1"]*1248,
        "Edad_inicio_torneo": [26.4]*1248,
        "Club": ["Club"]*1248,
        "Altura_cm": [180]*1248,
        "Internacionalidades": [1]*1248,
        "Goles_selección": [0]*1248,
        "source_page": [(i//26)+1 for i in range(1248)],
        "_match_name": [f"PLAYER {i}" for i in range(1248)],
        "_match_name_original": [f"PLAYER {i}" for i in range(1248)],
        "_match_team": [f"T{i//26:02d}" for i in range(1248)],
    })
    monkeypatch.setattr(engine, "official_players", lambda: roster)
    out = engine._enrich_players(pd.DataFrame())
    assert len(out) == 1248
    assert out["Fecha_nacimiento"].notna().all()

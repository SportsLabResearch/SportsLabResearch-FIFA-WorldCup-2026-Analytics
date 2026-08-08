from pathlib import Path


def test_fixed_fifa_competition_is_configured():
    source = Path("main.py").read_text(encoding="utf-8")
    assert "FIFA World Cup 2026" in source
    assert "BASE_URL" in source
    assert "input(\"URL" not in source


def test_complementary_menu_has_human_readable_sections():
    source = Path("main.py").read_text(encoding="utf-8")
    for label in (
        "Clasificación final del torneo",
        "Partidos, calendario y resultados",
        "Plantillas oficiales de las selecciones",
        "FIFA Power Rankings de jugadores",
    ):
        assert label in source

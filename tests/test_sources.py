from pathlib import Path

from src.core.sources import get_source, load_sources


def test_sources_configuration_exists():
    assert Path("config/sources.json").exists()


def test_load_sources():
    sources = load_sources()
    assert len(sources) >= 3


def test_fifa_source():
    source = get_source("fifa_world_cup_2026")
    assert source["type"] == "fifa_web"
    assert source["url"] == "https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026"

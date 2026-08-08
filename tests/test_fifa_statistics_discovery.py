from src.discovery.fifa_statistics_discovery import FIFAStatisticsDiscovery

def test_extract_and_classify_blocks():
    html='''<a href="/en/tournaments/mens/worldcup/canadamexicousa2026/statistics/player-statistics">P</a><a href="/en/tournaments/mens/worldcup/canadamexicousa2026/statistics/team-statistics">T</a><a href="/en/tournaments/mens/worldcup/canadamexicousa2026/standings">S</a>'''
    urls=FIFAStatisticsDiscovery._extract_candidate_urls(html,'https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026')
    assert [b.id for b in FIFAStatisticsDiscovery()._classify(urls)]==['player_statistics','team_statistics','standings']

def test_fallback(monkeypatch):
    e=FIFAStatisticsDiscovery(); monkeypatch.setattr(e,'_fetch_html',lambda: (_ for _ in ()).throw(RuntimeError('offline')))
    blocks=e.discover(); assert len(blocks)>=6 and e.last_mode=='verified_catalog'

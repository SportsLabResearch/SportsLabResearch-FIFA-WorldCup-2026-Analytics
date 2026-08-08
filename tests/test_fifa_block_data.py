from src.discovery.fifa_block_data import FIFABlockDataExtractor


def test_extracts_html_and_embedded_json_tables():
    html = '''
    <html><body><h1>Player Statistics</h1>
    <table><tr><th>Player</th><th>Goals</th></tr><tr><td>A</td><td>2</td></tr></table>
    <a href="/en/tournaments/mens/worldcup/canadamexicousa2026/teams">Teams</a>
    <script id="__NEXT_DATA__" type="application/json">
    {"props":{"players":[{"name":"A","assists":1},{"name":"B","assists":2}]}}
    </script></body></html>'''
    result = FIFABlockDataExtractor().extract_from_html(html, 'https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026/statistics/player-statistics')
    assert len(result.tables) >= 2
    assert result.row_count >= 3
    assert len(result.links) == 1

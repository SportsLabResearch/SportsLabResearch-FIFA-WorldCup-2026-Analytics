from pathlib import Path
from src.reports.block_reports import generate_reports

def test_generates_excel_and_word(tmp_path:Path):
    b={'id':'player_statistics','name':'Estadísticas de jugadores','url':'https://www.fifa.com/test/player-statistics','description':'Goles y asistencias','source':'test'}
    r=generate_reports(b,tmp_path); assert Path(r['excel']).exists() and Path(r['word']).exists()

from pathlib import Path
import pandas as pd
from openpyxl import load_workbook
from src.discovery.fifa_comprehensive_stats import FIFAComprehensiveStatistics


def test_excel_safe_dataframe_removes_control_chars():
    df = pd.DataFrame({"Jugador": ["BELGHALI Rak\x0bTest", "Normal"]})
    out = FIFAComprehensiveStatistics._excel_safe_dataframe(df)
    assert out.loc[0, "Jugador"] == "BELGHALI RakTest"


def test_save_excel_with_illegal_character(tmp_path):
    out = tmp_path / "test.xlsx"
    merged = pd.DataFrame({"Jugador": ["BELGHALI Rak\x0bTest"], "Fecha_nacimiento": [pd.Timestamp("2000-01-01")]})
    FIFAComprehensiveStatistics.save_excel("players", merged, {}, [], out)
    wb = load_workbook(out, read_only=True)
    assert wb["Todos_los_datos"]["A2"].value == "BELGHALI RakTest"
    assert not (tmp_path / "test__tmp.xlsx").exists()

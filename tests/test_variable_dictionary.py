from pathlib import Path
import pandas as pd

from src.discovery.fifa_comprehensive_stats import FIFAComprehensiveStatistics
from src.reports.variable_dictionary import build_variable_dictionary


def test_dictionary_explains_all_columns():
    cols = ["Jugador", "Fecha_nacimiento", "Ataque · Goals", "Físico · Distance"]
    dic = build_variable_dictionary(cols)
    assert list(dic["Variable"]) == cols
    assert dic["Explicación"].astype(str).str.len().min() > 10
    assert set(["Variable", "Categoría", "Explicación", "Tipo_unidad"]).issubset(dic.columns)


def test_comprehensive_excel_contains_dictionary(tmp_path: Path):
    merged = pd.DataFrame({"Jugador": ["TEST Player"], "Fecha_nacimiento": [pd.Timestamp("2000-01-01")], "Ataque · Goals": [1]})
    output = tmp_path / "test.xlsx"
    FIFAComprehensiveStatistics.save_excel("players", merged, {"Ataque": merged}, [], output)
    xls = pd.ExcelFile(output)
    assert "Diccionario_variables" in xls.sheet_names

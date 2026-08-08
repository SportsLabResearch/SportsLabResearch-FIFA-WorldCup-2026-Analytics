from datetime import date
import pandas as pd
from src.processing.players import prepare_players


def test_prepare_players_creates_rae_variables():
    df = pd.DataFrame({
        "jugador": ["A", "B"], "seleccion": ["Spain", "France"],
        "fecha_nacimiento": ["01/02/2000", "20/10/2001"],
        "posicion": ["MF", "DF"], "club": ["Club A", "Club B"],
    })
    result = prepare_players(df, reference_date=date(2026, 7, 10))
    assert list(result["birth_quarter"].astype(str)) == ["Q1", "Q4"]
    assert list(result["birth_semester"].astype(str)) == ["S1", "S2"]
    assert list(result["age"]) == [26, 24]

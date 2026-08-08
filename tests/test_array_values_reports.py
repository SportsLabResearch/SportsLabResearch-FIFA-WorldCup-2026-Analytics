import numpy as np
import pandas as pd
from pathlib import Path

from src.discovery.fifa_block_data import ExtractedBlockData
from src.reports.block_reports import generate_excel, generate_word


def test_reports_accept_numpy_arrays(tmp_path: Path):
    frame = pd.DataFrame({
        "name": ["Jugador A", "Jugador B"],
        "values": [np.array([]), np.array([1, 2, 3])],
    })
    data = ExtractedBlockData(
        url="https://example.test",
        title="Prueba",
        tables=[frame],
        links=pd.DataFrame(columns=["texto", "url"]),
        endpoints=pd.DataFrame(columns=["tipo", "url"]),
        text_sections=pd.DataFrame(columns=["tipo", "texto"]),
        discovery_mode="test",
    )
    block = {"name": "Prueba arrays", "description": "Prueba", "url": "https://example.test"}
    assert generate_excel(block, data, tmp_path / "Excel").exists()
    assert generate_word(block, data, tmp_path / "Word").exists()

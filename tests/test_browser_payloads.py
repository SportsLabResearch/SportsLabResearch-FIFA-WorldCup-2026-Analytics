from src.discovery.fifa_block_data import FIFABlockDataExtractor

def test_payload_tables_extract_records():
    ex = FIFABlockDataExtractor()
    payload = {"data": {"players": [
        {"name": "A", "goals": 2, "team": "X"},
        {"name": "B", "goals": 1, "team": "Y"},
    ]}}
    tables = ex._payload_tables([payload])
    assert tables
    assert len(tables[0]) == 2
    assert "name" in tables[0].columns

from src.datasets.registry import load_registry, register_dataset


def test_registry_roundtrip(tmp_path):
    path = tmp_path / "datasets.json"
    register_dataset({"dataset_name": "Test", "rows": 2}, path)
    records = load_registry(path)
    assert records[0]["dataset_name"] == "Test"
    assert records[0]["rows"] == 2

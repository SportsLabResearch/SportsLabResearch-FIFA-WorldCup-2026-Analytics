from pathlib import Path
from src.core.audit import audit_project


def test_consolidated_directories_exist():
    for path in ["src/analytics", "src/validation", "src/datasets", "src/visualization", "src/export", "data/processed", "data/metadata"]:
        assert Path(path).exists()


def test_project_audit_is_complete():
    assert audit_project()["score"] == 100.0

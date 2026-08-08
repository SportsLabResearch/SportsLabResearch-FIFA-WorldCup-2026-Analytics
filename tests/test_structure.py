from pathlib import Path


def test_required_governance_files_exist():
    root = Path(__file__).resolve().parents[1]
    required = [
        "README.md",
        "CHANGELOG.md",
        "LICENSE",
        "CITATION.cff",
        ".gitignore",
    ]
    for name in required:
        assert (root / name).exists(), f"Missing required file: {name}"

from __future__ import annotations

from pathlib import Path

REQUIRED_PATHS = [
    "config/sources.json", "data/raw", "data/processed", "data/metadata",
    "docs", "results", "src/core", "src/datasets", "src/importers",
    "src/processing", "src/analytics", "src/validation", "src/reports",
    "src/visualization", "src/export", "tests", "README.md",
    "CHANGELOG.md", "LICENSE", "CITATION.cff", "pyproject.toml",
]


def audit_project(root: Path = Path(".")) -> dict:
    checks = [{"path": item, "exists": (root / item).exists()} for item in REQUIRED_PATHS]
    passed = sum(check["exists"] for check in checks)
    total = len(checks)
    return {
        "score": round(passed / total * 100, 1) if total else 0.0,
        "passed": passed,
        "total": total,
        "checks": checks,
    }

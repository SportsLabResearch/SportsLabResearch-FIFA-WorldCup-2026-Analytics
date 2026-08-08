from __future__ import annotations

from pathlib import Path

from src.datasets.registry import register_dataset
from src.downloaders.pdf import download_pdf, is_url
from src.importers.fifa_pdf import extract_fifa_squads
from src.importers.tabular import load_player_file
from src.processing.players import prepare_players
from src.reports.excel import export_workbook
from src.validation.schema import validate_player_schema


def _safe_output_name(source_name: str) -> str:
    cleaned = "".join(character if character.isalnum() else "_" for character in source_name.strip())
    return "_".join(part for part in cleaned.split("_") if part) or "SportsLab_Analytics"


def run_pipeline(source: str, source_name: str = "Imported_Dataset", competition: str = "Custom dataset") -> dict:
    source = str(source).strip()
    if not source:
        raise ValueError("La fuente de datos está vacía.")
    downloaded_pdf = None
    if is_url(source):
        print("Descargando fuente oficial...")
        pdf_path = download_pdf(source, Path("data/raw"))
        downloaded_pdf = pdf_path
        print("Extrayendo datos del PDF...")
        raw = extract_fifa_squads(pdf_path)
        input_type = "PDF URL"
    else:
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"No se encuentra el archivo: {path}")
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            print("Extrayendo datos del PDF...")
            raw = extract_fifa_squads(path)
            input_type = "PDF local"
        elif suffix in {".csv", ".xlsx", ".xls"}:
            print("Importando tabla local...")
            raw = load_player_file(path)
            input_type = "Tabla local"
        else:
            raise ValueError("Formato no compatible. Use PDF, CSV, XLSX o XLS.")
    print("Limpiando y normalizando datos...")
    clean = prepare_players(raw)
    validation = validate_player_schema(clean)
    if not validation["valid"]:
        raise ValueError(f"Dataset no válido: {validation}")
    output_path = Path("results") / f"{_safe_output_name(source_name)}_Database.xlsx"
    print("Generando Excel científico...")
    output_file = export_workbook(clean, output_path, source, input_type, source_name, competition)
    registry_record = register_dataset({
        "dataset_name": source_name, "competition": competition,
        "source": source, "input_type": input_type,
        "rows": len(clean), "teams": int(clean["team"].nunique()),
        "output_file": str(output_file), "validation": validation,
    })
    return {
        "input_type": input_type, "rows": len(clean),
        "teams": int(clean["team"].nunique()), "downloaded_pdf": downloaded_pdf,
        "output_file": output_file, "dataset_name": source_name,
        "competition": competition, "validation": validation,
        "registry_record": registry_record,
    }

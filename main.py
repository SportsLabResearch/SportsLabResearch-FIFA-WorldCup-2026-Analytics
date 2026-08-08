from pathlib import Path

from src.core.audit import audit_project
from src.discovery.fifa_comprehensive_stats import FIFAComprehensiveStatistics
from src.discovery.fifa_statistics_discovery import BASE_URL
from src.reports.block_reports import generate_reports
from src.version import __version__

RESULTS = Path("results")
FIFA_RESULTS = RESULTS / "FIFA_World_Cup_2026"
LEGACY_RESULTS = RESULTS / "FIFA_Statistics"
COMPETITION = "FIFA World Cup 2026"


def show_header() -> None:
    print("=" * 72)
    print("SportsLab-Analytics · SportsLabResearch")
    print(f"Versión {__version__} · {COMPETITION}")
    print("=" * 72)


def show_audit() -> None:
    audit = audit_project()
    print(f"\nAUDITORÍA: {audit['score']}% ({audit['passed']}/{audit['total']})")
    for check in audit["checks"]:
        status = "OK" if check["exists"] else "FALTA"
        print(f"[{status}] {check['path']}")


def run_comprehensive(entity: str) -> None:
    labels = {"players": "JUGADORES", "teams": "SELECCIONES"}
    filenames = {
        "players": FIFA_RESULTS / "Players" / "FIFA_2026_Player_Statistics.xlsx",
        "teams": FIFA_RESULTS / "Teams" / "FIFA_2026_Team_Statistics.xlsx",
    }

    print(f"\nDESCARGA COMPLETA · {labels[entity]}")
    print("Recorriendo: Ataque, Distribución, Defensa, Disciplina, Portería, Movimiento y Físico.")
    if entity == "players":
        print("Añadiendo plantilla oficial FIFA: fecha de nacimiento, club, dorsal y datos básicos.")

    engine = FIFAComprehensiveStatistics()

    def progress(name: str, index: int, total: int, message: str) -> None:
        if index == 0:
            print(f"  [BASE] {name}: {message}", flush=True)
        else:
            print(f"  [{index}/{total}] {name}: {message}", flush=True)

    merged, categories, errors = engine.download_all(entity, progress=progress)
    if entity == "teams" and (merged.empty or merged.get("Selección", []).nunique() < 48):
        raise RuntimeError(
            "La descarga de selecciones no está completa. No se genera un Excel defectuoso."
        )
    output = engine.save_excel(entity, merged, categories, errors, filenames[entity])

    print(f"\nRegistros consolidados: {len(merged)}")
    print(f"Variables consolidadas: {len(merged.columns)}")
    print(f"Categorías recuperadas: {len(categories)}/7")
    print(f"Excel: {output}")
    if errors:
        print("\nINCIDENCIAS:")
        for error in errors:
            print(f"- {error}")


def parse_selection(value: str, total: int) -> list[int]:
    value = value.strip().upper()
    if value in {"A", "T", "TODAS", "TODO"}:
        return list(range(total))
    selected: set[int] = set()
    for part in value.replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = [int(item.strip()) for item in part.split("-", 1)]
            if start > end:
                start, end = end, start
            selected.update(range(start - 1, end))
        else:
            selected.add(int(part) - 1)
    if not selected or any(index < 0 or index >= total for index in selected):
        raise ValueError("Selección no válida.")
    return sorted(selected)


def run_other_blocks() -> None:
    blocks = [
        {
            "id": "final_standings",
            "name": "Clasificación final del torneo",
            "url": f"{BASE_URL}/articles/final-tournament-standings",
            "description": "Posición final de las 48 selecciones al terminar la FIFA World Cup 2026.",
        },
        {
            "id": "matches",
            "name": "Partidos, calendario y resultados",
            "url": f"{BASE_URL}/matches",
            "description": "Partidos disputados, fechas, fases, equipos y resultados del torneo.",
        },
        {
            "id": "squads",
            "name": "Plantillas oficiales de las selecciones",
            "url": f"{BASE_URL}/teams",
            "description": "Información complementaria de las plantillas y selecciones participantes.",
        },
        {
            "id": "power_rankings",
            "name": "FIFA Power Rankings de jugadores",
            "url": f"{BASE_URL}/power-rankings",
            "description": "Clasificaciones individuales FIFA en ataque, creatividad y defensa, y métricas específicas de porteros.",
        },
    ]

    print("\nINFORMACIÓN COMPLEMENTARIA FIFA")
    print("Seleccione el contenido que desea descargar:")
    for index, block in enumerate(blocks, 1):
        print(f"{index}. {block['name']}")
    print("5. Descargar todos los apartados")
    print("0. Volver")

    raw = input("\nSeleccione una opción: ").strip()
    if raw == "0":
        return
    if raw == "5":
        positions = range(len(blocks))
    elif raw in {"1", "2", "3", "4"}:
        positions = [int(raw) - 1]
    else:
        raise ValueError("Opción no válida.")

    for position in positions:
        block = blocks[position]
        print(f"\nProcesando: {block['name']}")
        result = generate_reports(block, LEGACY_RESULTS)
        print(f"  Registros: {result['rows']}")
        print(f"  Excel: {result['excel']}")
        print(f"  Word:  {result['word']}")
        if result.get("error"):
            print(f"  Aviso: {result['error']}")


def main() -> None:
    while True:
        show_header()
        print("1. Descargar estadísticas completas de jugadores")
        print("2. Descargar estadísticas completas de selecciones")
        print("3. Descargar jugadores + selecciones")
        print("4. Información complementaria FIFA")
        print("5. Auditoría")
        print("6. Salir")

        option = input("\nSeleccione una opción: ").strip()
        try:
            if option == "1":
                run_comprehensive("players")
            elif option == "2":
                run_comprehensive("teams")
            elif option == "3":
                run_comprehensive("players")
                run_comprehensive("teams")
            elif option == "4":
                run_other_blocks()
            elif option == "5":
                show_audit()
            elif option in {"6", "0"}:
                print("\nPrograma finalizado.")
                break
            else:
                print("\nOpción no válida.")
        except KeyboardInterrupt:
            print("\n\nPrograma finalizado.")
            break
        except Exception as exc:
            print(f"\nERROR: {exc}")

        input("\nPulse ENTER para volver al menú...")
        print("\n" * 2)


if __name__ == "__main__":
    main()

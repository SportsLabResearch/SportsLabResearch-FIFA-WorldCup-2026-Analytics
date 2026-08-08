from __future__ import annotations

import re
import pandas as pd

BASE_DESCRIPTIONS = {
    "Jugador": ("Identificación", "Nombre del jugador.", "Texto"),
    "Selección": ("Identificación", "Selección nacional a la que pertenece el jugador o registro.", "Texto"),
    "Selección_nombre": ("Identificación", "Nombre completo de la selección nacional.", "Texto"),
    "Posición": ("Identificación", "Posición habitual del jugador en el campo.", "Categoría"),
    "Dorsal": ("Identificación", "Número de camiseta asignado al jugador en el torneo.", "Número"),
    "Fecha_nacimiento": ("Datos personales deportivos", "Fecha de nacimiento del jugador según la plantilla oficial de FIFA.", "Fecha"),
    "Año_nacimiento": ("Datos personales deportivos", "Año de nacimiento derivado de la fecha de nacimiento.", "Año"),
    "Mes_nacimiento": ("Datos personales deportivos", "Mes de nacimiento derivado de la fecha de nacimiento.", "Mes"),
    "Trimestre_nacimiento": ("Datos personales deportivos", "Trimestre natural de nacimiento: Q1 enero-marzo, Q2 abril-junio, Q3 julio-septiembre y Q4 octubre-diciembre.", "Categoría"),
    "Edad_inicio_torneo": ("Datos personales deportivos", "Edad del jugador al inicio de la FIFA World Cup 2026.", "Años"),
    "Club": ("Identificación", "Club de procedencia declarado en la plantilla oficial de FIFA.", "Texto"),
    "Altura_cm": ("Antropometría", "Altura del jugador.", "cm"),
    "Internacionalidades": ("Experiencia internacional", "Número de partidos internacionales disputados antes o según el registro oficial de plantilla.", "Partidos"),
    "Goles_selección": ("Experiencia internacional", "Número de goles internacionales acumulados según la plantilla oficial.", "Goles"),
}

PATTERNS = [
    (r"puesto|rank", "Clasificación ordinal dentro de la métrica correspondiente.", "Puesto"),
    (r"goal|goles", "Número de goles registrados en la competición para esta métrica.", "Goles"),
    (r"assist|asist", "Número de asistencias registradas en la competición.", "Asistencias"),
    (r"minute|minutos", "Tiempo acumulado de participación en la competición.", "Minutos"),
    (r"attempt|shot|tiro|remate", "Número de intentos de finalización registrados por FIFA.", "Acciones"),
    (r"expected goals|\bxg\b", "Valor de goles esperados estimado por el modelo estadístico de FIFA.", "xG"),
    (r"pass|pase", "Métrica relacionada con la distribución y ejecución de pases.", "Acciones / %"),
    (r"accuracy|precisi", "Porcentaje de acierto o precisión en la acción indicada.", "%"),
    (r"possession|posesi", "Proporción de posesión del balón registrada durante la competición.", "%"),
    (r"cross|centro", "Número de centros realizados o completados, según la variable FIFA.", "Acciones"),
    (r"dribbl|regate", "Número o rendimiento de acciones de regate registradas por FIFA.", "Acciones / %"),
    (r"tackle|entrada", "Número de entradas defensivas registradas.", "Acciones"),
    (r"interception|intercep", "Número de interceptaciones defensivas registradas.", "Acciones"),
    (r"clearance|despeje", "Número de despejes defensivos registrados.", "Acciones"),
    (r"save|parada", "Número de paradas realizadas por el guardameta.", "Paradas"),
    (r"clean sheet|portería a cero", "Número de partidos finalizados sin encajar gol.", "Partidos"),
    (r"yellow|amarilla", "Número de tarjetas amarillas recibidas.", "Tarjetas"),
    (r"red|roja", "Número de tarjetas rojas recibidas.", "Tarjetas"),
    (r"foul|falta", "Número de faltas cometidas o recibidas, según la variable FIFA.", "Faltas"),
    (r"distance|distancia", "Distancia recorrida registrada durante la competición.", "km / m"),
    (r"speed|velocidad", "Métrica de velocidad registrada por FIFA.", "km/h"),
    (r"sprint", "Métrica relacionada con acciones de sprint registradas por FIFA.", "Acciones / km/h"),
    (r"match|played|partidos", "Número de partidos correspondientes al registro.", "Partidos"),
    (r"won|victorias", "Número de partidos ganados.", "Partidos"),
    (r"draw|empates", "Número de partidos empatados.", "Partidos"),
    (r"lost|derrotas", "Número de partidos perdidos.", "Partidos"),
    (r"points|puntos", "Puntos obtenidos en la clasificación.", "Puntos"),
]


def _split_category(variable: str) -> tuple[str, str]:
    if " · " in variable:
        category, label = variable.split(" · ", 1)
        return category.strip(), label.strip()
    if variable.startswith("Puesto_"):
        return variable.replace("Puesto_", "", 1), "Puesto"
    return "General", variable


def describe_variable(variable: str) -> tuple[str, str, str]:
    if variable in BASE_DESCRIPTIONS:
        return BASE_DESCRIPTIONS[variable]
    category, label = _split_category(variable)
    normalized = re.sub(r"[_-]+", " ", label).strip()
    low = normalized.lower()
    for pattern, explanation, unit in PATTERNS:
        if re.search(pattern, low, flags=re.I):
            return category, explanation, unit
    return category, f"Variable publicada por FIFA denominada «{normalized}» dentro del bloque {category}.", "Según FIFA"


def build_variable_dictionary(columns) -> pd.DataFrame:
    rows = []
    for variable in map(str, columns):
        category, explanation, unit = describe_variable(variable)
        rows.append({
            "Variable": variable,
            "Categoría": category,
            "Explicación": explanation,
            "Tipo_unidad": unit,
        })
    return pd.DataFrame(rows)

# SportsLab-Analytics

**Versión 0.7.3-alpha**

Herramienta de SportsLabResearch para descargar, organizar y exportar datos de la FIFA World Cup 2026™.

## Menú principal

1. Descargar estadísticas completas de jugadores
2. Descargar estadísticas completas de selecciones
3. Descargar jugadores + selecciones
4. Otros bloques FIFA
5. Auditoría
6. Salir

## Opción 1 · Jugadores

Recorre las categorías FIFA de Ataque, Distribución, Defensa, Disciplina, Portería, Movimiento y Físico. Las estadísticas se cruzan con la lista oficial de plantillas de FIFA para incorporar, entre otros campos:

- Fecha de nacimiento
- Selección
- Posición
- Dorsal
- Club
- Altura
- Internacionalidades
- Goles con la selección
- Año, mes y trimestre de nacimiento
- Edad al inicio del torneo

El PDF oficial de plantillas se descarga automáticamente desde FIFA y se conserva en `data/raw/SquadLists-English.pdf` para reutilizarlo.

Salida principal:

`results/FIFA_World_Cup_2026/Players/FIFA_2026_Player_Statistics.xlsx`

## Opción 2 · Selecciones

Recorre las mismas siete categorías con los identificadores específicos de estadísticas de selecciones y consolida los resultados por selección.

Salida principal:

`results/FIFA_World_Cup_2026/Teams/FIFA_2026_Team_Statistics.xlsx`

## Opción 3

Ejecuta consecutivamente las opciones 1 y 2.

## Opción 4

Mantiene el sistema de descubrimiento de otros bloques FIFA y genera los informes disponibles en Excel y Word.

## Opción 5

Comprueba la integridad básica de la estructura del proyecto.

## Instalación

```powershell
pip install -r requirements.txt
python main.py
```

Se requiere Google Chrome o Chromium para la lectura dinámica de las páginas estadísticas de FIFA.


## Versión 0.7.7

- Las descargas completas de jugadores y selecciones mantienen la lógica estable de la versión anterior.
- Los Excel incorporan la hoja `Diccionario_variables`, con nombre, categoría, explicación y tipo/unidad de cada variable.
- La opción 4 pasa a denominarse **Información complementaria FIFA** y ofrece cuatro apartados legibles: clasificación final, partidos/resultados, plantillas oficiales y FIFA Power Rankings.
- Se eliminan de las salidas de la opción 4 columnas técnicas internas que no aportan información deportiva útil.

# Changelog

## 0.7.3-alpha - 2026-08-08

- Corregido el error `KeyError: Selección` al consolidar estadísticas de selecciones.
- Añadida la lista oficial FIFA de 1.248 jugadores como fuente de metadatos.
- Añadida `Fecha_nacimiento` a la salida consolidada de jugadores.
- Añadidos dorsal, club, altura, internacionalidades, goles con la selección y variables derivadas de nacimiento.
- Mejorado el cruce de nombres entre estadísticas y plantillas FIFA.
- Menú actualizado: la opción 6 finaliza el programa; la opción 0 se mantiene como compatibilidad interna.
- Añadidas pruebas de regresión para la consolidación de selecciones y el enriquecimiento de jugadores.

## 0.6.2-alpha
- Corregida la fuente principal de FIFA World Cup 2026: ahora apunta a la página oficial del torneo.
- El PDF de plantillas se conserva como fuente auxiliar desactivada.
- Mantenidos exclusivamente los 6 bloques independientes verificados del menú.
- Alineada la configuración de fuentes con el motor real de descubrimiento web.

## 0.5.4-alpha
- Corregido el error `truth value of an empty array is ambiguous`.
- Conversión segura de arrays NumPy en informes Word y Excel.
- Añadida prueba de regresión para arrays vacíos y arrays con datos.
- Verificada la generación de ambos formatos.


## [0.3.0-alpha] - 2026-07-12

### Added
- Arquitectura modular consolidada.
- Registro persistente de datasets.
- Validación del esquema normalizado.
- Módulo científico inicial de efecto de edad relativa.
- Hoja `Relative_Age` en los informes Excel.
- Auditoría estructural desde el menú.
- Directorios `processed`, `cache`, `metadata`, `analytics`, `validation`, `visualization`, `export` y `datasets`.

### Changed
- Pipeline desacoplado en capas funcionales.
- Metadatos de versión centralizados.
- README y estructura actualizados.

### Preserved
- Importación del PDF oficial FIFA.
- Importación local CSV y Excel.
- Limpieza y normalización de jugadores.
- Exportación Excel existente.


## v0.4.0-alpha
- FIFA Statistics Discovery Engine
- Dataset Registry
- Analytics module scaffold
- Dashboard/results folders

## v0.5.3-alpha
- Sustituida la extracción estática por renderizado Chrome/Selenium.
- Captura de respuestas JSON de la red utilizadas por FIFA.
- Conversión automática de payloads JSON en tablas Excel y Word.
- Mensajes de error reales cuando FIFA no devuelve registros.

## 0.5.5-alpha
- Eliminada cualquier solicitud de URL en el flujo principal.
- FIFA World Cup 2026 y su página oficial quedan configuradas internamente.
- El programa abre directamente el inventario de bloques estadísticos.
- Eliminadas del menú principal las entradas locales que podían confundirse con el flujo FIFA.

# Datos

Los datos no se versionan porque contienen datos personales (nombres, correos y códigos de estudiantes y monitores, y comentarios abiertos).

Para reproducir:

1. Copiar `Bookeau.zip` (compartido por la coordinación de CupiTaller) en `data/bronce/` y descomprimirlo como `data/bronce/Bookeau/`.
2. Desde la raíz del proyecto, ejecutar `python3 src/main.py`, que corre todos los pasos en orden. Se regeneran `data/plata/` (Silver) y `data/oro/` (Gold, incluida `bookeau.sqlite3`).

## Datos ficticios para probar el flujo

`python3 src/main.py --dummy` genera libros de Excel inventados (sin información personal) en `data/bronce/dummy/` y ejecuta todo el pipeline sobre ellos. Los libros se guardan en `data/bronce/dummy/` (no toca `data/bronce/Bookeau/`) y el resto del flujo es el mismo: Silver en `data/plata/`, Gold en `data/oro/` y documentación y tablero en `docs/`. Por eso **reemplaza los resultados que hubiera**; para volver a los reales basta ejecutar `python3 src/main.py` sin `--dummy`. Los libros ficticios sí se pueden versionar.

| Capa | Carpeta | Contenido |
|---|---|---|
| Bronze | `data/bronce/` | ZIP y 114 Excel originales, sin modificar |
| Silver | `data/plata/` | 5 CSV limpios con trazabilidad y banderas |
| Gold | `data/oro/` | Dimensiones, hechos y base SQLite |

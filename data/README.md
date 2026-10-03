# Datos

Los datos no se versionan porque contienen datos personales (nombres, correos y códigos de estudiantes y monitores, y comentarios abiertos).

Para reproducir:

1. Copiar `Bookeau.zip` (compartido por la coordinación de CupiTaller) en `data/bronce/` y descomprimirlo como `data/bronce/Bookeau/`.
2. Desde la raíz del proyecto, ejecutar los scripts en el orden indicado en el README principal. Se regeneran `data/plata/` (Silver) y `data/oro/` (Gold, incluida `bookeau.sqlite3`).

| Capa | Carpeta | Contenido |
|---|---|---|
| Bronze | `data/bronce/` | ZIP y 114 Excel originales, sin modificar |
| Silver | `data/plata/` | 5 CSV limpios con trazabilidad y banderas |
| Gold | `data/oro/` | Dimensiones, hechos y base SQLite |

#!/usr/bin/env bash
# Exporta poster.html (o el nombre dado, p. ej. poster_corregido) a PDF de 70 x 100 cm, una hoja.
# Fuera de macOS, indicar el ejecutable de Chrome o Chromium con CHROME=/ruta/al/navegador.
set -euo pipefail
NOMBRE="${1:-poster}"
# El póster vive en docs/entregables/e2_poster/; este script está en src/auxiliar/.
cd "$(dirname "$0")/../../docs/entregables/e2_poster"
"${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}" --headless=new --disable-gpu \
  --no-pdf-header-footer --allow-file-access-from-files --virtual-time-budget=8000 \
  --print-to-pdf="$NOMBRE.pdf" "file://$PWD/$NOMBRE.html" 2> /dev/null
pdfinfo "$NOMBRE.pdf" | grep -E "Pages|Page size"

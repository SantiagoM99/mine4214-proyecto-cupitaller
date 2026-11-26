#!/usr/bin/env bash
# Exporta poster.html a poster.pdf (70 x 100 cm, una hoja) con Chrome sin interfaz.
set -euo pipefail
cd "$(dirname "$0")"
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --disable-gpu \
  --no-pdf-header-footer --allow-file-access-from-files --virtual-time-budget=8000 \
  --print-to-pdf=poster.pdf "file://$PWD/poster.html" 2> /dev/null
pdfinfo poster.pdf | grep -E "Pages|Page size"

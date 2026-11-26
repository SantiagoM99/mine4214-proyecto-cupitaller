#!/usr/bin/env bash
# Mide cuántos milímetros sobran (+) o faltan (-) en cada columna del póster.
# Sirve para ajustar el contenido sin adivinar a partir de una imagen.
set -euo pipefail
# El póster vive en docs/entregables/e2_poster/; este script está en src/auxiliar/.
cd "$(dirname "$0")/../../docs/entregables/e2_poster"
cat > .medir.js <<'JS'
// Se mide al terminar de cargar: antes de eso las figuras SVG todavía no tienen alto.
window.addEventListener('load', () => {
  const mm = px => (px / 3.7795).toFixed(0);
  // Las tarjetas se estiran para llenar la columna; aquí interesa su alto natural.
  document.querySelectorAll('.columna > .tarjeta').forEach(tarjeta => { tarjeta.style.flex = 'none'; });
  document.body.dataset.medida = [...document.querySelectorAll('.columna')].map((columna, i) => {
    const contenido = [...columna.children].reduce((suma, hijo) => suma + hijo.getBoundingClientRect().height, 0);
    const separacion = parseFloat(getComputedStyle(columna).rowGap);
    const disponible = columna.getBoundingClientRect().height - separacion * (columna.children.length - 1);
    return `columna ${i + 1}: ${mm(disponible - contenido)} mm`;
  }).join(' | ');
});
JS
python3 - <<'PY'
from pathlib import Path
html = Path('poster.html').read_text(encoding='utf-8')
Path('.medir.html').write_text(html.replace('</body>', f"<script>{Path('.medir.js').read_text()}</script></body>"), encoding='utf-8')
PY
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --disable-gpu --allow-file-access-from-files \
  --virtual-time-budget=8000 --dump-dom "file://$PWD/.medir.html" 2> /dev/null | grep -o 'data-medida="[^"]*"'
rm -f .medir.html .medir.js

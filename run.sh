#!/usr/bin/env bash
# Levantar capataz.
#
#     ./run.sh                 → http://127.0.0.1:5402
#     ./run.sh --instantanea   una copia estática con los datos adentro, para
#                              mirar el ancho angosto en un navegador que no
#                              llega al puerto (ver ops/00-mapa.md)
#
# Sin venv y sin instalar nada: capataz usa sólo la biblioteca estándar. Es la
# misma línea que `panel/panel.py` de ERP 360 y está escrito por qué en
# `lector.py`.

set -uo pipefail
cd "$(dirname "$0")"

exec python3 capataz.py "$@"

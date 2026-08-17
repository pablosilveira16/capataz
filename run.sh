#!/usr/bin/env bash
# Levantar capataz.
#
#     ./run.sh                 → http://127.0.0.1:5402, sólo esta máquina
#     ./run.sh --telefono      → abierto a la red de casa, para leerlo desde el
#                                teléfono. El nombre ya existe y lo publica
#                                macOS: http://<LocalHostName>.local:5402
#     ./run.sh --instantanea   una copia estática con los datos adentro, para
#                              mirar el ancho angosto en un navegador que no
#                              llega al puerto (ver ops/00-mapa.md)
#
# Sin venv y sin instalar nada: capataz usa sólo la biblioteca estándar. Es la
# misma línea que `panel/panel.py` de ERP 360 y está escrito por qué en
# `lector.py`.

set -uo pipefail
cd "$(dirname "$0")"

# `--telefono` no es un argumento de la app: es la decisión de a quién le
# contesta, y por eso viaja como entorno y se traduce acá. El default de
# `capataz.py` sigue siendo sólo esta máquina, así que olvidarse de la bandera
# no expone nada — que es el error que conviene que sea el barato.
ARGS=()
for a in "$@"; do
  if [ "$a" = "--telefono" ]; then
    export CAPATAZ_ESCUCHA=0.0.0.0
  else
    ARGS+=("$a")
  fi
done

exec python3 capataz.py ${ARGS+"${ARGS[@]}"}

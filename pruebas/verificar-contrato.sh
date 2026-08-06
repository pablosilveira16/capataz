#!/usr/bin/env bash
# El arnés más tonto del proyecto, y el primero: el contrato de SEGUIMIENTO.md.
#
# Existe antes que la primera línea de la app a propósito
# (`ERP360-Template/documentacion/andamio-proyecto-nuevo.md`, «El orden»): un
# proyecto sin compuerta forma la costumbre de mirar a ojo, y esa costumbre
# después no se saca.
#
# Verifica dos cosas y nada más:
#
#   1. `SEGUIMIENTO.md` existe y nombra los cinco estados.
#   2. Ninguna celda de estado, en ninguna tabla que tenga columna `Estado`,
#      usa una palabra que no sea una de las cinco.
#
# Lo segundo es el que vale. Un estado inventado —`relevado`, `en revisión`— no
# lo sabe leer ningún agente, y capataz, que lee seguimientos ajenos, tampoco.
#
#     bash pruebas/verificar-contrato.sh

cd "$(dirname "$0")/.." || exit 1

ASER=0
ROJAS=0

ok()   { ASER=$((ASER+1)); }
roja() { ROJAS=$((ROJAS+1)); printf 'ROJA  %s\n' "$1"; }

af() {  # af <descripción> <condición ya evaluada: 0 = bien>
  if [ "$2" = "0" ]; then ok; else roja "$1"; fi
}

SEG="SEGUIMIENTO.md"

# --- 1 · el archivo existe ------------------------------------------------
if [ -f "$SEG" ]; then ok; else
  roja "no existe $SEG — es el primer archivo del proyecto"
  printf '\nASERCIONES: %d\nROJAS: %d\n' "$ASER" "$ROJAS"
  exit 1
fi

# --- 2 · nombra los cinco estados ----------------------------------------
for e in pendiente "en curso" hecho diferido descartado; do
  grep -qF "\`$e\`" "$SEG"
  af "el contrato de $SEG no nombra el estado \`$e\`" $?
done

# --- 3 · ninguna celda de estado usa una palabra fuera de las cinco -------
#
# Se mira la ÚLTIMA celda de cada fila de datos de cada tabla cuyo encabezado
# tenga una columna `Estado` — que es donde el contrato dice que va. Una tabla
# sin esa columna no se mira acá: eso es el punto T4, y lo sufre el lector.
malas="$(awk '
  /^\|/ {
    if ($0 ~ /^\|[[:space:]:|-]+\|[[:space:]]*$/) {
      enTabla = 1
      conEstado = (encabezado ~ /Estado/)
      next
    }
    if (!enTabla) { encabezado = $0; next }
    if (!conEstado) next
    n = split($0, c, "|")
    celda = c[n-1]
    gsub(/[*`]/, "", celda)
    gsub(/^[[:space:]]+|[[:space:]]+$/, "", celda)
    if (celda == "") { print NR ": celda de estado vacía"; next }
    if (celda ~ /pendiente|en curso|hecho|diferido|descartado/) next
    print NR ": «" celda "» no es uno de los cinco estados"
    next
  }
  { enTabla = 0; encabezado = "" }
' "$SEG")"

filas="$(awk '
  /^\|/ {
    if ($0 ~ /^\|[[:space:]:|-]+\|[[:space:]]*$/) { enTabla=1; conEstado=(encabezado ~ /Estado/); next }
    if (!enTabla) { encabezado=$0; next }
    if (conEstado) n++
    next
  }
  { enTabla=0; encabezado="" }
  END { print n+0 }
' "$SEG")"

if [ "$filas" -eq 0 ]; then
  # Cero filas también es falla: quiere decir que este arnés dejó de encontrar
  # las tablas que mira y estaría saltando en silencio.
  roja "no encontré ninguna fila de datos con columna Estado en $SEG"
else
  for i in $(seq 1 "$filas"); do ok; done
  if [ -n "$malas" ]; then
    while IFS= read -r m; do
      [ -z "$m" ] && continue
      ROJAS=$((ROJAS+1)); ASER=$((ASER-1))
      printf 'ROJA  %s:%s\n' "$SEG" "$m"
    done <<< "$malas"
  fi
fi

printf '\nASERCIONES: %d\nROJAS: %d\n' "$ASER" "$ROJAS"
[ "$ROJAS" = "0" ] || exit 1

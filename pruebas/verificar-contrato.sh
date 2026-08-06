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

# --- 4 · CLAUDE.md: el tope de 72 líneas -----------------------------------
#
# Lo decía la cabecera de `CLAUDE.md` desde el día cero —«`pruebas/verificar-
# contrato.sh` verifica el tope y que exista lo que se nombra acá»— y **no era
# cierto**: este arnés miraba el seguimiento y nada más. Un archivo que se
# atribuye una compuerta que no existe es peor que uno sin compuerta, porque el
# que lo lee deja de mirar. Encontrado el 2026-08-06 al reconciliar.
CL="CLAUDE.md"
if [ ! -f "$CL" ]; then
  roja "no existe $CL"
else
  ok
  lineas="$(wc -l < "$CL" | tr -d ' ')"
  if [ "$lineas" -le 72 ]; then ok; else
    roja "$CL tiene $lineas líneas y el tope duro es 72 — si algo entra, algo sale"
  fi

  # --- 5 · y que exista todo lo que nombra ---------------------------------
  #
  # Se sacan los nombres de archivo entre backticks. Lo que se saltea, y por
  # qué —la lista es corta a propósito: cada excepción es un lugar donde una
  # ruta rota se puede esconder—:
  #
  #   · `ERP360-Template/…`  vive en el repo de al lado, no en éste;
  #   · `panel/…`, `agente.py`, `ops/60-roles.md`  son de los proyectos
  #     VIGILADOS. CLAUDE.md los nombra para decir que capataz los lee y no los
  #     escribe, y capataz no tiene ninguno de los tres.
  #
  # Cualquier otra ruta nombrada tiene que existir acá. Con esto, `BITACORA.md`
  # —que CLAUDE.md nombraba desde el día cero y no existía— se ve en rojo.
  nombrados="$(grep -oE '`[A-Za-z0-9_./-]+\.(md|sh|py|html|json|txt|js|yml)`' "$CL" \
               | tr -d '`' | sort -u)"
  mirados=0
  for ruta in $nombrados; do
    case "$ruta" in
      ERP360-Template/*|panel/*|agente.py|panel.py|ops/60-roles.md) continue ;;
    esac
    mirados=$((mirados+1))
    if [ -e "$ruta" ]; then ok; else
      roja "$CL nombra \`$ruta\` y no existe"
    fi
  done
  # Cero rutas miradas es falla: querría decir que el `grep` de arriba dejó de
  # encontrar lo que mira y este bloque estaría salteando en silencio.
  if [ "$mirados" -ge 8 ]; then ok; else
    roja "sólo encontré $mirados rutas en $CL — esperaba al menos 8; el grep dejó de ver"
  fi
fi

printf '\nASERCIONES: %d\nROJAS: %d\n' "$ASER" "$ROJAS"
[ "$ROJAS" = "0" ] || exit 1

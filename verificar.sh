#!/usr/bin/env bash
# Corre todos los arneses y da el total.
#
#     ./verificar.sh            todos
#     ./verificar.sh lector     sólo los que matcheen «lector»
#
# **El total importa tanto como el color.** Si un arnés deja de encontrar lo que
# mira no siempre se pone rojo —a veces saltea en silencio— y lo único que
# cambia es la cuenta. Por eso se imprime y por eso cero aserciones es falla.

set -uo pipefail
cd "$(dirname "$0")"

filtro="${1:-}"
verdes=0; rojas=0; fallaron=""

correr() {
  local f="$1" cmd="$2"
  [ -n "$filtro" ] && [[ "$f" != *"$filtro"* ]] && return 0
  local salida v r
  salida="$($cmd "pruebas/$f" 2>&1)" || true
  v=$(printf '%s' "$salida" | grep -oE 'ASERCIONES: *[0-9]+' | tail -1 | grep -oE '[0-9]+' || echo 0)
  r=$(printf '%s' "$salida" | grep -oE 'ROJAS: *[0-9]+'      | tail -1 | grep -oE '[0-9]+' || echo 0)
  verdes=$((verdes + v)); rojas=$((rojas + r))
  if [ "$r" != "0" ] || [ "$v" = "0" ]; then
    fallaron="$fallaron $f"
    printf '  \033[31m✗\033[0m %-30s %4s aserciones  %s rojas\n' "$f" "$v" "$r"
    printf '%s\n' "$salida" | grep -E 'ROJA|Error|Traceback' | head -10 | sed 's/^/        /'
  else
    printf '  \033[32m✓\033[0m %-30s %4s\n' "$f" "$v"
  fi
}

echo
# `verificar-nube.py` sale a **github.com de verdad** y clona los repositorios
# vigilados. Es el único que necesita red, y es el que vale de la tanda del
# 2026-08-06: un lector de red probado sólo contra respuestas grabadas pasa
# entero con la red rota. Si no hay salida, se pone rojo — no saltea.
for f in verificar-lector.py verificar-nube.py verificar-angosto.py \
         verificar-credenciales.py; do
  [ -f "pruebas/$f" ] && correr "$f" python3; done
for f in verificar-contrato.sh; do
  correr "$f" bash; done

# El arnés de la pantalla corre el JavaScript de `capataz.html` de verdad, así
# que necesita node. **Si node no está, esto es una falla y no un salteo**: un
# arnés que no corre no verifica nada, y la forma en que eso se nota es que el
# total baja. El aviso dice qué instalar para que no haya que leer el script.
if [ -z "$filtro" ] || [[ "verificar-pantalla.js" == *"$filtro"* ]]; then
  if command -v node >/dev/null 2>&1; then
    correr "verificar-pantalla.js" node
  else
    fallaron="$fallaron verificar-pantalla.js"
    printf '  \033[31m✗\033[0m %-30s %4s aserciones  %s\n' \
      "verificar-pantalla.js" "0" "no hay node"
    printf '        node no está instalado: el JavaScript de capataz.html no se ejecuta,\n'
    printf '        y la regla 3 («no sé» nunca verde) queda sin verificar en la pantalla.\n'
  fi
fi

echo
if [ -n "$fallaron" ]; then
  printf '  \033[31m%s aserciones · %s rojas\033[0m —%s\n\n' "$verdes" "$rojas" "$fallaron"
  exit 1
fi

# El total **medido**, dejado donde otro lo pueda leer.
#
# Es la mitad que le faltaba a «el total de aserciones es parte del resultado»:
# hasta acá el total se imprimía y se perdía, así que comparar una rama con
# `main` obligaba a correr las dos suites, o a creerle a un número escrito a
# mano en una celda del seguimiento. Ahora queda versionado, y capataz lo lee
# con `git show <rama>:pruebas/total-aserciones.txt` sin correr nada de nadie.
#
# Sólo se escribe cuando está todo verde: un total al lado de una roja no es un
# total, es la mitad de uno. Y sólo si cambió, para no ensuciar el árbol.
if [ ! -f pruebas/total-aserciones.txt ] || \
   [ "$(cat pruebas/total-aserciones.txt 2>/dev/null)" != "$verdes" ]; then
  printf '%s\n' "$verdes" > pruebas/total-aserciones.txt
fi
printf '  \033[32m%s aserciones en verde\033[0m\n\n' "$verdes"

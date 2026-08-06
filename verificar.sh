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
for f in verificar-lector.py verificar-angosto.py; do
  [ -f "pruebas/$f" ] && correr "$f" python3; done
for f in verificar-contrato.sh; do
  correr "$f" bash; done

echo
if [ -n "$fallaron" ]; then
  printf '  \033[31m%s aserciones · %s rojas\033[0m —%s\n\n' "$verdes" "$rojas" "$fallaron"
  exit 1
fi
printf '  \033[32m%s aserciones en verde\033[0m\n\n' "$verdes"

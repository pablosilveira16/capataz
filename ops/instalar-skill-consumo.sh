#!/usr/bin/env bash
# Instala la skill `consumo-sesion` para TODAS las sesiones de esta máquina.
#
# Claude Code busca las skills personales en `~/.claude/skills/` (o en
# `$CLAUDE_CONFIG_DIR/skills/` si esa variable está puesta). Esto la engancha
# ahí con un **enlace simbólico** al repo, no con una copia: una copia sería
# el segundo lugar con el mismo dato que la regla 1 existe para prohibir —
# se pudre sola y nadie sabe cuál gana. Con el enlace, actualizar el repo
# actualiza la skill.
#
#     ./ops/instalar-skill-consumo.sh
#
# Correrlo dos veces no rompe nada. Si en el destino hay algo que NO es un
# enlace —una copia editada a mano, otra skill con el mismo nombre— se niega
# y lo dice: pisar lo de otro no es instalar.

set -euo pipefail

aqui="$(cd "$(dirname "$0")/.." && pwd)"
origen="$aqui/.claude/skills/consumo-sesion"
raiz="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
destino="$raiz/skills/consumo-sesion"

[ -f "$origen/SKILL.md" ] || {
  echo "no está la skill en $origen — ¿el repo está entero?" >&2
  exit 1
}

mkdir -p "$raiz/skills"

if [ -L "$destino" ]; then
  rm "$destino"                       # re-enlazar es idempotente
elif [ -e "$destino" ]; then
  echo "ya hay algo en $destino que no es un enlace: no lo piso." >&2
  echo "si querés reinstalar, movelo o borralo a mano y volvé a correr esto." >&2
  exit 1
fi

ln -s "$origen" "$destino"
echo "skill enganchada: $destino -> $origen"
echo "vale para toda sesión de esta máquina; se prueba con: python3 $destino/consumo.py"

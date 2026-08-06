#!/usr/bin/env bash
# Helper de credenciales de git para GitHub — el token vive AFUERA del repo
#
# Traído de `ops/credencial-github.sh` de ERP 360 (2026-08-05) y adaptado: acá
# el repositorio es `pablosilveira16/capataz` y el archivo del token se llama
# distinto, porque **un token, un repositorio**. Lo que no cambió es el motivo.
#
# git llama a este programa con una palabra —`get`, `store` o `erase`—, le pasa
# el pedido por stdin y le lee la respuesta por stdout. Ante `get` contestamos
# `username=` y `password=`. Nada más.
#
# Por qué existe, en una línea: **para que el token no esté escrito en ningún
# lado que git pueda commitear ni imprimir**. La alternativa obvia —el token
# adentro de la URL del remote— es exactamente la que no se puede: git escupe
# la URL entera en los mensajes de error, en `git remote -v` y en la salida de
# cualquier agente que corra `git push`.
#
#     ../.credenciales/github-capataz.token      una línea, chmod 600
#
# Afuera y no adentro por dos motivos que se sostienen solos: ningún commit
# puede llevárselo —no es que esté ignorado, es que no está en el árbol— y
# **cualquier agente que trabaje sobre esa carpeta lo ve**, que es lo que hace
# que tres agentes en paralelo no tengan que configurar nada.
#
# El runbook completo está en `ops/70-credenciales.md`. Se prueba así, y no
# imprime el token:
#
#   printf 'protocol=https\nhost=github.com\n\n' | ops/credencial-github.sh get

set -uo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# `CAPATAZ_TOKEN` existe para los arneses y para quien tenga la carpeta en otro
# lado. El valor por defecto es el que usa todo el mundo. La ruta se **calcula**
# y no se escribe: la misma carpeta está montada en dos rutas distintas.
ARCHIVO="${CAPATAZ_TOKEN:-$(dirname "$RAIZ")/.credenciales/github-capataz.token}"

USUARIO="${CAPATAZ_GITHUB_USUARIO:-pablosilveira16}"

ayuda() {
  cat >&2 <<FIN

  No hay credencial de GitHub para empujar.

  Falta el archivo:   $ARCHIVO

  Qué hacer —son tres pasos y los da entero \`ops/70-credenciales.md\`—:

    1. Pablo crea un token *fine-grained* en GitHub, con alcance **sólo** el
       repositorio pablosilveira16/capataz y los permisos mínimos:
         Contents: Read and write
         Metadata: Read-only
         Workflows: Read and write   ← el que a ERP 360 le faltó y rechazó
                                       el push entero. Va desde el principio.
    2. Lo guarda, en una sola línea y sin comillas, en ese archivo:
         mkdir -p "$(dirname "$ARCHIVO")"
         printf '%s\\n' 'github_pat_…' > "$ARCHIVO"
         chmod 600 "$ARCHIVO"
    3. El agente vuelve a correr \`ops/empujar.sh\`.

  Mientras tanto la entrega es por parche:
    git format-patch main --stdout > tanda-N.patch

FIN
}

op="${1:-}"
case "$op" in
  get) ;;
  # No guardamos ni borramos nada: el archivo lo escribe una persona y sólo una
  # persona lo revoca. Un helper que «recuerda» credenciales termina dejando
  # copias del token en lugares que nadie audita.
  store|erase) exit 0 ;;
  *)
    echo "uso: $(basename "$0") get|store|erase   (helper de credenciales de git)" >&2
    exit 2
    ;;
esac

# El pedido de git: líneas `clave=valor` hasta una vacía. Hay que leerlo entero
# —si no, git escribe en un pipe cerrado— y además sirve para lo de abajo.
protocolo=""; host=""
while IFS= read -r linea; do
  [ -z "$linea" ] && break
  case "$linea" in
    protocol=*) protocolo="${linea#protocol=}" ;;
    host=*)     host="${linea#host=}" ;;
  esac
done

# Un helper que contesta a cualquier host le entrega el token al primer remote
# que alguien agregue por error. Silencio y salida limpia.
case "$host" in
  github.com|www.github.com) ;;
  *) exit 0 ;;
esac

if [ ! -f "$ARCHIVO" ]; then
  ayuda
  exit 1
fi

# Sólo un aviso: el push tiene que salir igual. Un permiso flojo es un problema
# de la máquina, no del push, y frenar acá haría que el aviso no se lea.
# El GNU primero y el BSD después, y no al revés: en Linux `stat -f` existe,
# significa otra cosa y **sale con éxito**, así que el `||` nunca caía al
# segundo. Es un bug que ERP 360 ya encontró y arregló; se trae arreglado.
permisos="$(stat -c '%a' "$ARCHIVO" 2>/dev/null || stat -f '%Lp' "$ARCHIVO" 2>/dev/null || echo '')"
case "$permisos" in
  600|400|"") ;;
  *) echo "  aviso: $ARCHIVO tiene permisos $permisos — debería ser 600 (chmod 600)" >&2 ;;
esac

# La primera línea que no esté vacía ni sea un comentario. Sin `echo` del
# contenido en ningún momento: lo único que sale por stdout es el protocolo.
token="$(tr -d '\r' < "$ARCHIVO" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//' \
         | grep -v '^#' | awk 'NF {print; exit}')"

if [ -z "$token" ]; then
  echo "  El archivo del token está vacío: $ARCHIVO" >&2
  echo "  Tiene que tener el PAT en una sola línea. Ver ops/70-credenciales.md" >&2
  exit 1
fi

printf 'protocol=%s\n' "${protocolo:-https}"
printf 'host=%s\n' "$host"
printf 'username=%s\n' "$USUARIO"
printf 'password=%s\n' "$token"

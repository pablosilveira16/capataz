#!/usr/bin/env bash
# Publicar en GitHub — lo que corre un agente cuando terminó
#
#     ops/empujar.sh            empuja la rama de trabajo
#     ops/empujar.sh --tomar    empuja SÓLO el commit del «en curso» a main
#
# Traído de `ops/empujar.sh` de ERP 360 (2026-08-06) y adaptado: acá el
# repositorio es `pablosilveira16/capataz`, el token se llama distinto —**un
# token, un repositorio**— y la alternativa sin token se explica en
# `ops/70-credenciales.md` en vez de en un `DIRECTRICES.md` que este proyecto no
# tiene. Lo que no cambió es todo lo demás, y el motivo está abajo.
#
# El `--tomar` es el arbitraje de la forma «punto»: el agente marca un punto
# `en curso (rol-N)` en `SEGUIMIENTO.md`, commitea esa línea sola y la empuja a
# `main`. Si el push entra, el punto es suyo. Por eso el modo existe aparte: si
# esa línea viaja mezclada con código, no arbitra nada.
#
# **Si git lo rechaza, «otro llegó primero» es sólo UNA de tres causas**, y las
# tres dan el mismo no-fast-forward: que otro haya tomado ESTE punto, que main
# haya avanzado por otra cosa —y entonces tu trabajo vale y hay que reintentar—,
# o que las historias no estén relacionadas, que no es arbitraje sino un repo mal
# enganchado. El script las distingue y dice cuál es.
#
# Tres cosas que este script hace y que a mano se olvidan:
#
# 1. **`GIT_TERMINAL_PROMPT=0`.** Un agente desatendido colgado en un prompt de
#    usuario es peor que uno que falla: el que falla deja un mensaje.
# 2. **La compuerta.** `./verificar.sh` entero en verde antes de empujar nada.
#    Está en `CLAUDE.md` y acá está en código, que es lo único que la hace pasar
#    siempre.
# 3. **El token no aparece nunca.** Ni en la URL del remote —git filtra la URL
#    en los mensajes de error—, ni en la salida. Va por
#    `ops/credencial-github.sh`, que lo lee de afuera del repo.
#
# Cómo se consigue el token, y qué hacer mientras no haya: `ops/70-credenciales.md`.

set -uo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RAIZ" || exit 1

REMOTO="https://github.com/pablosilveira16/capataz.git"
HELPER="$RAIZ/ops/credencial-github.sh"
ARCHIVO_TOKEN="${CAPATAZ_TOKEN:-$(dirname "$RAIZ")/.credenciales/github-capataz.token}"

# Todo por stdout, incluidas las rojas. No es descuido: la salida de este script
# es un informe que se lee en orden, y con las rojas en stderr el mensaje de
# error aparecía DESPUÉS de su propia explicación cada vez que alguien capturaba
# la salida. Lo que dice que falló es el código de salida, no el canal.
rojo()  { printf '\033[31m  ✗ %s\033[0m\n' "$1"; }
verde() { printf '\033[32m  ✓ %s\033[0m\n' "$1"; }
info()  { printf '    %s\n' "$1"; }

# Red de seguridad: `verificar.sh` corre `pruebas/verificar-credenciales.py`, y
# ese arnés ejecuta este script para comprobar que la compuerta existe. Sin este
# corte, el día que alguien invierta el orden de los chequeos se arma un bucle.
if [ "${CAPATAZ_EMPUJANDO:-}" = "1" ]; then
  rojo "empujar.sh no se llama a sí mismo (CAPATAZ_EMPUJANDO=1)"
  exit 3
fi

modo="rama"
case "${1:-}" in
  "")        ;;
  --tomar)   modo="tomar" ;;
  -h|--ayuda|--help)
    sed -n '2,34p' "$0" | sed 's/^# \{0,1\}//'
    exit 0
    ;;
  *) rojo "modo desconocido: $1 — usá  ops/empujar.sh  o  ops/empujar.sh --tomar"; exit 2 ;;
esac

# Todo lo que sale por acá pasa por este filtro. El helper no imprime el token y
# la URL no lo lleva, así que esto no debería tener nada que tapar nunca — pero
# es la clase de cosa que se agradece el día que git cambie un mensaje.
sin_secretos() {
  sed -E 's/(gh[pousr]_|github_pat_)[A-Za-z0-9_]{8,}/\1«TOKEN OCULTO»/g'
}

echo

# ------------------------------------------------------------------
# 1 · El remote y el helper, configurados en este repo
# ------------------------------------------------------------------
#
# Antes que todo lo demás, incluido el chequeo de credencial, y a propósito:
# esto no necesita token y **deja el repo configurado igual cuando no hay**. Una
# copia recién clonada no tiene nada en `.git/config` —no se versiona—, así que
# si esto viviera más abajo, una copia sin token quedaría sin configurar y
# `pruebas/verificar-credenciales.py` se pondría rojo por algo que no es un bug.
if git remote get-url origin >/dev/null 2>&1; then
  url="$(git remote get-url origin)"
else
  git remote add origin "$REMOTO" || exit 1
  url="$REMOTO"
  info "remote origin agregado: $REMOTO"
fi
case "$url" in
  *@*)
    rojo "El remote origin lleva credenciales adentro de la URL: $(printf '%s' "$url" | sed 's/:.*@/:«…»@/')"
    info "git filtra la URL en los mensajes de error, así que eso publica el token."
    info "Arreglo:  git remote set-url origin $REMOTO"
    exit 1
    ;;
esac

# El `!` hace que git lo corra por shell. Eso da las dos cosas que hacen falta:
# que la ruta pueda tener espacios —«frutos de cuyo» los tiene— y que se pueda
# calcular en el momento con `git rev-parse`, en vez de quedar escrita.
#
# Escrita no serviría: **la misma carpeta está montada en dos rutas distintas**
# —`/Users/Acer/Documents/…` en la Mac y `/sessions/…/mnt/…` en el contenedor— y
# `.git/config` es un solo archivo compartido por las dos. Una ruta absoluta
# dejaría andando a uno y roto al otro, según quién corrió esto último.
git config --local "credential.https://github.com.helper" \
  '!"$(git rev-parse --show-toplevel)"/ops/credencial-github.sh' || exit 1
git config --local credential.https://github.com.username \
  "${CAPATAZ_GITHUB_USUARIO:-pablosilveira16}" >/dev/null 2>&1

export GIT_TERMINAL_PROMPT=0     # nunca colgado esperando a una persona
unset GIT_ASKPASS SSH_ASKPASS    # ni preguntando por una ventana que no hay

# ------------------------------------------------------------------
# 2 · Hay credencial
# ------------------------------------------------------------------
#
# Va antes de la compuerta, y son dos motivos. Uno práctico: descubrir que falta
# el token después de correr todos los arneses es tiempo tirado. El otro manda:
# `pruebas/verificar-credenciales.py` **ejecuta este script** sin credencial para
# comprobar que la compuerta existe, y si la compuerta corriera antes, ese arnés
# dispararía `verificar.sh` en cascada. El orden está verificado allá.
if [ ! -x "$HELPER" ]; then
  rojo "falta $HELPER o no es ejecutable (chmod +x)"
  exit 1
fi
if [ ! -f "$ARCHIVO_TOKEN" ]; then
  rojo "No hay credencial de GitHub: falta $ARCHIVO_TOKEN"
  info "El runbook con los tres pasos —crear el token, guardarlo, chmod 600— es"
  info "ops/70-credenciales.md. Mientras tanto la entrega es por parche:"
  info "  git format-patch main --stdout > tanda-N.patch"
  exit 1
fi
verde "credencial presente (no se imprime)"

# ------------------------------------------------------------------
# 3 · El árbol está limpio
# ------------------------------------------------------------------
sucio="$(git status --porcelain 2>/dev/null)"
if [ -n "$sucio" ]; then
  rojo "El árbol está sucio: hay cambios sin commitear."
  printf '%s\n' "$sucio" | sed 's/^/      /' | head -20
  info "Commiteá o descartá antes de empujar. Lo que se empuja es lo que está commiteado,"
  info "y un push con el árbol sucio publica una foto que en tu carpeta no existe."
  exit 1
fi
verde "árbol limpio"

# ------------------------------------------------------------------
# 4 · Los .sh viajan con el bit de ejecución
# ------------------------------------------------------------------
#
# Se mira **el índice** y no el disco: `git ls-files -s` dice con qué modo va a
# viajar el archivo, que es lo único que no depende de en qué máquina se corra.
# La copia de la Mac está sobre una carpeta montada, y una copia con
# `core.filemode = false` ignora el modo — así que un `chmod +x` de ese lado no
# llega nunca al índice, y el que clona (o el CI) recibe un script que no se
# puede correr.
#
# Esto es la factura de ERP 360 traída ya pagada: sus `.sh` viajaron sin el bit
# y `run: ./verificar.sh` falló con «Permission denied» en TODAS las ramas
# empujadas durante un día, sin que nadie lo viera — porque desde el contenedor
# el resultado del CI no se puede leer.
sin_bit="$(git ls-files -s -- '*.sh' | awk '$1 !~ /^100755$/ {print $4}')"
if [ -n "$sin_bit" ]; then
  rojo "Hay .sh versionados sin el bit de ejecución en el ÍNDICE:"
  printf '%s\n' "$sin_bit" | sed 's/^/      /'
  info "Así viajan al CI y a cualquier clon, y ahí «./x.sh» es «Permission denied»."
  info "Arreglo:  git update-index --chmod=+x <archivo>   y commiteá."
  exit 1
fi
verde "todos los .sh versionados viajan ejecutables"

# ------------------------------------------------------------------
# 5 · La compuerta: ./verificar.sh entero en verde
# ------------------------------------------------------------------
info "corriendo ./verificar.sh …"
salida_v="$(CAPATAZ_EMPUJANDO=1 ./verificar.sh 2>&1)"
estado_v=$?
total="$(printf '%s' "$salida_v" | grep -oE '[0-9]+ aserciones' | tail -1)"
if [ "$estado_v" != "0" ]; then
  rojo "verificar.sh NO está en verde: no se empuja."
  printf '%s\n' "$salida_v" | tail -15 | sed 's/^/      /'
  info "Un agente que empuja algo rojo le pasa el problema al siguiente. Escribí en"
  info "SEGUIMIENTO.md qué se rompió, con el arnés y el mensaje, y devolvé el punto"
  info "a pendiente."
  exit 1
fi
verde "verificar.sh en verde — ${total:-sin total}"

rama="$(git rev-parse --abbrev-ref HEAD)"

# ------------------------------------------------------------------
# 6 · Empujar
# ------------------------------------------------------------------
# Empuja una sola vez y deja lo que dijo git en SALIDA_PUSH. Una sola vez no es
# un detalle de prolijidad: el segundo intento de un push rechazado devuelve un
# mensaje distinto —«everything up-to-date» o el mismo rechazo— y el diagnóstico
# se arma con el primero.
SALIDA_PUSH=""
empujar() {   # $1 refspec
  SALIDA_PUSH="$(git push origin "$1" 2>&1 | sin_secretos)"
  local estado=$?
  printf '%s\n' "$SALIDA_PUSH" | sed 's/^/      /'
  return "$estado"
}

if [ "$modo" = "tomar" ]; then
  # Lo que hace que esto arbitre es que viaje SOLO. Un commit que además trae
  # código no es una reserva de punto: es una rama disfrazada, y el que pierde
  # la carrera pierde también el trabajo.
  tocados="$(git diff --name-only HEAD~1 HEAD 2>/dev/null)"
  if [ "$tocados" != "SEGUIMIENTO.md" ]; then
    rojo "El último commit no es una toma de punto: toca $(printf '%s' "$tocados" | tr '\n' ' ')"
    info "--tomar empuja SÓLO el cambio del «en curso» a main. Un commit de una línea"
    info "sobre SEGUIMIENTO.md y nada más. El código va en su rama, sin --tomar."
    exit 1
  fi
  # La línea de la marca se guarda, no sólo se comprueba: de ahí salen el
  # identificador del punto y el nombre del que lo toma, y los dos hacen falta
  # después para diagnosticar un rechazo.
  LINEA_MARCA="$(git diff HEAD~1 HEAD -- SEGUIMIENTO.md | grep -E '^\+.*en curso' | head -1)"
  if [ -z "$LINEA_MARCA" ]; then
    rojo "El último commit toca SEGUIMIENTO.md pero no marca ningún punto «en curso»."
    info "La marca lleva quién lo toma: «en curso (coder-2)»."
    exit 1
  fi
  # `| T7 | **…** | 2026-08-06 | en curso (coder-2) |` → `T7`
  PUNTO="$(printf '%s' "$LINEA_MARCA" | sed -nE 's/^\+\|[[:space:]]*([A-Za-z]+[0-9]+)[[:space:]]*\|.*/\1/p')"
  DUENIO="$(printf '%s' "$LINEA_MARCA" | sed -nE 's/.*en curso[[:space:]]*\(([^)]*)\).*/\1/p')"

  # ------------------------------------------------------------------
  # El diagnóstico de un rechazo, que es la mitad del mecanismo
  # ------------------------------------------------------------------
  #
  # **Tres causas distintas producen exactamente el mismo rechazo de git** —el
  # no-fast-forward— y el remedio de cada una es diferente:
  #
  #   | Causa                      | Qué pasó                      | Remedio                    |
  #   |----------------------------|-------------------------------|----------------------------|
  #   | Otro agente tomó el punto  | main avanzó y toca ESTE punto | pull y otro punto          |
  #   | main avanzó por otra cosa  | alguien cerró un punto distinto | pull --rebase y reintentar |
  #   | Historias no relacionadas  | no hay antepasado común       | frenar: el repo está mal enganchado |
  #
  # Lo primero lo descubrió ERP 360 a la mala: su primer `--tomar` de verdad fue
  # rechazado por la tercera causa —`origin/main` era el «Initial commit» que
  # crea GitHub—, no había ningún otro agente, y el script afirmó lo contrario
  # con total seguridad. Un agente desatendido hace lo que el mensaje le dice:
  # por eso un mensaje de arbitraje equivocado es peor que ninguno.
  diagnosticar_rechazo() {
    # Sin el fetch, `origin/main` es la foto de la última vez que alguien miró y
    # todo lo que sigue diagnostica un pasado. Y si el fetch tampoco sale, se
    # dice: un diagnóstico que no pudo mirar nada es la clase de mentira que
    # este bloque existe para no volver a decir.
    if ! git fetch --quiet origin main >/dev/null 2>&1; then
      rojo "El push a main fue rechazado y NO PUDE AVERIGUAR POR QUÉ."
      info "«git fetch origin main» tampoco salió, así que no hay con qué comparar."
      info "Puede ser la red, o el token. No des por sentado que alguien te ganó el punto:"
      info "arreglá el fetch primero y volvé a correr esto — tu trabajo sigue estando."
      return 1
    fi
    local remoto base fila estado duenio_remoto
    remoto="$(git rev-parse FETCH_HEAD 2>/dev/null)"

    # --- Causa 3: no hay antepasado común -----------------------------
    base="$(git merge-base HEAD "$remoto" 2>/dev/null)"
    if [ -z "$base" ]; then
      rojo "HISTORIAS NO RELACIONADAS — esto NO es arbitraje."
      info "«git merge-base HEAD origin/main» no devuelve nada: tu historia y la del"
      info "main remoto no comparten ni un commit. Ningún push puede fast-forwardear,"
      info "no hay ningún otro agente, y tu trabajo no tiene nada de malo."
      info ""
      info "FRENÁ Y DECILO. No es tuyo para arreglar:"
      info "  · no elijas otro punto — con este repo va a fallar igual"
      info "  · «git pull --rebase origin main» FALLA acá, no lo intentes"
      info "  · «--force» sobre main es destructivo y no lo decide un agente"
      info ""
      info "El caso conocido es un repo recién creado en GitHub con README: ese"
      info "«Initial commit» es una historia propia. → BITACORA.md."
      return 1
    fi

    # --- Causa 1 vs 2: ¿este punto ya está tomado allá? ---------------
    #
    # Lo que separa la primera de la segunda **no es que main se haya movido**
    # —se movió en las dos—: es si el punto que estás tomando ya está tomado en
    # el `SEGUIMIENTO.md` del main remoto. Por eso hace falta el identificador,
    # y por eso esto lee el archivo del remoto en vez de mirar sólo los sha.
    if [ -n "$PUNTO" ]; then
      fila="$(git show "$remoto:SEGUIMIENTO.md" 2>/dev/null \
              | grep -E "^\|[[:space:]]*$PUNTO[[:space:]]*\|" | head -1)"
    fi
    estado="$(printf '%s' "${fila:-}" | awk -F'|' 'NF>2 {print $(NF-1)}')"

    case "$estado" in
      *"en curso"*)
        duenio_remoto="$(printf '%s' "$estado" | sed -nE 's/.*en curso[[:space:]]*\(([^)]*)\).*/\1/p')"
        # Que el de allá seas vos no es «otro agente»: es tu propia toma, que ya
        # entró. Mandarte a elegir otro punto ahí sería tirar el trabajo por el
        # que ya ganaste el arbitraje.
        if [ -n "$DUENIO" ] && [ "$duenio_remoto" = "$DUENIO" ]; then
          rojo "TU PROPIA TOMA DE $PUNTO YA ESTÁ EN MAIN."
          info "El main remoto marca «$PUNTO … en curso ($duenio_remoto)», que sos vos."
          info "El punto es tuyo y no hay nada que volver a empujar. Poné al día tu copia:"
          info "  git pull --rebase origin main"
          return 1
        fi
        rojo "OTRO AGENTE TOMÓ EL PUNTO PRIMERO: $PUNTO${duenio_remoto:+ lo tiene $duenio_remoto}."
        info "El main remoto ya marca ese punto «en curso», así que el arbitraje lo ganó"
        info "otro. No es un error a reintentar: reintentar no te lo devuelve."
        info ""
        info "Qué hacer, en este orden:"
        info "  1. git pull --rebase origin main"
        info "  2. mirá SEGUIMIENTO.md: el punto está «en curso (${duenio_remoto:-otro-rol-N})»"
        info "  3. ELEGÍ OTRO PUNTO y volvé a empezar"
        info ""
        info "Lo que NO se hace: --force. El punto es del que llegó primero; forzar"
        info "borra su marca y los dos terminan trabajando sobre lo mismo."
        return 1
        ;;
    esac

    # --- Causa 2: main avanzó, pero por otra cosa ---------------------
    rojo "MAIN AVANZÓ POR OTRA COSA — tu trabajo sigue siendo válido."
    if [ -n "$fila" ]; then
      info "En el main remoto, $PUNTO sigue sin estar «en curso»:"
      info "  $(printf '%s' "$estado" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')"
    elif [ -n "$PUNTO" ]; then
      info "En el main remoto no hay ninguna fila para $PUNTO — así que nadie lo tomó."
    else
      info "No pude leer el identificador del punto de tu commit, pero el main remoto"
      info "no tiene ninguna marca que choque con la tuya."
    fi
    info "Alguien empujó otro punto y por eso el fast-forward no entró. Nadie te ganó"
    info "nada y NO hay que elegir otro punto."
    info ""
    info "Qué hacer, en este orden:"
    info "  1. git pull --rebase origin main"
    info "  2. ops/empujar.sh --tomar          ← el mismo commit, otra vez"
    return 1
  }

  info "empujando la toma del punto a main …"
  if empujar "HEAD:main"; then
    echo; verde "El punto es tuyo: la toma de ${PUNTO:-el punto} entró en main."
    info "Si no lo terminás, devolvelo a «pendiente» y empujá eso también:"
    info "un «en curso» huérfano es un punto que nadie va a tocar."
    echo; exit 0
  fi

  echo
  if printf '%s' "$SALIDA_PUSH" | grep -qiE 'non-fast-forward|fetch first|rejected.*behind|failed to push some refs'; then
    diagnosticar_rechazo
  else
    rojo "El push a main falló, y no fue por no-fast-forward."
    info "Si dice «could not read Username» o «Authentication failed», el token no sirve"
    info "o le falta el permiso Contents: Read and write —y Workflows: Read and write si"
    info "el commit toca .github/workflows/. → ops/70-credenciales.md"
  fi
  echo; exit 1
fi

# --- modo por defecto: la rama de trabajo --------------------------
if [ "$rama" = "main" ]; then
  rojo "Estás en main y este modo empuja la rama de trabajo."
  info "Un agente, un punto, una rama:"
  info "  git switch -c <tema>     y volvé a correr esto"
  info "Si lo que querés es reservar un punto, el modo es:  ops/empujar.sh --tomar"
  exit 1
fi

info "empujando la rama «$rama» …"
if empujar "$rama:$rama"; then
  git branch --set-upstream-to="origin/$rama" "$rama" >/dev/null 2>&1
  echo; verde "Rama «$rama» publicada — ${total:-sin total}"
  info "Ahora: el CI en verde antes del merge, y el punto a «hecho» con el arnés"
  info "y el número de aserciones al lado. Un «hecho» sin prueba al lado es una opinión."
  echo; exit 0
fi
echo
rojo "No se pudo empujar la rama «$rama»."
# El mismo error de diagnóstico que tenía el --tomar, en chiquito: acá la causa
# es una sola y no tres —alguien empujó a TU rama— pero decirla es igual de barato.
if printf '%s' "$SALIDA_PUSH" | grep -qiE 'non-fast-forward|fetch first|rejected.*behind'; then
  info "Fue un rechazo por no-fast-forward: «origin/$rama» tiene commits que vos no"
  info "tenés. No es el token —el token autenticó bien— y no es arbitraje: acá la"
  info "rama es tuya. Alguien más empujó a ella, o tu copia quedó vieja."
  info "  git pull --rebase origin $rama    y volvé a correr esto"
else
  info "Si dice «could not read Username» o «Authentication failed», el token no sirve"
  info "o le falta el permiso Contents: Read and write —y Workflows: Read and write si"
  info "el commit toca .github/workflows/. → ops/70-credenciales.md"
fi
echo
exit 1

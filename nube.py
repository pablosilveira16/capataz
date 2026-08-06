#!/usr/bin/env python3
"""Lo que capataz lee **de GitHub**, y no de la carpeta de nadie.

## Por qué la nube y no el disco

Hasta el 2026-08-06 capataz leía carpetas locales. Está mal por tres motivos, y
el tercero ya pasó dos veces:

1. **Un agente puede correr en cualquier lado** —la Mac, un contenedor, otra
   máquina— y su trabajo se hace visible cuando **empuja**. La carpeta local no
   lo ve; el remoto sí.
2. **`git push` ya es el árbitro** (`ops/50-formas-de-trabajo.md` de ERP 360).
   Si el remoto decide quién tiene qué punto, el remoto **es** la fuente de
   verdad y mirar una copia local es mirar el reflejo.
3. `ERP360-Template/` desapareció de la máquina de Pablo y capataz se quedó
   ciego mientras el repositorio en GitHub estaba entero (punto D5). Y mientras
   se escribía este archivo volvió a pasar, con la carpeta de capataz.

## Por camino `git`, y no por la API — la decisión de esta tanda

`api.github.com` está **fuera de la lista blanca** del contenedor de un agente:
devuelve `000`, medido otra vez el 2026-08-06 y no supuesto. `github.com` por
HTTPS **sí** anda. O sea que de los dos caminos posibles hay uno que un agente
puede probar contra la realidad y otro que no:

    (a) la API      cómoda, da hasta el CI, y desde acá **no se puede probar**;
    (b) git         da ramas, commits, autores y el contenido de cualquier
                    archivo de cualquier rama, y **se prueba contra los repos
                    de verdad, ahora**. No da el estado del CI.

Se eligió **(b) para todo lo que da**, y (a) queda **sólo para el CI**, que es
lo único que git no puede contestar —`pedir_ci()`, apagado por defecto y con su
límite escrito ahí mismo—. Un lector de red probado únicamente contra respuestas
grabadas puede pasar entero con la red rota: eso es el arnés vacuo de la regla 2
de `CLAUDE.md`, y es exactamente el riesgo que (b) evita.

## El espejo, y por qué no contradice «capataz sólo lee»

Para leer un blob de un repositorio remoto hay que traer los objetos a disco:
git no tiene forma de leer un archivo sin bajarlo (`git archive --remote`
contra GitHub responde «operation not supported by protocol»; está medido).
Así que capataz **sí escribe**, y hay que decir exactamente dónde y qué:

  · escribe **sólo** adentro de `ESPEJOS`, una carpeta temporal suya;
  · **nunca** corre git sobre el repositorio de nadie más — `_git()` rechaza
    cualquier comando cuyo destino no esté adentro del espejo, y ésa es una
    invariante más fuerte que la lista blanca de subcomandos que había antes;
  · lo que hay adentro es **derivado y descartable**: borrar la carpeta entera
    y volver a leer da exactamente lo mismo, sólo que más lento.
    → `pruebas/verificar-nube.py` § 5 lo borra y compara.

Un espejo no es un estado propio: no hay ningún dato que viva ahí y no viva en
GitHub. La regla 1 prohíbe que capataz sea **fuente de verdad**, no que use un
buffer de transporte.

Sin dependencias: sólo biblioteca estándar.
"""
import io
import json
import os
import re
import shlex
import subprocess
import tempfile
import time

AQUI = os.path.dirname(os.path.abspath(__file__))

# Dónde viven los espejos. En el temporal a propósito: lo que se pierde al
# reiniciar la máquina es una copia que se vuelve a bajar en un segundo.
ESPEJOS = (os.environ.get("CAPATAZ_ESPEJOS")
           or os.path.join(tempfile.gettempdir(), "capataz-espejos"))

# Cada cuánto se vuelve a preguntarle a GitHub, y **es el único reloj que hace
# que un agente se vea antes**: la pantalla puede repintar cada un segundo, pero
# lo que no se fue a buscar no está. Con 60 s un agente que empuja tardaba hasta
# un minuto en aparecer prendido, que es justo el momento que se quiere mirar.
#
# 15 s sale medido: un `git fetch` contra el espejo tarda 1,2 s por repositorio
# (2026-08-06, dos repositorios), así que son ~2,4 s de git cada 15 — el resto
# del tiempo el servidor no toca la red. Bajarlo más no es gratis y lo que se
# gana es medio segundo de aviso.
REFRESCO = int(os.environ.get("CAPATAZ_REFRESCO", 15))

# Cuántos commits de historia se bajan. Alcanza para «los commits recientes» y
# para que `rev-list --count` diga la verdad en ramas que se abrieron hace poco,
# que son las únicas que importan acá.
HONDURA = 200

# Un `git` que se cuelga deja la pantalla colgada. Se corta y se dice por qué.
ESPERA = 45

# El usuario con el que se autentica. El token es de él; el helper lo lee.
USUARIO = os.environ.get("CAPATAZ_GITHUB_USUARIO", "pablosilveira16")

TOKEN_POR_DEFECTO = "github-capataz.token"

# `owner/repo`, tal como GitHub los acepta. Sin `.git`, sin URL, sin ruta: si
# alguien escribe `../Finca360` acá, tiene que verse el error con lo que buscó
# y no una tarjeta vacía.
_REPO = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*/[A-Za-z0-9][A-Za-z0-9._-]*$")

# Cualquier cosa con forma de credencial que se cuele en un mensaje de error de
# git. Un tablero que imprime el token en pantalla lo filtra a la primera
# captura. → `pruebas/verificar-nube.py` § 4
_CREDENCIAL = re.compile(r"(gh[pousr]_[A-Za-z0-9]{10,}|github_pat_[A-Za-z0-9_]{10,})")

MOTIVO_CI = (
    "api.github.com está fuera de la lista blanca del contenedor de un agente "
    "—medido el 2026-08-06: devuelve 000— y gh no está instalado. Desde acá el "
    "CI no se lee; hay que abrirlo en la web, o correr capataz en la Mac con "
    "CAPATAZ_CI=1."
)

MOTIVO_CI_APAGADO = (
    "la lectura del CI está apagada. Va detrás de CAPATAZ_CI=1 a propósito: "
    "donde api.github.com no se alcanza, encenderla sólo agrega espera por "
    "proyecto para terminar en el mismo «no sé»."
)

MOTIVO_TOTAL = (
    "el proyecto no dejó el total medido en pruebas/total-aserciones.txt. "
    "Un total declarado en prosa no es un total medido."
)

# Sólo estos tres salen a la red, y sólo hacia adentro del espejo.
GIT_RED = frozenset(("clone", "fetch", "ls-remote"))

# Y estos leen el espejo ya bajado. No hay un tercer grupo: `checkout`,
# `commit`, `push` y `gc` no están en ninguno y `_git` los rechaza.
GIT_LECTURA = frozenset((
    "rev-parse", "for-each-ref", "rev-list", "show", "log", "cat-file",
    "ls-tree", "count-objects",
))


class FueraDelEspejo(RuntimeError):
    """Se intentó correr git sobre algo que no es un espejo de capataz.

    Es la regla 1 de `CLAUDE.md` puesta donde se hace cumplir: capataz no toca
    el repositorio de nadie. Ni para leer — para leer está el espejo.
    """


def limpiar_secreto(texto):
    """Un mensaje de error sin nada que tenga forma de token."""
    return _CREDENCIAL.sub("«token»", texto or "")


def url_de(repo):
    return "https://github.com/%s" % repo


def carpeta_de(repo, base=None):
    """Dónde vive el espejo de ese repositorio. Un nombre plano, sin `/`."""
    return os.path.join(base or ESPEJOS, repo.replace("/", "__") + ".git")


def _dentro(ruta, base):
    r = os.path.realpath(ruta)
    b = os.path.realpath(base)
    return r == b or r.startswith(b + os.sep)


def _entorno(archivo_token):
    e = dict(os.environ)
    # **Nunca preguntar.** Sin esto, un repositorio sin credencial deja a git
    # esperando un nombre de usuario que nadie va a escribir, y la pantalla se
    # cuelga en vez de decir «no pude».
    e["GIT_TERMINAL_PROMPT"] = "0"
    e["GIT_ASKPASS"] = "true"
    if archivo_token:
        e["CAPATAZ_TOKEN"] = archivo_token
    return e


def _git(destino, *args, **kw):
    """git, siempre contra un espejo de capataz y nunca contra otra cosa.

    Dos compuertas, y las dos hacen falta:

      · el subcomando tiene que estar en `GIT_RED` o en `GIT_LECTURA`;
      · el destino tiene que estar **adentro** de la carpeta de espejos.

    La segunda es la que vale. La primera se puede burlar con un subcomando
    nuevo que parezca inocente; la segunda dice que pase lo que pase, lo que se
    toque va a ser una copia descartable de capataz.
    """
    base = kw.pop("base", None) or ESPEJOS
    token = kw.pop("token", None)
    sub = args[0] if args else ""
    if sub not in GIT_RED and sub not in GIT_LECTURA:
        raise FueraDelEspejo(
            "«git %s» no está permitido. Capataz sólo lee (CLAUDE.md § 1). "
            "Los permitidos: %s" % (sub, ", ".join(sorted(GIT_RED | GIT_LECTURA))))
    if not _dentro(destino, base):
        raise FueraDelEspejo(
            "«git %s» apuntaba a %s, que está fuera de %s. Capataz no corre git "
            "sobre el repositorio de nadie: para eso está el espejo."
            % (sub, destino, base))
    helper = "!" + shlex.quote(os.path.join(AQUI, "ops", "credencial-github.sh"))
    cmd = ["git",
           "-c", "credential.https://github.com.helper=" + helper,
           "-c", "credential.https://github.com.username=" + USUARIO]
    if sub in GIT_LECTURA or sub == "fetch":
        cmd += ["-C", destino]
    cmd += list(args)
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           timeout=ESPERA, env=_entorno(token))
    except subprocess.TimeoutExpired:
        return None, "git %s tardó más de %d s y se cortó" % (sub, ESPERA)
    except OSError as e:
        return None, "no pude correr git: %s" % e
    salida = p.stdout.decode("utf-8", "replace")
    error = limpiar_secreto(p.stderr.decode("utf-8", "replace").strip())
    if p.returncode != 0:
        return None, error or ("git %s falló con código %d" % (sub, p.returncode))
    return salida.strip(), ""


def _explicar(error, repo, archivo_token):
    """Traducir el gruñido de git a algo que diga qué hacer.

    Un tablero que muestra «falló» no sirve; uno que muestra la causa **con el
    dato que buscó** —la URL, el archivo del token— es el que se puede arreglar
    sin abrir el código.
    """
    e = (error or "").lower()
    donde = "%s · token %s" % (url_de(repo), archivo_token or "(ninguno)")
    if "repository not found" in e or "not found" in e:
        return ("no existe github.com/%s, o el token no lo alcanza. GitHub "
                "contesta lo mismo en los dos casos, a propósito. Buscado en: %s"
                % (repo, donde))
    if "could not read username" in e or "authentication failed" in e or \
            "invalid username or password" in e:
        return ("GitHub pidió credencial y no hubo ninguna válida. %s. "
                "Ver ops/70-credenciales.md" % donde)
    if "could not resolve host" in e or "failed to connect" in e or \
            "connection" in e or "timed out" in e or "se cortó" in e:
        return ("no llegué a github.com. %s. Desde el contenedor de un agente "
                "github.com anda y api.github.com no; si esto falla, la salida "
                "de red se cerró entera. Detalle: %s" % (donde, error))
    return "%s. Buscado en: %s" % (error or "git falló sin decir por qué", donde)


# ----------------------------------------------------------------------------
# 1 · El espejo
# ----------------------------------------------------------------------------

def refrescar(repo, base=None, token=None, refresco=None, ahora=None):
    """Traer el espejo al día. Devuelve `(carpeta, error)`.

    La primera vez clona; después hace `fetch`, y sólo si pasó `REFRESCO`. Un
    espejo que no se pudo refrescar **no se descarta**: se sigue usando el que
    hay y el error viaja al lado del dato, porque «lo de hace dos minutos» es
    mucho mejor que «no sé» y peor que «lo de ahora» — las tres cosas hay que
    poder distinguirlas.
    """
    base = base or ESPEJOS
    ahora = time.time() if ahora is None else ahora
    refresco = REFRESCO if refresco is None else refresco
    destino = carpeta_de(repo, base)
    marca = os.path.join(destino, "FETCH_HEAD")
    if not os.path.isdir(os.path.join(destino, "objects")):
        if not os.path.isdir(base):
            os.makedirs(base)
        # **`--no-single-branch` no es opcional.** `--depth` lo implica al
        # revés: un clon superficial trae UNA sola rama si no se le dice que
        # no, y capataz se quedaba viendo `main` y nada más — o sea, ciego
        # justo para lo que motiva la tanda, que es ver las ramas de los
        # agentes. Medido: con `--mirror --depth 200` solo, el espejo de
        # erp360 traía 1 rama de las 3 que tiene.
        _, error = _git(destino, "clone", "--mirror", "--depth", str(HONDURA),
                        "--no-single-branch", "--quiet", url_de(repo), destino,
                        base=base, token=token)
        return destino, error
    # `git clone` no escribe `FETCH_HEAD`: sólo lo escribe el `fetch`. Sin este
    # segundo candidato, un espejo recién clonado se veía con edad infinita y
    # se refrescaba en **cada** pedido — cuatro por minuto por proyecto, para
    # traer lo que se acababa de traer.
    if not os.path.exists(marca):
        marca = destino
    edad = ahora - os.path.getmtime(marca)
    if edad < refresco:
        return destino, ""
    _, error = _git(destino, "fetch", "--prune", "--quiet",
                    "--depth", str(HONDURA), "origin",
                    base=base, token=token)
    return destino, error


def _traido_en(destino):
    """Cuándo se habló con GitHub por última vez. **No es lo mismo que leer.**

    `leido_en` dice cuándo capataz miró el espejo, y eso pasa en cada pedido de
    la pantalla: mostrarlo como frescura del dato daba «GitHub leído hace 1 s»
    para siempre, aunque el último `fetch` fuera de hace quince segundos. La
    marca de verdad la deja git: `FETCH_HEAD` la escribe cada `fetch`, y en un
    espejo recién clonado —donde todavía no hubo ninguno— vale la carpeta.

    Sin ninguna de las dos no se inventa una fecha: `None`, y la pantalla dice
    «no sé».
    """
    for marca in (os.path.join(destino, "FETCH_HEAD"), destino):
        try:
            return os.path.getmtime(marca)
        except OSError:
            pass
    return None


def _texto(destino, ref, archivo, base=None):
    if not archivo:
        return None
    salida, error = _git(destino, "show", "%s:%s" % (ref, archivo), base=base)
    return None if error else salida


def _total(destino, ref, archivo, base=None):
    """El total de aserciones que esa rama dejó **medido**.

    Si el archivo no está, `None` — y la pantalla dice «no sé». Nunca se saca
    de la prosa del seguimiento: un número escrito a mano en una celda es lo
    que alguien recordó, no lo que la suite midió.
    """
    t = _texto(destino, ref, archivo, base)
    if t is None:
        return None
    m = re.search(r"\d+", t)
    return int(m.group(0)) if m else None


def _ramas(destino, principal, total_archivo, base=None):
    fmt = "%(refname:short)\t%(committerdate:unix)\t%(authorname)\t%(subject)"
    salida, error = _git(destino, "for-each-ref", "--format=" + fmt,
                         "refs/heads", base=base)
    if error:
        return [], error
    total_main = _total(destino, principal, total_archivo, base)
    ramas = []
    for linea in salida.splitlines():
        partes = linea.split("\t")
        if len(partes) < 4:
            continue
        nombre, cuando, autor, asunto = partes[0], partes[1], partes[2], partes[3]
        cuenta, err = _git(destino, "rev-list", "--left-right", "--count",
                           "%s...%s" % (principal, nombre), base=base)
        atras = adelante = None
        if not err and cuenta:
            nums = cuenta.split()
            if len(nums) == 2:
                atras, adelante = int(nums[0]), int(nums[1])
        sha, _ = _git(destino, "rev-parse", nombre, base=base)
        total = _total(destino, nombre, total_archivo, base)
        m = re.match(r"^([A-Za-z]{1,4})[-_]?(\d+)", nombre)
        try:
            ts = int(cuando)
        except ValueError:
            ts = None
        ramas.append({
            "nombre": nombre,
            "es_principal": nombre == principal,
            "punto": (m.group(1) + m.group(2)).upper() if m else "",
            "sha": (sha or "")[:7],
            "ts": ts,
            "autor": autor,
            "asunto": asunto[:160],
            "commits_adelante": adelante,
            "commits_atras": atras,
            "total": total,
            "total_main": total_main,
            "delta": (None if total is None or total_main is None
                      else total - total_main),
            "motivo_sin_total": "" if total is not None else MOTIVO_TOTAL,
        })
    ramas.sort(key=lambda r: (not r["es_principal"], -(r["ts"] or 0), r["nombre"]))
    return ramas, ""


def _commits(destino, cuantos=25, base=None):
    """Los commits recientes de **todas** las ramas, con su autor.

    De acá sale la cuadrilla real: los agentes commitean con su nombre de rol
    (`coder-1`, `escriba`…), así que quién empujó qué está en la historia y no
    en ningún archivo que haya que mantener al día.
    """
    salida, error = _git(destino, "log", "--all", "--no-merges",
                         "--format=%h\t%ct\t%an\t%s", "-n", str(cuantos),
                         base=base)
    if error:
        return [], error
    out = []
    for linea in salida.splitlines():
        p = linea.split("\t")
        if len(p) < 4:
            continue
        try:
            ts = int(p[1])
        except ValueError:
            continue
        out.append({"sha": p[0], "ts": ts, "autor": p[2], "asunto": p[3][:160]})
    return out, ""


# ----------------------------------------------------------------------------
# 2 · Un repositorio entero
# ----------------------------------------------------------------------------

def leer(proy, base=None, token_base=None, ahora=None, refresco=None):
    """Todo lo que capataz puede saber de un repositorio, leyendo de GitHub.

    Devuelve siempre un diccionario con la misma forma. **Nunca revienta y
    nunca devuelve vacío por error**: si algo no se pudo leer, `ok` es falso y
    `error` dice qué se buscó y dónde. Un tablero que muestra cero puntos
    porque no llegó a la red miente exactamente igual que uno que pinta verde
    lo que no sabe.
    """
    base = base or ESPEJOS
    ahora = time.time() if ahora is None else ahora
    repo = (proy.get("repo") or "").strip()
    vacio = {
        "repo": repo, "url": url_de(repo) if repo else "", "ok": False,
        "error": "", "leido_en": ahora, "espejo": "",
        "archivos": {}, "ramas": [], "commits": [],
    }
    if not repo:
        vacio["error"] = (proy.get("motivo_sin_repo")
                          or "este proyecto no declara «repo» en proyectos.json, "
                             "y capataz lee de GitHub: sin owner/repo no hay "
                             "nada que mirar")
        vacio["sin_repo"] = True
        return vacio
    if not _REPO.match(repo):
        vacio["error"] = ("«%s» no tiene forma owner/repo. Capataz lee de "
                          "GitHub: en proyectos.json va «pablosilveira16/erp360», "
                          "no una ruta ni una URL" % repo)
        return vacio

    archivo_token = _archivo_token(proy, token_base)
    destino, error = refrescar(repo, base=base, token=archivo_token,
                               refresco=refresco, ahora=ahora)
    vacio["espejo"] = destino
    hay_espejo = os.path.isdir(os.path.join(destino, "objects"))
    if error and not hay_espejo:
        vacio["error"] = _explicar(error, repo, archivo_token)
        return vacio

    principal = proy.get("rama_principal") or "main"
    ramas, err_ramas = _ramas(destino, principal,
                              proy.get("total_aserciones"), base=base)
    commits, _ = _commits(destino, base=base)
    archivos = {}
    for clave in ("seguimiento", "roles"):
        nombre = proy.get(clave)
        archivos[clave] = {"archivo": nombre,
                           "texto": _texto(destino, principal, nombre, base)}
    if err_ramas and not ramas:
        vacio["error"] = _explicar(err_ramas, repo, archivo_token)
        return vacio
    return {
        "repo": repo,
        "url": url_de(repo),
        "ok": True,
        # Un espejo viejo con un `fetch` fallado sigue sirviendo, y **dice que
        # está viejo**. Es la tercera opción entre «al día» y «no sé».
        "error": _explicar(error, repo, archivo_token) if error else "",
        "rancio": bool(error),
        "leido_en": ahora,
        "traido_en": _traido_en(destino),
        "espejo": destino,
        "principal": principal,
        "archivos": archivos,
        "ramas": ramas,
        "commits": commits,
    }


def _archivo_token(proy, token_base=None):
    """El archivo de credencial que le toca a este proyecto.

    **Un token, un repositorio** (`ops/70-credenciales.md`): por eso el nombre
    del archivo se declara por proyecto y no hay uno solo para todos.
    """
    nombre = proy.get("token") or TOKEN_POR_DEFECTO
    if os.path.isabs(nombre):
        return nombre
    base = token_base or os.environ.get("CAPATAZ_CREDENCIALES") \
        or os.path.join(os.path.dirname(AQUI), ".credenciales")
    return os.path.join(base, nombre)


# ----------------------------------------------------------------------------
# 3 · El CI — el único dato por el que hay que ir a la API
# ----------------------------------------------------------------------------
#
# **Esto es el camino (a), y desde el contenedor de un agente no se puede
# probar contra la realidad.** Lo que sí se prueba, y se prueba de verdad:
#
#   · que armado el pedido salga la URL y las cabeceras que la API documenta
#     → contra una respuesta **grabada a mano** (`pruebas/grabado/`), y el
#       arnés dice en su cara que es grabada;
#   · que **desde acá falle**, y que el resultado de fallar sea «no sé» con el
#     motivo escrito → eso se ejecuta contra `api.github.com` de verdad, y es
#     la única parte honesta que este contenedor puede afirmar.
#
# Falta verificarlo contra la API real desde la Mac: es el punto T11.

API = "https://api.github.com"


def pedir_ci(repo, rama="main", archivo_token=None, abrir=None, api=None,
             encendido=None):
    """La última corrida del CI de esa rama. Devuelve `(respuesta, motivo)`.

    `respuesta` es el diccionario crudo de la API —el que entiende
    `lector.interpretar_ci`— o `None`, y entonces `motivo` dice por qué. **No
    hay un tercer resultado**: sin respuesta, la pantalla muestra «no sé» y
    jamás verde.

    `abrir` se inyecta para poder ejercitar el armado del pedido sin red. En
    producción es `urllib.request.urlopen` y nada más.
    """
    if encendido is None:
        encendido = os.environ.get("CAPATAZ_CI") == "1"
    if not encendido:
        return None, MOTIVO_CI_APAGADO
    if not repo or not _REPO.match(repo):
        return None, "«%s» no tiene forma owner/repo" % repo
    url = "%s/repos/%s/actions/runs?branch=%s&per_page=1" % (
        api or API, repo, rama)
    cabeceras = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "capataz",
    }
    token = _token_de(archivo_token)
    if token:
        cabeceras["Authorization"] = "Bearer " + token
    # Un `Request` de verdad y no un objeto de mentira: el arnés inyecta el
    # `abrir` y le mira las cabeceras a **el mismo objeto** que saldría a la
    # red. Un pedido armado sólo para la prueba no prueba el pedido.
    import urllib.request
    if abrir is None:
        abrir = urllib.request.urlopen
    pedido = urllib.request.Request(url, headers=cabeceras)
    try:
        with abrir(pedido, timeout=10) as r:
            datos = json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:                      # noqa: BLE001 — cualquier cosa
        return None, "%s  ·  %s: %s" % (MOTIVO_CI, url, limpiar_secreto(str(e)))
    corridas = datos.get("workflow_runs") if isinstance(datos, dict) else None
    if not corridas:
        return None, "la API contestó sin ninguna corrida para la rama %s" % rama
    return corridas[0], ""


def _token_de(archivo):
    if not archivo or not os.path.isfile(archivo):
        return ""
    try:
        with io.open(archivo, encoding="utf-8", errors="replace") as f:
            for linea in f:
                linea = linea.strip()
                if linea and not linea.startswith("#"):
                    return linea
    except OSError:
        return ""
    return ""

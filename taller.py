"""El taller: quién está trabajando en **esta** máquina, ahora mismo.

`nube.py` contesta *qué quedó publicado* y lo lee de GitHub, que es el árbitro.
Este archivo contesta otra pregunta, la que git no puede contestar: **si un
proceso está vivo en este segundo**. Hasta hoy capataz la aproximaba mirando si
una rama se había movido, y por eso la regla 3 lo obliga a decir `dudoso` en vez
de `caído`. Esa inferencia se puede reemplazar por un dato medido.

## Por qué esto no contradice la regla 1

La regla 1 dice que capataz lee de GitHub, y el punto T12 rechazó a propósito
«dejar un segundo camino de lectura local». Esto no es ese caso, y la diferencia
es toda la justificación de que el archivo exista:

    T12 rechazaba leer **el mismo dato** —el `SEGUIMIENTO.md`— desde dos lugares
    sin regla de cuál gana; eso es el bug más caro de Finca 360. Acá se lee un
    dato **que no está en git y no puede estar**: si un proceso corre. No hay dos
    versiones del mismo hecho, así que no hay cuál-gana que decidir.

Lo que se mantiene igual, y lo verifica el arnés: **no escribe, no lanza nada, no
guarda estado propio y jamás abre una transcripción.**

## El alcance es parte del dato, no una nota al pie

Lo que se ve acá es **esta máquina y nada más**. Un agente corriendo en otra Mac
o en un contenedor no aparece, y mostrarlo como si fuera la flota entera es
exactamente el tablero que miente del que habla la regla 3. Por eso `leer()`
devuelve `alcance` junto a los datos y la pantalla lo muestra pegado al título.

## Lo que se abre y lo que no

De `~/.claude` se leen **dos clases de archivo, las dos diminutas**:

    sessions/<pid>.json                         ~300 bytes, el registro de vivas
    projects/<proy>/<sesión>/subagents/
        agent-<id>.meta.json                    ~130 bytes, y **es el árbol**

Y desde el 2026-08-15, **la cola de la transcripción**: los últimos 64 KB, y
nada más. Hasta ese día este módulo prometía no abrirla nunca, con este motivo
escrito: una transcripción es todo lo que el agente leyó —archivos, errores, lo
que sea— y un tablero que la abre es un tablero que puede mostrarla.

El motivo sigue siendo cierto, así que la promesa **no se borró: se hizo más
chica y más verificable**. Pablo pidió ver *qué* está haciendo cada agente y no
sólo *si* trabaja, y eso está en un solo lugar. Lo que la sostiene ahora:

    · se leen los últimos COLA_BYTES y nunca el archivo entero — hay
      transcripciones de 13 MB en esta máquina;
    · de cada evento se saca lo que está en una **lista blanca**: el nombre de
      la herramienta, su `description` —que ya está escrita para un humano— y el
      **basename** de la ruta sobre la que trabaja;
    · **nunca** el `command` de un Bash, el texto de un mensaje, ni un
      `old_string`. Y es lista blanca y no lista negra a propósito: una lista de
      lo prohibido es por donde se escapa el primer secreto.

El `mtime` sigue siendo el latido —eso no cambió— y sigue costando un `os.stat`.

## Los umbrales salen de una medición, no de una intuición

Sobre los 17 subagentes que había en disco (2830 huecos entre líneas): un agente
que **sí** está trabajando puede quedarse callado hasta **272 s**; el p99 es 50 s
y el p99.9, 150 s. Por eso `FRESCO` son 5 minutos y no 1: con 1 minuto, uno de
cada cien agentes vivos aparecería como caído, y un tablero que se equivoca en el
caso que importa no se mira más.

Sin dependencias: sólo biblioteca estándar. → `pruebas/verificar-taller.py`
"""

import io
import json
import os
import re
import time

from nube import limpiar_secreto

AQUI = os.path.dirname(os.path.abspath(__file__))

# La carpeta de Claude Code. Se puede mover con `CAPATAZ_TALLER`, que es lo que
# usa el arnés para apuntar a un taller de mentira sin tocar el de verdad.
RAIZ = os.environ.get("CAPATAZ_TALLER") or os.path.expanduser("~/.claude")

# ---------------------------------------------------------------------------
# Trabajando, dudoso o caído: los dos umbrales, medidos el 2026-08-06
# ---------------------------------------------------------------------------
#
# Sobre los 17 subagentes que había en disco, el hueco más largo entre dos
# líneas de un agente **que estaba trabajando** fue de 272 s. Los percentiles:
# p50 = 2 s, p90 = 10 s, p99 = 50 s, p99.9 = 150 s. `FRESCO` va arriba del
# máximo observado a propósito: el error caro no es tardar en decir «caído», es
# decirlo de alguien que está pensando.
FRESCO = 5 * 60           # menos que esto: trabajando
TIBIO = 30 * 60           # entre los dos: dudoso. Más: caído

# Y un tercero, más chico, que no decide un desenlace: decide si la pantalla
# **late**. Sale de la misma medición y no de una intuición: sobre los 2830
# huecos entre líneas, el p90 es de 10 s. O sea que un agente que escribió hace
# menos de eso está, nueve de cada diez veces, en el medio de algo.
#
# Es una banda para mirar, no para afirmar: pasado el umbral el agente sigue
# `trabajando` —eso no cambió—, sólo se le apaga el latido. La diferencia
# importa: si `LATIENDO` decidiera un estado, un agente pensando 20 segundos se
# vería como apagado, que es justo el error que `FRESCO` evita.
LATIENDO = 10

# Los archivos que se abren son de cientos de bytes. Con este tope, apuntar
# `CAPATAZ_TALLER` a una carpeta con un archivo enorme no cuelga la pantalla.
TOPE_BYTES = 64 * 1024

# Y un tope de agentes recorridos, por lo mismo: una sesión larga acumula
# transcripciones y la pantalla no sirve para leer un log.
TOPE_AGENTES = 500

# Las claves que el `.meta.json` trae siempre, medidas sobre los 17 casos. Las
# otras cuatro —`model`, `worktreePath`, `worktreeBranch`, `parentAgentId`— son
# opcionales, y `parentAgentId` aparece sólo cuando `spawnDepth` es mayor que 1.
META_SIEMPRE = ("agentType", "description", "toolUseId", "spawnDepth")

ALCANCE = ("esta máquina · ahora. Un agente en otra máquina o en un contenedor "
           "no aparece acá: para eso está la lectura de GitHub.")

MOTIVO_SIN_TALLER = (
    "no encontré la carpeta de Claude Code. Sin ella no hay nada que mirar del "
    "taller —lo de GitHub se lee igual—. Se apunta con CAPATAZ_TALLER si vive "
    "en otro lado. Buscado en: %s")

# Sin la ruta, a propósito. La regla es mostrar **qué buscó** cuando algo está
# roto, y acá no hay nada roto: una sesión que todavía no lanzó ningún subagente
# es lo más común del mundo. Metida en la pantalla, esa ruta ocupaba nueve
# renglones de teléfono para decir «no pasa nada».
MOTIVO_SIN_TRANSCRIPTOS = (
    "sin subagentes todavía: son cero agentes, no un error%s")

MOTIVO_SESION_MUERTA = (
    "el proceso de la sesión ya no está, así que ninguno de sus agentes puede "
    "estar corriendo. Si terminó o lo cortaron no se sabe desde acá: adentro de "
    "la transcripción de un subagente no hay ninguna marca de cierre (medido "
    "sobre 17 casos el 2026-08-06)")

# Este texto **se lee en la pantalla**, así que no lleva markdown: los
# asteriscos de énfasis salieron literales la primera vez que se lo miró en el
# navegador. Y es un renglón y no un párrafo: al lado de un chip, tres líneas de
# explicación tapan a los otros agentes. El porqué largo vive en el docstring de
# `estado_agente`, que es donde se lee cuando se lo busca.
MOTIVO_SIN_SEÑAL = "terminado o colgado: desde acá no se distinguen"

MOTIVO_SIN_LATIDO = (
    "el agente está declarado pero su transcripción no existe todavía. Entre "
    "que se escribe el meta y la primera línea pasan unos segundos")


class FueraDelTaller(RuntimeError):
    """Se intentó abrir algo que está fuera de la carpeta de Claude Code.

    Es la contracara de `FueraDelEspejo` de `nube.py`, y acá pesa más: `~/.claude`
    **no es de capataz ni es descartable**, es estado de otro. La compuerta dice
    que pase lo que pase, lo que se abra va a estar adentro de esa carpeta.
    """


# ----------------------------------------------------------------------------
# 1 · La compuerta — el único lugar del módulo donde se abre un archivo
# ----------------------------------------------------------------------------

def _dentro(ruta, base):
    """`realpath` de los dos lados: neutraliza `..` y los symlinks."""
    r = os.path.realpath(ruta)
    b = os.path.realpath(base)
    return r == b or r.startswith(b + os.sep)


def _abrir(ruta, raiz=None):
    """Leer un JSON chico de adentro del taller. Devuelve `(dato, error)`.

    **Este es el único `io.open` del módulo, y es de sólo lectura.** El arnés lo
    cuenta por AST y exige exactamente uno, igual que `verificar-nube.py` exige
    un solo `subprocess` adentro de `_git`. Que sea uno solo es lo que hace que
    la afirmación «capataz no escribe» se pueda verificar mirando el código y no
    creyéndole a un comentario.

    Y **nunca abre un `.jsonl`**: la compuerta de extensión está abajo, y su
    motivo está en el docstring del módulo.
    """
    base = raiz or RAIZ
    if not _dentro(ruta, base):
        raise FueraDelTaller(
            "«%s» está fuera de %s. Capataz no abre archivos de nadie afuera "
            "del taller." % (ruta, base))
    if not ruta.endswith(".json"):
        raise FueraDelTaller(
            "«%s» no es un .json. De una transcripción se mira el mtime y nada "
            "más: abrirla es poder mostrarla." % ruta)
    try:
        if os.path.getsize(ruta) > TOPE_BYTES:
            return None, "%s pesa más de %d bytes; no es un archivo del taller" \
                % (os.path.basename(ruta), TOPE_BYTES)
        with io.open(ruta, encoding="utf-8", errors="replace") as f:
            return json.load(f), ""
    except (OSError, ValueError) as e:
        return None, limpiar_secreto("no pude leer %s: %s" % (ruta, e))


# ----------------------------------------------------------------------------
# 1b · Qué está haciendo — la cola de la transcripción, y sólo la lista blanca
# ----------------------------------------------------------------------------
#
# Medido el 2026-08-15 sobre las transcripciones de esta máquina: en 64 KB
# entran 27 eventos, de sobra para encontrar la última herramienta usada. Los
# archivos van de 33 KB a 13 MB, así que leer la cola es lo que hace que esto
# cueste lo mismo con un agente que recién arranca y con uno de todo el día.
COLA_BYTES = 64 * 1024

# **Lista blanca, y por eso es una tupla y no un `if`.** De la entrada de una
# herramienta sale el basename de una de estas claves y nada más. El `command`
# de un Bash y el texto de un mensaje no están, y no se agregan: lo que se
# muestra en un tablero es lo que se puede filtrar a la pantalla de al lado.
CAMPOS_RUTA = ("file_path", "notebook_path", "path")

# El `description` de una herramienta lo escribe el modelo para que lo lea una
# persona —«List files in current directory»—, igual que el `description` de un
# subagente que este módulo ya muestra. Se limpia y se corta como cualquier
# texto de afuera.
TOPE_QUE_HACE = 70

MOTIVO_SIN_COLA = (
    "escribió recién pero en los últimos %d KB de su transcripción no hay "
    "ninguna herramienta: puede estar pensando o escribiendo la respuesta")


def _cola(ruta, raiz=None):
    """Los últimos `COLA_BYTES` de una transcripción, en eventos ya parseados.

    **Este es el segundo y último `io.open` del módulo**, y el arnés cuenta los
    dos: uno abre `.json` y éste abre `.jsonl`, sin leerlo entero. La compuerta
    de carpeta es la misma —lo que se abra está adentro del taller—; lo que
    cambia es la extensión, y por eso está acá y no adentro de `_abrir`: que las
    dos clases de archivo se abran en dos funciones distintas es lo que permite
    decir en una línea qué hace cada una.
    """
    base = raiz or RAIZ
    if not _dentro(ruta, base):
        raise FueraDelTaller(
            "«%s» está fuera de %s. Capataz no abre archivos de nadie afuera "
            "del taller." % (ruta, base))
    if not ruta.endswith(".jsonl"):
        raise FueraDelTaller(
            "«%s» no es una transcripción .jsonl." % ruta)
    try:
        tam = os.path.getsize(ruta)
        with io.open(ruta, "rb") as f:
            f.seek(max(0, tam - COLA_BYTES))
            crudo = f.read(COLA_BYTES)
    except OSError:
        return []
    lineas = crudo.decode("utf-8", "replace").splitlines()
    # La primera línea de la cola casi siempre está cortada por la mitad: se
    # tira. Sólo se conserva entera cuando el archivo entra en la cola.
    if tam > COLA_BYTES and lineas:
        lineas = lineas[1:]
    eventos = []
    for l in lineas:
        try:
            d = json.loads(l)
        except ValueError:
            continue            # una línea partida no es un error: es la cola
        if isinstance(d, dict):
            eventos.append(d)
    return eventos


def _nombre_corto(nombre):
    """`mcp__Claude_Browser__javascript_tool` → `javascript_tool`.

    Las herramientas de un servidor MCP llegan con el servidor adelante y el
    nombre útil al final. Sin esto el chip mide media pantalla de teléfono y
    empuja lo de al lado a dos renglones — se vio mirando, con este mismo nombre
    de ejemplo. Se corta por el separador, no por largo: cortar por largo deja
    `mcp__Claude_Browser__javascr…`, que no dice nada.
    """
    if nombre.startswith("mcp__") and "__" in nombre[5:]:
        return nombre.rsplit("__", 1)[-1] or nombre
    return nombre


def _de_la_lista_blanca(bloque):
    """De un `tool_use`, lo único que se deja salir. Devuelve `(que, sobre)`."""
    nombre = _nombre_corto(limpiar_secreto(str(bloque.get("name") or ""))[:60])[:40]
    entrada = bloque.get("input")
    entrada = entrada if isinstance(entrada, dict) else {}
    sobre = ""
    for clave in CAMPOS_RUTA:
        valor = entrada.get(clave)
        if isinstance(valor, str) and valor:
            # El **basename**, no la ruta: la carpeta ya se muestra arriba y una
            # ruta entera ocupa tres renglones de teléfono.
            sobre = os.path.basename(valor)
            break
    if not sobre:
        d = entrada.get("description")
        if isinstance(d, str):
            sobre = d
    return nombre, _para_pantalla(sobre)


def _para_pantalla(texto):
    """Texto de otro agente, listo para dibujar. Sin markdown y cortado.

    Lo que llega acá lo escribió otro agente para que lo lea una persona, y
    viene con backticks y asteriscos: **en una pantalla salen literales**, que
    es la misma marca que ya tienen `taller.ALCANCE` y `consola.ALCANCE`. Se
    sacan los dos y se corta en un espacio, no en el medio de una palabra —
    cortar al bruto dejaba cosas como «la magnitud conductividad en **dS».
    """
    t = limpiar_secreto(texto or "").replace("`", "").replace("*", "")
    t = " ".join(t.split())
    if len(t) <= TOPE_QUE_HACE:
        return t
    corte = t[:TOPE_QUE_HACE]
    espacio = corte.rfind(" ")
    return (corte[:espacio] if espacio > TOPE_QUE_HACE // 2 else corte) + "…"


def que_hace(transcripcion, raiz=None):
    """La última herramienta que usó ese agente. `(que, sobre, error)`.

    Se camina la cola **de atrás para adelante** y se corta en el primer
    `tool_use`: es lo último que hizo. Si en toda la cola no hay ninguno, no se
    inventa nada —se dice que puede estar pensando—, que es la regla 3 en el
    caso más chico del tablero.
    """
    try:
        eventos = _cola(transcripcion, raiz)
    except FueraDelTaller:
        raise
    except OSError:
        return "", "", "no pude leer la cola de la transcripción"
    for d in reversed(eventos):
        mensaje = d.get("message")
        if not isinstance(mensaje, dict):
            continue
        contenido = mensaje.get("content")
        if not isinstance(contenido, list):
            continue
        for bloque in reversed(contenido):
            if isinstance(bloque, dict) and bloque.get("type") == "tool_use":
                que, sobre = _de_la_lista_blanca(bloque)
                if que:
                    return que, sobre, ""
    return "", "", MOTIVO_SIN_COLA % (COLA_BYTES // 1024)


# ----------------------------------------------------------------------------
# 1c · En qué rama trabaja — 34 bytes, y sin correr git
# ----------------------------------------------------------------------------
#
# Es la **llave** que asocia una sesión de esta máquina con su renglón en la
# vista de GitHub: allá los agentes son ramas por delante de `main`, y acá una
# sesión es una carpeta. Lo que las une es en qué rama está parada esa carpeta,
# y ese dato no está en ninguna de las dos fuentes: está en el disco.
#
# Medido el 2026-08-15: `.git/HEAD` pesa entre 21 y 34 bytes y dice
# `ref: refs/heads/<rama>`. **No hace falta correr git**, que además está
# prohibido fuera del espejo (`nube._git`).
TOPE_HEAD = 4 * 1024

# Lo único que se acepta de ahí: el nombre de una rama. Un `HEAD` desprendido
# trae un sha y eso **no es una rama**, así que se dice que no se sabe en vez de
# mostrar cuarenta caracteres de hexadecimal en un teléfono.
_RAMA = re.compile(r"^ref:\s*refs/heads/(.+?)\s*$")


def rama_de(cwd):
    """La rama en la que está parada esa carpeta. `""` si no se puede saber.

    **Este es el único archivo que este módulo abre fuera de `~/.claude`**, y
    por eso tiene su propia compuerta en vez de pasar por `_abrir`: la ruta se
    arma acá —`<cwd>/.git/HEAD` y nada más—, así que por más que `cwd` venga de
    un archivo de otro, lo que se abre no puede ser otra cosa. Sigue siendo sólo
    lectura y sigue sin correr nada.
    """
    if not cwd or not os.path.isabs(cwd):
        return ""
    ruta = os.path.join(cwd, ".git", "HEAD")
    if os.path.basename(ruta) != "HEAD" or not ruta.endswith(
            os.path.join(".git", "HEAD")):
        return ""
    try:
        if not os.path.isfile(ruta) or os.path.getsize(ruta) > TOPE_HEAD:
            return ""
        with io.open(ruta, encoding="utf-8", errors="replace") as f:
            cabeza = f.read(TOPE_HEAD)
    except OSError:
        return ""
    m = _RAMA.match(cabeza.strip())
    return limpiar_secreto(m.group(1))[:120] if m else ""


def _vive(pid):
    """Si el proceso existe. `None` cuando no se puede saber.

    La señal 0 no le hace nada a nadie: es la forma que tiene el sistema de
    contestar «ese pid existe». No lanza un proceso, no lo toca y no lo cambia
    —capataz sigue sin correr nada—, y es la diferencia entre afirmar que una
    sesión está viva y suponerlo por un archivo que quedó tirado.
    """
    if not isinstance(pid, int) or pid <= 0:
        return None
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True         # existe, es de otro usuario
    except OSError:
        return None


def carpeta_de(cwd, raiz=None):
    """Dónde guarda Claude Code las transcripciones de un directorio.

    El nombre es la ruta con las barras cambiadas por guiones:
    `/Users/Acer/Proyectos/capataz` → `-Users-Acer-Proyectos-capataz`.
    """
    return os.path.join(raiz or RAIZ, "projects", (cwd or "").replace(os.sep, "-"))


# ----------------------------------------------------------------------------
# 2 · Las sesiones — el registro de lo que está prendido
# ----------------------------------------------------------------------------

def sesiones(raiz=None, ahora=None):
    """Las sesiones de Claude Code que esta máquina tiene registradas.

    Salen de `~/.claude/sessions/<pid>.json`, que es el registro que el propio
    Claude Code mantiene. Para una sesión **interactiva** el archivo **gana**:
    da doce campos contra los seis de `claude agents --json` y no cuesta lanzar
    un proceso. Ésa es la regla escrita de cuál fuente manda, y su otra mitad
    está en `consola.py`: el `state` de un background y los background ya
    terminados **no están acá y no pueden estar** —al pararse, este archivo se
    borra—, así que ésos los contesta el CLI y nadie más.

    Un archivo puede quedar tirado si la sesión murió mal, así que cada una
    viene con `viva`, que se pregunta al sistema y no al archivo.
    """
    raiz = raiz or RAIZ
    ahora = time.time() if ahora is None else ahora
    carpeta = os.path.join(raiz, "sessions")
    try:
        archivos = sorted(f for f in os.listdir(carpeta) if f.endswith(".json"))
    except OSError:
        return [], MOTIVO_SIN_TALLER % carpeta
    salida = []
    for a in archivos:
        d, error = _abrir(os.path.join(carpeta, a), raiz)
        if not d:
            continue
        pid = d.get("pid")
        arrancada = d.get("startedAt")
        # La transcripción de la sesión misma vive al lado de las de sus
        # subagentes, con el nombre del `sessionId`. Hasta hoy no se miraba, así
        # que de una sesión **sin** subagentes no se sabía nada: ni si estaba
        # trabajando. Su `mtime` es el latido y su cola dice qué está haciendo.
        transcripcion = os.path.join(carpeta_de(d.get("cwd") or "", raiz),
                                     "%s.jsonl" % (d.get("sessionId") or ""))
        try:
            ultimo = os.path.getmtime(transcripcion)
        except OSError:
            ultimo = None
        if ultimo is None:
            que, sobre, motivo_que = "", "", "no encontré su transcripción"
        else:
            que, sobre, motivo_que = que_hace(transcripcion, raiz)
        salida.append({
            "ultimo": ultimo,
            "quieto_hace": None if ultimo is None else max(0, int(ahora - ultimo)),
            "que": que,
            "sobre": sobre,
            "motivo_que": motivo_que,
            "pid": pid,
            "viva": _vive(pid),
            "sesion": d.get("sessionId") or "",
            "nombre": d.get("name") or "",
            "cwd": d.get("cwd") or "",
            # `kind` viaja crudo, y el archivo escribe `"bg"` donde el CLI
            # escribe `"background"` (medido el 2026-08-15). Traducirlo acá
            # sería tapar la diferencia justo donde `consola.cotejar` tiene que
            # poder verla; el alias se declara en un solo lugar y es suyo.
            "clase": d.get("kind") or "",
            # La rama de la carpeta: la llave que asocia esta sesión con su
            # renglón en la vista de GitHub.
            "rama": rama_de(d.get("cwd") or ""),
            "arrancada": arrancada / 1000.0 if isinstance(arrancada, (int, float)) else None,
            "version": d.get("version") or "",
            "entrada": d.get("entrypoint") or "",
            "error": error,
        })
    salida.sort(key=lambda s: (s["cwd"], s["nombre"]))
    return salida, ""


# ----------------------------------------------------------------------------
# 3 · Los agentes — y el árbol sale del meta, no de la transcripción
# ----------------------------------------------------------------------------

def agentes(cwd, sesion, raiz=None, ahora=None):
    """Los subagentes de una sesión, ya armados en árbol. `(agentes, error)`.

    Todo lo que hace falta está en los `.meta.json`, que pesan 130 bytes:
    `agentType`, `description`, `spawnDepth` y —cuando hay anidamiento—
    `parentAgentId`, que es la arista del árbol. Los archivos viven **planos**
    en la misma carpeta aunque los agentes estén anidados.

    De la transcripción sólo se mira el `mtime`, que es el último latido.
    """
    raiz = raiz or RAIZ
    ahora = time.time() if ahora is None else ahora
    carpeta = os.path.join(carpeta_de(cwd, raiz), sesion, "subagents")
    try:
        metas = sorted(f for f in os.listdir(carpeta) if f.endswith(".meta.json"))
    except OSError:
        return [], MOTIVO_SIN_TRANSCRIPTOS % ""
    planos = []
    for m in metas[:TOPE_AGENTES]:
        d, error = _abrir(os.path.join(carpeta, m), raiz)
        if not d:
            continue
        faltan = [k for k in META_SIEMPRE if k not in d]
        ident = m[len("agent-"):-len(".meta.json")]
        transcripcion = os.path.join(carpeta, "agent-%s.jsonl" % ident)
        try:
            ultimo = os.path.getmtime(transcripcion)
        except OSError:
            ultimo = None
        try:
            arrancado = os.path.getmtime(os.path.join(carpeta, m))
        except OSError:
            arrancado = None
        if ultimo is None:
            que, sobre, motivo_que = "", "", ""
        else:
            que, sobre, motivo_que = que_hace(transcripcion, raiz)
        planos.append({
            "id": ident,
            "que": que,
            "sobre": sobre,
            "motivo_que": motivo_que,
            "tipo": d.get("agentType") or "",
            "descripcion": limpiar_secreto(d.get("description") or ""),
            "profundidad": d.get("spawnDepth"),
            "padre": d.get("parentAgentId") or None,
            "modelo": d.get("model") or None,
            "worktree": d.get("worktreeBranch") or None,
            "arrancado": arrancado,
            "ultimo": ultimo,
            "quieto_hace": None if ultimo is None else max(0, int(ahora - ultimo)),
            "error": error or ("al meta le faltan %s" % ", ".join(faltan) if faltan else ""),
            "hijos": [],
        })
    return _arbol(planos), ""


def _arbol(planos):
    """Colgar cada agente de su padre. Los de primer nivel quedan arriba.

    Un agente de `spawnDepth` 1 no trae `parentAgentId` y su padre es la sesión.
    Si un `parentAgentId` apunta a alguien que no está —no debería pasar—, el
    agente queda arriba en vez de desaparecer: un huérfano visible es un dato,
    uno filtrado en silencio es un agente que capataz decidió no mostrar.
    """
    por_id = {a["id"]: a for a in planos}
    raices = []
    for a in planos:
        padre = por_id.get(a["padre"]) if a["padre"] else None
        if padre is None:
            raices.append(a)
        else:
            padre["hijos"].append(a)
    return raices


# ----------------------------------------------------------------------------
# 4 · Trabajando, dudoso o caído
# ----------------------------------------------------------------------------

def estado_agente(agente, sesion_viva, ahora=None):
    """Qué se puede afirmar de un subagente. Devuelve `(estado, motivo)`.

    Cinco desenlaces y ninguno inventa nada:

      `no sé`       el meta está pero la transcripción no existe todavía.
      `cerrado`     el proceso de la sesión no está. Ninguno de sus agentes
                    puede estar corriendo.
      `trabajando`  escribió hace menos de `FRESCO`.
      `dudoso`      entre `FRESCO` y `TIBIO`. No se afirma nada: es el rato en
                    que un agente pensando y uno colgado se parecen.
      `sin señal`   más de `TIBIO` callado.

    **No existe `terminado`, y no existe `caído`.** Es el hallazgo que más costó
    de esta tanda, y las dos ausencias son la misma:

      · Se midieron los 17 subagentes que había en disco y **ninguno deja marca
        de cierre en su propio archivo**. Un agente en curso y uno que terminó
        son indistinguibles por su última línea.
      · Se probó una segunda señal para salvar eso sin abrir transcripciones:
        *«si el padre escribió después de que el hijo se calló, el hijo
        terminó»*. **No discrimina, y se descarta.** Dio verdadero en los 17
        casos… que son 17 agentes terminados: cero casos negativos, o sea una
        aserción vacua de manual. Y tiene contraejemplo medido — un subagente en
        background no frena al padre, así que el padre sigue escribiendo
        mientras el hijo trabaja.

    Entonces se dice `sin señal` y se dice el rato, que es lo accionable, en vez
    de `caído`, que sería inventar un incendio donde lo más probable es que el
    agente haya entregado hace rato. Es la misma lección que `integrada` en
    `lector.estado_rama`.
    """
    ahora = time.time() if ahora is None else ahora
    if agente.get("ultimo") is None:
        return "no sé", MOTIVO_SIN_LATIDO
    if sesion_viva is False:
        return "cerrado", MOTIVO_SESION_MUERTA
    quieto = ahora - agente["ultimo"]
    if quieto < FRESCO:
        return "trabajando", ""
    if quieto < TIBIO:
        return "dudoso", ("más de lo esperable: un agente vivo se queda callado "
                          "hasta 4 min y medio —medido—")
    return "sin señal", MOTIVO_SIN_SEÑAL


def _rato(segundos):
    """«8 min», «2 h 21 min», «3 días». Un número de segundos no se lee."""
    s = int(segundos)
    if s < 60:
        return "%d s" % s
    if s < 3600:
        return "%d min" % (s // 60)
    if s < 86400:
        return "%d h %d min" % (s // 3600, (s % 3600) // 60)
    return "%d días" % (s // 86400)


# ----------------------------------------------------------------------------
# 5 · La vista entera
# ----------------------------------------------------------------------------

def leer(raiz=None, ahora=None):
    """Todo el taller de esta máquina, en la forma que espera la pantalla.

    Devuelve **siempre** un diccionario con la misma forma. Nunca revienta y
    nunca devuelve vacío por error: si no hay taller, `ok` es `False` y `error`
    dice qué buscó, que es lo accionable. Cero sesiones y «no pude mirar» son
    cosas distintas y tienen que verse distintas.
    """
    raiz = raiz or RAIZ
    ahora = time.time() if ahora is None else ahora
    vista = {
        "ok": False,
        "error": "",
        "raiz": raiz,
        "alcance": ALCANCE,
        "leido_en": ahora,
        "sesiones": [],
        "cuenta": {"sesiones": 0, "vivas": 0, "agentes": 0, "trabajando": 0},
    }
    ses, error = sesiones(raiz, ahora)
    if error:
        vista["error"] = error
        return vista
    cuenta = vista["cuenta"]
    for s in ses:
        arbol, err_agentes = agentes(s["cwd"], s["sesion"], raiz, ahora)
        s["agentes"] = arbol
        # Un error de agentes **no descarta la sesión**: que no tenga
        # transcripciones todavía es lo más normal del mundo, y la sesión
        # sigue siendo un dato bueno. El error viaja al lado.
        s["motivo_sin_agentes"] = err_agentes if not arbol else ""
        for a in _todos(arbol):
            a["estado"], a["motivo_estado"] = estado_agente(a, s["viva"], ahora)
            cuenta["agentes"] += 1
            if a["estado"] == "trabajando":
                cuenta["trabajando"] += 1
        cuenta["sesiones"] += 1
        if s["viva"]:
            cuenta["vivas"] += 1
    vista["ok"] = True
    vista["sesiones"] = ses
    return vista


def _todos(arbol):
    """Los agentes del árbol, aplanados. Iterativo: un ciclo no lo cuelga."""
    pila, salida, vistos = list(arbol), [], set()
    while pila:
        a = pila.pop()
        if a["id"] in vistos:
            continue
        vistos.add(a["id"])
        salida.append(a)
        pila.extend(a["hijos"])
    return salida


def empatar(vista, proyectos):
    """Anotarle a cada sesión de qué proyecto vigilado es la carpeta.

    **Anota, no reparte.** La tentación era devolver un diccionario
    `proyecto → sesiones`, y eso deja la misma sesión en dos lugares de la
    misma respuesta sin ninguna regla sobre cuál gana — que es literalmente el
    bug que este proyecto tiene escrito como regla 1. Acá la lista de sesiones
    sigue siendo una sola y cada una lleva su `proyecto`.

    El empate es por el nombre de la carpeta contra el del repositorio. Lo que
    no empata queda con `proyecto` vacío y **se muestra igual**: una sesión
    corriendo en una carpeta que capataz no vigila es exactamente el tipo de
    cosa que hay que ver, no filtrar.

    Devuelve cuántas quedaron sin dueño, que es lo que la pantalla rotula.
    """
    sueltas = 0
    for s in vista.get("sesiones", []):
        base = os.path.basename(s.get("cwd") or "").lower()
        s["proyecto"] = ""
        for p in proyectos:
            repo = (p.get("repo") or "").split("/")[-1].lower()
            nombre = (p.get("nombre") or "").lower().replace(" ", "")
            if base and base in (repo, nombre):
                s["proyecto"] = p.get("nombre") or ""
                break
        if not s["proyecto"]:
            sueltas += 1
    return sueltas

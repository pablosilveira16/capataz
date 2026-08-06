#!/usr/bin/env python3
"""Lo que capataz sabe de un proyecto, leyendo y nada más.

Todo lo que hay acá adentro es de **sólo lectura**, y no por prolijidad: es la
regla 1 de `CLAUDE.md`. El `SEGUIMIENTO.md` de cada proyecto es la verdad y git
es el árbitro; si capataz escribiera un estado propio habría dos lugares con el
mismo dato y ninguna regla sobre cuál gana. Concretamente, en este archivo:

  · ningún `open(..., "w")`, ningún `os.remove`, ningún `mkdir`;
  · los comandos de git pasan por `_git()`, que **rechaza** cualquier
    subcomando que no esté en `GIT_LECTURA` — un `fetch` o un `checkout` desde
    acá ya es capataz teniendo opinión sobre el repo de otro.

Lo verifica `pruebas/verificar-lector.py` § 1, y no leyendo este comentario:
saca una foto de un proyecto de prueba, corre `mirar()` entero y compara.

Sin dependencias: sólo biblioteca estándar. Es la misma línea que `panel.py` de
ERP 360, y el motivo está escrito en el andamio — un proyecto que necesita
instalar algo para verificarse es un proyecto donde el agente depende de que vos
estés. Acá se suma otro: capataz mira proyectos ajenos y no debe imponerles nada.

## Los dos formatos, que es la mitad del problema

ERP 360 y Finca 360 no escriben igual el seguimiento:

  · el archivo se llama distinto (`SEGUIMIENTO.md` vs `Finca360 — Seguimiento.md`)
    → por eso `proyectos.json` lleva el nombre de cada uno;
  · ERP 360 pone el estado en la última celda y la columna se llama `Estado`;
    Finca 360, en sus tablas de *Abierto ahora*, **no tiene columna de estado**:
    el estado lo dice el título de la sección («Depende de Pablo»).

Por eso el estado se saca del **encabezado de la tabla** y no de «la última
celda»: si hay una columna `Estado`, se lee de ahí. Si no la hay, se cae al
título de la sección, y sólo con el mapa que el propio `proyectos.json` declara
para ese proyecto. Si tampoco alcanza, el punto queda en `sin estado` y se
muestra como tal — no se adivina.
"""
import io
import json
import os
import re
import subprocess
import time

# Los cinco, y no hay otros. El mismo vocabulario cerrado del contrato de
# `SEGUIMIENTO.md`; capataz no agrega ninguno.
ESTADOS = ("pendiente", "en curso", "hecho", "diferido", "descartado")
SIN_ESTADO = "sin estado"

# El orden importa para el matcheo: «en curso» primero, porque es el único de
# dos palabras y porque es el que más urge ver.
_ORDEN_MATCHEO = ("en curso", "pendiente", "hecho", "diferido", "descartado")

# Después de esto, una marca de «empecé» deja de contar como trabajo en curso.
# Un agente que se cae no puede dejar el tablero diciendo que trabaja para
# siempre: eso sería peor que no tener tablero. Es el mismo valor que usa
# `panel/panel.py` de ERP 360, del que sale el formato de las marcas.
VENCE_EN = 30 * 60

# Cuántas marcas viajan a la pantalla. Con más, el tablero se vuelve un log.
ULTIMAS_MARCAS = 40

# Sólo lectura, y verificado: `_git()` revienta con cualquier otro subcomando.
GIT_LECTURA = frozenset((
    "rev-parse", "for-each-ref", "rev-list", "show", "log", "cat-file",
))

MOTIVO_CI = (
    "api.github.com está fuera de la lista blanca del contenedor de un agente "
    "(medido en ERP 360, ops/70-credenciales.md), y gh no está instalado. "
    "Desde acá no se puede leer el CI: hay que abrirlo en la web."
)

MOTIVO_TOTAL = (
    "el proyecto no dejó el total medido en pruebas/total-aserciones.txt. "
    "Un total declarado en prosa no es un total medido."
)


class SoloLectura(RuntimeError):
    """Se intentó correr algo que escribe. Capataz sólo lee (CLAUDE.md § 1)."""


# ----------------------------------------------------------------------------
# 1 · El seguimiento
# ----------------------------------------------------------------------------

_SEPARADOR = re.compile(r"^\|[\s:|-]+\|\s*$")
_FECHA = re.compile(r"\d{4}-\d{2}-\d{2}")
_QUIEN = re.compile(r"en curso\s*\(\s*([^)]*?)\s*\)", re.I)
_PABLO = re.compile(r"pendiente\s*\(\s*pablo", re.I)
_ID = re.compile(r"^([A-Za-z]{1,4})\s*-?\s*(\d+[a-z]?)$")


def _celdas(linea):
    partes = linea.strip().split("|")
    if partes and not partes[0].strip():
        partes = partes[1:]
    if partes and not partes[-1].strip():
        partes = partes[:-1]
    return [p.strip() for p in partes]


def _tablas(texto):
    """Cada tabla markdown del texto, con la sección en la que vive.

    Devuelve `(seccion, historia, encabezado, filas)`. `historia` dice si la
    tabla está debajo del título «Historia por tanda»: los dos proyectos usan
    ese corte para separar lo que falta de lo que ya se cerró, y contar las dos
    cosas juntas haría que un proyecto viejo parezca terminado.
    """
    seccion = ""
    historia = False
    prev = None
    enc = None
    filas = None
    sec_tabla = ""
    his_tabla = False
    for linea in texto.splitlines():
        s = linea.strip()
        if s.startswith("|"):
            if _SEPARADOR.match(s):
                # La fila de arriba era el encabezado. Si venía otra tabla
                # abierta, esa fila ya se le había sumado: se la devuelve.
                if enc is not None:
                    if filas and prev is not None and _celdas(prev) == filas[-1]:
                        filas.pop()
                    yield sec_tabla, his_tabla, enc, filas
                enc = (_celdas(prev)
                       if prev is not None and prev.strip().startswith("|")
                       else [])
                filas = []
                sec_tabla, his_tabla = seccion, historia
                prev = linea
                continue
            if enc is not None:
                filas.append(_celdas(s))
            prev = linea
            continue
        if enc is not None:
            yield sec_tabla, his_tabla, enc, filas
            enc = None
            filas = None
        if s.startswith("#"):
            seccion = s.lstrip("#").strip()
            # «Historia por tanda» abre lo cerrado; pero Finca 360 mete un
            # «Abierto de tandas anteriores» DEBAJO de ese título, y esos
            # puntos sí están abiertos. Sin este segundo corte, trece puntos
            # abiertos de Finca 360 se contaban como historia.
            if re.search(r"historia", seccion, re.I):
                historia = True
            elif re.search(r"abierto", seccion, re.I):
                historia = False
        prev = linea
    if enc is not None:
        yield sec_tabla, his_tabla, enc, filas


def _limpiar(celda):
    return re.sub(r"[*`~]", "", celda or "").strip()


def normalizar_estado(celda):
    """La palabra de estado que hay en una celda, o `None` si no hay ninguna.

    Tolera lo que los dos proyectos escriben de verdad: `**hecho** · arnés 61
    aserciones`, `pendiente (Pablo)`, `diferido a producción`, `en curso
    (coder-2)`. No tolera una palabra inventada: devuelve `None` y el punto
    queda en `sin estado`, que es lo que hay que ver.
    """
    t = _limpiar(celda).lower()
    if not t:
        return None
    for e in _ORDEN_MATCHEO:
        if e in t:
            return e
    return None


def _indice(enc, *nombres):
    for i, c in enumerate(enc):
        cl = _limpiar(c).lower()
        for n in nombres:
            if n in cl:
                return i
    return None


def _estado_de_seccion(seccion, mapa):
    """El estado que el `proyectos.json` le declara a una sección sin columna.

    Es interpretación de capataz, no dato propio: por eso vive en la
    configuración del proyecto vigilado y no escrita adentro del código. Sin
    mapa no se adivina nada.
    """
    if not mapa:
        return None
    sl = (seccion or "").lower()
    for clave, valor in mapa.items():
        if clave.lower() in sl:
            return valor
    return None


def leer_seguimiento(ruta, secciones=None):
    """Los puntos de un `SEGUIMIENTO.md`, con su estado y de dónde salió.

    Nunca revienta: si el archivo no está, devuelve el error adentro. Un
    tablero que se cae porque un proyecto se movió de carpeta no sirve de nada.
    """
    if not os.path.isfile(ruta):
        return {"ruta": ruta, "existe": False,
                "error": "no encuentro %s" % ruta, "puntos": []}
    try:
        with io.open(ruta, encoding="utf-8") as f:
            texto = f.read()
    except OSError as e:
        return {"ruta": ruta, "existe": True, "error": str(e), "puntos": []}

    puntos = []
    ignoradas = 0
    for seccion, historia, enc, filas in _tablas(texto):
        if not enc:
            # Un separador sin fila de encabezado arriba no es una tabla.
            continue
        i_estado = _indice(enc, "estado")
        i_desde = _indice(enc, "desde")
        i_id = 0 if _limpiar(enc[0]).lower() in ("#", "id", "n°", "nro") else None
        if i_id is None:
            # **Una tabla de puntos tiene columna `#`.** Sin esta regla entraba
            # la tabla del vocabulario de estados del propio contrato —cinco
            # filas, una por estado— y capataz contaba cinco puntos que no
            # existen, en los tres proyectos. Se cuenta cuántas se saltearon
            # para que el silencio se pueda mirar (`tablas_ignoradas`).
            ignoradas += 1
            continue
        i_titulo = None
        for i in range(len(enc)):
            if i in (i_id, i_desde, i_estado):
                continue
            i_titulo = i
            break
        for fila in filas:
            if not fila or len(fila) < 2:
                continue
            ident = _limpiar(fila[i_id]) if i_id < len(fila) else ""
            if not _ID.match(ident or ""):
                # Fila que no es un punto: una leyenda, un total, un separador.
                continue
            crudo = _limpiar(fila[i_estado]) if (
                i_estado is not None and i_estado < len(fila)) else ""
            estado = normalizar_estado(crudo)
            origen = "celda"
            if estado is None:
                de_seccion = _estado_de_seccion(seccion, secciones)
                estado = normalizar_estado(de_seccion or "")
                if estado is not None:
                    crudo = de_seccion
                    origen = "seccion"
            if estado is None:
                estado = SIN_ESTADO
                origen = "ninguno"
            titulo = _limpiar(fila[i_titulo]) if (
                i_titulo is not None and i_titulo < len(fila)) else ""
            desde = ""
            if i_desde is not None and i_desde < len(fila):
                m = _FECHA.search(fila[i_desde])
                desde = m.group(0) if m else ""
            if not desde:
                m = _FECHA.search(" ".join(fila))
                desde = m.group(0) if m else ""
            m = _QUIEN.search(crudo)
            puntos.append({
                "id": ident,
                "titulo": titulo[:400],
                "seccion": seccion,
                "historia": historia,
                "estado": estado,
                "estado_crudo": crudo[:200],
                "origen_estado": origen,
                "quien": m.group(1) if m else "",
                "desde": desde,
                "dias": _dias_desde(desde),
                "bloquea_a_pablo": bool(_PABLO.search(crudo)),
            })
    unicos, repetidos = separar_repetidos(puntos)
    return {"ruta": ruta, "existe": True, "error": "", "puntos": unicos,
            "repetidos": repetidos, "tablas_ignoradas": ignoradas}


def separar_repetidos(puntos):
    """Un identificador, un punto. El primero gana; los demás se apartan.

    Los dos proyectos repiten filas a propósito —Finca 360 lista X1…X5 en
    *Abierto ahora* y otra vez en *Abierto de tandas anteriores*—, y contarlas
    dos veces infla el tablero justo donde se lo mira para decidir. No se
    tiran: se devuelven aparte, porque dos filas del mismo punto con **estados
    distintos** es algo que alguien tiene que ver.
    """
    vistos = {}
    unicos = []
    repetidos = []
    for p in puntos:
        clave = p["id"]
        if clave and clave in vistos:
            otro = vistos[clave]
            repetidos.append(dict(p, choca_con=otro["estado"],
                                  discrepa=otro["estado"] != p["estado"]))
            continue
        if clave:
            vistos[clave] = p
        unicos.append(p)
    return unicos, repetidos


def _dias_desde(fecha, hoy=None):
    if not fecha:
        return None
    try:
        t = time.mktime(time.strptime(fecha, "%Y-%m-%d"))
    except ValueError:
        return None
    ahora = hoy if hoy is not None else time.time()
    return max(0, int((ahora - t) // 86400))


def contar(puntos, solo_abiertos=False):
    """Cuántos hay de cada estado — **los cinco, incluso los cero**.

    Los ceros son el punto, igual que en el reparto por rol: «pendiente 12» no
    dice nada al lado de «pendiente 12 · en curso 0».
    """
    cuenta = dict((e, 0) for e in ESTADOS)
    cuenta[SIN_ESTADO] = 0
    for p in puntos:
        if solo_abiertos and p["historia"]:
            continue
        cuenta[p["estado"]] = cuenta.get(p["estado"], 0) + 1
    return cuenta


def en_curso(puntos):
    """Los `en curso`, del más viejo al más nuevo. Un `en curso` viejo es lo
    que más urge ver: puede ser un agente que se cayó y dejó el punto tomado."""
    vivos = [p for p in puntos if p["estado"] == "en curso"]
    return sorted(vivos, key=lambda p: (-(p["dias"] or 0), p["id"]))


def pendientes_de_pablo(puntos):
    """Los que lo bloquean a él. Van aparte porque nadie más los puede mover."""
    return [p for p in puntos
            if p["estado"] == "pendiente" and p["bloquea_a_pablo"]]


# ----------------------------------------------------------------------------
# 2 · Los roles que existen en ese proyecto
# ----------------------------------------------------------------------------

_ROL = re.compile(r"^##\s+([A-Za-zÁÉÍÓÚÑáéíóúñ]+)\s*$")


def leer_roles(ruta):
    """Los tipos de agente del proyecto, leídos de su `ops/60-roles.md`.

    **Devuelve `None` si el archivo no está**, y eso es distinto de una lista
    vacía: quiere decir «no sé qué roles tiene este proyecto». Finca 360 no
    tiene ese archivo. Escribir acá la lista de seis de ERP 360 sería la segunda
    fuente que la regla 1 prohíbe, y además sería mentira.
    """
    if not ruta or not os.path.isfile(ruta):
        return None
    try:
        with io.open(ruta, encoding="utf-8") as f:
            texto = f.read()
    except OSError:
        return None
    roles = []
    for linea in texto.splitlines():
        m = _ROL.match(linea.strip())
        if m:
            r = m.group(1).lower()
            if r not in roles:
                roles.append(r)
    return roles


# ----------------------------------------------------------------------------
# 3 · La cuadrilla: quién trabaja ahora
# ----------------------------------------------------------------------------

def leer_marcas(ruta):
    """Las marcas de `panel/agentes.jsonl`, de la más vieja a la más nueva.

    Las **escribe** el `panel/agente.py` de cada proyecto; capataz sólo las lee.
    Una línea rota no puede tirar el tablero: se saltea y se sigue.
    """
    if not ruta or not os.path.isfile(ruta):
        return []
    out = []
    try:
        with io.open(ruta, encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if not linea:
                    continue
                try:
                    d = json.loads(linea)
                except ValueError:
                    continue
                if isinstance(d, dict):
                    out.append(d)
    except OSError:
        return []
    return out


def activos(marcas, ahora=None, vence_en=VENCE_EN):
    """Quién está trabajando ahora, en qué, con qué rol y hace cuánto."""
    ahora = time.time() if ahora is None else ahora
    abierto = {}
    for m in marcas:
        quien = m.get("quien") or "agente"
        if m.get("accion") == "empieza":
            abierto[quien] = m
        elif m.get("accion") == "termina":
            abierto.pop(quien, None)
    vivos = []
    for quien, m in abierto.items():
        desde = m.get("ts") or 0
        if ahora - desde > vence_en:
            continue
        vivos.append({"quien": quien,
                      "rol": (m.get("rol") or "").lower(),
                      "que": m.get("que") or "",
                      "desde": desde,
                      "hace_min": int((ahora - desde) // 60)})
    return sorted(vivos, key=lambda v: v["desde"])


def por_rol(vivos, roles):
    """El reparto por rol, **con los ceros**.

    «coder 3» no dice nada; «coder 3 · reviewer 0» es la frase que hace que
    alguien haga algo. Si el proyecto no declara sus roles (`roles is None`) no
    se inventan: se devuelven sólo los que aparecen en las marcas y el campo
    `conocidos` queda en falso, para que la pantalla lo diga.
    """
    cuenta = {}
    for r in (roles or ()):
        cuenta[r] = 0
    for v in vivos:
        r = v.get("rol") or ""
        clave = r or "sin rol"
        cuenta[clave] = cuenta.get(clave, 0) + 1
    orden = list(roles or ())
    for k in sorted(cuenta):
        if k not in orden:
            orden.append(k)
    return {"conocidos": roles is not None,
            "reparto": [{"rol": k, "cuantos": cuenta[k]} for k in orden]}


# ----------------------------------------------------------------------------
# 4 · Las ramas, y el total de aserciones de cada una
# ----------------------------------------------------------------------------

def _git(ruta, *args):
    """git, **sólo de lectura**. Cualquier otro subcomando revienta.

    No es una precaución teórica: `fetch`, `checkout` y `worktree` son las tres
    cosas que uno agrega sin pensar el día que quiere «un dato más», y las tres
    escriben en el repo de otro proyecto. La regla 1 de `CLAUDE.md` es que
    capataz no toca nada, y acá es donde se hace cumplir.
    """
    if not args or args[0] not in GIT_LECTURA:
        raise SoloLectura(
            "«git %s» no es de lectura. Capataz sólo lee (CLAUDE.md § 1). "
            "Los permitidos: %s" % (args[0] if args else "", ", ".join(sorted(GIT_LECTURA))))
    try:
        p = subprocess.run(["git", "-C", ruta] + list(args),
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           timeout=15)
    except (OSError, subprocess.SubprocessError):
        return None
    if p.returncode != 0:
        return None
    return p.stdout.decode("utf-8", "replace").strip()


def _total_en(ruta, ref, archivo):
    """El total de aserciones que el proyecto dejó **medido** en esa ref.

    Si no está el archivo, `None` — y la pantalla dice «no sé». Nunca se
    inventa un número ni se lo saca de la prosa del seguimiento: un total
    declarado a mano en una celda es lo que alguien recordó escribir, no lo que
    la suite midió.
    """
    if not archivo:
        return None
    salida = _git(ruta, "show", "%s:%s" % (ref, archivo))
    if salida is None:
        return None
    m = re.search(r"\d+", salida)
    return int(m.group(0)) if m else None


def leer_ramas(ruta, total_archivo="pruebas/total-aserciones.txt", principal="main"):
    """Las ramas del repo, de qué punto son y su total contra el de `main`.

    Devuelve `None` si el proyecto **no es un repo git** —Finca 360 no lo es— y
    eso también es un «no sé» y no un cero.
    """
    if _git(ruta, "rev-parse", "--is-inside-work-tree") != "true":
        return None
    fmt = "%(refname:short)\t%(committerdate:short)\t%(authorname)\t%(subject)"
    salida = _git(ruta, "for-each-ref", "--format=" + fmt, "refs/heads")
    if salida is None:
        return None
    total_main = _total_en(ruta, principal, total_archivo)
    ramas = []
    for linea in salida.splitlines():
        partes = linea.split("\t")
        if len(partes) < 4:
            continue
        nombre, fecha, autor, asunto = partes[0], partes[1], partes[2], partes[3]
        cuenta = _git(ruta, "rev-list", "--left-right", "--count",
                      "%s...%s" % (principal, nombre))
        atras = adelante = None
        if cuenta:
            nums = cuenta.split()
            if len(nums) == 2:
                atras, adelante = int(nums[0]), int(nums[1])
        total = _total_en(ruta, nombre, total_archivo)
        m = re.match(r"^([A-Za-z]{1,4})[-_]?(\d+)", nombre)
        ramas.append({
            "nombre": nombre,
            "es_principal": nombre == principal,
            "punto": (m.group(1) + m.group(2)).upper() if m else "",
            "fecha": fecha,
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
    ramas.sort(key=lambda r: (not r["es_principal"], r["nombre"]))
    return ramas


# ----------------------------------------------------------------------------
# 5 · El CI, que desde acá no se puede leer
# ----------------------------------------------------------------------------

def interpretar_ci(respuesta):
    """Traducir una respuesta de la API de GitHub a un estado de pantalla.

    Está separada de `estado_ci` a propósito: el día que capataz corra en la
    Mac —donde `api.github.com` sí se alcanza— lo único que cambia es quién le
    pasa la respuesta. **Sin respuesta, `no sé`. Nunca `verde`.**
    """
    if not respuesta:
        return {"estado": "no sé", "motivo": MOTIVO_CI, "detalle": ""}
    if not isinstance(respuesta, dict):
        return {"estado": "no sé", "motivo": "respuesta ininteligible", "detalle": ""}
    estado_bruto = (respuesta.get("status") or "").lower()
    conclusion = (respuesta.get("conclusion") or "").lower()
    if estado_bruto and estado_bruto != "completed":
        return {"estado": "corriendo", "motivo": "", "detalle": estado_bruto}
    if conclusion == "success":
        return {"estado": "verde", "motivo": "", "detalle": conclusion}
    if conclusion in ("failure", "timed_out", "startup_failure"):
        return {"estado": "rojo", "motivo": "", "detalle": conclusion}
    if conclusion in ("cancelled", "skipped", "neutral", "action_required"):
        return {"estado": "no sé", "motivo": "la corrida no concluyó",
                "detalle": conclusion}
    return {"estado": "no sé", "motivo": MOTIVO_CI, "detalle": conclusion}


def estado_ci(proyecto, respuesta=None):
    """Hoy, siempre `no sé` — y ése es el resultado correcto, no una falta.

    Un tablero que pinta el CI de verde cuando no lo pudo leer miente
    exactamente en el caso que importa: el de la rama que rompió algo.
    """
    return interpretar_ci(respuesta)


# ----------------------------------------------------------------------------
# 6 · Un proyecto entero, y la lista de proyectos vigilados
# ----------------------------------------------------------------------------

def _ruta(base, rel):
    if not rel:
        return ""
    return rel if os.path.isabs(rel) else os.path.join(base, rel)


def normalizar_proyecto(d):
    """Los valores por defecto de una entrada de `proyectos.json`.

    El nombre del archivo de seguimiento **no** tiene defecto obligatorio: es
    justamente lo que cambia entre proyectos, y por eso está en la
    configuración. Los demás sí, porque son la convención del template.
    """
    return {
        "nombre": d.get("nombre") or os.path.basename(str(d.get("ruta", "")).rstrip("/")),
        "ruta": d.get("ruta") or "",
        "seguimiento": d.get("seguimiento") or "SEGUIMIENTO.md",
        "roles": d.get("roles", "ops/60-roles.md"),
        "marcas": d.get("marcas", "panel/agentes.jsonl"),
        "total_aserciones": d.get("total_aserciones", "pruebas/total-aserciones.txt"),
        "rama_principal": d.get("rama_principal") or "main",
        "secciones": d.get("secciones") or {},
    }


def leer_proyectos(ruta_json):
    """La lista de proyectos vigilados.

    Las rutas relativas se resuelven contra la carpeta del propio
    `proyectos.json`, y eso no es comodidad: **la misma carpeta está montada en
    dos rutas distintas** —`/Users/Acer/Documents/…` en la Mac y `/sessions/…`
    en el contenedor de un agente—. Una ruta absoluta ahí deja andando a uno y
    roto al otro, que es la lección que ERP 360 ya pagó en `.git/config`
    (`ops/70-credenciales.md`, «Lo mismo sirve en la Mac y en el contenedor»).
    """
    if not os.path.isfile(ruta_json):
        return []
    try:
        with io.open(ruta_json, encoding="utf-8") as f:
            datos = json.load(f)
    except (OSError, ValueError):
        return []
    if isinstance(datos, dict):
        datos = datos.get("proyectos") or []
    aqui = os.path.dirname(os.path.abspath(ruta_json))
    salida = []
    for d in datos:
        if not isinstance(d, dict):
            continue
        p = normalizar_proyecto(d)
        if p["ruta"] and not os.path.isabs(p["ruta"]):
            p["ruta"] = os.path.normpath(os.path.join(aqui, p["ruta"]))
        salida.append(p)
    return salida


def mirar(proy, ahora=None):
    """Todo lo que capataz sabe de un proyecto. No escribe nada."""
    proy = normalizar_proyecto(proy)
    base = proy["ruta"]
    seg = leer_seguimiento(_ruta(base, proy["seguimiento"]), proy["secciones"])
    puntos = seg["puntos"]
    roles = leer_roles(_ruta(base, proy["roles"])) if proy["roles"] else None
    marcas = leer_marcas(_ruta(base, proy["marcas"])) if proy["marcas"] else []
    vivos = activos(marcas, ahora)
    ramas = leer_ramas(base, proy["total_aserciones"], proy["rama_principal"])
    return {
        "nombre": proy["nombre"],
        "ruta": base,
        "existe": os.path.isdir(base) if base else False,
        "seguimiento": {"archivo": proy["seguimiento"],
                        "existe": seg["existe"], "error": seg["error"],
                        "tablas_ignoradas": seg.get("tablas_ignoradas", 0),
                        "repetidos": seg.get("repetidos", [])},
        "cuenta_abiertos": contar(puntos, solo_abiertos=True),
        "cuenta_total": contar(puntos),
        "en_curso": en_curso(puntos),
        "pendientes_de_pablo": pendientes_de_pablo(puntos),
        "sin_estado": [p for p in puntos if p["estado"] == SIN_ESTADO],
        "roles": roles,
        "cuadrilla": vivos,
        "por_rol": por_rol(vivos, roles),
        "marcas": marcas[-ULTIMAS_MARCAS:][::-1],
        "ramas": ramas,
        "ci": estado_ci(proy),
    }


def mirar_todo(proyectos, ahora=None):
    return [mirar(p, ahora) for p in proyectos]

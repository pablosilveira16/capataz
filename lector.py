#!/usr/bin/env python3
"""Lo que capataz entiende de un proyecto. Funciones puras y nada más.

Este archivo **no toca la red, no corre git y no escribe nada**: recibe el
texto que `nube.py` trajo de GitHub y lo convierte en lo que la pantalla
dibuja. La separación no es prolijidad, es lo que hace que las dos mitades se
puedan verificar:

  · `lector.py` se ejercita con textos escritos en el arnés, sin red, y las
    cuentas se comparan contra números contados a mano
    → `pruebas/verificar-lector.py`;
  · `nube.py` se ejercita contra **los repositorios de verdad**, que es lo
    único que prueba que un lector de red lee → `pruebas/verificar-nube.py`.

Un lector de red probado sólo contra respuestas grabadas pasa entero con la red
rota. Ése es el arnés vacuo de la regla 2 de `CLAUDE.md`, y ésta es la forma de
no tenerlo.

Verificado, y no leyendo este comentario: `pruebas/verificar-lector.py` § 1
recorre el árbol sintáctico de este archivo y se pone rojo si aparece un
`open(..., "w")`, un `os.remove` o **un solo `subprocess`**.

## Los dos formatos de seguimiento, que es la mitad del problema

ERP 360 y Finca 360 no escriben igual el seguimiento:

  · el archivo se llama distinto (`SEGUIMIENTO.md` vs `Finca360 — Seguimiento.md`)
    → por eso `proyectos.json` lleva el nombre de cada uno;
  · ERP 360 pone el estado en la última celda y la columna se llama `Estado`;
    Finca 360, en sus tablas de *Abierto ahora*, **no tiene columna de estado**:
    el estado lo dice el título de la sección («Depende de Pablo»).

Por eso el estado se saca del **encabezado de la tabla** y no de «la última
celda». Si no hay columna `Estado`, se cae al título de la sección, y sólo con
el mapa que el propio `proyectos.json` declara. Si tampoco alcanza, el punto
queda en `sin estado` y se muestra como tal — no se adivina.

## De dónde sale la cuadrilla, desde el 2026-08-06

De **git**, y no de `panel/agentes.jsonl`. Ese archivo no se versiona a
propósito —tres agentes en tres copias producen tres archivos que no se
fusionan—, así que **nunca llega a la nube**: leerlo de la carpeta local sería
mostrar los agentes que corrieron en esta máquina como si fueran la cuadrilla
entera, que es la mentira exacta que la regla 3 prohíbe. Lo que sí llega a la
nube es la rama que un agente empujó y el autor de sus commits.
El capítulo está en `BITACORA.md`, Tanda 2.
"""
import io
import json
import os
import re
import time

# Los cinco, y no hay otros. El mismo vocabulario cerrado del contrato de
# `SEGUIMIENTO.md`; capataz no agrega ninguno.
ESTADOS = ("pendiente", "en curso", "hecho", "diferido", "descartado")
SIN_ESTADO = "sin estado"

# El orden importa para el matcheo: «en curso» primero, porque es el único de
# dos palabras y porque es el que más urge ver.
_ORDEN_MATCHEO = ("en curso", "pendiente", "hecho", "diferido", "descartado")

# ---------------------------------------------------------------------------
# Prendido o caído: los dos umbrales, y por qué son dos y no uno
# ---------------------------------------------------------------------------
#
# «Una rama que apareció hace diez minutos es un agente trabajando; una que no
# se mueve hace horas es un agente que se cayó.» Entre las dos hay un rato en
# que no se sabe, y **ese rato tiene que verse como lo que es**: un agente
# pensando y uno caído se parecen mucho a los veinte minutos y nada a las seis
# horas. Un umbral solo obliga a llamar «caído» a algo que capataz no sabe.
FRESCO = 45 * 60          # menos que esto: trabajando
TIBIO = 4 * 3600          # entre los dos: dudoso. Más: caído

# Cuántos commits recientes viajan a la pantalla. Con más, el tablero es un log.
ULTIMOS_COMMITS = 12


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


def analizar_seguimiento(texto, secciones=None, hoy=None):
    """Los puntos de un `SEGUIMIENTO.md`, con su estado y de dónde salió.

    Recibe el **texto**, no una ruta: el archivo lo trae `nube.py` de la rama
    principal del repositorio en GitHub. `texto is None` quiere decir «no se
    pudo leer», que es distinto de un archivo vacío y se devuelve distinto.
    """
    if texto is None:
        return {"existe": False, "puntos": [], "repetidos": [],
                "tablas_ignoradas": 0}
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
                "dias": _dias_desde(desde, hoy),
                "bloquea_a_pablo": bool(_PABLO.search(crudo)),
            })
    unicos, repetidos = separar_repetidos(puntos)
    return {"existe": True, "puntos": unicos, "repetidos": repetidos,
            "tablas_ignoradas": ignoradas}


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


def analizar_roles(texto):
    """Los tipos de agente del proyecto, leídos de su `ops/60-roles.md`.

    **Devuelve `None` si el texto no está**, y eso es distinto de una lista
    vacía: quiere decir «no sé qué roles tiene este proyecto». Escribir acá la
    lista de seis de ERP 360 sería la segunda fuente que la regla 1 prohíbe, y
    además sería mentira.
    """
    if texto is None:
        return None
    roles = []
    for linea in texto.splitlines():
        m = _ROL.match(linea.strip())
        if m:
            r = m.group(1).lower()
            if r not in roles:
                roles.append(r)
    return roles


_NOMBRE_ROL = re.compile(r"^([a-záéíóúñ]+)[-_ ]?\d*$")


def rol_de(quien):
    """El rol que se deduce de un nombre de agente: `coder-3` → `coder`.

    Es una **deducción sobre el nombre con que alguien commiteó**, no un dato:
    si el autor es `Pablo Silveira`, acá sale `""` y la pantalla dice «sin rol».
    Eso es correcto y además es información: quiere decir que en ese proyecto
    los agentes no firman con su rol, y entonces la cuadrilla por rol no se
    puede saber desde git.
    """
    m = _NOMBRE_ROL.match((quien or "").strip().lower())
    return m.group(1) if m else ""


def por_rol(cuadrilla, roles):
    """El reparto por rol, **con los ceros**.

    «coder 3» no dice nada; «coder 3 · reviewer 0» es la frase que hace que
    alguien haga algo. Si el proyecto no declara sus roles (`roles is None`) no
    se inventan: se devuelven sólo los que aparecen y `conocidos` queda en
    falso, para que la pantalla lo diga.
    """
    cuenta = {}
    for r in (roles or ()):
        cuenta[r] = 0
    for v in cuadrilla:
        clave = v.get("rol") or "sin rol"
        cuenta[clave] = cuenta.get(clave, 0) + 1
    orden = list(roles or ())
    for k in sorted(cuenta):
        if k not in orden:
            orden.append(k)
    return {"conocidos": roles is not None,
            "reparto": [{"rol": k, "cuantos": cuenta[k]} for k in orden]}


# ----------------------------------------------------------------------------
# 3 · Prendido o caído — lo que Pablo quiere ver
# ----------------------------------------------------------------------------

def estado_rama(rama, ahora=None):
    """Qué dice de un agente el último commit de su rama.

    Cinco desenlaces, y los cinco significan algo distinto:

      `principal`   es `main`. No es la rama de nadie.
      `integrada`   no tiene ni un commit por delante de `main`: lo que traía
                    ya entró. Una rama así **no es un agente caído**, es una
                    rama terminada, y llamarla caída sería inventar un
                    incendio. Es el desenlace más común y el que un umbral
                    solo se equivoca — de las cinco ramas que había el
                    2026-08-06 en los dos repositorios vigilados, tres.
      `trabajando`  se movió hace menos de 45 minutos.
      `dudoso`      hace más de eso y menos de 4 horas. **No se afirma nada**:
                    es el rato en que un agente pensando y uno caído se
                    parecen.
      `caído`       no se mueve hace más de 4 horas y tiene trabajo sin
                    integrar. Eso es lo que hay que mirar.

    Sin fecha del último commit —no debería pasar— el desenlace es `no sé`,
    nunca `trabajando`. Los dos umbrales son `FRESCO` y `TIBIO`.
    """
    ahora = time.time() if ahora is None else ahora
    if rama.get("es_principal"):
        return "principal"
    if rama.get("ts") is None:
        return "no sé"
    if rama.get("commits_adelante") == 0:
        return "integrada"
    edad = ahora - rama["ts"]
    if edad < FRESCO:
        return "trabajando"
    if edad < TIBIO:
        return "dudoso"
    return "caído"


def _hace(ts, ahora):
    if ts is None:
        return None
    return max(0, int(ahora - ts))


def cuadrilla(ramas, puntos, ahora=None):
    """Quién está prendido, quién se cayó y quién tomó un punto sin empujar.

    Sale entera de git, que es lo único que llega a la nube:

      · **una rama viva es un agente.** El autor de su último commit es quien
        trabaja, y `desde` es cuándo se movió por última vez;
      · **un `en curso (fulano)` sin ninguna rama de fulano** es un punto
        tomado del que no llegó nada. Puede ser un agente que trabaja sin
        empujar todavía o uno que se cayó antes del primer commit; capataz no
        puede distinguirlos y por eso dice `sin rama` y no elige.
    """
    ahora = time.time() if ahora is None else ahora
    vivos = []
    con_rama = set()
    for r in ramas or ():
        e = estado_rama(r, ahora)
        if e in ("principal", "integrada"):
            continue
        quien = r.get("autor") or "alguien"
        con_rama.add(quien.lower())
        vivos.append({
            "quien": quien,
            "rol": rol_de(quien),
            "que": r.get("nombre") or "",
            "punto": r.get("punto") or "",
            "asunto": r.get("asunto") or "",
            "estado": e,
            "desde": r.get("ts"),
            "hace_seg": _hace(r.get("ts"), ahora),
        })
    for p in (puntos or ()):
        if p.get("estado") != "en curso":
            continue
        quien = (p.get("quien") or "").strip()
        if not quien or quien.lower() in con_rama:
            continue
        con_rama.add(quien.lower())
        vivos.append({
            "quien": quien,
            "rol": rol_de(quien),
            "que": p.get("id") or "",
            "punto": p.get("id") or "",
            "asunto": p.get("titulo") or "",
            "estado": "sin rama",
            "desde": None,
            "hace_seg": None,
        })
    # El que hace más que no se mueve, primero: es el que hay que mirar.
    return sorted(vivos, key=lambda v: (v["hace_seg"] is None,
                                        -(v["hace_seg"] or 0)))


# ----------------------------------------------------------------------------
# 4 · El CI
# ----------------------------------------------------------------------------

def interpretar_ci(respuesta, motivo=""):
    """Traducir una respuesta de la API de GitHub a un estado de pantalla.

    Está separada de quien va a buscarla a propósito: la parte que decide el
    color se verifica entera sin red, y es la que importa. **Sin respuesta,
    `no sé`. Nunca `verde`.**
    """
    if not respuesta:
        return {"estado": "no sé", "motivo": motivo or "no hubo respuesta",
                "detalle": ""}
    if not isinstance(respuesta, dict):
        return {"estado": "no sé", "motivo": "respuesta ininteligible",
                "detalle": ""}
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
    return {"estado": "no sé", "motivo": motivo or "la respuesta no dice nada",
            "detalle": conclusion}


# ----------------------------------------------------------------------------
# 5 · Un proyecto entero, y la lista de proyectos vigilados
# ----------------------------------------------------------------------------

def normalizar_proyecto(d):
    """Los valores por defecto de una entrada de `proyectos.json`.

    El nombre del archivo de seguimiento **no** tiene defecto obligatorio: es
    justamente lo que cambia entre proyectos, y por eso está en la
    configuración. Los demás sí, porque son la convención del template.
    """
    return {
        "nombre": d.get("nombre") or d.get("repo") or "(sin nombre)",
        "repo": (d.get("repo") or "").strip(),
        "motivo_sin_repo": d.get("motivo_sin_repo") or "",
        "token": d.get("token") or "",
        "seguimiento": d.get("seguimiento") or "SEGUIMIENTO.md",
        "roles": d.get("roles", "ops/60-roles.md"),
        "total_aserciones": d.get("total_aserciones",
                                  "pruebas/total-aserciones.txt"),
        "rama_principal": d.get("rama_principal") or "main",
        "secciones": d.get("secciones") or {},
    }


def leer_proyectos(ruta_json):
    """La lista de proyectos vigilados.

    Desde el 2026-08-06 un proyecto se identifica por `owner/repo` y no por una
    ruta. **La ruta se fue a propósito**: la carpeta local no ve al agente que
    corre en otra máquina, y el día que `ERP360-Template/` desapareció de la
    Mac capataz se quedó ciego con el repositorio entero publicado en GitHub.
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
    return [normalizar_proyecto(d) for d in datos if isinstance(d, dict)]


def mirar(proy, repo, ahora=None):
    """Todo lo que capataz sabe de un proyecto. `repo` es lo que trajo `nube`.

    Es una función pura: mismos argumentos, misma salida, sin red y sin disco.
    Por eso el arnés puede armar el caso del repositorio que no se pudo leer
    sin tener que romper nada.
    """
    proy = normalizar_proyecto(proy)
    ahora = time.time() if ahora is None else ahora
    repo = repo or {}
    archivos = repo.get("archivos") or {}

    def texto(clave):
        d = archivos.get(clave) or {}
        return d.get("texto")

    seg = analizar_seguimiento(texto("seguimiento"), proy["secciones"], ahora)
    puntos = seg["puntos"]
    roles = analizar_roles(texto("roles"))
    ramas = repo.get("ramas") if repo.get("ok") else None
    for r in (ramas or ()):
        r["estado"] = estado_rama(r, ahora)
        r["hace_seg"] = _hace(r.get("ts"), ahora)
    equipo = cuadrilla(ramas, puntos, ahora)
    commits = (repo.get("commits") or [])[:ULTIMOS_COMMITS]
    for c in commits:
        c["hace_seg"] = _hace(c.get("ts"), ahora)
    return {
        "nombre": proy["nombre"],
        "repo": proy["repo"],
        "url": repo.get("url", ""),
        "nube": {
            "ok": bool(repo.get("ok")),
            "error": repo.get("error", ""),
            "rancio": bool(repo.get("rancio")),
            "sin_repo": bool(repo.get("sin_repo")),
            "leido_en": repo.get("leido_en"),
        },
        "seguimiento": {"archivo": proy["seguimiento"],
                        "existe": seg["existe"],
                        "error": ("" if seg["existe"]
                                  else _por_que_falta(proy, repo)),
                        "tablas_ignoradas": seg.get("tablas_ignoradas", 0),
                        "repetidos": seg.get("repetidos", [])},
        "cuenta_abiertos": contar(puntos, solo_abiertos=True),
        "cuenta_total": contar(puntos),
        "en_curso": en_curso(puntos),
        "pendientes_de_pablo": pendientes_de_pablo(puntos),
        "sin_estado": [p for p in puntos if p["estado"] == SIN_ESTADO],
        "roles": roles,
        "cuadrilla": equipo,
        "por_rol": por_rol(equipo, roles),
        "ramas": ramas,
        "commits": commits,
        "ci": interpretar_ci(repo.get("ci"), repo.get("motivo_ci", "")),
    }


def _por_que_falta(proy, repo):
    """Por qué no hay seguimiento — **con el dato que se buscó**.

    Un proyecto mal configurado tiene que verse como un error que dice qué
    buscó, no como un proyecto sin puntos pendientes. Son cosas opuestas y en
    la pantalla se parecen demasiado.
    """
    if repo.get("error"):
        return repo["error"]
    return ("el repositorio se leyó, pero no tiene «%s» en la rama %s de %s"
            % (proy["seguimiento"], proy["rama_principal"],
               repo.get("url") or proy["repo"] or "(sin repo)"))

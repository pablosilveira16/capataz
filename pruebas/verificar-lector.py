#!/usr/bin/env python3
"""El arnés del lector: proyectos de verdad armados en /tmp, no cadenas.

**Por qué así y no leyendo `lector.py`.** La regla 2 de `CLAUDE.md`: leer un
archivo y buscar una cadena no prueba que el código corra. En el proyecto
hermano eso salió mal cuatro veces. Acá cada sección arma un proyecto completo
en `/tmp` —con su seguimiento, su `ops/60-roles.md`, sus marcas y, cuando hace
falta, un repositorio git de verdad con ramas y commits—, corre las funciones
del lector contra él y compara con **números que están escritos acá arriba**.

Los dos formatos que hay que soportar están los dos:

    § 2  con columna `Estado`, como ERP 360
    § 3  SIN columna `Estado`, como Finca 360, donde el estado lo dice la
         sección — y sin el mapa declarado, `sin estado`, que es lo correcto:
         adivinar sería peor.

    python3 pruebas/verificar-lector.py
"""
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(AQUI))
import lector  # noqa: E402

ASER = 0
ROJAS = 0
HOY = time.time()


def af(descripcion, condicion, detalle=""):
    global ASER, ROJAS
    if condicion:
        ASER += 1
    else:
        ROJAS += 1
        print("ROJA  %s%s" % (descripcion, ("  →  %s" % detalle) if detalle else ""))


def igual(descripcion, obtenido, esperado):
    af(descripcion, obtenido == esperado, "obtuve %r, esperaba %r" % (obtenido, esperado))


def escribir(ruta, texto):
    d = os.path.dirname(ruta)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    with io.open(ruta, "w", encoding="utf-8") as f:
        f.write(texto)


def foto(carpeta, saltar=(".git",)):
    """Ruta → (tamaño, sha1) de cada archivo. Lo que compara la § 1."""
    out = {}
    for raiz, dirs, archivos in os.walk(carpeta):
        dirs[:] = [d for d in dirs if d not in saltar]
        for a in archivos:
            p = os.path.join(raiz, a)
            try:
                with open(p, "rb") as f:
                    datos = f.read()
            except OSError:
                continue
            out[os.path.relpath(p, carpeta)] = (len(datos),
                                                hashlib.sha1(datos).hexdigest())
    return out


def git(carpeta, *args):
    return subprocess.run(
        ["git", "-C", carpeta, "-c", "user.name=arnes",
         "-c", "user.email=arnes@capataz.local"] + list(args),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


# ---------------------------------------------------------------------------
# Los dos proyectos de prueba
# ---------------------------------------------------------------------------

# Formato ERP 360: columna `Estado` en cada tabla, última celda.
# Los números que este archivo tiene que producir, contados a mano:
#   abiertos: pendiente 4 (2 de ellos «(Pablo)»), en curso 2, diferido 1,
#             descartado 1, sin estado 1  ·  hecho 0
#   total   : lo de arriba + 2 hechos de la historia
SEG_CON_ESTADO = u"""# Prueba — Seguimiento

## El contrato de este archivo

| | |
|---|---|
| `pendiente` | falta |
| `en curso` | alguien lo hace |
| `hecho` | terminado |
| `diferido` | todavía no |
| `descartado` | no se hace |

## Abierto ahora

### Depende de una decisión (Pablo)

| # | Qué falta | Desde | Estado |
|---|---|---|---|
| D1 | Elegir el motor de base | 2026-07-01 | pendiente (Pablo) |
| D2 | Multi-empresa sí o no | 2026-08-01 | pendiente (Pablo) |

### Se puede hacer sin preguntar

| # | Qué falta | Desde | Estado |
|---|---|---|---|
| T1 | Filtros en el listado | 2026-08-04 | pendiente |
| T2 | Anular un movimiento | 2026-08-05 | pendiente |
| T3 | El tester de navegador | 2026-07-20 | en curso (coder-2) |
| T4 | El backup diario | 2026-08-05 | en curso (reviewer-1) |
| T5 | Una cosa rara | 2026-08-05 | relevado |
| T6 | Algo para después | 2026-08-05 | diferido |
| T7 | Algo que no va | 2026-08-05 | descartado |

---

# Historia por tanda

## Tanda 0

| # | Punto | Estado |
|---|---|---|
| A1 | El esqueleto | **hecho** · `verificar-x.py` 12 aserciones |
| A2 | La portada | **hecho** · `verificar-x.py` 12 aserciones |
"""

# Formato Finca 360: las tablas de *Abierto ahora* NO tienen columna `Estado`.
# El estado lo dice el título de la sección. Sin el mapa declarado en
# `proyectos.json`, los cinco puntos tienen que quedar en `sin estado`.
SEG_SIN_ESTADO = u"""# Otro — Seguimiento

## Abierto ahora

### Depende de Pablo

| # | Qué falta | Desde |
|---|---|---|
| A11 | Ponerle categoría al presupuesto | 2026-08-03 |
| E4 | Borrar la carpeta de restos | 2026-08-03 |

### Se puede hacer sin preguntar

| # | Qué falta | Desde |
|---|---|---|
| N2a | El cambio de estado no genera movimientos | 2026-08-03 |
| N2b | La promoción a mano ignora SIMULADO | 2026-08-03 |

### Decidido, esperando el momento

| # | Qué | Desde | Hasta cuándo |
|---|---|---|---|
| X1 | Unificar las dos cajas | 2026-08-02 | la producción |

---

# Historia por tanda

## Tanda 8

| # | Punto | Estado |
|---|---|---|
| A1 | Copia de seguridad | **hecho** |

## Abierto de tandas anteriores

| # | Punto | Desde | Estado |
|---|---|---|---|
| X1 | Unificar las dos cajas | 2026-08-02 | diferido a producción |
| X9 | El staging rechaza por sesión vencida | 2026-08-03 | **hecho** · anda de nuevo |
"""

ROLES_MD = u"""# Los roles

## Por qué la parte importante es «qué NO hace»

Texto que no es un rol.

# Los tres roles

## coder

Qué hace. Qué NO hace.

## reviewer

Qué hace. Qué NO hace.

## escriba

Qué hace. Qué NO hace.

## Cómo se anuncia el rol

Esto tampoco es un rol.
"""


def armar_con_estado(base):
    escribir(os.path.join(base, "SEGUIMIENTO.md"), SEG_CON_ESTADO)
    escribir(os.path.join(base, "ops", "60-roles.md"), ROLES_MD)
    ahora = HOY
    marcas = [
        # vivo, con rol
        {"ts": ahora - 300, "quien": "coder-2", "rol": "coder",
         "accion": "empieza", "que": "T3 · el tester"},
        # vivo, con otro rol
        {"ts": ahora - 60, "quien": "reviewer-1", "rol": "reviewer",
         "accion": "empieza", "que": "rama t4-backup"},
        # abrió y cerró: no cuenta
        {"ts": ahora - 900, "quien": "escriba-1", "rol": "escriba",
         "accion": "empieza", "que": "cierre de tanda"},
        {"ts": ahora - 800, "quien": "escriba-1", "rol": "escriba",
         "accion": "termina", "que": "cierre de tanda"},
        # vencido: empezó hace más de VENCE_EN y nunca cerró
        {"ts": ahora - lector.VENCE_EN - 120, "quien": "coder-9", "rol": "coder",
         "accion": "empieza", "que": "algo que quedó colgado"},
        # una línea rota, que no puede tirar nada
        None,
    ]
    lineas = []
    for m in marcas:
        lineas.append("{ esto no es json" if m is None
                      else json.dumps(m, ensure_ascii=False))
    escribir(os.path.join(base, "panel", "agentes.jsonl"), "\n".join(lineas) + "\n")


def armar_sin_estado(base):
    escribir(os.path.join(base, u"Otro — Seguimiento.md"), SEG_SIN_ESTADO)
    # Sin ops/60-roles.md y sin panel/: es el caso de Finca 360.


def armar_repo(base):
    """Un repo git de verdad: main con 100 aserciones medidas, dos ramas.

    `t9-baja` deja el total en 97 —tres menos que main— que es exactamente el
    caso que hay que ver: una rama que baja el total es sospechosa aunque esté
    verde. `t8-sin-total` no deja el archivo, y ésa tiene que decir «no sé».
    """
    escribir(os.path.join(base, "SEGUIMIENTO.md"), SEG_CON_ESTADO)
    escribir(os.path.join(base, "pruebas", "total-aserciones.txt"), "100\n")
    git(base, "init", "-q", "-b", "main")
    git(base, "add", "-A")
    git(base, "commit", "-q", "-m", "inicial")
    git(base, "checkout", "-q", "-b", "t9-baja")
    escribir(os.path.join(base, "pruebas", "total-aserciones.txt"), "97\n")
    git(base, "add", "-A")
    git(base, "commit", "-q", "-m", "t9: baja el total")
    git(base, "checkout", "-q", "-b", "t8-sin-total", "main")
    os.remove(os.path.join(base, "pruebas", "total-aserciones.txt"))
    escribir(os.path.join(base, "otro.txt"), "algo\n")
    git(base, "add", "-A")
    git(base, "commit", "-q", "-m", "t8: sin total medido")
    git(base, "checkout", "-q", "main")


TMP = tempfile.mkdtemp(prefix="capataz-arnes-")
CON = os.path.join(TMP, "con-estado")
SIN = os.path.join(TMP, "sin-estado")
REPO = os.path.join(TMP, "repo")
armar_con_estado(CON)
armar_sin_estado(SIN)
armar_repo(REPO)

P_CON = {"nombre": "Con estado", "ruta": CON}
P_SIN = {"nombre": "Sin estado", "ruta": SIN,
         "seguimiento": u"Otro — Seguimiento.md"}
P_SIN_MAPA = dict(P_SIN, secciones={
    "Depende de Pablo": "pendiente (Pablo)",
    "Se puede hacer sin preguntar": "pendiente",
    "Decidido, esperando el momento": "diferido",
})

try:
    # -----------------------------------------------------------------------
    print("\n§ 1 · Capataz sólo lee — CLAUDE.md regla 1")
    # -----------------------------------------------------------------------
    for prohibido in ("fetch", "checkout", "push", "clone", "worktree",
                      "commit", "gc", "reset"):
        try:
            lector._git(REPO, prohibido, "--algo")
            af("«git %s» tendría que estar prohibido en el lector" % prohibido, False)
        except lector.SoloLectura:
            af("«git %s» rechazado" % prohibido, True)

    antes_con, antes_repo = foto(CON), foto(REPO)
    cabeza_antes = git(REPO, "rev-parse", "HEAD").stdout
    sucio_antes = git(REPO, "status", "--porcelain").stdout

    vistas = lector.mirar_todo([P_CON, P_SIN_MAPA, {"nombre": "Repo", "ruta": REPO}])

    igual("mirar_todo devuelve una vista por proyecto", len(vistas), 3)
    af("mirar() no tocó un solo byte del proyecto con estado", foto(CON) == antes_con)
    af("mirar() no tocó un solo byte del repo", foto(REPO) == antes_repo)
    af("mirar() no movió el HEAD del repo",
       git(REPO, "rev-parse", "HEAD").stdout == cabeza_antes)
    af("mirar() no ensució el árbol de trabajo del repo",
       git(REPO, "status", "--porcelain").stdout == sucio_antes)

    # Complemento, no sustituto, de las cinco aserciones de arriba: aquéllas
    # atrapan la escritura cuando ocurre, ésta atrapa la intención antes de
    # que corra. Y va por el árbol sintáctico y no por `grep`: la primera
    # versión buscaba la cadena `open(` y se ponía roja con **el comentario de
    # `lector.py` que dice que no hay ningún `open(..., "w")`**. Un arnés que
    # confunde una frase con una llamada es el arnés vacuo de la regla 2 dado
    # vuelta: no verifica el código, verifica la prosa.
    import ast
    fuente = io.open(os.path.join(os.path.dirname(AQUI), "lector.py"),
                     encoding="utf-8").read()
    arbol = ast.parse(fuente)
    escrituras = []
    PROHIBIDAS = ("remove", "unlink", "rmdir", "makedirs", "mkdir", "rename",
                  "rmtree", "chmod", "write_text", "symlink")
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.Call):
            continue
        f = nodo.func
        nombre = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
        if nombre in ("open",):
            modo = ""
            if len(nodo.args) > 1 and isinstance(nodo.args[1], ast.Constant):
                modo = str(nodo.args[1].value)
            for kw in nodo.keywords:
                if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                    modo = str(kw.value.value)
            if any(c in modo for c in "wax+"):
                escrituras.append("línea %d: open(..., %r)" % (nodo.lineno, modo))
        elif nombre in PROHIBIDAS:
            escrituras.append("línea %d: %s()" % (nodo.lineno, nombre))
    af("lector.py no abre nada para escribir ni borra nada (árbol sintáctico)",
       not escrituras, escrituras[:3])
    llamadas = [n.lineno for n in ast.walk(arbol)
                if isinstance(n, ast.Call)
                and isinstance(n.func, ast.Attribute) and n.func.attr == "run"]
    af("el único subprocess.run del lector está adentro de _git(), que filtra",
       len(llamadas) == 1, llamadas)

    # -----------------------------------------------------------------------
    print("§ 2 · Seguimiento CON columna Estado (formato ERP 360)")
    # -----------------------------------------------------------------------
    v = vistas[0]
    igual("los cinco estados están, con los ceros",
          sorted(v["cuenta_abiertos"]),
          sorted(list(lector.ESTADOS) + [lector.SIN_ESTADO]))
    igual("pendiente abiertos", v["cuenta_abiertos"]["pendiente"], 4)
    igual("en curso abiertos", v["cuenta_abiertos"]["en curso"], 2)
    igual("hecho abiertos (los hechos viven en la historia)",
          v["cuenta_abiertos"]["hecho"], 0)
    igual("diferido abiertos", v["cuenta_abiertos"]["diferido"], 1)
    igual("descartado abiertos", v["cuenta_abiertos"]["descartado"], 1)
    igual("un estado inventado cae en «sin estado», no en pendiente",
          v["cuenta_abiertos"][lector.SIN_ESTADO], 1)
    igual("el punto del estado inventado es T5",
          [p["id"] for p in v["sin_estado"]], ["T5"])
    igual("hecho en toda la historia", v["cuenta_total"]["hecho"], 2)

    igual("los pendiente (Pablo) van separados",
          [p["id"] for p in v["pendientes_de_pablo"]], ["D1", "D2"])
    af("un pendiente sin (Pablo) no entra ahí",
       all(p["id"] not in ("T1", "T2") for p in v["pendientes_de_pablo"]))

    ec = v["en_curso"]
    igual("los dos en curso, el más viejo primero",
          [p["id"] for p in ec], ["T3", "T4"])
    igual("el en curso dice quién lo tiene", [p["quien"] for p in ec],
          ["coder-2", "reviewer-1"])
    af("el en curso dice desde cuándo", ec[0]["dias"] is not None and ec[0]["dias"] > 0,
       ec[0]["dias"])
    af("y el más viejo es más viejo", ec[0]["dias"] > ec[1]["dias"])

    igual("la tabla del vocabulario de estados no se cuenta como puntos",
          v["seguimiento"]["tablas_ignoradas"], 1)

    # -----------------------------------------------------------------------
    print("§ 3 · Seguimiento SIN columna Estado (formato Finca 360)")
    # -----------------------------------------------------------------------
    crudo = lector.leer_seguimiento(
        os.path.join(SIN, u"Otro — Seguimiento.md"), secciones=None)
    abiertos_crudos = lector.contar(crudo["puntos"], solo_abiertos=True)
    igual("sin el mapa declarado, los cinco abiertos quedan «sin estado»",
          abiertos_crudos[lector.SIN_ESTADO], 5)
    igual("y NO se los adivina como pendiente", abiertos_crudos["pendiente"], 0)

    v2 = vistas[1]
    igual("con el mapa, la sección «Depende de Pablo» da pendiente (Pablo)",
          [p["id"] for p in v2["pendientes_de_pablo"]], ["A11", "E4"])
    igual("«Se puede hacer sin preguntar» da pendiente",
          v2["cuenta_abiertos"]["pendiente"], 4)
    igual("«Decidido, esperando el momento» da diferido",
          v2["cuenta_abiertos"]["diferido"], 1)
    igual("con el mapa no queda ningún «sin estado»",
          v2["cuenta_abiertos"][lector.SIN_ESTADO], 0)
    af("el estado sacado de la sección se marca como tal",
       all(p["origen_estado"] == "seccion"
           for p in v2["pendientes_de_pablo"]))

    ids = [p["id"] for p in crudo["puntos"]]
    af("«Abierto de tandas anteriores» no se cuenta como historia: X9 está abierto",
       "X9" in ids)
    igual("X9 está abierto y hecho",
          [p["historia"] for p in crudo["puntos"] if p["id"] == "X9"], [False])
    igual("un punto repetido se cuenta una sola vez", ids.count("X1"), 1)
    igual("y la repetición con OTRO estado se guarda para mostrarla",
          [(r["id"], r["discrepa"]) for r in crudo["repetidos"]], [("X1", True)])

    # -----------------------------------------------------------------------
    print("§ 4 · Los roles del proyecto y la cuadrilla")
    # -----------------------------------------------------------------------
    igual("los roles salen de ops/60-roles.md del proyecto, no de una lista de acá",
          v["roles"], ["coder", "reviewer", "escriba"])
    af("un proyecto sin ops/60-roles.md devuelve None, no una lista vacía",
       lector.leer_roles(os.path.join(SIN, "ops", "60-roles.md")) is None)
    igual("y en la vista eso queda como «no sé»", v2["roles"], None)
    af("la pantalla puede distinguirlo", v2["por_rol"]["conocidos"] is False)

    igual("la cuadrilla: sólo los vivos",
          sorted(a["quien"] for a in v["cuadrilla"]), ["coder-2", "reviewer-1"])
    af("un «empieza» seguido de «termina» no cuenta",
       all(a["quien"] != "escriba-1" for a in v["cuadrilla"]))
    af("un «empieza» vencido no cuenta — un agente caído no trabaja para siempre",
       all(a["quien"] != "coder-9" for a in v["cuadrilla"]))
    af("una línea rota del jsonl no tira el lector", len(v["cuadrilla"]) == 2)
    igual("la cuadrilla dice el rol y hace cuánto",
          [(a["rol"], a["hace_min"]) for a in v["cuadrilla"]],
          [("coder", 5), ("reviewer", 1)])

    reparto = dict((r["rol"], r["cuantos"]) for r in v["por_rol"]["reparto"])
    igual("el reparto trae los TRES roles del proyecto, con los ceros",
          sorted(reparto), ["coder", "escriba", "reviewer"])
    igual("coder 1", reparto["coder"], 1)
    igual("reviewer 1", reparto["reviewer"], 1)
    igual("escriba 0 — el cero es el punto", reparto["escriba"], 0)

    # -----------------------------------------------------------------------
    print("§ 5 · Ramas, totales y el «no sé» — CLAUDE.md regla 3")
    # -----------------------------------------------------------------------
    v3 = vistas[2]
    ramas = dict((r["nombre"], r) for r in v3["ramas"])
    igual("las tres ramas del repo", sorted(ramas), ["main", "t8-sin-total", "t9-baja"])
    igual("main trae su total medido", ramas["main"]["total"], 100)
    igual("la rama que baja el total lo dice", ramas["t9-baja"]["total"], 97)
    igual("y lo dice comparado con main", ramas["t9-baja"]["delta"], -3)
    igual("la rama sabe de qué punto es", ramas["t9-baja"]["punto"], "T9")
    igual("y cuántos commits tiene adelante de main",
          ramas["t9-baja"]["commits_adelante"], 1)

    af("una rama sin total medido dice «no sé», no cero",
       ramas["t8-sin-total"]["total"] is None, ramas["t8-sin-total"]["total"])
    af("y no inventa un delta", ramas["t8-sin-total"]["delta"] is None)
    af("con el motivo escrito", bool(ramas["t8-sin-total"]["motivo_sin_total"]))
    # El corolario de la regla 3: un aviso que sale siempre enseña a ignorarlo.
    af("y ese motivo NO sale cuando el total sí se sabe",
       ramas["t9-baja"]["motivo_sin_total"] == "")

    af("un proyecto que no es repo git da «no sé» en ramas, no una lista vacía",
       v2["ramas"] is None, v2["ramas"])

    igual("sin respuesta del CI, «no sé»",
          lector.interpretar_ci(None)["estado"], "no sé")
    igual("y con motivo escrito", bool(lector.interpretar_ci(None)["motivo"]), True)
    igual("una corrida exitosa sí es verde",
          lector.interpretar_ci({"status": "completed",
                                 "conclusion": "success"})["estado"], "verde")
    igual("una fallida es roja",
          lector.interpretar_ci({"status": "completed",
                                 "conclusion": "failure"})["estado"], "rojo")
    igual("una que está corriendo no es ni verde ni roja",
          lector.interpretar_ci({"status": "in_progress"})["estado"], "corriendo")
    igual("una cancelada no se cuenta como verde",
          lector.interpretar_ci({"status": "completed",
                                 "conclusion": "cancelled"})["estado"], "no sé")
    for vista in vistas:
        af("hoy el CI de %s es «no sé» y jamás verde" % vista["nombre"],
           vista["ci"]["estado"] == "no sé", vista["ci"]["estado"])

    # -----------------------------------------------------------------------
    print("§ 6 · La configuración de proyectos vigilados")
    # -----------------------------------------------------------------------
    cfg = os.path.join(TMP, "proyectos.json")
    escribir(cfg, json.dumps({"proyectos": [
        {"nombre": "Relativo", "ruta": "con-estado"},
        {"nombre": "Otro nombre de archivo", "ruta": "sin-estado",
         "seguimiento": u"Otro — Seguimiento.md"},
    ]}, ensure_ascii=False))
    ps = lector.leer_proyectos(cfg)
    igual("dos proyectos vigilados", len(ps), 2)
    igual("una ruta relativa se resuelve contra el propio proyectos.json",
          os.path.realpath(ps[0]["ruta"]), os.path.realpath(CON))
    af("cada proyecto declara el nombre de SU archivo de seguimiento",
       lector.mirar(ps[1])["seguimiento"]["existe"], "no lo encontró")
    igual("y el que no lo declara usa SEGUIMIENTO.md",
          ps[0]["seguimiento"], "SEGUIMIENTO.md")
    af("un proyectos.json que no existe no tira nada",
       lector.leer_proyectos(os.path.join(TMP, "no-existe.json")) == [])
    af("una ruta que no existe tampoco",
       lector.mirar({"nombre": "fantasma", "ruta": "/no/existe"})
       ["seguimiento"]["existe"] is False)

finally:
    shutil.rmtree(TMP, ignore_errors=True)

print("\nASERCIONES: %d\nROJAS: %d" % (ASER, ROJAS))
sys.exit(1 if ROJAS else 0)

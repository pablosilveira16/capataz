#!/usr/bin/env python3
"""El arnés del lector: la mitad que entiende, sin red.

**Qué verifica esto y qué NO.** `lector.py` es una pila de funciones puras:
recibe el texto que `nube.py` bajó de GitHub y devuelve lo que la pantalla
dibuja. Acá se lo ejercita con textos escritos abajo y se comparan las cuentas
contra **números contados a mano**, que están escritos al lado de cada texto.

Lo que este arnés **no** puede afirmar es que capataz lea GitHub: eso se prueba
contra los repositorios de verdad y vive en `pruebas/verificar-nube.py`. La
división es a propósito y es la regla 2 de `CLAUDE.md`: un lector de red probado
sólo contra respuestas escritas a mano pasa entero con la red rota.

Los dos formatos de seguimiento están los dos:

    § 2  con columna `Estado`, como ERP 360
    § 3  SIN columna `Estado`, como Finca 360, donde el estado lo dice la
         sección — y sin el mapa declarado, `sin estado`, que es lo correcto:
         adivinar sería peor.

    python3 pruebas/verificar-lector.py
"""
import ast
import io
import json
import os
import sys
import tempfile
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, RAIZ)
import lector  # noqa: E402
import nube    # noqa: E402

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


# ---------------------------------------------------------------------------
# Los dos seguimientos de prueba
# ---------------------------------------------------------------------------

# Formato ERP 360: columna `Estado` en cada tabla, última celda.
# Los números que este texto tiene que producir, contados a mano:
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

MAPA_SECCIONES = {
    "Depende de Pablo": "pendiente (Pablo)",
    "Se puede hacer sin preguntar": "pendiente",
    "Decidido, esperando el momento": "diferido",
}


def repo_falso(seguimiento=SEG_CON_ESTADO, roles=ROLES_MD, ramas=None,
               commits=None, ok=True, error="", **extra):
    """La forma exacta que `nube.leer()` devuelve, armada a mano.

    **Esto no prueba que capataz lea GitHub** y no pretende hacerlo: prueba que
    dado lo que GitHub contesta, las cuentas salen. Que la forma sea de verdad
    ésta lo verifica `pruebas/verificar-nube.py` § 3, contra los repositorios
    reales — es la aserción que evita que estas dos páginas se conviertan en un
    arnés vacuo que verifica un diccionario inventado.
    """
    d = {
        "repo": "quien/que", "url": "https://github.com/quien/que",
        "ok": ok, "error": error, "rancio": False, "leido_en": HOY,
        "espejo": "/tmp/espejo.git", "principal": "main",
        "archivos": {"seguimiento": {"archivo": "SEGUIMIENTO.md",
                                     "texto": seguimiento},
                     "roles": {"archivo": "ops/60-roles.md", "texto": roles}},
        "ramas": ramas if ramas is not None else [],
        "commits": commits or [],
    }
    d.update(extra)
    return d


def rama(nombre, hace_seg, adelante=1, atras=0, autor="coder-1", total=None,
         principal=False, asunto="algo"):
    return {"nombre": nombre, "es_principal": principal,
            "punto": nombre.split("-")[0].upper(),
            "sha": "abc1234", "ts": HOY - hace_seg, "autor": autor,
            "asunto": asunto, "commits_adelante": adelante,
            "commits_atras": atras, "total": total, "total_main": 100,
            "delta": None if total is None else total - 100,
            "motivo_sin_total": "" if total is not None else nube.MOTIVO_TOTAL}


P_CON = {"nombre": "Con estado", "repo": "quien/que"}
P_SIN = {"nombre": "Sin estado", "repo": "otro/cosa",
         "seguimiento": u"Otro — Seguimiento.md"}
P_SIN_MAPA = dict(P_SIN, secciones=MAPA_SECCIONES)

# -----------------------------------------------------------------------
print("\n§ 1 · Capataz sólo lee, y el lector ni siquiera sale de su proceso")
# -----------------------------------------------------------------------
#
# Va por el árbol sintáctico y no por `grep`: la primera versión de esta
# comprobación buscaba la cadena `open(` y se ponía roja con **el comentario de
# `lector.py` que dice que no hay ningún `open(..., "w")`**. Un arnés que
# confunde una frase con una llamada es el arnés vacuo dado vuelta: no verifica
# el código, verifica la prosa.
FUENTE = io.open(os.path.join(RAIZ, "lector.py"), encoding="utf-8").read()
ARBOL = ast.parse(FUENTE)

escrituras = []
PROHIBIDAS = ("remove", "unlink", "rmdir", "makedirs", "mkdir", "rename",
              "rmtree", "chmod", "write_text", "symlink", "run", "Popen",
              "system", "urlopen")
for nodo in ast.walk(ARBOL):
    if not isinstance(nodo, ast.Call):
        continue
    f = nodo.func
    nombre = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
    if nombre == "open":
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
af("lector.py no abre nada para escribir, no borra nada y no corre nada",
   not escrituras, escrituras[:3])

# Y la compuerta que se movió en esta tanda: antes el lector tenía UN
# `subprocess.run` adentro de un `_git()` con lista blanca. Ahora **no tiene
# ninguno**, porque salir a buscar el dato es trabajo de `nube.py`. Es una
# invariante más fuerte y más fácil de mirar: el lector no puede tocar nada
# de nadie porque no tiene con qué.
importados = set()
for nodo in ast.walk(ARBOL):
    if isinstance(nodo, ast.Import):
        for a in nodo.names:
            importados.add(a.name.split(".")[0])
    elif isinstance(nodo, ast.ImportFrom) and nodo.module:
        importados.add(nodo.module.split(".")[0])
AFUERA = {"subprocess", "socket", "urllib", "http", "shutil", "tempfile",
          "requests", "nube"}
af("lector.py no importa nada que salga del proceso ni que escriba",
   not (importados & AFUERA), sorted(importados & AFUERA))
af("y sí importa lo que necesita para leer texto", "re" in importados)

# Pureza, ejecutada: dos llamadas con los mismos argumentos dan lo mismo, y
# ninguna de las dos deja un archivo nuevo en la carpeta del proyecto.
tmp = tempfile.mkdtemp(prefix="capataz-lector-")
antes = sorted(os.listdir(RAIZ))
uno = lector.mirar(P_CON, repo_falso(), HOY)
dos = lector.mirar(P_CON, repo_falso(), HOY)
igual("mirar() es pura: dos veces lo mismo da lo mismo",
      json.dumps(uno, sort_keys=True, default=str),
      json.dumps(dos, sort_keys=True, default=str))
igual("y no creó ningún archivo en la carpeta del proyecto",
      sorted(os.listdir(RAIZ)), antes)
igual("ni en la carpeta temporal que se le puso al lado", os.listdir(tmp), [])
os.rmdir(tmp)

# -----------------------------------------------------------------------
print("§ 2 · Seguimiento CON columna Estado (formato ERP 360)")
# -----------------------------------------------------------------------
v = uno
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
crudo = lector.analizar_seguimiento(SEG_SIN_ESTADO, None, HOY)
abiertos_crudos = lector.contar(crudo["puntos"], solo_abiertos=True)
igual("sin el mapa declarado, los cinco abiertos quedan «sin estado»",
      abiertos_crudos[lector.SIN_ESTADO], 5)
igual("y NO se los adivina como pendiente", abiertos_crudos["pendiente"], 0)

v2 = lector.mirar(P_SIN_MAPA, repo_falso(seguimiento=SEG_SIN_ESTADO,
                                         roles=None), HOY)
igual("con el mapa, la sección «Depende de Pablo» da pendiente (Pablo)",
      [p["id"] for p in v2["pendientes_de_pablo"]], ["A11", "E4"])
igual("«Se puede hacer sin preguntar» da pendiente",
      v2["cuenta_abiertos"]["pendiente"], 4)
igual("«Decidido, esperando el momento» da diferido",
      v2["cuenta_abiertos"]["diferido"], 1)
igual("con el mapa no queda ningún «sin estado»",
      v2["cuenta_abiertos"][lector.SIN_ESTADO], 0)
af("el estado sacado de la sección se marca como tal",
   all(p["origen_estado"] == "seccion" for p in v2["pendientes_de_pablo"]))

ids = [p["id"] for p in crudo["puntos"]]
af("«Abierto de tandas anteriores» no se cuenta como historia: X9 está abierto",
   "X9" in ids)
igual("X9 está abierto y hecho",
      [p["historia"] for p in crudo["puntos"] if p["id"] == "X9"], [False])
igual("un punto repetido se cuenta una sola vez", ids.count("X1"), 1)
igual("y la repetición con OTRO estado se guarda para mostrarla",
      [(r["id"], r["discrepa"]) for r in crudo["repetidos"]], [("X1", True)])

# -----------------------------------------------------------------------
print("§ 4 · Prendido o caído — lo que motiva la tanda")
# -----------------------------------------------------------------------
#
# Los cinco desenlaces, uno por uno, con la edad escrita al lado. Los dos que
# se equivocan si uno pone un solo umbral son `integrada` —una rama terminada
# no es un agente caído— y `dudoso` —el rato en que capataz no sabe—.
RAMAS = [
    rama("main", 60, adelante=0, principal=True, autor="coder-1", total=100),
    rama("t1-recien", 10 * 60, autor="coder-1", total=105),
    rama("t2-pensando", 2 * 3600, autor="coder-2", total=100),
    rama("t3-caida", 30 * 3600, autor="coder-3", total=97),
    rama("t4-integrada", 40 * 3600, adelante=0, autor="escriba-1", total=100),
]
por_nombre = {}
for r in RAMAS:
    por_nombre[r["nombre"]] = lector.estado_rama(dict(r), HOY)
igual("main es la principal, no la rama de nadie",
      por_nombre["main"], "principal")
igual("una rama de hace 10 minutos es un agente trabajando",
      por_nombre["t1-recien"], "trabajando")
igual("una de hace 2 horas es dudoso: capataz no afirma nada",
      por_nombre["t2-pensando"], "dudoso")
igual("una de hace 30 horas con trabajo sin integrar es un agente caído",
      por_nombre["t3-caida"], "caído")
igual("y una vieja SIN nada por delante de main está integrada, no caída",
      por_nombre["t4-integrada"], "integrada")
igual("sin fecha del último commit, «no sé» — nunca «trabajando»",
      lector.estado_rama({"ts": None, "commits_adelante": 3}, HOY), "no sé")

# Justo a los dos lados de cada umbral, que es donde un `<` de más se esconde.
af("un segundo antes de FRESCO todavía es «trabajando»",
   lector.estado_rama({"ts": HOY - lector.FRESCO + 1, "commits_adelante": 1},
                      HOY) == "trabajando")
af("un segundo después ya es «dudoso»",
   lector.estado_rama({"ts": HOY - lector.FRESCO - 1, "commits_adelante": 1},
                      HOY) == "dudoso")
af("un segundo antes de TIBIO todavía es «dudoso»",
   lector.estado_rama({"ts": HOY - lector.TIBIO + 1, "commits_adelante": 1},
                      HOY) == "dudoso")
af("un segundo después ya es «caído»",
   lector.estado_rama({"ts": HOY - lector.TIBIO - 1, "commits_adelante": 1},
                      HOY) == "caído")

vista = lector.mirar(P_CON, repo_falso(ramas=[dict(r) for r in RAMAS]), HOY)
equipo = dict((a["quien"], a) for a in vista["cuadrilla"])
igual("la cuadrilla sale de las ramas vivas, y sólo de ésas",
      sorted(equipo), ["coder-1", "coder-2", "coder-3", "reviewer-1"])
af("una rama integrada no pone a nadie en la cuadrilla",
   "escriba-1" not in equipo)
igual("el que hace más que no se mueve va primero",
      vista["cuadrilla"][0]["quien"], "coder-3")
igual("y se ve en qué estado está cada uno",
      [(a["quien"], a["estado"]) for a in vista["cuadrilla"]],
      [("coder-3", "caído"), ("coder-2", "dudoso"), ("coder-1", "trabajando"),
       ("reviewer-1", "sin rama")])
igual("un «en curso (reviewer-1)» sin ninguna rama se ve como «sin rama»",
      equipo["reviewer-1"]["estado"], "sin rama")
af("y no se lo llama caído, que sería afirmar algo que no se sabe",
   equipo["reviewer-1"]["estado"] != "caído")
af("un «en curso» de alguien que SÍ tiene rama no se duplica",
   len([a for a in vista["cuadrilla"] if a["quien"] == "coder-2"]) == 1)

igual("el rol se deduce del nombre con que commiteó", lector.rol_de("coder-3"),
      "coder")
igual("y de un nombre de persona no se deduce ninguno",
      lector.rol_de("Pablo Silveira"), "")

# -----------------------------------------------------------------------
print("§ 4b · Los agentes de TODOS los proyectos — la vista primaria")
# -----------------------------------------------------------------------
#
# Lo que se mira no es «cómo va el proyecto X» sino quién trabaja ahora, y un
# agente no se busca adentro de la tarjeta del proyecto que le tocó.
OTRAS = [
    rama("main", 60, adelante=0, principal=True, autor="coder-1", total=100),
    rama("t9-recien", 30, autor="coder-8", total=100),
]
v_uno = lector.mirar(P_CON, repo_falso(ramas=[dict(r) for r in RAMAS]), HOY)
v_dos = lector.mirar(dict(P_CON, nombre="El otro", repo="otro/repo"),
                     repo_falso(ramas=[dict(r) for r in OTRAS]), HOY)
todos = lector.agentes([v_uno, v_dos], HOY)

igual("la lista junta la cuadrilla de los dos proyectos",
      sorted(a["quien"] for a in todos),
      ["coder-1", "coder-2", "coder-2", "coder-3", "coder-8",
       "reviewer-1", "reviewer-1"])
af("el mismo nombre en dos proyectos son DOS renglones y no uno: son dos "
   "trabajos distintos, y unirlos escondería uno de los dos",
   len([a for a in todos if a["quien"] == "coder-2"]) == 2)
af("y se distinguen por el proyecto, que es lo que la pantalla usa de clave",
   len(set(a["proyecto"] for a in todos if a["quien"] == "coder-2")) == 2)
af("y cada agente dice de qué proyecto es, o no se sabe a quién ir a buscar",
   all(a["proyecto"] for a in todos),
   [(a["quien"], a["proyecto"]) for a in todos])
igual("el que se movió recién va PRIMERO — al revés que la cuadrilla de un "
      "proyecto, que pone primero al que hace más que no se mueve",
      todos[0]["quien"], "coder-8")
igual("y la cuadrilla de cada proyecto conserva su propio orden",
      v_uno["cuadrilla"][0]["quien"], "coder-3")
igual("el que no tiene rama va último: no tiene con qué ordenarse",
      todos[-1]["estado"], "sin rama")
af("cada agente lleva el sha de su rama, que es con lo que la pantalla ve que "
   "se despertó — sin esto el aviso se apoyaría en el reloj y avisaría solo",
   all(a["sha"] for a in todos if a["estado"] != "sin rama"),
   [(a["quien"], a["sha"]) for a in todos])
af("y el que no tiene rama no inventa un sha", todos[-1]["sha"] == "")
af("sin proyectos, la lista está vacía y no explota",
   lector.agentes([], HOY) == [] and lector.agentes(None, HOY) == [])

# -----------------------------------------------------------------------
print("§ 5 · Los roles del proyecto y el reparto")
# -----------------------------------------------------------------------
igual("los roles salen del ops/60-roles.md del repositorio, no de una lista de acá",
      vista["roles"], ["coder", "reviewer", "escriba"])
af("un repositorio sin ese archivo devuelve None, no una lista vacía",
   lector.analizar_roles(None) is None)
igual("y en la vista eso queda como «no sé»", v2["roles"], None)
af("la pantalla puede distinguirlo", v2["por_rol"]["conocidos"] is False)

reparto = dict((r["rol"], r["cuantos"]) for r in vista["por_rol"]["reparto"])
igual("el reparto trae los TRES roles del proyecto, con los ceros",
      sorted(reparto), ["coder", "escriba", "reviewer"])
igual("coder 3", reparto["coder"], 3)
igual("reviewer 1", reparto["reviewer"], 1)
igual("escriba 0 — el cero es el punto", reparto["escriba"], 0)

# -----------------------------------------------------------------------
print("§ 6 · Ramas, totales y el «no sé» — CLAUDE.md regla 3")
# -----------------------------------------------------------------------
ramas = dict((r["nombre"], r) for r in vista["ramas"])
igual("las cinco ramas", len(ramas), 5)
igual("main trae su total medido", ramas["main"]["total"], 100)
igual("la rama que baja el total lo dice", ramas["t3-caida"]["total"], 97)
igual("y lo dice comparado con main", ramas["t3-caida"]["delta"], -3)
igual("la rama sabe de qué punto es", ramas["t3-caida"]["punto"], "T3")

sin_total = lector.mirar(
    P_CON, repo_falso(ramas=[rama("t8-sin-total", 60, autor="coder-8")]), HOY)
r8 = sin_total["ramas"][0]
af("una rama sin total medido dice «no sé», no cero", r8["total"] is None,
   r8["total"])
af("y no inventa un delta", r8["delta"] is None)
af("con el motivo escrito", bool(r8["motivo_sin_total"]))
# El corolario de la regla 3: un aviso que sale siempre enseña a ignorarlo.
af("y ese motivo NO sale cuando el total sí se sabe",
   ramas["t3-caida"]["motivo_sin_total"] == "")

# Un repositorio que no se pudo leer: «no sé» en todo, y el porqué al lado.
roto = lector.mirar(
    {"nombre": "Roto", "repo": "quien/no-existe"},
    repo_falso(seguimiento=None, roles=None, ok=False,
               error="no existe github.com/quien/no-existe, o el token no lo alcanza"),
    HOY)
af("un repositorio que no se pudo leer da «no sé» en ramas, no lista vacía",
   roto["ramas"] is None, roto["ramas"])
af("y no dice que no hay puntos: dice que no pudo",
   roto["seguimiento"]["existe"] is False)
af("con la causa adentro, que es lo único accionable",
   "no existe github.com/quien/no-existe" in roto["seguimiento"]["error"],
   roto["seguimiento"]["error"])
igual("y su cuadrilla es vacía porque no hay ramas que mirar",
      roto["cuadrilla"], [])

# Un proyecto declarado sin repositorio —Finca 360— no es lo mismo que uno roto.
sin_repo = lector.mirar(
    {"nombre": "Finca 360", "repo": None, "motivo_sin_repo": "no está publicado"},
    {"ok": False, "sin_repo": True, "error": "no está publicado",
     "archivos": {}, "ramas": [], "commits": []}, HOY)
af("un proyecto sin repositorio se marca como tal, no como error de red",
   sin_repo["nube"]["sin_repo"] is True)
af("y trae el motivo declarado en proyectos.json",
   sin_repo["nube"]["error"] == "no está publicado")

igual("sin respuesta del CI, «no sé»",
      lector.interpretar_ci(None)["estado"], "no sé")
igual("y con motivo escrito",
      bool(lector.interpretar_ci(None, "porque sí")["motivo"]), True)
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
for nombre, vv in (("con estado", v), ("sin estado", v2), ("roto", roto)):
    af("sin que nadie le pase una respuesta, el CI de «%s» es «no sé»" % nombre,
       vv["ci"]["estado"] == "no sé", vv["ci"]["estado"])

# -----------------------------------------------------------------------
print("§ 7 · La configuración de proyectos vigilados")
# -----------------------------------------------------------------------
tmp = tempfile.mkdtemp(prefix="capataz-cfg-")
cfg = os.path.join(tmp, "proyectos.json")
with io.open(cfg, "w", encoding="utf-8") as f:
    f.write(json.dumps({"proyectos": [
        {"nombre": "Uno", "repo": "pablosilveira16/erp360"},
        {"nombre": "Otro nombre de archivo", "repo": "pablosilveira16/capataz",
         "seguimiento": u"Otro — Seguimiento.md", "token": "otro.token"},
        {"nombre": "Sin publicar", "repo": None,
         "motivo_sin_repo": "todavía no está en GitHub"},
    ]}, ensure_ascii=False))
ps = lector.leer_proyectos(cfg)
igual("tres proyectos vigilados", len(ps), 3)
igual("un proyecto se identifica por owner/repo y no por una ruta",
      ps[0]["repo"], "pablosilveira16/erp360")
af("ninguna entrada conserva el campo «ruta», que se fue en esta tanda",
   all("ruta" not in p for p in ps), [sorted(p) for p in ps[:1]])
igual("cada proyecto declara el nombre de SU archivo de seguimiento",
      ps[1]["seguimiento"], u"Otro — Seguimiento.md")
igual("y el que no lo declara usa SEGUIMIENTO.md",
      ps[0]["seguimiento"], "SEGUIMIENTO.md")
igual("cada proyecto declara SU token — un token, un repositorio",
      ps[1]["token"], "otro.token")
igual("y el que declara repo nulo lo deja vacío, con su motivo",
      (ps[2]["repo"], ps[2]["motivo_sin_repo"]),
      ("", "todavía no está en GitHub"))
af("un proyectos.json que no existe no tira nada",
   lector.leer_proyectos(os.path.join(tmp, "no-existe.json")) == [])
os.remove(cfg)
os.rmdir(tmp)

# Y el `proyectos.json` de verdad, que es el que corre: si alguien deja una
# ruta donde va un `owner/repo`, esto se pone rojo antes que la pantalla.
reales = lector.leer_proyectos(os.path.join(RAIZ, "proyectos.json"))
af("el proyectos.json versionado tiene al menos dos proyectos con repo",
   len([p for p in reales if p["repo"]]) >= 2, len(reales))
malos = [p["nombre"] for p in reales
         if p["repo"] and ("/" not in p["repo"] or p["repo"].startswith("."))]
af("y ninguno declara una ruta donde va un owner/repo", not malos, malos)
# Esta aserción decía «todos los que no tienen repo declaran por qué», y el
# 2026-08-06 —al publicar Finca 360— esa lista quedó **vacía**: `all([])` es
# `True`, así que pasaba siempre, seguía sumando al total y no verificaba nada.
# Es el caso vacuo del § 2 de `CLAUDE.md`, aparecido no por escribir mal el
# arnés sino por **arreglar el dato**, que es la forma más difícil de verla.
# Ahora habla de los tres proyectos y no de un subconjunto que puede vaciarse; y
# `reales and` es lo que impide que sobreviva a un `proyectos.json` vacío.
mudos = [p["nombre"] for p in reales if not p["repo"] and not p["motivo_sin_repo"]]
af("cada proyecto declara un repo o declara por qué no lo tiene (%d proyectos)"
   % len(reales), reales and not mudos, mudos)

print("\nASERCIONES: %d\nROJAS: %d" % (ASER, ROJAS))
sys.exit(1 if ROJAS else 0)

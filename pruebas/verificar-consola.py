"""Arnés de `consola.py` — el lector de `claude agents --json`.

Lo que se verifica, y por qué cada sección no es vacua:

    § 1  **Capataz no lanza agentes**, y acá eso es código y no una promesa: la
         compuerta ejercitada con cada bandera que despacha, más un recuento por
         AST de que hay **un solo `subprocess`** en todo el archivo y que está
         adentro de `_correr`. Igual que `verificar-nube.py` con `_git`.
    § 2  Contra el **CLI de verdad** de esta máquina. Es la lección de `nube.py`
         puesta acá: un lector probado sólo contra respuestas escritas a mano
         pasa entero con el CLI cambiado, desinstalado o mudo. Si `claude` no
         está, esto se pone **rojo** y no saltea.
    § 3  Los seis `state` medidos, y que uno que nadie vio se diga «no sé» **con
         la palabra cruda**, nunca pintado del color de al lado.
    § 4  `cotejar`, con los dos lados: que **encuentre** un desacuerdo de verdad
         y que **no invente** los dos que están medidos y explicados. Una lista
         que siempre sale vacía no verifica nada; una que siempre sale llena es
         el aviso que enseña a ignorarse.
    § 5  Lo que falla, falla diciendo **qué corrió y qué pasó** — y nunca «cero
         agentes», que es la regla 3.
    § 6  No guarda estado propio: se tira lo cacheado, se relee y sale lo mismo.

    python3 pruebas/verificar-consola.py
"""
import ast
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, RAIZ)
import consola  # noqa: E402
import taller  # noqa: E402

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


def revienta(descripcion, fn, *args):
    """Que `fn` levante `FueraDeLaConsola`. Devuelve el mensaje, para mirarlo."""
    try:
        fn(*args)
    except consola.FueraDeLaConsola as e:
        af(descripcion, True)
        return str(e)
    except Exception as e:          # noqa: BLE001 — cualquier otra es una roja
        af(descripcion, False, "levantó %s: %s" % (type(e).__name__, e))
        return ""
    af(descripcion, False, "no levantó nada")
    return ""


FALSOS = tempfile.mkdtemp(prefix="capataz-consola-arnes-")


def claude_falso(nombre, cuerpo):
    """Un `claude` de mentira, ejecutable, que hace lo que le digamos.

    Se llama `claude` a propósito: la compuerta mira el basename, así que esto
    ejercita el camino de verdad en vez de esquivarlo.
    """
    carpeta = os.path.join(FALSOS, nombre)
    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, "claude")
    with io.open(ruta, "w", encoding="utf-8") as f:
        f.write(cuerpo)
    os.chmod(ruta, os.stat(ruta).st_mode | stat.S_IXUSR | stat.S_IXGRP)
    return ruta


def argv_de(ruta, *extra):
    return (ruta, "agents", "--json", "--all") + extra


# ---------------------------------------------------------------------------
print("\n§ 1 · La compuerta: capataz no lanza agentes")
# ---------------------------------------------------------------------------

igual("el argv por defecto es `claude agents --json --all`",
      consola.ARGV, ("claude", "agents", "--json", "--all"))
af("`--all` está, que es lo que trae los background ya terminados",
   "--all" in consola.ARGV)

# El corazón del § 1: cada bandera que despacharía una sesión tiene que ser
# rechazada. No se prueba «alguna»: se prueban **todas** las declaradas, así que
# agregar una a la lista sin que la compuerta la mire pone esto rojo.
for mala in consola.PROHIBIDAS:
    msg = revienta("«%s» se rechaza" % mala,
                   consola._compuerta, argv_de("claude", mala))
    if mala == consola.PROHIBIDAS[0]:
        af("y el mensaje nombra la regla", "CLAUDE.md § 1" in msg, msg)

msg = revienta("un binario que no es `claude` se rechaza",
               consola._compuerta, ("git", "agents", "--json"))
af("y el mensaje dice cuál era", "git" in msg, msg)

msg = revienta("`claude agents` **sin** --json se rechaza",
               consola._compuerta, ("claude", "agents"))
af("y el mensaje explica que sin --json eso abre la vista que despacha",
   "interactiva" in msg and "despachan" in msg, msg)
revienta("`claude --json` sin `agents` se rechaza",
         consola._compuerta, ("claude", "--json"))
revienta("un argv vacío se rechaza", consola._compuerta, ())

af("el argv por defecto pasa la compuerta",
   consola._compuerta(consola.ARGV) == consola.ARGV)
# Una ruta absoluta a un `claude` pasa: es lo que usa el resto de este arnés, y
# si no pasara, todo lo de abajo estaría probando otra cosa.
af("una ruta absoluta a un binario llamado `claude` pasa",
   consola._compuerta(argv_de("/usr/local/bin/claude")) is not None)

# --- El AST: un solo subprocess, y adentro de `_correr` -------------------
FUENTE = os.path.join(RAIZ, "consola.py")
with io.open(FUENTE, encoding="utf-8") as f:
    ARBOL = ast.parse(f.read(), FUENTE)


def llamadas_subprocess(nodo):
    salida = []
    for n in ast.walk(nodo):
        if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) \
                and n.value.id == "subprocess" and n.attr in ("run", "Popen",
                                                              "call", "check_output",
                                                              "check_call"):
            salida.append(n.attr)
    return salida


TODAS = llamadas_subprocess(ARBOL)
igual("en todo el archivo hay **una sola** llamada a subprocess", TODAS, ["run"])

FUNCIONES = {n.name: n for n in ast.walk(ARBOL)
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
af("`_correr` existe", "_correr" in FUNCIONES)
igual("y la llamada está adentro de `_correr`",
      llamadas_subprocess(FUNCIONES["_correr"]), ["run"])

LLAMADA = [n for n in ast.walk(FUNCIONES["_correr"])
           if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
           and n.func.attr == "run"][0]
CLAVES = {k.arg: k.value for k in LLAMADA.keywords}
af("no se corre por shell", "shell" not in CLAVES)
af("hay tope de tiempo", "timeout" in CLAVES)
af("stdin va a DEVNULL: un proceso ajeno esperando una tecla no cuelga la pantalla",
   isinstance(CLAVES.get("stdin"), ast.Attribute)
   and CLAVES["stdin"].attr == "DEVNULL")
af("y el argv que se corre es el que pasó por la compuerta, no otro",
   isinstance(LLAMADA.args[0], ast.Call)
   and getattr(LLAMADA.args[0].func, "id", "") == "list"
   and getattr(LLAMADA.args[0].args[0], "id", "") == "argv")

# Y que la compuerta esté **antes** de correr nada: si el orden se invirtiera, el
# proceso ya salió cuando se lo rechaza.
CUERPO = FUNCIONES["_correr"].body


def tiene_llamada(nodo, nombre):
    """Si adentro del nodo hay una **llamada** a `nombre`. Mirar `ast.dump` en
    crudo no sirve: el docstring nombra a los dos y los encuentra en la línea 0,
    que es cómo esta aserción salió roja la primera vez sin que hubiera bug."""
    for n in ast.walk(nodo):
        if isinstance(n, ast.Call):
            f = n.func
            if getattr(f, "id", "") == nombre:
                return True
            if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) \
                    and "%s.%s" % (f.value.id, f.attr) == nombre:
                return True
    return False


POS_COMPUERTA = [i for i, n in enumerate(CUERPO) if tiene_llamada(n, "_compuerta")]
POS_RUN = [i for i, n in enumerate(CUERPO) if tiene_llamada(n, "subprocess.run")]
af("la compuerta corre **antes** que el subproceso",
   POS_COMPUERTA and POS_RUN and POS_COMPUERTA[0] < POS_RUN[0],
   "compuerta en %s, run en %s" % (POS_COMPUERTA, POS_RUN))

# Escribir: no hay. Es la misma afirmación que en `lector.py` y `taller.py`.
ESCRITURAS = [n for n in ast.walk(ARBOL) if isinstance(n, ast.Call)
              and getattr(n.func, "id", "") in ("open",)
              or (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                  and n.func.attr in ("open", "mkdir", "makedirs", "remove",
                                      "rmtree", "write_text"))]
igual("no abre ni crea ni borra ningún archivo", ESCRITURAS, [])


# ---------------------------------------------------------------------------
print("\n§ 2 · Contra el CLI de verdad de esta máquina")
# ---------------------------------------------------------------------------
#
# Esto es lo que hace que el arnés valga. Un lector probado sólo contra
# respuestas escritas a mano pasa entero con el CLI desinstalado, cambiado de
# formato o contestando basura — y la primera vez que alguien lo mira es cuando
# la pantalla dice «ningún agente» y no es cierto.

CLAUDE = shutil.which("claude")
af("`claude` está instalado y en el PATH", CLAUDE is not None,
   "sin él no se puede verificar nada de lo que este módulo afirma. No se "
   "saltea: se pone rojo, porque un arnés que no corre no verifica nada")

if CLAUDE:
    consola.olvidar()
    VISTA = consola.leer(refresco=0)
    af("la lectura de verdad sale `ok`", VISTA["ok"], VISTA["error"])
    igual("y corrió el comando que dice que corre",
          VISTA["comando"], " ".join(consola.ARGV))

    # Contra el CLI corrido a mano acá mismo: si `consola.py` filtrara, ordenara
    # o inventara, los dos conjuntos de sessionId no coincidirían.
    CRUDO = json.loads(subprocess.run(
        [CLAUDE, "agents", "--json", "--all"], stdout=subprocess.PIPE,
        stdin=subprocess.DEVNULL, timeout=15).stdout.decode("utf-8"))
    af("el CLI de verdad contesta una lista", isinstance(CRUDO, list))
    IDS_CRUDO = set(s.get("sessionId") for s in CRUDO if isinstance(s, dict))
    IDS_VISTA = set(s["sesion"] for s in
                    VISTA["background"] + VISTA["interactivas"])
    # No se exige igualdad exacta: entre las dos corridas puede abrirse o
    # cerrarse una sesión, y una aserción que se pone roja sola no sirve. Lo que
    # sí se exige es que no haya inventadas y que el grueso coincida.
    af("ningún sessionId inventado: todo lo que muestra estaba en el CLI",
       IDS_VISTA <= IDS_CRUDO | {""},
       "de más: %s" % (IDS_VISTA - IDS_CRUDO))
    af("y no se perdió más de una sesión entre las dos corridas",
       len(IDS_CRUDO - IDS_VISTA) <= 1, "faltan %s" % (IDS_CRUDO - IDS_VISTA))

    igual("las interactivas se cuentan pero **no** se muestran como background",
          [s for s in VISTA["background"] if s["clase"] == "interactive"], [])
    af("las interactivas viajan aparte, para cotejar y nada más",
       VISTA["cuenta"]["interactivas"] == len(VISTA["interactivas"]))
    af("hay al menos una sesión interactiva: esta misma corrida es una",
       VISTA["cuenta"]["interactivas"] >= 1)

    for s in VISTA["background"]:
        af("el background %s trae un estado de los conocidos" % s["id"],
           s["estado"] in ("trabajando", "en cola", "esperando", "terminado",
                           "falló", "parado", "no sé"), s["estado"])
        af("y trae el `id` corto, que es el asa para `claude attach`",
           bool(s["id"]) or s["estado"] == "no sé")

    # La frescura viaja, que es la lección de T21: sin esto la pantalla diría
    # «recién preguntado» para siempre.
    af("la vista dice **cuándo** se preguntó",
       isinstance(VISTA["preguntado_en"], float)
       and abs(VISTA["preguntado_en"] - time.time()) < 60)

    # Y el cotejo contra el taller **de esta máquina**, que es el caso real: las
    # dos fuentes mirando las mismas sesiones interactivas vivas.
    VT = taller.leer()
    DES = consola.cotejar(VISTA, VT)
    # **No se exige que la lista esté vacía**, y eso costó una roja para
    # entenderlo: el 2026-08-15 la máquina tenía un desacuerdo de verdad — un
    # background con `state: blocked` que el CLI sigue listando **sin `pid`**,
    # o sea con el proceso muerto y el registro viejo (T37). Exigir cero acá es
    # pedirle a un arnés que la máquina no tenga nunca nada raro, y el día que
    # lo tenga la roja es del arnés y no del código.
    #
    # Lo que sí se exige es que **ninguno sea de los dos que están declarados
    # como falsos positivos**: el alias `bg`/`background` y un background
    # terminado sin archivo. Ésos son los que harían salir el aviso siempre.
    DECLARADOS = [d for d in DES if d["que"] == "la clase de sesión no coincide"
              or (d["que"] == "la consola la ve y el taller no"
                  and "background · " in d["consola"]
                  and d["sesion"] in [b["sesion"] for b in VISTA["background"]
                                      if b["estado"] in ("terminado", "falló",
                                                         "parado")])]
    igual("cotejar no inventa ninguno de los dos desacuerdos declarados",
          DECLARADOS, [])
    if DES:
        print("       (la máquina tiene %d desacuerdo(s) de verdad: %s)"
              % (len(DES), ", ".join(d["que"] for d in DES)))
    af("y el taller ve las mismas sesiones que la consola",
       len(VT.get("sesiones", [])) >= 1)
    # Ésta es la que prueba que el alias no es decorativo: si el taller y el CLI
    # no escribieran `kind` distinto, `ALIAS_KIND` no haría falta y la aserción
    # de arriba sería vacua. Se mide que las clases crudas existen.
    CLASES = set(s.get("clase") for s in VT.get("sesiones", []) if s.get("clase"))
    af("el taller trae la clase cruda de cada sesión (`interactive`/`bg`)",
       bool(CLASES), "no trae ninguna: el cotejo de clase no verificaría nada")


# ---------------------------------------------------------------------------
print("\n§ 3 · Los seis estados medidos, y el que nadie vio")
# ---------------------------------------------------------------------------

igual("son los seis que se midieron, ni uno más",
      sorted(consola.ESTADOS),
      ["blocked", "done", "failed", "queued", "stopped", "working"])

for crudo, esperado in (("working", "trabajando"), ("queued", "en cola"),
                        ("blocked", "esperando"), ("done", "terminado"),
                        ("failed", "falló"), ("stopped", "parado")):
    e, _m = consola.estado_background({"state": crudo, "id": "abc123"})
    igual("`state: %s` → %s" % (crudo, esperado), e, esperado)

E, M = consola.estado_background({"state": "blocked", "id": "abc123"})
af("`blocked` dice que hace falta una persona, que es lo accionable",
   "una persona" in M, M)
# El comando para abrirlo **no** va en el motivo: la pantalla ya lo dibuja
# aparte, y repetirlo son dos renglones de teléfono diciendo lo mismo. Que esté
# una sola vez es lo que verifica esta aserción.
af("y el comando no se repite adentro del motivo", "attach" not in M, M)

E, M = consola.estado_background({"state": "hibernating", "id": "x"})
igual("un `state` que nadie vio no se pinta: es «no sé»", E, "no sé")
af("y el motivo lleva la palabra cruda, que es lo accionable",
   "hibernating" in M, M)
E, M = consola.estado_background({"state": "", "id": "x"})
igual("sin `state` tampoco se afirma nada", E, "no sé")
af("y se dice que es un campo *background only*", "background" in M, M)

# El nombre de un background **es lo que escribió una persona**: se limpia y se
# corta. Sin esto, un prompt con un token adentro se dibuja en la pantalla.
LARGO = "x" * 500
af("un nombre larguísimo se corta", len(consola._texto(LARGO)) <= consola.TOPE_NOMBRE)
SEÑUELO = "ghp" + "_" + "A" * 36
af("y un secreto en el nombre no llega a la pantalla",
   SEÑUELO not in consola._texto("mirá esto: " + SEÑUELO),
   consola._texto("mirá esto: " + SEÑUELO))
igual("los saltos de línea no rompen el renglón",
      "\n" in consola._texto("uno\ndos"), False)


# ---------------------------------------------------------------------------
print("\n§ 4 · Cotejar: que encuentre, y que no invente")
# ---------------------------------------------------------------------------
#
# Las dos mitades hacen falta y ninguna sirve sola. Sin la primera, una función
# que devuelve `[]` siempre pasaría el arnés entero. Sin la segunda, el aviso
# saldría en todas las corridas y sería el que enseña a ignorarse.

SES_A = "aaaaaaaa-1111-2222-3333-444444444444"
SES_B = "bbbbbbbb-1111-2222-3333-444444444444"
SES_C = "cccccccc-1111-2222-3333-444444444444"


def vista_consola(interactivas=(), background=()):
    return {"ok": True, "interactivas": list(interactivas),
            "background": list(background)}


def vista_taller(sesiones=()):
    return {"ok": True, "sesiones": list(sesiones)}


# --- Lo que NO es un desacuerdo, y está medido ---------------------------
SIN = consola.cotejar(
    vista_consola(interactivas=[{"sesion": SES_A, "cwd": "/p", "nombre": "n",
                                 "clase": "interactive"}]),
    vista_taller([{"sesion": SES_A, "cwd": "/p", "clase": "interactive",
                   "viva": True, "pid": 1}]))
igual("dos fuentes que coinciden no reportan nada", SIN, [])

ALIAS = consola.cotejar(
    vista_consola(background=[{"sesion": SES_B, "cwd": "/p", "nombre": "n",
                               "clase": "background", "estado": "trabajando",
                               "id": "b1"}]),
    vista_taller([{"sesion": SES_B, "cwd": "/p", "clase": "bg", "viva": True,
                   "pid": 2}]))
igual("`bg` y `background` son la misma palabra: no es un desacuerdo", ALIAS, [])

MUERTO = consola.cotejar(
    vista_consola(background=[{"sesion": SES_C, "cwd": "/p", "nombre": "n",
                               "clase": "background", "estado": "terminado",
                               "id": "c1"}]),
    vista_taller([]))
igual("un background terminado sin archivo es lo **esperado**, no un desacuerdo",
      MUERTO, [])

# --- Lo que SÍ es un desacuerdo -----------------------------------------
# **Que una fuente lo tenga y la otra no ya no se reporta acá.** Desde que las
# dos secciones se unieron, ese agente se dibuja igual —en su renglón, marcado
# `fuente: cli` y con «no sé si vive»—, así que el aviso sería decir dos veces
# lo mismo. Y como un background muerto se queda en el CLI para siempre (T37),
# saldría en todas las corridas: el aviso que enseña a ignorarse.
SOLO_EN_CLI = consola.cotejar(
    vista_consola(interactivas=[{"sesion": SES_A, "cwd": "/p", "nombre": "n",
                                 "clase": "interactive"}]),
    vista_taller([]))
igual("que sólo lo tenga una fuente no es un desacuerdo: lo dice el renglón",
      SOLO_EN_CLI, [])
# Y lo mismo del otro lado.
igual("ni al revés", consola.cotejar(
    vista_consola(),
    vista_taller([{"sesion": SES_A, "cwd": "/p", "clase": "interactive",
                   "viva": True, "pid": 1}])), [])
# Pero el renglón **sí** tiene que decirlo, y con la contradicción escrita: un
# background que el CLI da por vivo y del que no queda archivo es el T37.
FANTASMA = consola.unir(
    vista_consola(background=[{"sesion": SES_A, "cwd": "/p", "nombre": "n",
                               "clase": "background", "estado": "esperando",
                               "id": "z9"}]),
    vista_taller([]))
F0 = FANTASMA[0] if FANTASMA else {}
af("un background que el CLI da por vivo y no tiene archivo lo dice en su renglón",
   "quedó viejo" in (F0.get("motivo_consola") or ""), F0.get("motivo_consola"))
af("y aclara que no está esperando a nadie",
   "no está esperando" in (F0.get("motivo_consola") or ""))
# Anti-vacua: uno terminado no arrastra esa frase, porque ahí no hay contradicción.
TERMINADO = consola.unir(
    vista_consola(background=[{"sesion": SES_B, "cwd": "/p", "nombre": "n",
                               "clase": "background", "estado": "terminado",
                               "id": "z8", "motivo_estado": "terminó solo"}]),
    vista_taller([]))
T0 = TERMINADO[0] if TERMINADO else {}
af("y uno terminado no la lleva: ahí las dos fuentes no se contradicen",
   bool(TERMINADO) and "quedó viejo" not in (T0.get("motivo_consola") or ""),
   T0.get("motivo_consola"))

CARPETA = consola.cotejar(
    vista_consola(interactivas=[{"sesion": SES_A, "cwd": "/uno", "nombre": "n",
                                 "clase": "interactive"}]),
    vista_taller([{"sesion": SES_A, "cwd": "/otro", "clase": "interactive",
                   "viva": True, "pid": 1}]))
igual("el mismo sessionId con distinto cwd se reporta", len(CARPETA), 1)
igual("y muestra las **dos** versiones, sin elegir ganador",
      (CARPETA[0]["consola"], CARPETA[0]["taller"]) if CARPETA else None,
      ("/uno", "/otro"))

CLASE = consola.cotejar(
    vista_consola(interactivas=[{"sesion": SES_A, "cwd": "/p", "nombre": "n",
                                 "clase": "interactive"}]),
    vista_taller([{"sesion": SES_A, "cwd": "/p", "clase": "bg", "viva": True,
                   "pid": 1}]))
igual("una clase que no es alias de la otra se reporta", len(CLASE), 1)

af("si alguna de las dos fuentes no se pudo leer, no se coteja nada",
   consola.cotejar({"ok": False, "interactivas": [], "background": []},
                   vista_taller([{"sesion": SES_A, "viva": True}])) == [])


# ---------------------------------------------------------------------------
print("\n§ 4b · Unir: un renglón por agente, y el archivo gana lo compartido")
# ---------------------------------------------------------------------------
#
# La pantalla tenía dos secciones, una por fuente, y el **mismo** agente salía
# dibujado en las dos. `unir` las junta por `sessionId`. Lo que hay que
# verificar no es que junte: es **que no tape**. Juntar mal es elegir un ganador
# sin decirlo, que es el bug de la regla 1 con otra cara.

DOS = consola.unir(
    vista_consola(background=[{"sesion": SES_A, "cwd": "/lo-que-dice-el-cli",
                               "nombre": "el-del-cli", "clase": "background",
                               "estado": "esperando", "id": "abc123",
                               "state": "blocked", "motivo_estado": "trabado"}]),
    vista_taller([{"sesion": SES_A, "cwd": "/lo-que-dice-el-archivo",
                   "nombre": "el-del-archivo", "clase": "bg", "viva": True,
                   "pid": 7, "agentes": [{"id": "sub1", "hijos": []}],
                   "que": "Bash", "quieto_hace": 3}]))
igual("un agente que está en las dos fuentes es **un** renglón", len(DOS), 1)
igual("y lo compartido lo pone el archivo, que trae el doble de campos",
      (DOS[0]["cwd"], DOS[0]["nombre"]),
      ("/lo-que-dice-el-archivo", "el-del-archivo"))
igual("el `id` para `claude attach` lo pone el CLI, que es el único que lo tiene",
      DOS[0]["id"], "abc123")
igual("y el `state`, también", DOS[0]["estado_consola"], "esperando")
igual("el renglón dice de qué fuentes salió", DOS[0]["fuente"], "archivo+cli")
af("y no se le perdieron los subagentes por el camino",
   len(DOS[0]["agentes"]) == 1, DOS[0]["agentes"])
af("ni lo que está haciendo", DOS[0]["que"] == "Bash")

SOLO_CLI = consola.unir(
    vista_consola(background=[{"sesion": SES_C, "cwd": "/p", "nombre": "terminado",
                               "clase": "background", "estado": "terminado",
                               "id": "c1", "state": "done"}]),
    vista_taller([]))
igual("un background sin archivo entra igual: es el dato que sólo tiene el CLI",
      len(SOLO_CLI), 1)
# Indexado con guarda: con el bug de «unir se olvida de los sin archivo»
# puesto, esto reventaba y el arnés moría antes de las secciones de abajo. Un
# arnés que se cae no dice cuántas rojas hay: dice cero aserciones.
UNO = SOLO_CLI[0] if SOLO_CLI else {}
igual("marcado como tal", UNO.get("fuente"), "cli")
igual("y **no se afirma** si su proceso vive: no hay con qué saberlo",
      UNO.get("viva"), None)
af("con el motivo de por qué no tiene subagentes",
   "ya no queda archivo" in (UNO.get("motivo_sin_agentes") or ""),
   UNO.get("motivo_sin_agentes"))

# Una sesión interactiva no la toca el CLI: ahí el archivo manda entero.
SOLA = consola.unir(
    vista_consola(interactivas=[{"sesion": SES_B, "cwd": "/p", "nombre": "i",
                                 "clase": "interactive"}]),
    vista_taller([{"sesion": SES_B, "cwd": "/p", "nombre": "i", "viva": True,
                   "clase": "interactive", "pid": 3, "agentes": []}]))
igual("una interactiva queda con la fuente del archivo y nada más",
      (len(SOLA), SOLA[0]["fuente"]), (1, "archivo"))
af("y sin estado de consola inventado", not SOLA[0].get("estado_consola"))

# El orden: primero el que necesita a una persona — **entre los que existen**.
ORDEN = consola.unir(
    vista_consola(background=[
        {"sesion": SES_A, "cwd": "/p", "nombre": "x", "clase": "background",
         "estado": "trabajando", "id": "a"},
        {"sesion": SES_B, "cwd": "/p", "nombre": "y", "clase": "background",
         "estado": "esperando", "id": "b"}]),
    vista_taller([
        {"sesion": SES_A, "cwd": "/p", "nombre": "el-que-trabaja", "viva": True,
         "clase": "bg", "pid": 1, "agentes": [], "quieto_hace": 5},
        {"sesion": SES_B, "cwd": "/p", "nombre": "el-trabado", "viva": True,
         "clase": "bg", "pid": 2, "agentes": [], "quieto_hace": 5}]))
igual("primero el que pide una persona, después el que trabaja",
      [f["nombre"] for f in ORDEN], ["el-trabado", "el-que-trabaja"])

# **Y los fantasmas al final, aunque el CLI los dé por «esperando».** Un
# background del que no queda archivo no está esperando a nadie, y ponerlo
# arriba tapa a los que sí trabajan con los que ya no existen — se vio mirando
# la pantalla, con dos agentes muertos encabezando la lista.
FANTASMAS = consola.unir(
    vista_consola(background=[
        {"sesion": SES_C, "cwd": "/p", "nombre": "el-fantasma",
         "clase": "background", "estado": "esperando", "id": "f"},
        {"sesion": SES_A, "cwd": "/p", "nombre": "x", "clase": "background",
         "estado": "trabajando", "id": "a"}]),
    vista_taller([{"sesion": SES_A, "cwd": "/p", "nombre": "el-vivo",
                   "viva": True, "clase": "bg", "pid": 1, "agentes": [],
                   "quieto_hace": 5}]))
igual("el que ya no tiene archivo va al final, aunque diga «esperando»",
      [f["nombre"] for f in FANTASMAS], ["el-vivo", "el-fantasma"])
# **Y lo dice en el renglón**, que es lo que se agregó el 2026-08-17. Antes ser
# fantasma se calculaba adentro de la función de orden y no salía a ningún lado;
# desde que la pantalla tiene una zona para «esto pide una persona», ella
# también necesita saberlo — y dos lugares calculando lo mismo es la regla 1.
igual("y el renglón dice que es un fantasma, para que no lo use nadie más",
      [(f["nombre"], f["fantasma"]) for f in FANTASMAS],
      [("el-vivo", False), ("el-fantasma", True)])
af("un background terminado NO es un fantasma: que ya no tenga archivo es "
   "justamente lo que se espera de uno que terminó",
   UNO.get("fantasma") is False, UNO.get("fantasma"))
af("y uno con archivo tampoco, por trabado que esté: ése sí espera a alguien",
   DOS[0]["fantasma"] is False, DOS[0]["fantasma"])

af("si el taller no se pudo leer, unir no inventa: devuelve lo que había",
   consola.unir(vista_consola(background=[{"sesion": SES_A, "estado": "x"}]),
                {"ok": False, "sesiones": []}) == [])

# Y contra las dos fuentes **de verdad**: ningún agente puede salir dos veces,
# que es exactamente el bug que esta función vino a matar.
if CLAUDE:
    UNIDA = consola.unir(VISTA, VT)
    IDS = [f["sesion"] for f in UNIDA if f["sesion"]]
    igual("contra las fuentes reales, ningún sessionId sale dos veces",
          sorted(set(IDS)), sorted(IDS))
    af("y están todas las sesiones del taller",
       all(s["sesion"] in IDS for s in VT.get("sesiones", []) if s.get("sesion")))
    af("más los background que ya no tienen archivo",
       len(UNIDA) >= len(VT.get("sesiones", [])),
       (len(UNIDA), len(VT.get("sesiones", []))))
    # Anti-vacua: si no hubiera ningún background, todo lo de arriba pasaría
    # igual con un `unir` que devuelve las sesiones tal cual.
    af("y hay al menos un background de verdad que unir (si no, esto no mira nada)",
       len(VISTA["background"]) >= 1,
       "no hay ninguno: lanzá uno con `claude --bg` para que esto verifique algo")


# ---------------------------------------------------------------------------
print("\n§ 5 · Lo que falla, falla diciendo qué corrió")
# ---------------------------------------------------------------------------

def leer_con(ruta, **kw):
    consola.olvidar()
    return consola.leer(argv=argv_de(ruta), refresco=0, **kw)


NO_ESTA = os.path.join(FALSOS, "vacio", "claude")
V = leer_con(NO_ESTA)
igual("sin el CLI, `ok` es False", V["ok"], False)
igual("y **no** dice cero agentes", V["background"], [])
af("el error dice qué comando buscó", NO_ESTA in V["error"], V["error"])
af("y explica por qué eso no se puede sacar de un archivo",
   "desaparece" in V["error"], V["error"])
af("y aclara que lo demás se lee igual", "GitHub" in V["error"], V["error"])

V = leer_con(claude_falso("basura", "#!/bin/sh\necho 'no soy json'\n"))
igual("una respuesta que no es JSON no se lee como cero agentes", V["ok"], False)
af("y el error muestra lo que contestó de verdad", "no soy json" in V["error"],
   V["error"])

V = leer_con(claude_falso("objeto", "#!/bin/sh\necho '{\"a\":1}'\n"))
igual("un JSON que no es una lista tampoco", V["ok"], False)
af("y el error dice qué tipo vino", "dict" in V["error"], V["error"])

V = leer_con(claude_falso("codigo", "#!/bin/sh\necho 'se rompio' >&2\nexit 3\n"))
igual("un código de salida distinto de cero es un error", V["ok"], False)
af("y el error trae el código y lo que dijo", "3" in V["error"]
   and "se rompio" in V["error"], V["error"])

# El tope de tiempo, ejercitado de verdad: sin él la pantalla se queda colgada
# de un proceso que no es de capataz.
ESPERA_VIEJA = consola.ESPERA
consola.ESPERA = 1
INICIO = time.time()
V = leer_con(claude_falso("lento", "#!/bin/sh\nsleep 20\n"))
TARDO = time.time() - INICIO
consola.ESPERA = ESPERA_VIEJA
igual("un CLI que se cuelga se corta", V["ok"], False)
af("y se corta en el tope, no cuando el otro quiera", TARDO < 5, "tardó %.1f s" % TARDO)
af("y el error dice cuánto esperó", "1 s" in V["error"], V["error"])

# `stdin` a /dev/null, ejercitado: este falso **lee una línea** antes de
# contestar. Con stdin abierto se quedaría esperando hasta el tope; con DEVNULL
# recibe EOF y sigue. Es la aserción que distingue el comentario del hecho.
INICIO = time.time()
V = leer_con(claude_falso("pregunton", "#!/bin/sh\nread x\necho '[]'\n"))
TARDO = time.time() - INICIO
igual("un CLI que lee stdin no cuelga la pantalla: recibe EOF", V["ok"], True)
af("y contesta enseguida, no al vencer el tope", TARDO < 3, "tardó %.1f s" % TARDO)

V = leer_con(claude_falso("vacio-ok", "#!/bin/sh\necho '[]'\n"))
igual("una lista vacía sí es cero agentes, y eso es `ok`", (V["ok"], V["background"]),
      (True, []))

# Apagada a mano: dice por qué, y sigue sin ser verde.
APAGADA_VIEJA = consola.APAGADA
consola.APAGADA = True
consola.olvidar()
V = consola.leer(refresco=0)
consola.APAGADA = APAGADA_VIEJA
igual("apagada con CAPATAZ_CONSOLA=0, `ok` es False", V["ok"], False)
af("y dice cómo está apagada", "CAPATAZ_CONSOLA=0" in V["error"], V["error"])


# ---------------------------------------------------------------------------
print("\n§ 6 · No guarda estado propio")
# ---------------------------------------------------------------------------
#
# Es la misma aserción que la del espejo descartable de `nube.py` (§ 5): se tira
# lo que quedó guardado, se vuelve a leer, y lo único que puede cambiar es la
# marca de cuándo se preguntó. Si algo más cambia, capataz está acumulando algo
# suyo — que es lo que la regla 1 prohíbe.

FALSO_OK = claude_falso("estable", """#!/bin/sh
echo '[{"pid":1,"id":"z1","cwd":"/p","kind":"background","startedAt":1786822504306,
 "sessionId":"zzzzzzzz-1111-2222-3333-444444444444","name":"uno","state":"working"}]'
""")
# El reloj va **puesto a mano** en las dos lecturas, y no por prolijidad: `hace`
# se calcula contra `ahora`, así que dos lecturas separadas por el cruce de un
# segundo difieren en un campo sin que nada esté mal. Esa es la roja que aparece
# sola una vez cada tantas corridas y hace que se deje de confiar en el arnés.
UNA = leer_con(FALSO_OK, ahora=HOY)
consola.olvidar()
OTRA = consola.leer(argv=argv_de(FALSO_OK), refresco=0, ahora=HOY)


def sin_reloj(v):
    return {k: val for k, val in v.items() if k != "preguntado_en"}


igual("borrar lo cacheado y releer da byte por byte lo mismo",
      json.dumps(sin_reloj(UNA), sort_keys=True, default=str),
      json.dumps(sin_reloj(OTRA), sort_keys=True, default=str))
igual("con el reloj puesto a mano, **ningún** campo difiere",
      [k for k in UNA if UNA[k] != OTRA[k]], [])
consola.olvidar()
DESPUES = consola.leer(argv=argv_de(FALSO_OK), refresco=0)
af("y con el reloj de verdad, esa marca **sí** se mueve",
   DESPUES["preguntado_en"] > UNA["preguntado_en"])

# Y el refresco: dos lecturas seguidas no lanzan dos procesos. Se verifica por
# el reloj de la vista, que es lo que la pantalla muestra.
consola.olvidar()
P1 = consola.leer(argv=argv_de(FALSO_OK), refresco=30)
P2 = consola.leer(argv=argv_de(FALSO_OK), refresco=30)
af("con el refresco puesto, la segunda lectura no vuelve a correr el CLI",
   P1["preguntado_en"] == P2["preguntado_en"])
P3 = consola.leer(argv=argv_de(FALSO_OK), refresco=0)
af("con refresco 0 sí vuelve a correrlo",
   P3["preguntado_en"] >= P1["preguntado_en"])
consola.olvidar()

shutil.rmtree(FALSOS, ignore_errors=True)

print("\nASERCIONES: %d" % ASER)
print("ROJAS: %d" % ROJAS)
sys.exit(1 if ROJAS else 0)

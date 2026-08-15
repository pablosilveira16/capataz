"""Arnés de `taller.py` — el lector del taller de esta máquina.

Lo que se verifica, y por qué cada sección no es vacua:

    § 1  **No escribe, no corre nada y no abre una transcripción.** Es la
         afirmación entera del módulo, y se prueba de tres formas que no se
         tapan entre sí: las guardas ejercitadas, un recuento por AST del
         código de verdad, y la huella del disco antes y después de leer.
    § 2  Las sesiones, contra el `~/.claude` **de esta máquina**. Un lector de
         archivos probado sólo contra un directorio armado a mano pasa entero
         con el formato real cambiado — es la misma lección que dejó `nube.py`.
    § 3  El árbol de agentes, contra los subagentes que hay en disco de verdad.
    § 4  Los desenlaces y los dos umbrales, con el reloj puesto a mano.
    § 5  Lo que falla, falla diciendo **qué buscó**.

Contra fuentes reales, y cuando no las hay se dice y **no se saltea**: una
sección que desaparece en silencio se lleva su cuenta de aserciones con ella y
lo único que cambia es el total.

    python3 pruebas/verificar-taller.py
"""
import ast
import io
import json
import os
import shutil
import sys
import tempfile
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
sys.path.insert(0, RAIZ)
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


def huella(base):
    """Ruta, tamaño y mtime de todo lo que cuelga de una carpeta.

    Comparar esto antes y después es lo que hace verificable la frase «no
    escribe»: no le cree al código, mira el disco.
    """
    salida = {}
    for carpeta, _, archivos in os.walk(base):
        for a in archivos:
            p = os.path.join(carpeta, a)
            e = os.stat(p)
            salida[os.path.relpath(p, base)] = (e.st_size, e.st_mtime)
    return salida


def pid_muerto():
    """Un pid que con seguridad no existe. Medido, no elegido de memoria."""
    for p in range(90000, 99999):
        try:
            os.kill(p, 0)
        except ProcessLookupError:
            return p
        except OSError:
            continue
    return 99998


# ---------------------------------------------------------------------------
# Un taller de mentira, con el formato exacto que se midió sobre los reales.
# ---------------------------------------------------------------------------
FALSO = tempfile.mkdtemp(prefix="capataz-taller-arnes-")
CWD_FALSO = "/tmp/proyecto-de-mentira"
SESION_VIVA = "11111111-2222-3333-4444-555555555555"
SESION_MUERTA = "99999999-8888-7777-6666-555555555555"
MUERTO = pid_muerto()


def sembrar():
    """Armar el taller de mentira. Devuelve la carpeta de subagentes viva."""
    ses = os.path.join(FALSO, "sessions")
    os.makedirs(ses)
    for pid, sesion, nombre in ((os.getpid(), SESION_VIVA, "viva-a1"),
                                (MUERTO, SESION_MUERTA, "muerta-b2")):
        with io.open(os.path.join(ses, "%d.json" % pid), "w", encoding="utf-8") as f:
            json.dump({"pid": pid, "sessionId": sesion, "cwd": CWD_FALSO,
                       "startedAt": int((HOY - 600) * 1000), "version": "2.1.221",
                       "kind": "interactive", "entrypoint": "claude-desktop",
                       "name": nombre}, f)
    subs = {}
    for sesion in (SESION_VIVA, SESION_MUERTA):
        d = os.path.join(taller.carpeta_de(CWD_FALSO, FALSO), sesion, "subagents")
        os.makedirs(d)
        subs[sesion] = d
    # Cuatro agentes en la sesión viva: uno recién escrito, uno tibio, uno
    # callado hace rato, y uno anidado colgando del primero.
    plan = [("aaaa1", "general-purpose", "el que trabaja", 1, None, HOY - 10),
            ("aaaa2", "general-purpose", "el dudoso", 1, None, HOY - taller.FRESCO - 60),
            ("aaaa3", "Explore", "el callado", 1, None, HOY - taller.TIBIO - 60),
            ("aaaa4", "Explore", "el hijo", 2, "aaaa1", HOY - 10)]
    for ident, tipo, desc, hondo, padre, cuando in plan:
        meta = {"agentType": tipo, "description": desc,
                "toolUseId": "toolu_" + ident, "spawnDepth": hondo}
        if padre:
            meta["parentAgentId"] = padre
        with io.open(os.path.join(subs[SESION_VIVA], "agent-%s.meta.json" % ident),
                     "w", encoding="utf-8") as f:
            json.dump(meta, f)
        j = os.path.join(subs[SESION_VIVA], "agent-%s.jsonl" % ident)
        with io.open(j, "w", encoding="utf-8") as f:
            f.write('{"type":"assistant","isSidechain":true}\n')
        os.utime(j, (cuando, cuando))
    # Y uno en la sesión muerta, para el desenlace `cerrado`.
    with io.open(os.path.join(subs[SESION_MUERTA], "agent-bbbb1.meta.json"),
                 "w", encoding="utf-8") as f:
        json.dump({"agentType": "general-purpose", "description": "el huérfano",
                   "toolUseId": "toolu_bbbb1", "spawnDepth": 1}, f)
    j = os.path.join(subs[SESION_MUERTA], "agent-bbbb1.jsonl")
    with io.open(j, "w", encoding="utf-8") as f:
        f.write('{"type":"assistant","isSidechain":true}\n')
    os.utime(j, (HOY - 30, HOY - 30))
    return subs[SESION_VIVA]


try:
    VIVOS = sembrar()

    # -----------------------------------------------------------------------
    print("§ 1 · No escribe, no corre nada y no abre una transcripción")
    # -----------------------------------------------------------------------
    #
    # Tres pruebas distintas de la misma afirmación. La primera ejercita las
    # guardas de producción; la segunda mira el código, porque una guarda se
    # puede esquivar por otro camino; la tercera mira el disco, que es lo único
    # que no se puede argumentar.

    for ruta, por_que in ((os.path.join(FALSO, "..", "afuera.json"), "un .. que sale"),
                          ("/etc/hosts", "una ruta absoluta de afuera"),
                          (os.path.expanduser("~/.ssh/id_rsa"), "la carpeta de claves")):
        try:
            taller._abrir(ruta, FALSO)
            af("_abrir rechaza %s" % por_que, False, ruta)
        except taller.FueraDelTaller:
            af("_abrir rechaza %s" % por_que, True)

    for nombre in ("agent-aaaa1.jsonl", "sesion.jsonl", "cualquiera.txt"):
        try:
            taller._abrir(os.path.join(VIVOS, nombre), FALSO)
            af("_abrir rechaza «%s»: una transcripción no se abre" % nombre, False)
        except taller.FueraDelTaller:
            af("_abrir rechaza «%s»: una transcripción no se abre" % nombre, True)

    # La aserción positiva, sin la cual las seis de arriba pasarían con un
    # `_abrir` que rechaza absolutamente todo.
    dato, error = taller._abrir(os.path.join(VIVOS, "agent-aaaa1.meta.json"), FALSO)
    af("y un .meta.json de adentro NO se rechaza", dato is not None, error)

    arbol = ast.parse(io.open(os.path.join(RAIZ, "taller.py"), encoding="utf-8").read())
    llamadas = [n for n in ast.walk(arbol) if isinstance(n, ast.Call)]

    def nombre_de(n):
        f = n.func
        if isinstance(f, ast.Attribute):
            return "%s.%s" % (getattr(f.value, "id", "?"), f.attr)
        return getattr(f, "id", "?")

    nombres = [nombre_de(n) for n in llamadas]
    igual("el único io.open de taller.py está adentro de _abrir()",
          nombres.count("io.open"), 1)
    prohibidas = [n for n in nombres if n in (
        "subprocess.run", "subprocess.Popen", "subprocess.call",
        "subprocess.check_output", "os.system", "os.popen", "eval", "exec")]
    igual("no corre nada: cero subprocess y cero exec", prohibidas, [])
    escrituras = [n for n in nombres if n in (
        "os.remove", "os.unlink", "os.rmdir", "os.makedirs", "os.mkdir",
        "os.rename", "os.chmod", "os.utime", "shutil.rmtree", "open")]
    igual("no escribe: cero llamadas que toquen el disco", escrituras, [])

    # `os.kill` está, y es lo que más se parece a «correr algo». Que la señal
    # sea la 0 —la que no hace nada— no puede quedar en un comentario.
    kills = [n for n in llamadas if nombre_de(n) == "os.kill"]
    igual("os.kill aparece una sola vez", len(kills), 1)
    af("y siempre con la señal 0, la que no le hace nada a nadie",
       bool(kills) and len(kills[0].args) == 2
       and isinstance(kills[0].args[1], ast.Constant) and kills[0].args[1].value == 0,
       ast.dump(kills[0]) if kills else "no hay ninguna")

    antes = huella(FALSO)
    vista = taller.leer(FALSO, HOY)
    taller.sesiones(FALSO, HOY)
    taller.agentes(CWD_FALSO, SESION_VIVA, FALSO, HOY)
    despues = huella(FALSO)
    # El detalle es **la diferencia**, no las dos huellas enteras: con trece
    # archivos, volcar las dos tapa el rojo en vez de explicarlo.
    tocados = sorted(k for k in set(antes) | set(despues)
                     if antes.get(k) != despues.get(k))
    af("leer el taller entero no cambió un solo byte en disco", not tocados, tocados)

    # -----------------------------------------------------------------------
    print("§ 2 · Las sesiones")
    # -----------------------------------------------------------------------

    ses = {s["nombre"]: s for s in vista["sesiones"]}
    igual("encuentra las dos sesiones sembradas", sorted(ses), ["muerta-b2", "viva-a1"])
    igual("la del proceso propio está viva", ses["viva-a1"]["viva"], True)
    igual("y la del pid inexistente, no", ses["muerta-b2"]["viva"], False)
    igual("el sessionId sale del archivo, no del nombre",
          ses["viva-a1"]["sesion"], SESION_VIVA)
    af("startedAt llega en segundos y no en milisegundos",
       abs(ses["viva-a1"]["arrancada"] - (HOY - 600)) < 2, ses["viva-a1"]["arrancada"])
    af("la vista declara su alcance: sin eso, el tablero miente",
       "esta máquina" in vista["alcance"], vista["alcance"])

    # -----------------------------------------------------------------------
    print("§ 3 · El árbol de agentes")
    # -----------------------------------------------------------------------

    raices = ses["viva-a1"]["agentes"]
    igual("tres agentes de primer nivel, no cuatro", len(raices), 3)
    por_desc = {a["descripcion"]: a for a in raices}
    igual("el anidado NO aparece arriba", sorted(por_desc),
          ["el callado", "el dudoso", "el que trabaja"])
    igual("cuelga de su padre, por parentAgentId",
          [h["descripcion"] for h in por_desc["el que trabaja"]["hijos"]], ["el hijo"])
    igual("y el padre de los otros dos es la sesión",
          [len(por_desc[d]["hijos"]) for d in ("el dudoso", "el callado")], [0, 0])
    igual("el aplanado los cuenta a los cuatro",
          len(taller._todos(raices)), 4)
    igual("la cuenta de la vista suma los de las dos sesiones",
          vista["cuenta"]["agentes"], 5)

    # Un `parentAgentId` colgado no puede hacer desaparecer a un agente.
    huerfano = taller._arbol([{"id": "x", "padre": "no-existe", "hijos": []}])
    igual("un padre que no existe deja al agente arriba, no lo esconde",
          [a["id"] for a in huerfano], ["x"])

    # -----------------------------------------------------------------------
    print("§ 4 · Trabajando, dudoso, sin señal — y lo que NO se afirma")
    # -----------------------------------------------------------------------

    igual("el que escribió recién, trabajando",
          por_desc["el que trabaja"]["estado"], "trabajando")
    igual("pasado FRESCO, dudoso", por_desc["el dudoso"]["estado"], "dudoso")
    igual("pasado TIBIO, «sin señal»", por_desc["el callado"]["estado"], "sin señal")
    af("y «sin señal» explica que terminado y colgado no se distinguen",
       "no se distinguen" in por_desc["el callado"]["motivo_estado"],
       por_desc["el callado"]["motivo_estado"][:60])
    af("nunca se dice «caído»: sería inventar un incendio",
       "caído" not in json.dumps(vista, ensure_ascii=False),
       "aparece «caído» en la vista")
    af("ni «terminado»: no hay marca de cierre que lo sostenga",
       "terminado" not in [a["estado"] for a in taller._todos(raices)])
    igual("el de la sesión muerta queda «cerrado»",
          ses["muerta-b2"]["agentes"][0]["estado"], "cerrado")

    # El umbral no puede ser una opinión: se mueve el reloj y tiene que cambiar.
    solo = dict(por_desc["el que trabaja"])
    igual("con el reloj adelantado FRESCO, el mismo agente ya no es trabajando",
          taller.estado_agente(solo, True, HOY + taller.FRESCO + 30)[0], "dudoso")
    igual("y adelantado TIBIO, pasa a sin señal",
          taller.estado_agente(solo, True, HOY + taller.TIBIO + 30)[0], "sin señal")
    igual("sin transcripción todavía, «no sé» y nunca trabajando",
          taller.estado_agente({"ultimo": None}, True, HOY)[0], "no sé")
    af("FRESCO está arriba del silencio más largo medido en un agente vivo (272 s)",
       taller.FRESCO > 272, taller.FRESCO)

    # -----------------------------------------------------------------------
    print("§ 5 · Contra el taller de esta máquina, que es el que importa")
    # -----------------------------------------------------------------------
    #
    # Un lector de archivos probado sólo contra la carpeta que él mismo sembró
    # pasa entero con el formato real cambiado. Acá se lee `~/.claude` de
    # verdad. Si no hay ninguno, **se dice y se cuenta igual**: la premisa se
    # mide, no se supone.

    real = taller.leer()
    hay = os.path.isdir(taller.RAIZ)
    af("la carpeta de Claude Code de esta máquina existe", hay, taller.RAIZ)
    if hay:
        af("y se pudo leer", real["ok"], real["error"][:90])
        # Agrupadas en una aserción cada una: cuántas sesiones y agentes hay
        # cambia con lo que esté corriendo, y el total no puede depender de eso.
        malas = [s["nombre"] for s in real["sesiones"]
                 if not s["sesion"] or not s["cwd"] or s["viva"] is None]
        af("cada sesión real trae sessionId, cwd y un veredicto de si vive",
           not malas, malas)
        todos = [a for s in real["sesiones"] for a in taller._todos(s["agentes"])]
        # Los subagentes de una sesión **que ya cerró** siguen en disco, y son
        # los únicos que hay casi siempre: para que `leer()` los devuelva, esa
        # sesión tiene que estar todavía registrada como viva en `sessions/`,
        # que es lo raro. Sin esto, la aserción anti-vacua de abajo se ponía
        # roja según lo que estuviera corriendo en el momento — y una roja que
        # va y viene sola es la que hace que se deje de mirar el color.
        #
        # Los metas se buscan en disco y se leen **con el lector de verdad**,
        # que es lo que esta sección promete ejercitar.
        if not todos:
            for carpeta, dirs, archivos in os.walk(
                    os.path.join(taller.RAIZ, "projects")):
                if os.path.basename(carpeta) != "subagents":
                    continue
                if not any(a.endswith(".meta.json") for a in archivos):
                    continue
                sesion = os.path.basename(os.path.dirname(carpeta))
                proyecto = os.path.basename(os.path.dirname(os.path.dirname(carpeta)))
                cwd = proyecto.replace("-", os.sep)
                arbol, _err = taller.agentes(cwd, sesion)
                todos = taller._todos(arbol)
                if todos:
                    for a in todos:
                        a["estado"], a["motivo_estado"] = taller.estado_agente(
                            a, False, HOY)
                    break
        flojos = [a["id"] for a in todos
                  if not a["tipo"] or not a["descripcion"] or a["profundidad"] is None]
        af("cada agente real trae las cuatro claves que el meta siempre tiene",
           not flojos, flojos)
        af("los estados salen del vocabulario cerrado",
           all(a["estado"] in ("trabajando", "dudoso", "sin señal", "cerrado", "no sé")
               for a in todos),
           sorted({a["estado"] for a in todos}))
        # Anti-vacua: sin esto, las tres de arriba pasan con cero agentes.
        af("y se encontró al menos un agente de verdad (si no, no se miró nada)",
           len(todos) >= 1, len(todos))
    else:
        af("y sin ella el error dice qué buscó", taller.RAIZ in real["error"],
           real["error"][:90])
        af("sin taller no se inventan sesiones", real["sesiones"] == [], real["sesiones"])
        af("ok es False, que no es lo mismo que cero sesiones", real["ok"] is False)
        af("(no hay agentes reales que mirar en esta máquina)", True)

    # -----------------------------------------------------------------------
    print("§ 6 · Lo que falla, falla diciendo qué buscó")
    # -----------------------------------------------------------------------

    vacia = taller.leer(os.path.join(FALSO, "no-existe"), HOY)
    igual("un taller inexistente no revienta", vacia["ok"], False)
    af("y el error nombra la carpeta que buscó", "no-existe" in vacia["error"],
       vacia["error"][:90])
    af("la forma del diccionario es la misma que en el caso bueno",
       sorted(vacia) == sorted(vista), sorted(vacia))
    af("y nombra la variable con la que se destraba",
       "CAPATAZ_TALLER" in vacia["error"], vacia["error"][:90])

    sin_subs = taller.agentes(CWD_FALSO, "sesion-que-no-existe", FALSO, HOY)
    igual("una sesión sin carpeta de transcripciones devuelve lista vacía", sin_subs[0], [])
    af("con el motivo, que dice que cero agentes no es un error",
       "no un error" in sin_subs[1], sin_subs[1][:90])

    # Un `.meta.json` corrupto no puede tumbar la pantalla entera.
    with io.open(os.path.join(VIVOS, "agent-roto.meta.json"), "w", encoding="utf-8") as f:
        f.write("{esto no es json")
    roto = taller.leer(FALSO, HOY)
    af("un meta corrupto no tumba la lectura de los demás",
       len(roto["sesiones"]) == 2 and len(roto["sesiones"][0]["agentes"]) >= 1,
       [len(s["agentes"]) for s in roto["sesiones"]])

finally:
    shutil.rmtree(FALSO, ignore_errors=True)

print("\nASERCIONES: %d\nROJAS: %d" % (ASER, ROJAS))
sys.exit(1 if ROJAS else 0)

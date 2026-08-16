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
    # **Dos, y se sabe cuál es cada uno.** Hasta el 2026-08-15 era uno solo:
    # `_abrir`, que lee los `.json` chicos. El segundo es `_cola`, que abre la
    # transcripción y lee sólo los últimos bytes. Que sean funciones distintas
    # —y que el arnés cuente exactamente dos— es lo que permite decir en una
    # línea qué abre cada una; con los dos adentro de la misma, «capataz lee la
    # cola y nada más» sería un comentario en vez de una afirmación.
    # **Tres, y se sabe cuál es cada uno.** El tercero llegó el 2026-08-15 con
    # `rama_de`, que lee `<cwd>/.git/HEAD` —21 a 34 bytes— para saber en qué
    # rama trabaja una sesión. Es el **único archivo que este módulo abre fuera
    # de `~/.claude`**, y por eso tiene su propia compuerta: la ruta se arma
    # acá, así que por más que el `cwd` venga de un archivo ajeno, lo que se
    # abre no puede ser otra cosa.
    igual("taller.py abre archivos en exactamente cuatro lugares",
          nombres.count("io.open"), 4)
    funciones = {n.name: n for n in ast.walk(arbol)
                 if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    for cual in ("_abrir", "_cola", "rama_de", "autor_de"):
        af("«%s» existe" % cual, cual in funciones)
        adentro = [nombre_de(n) for n in ast.walk(funciones[cual])
                   if isinstance(n, ast.Call)]
        igual("y %s abre exactamente uno" % cual, adentro.count("io.open"), 1)
    # Y que la cola sea cola: un `seek` y una lectura acotada. Sin esto, `_cola`
    # podría leer una transcripción de 13 MB entera y el arnés no se enteraría.
    cuerpo_cola = [nombre_de(n) for n in ast.walk(funciones["_cola"])
                   if isinstance(n, ast.Call)]
    af("_cola se posiciona con seek en vez de leer el archivo entero",
       "f.seek" in cuerpo_cola, cuerpo_cola)
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

    # -----------------------------------------------------------------------
    print("§ 7 · Qué está haciendo — y lo que NO puede salir de la cola")
    # -----------------------------------------------------------------------
    #
    # Desde el 2026-08-15 este módulo abre la transcripción, que es lo que hasta
    # ese día prometía no hacer. La promesa no se borró: se hizo más chica —sólo
    # la cola, y sólo la lista blanca— y esta sección es lo que la sostiene.
    #
    # La aserción que vale es el **señuelo**: se planta una transcripción con un
    # secreto adentro del `command` de un Bash y se exige que no aparezca en
    # ninguna parte de lo que capataz devuelve. Una lista blanca que no se
    # ejercita con algo que tiene que quedar afuera no es una lista blanca.

    SECRETO = "ghp" + "_" + "S3CRET" + "0" * 30
    TEXTO_PRIVADO = "el contenido del archivo que el agente leyó"
    # **El señuelo que de verdad prueba la lista blanca.** El de arriba tiene
    # forma de token, así que si se escapara lo taparía `limpiar_secreto` y la
    # aserción pasaría **igual con el `command` adentro de la lista blanca** —se
    # midió: puesto ese bug, el secreto salía como «token» y sólo se caía otra
    # aserción—. Éste no tiene forma de nada: si aparece, es porque el `command`
    # salió, y no hay red que lo ataje.
    CANARIO = "canario-que-viaja-adentro-del-command"
    cola = os.path.join(VIVOS, "agent-aaaa1.jsonl")
    with io.open(cola, "w", encoding="utf-8") as f:
        f.write(json.dumps({"type": "assistant", "message": {"role": "assistant",
                "content": [{"type": "text", "text": TEXTO_PRIVADO}]}}) + "\n")
        f.write(json.dumps({"type": "assistant", "message": {"role": "assistant",
                "content": [{"type": "tool_use", "name": "Bash",
                             "input": {"command": "curl %s -H 'token: %s'"
                                                  % (CANARIO, SECRETO),
                                       "description": "Desplegar a QAS"}}]}}) + "\n")
        f.write(json.dumps({"type": "user", "message": {"role": "user",
                "content": [{"type": "tool_result", "content": TEXTO_PRIVADO}]}}) + "\n")

    que, sobre, motivo = taller.que_hace(cola, FALSO)
    igual("dice qué herramienta usó", que, "Bash")
    igual("y sobre qué, con la descripción escrita para una persona",
          sobre, "Desplegar a QAS")
    todo = json.dumps([que, sobre, motivo], ensure_ascii=False)
    af("el `command` del Bash NO sale — el canario que viajaba adentro no aparece",
       CANARIO not in todo, todo[:120])
    af("ni el secreto que tenía", SECRETO not in todo, todo[:120])
    af("y el texto de los mensajes tampoco", TEXTO_PRIVADO not in todo, todo[:120])
    # Y lo mismo sobre la vista entera, que es lo que viaja a la pantalla: si un
    # campo nuevo lo arrastrara sin querer, acá se ve.
    vista_json = json.dumps(taller.leer(FALSO, HOY), ensure_ascii=False, default=str)
    af("ni por la vista entera se escapa el secreto", SECRETO not in vista_json)
    af("ni el contenido de un tool_result", TEXTO_PRIVADO not in vista_json)

    # La ruta sale como **basename**: ni la carpeta ni la ruta entera.
    con_ruta = os.path.join(VIVOS, "agent-aaaa2.jsonl")
    with io.open(con_ruta, "w", encoding="utf-8") as f:
        f.write(json.dumps({"type": "assistant", "message": {"role": "assistant",
                "content": [{"type": "tool_use", "name": "Edit",
                             "input": {"file_path": "/Users/secreta/Proyectos/x/lector.py",
                                       "old_string": TEXTO_PRIVADO}}]}}) + "\n")
    que2, sobre2, _ = taller.que_hace(con_ruta, FALSO)
    igual("de una ruta sale sólo el nombre del archivo", (que2, sobre2),
          ("Edit", "lector.py"))
    af("el `old_string` de un Edit no sale",
       TEXTO_PRIVADO not in json.dumps([que2, sobre2]))

    # Sin herramientas en la cola no se inventa nada: es la regla 3 en chico.
    pensando = os.path.join(VIVOS, "agent-aaaa3.jsonl")
    with io.open(pensando, "w", encoding="utf-8") as f:
        f.write(json.dumps({"type": "assistant", "message": {"role": "assistant",
                "content": [{"type": "text", "text": "pensando"}]}}) + "\n")
    q3, s3, m3 = taller.que_hace(pensando, FALSO)
    igual("sin ninguna herramienta en la cola, no se afirma nada", (q3, s3), ("", ""))
    af("y el motivo dice que puede estar pensando", "pensando" in m3, m3)

    # La cola es cola: un archivo grande no se lee entero, y lo viejo no llega.
    grande = os.path.join(VIVOS, "agent-aaaa4.jsonl")
    with io.open(grande, "w", encoding="utf-8") as f:
        f.write(json.dumps({"type": "assistant", "message": {"role": "assistant",
                "content": [{"type": "tool_use", "name": "HerramientaVieja",
                             "input": {"description": "esto quedó muy atrás"}}]}}) + "\n")
        f.write(" " * (taller.COLA_BYTES * 2) + "\n")
        f.write(json.dumps({"type": "assistant", "message": {"role": "assistant",
                "content": [{"type": "tool_use", "name": "HerramientaNueva",
                             "input": {"description": "lo último"}}]}}) + "\n")
    q4, _s4, _m4 = taller.que_hace(grande, FALSO)
    igual("de un archivo grande sale lo último, no lo primero",
          q4, "HerramientaNueva")
    af("y el archivo pesa más que la cola, así que no se leyó entero",
       os.path.getsize(grande) > taller.COLA_BYTES * 2)

    # **Dos herramientas adentro de la MISMA cola**, que es lo que verifica que
    # se camine para atrás. La de arriba no lo hacía: la vieja quedaba fuera de
    # los 64 KB, así que caminar para adelante o para atrás daba lo mismo y la
    # aserción pasaba con el bug puesto. Se midió.
    dos = os.path.join(VIVOS, "agent-aaaa5.jsonl")
    with io.open(dos, "w", encoding="utf-8") as f:
        for nombre in ("Primera", "Segunda"):
            f.write(json.dumps({"type": "assistant", "message": {"role": "assistant",
                    "content": [{"type": "tool_use", "name": nombre,
                                 "input": {"description": nombre}}]}}) + "\n")
    q5, _s5, _m5 = taller.que_hace(dos, FALSO)
    igual("con dos herramientas en la misma cola, se devuelve la última", q5, "Segunda")

    # La compuerta de `_cola`: la misma carpeta, y sólo `.jsonl`.
    for malo, porque in ((os.path.join(RAIZ, "lector.py"), "está fuera del taller"),
                         (os.path.join(VIVOS, "agent-aaaa1.meta.json"), "no es .jsonl")):
        try:
            taller._cola(malo, FALSO)
            af("_cola tendría que rechazar %s (%s)" % (malo, porque), False)
        except taller.FueraDelTaller:
            af("_cola rechaza lo que %s" % porque, True)

    # -----------------------------------------------------------------------
    # La rama: 34 bytes que asocian esta sesión con su renglón en GitHub
    # -----------------------------------------------------------------------
    #
    # Es el único archivo que este módulo abre fuera de `~/.claude`, así que lo
    # que hay que verificar es sobre todo **qué NO abre**: la ruta se arma acá
    # y no puede terminar en otra cosa que `<cwd>/.git/HEAD`.
    REPO = os.path.join(FALSO, "un-repo")
    os.makedirs(os.path.join(REPO, ".git"), exist_ok=True)
    with io.open(os.path.join(REPO, ".git", "HEAD"), "w", encoding="utf-8") as f:
        f.write("ref: refs/heads/t10-mirar-la-nube\n")
    igual("de .git/HEAD sale el nombre de la rama", taller.rama_de(REPO),
          "t10-mirar-la-nube")

    # Un HEAD desprendido trae un sha, y **un sha no es una rama**: se dice que
    # no se sabe en vez de poner cuarenta caracteres de hexadecimal en un
    # teléfono.
    with io.open(os.path.join(REPO, ".git", "HEAD"), "w", encoding="utf-8") as f:
        f.write("9f1c0a2b3d4e5f60718293a4b5c6d7e8f9012345\n")
    igual("un HEAD desprendido no se muestra como rama", taller.rama_de(REPO), "")

    # Y lo que no se puede leer no inventa nada.
    igual("una carpeta que no es repositorio da vacío",
          taller.rama_de(os.path.join(FALSO, "no-existe")), "")
    igual("una ruta relativa no se lee", taller.rama_de("relativa/de/mentira"), "")
    igual("y un cwd vacío tampoco", taller.rama_de(""), "")

    # La compuerta que importa: apuntarle **a un archivo** no lo abre, porque la
    # ruta se arma acá. Sin esto, un `cwd` de un archivo ajeno sería una lectura
    # arbitraria del disco.
    SECRETO_FALSO = os.path.join(FALSO, "parece-un-secreto")
    with io.open(SECRETO_FALSO, "w", encoding="utf-8") as f:
        f.write("ref: refs/heads/esto-no-tiene-que-salir\n")
    igual("apuntar a un archivo suelto no lo lee: la ruta se arma acá",
          taller.rama_de(SECRETO_FALSO), "")
    igual("ni apuntando a /etc", taller.rama_de("/etc"), "")

    # El autor, que es de donde sale el rol. Mismo archivo, misma compuerta.
    with io.open(os.path.join(REPO, ".git", "config"), "w", encoding="utf-8") as f:
        f.write("[core]\n\tbare = false\n[user]\n\tname = coder-7\n"
                "\temail = x@y.z\n[remote \"origin\"]\n\turl = https://x/y\n")
    igual("de .git/config sale con qué nombre commitea esa carpeta",
          taller.autor_de(REPO), "coder-7")
    igual("una carpeta sin config no inventa autor",
          taller.autor_de(os.path.join(FALSO, "no-existe")), "")
    igual("y apuntar a un archivo suelto tampoco lo lee",
          taller.autor_de(SECRETO_FALSO), "")
    # Y la deducción que hace que esto sirva: de ese nombre sale el rol.
    import lector as _lector  # noqa: E402
    igual("y de ese nombre se deduce el rol", _lector.rol_de("coder-7"), "coder")
    igual("de un nombre de persona no se deduce ninguno",
          _lector.rol_de("Pablo Silveira"), "")

    # Y contra las carpetas **de verdad**: al menos una sesión de esta máquina
    # tiene que decir en qué rama está, o esto no verifica nada.
    reales = [s for s in taller.leer()["sesiones"] if s.get("rama")]
    af("al menos una sesión real dice en qué rama trabaja", len(reales) >= 1,
       "ninguna: sin esto, la asociación con GitHub no se puede verificar")
    af("y ninguna rama real trae un salto de línea o un `ref:` sin parsear",
       all("\n" not in s["rama"] and not s["rama"].startswith("ref")
           for s in reales), [s["rama"] for s in reales])

    # Contra las transcripciones **de verdad** de esta máquina, que es la lección
    # que dejó `nube.py`: un lector probado sólo contra archivos que él mismo
    # escribió pasa entero con el formato real cambiado.
    real = taller.leer()
    con_que = [s for s in real["sesiones"] if s.get("que")]
    af("y al menos una sesión de verdad dice qué está haciendo",
       len(con_que) >= 1,
       "ninguna de %d: si el formato del .jsonl cambió, esto no verifica nada"
       % len(real["sesiones"]))
    af("lo que dice es un nombre de herramienta, no una frase",
       all(" " not in s["que"] for s in con_que), [s["que"] for s in con_que])
    # El nombre de una herramienta MCP se corta por el separador. Sin esto el
    # chip mide media pantalla de teléfono: se vio mirando, con este nombre.
    igual("una herramienta MCP se muestra por su nombre útil",
          taller._nombre_corto("mcp__Claude_Browser__javascript_tool"),
          "javascript_tool")
    igual("y una que no es MCP no se toca", taller._nombre_corto("Bash"), "Bash")
    # El texto de otro agente viene con markdown, y en una pantalla sale
    # literal: es la misma marca que ya tienen los alcances de los dos módulos.
    igual("los backticks y asteriscos no llegan a la pantalla",
          taller._para_pantalla("declara `conductividad` en **dS**"),
          "declara conductividad en dS")
    largo = taller._para_pantalla("palabra " * 40)
    af("un texto largo se corta con puntos suspensivos",
       largo.endswith("…") and len(largo) <= taller.TOPE_QUE_HACE + 1, largo)
    af("y se corta en un espacio, no en el medio de una palabra",
       "palabr…" not in largo, largo)
    af("ninguna de las de verdad pasa de 40 caracteres",
       all(len(s["que"]) <= 40 for s in con_que), [s["que"] for s in con_que])

finally:
    shutil.rmtree(FALSO, ignore_errors=True)

print("\nASERCIONES: %d\nROJAS: %d" % (ASER, ROJAS))
sys.exit(1 if ROJAS else 0)

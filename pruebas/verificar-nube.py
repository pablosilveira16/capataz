#!/usr/bin/env python3
"""El arnés de la nube: capataz leyendo **GitHub de verdad**.

**Por qué este archivo existe y por qué es el que vale de la tanda.** El riesgo
de un lector de red es que se lo pruebe sólo contra respuestas grabadas: así
pasa entero con la red rota, y eso es el arnés vacuo de la regla 2 de
`CLAUDE.md`. Acá `nube.py` sale a `github.com` y clona los repositorios
vigilados de verdad; si no hay salida, esto se pone **rojo** y no saltea. Un
arnés de red que se saltea cuando no hay red no verifica nada, y además baja el
total sin ponerse rojo, que es la otra forma de mentir.

**El repositorio con el que se verifica siempre es `pablosilveira16/capataz`,
que es público**: no necesita credencial, así que estas aserciones dan lo mismo
en la carpeta de un agente y en el runner del CI. Los demás proyectos vigilados
se miran agrupados —una aserción, no una por proyecto— porque cuántos hay y
cuáles tienen credencial cambia según dónde se corra, y **el total de
aserciones tiene que ser comparable entre una rama y `main`**.

Lo que sí y lo que no:

    § 1  git nunca sale del espejo — la regla 1, donde se hace cumplir
    § 2  se lee GitHub de verdad, y el espejo coincide con `git ls-remote`
    § 3  el contrato entre las dos mitades: la forma que `leer()` devuelve es
         la que `pruebas/verificar-lector.py` supone
    § 4  lo que falla dice la causa, y ningún mensaje lleva un token
    § 5  el espejo es descartable: se borra, se vuelve a leer, sale lo mismo
    § 6  el CI — la única parte que no se puede probar contra la realidad, y
         lo que sí se puede

    python3 pruebas/verificar-nube.py
"""
import io
import json
import os
import re
import shutil
import subprocess
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

# El repositorio público con el que se verifica siempre. Es capataz a sí mismo:
# el único que está garantizado presente y legible desde cualquier lado.
PUBLICO = "pablosilveira16/capataz"

# El caso «no se alcanza sin credencial», que es el que hay que ver en el runner
# del CI, donde `.credenciales/` no existe.
#
# **Se mide cuál sirve, no se supone.** Este arnés declaraba `erp360` como el
# repositorio privado de la casa y el 2026-08-06 se puso rojo en tres
# aserciones: `erp360` es **público**, así que sin credencial se lee igual y el
# caso no ejercitaba nada de lo que decía ejercitar. La premisa había
# envejecido sin que nadie la volviera a mirar, que es la forma que tiene una
# aserción de volverse mentira sin cambiar una línea.
#
# Y no alcanza con cambiar el nombre por otro: si mañana ese otro también se
# hace público, esto volvería al mismo lugar en silencio. Por eso se pregunta
# —una vez, con `git ls-remote` y sin ninguna credencial— y hay una aserción de
# que el repositorio elegido de verdad no se alcanza.
DECLARADO_PRIVADO = "pablosilveira16/erp360"
INALCANZABLE_SEGURO = "pablosilveira16/no-existe-jamas-2026-privado"


def alcanzable_sin_credencial(repo):
    """¿Se lee este repositorio sin ninguna credencial? Medido, no supuesto.

    Sin config global ni de sistema —ahí vive el helper de credenciales de la
    Mac, que si no contestaría por nosotros— y sin prompt: un arnés colgado
    esperando una contraseña es peor que uno que falla.
    """
    entorno = dict(os.environ)
    entorno.update({"GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": "",
                    "GIT_CONFIG_GLOBAL": os.devnull,
                    "GIT_CONFIG_SYSTEM": os.devnull})
    try:
        proceso = subprocess.Popen(
            ["git", "ls-remote", "--exit-code", nube.url_de(repo), "HEAD"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=entorno)
        proceso.communicate(timeout=90)
        return proceso.returncode == 0
    except Exception:
        return False


PRIVADO = (INALCANZABLE_SEGURO if alcanzable_sin_credencial(DECLARADO_PRIVADO)
           else DECLARADO_PRIVADO)


def af(descripcion, condicion, detalle=""):
    global ASER, ROJAS
    if condicion:
        ASER += 1
    else:
        ROJAS += 1
        print("ROJA  %s%s" % (descripcion, ("  →  %s" % detalle) if detalle else ""))


def diferencias(a, b, ruta=""):
    """Los caminos donde dos vistas difieren, con el nombre del campo.

    Comparar dos JSON como cadenas contesta «algo cambió», que en una vista de
    cuarenta campos no alcanza para saber si lo que cambió está bien. Esto
    contesta **cuál**, y por eso la aserción puede ser exacta —«sólo este
    campo»— en vez de tener que aflojarse a «casi lo mismo».
    """
    if isinstance(a, dict) and isinstance(b, dict):
        salida = []
        for k in sorted(set(a) | set(b)):
            salida += diferencias(a.get(k), b.get(k), "%s/%s" % (ruta, k))
        return salida
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        salida = []
        for i in range(len(a)):
            salida += diferencias(a[i], b[i], "%s/%d" % (ruta, i))
        return salida
    return [] if a == b else [ruta or "/"]


def igual(descripcion, obtenido, esperado):
    af(descripcion, obtenido == esperado, "obtuve %r, esperaba %r" % (obtenido, esperado))


BASE = tempfile.mkdtemp(prefix="capataz-espejos-arnes-")
# Los casos que tienen que fallar van a su propia carpeta, **vacía**. Con la
# de arriba pasaba esto: § 3 ya había clonado el repositorio privado con su
# credencial de verdad, así que el caso «privado sin credencial» encontraba el
# espejo hecho y leía perfecto. La aserción pasaba y no verificaba nada — y
# encima habría dado distinto en el CI, donde ese espejo no existe.
SUCIO = tempfile.mkdtemp(prefix="capataz-espejos-fallos-")

try:
    # -----------------------------------------------------------------------
    print("\n§ 1 · git nunca sale del espejo — CLAUDE.md regla 1")
    # -----------------------------------------------------------------------
    #
    # Dos compuertas. La segunda es la que vale: la primera se puede burlar con
    # un subcomando nuevo que parezca inocente, la segunda dice que pase lo que
    # pase lo que se toque va a ser una copia descartable de capataz.
    for prohibido in ("checkout", "push", "commit", "worktree", "gc", "reset",
                      "rebase", "config"):
        try:
            nube._git(os.path.join(BASE, "x.git"), prohibido, "--algo", base=BASE)
            af("«git %s» tendría que estar prohibido" % prohibido, False)
        except nube.FueraDelEspejo:
            af("«git %s» rechazado por subcomando" % prohibido, True)

    for afuera in (RAIZ, os.path.dirname(RAIZ), "/tmp", os.path.join(BASE, "..")):
        try:
            nube._git(afuera, "log", "-1", base=BASE)
            af("git contra %s tendría que estar prohibido" % afuera, False)
        except nube.FueraDelEspejo:
            af("git contra %s rechazado por destino" % afuera, True)
    try:
        nube._git(os.path.join(BASE, "..", "..", "etc"), "clone", "x", base=BASE)
        af("un destino con «..» tendría que estar prohibido", False)
    except nube.FueraDelEspejo:
        af("un destino con «..» que se escapa del espejo, rechazado", True)

    # Y que la compuerta no sea tan celosa que no deje leer el espejo propio.
    # Sin esto, § 1 pasaría igual con un `_git()` que rechaza todo.
    af("un destino adentro del espejo NO se rechaza",
       nube._dentro(os.path.join(BASE, "algo.git"), BASE))

    # El código, además de la ejecución: que no haya ningún `subprocess` fuera
    # de `_git()`, que es el único lugar donde están las dos compuertas.
    import ast
    fuente = io.open(os.path.join(RAIZ, "nube.py"), encoding="utf-8").read()
    corridas = [n.lineno for n in ast.walk(ast.parse(fuente))
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr in ("run", "Popen", "call", "check_output")]
    igual("el único subprocess de nube.py está adentro de _git()",
          len(corridas), 1)

    # -----------------------------------------------------------------------
    print("§ 2 · Se lee GitHub de verdad — %s" % PUBLICO)
    # -----------------------------------------------------------------------
    proy = {"nombre": "Capataz", "repo": PUBLICO,
            "seguimiento": "SEGUIMIENTO.md", "roles": "ops/60-roles.md",
            "total_aserciones": "pruebas/total-aserciones.txt",
            "rama_principal": "main"}
    t0 = time.time()
    datos = nube.leer(proy, base=BASE, ahora=HOY)
    tardo = time.time() - t0

    if not datos["ok"]:
        print("        %s" % datos["error"])
        print("        Este arnés necesita salida a github.com por HTTPS. Si no")
        print("        la hay, ROJO es el resultado correcto: un lector de red")
        print("        sin red no está verificado. No es un salteo.")
    af("el repositorio público se leyó de GitHub, sin credencial",
       datos["ok"], datos["error"])
    af("y tardó menos de 40 s — si no, el poll de 15 s no sirve", tardo < 40,
       "%.1f s" % tardo)
    print("       %s leído en %.1f s" % (PUBLICO, tardo))

    if datos["ok"]:
        # --- el espejo dice lo mismo que el remoto, preguntado aparte --------
        #
        # Ésta es la aserción que prueba que se habló con GitHub y no con una
        # copia vieja: `git ls-remote` es una **segunda** llamada de red, por
        # otro camino, y los SHA tienen que coincidir uno a uno.
        crudo = subprocess.run(
            ["git", "ls-remote", "--heads", nube.url_de(PUBLICO)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=45,
            env=dict(os.environ, GIT_TERMINAL_PROMPT="0")).stdout.decode()
        del_remoto = {}
        for linea in crudo.splitlines():
            p = linea.split()
            if len(p) == 2 and p[1].startswith("refs/heads/"):
                del_remoto[p[1][len("refs/heads/"):]] = p[0][:7]
        del_espejo = dict((r["nombre"], r["sha"]) for r in datos["ramas"])
        af("ls-remote encontró al menos una rama (si no, no se comparó nada)",
           len(del_remoto) >= 1, len(del_remoto))
        igual("las ramas del espejo son exactamente las del remoto",
              sorted(del_espejo), sorted(del_remoto))
        igual("y cada una está en el mismo commit que en GitHub",
              del_espejo, del_remoto)
        print("       %d ramas en %s: %s" %
              (len(del_remoto), PUBLICO, ", ".join(sorted(del_remoto))))

        # --- el seguimiento, bajado de la rama principal ---------------------
        texto = (datos["archivos"]["seguimiento"] or {}).get("texto")
        af("bajó el SEGUIMIENTO.md de main, y no está vacío",
           bool(texto) and len(texto) > 2000, len(texto or ""))
        af("y es el archivo de capataz, no otro",
           bool(texto) and "Capataz — Seguimiento" in texto)

        # **Los dos conteos.** El de capataz sale de `analizar_seguimiento`, que
        # arma tablas; éste sale de un regex por línea, que es otro algoritmo.
        # Si los dos dan lo mismo sobre el MISMO texto real, el parser no se
        # está inventando puntos ni perdiéndolos.
        #
        # **Y el conteo a mano mira la última celda, no el renglón entero.** La
        # primera versión buscaba `en curso (` en toda la línea y se puso roja
        # el 2026-08-17 con tres puntos —T3, T10b y T32— que **hablan de** un
        # `en curso (fulano)` en su título mientras su estado dice otra cosa. La
        # roja era del arnés, que es la primera hipótesis cuando un arnés falla:
        # capataz leía bien y el que confundía una frase con un estado era el
        # que verifica. Es la misma trampa que ya se había comido a
        # `verificar-angosto.py` con el comentario que explica que no hay
        # tablas.
        #
        # Sigue siendo otro algoritmo —una expresión regular por línea, sin
        # armar ninguna tabla ni mirar encabezados—, que es lo que hace que
        # comparar los dos signifique algo.
        vista = lector.mirar(proy, datos, HOY)
        a_mano_pablo = set()
        a_mano_curso = set()
        filas_vistas = 0
        for linea in (texto or "").splitlines():
            if not linea.strip().startswith("|"):
                continue
            m = re.match(r"^\|\s*([A-Za-z]{1,4}\d+[a-z]?)\s*\|", linea)
            if not m:
                continue
            celdas = [c.strip() for c in linea.strip().strip("|").split("|")]
            if len(celdas) < 2:
                continue
            filas_vistas += 1
            estado = celdas[-1]
            if re.search(r"pendiente\s*\(\s*Pablo", estado, re.I):
                a_mano_pablo.add(m.group(1))
            if re.search(r"en curso\s*\(", estado, re.I):
                a_mano_curso.add(m.group(1))
        af("el conteo a mano encontró filas que comparar (si no, no compara nada)",
           filas_vistas >= 10, filas_vistas)
        af("y encontró al menos un «pendiente (Pablo)» de verdad",
           len(a_mano_pablo) >= 1, sorted(a_mano_pablo))
        # El de `en curso` **puede dar cero y no es un hueco**: depende de si en
        # este momento hay alguien con un punto tomado en `main`. Lo que sostiene
        # esa comparación cuando da vacía es la de arriba —el mismo camino de
        # código, ejercitado con datos— y la § 2 de `verificar-lector.py`, que
        # tiene dos `en curso` escritos a mano y contados a mano.
        igual("los «pendiente (Pablo)»: capataz y el conteo a mano coinciden",
              sorted(p["id"] for p in vista["pendientes_de_pablo"]),
              sorted(a_mano_pablo))
        igual("los «en curso»: capataz y el conteo a mano coinciden",
              sorted(p["id"] for p in vista["en_curso"]),
              sorted(a_mano_curso))
        print("       pendiente (Pablo): %d · en curso: %d · pendiente: %d · "
              "diferido: %d · hechos en la historia: %d" %
              (len(vista["pendientes_de_pablo"]), len(vista["en_curso"]),
               vista["cuenta_abiertos"]["pendiente"],
               vista["cuenta_abiertos"]["diferido"],
               vista["cuenta_total"]["hecho"]))

        # --- el total medido de cada rama, leído de la nube ------------------
        principal = [r for r in datos["ramas"] if r["es_principal"]]
        af("main está entre las ramas", len(principal) == 1)
        if principal:
            af("y trae el total de aserciones MEDIDO que dejó su verificar.sh",
               isinstance(principal[0]["total"], int) and principal[0]["total"] > 100,
               principal[0]["total"])
            print("       total de aserciones de main, leído de GitHub: %s"
                  % principal[0]["total"])

        # --- los commits recientes, con autor --------------------------------
        af("bajaron commits recientes", len(datos["commits"]) >= 5,
           len(datos["commits"]))
        af("cada uno con autor, fecha y asunto",
           all(c["autor"] and c["ts"] and c["asunto"] for c in datos["commits"]))
        af("y las fechas son del pasado, no del futuro",
           all(c["ts"] <= HOY + 60 for c in datos["commits"]))
        autores = sorted(set(c["autor"] for c in datos["commits"]))
        af("de ahí sale la cuadrilla real: hay al menos un autor",
           len(autores) >= 1, autores)
        print("       %d commits, autores: %s" % (len(datos["commits"]),
                                                  ", ".join(autores)))

        # --- prendido o caído, sobre las ramas de verdad ---------------------
        estados = sorted(set(r["estado"] for r in vista["ramas"]))
        af("cada rama real quedó clasificada con una palabra del vocabulario",
           all(e in ("principal", "integrada", "trabajando", "dudoso",
                     "caído", "no sé") for e in estados), estados)
        af("y ninguna rama real quedó sin fecha del último commit",
           all(r["ts"] for r in datos["ramas"]))
        print("       ramas por estado: %s" %
              ", ".join("%s=%s" % (r["nombre"], r["estado"])
                        for r in vista["ramas"]))

    # -----------------------------------------------------------------------
    print("§ 3 · El contrato entre las dos mitades")
    # -----------------------------------------------------------------------
    #
    # `pruebas/verificar-lector.py` arma a mano un diccionario con la forma que
    # `nube.leer()` devuelve. Si las dos formas se separan, aquel arnés seguiría
    # verde verificando un diccionario que ya no existe — el arnés vacuo más
    # difícil de ver, porque no se rompe nada. Esto lo ata.
    ESPERADAS = ("repo", "url", "ok", "error", "leido_en", "espejo", "archivos",
                 "ramas", "commits")
    faltan = [k for k in ESPERADAS if k not in datos]
    af("leer() devuelve todas las claves que el arnés del lector supone",
       not faltan, faltan)
    if datos["ramas"]:
        DE_RAMA = ("nombre", "es_principal", "punto", "sha", "ts", "autor",
                   "asunto", "commits_adelante", "commits_atras", "total",
                   "total_main", "delta", "motivo_sin_total")
        faltan_r = [k for k in DE_RAMA if k not in datos["ramas"][0]]
        af("y cada rama trae todas las claves que la pantalla dibuja",
           not faltan_r, faltan_r)
    af("una rama real pasa por estado_rama() sin reventar",
       lector.estado_rama(dict(datos["ramas"][0]), HOY) if datos["ramas"]
       else False)

    # Y los proyectos vigilados de verdad, **agrupados en una aserción**: cuáles
    # hay y cuáles tienen credencial acá cambia según dónde se corra, y el total
    # de aserciones no puede depender de eso (es la lección del punto R4).
    reales = lector.leer_proyectos(os.path.join(RAIZ, "proyectos.json"))
    con_repo = [p for p in reales if p["repo"]]
    malos = []
    for p in con_repo:
        d = nube.leer(p, base=BASE, ahora=HOY)
        if not d["ok"] and not os.path.isfile(nube._archivo_token(p)):
            continue          # sin credencial acá: § 4 se ocupa de ese caso
        if not d["ok"]:
            malos.append("%s: %s" % (p["nombre"], d["error"][:80]))
    af("cada proyecto vigilado con credencial disponible se leyó de GitHub "
       "(%d con repo)" % len(con_repo), not malos, "; ".join(malos))

    # -----------------------------------------------------------------------
    print("§ 4 · Lo que falla, falla diciendo la causa — y sin el token")
    # -----------------------------------------------------------------------
    #
    # Los cuatro casos que la pantalla tiene que distinguir de «no hay nada
    # pendiente», que es lo que se ve si esto devuelve vacío en silencio.
    casos = [
        ("una ruta donde va un owner/repo",
         {"nombre": "Mal", "repo": "../Finca360"}, "owner/repo"),
        ("una URL entera donde va un owner/repo",
         {"nombre": "Mal", "repo": "https://github.com/pablosilveira16/capataz"},
         "owner/repo"),
        ("un repositorio que no existe",
         {"nombre": "Fantasma", "repo": "pablosilveira16/no-existe-jamas-2026",
          "token": "no-existe.token"}, "github.com"),
        # Sin credencial que lo alcance: el caso del runner del CI, donde
        # `.credenciales/` no existe. Se lo fuerza acá, así se ejercita igual
        # en la Mac. Cuál es el repositorio se decidió arriba, midiendo.
        ("un repositorio que no se alcanza sin credencial",
         {"nombre": "Inalcanzable", "repo": PRIVADO, "token": "no-existe.token"},
         "github.com"),
    ]

    # La aserción que hace que el caso de arriba no sea vacuo. Sin ella, el día
    # que ese repositorio se vuelva público las cuatro aserciones de su caso
    # empiezan a mentir y nadie se entera; con ella, se pone roja acá.
    af("el caso «no se alcanza sin credencial» se ejercita contra un "
       "repositorio que de verdad no se alcanza — medido, no supuesto",
       not alcanzable_sin_credencial(PRIVADO), PRIVADO)
    if PRIVADO != DECLARADO_PRIVADO:
        print("       nota: %s se lee sin credencial —es público— así que el "
              "caso va contra %s" % (DECLARADO_PRIVADO, PRIVADO))

    def fallar(p, i):
        """Leer con espejo vacío y sin ninguna credencial a mano."""
        rincon = os.path.join(SUCIO, "caso%d" % i)
        return nube.leer(p, base=rincon,
                         token_base=os.path.join(SUCIO, "sin-token"), ahora=HOY)

    for i, (etiqueta, p, esperado) in enumerate(casos):
        d = fallar(p, i)
        af("%s: no se lee, y no queda como vacío" % etiqueta, not d["ok"])
        af("%s: el error dice qué buscó" % etiqueta,
           esperado in d["error"], d["error"][:160])
        v = lector.mirar(p, d, HOY)
        af("%s: la pantalla lo ve como error y no como cero puntos" % etiqueta,
           v["seguimiento"]["existe"] is False and bool(v["seguimiento"]["error"]),
           v["seguimiento"]["error"][:120])
        af("%s: y las ramas quedan en «no sé», no en lista vacía" % etiqueta,
           v["ramas"] is None, v["ramas"])
    print("       ejemplo: %s"
          % fallar({"repo": PRIVADO, "token": "no-existe.token"}, 99)["error"][:150])

    # Nada con forma de token puede salir en un mensaje que va a la pantalla.
    #
    # **El señuelo se arma en pedazos a propósito.** Escrito de una pieza,
    # `pruebas/verificar-credenciales.py` lo encuentra —busca esa forma en todo
    # archivo versionado **y en toda la historia**— y se pone rojo con razón: no
    # tiene forma de distinguir un señuelo de un token filtrado, y no debería
    # tenerla, porque una lista de excepciones es exactamente por donde se
    # escapa el primero de verdad. Pasó el 2026-08-06 al escribir esta línea:
    # dos rojas, y las dos correctas.
    FALSO = "github_" + "pat_" + "11ABCDEFG0123456789_abcdefghijklmnopqrs"
    af("un mensaje con algo con forma de PAT sale tapado",
       FALSO not in nube.limpiar_secreto("fatal: %s no sirve" % FALSO))
    af("y se ve que algo se tapó, en vez de desaparecer sin decirlo",
       "«token»" in nube.limpiar_secreto("fatal: %s no sirve" % FALSO))
    VIEJO = "ghp" + "_" + "0123456789abcdefghij"   # en pedazos, por lo mismo
    af("también las formas viejas de token (ghp_…)",
       "ghp_" not in nube.limpiar_secreto("x %s y" % VIEJO))
    af("y un texto sin credencial no se toca",
       nube.limpiar_secreto("todo bien") == "todo bien")
    todos_los_errores = " ".join(
        [datos.get("error", "")] +
        [fallar(p, i)["error"] for i, (_, p, _) in enumerate(casos)])
    af("ningún error de los que se acaban de producir lleva un token adentro",
       not re.search(r"gh[pousr]_|github_pat_", todos_los_errores))

    # -----------------------------------------------------------------------
    print("§ 5 · El espejo es descartable — no es un estado propio")
    # -----------------------------------------------------------------------
    #
    # La regla 1 prohíbe que capataz sea fuente de verdad de algo. El espejo
    # escribe en disco, así que hay que poder demostrar que lo que hay adentro
    # es **derivado**: se borra entero, se vuelve a leer y tiene que salir lo
    # mismo. Si algo viviera sólo ahí, esta aserción se pondría roja.
    if datos["ok"]:
        primera = lector.mirar(proy, datos, HOY)
        carpeta = nube.carpeta_de(PUBLICO, BASE)
        af("el espejo está adentro de la carpeta de espejos y no en otro lado",
           nube._dentro(carpeta, BASE), carpeta)
        af("y existe en disco antes de borrarlo", os.path.isdir(carpeta))
        shutil.rmtree(carpeta)
        af("borrado", not os.path.isdir(carpeta))
        de_nuevo = lector.mirar(proy, nube.leer(proy, base=BASE, ahora=HOY), HOY)
        # Se comparan los CAMINOS que difieren y no dos cadenas: así la
        # aserción dice **qué** cambió en vez de «algo cambió», y no se puede
        # aflojar sin que se note. Lo único que puede cambiar es la marca de
        # cuándo se trajo el espejo —un hecho del espejo, no un dato de
        # GitHub—: un clon nuevo se acaba de traer. Cualquier otro camino en
        # esta lista significa que un dato vivía sólo adentro del espejo, que
        # es exactamente lo que la regla 1 prohíbe.
        igual("borrar el espejo entero y volver a leer da lo mismo, salvo "
              "cuándo se lo trajo",
              diferencias(primera, de_nuevo), ["/nube/traido_en"])

        # Y el camino del `fetch`, que es el que corre siempre después de la
        # primera vez: con `refresco=0` se fuerza y tiene que dar lo mismo.
        refrescado = lector.mirar(
            proy, nube.leer(proy, base=BASE, ahora=HOY, refresco=0), HOY)
        igual("refrescar un espejo que ya estaba también da lo mismo",
              diferencias(primera, refrescado), ["/nube/traido_en"])
        af("y capataz no escribió nada afuera de su carpeta de espejos",
           sorted(os.listdir(BASE)) ==
           sorted([os.path.basename(nube.carpeta_de(p["repo"], BASE))
                   for p in con_repo
                   if os.path.isdir(nube.carpeta_de(p["repo"], BASE))]),
           sorted(os.listdir(BASE)))

    # -----------------------------------------------------------------------
    print("§ 5b · Leer el espejo NO es hablar con GitHub")
    # -----------------------------------------------------------------------
    #
    # La pantalla muestra hace cuánto se leyó GitHub, y esa frescura tiene que
    # ser la del `fetch` y no la del vistazo al espejo: el espejo se lee en
    # **cada** pedido de la pantalla —una vez por segundo— y la red se toca cada
    # `REFRESCO`. Con la marca equivocada el tablero decía «GitHub leído hace
    # 1 s» para siempre, que es la regla 3 rota justo en el dato que dice si
    # creerle al resto de la pantalla.
    if datos["ok"]:
        uno = nube.leer(proy, base=BASE, ahora=HOY)
        af("una lectura deja la marca de cuándo se habló con GitHub",
           uno.get("traido_en") is not None)
        dos = nube.leer(proy, base=BASE, ahora=HOY + 5)
        igual("volver a leer el espejo NO mueve esa marca: no se fue a la red",
              dos["traido_en"], uno["traido_en"])
        af("y en cambio sí mueve la de cuándo se leyó — son dos cosas distintas "
           "y confundirlas es lo que hacía que la pantalla dijera «hace 1 s» "
           "aunque el último fetch fuera de hace quince segundos",
           dos["leido_en"] > uno["leido_en"],
           (uno["leido_en"], dos["leido_en"]))
        tres = nube.leer(proy, base=BASE, ahora=HOY, refresco=0)
        af("forzar el refresco sí la mueve para adelante: eso es hablar con "
           "GitHub", tres["traido_en"] >= uno["traido_en"],
           (uno["traido_en"], tres["traido_en"]))

    # -----------------------------------------------------------------------
    print("§ 5c · El espejo que el limpiador de temporales dejó a medias")
    # -----------------------------------------------------------------------
    #
    # Encontrado el 2026-08-15 **mirando la pantalla**, no acá: los tres
    # proyectos aparecían ilegibles con un gruñido de git —«not a git
    # repository»— y el motivo era que `/var/folders/…/T` es temporal de verdad.
    # macOS le borra los archivos viejos por antigüedad y **deja los
    # directorios**, así que los espejos quedaron con `objects/` y `refs/` pero
    # sin `HEAD` ni `config`. Capataz decidía «ya está clonado» mirando si
    # existía la carpeta `objects/`, hacía `fetch` contra el esqueleto, y no se
    # recuperaba nunca: ni reiniciando, porque la carpeta seguía ahí.
    #
    # Este arnés no lo podía ver, y ése es el punto: cada corrida clona en un
    # `mkdtemp` nuevo, o sea siempre en el caso feliz. **Un espejo de un día
    # para el otro era un camino que ninguna aserción recorría.** Acá se
    # reproduce el destripe exacto y se exige que capataz se recupere solo.
    if datos["ok"]:
        destino = nube.carpeta_de(proy["repo"], BASE)
        af("antes del destripe, el espejo es un espejo", nube._es_espejo(destino))
        comidos = []
        for archivo in ("HEAD", "config", "packed-refs", "description"):
            ruta = os.path.join(destino, archivo)
            if os.path.isfile(ruta):
                os.remove(ruta)
                comidos.append(archivo)
        af("el destripe se hizo de verdad: se comieron HEAD y config",
           "HEAD" in comidos and "config" in comidos, comidos)
        af("y las carpetas quedaron, que es lo que hace el limpiador",
           os.path.isdir(os.path.join(destino, "objects")))
        af("capataz ya no lo confunde con un espejo bueno",
           not nube._es_espejo(destino))

        revivido = nube.leer(proy, base=BASE, ahora=HOY, refresco=0)
        af("y al leer, se recupera solo: vuelve a clonar", revivido["ok"],
           (revivido.get("error") or "")[:140])
        texto = ((revivido.get("archivos") or {}).get("seguimiento")
                 or {}).get("texto") or ""
        af("el seguimiento se vuelve a leer entero, no a medias",
           len(texto) > 1000, len(texto))
        af("y el espejo quedó sano otra vez", nube._es_espejo(destino))

    # El borrado llega con compuerta, que es lo que el T14 pedía: es la única
    # escritura destructiva de capataz y no puede apuntar afuera. Sin estas
    # cuatro, el arreglo de arriba sería un `rmtree` suelto en un tablero.
    for afuera in (RAIZ, os.path.dirname(RAIZ), BASE,
                   os.path.join(BASE, "..", "otra-cosa.git")):
        try:
            nube._tirar_espejo_roto(afuera, BASE)
            af("borrar %s tendría que estar prohibido" % afuera, False)
        except nube.FueraDelEspejo:
            af("borrar %s: rechazado" % afuera, True)
        except OSError:
            af("borrar %s: rechazado" % afuera, True)
    # Anti-vacua de las cuatro de arriba: sin esto pasarían con un
    # `_tirar_espejo_roto` que rechaza absolutamente todo y nunca arregla nada.
    sano = os.path.join(BASE, "inventado-para-el-arnes.git")
    os.makedirs(os.path.join(sano, "objects"), exist_ok=True)
    af("y un espejo destripado de los suyos SÍ se tira",
       nube._tirar_espejo_roto(sano, BASE) and not os.path.isdir(sano))
    # Adentro de la carpeta de espejos, pero sin la forma de uno: tampoco. Es la
    # diferencia entre «borro lo mío» y «borro lo que haya en esta carpeta».
    ajeno = os.path.join(BASE, "esto-no-es-un-espejo")
    os.makedirs(ajeno, exist_ok=True)
    try:
        nube._tirar_espejo_roto(ajeno, BASE)
        af("una carpeta sin forma de espejo tendría que estar protegida", False)
    except nube.FueraDelEspejo:
        af("una carpeta adentro del espejo pero sin forma de espejo, no se toca",
           os.path.isdir(ajeno))
    os.rmdir(ajeno)

    # -----------------------------------------------------------------------
    print("§ 6 · El CI — lo grabado, y lo que sí se puede probar acá")
    # -----------------------------------------------------------------------
    #
    # **Esto es el camino (a) y desde el contenedor de un agente no se puede
    # probar contra la realidad.** Las respuestas de `pruebas/grabado/` están
    # escritas a mano a partir de la forma documentada, y ese archivo lo dice en
    # su primera línea. Lo que sí se ejecuta contra la realidad es el otro lado:
    # que desde acá el pedido falle y que fallar termine en «no sé».
    grabado = json.load(io.open(
        os.path.join(AQUI, "grabado", "actions-runs.json"), encoding="utf-8"))
    af("el archivo de respuestas grabadas dice que son grabadas, no capturadas",
       "NO CAPTURADAS" in " ".join(grabado["_leeme"]))

    pedidos = []

    def abrir_falso(clave):
        cuerpo = json.dumps(grabado[clave]).encode("utf-8")

        class Respuesta(object):
            def read(self):
                return cuerpo

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

        def abrir(pedido, timeout=None):
            pedidos.append(pedido)
            return Respuesta()
        return abrir

    r, motivo = nube.pedir_ci(PUBLICO, "main", abrir=abrir_falso("verde"),
                              encendido=True)
    igual("con una respuesta grabada de éxito, el CI se lee verde",
          lector.interpretar_ci(r, motivo)["estado"], "verde")
    r, motivo = nube.pedir_ci(PUBLICO, "t9", abrir=abrir_falso("rojo"),
                              encendido=True)
    igual("con una de fallo, rojo", lector.interpretar_ci(r, motivo)["estado"],
          "rojo")
    r, motivo = nube.pedir_ci(PUBLICO, "main", abrir=abrir_falso("corriendo"),
                              encendido=True)
    igual("con una corriendo, ni verde ni rojo",
          lector.interpretar_ci(r, motivo)["estado"], "corriendo")
    r, motivo = nube.pedir_ci(PUBLICO, "main", abrir=abrir_falso("sin_corridas"),
                              encendido=True)
    igual("sin ninguna corrida, «no sé»",
          lector.interpretar_ci(r, motivo)["estado"], "no sé")
    af("y con el motivo escrito", bool(motivo), motivo)

    # El pedido que saldría a la red, mirado en el mismo objeto que saldría.
    af("se armaron los cuatro pedidos", len(pedidos) == 4, len(pedidos))
    p0 = pedidos[0]
    af("el pedido va a la API de GitHub, al endpoint de corridas",
       p0.full_url.startswith("https://api.github.com/repos/%s/actions/runs"
                              % PUBLICO), p0.full_url)
    af("y filtra por la rama que se le pidió", "branch=main" in p0.full_url,
       p0.full_url)
    af("con la cabecera Accept que la API documenta",
       p0.get_header("Accept") == "application/vnd.github+json")
    af("y la versión de la API fijada, para que un cambio no lo rompa solo",
       bool(p0.get_header("X-github-api-version")))

    # --- y ahora la parte honesta: contra api.github.com de verdad -----------
    t0 = time.time()
    r, motivo = nube.pedir_ci(PUBLICO, "main", encendido=True)
    tardo = time.time() - t0
    alcanza = r is not None
    print("       api.github.com desde acá: %s (%.1f s)" %
          ("contesta" if alcanza else "no se alcanza", tardo))
    if not alcanza:
        # Es el caso medido del contenedor de un agente. Lo que se afirma no es
        # que la API esté caída: es que **cuando no se la alcanza, el resultado
        # es «no sé» con el motivo, y jamás verde**.
        af("sin alcanzar la API, el resultado es «no sé»",
           lector.interpretar_ci(r, motivo)["estado"] == "no sé")
        af("y el motivo nombra api.github.com, que es lo accionable",
           "api.github.com" in motivo, motivo[:160])
        af("y la URL que intentó", "actions/runs" in motivo, motivo[:160])
    else:
        # En la Mac esto sí anda. Que ande no puede volver verde lo que no
        # concluyó: se afirma que la traducción sigue siendo la de siempre, y
        # queda escrito que alguien la alcanzó — que es el punto T11.
        af("alcanzando la API, la respuesta es un diccionario de corrida",
           isinstance(r, dict) and "status" in r, str(r)[:120])
        af("y su traducción es una de las cuatro palabras del vocabulario",
           lector.interpretar_ci(r, motivo)["estado"] in
           ("verde", "rojo", "corriendo", "no sé"))
        af("(T11) la API se alcanzó de verdad desde acá: anotarlo y cerrarlo",
           True)

    # Apagada, que es como corre por defecto: ni siquiera intenta.
    r, motivo = nube.pedir_ci(PUBLICO, "main", encendido=False,
                              abrir=abrir_falso("verde"))
    af("apagada, el CI no sale a la red", len(pedidos) == 4, len(pedidos))
    igual("y el resultado es «no sé», nunca verde",
          lector.interpretar_ci(r, motivo)["estado"], "no sé")
    af("con el motivo que dice cómo prenderla", "CAPATAZ_CI" in motivo, motivo)

finally:
    shutil.rmtree(BASE, ignore_errors=True)
    shutil.rmtree(SUCIO, ignore_errors=True)

print("\nASERCIONES: %d\nROJAS: %d" % (ASER, ROJAS))
sys.exit(1 if ROJAS else 0)

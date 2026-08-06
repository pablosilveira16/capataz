#!/usr/bin/env python3
"""
Arnés de las credenciales
=========================

Vigila la plomería con la que un agente empuja a GitHub sin que Pablo tenga que
estar: `ops/credencial-github.sh`, `ops/empujar.sh`, `ops/70-credenciales.md` y
el remote `origin`.

Traído de `pruebas/verificar-credenciales.py` de ERP 360 (2026-08-06) y
adaptado al repositorio, al nombre del token y a la variable de este proyecto.

**Por qué ejecuta en vez de leer.** Es la regla 2 de `CLAUDE.md`: leer un
archivo y buscar una cadena no prueba que el código corra. Que el helper falle
con un mensaje útil **y no se cuelgue** cuando no hay token sólo se comprueba
corriéndolo con un temporizador; que no le entregue el token a otro host, sólo
hablándole por stdin como le habla git.

Lo que afirma, en orden:

* **El token vive afuera del repo.** No hay ningún `*.token` en el árbol, no hay
  nada de `.credenciales/` versionado, y el archivo por defecto cae fuera de la
  carpeta del repositorio. Es la regla que hace que ningún commit pueda
  llevárselo.
* **`.gitignore` cubre `*.token` y `.credenciales/`** — y no se lee el archivo:
  se le pregunta a git con `git check-ignore`, que es quien decide de verdad.
* **Ningún archivo versionado —ni ningún commit de la historia— tiene algo con
  forma de PAT.**
* **Todo `.sh` versionado viaja con el bit de ejecución en el ÍNDICE.** Es la
  factura de ERP 360, traída ya pagada: sus scripts viajaron sin el bit y el CI
  falló con «Permission denied» en todas las ramas durante un día, sin que nadie
  lo viera.
* **`ops/empujar.sh` tiene las protecciones que no se pueden olvidar**: la
  compuerta de `./verificar.sh`, `GIT_TERMINAL_PROMPT=0`, y el orden correcto
  entre las dos.
* **Está configurado el remote `origin`**, sin credenciales adentro de la URL, y
  el helper enganchado con la ruta **calculada** y no escrita.

    python3 pruebas/verificar-credenciales.py
"""

import io
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PADRE = os.path.dirname(AQUI)

HELPER = os.path.join(AQUI, "ops", "credencial-github.sh")
EMPUJAR = os.path.join(AQUI, "ops", "empujar.sh")
RUNBOOK = os.path.join(AQUI, "ops", "70-credenciales.md")
MAPA = os.path.join(AQUI, "ops", "00-mapa.md")
GITIGNORE = os.path.join(AQUI, ".gitignore")

TOKEN_POR_DEFECTO = os.path.join(PADRE, ".credenciales", "github-capataz.token")
REPO_ESPERADO = "github.com/pablosilveira16/capataz"

# Los prefijos se arman por pedazos y el patrón exige veinte caracteres de cola.
# Las dos cosas son a propósito: si el patrón fuera el prefijo pelado, este
# archivo y `ops/70-credenciales.md` —que tienen que poder nombrarlos para
# explicar qué se busca— dispararían la roja que existe para atrapar un token de
# verdad. Un arnés que no puede documentarse a sí mismo se termina apagando.
PREFIJOS = ["gh" + "p_", "github" + "_pat_", "gh" + "o_", "gh" + "s_", "gh" + "u_"]
PATRON_PAT = re.compile("(" + "|".join(PREFIJOS) + r")[A-Za-z0-9_]{20,}")

verdes = 0
rojas = 0


def ok(_etq):
    global verdes
    verdes += 1


def roja(etq, detalle=""):
    global rojas
    rojas += 1
    print("  ROJA  %s%s" % (etq, (" — %s" % detalle) if detalle else ""))


def afirmar(cond, etq, detalle=""):
    ok(etq) if cond else roja(etq, detalle)


def leer(ruta):
    if not os.path.exists(ruta):
        return ""
    with io.open(ruta, encoding="utf-8", errors="replace") as f:
        return f.read()


def correr(cmd, entrada="", segundos=15, entorno=None, cwd=None):
    """Corre algo con temporizador y devuelve (código, stdout, stderr, colgado).

    Con `start_new_session` y el `killpg`: sin eso, este arnés se cuelga
    justamente cuando lo que verifica se colgó. `subprocess.run` mata al hijo
    cuando vence el plazo, pero después se queda esperando a que se cierren los
    pipes — y si el hijo dejó un nieto vivo (un `git` colgado), el nieto los
    tiene abiertos y nunca se cierran. El temporizador que existe para no
    colgarse cuelga igual.
    """
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, universal_newlines=True,
                         env=entorno, cwd=cwd, start_new_session=True)
    try:
        salida, error = p.communicate(entrada, timeout=segundos)
        return p.returncode, salida, error, False
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(p.pid), signal.SIGKILL)
        except OSError:                                       # pragma: no cover
            p.kill()
        try:
            p.communicate(timeout=10)
        except Exception:                                     # pragma: no cover
            pass
        return None, "", "", True


def git(*args):
    try:
        r = subprocess.run(["git", "-C", AQUI] + list(args),
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           universal_newlines=True, timeout=30)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except Exception as e:                                    # pragma: no cover
        return 1, "", str(e)


# ------------------------------------------------------------------
# 1 · El token vive afuera del repositorio
# ------------------------------------------------------------------
print()
print("1 · El token, afuera del repo")

# Que caiga afuera del árbol no es una preferencia de orden: es lo que hace que
# la regla no dependa de que nadie edite `.gitignore` por accidente.
afirmar(not os.path.abspath(TOKEN_POR_DEFECTO).startswith(os.path.abspath(AQUI) + os.sep),
        "el archivo del token por defecto cae fuera del repositorio",
        TOKEN_POR_DEFECTO)

texto_helper = leer(HELPER)
afirmar(".credenciales/github-capataz.token" in texto_helper,
        "el helper busca el token en ../.credenciales/github-capataz.token",
        "un token, un repositorio: el de ERP 360 no sirve acá")

sueltos = []
for raiz, dirs, archivos in os.walk(AQUI):
    dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", ".venv", "venv")]
    for a in archivos:
        if a.endswith(".token") or a.endswith(".pat"):
            sueltos.append(os.path.relpath(os.path.join(raiz, a), AQUI))
afirmar(not sueltos, "no hay ningún archivo de token dentro del repositorio",
        " ".join(sueltos))

afirmar(not os.path.isdir(os.path.join(AQUI, ".credenciales")),
        "no hay una carpeta .credenciales/ dentro del repositorio",
        "va en la carpeta padre: el repo se clona y se borra, la carpeta padre no")

codigo, versionados, _ = git("ls-files")
lista = [l for l in versionados.splitlines() if l.strip()]
afirmar(codigo == 0 and lista, "git ls-files responde",
        "sin la lista de archivos versionados este arnés no verifica nada")

marcados = [f for f in lista
            if f.endswith(".token") or f.startswith(".credenciales/")
            or "/.credenciales/" in f]
afirmar(not marcados, "no hay ningún token versionado en git", " ".join(marcados))

# ------------------------------------------------------------------
# 2 · `.gitignore`, preguntándole a git
# ------------------------------------------------------------------
print("2 · .gitignore")

ignore = leer(GITIGNORE)


# Anclado a la línea entera y no `"*.token" in ignore`: el archivo tiene un
# comentario que explica por qué están estas dos líneas, y ese comentario las
# nombra. Con la versión floja, borrar el patrón y dejar el comentario da verde.
def patron_en_gitignore(p):
    return any(l.strip() == p for l in ignore.splitlines())


afirmar(patron_en_gitignore("*.token"), ".gitignore ignora *.token")
afirmar(patron_en_gitignore(".credenciales/"), ".gitignore ignora .credenciales/")

# Lo anterior es leer el archivo; esto es preguntarle al que decide. Un patrón
# escrito más abajo que un `!negado`, o con una barra de más, aparece en el texto
# y no ignora nada.
#
# `.credenciales/notas.txt` no termina en `.token` a propósito: con un `.token`
# adentro, el que ignora es `*.token` y la prueba pasa aunque `.credenciales/` no
# esté. Cada patrón se prueba con un caso que sólo él cubre.
for prueba in ("cualquiera.token", ".credenciales/notas.txt",
               "ops/robado.token", ".credenciales/github-capataz.token"):
    c, _o, _e = git("check-ignore", "-q", "--no-index", prueba)
    afirmar(c == 0, "git ignora de verdad «%s»" % prueba,
            "está en el texto de .gitignore pero git no lo ignora")

# ------------------------------------------------------------------
# 3 · Ningún archivo versionado tiene forma de PAT
# ------------------------------------------------------------------
print("3 · Ningún PAT versionado")

con_pat = []
for rel in lista:
    ruta = os.path.join(AQUI, rel)
    if not os.path.isfile(ruta):
        continue
    try:
        with io.open(ruta, encoding="utf-8", errors="ignore") as f:
            contenido = f.read()
    except OSError:
        continue
    m = PATRON_PAT.search(contenido)
    if m:
        con_pat.append("%s:%s…" % (rel, m.group(1)))
afirmar(not con_pat,
        "ningún archivo versionado contiene algo con forma de token de GitHub",
        " ".join(con_pat) + " — revocalo YA en GitHub y después leé ops/70-credenciales.md")

# El mismo patrón, sobre la historia. Un token borrado en el commit siguiente
# sigue estando: `git log -p` lo muestra igual.
c, historia, _e = git("log", "-p", "--all")
enc = PATRON_PAT.search(historia or "")
afirmar(c == 0 and not enc,
        "ningún commit de la historia contiene algo con forma de token",
        (enc.group(1) + "… — hay que revocar el token y reescribir el commit") if enc else "")

# Y la trampa que este mecanismo existe para evitar: el token metido en la URL
# del remote, que git escupe entero en cualquier mensaje de error. El largo
# mínimo deja pasar el `https://TOKEN@github.com` de una explicación y no deja
# pasar un token de verdad, que anda por los noventa caracteres.
URL_CON_CREDENCIAL = re.compile(r"https://[A-Za-z0-9_%.:-]{8,}@github\.com")
urls_con_credencial = [
    rel for rel in lista
    if os.path.isfile(os.path.join(AQUI, rel))
    and URL_CON_CREDENCIAL.search(leer(os.path.join(AQUI, rel)))
]
afirmar(not urls_con_credencial,
        "ningún archivo versionado arma una URL https://algo@github.com",
        " ".join(urls_con_credencial))

# ------------------------------------------------------------------
# 4 · Los `.sh` viajan ejecutables — se mira el ÍNDICE, no el disco
# ------------------------------------------------------------------
#
# `git ls-files -s` dice con qué modo va a viajar el archivo, y eso es lo único
# que no depende de en qué máquina se corra esto. La copia de la Mac está sobre
# una carpeta montada: si esa copia tiene `core.filemode = false`, un `chmod +x`
# de ese lado no llega nunca al índice y el que clona —o el CI— recibe un script
# que no se puede correr. En ERP 360 eso dejó `run: ./verificar.sh` en
# «Permission denied» en TODAS las ramas durante un día, y no se vio porque
# desde el contenedor el resultado del CI no se puede leer.
print("4 · Los .sh, ejecutables en el índice")

codigo, modos, _e = git("ls-files", "-s", "--", "*.sh")
filas = [l.split(None, 3) for l in modos.splitlines() if l.strip()]
afirmar(codigo == 0 and len(filas) >= 3,
        "git ls-files -s encuentra los .sh versionados (al menos 3)",
        "%d encontrados — si es cero, esto no está verificando nada" % len(filas))
sin_bit = [f[3] for f in filas if f and f[0] != "100755"]
afirmar(not sin_bit,
        "todos los .sh versionados tienen el bit de ejecución en el índice",
        " ".join(sin_bit) + " — git update-index --chmod=+x <archivo>")

# Y el chequeo tiene que estar también en `empujar.sh`, que es quien lo aplica
# antes de publicar: un arnés lo atrapa cuando alguien corre la suite, el script
# lo atrapa siempre.
afirmar("ls-files -s" in leer(EMPUJAR),
        "empujar.sh también mira el modo del índice antes de publicar")

# ------------------------------------------------------------------
# 5 · El helper, corriéndolo
# ------------------------------------------------------------------
print("5 · El helper")

afirmar(os.path.exists(HELPER), "ops/credencial-github.sh existe")
afirmar(os.access(HELPER, os.X_OK), "ops/credencial-github.sh es ejecutable",
        "git no lo puede llamar: chmod +x")


def correr_helper(op="get", token=None, host="github.com", segundos=10):
    """Le habla como le habla git: el pedido por stdin, la respuesta por stdout."""
    entorno = dict(os.environ)
    entorno["CAPATAZ_TOKEN"] = token or os.path.join(tempfile.gettempdir(),
                                                     "capataz-no-existe.token")
    entorno.pop("CAPATAZ_EMPUJANDO", None)
    return correr(["bash", HELPER, op], "protocol=https\nhost=%s\n\n" % host,
                  segundos=segundos, entorno=entorno)


# --- sin token: falla, no cuelga, y dice qué hacer ------------------
codigo, salida, error, colgado = correr_helper()
afirmar(not colgado, "sin token el helper NO se cuelga esperando a nadie",
        "quedó colgado: un agente desatendido se queda ahí para siempre")
afirmar(codigo not in (0, None), "sin token el helper falla", "salió %s" % codigo)
afirmar("70-credenciales" in error,
        "el mensaje de falta de token manda al runbook",
        "un error que no dice qué hacer obliga a leer el código para saberlo")
afirmar("Contents" in error and "Read and write" in error,
        "el mensaje nombra el permiso que hace falta")
# `Workflows` es el que a ERP 360 le faltó: GitHub rechaza el push del commit
# que crea `.github/workflows/…` con «refusing to allow a Personal Access Token
# to create or update workflow … without `workflow` scope». Un runbook de
# permisos al que le falta uno hace perder el rato dos veces: la primera creando
# el token y la segunda buscando por qué no anda.
afirmar("Workflows" in error,
        "el mensaje nombra también el permiso Workflows",
        "sin él, el push que toca .github/workflows/ lo rechaza GitHub")
afirmar("password=" not in salida and "username=" not in salida,
        "sin token no contesta ninguna credencial")

# --- con token: contesta el protocolo -------------------------------
FALSO = "token-de-prueba-de-este-arnes-no-sirve-para-nada"
tmp = tempfile.mkdtemp(prefix="capataz-cred-")
ruta_falsa = os.path.join(tmp, "github-capataz.token")
with io.open(ruta_falsa, "w", encoding="utf-8") as f:
    f.write(FALSO + "\n")
os.chmod(ruta_falsa, 0o600)

codigo, salida, error, colgado = correr_helper(token=ruta_falsa)
afirmar(not colgado and codigo == 0, "con token el helper contesta y sale bien",
        "salió %s" % codigo)
afirmar("password=%s" % FALSO in salida, "contesta password= con el token del archivo")
afirmar("username=" in salida, "contesta username=",
        "git exige los dos campos aunque GitHub sólo mire el password")
afirmar(FALSO not in error, "el token no sale nunca por stderr")

# --- un permiso flojo avisa, pero no frena el push -------------------
#
# Las dos mitades importan. La primera porque un token legible por cualquiera es
# un token filtrado a medias; la segunda porque frenar el push por eso haría que
# el aviso se ignore. Y el aviso tiene que ser **una línea**: en ERP 360 la
# primera versión probaba `stat -f` antes que `stat -c`, y en Linux `stat -f`
# existe, significa otra cosa y sale con éxito — el aviso salía con media
# pantalla de bloques e inodos. Un aviso ilegible es un aviso que nadie lee.
os.chmod(ruta_falsa, 0o644)
codigo, salida, error, colgado = correr_helper(token=ruta_falsa)
afirmar(not colgado and codigo == 0 and "password=%s" % FALSO in salida,
        "con permisos flojos avisa pero contesta igual",
        "frenar el push por el chmod haría que el aviso se saltee")
afirmar("600" in error and len(error.strip().splitlines()) == 1,
        "el aviso de permisos es una sola línea y dice el chmod que falta",
        error.strip()[:120])
os.chmod(ruta_falsa, 0o600)

# --- a otro host no le contesta nada --------------------------------
codigo, salida, error, colgado = correr_helper(token=ruta_falsa, host="gitlab.com")
afirmar(not colgado and FALSO not in salida,
        "a un host que no es github.com no le entrega el token",
        "un helper que contesta a cualquiera se lo da al primer remote mal escrito")

# --- store y erase no escriben nada ---------------------------------
codigo, salida, error, colgado = correr_helper(op="store", token=ruta_falsa)
afirmar(not colgado and codigo == 0 and not salida.strip(),
        "«store» no guarda copias del token en ningún lado")

os.remove(ruta_falsa)
os.rmdir(tmp)

# ------------------------------------------------------------------
# 6 · empujar.sh: las protecciones, y corriéndolo
# ------------------------------------------------------------------
print("6 · empujar.sh")

texto_empujar = leer(EMPUJAR)
afirmar(os.path.exists(EMPUJAR), "ops/empujar.sh existe")
afirmar(os.access(EMPUJAR, os.X_OK), "ops/empujar.sh es ejecutable")

afirmar(re.search(r"GIT_TERMINAL_PROMPT=0", texto_empujar) is not None,
        "empujar.sh pone GIT_TERMINAL_PROMPT=0",
        "sin eso, un agente desatendido se cuelga en el prompt de usuario de git")

# La compuerta, en código. No alcanza con nombrar el archivo en un comentario:
# tiene que ejecutarlo y mirar el estado.
compuerta = re.search(r"^[^#\n]*\$\([^)\n]*\./verificar\.sh", texto_empujar, re.M)
afirmar(compuerta is not None,
        "empujar.sh corre ./verificar.sh de verdad, no lo nombra en un comentario")
afirmar("estado_v" in texto_empujar and re.search(r'estado_v.*!=.*"0"', texto_empujar),
        "empujar.sh mira el estado de verificar.sh y frena si no está verde")

# El orden importa y por eso se verifica: si la compuerta corriera ANTES del
# chequeo de credencial, este mismo arnés —que ejecuta empujar.sh unas líneas
# más abajo— dispararía verificar.sh en cascada.
pos_cred = texto_empujar.find("No hay credencial de GitHub")
pos_gate = compuerta.start() if compuerta else -1
afirmar(pos_cred > 0 and pos_gate > pos_cred,
        "empujar.sh chequea la credencial ANTES de correr la compuerta",
        "al revés, el arnés de credenciales dispara verificar.sh en cascada")

afirmar("--tomar" in texto_empujar, "empujar.sh tiene el modo --tomar")
afirmar(re.search(r"HEAD:main", texto_empujar) is not None,
        "el modo --tomar empuja a main")
afirmar("SEGUIMIENTO.md" in texto_empujar and "en curso" in texto_empujar,
        "el modo --tomar exige que el commit sea la marca de «en curso»")
afirmar(re.search(r"non-fast-forward", texto_empujar) is not None,
        "empujar.sh reconoce el rechazo por no-fast-forward")
afirmar(re.search(r"(?i)otro agente tom", texto_empujar) is not None,
        "y lo traduce a «otro agente tomó el punto primero»",
        "ese mensaje es la mitad del mecanismo: sin él el rechazo parece un error de red")
afirmar(re.search(r"(?i)historias no relacionadas", texto_empujar) is not None,
        "y distingue el caso que NO es arbitraje: historias no relacionadas",
        "tratarlo como «otro llegó primero» manda a tirar trabajo válido")

# --- y corriéndolo, sin credencial: falla, no cuelga, y dice dónde leer ---
entorno = dict(os.environ)
entorno["CAPATAZ_TOKEN"] = os.path.join(tempfile.gettempdir(), "capataz-no-existe.token")
entorno.pop("CAPATAZ_EMPUJANDO", None)
codigo, salida, error, colgado = correr(["bash", EMPUJAR], segundos=60,
                                        entorno=entorno, cwd=AQUI)

afirmar(not colgado, "sin credencial empujar.sh NO se cuelga")
afirmar(codigo not in (0, None), "sin credencial empujar.sh se niega a empujar",
        "salió %s" % codigo)
afirmar("70-credenciales" in (salida + error),
        "y manda a leer ops/70-credenciales.md")
afirmar("format-patch" in (salida + error),
        "y recuerda que mientras tanto la entrega es por parche")

# Que se haya negado ANTES de correr la suite: si hubiera corrido la compuerta,
# la salida traería el total de aserciones. Es la prueba de que el orden de
# arriba no es sólo la posición del texto en el archivo.
afirmar("aserciones" not in (salida + error),
        "y se negó ANTES de correr verificar.sh, no después",
        "corrió la suite entera para nada — y desde un arnés, en cascada")

# --- un modo inventado se rechaza, no se trata como el de por defecto ---
codigo, salida, error, colgado = correr(["bash", EMPUJAR, "--publicar"], segundos=30,
                                        entorno=entorno, cwd=AQUI)
afirmar(not colgado and codigo == 2,
        "un modo desconocido sale con 2 y no empuja nada", "salió %s" % codigo)

# ------------------------------------------------------------------
# 7 · El remote
# ------------------------------------------------------------------
print("7 · El remote")

codigo, url, _e = git("remote", "get-url", "origin")
afirmar(codigo == 0 and url, "está configurado el remote origin",
        "sin remoto no hay dónde empujar ni dónde arbitrar")
afirmar(REPO_ESPERADO in (url or ""),
        "origin apunta a %s" % REPO_ESPERADO, url or "(no hay)")
afirmar("@" not in (url or ""),
        "la URL de origin no lleva credenciales adentro",
        "git filtra la URL entera en los mensajes de error: eso publica el token")

# --- una copia recién clonada queda configurada, y sin ruta escrita ---------
#
# **Se prueba sobre un clon de verdad y no sobre este repo**, y el motivo vale
# escribirlo: `.git/config` **no se versiona**. Afirmar sobre el config de la
# copia en la que uno está es afirmar sobre lo que hizo el último que pasó por
# acá — verde en la máquina de quien ya empujó una vez, rojo en un clon nuevo y
# rojo en el CI, sin que nada esté mal. Lo que sí es una propiedad del proyecto
# es que **`ops/empujar.sh` deje andando una copia recién clonada**, y eso se
# comprueba clonando y corriéndolo.
#
# Y la ruta tiene que quedar **calculada** (`git rev-parse`) y no escrita: la
# misma carpeta está montada en dos rutas —`/Users/…` en la Mac, `/sessions/…`
# en el contenedor— y `.git/config` es un solo archivo compartido por las dos.
# Escrita, el último que corriera `ops/empujar.sh` dejaría al otro sin empujar.
clon = tempfile.mkdtemp(prefix="capataz-clon-")
destino = os.path.join(clon, "copia")
c = subprocess.run(["git", "clone", "--quiet", "--no-hardlinks", AQUI, destino],
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
afirmar(c.returncode == 0, "se puede clonar el repositorio",
        c.stderr.decode("utf-8", "replace")[:200])

if c.returncode == 0:
    cc, antes, _e = 0, "", ""
    r = subprocess.run(["git", "-C", destino, "config", "--get",
                        "credential.https://github.com.helper"],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    antes = r.stdout.decode().strip()
    afirmar(not antes, "un clon nuevo no trae NADA configurado",
            "si ya viniera configurado, lo de abajo no probaría nada")

    entorno_clon = dict(os.environ)
    entorno_clon["CAPATAZ_TOKEN"] = os.path.join(tempfile.gettempdir(),
                                                 "capataz-no-existe.token")
    entorno_clon.pop("CAPATAZ_EMPUJANDO", None)
    correr(["bash", os.path.join(destino, "ops", "empujar.sh")],
           segundos=60, entorno=entorno_clon, cwd=destino)

    r = subprocess.run(["git", "-C", destino, "config", "--get",
                        "credential.https://github.com.helper"],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    conf = r.stdout.decode().strip()
    afirmar("ops/credencial-github.sh" in conf,
            "ops/empujar.sh deja el helper enganchado en una copia recién clonada",
            conf or "(nada) — un clon nuevo se quedaría sin poder empujar")
    afirmar(re.match(r"^!?[\"']?/", conf or "!") is None,
            "y lo engancha con la ruta calculada, no escrita",
            conf + " — la carpeta está montada en dos rutas: escribirla rompe la otra")
    afirmar("rev-parse" in conf,
            "…que es literalmente un git rev-parse en el momento de la llamada",
            conf)

subprocess.run(["chmod", "-R", "u+w", clon], stdout=subprocess.PIPE,
               stderr=subprocess.PIPE)
shutil.rmtree(clon, ignore_errors=True)

# ------------------------------------------------------------------
# 8 · El runbook, y quién lo apunta
# ------------------------------------------------------------------
print("8 · El runbook")

runbook = leer(RUNBOOK)
afirmar(bool(runbook), "ops/70-credenciales.md existe")

for frase, etq in [
    ("Contents", "el runbook nombra el permiso Contents"),
    ("Read and write", "…y dice que va en Read and write"),
    ("Metadata", "el runbook nombra Metadata, que es obligatorio"),
    ("Workflows", "el runbook nombra Workflows, sin el cual el push del CI se rechaza"),
    ("without `workflow` scope",
     "…y trae el síntoma exacto, que es lo que alguien va a buscar cuando le pase"),
    ("chmod 600", "el runbook dice el chmod 600"),
    ("pablosilveira16/capataz", "el runbook acota el alcance a un solo repositorio"),
    ("cualquier agente", "el runbook dice con todas las letras quién puede usar el token"),
    ("format-patch", "el runbook trae la alternativa sin token"),
    ("22", "el runbook dice por qué no SSH: el puerto 22 está cerrado"),
    ("api.github.com", "el runbook dice qué NO se alcanza, que es de dónde sale la regla 3"),
]:
    afirmar(frase.lower() in runbook.lower(), etq)

afirmar(re.search(r"(?i)##\s*cómo se revoca", runbook) is not None,
        "el runbook tiene la sección de cómo se revoca",
        "una credencial que no se sabe apagar no se puede haber creado con cuidado")
afirmar(re.search(r"(?i)##\s*si se filtró", runbook) is not None,
        "el runbook dice qué hacer si se filtró")

# El puntero. En ERP 360 vive en `CLAUDE.md`; acá no puede: `CLAUDE.md` tiene un
# tope duro de 72 líneas y está en 72, y las reglas se ganan una por una. El
# lugar de los runbooks es `ops/00-mapa.md`, que además lo verifica
# `pruebas/verificar-contrato.sh` § 5 para los archivos que CLAUDE.md sí nombra.
mapa = leer(MAPA)
afirmar("ops/70-credenciales.md" in mapa,
        "ops/00-mapa.md nombra el runbook de credenciales")

print()
print("ASERCIONES: %d" % verdes)
print("ROJAS: %d" % rojas)
sys.exit(1 if rojas else 0)

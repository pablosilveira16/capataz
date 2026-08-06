# La credencial de GitHub

> Cómo se consigue, dónde vive y cómo se revoca el token con el que un agente
> empuja a `pablosilveira16/capataz`. Lo lee Pablo una vez —para crearlo— y lo
> lee un agente cuando `ops/empujar.sh` le dice que falta.
>
> Traído de `ops/70-credenciales.md` de ERP 360 (2026-08-06) y adaptado. **Un
> token, un repositorio**: el de allá no sirve acá y el de acá no sirve allá, y
> eso es la mitad del punto de que sean *fine-grained*.

## Lo primero, porque es la decisión y no el detalle

**Cualquier agente con acceso a la carpeta `frutos de cuyo` puede usar ese
token.** No hay contraseña, no hay confirmación y no hay nadie mirando: se lee
un archivo y se empuja.

Eso **es el objetivo**, no un descuido. Un token que hay que pasarle a mano a
cada agente en cada sesión es un token que no está cuando la sesión se corta a
las tres de la mañana, y entonces publicar vuelve a depender de que Pablo esté
despierto. Lo que se elige acá es exactamente eso: que no dependa.

Y por eso —porque el que lo use puede ser cualquiera— **el alcance es un solo
repositorio y no la cuenta**. Lo peor que puede hacer alguien con este token es
escribir en `pablosilveira16/capataz`, que es un repo cuyo contenido entero ya
está en la carpeta. No puede leer otros repos, no puede borrar el repositorio,
no puede tocar la cuenta ni las claves.

Si algún día hace falta más, se crea **otro** token con ese alcance; no se le
agregan permisos a éste.

## Crear el token — lo hace Pablo, una vez

GitHub → *Settings* → *Developer settings* → *Personal access tokens* →
**Fine-grained tokens** → *Generate new token*.

| Campo | Qué poner | Por qué |
|---|---|---|
| **Token name** | `capataz-agentes` | Que el nombre diga quién lo usa: es lo único que se ve al revocarlo |
| **Expiration** | 90 días | Un token sin vencimiento es un token que nadie revisa. Renovarlo es reescribir un archivo |
| **Resource owner** | `pablosilveira16` | La cuenta personal |
| **Repository access** | *Only select repositories* → **`capataz`**, y ninguno más | El punto entero de que sea fine-grained |
| **Repository permissions → Contents** | **Read and write** | Es el permiso del `git push`. Sin esto no hay nada |
| **Repository permissions → Metadata** | **Read-only** | GitHub lo marca *(mandatory)* y lo agrega solo al elegir Contents. No se puede sacar |
| **Repository permissions → Workflows** | **Read and write** | Sin esto, cualquier commit que toque `.github/workflows/` hace fallar el push entero. Medido en ERP 360, no supuesto — abajo está el mensaje exacto |
| Todo lo demás | **No access** | Actions, Issues, Pull requests, Webhooks, Secrets: nada de eso hace falta para empujar |

### `Workflows`, que en ERP 360 costó un push entero

Allá la tabla decía que alcanzaba con `Contents: Read and write` +
`Metadata: Read-only`, y **no alcanza**. Capataz tiene
`.github/workflows/verificar.yml`, así que el primer push que lo crea —y después
cualquiera que toque el CI— vuelve con esto:

```
 ! [remote rejected] main -> main (refusing to allow a Personal Access Token to
   create or update workflow `.github/workflows/verificar.yml` without `workflow` scope)
error: failed to push some refs to 'https://github.com/pablosilveira16/capataz.git'
```

Se busca por «`without \`workflow\` scope`», que es la parte del mensaje que no
cambia. Dos cosas que confunden y conviene tener escritas:

- **No es un problema de `Contents`.** El token autenticó bien y GitHub aceptó
  todo lo demás; lo que rechaza es ese archivo. Un error que dice `rejected`
  después de un `Authentication` en verde se lee como un permiso de escritura y
  no lo es.
- **El rechazo es del push entero, no del archivo.** No entra nada, ni siquiera
  los commits que no tocan el workflow.

Con el permiso puesto no hay nada que reintentar de otra forma: el mismo push
sale. Y no se le agrega ningún otro permiso «por las dudas».

*Fine-grained* y no *classic*: el token classic más chico que sirve para empujar
lleva el scope `repo`, y ese scope alcanza **todos** los repositorios de la
cuenta, privados incluidos. La diferencia no es de prolijidad.

El token se muestra **una sola vez**. Si se pierde la pantalla, se revoca y se
crea otro; no hay forma de volver a verlo.

## Dónde va el archivo

Afuera del repositorio, en la carpeta montada padre:

```
/Users/Acer/Documents/frutos de cuyo/.credenciales/github-capataz.token
```

Una sola línea con el token, sin comillas, sin `usuario:` adelante:

```bash
mkdir -p ~/Documents/frutos\ de\ cuyo/.credenciales
printf '%s\n' 'github_pat_…' > ~/Documents/frutos\ de\ cuyo/.credenciales/github-capataz.token
chmod 600 ~/Documents/frutos\ de\ cuyo/.credenciales/github-capataz.token
```

**Afuera y no adentro**, por dos motivos que se sostienen solos:

1. **Ningún commit puede llevárselo.** No es que esté ignorado —lo está igual,
   `.gitignore` cubre `*.token` y `.credenciales/`—: es que **no está en el
   árbol**. Un `.gitignore` se edita por accidente; la geografía no.
2. **Todos los agentes lo ven.** El repo se clona, se copia y se borra; la
   carpeta padre es la misma para las tres copias con las que trabajan tres
   agentes en paralelo. Se configura una vez y sirve para todos.

El `chmod 600` es lo que hace que sólo el dueño lo lea. `ops/credencial-github.sh`
avisa por `stderr` si encuentra otra cosa, pero **no frena el push**: un permiso
flojo es un problema de la máquina, y frenar ahí sólo lograría que el aviso se
saltee.

Si la carpeta estuviera en otro lado, la variable `CAPATAZ_TOKEN` apunta al
archivo. Es lo que usan los arneses; en el uso normal no hace falta.

## Lo mismo sirve en la Mac y en el contenedor

No hay dos configuraciones. La carpeta es una sola, montada en dos rutas
distintas —`/Users/Acer/Documents/frutos de cuyo/…` y `/sessions/…/mnt/…`— y
`.git/config` es **un solo archivo compartido por las dos**. Por eso el helper
se engancha con la ruta calculada y no escrita:

```
credential.https://github.com.helper = !"$(git rev-parse --show-toplevel)"/ops/credencial-github.sh
```

Con la ruta escrita, el último que corriera `ops/empujar.sh` dejaría al otro sin
poder empujar. `ops/empujar.sh` reescribe esa línea en cada corrida —antes de
mirar si hay token, así que también deja configurada una copia recién clonada— y
`pruebas/verificar-credenciales.py` se pone rojo si vuelve a ser absoluta.

## Cómo se prueba, sin empujar nada

```bash
# 1 · El helper contesta el protocolo de credenciales de git.
#     Imprime username= y password=, así que NO se corre con testigos.
printf 'protocol=https\nhost=github.com\n\n' | ops/credencial-github.sh get | head -3

# 2 · Sin el archivo, el mensaje dice qué hacer y no cuelga.
CAPATAZ_TOKEN=/no/existe ops/credencial-github.sh get < /dev/null ; echo "salió $?"

# 3 · git lo usa de verdad: si el token sirve, esto lista las ramas del remoto.
#     Si no sirve, dice «Authentication failed» y no pregunta nada.
GIT_TERMINAL_PROMPT=0 git ls-remote origin

# 4 · Y el arnés, que es lo que corre siempre:
python3 pruebas/verificar-credenciales.py
```

El paso 3 es el que vale: es el único que prueba las tres cosas juntas —que hay
salida a `github.com`, que el helper está bien enganchado y que el token tiene el
permiso—. Los otros tres prueban una cada uno.

**La salida de red, medida en el contenedor del agente:** el proxy deja pasar
`github.com` por HTTPS —`git ls-remote` llega y contesta— pero **no** deja pasar
`api.github.com`, que devuelve `000`. O sea: **git funciona, la API de GitHub
no**. Cualquier cosa que se quiera automatizar contra GitHub tiene que salir por
`git`, no por la API ni por `gh` —que además no está instalado—. De ahí sale la
regla 3 de `CLAUDE.md`: el estado del CI se muestra «no sé» y jamás verde. Y el
puerto 22 está cerrado: **SSH y las deploy keys no son una opción**, por eso esto
es HTTPS con token.

## Cómo se revoca — antes de necesitarlo

GitHub → *Settings* → *Developer settings* → *Personal access tokens* →
**Fine-grained tokens** → `capataz-agentes` → **Delete**.

Es inmediato y no hay que avisarle a nadie: el push siguiente de cualquier agente
falla con «Authentication failed» y `ops/empujar.sh` manda a leer este archivo.
Después:

```bash
rm ~/Documents/frutos\ de\ cuyo/.credenciales/github-capataz.token
```

Borrar el archivo **sin** revocar en GitHub no revoca nada: el token sigue siendo
válido en cualquier copia que exista. Primero GitHub, después el archivo.

## Si se filtró

Un token en un commit, en un log, en una captura o pegado en un chat es un token
filtrado, aunque el commit no se haya publicado nunca.

1. **Revocarlo. Primero, ya, antes de investigar.** Es un click y no rompe nada
   que no se arregle creando otro. Investigar con el token vivo es investigar
   mientras el problema sigue pasando.
2. Crear uno nuevo y escribirlo en el archivo. El resto sigue igual: nada más
   apunta al token viejo.
3. Recién ahí, mirar por dónde salió — y **arreglarlo con una aserción**, no con
   una advertencia. `pruebas/verificar-credenciales.py` se pone rojo si algo con
   forma de PAT aparece en un archivo versionado o en la historia; si se filtró
   por un camino que el arnés no mira, ese camino es una aserción nueva.
4. Si llegó a entrar en un commit, **no alcanza con borrarlo en el commit
   siguiente**: queda en la historia y `git log -p` lo muestra. El commit hay que
   reescribirlo — `ops/90-volver-atras.md`. El token, de todos modos, ya está
   revocado en el paso 1 y no sirve para nada.

## Sin token: el parche

No hace falta esperar. Mientras no haya credencial —o si lo que se quiere es que
Pablo mire el cambio **antes** de que exista en ningún lado— la entrega es por
parche:

```bash
# El que entrega
git format-patch main --stdout > tanda-N.patch

# El que recibe: mirar primero, aplicar después, y poder volver
git apply --stat tanda-N.patch      # qué toca
git apply --check tanda-N.patch     # ¿entra limpio?
git apply tanda-N.patch
git diff                            # qué quedó
git checkout .                      # deshacer, si no
```

Un token no es un backup ni una revisión. Es el árbitro de quién tomó qué punto,
y nada más que eso.

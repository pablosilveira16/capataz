# Capataz — Bitácora

> **El *por qué*.** `SEGUIMIENTO.md` lleva lo que falta; acá va lo que se hizo y,
> sobre todo, **con qué motivo** — para que la próxima sesión no vuelva a decidir
> desde cero algo que ya se decidió una vez, con razón.
>
> Se lee **sólo el capítulo del tema que se va a tocar**. Un archivo que hay que
> leer entero deja de leerse, y entonces no sirve de nada haberlo escrito.

---

# Día cero — 2026-08-06

## Por qué existe capataz

El pedido es de una línea: **saber desde el teléfono qué están haciendo los
agentes**, sin abrir GitHub en la computadora. Hoy la respuesta a «¿en qué anda
esto?» vive repartida en tres archivos de tres proyectos distintos, con formatos
distintos, y para leerla hay que sentarse.

Lo que hace que sea un proyecto y no un script: los tres proyectos **no escriben
igual**, ninguno va a cambiar su formato para que capataz lo lea más fácil, y el
que mira el tablero tiene que poder creerle. Las tres reglas de `CLAUDE.md` salen
de ahí, una por cada cosa que puede salir mal.

## El orden que se siguió, y por qué ése

Se siguió al pie `ERP360-Template/documentacion/andamio-proyecto-nuevo.md`,
§ «El orden». Los cuatro primeros pasos **no tocan la aplicación**:

| | Paso | Commit |
|---|---|---|
| A1 | `SEGUIMIENTO.md` con su contrato y los cinco estados, **vacío** | `eb6a341` |
| A2 | `verificar.sh` y el arnés más tonto que se me ocurrió | `eb6a341` |
| A3 | `git init` y el primer commit, **antes de la primera línea de la app** | `eb6a341` |
| A4 | `CLAUDE.md` con **tres** reglas — no diez | `f968fa6` |
| A5 | `lector.py` | `80583eb` |
| A6 | `capataz.py` + `capataz.html` en el 5402 | `80583eb` |
| A7 | `ops/`, con la marcha atrás **antes** que el despliegue | `4d08197` |

El orden importa por un motivo concreto y medible: **la compuerta tiene que
existir antes que la costumbre**. Un proyecto que arranca sin arnés forma la
costumbre de mirar a ojo, y esa costumbre después no se saca. Por eso el primer
arnés —`verificar-contrato.sh`, que sólo mira que ningún estado sea una palabra
inventada— es anterior a la primera línea de `lector.py`.

Y `git init` antes que el código por otro motivo: **en este proyecto el respaldo
es el commit**. Finca 360 vive con copias `.antes-de-*` porque no tiene git;
acá no hay ninguna copia suelta y no la va a haber.

## Regla 1 · Capataz sólo lee — de dónde sale

No es prolijidad. Es **el bug más caro de Finca 360** dado vuelta: dos lugares
con el mismo dato y ninguna regla sobre cuál gana. Si capataz guardara el estado
de un punto, el día que difiera del `SEGUIMIENTO.md` del proyecto nadie sabría a
cuál creerle — y la respuesta «al proyecto» sólo sirve si está escrita **antes**
de que pase.

Está puesta en tres lugares, y el que vale es el tercero:

1. escrita en `CLAUDE.md` § 1;
2. puesta en la puerta: `capataz.py` **no tiene ningún POST**. El panel de
   ERP 360 sí lo tiene, porque escribe marcas; capataz no tiene por dónde;
3. **verificada ejecutando**: `pruebas/verificar-lector.py` § 1 saca una foto
   (tamaño + sha1) de un proyecto de prueba, corre `mirar()` entero y compara
   byte a byte, y además comprueba que el `HEAD` no se movió y que el árbol no
   quedó sucio.

Y una cuarta que es la que atrapa la intención antes de que corra: `_git()`
rechaza cualquier subcomando que no esté en `GIT_LECTURA`. `fetch`, `checkout` y
`worktree` son las tres cosas que uno agrega sin pensar el día que quiere «un
dato más», y las tres escriben en el repo de otro.

**Corolario que se pierde si no se escribe:** las marcas de agentes las escribe
el `panel/agente.py` **de cada proyecto**, en su propio `panel/agentes.jsonl`.
Capataz las lee y no las escribe nunca. Por eso no absorbió `agente.py`. Ver el
capítulo «El `panel/` de ERP 360», más abajo.

### El arnés que se puso rojo con su propia explicación

Dos veces, y las dos por lo mismo. La primera versión de «`lector.py` no abre
nada para escribir» buscaba la cadena `open(` con `grep`, y se puso roja con **el
comentario de `lector.py` que dice que no hay ningún `open(..., "w")`**. La
primera versión de «no hay ni un `<table>`» se puso roja con **el comentario de
la hoja de estilo que explica por qué no hay ninguno**.

Es el arnés vacuo de la regla 2 dado vuelta: no verifica el código, verifica la
prosa. El arreglo del primero fue pasar por el árbol sintáctico (`ast`); el del
segundo, sacar comentarios antes de mirar el marcado.

## Regla 3 · «No sé» nunca se pinta verde — los tres datos que faltan

Un tablero que miente en el caso que importa es peor que no tenerlo, **porque al
que miente se le cree**. Los tres, medidos y no supuestos:

- **El CI.** `api.github.com` está fuera de la lista blanca del contenedor de un
  agente —devuelve `000`, medido en ERP 360— y `gh` no está instalado. Sin
  respuesta, `no sé`. `interpretar_ci()` está separada de `estado_ci()` a
  propósito: el día que capataz corra donde la API se alcance, lo único que
  cambia es quién le pasa la respuesta.
- **El total de aserciones de una rama.** Sólo si el proyecto lo dejó **medido**
  en `pruebas/total-aserciones.txt`. Un total declarado en prosa es lo que
  alguien recordó escribir, no lo que la suite midió. Hoy ni ERP 360 ni Finca 360
  lo dejan, así que capataz dice «no sé» en todas sus ramas — que es correcto y
  también es inútil, y por eso es el punto T2.
- **Los roles.** Finca 360 no tiene `ops/60-roles.md`. Escribir acá la lista de
  seis de ERP 360 sería la segunda fuente que la regla 1 prohíbe, y además sería
  mentira.

El corolario que cuesta más respetar: **no se agrega un aviso que sale siempre**.
Por eso `tablas_ignoradas` se cuenta y no se muestra (punto T4), y por eso
`motivo_sin_total` viene vacío cuando el total sí se sabe — hay una aserción
dedicada a que ese motivo **no** salga cuando no hace falta.

## Los dos formatos de seguimiento, que son la mitad del problema

ERP 360 pone el estado en la última celda, en una columna que se llama `Estado`.
Finca 360, en sus tablas de *Abierto ahora*, **no tiene columna de estado**: lo
dice el título de la sección.

Por eso el estado se saca del **encabezado de la tabla** y no de «la última
celda». Y por eso el mapa sección → estado vive en `proyectos.json` y no adentro
del código: **es interpretación de capataz sobre el archivo de otro**, y una
interpretación escondida en el código es una que nadie puede discutir. Sin mapa
declarado, el punto queda en `sin estado`, que es lo que hay que ver.

Tres cosas que sólo aparecieron al correrlo contra los archivos de verdad:

- **Una tabla de puntos tiene columna `#`.** Sin esa regla entraba la tabla del
  vocabulario de estados del propio contrato —cinco filas, una por estado— y
  capataz contaba cinco puntos que no existen, en los tres proyectos.
- **«Abierto de tandas anteriores» va debajo de «Historia por tanda».** Finca 360
  lo escribe así, y sin el segundo corte trece puntos abiertos se contaban como
  historia.
- **Un identificador, un punto.** Los dos proyectos repiten filas a propósito.
  El primero gana; los repetidos **no se tiran**, se devuelven aparte, porque dos
  filas del mismo punto con estados distintos es algo que alguien tiene que ver.
  Encontró dos de verdad en Finca 360 el mismo día — ver el capítulo siguiente.

## La pantalla: angosto primero, y sin excepciones

La medida de referencia es **360 px**, sin scroll horizontal y sin zoom. Tres
decisiones que salen de ahí y que el arnés vigila una por una: ningún ancho fijo
mayor a 360 px, `overflow-wrap: anywhere` en todo lo que lleve texto ajeno
—los títulos traen rutas y `código` sin espacios, que es justo lo que desborda—
y **ni un `<table>`**, porque cinco columnas no entran en 360 px de ninguna forma.

`pruebas/verificar-angosto.py` **no puede afirmar «entra en 360 px»**: sin
navegador no hay layout. Afirma las condiciones, calculadas sobre la hoja de
estilo de verdad (340 + 2 × 10 = 360), y ejecuta `render_estatico()` para mirar
el HTML producido y no la plantilla. Eso es menos que mirar, y por eso existe
`./run.sh --instantanea`: un archivo suelto con los datos incrustados que se abre
con `file://` desde un navegador que no llega al 5402 del contenedor.

---

# Tanda 1 — reconciliar y cerrar, 2026-08-06

## Lo primero: el seguimiento decía cosas que no eran

A `coder-1` lo interrumpieron **antes de cerrar por escrito**. Dejó el código
entero y 133 aserciones en verde, y dejó el `SEGUIMIENTO.md` afirmando tres cosas
falsas. Vale la pena escribir cuáles, porque el patrón se repite:

1. **T1 figuraba `hecho` con un arnés que no existe.** Decía «`hecho` ·
   `verificar-credenciales.py` 26 aserciones», y `pruebas/verificar-credenciales.py`
   no estaba en el repo, ni `ops/empujar.sh`, ni `ops/70-credenciales.md`. Lo
   único construido —`ops/credencial-github.sh`— estaba **sin commitear**.
2. **Los números de aserciones estaban viejos** en seis filas: `verificar-contrato.sh`
   figuraba con 10 y tenía 24; `verificar-angosto.py` con 25 y tenía 28.
3. **`CLAUDE.md` se atribuía una compuerta que no existía.** Su cabecera dice
   desde el día cero que `pruebas/verificar-contrato.sh` «verifica el tope y que
   exista lo que se nombra acá», y ese arnés miraba el seguimiento y nada más.

Las tres tienen la misma forma: **una afirmación escrita que nadie ejecuta**. Y
la tercera es la que las explica a las dos primeras — si el arnés hubiera
verificado lo que el archivo decía, `BITACORA.md` habría estado en rojo desde el
primer minuto y nadie habría cerrado la tanda sin escribirla.

El arreglo no fue borrar las afirmaciones sino **hacerlas ejecutables**:
`verificar-contrato.sh` § 4 y § 5 ahora miden el tope de 72 líneas y comprueban
que exista cada archivo que `CLAUDE.md` nombra. Se lo vio rojo con el bug que lo
justificó (`BITACORA.md` ausente) antes de escribir este archivo.

**La regla que queda:** un `hecho` se escribe **después** de correr el arnés y
copiar el número que imprimió, nunca antes. Un número de aserciones escrito de
memoria es una opinión con formato de medición.

## Los números contra los archivos de verdad

Se levantó capataz en el 5402 y se contaron los dos proyectos a mano, fila por
fila, contra lo que muestra la pantalla:

| | Capataz | A mano | |
|---|---|---|---|
| ERP 360 · pendientes abiertos | 22 | 22 (7 D + 15 T) | ✓ |
| ERP 360 · diferidos | 5 | 5 (X1…X5) | ✓ |
| ERP 360 · te bloquean a vos | 7 | 7 (D1,D2,D3,D4,D5,D7,D9) | ✓ |
| ERP 360 · hechos en la historia | 44 | 44 | ✓ |
| Finca 360 · pendientes abiertos | 13 | 13 (7 + 6) | ✓ |
| Finca 360 · diferidos | 4 | 4 (X1,X2,X4,X5) | ✓ |
| Finca 360 · te bloquean a vos | 7 | 7 (A11,E4,X3,N1,G1,V1,F4) | ✓ |
| Finca 360 · hechos en la historia | **43** | **44** | ver abajo |

**La única diferencia es E9 de Finca 360, y capataz tiene razón.** Ese punto
aparece dos veces en el archivo con estados contradictorios: en la línea 186
`pendiente` («`atar-costos-fijos.py` sigue sin aplicarse») y en la 270 **hecho**
(«no había nada que aplicar»). El conteo a mano cuenta la fila que dice `hecho`;
capataz aplica «un identificador, un punto: el primero gana», deja E9 en
`pendiente` y manda la otra fila al bloque **«El mismo punto, dos estados»**.

O sea que la diferencia de 1 no es un error de capataz: **es capataz mostrando
una contradicción del archivo de Finca 360 que el conteo a mano tapa**. Encontró
otra igual: X4 figura `diferido` en *Decidido, esperando el momento* y
`pendiente (propuesto)` en *Abierto de tandas anteriores*.

Y lo importante para la regla que motiva el proyecto: **Finca 360 no tiene
columna `Estado`** y capataz lo interpreta por sección, con el mapa declarado en
`proyectos.json`. Los 13 pendientes y los 4 diferidos que muestra salen de tres
títulos de sección, y coinciden fila por fila con el conteo a mano. **No inventó
ninguno.** Lo que además vale escribir es lo que hace cuando no puede: sin el
mapa declarado los mismos cinco puntos quedan en `sin estado` y no en
`pendiente` — hay una aserción dedicada a eso en `verificar-lector.py` § 3.

## El `panel/` de ERP 360 — decisión: **reemplazar la mitad que mira, nunca absorber la que escribe**

El planteo era: dos lugares con el mismo dato es lo que la regla 1 prohíbe. Al
mirarlo de cerca, el `panel/` de ERP 360 son **dos cosas distintas** y sólo una
es el problema:

| | Qué es | Qué se decidió |
|---|---|---|
| `panel/agente.py` + `panel/agentes.jsonl` | **Escribe** las marcas de quién trabaja en qué | **No se absorbe nunca.** Capataz sólo lee: no tiene por dónde escribir una marca, y dárselo sería cambiar la regla que manda |
| `panel/panel.py` + `panel/panel.html` (5401) | **Mira** el `SEGUIMIENTO.md` y las marcas de ERP 360, para un solo proyecto | **Lo reemplaza capataz**, cuando capataz tenga dónde correr |

**Precisión que hay que dejar escrita, porque es la que evita la decisión
apurada:** `panel/panel.py` **no viola la regla 1**. No guarda estado propio —
lee los mismos dos archivos que lee capataz. Dos pantallas de sólo lectura no
son dos fuentes de verdad. Lo que sí son es **dos pantallas que se separan**: el
día que muestren cosas distintas —porque una arregló el conteo de las tablas sin
columna `#` y la otra no— nadie va a saber cuál mirar, y la que se mire va a ser
la que esté a mano. Ése es el costo, y alcanza para decidir.

Capataz la supera en las cuatro cosas que importan: mira **varios** proyectos,
entra en un teléfono, dice «no sé» donde el panel no dice nada, y lee las ramas
y los totales medidos.

**Por qué no se ejecuta ya, y no es cortesía:** hoy `panel/panel.py` es lo único
que le da a un agente de ERP 360 una pantalla **sin depender de que capataz esté
levantado**, y capataz todavía no tiene dónde correr (D3, X2). Sacarle el panel a
ERP 360 antes de eso lo deja sin nada. Por eso el punto nace **diferido hasta que
se decida D3**, que es exactamente para lo que existe esa sección.

**Y no lo ejecuta capataz.** Borrar o marcar como reemplazado `panel/panel.py` es
un cambio en el repositorio de ERP 360, y tocar el repo de al lado no es de este
proyecto: queda anotado como **T7** en `SEGUIMIENTO.md`, con la decisión escrita,
para que lo levante quien trabaje allá.

## La plomería de credenciales — T1, terminada

Traída de ERP 360 (`ops/credencial-github.sh`, `ops/empujar.sh`,
`ops/70-credenciales.md`, `pruebas/verificar-credenciales.py`) y adaptada: acá el
repositorio es `pablosilveira16/capataz`, el token se llama
`github-capataz.token` y la variable es `CAPATAZ_TOKEN`, porque **un token, un
repositorio**.

Lo que **no** cambió es el motivo: el token vive **afuera del repo**, en
`../.credenciales/`. Afuera y no adentro por dos razones que se sostienen solas:
ningún commit puede llevárselo —no es que esté ignorado, es que no está en el
árbol— y **cualquier agente que trabaje sobre esa carpeta lo ve**, que es lo que
hace que tres agentes en paralelo no configuren nada.

Tres cosas se trajeron **ya arregladas**, y las tres costaron un rato allá:

1. **`Workflows: Read and write` en el token, desde el principio.** A ERP 360 le
   faltaba y GitHub le rechazó **el push entero** —no el archivo— con «refusing
   to allow a Personal Access Token to create or update workflow … without
   `workflow` scope». El síntoma confunde: el token autenticó bien, así que el
   `rejected` se lee como un permiso de escritura y no lo es.
2. **`stat -c` antes que `stat -f`.** En Linux `stat -f` existe, significa otra
   cosa y **sale con éxito**, así que el `||` nunca caía al segundo y el aviso de
   permisos salía con media pantalla de bloques e inodos. Un aviso ilegible es un
   aviso que nadie lee.
3. **El helper enganchado con la ruta calculada y no escrita.** La misma carpeta
   está montada en dos rutas —`/Users/Acer/Documents/…` y `/sessions/…`— y
   `.git/config` es **un solo archivo compartido por las dos**. Con la ruta
   escrita, el último que corriera `ops/empujar.sh` dejaría al otro sin poder
   empujar.

Lo que se sacó al adaptar: capataz no tiene `DIRECTRICES.md`, así que la
alternativa sin token —`git format-patch`— se escribe en el propio runbook en
vez de referenciar un archivo que no existe. Y `verificar-credenciales.py` no
exige que `CLAUDE.md` nombre la plomería: `CLAUDE.md` tiene un tope duro de 72
líneas y está en 72. El puntero vive en `ops/00-mapa.md`, que es donde va.

## El CI, y por qué el primero hay que mirarlo desde la Mac

`.github/workflows/verificar.yml` corre `./verificar.sh` y nada más: **el
workflow no tiene pasos propios de verificación**. Si en el CI hiciera falta un
paso extra para pasar, ese paso está mal y va adentro del script.

Se le agregó lo que en ERP 360 fue una lección aparte: **«sin errores» no es lo
mismo que «dibujó algo»**. El workflow levanta `capataz.py` y afirma que
`/api/estado` contesta JSON y que `/` trae la pantalla.

Y una condición que este proyecto tiene y ERP 360 no: en el CI **los proyectos
vigilados no existen** —el checkout trae capataz solo—, así que la suite tiene
que pasar igual con los tres seguimientos ausentes. Se ensayó localmente
clonando el repo a `/tmp`, donde no hay hermanos, antes de empujar.

**El primer resultado no se puede leer desde acá.** `api.github.com` está fuera
de la lista blanca del contenedor. En ERP 360 eso costó caro: los `.sh` viajaron
sin bit de ejecución y `run: ./verificar.sh` falló con «Permission denied» en
**todas** las ramas empujadas durante un día, y nadie lo vio. Acá el modo del
índice se verifica antes de empujar; el resultado de la primera corrida, igual,
lo tiene que abrir alguien en la web.

## La pantalla, mirada — y no sólo calculada

D1 decía que las condiciones para 360 px estaban verificadas pero que *mirar* no
se había podido: en el contenedor de un agente no hay Chromium ni Playwright. Se
resolvió por el otro lado, con el navegador de la Mac:

`./run.sh --instantanea` deja la pantalla con los datos adentro; se la cargó en
un **iframe de 360 px de ancho**, que es un viewport de verdad con layout de
verdad — la ventana de Chrome en macOS no baja de 500 px, así que redimensionarla
no alcanzaba. Lo medido, no estimado:

| | |
|---|---|
| viewport | 360 px |
| `scrollWidth` / `clientWidth` | 360 / 360 → **sin scroll horizontal** |
| ancho de `.hoja` | 340 px (+ 2 × 10 de padding = 360) |
| elementos que pasan de 360 px | **cero** |
| alto total | 3206 px · 3 tarjetas · 20 chips |

Y **mirada**: se lee. Las tarjetas se apilan, los títulos largos de los puntos
ajenos envuelven, los chips pasan a una segunda fila en vez de estirar la
página, y los tres «no sé» —CI, aserciones, roles— se ven distintos del verde:
borde punteado y gris. El bloque «El mismo punto, dos estados» de Finca 360
muestra en pantalla exactamente las dos contradicciones que el conteo a mano
había encontrado, E9 y X4.

Lo que queda —un teléfono físico, con su tipografía y su notch— ya no bloquea
nada, así que D1 se cierra.

## Dos cosas cambiaron abajo mientras esta tanda corría

No las hizo capataz —sólo lee, y eso está verificado byte a byte— y no las hizo
esta tanda. Se anotan porque el próximo que llegue va a ver otra cosa que la que
dice el capítulo de arriba:

- **`ERP360-Template/` desapareció de la carpeta.** A las 01:26 estaba y capataz
  le leía 22 pendientes y 44 hechos —contados a mano, coincidentes—; a las 02:24
  ya no estaba. Es el punto **D5**, y es de Pablo porque nadie más sabe si se
  movió o se borró. Dos cosas buenas salieron de verlo: la pantalla lo muestra
  **en rojo, con la ruta que buscó**, en vez de dibujar una tarjeta vacía que se
  leería como «no falta nada»; y la suite siguió en verde con el proyecto
  ausente, que es exactamente lo que el CI necesita.
- **Finca 360 pasó a ser un repositorio git** (`cf6add0`, «Finca 360 al día del
  2026-08-05»). Hasta esta tanda no lo era, y capataz decía «ramas · no sé», que
  era correcto. Ahora muestra su `main` y dice «aserciones · no sé», que también
  lo es: le falta dejar el total medido, y eso es T2.

## Qué quedó abierto y no estaba escrito

- **D4** — la primera corrida del CI hay que abrirla en la web. Desde el
  contenedor no se puede leer.
- **D5** — `ERP360-Template/` no está (arriba). Bloquea T2 y T7.
- **T7** — el `panel/` de ERP 360 (arriba). Es trabajo **en el repo de ellos**.
- **T8** — el total se mueve con el largo del `SEGUIMIENTO.md`:
  `verificar-contrato.sh` cuenta **una aserción por fila con columna `Estado`**.
  Es honesto —cada fila se verifica de verdad— pero hace que agregar un punto
  suba el total sin haber verificado nada nuevo, y entonces «el total bajó» deja
  de ser una señal limpia. Se vio en vivo esta misma tanda: 258 antes de
  reconciliar el seguimiento, 268 después, sin una línea de código de por medio.
  Es un cambio de diseño de un arnés ajeno, así que va como punto y no de paso.
- **T9** — capataz no tiene `ops/60-roles.md`, así que la tarjeta de **su propio**
  proyecto dice «qué roles existen · no sé». Es correcto y es feo: capataz es el
  único de los tres que puede arreglarlo sin tocar el repo de nadie.

---

# Tanda 2 — capataz mira la nube, 2026-08-06

> Pablo lo pidió con una frase: **«capataz siempre tiene que estar mirando la
> nube de GitHub, justamente ésa es la gracia, y al observar variaciones en vivo
> va a poder ver los agentes que se prenden y apagan».** Este capítulo es por
> qué eso obligó a rehacer de dónde salen los datos, y qué se decidió en cada
> bifurcación. Rama `t10-mirar-la-nube`, `coder-3`.

## Por qué la carpeta local estaba mal, y no es una cuestión de gusto

Tres motivos, y el tercero pasó **dos veces el mismo día**:

1. **Un agente corre donde sea.** La Mac, un contenedor, otra máquina. Su
   trabajo se hace visible cuando **empuja**, y la carpeta de Pablo no lo ve. Un
   tablero que mira una carpeta muestra a los agentes de esa carpeta.
2. **`git push` ya era el árbitro** del proyecto. Si el remoto es quien decide
   quién tiene qué punto, entonces el remoto **es** la verdad, y capataz estaba
   mirando una copia de la verdad. No es lo mismo aunque casi siempre coincida.
3. **La carpeta desaparece.** `ERP360-Template/` se fue de la Mac entre las
   01:26 y las 02:24 y capataz se quedó ciego con el repositorio entero
   publicado en GitHub — 46 archivos, `443178a`. Y a las 03:12, escribiendo
   justamente esta tanda, **desapareció la carpeta `capataz/` entera**, con el
   trabajo sin commitear. Se rehízo clonando `main` de GitHub y aplicando todo
   de nuevo; de ahí salió la costumbre, para el resto de la tanda, de commitear
   y empujar cada vez que había algo que valiera la pena no perder.

El punto 3 es el argumento entero en una anécdota: **lo único que sobrevivió a
las dos desapariciones fue lo que estaba en GitHub.**

## La decisión central: git, no la API

Los dos caminos, y por qué se eligió el que se eligió.

**Lo medido primero**, desde el contenedor de un agente, el 2026-08-06:

| Destino | HTTP |
|---|---|
| `github.com` | **200** |
| `api.github.com` | 000 |
| `codeload.github.com` | 000 |
| `raw.githubusercontent.com` | 000 |

O sea que **el único camino a GitHub es `git` contra `github.com`**. No es sólo
que la API esté bloqueada: los dos atajos que uno probaría después —bajar un tar
por `codeload`, leer un archivo por `raw`— también lo están.

- **(a) La API.** Da ramas, commits, corridas del CI y contenido de archivos en
  un formato cómodo. Y **desde acá no se puede probar contra la realidad**: sólo
  contra respuestas escritas a mano. En la Mac funcionaría.
- **(b) `git`.** Da ramas, commits con autor y fecha, y el contenido de
  cualquier archivo de cualquier rama. **Se prueba de verdad, ahora, contra los
  repositorios reales.** No da el estado del CI.

Se eligió **(b) para todo lo que da, y (a) sólo para el CI**, que es lo único
que git no puede contestar. El motivo no es preferencia: es la regla 2. Un
lector de red probado únicamente contra respuestas grabadas **pasa entero con la
red rota**, y eso es el arnés vacuo con otra ropa. Con (b), `verificar-nube.py`
clona los repositorios de verdad y compara contra `git ls-remote` —una segunda
llamada de red, por otro camino— rama por rama y SHA por SHA.

De (a) quedó `nube.pedir_ci()`, y **con su límite escrito en tres lugares**: en
el propio archivo, en la primera línea de `pruebas/grabado/actions-runs.json`
(«RESPUESTAS ESCRITAS A MANO, NO CAPTURADAS») y como punto abierto T11. Lo que
sí se ejecuta contra la realidad es el otro lado: desde acá el pedido falla, y
**fallar termina en «no sé» con el motivo escrito**. Eso no es una hipótesis.

### `git archive --remote`, que habría evitado el espejo

Se probó antes de escribir nada: GitHub contesta `operation not supported by
protocol`. No hay forma de leer un blob remoto sin bajar objetos. De ahí sale el
espejo, y no de comodidad.

## El espejo, y por qué no rompe «capataz sólo lee»

Capataz **escribe**, y hay que decirlo en voz alta: un clon `--mirror` por
repositorio, en el temporal. Lo que lo hace compatible con la regla 1 son tres
cosas, y las tres están verificadas:

1. **Sólo adentro de su carpeta de espejos.** `nube._git()` tiene dos compuertas
   —lista blanca de subcomandos, y el destino tiene que estar adentro del
   espejo— y la segunda es la que vale: la primera se burla con un subcomando
   nuevo que parezca inocente, la segunda dice que pase lo que pase, lo que se
   toque va a ser una copia descartable. Es una invariante **más fuerte** que la
   que había: antes capataz corría `git` sobre el repositorio de otro proyecto,
   aunque fuera de lectura. Ahora no lo toca ni para leer.
2. **Lo de adentro es derivado.** `verificar-nube.py` § 5 borra el espejo
   entero, vuelve a leer y compara byte por byte. Si algo viviera sólo ahí, se
   pone rojo — se lo vio rojo guardando un contador de lecturas adentro del
   espejo: `veces_leido: 1` contra `2`.
3. **`lector.py` quedó puro.** Sin red, sin disco, sin un solo `subprocess`, y
   verificado sobre el árbol sintáctico. La mitad que decide qué se muestra no
   puede tocar nada porque no tiene con qué.

La regla 1 prohíbe que capataz sea **fuente de verdad**. No prohíbe un buffer de
transporte, y la diferencia se puede afirmar con una aserción.

## `panel/agentes.jsonl`: se dejó de leer

**Decisión: la cuadrilla sale enteramente de git.** El motivo no es de gusto y
es corto: ese archivo **no se versiona a propósito** —tres agentes en tres
copias producen tres archivos que no se fusionan, decisión de ERP 360—, así que
**nunca va a llegar a la nube**. Seguir leyéndolo de la carpeta local sería
mostrar los agentes que corrieron *en esta máquina* como si fueran la cuadrilla
entera. Eso no es un dato incompleto: es la mentira exacta que la regla 3
prohíbe, porque un tablero con dos agentes se lee igual esté completo o no.

Lo que reemplaza al archivo llega a la nube por definición: **la rama que un
agente empujó** y **el autor de sus commits**. Y trae un dato que las marcas no
tenían — hace cuánto se movió, al segundo.

Efecto lateral honesto: en ERP 360 los commits están firmados `Pablo Silveira`,
no con un nombre de rol, así que ahí el reparto por rol dice **«sin rol»**. Es
correcto y además es información: quiere decir que en ese repositorio los
agentes no firman con su rol, y entonces la cuadrilla por rol **no se puede
saber desde git**. Se prefirió eso a inventarlo.

## Prendido o caído: por qué son cinco palabras y no dos

El pedido era distinguir «un agente trabajando» de «un agente que se cayó». Dos
palabras no alcanzan, y las dos que faltan son las que un umbral solo arruina:

- **`integrada`** — una rama sin ni un commit por delante de `main`. No es un
  agente caído: es una rama **terminada**. De las cinco ramas que había el
  2026-08-06 en los dos repositorios vigilados, **tres eran ésta**. Con un solo
  umbral, capataz habría inventado tres incendios.
- **`dudoso`** — entre 45 minutos y 4 horas. Un agente pensando y uno caído se
  parecen mucho a los veinte minutos y nada a las seis horas, y ese rato tiene
  que verse como lo que es. Tiene su propio color, que **no es ni el verde ni el
  rojo**: pintarlo de cualquiera de los dos sería afirmar algo que capataz no
  sabe. Es la regla 3 aplicada a un agente.

Y una quinta, `sin rama`, para un `en curso (fulano)` del que no llegó ningún
commit. Puede ser alguien que trabaja sin empujar todavía o alguien que se cayó
antes del primer commit; **capataz no puede distinguirlos y no elige**.

## Finca 360: queda declarado, sin publicar

Es repositorio git local (`cf6add0`) y **no está en GitHub**. Las dos salidas
eran sacarlo de la lista o dejarlo con lectura local.

**Se dejó declarado, con `repo: null` y su motivo escrito en `proyectos.json`,
y no se lee nada.** Los dos porqués:

- **No se lo sacó** porque entonces el hecho de que Finca 360 existe y está sin
  publicar no quedaría escrito en ningún lado, y capataz diría que vigila dos
  proyectos cuando son tres.
- **No se le dejó lectura local** porque mantener el lector de carpetas vivo
  para un solo proyecto es mantener entera la clase de bug que esta tanda vino a
  matar — y la habría mantenido en el proyecto que corre en una VM ajena, que es
  donde más caro sale.

En la pantalla se ve como **«sin publicar · no sé»**, ni rojo ni verde: no está
roto, está sin publicar, y pintar de rojo algo que está así a propósito es el
aviso que sale siempre. Se arregla publicándolo → punto T12.

## Los dos conteos, que es lo que hace creíble al resto

Contra los repositorios reales, el 2026-08-06:

| | capataz | a mano |
|---|---|---|
| `pablosilveira16/erp360` · abiertos | pendiente 22 · diferido 5 | pendiente 22 · diferido 5 |
| `pablosilveira16/erp360` · historia | hecho 44 | hecho 44 |
| `pablosilveira16/capataz` · abiertos | pendiente 10 · diferido 3 | pendiente 10 · diferido 3 |
| `pablosilveira16/capataz` · historia | hecho 14 | hecho 14 |

El conteo a mano de ERP 360 se hizo con un script aparte, de otro algoritmo
—regex por línea en vez de armado de tablas— sobre el mismo texto bajado de
`main`. Y coincide con lo que capataz había leído de la **carpeta** a las 01:26
del mismo día, antes de que desapareciera: 22 pendientes y 44 hechos (D5).

Esa comparación quedó **adentro del arnés** y no en esta bitácora:
`verificar-nube.py` § 2 vuelve a contar a mano cada vez, sobre el texto real, y
compara. Un número escrito en un documento envejece; una aserción no.

## Lo que se vio rojo, a propósito

| Bug puesto de vuelta | Qué se puso rojo |
|---|---|
| `clone --mirror --depth` **sin** `--no-single-branch` | 2 rojas: el espejo trae 1 rama de 3. **Era un bug de verdad**, encontrado así |
| `_git()` sin la compuerta de destino | 5 rojas: git corriendo sobre el repositorio de otro |
| Un solo umbral en `estado_rama()` | 6 rojas: una rama integrada pasa a «caído» |
| `dudoso` con la clase CSS de `trabajando` | 1 roja, en la pantalla dibujada |
| La cuadrilla diciendo «nadie» cuando no pudo leer | 1 roja |
| `leer()` devolviendo `ok=True` vacío ante un error | 6 rojas |
| Un contador de lecturas guardado en el espejo | 1 roja: `veces_leido` 1 contra 2 |
| `import subprocess` de vuelta en `lector.py` | 1 roja |

Y una que **no** se puso de vuelta a propósito: `pruebas/verificar-credenciales.py`
se puso rojo solo, dos veces, porque el señuelo con forma de PAT que usa
`verificar-nube.py` estaba escrito de una pieza. Las dos rojas eran **correctas**
—ese arnés no puede distinguir un señuelo de un token filtrado, y no debería
poder, porque una lista de excepciones es por donde se escapa el primero de
verdad—. Se arregló armando el señuelo en pedazos, y reescribiendo la rama:
un token en la historia no se borra con el commit siguiente.

## El total

**268 → 389 aserciones.** El desglose, porque el número solo no dice nada:

| Arnés | Antes | Después |
|---|---|---|
| `verificar-lector.py` | 81 | 95 |
| `verificar-nube.py` | — | **81** (nuevo, contra los repositorios reales) |
| `verificar-pantalla.js` | 36 | 50 |
| `verificar-contrato.sh` | 48 | 60 |
| `verificar-angosto.py` | 28 | 28 |
| `verificar-credenciales.py` | 75 | 75 |

De las 121 nuevas, **12 son de `verificar-contrato.sh` y no verifican nada
nuevo**: ese arnés cuenta una aserción por fila del `SEGUIMIENTO.md`, así que
escribir puntos sube el total. Es el punto T8, y esta tanda lo volvió a pagar.

## Qué quedó abierto

- **T11** — la lectura del CI contra `api.github.com` **de verdad**, desde la
  Mac. Es lo único de esta tanda que nadie pudo probar contra la realidad.
- **T12** — publicar Finca 360 en GitHub.
- **T13** — los dos tokens alcanzan los dos repositorios, y
  `ops/70-credenciales.md` dice «un token, un repositorio». Medido, no supuesto.
- **T14** — el espejo no se limpia nunca.
- **D5** — quedó reescrito: **el problema ya no es que capataz se quede ciego**
  —lee de GitHub— sino **qué borra las carpetas de la Mac**. Pasó dos veces en
  un día y la segunda se llevó una tanda a medio escribir.


---

# Tanda 3 — el visor por agente, en vivo

*2026-08-06. El pedido, textual: «preciso que el primer visor sea por agente, y
esto tiene que ser una app no un html estático, tiene que tener posiblemente un
demoncito en js que esté actualizando una vez por segundo o una cosa así, así
puedo ver en directo cuando un agente se despierta».*

## Lo primero: capataz ya era una app

La instantánea que se mandó al teléfono es una salida de escape —`run.sh
--instantanea`, un `file://` para mirar el ancho angosto—, no la aplicación. La
aplicación ya servía `/api/estado` y repintaba sola. Lo que **no** hacía era
mirarse como algo vivo: repintaba cada 15 s, los contadores no se movían y la
primera pantalla eran tres tarjetas de proyecto. El pedido no era cambiar de
tecnología, era cambiar **qué se mira primero y cada cuánto**.

## Los tres relojes, y por qué no son uno

Un solo número —«actualizar una vez por segundo»— esconde tres cosas que cuestan
distinto:

| Reloj | Cada cuánto | Qué cuesta | Qué se gana |
|---|---|---|---|
| Repintar y volver a decidir el estado | 1 s | nada: no sale del navegador | el contador corre y el chip cambia **en el segundo justo** |
| Pedir `/api/estado` | 2 s | 0,008 s de armar la vista | los datos nuevos llegan enseguida |
| Preguntarle a GitHub | 15 s | **1,2 s de `git fetch` por repositorio** | es el único que hace que un agente aparezca antes |

Medido el 2026-08-06 en la Mac, dos repositorios. El tercero bajó de 60 s a 15;
más abajo no es gratis y lo que se gana es medio segundo de aviso.

**Y el estado lo vuelve a decidir la pantalla, no el servidor.** Si el chip
saliera cocinado del servidor, un agente que cruza los 45 minutos seguiría
diciendo «trabajando» hasta la lectura siguiente. Por eso los umbrales viajan en
el JSON: la pantalla los aplica a cada segundo y **no los tiene copiados** —los
mismos dos números en dos lugares sin regla sobre cuál gana es la regla 1 de
este proyecto, y es el bug más caro de Finca 360—.

## «Se despertó» tiene que ser un empujón, no un reloj

El aviso que se pidió —ver en directo cuando un agente se prende— es fácil de
hacer mal: bastaría con marcar al que tenga el contador chico. Eso avisaría
solo, siempre, y en dos días nadie lo miraría. La marca es **el sha**: cambió el
último commit de su rama, o apareció una rama que no estaba. Y la primera
lectura no marca a nadie, porque si no abrir la pantalla parecería que empujaron
todos a la vez.

## El que casi miente: «GitHub leído hace 1 s»

Con el demonio andando, la línea de frescura decía **«GitHub leído hace 1 s»
para siempre**, con un refresco de 15 s. La marca que estaba usando era
`leido_en`, que es cuándo capataz miró su espejo — y eso pasa en cada pedido de
la pantalla, o sea una vez por segundo. La marca de verdad la deja git en
`FETCH_HEAD`, y es la que ahora viaja como `traido_en`.

Es exactamente la regla 3 en el peor lugar posible: **el dato que dice si hay
que creerle al resto de la pantalla**. Un contador que corre cada segundo sobre
una lectura de hace un minuto no es un detalle de presentación; es el tablero
mintiendo justo en el caso que importa. Corolario nuevo, del mismo tipo: si el
servidor deja de contestar, la pantalla lo dice y apaga lo que muestra en vez de
seguir pintándolo como si fuera de ahora.

## Una aserción vieja que se puso roja con razón

Poner `traido_en` en la vista rompió la aserción de que **el espejo es
descartable**: se borra entero, se vuelve a leer y tiene que salir lo mismo. Y
tenía razón — un clon nuevo se acaba de traer, así que esa marca cambia.

La salida no fue aflojarla. Comparaba dos JSON como cadenas, que contesta «algo
cambió»; ahora compara **los caminos que difieren** y el único admitido es
`/nube/traido_en`. Quedó más estricta que antes: cualquier otro campo que
dependa del espejo la pone roja con nombre y apellido.

## Lo que se vio rojo, a propósito

| Bug puesto de vuelta | Qué se cayó |
|---|---|
| El orden de `agentes()` invertido | «el que se movió recién va primero» — queda `coder-3` donde va `coder-8` |
| La cuadrilla sin el sha | la pantalla se quedaría sin con qué ver que alguien se despertó |
| Marcar «se despertó» por tiempo | la primera lectura y una relectura idéntica avisan las dos |
| La pantalla se queda con el estado del servidor | los cuatro lados de los dos umbrales |
| La frescura mirando `leido_en` | «sin la marca, la frescura dice no sé» |
| `_traido_en()` sin ninguna marca que mirar | las dos del espejo descartable, y la de § 5b |

Todos revertidos y confirmados con `diff -q`.

## Lo que se miró con los ojos

El arnés de la pantalla corre en un `vm` con un DOM de mentira, así que el
demonio de verdad se miró en un navegador contra el servidor de verdad, a 375
px: el pulso latiendo, el contador de frescura subiendo 7→15 s y volviendo a 2,
`scrollWidth == clientWidth == 375` y **cero elementos pasando del ancho**. La
tarjeta que se ve es `coder-3 · coder · Capataz · t10-mirar-la-nube · punto
T10`, en rojo, «hace 10 h sin moverse».

## El total

**421 aserciones, 4 rojas** — y las cuatro son puntos ya anotados: T15 (tres, el
arnés da por sentado que `erp360` es privado y los dos repositorios son
públicos) y T16 (una, el arnés se pone rojo con su propio fixture falso).

Antes de esta tanda eran 335 con las de la pantalla en cero, porque no había
`node`. Con el binario oficial bajado a una carpeta temporal, la pantalla
aportó 69. **Ese salto no es cobertura nueva de golpe**: 50 de esas aserciones
ya existían y estaban salteándose en silencio, que es justo lo que T17 dice.

## Y las dos rojas que la compuerta obligó a mirar

Empujar pide `./verificar.sh` entero en verde —está en `CLAUDE.md` y está en
código, adentro de `ops/empujar.sh`—, así que las cuatro rojas que venían de
antes dejaron de ser «ya anotadas» y pasaron a ser el trabajo.

**T15 · una premisa que envejeció sin que nadie la mirara.** El arnés declaraba
`erp360` como el repositorio privado de la casa. Es público: `git ls-remote` sin
ninguna credencial lo lee. Las tres aserciones del caso «privado sin credencial»
no verificaban nada de lo que decían verificar — y no estaban en verde
mintiendo, estaban en rojo, que es la única razón por la que se encontró. La
salida no fue cambiarle el nombre al repositorio: **se mide**, una vez, con
`ls-remote` y sin credencial, y hay una aserción de que el elegido de verdad no
se alcanza. Si mañana ése también se hace público, se pone roja acá en vez de
volverse vacua en silencio.

**T16 · el señuelo que disparaba la alarma.** La aserción que busca tokens en
toda la historia encontraba el `github_pat_…` **falso** con el que se prueba
`limpiar_secreto()`. No hay ninguna credencial filtrada. Y el arnés hace bien en
no distinguirlos: no tiene forma, y una lista de excepciones es exactamente por
donde se escapa el primero de verdad.

Lo que hizo que esto se pudiera arreglar sin drama fue **medir dónde estaba el
literal** en vez de suponerlo. Parecía estar en `270bb84` —commit ya empujado,
o sea reescribir historia publicada y forzar un push—, y estaba sólo en
`0706590`: la rama local de respaldo de la copia divergida, que nunca salió de
la Mac. Un `commit --amend` sobre una rama que nadie más tiene, y listo.

---

# Tanda 3 · El taller: lo que git no puede contestar

Pablo preguntó si convenía un front nuevo para el *agent viewer* que Claude Code
liberó, con todos los agentes y subagentes en una pantalla. La respuesta fue que
no, y el motivo es el que ordena toda esta tanda: **capataz ya es esa pantalla.
Lo que le faltaba no era front, era una segunda fuente.**

## La pregunta que git no puede contestar

`nube.py` contesta *qué quedó publicado* y lo lee de GitHub, que es el árbitro.
Nadie le puede pedir que conteste *si un proceso está corriendo ahora*: eso no
está en git y no puede estar. Hasta hoy capataz lo aproximaba mirando si la rama
de un agente se había movido, y por eso la regla 3 lo obliga a decir `dudoso`.

El punto T12 había rechazado, con razón, «dejar un segundo camino de lectura
local». La diferencia que habilita `taller.py` —y que quedó escrita en su
docstring, porque es toda su justificación— es ésta:

> T12 rechazaba leer **el mismo dato** desde dos lugares sin regla de cuál gana.
> Acá se lee un dato **que git no puede tener**. No hay dos versiones del mismo
> hecho, así que no hay cuál-gana que decidir.

## Lo que se midió antes de escribir una línea

Ninguna de las decisiones de abajo salió de la documentación. La doc dice que
`claude agents --json` existe; lo que hizo falta saber es qué devuelve **acá**.

- **`claude agents --json` no muestra subagentes.** Lo dice la doc y se
  confirmó: lista sesiones, no árboles. Para lo que Pablo pedía, no alcanza.
- **Y devuelve menos que el archivo**: seis campos contra los once de
  `~/.claude/sessions/<pid>.json`. `state` y `waitingFor` son *background only*
  y no hay sesiones background en esta máquina. Por eso capataz **lee los
  archivos y no llama al CLI** → T22.
- **El árbol está en los `.meta.json`**, de 130 bytes: `agentType`,
  `description` —ya escrita para un humano—, `spawnDepth` y, cuando hay
  anidamiento, **`parentAgentId`**. Ese campo no aparecía en ninguno de los 17
  casos viejos porque todos eran de profundidad 1; apareció lanzando un
  subagente que lanzara otro. **No hace falta abrir un solo transcripto para
  dibujar la jerarquía**, que era el miedo de diseño.
- **Los transcriptos se escriben por append**, así que la pantalla puede latir:
  crecen cada pocos segundos mientras el agente trabaja.
- **El umbral se midió, no se eligió.** Sobre 2830 huecos entre líneas: un
  agente **que sí está trabajando** puede quedarse callado hasta **272 s**
  (p99 = 50 s). `FRESCO` quedó en 5 minutos, arriba del máximo observado. Con
  un minuto, uno de cada cien agentes vivos se vería como caído.

## La señal que se descartó, que es lo que más vale de la tanda

No hay marca de cierre adentro del `.jsonl` de un subagente: uno en curso y uno
terminado son indistinguibles por su última línea. Sin eso, capataz mostraba
`caído` a dos agentes de Finca 360 que habían **terminado bien** dos horas
antes — o sea inventaba un incendio, el mismo error que `estado_rama` ya evita
con `integrada`.

Se probó una segunda señal para salvarlo sin abrir transcripciones: *«si el
padre escribió después de que el hijo se calló, el hijo terminó»*. **Dio
verdadero en los 17 casos y se descartó igual**, por dos motivos:

1. Los 17 son agentes **terminados**. Cero casos negativos: una señal que nunca
   se vio decir que no, no se sabe si sabe decir que no. Es la aserción vacua
   del § 2 de `CLAUDE.md`, disfrazada de evidencia.
2. Tiene contraejemplo medido: un subagente en background **no frena al padre**,
   así que el padre escribe mientras el hijo trabaja.

Por eso el desenlace se llama **`sin señal`** y dice el rato, en vez de `caído`
o `terminado`. Las dos palabras que faltan son el resultado, no un pendiente
→ T19.

## Lo que se vio rojo, a propósito

Cinco bugs puestos de vuelta, cada uno revertido y confirmado con `diff -q`:

| Bug puesto | Lo que se puso rojo |
|---|---|
| `_abrir` sin la compuerta de extensión | 3 rojas: una transcripción se podía abrir |
| `_arbol` filtrando huérfanos en silencio | 1 roja: un agente desaparecía de la pantalla |
| Volver a decir `caído` | 5 rojas, **una de ellas contra los agentes reales** |
| `leer()` guardando estado propio | 2 rojas: el AST y la huella del disco, por separado |
| `sin señal` pintado de verde | 1 roja en la pantalla ejecutada |

## Lo que se miró con los ojos, y que ningún arnés encontró

Tres cosas aparecieron recién al abrir la pantalla en 375 px, con los 495 en
verde:

- Los `**` de markdown salían **literales**: el texto era para un archivo y
  terminó en un chip.
- El motivo de `sin señal` era un párrafo de cuatro renglones al lado de un chip
  de una palabra, y tapaba a los otros agentes.
- `.porque` estaba escrito como **descendiente** de `.subagente`, así que el
  mensaje de una sesión sin subagentes salía en cuerpo grande, con nueve
  renglones de ruta para decir «no pasa nada».

Ninguna es un bug de lógica y las tres arruinaban la pantalla. La regla vieja
—«el ancho angosto hay que mirarlo»— se ganó otro día.

## Y una premisa vieja que se cayó sola

T17 decía que `node` no estaba instalado y que instalarlo pedía la contraseña de
Pablo. **Ya estaba instalado** hacía días, en `~/.local`. Lo que fallaba era el
PATH: `.zshrc` lo exporta y `.zshrc` sólo lo lee la shell **interactiva**. El
arreglo fue una línea en `~/.zprofile`, sin contraseña de nadie. Es la segunda
premisa envejecida de este proyecto —la primera fue el `erp360` «privado» de
T15— y las dos se cayeron por lo mismo: **nadie las volvió a medir.**

## El total

**495 aserciones en verde**, contra 431 al empezar. Las 64 nuevas: 50 del arnés
de `taller.py` y 14 de la pantalla.

## Finca 360, y la aserción que se volvió vacua al arreglar el dato

T12 quedó cerrado: `pablosilveira16/finca360`, privado, 13 ramas. Lo que costó
una medición fue la premisa. «Ya está cargado con todo» era razonable —el repo
existía y `git ls-remote` autenticaba— y era falso: **devolvía cero refs**, y el
clon local no tenía ningún remoto ni upstream en ninguna rama. Crear el
repositorio en github.com no sube nada. Es la tercera premisa de este proyecto
que se cae al medirla, y las tres se caen igual: alguien la afirmó una vez y
nadie volvió a mirar.

Lo que dejó de regalo es más interesante que el push. Esta aserción vivía en
`verificar-lector.py` y estaba bien escrita:

```python
sin = [p for p in reales if not p["repo"]]
af("un proyecto sin repo declara por qué", all(p["motivo_sin_repo"] for p in sin))
```

Al publicar Finca 360, `sin` quedó **vacía**. `all([])` es `True`: la aserción
pasa siempre, sigue sumando al total y no verifica nada. **No se volvió vacua
por escribir mal el arnés, sino por arreglar el dato**, que es la forma más
difícil de verla — nadie sospecha de un arnés que sigue verde después de un
cambio que salió bien. La reescritura habla de los tres proyectos y no de un
subconjunto que puede vaciarse, y lleva `reales and` adelante para no sobrevivir
a un `proyectos.json` vacío. Se la vio roja antes de contarla.

Quedaron dos puntos que la lectura destapó: Finca 360 no tiene token propio
(T23) y **la carpeta de credenciales que `nube.py` busca por defecto no es la
que existe en la Mac** (T24). Los dos están tapados hoy por el llavero de macOS,
que contesta antes que el helper — o sea que la próxima máquina sin llavero se
va a encontrar con los tres proyectos fallando juntos por una ruta que nadie
miró.

---

# Tanda 4 · La consola: lo que ni git ni los archivos pueden tener

Pablo pidió **que el panel consuma la vista `claude agents` de consola**. Ese
pedido ya tenía una respuesta escrita y era «no»: el punto T22 lo había
rechazado el 2026-08-06 con una medición honesta. La tanda empieza volviendo a
medir, y termina en el lugar opuesto — pero por un motivo que el T22 no podía
saber, no porque el T22 estuviera mal.

## La medición que dio vuelta el punto

El T22 decía: para una sesión **interactiva**, `claude agents --json` devuelve
seis campos y `~/.claude/sessions/<pid>.json` devuelve once. Pagar un
subproceso para obtener menos que un `open()` no se paga. **Se volvió a medir el
2026-08-15 y eso sigue siendo cierto** (hoy son doce campos contra seis).

Lo que el T22 dejaba abierto era la puerta: *«el día que se usen agentes en
background, ese JSON agrega `state` y el `id` para `claude attach`»*. Nadie
había lanzado uno. Se lanzó:

    claude --bg "contá del 1 al 20, uno por línea, y nada más"

Y ahí aparecieron las dos cosas que cambian el diseño:

- **Vivo**, el CLI trae `id`, `status` y **`state`** — y `state` **no está en el
  archivo**. Es el campo que dice si el agente trabaja o está trabado. El de la
  prueba salió `blocked`, porque una sesión background no hereda la sesión de
  Claude y quedó pidiendo `/login`. O sea que el primer background que corrió en
  esta máquina fue, sin querer, exactamente el caso que un capataz tiene que
  poder ver: *un agente que no avanza y necesita a una persona*.
- **Parado**, `<pid>.json` **desaparece** y sólo `claude agents --json --all` lo
  conserva, con `state: "stopped"`. Un background terminado no es un dato que
  `taller.py` lea mal: es un dato que **no puede** leer, porque ya no hay
  archivo que abrir.

Los seis valores de `state` no se eligieron: dos se vieron en vivo y el resto
salió del propio binario del CLI, que los lleva como lista literal —
`"working","blocked","done","stopped","failed"`, más `queued`. Lo que no esté en
esa lista se muestra **«no sé» con la palabra cruda adentro**.

## El hallazgo que contradice al T19 sin contradecirlo

De un **subagente** no se puede saber si terminó o se colgó: no hay marca de
cierre en su `.jsonl` (T19), y por eso el taller dice `sin señal`. De un
**background**, el CLI distingue `done`, `failed` y `stopped` — tres desenlaces.
Son dos preguntas parecidas con respuestas distintas, y la pantalla dice la que
corresponde a cada una. La incoherencia aparente está escrita al lado de los
colores, para que el próximo que la vea no la «arregle».

## Dos fuentes del mismo hecho, y por primera vez hay que escribir la regla

Hasta hoy la regla 1 se cumplía sola: cada módulo contestaba algo que ningún
otro contestaba. Con la consola aparece solapamiento de verdad — una sesión
interactiva viva está en el archivo **y** en el CLI —, y «dos lugares con el
mismo dato y ninguna regla sobre cuál gana» es literalmente el bug más caro de
Finca 360. Entonces la regla se escribe:

1. Sesión interactiva → **gana el archivo**. La consola ni la muestra.
2. `state` y background terminado → **sólo la consola**. No hay qué comparar.
3. Lo que no coincide → **se muestra**. Resolverlo en silencio sería elegir un
   ganador sin decirlo, que es el bug otra vez.

Y el corolario de la regla 3 obligó a la mitad menos obvia: **declarar los
desacuerdos que no son desacuerdos**. El archivo escribe `kind: "bg"` y el CLI
escribe `kind: "background"` para la misma sesión; un background terminado no
tiene archivo. Si esas dos cosas se reportaran, el aviso saldría en **todas** las
corridas y enseñaría a ignorarse. Están declaradas y medidas, y el arnés tiene
una aserción de cada lado: que el aviso salga cuando hay algo, y que no salga
cuando no.

## Lo que se vio rojo, a propósito

Trece bugs puestos de vuelta, cada uno revertido y confirmado con `diff -q`:

| Bug puesto | Lo que se puso rojo |
|---|---|
| La compuerta deja pasar `--agent`, `attach`, `stop`… | 18 rojas |
| La compuerta corre **después** del `subprocess` | 1, y es la que importa |
| `stdin` deja de ir a `/dev/null` | 3 — una es un CLI que pide una tecla y cuelga la pantalla 5 s |
| `leer()` devuelve `ok=True` cuando falla | 3: el «cero agentes» que miente |
| `bg` deja de ser alias de `background` | 1 |
| Un `state` que nadie vio se pinta de trabajando | 1 |
| `cotejar` se calla siempre | 6 |
| El taller deja de traer la clase cruda | 2 |
| «esperando» pintado de verde en la pantalla | 1 |
| La consola sin CLI dice «ningún agente background» | 2 |
| El espejo se da por bueno si existe `objects/` | 3 |
| El borrado deja de mirar si el destino es suyo | 1 |

## El bug que encontró la pantalla, no el arnés

A mitad de tanda la suite se puso roja en un lugar inesperado: el arnés de la
pantalla no encontraba **ningún** proyecto legible. Los tres decían «not a git
repository», y `verificar-nube.py` seguía en 86 verdes.

`/var/folders/…/T` es temporal de verdad: macOS le borra los archivos viejos por
antigüedad **y deja los directorios**. Los tres espejos habían quedado con
`objects/` y `refs/` pero sin `HEAD`, `config` ni `packed-refs`. Y capataz
decidía «ya está clonado» preguntando si existía la **carpeta** `objects/` — que
es justo lo que sobrevive—, hacía `fetch` contra el esqueleto y **no se
recuperaba nunca**, ni reiniciando.

Lo que más vale de esto es por qué el arnés no lo veía: **cada corrida clona en
un `mkdtemp` nuevo**, o sea siempre en el caso feliz. Un espejo de un día para el
otro era un camino que ninguna aserción recorría — no una aserción vacua, algo
más silencioso: un camino que no existía en la prueba. Ahora se reproduce el
destripe exacto y se exige que capataz se recupere solo.

El arreglo obligó a la primera escritura destructiva del proyecto —`git clone`
no entra en un directorio que no está vacío—, y llegó con la compuerta que el
T14 había pedido por escrito. **Y la compuerta encontró un bug en el arreglo**:
la guarda «si no existe, salgo» estaba arriba de la validación, así que un
destino de afuera se iba por el `return` sin pasar por ningún control. Es el
mismo error de orden que el arnés de la consola vigila en `_correr`, escrito por
la misma mano el mismo día.

## La roja que iba y venía sola

`verificar-taller.py` tenía una aserción anti-vacua —«se encontró al menos un
agente de verdad»— que dependía de que en ese momento hubiera un subagente
colgando de una sesión **todavía registrada como viva**. Los metas quedan en
disco cuando la sesión cierra, pero `leer()` sólo llega a los de las vivas, así
que la suite quedaba roja o verde según lo que estuviera corriendo. Se midió que
es anterior a esta tanda: da idéntica con y sin los cambios de la consola. Ahora
los metas se buscan en disco —18 en 6 carpetas— y se leen con el lector de
verdad.

## Lo que se miró con los ojos

A 375 px, contra el servidor de verdad: `scrollWidth == clientWidth == 375`,
cero elementos pasando del ancho, y la tarjeta del background con su asa
`claude attach 6ced0113` en monoespaciada. Y apareció lo que ningún arnés podía
ver, porque para él son cadenas: **los backticks salían literales en la
pantalla** — la misma marca que `taller.py` ya tenía anotada para los
asteriscos. Cuatro textos reescritos sin markdown.

## El total

**641 aserciones en verde**, cero rojas. Antes de la tanda eran 495. Las nuevas:
103 de `verificar-consola.py`, 16 de la § 9 de la pantalla, 13 de la § 5c de la
nube, y el resto son las que ya existían corriendo con los espejos sanos.

Tres de esas 641 no verifican nada nuevo: son las tres filas que esta tanda
agregó al seguimiento, y `verificar-contrato.sh` cuenta una aserción por fila.
Es el T8 exactamente, visto otra vez — el número se anotó primero como 638
mirando la corrida de antes de escribir el cierre, y subió a 641 al escribirlo.
Mientras el total se mueva con el largo de un archivo de texto, «el total bajó»
no es una señal limpia.

---

# Tanda 5 · La app con menús, y la pestaña que no puede esconder nada

Pedido de Pablo, textual: *«preciso que organices la app y que sea parecida al
ERP o busquemos algún formato que sirva; tipo página vertical no sirve, tiene
que ser una app con menús y el primer Dashboard el de los agentes de la
consola»*.

## El formato no se inventó: se copió del de al lado

`ERP360/static/index.html` ya resuelve esto y hace meses: barra arriba, menú
lateral en pantalla ancha y **tabbar abajo en teléfono**, con las secciones
declaradas en un solo lugar. Son dos tableros del mismo sistema, así que aprender
a moverse en uno tiene que servir para el otro. Lo único que no se copió es la
implementación —capataz sigue siendo **un archivo sin dependencias**—, pero la
forma es la misma.

Cuatro vistas, y la primera es la consola porque es lo que se pidió y porque es
lo único de la pantalla que puede pedir que alguien haga algo ahora mismo.

## Lo que este cambio obligó a resolver, y es la mitad que vale

Un menú esconde tres cuartas partes del tablero. Apiladas, las secciones se
veían al pasar; **detrás de una pestaña, un «no pude leer» que nadie abre es un
error que no existe.** Dicho de otra forma: navegar por pestañas, hecho sin
cuidado, hace a capataz *menos* honesto que la página vertical que reemplaza.

De ahí las dos decisiones que sostienen el cambio:

1. **La frescura y el pulso viven en la barra**, no adentro de una vista. Si
   estuvieran en una, las otras tres mostrarían datos sin decir de cuándo son —
   la regla 3 rota justo en el dato que dice si creerle al resto de la pantalla.
2. **Una vista escondida marca su pestaña.** Y marca dos cosas nada más: lo que
   **no se pudo leer** y lo que **pide una persona**.

El «nada más» de ahí es el corolario de la regla 3, y se decidió midiendo. Los
candidatos obvios estaban todos descartados por los datos de hoy: los **cuatro**
agentes del tablero están `caído` y los tres proyectos tienen filas «sin
estado», así que marcar por eso sería prender las cuatro pestañas en todas las
corridas — el aviso que enseña a ignorarse. Quedaron marcando: una sección que
no se pudo leer, un background `esperando` o `falló`, un proyecto ilegible, y un
`sin rama` (un `en curso (fulano)` del que no llegó ni un commit).

Por eso la § 10 del arnés tiene aserción de los **dos** lados: que la marca
salga con una consola caída **estando la pestaña escondida**, y que **no salga**
con todo sano. Sin la segunda, prender las cuatro siempre pasaría el arnés.

## El bug que estaba desde el día cero

Al reordenar el marcado, un `Edit` falló diciendo que encontraba dos coincidencias
idénticas. Eran dos **`function pintar(d)`** en el mismo archivo: la del día cero
—quince líneas, sólo las tarjetas de proyecto— y la de la vista en vivo. En
JavaScript la última declaración gana, así que la primera hacía tanto tiempo que
no se ejecutaba que nadie se había enterado.

Estaba en `HEAD` y en todos los commits anteriores. Dos versiones de la misma
función y ninguna regla sobre cuál gana, adentro del proyecto que tiene
exactamente eso escrito como regla 1. Se borró, y **la suite quedó igual de
verde**: no la vigilaba nadie, que es la definición del código muerto.

## Un bug puesto en el lugar equivocado no prueba nada

Poniendo `var VISTA = "proyectos"` el arnés dio **cero rojas**, y por un momento
pareció que la aserción «arranca en la consola» era vacua. No lo era: quien
decide de verdad es `arrancarVistas()`, que corre en el mismo tick y pisa ese
valor. Puesto el bug **ahí**, se ponen rojas dos. Queda escrito al lado de la
variable, porque la conclusión fácil —«esta aserción no sirve»— habría borrado
una aserción buena.

## Lo que se miró con los ojos, y que ningún arnés encontró

Los dos son de la barra nueva, y los dos aparecieron a 375 px:

- **«capataz» salía partido en dos renglones**, «cap a / ta z»: el estado, que es
  texto largo, le comía el ancho a la marca. Para el arnés es una cadena que
  está entera.
- **El primer título quedaba seis píxeles debajo de la barra con la página sin
  scrollear.** Fue culpa del margen negativo con el que saqué la barra del
  padding del body. Se arregló sacándole el padding lateral al body y
  poniéndoselo al contenido, que además es lo que hace que la barra llegue de
  borde a borde.

Después, medido en el navegador: barra 0–55, primer título en 69, sin
superposición, `scrollWidth == clientWidth == 375`, cero elementos pasando del
ancho, el pie sin quedar tapado por la tabbar. Y a 1000 px, el lateral con la
vista abierta marcada. Navegando de verdad: una sola vista abierta, el `#hash`
sigue a la vista, y **el contenido de la anterior no se borra ni se vuelve a
pedir** — cambiar de pestaña no dispara una lectura.

## La roja que era del arnés, otra vez

Mover el padding lateral del `body` al contenido puso roja a
`verificar-angosto.py`: *«340 px de hoja + 2 × 40 px de padding = 420 px»*. La
hoja entraba perfecta —el navegador decía 375 == 375 con cero desbordes—, así
que la primera hipótesis fue la de `CLAUDE.md` § 2: **el arnés**. Y era.

Leía el `padding` del body quedándose con los valores terminados en `px` y
**perdiendo la posición**: de `padding: 0 0 40px` se llevaba el 40, que es el de
abajo, y lo sumaba dos veces como si fueran los costados. Un cero sin unidad no
existía para él. Ahora lee la abreviatura por posición —1, 2, 3 o 4 valores— y
suma los costados del `body` **y** los del contenedor, que es donde viven desde
hoy. Se la vio roja inflando el padding a 30 px: 400 px, roja.

## El total

**663 aserciones en verde**, cero rojas. Antes de esta tanda eran 641. Las
nuevas son las 16 de la § 10 de la pantalla y las que sumaron las filas de este
seguimiento; `verificar-consola.py` subió sola de 103 a 105 porque hay dos
agentes background en la máquina y tiene aserciones por agente — otro total que
se mueve con el ambiente, primo hermano del T8.

---

# Tanda 6 · Qué está haciendo cada agente, y la promesa que se hizo más chica

Pablo preguntó si se podía tener «algún dato más de lo que está haciendo cada
agente». Hasta acá el tablero contestaba *si* trabaja —hace cuánto escribió— y
no *qué* hace.

## Lo que se midió antes de elegir

- **`claude logs <id>` no sirve.** Para un background parado devuelve
  `Couldn't read logs — connect ENOENT …/control.sock`: anda sólo mientras el
  demonio vive. Descartado por medición, no por opinión.
- **El `.meta.json` de un subagente ya está exprimido**: cuatro campos, y la
  `description` ya se muestra.
- **Lo que falta está en la transcripción**, que es justo lo que `taller.py`
  prometía no abrir jamás. Leyendo **los últimos 64 KB** entran 27 eventos y el
  último `tool_use` trae `name` y un `description` escrito para humanos.

## La promesa no se borró: se hizo más chica y más verificable

La decisión fue de Pablo: leer la cola. El motivo original de la promesa sigue
siendo cierto —una transcripción es todo lo que el agente leyó—, así que lo que
cambia es el alcance, y lo que lo sostiene es una **lista blanca**: el nombre de
la herramienta, su `description`, y el **basename** de la ruta. Nunca el
`command` de un Bash, nunca el texto de un mensaje, nunca un `old_string`. Es
lista blanca y no lista negra porque una lista de lo prohibido es por donde se
escapa el primero que nadie previó.

El arnés pasó de contar «un solo `io.open`» a contar **exactamente dos**, y a
exigir cuál está en cuál función: `_abrir` para los `.json` chicos, `_cola` para
la transcripción — más una aserción de que `_cola` usa `seek` y no lee entero,
porque en esta máquina hay transcripciones de 13 MB.

## Tres aserciones que parecían buenas y eran vacuas

Esta tanda las encontró a las tres poniendo bugs, y las tres enseñan lo mismo:
**una aserción que no se vio roja no está verificada.**

1. **El señuelo con forma de token.** Se plantó un `ghp_…` adentro del `command`
   y se afirmó que no salía. Puesto el bug —`command` adentro de la lista
   blanca— la aserción **seguía pasando**: `limpiar_secreto` tapaba el token y
   lo mostraba como «token». El canario tuvo que ser una cadena sin forma de
   nada: si aparece, es porque el `command` salió, y no hay red que lo ataje.
2. **Caminar la cola para atrás.** El caso ponía una herramienta vieja al
   principio de un archivo grande y otra al final. Pero la vieja quedaba fuera
   de los 64 KB, así que caminar para adelante o para atrás daba igual. Se
   agregó un caso con **dos herramientas adentro de la misma cola**.
3. **«Arranca en la consola»** (de la tanda anterior, y la misma lección al
   revés): el bug puesto en `var VISTA` no ponía nada rojo porque
   `arrancarVistas()` lo pisa. La aserción era buena; el bug estaba en el lugar
   equivocado.

## El bug que sólo se ve mirando

Con todo en verde, la pantalla **no mostraba nada**. La API mandaba el dato, el
arnés lo dibujaba, y el navegador no. La causa: la firma que decide si vale la
pena repintar miraba **quién está y en qué estado**, no qué hace. Así que una
sesión que pasa de `Bash` a `Edit` no se repinta nunca — un tablero en vivo
mostrando lo de hace media hora, que es exactamente el bug del T21 en otra
sección. Ahora `que` y `sobre` van en la firma, y hay una aserción que pinta
**dos veces sobre el mismo contexto** —como hace el navegador— y exige que el
cambio se vea. Se la vio roja sacando los dos campos de la firma.

Y tres cosas de dibujo que ningún arnés puede ver:

- `mcp__Claude_Browser__javascript_tool` ocupaba media pantalla. Se corta por el
  separador y queda `javascript_tool`: cortar por largo dejaba
  `mcp__Claude_Browser__javascr…`, que no dice nada.
- `TaskCreate` se partía en «TaskC / reate». Un nombre de herramienta es una
  palabra sola y partirla no la acorta, la hace ilegible.
- El texto que escribe otro agente **viene con markdown** y salía literal
  —«la magnitud `conductividad` en \*\*dS»—, la misma marca que ya tenían los
  alcances de los dos módulos. Se sacan los backticks y los asteriscos, y el
  corte va en un espacio y no en el medio de una palabra.

## El desacuerdo que se encontró solo

A mitad de tanda `verificar-consola.py` se puso rojo sin que nadie tocara la
consola: `cotejar` había encontrado un desacuerdo **de verdad**. El background
`c9b6af26` figura con `state: blocked` y **ya no trae `pid`** —el proceso murió
y el registro del CLI quedó viejo—, mientras su archivo desapareció. La pantalla
dice «trabado: necesita a una persona» y no es cierto: está muerto. Quedó como
T37.

Lo que se arregló acá fue el arnés: pedía **cero** desacuerdos contra la máquina
de verdad, y eso es pedirle que la máquina nunca tenga nada raro. Ahora exige
que ninguno sea de los **dos declarados como falsos positivos**, y si hay otros
los imprime. La roja era del arnés; el hallazgo, del código.

## El total

**699 aserciones en verde**, cero rojas. Antes de la tanda eran 663.

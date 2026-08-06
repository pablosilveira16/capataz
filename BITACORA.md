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

## Qué quedó abierto y no estaba escrito

- **T7** — el `panel/` de ERP 360 (arriba). Es trabajo **en el repo de ellos**.
- **T8** — `pruebas/total-aserciones.txt` de capataz se reescribe en cada corrida
  verde, y el total se mueve cuando cambia `SEGUIMIENTO.md`: `verificar-contrato.sh`
  cuenta **una aserción por fila con columna `Estado`**. Es honesto —cada fila se
  verifica de verdad— pero hace que el total dependa del largo del seguimiento, y
  entonces «el total bajó» deja de ser una señal limpia.
- **T9** — capataz no tiene `ops/60-roles.md`, así que la tarjeta de **su propio**
  proyecto dice «qué roles existen · no sé». Es correcto y es feo: capataz es el
  único de los tres que puede arreglarlo sin tocar el repo de nadie.

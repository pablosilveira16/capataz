# Capataz — Seguimiento

> **Si sos un agente que recién llega a este proyecto, empezá por acá.** Esta es
> la única lista de lo que está abierto. No depende de ninguna sesión ni de
> ningún modelo: lo que no está escrito acá, no existe.
>
> Después leé `CLAUDE.md` (las tres reglas) y `BITACORA.md` (por qué quedó así),
> sólo el capítulo del tema que vas a tocar.

## Qué es capataz

Una app web chica que **mira** el trabajo de los agentes en varios proyectos y
lo muestra en una pantalla que se lee **desde un teléfono**. Ése es el requisito
que la motiva: sin esto, saber qué pasó exige abrir GitHub en la computadora.

**Capataz sólo lee.** El `SEGUIMIENTO.md` de cada proyecto es la verdad y git es
el árbitro; capataz no guarda ningún estado propio. Está escrito como regla en
`CLAUDE.md` y verificado en `pruebas/verificar-lector.py`.

## El contrato de este archivo

**Qué lleva.** Lo que **falta**. La bitácora lleva lo que se hizo y por qué;
cuando un punto se cierra, su historia se va a la bitácora y acá queda la línea
de estado. Las dos cosas se escriben al cerrar cada tanda.

**Cuándo se escribe una línea.** Apenas aparece el punto, no al terminar. Un
pedido que se anota cuando ya está resuelto no sirve de nada: el archivo existe
para el caso en que la sesión se corte en el medio.

**Los estados, y no hay otros** — los verifica `pruebas/verificar-contrato.sh`,
que se pone rojo con cualquier palabra que no sea una de estas cinco:

| | |
|---|---|
| `pendiente` | Falta hacerlo. Si depende de una persona, se aclara: `pendiente (Pablo)` |
| `en curso` | Alguien lo está haciendo ahora. Con quién: `en curso (coder-1)` |
| `hecho` | Terminado **y verificado** — con el arnés y el número de aserciones al lado |
| `diferido` | Se decidió no hacerlo todavía, y se dice hasta cuándo o por qué |
| `descartado` | Se decidió no hacerlo |

**Dónde va el estado.** En la **última celda** de la fila, y la columna se llama
`Estado`. El arnés lo lee de ahí; una tabla de puntos sin columna de estado es
una tabla que nadie verifica — y capataz, que lee los seguimientos ajenos, tiene
que adivinar (ver `lector.py`, y el punto T4).

**Cómo se cierra un punto.** Se marca `hecho` con la prueba pegada al lado —el
arnés que lo vigila **y** su número de aserciones—, se saca de *Abierto ahora* y
se le escribe el capítulo en la bitácora. **`hecho` sin prueba al lado es una
opinión.** Y el número se copia **después** de correr el arnés, nunca de memoria:
el 2026-08-06 seis filas de este archivo tenían números viejos y una citaba un
arnés que no existía (`BITACORA.md`, Tanda 1).

**Y acá hay git.** Todo punto cerrado tiene su commit. Un punto que se cerró en
la máquina de alguien y no está en `main` está abierto.

---

## Abierto ahora

Lo único que hay que mirar para saber qué falta. El detalle de cada punto está
más abajo, en la tanda donde nació.

### Depende de una decisión (Pablo)

| # | Qué falta | Desde | Estado |
|---|---|---|---|
| D3 | **Hasta dónde llega capataz.** Hoy es un visor y `CLAUDE.md` § 1 dice que no decide ni lanza nada. La orquestación —convocar un agente, asignarle un punto— es el paso siguiente y **cambia la regla que manda**: en el momento en que capataz marque un punto `en curso`, deja de ser sólo lector. Se decide cuando la lectura esté rodada, no antes | 2026-08-06 | pendiente (Pablo) |
| D4 | **Mirar la primera corrida del CI, en la web.** El workflow está escrito y ensayado en un clon sin vecinos (T6), pero **desde el contenedor de un agente el resultado no se puede leer**: `api.github.com` está fuera de la lista blanca y `gh` no está instalado. Es de Pablo porque el navegador está de ese lado. Y hay motivo concreto: a ERP 360 los `.sh` le viajaron sin bit de ejecución y su CI estuvo en rojo un día entero sin que nadie lo viera. La primera corrida que hay que abrir es la de la rama `t10-mirar-la-nube` | 2026-08-06 | pendiente (Pablo) |
| D5 | **Las carpetas del proyecto desaparecen de la Mac, y ya pasó dos veces.** `ERP360-Template/` se fue entre las 01:26 y las 02:24 del 2026-08-06; **la carpeta `capataz/` entera se fue a las 03:12 del mismo día**, con la tanda T10 a medio escribir y sin commitear —se rehízo clonando de GitHub, y por eso ahora se commitea y se empuja seguido—. **No fue capataz**: sólo lee, y `verificar-lector.py` § 1 lo verifica sobre el árbol sintáctico. Lo que sí cambió: **capataz ya no se queda ciego por esto** (T10), porque lee de GitHub. Lo que falta saber es **qué borra las carpetas**, que es de la máquina y no del código | 2026-08-06 | pendiente (Pablo) |

### Se puede hacer sin preguntar

| # | Qué falta | Desde | Estado |
|---|---|---|---|
| T2 | **Ni ERP 360 ni Finca 360 dejan el total de aserciones medido**, así que capataz muestra «no sé» en todas sus ramas — que es lo correcto y también es inútil. El arreglo son tres líneas en el `verificar.sh` de cada uno, las mismas que ya tiene el de capataz: escribir el total en `pruebas/total-aserciones.txt` sólo cuando está todo verde. Es trabajo **en el repo de ellos**, no acá. Al 2026-08-06 Finca 360 pasó a ser repositorio git (`cf6add0`), así que ahora también tiene dónde dejarlo | 2026-08-06 | pendiente |
| T3 | **Un `en curso` sin fecha no dice hace cuánto.** El lector saca la antigüedad de la columna `Desde`, que es la fecha en que nació el punto y no la de la toma: un punto tomado hoy que nació hace un mes se ve como un `en curso` de treinta días. T10 arregló la mitad —cuándo se movió la **rama** de ese agente sí se sabe, al segundo— y dejó la otra: cuándo se **tomó el punto**. Está en el commit que escribió la celda `en curso (fulano)`, y se saca con un `git log -S` sobre el seguimiento. `panel/agentes.jsonl` ya no cuenta: no llega a la nube | 2026-08-06 | pendiente |
| T4 | **Un proyecto cuyas tablas de puntos no tengan columna `#` se lee como vacío**, en silencio. Hoy se cuenta en `tablas_ignoradas` y no se muestra: mostrarlo siempre sería el aviso que sale siempre. Falta la forma que avise **sólo cuando importa** —cero puntos leídos y una tabla ignorada— y un arnés que lo vea rojo | 2026-08-06 | pendiente |
| T6 | **El CI está escrito y nadie lo vio correr.** `.github/workflows/verificar.yml` existe y corre `./verificar.sh` y nada más; se ensayó clonando el repo a `/tmp` —donde los proyectos vecinos no existen, igual que en el runner— y la suite dio **268 aserciones en verde**, el mismo número que en la carpeta de trabajo. Eso es la mitad: **falta ver una corrida de verdad**, y desde acá no se puede → D4. Queda `pendiente` a propósito: un `hecho` que nadie vio correr es exactamente la clase de línea que esta tanda tuvo que reconciliar | 2026-08-06 | pendiente |
| T8 | **El total de aserciones se mueve con el largo de este archivo.** `verificar-contrato.sh` cuenta **una aserción por fila con columna `Estado`** —honesto, cada fila se verifica de verdad— pero eso hace que agregar un punto suba el total sin que se haya verificado nada nuevo, y entonces «el total bajó» deja de ser una señal limpia. La salida es contar las filas en **una** aserción («ninguna de las N celdas usa una palabra fuera de las cinco») más otra de piso («hay al menos N filas»), que conserva la propiedad de que cero es falla. Es un cambio de diseño de un arnés ajeno, así que va como punto y no de paso | 2026-08-06 | pendiente |
| T9 | **Capataz no tiene `ops/60-roles.md`**, así que la tarjeta de su **propio** proyecto dice «qué roles existen · no sé». Es correcto —no se inventa la lista de otro— y es el único de los tres proyectos que puede arreglarlo sin tocar el repositorio de nadie. Va con la lista de roles que este proyecto use de verdad, no con la de seis copiada de ERP 360 | 2026-08-06 | pendiente |
| T11 | **La lectura del CI por la API está escrita y NADIE la corrió contra `api.github.com`.** `nube.pedir_ci()` arma el pedido, lo manda y traduce la respuesta; está verificado contra respuestas **escritas a mano** —`pruebas/grabado/actions-runs.json` lo dice en su primera línea— y contra la API de verdad **sólo del lado que falla**: desde el contenedor devuelve `000` y el resultado es «no sé» con el motivo, y eso sí se ejecuta (`verificar-nube.py` § 6). Falta correrlo **desde la Mac** con `CAPATAZ_CI=1 ./run.sh` y mirar que el chip del CI se pinte con la corrida de verdad. Es de quien tenga la Mac; el arnés ya tiene la rama del caso que anda y se pone verde solo cuando alguien la alcanza | 2026-08-06 | pendiente |
| T12 | **Finca 360 no está en GitHub, así que capataz no lo puede vigilar.** Es repositorio git local (`cf6add0`) y sin remoto. Queda declarado en `proyectos.json` con `repo: null` y su motivo, y la tarjeta lo muestra como «sin publicar · no sé» —ni rojo ni verde, porque no está roto: está sin publicar—. **La decisión fue no dejar un segundo camino de lectura local**: mantener el lector de carpetas vivo para un solo proyecto es mantener entera la clase de bug que esta tanda vino a matar. Se arregla publicándolo: `gh repo create` o a mano, un token propio, y esta línea pasa a ser un `repo`. **Hecho el 2026-08-06**: `pablosilveira16/finca360`, privado, **13 ramas** empujadas, y capataz le lee el seguimiento de 69.642 caracteres. Dos cosas que conviene tener escritas porque costaron una medición: **crear el repo en github.com no sube nada** —existía y devolvía cero refs, y el clon local no tenía ningún remoto ni upstream— y entre las 13 ramas viajó una `worktree-agent-…`, que es andamio de Claude Code y no de nadie. Falta el token propio → T23 | 2026-08-06 | hecho |
| T23 | **Finca 360 no tiene token propio**: `proyectos.json` declara `github-finca360.token` y ese archivo **no existe**. En la Mac no se nota porque el llavero de macOS contesta por él —por eso la lectura anda—, pero en el contenedor de un agente la tarjeta va a mostrar el error con lo que buscó, que es el comportamiento correcto y también es la tarjeta rota. Se crea siguiendo `ops/70-credenciales.md`: *fine-grained*, sólo `finca360`, Contents R/W + Metadata R, y el archivo en `~/Documents/frutos de cuyo/.credenciales/`. Es de Pablo porque el navegador está de ese lado | 2026-08-06 | pendiente (Pablo) |
| T24 | **La carpeta de credenciales de la Mac no es la que `nube.py` busca por defecto.** El código cae en `<padre del repo>/.credenciales` —o sea `/Users/Acer/Proyectos/.credenciales`, que **no existe**— y los tokens viven en `~/Documents/frutos de cuyo/.credenciales`. Hoy no se nota porque el llavero de macOS contesta primero, y por eso mismo es peligroso: el día que el llavero no esté, los tres proyectos van a fallar juntos por una ruta que nadie miró. Se destraba con `CAPATAZ_CREDENCIALES`, y lo que falta es decidir si eso va en `run.sh`, en el entorno, o si el default cambia | 2026-08-06 | pendiente |
| T13 | **Los dos tokens alcanzan los dos repositorios.** Medido el 2026-08-06: `github-capataz.token` lee `pablosilveira16/erp360` y `github-erp360.token` lee `capataz`. `ops/70-credenciales.md` dice «un token, un repositorio» y el alcance real es más ancho que eso — o son el mismo token, o se creó con *All repositories*. No rompe nada hoy y **no es urgente**, pero el runbook describe algo que no es cierto, y un runbook que miente en el alcance es el que hace que nadie revise el alcance | 2026-08-06 | pendiente (Pablo) |
| T14 | **El espejo no se limpia nunca.** `nube.py` deja un clon `--mirror` por repositorio vigilado en el temporal y no lo borra: son 300 KB por repo hoy, y con veinte repositorios y un proceso que no se reinicia deja de ser gratis. No se hizo ya porque borrar es escribir, y **la única escritura que capataz tiene hoy está acotada a crear el espejo**; agregar un borrado quiere su propia aserción de que no puede apuntar afuera. **Al 2026-08-15 esa aserción existe** —el T29 obligó a borrar para poder recuperar un espejo destripado, y el borrado quedó con su compuerta y sus cinco aserciones (T30)—, así que lo que falta acá ya no es el mecanismo sino la política: **cuándo** se limpia. Y hay un dato nuevo para decidirla: el sistema los limpia solo, por antigüedad, y a medias | 2026-08-06 | pendiente |
| T18 | **El taller: capataz ve los agentes y subagentes de esta máquina, en vivo.** `taller.py` lee `~/.claude` —el registro de sesiones y los `.meta.json` de cada subagente, 130 bytes cada uno— y arma el árbol sesión → agente → subagente. **De la transcripción `.jsonl` sólo mira el `mtime`: nunca la abre**, y el arnés lo verifica por AST (un solo `io.open`, cero `subprocess`, cero escrituras) y por la huella del disco antes y después. No contradice la regla 1 porque **no lee el mismo dato desde dos lugares**: lee uno que git no puede tener —si un proceso está vivo—. 50 aserciones, cuatro bugs vistos rojos | 2026-08-06 | hecho |
| T19 | **No se puede saber si un subagente terminó o se colgó, y por eso capataz no lo dice.** Medido sobre 17 subagentes: **adentro de su `.jsonl` no hay ninguna marca de cierre** —un agente en curso y uno terminado son indistinguibles por su última línea—. Se probó una segunda señal, «si el padre escribió después de que el hijo se calló, el hijo terminó», y **no discrimina**: dio verdadero en los 17 casos, que son 17 agentes terminados —cero casos negativos, aserción vacua de manual— y tiene contraejemplo, porque un subagente en background no frena al padre. Por eso el desenlace se llama `sin señal` y no `caído` ni `terminado`. Queda abierto: el cierre **sí** está en el transcripto del padre, y leerlo significa abrir una transcripción, que es justo lo que este módulo promete no hacer. Falta una salida que no rompa esa promesa | 2026-08-06 | pendiente |
| T20 | **El taller sólo ve esta máquina, y eso hoy se dice pero no se arregla.** Un agente en otra Mac o en un contenedor no aparece; la pantalla lo rotula («esta máquina · ahora») para no mentir. La salida candidata es **publicar por git los `.meta.json`** —130 bytes, y traen el árbol entero— con un latido que agregue lo que al meta le falta: arranque, última señal y cierre. **Los `.jsonl` no se publican jamás**: pesan entre 33 KB y 1,1 MB y son todo lo que el agente leyó. Quien escribe el latido tiene que ser el agente, no capataz —regla 1—, así que va como hook en el repo de cada proyecto. Y el límite honesto queda igual: un latido que se corta no distingue «murió» de «no pudo empujar», o sea `dudoso`, nunca `caído` | 2026-08-06 | pendiente (Pablo) |
| T21 | **El empate entre una sesión y su proyecto es por el nombre de la carpeta.** `taller.empatar` compara el `basename` del `cwd` contra el nombre del repositorio o del proyecto. Anda para los tres de hoy y se rompe el día que dos proyectos vigilados terminen en una carpeta con el mismo nombre. Lo que no empata **se muestra igual**, rotulado «carpeta que capataz no vigila», que es lo que evita que el bug se esconda | 2026-08-06 | pendiente |
| T22 | **`claude agents --json` está instalado y capataz no lo usa, a propósito.** Medido: para sesiones interactivas devuelve **seis** campos y `~/.claude/sessions/<pid>.json` devuelve **once**; `state` y `waitingFor` —los que valdrían— son *background only*, y no hay sesiones background en esta máquina. Colgar la pantalla en un subproceso para obtener menos que un `open()` no se paga. **La puerta queda abierta**: el día que se usen agentes en background (`claude --bg`), ese JSON agrega `state`, `waitingFor` y el `id` para `claude attach`, y ahí sí entra. **Se abrió el 2026-08-15**, y no por una decisión sino por una medición: se lanzó un background de verdad con `claude --bg` y el CLI trae `id`, `status` y **`state`**, que el archivo **no tiene**; y al pararlo **el archivo `<pid>.json` desaparece y sólo `--all` lo conserva** (`state: "stopped"`). O sea que hay un dato que `taller.py` no puede tener nunca, igual que `taller.py` tiene uno que git no puede tener. Sigue en pie lo otro: para una sesión **interactiva** el archivo gana, y por eso la consola **no vuelve a contestar** lo que el taller ya contesta → T25 | 2026-08-06 | hecho |
| T17 | **`node` no está instalado en la Mac, así que la pantalla no se verifica sola: 0 aserciones, y cero es falla.** `verificar-pantalla.js` es el único arnés que ejecuta el JavaScript de `capataz.html` —donde vive la regla 3, «no sé» nunca verde— y sin `node` saltea entero: el 2026-08-06 la suite dio **335 aserciones y 4 rojas** con las de la pantalla afuera del total y afuera del rojo. En la Tanda 3 se bajó el binario oficial (v24.19.0 LTS, sha256 verificado contra `SHASUMS256.txt`) a una carpeta temporal y con él **la suite entera dio 421 aserciones**, con las 69 de la pantalla adentro. Lo que falta es que quede instalado de verdad —`sudo cp -R node-v24.19.0-darwin-arm64/{bin,include,lib,share} /usr/local/`, y eso pide la contraseña de Pablo—; mientras tanto cada corrida depende de que alguien acerque un `node` a mano. **Cerrado el 2026-08-06, y la premisa estaba vieja:** node **ya estaba instalado** —v22.14.0 de nodejs.org, en `~/.local/src` con symlinks en `~/.local/bin`, puesto ahí para los arneses JS de Finca 360— y no hizo falta ninguna contraseña. Lo que fallaba era el **PATH**: `~/.zshrc` lo exporta y `.zshrc` **sólo lo lee la shell interactiva**, así que un script, un cron o un proceso lanzado por otro programa seguían sin verlo. El arreglo fue mover el `export` a `~/.zprofile`. La suite entera pasó de 431 a **495 en verde**, con las 83 de la pantalla adentro. Lección: *«no está instalado» era «no está en el PATH de esta shell», y nadie volvió a medirlo* | 2026-08-06 | hecho |

### Decidido, esperando el momento

| # | Qué | Desde | Hasta cuándo | Estado |
|---|---|---|---|---|
| T7 | **El `panel/` de ERP 360: reemplazar la mitad que mira, nunca absorber la que escribe.** La decisión está tomada y escrita en `BITACORA.md`, Tanda 1. `panel/agente.py` + `panel/agentes.jsonl` **no se absorben nunca** —escriben, y capataz sólo lee—; `panel/panel.py` + `panel/panel.html` (5401) los reemplaza capataz, que mira varios proyectos, entra en un teléfono y dice «no sé» donde el panel no dice nada. **No se ejecuta todavía** porque hoy ese panel es lo único que le da a un agente de ERP 360 una pantalla sin depender de que capataz esté levantado. Y **no lo ejecuta capataz**: es un cambio en el repositorio de ellos | 2026-08-06 | que se decida D3, y que vuelva `ERP360-Template/` (D5) | diferido |
| X1 | **Que capataz muestre el CI de verdad en el tablero.** El mecanismo está (T5); lo que falta es dónde corre capataz | 2026-08-06 | que se decida D3 | diferido |
| X2 | **Despliegue.** Hoy corre en `127.0.0.1:5402` con el servidor de la biblioteca estándar, que no va a producción. Y para leerlo desde el teléfono hace falta que llegue desde afuera de la Mac, que es una decisión de red antes que de código. Medido el 2026-08-06 probando un túnel: **el DNS de la red de casa devuelve `NXDOMAIN` para `api.trycloudflare.com`** —con `1.1.1.1` resuelve `104.16.230.132`—, así que un túnel rápido de Cloudflare no levanta sin cambiarle el DNS a la Mac. `cloudflared` 2026.7.3 quedó bajado y anda; lo que no anda es el nombre | 2026-08-06 | que se decida D3 | diferido |

---

# Historia por tanda

Lo de abajo es el registro de cada tanda, con los puntos ya cerrados. **Para
saber qué falta no hace falta leerlo**: está todo arriba.

---

## Tanda 0 — el andamio y el lector, 2026-08-06

El proyecto arranca siguiendo al pie el orden de
`ERP360-Template/documentacion/andamio-proyecto-nuevo.md`, § «El orden». Los
cuatro primeros puntos son el andamio y **ninguno toca la aplicación**; el
código empieza en el A5.

Los números de aserciones de esta tabla estaban viejos y se corrigieron el
2026-08-06 corriendo cada arnés; el detalle está en `BITACORA.md`, Tanda 1.

| # | Punto | Estado |
|---|---|---|
| A1 | Este seguimiento, con el contrato y los cinco estados, **vacío** | **hecho** · `verificar-contrato.sh` 38 aserciones — commit `eb6a341` |
| A2 | `verificar.sh` y un arnés que verifique lo más tonto que se me ocurra | **hecho** · `verificar-contrato.sh` 38 aserciones — visto en rojo con un estado inventado |
| A3 | `git init` y el primer commit, **antes de la primera línea de la app** | **hecho** · commit `eb6a341`, y `core.filemode true` puesto desde el día cero |
| A4 | `CLAUDE.md` con tres reglas — no diez | **hecho** · `verificar-contrato.sh` §§ 4 y 5, 38 aserciones — 72 de 72 líneas y todo lo que nombra existe, commit `f968fa6` |
| A5 | `lector.py`: los dos formatos de seguimiento, los roles, la cuadrilla, las ramas y el CI | **hecho** · `verificar-lector.py` 81 aserciones — proyectos de verdad armados en `/tmp` |
| A6 | `capataz.py` y `capataz.html` en el 5402, sin dependencias | **hecho** · `verificar-angosto.py` 28 aserciones — se ejecuta `render_estatico()` y se mira el HTML producido |
| A7 | `ops/`, con la marcha atrás **antes** que el despliegue | **hecho** · `verificar-angosto.py` 28 aserciones — el puerto del mapa y el de `capataz.py` son el mismo |
| T1 | La plomería para empujar a GitHub, traída de ERP 360 y adaptada | **hecho** en la Tanda 1 · `verificar-credenciales.py` 75 aserciones — commit `1f893c3`. **Figuró `hecho` sin estarlo**: citaba un arnés que no existía |

---

## Tanda 1 — reconciliar y cerrar, 2026-08-06

La tanda empieza ordenando lo que este archivo decía y no era: a `coder-1` lo
interrumpieron antes de cerrar por escrito. El capítulo completo —qué mentía, y
qué se hizo para que no vuelva a pasar— está en `BITACORA.md`, Tanda 1.

| # | Punto | Estado |
|---|---|---|
| R1 | **Reconciliar este archivo con lo que existe de verdad**, punto por punto y corriendo cada arnés — y escribir `BITACORA.md`, que `CLAUDE.md` nombraba desde el día cero y no existía | **hecho** · `verificar-contrato.sh` 38 aserciones — §§ 4 y 5 nuevas: miden el tope de 72 líneas y que exista cada archivo que `CLAUDE.md` nombra. **Vistas en rojo** con `BITACORA.md` ausente y con `CLAUDE.md` en 73 líneas |
| T1 | **La plomería para empujar**: `ops/credencial-github.sh` commiteado, `ops/empujar.sh` y `ops/70-credenciales.md` traídos de ERP 360 y adaptados | **hecho** · `verificar-credenciales.py` 75 aserciones — commit `1f893c3`. Ejecuta el helper y `empujar.sh` de verdad, y clona el repositorio para comprobar que una copia nueva queda configurada. **Visto en rojo** con la ruta del helper escrita en vez de calculada |
| R2 | **La pantalla, ejecutándola**: la regla 3 estaba verificada en el lector y **no en la pantalla**, que es donde alguien la lee | **hecho** · `verificar-pantalla.js` 36 aserciones — corre el JavaScript de `capataz.html` en un `vm` con los datos de verdad. **Visto en rojo**: con `clase = e === "rojo" ? "rojo" : "verde"` puesto, se caen siete aserciones y el chip dice «CI · no sé» pintado de verde |
| R3 | **Que todo `.sh` versionado viaje ejecutable**, mirando el índice y no el disco — la factura que ERP 360 pagó con un día de CI en rojo que nadie vio | **hecho** · `verificar-credenciales.py` 75 aserciones, y la misma compuerta adentro de `ops/empujar.sh`. **Visto en rojo** con `git update-index --chmod=-x run.sh` |
| R4 | **Que el total de aserciones sea comparable.** Medido: 274 en la carpeta de trabajo y 260 en un clon sin vecinos, sin que hubiera cambiado nada — el arnés de la pantalla sumaba una aserción por proyecto | **hecho** · `verificar-pantalla.js` 36 aserciones — agrupado da el mismo número en los dos lados —268 el 2026-08-06— y el detalle sigue diciendo cuál falló |
| D1 | **Mirar la pantalla en un teléfono** — el requisito que motiva el proyecto | **hecho** · `verificar-angosto.py` 28 + `verificar-pantalla.js` 36 aserciones, **y mirada**: Chrome con un viewport de 360 px de verdad. `scrollWidth == clientWidth == 360`, sin scroll horizontal, la hoja en 340 px, **cero elementos pasando de 360**, las tres tarjetas legibles. Lo que queda —un teléfono físico— ya no bloquea nada |
| D2 | **El repositorio `github.com/pablosilveira16/capataz` y el token** | **hecho** · `verificar-credenciales.py` 75 aserciones — `main` publicado en `4d08197`, y el permiso **`Workflows: Read and write` confirmado**: el push de esta rama llevó `.github/workflows/verificar.yml` y entró. Es justo el permiso que a ERP 360 le faltó y le rechazó el push entero |

---

## Tanda 2 — capataz mira la nube, 2026-08-06

El cambio de diseño que Pablo pidió con una frase: **«capataz siempre tiene que
estar mirando la nube de GitHub, justamente ésa es la gracia, y al observar
variaciones en vivo va a poder ver los agentes que se prenden y apagan».** El
capítulo con las decisiones —por qué git y no la API, qué se hizo con
`agentes.jsonl` y con Finca 360, y por qué un espejo no contradice la regla 1—
está en `BITACORA.md`, Tanda 2.

Y la tanda se ganó su propia cicatriz: **a las 03:12 la carpeta `capataz/`
desapareció entera de la Mac**, con el trabajo sin commitear. Se rehízo clonando
`main` de GitHub. Es exactamente el bug que la tanda vino a arreglar, esta vez
del lado del que escribe (D5).

| # | Punto | Estado |
|---|---|---|
| T10 | **Capataz lee de GitHub y no de carpetas.** `nube.py` nuevo: espejos `--mirror` descartables en el temporal, `SEGUIMIENTO.md` y `ops/60-roles.md` leídos de `main`, las ramas con su autor y hace cuánto, los commits recientes y el total medido de cada rama. `proyectos.json` pasó de `ruta` a `repo` (`owner/repo`) + `token`. `lector.py` quedó **puro**: sin red, sin disco, sin un solo `subprocess` | **hecho** · `verificar-nube.py` 81 aserciones (contra los repositorios reales) + `verificar-lector.py` 95. **Visto en rojo** sacando `--no-single-branch` —el espejo trae 1 rama de 3— y sacando la compuerta de destino de `_git()`, que deja correr git sobre el repositorio de otro |
| T10b | **Prendido o caído, que es lo que se quería ver.** Cinco desenlaces por rama: `principal`, `integrada` (nada por delante de `main` — **no** es un agente caído), `trabajando` (< 45 min), `dudoso` (< 4 h, y capataz no afirma nada) y `caído`. Más `sin rama`, para un `en curso (fulano)` del que no llegó ni un commit | **hecho** · `verificar-lector.py` 95 aserciones —los dos lados de cada umbral— y `verificar-pantalla.js` 50, que mira los colores dibujados. **Visto en rojo** con un solo umbral (una rama integrada pasa a «caído») y pintando `dudoso` con la clase de `trabajando` |
| T10c | **La cuadrilla sale de git y `panel/agentes.jsonl` se dejó de leer.** Ese archivo no se versiona a propósito, así que **nunca llega a la nube**: leerlo de la carpeta local era mostrar los agentes de una máquina como si fueran la cuadrilla entera. Quién trabaja son ahora las ramas empujadas y los autores de los commits | **hecho** · `verificar-lector.py` § 4. El rol se deduce del nombre (`coder-3` → `coder`) y de un nombre de persona **no se deduce ninguno**, que es lo que pasa de verdad en ERP 360 |
| T10d | **Un repositorio que no se pudo leer se ve como error con lo que buscó**, nunca como cero puntos: una ruta donde va un `owner/repo`, una URL entera, un repositorio inexistente y uno privado sin credencial. Y ningún mensaje de error puede llevar algo con forma de token | **hecho** · `verificar-nube.py` § 4, 81 aserciones. **Visto en rojo** haciendo que `leer()` devuelva `ok=True` vacío ante un error: seis rojas |
| T10e | **El espejo es descartable, y hay una aserción que lo prueba**: se borra entero, se vuelve a leer y sale byte por byte lo mismo. Es lo que hace que escribir en `/tmp` no contradiga «capataz no guarda estado propio» | **hecho** · `verificar-nube.py` § 5. **Visto en rojo** guardando un contador de lecturas adentro del espejo —un dato que no está en GitHub—: `veces_leido: 1` contra `2` |
| T5 | **La lectura del CI, detrás de una variable de entorno.** `nube.pedir_ci()` arma el pedido a `api.github.com`, lo manda y `interpretar_ci()` lo traduce. Apagada por defecto (`CAPATAZ_CI=1`), y **sin ella el resultado se queda en «no sé», nunca en verde** | **hecho** · `verificar-nube.py` § 6, 81 aserciones. Lo que **no** se pudo probar acá —la API real— quedó abierto como T11, y las respuestas grabadas dicen en su primera línea que son escritas a mano |

---

## Tanda 3 — el visor por agente, en vivo, 2026-08-06

La pantalla dejó de ser «tres tarjetas de proyecto» y pasó a ser **quién está
trabajando ahora**. El pedido fue textual: *«el primer visor tiene que ser por
agente, y un demoncito en js que actualice una vez por segundo, así puedo ver en
directo cuando un agente se despierta»*. El capítulo está en `BITACORA.md`,
Tanda 3.

| # | Punto | Estado |
|---|---|---|
| T18 | **La vista primaria son los agentes de todos los proyectos, no los proyectos.** `lector.agentes()` junta la cuadrilla de cada uno y ordena por **quién se movió recién** —al revés que la cuadrilla de un proyecto, que pone primero al que hace más que no se mueve—; el mismo nombre en dos proyectos son dos renglones, porque son dos trabajos. Los proyectos siguen abajo: contestan otra pregunta | **hecho** · `verificar-lector.py` 105 aserciones (§ 4b) + `verificar-pantalla.js` 69 (§ 7). **Visto en rojo** invirtiendo el orden —queda `coder-3` donde va `coder-8`— y sacándole el sha a la cuadrilla |
| T19 | **El demonio de un segundo, y los tres relojes que no se pueden confundir.** 1 s la pantalla repinta y **vuelve a decidir el estado** con los umbrales que manda el servidor —copiarlos en el HTML serían los mismos dos números en dos lugares—; 2 s le pide `/api/estado`; 15 s capataz le pregunta a GitHub. El tercero bajó de 60 s y es el único que hace que un agente aparezca antes: medido, `git fetch` cuesta 1,2 s por repositorio | **hecho** · `verificar-pantalla.js` 69 aserciones — los dos lados de cada umbral **decididos en la pantalla**, sin ninguna lectura nueva. **Visto en rojo** haciendo que la pantalla se quede con el estado del servidor: cuatro rojas |
| T20 | **«Se despertó» es un sha nuevo, no un reloj que avanzó.** La fila late unos segundos cuando cambia el sha de la rama de ese agente, y también cuando aparece uno que no estaba. La primera lectura **no** marca a nadie: si no, abrir la pantalla parecería que empujaron todos | **hecho** · `verificar-pantalla.js` § 7. **Visto en rojo** marcando por tiempo en vez de por sha: la primera lectura y la relectura idéntica avisan las dos |
| T21 | **La frescura que se muestra es la del `fetch`, no la del vistazo al espejo.** `leido_en` se mueve en cada pedido de la pantalla, así que la pantalla decía «GitHub leído hace 1 s» **para siempre**, aunque el último `fetch` fuera de hace quince segundos. Ahora viaja `traido_en` —la marca que deja git en `FETCH_HEAD`— y sin ella se dice «no sé». Y si el servidor deja de contestar, la pantalla lo dice y apaga lo que muestra en vez de seguir pintándolo como si fuera de ahora | **hecho** · `verificar-nube.py` § 5b, 82 aserciones + `verificar-pantalla.js` § 7. **Visto en rojo** con las dos marcas confundidas, y sin la marca del `fetch`: tres rojas, incluidas las de que el espejo es descartable |
| T22 | **La aserción del espejo descartable dice ahora QUÉ cambió, no «algo cambió».** Comparaba dos JSON como cadenas; compara los **caminos** que difieren, y el único admitido es `/nube/traido_en`. Salió de que el cambio de T21 la puso roja con razón: un clon nuevo se acaba de traer | **hecho** · `verificar-nube.py` § 5, 82 aserciones. **Visto en rojo** dejando `_traido_en()` sin ninguna marca que mirar |
| T15 | **El arnés de la nube daba por sentado que `erp360` era privado, y los dos repositorios son públicos**: sin credencial se leen igual, así que el caso «no se alcanza sin credencial» no ejercitaba nada de lo que decía —tres rojas—. Ahora **se mide con `git ls-remote` y sin credencial** cuál repositorio usar, y hay una aserción de que el elegido de verdad no se alcanza | **hecho** · `verificar-nube.py` 86 aserciones — § 4. **Visto en rojo** apuntando el caso a un repositorio público: se caen cuatro, y la primera es la que dice que el caso es vacuo |
| T16 | **El arnés de credenciales se ponía rojo con un señuelo falso**, el `github_pat_…` de `verificar-nube.py`. No había ninguna credencial filtrada —el literal es inventado— pero el arnés no puede distinguir un señuelo de un token de verdad, **y no debe poder**: una lista de excepciones es por donde se escapa el primero real. El literal estaba en `0706590`, la rama local de respaldo y **nunca empujada**, así que no hubo que reescribir nada publicado: se desarmó el señuelo en pedazos, como ya estaba en la rama de trabajo | **hecho** · `verificar-credenciales.py` 75 aserciones — la historia entera contra el patrón del arnés da cero apariciones |

---

## Tanda 4 — la consola: los agentes background, 2026-08-15

El pedido de Pablo: **que el panel consuma la vista `claude agents` de consola**.
El T22 la tenía rechazada con una medición del 2026-08-06 que era correcta y
envejeció: *el CLI da menos que el archivo*. Se volvió a medir y hay un caso
donde da algo que el archivo **no puede tener**. El capítulo está en
`BITACORA.md`, Tanda 4.

| # | Punto | Estado |
|---|---|---|
| T25 | **`consola.py`: los agentes background salen del CLI, y sólo ellos.** Un `subprocess` único con argv **constante** —`claude agents --json --all`, nunca armado con nada de afuera— y un tope de tiempo, para que la pantalla no quede colgada de un proceso ajeno | **hecho** · `verificar-consola.py` 103 aserciones (§§ 1, 2 y 5) + `verificar-pantalla.js` 99 (§ 9). Contra el CLI **de verdad**: si `claude` no está, es rojo y no salteo. **Visto en rojo** sacándole la compuerta a las banderas que despachan (18 rojas), sacando `stdin=DEVNULL` (3, y una de ellas es un CLI que pide una tecla y cuelga la pantalla 5 s) y poniendo la compuerta **después** del `subprocess` |
| T26 | **La regla escrita de cuál fuente gana**, que es la regla 1 aplicada al caso en que de verdad hay dos: para una sesión interactiva **gana el archivo** (doce campos contra seis) y la consola no la vuelve a contestar; el `state` y los background terminados **sólo existen en la consola**. Y donde las dos hablan del mismo hecho y no coinciden, **el desacuerdo se muestra** en vez de resolverse en silencio | **hecho** · `verificar-consola.py` § 4, 103 aserciones — las dos mitades: que `cotejar` **encuentre** un desacuerdo de verdad y que **no invente** los dos que están medidos. **Visto en rojo** haciendo que `cotejar` devuelva siempre vacío: 6 rojas |
| T27 | **`bg` y `background` son la misma palabra**, y declararlo es la diferencia entre un desacuerdo y el aviso que sale siempre. El archivo dice `kind: "bg"` y el CLI dice `kind: "background"` para la misma sesión: si eso cuenta como desacuerdo, la pantalla avisa en todas las corridas y el corolario de la regla 3 dice que ese aviso enseña a ignorarse | **hecho** · `verificar-consola.py` § 4 + `verificar-pantalla.js` § 9, que tiene una aserción de **cada lado**: con desacuerdos se dibuja, sin desacuerdos no se dibuja nada. **Visto en rojo** sacando `bg` de `ALIAS_KIND`. Hizo falta que `taller.sesiones()` trajera la clase cruda: sin eso la comparación de clase no comparaba nada |
| T28 | **Sin `claude` en el PATH la consola dice «no sé» con lo que buscó**, nunca cero agentes — y capataz sigue mostrando todo lo demás. Es el mismo caso que el CI: la parte que no se pudo leer se ve faltando, y no apaga el tablero | **hecho** · `verificar-consola.py` § 5, 103 aserciones — cinco `claude` de mentira: uno que no existe, uno que contesta basura, uno que contesta un objeto, uno que sale con código 3 y uno que se cuelga. **Visto en rojo** haciendo que `leer()` devuelva `ok=True` ante un error: 3 rojas |
| T29 | **El limpiador de temporales dejaba los espejos destripados y capataz no se recuperaba nunca.** Encontrado **mirando la pantalla**, no con un arnés: los tres proyectos aparecían ilegibles con «not a git repository». `/var/folders/…/T` es temporal de verdad y macOS le borra los archivos viejos **dejando los directorios**, así que los espejos quedaron con `objects/` y `refs/` pero sin `HEAD` ni `config`; capataz decidía «ya está clonado» mirando si existía la **carpeta** `objects/`, hacía `fetch` contra el esqueleto y no se recuperaba ni reiniciando. Ahora se pregunta por los archivos que hacen que git lo reconozca, y un espejo destripado se tira y se vuelve a clonar | **hecho** · `verificar-nube.py` § 5c, 99 aserciones — se reproduce el destripe exacto. **Visto en rojo** volviendo a preguntar por `objects/`: 3 rojas, y la primera trae el mismo «not a git repository» que se veía en la pantalla |
| T30 | **El borrado de un espejo es la primera escritura destructiva de capataz, y llega con compuerta.** Es lo que el T14 pedía por escrito. Se verifica que no pueda apuntar a la raíz del repo, ni a su padre, ni a la carpeta de espejos entera, ni afuera por un `..` — y que **sí** tire uno propio, que es la anti-vacua de las otras cuatro | **hecho** · `verificar-nube.py` § 5c. **Visto en rojo** sacando la compuerta de destino, y **encontró un bug de verdad en el arreglo**: la guarda «si no existe, salgo» estaba escrita **antes** que la compuerta, así que un destino de afuera se iba por el `return` sin pasar por ningún control |
| T31 | **Una roja del arnés del taller que iba y venía sola.** «Se encontró al menos un agente de verdad» es la aserción anti-vacua de su § 5, y dependía de que **en ese momento** hubiera un subagente colgando de una sesión todavía registrada como viva — que es lo raro: los metas quedan en disco cuando la sesión cierra, pero `leer()` sólo llega a los de las sesiones vivas. La suite quedaba roja según lo que estuviera corriendo, y una roja que aparece y desaparece sola es la que hace que se deje de mirar el color. Ahora, si no hay ninguno por ese camino, los metas se buscan en disco y se leen **con el lector de verdad** | **hecho** · `verificar-taller.py` § 5, 50 aserciones — 18 metas reales en 6 carpetas de sesión. Se la vio roja antes del arreglo, y es **anterior a esta tanda**: da idéntica con y sin los cambios de la consola |

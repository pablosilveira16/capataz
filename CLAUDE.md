# Reglas de esta carpeta

Una página, **tope duro de 72 líneas**: el valor de este archivo es que se lee
entero antes de empezar, y un archivo que crece deja de leerse. Si algo entra,
algo sale. Lo que **falta** va en `SEGUIMIENTO.md`, el *por qué* en `BITACORA.md`;
`pruebas/verificar-contrato.sh` verifica el tope y que exista lo que se nombra acá.

**Son tres reglas y no diez.** Van a ser diez; se ganan una por una, cada una con
el día que costó. Una regla sin cicatriz es una regla que nadie respeta.

## Empezar y terminar

1. **Leer `SEGUIMIENTO.md`.** Es la única lista de lo que está abierto: lo que no
   está escrito ahí, no existe. Y la bitácora, sólo el capítulo del tema.
2. `./run.sh` → **http://127.0.0.1:5402**. El puerto está fijo en `capataz.py` y
   escrito en `ops/00-mapa.md`; los vecinos ocupados son el 5300, 5301 y 5302 (VM
   de Oracle), el 5400 (app de ERP 360) y el 5401 (panel de ERP 360).
3. **Acá hay git: el respaldo es el commit.** Nada de copias `.antes-de-*`.
4. Al terminar: `./verificar.sh` en verde **con el total**, y cerrar por escrito
   —`SEGUIMIENTO.md` y `BITACORA.md` siempre—. Un punto nuevo se anota **apenas
   aparece**: el seguimiento existe para la sesión que se corta.

## 1 · Capataz sólo lee, y lee **de GitHub**. No es fuente de verdad de nada

El `SEGUIMIENTO.md` de cada repositorio es la verdad y **git es el árbitro**. Si
el remoto decide quién tiene qué punto, el remoto **es** la verdad: un agente
corre en cualquier máquina y su trabajo se ve cuando empuja. Por eso un proyecto
se declara `owner/repo` en `proyectos.json` y no como carpeta — el día que
`ERP360-Template/` desapareció de la Mac, capataz se quedó ciego con el
repositorio entero publicado.

Capataz mira y muestra: no decide, no lanza agentes, no marca puntos y **no
guarda estado propio**. Dos lugares con el mismo dato y ninguna regla sobre cuál
gana es **el bug más caro de Finca 360**. Verificado: **`lector.py` no escribe,
no corre nada y no importa nada que salga del proceso** (`pruebas/verificar-lector.py`
§ 1), y **`nube.py` sólo corre git contra su espejo descartable** — borrarlo y
releer da lo mismo. → `pruebas/verificar-nube.py` §§ 1 y 5

## 2 · Un arnés no vale hasta verlo rojo, y menos si es vacuo

**Nuevo o cambiado, se pone el bug de vuelta y se mira el rojo** — después se
revierte y se confirma con `diff -q`. Si no está escrito que se lo vio, no se lo
vio. Y **cuando un arnés falla, la primera hipótesis es el arnés.**

**El caso vacuo es el que más caro sale**, porque se cuenta en el total y da
sensación de cobertura: una aserción que pasa igual con el bug puesto no verifica
nada. La forma que ya salió mal cuatro veces en el proyecto hermano: **leer un
archivo y buscar una cadena no prueba que el código corra.** Y su forma nueva:
**un lector de red probado sólo contra respuestas grabadas pasa entero con la
red rota**, así que `nube.py` se ejercita contra los repositorios de verdad.
→ `pruebas/verificar-lector.py`, `pruebas/verificar-nube.py`

**El total de aserciones es parte del resultado**, y cero aserciones es falla: un
arnés que deja de encontrar lo que mira no se pone rojo, saltea en silencio y lo
único que cambia es la cuenta. → `verificar.sh`

## 3 · Lo que no se sabe se muestra «no sé», nunca verde

Un tablero que miente en el caso que importa es peor que no tenerlo: **al que
miente se le cree**. Tres datos pueden faltar y tienen que verse faltando:

- **El CI.** `api.github.com` está fuera de la lista blanca del contenedor de un
  agente —medido, no supuesto—: `github.com` anda y la API no. Sin respuesta,
  `no sé`; jamás `verde`. Va detrás de `CAPATAZ_CI=1`.
- **El repositorio que no se pudo leer.** Sin credencial o inexistente se
  muestra el **error con lo que buscó**, nunca cero puntos: se leen igual.
- **Un agente que no se sabe si trabaja.** Una rama que no se mueve hace un rato
  es `dudoso` y no `caído`; una sin nada por delante de `main` está `integrada`.
- **El total de una rama** y **los roles** de quien no publica esos archivos.

Corolario: **no se agrega un aviso que sale siempre.** Enseña a ignorarlo, y el
día que dice algo tampoco se lee. → `pruebas/verificar-pantalla.js` § 6

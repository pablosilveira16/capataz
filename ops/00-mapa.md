# El mapa: dónde vive cada cosa y quién llega a qué

> Lo primero que se lee antes de tocar cualquier cosa de ambientes, puertos o
> despliegue. Lo que está **sin decidir** dice «sin decidir», que es distinto de
> estar en blanco: un ambiente que nadie decidió no se documenta como si
> existiera.

## Los ambientes

| Ambiente | Dónde | Estado |
|---|---|---|
| **DEV** | La Mac de Pablo y el contenedor de un agente, sobre la misma carpeta montada | **El único que existe hoy** |
| QAS | — | Sin decidir → punto X2 del seguimiento |
| PRD | — | Sin decidir → punto X2 del seguimiento |

Los runbooks de crear, desplegar y promover **no se escriben** hasta que haya un
ambiente de verdad. Un runbook que describe un ambiente imaginario es peor que
no tenerlo, porque el día que haya uno alguien lo va a seguir.

## Los puertos

Medido antes de elegir, que es el orden que evita elegir uno ocupado:

| Puerto | Quién | Dónde |
|---|---|---|
| 5300 | Finca 360 | VM ARM de Oracle |
| 5301 | ocupado | VM ARM de Oracle |
| 5302 | ocupado | VM ARM de Oracle |
| 5400 | app de ERP 360 | local |
| 5401 | panel de agentes de ERP 360 | local |
| **5402** | **capataz** | local |

El 5402 está declarado en **un solo lugar del código** —`PUERTO_POR_DEFECTO` en
`capataz.py`— y repetido en `CLAUDE.md` y acá.
`pruebas/verificar-angosto.py` § 4 se pone rojo si los tres dejan de coincidir:
un puerto que vive en dos lugares que se separan es exactamente cómo se elige
uno ocupado.

## A quién le contesta capataz, que no es lo mismo que el puerto

Por defecto, **sólo esta máquina**: `capataz.py` escucha en `127.0.0.1`
(`SOLO_ESTA_MAQUINA`). No es prudencia genérica —el tablero muestra los
seguimientos de tres proyectos, la rama y la carpeta de cada agente, y no pide
ninguna credencial— y por eso abrirlo es un acto de cada arranque:

```
./run.sh              sólo esta Mac
./run.sh --telefono   CAPATAZ_ESCUCHA=0.0.0.0 — cualquiera en la wifi de casa
```

**El nombre para el teléfono ya existe y no hay que crear ninguno.** Medido el
2026-08-17 en esta Mac:

| Nombre | Resuelve a | Quién lo publica |
|---|---|---|
| `MacBook-Air.local` | 192.168.100.58 **y** 127.0.0.1 | Bonjour, de fábrica |
| `cualquier-cosa.localhost` | 127.0.0.1 | el resolver de macOS, de fábrica |

O sea que `/etc/hosts` no hace falta tocarlo, y sigue con las tres líneas que
trae de fábrica.

**Y la trampa, que costó una medición**: `MacBook-Air.local:5402` contesta 200
**desde la propia Mac** aunque el teléfono no pueda entrar, porque el nombre
resuelve también a loopback y el cliente cae ahí. La prueba que vale es contra
la IP de la wifi. Eso está verificado ejecutando dos servidores de verdad en
`pruebas/verificar-angosto.py` § 6.

## La misma carpeta, dos rutas

`frutos de cuyo` está montada en dos lugares a la vez:

```
/Users/Acer/Documents/frutos de cuyo/…          la Mac
/sessions/<sesión>/mnt/frutos de cuyo/…         el contenedor de un agente
```

Es **una sola carpeta**, con un solo `.git/config`. Por eso ninguna ruta se
escribe absoluta: ni en `proyectos.json` —las rutas son relativas al propio
archivo— ni en el helper de credenciales, que la calcula con `git rev-parse`.
Una ruta absoluta ahí deja andando a uno y roto al otro, según quién corrió algo
último. La factura de esa lección la pagó ERP 360.

## Quién llega a qué

- **Un agente en su contenedor**: la carpeta montada, `github.com` por HTTPS y
  poco más. **`api.github.com` está fuera de la lista blanca** —devuelve `000`,
  medido en ERP 360 y vuelto a medir el 2026-08-06— y `gh` no está instalado,
  así que **el estado del CI no se puede leer desde acá**. `codeload.github.com`
  y `raw.githubusercontent.com` también dan `000`: el **único** camino a GitHub
  es `git` contra `github.com`, que es por donde capataz lee todo lo demás. El
  puerto 22 está cerrado: SSH y las deploy keys no son una opción, y por eso el
  push es HTTPS con token.
- **Pablo, en la Mac**: todo lo anterior más el navegador, que es lo único que
  puede *mirar* la pantalla angosta (punto D1) y abrir una corrida del CI.
- **Nadie llega a un servidor**, porque no hay ninguno todavía.

## Qué mira capataz, y qué no toca

Capataz **sólo lee, y desde el 2026-08-06 lee de GitHub y no de ninguna
carpeta**. Un proyecto es un `owner/repo` en `proyectos.json`. De cada uno saca,
por `git` contra `github.com`:

```
main:<su archivo de seguimiento>        los puntos, sus estados y quién tiene cuál
main:ops/60-roles.md                    qué tipos de agente existen ahí
refs/heads/*                            las ramas, su autor y hace cuánto se movieron
<rama>:pruebas/total-aserciones.txt     el total MEDIDO de cada rama
git log --all                           los commits recientes, con autor
```

**El `panel/agentes.jsonl` ya no se lee.** No se versiona a propósito, así que
nunca llega a la nube: mostrarlo sería mostrar los agentes de una sola máquina
como si fueran la cuadrilla entera. Quién trabaja sale de las ramas empujadas.

**Dónde escribe, que es el único lugar:**

```
$TMPDIR/capataz-espejos/<owner>__<repo>.git    espejos de sólo lectura
```

Son clones `--mirror` descartables. `nube._git()` rechaza cualquier comando de
git cuyo destino esté **fuera** de esa carpeta —o sea que capataz no corre git
sobre el repositorio de nadie, ni para leer—, y `pruebas/verificar-nube.py` § 5
borra un espejo entero, vuelve a leer y compara: si algo viviera sólo ahí, se
pone rojo. `CAPATAZ_ESPEJOS` mueve la carpeta; `CAPATAZ_REFRESCO` (60 s por
defecto) dice cada cuánto se le vuelve a preguntar a GitHub.

## Los runbooks

| Archivo | Qué |
|---|---|
| `ops/00-mapa.md` | Este |
| `ops/70-credenciales.md` | El token de GitHub: cómo se crea, dónde vive, cómo se revoca |
| `ops/90-volver-atras.md` | La marcha atrás. Escrita **antes** que cualquier despliegue |
| `10-crear-qas.md`, `30-desplegar.md`, `40-promover.md` | **No existen**, y no se escriben hasta que X2 se decida |

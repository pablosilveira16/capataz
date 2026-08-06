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
  medido en ERP 360— y `gh` no está instalado, así que **el estado del CI no se
  puede leer desde acá**. El puerto 22 está cerrado: SSH y las deploy keys no
  son una opción, y por eso el push es HTTPS con token.
- **Pablo, en la Mac**: todo lo anterior más el navegador, que es lo único que
  puede *mirar* la pantalla angosta (punto D1) y abrir una corrida del CI.
- **Nadie llega a un servidor**, porque no hay ninguno todavía.

## Qué mira capataz, y qué no toca

Capataz **sólo lee**. De cada proyecto vigilado toca, en modo lectura:

```
<proyecto>/<su archivo de seguimiento>      los puntos y sus estados
<proyecto>/ops/60-roles.md                  qué tipos de agente existen ahí
<proyecto>/panel/agentes.jsonl              quién trabaja ahora
<proyecto>/.git                             ramas, fechas y totales medidos
<proyecto>/pruebas/total-aserciones.txt     el total, leído por `git show`
```

Y **no escribe ni uno solo**. `lector.py` no abre nada en modo escritura y sus
comandos de git pasan por una lista blanca de subcomandos de lectura;
`pruebas/verificar-lector.py` § 1 saca una foto de un proyecto de prueba, corre
`mirar()` entero y compara byte a byte.

## Los runbooks

| Archivo | Qué |
|---|---|
| `ops/00-mapa.md` | Este |
| `ops/70-credenciales.md` | El token de GitHub: cómo se crea, dónde vive, cómo se revoca |
| `ops/90-volver-atras.md` | La marcha atrás. Escrita **antes** que cualquier despliegue |
| `10-crear-qas.md`, `30-desplegar.md`, `40-promover.md` | **No existen**, y no se escriben hasta que X2 se decida |

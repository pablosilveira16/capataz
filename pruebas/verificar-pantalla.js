#!/usr/bin/env node
/* La pantalla, ejecutándola — y sobre todo: que «no sé» NUNCA se pinte verde.
 *
 * **Por qué existe, y por qué en node.** `pruebas/verificar-angosto.py` mira la
 * hoja de estilo y el HTML que produce `render_estatico()`, pero la tarjeta de
 * cada proyecto la dibuja el JavaScript de `capataz.html` en el navegador: el
 * archivo estático trae los datos y un `<div id="cuerpo">` vacío. O sea que la
 * regla 3 de `CLAUDE.md` —«lo que no se sabe se muestra no sé, nunca verde»—
 * estaría verificada en el lector y **no en la pantalla**, que es donde alguien
 * la lee. Entre las dos cosas hay una función y una línea que decide la clase
 * CSS. Un tablero que miente justo cuando no sabe es peor que no tenerlo, así
 * que esa línea merece que alguien la ejecute.
 *
 * Cómo: se saca el `<script>` de `capataz.html`, se lo corre en un `vm` con un
 * DOM mínimo, y se le pasan **los datos de verdad** —los que produce
 * `capataz.estado()` leyendo GitHub— capturando el HTML que escribe. No se lee
 * ni una cadena del archivo: se mira lo que dibujó.
 *
 * Las secciones que sostienen a las demás:
 *
 *   § 2  con los datos reales, el CI de cada proyecto dice «no sé» y su chip
 *        NO lleva la clase verde;
 *   § 3  **y con un CI verde de verdad, sí la lleva** — sin esto, § 2 pasaría
 *        igual con una pantalla que no pinta verde nunca, que es la definición
 *        de aserción vacua;
 *   § 4  un total de aserciones que no se sabe se dibuja «no sé» y no «0»: un
 *        cero se lee como «no hay» y esto es «no sé», que es otra cosa;
 *   § 6  prendido o caído: los tres colores de un agente, y que «dudoso» no
 *        sea ninguno de los dos.
 *
 *     node pruebas/verificar-pantalla.js
 */
"use strict";

const fs = require("fs");
const path = require("path");
const vm = require("vm");
const { execFileSync } = require("child_process");

const RAIZ = path.dirname(__dirname);
let ASER = 0;
let ROJAS = 0;

function af(descripcion, condicion, detalle) {
  if (condicion) {
    ASER += 1;
  } else {
    ROJAS += 1;
    console.log("ROJA  " + descripcion + (detalle ? "  →  " + detalle : ""));
  }
}

/* Comparar dos listas y decir **cuál salió**, no sólo que no coincidieron: la
 * § 13 compara órdenes de agentes, y «no dio» sin el orden obtenido obliga a
 * reproducirlo a mano para entender qué pasó. */
function igual(descripcion, obtenido, esperado) {
  af(descripcion, JSON.stringify(obtenido) === JSON.stringify(esperado),
     "obtuve " + JSON.stringify(obtenido) + ", esperaba " + JSON.stringify(esperado));
}

// --- los datos de verdad, producidos por el mismo código que sirve la API ----
//
// No es un JSON escrito a mano: es `capataz.estado()`, leyendo los repositorios
// vigilados de GitHub. Si mañana el lector devuelve otra forma, esto se entera.
const datos = JSON.parse(execFileSync(
  "python3",
  ["-c", "import json,capataz; print(json.dumps(capataz.estado(), default=str))"],
  { cwd: RAIZ, encoding: "utf-8", maxBuffer: 64 * 1024 * 1024 }
));

// --- el DOM más chico que hace falta ---------------------------------------
// Los atributos son de verdad —`hidden` y `aria-current` son TODO el mecanismo
// de las pestañas—, así que el nodo de mentira los guarda. Con un `setAttribute`
// que no hace nada, `irA()` corre entero, no rompe, y no cambia nada: la § 10
// pasaría en verde sin que la navegación funcionara.
/* **Y desde el 2026-08-17 el nodo tiene hijos de verdad.** La zona de los
 * agentes que trabajan ahora ya no se dibuja con un `innerHTML` sobre el
 * contenedor: cada agente tiene su caja, creada una sola vez, y lo que cambia
 * es el contenido de adentro. Con el nodo de antes —un objeto con una cadena—
 * eso no se podía verificar: `appendChild` no existía y la § 13 no tendría cómo
 * comprobar que la caja **es el mismo objeto** entre dos pintadas, que es
 * exactamente lo que Pablo pidió.
 *
 * `innerHTML` es un accesor: leerlo devuelve lo que se escribió **más lo que
 * dibujan los hijos**, así que las aserciones de las otras secciones —que leen
 * `.innerHTML` de un contenedor— ven todo lo que hay abajo, igual que en un
 * navegador. Escribirlo tira los hijos, también igual que en un navegador. */
function nodo(attrs) {
  const a = Object.assign({}, attrs || {});
  const n = {
    textContent: "", className: "", hijos: [], parentNode: null,
    classList: { add() {}, remove() {} },
    getAttribute: (k) => (k in a ? a[k] : null),
    setAttribute: (k, v) => { a[k] = v; },
    removeAttribute: (k) => { delete a[k]; },
    hasAttribute: (k) => k in a,
    atributos: a,
    appendChild(h) { h.parentNode = n; n.hijos.push(h); return h; },
    removeChild(h) {
      const i = n.hijos.indexOf(h);
      if (i >= 0) n.hijos.splice(i, 1);
      h.parentNode = null;
      return h;
    },
    querySelector: () => null, querySelectorAll: () => []
  };
  let propio = "";
  Object.defineProperty(n, "innerHTML", {
    get() {
      return propio + n.hijos.map((h) => h.dibujo()).join("");
    },
    set(v) {
      propio = String(v);
      n.hijos.forEach((h) => { h.parentNode = null; });
      n.hijos = [];
    }
  });
  n.dibujo = () => '<div class="' + n.className + '">' +
    n.textContent + n.innerHTML + '</div>';
  return n;
}

function armarPantalla() {
  const nodos = {
    cabecera: nodo(), cuerpo: nodo(),
    // Los tres de la vista primaria. Sin ellos `pintarAgentes()` escribiría
    // sobre `undefined` y este arnés se caería antes de afirmar nada.
    agentes: nodo(), frescura: nodo(), pulso: nodo(),
    // Y los dos del taller, por lo mismo.
    taller: nodo(), alcance: nodo(),
    // Las tres zonas nuevas: lo que pide una persona, los que trabajan ahora
    // —que se dibuja con nodos y no con una cadena— y sus dos rótulos.
    pide: nodo(), vivos: nodo(), "vivos-nota": nodo(),
    "titulo-vivos": nodo(), "resto-nota": nodo(),
    // El shell: los dos lugares donde se dibuja el menú.
    "nav-principal": nodo(), tabbar: nodo(),
    // Y el de apariencia. El menú arranca cerrado, como en el marcado.
    "btn-apariencia": nodo(), "menu-apariencia": nodo({ hidden: "" })
  };
  // Las cuatro vistas, con el `hidden` inicial que tiene el marcado: la primera
  // abierta y las otras tres cerradas. Si acá arrancaran todas visibles, la
  // aserción de «sólo una a la vez» no verificaría el estado inicial.
  const vistas = ["taller", "agentes", "proyectos"].map((v, i) =>
    nodo(i === 0 ? { "data-vista": v } : { "data-vista": v, hidden: "" }));
  const relojes = [];
  // `documentElement` es donde vive `data-tema`, y el almacenamiento es de
  // mentira pero **guarda de verdad**: con uno que no guarda nada, la aserción
  // de que la preferencia persiste pasaría sin que persistiera.
  const raiz = nodo();
  const guardado = {};
  const contexto = {
    window: {
      localStorage: {
        getItem: (k) => (k in guardado ? guardado[k] : null),
        setItem: (k, v) => { guardado[k] = String(v); }
      },
      // Por defecto el sistema pide oscuro; las pruebas lo cambian.
      matchMedia: (q) => ({ matches: false, media: q })
    },
    document: {
      getElementById: (id) => nodos[id],
      querySelectorAll: (sel) => (sel === ".vista" ? vistas : []),
      // La zona de los vivos crea sus cajas con esto. Sin `createElement` la
      // pantalla se cae al primer agente que trabaja, que es la mitad de lo que
      // este arnés mira.
      createElement: () => nodo(),
      documentElement: raiz,
      body: nodo()
    },
    console: console,
    // Si el script intentara pedir datos por la red, esto lo delata: acá los
    // datos vienen incrustados y `traer()` no se tiene que llamar nunca.
    fetch: () => { throw new Error("la pantalla estática no debe hacer fetch"); },
    // **Un `setInterval` local ya no es un pecado, y un `fetch` sí.** La
    // pantalla estática late para que los contadores sigan siendo ciertos
    // mientras alguien la mira —el tiempo pasa igual—, pero no tiene a quién
    // preguntarle. Lo que se afirma abajo es que late y que NO pollea.
    setInterval: (fn, ms) => { relojes.push(ms); return relojes.length; }
  };
  contexto.window.CAPATAZ_DATOS = null;
  return { nodos, contexto, relojes, vistas, raiz, guardado };
}

const HTML = fs.readFileSync(path.join(RAIZ, "capataz.html"), "utf-8");
const guiones = HTML.match(/<script>([\s\S]*?)<\/script>/g) || [];
af("capataz.html trae exactamente un <script> con la pantalla",
   guiones.length === 1, String(guiones.length));
const CODIGO = guiones.join("\n").replace(/<\/?script>/g, "");
af("y el guión no está vacío", CODIGO.length > 2000, String(CODIGO.length));

function pintarCon(d) {
  const { nodos, contexto, relojes, vistas, raiz, guardado } = armarPantalla();
  contexto.window.CAPATAZ_DATOS = d;
  vm.createContext(contexto);
  vm.runInContext(CODIGO, contexto, { filename: "capataz.html" });
  nodos.relojes = relojes;
  nodos.contexto = contexto;
  nodos.vistas = vistas;
  nodos.raiz = raiz;
  nodos.guardado = guardado;
  return nodos;
}

function copia(x) { return JSON.parse(JSON.stringify(x)); }

/* Todo lo que la vista de agentes dibujó, sin importar en qué zona cayó cada
 * uno. Desde el 2026-08-17 son tres —lo que pide una persona, los que trabajan
 * ahora y el resto— y hay aserciones de dos clases: las que preguntan **qué**
 * se dibujó usan esto, y las que preguntan **dónde** miran la zona a mano,
 * porque en esas la zona es justamente lo que se afirma. */
function htmlAgentes(p) {
  return p.pide.innerHTML + p.vivos.innerHTML + p.taller.innerHTML +
    p.agentes.innerHTML;
}

console.log("\n§ 1 · La pantalla dibuja algo con los datos de verdad");
const pintado = pintarCon(datos);
af("hay al menos un proyecto vigilado que mirar",
   datos.proyectos.length >= 1, String(datos.proyectos.length));
af("el cuerpo no quedó vacío — «sin errores» no es lo mismo que «dibujó algo»",
   pintado.cuerpo.innerHTML.length > 500, String(pintado.cuerpo.innerHTML.length));
af("la cabecera dice cuántos proyectos y cuándo",
   /\d{4}-\d{2}-\d{2}/.test(pintado.cabecera.textContent) &&
   pintado.cabecera.textContent.indexOf("proyecto") >= 0,
   pintado.cabecera.textContent);
/* **Una aserción por comprobación, no una por proyecto.** El total de
 * aserciones es parte del resultado, y con un `forEach` que suma una por
 * proyecto el total dependería de cuántos repositorios haya configurados — se
 * midió: 274 en la carpeta de trabajo y 260 en un clon sin vecinos, como el del
 * CI, sin que nada hubiera cambiado. Un número que se mueve solo deja de servir
 * para comparar una rama con main. Agrupado da el mismo número de los dos
 * lados, y **el detalle dice cuáles fallaron**. */
function todos(descripcion, lista, prueba) {
  const malos = lista.filter(function (p) { return !prueba(p); })
                     .map(function (p) { return p.nombre; });
  af(descripcion + " (" + lista.length + " proyectos)", malos.length === 0,
     malos.join(", "));
}

todos("cada proyecto vigilado tiene su tarjeta dibujada", datos.proyectos,
      function (p) { return pintado.cuerpo.innerHTML.indexOf(">" + p.nombre + "<") >= 0; });

/* Los proyectos cuyo seguimiento SÍ se pudo leer. En el runner del CI no hay
 * credencial para los repositorios privados y Finca 360 no está publicado, así
 * que la lista de acá cambia según dónde se corra — y por eso todo lo de abajo
 * va agrupado. Sin este corte, este arnés se pondría rojo en el CI por algo que
 * no es un bug; con él, sigue habiendo una aserción de que quedó al menos uno
 * que mirar. */
const legibles = datos.proyectos.filter(function (p) { return p.seguimiento.existe; });
af("hay al menos un proyecto con el seguimiento legible (si no, § 2 no mira nada)",
   legibles.length >= 1, String(legibles.length));

/* Y el caso contrario, armado a mano para que se ejercite siempre: un
 * repositorio que capataz no pudo leer tiene que DECIRLO, no dibujar una
 * tarjeta vacía que se lee como «no hay nada pendiente». */
const perdido = copia(datos);
perdido.proyectos = [copia(datos.proyectos[0])];
perdido.proyectos[0].nombre = "No llegué";
perdido.proyectos[0].nube = { ok: false, error: "x", rancio: false, sin_repo: false };
perdido.proyectos[0].seguimiento.existe = false;
perdido.proyectos[0].seguimiento.error =
  "no existe github.com/pablosilveira16/fantasma, o el token no lo alcanza";
const htmlPerdido = pintarCon(perdido).cuerpo.innerHTML;
af("un repositorio que no se pudo leer lo dice, en rojo",
   /class="chip rojo"/.test(htmlPerdido) &&
   htmlPerdido.indexOf("no pude leer el repositorio") >= 0, htmlPerdido.slice(0, 300));
af("y muestra lo que buscó, que es lo único accionable",
   htmlPerdido.indexOf("github.com/pablosilveira16/fantasma") >= 0);
af("y NO dibuja chips de estados, que se leerían como «no falta nada»",
   htmlPerdido.indexOf("Puntos abiertos") < 0);

/* Un proyecto declarado SIN repositorio —Finca 360, que todavía no está
 * publicado— no es lo mismo que uno que falló. No se pinta rojo: pintar de rojo
 * algo que está así a propósito es el aviso que sale siempre, y el corolario de
 * la regla 3 dice que eso enseña a ignorar los avisos. */
const sinRepo = copia(datos);
sinRepo.proyectos = [copia(datos.proyectos[0])];
sinRepo.proyectos[0].nombre = "Sin publicar";
sinRepo.proyectos[0].repo = "";
sinRepo.proyectos[0].nube = { ok: false, error: "todavía no está en GitHub",
                              rancio: false, sin_repo: true };
const htmlSinRepo = pintarCon(sinRepo).cuerpo.innerHTML;
af("un proyecto sin repositorio dice «no sé», no un error",
   htmlSinRepo.indexOf("sin publicar") >= 0 &&
   htmlSinRepo.indexOf("no sé") >= 0, htmlSinRepo.slice(0, 300));
af("y NO se pinta rojo: está así a propósito",
   !/class="chip rojo"/.test(htmlSinRepo));
af("ni verde, que sería decir que está todo bien",
   !/class="chip[^"]*\bverde\b/.test(htmlSinRepo));
af("con el motivo declarado en proyectos.json a la vista",
   htmlSinRepo.indexOf("todavía no está en GitHub") >= 0);

/* El bloque de CI de un proyecto, tal como quedó dibujado. Se corta desde el
 * <h3>CI</h3> hasta el final de sus chips: mirar el HTML entero mezclaría el
 * verde de un chip de aserciones con el del CI, que es justo lo que hay que
 * distinguir. */
function bloqueCiDe(html, nombre) {
  const i = html.indexOf(">" + nombre + "<");
  const desde = html.indexOf("<h3>CI</h3>", i);
  if (desde < 0) return "";
  const hasta = html.indexOf("</details>", desde);
  return html.slice(desde, hasta > 0 ? hasta : desde + 400);
}

console.log("§ 2 · El CI que no se pudo leer no se pinta verde");
const ci = function (p) { return bloqueCiDe(pintado.cuerpo.innerHTML, p.nombre); };
todos("cada proyecto legible dibuja su bloque de CI", legibles,
      function (p) { return ci(p).length > 0; });
todos("el lector dice «no sé» para todos —la lectura del CI está apagada—", legibles,
      function (p) { return p.ci.estado === "no sé"; });
todos("y la pantalla lo muestra como «no sé»", legibles,
      function (p) { return ci(p).indexOf("no sé") >= 0; });
todos("y NINGÚN chip de CI lleva la clase verde", legibles,
      function (p) { return !/class="chip[^"]*\bverde\b/.test(ci(p)); });
todos("ni la clase roja: no saber no es haber fallado", legibles,
      function (p) { return !/class="chip[^"]*\brojo\b/.test(ci(p)); });
todos("lleva la clase «nose», que es la de borde punteado", legibles,
      function (p) { return /class="chip[^"]*\bnose\b/.test(ci(p)); });
todos("y trae el porqué a mano, plegado", legibles,
      function (p) { return ci(p).indexOf("por qué no se sabe") >= 0; });

console.log("§ 3 · …y con un CI verde de verdad, sí se pinta verde");
/* Sin esta sección, la § 2 pasaría igual con una pantalla que no pinta verde
 * nunca —o que no dibuja el CI—, y sería la aserción vacua de la regla 2. */
const conCi = copia(datos);
conCi.proyectos = [copia(legibles[0])];
const nombre0 = conCi.proyectos[0].nombre;

conCi.proyectos[0].ci = { estado: "verde", motivo: "", detalle: "success" };
let b = bloqueCiDe(pintarCon(conCi).cuerpo.innerHTML, nombre0);
af("un CI verde se dibuja verde", /class="chip[^"]*\bverde\b/.test(b), b);
af("y sin el «por qué no se sabe», que ahí sería el aviso que sale siempre",
   b.indexOf("por qué no se sabe") < 0, b);

conCi.proyectos[0].ci = { estado: "rojo", motivo: "", detalle: "failure" };
b = bloqueCiDe(pintarCon(conCi).cuerpo.innerHTML, nombre0);
af("un CI rojo se dibuja rojo", /class="chip[^"]*\brojo\b/.test(b), b);

/* «corriendo» no es ninguna de las dos. Es el caso que se cuela si alguien
 * escribe `clase = e === "rojo" ? "rojo" : "verde"`. */
conCi.proyectos[0].ci = { estado: "corriendo", motivo: "", detalle: "in_progress" };
b = bloqueCiDe(pintarCon(conCi).cuerpo.innerHTML, nombre0);
af("«corriendo» no se pinta verde", !/class="chip[^"]*\bverde\b/.test(b), b);
af("ni rojo", !/class="chip[^"]*\brojo\b/.test(b), b);

console.log("§ 4 · Un total que no se sabe se dibuja «no sé», no «0»");
function ramaFalsa(extra) {
  return Object.assign({
    nombre: "x", es_principal: false, punto: "", sha: "abc1234",
    ts: 1785989327, hace_seg: 600, autor: "coder-1", asunto: "algo",
    commits_adelante: 1, commits_atras: 0, total: 100, total_main: 100,
    delta: 0, motivo_sin_total: "", estado: "trabajando"
  }, extra);
}
const conRamas = copia(datos);
conRamas.proyectos = [copia(legibles[0])];
conRamas.proyectos[0].ramas = [
  ramaFalsa({ nombre: "main", es_principal: true, estado: "principal",
              commits_adelante: 0 }),
  ramaFalsa({ nombre: "t9-baja", punto: "T9", total: 97, delta: -3 }),
  ramaFalsa({ nombre: "t8-sin-total", punto: "T8", total: null, delta: null,
              motivo_sin_total: "no dejó el total medido" })
];
const htmlRamas = pintarCon(conRamas).cuerpo.innerHTML;
const iSin = htmlRamas.indexOf("t8-sin-total");
const filaSin = htmlRamas.slice(iSin, iSin + 400);
af("la rama sin total medido dice «no sé»", filaSin.indexOf("no sé") >= 0, filaSin);
af("y no dibuja un 0, que se leería como «no hay aserciones»",
   !/<b>0<\/b>\s*aserciones/.test(filaSin), filaSin);
const iBaja = htmlRamas.indexOf("t9-baja");
const filaBaja = htmlRamas.slice(iBaja, iBaja + 500);
af("una rama que BAJA el total se marca en rojo aunque esté verde",
   /class="chip[^"]*\brojo\b/.test(filaBaja), filaBaja);
af("y dice cuánto bajó contra main", filaBaja.indexOf("-3 vs main") >= 0, filaBaja);

/* Un repositorio que no se pudo leer: «no sé», no «ninguna rama». */
conRamas.proyectos[0].ramas = null;
const sinRamas = pintarCon(conRamas).cuerpo.innerHTML;
af("un repositorio que no se leyó dice «no sé» en ramas",
   /ramas · no sé/.test(sinRamas));
af("y no dice «ninguna», que sería afirmar que no tiene",
   sinRamas.indexOf(">ninguna<") < 0);
/* Y lo mismo con la cuadrilla, que es el dato nuevo de esta tanda: sin poder
 * leer el repositorio, «nadie trabajando» se lee igual que «todo tranquilo» y
 * es exactamente lo contrario de lo que puede estar pasando. */
af("y en la cuadrilla dice «quién trabaja · no sé», no «nadie trabajando»",
   sinRamas.indexOf("quién trabaja · no sé") >= 0 &&
   sinRamas.indexOf("nadie trabajando") < 0, sinRamas.slice(0, 200));

console.log("§ 5 · Los ceros se dibujan, y el texto ajeno se escapa");
const primero = legibles[0];
const trozo = pintado.cuerpo.innerHTML;
["pendiente", "en curso", "hecho", "diferido", "descartado"].forEach(function (e) {
  af("el chip de «" + e + "» está dibujado aunque valga " +
     primero.cuenta_abiertos[e], trozo.indexOf(">" + e + "</span>") >= 0);
});
af("y los ceros se marcan con la clase «cero» en vez de esconderse",
   trozo.indexOf("chip e-") >= 0 && /class="chip [^"]*cero"/.test(trozo));

/* El seguimiento de otro proyecto es texto que capataz no controla. Si alguien
 * escribe `<img onerror=…>` en una celda, tiene que salir escapado. */
const conHtml = copia(datos);
conHtml.proyectos = [copia(legibles[0])];
// Va en `falta`, que es donde los títulos ajenos se dibujan desde el
// 2026-08-17: es la lista de lo que hay que hacer, y la que trae el texto que
// escribió otro proyecto.
conHtml.proyectos[0].falta = [{
  id: "Z1", titulo: '<img src=x onerror="alert(1)">& "comillas"',
  dias: 3, quien: "", estado: "pendiente", grupo: 2, rotulo_grupo: "pendiente",
  porque: "como está escrito en el seguimiento"
}];
const escapado = pintarCon(conHtml).cuerpo.innerHTML;
af("un título con marcado ajeno sale escapado",
   escapado.indexOf("<img src=x") < 0 && escapado.indexOf("&lt;img src=x") >= 0);
af("y los & y las comillas también",
   escapado.indexOf("&amp;") >= 0 && escapado.indexOf("&quot;") >= 0);

console.log("§ 6 · Prendido o caído — los tres colores de un agente");
/* Es el punto entero de la tanda: «al observar variaciones en vivo va a poder
 * ver los agentes que se prenden y apagan». Los tres estados tienen que
 * distinguirse **en la pantalla** y no sólo en el JSON, y el del medio —el que
 * capataz no sabe— no puede caer en ninguno de los otros dos. */
const conAgentes = copia(datos);
conAgentes.proyectos = [copia(legibles[0])];
conAgentes.proyectos[0].ramas = [
  ramaFalsa({ nombre: "main", es_principal: true, estado: "principal",
              commits_adelante: 0 }),
  ramaFalsa({ nombre: "t1-viva", estado: "trabajando", hace_seg: 600,
              autor: "coder-1" }),
  ramaFalsa({ nombre: "t2-dudosa", estado: "dudoso", hace_seg: 7200,
              autor: "coder-2" }),
  ramaFalsa({ nombre: "t3-caida", estado: "caído", hace_seg: 108000,
              autor: "coder-3" }),
  ramaFalsa({ nombre: "t4-lista", estado: "integrada", commits_adelante: 0,
              autor: "escriba-1" })
];
conAgentes.proyectos[0].cuadrilla = [
  { quien: "coder-3", rol: "coder", que: "t3-caida", punto: "T3",
    asunto: "algo", estado: "caído", desde: 1, hace_seg: 108000 },
  { quien: "coder-2", rol: "coder", que: "t2-dudosa", punto: "T2",
    asunto: "algo", estado: "dudoso", desde: 1, hace_seg: 7200 },
  { quien: "coder-1", rol: "coder", que: "t1-viva", punto: "T1",
    asunto: "algo", estado: "trabajando", desde: 1, hace_seg: 600 },
  { quien: "reviewer-1", rol: "reviewer", que: "T7", punto: "T7",
    asunto: "un punto tomado", estado: "sin rama", desde: null, hace_seg: null }
];
const htmlAg = pintarCon(conAgentes).cuerpo.innerHTML;
/* La fila de esa clave, **cortada en su propio `</li>`**. Con una ventana de
 * N caracteres se colaba el chip del agente siguiente: la aserción de que
 * «dudoso» no lleva la clase de «trabajando» se ponía roja porque la clase
 * estaba en la fila de al lado. Primera hipótesis, el arnés — y era. */
function filaDe(html, clave) {
  const i = html.indexOf(clave);
  if (i < 0) return "";
  const fin = html.indexOf("</li>", i);
  return html.slice(i, fin < 0 ? i + 420 : fin);
}
af("un agente que se movió recién se dibuja como «trabajando», en verde",
   /class="chip r-trabajando"/.test(filaDe(htmlAg, "t1-viva")) &&
   filaDe(htmlAg, "t1-viva").indexOf("trabajando") >= 0,
   filaDe(htmlAg, "t1-viva"));
af("uno que no se mueve hace 30 horas se dibuja «caído», en rojo",
   /class="chip r-caido"/.test(filaDe(htmlAg, "t3-caida")),
   filaDe(htmlAg, "t3-caida"));
af("y el del medio se dibuja «dudoso», que NO es ni el verde ni el rojo",
   /class="chip r-dudoso"/.test(filaDe(htmlAg, "t2-dudosa")) &&
   !/class="chip r-trabajando"/.test(filaDe(htmlAg, "t2-dudosa")) &&
   !/class="chip r-caido"/.test(filaDe(htmlAg, "t2-dudosa")),
   filaDe(htmlAg, "t2-dudosa"));
af("una rama integrada no se dibuja como un agente caído",
   /class="chip r-integrada"/.test(filaDe(htmlAg, "t4-lista")),
   filaDe(htmlAg, "t4-lista"));
af("un punto en curso sin rama se ve como «sin rama», no como caído",
   htmlAg.indexOf("sin rama") >= 0 &&
   /class="chip r-sinrama"/.test(filaDe(htmlAg, "reviewer-1")),
   filaDe(htmlAg, "reviewer-1"));
af("la cuadrilla dice hace cuánto se movió cada uno, en la unidad que se lee",
   htmlAg.indexOf("hace 10 min") >= 0 && htmlAg.indexOf("hace 30 h") >= 0,
   htmlAg.slice(htmlAg.indexOf("La cuadrilla"), htmlAg.indexOf("La cuadrilla") + 600));
af("y el reparto por rol sigue con los ceros",
   /class="chip [^"]*cero"/.test(htmlAg));

/* Sin ninguna rama viva, se dice que no hay nadie **y sobre qué se miró**: no
 * es lo mismo que no haber podido mirar, y las dos frases tienen que ser
 * distintas. */
conAgentes.proyectos[0].cuadrilla = [];
conAgentes.proyectos[0].ramas = [
  ramaFalsa({ nombre: "main", es_principal: true, estado: "principal",
              commits_adelante: 0 })
];
const htmlVacio = pintarCon(conAgentes).cuerpo.innerHTML;
af("sin nadie trabajando se dice, y se dice sobre qué se miró",
   htmlVacio.indexOf("nadie trabajando") >= 0 &&
   htmlVacio.indexOf("sin integrar") >= 0, htmlVacio.slice(0, 200));
af("y eso NO es «no sé»", htmlVacio.indexOf("quién trabaja · no sé") < 0);


/* Lo que el servidor arma con `lector.asociar()`: una sola lista donde cada
   agente es un renglón. Los ayudantes de abajo la producen igual que él, porque
   es lo que la pantalla dibuja — sin esto, las secciones probarían una forma de
   datos que ya no existe. */
function soloGitHub(agentes) {
  return (agentes || []).map((g) => ({
    sesion: "", nombre: g.quien, cwd: "", proyecto: g.proyecto, rama: g.que,
    viva: null, quieto_hace: null, que: "", sobre: "", motivo_que: "",
    agentes: [], motivo_sin_agentes: "sólo publicado", id: "",
    estado_consola: "", motivo_consola: "", github: g, fuente: "github"
  }));
}
function soloMaquina(sesiones) {
  return (sesiones || []).map((s) => Object.assign({}, s,
    { fuente: s.fuente || "archivo", github: s.github || null }));
}

console.log("§ 7 · El visor por agente, y el demonio de un segundo");
/* La vista primaria: quién trabaja ahora, de todos los proyectos juntos. Y el
 * demonio que la mantiene viva sin mentir sobre la frescura de lo que muestra. */
const conAg = copia(datos);
conAg.taller = Object.assign({}, conAg.taller, { ok: true, error: "",
  sesiones: [], agentes_maquina: [] });
conAg.agentes = [
  { quien: "coder-1", rol: "coder", proyecto: "Uno", que: "t1-una",
    punto: "T1", asunto: "empujó algo", estado: "trabajando", desde: 1,
    hace_seg: 60, sha: "aaa1111" },
  { quien: "coder-2", rol: "coder", proyecto: "Dos", que: "t2-otra",
    punto: "T2", asunto: "hace rato", estado: "caído", desde: 1,
    hace_seg: 90000, sha: "bbb2222" }
];
conAg.agentes_todos = soloGitHub(conAg.agentes);
const p7 = pintarCon(conAg);
const hAg = p7.agentes.innerHTML;
const hTodo7 = htmlAgentes(p7);
af("la vista primaria dibuja a cada agente con su nombre",
   hTodo7.indexOf("coder-1") >= 0 && hTodo7.indexOf("coder-2") >= 0,
   hTodo7.slice(0, 200));
af("y de qué proyecto es cada uno: sin eso no se sabe a quién ir a buscar",
   hTodo7.indexOf("Uno") >= 0 && hTodo7.indexOf("Dos") >= 0);
af("junta agentes de proyectos distintos, que es lo que la hace primaria",
   hTodo7.indexOf("t1-una") >= 0 && hTodo7.indexOf("t2-otra") >= 0);
af("el que se cayó se pinta con su color y NO de verde",
   /a-caido/.test(hAg) && !/chip-estado verde/.test(hAg), hAg.slice(0, 300));
/* Y desde el 2026-08-17, **el que trabaja no está ahí abajo**: está arriba, en
 * la zona de los que se mueven ahora. Las dos aserciones van juntas a
 * propósito: la segunda es la que verifica que la zona no sea una copia, que es
 * el bug que T41 encontró dibujando al mismo agente en dos secciones. */
af("y el que trabaja va arriba, en la zona de los que se mueven ahora",
   p7.vivos.innerHTML.indexOf("coder-1") >= 0 &&
   /v-trabajando|v-late/.test(p7.vivos.innerHTML),
   p7.vivos.innerHTML.slice(0, 240));
af("y NO se lo dibuja además abajo: un agente, un lugar",
   hAg.indexOf("coder-1") < 0, hAg.slice(0, 200));

/* El demonio. Lo que se afirma no es que exista un `setInterval` —eso es una
 * cadena— sino con qué ritmos quedó armado y que la instantánea no pollee. */
af("la pantalla late una vez por segundo: los contadores siguen siendo ciertos " +
   "mientras alguien la mira", p7.relojes.indexOf(1000) >= 0,
   JSON.stringify(p7.relojes));
af("y la instantánea NO pollea: no hay a quién preguntarle",
   p7.relojes.filter(function (m) { return m !== 1000; }).length === 0,
   JSON.stringify(p7.relojes));

/* Los umbrales los manda el servidor y la pantalla los vuelve a aplicar a cada
 * segundo. Los dos lados de cada uno, que es donde se esconde un `<` de más. */
const ctx = p7.contexto;
af("un segundo antes de FRESCO la pantalla dice «trabajando»",
   ctx.estadoVivo(conAg.umbrales.fresco - 1, "caído") === "trabajando");
af("un segundo después, «dudoso» — sin esperar ninguna lectura nueva",
   ctx.estadoVivo(conAg.umbrales.fresco + 1, "trabajando") === "dudoso");
af("un segundo antes de TIBIO todavía es «dudoso»",
   ctx.estadoVivo(conAg.umbrales.tibio - 1, "trabajando") === "dudoso");
af("un segundo después ya es «caído»",
   ctx.estadoVivo(conAg.umbrales.tibio + 1, "trabajando") === "caído");
af("y el que no tiene rama sigue sin tenerla: el reloj no lo convierte en nada",
   ctx.estadoVivo(null, "sin rama") === "sin rama");
/* Una instantánea vieja no trae umbrales. No se inventan: queda lo que dijo el
 * servidor, que es la regla 3 aplicada a la pantalla misma. */
const sinUmbrales = copia(conAg);
delete sinUmbrales.umbrales;
af("sin umbrales en el JSON no se inventa ninguno",
   pintarCon(sinUmbrales).contexto.estadoVivo(10, "dudoso") === "dudoso");

/* «Se despertó» tiene que ser un empujón y no un reloj: si se marcara por
 * tiempo, avisaría solo y el aviso dejaría de querer decir nada. */
function relectura(ctxt, agentes) {
  const d = copia(conAg);
  d.agentes = agentes;
  d.agentes_todos = soloGitHub(agentes);
  ctxt.FIRMA = "";
  ctxt.pintar(d);
  // Las dos zonas: el que empuja un sha nuevo pasa a estar trabajando, así que
  // la marca de «se despertó» tiene que sobrevivir el cambio de zona. Mirar
  // sólo la de abajo haría que esta aserción se pusiera verde por mudanza.
  return ctxt.document.getElementById("agentes").innerHTML +
    ctxt.document.getElementById("vivos").innerHTML;
}
ctx.VISTOS = null;
ctx.DESPIERTOS = {};
af("la primera lectura no marca a nadie como recién despierto: si no, cada vez " +
   "que se abre la pantalla parecería que empujaron todos",
   !/desperto/.test(relectura(ctx, conAg.agentes)));
af("dos lecturas con el mismo sha tampoco: no pasó nada",
   !/desperto/.test(relectura(ctx, conAg.agentes)));
const movido = copia(conAg.agentes);
movido[0].sha = "ccc3333";
movido[0].hace_seg = 2;
af("y un sha nuevo sí: eso es un empujón",
   /desperto/.test(relectura(ctx, movido)));

/* La frescura. Es el dato que dice si creerle al resto de la pantalla. */
ctx.ESTATICA = false;
ctx.ULTIMO_OK = Date.now();
const sinMarca = copia(conAg);
sinMarca.proyectos.forEach(function (p) {
  if (p.nube) { p.nube.traido_en = null; p.nube.sin_repo = false; }
});
ctx.pintar(sinMarca);
ctx.pintarFrescura();
af("sin la marca de cuándo se trajo, la frescura dice «no sé» y no «hace 0 s»",
   p7.frescura.textContent.indexOf("no sé") >= 0, p7.frescura.textContent);
ctx.ULTIMO_OK = Date.now() - 30000;
ctx.pintarFrescura();
af("y si el servidor deja de contestar, la pantalla lo dice en vez de seguir " +
   "mostrando lo viejo como si fuera de ahora",
   p7.frescura.textContent.indexOf("sin contacto") >= 0, p7.frescura.textContent);
af("con hace cuánto que no sabe nada, que es lo accionable",
   /\d+ s/.test(p7.frescura.textContent), p7.frescura.textContent);

/* -------------------------------------------------------------------------
   § 8 · El taller — y que su alcance se vea

   La sección nueva muestra los agentes de ESTA máquina. Dos cosas tienen que
   ser ciertas en la pantalla y no sólo en el lector: que `sin señal` no se
   pinte como un desenlace —terminado y colgado no se distinguen— y que el
   alcance esté a la vista, porque tres agentes locales mostrados como si
   fueran la flota son el tablero que miente.
------------------------------------------------------------------------- */
console.log("\n§ 8 · El taller");

const p8 = pintarCon(datos);
af("el alcance está escrito, no es una nota al pie",
   p8.alcance.textContent.indexOf("esta máquina") >= 0, p8.alcance.textContent);
af("con los datos de verdad, el taller dibuja algo",
   p8.taller.innerHTML.length > 50, String(p8.taller.innerHTML.length));

/* Un taller a mano con los cinco desenlaces, para que ninguno quede sin pintar
   por lo que haya corriendo en la máquina en este momento. */
function conTaller(sesiones, ok, error) {
  const d = copia(datos);
  d.taller = { ok: ok === undefined ? true : ok, error: error || "",
               raiz: "/x/.claude", alcance: "esta máquina · ahora",
               leido_en: d.ahora, sesiones: sesiones,
               cuenta: { sesiones: sesiones.length, vivas: 1, agentes: 0,
                         trabajando: 0 }, sueltas: 0,
               // Lo que la pantalla dibuja de verdad: la lista **ya unida**,
               // que en el servidor arma `consola.unir()`.
               agentes_maquina: sesiones };
  d.agentes = [];
  d.agentes_todos = soloMaquina(sesiones);
  return d;
}

function agente(id, estado, quieto, hijos) {
  return { id: id, tipo: "general-purpose", descripcion: "el " + id,
           profundidad: hijos ? 1 : 2, padre: null, modelo: null,
           worktree: null, arrancado: 1, ultimo: 1, quieto_hace: quieto,
           estado: estado, motivo_estado: estado === "sin señal"
             ? "terminado y colgado no se distinguen desde acá" : "",
           hijos: hijos || [] };
}

const sesion = {
  pid: 1, viva: true, sesion: "s-1", nombre: "una-sesion", cwd: "/x/proy",
  arrancada: 1, version: "2.1.221", entrada: "claude-desktop", error: "",
  proyecto: "Capataz", motivo_sin_agentes: "",
  agentes: [agente("padre", "trabajando", 3, [agente("hijo", "dudoso", 600)]),
            agente("mudo", "sin señal", 9000),
            agente("ido", "cerrado", 50)]
};
const p8b = pintarCon(conTaller([sesion]));
const htmlT = p8b.taller.innerHTML;

af("«sin señal» se pinta con la pinta de «no sé» y NUNCA verde",
   /r-sinsenal/.test(htmlT) && !/r-sinsenal[^"]*verde/.test(htmlT), htmlT.slice(0, 120));
af("y dice por qué: que terminado y colgado no se distinguen",
   htmlT.indexOf("no se distinguen") >= 0);
af("«cerrado» tampoco es verde: el proceso no está, no es un logro",
   /r-cerrado/.test(htmlT));
/* La anti-vacua de las tres de arriba: sin esto pasarían igual con una
   pantalla que no pinta de color nunca. */
af("y un agente trabajando SÍ lleva la clase de trabajando",
   /r-trabajando/.test(htmlT));
af("el subagente anidado se dibuja adentro del padre",
   htmlT.indexOf("el hijo") > htmlT.indexOf("el padre"));
af("la sesión dice de qué proyecto es la carpeta", htmlT.indexOf("Capataz") >= 0);

/* Los umbrales llegan del servidor. Sin ellos no se inventa ninguno. */
const ctxT = p8b.contexto;
af("con los umbrales del servidor, el estado se recalcula con el reloj",
   ctxT.estadoTaller(1, "sin señal") === "trabajando" &&
   ctxT.estadoTaller(999999, "trabajando") === "sin señal");
af("pero «cerrado» no se recalcula: es un hecho medido, no un rato",
   ctxT.estadoTaller(1, "cerrado") === "cerrado");
af("ni «no sé»: es la ausencia de transcripción",
   ctxT.estadoTaller(1, "no sé") === "no sé");

/* No pude mirar ≠ no hay nadie. Es la distinción que un tablero suele borrar. */
const p8c = pintarCon(conTaller([], false, "no encontré /x/.claude · CAPATAZ_TALLER"));
af("si el taller no se pudo leer, se dice y se nombra lo que buscó",
   p8c.taller.innerHTML.indexOf("/x/.claude") >= 0, p8c.taller.innerHTML.slice(0, 120));
const p8d = pintarCon(conTaller([]));
af("y cero agentes es otra cosa: se dice que no hay ninguno",
   p8d.taller.innerHTML.indexOf("ningún agente de Claude Code") >= 0,
   p8d.taller.innerHTML.slice(0, 120));
af("y avisa que los de otra máquina no se ven acá",
   p8d.taller.innerHTML.indexOf("otra máquina") >= 0);

/* Qué está haciendo cada uno, dibujado. La sesión de arriba no trae `que`, así
   que sirve para el caso «no se sabe»: tiene que salir el motivo y NO un hueco
   ni un invento. */
const conQue = copia(sesion);
conQue.que = "Bash"; conQue.sobre = "Desplegar a QAS"; conQue.quieto_hace = 12;
conQue.agentes = [agente("padre", "trabajando", 3)];
conQue.agentes[0].que = "Edit"; conQue.agentes[0].sobre = "lector.py";
/* Escribió hace 12 segundos, así que **está trabajando**: desde el 2026-08-17
 * va a la zona de arriba y no a la lista de abajo. Lo que se afirma es lo
 * mismo de siempre —qué herramienta, sobre qué, hace cuánto, y qué hace su
 * subagente—, más la zona, que ahora es parte de la respuesta. */
const p8q = pintarCon(conTaller([conQue]));
const htmlQ = htmlAgentes(p8q);
af("la sesión dice qué herramienta está usando y sobre qué",
   htmlQ.indexOf("Bash") >= 0 && htmlQ.indexOf("Desplegar a QAS") >= 0);
af("una que escribió hace 12 s va a la zona de los que trabajan ahora",
   p8q.vivos.innerHTML.indexOf("Desplegar a QAS") >= 0 &&
   p8q.taller.innerHTML.indexOf("Desplegar a QAS") < 0,
   p8q.vivos.innerHTML.slice(0, 200));
af("y hace cuánto que no escribe", /hace \d+ s/.test(p8q.vivos.innerHTML),
   p8q.vivos.innerHTML.slice(0, 300));
af("el subagente también dice qué hace",
   htmlQ.indexOf("Edit") >= 0 && htmlQ.indexOf("lector.py") >= 0);
/* **Que un cambio de herramienta repinte.** Es la aserción que nació de un bug
   de verdad: la firma que decide si vale la pena redibujar miraba quién está y
   en qué estado, no qué hace — así que una sesión que pasaba de `Bash` a `Edit`
   se quedaba mostrando lo de antes para siempre. Se pinta dos veces sobre el
   MISMO contexto, que es lo que hace el navegador. */
const pDoble = pintarCon(conTaller([conQue]));
const segundo = copia(conQue);
segundo.que = "Edit"; segundo.sobre = "nube.py";
pDoble.contexto.pintar(conTaller([segundo]));
af("cambiar de herramienta repinta: no se queda con la de antes",
   htmlAgentes(pDoble).indexOf("nube.py") >= 0 &&
   htmlAgentes(pDoble).indexOf("Desplegar a QAS") < 0,
   pDoble.vivos.innerHTML.slice(0, 220));

const sinQue = copia(sesion);
sinQue.que = ""; sinQue.sobre = "";
sinQue.motivo_que = "escribió recién pero no hay ninguna herramienta en la cola";
const htmlSQ = pintarCon(conTaller([sinQue])).taller.innerHTML;
af("y si no se sabe qué hace, se dice el motivo y no se inventa nada",
   htmlSQ.indexOf("no hay ninguna herramienta") >= 0 &&
   htmlSQ.indexOf("sin escribir") < 0, htmlSQ.slice(0, 160));

/* -------------------------------------------------------------------------
   § 9 · La consola — los agentes background, dibujados

   Es la tercera fuente y la única que sale de correr un programa. Tres cosas
   tienen que ser ciertas **en la pantalla** y no sólo en el lector:

     · `esperando` salta —es lo único que pide que alguien haga algo— y `no sé`
       no se pinta de ningún color, que es la regla 3;
     · no haber podido preguntar no se dibuja como «ningún agente»;
     · **el desacuerdo entre las dos fuentes sólo aparece cuando lo hay.** Un
       aviso que sale siempre enseña a ignorarse (corolario de la regla 3), así
       que hay una aserción de cada lado: que sale, y que no sale.
------------------------------------------------------------------------- */
console.log("\n§ 9 · La consola");

function conConsola(background, extra) {
  const d = copia(datos);
  // Igual que el servidor: los background van a la lista unida del taller —que
  // es la que se dibuja— con el estado del CLI en `estado_consola`.
  d.taller = Object.assign({}, d.taller, { ok: true, error: "",
    alcance: "esta máquina · ahora", sesiones: [],
    // Backgrounds **cuyo archivo existe**: eso es lo que los distingue de un
    // fantasma, y por eso `fuente` dice que hablaron las dos fuentes y
    // `fantasma` es falso. Un cli-solo con `esperando` es, por definición, uno
    // que murió sin avisar (T37) y tiene su propio caso más abajo.
    agentes_maquina: background.map((b) => Object.assign({}, b, {
      estado_consola: b.estado, motivo_consola: b.motivo_estado,
      viva: null, agentes: [], fuente: "archivo+cli", fantasma: false,
      proyecto: "", motivo_sin_agentes: "" })) });
  d.agentes = [];
  d.agentes_todos = d.taller.agentes_maquina.slice();
  d.consola = Object.assign({
    ok: true, error: "", alcance: "esta máquina · ahora. Son los agentes background",
    comando: "claude agents --json --all", preguntado_en: d.ahora,
    background: background, interactivas: [], desacuerdos: [],
    cuenta: { background: background.length, trabajando: 0, esperando: 0,
              terminados: 0, interactivas: 0 }
  }, extra || {});
  return d;
}

function bg(id, estado, motivo) {
  return { id: id, sesion: "s-" + id, pid: 10, nombre: "el " + id,
           cwd: "/x/proy", clase: "background", state: "x", status: "y",
           arrancada: 1, hace: 120, estado: estado, motivo_estado: motivo || "" };
}

const p9 = pintarCon(conConsola([
  bg("b1", "esperando", "trabado: necesita a una persona"),
  bg("b2", "trabajando"), bg("b3", "falló"), bg("b4", "terminado"),
  bg("b5", "no sé", "el CLI dice `state: 'hibernating'`")]));
const htmlC = p9.taller.innerHTML;

af("el alcance de la consola está escrito y dice que es esta máquina",
   p9.alcance.textContent.indexOf("esta máquina") >= 0,
   p9.alcance.textContent);
/* El estado ya no es un chip de color: es **el borde izquierdo de la fila**,
   que es lo que separa un agente del de abajo de un vistazo. La regla no
   cambió —lo que pide una persona salta, lo sabido va apagado— y por eso las
   aserciones siguen siendo las mismas con otra clase. */
/* **El que está trabado ya no es un renglón un poco más arriba: tiene zona
   propia.** Fue el pedido de Pablo del 2026-08-17 —«cuando se traba con una
   pregunta, que la pantalla se vea bien rápido eso»— y por eso estas
   aserciones miran **la zona** y no sólo el color: para notar que algo subió un
   lugar en una lista hay que estar leyendo la lista, que es justo lo que no
   pasa cuando uno mira un tablero de reojo. */
const hTodo9 = htmlAgentes(p9);
af("«esperando» va a la zona de arriba, la que pide una persona",
   p9.pide.innerHTML.indexOf("el b1") >= 0 &&
   p9.pide.innerHTML.indexOf("Trabado") >= 0, p9.pide.innerHTML.slice(0, 200));
af("y no queda además abajo, mezclado con los demás",
   htmlC.indexOf("el b1") < 0, htmlC.slice(0, 200));
af("y dice cómo se destraba",
   p9.pide.innerHTML.indexOf("necesita a una persona") >= 0);
af("«no sé» no se pinta de ningún color, y lleva la palabra cruda del CLI",
   /nose/.test(htmlC) && htmlC.indexOf("hibernating") >= 0);
af("«falló» sí es rojo: eso sí es un incendio",
   /pide-rojo/.test(p9.pide.innerHTML), p9.pide.innerHTML.slice(0, 200));
af("«terminado» va apagado: es un hecho sabido, no un logro",
   /f-apagado/.test(htmlC));
af("y el estado se sigue diciendo con todas las letras, no sólo con un color",
   hTodo9.indexOf("terminado") >= 0 && hTodo9.indexOf("esperando") >= 0);
/* La anti-vacua de las cuatro de arriba: sin esto pasarían con una pantalla
   que no pinta de verde nunca. */
af("y el que se está moviendo SÍ lleva el color de vivo", /v-late/.test(
   pintarCon(conConsola([Object.assign(bg("bx", "trabajando"),
     { quieto_hace: 0 })])).vivos.innerHTML));
af("el asa para abrirlo se muestra, y es un texto: capataz no lo corre",
   p9.pide.innerHTML.indexOf("claude attach b1") >= 0);
/* Los dos lados de la misma cosa, y la segunda es la que la salva de ser
   vacua: una pantalla que mandara a **todos** a la zona de «pide una persona»
   pasaría la primera sin despeinarse. */
af("el que espera a una persona está arriba, y el que trabaja no",
   p9.pide.innerHTML.indexOf("el b2") < 0 &&
   p9.vivos.innerHTML.indexOf("el b2") >= 0, p9.vivos.innerHTML.slice(0, 200));

/* **Y un fantasma no espera a nadie.** El CLI da por `esperando` a todo
   background que murió sin avisar —su registro no se limpia nunca (T37)—, así
   que si eso subiera a la zona de arriba, la zona estaría ocupada en todas las
   corridas y el cartel que se hizo para que un pedido se vea rápido sería el
   aviso que enseña a ignorarse. **Se encontró mirando la pantalla**, no acá:
   los dos primeros carteles de «trabado» eran dos agentes muertos hacía horas. */
const fantasma = Object.assign(bg("b7", "esperando", "trabado: necesita a una persona"),
  { quieto_hace: null });
const p9e = pintarCon(conConsola([fantasma]));
p9e.contexto.pintar((function () {
  const d = conConsola([fantasma]);
  d.taller.agentes_maquina.forEach(function (f) {
    f.fuente = "cli"; f.fantasma = true;
    f.motivo_consola = "el CLI lo da por «esperando» pero ya no queda ningún " +
      "archivo suyo: el registro quedó viejo, no está esperando a nadie";
  });
  d.agentes_todos = d.taller.agentes_maquina.slice();
  return d;
})());
af("un background del que no queda archivo NO ocupa la zona que pide una persona",
   p9e.pide.innerHTML.indexOf("el b7") < 0, p9e.pide.innerHTML.slice(0, 200));
af("ni la de los que trabajan: el CLI afirma algo que su archivo desmiente",
   p9e.vivos.innerHTML.indexOf("el b7") < 0, p9e.vivos.innerHTML.slice(0, 200));
af("pero se muestra igual, abajo, y con el motivo: capataz no lo esconde",
   p9e.taller.innerHTML.indexOf("el b7") >= 0 &&
   p9e.taller.innerHTML.indexOf("el registro quedó viejo") >= 0,
   p9e.taller.innerHTML.slice(0, 260));

/* El estado de un background NO se recalcula con el reloj, al revés que el de
   una rama y el de un subagente. Aquéllos son «hace cuánto que no se mueve»;
   éste es un hecho que el CLI afirma. Recalcularlo sería inventarlo. */
const viejo = bg("b9", "trabajando");
viejo.hace = 999999;
af("un background que arrancó hace un siglo sigue diciendo lo que dice el CLI",
   pintarCon(conConsola([viejo])).taller.innerHTML.indexOf("trabajando") >= 0);

/* No pude preguntar ≠ no hay ninguno. */
const p9b = pintarCon(conConsola([], {
  ok: false, error: "no pude correr «claude agents --json --all»: no such file" }));
af("si la consola no se pudo leer, se dice y se nombra el comando que corrió",
   p9b.taller.innerHTML.indexOf("claude agents --json --all") >= 0,
   p9b.taller.innerHTML.slice(0, 140));
af("y se aclara que lo que sale de los archivos se lee igual",
   p9b.taller.innerHTML.indexOf("se lee igual") >= 0,
   p9b.taller.innerHTML.slice(0, 200));
const p9c = pintarCon(conConsola([]));
af("y cero agentes es otra cosa: se dice que no hay ninguno",
   p9c.taller.innerHTML.indexOf("ningún agente de Claude Code") >= 0,
   p9c.taller.innerHTML.slice(0, 140));

/* Los dos lados del aviso que no puede salir siempre. */
af("sin desacuerdos, la pantalla no dibuja ninguno",
   p9c.taller.innerHTML.indexOf("no dicen lo mismo") < 0);
const p9d = pintarCon(conConsola([], { desacuerdos: [{
  sesion: "s-7", que: "la carpeta no coincide",
  consola: "/uno", taller: "/otro" }] }));
af("con uno, se muestra y se ven **las dos** versiones",
   p9d.taller.innerHTML.indexOf("/uno") >= 0 &&
   p9d.taller.innerHTML.indexOf("/otro") >= 0);
af("y se dice que capataz no eligió ganador",
   p9d.taller.innerHTML.indexOf("no elige un ganador") >= 0 ||
   p9d.taller.innerHTML.indexOf("no elige") >= 0);

/* -------------------------------------------------------------------------
   § 10 · El menú — y que una pestaña no esconda nada

   El pedido fue «una app con menús, y el primer dashboard el de los agentes de
   la consola». Lo que hay que verificar no es que el menú se dibuje: es que
   **navegar no haga a capataz menos honesto**. Apiladas, las cuatro secciones
   se veían al pasar; detrás de un menú, un «no pude leer» que nadie abre es un
   error que no existe.

   Por eso las dos mitades: la marca **sale** cuando hay algo, y **no sale**
   cuando no lo hay. Sin la segunda, prender las cuatro pestañas siempre pasaría
   este arnés y sería el aviso que enseña a ignorarse.
------------------------------------------------------------------------- */
console.log("\n§ 10 · El menú");

function igualdad(descripcion, obtenido, esperado) {
  af(descripcion, JSON.stringify(obtenido) === JSON.stringify(esperado),
     "obtuve " + JSON.stringify(obtenido) + ", esperaba " + JSON.stringify(esperado));
}

const p10 = pintarCon(datos);
const ctx10 = p10.contexto;

af("arranca en los agentes, que es la pantalla que se pidió",
   ctx10.VISTA === "agentes");
igualdad("y esa es la única vista abierta",
  p10.vistas.filter((v) => !v.hasAttribute("hidden")).map(
    (v) => v.getAttribute("data-vista")), ["agentes"]);
af("el menú se dibuja en los dos lugares: lateral y tabbar",
   p10["nav-principal"].innerHTML.indexOf("Agentes") >= 0 &&
   p10.tabbar.innerHTML.indexOf("Proyectos") >= 0);
igualdad("y quedaron **dos** vistas, no más",
  ["Agentes", "Proyectos", "Taller", "Consola", "GitHub"].filter(
    (r) => p10.tabbar.innerHTML.indexOf(r) >= 0), ["Agentes", "Proyectos"]);
af("la pestaña abierta se marca como tal, para que se sepa dónde uno está",
   /aria-current="page"/.test(p10.tabbar.innerHTML));

ctx10.irA("proyectos");
igualdad("al navegar, la abierta es la nueva y ninguna otra",
  p10.vistas.filter((v) => !v.hasAttribute("hidden")).map(
    (v) => v.getAttribute("data-vista")), ["proyectos"]);
af("y el contenido de la vista de antes NO se borra: no se vuelve a pedir nada",
   p10.taller.innerHTML.length > 50,
   String(p10.taller.innerHTML.length));
ctx10.irA("agentes");
igualdad("y se puede volver", p10.vistas.filter(
  (v) => !v.hasAttribute("hidden")).map((v) => v.getAttribute("data-vista")),
  ["agentes"]);

/* La frescura y el pulso viven en la barra, no adentro de una vista: si
   estuvieran en una, las otras tres mostrarían datos sin decir de cuándo son. */
af("la frescura se escribe en el shell y no en una pestaña",
   p10.frescura.textContent.length > 5, p10.frescura.textContent);
af("y sigue escrita después de navegar a otra vista",
   (ctx10.irA("proyectos"), ctx10.pintarFrescura(),
    p10.frescura.textContent.length > 5), p10.frescura.textContent);

/* --- La marca: los dos lados ------------------------------------------ */
function conTodoSano() {
  const d = conConsola([bg("ok1", "trabajando")]);
  d.taller = { ok: true, error: "", raiz: "/x", alcance: "esta máquina · ahora",
               leido_en: d.ahora, sesiones: [], cuenta: {}, sueltas: 0 };
  d.agentes = (d.agentes || []).map((a) => Object.assign({}, a,
    { estado: "trabajando" }));
  d.proyectos = d.proyectos.map((p) => Object.assign({}, p,
    { seguimiento: Object.assign({}, p.seguimiento, { existe: true, error: "" }) }));
  return d;
}
const sano = pintarCon(conTodoSano());
af("con todo sano, NINGUNA pestaña se marca — si no, el aviso sale siempre",
   sano.tabbar.innerHTML.indexOf("marca-vista") < 0,
   sano.tabbar.innerHTML.slice(0, 200));
/* La anti-vacua de la de arriba, y la razón de ser de toda la sección. */
const rota = pintarCon(conConsola([], {
  ok: false, error: "no pude correr «claude agents --json --all»" }));
af("una consola que no se pudo leer marca su pestaña **estando escondida**",
   (rota.contexto.irA("proyectos"),
    rota.tabbar.innerHTML.indexOf("marca-vista") >= 0),
   rota.tabbar.innerHTML.slice(0, 240));
af("un background esperando a una persona también marca",
   pintarCon(conConsola([bg("b1", "esperando")])).tabbar
     .innerHTML.indexOf("marca-vista") >= 0);
af("pero uno terminado no: es un hecho, no un pendiente",
   pintarCon(conConsola([bg("b1", "terminado")])).tabbar
     .innerHTML.indexOf("marca-vista") < 0);

/* Y el estado que NO puede marcar, porque sale en todas las corridas. Medido el
   2026-08-15 contra los datos de verdad: los cuatro agentes del tablero están
   «caído» y los tres proyectos tienen filas «sin estado». */
const conCaidos = conTodoSano();
conCaidos.agentes = [{ quien: "x", proyecto: "P", que: "r", estado: "caído",
                       punto: "", asunto: "", sha: "a" }];
conCaidos.agentes_todos = soloGitHub(conCaidos.agentes);
af("«caído» NO marca la pestaña: es el estado más común del tablero",
   pintarCon(conCaidos).tabbar.innerHTML.indexOf("marca-vista") < 0);
const conSinRama = conTodoSano();
conSinRama.agentes = [{ quien: "x", proyecto: "P", que: "r", estado: "sin rama",
                        punto: "T1", asunto: "", sha: "" }];
conSinRama.agentes_todos = soloGitHub(conSinRama.agentes);
af("«sin rama» sí marca: es un `en curso` del que no llegó ni un commit",
   pintarCon(conSinRama).tabbar.innerHTML.indexOf("marca-vista") >= 0);

/* -------------------------------------------------------------------------
   § 11 · Apariencia — claro, oscuro, y lo que diga el aparato

   Lo que hay que verificar no es que el menú se dibuje: es que **la
   preferencia mande, que se recuerde, y que no romper nada cuando no hay dónde
   recordarla**. Una instantánea abierta con `file://` no tiene `localStorage`,
   y ahí la pantalla tiene que seguir andando.
------------------------------------------------------------------------- */
console.log("\n§ 11 · Apariencia");

const p11 = pintarCon(datos);
af("arranca en automático si nadie eligió nada", p11.contexto.TEMA === "auto");
af("y con el sistema en oscuro, no se marca el tema claro",
   p11.raiz.getAttribute("data-tema") === null,
   String(p11.raiz.getAttribute("data-tema")));
af("el menú ofrece los tres",
   ["Automático", "Claro", "Oscuro"].every(
     (r) => p11["menu-apariencia"].innerHTML.indexOf(r) >= 0),
   p11["menu-apariencia"].innerHTML.slice(0, 160));
af("y marca cuál está puesto", /aria-current="true"/.test(
   p11["menu-apariencia"].innerHTML));

p11.contexto.aplicarTema("claro");
af("elegir claro marca la raíz, que es de donde cuelgan los colores",
   p11.raiz.getAttribute("data-tema") === "claro",
   String(p11.raiz.getAttribute("data-tema")));
af("y la preferencia se recuerda en el navegador, no en el servidor",
   p11.guardado["capataz-tema"] === "claro",
   JSON.stringify(p11.guardado));
p11.contexto.aplicarTema("oscuro");
af("elegir oscuro la saca", p11.raiz.getAttribute("data-tema") === null,
   String(p11.raiz.getAttribute("data-tema")));

/* Automático mira al aparato, y hay que probar los dos lados: con uno solo, un
   `temaEfectivo()` que devolviera siempre lo mismo pasaría igual. */
p11.contexto.window.matchMedia = (q) => ({ matches: true, media: q });
p11.contexto.aplicarTema("auto");
af("en automático, si el aparato pide claro, se pone claro",
   p11.raiz.getAttribute("data-tema") === "claro");
p11.contexto.window.matchMedia = (q) => ({ matches: false, media: q });
p11.contexto.aplicarTema("auto");
af("y si pide oscuro, oscuro", p11.raiz.getAttribute("data-tema") === null);

/* Sin dónde guardar —una instantánea en `file://`— no se rompe nada. */
const p11b = pintarCon(datos);
delete p11b.contexto.window.localStorage;
delete p11b.contexto.window.matchMedia;
let exploto = false;
try { p11b.contexto.aplicarTema("claro"); } catch (e) { exploto = true; }
af("sin localStorage ni matchMedia la pantalla no se rompe", !exploto);
af("y el tema elegido igual se aplica",
   p11b.raiz.getAttribute("data-tema") === "claro");

/* -------------------------------------------------------------------------
   § 12 · El latido — que se vea cuál está trabajando AHORA

   Pedido de Pablo: «hace 0 s sin escribir significa activo, hace 34 min
   significa que no está haciendo nada». El umbral no se inventó: es el p90 de
   los huecos medidos, y **lo manda el servidor** como los otros dos.

   Y late **sin cambiar el estado**: pasado el umbral el agente sigue
   `trabajando`. Si el latido decidiera el estado, uno pensando veinte segundos
   se vería apagado — el error que los umbrales medidos evitan.
------------------------------------------------------------------------- */
console.log("\n§ 12 · El latido");

af("el servidor manda el umbral del latido, y la pantalla no lo copia",
   datos.umbrales_taller && typeof datos.umbrales_taller.latiendo === "number",
   JSON.stringify(datos.umbrales_taller));
af("y es más chico que el de «trabajando»: es una banda para mirar, no un estado",
   datos.umbrales_taller.latiendo < datos.umbrales_taller.fresco);

function conLatido(seg) {
  const s = copia(sesion);
  s.quieto_hace = seg; s.que = "Bash"; s.sobre = "algo"; s.agentes = [];
  // Las dos zonas: la que late está arriba y la de hace 34 minutos abajo, y lo
  // que esta sección afirma es el latido, no en cuál cayó.
  return htmlAgentes(pintarCon(conTaller([s])));
}
const activa = conLatido(0);
const dormida = conLatido(34 * 60);
af("una sesión que escribió recién late", /class="late"/.test(activa),
   activa.slice(0, 200));
af("y una de hace 34 minutos no", !/class="late"/.test(dormida));
/* Los dos lados del umbral exacto, que es lo que verifica que se use el número
   del servidor y no otro. */
af("justo debajo del umbral, late",
   /class="late"/.test(conLatido(datos.umbrales_taller.latiendo - 1)));
af("justo encima, no",
   !/class="late"/.test(conLatido(datos.umbrales_taller.latiendo + 1)));
af("y la que late sigue diciendo que está prendida: el latido no es un estado",
   activa.indexOf("prendida") >= 0, activa.slice(0, 220));

/* -------------------------------------------------------------------------
   § 13 · Los que trabajan ahora: orden fijo y el renglón que se actualiza
          por adentro

   El pedido de Pablo del 2026-08-17: «los agentes que están vivos tienen que
   quedar fijo y que se vaya actualizando el contenido de adentro, no que vayan
   cambiando el orden a medida que mete una acción cada uno».

   Son **dos** cosas y ninguna alcanza sola, así que hay aserciones de las dos:

     · el orden no se rehace aunque el servidor mande otro —y la anti-vacua de
       eso es que una pantalla recién abierta **sí** respeta el que le mandan,
       porque si no, «no baraja» pasaría con una lista que siempre sale igual
       por casualidad—;
     · la caja de cada agente es **el mismo objeto del DOM** entre dos pintadas,
       y lo que cambia es lo de adentro. Sin esto, el orden podría quedar fijo y
       aun así el renglón que estás leyendo dejaría de existir dos veces por
       segundo, que es la mitad del problema que se quiso arreglar.
------------------------------------------------------------------------- */
console.log("\n§ 13 · Los vivos: orden fijo y contenido que se actualiza adentro");

function ses(nombre, quieto, que, sobre) {
  return Object.assign(copia(sesion), {
    sesion: "s-" + nombre, nombre: nombre, quieto_hace: quieto,
    que: que || "Bash", sobre: sobre || "algo", agentes: []
  });
}
/* El orden **dibujado**, leído del HTML de la zona y no de la estructura de
   nodos. Es a propósito: si esto mirara `hijos`, una pantalla que volviera a
   armar la zona con un `innerHTML` —el bug que se quiere evitar— daría lista
   vacía y se pondría roja por el motivo equivocado, sin decir nunca que el
   orden se barajó. Así, la aserción se pone roja diciendo qué orden salió. */
function nombresDe(p) {
  return (p.vivos.innerHTML.match(/class="nombre">agente-[abcd]/g) || [])
    .map(function (t) { return t.slice(t.indexOf(">") + 1); });
}

const tres = [ses("agente-a", 1), ses("agente-b", 2), ses("agente-c", 3)];
const p13 = pintarCon(conTaller(copia(tres)));
af("los que trabajan se dibujan arriba, cada uno en su propia caja",
   p13.vivos.hijos.length === 3, String(p13.vivos.hijos.length));
const orden1 = nombresDe(p13);
igual("y en la primera lectura salen como los manda el servidor",
      orden1, ["agente-a", "agente-b", "agente-c"]);

/* Lo mismo, del revés, en una pantalla **recién abierta**: acá el orden del
   servidor sí manda. Es la anti-vacua de la aserción de abajo. */
const pRev = pintarCon(conTaller([copia(tres[2]), copia(tres[1]), copia(tres[0])]));
igual("una pantalla nueva respeta el orden que le mandan (si no, «no baraja» " +
      "pasaría con cualquier lista)",
      nombresDe(pRev), ["agente-c", "agente-b", "agente-a"]);

/* Y ahora el pedido: la MISMA pantalla, con el orden dado vuelta —que es lo que
   pasa de verdad cuando otro agente escribe una línea y pasa a ser el que se
   movió recién—. No se tiene que mover nadie. */
p13.contexto.pintar(conTaller([copia(tres[2]), copia(tres[1]), copia(tres[0])]));
igual("y si el servidor cambia el orden, la pantalla NO baraja: cada uno se " +
      "queda en su lugar", nombresDe(p13), orden1);

/* El mismo nodo, no uno nuevo con el mismo dibujo. */
const cajaA = p13.vivos.hijos[0];
const antesB = p13.vivos.hijos[1].innerHTML;
const cambiado = copia(tres);
cambiado[0].que = "Edit";
cambiado[0].sobre = "nube.py";
p13.contexto.pintar(conTaller(cambiado));
af("la caja del primero es el MISMO nodo después de repintar",
   p13.vivos.hijos[0] === cajaA);
af("y lo que cambió es su contenido de adentro",
   cajaA.innerHTML.indexOf("nube.py") >= 0, cajaA.innerHTML.slice(0, 200));
af("mientras que la del que no cambió no se reescribió",
   p13.vivos.hijos[1].innerHTML === antesB,
   p13.vivos.hijos[1].innerHTML.slice(0, 120));

/* El reloj es el otro nodo, y es el que cambia siempre. Se mueve el reloj de la
   máquina para atrás —que es lo que hace el tiempo— y se pide un tick: el
   contador tiene que avanzar **sin que se reescriba una línea de HTML**. */
const nodoA = p13.contexto.NODOS_VIVOS[Object.keys(p13.contexto.NODOS_VIVOS)[0]];
const relojAntes = nodoA.reloj.textContent;
const accionAntes = nodoA.accion.innerHTML;
p13.contexto.T_RECIBIDO = Date.now() - 300000;
p13.contexto.tick();
af("el contador avanza solo entre dos lecturas del servidor",
   nodoA.reloj.textContent !== relojAntes,
   relojAntes + " → " + nodoA.reloj.textContent);
af("y avanzarlo no reescribe lo que el agente está haciendo",
   nodoA.accion.innerHTML === accionAntes);
af("ni cambia la caja por otra", p13.vivos.hijos[0] === cajaA);

/* Uno nuevo: **al final**, aunque el servidor lo mande primero. Si entrara
   arriba, empujaría un lugar a todos los que se están leyendo. */
const conNuevo = [ses("agente-d", 1)].concat(copia(cambiado));
p13.contexto.pintar(conTaller(conNuevo));
igual("un agente nuevo entra al final, aunque el servidor lo mande primero",
      nombresDe(p13), ["agente-a", "agente-b", "agente-c", "agente-d"]);

/* Y el que deja de trabajar se va de la zona: su caja se saca del contenedor.
   Sin esto, la zona sería una lista que sólo crece. */
p13.contexto.pintar(conTaller([copia(cambiado[0])]));
igual("el que deja de trabajar se va de arriba", nombresDe(p13), ["agente-a"]);
af("y su caja se sacó del DOM, no quedó escondida",
   p13.vivos.hijos.length === 1, String(p13.vivos.hijos.length));

/* -------------------------------------------------------------------------
   § 14 · Un proyecto: lo que falta, y que el orden no se presente como una
          opinión de capataz

   «Fuerte foco en los puntos pendientes y priorizando por importancia de la
   funcionalidad.» La importancia no está escrita en ninguna celda de ningún
   seguimiento, así que lo que se verifica es lo otro: que la pantalla dibuje
   lo que `lector.falta()` ordenó **sin volver a ordenarlo** (dos criterios en
   dos archivos son la regla 1 rota), que el tope diga lo que no entró, y que
   la regla del orden esté escrita al lado del orden.
------------------------------------------------------------------------- */
console.log("\n§ 14 · Un proyecto: lo que falta");

function conFalta(puntos) {
  const d = copia(datos);
  d.proyectos = [copia(legibles[0])];
  d.proyectos[0].falta = puntos;
  return d;
}
function punto(id, grupo, rotulo, titulo) {
  return { id: id, titulo: titulo || ("el punto " + id), grupo: grupo,
           rotulo_grupo: rotulo, porque: "x", dias: 3, quien: "",
           estado: "pendiente" };
}
const cuatro = [
  punto("T1", 0, "en curso"), punto("D9", 1, "espera a una persona"),
  punto("T2", 2, "pendiente"), punto("T3", 3, "sin estado")
];
const h14 = pintarCon(conFalta(cuatro)).cuerpo.innerHTML;
af("lo que falta se dibuja, y en el orden que decidió el lector",
   h14.indexOf("T1") < h14.indexOf("D9") &&
   h14.indexOf("D9") < h14.indexOf("T2") &&
   h14.indexOf("T2") < h14.indexOf("T3"), h14.slice(0, 200));
af("cada grupo dice cómo se llama, para que el orden se entienda",
   h14.indexOf("en curso") >= 0 && h14.indexOf("espera a una persona") >= 0 &&
   h14.indexOf("sin estado") >= 0);
af("y cada punto lleva el color de su grupo",
   /class="punto g0"/.test(h14) && /class="punto g1"/.test(h14),
   h14.slice(0, 200));
/* La regla 3 puesta en el orden: capataz **dice** que la importancia no la
   sabe. Un orden sin su regla al lado se lee como una decisión suya. */
af("y la pantalla dice con qué ordenó, y que la importancia no la sabe",
   h14.indexOf("orden en que está escrito") >= 0 &&
   h14.indexOf("no está escrito en ninguna celda") >= 0, h14.slice(0, 400));

/* El tope, y su mitad honesta: lo que no entró se dice. Un corte silencioso se
   lee como «esto es todo lo que falta», que es la peor de las dos mentiras. */
const muchos = [];
for (let i = 0; i < 20; i++) muchos.push(punto("T" + (100 + i), 2, "pendiente"));
muchos.push(punto("ZZ9", 2, "pendiente", "el que no entra"));
const hTope = pintarCon(conFalta(muchos)).cuerpo.innerHTML;
af("con más puntos que el tope, se dibujan sólo los primeros",
   hTope.indexOf("el que no entra") < 0, hTope.slice(0, 200));
af("y se dice cuántos quedaron afuera: un corte en silencio se lee como que " +
   "no falta nada más", /y \d+ más/.test(hTope), hTope.slice(0, 300));
af("y se dice dónde están de verdad: el seguimiento del proyecto",
   hTope.indexOf("que es la verdad") >= 0);

/* Cero abiertos no es lo mismo que no haberlo podido leer, y las dos se
   parecen mucho en una pantalla vacía. */
const hCero = pintarCon(conFalta([])).cuerpo.innerHTML;
af("un proyecto sin puntos abiertos lo dice con todas las letras",
   hCero.indexOf("ningún punto abierto") >= 0, hCero.slice(0, 200));

console.log("\nASERCIONES: " + ASER + "\nROJAS: " + ROJAS);
process.exit(ROJAS ? 1 : 0);

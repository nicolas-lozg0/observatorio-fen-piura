"""
Prueba de la página (docs/index.html) en un navegador sin ventana, antes de subir cambios.

Revisa, en escritorio (1280 px) y celular (375 px):
  - que cada dirección #pestaña muestre solo su pestaña y la marque en el menú;
  - que la página no se desplace de lado, ni con el detalle abierto;
  - que ninguna tabla larga (más de 15 filas) se vea sin abrir "Ver detalle";
  - que no haya errores en la consola ni tokens de diseño (var(--…)) sin definir;
  - que un enlace antiguo (#alertas) abra Obras con el detalle desplegado;
  - que el año de la pestaña Dengue sea el de la sala de la DIRESA;
  - que los rótulos del gráfico semanal de dengue no se encimen ni se salgan del gráfico;
  - que las pestañas midan al menos 44 px de alto, y que estén el botón de compartir y los enlaces "Siguiente";
  - que los 5 títulos de la portada tengan texto y que el de salud cuadre con el mes de su cifra y su comparación;
  - que el título del dengue siga la regla de semanas completas (las preliminares no cuentan) y que el semáforo del
    presupuesto cambie en 5 y 15 puntos;
  - que los mapas de Obras y Salud (Leaflet) se dibujen, o digan claramente que no cargaron;
  - los nombres cortos de obras, las duraciones en años y meses y los nombres legibles de entidades;
  - que el título y el color de las obras paralizadas sigan la regla frente al país, y que cada causa tenga definición;
  - que un dato de camas de SUSALUD que no cuadra se marque para revisar, y uno normal no;
  - que aparezca "Dato no actualizado" si se simula una fecha 60 días después.

Requiere Playwright (pip3 install playwright) y un navegador Chromium: usa Brave o Chrome si están
instalados (Playwright no trae navegador para macOS 12); otro, con la variable NAVEGADOR=/ruta/al/ejecutable.
Uso: python3 scripts/test_pagina.py
"""
import os
import socket
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

from playwright.sync_api import sync_playwright

DOCS = Path(__file__).resolve().parent.parent / "docs"
PESTANAS = ["resumen", "clima", "dengue", "gasto", "obras", "vulnerabilidad", "salud", "precios", "fuentes"]
NAVEGADORES = [os.environ.get("NAVEGADOR"), "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
               "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]
fallos = []


def revisar(condicion, mensaje):
    if not condicion:
        fallos.append(mensaje)


def puerto_libre():
    with socket.socket() as s:
        s.bind(("localhost", 0))
        return s.getsockname()[1]


def abrir_navegador(p):
    ruta = next((r for r in NAVEGADORES if r and Path(r).exists()), None)
    return p.chromium.launch(executable_path=ruta, headless=True) if ruta else p.chromium.launch(headless=True)


def main():
    puerto = puerto_libre()
    # salida del servidor a /dev/null: si se leyera por una tubería sin vaciarla, podría bloquearse
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(puerto), "-d", str(DOCS)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://localhost:{puerto}/index.html"
    try:
        time.sleep(1)
        with sync_playwright() as p:
            nav = abrir_navegador(p)
            for ancho in (1280, 375):
                pg = nav.new_page(viewport={"width": ancho, "height": 900})
                errores = []
                pg.on("pageerror", lambda e: errores.append(str(e)))
                # imerg_piura.json no existe hasta la primera ejecución del workflow imerg.yml (necesita el token): su 404 no es un error de la página
                pg.on("console", lambda m: m.type == "error" and not m.location.get("url", "").endswith("imerg_piura.json") and errores.append(m.text))
                pg.goto(base + "#resumen")
                pg.wait_for_function("document.querySelectorAll('#resumen-paneles .panel').length >= 5", timeout=15000)
                for t in PESTANAS:
                    pg.evaluate(f"location.hash = '#{t}'")
                    pg.wait_for_timeout(300)
                    r = pg.evaluate(f"""() => {{
                        const s = document.getElementById('{t}'), de = document.documentElement;
                        const visibles = [...document.querySelectorAll('.pestana')].filter(x => !x.hidden).map(x => x.id);
                        const actual = document.querySelector('.pestanas a[aria-current="page"]')?.getAttribute('href');
                        const tablas = [...s.querySelectorAll('table')].filter(tb => !tb.closest('details'))
                            .map(tb => tb.querySelectorAll('tbody tr').length);
                        const desborde1 = de.scrollWidth - de.clientWidth;
                        s.querySelectorAll('details').forEach(d => d.open = true);
                        const desborde2 = de.scrollWidth - de.clientWidth;
                        s.querySelectorAll('details').forEach(d => d.open = false);
                        return {{ visibles, actual, tablas, desborde1, desborde2 }};
                    }}""")
                    revisar(r["visibles"] == [t], f"{ancho}px #{t}: se ven {r['visibles']}")
                    revisar(r["actual"] == f"#{t}", f"{ancho}px #{t}: el menú marca {r['actual']}")
                    revisar(max(r["desborde1"], r["desborde2"]) <= 0,
                            f"{ancho}px #{t}: la página se desplaza de lado ({r['desborde1']} / {r['desborde2']} px con detalle)")
                    largas = [n for n in r["tablas"] if n > 15]
                    revisar(not largas,
                            f"{ancho}px #{t}: tablas visibles sin abrir el detalle ({r['tablas']} filas)")
                pg.evaluate("location.hash = '#alertas'")
                pg.wait_for_timeout(300)
                r = pg.evaluate("() => ({ tab: [...document.querySelectorAll('.pestana')].filter(x => !x.hidden).map(x => x.id),"
                                " abierto: document.querySelector('#obras details').open })")
                revisar(r == {"tab": ["obras"], "abierto": True}, f"{ancho}px #alertas: {r}")
                anio = pg.evaluate("() => [document.querySelector('#t-dengue .anio-d').textContent,"
                                   " String(D.d26?.fecha_corte ?? '').slice(0, 4)]")
                revisar(anio[0] == anio[1] and anio[0].isdigit(), f"{ancho}px: año de Dengue {anio[0]} y de la sala {anio[1]}")
                # Rótulos del gráfico semanal: cajas reales, sin choques entre ellas ni fuera del gráfico
                pg.evaluate("location.hash = '#dengue'")
                pg.wait_for_timeout(500)
                r = pg.evaluate("""() => {
                    const svg = document.querySelector('#g-semanas svg'), w = svg.viewBox.baseVal.width;
                    const c = [...svg.querySelectorAll('text.rotulo')].map(t => { const b = t.getBBox();
                        return { t: t.textContent, x0: b.x, y0: b.y, x1: b.x + b.width, y1: b.y + b.height }; });
                    const choques = c.flatMap((a, i) => c.slice(i + 1).filter(b => a.x0 < b.x1 && b.x0 < a.x1 && a.y0 < b.y1 && b.y0 < a.y1)
                        .map(b => a.t + ' / ' + b.t));
                    return { n: c.length, choques, fuera: c.filter(a => a.x0 < 0 || a.x1 > w || a.y0 < 0).map(a => a.t) };
                }""")
                revisar(r["n"] >= 2 and not r["choques"] and not r["fuera"],
                        f"{ancho}px gráfico de dengue: {r['n']} rótulos, se enciman {r['choques']}, fuera {r['fuera']}")
                r = pg.evaluate("""() => ({ alto: Math.min(...[...document.querySelectorAll('.pestanas a')].map(a => a.getBoundingClientRect().height)),
                    compartir: !!document.getElementById('compartir'), siguientes: document.querySelectorAll('.siguiente a').length,
                    actualizado: document.getElementById('actualizado').textContent })""")
                revisar(r["alto"] >= 44, f"{ancho}px: pestañas de {r['alto']:.0f} px (mínimo 44)")
                revisar(r["compartir"] and r["siguientes"] == len(PESTANAS) and r["actualizado"].startswith("Actualizado al"),
                        f"{ancho}px: compartir {r['compartir']}, enlaces Siguiente {r['siguientes']}, «{r['actualizado']}»")
                # Todo var(--token) usado en la página (estilos y SVG generados) debe estar definido
                sin_definir = pg.evaluate("""() => { const css = getComputedStyle(document.documentElement);
                    const usados = new Set([...document.documentElement.outerHTML.matchAll(/var\\((--[\\w-]+)[),]/g)].map(m => m[1]));
                    return [...usados].filter(v => !['--c', '--x', '--p', '--n', '--prom', '--t'].includes(v) && !css.getPropertyValue(v).trim()); }""")
                revisar(not sin_definir, f"{ancho}px: tokens sin definir: {sin_definir}")
                revisar(not errores, f"{ancho}px: errores en la consola: {errores[:3]}")
                pg.close()
            # Títulos de la portada: 5 con texto; el de salud, por regla, solo si la serie y la cifra son del mismo mes
            pg = nav.new_page()
            pg.goto(base + "#resumen")
            pg.wait_for_function("document.querySelectorAll('#resumen-paneles .panel').length >= 5", timeout=15000)
            r = pg.evaluate("""() => {
                const t = [...document.querySelectorAll('#resumen-paneles .panel h3')].map(h => h.textContent.trim());
                const o = ocupacionSerie(), sal = t.find(x => /salud|ocupación de camas/i.test(x));
                let esperado = '¿Está preparada la salud?';
                if (o?.dir) esperado = `La ocupación de camas ${o.dir} frente a hace un año`;
                const regla = !o?.prev || (o.oc(o.u) - o.oc(o.prev) >= 1 ? 'sube' : o.oc(o.u) - o.oc(o.prev) <= -1 ? 'baja' : 'se mantiene') === o.dir;
                // con la serie desfasada un mes, el título vuelve a la pregunta
                D.camas = { ...D.camas, periodo: 'agosto de 1999' };
                const desfasada = ocupacionSerie() === null;
                return { t, sal, esperado, regla, desfasada };
            }""")
            revisar(len(r["t"]) == 5 and all(r["t"]), f"títulos de la portada: {r['t']}")
            # Dengue: tendencia de las 4 últimas semanas completas; cambiar una semana preliminar no la mueve
            r2 = pg.evaluate("""() => {
                const d = D.d26, t = tendenciaDengue(d), titulo = document.querySelector('#resumen-paneles .destacado h3').textContent.trim();
                const prelim = { ...d, serie: d.serie.map(([s, c]) => [s, s > d.se - PRELIMINAR ? 0 : c]) };
                const sube = { ...d, serie: d.serie.map(([s, c]) => [s, s <= d.se - PRELIMINAR && s > d.se - PRELIMINAR - 4 ? c * 3 : c]) };
                const baja = { ...d, serie: d.serie.map(([s, c]) => [s, s <= d.se - PRELIMINAR && s > d.se - PRELIMINAR - 4 ? 0 : c]) };
                return { titulo, esperado: `El dengue ${t.dir} en las últimas 4 semanas completas`, igual: tendenciaDengue(prelim).dir === t.dir,
                  sube: tendenciaDengue(sube).dir, baja: tendenciaDengue(baja).dir,
                  semaforo: [semaforo(80, 85)[1], semaforo(79.9, 85)[1], semaforo(70, 85)[1], semaforo(69.9, 85)[1]],
                  nombres: [nombreCorto("  "), nombreCorto("A".repeat(90)).length, nombreCorto("MEJORAMIENTO DE LA I E SAN JOSE EN LA LOCALIDAD DE CASTILLA DISTRITO DE CASTILLA"),
                    nombreCorto("AGUA POTABLE EN LAS LOCALIDADES DE SULLANA Y MARCAVELICA DE LA PROVINCIA DE SULLANA DEPARTAMENTO DE PIURA"),
                    distritoDengue({ distrito: "SALITRAL (MOR)", provincia: "MORROPON" }),
                    duracion(0), duracion(250), duracion(365.25 * 4 + 3), duracion(640)],
                  entidades: [legible("MUNICIPALIDAD DISTRITAL DE LA UNION"), legible("MUNICIPALIDAD DISTRITAL DE SAN MIGUEL DE EL FAIQUE"),
                    legible("MANCOMUNIDAD MUNICIPAL SIMON RODRIGUEZ - MMSR")] };
            }""")
            revisar(r2["titulo"] == r2["esperado"] and r2["igual"] and r2["sube"] == "sube" and r2["baja"] == "baja",
                    f"regla del dengue: {r2}")
            revisar(r2["semaforo"] == ["ok", "lento", "lento", "muy-lento"], f"semáforo: {r2['semaforo']}")
            revisar(r2["nombres"] == ["Obra sin nombre", 90, "I.E. san jose", "Agua potable en las localidades de Sullana y Marcavelica", "Salitral (Morropón)", "menos de 1 mes", "8 meses", "4 años", "1 año y 9 meses"],
                    f"nombres cortos y duraciones: {r2['nombres']}")
            # Camas: dato de SUSALUD que no cuadra se marca (no se corrige); un dato normal no
            r4 = pg.evaluate("""() => [!!datoCamaRaro({ reporto: true, camas: 8, dias_cama: 95, pacientes_dia: 98 }, "setiembre de 2026"),
                !!datoCamaRaro({ reporto: true, camas: 10, dias_cama: 300, pacientes_dia: 200 }, "setiembre de 2026"),
                diasMes("febrero de 2028")]""")
            revisar(r4 == [True, False, 29], f"datos de camas a revisar: {r4}")
            # Obras revisadas a mano: las reactivadas se señalan en la lista, sin cambiar la cifra de paralizadas
            r5 = pg.evaluate("""() => { const t = document.querySelectorAll('#resumen-paneles .panel')[2].querySelector('.cifra').textContent;
                const act = D.obras.obras.filter(x => !APARTE[x.codigo_infobras]);
                return { cifra: t.trim() === String(act.filter(x => x.estado === "Paralizada").length),
                  reactivadas: act.filter(reactivada).map(x => x.codigo_infobras).sort() }; }""")
            revisar(r5["cifra"] and r5["reactivadas"] == ["114837", "88999"], f"obras revisadas a mano: {r5}")
            # Obras frente al país: título y color siguen la regla de 1 punto; cada causa de Piura tiene definición
            r3 = pg.evaluate("""() => {
                const act = D.obras.obras.filter(x => !APARTE[x.codigo_infobras]), par = act.filter(x => x.estado === "Paralizada");
                const c = obrasPais(act, par), tarjeta = document.querySelectorAll('#resumen-paneles .panel')[2];
                const sube = obrasPais(act, [...par, ...act.filter(x => x.estado !== "Paralizada").slice(0, Math.ceil(act.length * .02))]);
                const titulos = [tituloPais({ comp: "similar", costoAlto: true }),
                  tituloPais({ ...c, costoAlto: c.cP >= COSTO_ALTO * (c.cP + 1) })];
                return { ok: !!c, titulos, costoAlto: c.costoAlto === (c.cP >= 1.5 * c.cN), titulo: tarjeta.querySelector('h3').textContent.trim() === tituloPais(c),
                  rojo: tarjeta.classList.contains('cifra-alerta') === (c.comp === "mas"), mas: sube.comp,
                  sinDef: [...new Set(par.map(x => x.causal).filter(Boolean))].filter(k => !defCausa(k)) };
            }""")
            revisar(r3["costoAlto"] and r3["titulos"][0] == "Pocas obras paralizadas, pero de alto costo" and r3["titulos"][1] in ("Obras paralizadas en la proporción del país", "Más obras paralizadas que el país",
                    "Menos obras paralizadas que el país"), f"regla de costo alto: {r3}")
            revisar(r3["ok"] and r3["titulo"] and r3["rojo"] and r3["mas"] == "mas" and not r3["sinDef"], f"obras frente al país y causas: {r3}")
            # Barra del costo de las paralizadas: 5 tramos y el resto suman el total; el tramo abre su nombre y monto
            pg.evaluate("location.hash = '#obras'")
            pg.wait_for_selector("#obras-paneles .barra-costo")
            pg.locator("#obras-paneles .tramo").first.click()
            r6 = pg.evaluate("""() => { const ps = [...document.querySelectorAll('#obras-paneles .tramo')].map(b => +b.style.getPropertyValue('--p'));
                return { n: ps.length, suma: ps.reduce((a, b) => a + b, 0), caja: !$('definicion').hidden && $('definicion').textContent }; }""")
            revisar(r6["n"] == 6 and abs(r6["suma"] - 1) < 1e-3 and str(r6["caja"]).startswith("1. "), f"barra del costo: {r6}")
            pg.keyboard.press("Escape")
            revisar(r2["entidades"] == ["Municipalidad Distrital de La Unión", "Municipalidad Distrital de San Miguel de El Faique",
                                        "Mancomunidad Municipal Simón Rodríguez (MMSR)"], f"nombres de entidades: {r2['entidades']}")
            # Mapas con Leaflet: dibujados, o con su mensaje si el CDN no respondió
            for tab, mapa in (("obras", "mapa-obras"), ("salud", "mapa-salud")):
                pg.evaluate(f"location.hash = '#{tab}'")
                pg.wait_for_function(f"document.querySelector('#{mapa} .leaflet-interactive, #{mapa} .sin-datos')", timeout=20000)
                n = pg.evaluate(f"document.querySelectorAll('#{mapa} path.leaflet-interactive').length")
                revisar(n >= 60 or pg.evaluate(f"!!document.querySelector('#{mapa} .sin-datos')"), f"mapa {mapa}: {n} distritos")
            # Clima: 4 tarjetas con «Más detalle» (salvo el radar: incrustado y con su botón), gráficos dibujados, regla del título
            # del mar, un círculo por estación en el mapa de lluvia, el top 5, y una fuente que falta no rompe la pestaña
            pg.evaluate("location.hash = '#clima'")
            pg.wait_for_selector("#g-tsm svg")
            pg.wait_for_function("document.querySelector('#mapa-lluvia .leaflet-interactive, #mapa-lluvia .sin-datos')", timeout=20000)
            rc = pg.evaluate("""() => {
                const ps = [...document.querySelectorAll('#clima-paneles > .panel')];
                const r = { paneles: ps.length, detalle: document.querySelectorAll('#clima-paneles .ver-mas').length,
                  radar: !!document.querySelector('#clima-paneles a.boton[href*="ecrmm.udep.edu.pe"]') && !!document.querySelector('#clima-paneles img.radar-img')
                    && (() => { const img = document.querySelector('#clima-paneles img.radar-img'); radarFallo(img);  // si el radar falla: aviso y botón
                      return img.closest('figure').hidden && !document.querySelector('#clima-paneles .radar-fallo').hidden; })(),
                  lluvia: document.querySelectorAll('#g-lluvia svg').length, nino: !!document.querySelector('#g-nino12 svg'),
                  estado: document.querySelector('.etiqueta-estado')?.textContent === D.enfen.estado,
                  top5: Math.min(5, D.lluvia.estaciones.filter(x => lluviaDia(x, D.lluvia.fecha_corte) >= INAPRECIABLE).length) === document.querySelectorAll('.lluvia-top b').length,
                  circulos: document.querySelectorAll('#mapa-lluvia path.leaflet-interactive').length >= D.lluvia.estaciones.length,
                  imerg: D.imerg ? true : /no cargó/i.test(document.getElementById('nota-imerg').textContent),
                  clases: [claseLluvia(0.5), claseLluvia(1), claseLluvia(49.9), claseLluvia(50)],
                  titulos: [tsmTitulo(0.4), tsmTitulo(8.03), tsmTitulo(-1.2)],
                  // temperatura (ronda 18): después del mar y antes del radar, con su gráfico de 4 líneas y la nota de reanálisis
                  temp: (() => { const cl = ps.map(p => [...p.classList].find(c => c.startsWith('clima-')));
                    return cl.indexOf('clima-temp') === cl.indexOf('clima-mar') + 1 && cl.indexOf('clima-rios') < cl.indexOf('clima-radar')
                      && document.querySelectorAll('#g-temp polyline').length === 4
                      && /Reanálisis, no estación/.test(document.querySelector('.clima-temp').textContent)
                      && /a esta fecha de 1997 estaba/.test(document.querySelector('.clima-temp h3').textContent); })() };
                const guardado = D.tsm; D.tsm = null; pintarClima();
                r.sinTsm = document.querySelectorAll('#clima-paneles .pendiente').length === 1;
                D.tsm = guardado; pintarClima(); graficosClima();
                return r; }""")
            revisar(rc == {"paneles": 7, "detalle": 4, "radar": True, "lluvia": 3, "nino": True, "estado": True, "top5": True, "circulos": True,
                           "imerg": True, "clases": [-1, 0, 3, 4], "sinTsm": True, "temp": True,
                           "titulos": ["El mar frente a Paita está cerca de lo normal", "El mar frente a Paita está 8,0 °C más caliente que lo normal",
                                       "El mar frente a Paita está 1,2 °C más frío que lo normal"]}, f"pestaña Clima: {rc}")
            # Lluvia, una sola fecha (ronda 17): para cada estación, la última barra de su serie (globo) tiene el mismo día y los
            # mismos mm que su círculo en el mapa diario; 0 mm lleva marca; la escala común se corta en 60 mm con el valor encima;
            # fechas cada 7 días; un selector con todas las estaciones en cada gráfico
            pg.wait_for_function("document.querySelector('#mapa-lluvia .leaflet-interactive')", timeout=20000)
            rl = pg.evaluate("""async () => {
                const l = D.lluvia, m = await mapaLluviaP, enMapa = {}, dia = diaLluvia(l.fecha_corte), malas = [];
                m.eachLayer(c => { if (c instanceof L.CircleMarker && c.getTooltip()) { const t = c.getTooltip().getContent();
                  enMapa[t.match(/<strong>(.*?)<\\/strong>/)[1]] = t.split('Medido en estación: ')[1]; } });
                for (const x of l.estaciones) {
                  seriesLluvia[0] = x.cod; graficosLluvia();
                  const g = document.querySelector('#g-lluvia .grafico'), zona = g.querySelector('.zona'), z = zona.getBoundingClientRect();
                  zona.dispatchEvent(new PointerEvent('pointermove', { clientX: z.right - 1, clientY: z.top + 5, bubbles: true }));
                  const globo = g.querySelector('.globo').textContent, mapa = enMapa[esc(lugar(x.nombre))];
                  if (!mapa || !globo.startsWith(dia) || !globo.endsWith(mapa)) malas.push(`${x.nombre}: serie «${globo}», mapa «${mapa}»`);
                }
                seriesLluvia = [...l.series]; graficosLluvia();
                const ceros = [...document.querySelectorAll('#g-lluvia .grafico')].every((g, j) => {
                  const x = l.estaciones.find(e => e.cod === seriesLluvia[j]);
                  return g.querySelectorAll('rect[height="2"]').length === diasLluvia(l).filter(d => lluviaDia(x, d) === 0).length; });
                const div = document.createElement('div'); div.style.width = '300px'; document.body.append(div);
                graficoMeses(div, diasLluvia(l), [{ nombre: 'Lluvia', color: 'red', v: Array(29).fill(1).concat(100) }], 'barras',
                  { dias: true, cada: 7, hi: 60, recorte: true, alto: 170, fmt: mm });
                const r = { malas, ceros, sub: document.querySelector('#clima-paneles .clima-lluvia').textContent.includes('Lluvia del ' + dia),
                  tope: div.querySelector('text.rotulo')?.textContent === '100',
                  fechas: [...div.querySelectorAll('text')].filter(e => /^\\d\\d\\/\\d\\d$/.test(e.textContent)).length,
                  selectores: [...document.querySelectorAll('#g-lluvia select')].map(s => s.options.length),
                  totales: document.querySelectorAll('#g-lluvia .total-ll b').length };
                div.remove();
                return r; }""")
            n_est = pg.evaluate("D.lluvia.estaciones.length")
            revisar(rl == {"malas": [], "ceros": True, "sub": True, "tope": True, "fechas": 5, "selectores": [n_est] * 3, "totales": 3},
                    f"lluvia, serie y mapa con la misma fecha: {rl}")
            # Vulnerabilidad: la base se carga al abrir la pestaña (hexágonos de 350 m); los de 130 m al zoom 15 y las manzanas al 16.
            # 5 clases fijas (servicios y vivienda en palabras); el total de la tabla suma numeradores y denominadores (no promedia);
            # la barra y su frase cubren toda la localidad; la comparación va ordenada, con el promedio de las zonas urbanas
            pg.evaluate("location.hash = '#vulnerabilidad'")
            pg.wait_for_function("document.querySelector('#mapa-vul canvas, #mapa-vul .sin-datos, #vulnerabilidad .pendiente')", timeout=30000)
            rv = pg.evaluate("""async () => {
                const i = vulInd(), t = vulTotal(i.k), filas = [...document.querySelectorAll('#vul-tabla tr')];
                const total = filas.at(-1).querySelector('td.n .casos').textContent.replace(/\\s/g, '');
                const h = D.censo.hexagonos.features[0], conA = a => ({ properties: { ...h.properties, a } });
                return { canvas: !!document.querySelector('#mapa-vul canvas'), leyenda: document.querySelectorAll('#vul-leyenda .grilla-clases li').length + document.querySelectorAll('#vul-leyenda .lista-clases li').length,
                  barra: Math.round([...document.querySelectorAll('#vul-leyenda .barra-clases span')].reduce((s, x) => s + +x.style.getPropertyValue('--p'), 0)),
                  sinManzanas: !vulDatos.metro.mz && !vulDatos.metro.h10,  // no se descargan hasta acercar el mapa
                  filas: filas.length, total: total === (num(t[0]) + 'de' + num(t[1])).replace(/\\s/g, ''),
                  // sin desagüe, escala fija 5, 20, 50, 80: 4,9 % en la 1.ª clase, 5 % en la 2.ª, 50 % en la 4.ª, 100 % en la 5.ª
                  clases: [[4.9, 100], [5, 100], [50, 100], [100, 100]].map(a => [...TONOS_V.map(token)].indexOf(hexEstilo(conA(a)).fillColor)),
                  rotulos: [etiquetasVul(i).at(-1), rangosVul(i).at(-1), rangosVul(i)[0], rangosVul({ cortes: [4, 8, 12, 16] }).at(-1), rangosVul({ cortes: [4, 8, 12, 16] })[0]],
                  // los % de la leyenda suman 100 (mayor resto) y una clase con casos que redondea a 0 dice «menos de 1 %»
                  enteros: [enteros100([1, 1, 1]), enteros100([0.2, 50, 49.8, 0, 0]), pctClase(0, 3), pctClase(0, 0)].map(String),
                  suma100: [...document.querySelectorAll('#vul-leyenda .grilla-clases b')].reduce((s, b) => s + (parseInt(b.textContent) || 0), 0),
                  fraseBarra: document.querySelector('#vul-leyenda .frase-barra').textContent.startsWith('De cada 100 viviendas de la ciudad de Piura, '),
                  comparacion: (() => { const fs = [...document.querySelectorAll('#vul-localidades .fila-loc')], ps = fs.map(f => +f.querySelector('.barra').style.getPropertyValue('--p'));
                    const ls = D.censo.localidades, prom = pct(ls.reduce((s, x) => s + x.a[0], 0), ls.reduce((s, x) => s + x.a[1], 0));
                    return fs.length === ls.length && ps.every((p, j) => !j || ps[j - 1] >= p) && fs.filter(f => f.classList.contains('sel')).length === 1
                      && Math.abs($('vul-localidades').style.getPropertyValue('--prom') - prom) < 1e-9
                      && /en número, la mayoría está en la ciudad de Piura/.test($('vul-comp-titular').textContent); })(),
                  borde: hexEstilo(conA([0, 100])).weight > 0 && hexEstilo(conA([0, 100])).fillOpacity === 1,
                  multiplicar: getComputedStyle(document.querySelector('#mapa-vul .leaflet-tile-pane')).mixBlendMode,
                  hex30: hexVisibles().features.every(x => x.properties[vulInd().k][1] >= 30),
                  // una fila de casas por distrito, de mayor a menor %, con 10 casas y su texto alternativo; sin la línea del total
                  frases: (() => { const fs = [...document.querySelectorAll('#vul-frases .fila-casas')], ds = Object.values(D.censo.distritos);
                    const ps = fs.map(f => +f.querySelector('p').textContent.match(/\\(([\\d,]+) %\\)/)[1].replace(',', '.'));
                    return fs.length === ds.length && ds.every(x => fs.some(f => f.querySelector('p').textContent.startsWith(lugar(x.nombre) + ':')))
                      && ps.every((p, j) => !j || ps[j - 1] >= p) && fs.every(f => { const s = f.querySelector('svg');
                        return s.getAttribute('role') === 'img' && s.getAttribute('aria-label') + '.' === f.querySelector('p').textContent
                          && s.getAttribute('focusable') === 'false' && s.querySelectorAll('g path').length === 10; })
                      && !/En toda/.test($('vul-frases').textContent); })(),
                  decimos: [decimos(31.9), decimos(3), decimos(98.1), decimos(100), decimos(12)].map(x => x.join('|')),
                  // los 5 sectores: más de la mitad afectada, de mayor a menor número, con su barra y su cifra
                  criticos: (() => { const ids = [...document.querySelectorAll('#vul-criticos [data-hex]')].map(b => b.dataset.hex);
                    const hs = ids.map(id => D.censo.hexagonos.features.find(x => x.id === id).properties[i.k]);
                    return ids.length === 5 && hs.every(x => x[0] > x[1] / 2) && hs.every((x, j) => !j || hs[j - 1][0] >= x[0])
                      && document.querySelectorAll('#vul-criticos .barra-crit').length === 5
                      && /sectores más críticos están en/.test($('vul-criticos-titulo').textContent)
                      && /^Sectores donde más de la mitad de las viviendas no tienen desagüe/.test($('vul-criticos-sub').textContent); })(),
                  proporcion: [proporcion(26.7), proporcion(62), proporcion(97)].map(x => x.join('|')) };
            }""")
            revisar(rv == {"canvas": True, "leyenda": 10, "barra": 100, "sinManzanas": True, "filas": 4, "total": True, "clases": [0, 1, 3, 4],
                           "rotulos": ["Casi todas", "80–100 %", "0–5 %", "16 % o más", "menos de 4 %"],
                           "enteros": ["34,33,33", "0,50,50,0,0", "menos de 1 %", "0 %"], "suma100": 100, "fraseBarra": True, "comparacion": True, "borde": True, "multiplicar": "multiply",
                           "hex30": True, "frases": True, "criticos": True,
                           "decimos": ["3 de cada 10|true", "menos de 1 de cada 10|false", "casi 10 de cada 10|true", "10 de cada 10|true", "1 de cada 10|false"], "proporcion": ["1 de cada 4|false", "6 de cada 10|true", "casi todas las|true"]},
                    f"pestaña Vulnerabilidad: {rv}")
            # Zoom 15: hexágonos de 130 m (mínimo 20); zoom 16: manzanas (denominador 0 no se dibuja, extensas sin relleno, gris con
            # pocos casos); vista de número: densidad por hectárea de manzana en el mismo nivel; localidades sin el nivel de 130 m
            rz = pg.evaluate("""async () => { const m = await vulP, espera = ms => new Promise(r => setTimeout(r, ms));
                m.setZoom(15); await espera(300); await vulNivel(m);
                const h10 = m.hasLayer(vulCapas.h10) && !m.hasLayer(vulCapas.h9) && visibles('h10').features.every(x => x.properties[vulInd().k][1] >= 20);
                m.setZoom(16); await espera(300); await vulNivel(m);
                const mz = m.hasLayer(vulCapas.mz) && !m.hasLayer(vulCapas.h10), f = vulDatos.metro.mz.features;
                const g = f.find(x => !x.properties.km2), gris = { properties: { ...g.properties, a: [1, 3] } };
                const r = { h10, mz, sinCero: visibles('mz').features.every(x => x.properties[vulInd().k][1] > 0) && visibles('mz').features.length < f.length,
                  extensa: vulEstilo(f.find(x => x.properties.km2)).fill === false, gris: vulEstilo(gris).fillColor === token('--neutro'),
                  globo: vulGlobo({ ...gris, id: 'X' }).includes('pocos casos') && !vulGlobo({ ...gris, id: 'X' }).includes('%') };
                $('f-vista-vul').value = 'num'; $('f-vista-vul').dispatchEvent(new Event('change')); await espera(300); await vulNivel(m);
                r.num = m.hasLayer(vulCapas.mz) && !m.hasLayer(vulCapas.h9) && vulGlobo(g).includes('por hectárea de manzana');
                $('f-vista-vul').value = 'pct'; $('f-vista-vul').dispatchEvent(new Event('change'));
                const conHa = (n, ha) => ({ properties: { a: [n, 100], ha } }), ia = { k: 'a', densidad: [5, 10, 20, 40] };
                r.claseNum = [claseNum(ia, conHa(4.9, 1)), claseNum(ia, conHa(10, 2)), claseNum(ia, conHa(400, 2)), claseNum(ia, conHa(5, 0))];
                // clic en el primer sector crítico: zoom 14, borde de resalte y su globo abierto
                await vulNivel(m); document.querySelector('#vul-criticos button').click(); await espera(600);
                const abierto = !!vulCapas.globo && m.hasLayer(vulCapas.globo) && vulCapas.globo.getContent().includes(vulGlobo(D.censo.hexagonos.features.find(x => x.id === document.querySelector('#vul-criticos button').dataset.hex)).slice(0, 30));
                r.clic = !!vulCapas.resalte && m.hasLayer(vulCapas.resalte) && m.getZoom() === 14 && abierto;
                // Otra localidad: se carga su archivo, la tabla la marca, las frases la nombran y se ve un solo nivel; el resalte se va
                $('f-loc').value = 'catacaos'; await cambiarLoc(); await espera(300);
                r.loc = !!vulDatos.catacaos?.h9 && document.querySelector('#vul-localidades .fila-loc.sel')?.textContent.includes('Catacaos')
                  && document.querySelector('#vul-frases .fila-casas p').textContent.startsWith('Catacaos:')
                  && document.querySelectorAll('#vul-frases .fila-casas').length === 2 && !vulCapas.resalte
                  && document.querySelector('#vul-leyenda .frase-barra').textContent.includes('de Catacaos')
                  && ['h9', 'h10', 'mz'].filter(n => vulCapas[n] && m.hasLayer(vulCapas[n])).length === 1;
                m.setZoom(15); await espera(300); await vulNivel(m);
                r.sin130 = m.hasLayer(vulCapas.mz) && !vulCapas.h10 && !vulDatos.catacaos.h10;
                $('f-loc').value = 'metro'; await cambiarLoc();
                return r; }""")
            revisar(rz == {"h10": True, "mz": True, "sinCero": True, "extensa": True, "gris": True, "globo": True, "num": True, "claseNum": [0, 1, 4, 0], "loc": True, "sin130": True, "clic": True},
                    f"vulnerabilidad, zoom y vista: {rz}")
            revisar(r["sal"] == r["esperado"] and r["regla"] and r["desfasada"],
                    f"título de salud «{r['sal']}», esperado «{r['esperado']}», regla {r['regla']}, serie desfasada {r['desfasada']}")
            pg.close()
            # Aviso de datos viejos: con el reloj 60 días adelante deben aparecer avisos
            pg = nav.new_page()
            pg.clock.set_fixed_time(datetime.now() + timedelta(days=60))
            pg.goto(base + "#resumen")
            pg.wait_for_function("document.querySelectorAll('#resumen-paneles .panel').length >= 5", timeout=15000)
            n = pg.evaluate("document.querySelectorAll('#resumen-paneles .vencido').length")
            revisar(n >= 3, f"con 60 días de retraso simulado se ven {n} avisos 'Dato no actualizado' en el resumen")
            nav.close()
    finally:
        srv.terminate()
    if fallos:
        print("FALLA:\n  " + "\n  ".join(fallos))
        sys.exit(1)
    print(f"OK: {len(PESTANAS)} pestañas a 1280 y 375 px, enlace antiguo, año de Dengue, rótulos del gráfico, pestañas, compartir, títulos de la portada, regla del dengue, semáforo, mapas y aviso de datos viejos")


if __name__ == "__main__":
    main()

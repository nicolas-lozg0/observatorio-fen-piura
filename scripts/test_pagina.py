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
  - que los 6 títulos de la portada tengan texto (ronda 20: tarjeta de El Niño, Vulnerabilidad y orden de la grilla) y que el de salud cuadre con el mes de su cifra y su comparación;
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
                        // la lista de fuentes crece con cada fuente nueva: no es una tabla de datos larga
                        const tablas = [...s.querySelectorAll('table')].filter(tb => !tb.closest('details') && !tb.querySelector('#fuentes-cuerpo'))
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
                # Precios de alimentos (SISAP): una fila por alimento, rayas según «Comparar con», cifras sin encimarse ni salirse
                pg.evaluate("location.hash = '#precios'")
                pg.wait_for_timeout(500)
                r = pg.evaluate("""() => {
                    const g = () => document.querySelector('#g-alim svg'), elegir = (id, v) => { const s = document.getElementById(id);
                        s.value = v; s.dispatchEvent(new Event('change')); };
                    // rayas de lo habitual (sin contar la línea punteada que une la raya con la barra)
                    const rayas = () => g().querySelectorAll('.alim-fila line:not([stroke-dasharray])').length, w = () => g().viewBox.baseVal.width;
                    const cajas = () => [...g().querySelectorAll('text')].map(t => { const b = t.getBBox();
                        return { t: t.textContent, x0: b.x, y0: b.y, x1: b.x + b.width, y1: b.y + b.height }; });
                    const c = cajas(), choques = c.flatMap((a, i) => c.slice(i + 1).filter(b => a.x0 < b.x1 - 1 && b.x0 < a.x1 - 1
                        && a.y0 < b.y1 - 1 && b.y0 < a.y1 - 1).map(b => a.t + ' / ' + b.t));
                    const out = { filas: g().querySelectorAll('.alim-fila').length, n: D.sisap.productos.length, choques,
                        fuera: c.filter(a => a.x0 < -1 || a.x1 > w() + 1).map(a => a.t), habitual: rayas(),
                        esperadas: D.sisap.productos.filter(p => p.mayorista.habitual != null).length,
                        // fuera de lo habitual: nombre en negrita y línea punteada, los mismos que dice el titular
                        negritas: g().querySelectorAll('.alim-fila.fuera').length, punteadas: g().querySelectorAll('.alim-fila line[stroke-dasharray]').length,
                        fuera_dato: D.sisap.productos.filter(p => fueraHabitual(p.mayorista)).length,
                        // leyenda: 2 cuadrados (barras) y 1 raya
                        cajas_ley: document.querySelectorAll('#panel-alim .leyenda .caja').length, raya_ley: !!document.querySelector('#panel-alim .leyenda .raya'),
                        tit: document.getElementById('alim-tit').textContent };
                    // simbología simple (24/11/2026): sin * ni † en los nombres; orden de la pestaña: mercados, inflación (un solo bloque
                    // con selector) y canasta; la tarjeta del Resumen da los mercados primero
                    out.simbolos = ![...g().querySelectorAll('.alim-fila .nombre')].some(t => /[*†]/.test(t.textContent));
                    const orden = [...document.querySelectorAll('#precios-paneles > .panel')].map(x => x.id || x.querySelector('h3').textContent.slice(0, 12));
                    out.orden = orden[0] === 'panel-alim' && orden[1] === 'panel-ipc' && orden.length === 3;
                    out.ipc = document.querySelectorAll('#panel-ipc .grafico').length === 1 && !!$('f-ipc-graf')
                      && document.querySelectorAll('#panel-ipc .cifras-ipc .cifra').length === 2;
                    elegir('f-ipc-graf', 'mensual'); out.ipcMensual = !!document.querySelector('#g-ipc rect'); elegir('f-ipc-graf', 'anual');
                    out.resumen = [...document.querySelectorAll('#resumen-paneles .panel h3')].some(h => /^Subieron [0-9]+ de [0-9]+ alimentos/.test(h.textContent));
                    // cifra promedio sobre el gráfico y la misma en la tarjeta del Resumen
                    const m = D.sisap.promedio.mayorista, prom = $('alim-prom').textContent;
                    const tarjeta = [...document.querySelectorAll('#resumen-paneles .panel')].find(p => /^Subieron/.test(p.querySelector('h3')?.textContent || ''));
                    out.promedio = /^En promedio, los alimentos (subieron|bajaron|no variaron)/.test(prom) && prom.includes(signo(m.habitual))
                      && tarjeta?.querySelector('.cifra')?.textContent.trim() === signo(m.var) && $('alim-prom-n').textContent.includes(`${m.n} alimentos`);
                    elegir('f-alim-orden', 'dif');
                    const prim = g().querySelector('.alim-fila .nombre').textContent.replace(/[*†]/g, ''), difs = D.sisap.productos
                        .filter(p => p.mayorista.habitual != null && p.mayorista.var != null).sort((a, b) => (b.mayorista.var - b.mayorista.habitual) - (a.mayorista.var - a.mayorista.habitual));
                    out.orden = prim === difs[0].nombre; elegir('f-alim-orden', 'var');
                    elegir('f-alim-comp', ''); out.sin = rayas();
                    elegir('f-alim-tipo', 'minorista'); out.frase = document.getElementById('alim-tit').textContent;
                    out.tabla = document.querySelector('#tabla-alim caption').textContent.includes('minoristas');
                    elegir('f-alim-tipo', 'mayorista'); elegir('f-alim-comp', 'habitual');
                    return out; }""")
                revisar(r["promedio"] and r["simbolos"] and r["orden"] and r["ipc"] and r["ipcMensual"] and r["resumen"] and r["filas"] == r["n"] >= 19 and r["habitual"] == r["esperadas"] and r["sin"] == 0
                        and r["negritas"] == r["punteadas"] == r["fuera_dato"] and r["cajas_ley"] == 2 and r["raya_ley"] and r["orden"]
                        and r["tit"].startswith("Entre la 2.ª quincena") and "mayoristas" in r["tit"]
                        and "minoristas" in r["frase"] and r["tabla"] and not r["choques"] and not r["fuera"],
                        f"{ancho}px precios de alimentos: {r}")
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
                // ronda 20: tarjeta de El Niño (estado, mar y aire en 3 columnas, línea de ríos, enlace y pie con fuentes)
                const np = document.querySelector('#hoy .nino-portada'), cifras = np ? [...np.querySelectorAll('.nino-col .cifra')].map(c => c.textContent.replace(/\\s/g, ' ')) : [];
                const franja = !!np && np.querySelector('.etiqueta-estado')?.textContent === D.enfen.estado && np.querySelectorAll('.nino-col').length === 3
                  && cifras[0] === conSigno(anomMar()[2]) + ' °C' && cifras[1] === conSigno(D.temp.anomalia_7d.actual) + ' °C'
                  && !!np.querySelector('a[href="#clima"]') && /ENFEN[^]*NOAA[^]*Open-Meteo[^]*Senamhi/.test(np.querySelector('.pie').textContent)
                  && RIOS.every(x => np.querySelector('.rios-nino').innerHTML.includes(fraseRio(x).corto));
                // Vulnerabilidad: tarjeta normal con la proporción en el titular, la cifra, 10 casas y el distrito con el mayor %
                const vp = document.querySelector('#resumen-paneles .vul-portada');
                const fracciones = [26.7, 33.3, 31, 60, 12.5, 50].map(fraccionTxt).join('|');
                const vul = !!vp && vp.querySelectorAll('svg.casas .base path').length === 10
                  && vp.querySelector('h3').textContent === 'Más de 1 de cada 4 viviendas de la ciudad de Piura no tiene desagüe'
                  && vp.querySelector('.cifra').textContent === '39.607' && /En Castilla llega a 31,9/.test(vp.textContent)
                  && !!vp.querySelector('a[href="#vulnerabilidad"]')
                  && fracciones === 'Más de 1 de cada 4|1 de cada 3|Casi 1 de cada 3|6 de cada 10|1 de cada 8|1 de cada 2';
                // orden de la grilla: lo que pesa en una emergencia primero
                const orden = [...document.querySelectorAll('#resumen-paneles .panel > a.ver-mas')].map(a => a.getAttribute('href')).join(',');
                const ordenOk = orden === '#dengue,#salud,#vulnerabilidad,#gasto,#obras,#precios';
                // ríos: un aviso naranja o rojo vuelve la línea una alerta destacada; uno amarillo, no
                const guardado = D.rios.avisos, hoyIso = new Date(Date.now() - 5 * 36e5).toISOString().slice(0, 10);
                const av = n => ({ numero: 9999, titulo: 'INCREMENTO DEL CAUDAL DEL RÍO ALAMOR - ESTACIÓN ALAMOR', rio: 'ALAMOR',
                  estacion: 'ALAMOR', cuenca: 'Chira', inicio: hoyIso, fin: hoyIso, horas: 2, nivel: n, vigente: true });
                D.rios.avisos = [av('AMARILLO')]; const conAmarillo = /alerta-rios/.test(tarjetaNino());
                D.rios.avisos = [av('NARANJA')]; const conNaranja = /alerta-rios naranja[^]*<strong>[^]*aviso naranja por el río Alamor/.test(tarjetaNino())
                  && /frase-rio grave[^]*está creciendo el río Alamor, que desemboca en el Chira/.test(fraseRio(RIOS[1]).html);
                D.rios.avisos = guardado;
                const rios = !conAmarillo && conNaranja && ordenOk;
                return { t, sal, esperado, regla, desfasada, franja, vul, rios };
            }""")
            revisar(r["franja"] and r["vul"] and r["rios"], f"portada: tarjeta de El Niño {r['franja']}, tarjeta de Vulnerabilidad {r['vul']}, ríos y orden {r['rios']}")
            revisar(len(r["t"]) == 6 and all(r["t"]), f"títulos de la portada: {r['t']}")
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
            r5 = pg.evaluate("""() => { const t = document.querySelector('#resumen-paneles a[href="#obras"]').closest('.panel').querySelector('.cifra').textContent;
                const act = D.obras.obras.filter(x => !APARTE[x.codigo_infobras]);
                return { cifra: t.trim() === String(act.filter(x => x.estado === "Paralizada").length),
                  reactivadas: act.filter(reactivada).map(x => x.codigo_infobras).sort() }; }""")
            revisar(r5["cifra"] and r5["reactivadas"] == ["114837", "88999"], f"obras revisadas a mano: {r5}")
            # Obras frente al país: título y color siguen la regla de 1 punto; cada causa de Piura tiene definición
            r3 = pg.evaluate("""() => {
                const act = D.obras.obras.filter(x => !APARTE[x.codigo_infobras]), par = act.filter(x => x.estado === "Paralizada");
                const c = obrasPais(act, par), tarjeta = document.querySelector('#resumen-paneles a[href="#obras"]').closest('.panel');
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
                      && !!document.querySelector('#g-temp polygon[fill="var(--calor)"]')
                      && document.querySelector('.clima-temp .cifra').textContent.trim() === conSigno(D.temp.anomalia_7d.actual) + ' °C'
                      && document.querySelector('.clima-temp h3').textContent === tituloTemp(D.temp.anomalia_7d.actual)
                      && /para esta época/.test(tituloTemp(D.temp.anomalia_7d.actual)) && !/1997|2016/.test(document.querySelector('.clima-temp h3').textContent)
                      && /lo normal es/.test(document.querySelector('.clima-temp .ud').textContent)
                      && /^Fuente: reanálisis ERA5-Land y modelo de pronóstico/.test(document.querySelector('.clima-temp .pie').textContent.trim())
                      && document.querySelectorAll('#g-temp .rotulo').length === 1
                      && document.querySelectorAll('.clima-rios .rio').length === 2 && document.querySelectorAll('.clima-rios .aviso').length === 2
                      && document.querySelectorAll('.clima-rios .grafico polygon').length === 2; })(),
                  // ríos (ronda 20): la frase de Clima es la misma que resume el Resumen; nada técnico en el cuerpo
                  riosIgual: RIOS.every(x => document.querySelector(`#g-rio-${x.cod}`).closest('.rio').querySelector('.frase-rio').outerHTML === fraseRio(x).html),
                  riosCuerpo: !/no caudal|COER|1100/.test([...document.querySelector('.clima-rios').children].filter(c => !c.matches('.calculo')).map(c => c.textContent).join(' ')),
                  // mismas cifras en Clima y Resumen: aire (anomalía de 7 días) y mar (anomalía del último día)
                  igual: document.querySelector('.clima-temp .cifra').textContent.trim().replace(/\\s/g, ' ') === document.querySelectorAll('.nino-portada .nino-col .cifra')[1].textContent.replace(/\\s/g, ' ')
                      && document.querySelector('.clima-mar .ud').textContent.replace(/\\s/g, ' ').includes(document.querySelectorAll('.nino-portada .nino-col .cifra')[0].textContent.replace(/\\s/g, ' ')),
                  tendencias: (() => { const s = (vs, h0 = 0) => vs.map((v, i) => [`2026-11-17T${String(h0 + i).padStart(2, '0')}:00`, v]);
                    return [tendenciaRio(s([1, 1, 1, 1, 1, 1, 1.1])), tendenciaRio(s([1, 1, 1, 1, 1, 1, 0.9])), tendenciaRio(s([1, 1, 1, 1, 1, 1, 1.03])),
                      tendenciaRio(s([1, 1.1, 1.3, 1.2, 1.1, 1, 1], 2)), tendenciaRio(s([1, 1, 1]))].map(x => x ? x.txt : null).join('|'); })() };
                const guardado = D.tsm; D.tsm = null; pintarClima();
                r.sinTsm = document.querySelectorAll('#clima-paneles .pendiente').length === 1;
                D.tsm = guardado; pintarClima(); graficosClima();
                return r; }""")
            revisar(rc == {"paneles": 7, "detalle": 4, "radar": True, "lluvia": 3, "nino": True, "estado": True, "top5": True, "circulos": True,
                           "imerg": True, "clases": [-1, 0, 3, 4], "sinTsm": True, "temp": True, "riosIgual": True, "riosCuerpo": True, "igual": True,
                           "tendencias": "está subiendo|viene bajando|está estable|subió de madrugada y ya está bajando|",
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
                return { canvas: !!document.querySelector('#mapa-vul canvas'), leyenda: document.querySelectorAll('#vul-reparto .grilla-clases li').length + document.querySelectorAll('#vul-reparto .lista-clases li').length,
                  barra: Math.round([...document.querySelectorAll('#vul-reparto .barra-clases span')].reduce((s, x) => s + +x.style.getPropertyValue('--p'), 0)),
                  sinManzanas: !vulDatos.metro.mz && !vulDatos.metro.h10,  // no se descargan hasta acercar el mapa
                  filas: filas.length, total: total === (num(t[0]) + 'de' + num(t[1])).replace(/\\s/g, ''),
                  // sin desagüe, escala fija 5, 20, 50, 80: 4,9 % en la 1.ª clase, 5 % en la 2.ª, 50 % en la 4.ª, 100 % en la 5.ª
                  clases: [[4.9, 100], [5, 100], [50, 100], [100, 100]].map(a => [...TONOS_V.map(token)].indexOf(hexEstilo(conA(a)).fillColor)),
                  rotulos: [etiquetasVul(i).at(-1), rangosVul(i).at(-1), rangosVul(i)[0], rangosVul({ cortes: [4, 8, 12, 16] }).at(-1), rangosVul({ cortes: [4, 8, 12, 16] })[0]],
                  // los % de la leyenda suman 100 (mayor resto) y una clase con casos que redondea a 0 dice «menos de 1 %»
                  enteros: [enteros100([1, 1, 1]), enteros100([0.2, 50, 49.8, 0, 0]), pctClase(0, 3), pctClase(0, 0)].map(String),
                  suma100: [...document.querySelectorAll('#vul-reparto .grilla-clases b')].reduce((s, b) => s + (parseInt(b.textContent) || 0), 0),
                  fraseBarra: document.querySelector('#vul-reparto .frase-barra').textContent.startsWith('De cada 100 viviendas de la ciudad de Piura, '),
                  // barras pareadas: una fila por localidad, de mayor a menor %, la elegida marcada y el promedio en la nota
                  comparacion: (() => { const fs = [...document.querySelectorAll('#vul-localidades .par')], ps = fs.map(f => +f.dataset.p);
                    const ls = D.censo.localidades, prom = pct(ls.reduce((s, x) => s + x.a[0], 0), ls.reduce((s, x) => s + x.a[1], 0));
                    return fs.length === ls.length && ps.every((p, j) => !j || ps[j - 1] >= p) && fs.filter(f => f.classList.contains('sel')).length === 1
                      && fs.every(f => f.querySelectorAll('.par-barra').length === 2 && /\\d viviendas/.test(f.querySelector('small').textContent))
                      && $('vul-prom').textContent.includes(pctTxt(prom)) && !$('vul-detallado').open; })(),
                  borde: hexEstilo(conA([0, 100])).weight > 0 && hexEstilo(conA([0, 100])).fillOpacity === 1,
                  multiplicar: getComputedStyle(document.querySelector('#mapa-vul .leaflet-tile-pane')).mixBlendMode,
                  hex30: hexVisibles().features.every(x => x.properties[vulInd().k][1] >= 30),
                  // una fila de casas por distrito, de mayor a menor %, con 10 casas y su texto alternativo; sin la línea del total
                  frases: (() => { const fs = [...document.querySelectorAll('#vul-frases .fila-casas')], ds = Object.values(D.censo.distritos);
                    const ps = fs.map(f => +f.querySelector('p').textContent.match(/\\(([\\d,]+) %\\)/)[1].replace(',', '.'));
                    return fs.length === ds.length && ds.every(x => fs.some(f => f.querySelector('p').textContent.startsWith(lugar(x.nombre) + ':')))
                      && ps.every((p, j) => !j || ps[j - 1] >= p) && fs.every(f => { const s = f.querySelector('svg');
                        return s.getAttribute('role') === 'img' && s.getAttribute('aria-label') + '.' === f.querySelector('p').textContent
                          && s.getAttribute('focusable') === 'false' && s.querySelectorAll('.base path').length === 10; })
                      && !/En toda/.test($('vul-frases').textContent); })(),
                  decimos: [decimos(31.9), decimos(3), decimos(98.1), decimos(100), decimos(12)].map(x => x.join('|')),
                  // los 5 sectores: más de la mitad afectada, de mayor a menor número, con su barra y su cifra
                  criticos: (() => { const ids = [...document.querySelectorAll('#vul-criticos [data-hex]')].map(b => b.dataset.hex);
                    const hs = ids.map(id => D.censo.hexagonos.features.find(x => x.id === id).properties[i.k]);
                    return ids.length === 5 && hs.every(x => x[0] > x[1] / 2 && x[1] >= 30) && hs.every((x, j) => !j || hs[j - 1][0] >= x[0])
                      && document.querySelectorAll('#vul-criticos .barra-crit').length === 5
                      && /^Sectores con más viviendas sin desagüe por red pública/.test($('vul-criticos-titulo').textContent)
                      && /^Sectores de 350 m con al menos 30 viviendas donde más de la mitad de las viviendas no tienen desagüe/.test($('vul-criticos-sub').textContent); })(),
                  proporcion: [proporcion(26.7), proporcion(62), proporcion(97)].map(x => x.join('|')) };
            }""")
            revisar(rv == {"canvas": True, "leyenda": 10, "barra": 100, "sinManzanas": True, "filas": 4, "total": True, "clases": [0, 1, 3, 4],
                           "rotulos": ["Casi todas", "80–100 %", "0–5 %", "16 % o más", "menos de 4 %"],
                           "enteros": ["34,33,33", "0,50,50,0,0", "menos de 1 %", "0 %"], "suma100": 100, "fraseBarra": True, "comparacion": True, "borde": True, "multiplicar": "multiply",
                           "hex30": True, "frases": True, "criticos": True,
                           "decimos": ["3 de cada 10|true", "menos de 1 de cada 10|false", "casi 10 de cada 10|true", "10 de cada 10|true", "1 de cada 10|false"], "proporcion": ["1 de cada 4|false", "6 de cada 10|true", "casi todas las|true"]},
                    f"pestaña Vulnerabilidad: {rv}")
            # Lluvia y localidades (coherencia): los puntos del mapa de lluvia, las barras pareadas, la tabla y el gráfico detallado
            # muestran exactamente lo que da datosLocalidades (mismas localidades, mismo %, misma lluvia) con 2017 y con 1998; las
            # filas resaltadas son las del tercio superior de las dos variables. El mapa de lluvia va aparte: el de vivienda no
            # tiene lluvia ni círculos al alejarse; el selector de año (solo años, 2017 al abrir) rige el mapa de lluvia y las barras
            rc = pg.evaluate("""async () => { const m = await vulP, espera = ms => new Promise(r => setTimeout(r, ms));
                for (let k = 0; k < 100 && $('f-lluvia-vul').disabled; k++) await espera(100);
                const ml = await mapaLluviaVulP; for (let k = 0; k < 50 && !ml?._puntos; k++) await espera(100);
                const clave = (id, p, ll) => `${id}|${p}|${ll}`, r = {};
                const desde = sel => [...document.querySelectorAll(sel)].map(e => clave(e.dataset.loc, +e.dataset.p, +e.dataset.ll)).sort().join();
                r.selector = [...$('f-lluvia-vul').options].map(o => o.value).join() + '|' + $('f-lluvia-vul').value;
                for (const anio of ['2017', '1998']) {
                  $('f-lluvia-vul').value = anio; $('f-lluvia-vul').dispatchEvent(new Event('change')); await espera(800);
                  const datos = datosLocalidades(vulInd()), esperado = datos.map(x => clave(x.id, x.p, x.lluvia)).sort().join(), pts = [];
                  ml._puntos.eachLayer(c => pts.push(c.options.loc + '|' + c.options.ll));
                  const dest = destacadas(datos), filasDest = [...document.querySelectorAll('#vul-localidades .par.destacada')].map(f => f.dataset.loc).sort().join();
                  const ciudad = datos.find(x => x.id === 'metro').lluvia;
                  r[anio] = { puntos: pts.sort().join() === datos.map(x => x.id + '|' + x.lluvia).sort().join(), barras: desde('#vul-localidades .par') === esperado,
                    // gráfico de puntos (lluvia de ese año contra el indicador): los mismos puntos que datosLocalidades
                    tabla: desde('#vul-tabla-loc tr') === esperado, grafico: datosPuntos('ll:' + anio, 'c:' + vulInd().k)
                      .map(q => clave(q.id, q.y, q.x)).sort().join() === esperado,
                    conLluvia: datos.every(x => typeof x.lluvia === 'number'), resaltadas: filasDest === [...dest].sort().join(),
                    frase: new RegExp(`^En ${anio} llovió más en .+La ciudad de Piura recibió ${num(ciudad)} mm`).test($('vul-lluvia-frase').textContent.replace(/\\s+/g, ' ')),
                    franjas: document.querySelectorAll('#vul-lluvia-leyenda .franjas-ley span').length, m1983: $('vul-lluvia-1983').hidden };
                }
                // nombres de los puntos del mapa de lluvia sin superponerse
                const et = [...document.querySelectorAll('#mapa-lluvia-vul .nombre-punto-lluvia')].map(e => e.getBoundingClientRect());
                r.nombres = et.length > 0 && et.every((p, a) => et.every((q, b) => a === b || p.right <= q.left + .5 || q.right <= p.left + .5 || p.bottom <= q.top + .5 || q.bottom <= p.top + .5));
                // mapa de vivienda: al alejar siguen los sectores (sin círculos ni lluvia)
                m.setZoom(10); await espera(300); await vulNivel(m);
                r.vivienda = nivelDe(m) === 'h9' && !vulCapas.loc && !m.getPane('lluvia') && m.hasLayer(vulCapas.h9);
                encuadrar(m); await espera(300); await vulNivel(m);
                r.estilos = getComputedStyle(document.querySelector('#vul-localidades .par')).display === 'grid'
                  && getComputedStyle(document.querySelector('#vul-lluvia-leyenda .franjas-ley span'), '::before').width === '14px';
                // cuadrante: por encima del promedio simple en las dos (lluvia 443, % 29): a y b
                const f = (id, lluvia, p) => ({ id, lluvia, p });
                r.tercio = [...destacadas([f('a', 900, 50), f('b', 800, 50), f('c', 800, 10), f('d', 100, 60), f('e', 50, 5), f('f', 10, 1)])].sort().join();
                r.marca = MARCA_DESTACADA(vulInd());
                $('f-orden-loc').value = 'lluvia'; $('f-orden-loc').dispatchEvent(new Event('change'));
                const ll = [...document.querySelectorAll('#vul-localidades .par')].map(e => +e.dataset.ll);
                r.ordenLluvia = ll.every((x, j) => !j || ll[j - 1] >= x);
                const vis = [...document.querySelectorAll('#vul-localidades .par')].filter(e => getComputedStyle(e).display !== 'none');
                r.primeras = vis.length <= 12 && vis.some(e => e.dataset.loc === 'metro') && !$('vul-ver-todas').hidden;
                $('vul-ver-todas').click();
                r.todas = [...document.querySelectorAll('#vul-localidades .par')].every(e => getComputedStyle(e).display !== 'none');
                $('vul-ver-todas').click();
                $('f-orden-loc').value = 'p'; $('f-orden-loc').dispatchEvent(new Event('change'));
                $('f-lluvia-vul').value = '2017'; $('f-lluvia-vul').dispatchEvent(new Event('change')); await espera(300);
                return r; }""")
            ok_anio = {"puntos": True, "barras": True, "tabla": True, "grafico": True, "conLluvia": True, "resaltadas": True, "frase": True,
                       "franjas": 5, "m1983": True}
            revisar(rc == {"selector": "1983,1998,2017,2023|2017", "2017": ok_anio, "1998": ok_anio, "nombres": True, "vivienda": True,
                           "estilos": True, "tercio": "a,b", "marca": "Más lluvia y sin desagüe", "ordenLluvia": True,
                           "primeras": True, "todas": True},
                    f"vulnerabilidad, lluvia y localidades: {rc}")
            # Lluvia y localidades, vista de puntos (25/11/2026): un punto por localidad, ejes guiados (lluvia del mapa × indicador
            # del panel), pregunta guiada que cambia el indicador del panel, cuadrante sombreado, etiquetas sin superponerse,
            # correlaciones en el detalle y la nota de CHIRPS solo con lluvia en un eje; la vista de barras comparte titular y nota
            rx = pg.evaluate("""async () => { const espera = ms => new Promise(r => setTimeout(r, ms)), r = {};
                const tit = $('vul-comp-titular').textContent;
                // la vista de puntos es la principal (por defecto)
                r.vista = $('vista-barras').hidden && !$('vista-puntos').hidden && document.querySelector('.vista-comp [aria-pressed=true]').dataset.vista === 'puntos';
                document.querySelector('.vista-comp [data-vista=puntos]').click(); await espera(300);
                r.vista &&= $('vul-comp-titular').textContent === tit;
                const pts = $('pts-grafico')._pintado.pts;
                r.puntos = document.querySelectorAll('#pts-grafico circle').length === D.censo.localidades.length && pts.length === D.censo.localidades.length;
                // cuadrante sombreado en el tono del indicador; sus puntos en ese color; «promedio» fuera del área de datos
                const P = $('pts-grafico')._pintado;
                r.cuadrante = !!document.querySelector('#pts-grafico rect') && document.querySelectorAll('#pts-grafico .prom').length === 2 && P.tono === '--v4'
                  && [...document.querySelectorAll('#pts-grafico circle')].filter(c => c.getAttribute('fill') === `var(${P.tono})`).length === destacadas(datosLocalidades(vulInd())).size
                  && [...document.querySelectorAll('#pts-grafico .prom-rot')].every(t => { const b = t.getBBox(), a = document.querySelector('#pts-grafico .prom').getBBox(); return b.x >= +document.querySelectorAll('#pts-grafico .prom')[1].getAttribute('x2') || b.y + b.height <= a.y + 1; });
                const et = [...document.querySelectorAll('#pts-grafico .et')].map(e => e.getBoundingClientRect());
                r.etiquetas = et.length > 0 && et.every((p, a) => et.every((q, b) => a === b || p.right <= q.left + .5 || q.right <= p.left + .5 || p.bottom <= q.top + .5 || q.bottom <= p.top + .5));
                r.ejes = !document.querySelector('#pts-grafico text[transform]') && $('pts-grafico').querySelector('.eje-y').textContent.includes('%');
                r.sinCoef = !/[0-9],[0-9]{2}\\b/.test($('vul-comp-titular').textContent) && /Correlación sin ponderar: -?[0-9]/.test($('pts-detalle').textContent)
                  && /ponderada por viviendas/.test($('pts-detalle').textContent) && /ciudad de Piura/.test($('pts-detalle').textContent);
                r.chirps = /CHIRPS/.test($('vul-comp-nota').textContent);
                // pregunta guiada: cambia el indicador del panel (sincronía) y el eje vertical
                $('f-pregunta').value = 'j'; $('f-pregunta').dispatchEvent(new Event('change')); await espera(500);
                r.pregunta = $('f-vul').value === 'j' && $('vul-titulo').textContent === tituloVul(vulInd()) && $('pts-grafico')._pintado.Y.i.k === 'j';
                $('f-vul').value = 'e'; cambiarVul({ target: $('f-vul') }); await espera(300);
                r.otra = $('f-pregunta').value === '' && /Indicador elegido arriba/.test($('f-pregunta').selectedOptions[0].textContent);
                // Personalizar: un par sin lluvia quita la nota de CHIRPS; el color por provincia pone la leyenda en círculos
                $('pts-personalizar').open = true; await espera(100);
                $('f-pts-x').value = 'c:a'; $('f-pts-x').dispatchEvent(new Event('change'));
                $('f-pts-prov').checked = true; $('f-pts-prov').dispatchEvent(new Event('change')); await espera(200);
                r.custom = !/CHIRPS/.test($('vul-comp-nota').textContent) && document.querySelectorAll('#pts-leyenda .circulo').length >= 5;
                $('f-pts-prov').checked = false; $('pts-personalizar').open = false;
                $('f-pregunta').value = 'a'; $('f-pregunta').dispatchEvent(new Event('change')); await espera(300);
                r.vuelve = $('pts-grafico')._pintado.X.lluvia && /CHIRPS/.test($('vul-comp-nota').textContent);
                // correlación: recta creciente = 1, decreciente = −1; el peso cambia el resultado
                const c = (xs, w) => corrPond(xs.map(([x, y, peso]) => ({ x, y, peso })), w);
                r.corr = [c([[1, 2, 1], [2, 4, 1], [3, 6, 5]]), c([[1, 3, 1], [2, 2, 1], [3, 1, 1]])].map(v => v.toFixed(3)).join()
                  + '|' + c([[0, 0, 1], [1, 0, 10], [2, 3, 1]], false).toFixed(3) + ',' + c([[0, 0, 1], [1, 0, 10], [2, 3, 1]]).toFixed(3);
                r.debil = titularRelacion({ lluvia: true, anio: 2017 }, { i: vulInd() }, [{ id: 'a', nombre: 'A', x: 1, y: 1 }, { id: 'b', nombre: 'B', x: 2, y: 3 }, { id: 'c', nombre: 'C', x: 3, y: 3 }, { id: 'd', nombre: 'D', x: 4, y: 1 }], { ids: new Set() }).includes('no hay una relación clara');
                // concordancia del titular en días (masculino plural), horas (femenino plural) y lluvia contra población (femenino)
                const sube = [1, 2, 3, 4].map(k => ({ id: 'q' + k, nombre: 'Q' + k, x: k, y: k })), ind = k => ({ i: D.censo.indicadores.find(x => x.k === k) });
                r.concordancia = /los días sin agua por semana tienden a ser más altos/.test(titularRelacion({ lluvia: true, anio: 2017 }, ind('r'), sube, { ids: new Set() }))
                  && /las horas sin agua por semana tienden a ser más altas/.test(titularRelacion({ lluvia: true, anio: 2017 }, ind('s'), sube, { ids: new Set() }))
                  && /la población tiende a ser más alta/.test(titularRelacion({ lluvia: true, anio: 2017 }, { tot: 'p' }, sube, { ids: new Set() }))
                  && /donde los días sin agua por semana son mayores, el porcentaje de .+ tiende a ser más alto/.test(titularRelacion(ind('r'), ind('a'), sube, { ids: new Set() }));
                // ningún punto se corta en los bordes del gráfico
                const caja = document.querySelector('#pts-grafico svg').getBoundingClientRect();
                r.bordes = [...document.querySelectorAll('#pts-grafico circle')].every(c => { const b = c.getBoundingClientRect(); return b.left >= caja.left && b.right <= caja.right && b.top >= caja.top && b.bottom <= caja.bottom; });
                document.querySelector('.vista-comp [data-vista=barras]').click(); await espera(200);
                r.barras = !$('vista-barras').hidden && $('vista-puntos').hidden;
                return r; }""")
            revisar(rx == {"vista": True, "puntos": True, "cuadrante": True, "etiquetas": True, "ejes": True, "sinCoef": True, "chirps": True,
                           "pregunta": True, "otra": True, "custom": True, "vuelve": True, "corr": "1.000,-1.000|0.866,0.739", "debil": True, "concordancia": True, "bordes": True, "barras": True},
                    f"vulnerabilidad, gráfico de puntos: {rx}")
            # Íconos con un indicador bajo (no sabe leer ni escribir, 2 %): cuadrícula de 100 con su frase y texto alternativo,
            # barras por distrito con la misma escala, sectores ordenados por número con al menos 200 personas y sin «Sector sin nombre»
            rb = pg.evaluate("""async () => { const espera = ms => new Promise(r => setTimeout(r, ms)), r = {};
                $('f-vul').value = 'an'; cambiarVul({ target: $('f-vul') }); await espera(400);
                const g = document.querySelector('#vul-frases .grilla100 svg'), bs = [...document.querySelectorAll('#vul-frases .fila-barra')];
                r.grilla = !!g && g.querySelectorAll('.base path').length === 100 && /de cada 100/.test(g.getAttribute('aria-label'))
                  && g.querySelectorAll('.relleno path').length === (p => Math.floor(p) + (p % 1 >= .25 ? 1 : 0))(pct(...vulTotal('an').slice(0, 2)));
                // tira de puntos: un punto por distrito, la marca de la ciudad, sin barras; etiquetas sin superponerse
                const ets = [...document.querySelectorAll('#vul-tira .et')].map(e => e.getBoundingClientRect());
                r.tira = document.querySelectorAll('#vul-tira circle').length === 3 && !!document.querySelector('#vul-tira .total') && !bs.length
                  && !document.querySelector('#vul-frases .fila-casas') && /de cada 100/.test(document.querySelector('#vul-tira svg').getAttribute('aria-label'))
                  && /^Va de .+ a .+\\.$/.test(document.querySelector('.tira-frase').textContent)
                  && ets.every((p, a) => ets.every((q, b) => a === b || p.right <= q.left + .5 || q.right <= p.left + .5 || p.bottom <= q.top + .5 || q.bottom <= p.top + .5));
                // íconos parciales: recortados (clipPath) en el mismo color, sin opacidad; bajo un cuarto de ícono, nada
                r.parcial = /clipPath/.test(casasSvg(33)) && !/fill-opacity/.test(casasSvg(33)) && !/clipPath/.test(casasSvg(32)) && casasSvg(32).match(/<path/g).length === 13;
                const ids = [...document.querySelectorAll('#vul-criticos [data-hex]')].map(b => b.dataset.hex), hs = ids.map(id => D.censo.hexagonos.features.find(x => x.id === id).properties.an);
                r.sectores = ids.length === 5 && hs.every(x => x[1] >= 200) && hs.every((x, j) => !j || hs[j - 1][0] >= x[0]) && /^Sectores con más personas que no saben leer ni escribir/.test($('vul-criticos-titulo').textContent);
                r.decimos100 = [decimos100(2.04), decimos100(0.3), decimos100(1)].map(x => x.join('|')).join(';');
                r.tope = [topeBarras(2.4), topeBarras(7.1), topeBarras(0.3), topeBarras(10)].join();
                r.sinNombre = !document.body.textContent.includes('Sector sin nombre') && D.censo.hexagonos.features.every(h => h.properties.n);
                $('f-vul').value = 'a'; cambiarVul({ target: $('f-vul') }); await espera(300);
                return r; }""")
            revisar(rb == {"grilla": True, "tira": True, "parcial": True, "sectores": True, "decimos100": "2 de cada 100|true;menos de 1 de cada 100|false;1 de cada 100|false",
                           "tope": "3,10,1,10", "sinNombre": True}, f"vulnerabilidad, íconos con indicador bajo: {rb}")
            # Sincronía: con cada localidad y cada indicador (26 × 23), todos los bloques muestran el mismo indicador y la misma cifra
            # total: título, cifra, frases (con su ícono), leyenda (reparto en servicios; simple en población), mapa (color del
            # grupo), sectores, ayuda, barras pareadas (fila elegida, base en viviendas o personas, orden inicial), tabla y gráfico
            # detallados, y desglose por distrito (solo en la Ciudad de Piura). En población no aparecen «crítico», «problema» ni «afectados»
            rs = pg.evaluate("""async () => { const m = await vulP, espera = ms => new Promise(r => setTimeout(r, ms)), fallas = [];
                for (let k = 0; k < 100 && $('f-lluvia-vul').disabled; k++) await espera(100);
                let combinaciones = 0;
                for (const lc of D.censo.localidades) {
                  $('f-loc').value = lc.id; await cambiarLoc(); await espera(150);
                  for (const ind of D.censo.indicadores) {
                    $('f-vul').value = ind.k; $('f-vul').dispatchEvent(new Event('change')); await espera(60); await vulNivel(m); await espera(40);
                    combinaciones++;
                    // pT: el valor del indicador (% o, en días y horas, el promedio); mag: días u horas (sin íconos ni «de cada 10»)
                    const i = vulInd(), t = vulTotal(i.k), loc = locActual(), metro = vulLoc === 'metro', gr = grupoVul(i), pT = valVul(i, t[0], t[1]), mag = esMag(i);
                    const filasF = [...document.querySelectorAll('#vul-frases .fila-casas')];
                    let capa = vulCapas[nivelDe(m)], l; capa?.eachLayer(x => { l ||= x; });
                    const sel = document.querySelector('#vul-localidades .par.sel');
                    const fila = document.querySelector(`#vul-tabla-loc tr[data-loc="${vulLoc}"]`), punto = datosPuntos('c:' + i.k, 'c:' + i.k).find(q => q.id === vulLoc);
                    const bajo = escala100(i), filasB = [...document.querySelectorAll('#vul-frases .fila-barra')], grilla = document.querySelector('#vul-frases .grilla100');
                    // la línea de detalle (tablas, fuente y «Cómo se calcula», con textos generales) no cuenta
                    const sinPie = (() => { const c = $('vul-lluvia-panel').cloneNode(true); c.querySelectorAll('.vul-pie-linea, #vul-pie, #vul-calculo').forEach(e => e.remove()); return c.textContent; })();
                    const textoPob = ['vul-resumen', 'vul-mapa', 'vul-sectores'].map(id => $(id).textContent).join(' ') + ' ' + sinPie;
                    const ok = {
                      titulo: $('vul-titulo').textContent === tituloVul(i),
                      cifra: $('vul-cifra').textContent.includes(vulPct(i, t)) && $('vul-cifra').textContent.includes(num(mag ? t[1] : t[0])),
                      frases: mag ? filasF.length === (metro ? 3 : 2) && filasF.every(f => f.querySelectorAll('svg.semana text').length === 7 && / a la semana sin agua$/.test(f.querySelector('p').textContent))
                          && (metro || filasF[0].textContent.startsWith(loc.nombre + ':') && filasF[0].textContent.includes(cifraMag(i, pT)))
                        : bajo ? !filasF.length && document.querySelectorAll('#vul-tira circle').length === (metro ? 3 : 1) && grilla?.textContent.includes(pctTxt(pT))
                          && grilla.querySelector('path').getAttribute('d') === (gr.icono === 'persona' ? PERSONA : CASA)
                          && (metro || document.querySelector('#vul-tira .et-total').textContent.startsWith(loc.nombre))
                        : (metro ? filasF.length === 3 : filasF[0]?.querySelector('p').textContent.startsWith(loc.nombre + ':')
                          && filasF[0].querySelector('p').textContent.includes(pctTxt(pT)))
                        && filasF.every(f => f.querySelector('path').getAttribute('d') === (gr.icono === 'persona' ? PERSONA : CASA)),
                      // sobre el mapa, la leyenda compacta; el reparto, en la columna izquierda (solo servicios, vivienda y hogar)
                      leyenda: !!document.querySelector('#vul-leyenda .leyenda-pob') && (gr.reparto ? !!document.querySelector('#vul-reparto .reparto') && $('vul-reparto').textContent.includes(nombreTexto(loc))
                        : !document.querySelector('#vul-reparto .reparto')),
                      // sin sectores con base suficiente (ej. Tambogrande, agua las 24 horas) el mapa queda vacío, y está bien
                      mapa: m.hasLayer(capa) && (l ? hexEstilo(l.feature).fillColor === token(gr.tonos[claseVul(i, l.feature)]) : !visibles(nivelDe(m)).features.length),
                      sectores: mag || bajo ? /Sectores con más|base suficiente/.test($('vul-criticos-titulo').textContent)
                        : gr.criterio ? !/mayor proporción/.test($('vul-criticos-titulo').textContent) : /mayor proporción de|base suficiente/.test($('vul-criticos-titulo').textContent),
                      // selector: el indicador está en el grupo que dice su «grupo»; días y horas sin vista de número
                      grupo: $('f-vul').selectedOptions[0].parentElement.label === GRUPOS_SELECTOR[i.grupo]
                        && $('f-vista-vul').querySelector('[value="num"]').disabled === mag,
                      ayuda: $('vul-ayuda').textContent === gr.ayuda,
                      barras: sel?.dataset.loc === vulLoc && +sel.dataset.p === pT && sel.querySelector('small').textContent.includes(gr.base)
                        && $('f-orden-loc').value === gr.orden,
                      tabla: +fila?.dataset.p === pT && $('vul-tabla-loc-cab').textContent.toLowerCase().includes(gr.base),
                      grafico: punto?.y === pT && punto?.x === pT,
                      distritos: metro ? !$('vul-distritos').hidden && document.querySelector('#vul-tabla tr.total').textContent.includes(vulPct(i, t))
                        : $('vul-distritos').hidden && !$('vul-un-distrito').hidden && $('vul-un-distrito').textContent.includes(loc.nombre),
                      lenguaje: gr.criterio ? true : !/crític|problema|afectad/i.test(textoPob) };
                    const mal = Object.keys(ok).filter(x => !ok[x]);
                    if (mal.length) fallas.push(`${lc.id}/${ind.k}: ${mal.join(',')}`);
                  }
                }
                $('f-loc').value = 'metro'; await cambiarLoc();
                $('f-vul').value = 'a'; $('f-vul').dispatchEvent(new Event('change')); await espera(800);  // que termine el movimiento del mapa
                return { combinaciones, fallas }; }""")
            print(f"Sincronía de la pestaña Vulnerabilidad: {rs['combinaciones']} combinaciones, {len(rs['fallas'])} con fallas")
            revisar(rs["combinaciones"] == 23 * 26 and not rs["fallas"], f"vulnerabilidad, sincronía: {rs['fallas'][:10]}")
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
                r.loc = !!vulDatos.catacaos?.h9 && document.querySelector('#vul-localidades .par.sel')?.textContent.includes('Catacaos')
                  && document.querySelector('#vul-frases .fila-casas p').textContent.startsWith('Catacaos:')
                  && document.querySelectorAll('#vul-frases .fila-casas').length === 2 && !vulCapas.resalte
                  && document.querySelector('#vul-reparto .frase-barra').textContent.includes('de Catacaos')
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
            pg.wait_for_timeout(1000)  # los avisos se agregan después de dibujar las tarjetas
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

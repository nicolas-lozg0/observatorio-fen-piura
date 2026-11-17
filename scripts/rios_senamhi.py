"""
Nivel de los ríos Piura y Chira (estaciones automáticas del Senamhi) y su estado de alerta (PHISIS). Solo acumula: la tarjeta
de la página está «en preparación» (ronda 18) hasta tener caudal y umbrales oficiales.

Por qué acumular: la ventana de cada estación automática del mapa del Senamhi trae solo las últimas 24 horas (nivel cada 10
minutos) y la tabla histórica tiene captcha. Guardando un valor por hora cada día, la serie de 7 a 30 días existirá cuando
empiecen las lluvias. No es una descarga oficial: se leen los arreglos del gráfico, como en lluvia_senamhi.py.

Semáforo oficial (ronda 19): la lista pública de avisos hidrológicos del Senamhi (número, fechas y nivel en palabras:
AMARILLO, NARANJA o ROJO). Se guardan los avisos de los últimos 30 días de los ríos de las cuencas del Piura y del Chira en
el departamento (con sus afluentes). El estado numérico de PHISIS también se guarda, pero no dice qué color es cada número.

Resultado: docs/data/rios_piura.json (se agrega a lo que ya había; se guardan los últimos 60 días). Uso: python3 scripts/rios_senamhi.py
"""
import json
import re
import sys
from datetime import datetime, timedelta, timezone

from comun import DATOS, abrir, guardar

ESTACION = ("https://www.senamhi.gob.pe/mapas/mapa-estaciones-2/map_red_graf.php?cod={cod}&estado=AUTOMATICA&tipo_esta=H"
            "&cate=EHA&cod_old=")
MONITOREO = "https://www.senamhi.gob.pe/mapas/mapa-monitoreohidro/mapa-monitoreo.php"
PAGINA = "https://www.senamhi.gob.pe/?&p=monitoreo-hidrologico"
AVISOS = "https://www.senamhi.gob.pe/?p=avisos-hidrologicos"
# Cuenca de cada río con avisos posibles en el departamento (el río principal y sus afluentes)
CUENCAS = {"PIURA": "Piura", "CHARANAL": "Piura", "BIGOTE": "Piura", "CORRAL DEL MEDIO": "Piura", "YAPATERA": "Piura", "SAN FRANCISCO": "Piura",
           "CHIRA": "Chira", "ALAMOR": "Chira", "MACARA": "Chira", "MACARÁ": "Chira", "QUIROZ": "Chira", "CHIPILLICO": "Chira"}
# Río Piura: Puente Ñácara (Chulucanas, aguas arriba de la ciudad); Tambo Grande no envía datos (noviembre de 2026).
# Río Chira: La Ardilla.
ESTACIONES = {"47E0415A": ("Puente Ñácara", "Piura"), "47E09732": ("La Ardilla", "Chira")}
DIAS = 60
PERU = timezone(timedelta(hours=-5))


def leer(url):
    with abrir(url, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def niveles(html, ahora):
    """Valores por hora en punto de la ventana de una estación automática: [[«AAAA-MM-DDTHH:MM», nivel en m], …].
    Las etiquetas vienen como «dd/mm HH:MM», sin año: se toma el año de hoy (o el anterior si la fecha quedaría en el futuro)."""
    et = re.search(r"const\s+LABEL\s*=\s*\[([^\]]*)\]", html)
    va = re.search(r"const\s+DATOS\s*=\s*\[([^\]]*)\]", html)
    if not (et and va):
        raise ValueError("no se encontraron LABEL y DATOS (¿cambió la página?)")
    etiquetas = re.findall(r"'(\d\d)/(\d\d) (\d\d):(\d\d)'", et.group(1))
    valores = [None if x.strip() in ("null", "") else float(x) for x in va.group(1).strip().rstrip(",").split(",")]
    if len(etiquetas) != len(valores):
        raise ValueError(f"{len(etiquetas)} etiquetas y {len(valores)} valores")
    serie = []
    for (d, m, h, mi), v in zip(etiquetas, valores):
        if mi != "00" or v is None:
            continue
        anio = ahora.year - (1 if (int(m), int(d)) > (ahora.month, ahora.day) else 0)
        serie.append([f"{anio}-{m}-{d}T{h}:{mi}", v])
    return serie


def alertas(html):
    """Estado de alerta de PHISIS por código de estación (0 = normal)."""
    return {o["codEstacion"]: o.get("nivel") for o in map(json.loads, re.findall(r'\{"codZonal":"01"[^{}]*\}', html))
            if o.get("codEstacion")}


def avisos(html):
    """Filas de la lista de avisos hidrológicos de las cuencas del Piura y del Chira: número, fechas, horas, nivel, río y estación."""
    filas = []
    for tr in re.findall(r"<tr>(.*?)</tr>", html, re.S):
        tds = [re.sub(r"<[^>]+>", "", x).strip() for x in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        if len(tds) != 6 or tds[5] not in ("AMARILLO", "NARANJA", "ROJO"):
            continue
        m = re.search(r"RÍO (.+?) - ESTACIÓN (.+)$", tds[0])
        if not m or m.group(1) not in CUENCAS:
            continue
        ce = re.search(r"ce=([0-9A-Za-z]+)", tr)
        filas.append({"numero": int(re.sub(r"\D", "", tds[1])), "titulo": tds[0], "rio": m.group(1), "estacion": m.group(2),
                      "cuenca": CUENCAS[m.group(1)], "inicio": tds[2], "fin": tds[3], "horas": int(tds[4]), "nivel": tds[5],
                      "vigente": "vigente" in tds[1], "codigo": ce.group(1) if ce else None})
    return filas


def main():
    ahora = datetime.now(PERU)
    previo = DATOS / "rios_piura.json"
    datos = json.loads(previo.read_text(encoding="utf-8")) if previo.exists() else {"estaciones": {}}
    try:
        alerta = alertas(leer(MONITOREO))
    except (OSError, ValueError) as e:
        print("  Aviso: no se leyó el estado de alerta de PHISIS:", e)
        alerta = {}
    try:
        nuevos_av = avisos(leer(AVISOS))
    except (OSError, ValueError) as e:
        print("  Aviso: no se leyó la lista de avisos hidrológicos:", e)
        nuevos_av = None
    if nuevos_av is not None:  # se suman a los anteriores (la lista del Senamhi es corta) y se guardan 30 días
        lim = (ahora - timedelta(days=30)).date().isoformat()
        todos = {a["numero"]: a for a in datos.get("avisos", []) + nuevos_av}
        datos["avisos"] = sorted((a for a in todos.values() if a["fin"] >= lim), key=lambda a: -a["numero"])
        print(f"Avisos del Senamhi en las cuencas del Piura y del Chira (30 días): {len(datos['avisos'])}; "
              f"{[(a['numero'], a['rio'], a['nivel'], a['fin']) for a in datos['avisos'][:4]]}")
    leidas = 0
    corte = (ahora - timedelta(days=DIAS)).strftime("%Y-%m-%dT%H:%M")
    for cod, (nombre, rio) in ESTACIONES.items():
        try:
            nuevos = niveles(leer(ESTACION.format(cod=cod)), ahora)
        except (OSError, ValueError) as e:
            print(f"  Aviso: {nombre} ({cod}): {e}")
            continue
        e = datos["estaciones"].setdefault(cod, {"nombre": nombre, "rio": rio, "serie": []})
        serie = dict(map(tuple, e["serie"]))
        serie.update(map(tuple, nuevos))
        e["serie"] = [[f, v] for f, v in sorted(serie.items()) if f >= corte]
        e["alerta"] = alerta.get(cod)
        leidas += 1
        print(f"{nombre} (río {rio}): {len(nuevos)} horas nuevas; {len(e['serie'])} en total; último nivel "
              f"{e['serie'][-1] if e['serie'] else 'sin dato'}; alerta PHISIS {e['alerta']}")
    if not leidas:
        sys.exit("No se leyó ninguna estación: no se guarda nada")
    guardar("rios_piura.json", {
        "fuente": "Senamhi, estaciones hidrológicas automáticas (nivel) y avisos hidrológicos",
        "url": PAGINA,
        "fecha_corte": ahora.date().isoformat(),
        "nota": "Nivel en metros (no caudal), un valor por hora; acumulado por el observatorio porque el Senamhi publica solo 24 h",
        "desde": datos.get("desde") or ahora.date().isoformat(),
        "avisos": datos.get("avisos", []),
        "url_avisos": AVISOS,
        "estaciones": datos["estaciones"],
    })


if __name__ == "__main__":
    main()

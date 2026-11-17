"""
Nivel de los ríos Piura y Chira (estaciones automáticas del Senamhi) y su estado de alerta (PHISIS). Solo acumula: la tarjeta
de la página está «en preparación» (ronda 18) hasta tener caudal y umbrales oficiales.

Por qué acumular: la ventana de cada estación automática del mapa del Senamhi trae solo las últimas 24 horas (nivel cada 10
minutos) y la tabla histórica tiene captcha. Guardando un valor por hora cada día, la serie de 7 a 30 días existirá cuando
empiecen las lluvias. No es una descarga oficial: se leen los arreglos del gráfico, como en lluvia_senamhi.py.

Estado de alerta: el mapa de monitoreo hidrológico del Senamhi (PHISIS) trae, por estación, un nivel de alerta (0 = normal),
sin valores ni umbrales numéricos.

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


def main():
    ahora = datetime.now(PERU)
    previo = DATOS / "rios_piura.json"
    datos = json.loads(previo.read_text(encoding="utf-8")) if previo.exists() else {"estaciones": {}}
    try:
        alerta = alertas(leer(MONITOREO))
    except (OSError, ValueError) as e:
        print("  Aviso: no se leyó el estado de alerta de PHISIS:", e)
        alerta = {}
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
        "fuente": "Senamhi, estaciones hidrológicas automáticas (nivel) y monitoreo hidrológico PHISIS (estado de alerta)",
        "url": PAGINA,
        "fecha_corte": ahora.date().isoformat(),
        "nota": "Nivel en metros (no caudal), un valor por hora; acumulado por el observatorio porque el Senamhi publica solo 24 h",
        "estaciones": datos["estaciones"],
    })


if __name__ == "__main__":
    main()

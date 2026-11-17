"""
Temperatura máxima del aire en la ciudad de Piura (pestaña Clima), del reanálisis ERA5-Land vía Open-Meteo (sin clave).

No es una estación: es un reanálisis (Copernicus/ECMWF) en una celda de unos 10 km sobre la ciudad. Se eligió porque la estación
convencional de la ciudad (San Miguel, Senamhi) publica pocos días y no tiene normales en línea. Un solo modelo para todo (el
último día, la normal 1991-2020 y las mismas fechas de 1997 y 2016) evita saltos entre fuentes; el costo es que ERA5-Land llega
con unos 7 días de retraso, y la página lo dice.

Normal de cada fecha: promedio 1991-2020 de ese día del año, suavizado con una media móvil centrada de 15 días.
Anomalía: promedio de los últimos 7 días con dato frente a la normal de esos días (la máxima de un día varía 2 a 3 °C).

Resultado: docs/data/temperatura_piura.json. Uso: python3 scripts/temperatura_piura.py
"""
import json
import sys
from datetime import date, timedelta

from comun import abrir, guardar

LAT, LON = -5.19, -80.63  # ciudad de Piura
URL = ("https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={ini}&end_date={fin}"
       "&daily=temperature_2m_max&timezone=America%2FLima&models=era5_land")
PAGINA = "https://open-meteo.com/en/docs/historical-weather-api"
NORMAL = (1991, 2020)
VENTANA = 15  # días de la media móvil de la normal
DIAS = 90  # días del gráfico
ANOM = 7  # días del promedio de la anomalía
REFERENCIAS = [1997, 2016]  # Niño 1997-98; antes del Niño costero 2017


def md(f):
    """Mes y día; el 29 de febrero se toma como el 28 (la normal no tiene 29)."""
    return (f.month, 28) if (f.month, f.day) == (2, 29) else (f.month, f.day)


def normal_suavizada(serie):
    """Normal 1991-2020 por día del año, con media móvil circular de VENTANA días."""
    dias = [date(2001, 1, 1) + timedelta(d) for d in range(365)]  # año no bisiesto
    suma = {md(d): [0.0, 0] for d in dias}
    for f, v in serie.items():
        if NORMAL[0] <= f.year <= NORMAL[1] and v is not None:
            s = suma[md(f)]
            s[0] += v
            s[1] += 1
    cruda = [suma[md(d)][0] / suma[md(d)][1] for d in dias]
    m = VENTANA // 2
    suave = [sum(cruda[(j + k) % 365] for k in range(-m, m + 1)) / VENTANA for j in range(365)]
    return {md(d): v for d, v in zip(dias, suave)}


def en_anio(serie, f, anio):
    """Valor de la misma fecha en otro año (el 29 de febrero, el 28)."""
    m, d = md(f)
    return serie.get(date(anio, m, d))


def calcular(serie):
    """Filas del gráfico y anomalías, a partir de {fecha: máxima} (None = sin dato)."""
    con = sorted(f for f, v in serie.items() if v is not None)
    if not con:
        sys.exit("Open-Meteo no devolvió ningún valor: no se guarda nada")
    ultimo = con[-1]
    normal = normal_suavizada(serie)
    dias = [ultimo - timedelta(d) for d in range(DIAS - 1, -1, -1)]
    r1 = lambda v: None if v is None else round(v, 1)
    filas = [[f.isoformat(), r1(serie.get(f)), r1(normal[md(f)])] + [r1(en_anio(serie, f, a)) for a in REFERENCIAS] for f in dias]
    ult7 = dias[-ANOM:]

    def anomalia(valores):
        pares = [(v, normal[md(f)]) for f, v in zip(ult7, valores) if v is not None]
        return round(sum(v - n for v, n in pares) / len(pares), 1) if len(pares) >= ANOM - 1 else None

    anom = {"actual": anomalia([serie.get(f) for f in ult7])}
    for a in REFERENCIAS:
        anom[str(a)] = anomalia([en_anio(serie, f, a) for f in ult7])
    return ultimo, filas, anom


def main():
    hoy = date.today()
    with abrir(URL.format(lat=LAT, lon=LON, ini=f"{NORMAL[0]}-01-01", fin=hoy.isoformat()), timeout=120) as r:
        d = json.load(r)
    if "daily" not in d:
        sys.exit(f"Open-Meteo respondió sin datos diarios: {str(d)[:200]}")
    serie = {date.fromisoformat(f): v for f, v in zip(d["daily"]["time"], d["daily"]["temperature_2m_max"])}
    ultimo, filas, anom = calcular(serie)
    # comprobaciones: 90 días, normales plausibles para Piura, y la normal cubre los 30 años
    assert len(filas) == DIAS and all(20 <= x[2] <= 40 for x in filas), "normal fuera de rango"
    assert sum(1 for f in serie if NORMAL[0] <= f.year <= NORMAL[1] and serie[f] is not None) > 0.95 * 365 * 30, "faltan años de la normal"
    retraso = (hoy - ultimo).days
    print(f"ERA5-Land en ({d['latitude']}, {d['longitude']}): último día {ultimo} ({retraso} días de retraso), máxima {serie[ultimo]} °C; "
          f"anomalía de 7 días {anom}")
    guardar("temperatura_piura.json", {
        "fuente": "Reanálisis ERA5-Land (Copernicus/ECMWF), vía Open-Meteo (CC BY 4.0)",
        "url": PAGINA,
        "fecha_corte": ultimo.isoformat(),
        "celda": [d["latitude"], d["longitude"]],
        "normal": f"{NORMAL[0]}-{NORMAL[1]}, media móvil de {VENTANA} días",
        "columnas": ["fecha", "maxima", "normal"] + [str(a) for a in REFERENCIAS],
        "filas": filas,
        "anomalia_7d": anom,
    })


if __name__ == "__main__":
    main()

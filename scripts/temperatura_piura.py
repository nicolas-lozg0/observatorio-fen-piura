"""
Temperatura máxima del aire en la ciudad de Piura (pestaña Clima), con datos de Open-Meteo (sin clave).

Dos tramos (ronda 19):
- Reanálisis ERA5-Land (Copernicus/ECMWF), en una celda de unos 10 km sobre la ciudad: la normal 1991-2020, 1997, 2016 y la
  serie actual hasta su último día (llega con unos 7 días de retraso).
- Los días siguientes, hasta ayer, del modelo de pronóstico de Open-Meteo (past_days), corregidos con la diferencia media con
  ERA5-Land en los últimos 30 días que tienen los dos (en noviembre de 2026, el pronóstico marca unos 0,5 a 0,7 °C menos). Se
  marcan como estimación.
No es una estación: la estación convencional de la ciudad (San Miguel, Senamhi) publica pocos días y no tiene normales en línea.

Una sola métrica: el promedio de las máximas de los 7 días que terminan en cada fecha. Lo normal es la mediana de ese promedio en
1991-2020 (juntando los 30 años y ±7 días alrededor de la fecha, unas 450 semanas); la franja va del percentil 10 al 90.
Anomalía = promedio de los últimos 7 días − mediana de la fecha.

Resultado: docs/data/temperatura_piura.json. Uso: python3 scripts/temperatura_piura.py
"""
import json
import statistics
import sys
from datetime import date, datetime, timedelta, timezone

from comun import abrir, guardar

LAT, LON = -5.19, -80.63  # ciudad de Piura
ARCHIVO = ("https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={ini}&end_date={fin}"
           "&daily=temperature_2m_max&timezone=America%2FLima&models=era5_land")
PRONOSTICO = ("https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&daily=temperature_2m_max&past_days=92"
              "&forecast_days=1&timezone=America%2FLima")
PAGINA = "https://open-meteo.com/en/docs/historical-weather-api"
NORMAL = (1991, 2020)
DIAS = 90  # días del gráfico
SEMANA = 7  # días del promedio móvil
AMPLIO = 7  # ±días alrededor de la fecha que se juntan para la franja normal
COMUNES = 30  # días comunes con los que se mide la diferencia entre el pronóstico y ERA5-Land
REFERENCIAS = [1997, 2016]  # Niño 1997-98; antes del Niño costero 2017
PERU = timezone(timedelta(hours=-5))


def md(f):
    """Mes y día; el 29 de febrero se toma como el 28 (la normal no tiene 29)."""
    return (f.month, 28) if (f.month, f.day) == (2, 29) else (f.month, f.day)


def en_anio(f, anio):
    m, d = md(f)
    return date(anio, m, d)


def media7(serie, f):
    """Promedio de las máximas de los 7 días que terminan en f (con al menos 6 con dato)."""
    vs = [serie.get(f - timedelta(k)) for k in range(SEMANA)]
    vs = [v for v in vs if v is not None]
    return sum(vs) / len(vs) if len(vs) >= SEMANA - 1 else None


def franja_normal(serie):
    """Por día del año: percentiles 10, 50 y 90 del promedio de 7 días en 1991-2020, juntando ±AMPLIO días."""
    dias = [date(2001, 1, 1) + timedelta(d) for d in range(365)]  # año no bisiesto
    indice = {md(d): j for j, d in enumerate(dias)}
    por_dia = [[] for _ in range(365)]
    f = date(NORMAL[0], 1, SEMANA)
    while f.year <= NORMAL[1]:
        v = media7(serie, f)
        if v is not None:
            por_dia[indice[md(f)]].append(v)
        f += timedelta(1)
    out = {}
    for j, d in enumerate(dias):
        vals = [v for k in range(-AMPLIO, AMPLIO + 1) for v in por_dia[(j + k) % 365]]
        q = statistics.quantiles(vals, n=10)
        out[md(d)] = (q[0], q[4], q[8])
    return out


def unir(era5, pron, ayer):
    """Serie actual: ERA5-Land hasta su último día; después, el pronóstico corregido con la diferencia media de los últimos
    COMUNES días que tienen los dos. Devuelve la serie, las fechas estimadas, la corrección y el último día de ERA5-Land."""
    ult_era5 = max(f for f, v in era5.items() if v is not None)
    comunes = sorted(f for f in pron if pron[f] is not None and era5.get(f) is not None)[-COMUNES:]
    if len(comunes) < 20:
        sys.exit(f"Solo {len(comunes)} días comunes entre el pronóstico y ERA5-Land: no se puede corregir")
    correccion = statistics.mean(era5[f] - pron[f] for f in comunes)
    serie, estimados = dict(era5), set()
    for f, v in pron.items():
        if ult_era5 < f <= ayer and v is not None:
            serie[f] = v + correccion
            estimados.add(f)
    return serie, estimados, round(correccion, 2), ult_era5


def calcular(serie, estimados, ultimo, franja):
    """Filas del gráfico ([fecha, máxima, promedio de 7 días, p10, mediana, p90, 1997, 2016, estimado]) y anomalías."""
    r1 = lambda v: None if v is None else round(v, 1)
    dias = [ultimo - timedelta(d) for d in range(DIAS - 1, -1, -1)]
    filas = []
    for f in dias:
        p10, p50, p90 = franja[md(f)]
        filas.append([f.isoformat(), r1(serie.get(f)), r1(media7(serie, f)), r1(p10), r1(p50), r1(p90)]
                     + [r1(media7(serie, en_anio(f, a))) for a in REFERENCIAS] + [int(f in estimados)])
    mediana = franja[md(ultimo)][1]
    anom = {"actual": r1(media7(serie, ultimo) - mediana)}
    for a in REFERENCIAS:
        v = media7(serie, en_anio(ultimo, a))
        anom[str(a)] = None if v is None else r1(v - mediana)
    return filas, anom


def leer_json(url):
    with abrir(url, timeout=120) as r:
        return json.load(r)


def main():
    hoy = datetime.now(PERU).date()
    ayer = hoy - timedelta(1)  # el máximo de hoy aún no se completa
    d = leer_json(ARCHIVO.format(lat=LAT, lon=LON, ini=f"{NORMAL[0]}-01-01", fin=hoy.isoformat()))
    p = leer_json(PRONOSTICO.format(lat=LAT, lon=LON))
    if "daily" not in d or "daily" not in p:
        sys.exit(f"Open-Meteo respondió sin datos diarios: {str(d)[:150]} {str(p)[:150]}")
    era5 = {date.fromisoformat(f): v for f, v in zip(d["daily"]["time"], d["daily"]["temperature_2m_max"])}
    pron = {date.fromisoformat(f): v for f, v in zip(p["daily"]["time"], p["daily"]["temperature_2m_max"])}
    assert sum(1 for f, v in era5.items() if NORMAL[0] <= f.year <= NORMAL[1] and v is not None) > 0.95 * 365 * 30, "faltan años de la normal"
    serie, estimados, correccion, ult_era5 = unir(era5, pron, ayer)
    ultimo = max(f for f, v in serie.items() if v is not None)
    filas, anom = calcular(serie, estimados, ultimo, franja_normal(era5))
    assert len(filas) == DIAS and all(20 <= x[4] <= 40 and x[3] <= x[4] <= x[5] for x in filas), "franja normal fuera de rango"
    print(f"ERA5-Land hasta {ult_era5}; pronóstico corregido ({correccion:+} °C) hasta {ultimo}: {len(estimados)} días estimados. "
          f"Promedio de 7 días al {ultimo}: {filas[-1][2]} °C; mediana normal {filas[-1][4]} °C; anomalías {anom}")
    guardar("temperatura_piura.json", {
        "fuente": "Open-Meteo: reanálisis ERA5-Land (Copernicus/ECMWF) y, en los últimos días, su modelo de pronóstico corregido (CC BY 4.0)",
        "url": PAGINA,
        "fecha_corte": ultimo.isoformat(),
        "ultimo_era5": ult_era5.isoformat(),
        "correccion": correccion,
        "dias_comunes": COMUNES,
        "celda": [d["latitude"], d["longitude"]],
        "normal": f"{NORMAL[0]}-{NORMAL[1]}: mediana y percentiles 10 y 90 del promedio de {SEMANA} días (±{AMPLIO} días)",
        "columnas": ["fecha", "maxima", "media7", "p10", "mediana", "p90"] + [str(a) for a in REFERENCIAS] + ["estimado"],
        "filas": filas,
        "anomalia_7d": anom,
    })


if __name__ == "__main__":
    main()

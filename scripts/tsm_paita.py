"""
Temperatura superficial del mar (TSM) frente a Paita, por satélite (pestaña Clima).

Principal: NOAA OISST v2.1 (diaria, 0,25°), servidor OPeNDAP de NOAA PSL, celda 5,125° S y 81,375° O (unos 25 km
mar adentro; la celda vecina hacia la costa es tierra). La anomalía se calcula contra el promedio diario 1991-2020 del
mismo OISST (el mismo periodo que usa el ENFEN), no con la variable `anom` del archivo, que es contra 1971-2000.
Respaldo: NOAA Coral Reef Watch (5 km, ERDDAP de coastwatch.noaa.gov), con la anomalía contra el mismo promedio
1991-2020, guardado en el JSON anterior.

Las estaciones costeras de IMARPE y DHN no se usan: sus páginas bloquean el acceso automático (Cloudflare y
verificación de persona).

Resultado: docs/data/tsm_paita.json (últimos 90 días). Uso: python3 scripts/tsm_paita.py
"""
import json
import re
import sys
from datetime import date, timedelta

from comun import DATOS, abrir, guardar

PSL = "https://psl.noaa.gov/thredds/dodsC/Datasets/noaa.oisst.v2.highres/"
ILAT, ILON = 339, 1114  # índices de la celda: lat -5,125 y lon 278,625 (= -81,375)
CRW = ("https://coastwatch.noaa.gov/erddap/griddap/noaacrwsstDaily.csv?analysed_sst"
       "[({ini}T12:00:00Z):1:(last)][(-5.125)][(-81.375)]")
DIAS = 90
PAGINA = "https://psl.noaa.gov/data/gridded/data.noaa.oisst.v2.highres.html"


def leer(url):
    with abrir(url, timeout=120) as r:
        return r.read().decode("utf-8", "replace")


def valores(ascii_):
    """Valores de la grilla en la respuesta ASCII de OPeNDAP: líneas «[i][0], v» → lista en orden (None si falta)."""
    bloque = ascii_.split("sst.sst", 1)[1] if "sst.sst" in ascii_ else ascii_
    vals = [float(v) for v in re.findall(r"^\[\d+\]\[0\], (\S+)", bloque, re.M)]
    return [None if abs(v) > 100 else v for v in vals]  # valor de relleno (-9.97e36): sin dato


def normal_1991_2020():
    """Promedio diario 1991-2020 de la celda, por «mm-dd» (calendario de 365 días; el 29/02 usa el 28/02)."""
    # en tramos de 92 días: pedir los 365 de una vez pasa del límite de 60 s del servidor (error 502)
    v = [x for i0 in range(0, 365, 92) for x in valores(leer(
        PSL + f"sst.day.mean.ltm.1991-2020.nc.ascii?sst[{i0}:1:{min(i0 + 91, 364)}][{ILAT}:1:{ILAT}][{ILON}:1:{ILON}]"))]
    if len(v) != 365 or None in v:
        raise ValueError(f"promedio 1991-2020: {len(v)} días")
    return {(date(2001, 1, 1) + timedelta(i)).strftime("%m-%d"): round(x, 2) for i, x in enumerate(v)}


def oisst():
    """[[fecha, tsm], …] de los últimos días (este año y, si hace falta, el anterior)."""
    serie, anio = [], date.today().year
    for a in (anio - 1, anio):
        dds = leer(PSL + f"sst.day.mean.{a}.nc.dds")
        n = int(re.search(r"time\s*=\s*(\d+)\]", dds).group(1))
        i0 = max(0, n - DIAS - 5)
        if a < anio and len(serie) >= DIAS:
            continue
        v = valores(leer(PSL + f"sst.day.mean.{a}.nc.ascii?sst[{i0}:1:{n - 1}][{ILAT}:1:{ILAT}][{ILON}:1:{ILON}]"))
        serie += [[(date(a, 1, 1) + timedelta(i0 + i)).isoformat(), x] for i, x in enumerate(v)]
    return sorted(serie)


def crw():
    ini = (date.today() - timedelta(DIAS + 5)).isoformat()
    filas = leer(CRW.format(ini=ini)).strip().splitlines()[2:]  # cabecera y unidades
    return [[f.split(",")[0][:10], float(f.split(",")[3])] for f in filas if f.split(",")[3] not in ("", "NaN")]


def main():
    # El promedio 1991-2020 no cambia: se descarga una vez y luego se toma del archivo anterior
    anterior = DATOS / "tsm_paita.json"
    normal = json.loads(anterior.read_text(encoding="utf-8")).get("normal") if anterior.exists() else None
    if not normal:
        try:
            normal = normal_1991_2020()
        except (OSError, ValueError, AttributeError) as e:
            sys.exit(f"Sin promedio 1991-2020: {e}")
    fuente = {"fuente": "NOAA OISST v2.1 (satélite), celda frente a Paita", "url": PAGINA}
    try:
        serie = oisst()
    except (OSError, ValueError, AttributeError) as e:
        print(f"  Aviso: OISST no respondió ({e}); se usa Coral Reef Watch")
        serie = crw()
        fuente = {"fuente": "NOAA Coral Reef Watch (satélite, 5 km), celda frente a Paita",
                  "url": "https://coralreefwatch.noaa.gov/product/5km/index_5km_sst.php"}
    serie = [[f, t] for f, t in serie if t is not None][-DIAS:]
    if len(serie) < 30:
        sys.exit(f"Solo {len(serie)} días con dato: no se guarda nada")
    ultimo = date.fromisoformat(serie[-1][0])
    if (date.today() - ultimo).days > 10:
        sys.exit(f"El último dato es del {ultimo}: la fuente no se actualiza")
    clave = lambda f: "02-28" if f[5:] == "02-29" else f[5:]
    filas = [[f, round(t, 2), round(t - normal[clave(f)], 2)] for f, t in serie]
    print(f"{fuente['fuente']}: {len(filas)} días, último {filas[-1][0]}: {filas[-1][1]} °C, anomalía {filas[-1][2]:+.2f} °C")
    guardar("tsm_paita.json", {
        **fuente,
        "fecha_corte": filas[-1][0],
        "celda": {"lat": -5.125, "lon": -81.375},
        "base": "1991-2020",
        "columnas": ["fecha", "tsm", "anomalia"],
        "filas": filas,
        "normal": normal,
    })


if __name__ == "__main__":
    main()

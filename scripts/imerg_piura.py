"""
Lluvia de 24 h estimada por satélite (NASA GPM IMERG Early, V07) sobre el departamento de Piura (pestaña Clima).

Suma las 48 medias horas de 12:00 UTC del día anterior a 12:00 UTC de hoy, que es de 7:00 a 7:00 en Lima, la misma
ventana que se asume para las estaciones del Senamhi. IMERG Early sale unas 4 horas después de cada media hora: por eso
este script corre en su propio workflow a las 12:30 de Lima (imerg.yml).

Datos: servidor OPeNDAP de GES DISC (NASA), recortado a una caja alrededor de Piura (rejilla de 0,1°). La lista de archivos
es pública; los datos piden una cuenta de Earthdata: el token se lee de la variable de entorno EARTHDATA_TOKEN (secreto de
GitHub) y solo viaja en la cabecera de la consulta. Nunca se escribe ni se imprime.

Se guardan solo las celdas cuyo centro cae dentro del departamento (límites de docs/data/piura_distritos.json).
Resultado: docs/data/imerg_piura.json. Uso: EARTHDATA_TOKEN=… python3 scripts/imerg_piura.py
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

from comun import DATOS, PERU, guardar

LISTA = "https://gpm1.gesdisc.eosdis.nasa.gov/data/GPM_L3/GPM_3IMERGHHE.07/{a}/{doy:03d}/"
OPENDAP = "https://gpm1.gesdisc.eosdis.nasa.gov/opendap/GPM_L3/GPM_3IMERGHHE.07/{a}/{doy:03d}/{archivo}.ascii?{var}"
PAGINA = "https://gpm.nasa.gov/data/imerg"
# Caja de Piura en índices de la rejilla global de 0,1° (lon −179,95 + 0,1·i; lat −89,95 + 0,1·j)
LON0, LON1 = 985, 1007  # −81,45 a −79,25
LAT0, LAT1 = 835, 859   # −6,45 a −4,05
LATENCIA = timedelta(hours=4, minutes=30)
MINIMO = 44  # medias horas que deben llegar (de 48); con menos, no se guarda nada
UA = "observatorio-fen-piura/1.0"


def leer(url, token=None):
    pedido = urllib.request.Request(url, headers={"User-Agent": UA})
    if token:
        pedido.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(pedido, timeout=120) as r:
        return r.read().decode("utf-8", "replace")


def rejilla(texto, nlon, nlat):
    """Respuesta ASCII de OPeNDAP de precipitation[0][lon][lat] → lista por lon de listas por lat (None si falta)."""
    bloque = texto.split("precipitation.precipitation", 1)[-1]
    filas = {int(i): [float(v) for v in vals.split(",")] for i, vals in re.findall(r"^\[0\]\[(\d+)\], (.+)$", bloque, re.M)}
    if len(filas) != nlon or any(len(v) != nlat for v in filas.values()):
        raise ValueError(f"rejilla de {len(filas)} × {set(len(v) for v in filas.values())}, se esperaba {nlon} × {nlat}")
    return [[None if x < 0 else x for x in filas[i]] for i in range(nlon)]


def es_login(texto):
    """True si NASA devolvió su página de inicio de sesión en vez de datos (token vencido o sin autorizar la aplicación)."""
    return "<html" in texto[:2000].lower() and ("earthdata" in texto.lower() or "login" in texto.lower())


def archivos(ini, fin, listas):
    """Nombres de los archivos de media hora entre ini y fin, desde la lista pública de cada día (llevan la versión, p. ej.
    V07C). `listas` guarda las listas ya leídas."""
    nombres = {}
    dia = ini.date()
    while dia <= (fin - timedelta(minutes=30)).date():
        if dia not in listas:
            listas[dia] = leer(LISTA.format(a=dia.year, doy=dia.timetuple().tm_yday))
        for m in re.finditer(r"(3B-HHR-E\.MS\.MRG\.3IMERG\.(\d{8})-S(\d{6})-E\d{6}\.\d{4}\.V\w+\.HDF5)", listas[dia]):
            nombres[datetime.strptime(m.group(2) + m.group(3), "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)] = m.group(1)
        dia += timedelta(days=1)
    return nombres


def anillos_piura():
    """Contornos de los distritos de Piura en (lon, lat), desde el trazado proyectado de piura_distritos.json."""
    m = json.loads((DATOS / "piura_distritos.json").read_text(encoding="utf-8"))
    P = m["proyeccion"]
    anillos = []
    for d in m["distritos"].values():
        for r in d["d"].split("Z"):
            if r:
                pts = [tuple(map(float, q.split(","))) for q in r[1:].split("L")]
                anillos.append([(P["lon0"] + x / (P["k"] * P["escala"]), P["lat1"] - y / P["escala"]) for x, y in pts])
    return anillos


def dentro(lon, lat, anillos):
    """Punto en algún polígono (regla par-impar, por anillo)."""
    for r in anillos:
        c = False
        for (x0, y0), (x1, y1) in zip(r, r[1:] + r[:1]):
            if (y0 > lat) != (y1 > lat) and lon < x0 + (lat - y0) * (x1 - x0) / (y1 - y0):
                c = not c
        if c:
            return True
    return False


def main():
    token = os.environ.get("EARTHDATA_TOKEN", "").strip()
    if not token:
        sys.exit("Falta la variable de entorno EARTHDATA_TOKEN (secreto de GitHub): no se guarda nada")
    # Ventana de 7:00 a 7:00 de Lima (12:00 UTC). Si la del día aún no está completa en la lista (latencia de IMERG Early),
    # se usa la última completa, de hasta 3 días antes; el mapa dice de qué fechas es.
    ahora = datetime.now(timezone.utc)
    fin = ahora.replace(hour=12, minute=0, second=0, microsecond=0)
    if ahora < fin + LATENCIA:
        fin -= timedelta(days=1)
    listas = {}
    for _ in range(4):
        ini = fin - timedelta(days=1)
        nombres = archivos(ini, fin, listas)
        if sum(1 for k in nombres if ini <= k < fin) >= MINIMO:
            break
        print(f"  La ventana que termina el {fin:%d/%m %H:%M} UTC aún no está completa en la lista: se prueba el día anterior")
        fin -= timedelta(days=1)
    else:
        sys.exit("No hay una ventana de 24 horas completa en los últimos 4 días: no se guarda nada")
    var = f"precipitation[0:1:0][{LON0}:1:{LON1}][{LAT0}:1:{LAT1}]"
    nlon, nlat = LON1 - LON0 + 1, LAT1 - LAT0 + 1
    suma = [[0.0] * nlat for _ in range(nlon)]
    usadas, faltan = 0, []
    t = ini
    while t < fin:
        archivo = nombres.get(t)
        try:
            if not archivo:
                raise ValueError("no está en la lista")
            texto = leer(OPENDAP.format(a=t.year, doy=t.timetuple().tm_yday, archivo=archivo, var=var), token)
            if es_login(texto):
                sys.exit("NASA respondió con su página de inicio de sesión: token vencido o sin autorización "
                         "(revisa EARTHDATA_TOKEN y que la cuenta tenga autorizada la aplicación NASA GESDISC DATA ARCHIVE)")
            g = rejilla(texto, nlon, nlat)
            for i in range(nlon):
                for j in range(nlat):
                    suma[i][j] += (g[i][j] or 0.0) * 0.5  # mm/h durante media hora
            usadas += 1
        except urllib.error.HTTPError as e:  # el mensaje de urllib no incluye cabeceras: el token no se imprime
            if e.code in (401, 403):
                sys.exit(f"HTTP {e.code}: token vencido o sin autorización (revisa EARTHDATA_TOKEN y que la cuenta tenga "
                         "autorizada la aplicación NASA GESDISC DATA ARCHIVE). No se guarda nada")
            faltan.append(f"{t:%H:%M} UTC (HTTP {e.code})")
        except (OSError, ValueError) as e:
            faltan.append(f"{t:%H:%M} UTC ({type(e).__name__}: {str(e)[:80]})")
        t += timedelta(minutes=30)
    if usadas < MINIMO:
        sys.exit(f"Solo llegaron {usadas} de 48 medias horas (mínimo {MINIMO}): no se guarda nada. Faltan: {'; '.join(faltan[:5])}")
    anillos = anillos_piura()
    lon = lambda i: round(-179.95 + 0.1 * (LON0 + i), 2)
    lat = lambda j: round(-89.95 + 0.1 * (LAT0 + j), 2)
    celdas = [[lat(j), lon(i), round(suma[i][j], 1)] for i in range(nlon) for j in range(nlat) if dentro(lon(i), lat(j), anillos)]
    mx = max(c[2] for c in celdas)
    print(f"IMERG Early: {usadas} de 48 medias horas, {len(celdas)} celdas en Piura, máximo {mx} mm"
          + (f"; faltan {len(faltan)}: {'; '.join(faltan[:3])}" if faltan else ""))
    guardar("imerg_piura.json", {
        "fuente": "NASA GPM IMERG Early (V07), estimación satelital",
        "url": PAGINA,
        "fecha_corte": fin.astimezone(PERU).date().isoformat(),
        "inicio_lima": ini.astimezone(PERU).isoformat(timespec="minutes"),
        "fin_lima": fin.astimezone(PERU).isoformat(timespec="minutes"),
        "medias_horas": usadas,
        "paso": 0.1,
        "columnas": ["lat", "lon", "mm"],
        "celdas": celdas,
    })


if __name__ == "__main__":
    main()

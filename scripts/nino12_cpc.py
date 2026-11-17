"""
Anomalía semanal de la temperatura del mar en la región Niño 1+2 (frente a Perú y Ecuador), últimos 12 meses.

Fuente: NOAA CPC, https://www.cpc.ncep.noaa.gov/data/indices/wksst9120.for (OISST, semanas centradas en miércoles;
anomalía frente a 1991-2020). Texto de ancho fijo: semana, y por región la TSM y su anomalía, a veces pegadas
(«20.6-0.1»).

Resultado: docs/data/nino12.json. Uso: python3 scripts/nino12_cpc.py
"""
import re
import sys
from datetime import datetime, timedelta

from comun import abrir, guardar

URL = "https://www.cpc.ncep.noaa.gov/data/indices/wksst9120.for"
SEMANAS = 53  # unos 12 meses


def leer(texto):
    """[[fecha ISO, TSM, anomalía], …] de la región Niño 1+2 (primeras dos cifras de cada fila)."""
    filas = []
    for linea in texto.splitlines():
        m = re.match(r"\s*(\d{2}[A-Z]{3}\d{4})\s+(.*)", linea)
        if not m:
            continue
        cifras = re.findall(r"-?\d+\.\d", m.group(2))
        if len(cifras) < 8:
            raise ValueError(f"fila con {len(cifras)} cifras: {linea!r}")
        fecha = datetime.strptime(m.group(1).title(), "%d%b%Y").date()
        filas.append([fecha.isoformat(), float(cifras[0]), float(cifras[1])])
    return filas


def main():
    with abrir(URL, timeout=90) as r:
        filas = leer(r.read().decode("ascii", "replace"))
    if len(filas) < SEMANAS:
        sys.exit(f"Solo {len(filas)} semanas: no se guarda nada")
    ultima = datetime.fromisoformat(filas[-1][0]).date()
    if (datetime.now().date() - ultima) > timedelta(days=21):
        sys.exit(f"La última semana es del {ultima}: el archivo no se actualiza")
    filas = filas[-SEMANAS:]
    print(f"Niño 1+2: {len(filas)} semanas, última {filas[-1][0]}: {filas[-1][1]} °C, anomalía {filas[-1][2]:+.1f} °C")
    guardar("nino12.json", {
        "fuente": "NOAA CPC, anomalía semanal de la TSM en la región Niño 1+2",
        "url": URL,
        "fecha_corte": filas[-1][0],
        "base": "1991-2020",
        "columnas": ["semana", "tsm", "anomalia"],
        "filas": filas,
    })


if __name__ == "__main__":
    main()

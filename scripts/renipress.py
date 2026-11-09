"""
Ubicación de los establecimientos de salud de Piura con camas, según el registro RENIPRESS de SUSALUD.

RENIPRESS trae una fila por establecimiento (COD_IPRESS) con latitud (columna NORTE) y longitud (ESTE) en grados
decimales, y su ubigeo. Se guardan solo los establecimientos que figuran en docs/data/camas_piura.json, así que
este script corre después de camas_susalud.py. Si un establecimiento no tiene coordenadas o caen fuera de Piura,
se guarda sin ellas y la página lo ubica en el centro de su distrito.
Resultado: docs/data/ipress_piura.json. Se corre a mano con scripts/actualizar_local.sh.
"""
import json
import re
import tempfile
from pathlib import Path

import pandas as pd

from comun import DATOS, abrir, descargar, fecha_modificacion, guardar, verificar_espacio

DATASET = "http://datos.susalud.gob.pe/dataset/registro-nacional-de-ipress-renipress"
CAJA_PIURA = (-6.5, -3.3, -81.5, -79.0)  # latitud mínima y máxima, longitud mínima y máxima


def coordenada(lat, lon):
    """(lat, lon) redondeados, o None si falta alguno o cae fuera de Piura."""
    try:
        lat, lon = float(lat), float(lon)
    except (TypeError, ValueError):
        return None
    ok = CAJA_PIURA[0] <= lat <= CAJA_PIURA[1] and CAJA_PIURA[2] <= lon <= CAJA_PIURA[3]
    return (round(lat, 5), round(lon, 5)) if ok else None


assert coordenada("-5.19", "-80.63") == (-5.19, -80.63)
assert coordenada("-11.86", "-69.13") is None and coordenada("", "-80") is None


def main():
    verificar_espacio()
    pagina = abrir(DATASET).read().decode("utf-8", "replace")
    csvs = sorted(set(re.findall(r'http[^"]*RENIPRESS_(\d{4})_v(\d+)\.csv', pagina)), key=lambda x: (int(x[0]), int(x[1])))
    if not csvs:
        raise SystemExit("La página de RENIPRESS respondió, pero no tiene enlaces a CSV.")
    a, v = csvs[-1]
    url = f"http://datos.susalud.gob.pe/sites/default/files/RENIPRESS_{a}_v{v}.csv"
    codigos = {f["co_ipress"] for f in json.loads((DATOS / "camas_piura.json").read_text(encoding="utf-8"))["establecimientos"]}
    with tempfile.TemporaryDirectory() as tmp:
        archivo = Path(tmp) / "renipress.csv"
        print("Descargando", url)
        descargar(url, archivo)
        d = pd.read_csv(archivo, sep=";", dtype=str, encoding="utf-8-sig",
                        usecols=["COD_IPRESS", "NOMBRE", "DEPARTAMENTO", "UBIGEO", "NORTE", "ESTE"])
    d = d[d["COD_IPRESS"].isin(codigos)]
    filas = []
    for r in d.itertuples():
        c = coordenada(r.NORTE, r.ESTE)
        filas.append({"co_ipress": r.COD_IPRESS, "ubigeo": r.UBIGEO, "lat": c[0] if c else None, "lon": c[1] if c else None})
    faltan = codigos - {f["co_ipress"] for f in filas}
    sin = [f["co_ipress"] for f in filas if f["lat"] is None]
    print(f"{len(filas)} de {len(codigos)} establecimientos en RENIPRESS; {len(sin)} sin coordenadas válidas: {sin}")
    if faltan:
        print("  No están en RENIPRESS:", sorted(faltan))
    guardar("ipress_piura.json", {
        "fuente": "SUSALUD, Registro Nacional de IPRESS (RENIPRESS)",
        "url": DATASET,
        "fecha_corte": (fecha_modificacion(url) or "")[:10] or None,
        "nota": "Coordenadas (columnas NORTE y ESTE, en grados decimales) de los establecimientos con datos de camas. "
                "Sin coordenadas válidas: la página los ubica en el centro de su distrito.",
        "establecimientos": sorted(filas, key=lambda f: f["co_ipress"]),
    })


if __name__ == "__main__":
    main()

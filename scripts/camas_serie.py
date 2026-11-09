"""
Serie mensual de camas y ocupación en Piura: los últimos 24 meses publicados por SUSALUD (Consulta D1).

Usa el mismo cálculo que camas_susalud.py (resumir): por cada mes, suma camas, pacientes-día y días-cama de los
establecimientos de Piura que reportaron. La página calcula la ocupación como pacientes-día / días-cama.
SUSALUD vuelve a publicar meses pasados, así que en cada corrida se recalculan los 24 meses.
El grupo de establecimientos que reporta cambia de un mes a otro: se guarda cuántos reportaron.
Resultado: docs/data/camas_serie.json. Se corre a mano con scripts/actualizar_local.sh.
"""
import re
import urllib.error
from datetime import date

import pandas as pd

from camas_susalud import DATASET, resumir
from comun import abrir, guardar, verificar_espacio

MESES = 24


def enlaces():
    """{(año, mes): url} de los CSV de la Consulta D1 publicados en los últimos tres años."""
    r = {}
    for anio in range(date.today().year - 2, date.today().year + 1):
        try:
            pagina = abrir(DATASET.format(anio=anio)).read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code == 404:  # el conjunto del año aún no existe
                continue
            raise
        for url, a, m in re.findall(r'(http[^"]*Consulta_D1_Hospitalizaciones_(\d{4})_(\d+)\.csv)', pagina):
            r[(int(a), int(m))] = url
    return r


def mes_de(d):
    """Totales de Piura de un mes, con los establecimientos que reportaron."""
    todos = resumir(d)
    rep = [f for f in todos if f["reporto"]]
    return {"establecimientos": len(todos), "reportaron": len(rep), "camas": sum(f["camas"] for f in rep),
            "pacientes_dia": sum(f["pacientes_dia"] for f in rep), "dias_cama": sum(f["dias_cama"] for f in rep)}


def main():
    verificar_espacio()
    todos = enlaces()
    if not todos:
        raise SystemExit("La página de SUSALUD respondió, pero no tiene enlaces a CSV de la Consulta D1.")
    serie = []
    for (a, m) in sorted(todos)[-MESES:]:
        with abrir(todos[(a, m)]) as r:
            d = pd.read_csv(r, sep=";", dtype=str, encoding="utf-8")
        assert (int(d["ANHO"].iloc[0]), int(d["MES"].iloc[0])) == (a, m), f"el archivo {a}-{m} trae otro mes"
        fila = {"mes": f"{a}-{m:02d}", **mes_de(d)}
        print(fila["mes"], fila["reportaron"], "reportaron;", f"ocupación {100 * fila['pacientes_dia'] / fila['dias_cama']:.1f} %")
        serie.append(fila)
    meses = [s["mes"] for s in serie]
    assert len(serie) == min(MESES, len(todos)) and meses == sorted(set(meses)), "meses repetidos o desordenados"
    guardar("camas_serie.json", {
        "fuente": "SUSALUD, Consulta D1: producción asistencial en hospitalización",
        "url": DATASET.format(anio=int(meses[-1][:4])),
        "fecha_corte": f"{meses[-1]}-01",  # el dato más reciente es del mes; SUSALUD lo publica uno o dos meses después
        "nota": "Por mes, suma de los establecimientos de Piura que reportaron (el grupo cambia de un mes a otro). "
                "Ocupación = pacientes-día / días-cama disponibles.",
        "serie": serie,
    })


if __name__ == "__main__":
    main()

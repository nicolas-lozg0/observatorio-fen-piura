"""
Camas hospitalarias en Piura según SUSALUD (Consulta D1, producción asistencial en hospitalización).

SUSALUD publica un CSV por mes, con uno o dos meses de retraso. Se toma el último mes publicado del año en
curso y se suma por establecimiento (IPRESS): camas, días-cama disponibles, ingresos y egresos. Las camas de
cuidados intensivos (UCI) se cuentan aparte. Con los pacientes-día (NRO_TOTAL_PACIENTES_CAMAS) y los días-cama
disponibles se puede calcular la ocupación del mes; no existe un dato público de camas libres en tiempo real. Los establecimientos que no reportaron vienen con 'NE_0001' y se
marcan como "no reportó". Resultado: docs/data/camas_piura.json.
"""
import re
import urllib.error
from datetime import date

import pandas as pd

from comun import abrir, fecha_modificacion, guardar, verificar_espacio

DATASET = "http://datos.susalud.gob.pe/dataset/consulta-d1-producci%C3%B3n-asistencial-en-hospitalizaci%C3%B3n-{anio}"
MONTOS = {"NRO_TOTAL_CAMAS": "camas", "DIAS_CAMA_DISPONIBLE": "dias_cama", "NRO_TOTAL_HOSPIT_ING": "ingresos",
          "NRO_TOTAL_HOSPIT_EGR": "egresos", "NRO_TOTAL_PACIENTES_CAMAS": "pacientes_dia"}
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "setiembre", "octubre",
         "noviembre", "diciembre"]


def ultimo_csv():
    """URL del CSV del último mes publicado (del año en curso o, en enero, del anterior)."""
    for anio in (date.today().year, date.today().year - 1):
        try:
            pagina = abrir(DATASET.format(anio=anio)).read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code == 404:  # el conjunto del año aún no existe (enero): se prueba el año anterior
                continue
            raise
        # un error de conexión (tiempo agotado, conexión rechazada) no se oculta: se informa tal cual
        enlaces = set(re.findall(r'http[^"]*Consulta_D1_Hospitalizaciones_(\d{4})_(\d+)\.csv', pagina))
        if enlaces:
            a, m = max(enlaces, key=lambda e: (int(e[0]), int(e[1])))
            return f"http://datos.susalud.gob.pe/sites/default/files/Consulta_D1_Hospitalizaciones_{a}_{m}.csv"
    raise SystemExit("La página de SUSALUD respondió, pero no tiene enlaces a CSV de la Consulta D1.")


def resumir(d):
    """Suma por establecimiento. Devuelve una lista de dicts ordenada por número de camas."""
    p = d[d["DEPARTAMENTO"] == "PIURA"].copy()
    p["reporto"] = p["NRO_TOTAL_CAMAS"] != "NE_0001"
    for c in MONTOS:
        p[c] = pd.to_numeric(p[c], errors="coerce").fillna(0)
    p["uci"] = p["NRO_TOTAL_CAMAS"].where(p["HOSPITALIZACION"].fillna("").str.contains("CUIDADOS INTENSIVOS"), 0)
    g = p.groupby(["CO_IPRESS", "RAZON_SOC", "PROVINCIA", "DISTRITO", "SECTOR", "CATEGORIA"], dropna=False)
    r = g.agg(**{v: (k, "sum") for k, v in MONTOS.items()}, uci=("uci", "sum"), reporto=("reporto", "any"))
    r = r.reset_index().sort_values(["reporto", "camas"], ascending=False)
    r.columns = [c.lower() for c in r.columns]
    return [{k: (int(v) if isinstance(v, float) else v) for k, v in f.items()} for f in r.to_dict("records")]


def main():
    verificar_espacio()
    url = ultimo_csv()
    print("Leyendo", url)
    with abrir(url) as r:
        d = pd.read_csv(r, sep=";", dtype=str, encoding="utf-8")
    anio, mes = int(d["ANHO"].iloc[0]), int(d["MES"].iloc[0])
    filas = resumir(d)
    assert filas, "no hay establecimientos de Piura"
    reportaron = [f for f in filas if f["reporto"]]
    print(f"{MESES[mes - 1]} {anio}: {len(filas)} establecimientos de Piura, {len(reportaron)} reportaron, "
          f"{sum(f['camas'] for f in filas):,} camas ({sum(f['uci'] for f in filas)} de UCI)")
    guardar("camas_piura.json", {
        "fuente": "SUSALUD, Consulta D1: producción asistencial en hospitalización",
        "url": DATASET.format(anio=anio),
        "fecha_corte": fecha_modificacion(url),
        "periodo": f"{MESES[mes - 1]} de {anio}",
        "nota": "Dato mensual. Camas: total de camas reportadas en el mes. Días-cama disponibles: suma en el mes. "
                "Pacientes-día: suma de pacientes que ocuparon las camas cada día del mes. "
                "Ocupación = pacientes-día / días-cama disponibles.",
        "establecimientos": filas,
    })


if __name__ == "__main__":
    main()

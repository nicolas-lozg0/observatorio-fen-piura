"""
Guarda una fila por día con los indicadores clave en docs/data/historial.csv, para armar series en el tiempo.

Lee los JSON ya generados por los demás scripts (criterio de gasto: lugar del gasto). Si ya hay una fila con
la misma fecha, la reemplaza. Un indicador sin datos queda en blanco.
"""
import csv
import json
from datetime import datetime

from comun import DATOS, PERU

ARCHIVO = DATOS / "historial.csv"
COLUMNAS = ["fecha", "gasto_corte", "gasto_pim", "gasto_devengado", "p0068_pim", "p0068_devengado", "p0017_pim",
            "p0017_devengado", "anin_pim", "anin_devengado", "fen_marco", "fen_devengado", "obras_en_ejecucion",
            "obras_paralizadas", "dengue_se", "dengue_casos_semana", "dengue_casos_acumulados", "dengue_graves",
            "dengue_fallecidos"]


def leer(nombre):
    ruta = DATOS / nombre
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else None


def indicadores():
    fila = {"fecha": datetime.now(PERU).date().isoformat()}
    g = leer("gasto_piura.json")
    if g:
        rs = [dict(zip(g["columnas"], f)) for f in g["filas"]]
        rs = [r for r in rs if r["ambito"] & 1]  # lugar del gasto
        suma = lambda cond, k: round(sum(r[k] for r in rs if cond(r)))
        fila |= {"gasto_corte": g["fecha_corte"][:10],
                 "gasto_pim": suma(lambda r: True, "pim"), "gasto_devengado": suma(lambda r: True, "devengado"),
                 "p0068_pim": suma(lambda r: r["programa"] == "0068", "pim"),
                 "p0068_devengado": suma(lambda r: r["programa"] == "0068", "devengado"),
                 "p0017_pim": suma(lambda r: r["programa"] == "0017", "pim"),
                 "p0017_devengado": suma(lambda r: r["programa"] == "0017", "devengado"),
                 "anin_pim": suma(lambda r: r["nivel"] == "E" and r["entidad"] == "029", "pim"),
                 "anin_devengado": suma(lambda r: r["nivel"] == "E" and r["entidad"] == "029", "devengado")}
    f = leer("fen_piura.json")
    if f:
        rs = [dict(zip(f["columnas"], x)) for x in f["filas"] if x[0] & 1]
        fila |= {"fen_marco": round(sum(r["marco"] for r in rs)), "fen_devengado": round(sum(r["devengado"] for r in rs))}
    o = leer("infobras_piura.json")
    if o:
        fila |= {"obras_en_ejecucion": o["por_estado"].get("En Ejecución", 0),
                 "obras_paralizadas": o["por_estado"].get("Paralizada", 0)}
    d = leer("dengue_2026.json")
    if d and d.get("totales"):
        t = d["totales"]
        fila |= {"dengue_se": d["se"], "dengue_casos_semana": t["semana"], "dengue_casos_acumulados": t["casos"],
                 "dengue_graves": t["grave"],
                 # mismo criterio que los casos: defunciones confirmadas y probables
                 "dengue_fallecidos": (d.get("defunciones") or {}).get("total", "")}
    return fila


def main():
    filas = list(csv.DictReader(ARCHIVO.open(encoding="utf-8"))) if ARCHIVO.exists() else []
    nueva = indicadores()
    filas = [f for f in filas if f["fecha"] != nueva["fecha"]] + [nueva]
    with ARCHIVO.open("w", encoding="utf-8", newline="") as a:
        w = csv.DictWriter(a, COLUMNAS, extrasaction="ignore")
        w.writeheader()
        w.writerows(sorted(filas, key=lambda f: f["fecha"]))
    print(f"Historial: {len(filas)} fechas; hoy: {nueva}")


if __name__ == "__main__":
    main()

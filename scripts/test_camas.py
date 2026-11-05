"""Prueba mínima de resumir() de camas_susalud.py con datos inventados. Correr: python3 scripts/test_camas.py"""
import pandas as pd

from camas_susalud import resumir

COLS = ["DEPARTAMENTO", "PROVINCIA", "DISTRITO", "CO_IPRESS", "RAZON_SOC", "SECTOR", "CATEGORIA", "HOSPITALIZACION",
        "NRO_TOTAL_CAMAS", "DIAS_CAMA_DISPONIBLE", "NRO_TOTAL_HOSPIT_ING", "NRO_TOTAL_HOSPIT_EGR", "NRO_TOTAL_PACIENTES_CAMAS"]
filas = [
    # un hospital con dos servicios: uno común y uno de cuidados intensivos (UCI)
    ["PIURA", "PIURA", "PIURA", "001", "HOSPITAL A", "MINSA", "II-2", "MEDICINA", "20", "600", "50", "48", "450"],
    ["PIURA", "PIURA", "PIURA", "001", "HOSPITAL A", "MINSA", "II-2", "UNIDAD DE CUIDADOS INTENSIVOS", "5", "150", "3", "3", "120"],
    # un establecimiento que no reportó en el mes: SUSALUD pone NE_0001 en los montos
    ["PIURA", "SULLANA", "SULLANA", "002", "CENTRO B", "MINSA", "I-4", "MEDICINA", "NE_0001", "NE_0001", "NE_0001", "NE_0001", "NE_0001"],
    # fuera de Piura: no debe contarse
    ["LIMA", "LIMA", "LIMA", "003", "HOSPITAL C", "MINSA", "III-1", "MEDICINA", "99", "999", "9", "9", "999"],
]
r = {f["co_ipress"]: f for f in resumir(pd.DataFrame(filas, columns=COLS))}

assert set(r) == {"001", "002"}, "solo establecimientos de Piura"
a, b = r["001"], r["002"]
assert a["reporto"] and not b["reporto"], "NE_0001 = no reportó"
assert (a["camas"], a["uci"], a["dias_cama"], a["pacientes_dia"]) == (25, 5, 750, 570), a
assert (a["ingresos"], a["egresos"]) == (53, 51)
assert b["camas"] == 0 and b["uci"] == 0, "el que no reportó no suma camas"
assert [f["co_ipress"] for f in resumir(pd.DataFrame(filas, columns=COLS))] == ["001", "002"], "primero los que reportaron"
print("OK")

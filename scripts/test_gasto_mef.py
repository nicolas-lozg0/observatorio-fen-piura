"""Prueba mínima del filtro y la agregación de gasto_mef.py con datos inventados. Correr: python scripts/test_gasto_mef.py"""
import pandas as pd

from gasto_mef import COLUMNAS, agregar, filtrar_piura, resumen

filas = [
    # meta, sede, nivel, nivel_nombre, pliego, pliego_nombre, sec_ejec, ejecutora, programa, programa_nombre, tipo, código, código_nombre, PIA, PIM, devengado
    ["PIURA", "LIMA", "E", "GOB NAC", "029", "ANIN", "1750", "ANIN", "0068", "PREV", "2", "2000001", "OBRA A", "100", "200", "0"],
    ["PIURA", "LIMA", "E", "GOB NAC", "029", "ANIN", "1750", "ANIN", "0068", "PREV", "2", "2000001", "OBRA A", "0", "0", "50"],
    ["PIURA", "PIURA", "M", "GOB LOC", " ", " ", "301234", "MUNI CASTILLA", "0017", "METAX", "3", "3000001", "ACT B", "0", "100", "25"],
    ["LIMA", "PIURA", "R", "GOB REG", "457", "GORE", "0001", "SEDE", "9001", "APNOP", "3", "3999999", "ACT C", "0", "40", "40"],
    ["LIMA", "LIMA", "E", "GOB NAC", "001", "PCM", "0001", "PCM", "9001", "APNOP", "3", "3999999", "ACT C", "0", "999", "999"],
]
df = pd.DataFrame(filas, columns=COLUMNAS)
agr = agregar(filtrar_piura(df))

assert len(agr) == 3, "debe excluir la fila de Lima y juntar las dos filas de OBRA A"
assert sorted(agr["AMBITO"]) == [1, 2, 3]
assert set(agr["ENTIDAD"]) == {"029", "301234", "457"}, "municipalidad = ejecutora; resto = pliego"
lugar, sede = resumen(agr, 1), resumen(agr, 2)
assert lugar.loc["TOTAL", "MONTO_PIM"] == 300 and lugar.loc["TOTAL", "MONTO_DEVENGADO"] == 75
assert lugar.loc["TOTAL", "AVANCE"] == 25
assert sede.loc["TOTAL", "MONTO_PIM"] == 140 and sede.loc["TOTAL", "MONTO_DEVENGADO"] == 65
print("OK")

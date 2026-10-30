"""Prueba rápida, con datos inventados, de la lectura de números del PDF y del conteo de casos históricos."""
import pandas as pd

from dengue_diresa import NoCuadra, n
from dengue_historico import contar

# Números del PDF: miles con coma, decimales, porcentajes; un valor cortado debe rechazarse
assert n("14,789") == 14789 and n("68.23") == 68.23 and n("18.06%") == 18.06 and n("7") == 7
for cortado in ["1,1", "12,26", ".8", "1,1958"]:
    try:
        n(cortado)
        raise AssertionError(f"debió rechazar {cortado!r}")
    except NoCuadra:
        pass

# Conteo histórico: dos filas idénticas son dos casos; solo cuenta Piura
caso = {"departamento": "PIURA", "enfermedad": "DENGUE GRAVE", "ano": "2023", "semana": "10",
        "tipo_dx": "C", "ubigeo": "200101"}
df = pd.DataFrame([caso, caso, {**caso, "tipo_dx": "P"}, {**caso, "departamento": "TUMBES"}])
agr, piura = contar(df)
assert len(piura) == 3 and agr["casos"].sum() == 3
assert agr.set_index("tipo_dx").loc["C", "casos"] == 2
print("OK")

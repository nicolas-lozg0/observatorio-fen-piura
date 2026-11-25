"""Prueba de precios_sisap.py: reglas de las ventanas y cifras de control (verificadas a mano el 24/11/2026).
Uso: python3 scripts/test_precios_sisap.py"""
import json
from datetime import date

from precios_sisap import HISTORIAL, calcular, leer_exportacion, ventanas

# Ventanas: el mes del corte si tiene 2 fechas o más; si no, el mes anterior completo. Base: 2.ª quincena del mes previo.
nov = [date(2026, 11, d) for d in (4, 11)]
assert ventanas(date(2026, 11, 11), nov) == ((2026, 11, 11), (2026, 10)), "noviembre con 2 fechas"
assert ventanas(date(2026, 12, 2), nov + [date(2026, 12, 2)]) == ((2026, 11, 31), (2026, 10)), "diciembre con 1 fecha: noviembre"
assert ventanas(date(2027, 1, 20), [date(2027, 1, 5), date(2027, 1, 20)]) == ((2027, 1, 20), (2026, 12)), "enero: base en diciembre"

# Cifras de control con el historial guardado, corte del 23/11/2026 (las del informe de factibilidad)
r = calcular(json.loads(HISTORIAL.read_text(encoding="utf-8"))["precios"], "2026-11-23")
p = {x["nombre"]: x for x in r["productos"]}
assert r["base"] == ["2026-10-16", "2026-10-31"] and r["reciente"] == ["2026-11-01", "2026-11-23"]
assert p["Zanahoria"]["mayorista"]["var"] == 11.5 and p["Zanahoria"]["mayorista"]["habitual"] == -1.5
assert p["Papa amarilla"]["minorista"]["var"] == 29.5 and p["Papa amarilla"]["minorista"]["habitual"] == -9.1
assert p["Tomate"]["mayorista"]["habitual"] is None, "tomate: un solo año de historial, sin «habitual»"
assert p["Lenteja"]["mayorista"]["habitual"] == -0.8, "lenteja: 3 años, el mínimo"

# Productos agregados, nombres simples (con el original del SISAP) y mínimo de 2 fechas por periodo de 2026
assert p["Cebolla roja"]["mayorista"]["var"] == 9.1 and p["Cebolla roja"]["mayorista"]["habitual"] == -1.5
assert p["Pollo"]["sisap"] == "Carne de pollo (eviscerado)" and "sin vísceras" in p["Pollo"]["descripcion"]
assert p["Ajo"]["mayorista"]["habitual"] == -6.9 and p["Ajo"]["sisap"] == "Ajo criollo o napuri"
assert p["Zanahoria"]["mayorista"]["fechas"]["2026"] == [3, 4] and p["Zanahoria"]["mayorista"]["suficiente"]
assert p["Camote morado"]["mayorista"]["fechas"]["2026"] == [2, 4] and p["Camote morado"]["mayorista"]["suficiente"], "2 fechas: entra"
assert r["minimo_fechas"] == 2 and all(x[t]["suficiente"] for x in r["productos"] for t in ("mayorista", "minorista"))
# Lo habitual usa las mismas ventanas de fechas en cada año (16-31 oct. frente a 1-23 nov.)
from precios_sisap import tramo
assert [tramo(a, 10, 16, 31) for a in (2022, 2025)] == [("2022-10-16", "2022-10-31"), ("2025-10-16", "2025-10-31")]
assert tramo(2022, 11, 1, 31) == ("2022-11-01", "2022-11-30"), "noviembre completo se recorta al 30"

# Lectura de una celda exportada: saco de 50 kg → S/ por kg
celda = '<td class=numero rel="16/11/2026,Saco normal(50 kg./lt.)~Piura,Arroz superior,Mayorista">136.50</td>'
from pathlib import Path
import tempfile
with tempfile.TemporaryDirectory() as t:
    f = Path(t) / "x.xls"; f.write_text(celda, encoding="latin-1")
    assert list(leer_exportacion(f)) == [("2026-11-16", "Arroz superior", "mayorista", 2.73)]
# Ronda del 24/11/2026: huevos, procesados, mango, empalme del aceite y promedio ponderado por los pesos del IPC
from precios_sisap import PESO, PRODUCTOS, SUBCLASES
assert p["Huevos"]["sisap"] == "Huevos rosados" and len(r["productos"]) == 23
assert {n for n, _, _ in PRODUCTOS} == set(PESO), "cada producto tiene su subclase del IPC"
assert abs(sum(x["peso"] for x in r["productos"]) - sum(w for _, w, _ in SUBCLASES.values())) < 1e-3
assert p["Aceite vegetal"]["mayorista"]["anios"]["2022"] is not None, "aceite: 2022 sale de la botella de 1 l (empalme)"
assert p["Azúcar rubia"]["mayorista"]["var"] == 10.0 and p["Mango"]["mayorista"]["habitual"] == -1.3
assert r["promedio"]["mayorista"] == {"var": 3.3, "habitual": -0.2, "n": 21}
from precios_sisap import promedio_ponderado
f = lambda v, h: {"suficiente": True, "var": v, "habitual": h}
assert promedio_ponderado([{"peso": 3, "t": f(10, 0)}, {"peso": 1, "t": f(-2, 4)}, {"peso": 9, "t": f(50, None)}], "t") == \
    {"var": 7.0, "habitual": 1.0, "n": 2}, "pondera y deja fuera los que no tienen lo habitual"

# Series mensuales y canasta estimada (precios_mensual.py, 25/11/2026)
from precios_mensual import CORRESPONDENCIA, mensual, separacion
assert separacion([1, 3, 1, 3, 4, 5]) == 4, "se separa desde el primer mes que ya no vuelve bajo el umbral"
assert separacion([-3, -4, -5]) == 1 and separacion([3, 4, 1]) is None and separacion([None, 3, None, 4]) == 2
assert mensual({"2026-01-05": 2.0, "2026-01-20": 4.0, "2026-01-28": 9.0}, 2026, 1, hasta=25) == 3.0, "mes parcial: hasta el día de corte"
assert mensual({"2026-01-05": 2.0}, 2026, 1) is None, "menos de 2 fechas: mes vacío"
DATOS = HISTORIAL.parent.parent / "docs" / "data"
pesos = json.loads((DATOS / "canasta_pesos.json").read_text(encoding="utf-8"))
assert len(pesos["productos"]) == 110 and abs(pesos["total_valor"] - 4.2727) < 1e-3, "canasta de Costa urbana: 110 productos, S/ 4,27 al día"
assert {n for n, _ in CORRESPONDENCIA.values()} <= {f["n"] for f in pesos["productos"] if f["valor_costa_urbana"] > 0}
c = json.loads((DATOS / "canasta_estimada.json").read_text(encoding="utf-8"))
x = c["minorista"]
assert 30 < x["cobertura"] < 40 and abs(c["fuera_del_hogar"] - 31.3) < 0.1
for a, r in x["anios"].items():  # (b) = cubierta × cobertura + resto con el IPC (alimentos dentro del hogar, restaurantes fuera)
    cob, f = x["cobertura"] / 100, c["fuera_del_hogar"] / 100
    assert abs(r["b"] - (cob * r["cubierta"] + (1 - cob - f) * r["ipc"]["alimentos"] + f * r["ipc"]["restaurantes"])) < 0.02, a
assert x["anios"]["2026"]["ipc"] == {"alimentos": 5.86, "restaurantes": 3.83}, "IPC nacional ene.-oct. 2026 (INEI, Cuadro 1)"
m = json.loads((DATOS / "precios_mensual.json").read_text(encoding="utf-8"))
pm = {q["nombre"]: q for q in m["productos"]}
z = pm["Zanahoria"]["anios"]["2026"]
assert abs(z["precio"][0] / z["diciembre_anterior"] * 100 - z["indice"][0]) < 0.01, "índice: diciembre anterior = 100"
assert pm["Papa yungay"]["acumulada"] is None, "papa yungay: sin diciembre de 2023, sin lo habitual"
assert m["diesel"]["sube_desde"] == 3 and m["shocks"]["enfen"]["fecha"] == "2026-02-13"
print("test_precios_sisap: todo bien")

"""
Precio mensual del diésel en Piura (Osinergmin): precio promedio del DIESEL B5 S-50 UV en grifos y estaciones de servicio
(EESS) del departamento de Piura, en soles por galón, desde diciembre de 2023 (la base del índice de 2024).

Fuente: Osinergmin, División de Supervisión Regional, «Reporte mensual de precios» (datos del sistema PRICE), un PDF por
mes, página 2 («EESS/GRIFOS Y GASOCENTROS»). Los PDF se guardan en data/raw/osinergmin/ (fuera del repositorio).
Uso: python3 scripts/diesel_osinergmin.py   →   docs/data/diesel_piura.json
"""
from datetime import date

import pdfplumber

from comun import RAIZ, abrir, guardar

CRUDO = RAIZ / "data" / "raw" / "osinergmin"
URL = "https://www.osinergmin.gob.pe/seccion/centro_documental/hidrocarburos/SCOP/SCOP-DOCS/{a}/Reporte-Mensual-Precios-{m}-{a}.pdf"
MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Setiembre", "Octubre", "Noviembre", "Diciembre"]
COLUMNA = "DIESEL B5 S-50 UV"
DESDE = (2023, 12)  # diciembre de 2023: la base del índice de 2024


def bajar(a, m):
    """PDF del mes (de la carpeta local si ya está). Prueba «Setiembre» y «Septiembre». None si aún no se publica."""
    ruta = CRUDO / f"{a}-{m:02d}.pdf"
    if ruta.exists():
        return ruta
    for nombre in [MESES[m - 1]] + (["Septiembre"] if m == 9 else []):
        try:
            with abrir(URL.format(a=a, m=nombre), intentos=1) as r:
                datos = r.read()
        except OSError:
            continue
        if datos[:5] == b"%PDF-":
            CRUDO.mkdir(parents=True, exist_ok=True)
            ruta.write_bytes(datos)
            return ruta
    return None


def leer(ruta):
    """Precio de COLUMNA en la fila PIURA de la tabla de grifos (la página que dice «EESS»)."""
    with pdfplumber.open(ruta) as pdf:
        for pagina in pdf.pages:
            if "EESS" not in (pagina.extract_text() or ""):
                continue
            for tabla in pagina.extract_tables():
                cab = next((f for f in tabla if f and f[0] == "DEPARTAMENTO"), None)
                if not cab:
                    continue
                k = [(c or "").replace("\n", " ") for c in cab].index(COLUMNA)
                fila = next((f for f in tabla if f and (f[0] or "").strip() == "PIURA"), None)
                return float(fila[k]) if fila and fila[k] else None
    return None


def main():
    hoy, serie = date.today(), []
    a, m = DESDE
    while (a, m) < (hoy.year, hoy.month):
        ruta = bajar(a, m)
        if ruta is None:
            print(f"{a}-{m:02d}: sin reporte publicado")
        else:
            v = leer(ruta)
            print(f"{a}-{m:02d}: {v}")
            serie.append({"mes": f"{a}-{m:02d}", "precio": v})
        a, m = (a + 1, 1) if m == 12 else (a, m + 1)
    assert sum(1 for x in serie if x["precio"]) >= 12, "muy pocos meses con precio: ¿cambió el formato del reporte?"
    guardar("diesel_piura.json", {
        "fuente": "Osinergmin, Reporte mensual de precios de combustibles (sistema PRICE), grifos y estaciones de servicio",
        # el reporte del último mes con precio (cada mes tiene su PDF)
        "url": (lambda ult: URL.format(a=ult[:4], m=MESES[int(ult[5:]) - 1]))(next(x["mes"] for x in reversed(serie) if x["precio"])),
        "producto": "Diésel B5 S-50 UV, soles por galón, promedio del departamento de Piura",
        "fecha_corte": next(x["mes"] for x in reversed(serie) if x["precio"]),
        "serie": serie})


if __name__ == "__main__":
    main()

"""
Líneas de pobreza del INEI: valor mensual por persona de la canasta básica de alimentos (pobreza extrema) y de la
canasta básica total (pobreza total), para los dominios Costa urbana y Costa rural (los de Piura) y el nacional.

Fuente: INEI, "Perú: Evolución de la Pobreza Monetaria 2016-2025. Informe Técnico" (mayo de 2026), Cuadros N° 3.1
(línea de pobreza extrema) y N° 3.2 (línea de pobreza total). El INEI no publica las líneas por departamento.
El informe sale una vez al año (en mayo): para actualizar, cambiar INFORME y PAGINA por los de la nueva edición,
correr el script a mano y revisar el CONTROL. Resultado: docs/data/lineas_pobreza.json.
"""
import re
import tempfile
from pathlib import Path

from pypdf import PdfReader

from comun import descargar, guardar, verificar_espacio

PAGINA = "https://www.gob.pe/institucion/inei/informes-publicaciones/8087825"
INFORME = "https://cdn.www.gob.pe/uploads/document/file/9911234/8087825-informe-tecnico-de-pobreza-monetaria-2016-2025.pdf"
CUADROS = {"extrema": "CUADRO N° 3.1", "total": "CUADRO N° 3.2"}
FILAS = {"Nacional": "nacional", "Costa urbana": "costa_urbana", "Costa rural": "costa_rural"}
# Valores de 2025 verificados a mano en el informe (págs. 59 y 63): si la lectura no los da, el script se detiene
CONTROL = {("extrema", 2025): {"nacional": 260, "costa_urbana": 247, "costa_rural": 215},
           ("total", 2025): {"nacional": 462, "costa_urbana": 465, "costa_rural": 371}}


def leer_cuadro(texto, titulo):
    """{fila: [valores por año]} y los años, del cuadro cuyo título empieza con `titulo`."""
    anios = re.search(r"(\d{4})\s*-\s*(\d{4})", texto[texto.index(titulo):])
    a0, a1 = int(anios.group(1)), int(anios.group(2))
    n = a1 - a0 + 1
    filas = {}
    for linea in texto.splitlines():
        for nombre, clave in FILAS.items():
            m = re.match(rf"{nombre} ((?:\d+ ){{{n - 1}}}\d+)\b", linea.strip())
            if m and clave not in filas:  # la primera aparición (Nacional aparece antes que los dominios)
                filas[clave] = [int(x) for x in m.group(1).split()]
    return list(range(a0, a1 + 1)), filas


assert leer_cuadro("CUADRO N° 3.1 X 2016-2018\nNacional 1 2 3 1,8\nCosta urbana 4 5 6 0,1\nCosta rural 7 8 9 1,0",
                   "CUADRO N° 3.1") == ([2016, 2017, 2018], {"nacional": [1, 2, 3], "costa_urbana": [4, 5, 6], "costa_rural": [7, 8, 9]})


def main():
    verificar_espacio()
    with tempfile.TemporaryDirectory() as tmp:
        pdf = Path(tmp) / "informe.pdf"
        descargar(INFORME, pdf)
        # pypdf y no pdfplumber: en este informe pdfplumber lee los cuadros letra por letra, en columnas
        paginas = [p.extract_text() or "" for p in PdfReader(pdf).pages]
    lineas = {}
    for tipo, titulo in CUADROS.items():
        texto = next(t for t in paginas if titulo in t and "LÍNEA DE POBREZA" in t)
        anios, filas = leer_cuadro(texto, titulo)
        assert set(filas) == set(FILAS.values()), f"{titulo}: faltan filas {set(FILAS.values()) - set(filas)}"
        lineas[tipo] = {"anios": anios, **filas}
        print(tipo, anios[0], "a", anios[-1], {k: v[-1] for k, v in filas.items()})
    for (tipo, anio), esperado in CONTROL.items():
        i = lineas[tipo]["anios"].index(anio)
        leido = {k: lineas[tipo][k][i] for k in esperado}
        assert leido == esperado, f"{tipo} {anio}: se leyó {leido}, el informe dice {esperado}"
    guardar("lineas_pobreza.json", {
        "fuente": "INEI, Perú: Evolución de la Pobreza Monetaria 2016-2025, Informe Técnico (Cuadros N° 3.1 y 3.2)",
        "url": PAGINA,
        "fecha_corte": "2026-05-01",  # publicación del informe (mayo de 2026); el último año de las líneas es 2025
        "nota": "Soles por persona al mes. Extrema: canasta básica de alimentos. Total: canasta básica total "
                "(alimentos y otros bienes y servicios). El INEI no publica las líneas por departamento.",
        "lineas": lineas,
    })


if __name__ == "__main__":
    main()

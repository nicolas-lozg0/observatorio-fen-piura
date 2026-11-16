"""
Estado del sistema de alerta del ENFEN según su último comunicado oficial (pestaña Clima).

La portada de https://enfen.imarpe.gob.pe/ enlaza el comunicado más reciente (PDF). El RSS del sitio llega con
retraso (el 16/11/2026 aún no tenía el N° 20), por eso se usa la portada. Del PDF se toman el número, la fecha y el
estado («No activo», «Vigilancia de El Niño Costero», «Alerta de La Niña Costera»…), que aparecen en su encabezado.

Resultado: docs/data/enfen.json. Uso: python3 scripts/enfen.py
"""
import html
import re
import sys
import tempfile
from datetime import date
from pathlib import Path

from pypdf import PdfReader

from comun import abrir, descargar, guardar

PORTADA = "https://enfen.imarpe.gob.pe/"
COMUNICADOS = "https://enfen.imarpe.gob.pe/comunicados/"
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "setiembre", "octubre", "noviembre", "diciembre"]
ESTADO = re.compile(r"(No activo|(?:Vigilancia|Alerta) de (?:El Niño|La Niña) Coster[oa])", re.I)


def leer_comunicado(texto):
    """(número, fecha, estado) del encabezado del comunicado; sale con error si falta alguno."""
    n = re.search(r"COMUNICADO OFICIAL ENFEN\s*N\s*°\s*(\d+)\s*[-–]\s*(\d{4})", texto, re.I)
    f = re.search(r"(\d{1,2})\s+(?:de\s+)?(" + "|".join(MESES) + r")\s+(?:de\s+)?(\d{4})", texto[:600], re.I)
    e = ESTADO.search(texto[:800])
    if not (n and f and e):
        sys.exit(f"No se pudo leer número ({bool(n)}), fecha ({bool(f)}) o estado ({bool(e)}) del comunicado")
    fecha = date(int(f.group(3)), MESES.index(f.group(2).lower()) + 1, int(f.group(1)))
    estado = e.group(1)[0].upper() + e.group(1)[1:].lower().replace("el niño", "El Niño").replace("la niña", "La Niña")
    return f"{n.group(1)}-{n.group(2)}", fecha, estado


def main():
    with abrir(PORTADA, timeout=90) as r:
        portada = r.read().decode("utf-8", "replace")
    enlaces = [(html.unescape(u), " ".join(re.sub("<[^>]+>", " ", t).split()))
               for u, t in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', portada, re.S)]
    com = [(u, t) for u, t in enlaces if re.search(r"comunicado oficial enfen n", t, re.I) and "/download/" in u]
    if not com:
        sys.exit("No se encontró el enlace al comunicado en la portada del ENFEN (¿cambió la página?)")
    url = re.sub(r"&refresh=[^&]*", "", com[0][0])  # «refresh» cambia en cada visita; el PDF es el mismo
    with tempfile.TemporaryDirectory() as tmp:
        pdf = Path(tmp) / "comunicado.pdf"
        descargar(url, pdf)
        texto = " ".join(" ".join((p.extract_text() or "") for p in PdfReader(pdf).pages[:2]).split())
    numero, fecha, estado = leer_comunicado(texto)
    print(f"Comunicado N° {numero} del {fecha}: {estado}")
    guardar("enfen.json", {
        "fuente": "ENFEN, comunicado oficial",
        "url": url,
        "pagina": COMUNICADOS,
        "fecha_corte": fecha.isoformat(),
        "numero": numero,
        "estado": estado,
    })


if __name__ == "__main__":
    main()

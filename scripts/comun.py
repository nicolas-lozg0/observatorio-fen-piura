"""Funciones compartidas por los scripts: control de espacio en disco, fechas y guardado de JSON."""
import email.utils
import json
import shutil
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "docs" / "data"  # GitHub Pages publica docs/, así que los datos van dentro
MINIMO_MB = 500
PERU = timezone(timedelta(hours=-5))


def verificar_espacio():
    """Detiene el script si el espacio libre en disco baja del mínimo."""
    libre = shutil.disk_usage(RAIZ).free / 2**20
    if libre < MINIMO_MB:
        sys.exit(f"Detenido: quedan {libre:.0f} MB libres en disco (mínimo {MINIMO_MB} MB).")


def fecha_modificacion(url):
    """Fecha de última modificación del archivo en el servidor (hora de Perú), o None."""
    with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=60) as r:
        lm = r.headers.get("Last-Modified")
    return email.utils.parsedate_to_datetime(lm).astimezone(PERU).isoformat(timespec="minutes") if lm else None


def descargar(url, destino):
    """Descarga a un archivo revisando el espacio libre cada 8 MB."""
    with urllib.request.urlopen(url, timeout=120) as r, open(destino, "wb") as f:
        while bloque := r.read(8 * 2**20):
            f.write(bloque)
            verificar_espacio()


def guardar(nombre, datos):
    """Guarda un JSON compacto en docs/data con la hora de proceso."""
    DATOS.mkdir(parents=True, exist_ok=True)
    datos["procesado"] = datetime.now(PERU).isoformat(timespec="minutes")
    ruta = DATOS / nombre
    ruta.write_text(json.dumps(datos, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Guardado {ruta.relative_to(RAIZ)} ({ruta.stat().st_size / 1024:.0f} KB)")

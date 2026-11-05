"""Funciones compartidas por los scripts: control de espacio en disco, fechas y guardado de JSON."""
import email.utils
import json
import shutil
import sys
import time
import urllib.error
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


def abrir(url, timeout=180, intentos=3, espera=20, metodo=None):
    """urlopen con reintentos: 3 intentos, con 20 y 40 s de espera entre ellos (espera creciente).
    Algunos portales del Estado tardan o cortan la conexión de vez en cuando."""
    req = urllib.request.Request(url, method=metodo, headers={"User-Agent": "Mozilla/5.0 (observatorio-fen-piura)"})
    for i in range(1, intentos + 1):
        try:
            return urllib.request.urlopen(req, timeout=timeout)
        except OSError as e:  # URLError y TimeoutError heredan de OSError
            # un 4xx (404, 403…) es una respuesta del servidor, no una caída: reintentar no cambia nada
            if i == intentos or (isinstance(e, urllib.error.HTTPError) and 400 <= e.code < 500):
                raise
            print(f"  Intento {i} de {intentos} falló ({e}); nuevo intento en {espera * i} s", flush=True)
            time.sleep(espera * i)


def fecha_modificacion(url):
    """Fecha de última modificación del archivo en el servidor (hora de Perú), o None."""
    with abrir(url, metodo="HEAD", timeout=60) as r:
        lm = r.headers.get("Last-Modified")
    return email.utils.parsedate_to_datetime(lm).astimezone(PERU).isoformat(timespec="minutes") if lm else None


def descargar(url, destino):
    """Descarga a un archivo revisando el espacio libre cada 8 MB."""
    with abrir(url) as r, open(destino, "wb") as f:
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

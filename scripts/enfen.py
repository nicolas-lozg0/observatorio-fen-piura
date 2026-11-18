"""
Aviso de comunicado nuevo del ENFEN (no escribe datos).

La tarjeta del ENFEN se llena a mano en docs/data/enfen_comunicado.json (ver scripts/actualizacion_local.md). Este script
revisa la portada de https://enfen.imarpe.gob.pe/, que enlaza los comunicados oficiales, y falla con un mensaje si hay
uno más reciente que el del JSON. En GitHub Actions el paso queda marcado y el resumen lo dice.

Uso: python3 scripts/enfen.py
"""
import json
import re
import sys

from comun import DATOS, abrir

PORTADA = "https://enfen.imarpe.gob.pe/"


def numeros(html):
    """Números de comunicado oficial enlazados en la portada: [(año, número), …]."""
    return [(int(a), int(n)) for n, a in re.findall(r"Comunicado Oficial Enfen N\s*°\s*(\d+)\s*[-–]\s*(\d{4})", html, re.I)]


def main():
    actual = json.loads((DATOS / "enfen_comunicado.json").read_text(encoding="utf-8"))["numero"]
    n, a = map(int, actual.split("-"))
    with abrir(PORTADA, timeout=90) as r:
        hay = numeros(r.read().decode("utf-8", "replace"))
    if not hay:
        sys.exit("No se encontraron comunicados en la portada del ENFEN (¿cambió la página?)")
    ultimo = max(hay)
    if ultimo > (a, n):
        sys.exit(f"Hay un comunicado nuevo del ENFEN (N.° {ultimo[1]}-{ultimo[0]}): actualiza docs/data/enfen_comunicado.json "
                 f"(ahora tiene el N.° {actual}). Instrucciones en scripts/actualizacion_local.md.")
    print(f"El JSON tiene el último comunicado (N.° {actual}).")


if __name__ == "__main__":
    main()

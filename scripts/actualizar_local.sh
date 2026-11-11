#!/usr/bin/env bash
# Actualiza desde esta computadora las fuentes que no responden a los servidores de GitHub:
# Infobras (obras) y SUSALUD (camas del último mes, serie de 24 meses y ubicación RENIPRESS). Luego hace commit
# y push solo de esos archivos de datos.
# Uso:  scripts/actualizar_local.sh            (actualiza, hace commit y push)
#       scripts/actualizar_local.sh --sin-push (actualiza y hace commit, sin push; para probar)
# Instrucciones: docs/actualizacion_local.md
set -u

cd "$(dirname "$0")/.." || exit 1
ARCHIVOS="docs/data/infobras_piura.json docs/data/infobras_departamentos.json docs/data/camas_piura.json docs/data/camas_serie.json docs/data/ipress_piura.json"
PUSH=1
[ "${1:-}" = "--sin-push" ] && PUSH=0

# Antes de empezar: rama main y sin cambios pendientes en esos archivos (para no mezclar otra cosa en el commit)
if [ "$(git branch --show-current)" != "main" ]; then
  echo "Estás en la rama $(git branch --show-current); cámbiate a main (git checkout main) y vuelve a correrlo."
  exit 1
fi
if ! git diff --quiet -- $ARCHIVOS || ! git diff --cached --quiet; then
  echo "Hay cambios sin guardar en los datos o en el área de preparación (git status). Resuélvelos antes."
  exit 1
fi

echo "== Trayendo la última versión del repositorio"
git pull --rebase --autostash --quiet || { echo "No se pudo hacer git pull; revisa la conexión o los conflictos."; exit 1; }

fallos=""
echo "== Infobras (descarga un Excel de ~57 MB; tarda unos 5 minutos)"
python3 scripts/infobras.py || fallos="$fallos infobras.py"
echo "== SUSALUD, camas (último mes publicado)"
# primero la prueba del cálculo: si SUSALUD cambió algo y la prueba falla, no se actualizan las camas
python3 scripts/test_camas.py && python3 scripts/camas_susalud.py || fallos="$fallos camas_susalud.py"
echo "== SUSALUD, serie de 24 meses (unos 30 MB; SUSALUD revisa meses pasados, por eso se recalculan todos)"
python3 scripts/test_camas.py >/dev/null && python3 scripts/camas_serie.py || fallos="$fallos camas_serie.py"
echo "== RENIPRESS, ubicación de los establecimientos (unos 20 MB)"
python3 scripts/renipress.py || fallos="$fallos renipress.py"

git add $ARCHIVOS
if git diff --cached --quiet; then
  echo "== Sin cambios en los datos: no hay nada que subir."
else
  git commit --quiet -m "Actualiza Infobras y SUSALUD (local) $(date +%F)" -- $ARCHIVOS
  echo "== Commit creado: $(git log --oneline -1)"
  if [ "$PUSH" = 1 ]; then
    # el workflow diario pudo subir datos mientras tanto: se trae antes de subir
    git pull --rebase --autostash --quiet && git push --quiet && echo "== Subido a GitHub. La página se actualiza en 1 o 2 minutos." \
      || { echo "No se pudo subir (git push). El commit quedó en tu computadora; vuelve a intentar con: git pull --rebase && git push"; exit 1; }
  else
    echo "== --sin-push: el commit quedó solo en tu computadora. Para subirlo: git push"
  fi
fi

if [ -n "$fallos" ]; then
  echo "ATENCIÓN: fallaron:$fallos. Sus datos anteriores se conservan; revisa los mensajes de arriba."
  exit 1
fi
echo "== Listo."

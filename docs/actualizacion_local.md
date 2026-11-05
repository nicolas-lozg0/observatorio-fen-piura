# Actualización local: Infobras y camas (SUSALUD)

Dos fuentes no se pueden actualizar desde GitHub y hay que hacerlo desde una computadora: **Infobras** (obras en ejecución y paralizadas) y **SUSALUD** (camas y ocupación hospitalaria). El script `scripts/actualizar_local.sh` las descarga, procesa y sube a GitHub en un solo paso.

## Por qué no van en la actualización automática

- **Ambos sitios no responden a los servidores de GitHub.** Fallaron con tiempo agotado en todas las ejecuciones del workflow diario desde que se creó (30/10/2026), y también con 3 reintentos y 3 minutos de espera.
- **Desde una computadora en Perú responden en segundos.** Infobras tarda unos 5 minutos en total, sobre todo por leer su Excel de 57 MB; SUSALUD tarda unos 5 segundos.
- **Probable causa:** que bloqueen o no atiendan conexiones desde el extranjero o desde centros de datos. No está confirmado con la Contraloría ni con SUSALUD.
- **El resto sigue automático:** MEF (gasto, emergencia FEN, avance de proyectos) e IPC, a diario con `.github/workflows/actualizar.yml`; dengue 2026, cada viernes con `.github/workflows/dengue.yml`.

## Cuándo usarlo

| Fuente | Cada cuánto publica | Cuándo correr el script | La página avisa "Dato no actualizado" a los |
| --- | --- | --- | --- |
| Infobras | Diario, aunque el archivo de datos abiertos no trae avances desde marzo de 2026 | **Una vez al mes** (por ejemplo, la primera semana) | 35 días |
| SUSALUD, camas | Mensual, con uno o dos meses de retraso | En la misma corrida mensual; el mes nuevo suele aparecer hacia fin de mes | 45 días |

La forma más simple de recordarlo: si en la página aparece **"Dato no actualizado desde [fecha]"** junto a las cifras de obras o de camas, toca correr el script. Correrlo más seguido no hace daño. Si no hay datos nuevos, no sube nada; Infobras cambia la fecha de consulta cada día, así que casi siempre habrá un commit.

## Cómo usarlo

Una sola vez, en la computadora, instala las dependencias:

```
cd "/Users/rodrig/Documentos (Local)/FEC2026-RA/observatorio-fen-piura"
pip3 install -r requirements.txt
```

Cada vez que toque actualizar, desde la carpeta del proyecto:

```
scripts/actualizar_local.sh
```

Para probar sin subir nada a GitHub:

```
scripts/actualizar_local.sh --sin-push
```

Necesitas conexión a internet y permiso para hacer `git push` al repositorio. Ese permiso ya está configurado en esta computadora: es el mismo que se usa para subir cambios.

## Qué hace, paso a paso

1. Comprueba que estés en la rama `main` y que no haya cambios a medias en los datos de obras o camas.
2. Trae la última versión del repositorio (`git pull --rebase`); los cambios tuyos en otros archivos se guardan y se reponen solos.
3. Corre `scripts/infobras.py` y `scripts/camas_susalud.py`. Cada uno reintenta hasta 3 veces si el sitio no responde. Si uno falla, el otro igual corre y se conservan los datos anteriores del que falló.
4. Hace un commit **solo** con `docs/data/infobras_piura.json` y `docs/data/camas_piura.json`, con el mensaje "Actualiza Infobras y camas (local) AAAA-MM-DD".
5. Vuelve a traer cambios (el workflow diario pudo subir datos mientras tanto) y hace `git push`. GitHub Pages publica la página en 1 o 2 minutos.
6. Termina con "Listo." o con "ATENCIÓN: fallaron: …" si alguna fuente no se pudo actualizar.

## Si algo falla

| Mensaje | Qué hacer |
| --- | --- |
| `Estás en la rama …` | `git checkout main` y volver a correrlo. |
| `Hay cambios sin guardar en los datos…` | Revisar con `git status`. Si son datos de una prueba anterior que no quieres, descártalos con `git checkout -- docs/data/infobras_piura.json docs/data/camas_piura.json`. |
| `No se pudo hacer git pull` | Revisar la conexión, o si hay un conflicto, resolverlo con `git status`. |
| Un error de tiempo agotado en Infobras o SUSALUD | El sitio está caído o lento; probar más tarde. Los datos anteriores se mantienen. |
| `La página de SUSALUD respondió, pero no tiene enlaces a CSV` | SUSALUD cambió su página o el nombre de los archivos: hay que revisar `scripts/camas_susalud.py`. |
| `No se pudo subir (git push)` | El commit quedó en la computadora. Correr `git pull --rebase && git push`. |

## Antes de subir cambios a la página

Si cambias `docs/index.html` (por ejemplo, en el rediseño), corre la prueba de la página antes de hacer push:

```
python3 scripts/test_pagina.py
```

- **Qué revisa:**
  - las 7 pestañas a 1280 y 375 px, cada una en su dirección `#pestaña`;
  - que la página no se desplace de lado;
  - que ninguna tabla larga se vea sin abrir "Ver detalle";
  - que no haya errores en la consola;
  - que el enlace antiguo `#alertas` lleve a Obras;
  - que el año de la pestaña Dengue sea el de la sala;
  - que los rótulos del gráfico semanal de dengue no se encimen;
  - que las pestañas midan al menos 44 px de alto, y que estén "Actualizado al", el botón de compartir y los enlaces "Siguiente";
  - que el aviso "Dato no actualizado" aparezca con una fecha simulada 60 días después.
- **Resultado:** termina con `OK` o con la lista de lo que falló. Tarda unos 25 segundos.
- **Requisito, una sola vez:** `pip3 install playwright`. No hace falta `playwright install`: en macOS 12 Playwright no trae navegador, y la prueba usa Brave o Chrome si están instalados. Con otro navegador basado en Chromium: `NAVEGADOR=/ruta/al/ejecutable python3 scripts/test_pagina.py`.
- **Dónde corre:** solo en tu computadora; no va en el workflow.

## Otra opción a futuro

Si el profesor prefiere no depender de una computadora, se puede instalar un *self-hosted runner* de GitHub en una máquina en Perú (por ejemplo, un servidor de la UDEP). El workflow correría ahí y estas dos fuentes volverían a ser automáticas. Requiere una máquina encendida siempre y la autorización de DIRCOM o de TI.

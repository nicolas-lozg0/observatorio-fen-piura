# Actualización local: Infobras y camas (SUSALUD)

Dos fuentes no se pueden actualizar desde GitHub y hay que hacerlo desde una computadora: **Infobras** (obras en ejecución y paralizadas) y **SUSALUD** (camas y ocupación hospitalaria). El script `scripts/actualizar_local.sh` las descarga, procesa y sube a GitHub en un solo paso.

## Por qué no van en la actualización automática

- **Ambos sitios no responden a los servidores de GitHub.** Fallaron con tiempo agotado en todas las ejecuciones del workflow diario desde que se creó (30/10/2026), y también con 3 reintentos y 3 minutos de espera.
- **Desde una computadora en Perú responden en segundos.** Infobras tarda unos 5 minutos en total, sobre todo por leer su Excel de 57 MB; SUSALUD tarda unos 5 segundos.
- **Probable causa:** que bloqueen o no atiendan conexiones desde el extranjero o desde centros de datos. No está confirmado con la Contraloría ni con SUSALUD.
- **El resto sigue automático:** MEF (gasto, emergencia FEN, avance de proyectos) e IPC, a diario con `.github/workflows/actualizar.yml`; dengue 2026, también a diario (la sala es semanal) con `.github/workflows/dengue.yml`.

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
4. Hace un commit **solo** con sus 5 archivos de datos (`infobras_piura.json`, `infobras_departamentos.json`, `camas_piura.json`, `camas_serie.json` e `ipress_piura.json`, en `docs/data/`), con el mensaje "Actualiza Infobras y camas (local) AAAA-MM-DD".
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

## Precios de alimentos del SISAP (a mano, cada semana)

El SISAP del Midagri no tiene descarga automática, así que la tabla se exporta a mano. Unos 3 minutos:

1. Entra a http://sistemas.midagri.gob.pe/sisap/portal2/ciudades/ y elige la región **Piura**.
2. Pestaña **Intervalo de tiempo**: «Desde» el 1 de enero del año en curso, «Hasta» hoy.
3. Marca **todos los productos** de la lista y, en «Variables», **May. Precio Promedio** y **Min. Precio Promedio** (con
   Ctrl o Cmd).
4. **Consultar** y, cuando aparezca la tabla, **Herramientas → Exportar a Excel**.
5. Guarda el archivo en `data/raw/sisap/` (reemplaza el del año en curso, por ejemplo `piura_2026.xls`).
6. Corre `scripts/actualizar_local.sh`, o solo `python3 scripts/precios_sisap.py` para probar.

El script suma los precios nuevos al historial `data/sisap_piura.json`, que sí se sube a GitHub, y recalcula
`docs/data/precios_sisap.json`. La página avisa «Dato no actualizado» a los 14 días.

- **Si una consulta larga vuelve vacía:** pasó con todo 2023. El script se detiene con un aviso; exporta por trimestres.
- **Si el SISAP cambia el nombre de un producto:** ese alimento queda «sin dato». Hay que actualizar la lista `PRODUCTOS`
  en `scripts/precios_sisap.py`.

## Comunicado del ENFEN (a mano, cada 15 días aproximadamente)

La tarjeta del ENFEN en la pestaña Clima sale de `docs/data/enfen_comunicado.json`, que se llena a mano con cada comunicado oficial. Si el ENFEN publica uno nuevo, el paso «Aviso de comunicado nuevo del ENFEN» del workflow diario falla y el resumen lo dice; la página también avisa «Dato no actualizado» a los 20 días.

1. Abre el comunicado (PDF) desde https://enfen.imarpe.gob.pe/comunicados/ y el Informe Técnico del mismo número.
2. Edita `docs/data/enfen_comunicado.json`:

   | Campo | Qué poner | Ejemplo (N.° 20-2026) |
   | --- | --- | --- |
   | `numero` | Número y año del comunicado | `"20-2026"` |
   | `fecha_corte` | Fecha del comunicado (aaaa-mm-dd) | `"2026-11-13"` |
   | `estado` | Estado del sistema de alerta, tal como lo dice el encabezado | `"Alerta de El Niño costero"` |
   | `magnitud` | Magnitud prevista del evento costero | `"Extraordinaria"` |
   | `horizonte` | Hasta cuándo se espera | `"Hasta febrero de 2027; se debilitaría hasta julio de 2027"` |
   | `puntos` | 2 o 3 puntos clave para Piura, de 20 palabras como máximo cada uno, con palabras del comunicado | lluvias, caudales del río Piura, temperatura del aire |
   | `url_pdf` | Enlace al PDF, sin el parámetro `&refresh=…` | `…/comunicado-oficial-enfen-n-20-2026/?wpdmdl=2218` |
   | `proximo` | Fecha del próximo comunicado, si el texto la dice (al final) | `"2026-11-30"` |
   | `paita_costera` | Anomalía de la TSM en la estación costera de Paita (IMARPE), con su periodo, tomada del Informe Técnico (sección de estaciones costeras) | `8.6`, «del 1 al 9 de noviembre de 2026» |
   | `actualizado_a_mano` | Fecha en que editaste el archivo | `"2026-11-16"` |

3. Corre `python3 scripts/test_clima.py` (revisa que estén todos los campos y que los puntos no pasen de 20 palabras) y `python3 scripts/enfen.py` (debe decir que el JSON tiene el último comunicado).
4. Haz commit y push.

## Otra opción a futuro

Si el profesor prefiere no depender de una computadora, se puede instalar un *self-hosted runner* de GitHub en una máquina en Perú (por ejemplo, un servidor de la UDEP). El workflow correría ahí y estas dos fuentes volverían a ser automáticas. Requiere una máquina encendida siempre y la autorización de DIRCOM o de TI.

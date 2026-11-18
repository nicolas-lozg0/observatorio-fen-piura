# Auditoría de la actualización automática

Fecha: 17 de noviembre de 2026. Es solo un diagnóstico: no se cambió la página, los scripts ni los workflows.

**Cómo se hizo:**

- Se auditó lo publicado en GitHub (`origin/main`).
- Se revisaron las últimas 15 corridas de `actualizar.yml` y las últimas 5 de `dengue.yml` (`gh run view --log`), paso por paso.
- Cada script se corrió desde la Mac en una copia aparte del repositorio (`git worktree`), sin tocar `docs/data/`.
- Se comparó a mano con la fuente original en tres casos: MEF, lluvia del Senamhi y ENFEN.

## 0. La señal de alerta: «Dato no actualizado desde 10/11/2026» en Gasto

**No es un fallo de la actualización.** Viene de la copia local del repositorio:

- La copia local no traía los commits diarios de GitHub Actions desde el 10/11. Las rondas 12 a 17 se trabajaron sobre esa base.
- Antes del `git pull --rebase` de hoy (14:47), el `gasto_piura.json` local tenía `fecha_corte` 2026-11-10T08:48. Con el plazo de 3 días, la página local mostraba el aviso.
- **Lo publicado hoy:**
  - `gasto_piura.json` al 17/11 08:54, igual al `Last-Modified` del CSV del MEF (17/11 13:54 UTC);
  - la página en línea no muestra ningún aviso «no actualizado» (revisado con un navegador sin caché).
- **Obras:** está al 10/11 porque Infobras se actualiza a mano (`actualizar_local.sh`) y su plazo es de 35 días. No está vencido.

**Lección:** antes de revisar en local, hacer `git pull`. Si no, se ven datos viejos.

## 1. Inventario de fuentes

**Modos de actualización:**

- **GH-diario:** `actualizar.yml`, todos los días; programado a las 10:00 de Lima.
- **GH-semanal:** `dengue.yml`, los viernes.
- **GH-IMERG:** `imerg.yml`, diario, 12:30 de Lima.
- **Mac:** `scripts/actualizar_local.sh`.
- **A mano:** editar un JSON.
- **Estático:** se genera una vez.

| Fuente | Script | Modo | Paso | Frecuencia de la fuente | Plazo de aviso en la página (`PLAZOS`) |
| --- | --- | --- | --- | --- | --- |
| Gasto MEF (PIA, PIM, devengado) | `gasto_mef.py` | GH-diario | **obligatorio** | Diaria (CSV de 9,1 GB) | 3 días |
| Inversiones MEF (Formato 12-B) | `inversiones_mef.py` | GH-diario | **obligatorio** | Diaria o casi diaria | 3 días |
| Emergencia FEN (MEF) | `fen_mef.py` | GH-diario | opcional | Diaria | 3 días |
| IPC (INEI) | `ipc_inei.py` | GH-diario | opcional | Mensual (día 1) | 45 días |
| Lluvia por estación (Senamhi) | `lluvia_senamhi.py` | GH-diario | opcional | Diaria (ventana de 31 días) | 2 días |
| Mar frente a Paita (NOAA OISST) | `tsm_paita.py` | GH-diario | opcional | Diaria, 1–2 días de retraso | 4 días |
| Niño 1+2 (NOAA CPC) | `nino12_cpc.py` | GH-diario | opcional | Semanal (lunes) | 14 días |
| Comunicado del ENFEN | `enfen.py` (solo avisa) + JSON a mano | GH-diario + a mano | opcional | Cada ~2 semanas | 20 días |
| Temperatura del aire (Open-Meteo) | `temperatura_piura.py` | GH-diario (**aún no está en GitHub**: ronda 18, sin push) | opcional | Diaria (ERA5-Land, 7 días de retraso, más el pronóstico) | 12 días |
| Nivel de ríos y avisos (Senamhi) | `rios_senamhi.py` | GH-diario (**aún no está en GitHub**: ronda 18/19, sin push) | opcional | Continua; el Senamhi publica solo 24 h | 2 días |
| Dengue 2026 (sala DIRESA) | `dengue_diresa.py` | GH-semanal (viernes) | obligatorio en su workflow | Semanal; aparece entre el lunes y el viernes | 14 días |
| Lluvia por satélite (NASA IMERG) | `imerg_piura.py` | GH-IMERG | obligatorio en su workflow | Cada media hora | 2 días |
| Obras (Infobras) | `infobras.py` | Mac | — | Diaria (sin avances desde marzo de 2026) | 35 días |
| Camas (SUSALUD) | `camas_susalud.py`, `camas_serie.py` | Mac | — | Mensual, con 1–2 meses de retraso | 45 días (solo `camas_piura`) |
| Establecimientos (RENIPRESS) | `renipress.py` | Mac | — | Continua | **sin plazo** |
| Revisión de fichas de Infobras (archivo de la Contraloría) | — (`obras_revisadas.json`) | A mano | — | Cuando se revise | **sin plazo** |
| Dengue histórico 2000–2024 (CDC) | `dengue_historico.py` | A mano (el portal da error 418 a robots) | — | Anual | sin plazo (no hace falta) |
| Líneas de pobreza (INEI) | `lineas_pobreza.py` | Estático | — | Anual (mayo) | sin plazo (no hace falta) |
| Censo 2025 por manzana (INEI) | `censo_inei.py` | Estático | — | Única | no hace falta |
| Mapa de distritos | `mapa_distritos.py` | Estático | — | Única | no hace falta |
| Radar (UDEP) | — | Lo carga el navegador de cada visitante desde ecrmm.udep.edu.pe | — | Continua | No aplica; si la imagen falla, hay respaldo |
| GloFAS | — | **No está**: se descartó en la ronda 19 | — | — | — |

## 2. Corridas reales en GitHub Actions

### `actualizar.yml`: últimas 15 corridas (paso a paso)

| Fecha (UTC) | Resultado | Pasos que fallaron (aunque el workflow siga) | Línea del log |
| --- | --- | --- | --- |
| 17/11 22:49 | falla | `lluvia_senamhi.py` | `Intento 1 de 3 falló (<urlopen error timed out>)` … `TimeoutError: timed out` |
| 16/11 23:41 | ok | — | — |
| 15/11 20:16 | ok | — | — |
| 14/11 19:51 | ok | — | — |
| 13/11 21:21 | falla | `gasto_mef.py` (obligatorio). **No corrieron** inversiones, FEN ni IPC, y no hubo commit ese día. | `pandas.errors.ParserError: Error tokenizing data. C error: EOF inside string starting at row 5843020` |
| 12/11 21:48 | ok | — | — |
| 11/11 21:50 | ok | — | — |
| 10/11 22:40 (manual) | falla | `ipc_inei.py` | `ConnectionResetError: [Errno 104] Connection reset by peer` |
| 10/11 21:15 | falla | `ipc_inei.py` | `Intento 2 de 3 falló (… SSL: UNEXPECTED_EOF_WHILE_READING …)` |
| 09/11 al 05/11 (5 corridas) | ok | — | — |
| 04/11 23:55 (manual) | falla | `infobras.py` y `camas_susalud.py` (versión anterior del workflow), y el push | `[Errno 110] Connection timed out`; `! [remote rejected] main -> main (Internal Server Error)` |

**Observaciones:**

1. **Los datos sí llegan a `docs/data/`.** Cada corrida con éxito hace su commit «Actualiza datos AAAA-MM-DD», con commits del 14, 15, 16 y 17/11.
   - El paso de guardar corre antes de la revisión final. Por eso, cuando falla un paso opcional, lo demás igual se guarda.
2. **Los pasos opcionales que fallan no pasan inadvertidos:** el último paso cuenta los fallos y hace fallar la corrida, así que GitHub manda un correo.
   - Ese correo llega a la cuenta que activó el horario (`nicolas-lozg0`). No pude confirmar si alguien lo lee.
3. **Hasta hoy, en GitHub solo corrían gasto, inversiones, FEN e IPC.**
   - Lluvia, mar, Niño 1+2 y ENFEN (rondas 13 a 17) llegaron a GitHub con el push de hoy. La corrida de hoy fue la primera con esos pasos.
   - Hasta ahora, sus JSON publicados venían de la Mac.
   - Temperatura y ríos (rondas 18 y 19) siguen sin push.
4. **El horario se atrasa mucho.**
   - El cron dice 15:00 UTC (10:00 de Lima), pero las corridas empezaron entre las 19:20 y las 23:56 UTC: de 4 a 9 horas tarde.
   - Es normal en GitHub con horarios en punto y mucha carga.
   - No afecta al MEF, que publica hacia las 8:30, pero sí a las series que dependen de la hora (ríos, ver la sección 4).
5. **Duración:**
   - **Total:** de 4 a 15 minutos.
   - **`gasto_mef.py`:** 6 a 12 minutos, por leer 9,1 GB.
   - **`lluvia_senamhi.py`:** hoy se perdieron 4 minutos en reintentos.
   - **Límite del workflow:** 60 minutos, con holgura.

### `dengue.yml`: últimas 5 corridas

Las 5 salieron bien, pero la del viernes 13/11 dijo `La sala SE 43-2026 ya está procesada.`.

- La sala de la SE 44 ya está publicada en gob.pe, con fecha del 13/11.
- La próxima corrida es el viernes 20/11, así que la página se queda una semana con la SE 43.

### `imerg.yml`

**Nunca corrió.**

- Llegó a GitHub con el push de hoy (19:47 UTC), después de su hora (17:30 UTC). La primera corrida será el 18/11.
- El secreto `EARTHDATA_TOKEN` existe, creado el 17/11 a las 03:56 UTC.
- `docs/data/imerg_piura.json` no existe todavía, así que la página muestra solo las estaciones.

## 3. Prueba local de cada script (Mac, copia aparte)

| Script | ¿Corre? | Tiempo | Salida | ¿Es lo último de la fuente? |
| --- | --- | --- | --- | --- |
| `gasto_mef.py` | sí | 208 s | 745 KB; TOTAL PIM 8205,9 / dev. 6398,1 (millones) | **Sí**: 17/11 08:54 = `Last-Modified` del CSV (comparado a mano) |
| `inversiones_mef.py` | sí | 8 s | 2412 inversiones | Sí: archivo modificado el 16/11 14:01 |
| `fen_mef.py` | sí | 8 s | Piura 36 filas; marco 151,2 millones | Sí. Las columnas corridas del CSV del MEF se resuelven con la comparación de totales, como dice el script |
| `ipc_inei.py` | sí | 18 s | sin informes nuevos | Sí: el IPC de octubre salió el 1/11; el de noviembre sale el 1/12 |
| `lluvia_senamhi.py` | **sí desde la Mac** | 69 s | 21 estaciones; último día 17/11 (19 con dato) | Lo publicado está al 16/11 porque hoy falló en GitHub. **Comparado a mano** (ver abajo) |
| `tsm_paita.py` | sí | 57 s | último 15/11, +8,03 °C | Sí (OISST, 2 días de retraso) |
| `nino12_cpc.py` | sí | 1 s | semana del 11/11, +5,4 °C | Sí |
| `enfen.py` | sí | 2 s | «El JSON tiene el último comunicado (N.° 20-2026)» | **Sí, comparado a mano**: la página de comunicados del ENFEN muestra el N.° 20-2026 del 13 de noviembre de 2026 como el último |
| `temperatura_piura.py` | sí | 5 s | ERA5-Land hasta el 11/11 y pronóstico corregido (+0,68 °C) hasta el 16/11; anomalía +4,5 °C | Sí |
| `rios_senamhi.py` | sí | 2 s | Ñácara 0,59 m y La Ardilla 4,89 m a las 19:00 del 17/11; 2 avisos (Alamor, amarillo) | Sí |
| `dengue_diresa.py` | sí | 19 s | **procesó la SE 44** (10 KB) | **Lo publicado está atrasado:** SE 43 en la página, SE 44 en la fuente |
| `imerg_piura.py` | no (sin token en la Mac, a propósito) | 0 s | `Falta la variable de entorno EARTHDATA_TOKEN …: no se guarda nada` | No se probó |
| `infobras.py` | sí | 278 s | Piura: 899 en ejecución y 55 paralizadas; 457 KB | Lo publicado es del 10/11; la fuente tiene el archivo del 17/11. Al día para su plazo (35 días) |
| `camas_susalud.py` | sí | 4 s | octubre de 2026: 43 de 65 establecimientos reportaron, 1883 camas (77 UCI) | **Lo publicado está atrasado:** setiembre en la página, octubre ya en SUSALUD |
| `camas_serie.py` | sí | 10 s | 24 meses, hasta octubre de 2026 (ocupación 59,2 %) | Igual: la publicada llega a setiembre |
| `renipress.py` | sí | 5 s | 65 de 65 establecimientos (2 sin coordenadas) | Sin cambios (RENIPRESS v8) |

**Comparación a mano de la lluvia.** Se leyeron los arreglos del gráfico del Senamhi (`map_red_graf.php`) de Bernal (105012) y Alto de Poclus (104097), del 18/10 al 17/11, y se compararon día por día con el JSON:

- Los 31 valores coinciden en las dos estaciones.
- La única diferencia con lo publicado: Alto de Poclus el 16/11 era `null` y ahora el Senamhi da 0,0. El dato llegó tarde y la corrida siguiente lo corrige sola, porque cada corrida vuelve a leer los 31 días.
- El Senamhi marca trazas como 0,01 mm, y así quedan.

## 4. Riesgos

1. **Pasos opcionales que fallan sin que nadie se entere:** hoy no pasa. El último paso hace fallar la corrida y deja una tabla en el resumen.
   - El aviso es un correo de GitHub a la cuenta dueña del horario. Si nadie lo lee, es como si no hubiera aviso.
   - **Hueco:** `gasto_mef.py` e `inversiones_mef.py` son obligatorios. Si fallan (como el 13/11), se corta todo el trabajo: no corren los opcionales y no hay commit, aunque esas fuentes estén bien.
2. **EARTHDATA_TOKEN:**
   - **Vencimiento:** el secreto es del 17/11/2026. Si dura 60 días, vence hacia el **16/01/2027**.
   - **Qué distingue el log:**
     - si el token falta: `Falta la variable de entorno EARTHDATA_TOKEN`;
     - si NASA devuelve su página de inicio de sesión, o un HTTP 401/403: `token vencido o sin autorización (revisa EARTHDATA_TOKEN y que la cuenta tenga autorizada la aplicación …)`.
   - No distingue entre «vencido» y «aplicación no autorizada» (NASA responde igual).
   - No avisa **antes** de que venza.
3. **Series que se construyen día a día:**
   - **Ríos (`rios_senamhi.py`):** sí se pierden datos para siempre. La estación publica solo las últimas 24 h, así que si una corrida falla, ese día queda en blanco.
     - Además, como el horario se atrasa de 4 a 9 horas, puede quedar un hueco de hasta ~4,5 h entre corridas que sí funcionan. Pasa si una corre a las 19:20 UTC y la siguiente a las 23:56.
     - Y si el Senamhi no responde a GitHub (ver el punto 6), el riesgo es diario.
   - **Lluvia (`lluvia_senamhi.py`):** no se pierde nada si falla menos de 30 días seguidos, porque cada corrida trae 31 días.
   - **Temperatura, mar y Niño 1+2:** se recalculan enteros desde la fuente; no se pierde nada.
   - **IMERG:** guarda solo el último día, así que no hay serie que perder. Si falla, la página vuelve a mostrar solo las estaciones.
4. **Plazos de antigüedad:**
   - **Bien calibrados:** gasto, inversiones y FEN (3 días), lluvia (2), mar (4), Niño 1+2 (14), IPC (45), ENFEN (20), obras (35), camas (45).
   - **Temperatura (12 días):** desde la ronda 19 el dato llega hasta ayer (pronóstico corregido). Bastaría con 3.
   - **Dengue (14 días):** coincide con la frecuencia, pero corre solo los viernes. Una sala publicada el viernes por la tarde espera 7 días, y un viernes fallido deja la página vencida.
   - **Sin plazo:** RENIPRESS (`ipress_piura.json`), `camas_serie.json` (su `fecha_corte` es el mes del dato, no la fecha de descarga) y `obras_revisadas.json`. Las tres son manuales y nadie avisa cuando envejecen.
5. **Tiempo, tamaño y minutos:**
   - **Repositorio público:** los minutos de Actions son gratis e ilimitados en ejecutores estándar.
   - **Tamaño:** `.git` pesa 32 MB y `docs/data`, 6 MB. Lo que más crece es `gasto_piura.json` (~190 KB comprimidos por día, unos 70 MB al año). Lejos del límite recomendado de GitHub (1 GB).
   - **Tiempo:** la corrida más larga fue de 15 minutos, con límite de 60.
   - **Avisos de GitHub en el log:** Node 20 obsoleto en las acciones y migración de `ubuntu-latest` a Ubuntu 26. No rompen nada hoy.
   - **Horarios desactivados:** GitHub desactiva los horarios de un repositorio público tras 60 días sin actividad. Los commits diarios del robot cuentan, así que el riesgo es bajo mientras la actualización funcione.
6. **robots.txt y bloqueos desde GitHub:**
   - **Infobras y SUSALUD:** sin respuesta desde GitHub (`[Errno 110] Connection timed out`) en todas las corridas desde el 30/10. Ya se actualizan desde la Mac.
   - **Senamhi:** hoy, en su primera corrida en GitHub, la portada del mapa no respondió (`<urlopen error timed out>`, 3 intentos). Desde la Mac responde en segundos.
     - Es **un solo caso**: falta ver 2 o 3 corridas más para saber si es un bloqueo.
     - Si lo es, también afecta a `rios_senamhi.py` (mismo servidor), que es el que más pierde.
   - **INEI:** cortó la conexión dos veces el 10/11 (`Connection reset by peer`). Es intermitente: el 11/11 volvió a responder.
   - **robots.txt:**
     - **`apps5.mineco.gob.pe` dice `User-Agent: * / Disallow: /`.** `fen_mef.py` consulta ese sitio todos los días, así que va **contra su robots.txt**. Hay que decidirlo.
     - **MEF datos abiertos (`fs.datosabiertos`), Senamhi y Contraloría:** sin robots.txt (404).
     - **gob.pe:** prohíbe solo `/admin/` y `?sheet=`.
     - **ENFEN:** Cloudflare, sin `Disallow` para `*`.
     - **Radar de la UDEP:** prohíbe robots, como ya estaba anotado; no se descarga en Actions.

## 5. Tabla de estado

Leyenda de esfuerzo: bajo (< 1 h), medio (medio día), alto (más de un día o depende de terceros).

| Fuente | Modo | Frecuencia esperada | Última corrida OK | Dato publicado | Dato más reciente en la fuente | Estado | Causa exacta | Propuesta | Esfuerzo |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Gasto MEF | GH-diario | diaria | 17/11 | 17/11 08:54 | 17/11 08:54 | OK | — (el 13/11: `ParserError … EOF inside string`, descarga cortada) | Reintentar la descarga una vez si falla la lectura; no cortar todo el trabajo si falla | bajo |
| Inversiones MEF | GH-diario | diaria | 17/11 | 16/11 14:01 | 16/11 14:01 | OK | — | Igual que gasto | bajo |
| Emergencia FEN (MEF) | GH-diario | diaria | 17/11 | 16/11 | 16/11 | OK, pero va contra robots.txt | `apps5.mineco.gob.pe/robots.txt`: `Disallow: /` | Decidir: pedir permiso o un archivo al MEF, o aceptar el caso como el de los gráficos del Senamhi | medio |
| IPC (INEI) | GH-diario | mensual | 17/11 | 1/11 (octubre) | 1/11 | OK | Cortes intermitentes (10/11: `Connection reset by peer`) | Nada: el plazo de 45 días absorbe un fallo | — |
| Lluvia (Senamhi) | GH-diario | diaria | 17/11 desde la Mac; **nunca en GitHub** | 16/11 | 17/11 | **Falla** | `lluvia_senamhi.py`: `<urlopen error timed out>` en la portada del mapa, 3 intentos | Esperar 2 o 3 corridas. Si sigue, es bloqueo: pasarla a la Mac o a un ejecutor propio (ver «No se puede automatizar») | bajo para confirmar; medio para resolver |
| Mar (OISST) | GH-diario | diaria | 17/11 | 15/11 | 15/11 | OK | — | — | — |
| Niño 1+2 | GH-diario | semanal | 17/11 | 11/11 | 11/11 | OK | — | — | — |
| ENFEN | GH-diario (aviso) + a mano | ~quincenal | 17/11 | N.° 20-2026 (13/11) | N.° 20-2026 (13/11) | OK | — | — | — |
| Temperatura del aire | GH-diario (aún sin push) | diaria | nunca en GitHub; Mac OK | 16/11 (local) | 16/11 | **No corre en GitHub** | Sin push (rondas 18–19) | Push tras tu revisión; bajar el plazo a 3 días | bajo |
| Ríos (Senamhi) | GH-diario (aún sin push) | horaria (se acumula) | nunca en GitHub; Mac OK | 17/11 (local) | 17/11 19:00 | **No corre en GitHub**; riesgo alto si el Senamhi bloquea | Sin push; mismo servidor que la lluvia | Push; correr 2 o 3 veces al día para que se solapen las ventanas de 24 h; si el Senamhi bloquea a GitHub, no hay forma automática segura | medio |
| Dengue 2026 (DIRESA) | GH-semanal | semanal | 13/11 | SE 43 | **SE 44** (publicada el 13/11) | **Atrasado** | `dengue.yml` corre solo los viernes; el 13/11: `La sala SE 43-2026 ya está procesada.` | Correrlo todos los días; no cambia nada si no hay sala nueva (19 s) | bajo |
| IMERG (NASA) | GH-IMERG | diaria | nunca | — (no existe) | — | **Aún no corrió** | `imerg.yml` llegó a GitHub después de su hora de hoy | Revisar la corrida del 18/11; avisar antes de que venza el token | bajo |
| Obras (Infobras) | Mac | mensual | 10/11 (Mac); hoy, en la prueba | 10/11 | 17/11 | OK (manual) | Desde GitHub: `[Errno 110] Connection timed out` | Seguir en la Mac una vez al mes | — |
| Camas (SUSALUD) | Mac | mensual | 10/11 (Mac); hoy, en la prueba | setiembre de 2026 (descargado el 28/10) | **octubre de 2026** | **Atrasado** (manual: falta correr `actualizar_local.sh`) | Desde GitHub: `[Errno 110] Connection timed out` | Seguir en la Mac una vez al mes | — |
| RENIPRESS | Mac | mensual | 10/11 (Mac) | 30/10 | — | OK (sin plazo) | — | Agregar un plazo (p. ej. 60 días) | bajo |
| Revisión de fichas de Infobras | A mano | cuando cambie el archivo | — | 10/11 | — | OK | — | Sin plazo; no hace falta | — |
| Dengue histórico, líneas de pobreza, censo, mapa | Estático o a mano | anual o única | — | 22/10, 1/5, 13/11 | — | No automatizable / no hace falta | Error 418 en el portal (dengue histórico) | — | — |
| Radar (UDEP) | Navegador del visitante | continua | — | en vivo | en vivo | OK (la imagen responde: HTTP 200) | — | — | — |

## 6. No se puede automatizar (y qué tendrías que hacer tú)

| Fuente | Por qué no | Qué hacer y cada cuánto |
| --- | --- | --- |
| **Comunicado del ENFEN** | El estado, la magnitud y los puntos clave salen de leer el PDF. Además, la página de comunicados está detrás de Cloudflare. | Cuando la corrida falle con `Hay un comunicado nuevo del ENFEN`, actualizar `docs/data/enfen_comunicado.json` a mano (cada ~2 semanas; ver `docs/actualizacion_local.md`). |
| **Infobras** | No responde a los servidores de GitHub (tiempo agotado desde el 30/10). | `scripts/actualizar_local.sh` en la Mac **una vez al mes** (la primera semana), o cuando la página diga «Dato no actualizado» en obras. |
| **SUSALUD (camas y serie) y RENIPRESS** | Igual que Infobras. | En la misma corrida mensual de `actualizar_local.sh`. El mes nuevo de camas suele aparecer hacia fin de mes. |
| **Lluvia y ríos del Senamhi**, si se confirma el bloqueo | El servidor no respondería a GitHub. | **Lluvia:** basta con la Mac una vez por semana, porque guarda 31 días; la página mostraría hasta 7 días de atraso. **Ríos:** necesitan una corrida diaria (mejor 2) desde una máquina en el Perú. Hay dos caminos: (a) un ejecutor propio de GitHub en una computadora de la UDEP siempre encendida; (b) `launchd` en la Mac, solo si está encendida a diario. Sin eso, la serie de ríos tendrá huecos. |
| **Revisión de fichas de Infobras** | Es una revisión hecha a mano. | Cuando llegue un archivo nuevo de la Contraloría. |
| **Dengue histórico (CDC)** | El portal devuelve error 418 a los programas. | Una vez al año, a mano. |
| **Token de Earthdata** | Vence; solo tú puedes renovarlo. | Renovarlo en urs.earthdata.nasa.gov y actualizar el secreto `EARTHDATA_TOKEN` **antes del ~16/01/2027**, y luego cada ~60 días. |

## 7. Monitoreo propuesto (no implementado)

1. **`docs/data/estado_fuentes.json`, generado al final de cada corrida** (también si algo falló, con `if: always()`). Por cada fuente:
   - `clave`, `nombre`, `modo`;
   - `fecha_corte` (leída de su JSON), `plazo_dias` (el mismo de `PLAZOS`; mejor moverlo a este archivo para que haya una sola fuente de verdad), `dias` (antigüedad) y `vencido`;
   - `ultimo_paso` (`success`, `failure` o `skipped`, tomado de `steps.<id>.outcome`) y `error` (última línea del log del paso, sin secretos);
   - `revisado` (fecha y hora de la corrida).

   Las fuentes de la Mac y las manuales entran solo con su fecha y su plazo, para que el vencimiento también se vea.
2. **Aviso automático con un issue de GitHub.** Un paso final con `gh issue create`/`gh issue comment` (permiso `issues: write`, sin secretos nuevos) que:
   - abra **un** issue «Fuente vencida: X» o «Paso fallido: X» si no existe uno abierto, o le agregue un comentario si ya existe;
   - lo cierre solo cuando la fuente vuelva a estar al día.

   Así llega a quien siga el repositorio, no solo al dueño del horario, y queda un historial. Para el token de Earthdata: un aviso 7 días antes de su vencimiento, leído de la fecha del token sin imprimirlo.
3. **Sección «Estado de las fuentes» en «Fuentes y método».** Una tabla generada desde `estado_fuentes.json`: fuente, modo, dato al, plazo y estado (al día, vencido o falló la última corrida), con la misma lógica del aviso «Dato no actualizado». Reemplaza el seguimiento a ojo.
4. **Cambios menores en el mismo paquete:**
   - `gasto_mef.py` e `inversiones_mef.py` con `continue-on-error` y en el resumen; un reintento de la descarga en `gasto_mef.py` si falla la lectura;
   - `dengue.yml` diario;
   - `rios_senamhi.py` 2 o 3 veces al día;
   - plazo de 3 días para la temperatura y plazos para RENIPRESS y `camas_serie`.

## 8. Notas menores encontradas

- **`imerg.yml`:** su comentario dice «de 7:00 a 7:00 de Lima», pero desde la ronda 19 la ventana es de 19:00 a 19:00.
- **`docs/actualizacion_local.md`:** dice que el commit lleva solo 2 archivos, pero `actualizar_local.sh` sube 5 (Infobras ×2, camas ×2 y RENIPRESS).

## Resumen

1. **Bien:**
   - Gasto, inversiones, FEN, IPC, mar, Niño 1+2 y ENFEN están al día. Se verificaron contra la fuente: MEF al 17/11 08:54 y ENFEN N.° 20-2026.
   - Los datos llegan a `docs/data/` todos los días.
   - Un paso que falla hace fallar la corrida, con aviso por correo.
2. **El aviso «desde 10/11» de Gasto venía de la copia local, que estaba sin actualizar.** Lo publicado no tiene ningún aviso.
3. **Falla o está atrasado hoy:**
   - lluvia del Senamhi: tiempo agotado en su primera corrida en GitHub;
   - dengue: SE 43 publicada y SE 44 en la fuente, porque solo corre los viernes;
   - camas: setiembre publicado y octubre en SUSALUD; falta correr `actualizar_local.sh`.
   - Temperatura, ríos e IMERG todavía no han corrido en GitHub.
4. **Riesgos:**
   - la serie de ríos pierde para siempre cada día que falla, y el Senamhi quizá no responde a GitHub;
   - `fen_mef.py` va contra el robots.txt de `apps5.mineco.gob.pe`;
   - si falla el gasto, se corta todo el trabajo;
   - el token de Earthdata vence hacia el 16/01/2027 sin aviso previo.
5. **Arreglar primero:**
   - correr `actualizar_local.sh` (camas de octubre);
   - pasar `dengue.yml` a diario;
   - ver 2 o 3 corridas más de la lluvia antes de decidir dónde corren lluvia y ríos;
   - decidir qué hacer con `fen_mef.py` y el robots.txt;
   - después, el monitoreo de la sección 7.

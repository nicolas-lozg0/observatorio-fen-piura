# Avance: ajustes a la página y Tarea 3 (salud y dengue)

Fecha: 30 de octubre de 2026. Es un borrador para recoger toda la retroalimentación del profesor de una vez. Todo corre en local. **No se ha hecho push ni se ha creado el repositorio.**

## Cómo ver la página en local

Desde la carpeta del proyecto:

```
python3 -m http.server 8000 -d docs
```

Luego abrir http://localhost:8000. Para cerrar el servidor, presiona Ctrl+C.

## Cómo actualizar los datos a mano

```
pip install -r requirements.txt
cd scripts
python3 test_gasto_mef.py && python3 test_dengue.py   # pruebas rápidas (deben decir OK)
python3 gasto_mef.py            # ~6 min
python3 infobras.py             # antes de inversiones_mef.py, que usa sus CUI
python3 inversiones_mef.py
python3 fen_mef.py
python3 camas_susalud.py
python3 dengue_diresa.py        # sala situacional más reciente; si ya está procesada, no hace nada
python3 historial.py            # agrega o reemplaza la fila del día en historial.csv
# Una sola vez (no van en la actualización automática):
python3 dengue_historico.py     # requiere el CSV en data/raw/
python3 mapa_distritos.py       # límites distritales para el mapa
```

## Segunda ronda: reestructuración de la página (30/10/2026)

El objetivo es que alguien entre y en pocos segundos sepa cómo está Piura frente a El Niño. Las fuentes y los cálculos validados no cambiaron, salvo lo que se indica abajo. Lo que sigue en las secciones A y B describe la primera ronda; donde la segunda ronda lo cambió, se anota aquí.

### Estructura y navegación

- **Menú fijo arriba**, visible al bajar: Resumen · Dengue y salud · Prevención y emergencia · Obras · Detalle del gasto · Fuentes y método. En celular se desliza de lado.
- **Nuevo orden:**
  1. Resumen.
  2. Dengue y salud: casos, mapa, hospitalizados, capacidad hospitalaria y vacunación.
  3. Prevención y emergencia: 0068, emergencia FEN, ANIN y 0017.
  4. Obras: alertas, luego las obras.
  5. Detalle del gasto: total, niveles de gobierno y proyectos.
  6. Otros indicadores.
  7. Fuentes y método.
- **Resumen:** las ocho cifras van con este orden de prioridad: casos de dengue de la semana, casos 2026, fallecidos, prevención 0068, emergencia FEN, reconstrucción ANIN, obras paralizadas y avance del gasto total. Cada tarjeta lleva a su sección al tocarla.
- **Sin repeticiones:** se quitaron "Indicadores destacados" y el bloque grande del 75,6 %. El avance total quedó como primera fila de "Detalle del gasto". En la sección de dengue ya no se repiten los casos ni los fallecidos del resumen; solo se muestran confirmados, graves, signos de alarma y hospitalizados.
- **Tablas largas:** las de proyectos, obras, paralizadas y camas muestran 10 filas, con un botón "Ver más" que agrega 25 cada vez. Al cambiar un filtro se vuelve a 10.
- **Id estables** para incrustar cada parte en la web de la UDEP:
  - Secciones: `resumen`, `dengue`, `prevencion`, `obras`, `gasto`, `otros` y `fuentes`.
  - Subsecciones: `dengue-semanas`, `dengue-distritos`, `dengue-hospitalizados`, `capacidad-hospitalaria`, `vacunacion`, `emergencia-fen`, `alertas`, `obras-lista` y `proyectos`.

### Alertas (al inicio de Obras)

- **Proyectos con más pagado que construido.** Se compara el avance financiero **acumulado** del MEF (gastado desde el inicio sobre el costo actualizado) con el avance físico acumulado. Se alerta si el financiero supera al físico en más de 30 puntos.
  - **Hoy ningún proyecto supera esa brecha.** De 1.058 proyectos con ambos datos, la mayor diferencia es de 27,4 puntos. La página lo dice así.
  - **Ojo con el puente de Tambogrande** (CUI 2392435):
    - El 99,7 % que se veía en la tabla es el avance **del año**: devengado de 2026 sobre el PIM de 2026.
    - Su avance financiero acumulado es 19,8 %, y el físico, 19,6 %. No hay brecha.
    - Comparar el avance del año con el físico acumulado mezcla periodos distintos. Por eso la tabla de proyectos ahora dice "Avance del año", y la sección de método lo explica.
- **Obras paralizadas:** las 55 aparecen ordenadas por costo, con fecha de paralización y causa. Su costo total es S/ 1.286,1 millones.

### Correcciones de datos

| Pedido | Qué se hizo |
| --- | --- |
| Fallecidos | La página muestra una sola cifra: **15**, de la tabla de defunciones por tipo de diagnóstico (10 confirmadas y 5 probables). Sigue el mismo criterio que los casos. "Fuentes y método" explica que la tabla por provincias de la misma sala suma 14. El historial también guarda 15. |
| Mapa | Lleva título, una leyenda con rangos ("175 a 323 casos", etc.) y distingue **"0 casos"** (gris) de **"sin dato"** (rayado). En 2026, "sin dato" son los distritos que la DIRESA agrupa en "otros distritos"; en años anteriores, un distrito que no figura tiene 0 casos. El mapa indica que el color es el número de casos y no la tasa. **Población de la tasa:** la tasa por 10 mil habitantes la calcula la DIRESA, y su sala situacional no dice qué población usa. Revisé el PDF de la SE 42 y no lo indica. La página lo dice así. |
| Refinería de Talara | Sale de los totales y se muestra aparte con una nota: "proyecto de Petroperú, sin relación con El Niño". Las obras en ejecución quedan en 898, con S/ 7.889,3 millones (antes, S/ 17.667 millones). La lista de excluidas es la constante `APARTE` en `index.html`. |
| Infobras desactualizado | **Reemplazado en la tercera ronda** (ver abajo): el retraso es del archivo de datos abiertos, no de las entidades. El avance físico ahora viene del MEF. |
| Camas | La sección se llama ahora "Capacidad hospitalaria" y dice que no existe un dato público de camas libres en tiempo real. **Se calcula la ocupación:** el diccionario de SUSALUD (DICCIONARIO_TABLA_D1_2026.pdf) define `NRO_TOTAL_PACIENTES_CAMAS` como la suma de pacientes que ocuparon las camas, es decir, los pacientes-día. Ocupación = pacientes-día / días-cama disponibles. En setiembre de 2026 fue de **58,7 %** en los 40 establecimientos que reportaron. Un centro de salud sale con 103,2 % y se marca para revisar. `camas_susalud.py` ahora guarda `pacientes_dia`. |
| Tablas cortadas | Las tablas anchas tienen un ancho mínimo y, en pantallas angostas, se desplazan dentro de su caja. El texto ya no se corta, y la página no se desplaza de lado. |

### Fuentes y método

Una sección al final reúne lo siguiente:
- **Fuentes:** una tabla con cada fuente, su enlace, la frecuencia de actualización y la fecha de los datos, que se lee de los archivos.
- **Criterios:** lugar del gasto frente a sede; PIM y devengado; avance del año frente a avance acumulado; confirmados y probables; obras ligadas a El Niño; avance desactualizado; ocupación de camas.
- **Validación de cada dato:** el estado de cada tabla de la DIRESA en la semana actual, con sus avisos.

### Verificación (segunda ronda)

- Revisé la página en Chrome, en modo claro:
  - **En escritorio:** sin errores en la consola. El menú queda fijo, las tarjetas llevan a su sección y "Ver más" pasa de 10 a 35 filas. El mapa muestra bien 2026 (con "sin dato") y 2023 (con "0 casos").
  - **A 375 px de ancho**, dentro de un marco: la página no se desplaza de lado y las 7 tablas anchas se desplazan dentro de su caja.
- `camas_susalud.py` e `historial.py` se volvieron a correr.

## A. Ajustes a lo existente (primera ronda)

| Pedido | Qué se hizo |
| --- | --- |
| Tarjeta de reconstrucción | Nueva tarjeta de **ANIN** en "Indicadores destacados": PIM S/ 711,3 millones, devengado S/ 625,4 millones, avance 87,9 %. ANIN tiene sede en Lima, así que con el criterio de sede no suma gasto en Piura. La **Autoridad para la Reconstrucción con Cambios** no registra gasto en Piura en 2026: su pliego, la PCM, no tiene PIM con meta en Piura. La tarjeta lo indica. |
| Infobras | Arriba van las obras **en ejecución (899)** y **paralizadas (55)**, con su costo total. Las finalizadas (7.094) y sin ejecución (1.759) quedan en una línea secundaria. La tabla muestra por defecto las obras en ejecución y paralizadas, y se puede filtrar por estado y buscar por texto. |
| Franja de resumen | Ocho cifras, cada una con su fuente y fecha: avance del gasto, prevención (0068), reconstrucción (ANIN), emergencia FEN, obras paralizadas, obras en ejecución, casos de dengue de la última semana y casos de dengue en 2026. El selector de criterio de gasto ahora está en esa franja. |
| Modo claro | La página queda fija en modo claro (`data-theme="light"` en `index.html`). Los colores de modo oscuro se conservan: basta quitar ese atributo para volver al modo automático. |
| Historial | `scripts/historial.py` guarda una fila por día en `docs/data/historial.csv` con 18 indicadores. Si se corre dos veces el mismo día, la fila se reemplaza. Corre al final de cada actualización. Cuando haya dos fechas o más, cada cifra de la franja muestra una pequeña línea de evolución. **Por ahora hay una sola fecha (30/10/2026), así que todavía no se ve ninguna línea.** |

## B. Tarea 3: salud y dengue

### 6. Dengue histórico 2000–2025 (CDC-Minsa)

- `data/raw/` está en `.gitignore`. Lo comprobé en un repositorio de prueba: el CSV queda ignorado y `historial.csv` sí se sube.
- `scripts/dengue_historico.py` cuenta los casos de Piura por año, semana, distrito (ubigeo), forma clínica (S sin signos de alarma, A con signos de alarma, G grave) y tipo de diagnóstico (C confirmado, P probable).
  - No elimina filas idénticas: el conteo usa todas las filas, y el script verifica que la suma sea igual al número de filas de Piura.
  - Resultado: 239.078 casos en 16.701 filas agregadas (477 KB), sin edad, sexo ni localidad.
- **Hallazgo 1:** el archivo trae la Ñ ya perdida, por ejemplo "PARI�AS" (con un carácter de reemplazo). En Piura ese carácter solo puede ser Ñ, así que se corrige en los nombres de distrito.
- **Hallazgo 2:** en los años recientes casi no hay probables (2023: 79.273 confirmados y 31 probables; 2024: 32.245 y 1). Al parecer el archivo guarda la clasificación final de cada caso. La DIRESA, en cambio, informa confirmados y probables del año en curso (2026: 68,8 % confirmados). **Por eso la comparación 2026 contra años anteriores es aproximada.** La página permite ver los años anteriores con confirmados y probables o solo con confirmados.

### 7. Dengue 2026 (salas situacionales de la DIRESA Piura)

`scripts/dengue_diresa.py` hace lo siguiente:

1. Busca en gob.pe la sala situacional más reciente (hoy, la SE 42 con datos al 27/10/2026).
2. Descarga el PDF a una carpeta temporal.
3. Ubica cada tabla por su título, no por el número de página.
4. Valida cada tabla contra los totales del propio PDF. **Si una tabla no cuadra, se guarda vacía, el motivo queda anotado y la página no la muestra.**

| Tabla | Validación | Resultado SE 42 |
| --- | --- | --- |
| Casos, formas clínicas, confirmados y probables, fallecidos por provincia | Cada columna suma su fila "Total"; formas clínicas = casos; C + P = casos | Cuadra: 14.789 casos, 54 graves, 14 fallecidos |
| Defunciones por tipo de diagnóstico | Confirmadas + probables = total | Cuadra: 15 (10 C y 5 P) |
| Casos por distrito y semana | Cada semana suma la fila TOTAL; además, cada fila debe cuadrar consigo misma | Cuadra. La fila "otros distritos" no cuadra consigo misma (sus semanas suman 1.530, pero el II semestre dice 1.944 y el total, 113), así que no se publica, y la página lo dice |
| Serie semanal de la región | La suma de todas las semanas = casos del año | Cuadra |
| Hospitalizados por establecimiento | Cada fila suma su total; la fila "Total general" cuadra consigo misma | Cuadra: 3.276. El PDF no lista todos los establecimientos; los 28 restantes van como "otros" |

- **Formato:** probé con las salas de la SE 41 y la SE 42. Las dos tienen el mismo formato y pasan la validación. La SE 26 tenía otro formato.
  - Si la DIRESA vuelve a cambiarlo, el script no publicará la tabla afectada.
  - Las salas antiguas no se procesaron.
- **Problemas del propio PDF:**
  - Algunas celdas vienen cortadas, por ejemplo "1,1" en lugar de 1.130 en la tabla de formas clínicas por semana. El script no las adivina: en esas semanas usa la fila TOTAL de la tabla por distrito.
  - La sala informa 14 fallecidos en una tabla y 15 defunciones en otra. Desde la segunda ronda, la página muestra 15, con el mismo criterio que los casos.
- **Actualización automática:** nuevo workflow `.github/workflows/dengue.yml`, que corre cada viernes a las 11:00 (hora de Perú) y también se puede lanzar a mano. Si no hay sala nueva, no cambia nada.

### 8. Dengue en la página

- **Casos por semana:**
  - El gráfico compara 2026 (DIRESA) con 2017, 2023 y 2024 (CDC).
  - Al pasar el cursor se ven los valores de la semana, y cada línea tiene su rótulo.
  - Los colores se comprobaron con el validador de paletas de la guía de visualización.
- **Casos por distrito:**
  - Un selector de año (2026 o cualquier año entre 2000 y 2025) cambia la tabla y el mapa.
  - En 2026, la DIRESA solo detalla los distritos con más casos (13.039 de 14.789); el resto queda en gris como "otros distritos".
- **Mapa de distritos:**
  - Usa los límites del INEI de 2007, tomados del GeoJSON público de github.com/juaneladio/peru-geojson (licencia MPL 2.0).
  - Se dibuja sin librerías externas.
  - Tiene dos limitaciones:
    - No existe el distrito Veintiséis de Octubre (creado en 2013): sus casos se suman al polígono de Piura y así lo dice el globo.
    - Bellavista (Sullana) viene sin polígono en esa fuente y no se dibuja.
- **Hospitalizados por establecimiento:** se muestran en una tabla.

### 9. Camas (SUSALUD)

- `scripts/camas_susalud.py` toma el último mes de la Consulta D1, hoy setiembre de 2026, publicado el 28/10/2026.
- La tabla de la página dice que el dato es mensual e indica el mes. Por establecimiento muestra camas, camas UCI, días-cama disponibles, ingresos y egresos.
- En setiembre reportaron 40 de los 62 establecimientos de Piura: 1.871 camas, 53 de ellas de UCI. Los que no reportaron aparecen como tales.
- Camas UCI son los servicios cuyo nombre incluye "cuidados intensivos". En la segunda ronda se agregó la ocupación del mes, una vez verificada la definición en el diccionario de SUSALUD.

### 10. Vacunación contra el dengue

No hay una fuente abierta. Solo encontré notas de prensa con cifras de REUNIS, de distintas fechas. La sala de la DIRESA tampoco trae cifras de vacunación. En la página, el indicador aparece como **"Sin fuente abierta disponible"**.

### 11. Precios (SISAP, MIDAGRI)

**Pendiente.** La página del SISAP no usa archivos descargables. Arma cada consulta con JavaScript, con direcciones cifradas y un token. Su botón "Exportar a Excel" reenvía al servidor la tabla ya mostrada en pantalla. Automatizarlo exigiría estudiar ese JavaScript o manejar un navegador.

## Verificación

- Todos los scripts se corrieron de principio a fin. Las dos pruebas (`test_gasto_mef.py` y `test_dengue.py`) dicen OK.
- La página se revisó en Chrome:
  - **En escritorio:** sin errores en la consola. Funcionan el selector de criterio, el globo del gráfico, el mapa con 2026 y 2023, el filtro de obras y la tabla de camas.
  - **En celular, a 390 px de ancho:** sin desplazamiento horizontal. Achicar la ventana del navegador no funcionó, así que la probé dentro de un marco de 390 px.
- `docs/data/` pesa 1,9 MB. No se guardan nombres de personas ni datos por caso.

## Lo que necesita decisión del profesor

1. **Criterio de "gasto en Piura":** lugar del gasto (por defecto) o sede de la entidad.
2. **Comparación del dengue:** el histórico casi no tiene probables y 2026 sí. ¿Comparamos 2026 en confirmados y probables (como ahora) o solo en confirmados? Si es solo en confirmados, hoy no hay serie semanal 2026 de confirmados: la sala solo da el total del año.
3. **Fallecidos por dengue:** se decidió mostrar 15 (confirmados y probables). Queda por confirmar con el profesor.
4. **Dengue por distrito en 2026:** la DIRESA solo detalla los distritos con más casos. ¿Pedimos a la DIRESA la tabla completa por distrito, o aceptamos "otros distritos"?
5. **Mapa:** ¿sirven los límites de 2007 (sin Veintiséis de Octubre y sin Bellavista de Sullana) o buscamos límites más recientes del INEI?
6. **Vacunación:** no hay archivo abierto. Hay dos opciones:
   - **(a)** pedir a la DIRESA Piura, por transparencia, las dosis aplicadas por distrito y por semana, como se hizo con el INEI;
   - **(b)** copiarlas a mano cada semana desde el tablero REUNIS del Minsa, que no se puede descargar ni leer automáticamente.

   La (a) da un dato verificable, pero tarda; la (b) es inmediata, pero depende de una persona y no se puede auditar igual.
7. **Precios:** hay dos opciones:
   - **(a)** el SISAP del MIDAGRI, con precios por producto y ciudad, incluida Piura, pero sin descarga, así que habría que automatizar un navegador o copiar a mano;
   - **(b)** el IPC de Piura del INEI, mensual y menos detallado, pero que podría actualizarse solo. **Todavía no verifiqué** que el INEI publique el IPC de Piura en un archivo descargable.
8. **Reconstrucción:** ¿basta con ANIN o hay que sumar proyectos de otras entidades marcados como "Reconstrucción con Cambios"? Infobras tiene esa marca por obra.
9. **Alerta de brecha:** el umbral es de 30 puntos, y hoy ningún proyecto lo supera (el máximo es 27,4). ¿Lo bajamos, por ejemplo a 20 puntos? (Cruzar con el avance físico de Infobras quedó descartado: su archivo no se actualiza desde marzo de 2026.)
10. **Megaproyectos excluidos:** por ahora solo la Refinería de Talara. ¿Hay otros que excluir? Por ejemplo, las obras de banda ancha o de irrigación del Alto Piura.
11. **Infobras desactualizado:** resuelto en la tercera ronda: el avance físico viene del MEF e Infobras queda solo para estado y causa. Sigue abierta la opción de preguntar a la Contraloría por qué el archivo diario no se actualiza.
12. **Fecha del avance del MEF:** el archivo del MEF no dice de qué mes es el avance físico, y el significado de `ULT_FEC_DECLA_ESTIM` no está confirmado (no hay diccionario). ¿Lo consultamos al MEF?
13. **CUI con varias obras:** el avance del MEF es de toda la inversión. En el CUI 2392435 (4 obras) el MEF da 19,6 % y la ficha de Infobras de la obra 4 da 92,69 %. La página lo indica en la celda.

## Tercera ronda: Infobras y avance físico (2 de noviembre de 2026)

**Diagnóstico.** Se compararon cuatro fichas web de Infobras con el archivo de datos abiertos del 02/11/2026:

| Código Infobras | CUI | Ficha web | Archivo de datos abiertos |
| --- | --- | --- | --- |
| 542437 | 2392435 | 92,69 %, setiembre de 2026 | 44,74 %, enero de 2026 (registrado el 19/02/2026) |
| 566350 | 2328427 | 54,89 %, setiembre de 2026 | no está |
| 563640 | 2702385 | 45,64 %, julio de 2026 | no está |
| 562977 | 2643165 | sin avance | no está |

- El script leía la columna correcta ("Avance Físico Real Acumulado (%)"): para 542437 coincide con el archivo y con el avance de enero que muestra la propia ficha.
- El archivo está congelado: su código Infobras más alto es el 556525 (las obras más nuevas no aparecen) y casi no tiene avances posteriores a marzo de 2026. Solo cambia la fecha de consulta.
- Infobras no ofrece otro archivo descargable (solo Obras Públicas y Asociaciones Público-Privadas). Se decidió no leer las fichas web de forma automática porque son direcciones internas de la aplicación, que pueden cambiar sin aviso.
- **robots.txt (revisado el 02/11/2026).** No prohíbe la lectura automática de las fichas:
  - `https://apps.contraloria.gob.pe/robots.txt`: no existe (HTTP 404).
  - `https://apps.contraloria.gob.pe/infobras/robots.txt` (versión antigua de Infobras) dice, textualmente:
    ```
    User-agent: *
    Crawl-delay: 60
    Disallow: /wfm_info_sugerencias.aspx
    ```
    Pide 60 segundos entre consultas y solo bloquea la página de sugerencias.
  - `https://infobras.contraloria.gob.pe/robots.txt` y `https://infobras.contraloria.gob.pe/InfobrasWeb/robots.txt` (sitio actual, donde están las fichas y el archivo de datos): no existen (HTTP 404).
  - En una versión anterior de este documento se dijo que el `robots.txt` no admitía lecturas automáticas; eso no era correcto.

**Cambios.**

| Qué | Detalle |
| --- | --- |
| Avance físico de obras | Viene del MEF (Detalle de inversiones, Formato 12-B), unido por código único de inversión. Columna de las tablas de obras: "Avance físico de la inversión (MEF)". La línea de fuente dice "Datos MEF al 31/10/2026" (fecha del archivo del MEF). `inversiones_mef.py` ahora también guarda los CUI de las obras activas de Infobras (575 de 809 encontrados). |
| CUI con varias obras | Cuando varias obras comparten un CUI, la celda lo indica: "19,6 % (inversión de 4 obras)". El número de obras se cuenta en todo el archivo de Infobras (todo el país y todos los estados), en `obras_en_cui`. Hoy son 166 de las 954 obras activas de Piura. |
| CUI 2392435 en el MEF | Avance físico **19,59 %**, avance de ejecución 19,81 % (archivo del MEF modificado el 31/10/2026). **El archivo no trae el mes al que corresponde el avance.** Es el avance de toda la inversión (11 puentes, 4 obras en Infobras, costo actualizado S/ 679,4 millones), no de la obra 4. |
| Columna `ULT_FEC_DECLA_ESTIM` del MEF | Es la única fecha cercana al avance (para el CUI 2392435: 27/10/2026), pero el MEF no publica el diccionario de este archivo (404) y su significado no está confirmado. **No se usa en la página.** |
| Infobras | Solo estado (en ejecución o paralizada) y causa de paralización. `infobras.py` ya no guarda avance ni mes de avance. |
| Tarjeta | La tarjeta "Avance sin actualizar hace más de 6 meses" se reemplazó por la nota: "Archivo de datos abiertos de Infobras sin actualizar desde marzo de 2026; obras registradas después no aparecen". El mes sale de los datos (`ultimo_avance`: el avance más reciente de Piura en el archivo). La nota se repite en el aviso de obras paralizadas y en la fuente. |
| Fechas futuras | Se excluyen las filas cuyo mes de avance aún no termina a la fecha del archivo (mes de la consulta o posterior). En el archivo del 02/11/2026 fueron **10 filas**, ninguna de Piura (3 de noviembre y 7 de diciembre de 2026). La cifra se guarda en `excluidas_fecha_futura` y se muestra en "Fuentes y método". Hay una undécima fila con avance de octubre de 2026 registrado en marzo: no es una fecha futura, así que no se excluye. Hay además 427 filas (16 de Piura) cuyo mes de avance es posterior a su fecha de registro; no se excluyen, porque la página ya no usa el avance de Infobras. |
| Obra 566350 | No está en nuestros datos (no aparece en el archivo de Infobras), así que no hay nada que corregir. Su ficha la ubica en Aramango (Bagua, Amazonas), pero el CUI 2328427 es, según el MEF, una obra de agua y alcantarillado en la Urb. San José, Veintiséis de Octubre, Piura, y el contrato de la ficha es de la "MDVO". Lo más probable es que el error esté en la ubicación de la ficha. |
| Workflow | `infobras.py` corre antes de `inversiones_mef.py`. |

**Verificación.** Se corrieron `infobras.py` e `inversiones_mef.py` con los archivos del día. La página se revisó en Chrome, en local, sin errores en la consola: la tarjeta y el aviso muestran la nota, y las obras de los puentes muestran "19,6 % (inversión de 4 obras)". La fuente dice "Datos MEF al 31/10/2026".

## Pendiente o por verificar

- **Antes de publicar** (igual que en la Tarea 2):
  - Crear el repositorio.
  - Activar Pages en `/docs`.
  - Darle a `gh` el permiso `workflow`.
- **Workflows:** ninguno de los dos se ha corrido en GitHub, porque no hay repositorio. Ambos hacen `git pull --rebase` antes del push, para no chocar entre sí.
- **Infobras:**
  - El archivo de datos subió de 29 KB a 496 KB, porque ahora guarda las 954 obras en ejecución y paralizadas (441 KB desde la tercera ronda, sin campos de avance; 457 KB con `obras_en_cui`).
  - Infobras pierde la Ñ en algunos textos: en el distrito se corrige "PARI AS" a "PARIÑAS"; en los nombres de obra se deja como viene.
  - Una obra domina el costo de las que están en ejecución: la modernización de la Refinería Talara, de S/ 9.778 millones.
- **Tabla de gasto en celular:** resuelto en la segunda ronda; ahora muestra 10 filas y un botón "Ver más".
- **Gráfico de dengue en celular:** si se gira el teléfono, hay que recargar la página para que el texto se ajuste.
- **Pillow:** al instalar `pdfplumber` en esta computadora, pip actualizó Pillow y eso rompía la compatibilidad de Streamlit. Lo devolví a la 10.4. `pdfplumber` funciona igual para este uso, pero pip avisa del conflicto. En GitHub Actions no hay conflicto, porque el entorno es nuevo.
- **Disco:** el espacio libre bajó de 2,4 GB a 1,3 GB durante la sesión. Mis archivos temporales ya están borrados. Los datos del proyecto suman unos 2 MB, más el CSV histórico de 118 MB que dejaste en `data/raw/`.

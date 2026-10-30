# Inventario de fuentes: Observatorio FEN Piura

Verificación hecha el 30 de octubre de 2026. Cada fuente se probó con descargas reales desde un script (sin navegador). Las cifras de prueba que aparecen abajo sirven solo para comprobar que los datos se pueden leer y filtrar. No son cifras oficiales para publicar sin revisar.

## Resumen

| # | Fuente | Qué da para Piura | Nivel geográfico | Frecuencia | Formato | ¿Se puede automatizar? |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | MEF, Presupuesto y Ejecución de Gasto | PIA, PIM, certificado, comprometido, devengado y girado por pliego, ejecutora, programa, proyecto y fuente | Departamento de la meta (el gasto); provincia y distrito solo de la ejecutora | Diaria (8:30 a. m. aprox.) | CSV de 8,6 GB | **Sí** |
| 2 | MEF, Detalle de inversiones (incluye avance del Formato 12-B) | Cada inversión con CUI, costo, PIM y devengado 2026, avance físico, ubicación | Departamento, provincia, distrito y coordenadas | Diaria (archivo modificado el 29/10/2026) | CSV de 239 MB | **Sí** |
| 3 | Infobras (Contraloría) | Obras: estado, avance físico real y programado, paralización, marca de Reconstrucción con Cambios | Departamento, provincia, distrito | Diaria (el nombre del archivo lleva la fecha) | XLSX de 57 MB | **Sí** |
| 4 | DIRESA Piura, Sala de situación semanal | Dengue por distrito y semana, formas clínicas (incluido dengue grave), fallecidos, hospitalizados por establecimiento | Distrito, semana epidemiológica | Semanal (SE 42 publicada el 29/10/2026) | PDF de 222 páginas | **Parcial**: el PDF trae texto extraíble, pero las tablas se tienen que leer por página |
| 5 | CDC-Minsa, Vigilancia epidemiológica de dengue (datos abiertos) | Histórico caso por caso, 2000-2025 | Distrito, localidad, semana | El archivo se modificó el 22/10/2026 | CSV de 118 MB | **No**: el portal bloquea descargas que no vienen de un navegador (error 418) |
| 6 | SUSALUD, Producción asistencial en hospitalización (Consulta D1) | Camas, días-cama disponibles, ingresos, egresos y fallecidos por establecimiento | Establecimiento (con distrito) | Mensual, con 1 a 2 meses de retraso | CSV pequeño por mes | **Sí** |
| 7 | SUSALUD, Camas diarias F500.2 | Camas disponibles y ocupadas por día | Establecimiento | **Se dejó de publicar** en SUSALUD el 01/11/2022 | CSV | No sirve para 2026 |
| 8 | SISAP (MIDAGRI), precios | Precios mayoristas y minoristas de 52 grupos de productos; Piura figura como ciudad | Ciudad | Diaria desde 1997 | Web con exportación a Excel | **Pendiente**: la consulta se arma con JavaScript |
| 9 | Vacunación contra el dengue | Ninguna fuente abierta encontrada | — | — | — | **Pendiente** |
| 10 | CDC, teleconferencias semanales | Varían de tema cada semana; la SE 40-2026 no trae tablas de dengue por distrito | — | Semanal | PDF | No conviene como fuente fija |

## 1. MEF: Presupuesto y Ejecución de Gasto

- **Página del conjunto de datos:** https://www.datosabiertos.gob.pe/dataset/presupuesto-y-ejecuci%C3%B3n-de-gasto
- **Archivos 2026:**
  - Diario: https://fs.datosabiertos.mef.gob.pe/datastorefiles/2026-Gasto-Diario.csv (8.574.743.677 bytes; modificado el 29/10/2026 a las 13:48 GMT)
  - Mensual: https://fs.datosabiertos.mef.gob.pe/datastorefiles/2026-Gasto-Mensual.csv (7.818.194.680 bytes; modificado el 22/10/2026). Según los metadatos, se actualiza el día 3 de cada mes.
- **Diccionario:** la URL `Gastos_Diccionario.csv` responde **404** aunque el portal todavía la enlaza. Las columnas se confirmaron con la cabecera del propio CSV y con los metadatos (https://www.datosabiertos.gob.pe/sites/default/files/Gastos_Metadatos.csv).
- **Descarga:** funciona sin bloqueo, a unos 38 MB/s. Leer el archivo diario completo en flujo, por partes de 500.000 filas y sin guardarlo en disco, tomó **5,5 minutos** (9.357.060 filas). El servidor acepta descargas parciales (HTTP Range).
- **Codificación:** UTF-8, separado por comas y entre comillas. (Corregido el 30/10: en la primera versión decía latin-1 por error y salían letras mal escritas, como "PARIÃAS" en vez de "PARIÑAS".)

### Columnas confirmadas (64)

| Lo que pedía la Tarea 1 | Columna en el CSV | Observación |
| --- | --- | --- |
| Año y mes | `ANO_EJE`, `MES_EJE` | **No hay columna de fecha diaria.** La fecha de corte es la fecha de modificación del archivo |
| Departamento | `DEPARTAMENTO_META`, `DEPARTAMENTO_META_NOMBRE` | Ubicación del gasto (la meta) |
| Provincia y distrito | `PROVINCIA_EJECUTORA_NOMBRE`, `DISTRITO_EJECUTORA_NOMBRE` | **Solo de la ejecutora**, no del gasto. No existe provincia ni distrito de la meta |
| Nivel de gobierno | `NIVEL_GOBIERNO` (E nacional, R regional, M local), `NIVEL_GOBIERNO_NOMBRE` | |
| Sector, pliego, ejecutora | `SECTOR`, `PLIEGO`, `PLIEGO_NOMBRE`, `SEC_EJEC`, `EJECUTORA_NOMBRE` | En gobiernos locales `PLIEGO` viene vacío: cada municipalidad aparece como unidad ejecutora |
| Programa presupuestal | `PROGRAMA_PPTO`, `PROGRAMA_PPTO_NOMBRE` | El 0068 aparece como `"0068"` (texto con cero inicial) |
| Proyecto o producto | `TIPO_ACT_PROY` (2 = proyecto, 3 = actividad), `PRODUCTO_PROYECTO`, `PRODUCTO_PROYECTO_NOMBRE` | |
| Código único de inversión | No hay columna con ese nombre | Cuando `TIPO_ACT_PROY = 2`, `PRODUCTO_PROYECTO` tiene 7 dígitos y **coincide con el CUI** en el 85 % de los casos probados (ver la sección 2) |
| Montos | `MONTO_PIA`, `MONTO_PIM`, `MONTO_CERTIFICADO`, `MONTO_COMPROMETIDO_ANUAL`, `MONTO_COMPROMETIDO`, `MONTO_DEVENGADO`, `MONTO_GIRADO` | |
| Otros | función, división y grupo funcional, meta, finalidad, fuente de financiamiento, rubro, tipo de recurso, categoría, genérica y específica de gasto | |

### Cómo se leen los montos (verificado con los datos)

- Las filas con `MES_EJE = 0` llevan **PIA y PIM**, con devengado igual a 0.
- Las filas con `MES_EJE` de 1 a 10 llevan la **ejecución de cada mes** (compromiso, devengado, girado), con PIA y PIM iguales a 0.
- Por eso el avance se calcula como `suma(MONTO_DEVENGADO) / suma(MONTO_PIM)` sobre todas las filas.

### Prueba con Piura (archivo diario del 29/10/2026)

Se filtró por `DEPARTAMENTO_META_NOMBRE == "PIURA"`: 324.521 filas.

| | PIM (millones de S/) | Devengado (millones de S/) | Avance |
| --- | ---: | ---: | ---: |
| Total Piura | 11.669,8 | 8.793,3 | 75,4 % |
| Gobierno nacional | 4.081,0 | 3.248,0 | 79,6 % |
| Gobiernos regionales | 4.750,1 | 3.717,5 | 78,3 % |
| Gobiernos locales | 2.838,7 | 1.827,9 | 64,4 % |
| Programa 0068 (Reducción de vulnerabilidad y atención de emergencias por desastres) | 241,9 | 99,2 | 41,0 % |

Estas cifras **no se han cotejado** con la Consulta Amigable del MEF. Hay que hacerlo antes de publicarlas.

### Decisión pendiente: qué cuenta como "gasto en Piura"

- S/ 3.540 millones de PIM con meta en Piura los ejecutan entidades del gobierno nacional con sede fuera de Piura (por ejemplo, ministerios en Lima). Si se filtra por la sede de la ejecutora, ese gasto se pierde.
- 1.774 filas tienen la ejecutora en Piura y la meta en otro departamento.
- **Recomendación:** filtrar por `DEPARTAMENTO_META_NOMBRE` (dónde se gasta). Germán debe confirmarlo.

### Reconstrucción y ANIN

- ANIN: pliego `029` (AUTORIDAD NACIONAL DE INFRAESTRUCTURA), ejecutora `1750`. En Piura: PIM de S/ 699,9 millones y devengado de S/ 625,3 millones.
- Autoridad para la Reconstrucción con Cambios: aparece como unidad ejecutora en el archivo de inversiones (sección 2). Su código de pliego y ejecutora en el CSV de gasto **queda pendiente de confirmar**.
- Infobras trae una marca propia de "Reconstrucción con Cambios" por obra (sección 3).

### Automatización

Sí. GitHub Actions puede descargar el archivo diario en flujo y filtrar Piura. La descarga de 8,6 GB pasa por la red pero no se guarda: el disco del runner (unos 14 GB libres) no se llena. Lo que se sube al repositorio es solo el resumen.

## 2. MEF: Detalle de inversiones (avance físico, Formato 12-B)

- **URL:** https://fs.datosabiertos.mef.gob.pe/datastorefiles/DETALLE_INVERSIONES.csv (239 MB, UTF-8, modificado el 29/10/2026)
- **No figuraba en CLAUDE.md.** Reemplaza la consulta CUI por CUI del Formato 12-B: trae el avance de todas las inversiones en un solo archivo.
- **Columnas clave (68):** `CODIGO_UNICO`, `NOMBRE_INVERSION`, `NIVEL`, `ENTIDAD`, `NOMBRE_UEP`, `SEC_EJEC`, `ESTADO`, `SITUACION`, `MONTO_VIABLE`, `COSTO_ACTUALIZADO`, `PIA_ANIO_ACTUAL`, `PIM_ANIO_ACTUAL`, `DEV_ANIO_ACTUAL`, `DEVEN_ACUMUL_ANIO_ANT`, `SALDO_EJECUTAR`, `TIENE_F12B`, `TIENE_AVAN_FISICO`, `AVANCE_FISICO`, `AVANCE_EJECUCION`, `IND_IOARR_EMERG`, `DEPARTAMENTO`, `PROVINCIA`, `DISTRITO`, `UBIGEO`, `LATITUD`, `LONGITUD`, `FEC_INI_EJECUCION`, `FEC_FIN_EJECUCION`, `FUNCION`, `PROGRAMA`, `MARCO`, entre otras.
- **Piura:** 7.487 inversiones activas (6.013 de gobiernos locales, 971 del nacional, 503 del regional).
  - 2.017 tienen PIM en 2026: S/ 4.282,5 millones de PIM y S/ 3.280,6 millones devengados.
  - 5.016 tienen Formato 12-B; 2.424 tienen avance físico registrado.
  - 134 están marcadas como IOARR de emergencia.
- **Cruce con el gasto:** de los 2.523 proyectos con gasto 2026 y meta en Piura, **2.137 (85 %)** se encuentran por `CODIGO_UNICO` entre las inversiones ubicadas en Piura. Falta revisar el 15 % restante; pueden ser inversiones ubicadas en varios departamentos o fuera de Piura.
- **Calidad:** `AVANCE_FISICO` llega hasta 145,1 %, así que hay registros por encima de 100 % que deben marcarse o recortarse.
- **Automatización:** sí, en el mismo flujo que el gasto.

## 3. Infobras (Contraloría)

- **Página de descargas:** https://infobras.contraloria.gob.pe/InfobrasWeb/DataSets
- **Archivo:** `DataSet-Obras-Publicas DD-MM-AAAA.xlsx`. El nombre cambia cada día, así que el script debe leer el enlace desde la página de descargas. Enlace del 29/10/2026: `https://infobras.contraloria.gob.pe/InfobrasWeb/Archivo/DownloadFile?filename=DataSet-Obras-Publicas%2029-10-2026&name=DataSet-Obras-Publicas%2029-10-2026&contentType=application%2Fvnd.openxmlformats-officedocument.spreadsheetml.sheet&extension=.xlsx`
- También hay un dataset de Asociaciones Público Privadas.
- **Formato:** XLSX de 57 MB. Los encabezados están en la fila 4; las filas 1 a 3 son título, fuente y fecha de consulta. Algunos montos usan un espacio como separador decimal (por ejemplo, `1205287 56`) y hay que limpiarlos.
- **Columnas útiles:** código Infobras, nombre de obra, entidad, nivel de gobierno, **código único de inversión** (para cruzar con el MEF), departamento, provincia, distrito, estado de ejecución, avance físico programado y real acumulado (%), año y mes del avance, monto de valorización, existe paralización, causal, días paralizado, marca Reconstrucción con Cambios, adicionales y deductivos, fechas de inicio y fin.
- **Piura:** 9.807 obras de 191.180 a nivel nacional, con 7.318 CUI distintos.
  - Estado: 7.094 finalizadas, 1.759 sin ejecución, 899 en ejecución, 55 paralizadas.
  - 1.496 tienen la marca Reconstrucción con Cambios y 384 tienen alguna paralización registrada.
- **Calidad:** de las 899 obras "en ejecución", solo 146 tienen avance registrado en 2026 y 220 no tienen ninguno. El avance físico de Infobras suele estar desactualizado, por eso conviene mostrarlo junto con la fecha del último avance.
- **Datos personales:** el archivo incluye nombres de supervisores y residentes de obra. **Esas columnas no se deben guardar** en el repositorio.
- **Automatización:** sí (descarga directa, sin bloqueo).

## 4. DIRESA Piura: Sala de situación de salud (dengue 2025-2026)

- **Listado:** https://www.gob.pe/institucion/regionpiura-diresa/informes-publicaciones (buscar "sala situacional")
- **Última publicada:** SE 42-2026, el 29/10/2026, con datos al 27/10. https://www.gob.pe/institucion/regionpiura-diresa/informes-publicaciones/8772077-sala-situacional-s-e-n-042-2026-epidemiologia ; PDF: https://cdn.www.gob.pe/uploads/document/file/10878622/8772077-sala_situacional_se_42.pdf (11 MB, 222 páginas)
- **Tablas de dengue con texto extraíble** (números de página de la SE 42; pueden cambiar entre semanas):

| Pág. | Contenido | Nivel |
| --- | --- | --- |
| 21 | Casos por formas clínicas (sin signos de alarma, con signos de alarma, **grave**), confirmados, probables, **fallecidos**, letalidad | Provincia |
| 22 | Casos por semana epidemiológica, acumulado y tasa de incidencia | **Distrito × semana** (solo las semanas del semestre en curso más los totales del semestre) |
| 23 | Distritos que concentran el 90 % de los casos en las últimas 7 semanas | Distrito |
| 27-29 | **Hospitalizados** por dengue: totales, por semana y por establecimiento de salud | Región, establecimiento × semana |
| 30 | Defunciones por distrito probable de infección | Distrito |
| 70 | Serotipos por distrito | Distrito |

- **Prueba:** al corte de la SE 42-2026 la región suma 14.789 casos, 54 de dengue grave y 14 fallecidos, según la página 21. En la página 30 figuran 15 fallecidos: 5 confirmados y 10 en investigación. La diferencia se debe a cómo se cuentan los casos en investigación.
- **Lo que no trae:** vacunación contra el dengue ni camas disponibles. Solo informa hospitalizados.
- **Automatización:** parcial. El script tendría que encontrar el PDF más reciente en gob.pe, extraer el texto (con `pypdf`, ya instalado) y ubicar las tablas por su título, no por número de página. Es frágil si DIRESA cambia el formato, así que conviene validar los totales contra la tabla de provincias.

## 5. CDC-Minsa: Vigilancia epidemiológica de dengue (datos abiertos)

- **URL del archivo:** https://www.datosabiertos.gob.pe/sites/default/files/datos_abiertos_vigilancia_dengue_2000_2025_0.csv (118 MB, modificado el 22/10/2026). El nombre indica que ahora cubre **2000-2025**, no 2000-2024.
- **Columnas:** `departamento, provincia, distrito, localidad, enfermedad, ano, semana, diagnostic, tipo_dx, diresa, ubigeo, localcod, edad, tipo_edad, sexo`. Hay una fila por caso. No hay columna de fallecido.
- **Bloqueo:** `www.datosabiertos.gob.pe` responde **418** a cualquier descarga que no venga de un navegador. Es el mismo bloqueo que impide leer el dataset de camas F500.2 posterior a 2021 (sección 7). Las columnas de arriba se leyeron una sola vez con una cabecera de navegador. Después **dejé de hacerlo**, porque equivale a saltarse un bloqueo puesto a propósito.
- **Datos personales:** tiene edad, sexo y localidad por caso. Hay que agregarlo por distrito y semana antes de guardar nada.
- **Automatización:** no, por ahora. Opciones: (a) descarga manual una vez, ya que es histórico y se actualiza poco; (b) pedir acceso al Minsa o a la Secretaría de Gobierno Digital.

## 6. SUSALUD: Producción asistencial en hospitalización (Consulta D1)

- **Portal:** http://datos.susalud.gob.pe/group/producci%C3%B3n-asistencial-en-hospitalizaci%C3%B3n-por-ipress (el https no responde; funciona por http).
- **2026:** http://datos.susalud.gob.pe/dataset/consulta-d1-producci%C3%B3n-asistencial-en-hospitalizaci%C3%B3n-2026, con un CSV por mes, del `Consulta_D1_Hospitalizaciones_2026_1.csv` al `_9.csv`. El de agosto se modificó el 19/10/2026.
- **Columnas:** `ANHO;MES;UBIGEO;DEPARTAMENTO;PROVINCIA;DISTRITO;SECTOR;CATEGORIA;CO_IPRESS;RAZON_SOC;ID_HOSPITALIZACION;HOSPITALIZACION;NRO_TOTAL_HOSPIT_ING;NRO_TOTAL_HOSPIT_EGR;NRO_TOTAL_ESTANCIAS;NRO_TOTAL_PACIENTES_CAMAS;NRO_TOTAL_CAMAS;DIAS_CAMA_DISPONIBLE;NRO_TOTAL_FALLECIDOS` (separador `;`).
- **Piura, agosto de 2026:** 177 filas. Las IPRESS que no reportaron aparecen con el código `NE_0001` en lugar de números.
- **Sirve para:** camas por establecimiento y servicio, ocupación mensual. **No** es disponibilidad diaria.
- **Automatización:** sí. Hay que leer la lista de archivos de la página del dataset del año.

## 7. SUSALUD: Camas diarias F500.2

- **En SUSALUD:** "Data histórica ... F500.2 - V.2 **actualizado hasta el 01/11/2022**": http://datos.susalud.gob.pe/sites/default/files/Camas-02_11_2022.csv (175 MB).
- La versión "NUEVO ... desde el 31/03/2021" redirige a datosabiertos.gob.pe, que bloquea con 418 (ver la sección 5). **No se pudo verificar** si tiene datos posteriores a 2022.
- **Conclusión:** para 2026 no hay camas diarias abiertas confirmadas. La alternativa es la Consulta D1 mensual (sección 6) más los hospitalizados por dengue de la DIRESA (sección 4).

## 8. SISAP (MIDAGRI): precios

- **URL:** http://sistemas.midagri.gob.pe/sisap/portal2/ciudades/
- **Piura sí figura** (código de región `200000`). Tiene 52 grupos de productos, precios mayoristas y minoristas (mínimo, promedio y máximo), y consultas por día, intervalo, mes o año desde 1997. Hay un botón "Exportar a Excel".
- **Automatización: pendiente.** Una petición POST directa devuelve el formulario vacío, porque la consulta se arma con JavaScript y lleva un token (`postID`). Se podría resolver estudiando el JavaScript del sitio o automatizando un navegador. Como los precios son "posible más adelante", no avancé más.

## 9. Vacunación contra el dengue

- **No se encontró una fuente abierta descargable.** REUNIS (Minsa) muestra tableros, pero no se verificó ninguna descarga por distrito.
- Las notas de prensa (Andina, El Peruano) citan cifras de REUNIS: unas 14.000 dosis en Piura, sin fecha clara, y la llegada de 225.000 dosis el 30/07/2026 para personas de 10 a 20 años en Loreto, Piura, Tumbes y Ucayali. No se deben usar como dato.
- **Pendiente:** revisar el tablero de REUNIS a mano o pedir los datos a la DIRESA Piura (estrategia de inmunizaciones).

## 10. CDC: teleconferencias semanales y sala situacional nacional

- **Teleconferencias:** https://www.dge.gob.pe/portalnuevo/informacion-publica/teleconferencias-semanales-descargar-archivos-de-presentacion/ (la última es la SE 40-2026). Cada semana tratan un tema distinto; la SE 40 trató brotes y rabia. No sirven como fuente fija de dengue por distrito.
- **Sala situacional de metaxénicas (CDC):** https://app7.dge.gob.pe/maps2/shiny_metaxenicas_web/ (aplicación Shiny interactiva). No se verificó si permite descargas.

## Propuesta de indicadores con fuente confirmada

1. Avance del gasto público en Piura (PIM, devengado, %): MEF gasto, diario.
2. Avance por nivel de gobierno: MEF gasto, diario.
3. Avance del programa 0068 (prevención): MEF gasto, diario.
4. Avance de ANIN en Piura: MEF gasto, diario.
5. Inversiones con avance físico y financiero, filtrables por provincia y distrito: MEF detalle de inversiones, diario.
6. Obras paralizadas y obras de Reconstrucción con Cambios: Infobras, diario.
7. Casos de dengue por distrito y semana: DIRESA Piura, semanal (PDF).
8. Dengue grave y fallecidos por provincia y distrito: DIRESA Piura, semanal (PDF).
9. Hospitalizados por dengue por establecimiento: DIRESA Piura, semanal (PDF).
10. Camas hospitalarias por establecimiento: SUSALUD D1, mensual.

Pendientes: vacunación contra el dengue, camas diarias, precios (SISAP) e histórico de dengue 2000-2025 (descarga manual).

## Decisiones que necesito de Germán

1. ¿"Gasto en Piura" se filtra por la ubicación de la meta (recomendado) o por la sede de la ejecutora?
2. ¿Se acepta el dengue desde el PDF de la DIRESA, sabiendo que la extracción puede romperse si cambian el formato?
3. ¿Se descarga a mano, una sola vez, el histórico de dengue del portal de datos abiertos?
4. Vacunación: ¿se pide a la DIRESA Piura o se deja pendiente?

# Avance: ronda 9 de ajustes

Fecha: 10 de noviembre de 2026. Todo está en commits locales; **no se ha hecho push**. Falta tu revisión.

Para verla en local: `python3 -m http.server 8000 -d docs` y abrir http://localhost:8000.

## A. Marca de lo esperado

- **El 85 % frente al 86 %.**
  - El cálculo ya era uno solo y usaba la fecha de los datos del MEF, no la de hoy.
  - La diferencia venía de la fecha de los datos: con los del 08/11 el año transcurrido era 85,3 % («85 %»); con los del 10/11 es 85,9 % («86 %»).
  - Ahora hay una función con nombre propio, `esperadoGasto()`, y un solo redondeo, `esperadoFmt()`, para la portada, la tabla, su nota y la tarjeta de entidades nacionales. Con los datos de hoy, todas dicen 86 %.
- **La marca se ve más.**
  - Mide 3 px de ancho y sobresale 4 px arriba y abajo de la barra, en el azul marino del texto.
  - Lleva un borde de 1 px del color de la tarjeta, porque el azul marino sobre el rojo daba solo 2,9:1 y el borde blanco sobre el rojo da 5,7:1.
  - Sobre el verde azulado da 4,7:1, sobre el ámbar 5,2:1 y sobre la pista vacía 13:1.
- **Rótulo.**
  - En la tabla, «esperado 86 %» aparece una sola vez, sobre la marca de la primera fila, en las dos vistas.
  - En las tarjetas con una sola barra, el rótulo va siempre junto a la marca.
  - La nota de la tabla dice «La marca vertical es lo esperado al 10/11/2026: el 86 % del año transcurrido».

Antes y después, en escritorio y en celular:

![Tabla de gasto antes](avance_tarea9/tabla_antes_1280.webp)
![Tabla de gasto después](avance_tarea9/tabla_1280.webp)
![Tabla de gasto en celular](avance_tarea9/tabla_375.webp)

## B. Obras paralizadas frente al país

- **El archivo de Infobras es nacional.** `scripts/infobras.py` ahora guarda, en la misma pasada, un resumen por departamento en `docs/data/infobras_departamentos.json` (2 KB). Trae obras activas, paralizadas y el costo de cada grupo.
  - El archivo completo nunca se sube.
  - `actualizar_local.sh` incluye el nuevo JSON en su commit.
  - El JSON actual sale del archivo de Infobras del 10/11/2026.
- **Decisiones:**
  - **Lima y Callao:** quedan como vienen. Infobras separa «LIMA» (Lima Metropolitana y provincias) de «P C DEL CALLAO», sin mezclas.
  - **Filas que no son departamentos:** «SIN DATO» y «NO APLICA» cuentan en el total del país, no en el puesto.
  - **Piura:** usa las mismas cifras que el resto de la página, sin la obra de Petroperú.
  - **Promedio nacional:** es el total del país, todas las paralizadas entre todas las activas, no el promedio de los porcentajes.
- **Resultado:** Piura tiene 5,8 % de sus obras activas paralizado; el país, 5,9 %. Está en el puesto 11 de 25.
  - El título dice «Piura tiene una proporción de obras paralizadas similar a la del país».
  - El 55 va en **azul marino**, porque la diferencia (−0,1 puntos) no pasa de 1 punto.
- **El umbral de 1 punto se mantiene.** Los departamentos van de 2,3 % a 11,3 %, con mediana de 5,0 % y desviación de 2,7 puntos.
- **Segunda línea:** «Representan el 14,0 % del costo de las obras activas de Piura (país: 6,3 %)». En costo, Piura está a más del doble del país.
- **Dónde está:**
  - en la tarjeta de la portada, sin la barrita;
  - en la pestaña Obras, con un gráfico de puntos de todos los departamentos ordenados, Piura resaltado y una línea punteada para el país;
  - en el detalle, con la tabla completa por departamento;
  - la regla se explica en «Cómo se calcula» y en «Fuentes y método».
- **El gráfico y dataviz:**
  - el gris de los demás departamentos no pasa el piso de saturación del validador, que está pensado para paletas de categorías;
  - aquí el gris es contexto a propósito, y Piura va en el color de acento, más grande y con su nombre y valor en negrita;
  - la separación entre los dos colores pasa la prueba de daltonismo (diferencia de 16,2).

![Tarjeta de obras antes](avance_tarea9/tarjeta_obras_antes_375.webp)
![Tarjeta de obras después](avance_tarea9/tarjeta_obras_375.webp)
![Obras en escritorio](avance_tarea9/obras_1280.webp)
![Obras en celular](avance_tarea9/obras_375.webp)

## C. Definiciones de las causas de paralización

- **Las 15 causas** que hay hoy en Piura, más el grupo «Otras», tienen una definición en `DEFINICIONES.causas`, con causa, definición, fuente y URL. Son las mismas que revisaste.
- **En la página:** se subrayan en el gráfico de causas y en las etiquetas de la lista de las 5 obras. Funcionan con el cursor, al tocar y con el teclado; probé el toque en un celular simulado y la tecla Esc.
- **Fuentes:** el glosario de «Fuentes y método» lista todas las causas con su fuente y su enlace.
  - [Ley 32069, texto consolidado del Congreso](https://leyes.congreso.gob.pe/Documentos/2021_2026/ADLP/Texto_Consolidado/32069-TXM.pdf), artículos 63.3, 67, 68.1 a y b, 69.2 b, 76.1 y 83.1;
  - [Ley 31589 en El Peruano](https://busquedas.elperuano.pe/normaslegales/ley-que-garantiza-la-reactivacion-de-obras-publicas-paraliza-ley-n-31589-2118030-3/), artículos 2.2 y 2.4, en su texto de 2022.
- **Redacción propia:** siete definiciones no tienen una norma que las defina. En el archivo dicen «Redacción propia», y algunas mencionan una norma relacionada.
- **Pendiente de verificar:**
  - el Texto Único Ordenado de la Ley 31589 (DS 206-2024-EF), por si cambió la numeración;
  - la Directiva 005-2023-CG/GMPL de Infobras.

## D. Verificación

- **`scripts/test_pagina.py` pasa.** Además comprueba que el título y el color de las obras sigan la regla frente al país, que un caso de prueba con más paralizadas dé «más», y que cada causa de Piura tenga definición.
- **Las cifras no cambiaron.** Comparé las 7 pestañas, con el detalle abierto, entre la versión publicada (`3aff323`) y la nueva, con los mismos datos.
  - No desapareció ningún número; solo se agregaron los de la comparación con el país, la tabla por departamento y las fuentes.
  - Con estos datos, la versión publicada ya decía 86 % en todas partes.
- **Auditoría web-design-guidelines:** no encontró problemas nuevos.
  - El gráfico de puntos tiene una descripción para lectores de pantalla y su tabla en el detalle.
  - Las cifras usan números tabulares.
  - Las definiciones de causas usan el mismo botón accesible de la ronda 8.
- **`/ponytail-review`:** sin hallazgos que corregir. Una nota de redacción: «Puesto 11 de 25 departamentos» cuenta al Callao, que es provincia constitucional. Se podría decir «25 regiones»; lo dejé con tu palabra.

Las otras pestañas:

![Portada en escritorio](avance_tarea9/resumen_1280.webp)
![Gasto en celular](avance_tarea9/gasto_375.webp)
![Dengue en celular](avance_tarea9/dengue_375.webp)
![Salud en celular](avance_tarea9/salud_375.webp)
![Precios en celular](avance_tarea9/precios_375.webp)
![Fuentes y método en celular](avance_tarea9/fuentes_375.webp)

## Pendiente

- Correr `scripts/actualizar_local.sh` el próximo mes para comprobar que el resumen por departamento se genere junto con el de Piura. Hoy el JSON se generó desde el mismo Excel con un script de prueba.
- Las dos verificaciones legales de la sección C.

---

# Ronda 10: ajustes pequeños

## Marca de lo esperado

- **Fecha de lo esperado:** es la de los datos del MEF, el **10/11/2026**. Al mediodía de ese día el año va en el 85,9 %, que se muestra como **86 %**.
- **Sin rótulo colgante:** las barras ya no llevan «esperado X %» ni su rayita. La marca vertical queda igual.
- **Leyenda:** arriba va una leyenda con una muestra de la marca, «Lo esperado a la fecha: 86 % del año». Está en la tabla de gasto, en la tarjeta de gasto de la portada y en la tarjeta de ministerios y organismos nacionales.
- **Pie de la tabla:** se quitó la frase sobre la línea vertical. Queda «La emergencia FEN no lleva colores: su marco no es un presupuesto anual».

![Tabla de gasto en escritorio](avance_tarea9/r10_tabla_1280.webp)
![Tabla de gasto en celular](avance_tarea9/r10_tabla_375.webp)

## Obras: un solo archivo y título según los datos

- **Mismo archivo para Piura y el país.** Corrí `scripts/infobras.py` y los dos JSON salen del archivo de Infobras del **10/11/2026**.
  - Ninguna cifra de Piura cambió: 55 paralizadas de 953 activas (5,8 %), S/ 1.286,1 millones (14,0 % del costo).
  - No cambió ninguna obra (estado, costo, causa ni fecha de paralización).
  - El pie muestra una sola fecha.
  - Hubo que liberar espacio: el disco tenía menos de 500 MB libres y el script se detuvo la primera vez. Borré solo archivos temporales de esta sesión.
- **Efecto esperado del archivo nuevo:** el tiempo paralizada se cuenta hasta la fecha del archivo. Al pasar del 04/11 al 10/11, algunas obras suman un mes; por ejemplo, el camino vecinal de Las Lomas pasa de «3 años y 4 meses» a «3 años y 5 meses».
- **Título según dos comparaciones con el país.**
  - **Obras:** «similar» si Piura está a ±1 punto del país; si no, «más» o «menos».
  - **Costo:** «alto costo» si el porcentaje del costo paralizado es al menos 1,5 veces el del país.
  - Hoy da **«Pocas obras paralizadas, pero de alto costo»**: 5,8 % frente a 5,9 % en número de obras, y 14,0 % frente a 6,3 % en costo, 2,2 veces.
  - El 55 sigue en azul marino: el rojo es solo para «más obras» que el país.
- **Tarjeta de la portada:**
  - «55 obras paralizadas de 953 activas: 5,8 % (país: 5,9 %)»;
  - «14,0 % del costo de las obras activas (país: 6,3 %)».
  - Sin el puesto. El encabezado de la pestaña Obras usa las mismas líneas.
- **Pestaña Obras:** dos gráficos de puntos por región, uno por número de obras y otro por costo, cada uno con «Piura: puesto N de 25 (1 = el de mayor proporción)».
  - Por obras, Piura está en el puesto 11; por costo, en el **puesto 2**, después de Cajamarca (21,2 %).
  - La tabla del detalle suma el porcentaje del costo y el puesto por costo.
  - Ahora se habla de «25 regiones (24 departamentos y el Callao)».

![Tarjeta de obras en escritorio](avance_tarea9/r10_tarjeta_obras_1280.webp)
![Tarjeta de obras en celular](avance_tarea9/r10_tarjeta_obras_375.webp)
![Obras en escritorio](avance_tarea9/r10_obras_1280.webp)
![Obras en celular](avance_tarea9/r10_obras_375.webp)

## Verificación de la ronda 10

- **`scripts/test_pagina.py` pasa.** Ahora también comprueba la regla del costo alto: el umbral de 1,5, el título de hoy y el título cuando el costo no es alto.
- **Las demás pestañas no cambiaron.** Comparé con la versión anterior (`74598a4`) y Dengue, Salud y Precios no tienen ni un número distinto. Lo que se fue, a propósito:
  - en Gasto, el «86 %» de los rótulos y la fecha de la nota;
  - en la portada, el puesto «11 de 25»;
  - en Obras y en «Fuentes y método», la fecha antigua de Infobras (04/11).
  - Lo nuevo es la comparación por costo.
- **`/ponytail-review`, 3 hallazgos corregidos:**
  - se quitó de «Fuentes y método» un «Hoy: …» escrito a mano, que habría quedado viejo al cambiar los datos;
  - prueba de la regla del costo;
  - se borró un dato que no se usaba.
- **Disco:** quedan unos 600 MB libres. La próxima actualización de Infobras necesita al menos 500 MB, así que conviene liberar espacio antes de correr `actualizar_local.sh`.

## Salitral y nombres con conectores colgantes

Piura tiene dos distritos llamados Salitral: uno en Morropón (200406) y otro en Sullana (200608). Los datos ya estaban bien asignados; se corrigió solo cómo se muestran.

- **Dengue:** la tabla por distrito decía «SALITRAL (MOR) (MORROPON)».
  - Ahora quita la abreviatura de la DIRESA cuando la provincia ya va al lado y escribe los nombres con la regla de nombres legibles: «Salitral (Morropón)», «Tambo Grande (Piura)», «Veintiséis de Octubre (Piura)».
  - Lo mismo en la lista de distritos con más casos.
- **Nombres cortos de obras:** al cortar la ubicación quedaba un conector colgando. Por ejemplo, «…Salitral y Marcavelica de la» seguido de «Piura (Piura)».
  - Ahora se borran los conectores finales («de», «de la», «del», «y»…).
  - Ningún nombre de obra termina ya en un conector.
- **Pruebas y cifras:** `test_pagina.py` suma los dos casos y pasa. Ninguna cifra cambió.

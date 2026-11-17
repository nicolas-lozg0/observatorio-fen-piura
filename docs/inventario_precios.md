# Inventario de fuentes: precios de alimentos en Piura (ronda 14)

Fecha: 16 de noviembre de 2026. Solo investigación: la página no cambia. Todo lo de aquí se consultó hoy desde una conexión peruana; el acceso desde GitHub Actions no se ha probado.

Regla aplicada: se usan **páginas públicas** (también un formulario visible que se llena y se envía), **archivos enlazados desde ellas** y **portales de datos abiertos**. **No** se usan direcciones de datos que solo aparecen en las herramientas de desarrollo del navegador o dentro del código del sitio.

## Resumen

| Fuente | Piura | Tipo | Último dato | Historial | Canasta | ¿Automatizable? |
| --- | --- | --- | --- | --- | --- | --- |
| 1. SISAP, «Precios en ciudades» (Midagri) | Sí: mercados mayoristas y minoristas de Piura | Mayorista y minorista | **16/11/2026** | Al menos desde 2025 (el selector va de 1997 a 2026) | 9 de 10 (sin pescado) | **No** con la regla: la tabla llega por un endpoint interno. Sí a mano, con el botón «Exportar a Excel» |
| 2. GORE Piura, Mercado Modelo (datos abiertos) | Sí: solo el Mercado Modelo de Piura | Mayorista y minorista | **13/03/2026** (detenido) | 08/01/2024 a 13/03/2026, 151 fechas | 9 de 10 (sin pescado) | **Sí**: un CSV con enlace de descarga (no probado desde GitHub) |
| 3. SIEA (Midagri) | No se pudo saber | — | — | — | — | **No**: solo tableros de Power BI, sin archivo descargable |
| 4. INEI, precios promedio | **No hay** precios promedio por producto para Piura | — | — | — | — | No aplica |

**Son los mismos datos.** Los precios minoristas del SISAP del 10/11/2025 coinciden exactamente con los del archivo del GORE para esa fecha: aceite 10,60, azúcar rubia 4,70, huevos 9,95, frijol canario 7,25, lenteja 8,35 y papa amarilla 5,15. También coinciden las fechas de noviembre de 2025 (3, 5, 7, 10 y 12). Lo más probable es que la Dirección Regional de Agricultura (DRA) Piura recoja los precios y que el SISAP los publique. El archivo abierto dejó de actualizarse en marzo; el SISAP no.

## 1. SISAP, «Precios en ciudades» (Midagri)

- **URL:** http://sistemas.midagri.gob.pe/sisap/portal2/ciudades/ (región «Piura»).
- **Cobertura:** «Mercados mayoristas de Piura» y «Mercados minoristas de Piura», según el pie de la tabla. No dice qué mercados ni si incluye Sullana.
- **Variables:** precio mínimo, promedio y máximo, mayorista y minorista.
- **Frecuencia:**
  - Mayorista: 04/11, 11/11 y 16/11/2026, casi semanal.
  - Minorista: 11/11 y 16/11/2026 (el 04/11 vacío). En noviembre de 2025 era tres veces por semana.
- **Último dato:** 16/11/2026, en mayorista y en minorista.
- **Historial:** verificado desde noviembre de 2025; el selector de años va de 1997 a 2026. No verifiqué desde qué año hay datos de Piura.
- **Productos de la canasta para Piura (nombres exactos):**
  - Mayorista: «Arroz extra», «Arroz superior» (saco normal de 50 kg), «Carne de pollo (eviscerado)» (kg), «Cebolla cabeza roja» (saco de 50 kg), «Limon sutil bolsa» (bolsa de 50 kg).
  - Minorista: «Aceite clásico botella 900 ml» (litro), «Arroz extra», «Arroz superior», «Azucar blanca nacional (granel)», «Azucar rubia nacional (granel)», «Frijol canario», «Frijol castilla», «Huevos rosados», «Lenteja», «Papa amarilla», «Papa canchan», «Papa yungay» (kg).
  - **Pescado:** no está en la lista de productos de Piura.
- **Formato:** formulario público. Los resultados aparecen en una tabla que el navegador arma con datos de un endpoint interno; al enviar el formulario sin navegador, el servidor devuelve el formulario vacío. El botón «Exportar a Excel» funciona en el navegador.
- **Acceso:** servidor antiguo (PHP 5.3, solo HTTP, sin cifrado) con una cookie de sesión. No tiene `robots.txt` (da 404) y no vi captcha.
- **¿Automatizable desde GitHub Actions?** **No**, sin usar el endpoint interno. A mano, sí: una persona exporta el Excel.

**Muestra (filas reales, 16/11/2026, minorista Piura):**

| Fecha | Mercado | Producto | Unidad | Precio (S/) |
| --- | --- | --- | --- | --- |
| 16/11/2026 | Minorista Piura | Aceite clásico botella 900 ml | Litro | 9,85 |
| 16/11/2026 | Minorista Piura | Arroz extra | Kilogramo | 4,60 |
| 16/11/2026 | Minorista Piura | Arroz superior | Kilogramo | 4,10 |
| 11/11/2026 | Minorista Piura | Arroz superior | Kilogramo | 3,95 |
| 16/11/2026 | Mayorista Piura | Carne de pollo (eviscerado) | Kilogramo | 8,55 |

## 2. Gobierno Regional Piura: precios del Mercado Modelo

- **Dataset:** https://www.datosabiertos.gob.pe/dataset/precios-mayorista-y-minorista-del-mercado-modelo-de-piuragobierno-regional-piura-grp
- **Archivo:** https://www.datosabiertos.gob.pe/sites/default/files/mimercado_dataset.csv (750 KB, 7464 filas, CSV UTF-8, licencia ODC Attribution). Hay un diccionario en Excel en el mismo dataset.
- **Columnas:** FECHA_CORTE, DEPARTAMENTO, PROVINCIA, DISTRITO, UBIGEO, FECHA_REGISTRO, PRODUCTO, PRECIO_MAYORISTA, PRECIO_MINORISTA, CATEGORIA, UNIDAD_MEDIDA_MAY, UNIDAD_MEDIDA_MIN.
- **Cobertura:** solo el Mercado Modelo de Piura (ubigeo 200101), con precio mayorista y minorista en la misma fila. Tiene 51 productos.
- **Frecuencia:** entre 5 y 11 fechas por mes; según el dataset, se recogen «inter diario».
- **Último dato:** 13/03/2026. La web de la DRA dice lo mismo («Precios actualizados hasta: 13/03/26»), aunque el archivo se modificó el 08/09/2026.
- **Historial:** 151 fechas, del 08/01/2024 al 13/03/2026. 2024 es irregular (de 1 a 7 fechas por mes); 2025 es casi continuo.
- **Canasta:** los 9 productos tienen 151 fechas con precio minorista: «Arroz superior», «Azucar rubia nacional (granel)», «Aceite clasico botella 900 ml», «Carne de pollo (eviscerado)», «Huevos rosados», «Papa amarilla», «Cebolla cabeza roja», «Limon sutil bolsa» y «Frijol canario». También tiene lenteja, frijol castilla, garbanzo, pallar y otras papas. **No hay pescado.**
- **Unidad mayorista:** el CSV dice «SACO NORMAL» o «CAJA CHICA», pero los valores parecen por kilogramo. Arroz superior: 3,11 en el CSV (12/11/2025) y S/ 136,50 por saco de 50 kg en el SISAP (16/11/2026), es decir 2,73 por kg. Es probable, pero no está confirmado.
- **Acceso:** con un User-Agent genérico responde 200; sin él, 418. Es el mismo portal que bloqueó la descarga del dengue. Desde GitHub no se ha probado.
- **Otra vía, la web «Mi Mercado» de la DRA** (http://mimercado.regionpiura.gob.pe/, enlazada desde gob.pe): muestra solo el último precio, sin historial. Por HTTPS falla, porque el certificado está incompleto. Sirve solo de respaldo para el último dato.
- **¿Automatizable desde GitHub Actions?** Sí en principio (es un archivo enlazado), pero no verificado, y hoy los datos están detenidos.

**Muestra (filas reales, 13/03/2026, Mercado Modelo de Piura):**

| Fecha | Producto | Mayorista (S/, unidad según el CSV) | Minorista (S/ por kg) |
| --- | --- | --- | --- |
| 13/03/2026 | Arroz superior | 3,03 (SACO NORMAL) | 3,50 |
| 13/03/2026 | Carne de pollo (eviscerado) | 10,90 (KILOGRAMO) | 13,75 |
| 13/03/2026 | Huevos rosados | 6,15 (KILOGRAMO) | 10,85 |
| 13/03/2026 | Cebolla cabeza roja | 1,92 (SACO) | 4,25 |
| 13/03/2026 | Limon sutil bolsa | 1,69 (KILOGRAMO) | 2,55 |

## 3. SIEA (Midagri)

- **Página:** https://siea.midagri.gob.pe/index.php/herramientas/estadistica-agropecuarias
- **Qué tiene:** solo enlaza tableros de Power BI («Abastecimiento Mercados y Precios», «Comportamiento de Precios Semanales», «Precios de la Canasta Básica Familiar», «Comparativa de Precios Mercados Lima»).
- **Por qué no sirve:** no ofrece archivos descargables. Sacar datos de Power BI exige su API interna, que la regla no permite. No abrí los tableros, así que no sé si traen Piura.
- **`robots.txt`:** bloquea solo carpetas técnicas (`/api/`, `/components/`, `/administrator/`).
- **datosabiertos.gob.pe:** no tiene datasets de precios de alimentos del Midagri. El único dataset del Midagri es «Datero Agrario» (estadísticas de consultas, hasta 2020).
- **Muestra:** no hay filas descargables.

## 4. INEI

- **Informe técnico mensual de precios** (el que ya usa la página): solo trae **variaciones**, no precios promedio por producto. Piura aparece en el Cuadro 2.
- **Páginas de índices:** solo dan Lima y el total nacional.
- **«Precios promedio en chacra»:** es un cuadro nacional de 2012 a 2015.
- **SIRTOD:** corta la conexión por HTTPS, no responde por HTTP y es una aplicación con JavaScript.
- **Conclusión:** **no hay precios promedio de alimentos para la ciudad de Piura.** Sirve solo como complemento, con la variación mensual del IPC.

**Muestra (filas reales del IPC de Piura, ya en `docs/data/ipc_piura.json`):**

| Mes | Variación mensual | En 12 meses | Nacional, 12 meses |
| --- | --- | --- | --- |
| Junio 2026 | −0,40 % | 2,61 % | 3,57 % |
| Julio 2026 | 0,13 % | 2,75 % | 3,70 % |
| Agosto 2026 | 0,47 % | 3,27 % | 4,06 % |
| Setiembre 2026 | −0,06 % | 2,94 % | 4,17 % |
| Octubre 2026 | 0,59 % | 3,39 % | 4,83 % |

## Recomendación

- **Fuente principal:** **SISAP «Precios en ciudades», Piura, minorista**. Tiene datos al día, casi semanales, y 9 de los 10 productos. Como no se puede automatizar sin el endpoint interno, una persona exportaría cada semana el Excel con el botón visible y lo dejaría en una carpeta. Un script lo procesa, igual que `actualizar_local.sh` con Infobras y SUSALUD.
- **Historial:** el CSV del GORE (2024 a marzo de 2026), que coincide con el SISAP en los días comparados. Con él se puede comparar con el mismo periodo del año anterior.
- **Respaldo automático:** el mismo CSV del GORE, si la DRA lo vuelve a actualizar. Se descarga solo, sin endpoints internos.
- **Complemento:** el IPC de Piura del INEI, que ya está en la pestaña.
- **Carta:** dejé un borrador para Germán en `privado/carta_precios.md` (no se sube). Pide a la DRA Piura actualizar el archivo de datos abiertos y al Midagri una descarga documentada del SISAP o permiso para usar su servicio. Si alguno responde, el paso manual desaparece.

**Canasta propuesta (minorista, por kg; aceite por botella):** arroz superior, azúcar rubia, aceite clásico de 900 ml, pollo eviscerado, huevos rosados, papa amarilla, cebolla roja, limón sutil y frijol canario. El pescado queda pendiente.

**Variación semanal:** el último precio de cada semana frente al último de la semana anterior y frente al de la misma semana del año anterior (la fecha más cercana). Si un producto no tiene precio en una semana, sale «sin dato»; no se repite el precio anterior.

## Boceto de la pestaña Precios (texto, sin construir)

Los valores de aceite y arroz son reales; los demás están en blanco.

```
¿Cómo están los precios?
El IPC de Piura (INEI) y los precios de 9 alimentos en los mercados de Piura (Midagri).

[Tarjetas actuales del IPC y la canasta básica, sin cambios]

Precios de alimentos en Piura, semana del 16/11/2026
Precio minorista promedio. Frente a la semana anterior y a la misma semana de 2025.

 Producto                     Precio      Semana anterior   Hace un año
 Arroz superior (kg)          S/ 4,10     ▲ 3,8 %           ▲ 12,3 %
 Aceite clásico (900 ml)      S/ 9,85     = 0,0 %           ▼ 7,1 %
 Azúcar rubia (kg)            S/ …        …                 …
 Pollo eviscerado (kg)        S/ …        …                 …
 Huevos rosados (kg)          S/ …        …                 …
 Papa amarilla (kg)           S/ …        …                 …
 Cebolla roja (kg)            S/ …        sin dato          …
 Limón sutil (kg)             S/ …        …                 …
 Frijol canario (kg)          S/ …        …                 …

 Título por regla: «Esta semana subieron X de 9 alimentos» (más de 1 % = sube).
 Al tocar un producto: mini-gráfica de 52 semanas (este año y el anterior).

 Fuente: Midagri, SISAP «Precios en ciudades» (mercados minoristas de Piura);
 2024 a marzo de 2026: GORE Piura, Mercado Modelo (datos abiertos). Datos al 16/11/2026 · Cómo se calcula
 Más detalle: SISAP →
 Aviso «Dato no actualizado» si pasan más de 10 días sin datos nuevos.
```

## Pendientes

1. **Pescado:** ninguna fuente lo trae. Queda para otra ronda revisar PRODUCE, los desembarques en Paita y los terminales pesqueros.
2. **Acceso desde GitHub Actions** a datosabiertos.gob.pe: no probado. Ese portal devolvió 418 con el dengue.
3. **Qué mercados entran** en «mercados mayoristas/minoristas de Piura» del SISAP, y desde qué año hay datos de Piura.
4. **Unidad del precio mayorista** en el CSV del GORE: parece por kg, aunque diga «saco».
5. **Caso intermedio (ronda 13):** la lluvia del Senamhi se lee de la ventana que se abre al hacer clic en una estación del mapa público. No es secreto, pero tampoco es una descarga oficial. Conviene revisarlo con la misma regla de esta ronda; no se cambió nada.

# Avance de la Tarea 2: prototipo con gasto público

Fecha: 30 de octubre de 2026. Todo corre de principio a fin en local. **No se ha hecho push ni se ha creado el repositorio.**

## Cómo ver la página en local

Desde la carpeta del proyecto:

```
python3 -m http.server 8000 -d docs
```

y abrir http://localhost:8000 en el navegador. Hay que usar el servidor porque, si se abre `index.html` con doble clic, el navegador no deja leer los archivos de datos; en ese caso la página muestra un aviso. Para cerrar el servidor, presiona Ctrl+C en la terminal.

## Cómo actualizar los datos a mano

```
pip install -r requirements.txt
python3 scripts/test_gasto_mef.py      # prueba rápida (debe decir OK)
python3 scripts/gasto_mef.py           # unos 6 minutos; lee el CSV de ~8 GB sin guardarlo
python3 scripts/inversiones_mef.py     # requiere haber corrido gasto_mef.py
python3 scripts/infobras.py
python3 scripts/fen_mef.py
```

Cada script se detiene si el espacio libre en disco baja de 500 MB. Los resultados van a `docs/data/` (956 KB en total).

## Control con la Consulta Amigable (archivo del MEF del 30/10/2026, 9:15 a. m.)

| | Control (Consulta Amigable) | Script | Coincide |
| --- | --- | --- | --- |
| Total Piura, PIM | S/ 11.681.399.012; 75,6 % | S/ 11.681.399.012; 75,6 % | Sí |
| Gobierno nacional | S/ 4.092.598.399; 79,8 % | S/ 4.092.598.399; 79,8 % | Sí |
| Gobiernos locales | S/ 2.838.652.545; 64,7 % | S/ 2.838.652.545; 64,7 % | Sí |
| Gobierno regional | S/ 4.750.148.068; 78,6 % | S/ 4.750.148.068; 78,6 % | Sí |
| Programa 0068 | S/ 242.918.930; 41,3 % | S/ 242.918.930; 41,3 % | Sí |

Criterio usado: lugar del gasto (`DEPARTAMENTO_META`), actividades y proyectos.

## Qué hay

| Archivo | Qué hace |
| --- | --- |
| `scripts/gasto_mef.py` | Lee el CSV diario de gasto del MEF por partes mientras se descarga, se queda con Piura y lo agrega por nivel, entidad, programa y producto/proyecto. Marca cada fila según el criterio: lugar del gasto, sede de la entidad o ambos |
| `scripts/test_gasto_mef.py` | Prueba con datos inventados del filtro, la agregación y el cálculo del avance |
| `scripts/inversiones_mef.py` | Del archivo de detalle de inversiones del MEF toma el avance físico, la provincia y el distrito de cada proyecto con gasto (unión por CUI) |
| `scripts/infobras.py` | Descarga el Excel diario de Infobras, cuenta las obras de Piura por estado y guarda las paralizadas. No guarda nombres de personas |
| `scripts/fen_mef.py` | Descarga el CSV de la consulta "Ejecución del Gasto de Emergencia - FEN" y guarda lo de Piura |
| `scripts/comun.py` | Control de espacio en disco, fechas y guardado de JSON |
| `docs/index.html` | La página. Es estática y no depende de servidores ni librerías externas, así que se puede incrustar luego como iframe |
| `.github/workflows/actualizar.yml` | Corre los scripts todos los días a las 10:00 (hora de Perú) y guarda los datos nuevos |

### Contenido de la página

1. Selector "¿Qué cuenta como gasto en Piura?": **lugar del gasto** (por defecto) o sede de la entidad. Cambia todas las cifras de gasto.
2. Avance total de Piura (PIM, devengado, %).
3. Indicadores destacados: programa 0068 (prevención de desastres), programa 0017 (metaxénicas y zoonosis, que incluye dengue) y gasto de emergencia FEN.
4. Avance por nivel de gobierno.
5. Tabla de proyectos y actividades con filtros por tipo, nivel, entidad, programa y búsqueda por nombre o código. Muestra el avance financiero y, en los proyectos, el avance físico y el distrito.
6. Gasto de emergencia FEN por entidad.
7. Obras de Infobras por estado y lista de obras paralizadas.

Cada bloque indica su fuente, con enlace, y la fecha de los datos.

## Hallazgos y decisiones tomadas

- **Entidad en gobiernos locales.** En el CSV del MEF, `PLIEGO` viene vacío para las municipalidades; cada una aparece como unidad ejecutora. Por eso el filtro "Entidad" usa el pliego en los niveles nacional y regional, y la ejecutora (la municipalidad) en el nivel local.
- **Codificación.** El CSV del MEF está en UTF-8, no en latin-1 como decía el inventario; ya se corrigió en `inventario.md`.
- **Unión por CUI.** De los 2.526 proyectos con gasto, 2.150 (85 %) se encuentran en el detalle de inversiones. Los demás no aparecen en ese archivo, que solo trae inversiones activas, así que salen sin avance físico ("—").
- **Avance físico mayor que 100 %.** Hay registros así en el MEF; la página los marca en otro color como "dato a revisar".
- **Infobras.** El avance de muchas obras está desactualizado (lo registra cada entidad). La página lo advierte.
- **Consulta FEN.** Se puede descargar desde la pestaña "Descargas - Datos Abiertos" con el botón "Exportar a CSV". No hubo ningún bloqueo. Pero **el CSV trae los nombres de las columnas de montos corridos una posición**: el marco presupuestal viene bajo `MONTO_ASIGNACION`, el devengado bajo `MONTO_COMPROMETIDO_ANUAL` y `MONTO_DEVENGADO` siempre vale 0. El script compara las sumas con el TOTAL que muestra el navegador del MEF, asigna cada monto a la columna correcta y se detiene si no cuadran.
  - Para Piura, todo el gasto FEN 2026 es del gobierno nacional, con sede fuera de Piura: marco presupuestal de S/ 172,8 millones y devengado de S/ 15,0 millones (8,7 %), al 29/10/2026. Por eso, con el criterio de sede de la entidad, el gasto FEN es cero.
- **Programa 0017 en Piura:** PIM de S/ 39,1 millones, avance de 88,7 %. Incluye todas las metaxénicas y zoonosis, no solo dengue; el CSV no separa el dengue.

## Pendiente o por decidir

- **Germán:** confirmar el criterio de "gasto en Piura" (la página ya permite los dos).
- **Antes de publicar:**
  - Crear el repositorio en GitHub.
  - Configurar Pages con "Deploy from a branch", rama `main`, carpeta `/docs`.
  - Darle a `gh` el permiso `workflow` (`gh auth refresh -h github.com -s workflow`) para poder subir el archivo de Actions.
- **Historial del repositorio:** el workflow guarda los JSON cada día en el repositorio (unos 950 KB por día con cambios), y eso hará crecer el historial con el tiempo. Si llega a ser un problema, se puede publicar con un "artifact" de Pages en lugar de guardar los datos en la rama.
- **Vista en celular:** no la pude comprobar en pantalla, porque la ventana del navegador no se dejó achicar. El diseño usa cuadrículas que se adaptan y tablas con desplazamiento horizontal, pero conviene revisarla en un teléfono.
- **Quedan para después, como se pidió:** dengue epidemiológico (DIRESA) y SUSALUD.
- **Ruta de los datos:** los datos van en `docs/data/` y no en `data/` como sugería CLAUDE.md, porque GitHub Pages solo publica lo que está dentro de `docs/`.

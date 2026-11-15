# SmartSeeds · contexto para retomar el trabajo

Archivo de traspaso. Resume lo que no se ve leyendo el código: decisiones, hallazgos
y en qué punto quedó cada cosa. Actualizado el sábado 14 de noviembre de 2026 (hora de Ecuador).
El detalle de instalación y recursos está en `README.md` y `README_PROGRAMADOR.md`.

## El proyecto

- **NASA Space Apps Challenge 2026**, sede Sangolquí, equipo **Condor Mission**, reto **Dancing with the SARs**.
- **SmartSeeds:** el agricultor toca su terreno en un mapa y recibe los 3 cultivos que más le convienen, con las razones en lenguaje sencillo. Combina aptitud física (radar NISAR, NASADEM, NASA POWER) con un indicador de mercado (ESPAC del INEC, precios del MAG).
- **Entrega:** domingo 15 de noviembre antes de las 23:59 (meta del equipo: 21:00). Página en inglés, video de 30 s o 7 diapositivas, app publicada y repositorio público.
- **Reglas que afectan al código:** declarar el uso de IA, citar todas las referencias (incluido código abierto), usar al menos un dato de la NASA.

## Cómo trabajar con el equipo

- Responder en **español** y con explicaciones sencillas: quien programa no es programador avanzado.
- Comentarios y nombres del código en español.
- No inventar datos. Si una tabla no tiene valores reales, se deja vacía y la app dice "sin datos".
- Decir claramente qué está probado y qué no.

## Reparto del trabajo entre programadores

- **Esta computadora:** zonas de la Costa (Santo Domingo y Daule ya hechas). El trabajo sigue en esta misma máquina, solo cambia la cuenta de Claude: la carpeta, el entorno `condor` y el login de Earthdata ya están listos.
- **El otro programador:** hace lo mismo para la Sierra, provincias de **Cotopaxi y Tungurahua**. Esa es la zona de la Sierra del plan; no hay que procesarla aquí.
- Trabaja sobre **este mismo código** (confirmado el 14 nov).
- **Plan de repositorios acordado:** este repositorio es la base de la **Costa** y está publicado en https://github.com/JotaCenfe/smartseeds-costa (público, rama `main`). El otro programador prepara la parte de la Sierra por su lado. Cuando las dos partes estén listas se crea **un solo repositorio común** con la app completa; ese es el que se entrega.
- Para que la unión sea fácil, la Sierra debería partir de una copia de este repositorio (clonarlo o hacer "fork"), no de cero.
- Para unir sin conflictos: cada zona genera sus propios archivos (`celdas_ZONA.csv`, `nisar_ZONA.npz`, `humedad_ZONA.npz`), así que no chocan. Los archivos que sí comparten los dos son `src/config.py` (lista `ZONAS`) y `tablas/requisitos_cultivos.csv`: hacer `git pull` antes de tocarlos.
- No cambiar el formato de la tabla por celda ni las firmas de `aptitud()` y `mercado()` sin avisarle.

## Cómo ejecutar

En Miniforge Prompt, desde la raíz del repositorio y con el entorno `condor` activado:

```
python tests/prueba_rapida.py                 # lógica, sin internet
streamlit run app/app.py                      # app en http://localhost:8501
python -m src.clima_relieve ZONA              # NASADEM + POWER -> tabla por celda
python -m src.nisar ZONA procesar             # GCOV en remoto -> nisar_ZONA.npz
python -m src.nisar ZONA humedad              # SME2 en remoto -> humedad_ZONA.npz
python -m src.nisar ZONA capas                # llena las columnas NISAR de la tabla
python -m src.suelo_lluvia ZONA               # SoilGrids (pH, textura) y CHELSA (lluvia a 1 km) -> tabla + lluvia_mensual_ZONA.npz
python -m src.vecindad ZONA                   # columna `agua_vecinos` (después de `nisar ZONA capas`)
python -m src.sentinel ZONA procesar          # Sentinel-1 de enero a mayo (época lluviosa); luego `calibrar` y `tabla`
python recolectar_referencia.py descargar worldcover ZONA   # mapa de referencia ESA WorldCover -> referencia_worldcover_ZONA.csv
python -m src.cobertura entrenar              # modelo de tipo de terreno -> columna `cobertura` (ejecutar al final)
python -m src.preparar_mercado                # arma tablas/mercado.csv con los Excel de datos/crudos/mercado/ (`ver` = solo mostrar)
```

Enlace directo a un terreno para demos: `http://localhost:8501/?lat=-0.33&lon=-79.12`.

## Arquitectura

| Archivo | Papel |
|---|---|
| `src/config.py` | Rutas, zonas (`ZONAS`), formato de la tabla por celda, rejilla. **Una zona nueva se agrega aquí.** |
| `src/clima_relieve.py` | NASA POWER (en vivo) y NASADEM → `datos/procesados/celdas_ZONA.csv` |
| `src/nisar.py` | Búsqueda en ASF, lectura remota de GCOV y SME2, capas, llenado de la tabla |
| `src/aptitud.py` | Puntaje 0–100 por cultivo y razones en texto. Temperatura, lluvia y pH graduados entre el rango ideal y el que el cultivo aguanta (`tablas/ecocrop_cultivos.csv`) |
| `src/suelo_lluvia.py` | SoilGrids (pH, textura, 250 m) y CHELSA (lluvia del año y de cada mes, 1 km) → columnas de la tabla. Pide rasterio (solo desarrollo) |
| `src/sentinel.py` | Radar de la época lluviosa: Sentinel-1 (OPERA RTC-S1, banda C). Serie aparte de NISAR → `invierno_ZONA.npz` y columna `agua_invierno` |
| `src/vecindad.py` | Agua en los terrenos vecinos (`agua_vecinos`) y resumen de lo que hay alrededor de un terreno. Solo numpy y pandas |
| `src/mercado.py` | Regla alta / media / saturado sobre `tablas/mercado.csv`; fila de la provincia y, si no hay, la nacional (compara sin tildes ni mayúsculas) |
| `src/preparar_mercado.py` | Arma `tablas/mercado.csv` desde los dos Excel del SIPA. Pide openpyxl (solo desarrollo) |
| `src/recomendar.py` | Une aptitud y mercado; adjunta el suelo preferido de `tablas/suelo_cultivos.csv` (solo informativo); `reparto_mejor_cultivo()` dice qué cultivo gana en cada parte de un terreno grande |
| `src/terreno.py` | Terreno dibujado: área (ha y cuadras), celdas que toca el contorno con su `peso` (parte de la celda ocupada) y "celda promedio" ponderada con el formato acordado. Solo numpy y pandas |
| `src/cobertura.py` | Tipo de terreno por celda (columna `cobertura`). Bosque aleatorio entrenado con el radar y el mapa de referencia ESA WorldCover, más reglas físicas; si no hay referencia, KMeans. Entrenar pide scikit-learn; la app solo lee la columna |
| `recolectar_referencia.py` | En la raíz. Lee el mapa de referencia solo en las zonas y lo resume por celda; también compara y prueba modelos |
| `app/app.py` | Interfaz Streamlit; solo lee `datos/procesados/` y consulta POWER |

Contratos acordados: tabla por celda `celda, lat, lon, altura, pendiente, temp, lluvia, humedad,
encharcamiento, vegetacion` (más `humedad_confiable`); `aptitud(celda, cultivo) -> 0..100`;
`mercado(cultivo, provincia) -> alta / media / saturado / sin_datos`.
La celda puede llevar además la clave opcional `riego` (True si el agricultor dice que tiene riego); la pone la app, no está en la tabla.
Columnas opcionales de la tabla (si faltan, ese factor no cuenta): `cobertura`, `ph`, `arcilla`, `arena`, `materia_organica`, `lluvia_power`, `agua_vecinos`, `agua_invierno`. Clave opcional de la celda: `lluvia_mensual` (lista de 12), que también pone la app.

Regla de oro: **todo lo pesado se calcula antes** y la app solo lee archivos pequeños.

## Lo que ya se sabe de NISAR (no volver a descubrirlo)

- Cada archivo GCOV pesa **~7 GB**. No se descargan: se abren en remoto con `earthaccess` + `fsspec` + `h5py` y se lee solo la ventana de la zona (~15 MB, ~20 s por archivo).
- Configuración que funciona: `block_size` de 1 MB con `cache_type="blockcache"`. Con bloques de 4 MB bajaba cientos de MB por archivo.
- **La lectura se cuelga** si un mismo proceso abre más de 2 o 3 archivos seguidos. Por eso `procesar_serie` lanza un proceso aparte por fecha, con límite de tiempo y reintento, y guarda cada fecha en `datos/procesados/_nisar_tmp/`.
- Estructura confirmada: `/science/LSAR/GCOV/grids/frequencyA` (10 m) y `frequencyB` (80 m), bandas `HHHH` y `HVHV` en potencia lineal, proyección UTM. Se usa **frequencyB**: basta para celdas de ~250 m.
- **Hay que aplicar `mask`**: 0 = muestra inválida, 255 = sin dato. Las inválidas traen valores casi cero que parecen agua.
- **SME2** es la humedad de suelo de nivel 3 de NISAR: `/science/LSAR/SME2/grids/soilMoisture`, 200 m, en m³/m³, relleno −9999. El bit 0 de `retrievalQualityFlag` en 0 significa "recomendado".
- En `asf_search`, la propiedad `bytes` de NISAR es un diccionario por archivo, no un número (el ejemplo de `README_PROGRAMADOR.md` sección 5.2 falla por eso).
- No imprimir nunca el contenido de la sesión de `earthaccess`: incluye el token de Earthdata.

## Resultados en Santo Domingo de los Tsáchilas

Recuadro: lon −79.40 a −79.00, lat −0.45 a −0.05. Órbita 76 ascendente, frames 1 y 2.

- 11 fechas GCOV (19 jun – 29 oct 2026) y 10 fechas SME2 procesadas.
- El radar cubre el **76 %** de las celdas; la franja al oeste de −79,35 queda fuera de la órbita.
- HH mediana −6,0 dB, HV −11,4 dB. Índice de vegetación (RVI) entre 0,83 y 0,95: vegetación densa.
- Encharcamiento ≈ 0 % en toda la zona (época seca; a 80 m los ríos angostos no se ven).
- Humedad media 0,26 m³/m³; solo el 6 % de las celdas tiene dato "recomendado". En las demás la app muestra el valor pero no lo usa en el puntaje.
- **Consecuencia:** aquí NISAR todavía no cambia el orden de los cultivos. Cacao, banano y plátano empatan en 100.

## Resultados en Daule – Salitre – Samborondón (segunda zona, hecha el 14 nov)

Clave `daule`. Recuadro: lon −80.05 a −79.65, lat −2.05 a −1.65. Órbita 112 descendente, frames 89 y 90.

- Se eligió midiendo el agua visible (HH < −18 dB) en las tres candidatas. 21 jun: Babahoyo 1,5 %, Daule 1,5 %, Vinces 0,1 %. 31 oct: Daule 4,0 %, Babahoyo 3,0 %. Las otras dos candidatas quedan descartadas (Babahoyo `(-79.75, -2.00, -79.35, -1.60)`, Vinces `(-79.90, -1.80, -79.50, -1.40)`).
- 10 fechas GCOV (21 jun – 31 oct 2026) y 9 fechas SME2 (hasta el 19 oct). Cobertura del radar: **100 %**. Todo el proceso tarda ~15 min.
- HH mediana −8,2 dB, HV −16,8 dB. RVI entre 0,33 y 0,80 (campo abierto).
- Encharcamiento: 7,2 % de las celdas con agua en ≥ 5 % de las pasadas; 3,8 % en ≥ 10 %; 0,3 % en ≥ 30 %. El agua baja de junio a septiembre y sube a fines de octubre.
- Humedad media 0,27 m³/m³; dato "recomendado" en el 49 % de las celdas.
- **Aquí NISAR sí cambia el orden.** Terreno inundado `?lat=-1.9356&lon=-79.6511`: solo arroz (49 sin riego, 92 con riego). Terreno seco `?lat=-1.8156&lon=-79.6733`: maíz duro 100, maracuyá 92, yuca 92; con riego el arroz sube de 48 a 92 y el banano de 33 a 88.
- (Reemplazado el 14 nov a las 17:00: la lluvia ahora es la de CHELSA y el orden cambió; ver "Análisis por terreno".) POWER daba 770 mm/año para toda la zona.
- Al ejecutar Python fuera de Miniforge Prompt, `matplotlib` falla sin mensaje (código 127) si `envs/condor/Library/bin` no está en el PATH.

## Riego, empates y tiempos de cultivo (decidido con el usuario el 14 nov)

- **Riego:** la app pregunta "¿Tienes riego?". El usuario pidió expresamente que marcar "sí" **no** infle todos los puntajes. Regla en `src/aptitud.py`: el riego solo reduce la falta de agua (lluvia bajo el mínimo y suelo que se seca), nunca la borra y no toca nada más. Nota de lluvia con riego = 1 − 0,5 × (parte del agua que falta). El 0,5 (`PESO_FALTA_AGUA_CON_RIEGO`) está sin calibrar.
- **Empates (regla anterior; el orden actual está en "Análisis por terreno"):** en Santo Domingo 8 de 15 cultivos sacan 100 (9 en un terreno plano, de hasta 5° de pendiente, porque entra el arroz). `evaluar_todos()` ordena los empatados por mercado y luego por la pregunta "¿Qué buscas?" (`preferencia="pronto"` o `"largo"`). El puntaje no cambia. `empatados()` lista los que quedan fuera del top 3 con la misma aptitud.
- **Tiempos:** cada cultivo muestra la primera cosecha (`ciclo_meses`) y el tipo. Son valores preliminares. No hay datos de costos y no se deben inventar.
- Se descartó desempatar por "qué tan al centro del rango está el terreno": con rangos sin verificar daba un orden que no se puede defender (y la altura mínima 0 lo rompe en la Costa). El arreglo de fondo es tener rango óptimo y tolerable de FAO EcoCrop.
- Si el radar vio agua en el terreno, ya no se le dice al arroz que "el suelo se seca rápido".
- **Heladas:** no aplican en la Costa (Daule: mínima de 18,6 °C; Santo Domingo llega a 2.401 m con media de 11,5 °C). Quedan para la Sierra.
- **Publicar la app:** el usuario decidió esperar a unir Sierra y Costa. No publicar antes.

## El radar en la app (hecho el 14 nov)

- **Gráfico por terreno:** `nisar.cargar_series()` y `nisar.serie_del_terreno()` leen `nisar_ZONA.npz` y `humedad_ZONA.npz` y devuelven vegetación, agua y humedad por fecha. La app los muestra como tres gráficos pequeños (`st.line_chart`, sin librerías nuevas), uno por medida, nunca dos escalas en un mismo gráfico.
- **Capa sobre el mapa:** `folium.raster_layers.ImageOverlay` con una imagen RGBA de 180×180 armada desde la tabla por celda. Un solo color por capa, de claro a oscuro; gris donde no hay radar. Funciona con `st_folium` agregándola directo al mapa.
- **Vegetación sobre agua:** el RVI no vale cuando la celda es agua (sale ~1 por ruido). `AGUA_TAPA_VEGETACION = 0.5` descarta esas fechas, tanto en la tabla (`capas`) como en el gráfico.
- En `st.cache_data`, un parámetro que empieza con guion bajo **no** entra en la clave de la caché: por eso `modificado` (fecha del archivo) va sin guion bajo.
- Probado en pantalla: gráfico en el terreno inundado de Daule y capa de agua. Las capas de vegetación y humedad, y el gráfico con un terreno dibujado, solo por código.

## Tarde del 14 nov: mapa, tipo de terreno, mercado y EcoCrop

- **Dibujo del terreno:** solo polígono (se quitó el rectángulo a pedido del usuario: quería formas libres y poder mover el lindero). El botón ✎ funciona. **No pasar `edit_options={"edit": True}` a `Draw`**: con eso Leaflet.draw 1.0.2 activa la edición pero falla por dentro y no aparecen las esquinas para arrastrar.
- **Peso por celda:** `celdas_del_terreno()` revisa 6×6 puntos por celda y devuelve `peso`. El promedio, el reparto de cultivos y la serie del radar usan ese peso. El límite real de precisión sigue siendo la celda de ~250 m; bajar a ~90 m exige reprocesar las zonas y acordarlo con la Sierra (cambia `PASO_CELDA_SEG`).
- **Fondos del mapa:** `tiles=None` + tres `TileLayer` + `LayerControl` (funciona con `st_folium` y conserva el dibujo y el acercamiento). Foto: Esri World Imagery (citar; no es NASA). NASA GIBS VIIRS llega solo a nivel 9 (~250 m); las capas HLS de 30 m devolvieron teselas vacías para la fecha probada.
- **Tipo de terreno:** `python -m src.cobertura entrenar` entrena con todas las zonas que tengan serie, guarda `datos/procesados/modelo_cobertura.npz` y escribe la columna `cobertura` en cada tabla. Hay que **volver a ejecutarlo después de `nisar ZONA capas`** (ese comando no borra la columna, pero una zona nueva no la tendrá). Al integrar la Sierra, reentrenar con las tres zonas. Es no supervisado: los nombres salen de reglas y solo se comprobó con pueblos y la zona inundada.
- El usuario pidió "entrenar una IA" con las pasadas para mejorar las recomendaciones. Se le explicó que no hay datos de campo (qué cultivo dio buen resultado y dónde), así que no se puede entrenar un modelo que acierte la recomendación; lo que sí se hizo es este modelo de tipo de terreno.
- **Mercado:** `tablas/mercado.csv` con 6 cultivos nacionales 2024–2025, cifras comprobadas en el PDF de la ESPAC 2025 y en el boletín SIPA de diciembre 2025. Columnas nuevas opcionales `rendimiento_t_ha` y `rendimiento_producto`. La firma de `mercado()` no cambió. Ojo: el boletín SIPA imprime las variaciones con el signo al revés; se recalcularon desde los precios.
- **EcoCrop:** `tablas/ecocrop_cultivos.csv` (15 cultivos, comprobados uno por uno en `ecocrop.apps.fao.org/ecocrop/srv/en/dataSheet?id=CODIGO`). **Desde las 17:00 sí se usa en el puntaje** (ver "Análisis por terreno"). Simulación anterior: mejora Santo Domingo (empates de 8 a 3) pero pone haba y maíz suave con 100 en Daule y baja la papa en la Sierra (71 a 3.000 m, 45 a 3.500 m). Decisión pendiente del equipo; hace falta un rango de altura del Ecuador (INIAP).
- **Mercado por provincia: hecho** (ver la sección siguiente). Lo de este punto sobre "6 cultivos nacionales" y el boletín de diciembre quedó reemplazado.
- La herramienta de lectura web de los subagentes dejó copias de los PDF y del CSV de EcoCrop (31 MB) en `C:\Users\PC\.claude\projects\C--condor\...\tool-results\`, fuera del repositorio.

## Cultivos mapeados por el MAG (14 nov)

- La ficha del terreno muestra los cultivos estimados por el MAG y el año de su mapa (2022 o 2025). Para un polígono, la app pondera cada cuadro por cuánto lo ocupa el terreno. Los períodos de arroz mapeado describen la cartografía histórica. El riego lo confirma el agricultor.
- El selector «Capa del mapa» incluye «Cultivo mapeado (MAG)». Usa los CSV ya procesados en las zonas que los tienen. El gris de cobertura del radar no se aplica a esta capa. Las celdas sin color pueden contener cultivos que no están en las seis estimaciones consultadas.
- Prueba de orden, pendiente de decisión: adelantar un cultivo mapeado en ≥ 50 % del cuadro si está a ≤ 10 puntos del mejor cultivo elegible, conservando el puntaje y el mínimo de aptitud. En 376 puntos históricos de arroz en Daule, el top 3 pasó de 126 a 264 al simular riego confirmado y de 76 a 77 sin riego. En los 374 puntos de Santo Domingo, el cultivo registrado entró al top 3 en 128 casos antes y 129 con la regla. La app conserva el orden vigente.
- MapBiomas: se excluyó el código beta de banano 74 del grupo agropecuario y se acotaron las solicitudes de GDAL. Prueba de cobertura: el 79 % se refiere a los cuadros con clase dominante incluidos en la evaluación.
- Sentinel-1: el procesamiento de agua conserva VV. La opción `--vh` guarda adicionalmente VH cuando la ráfaga la incluye. Para el piloto se seleccionan archivos concretos, porque el comando de una zona completa recorre todas las fechas.
- Pilotos con archivos reales (14 nov): OPERA RTC-S1 VH de ASF, tres GeoTIFF completos (~21,4 MB): dos fechas en Daule y una en Santo Domingo. En Daule, la mediana VH estuvo entre −17,2 y −16,0 dB para celdas dominadas por arroz en el mapa del MAG y entre −9,5 y −9,0 dB para banano. Muestra exploratoria sin máscara de calidad; Santo Domingo no aportó celdas con un cultivo MAG dominante dentro de la ráfaga probada. NASA HLS S30 v2: dos escenas completas de Daule; tras Fmask quedó despejado el 1,87 % y 4,25 % del área, respectivamente (1,65 % común). En Santo Domingo, la Fmask del 19 de junio dejó despejado el 4,61 % del área; las bandas ópticas seguían en transferencia al registrar este resultado. Para otro piloto, seleccionar escenas por el área despejada dentro de la zona y medir el efecto de VH en los mismos bloques de prueba con máscara de calidad. Los archivos de los pilotos se conservaron fuera del repositorio.
- Sierra: Cotopaxi y Tungurahua todavía no están como zonas detalladas en `src/config.py`. Al integrarlas, revisar qué capas del MAG cubren sus cultivos y qué nombres usan los puntos SIGTIERRAS. Luego ejecutar `cultivos_mapeados` (`descargar`, `tabla`, `comparar`) y `validar_campo` (`descargar`, `medir`) por zona.
- Licencia y cita: ver «Cultivos mapeados y observaciones de campo» en el README. El catálogo de Datos Abiertos indica uso no comercial para las capas de 2022 consultadas. Queda por confirmar la variante exacta y las condiciones específicas de las capas de 2025 y de SIGTIERRAS.
- Verificación: pasó `tests/prueba_rapida.py`. Streamlit AppTest abrió la ficha y seleccionó la capa en puntos de Daule y Santo Domingo con los CSV reales y NASA POWER simulado. También se comprobó la ponderación y ausencia de datos en un polígono representado por celdas, y la compatibilidad de VH con GeoTIFF y NPZ de prueba. Queda la comprobación visual del mapa en navegador.

## Radar de la época lluviosa: Sentinel-1 (14 nov)

El usuario autorizó procesar OPERA RTC-S1 sobre Daule ("Sí, procesar", ~1,8 GB de lectura). Hecho solo en Daule.

- **`src/sentinel.py`:** `procesar` (enero–mayo), `calibrar`, `tabla [UMBRAL]`, y `fecha FECHA` (uso interno: cada fecha va en su propio proceso con límite de 420 s, como en NISAR). Busca con `asf.search(dataset="OPERA-S1", processingLevel="RTC")`; los archivos están en `properties["additionalUrls"]` (`..._VV.tif`, `..._VH.tif`, `..._mask.tif`; `properties["url"]` es un `.h5` de metadatos). Se usa VV y la máscara (0 = dato bueno).
- **Lectura:** `fs.cat_file(url)` con la sesión de `nisar.sesion_remota()` y `rasterio.io.MemoryFile`; no se guarda el GeoTIFF. ~25 s por fecha (6 ráfagas la órbita 18, 3 la órbita 40). Las 55 fechas (46 de invierno + 9 de calibración) salieron a la primera, sin cuelgues.
- **Parciales:** `datos/procesados/_s1_tmp/ZONA_FECHA.npz` (13 MB, en `.gitignore`) guardan VV medio y el agua para los nueve umbrales de `UMBRALES_DB`: cambiar de umbral es solo `python -m src.sentinel daule tabla -20`, sin volver a leer.
- **Umbral:** `UMBRAL_AGUA_VV_DB = -19`. Sale de `calibrar`: Sentinel-1 de la época seca a ≤ 2 días de una pasada de NISAR (9 fechas, todas de la órbita 40, un día antes de NISAR). Coincidencia cuadro por cuadro (cuadros con agua ≥ 25 % para los dos / para alguno): 27 % con −19 dB; 26 % con −18 y con −20. Es baja y está declarada. Las cantidades por mes sí se parecen a las de NISAR.
- **Resultado:** `invierno_daule.npz` (5,9 MB: fechas, agua, vv, umbral_db) y columna `agua_invierno` (parte del cuadro con agua, promedio enero–mayo; 0 en laderas de más de 10°). Daule: 18,8 % de las celdas con ≥ 5 %, 12,3 % con ≥ 10 %, 3,0 % con ≥ 30 %. Agua en la zona: ene 0,9 %, feb 2,4 %, mar 8,0 %, abr 4,4 %, may 2,9 %.
- **Puntaje:** factor "Invierno" (límites del encharcamiento: 0,3 no tolera, 0,6 parcial, sin límite si tolera). Con `agua_invierno` en la celda, el factor "Alrededores" (`agua_vecinos`) **no se agrega**. El arroz usa el mayor de `encharcamiento` y `agua_invierno` para decidir si "el agua ya está ahí".
- **App:** aviso de la época lluviosa, capa "Agua en invierno (Sentinel-1)" (`CAPAS_RADAR`), gráfico por pasada dentro del desplegable del radar (`sentinel.agua_del_terreno`). El selector de capas ya no dice "NISAR" en el título.
- **Demo nueva:** `?lat=-1.9444&lon=-79.8489` (seco para NISAR, 43 % de agua en invierno → arroz 100, palma 51). Las otras demos de Daule casi no cambian (el terreno seco baja de 100 a 99).
- **Santo Domingo no se procesó.** Sin `agua_invierno`, ahí siguen contando los vecinos. Para procesarlo: `python -m src.sentinel santo_domingo procesar` (366 archivos, ~25 min) y `calibrar` (NISAR casi no ve agua ahí, así que la calibración dirá poco: usar el umbral de Daule).
- **Para la Sierra:** mismos comandos; en laderas la banda C da sombras (la máscara y la regla de 10° ayudan). No se probó.
- **Probado en pantalla:** el terreno de la demo nueva (aviso, puntaje, gráfico). **Solo por código:** la capa del mapa, un terreno dibujado.

## Tipo de terreno con mapa de referencia (14 nov)

El usuario entregó `TRASPASO_SMARTSEEDS.md` (revisión del commit `ea4e0a3` hecha en otra sesión) y `recolectar_referencia.py`, y pidió seguir su sección 4. Hecho: pasos 1 y 2, y la comprobación del paso 3.

- **`recolectar_referencia.py`** está en la raíz del repositorio, tal como lo entregó el usuario. Comandos: `descargar`, `comparar`, `probar`, con `worldcover` o `mapbiomas`.
- **MapBiomas no se puede leer sin cuenta de Google** (`storage.googleapis.com/mapbiomas-public/...` responde 403 "Anonymous caller does not have storage.objects.get access"; se probaron seis rutas). El script se queda colgado en ese caso: no volver a ejecutarlo con `mapbiomas` sin los archivos locales. La página de MapBiomas citada en el traspaso dio 404. Para usarlo, el usuario tendría que bajar los tres GeoTIFF con su navegador a `datos/crudos/referencia/`.
- **WorldCover funciona** (tile `S03W081`, 101 MB; solo se lee la ventana de 4.800 × 4.800 píxeles por zona, menos de un minuto). Reparto por cuadro: Santo Domingo árboles 85 %, pasto 13 %, construido 2 %; Daule cultivo 39 %, pasto 23 %, humedal 19 %, árboles 15 %, agua 2 %, construido 2 %.
- **`python -m src.cobertura entrenar`** ahora elige solo: si existe `referencia_worldcover_ZONA.csv` de alguna zona usa `entrenar_con_referencia()` (bosque aleatorio, 200 árboles, `class_weight="balanced"`, rasgos del radar + pendiente); si no, el KMeans de antes (`entrenar()`). Una zona sin referencia también se clasifica, con lo aprendido en las otras.
- Las celdas que enseñan reciben la clase de un modelo que **no vio su bloque** (`cross_val_predict` con `GroupKFold` por bloques de 30 × 30 celdas): el acierto medido vale para todo el mapa.
- **Clases:** las mismas seis claves de antes, así la app no cambió. WorldCover → app en `CLASE_DE_REFERENCIA` (árboles → `vegetacion_densa`, cultivo → `cultivo_activo`, humedal → `inundable`, pasto, arbustos y suelo desnudo → `vegetacion_baja`). Cambiaron los nombres visibles: "Cultivo de ciclo corto" y "Pasto o vegetación baja".
- **Reglas** (`aplicar_reglas`): `PENDIENTE_MAX_CONSTRUCCION = 10`, `PROBABILIDAD_MIN_CONSTRUCCION = 0.75` (con 0,5 acertaba el 53 % de las veces que decía "construcciones"; con 0,6 el 65 %; con 0,75 el 77 % y encuentra el 76 %), agua ≥ 0,5 → `agua`, agua ≥ 0,10 → `inundable`.
- **Acierto:** 79 % (52 % diciendo siempre la clase más común); promedio por clase 71 %; Santo Domingo 86 %, Daule 71 %; "¿cultivo de ciclo corto?" 91 %. Guardado en `datos/procesados/cobertura_evaluacion.json`; `cobertura.texto_evaluacion()` arma la frase que muestra la app.
- **El modelo de antes contra la misma referencia:** "construcciones" confirmadas 59 % (Santo Domingo) y 33 % (Daule); 62 laderas de más de 10° marcadas como construidas con 2 % de zona construida real.
- El tipo de terreno **no entra en el puntaje**: avisa, deja fuera lo no cultivable en un terreno dibujado y se pinta en el mapa. Los tres terrenos de demostración dan lo mismo que antes.
- No se usaron las clases "bosque natural" y "páramo" que proponía el traspaso: solo existen en MapBiomas. Para la Sierra (páramo) haría falta MapBiomas o aceptar que WorldCover lo llama pasto o arbustos.
- **Al integrar la Sierra:** `python recolectar_referencia.py descargar worldcover ZONA` y luego `python -m src.cobertura entrenar` (reentrena con todas las zonas).
- **OPERA RTC-S1 (paso 3 del traspaso), solo comprobado:** `asf.search(dataset="OPERA-S1", processingLevel="RTC", ...)`. Daule ene–may 2026: 221 archivos, 46 fechas, órbitas 18 ascendente (151) y 40 descendente (70), VV y VH. Santo Domingo ene–may: 366 archivos, 46 fechas. Jun–oct: 236 y 357 archivos, 50 fechas. A ~8 MB por archivo, la época lluviosa de Daule son ~1,8 GB si se descarga completa. Es banda C: guardarla como serie aparte de NISAR.
- **Del traspaso, ya estaba hecho** antes de recibirlo: hallazgo 1 (rangos graduados, y además lluvia de CHELSA y suelo de SoilGrids) y parte del 2 (el orden ya no depende de empates exactos). **Sigue pendiente:** hallazgo 3 (suavizar el mercado: promedios de dos años y exigir una baja de precio de al menos 5 %; decisión del equipo), y la lista "antes de entregar" (inglés, versiones en `requirements.txt`, licencia, etiquetas de fuente en `requisitos_cultivos.csv` y en la barra lateral, ejemplo 5.2 de `README_PROGRAMADOR.md`, referencias y declaración de IA).
- **Probado en pantalla:** la frase del modelo y el tipo de terreno en un punto de Daule. **Solo por código:** el resto.

## Análisis por terreno (14 nov, 17:00)

Pedido del usuario: "en cada zona que se pulsa nos da exactamente el mismo resultado"; quiere que el análisis use de verdad el terreno, los terrenos aledaños y cómo les ha ido a los cultivos cerca. Se midió y era cierto: 90 % de los terrenos de Santo Domingo y 98 % de los de Daule recibían el mismo top 3. Ahora el resultado más repetido es 27 % y 43 %.

- **Orden de los comandos por zona:** `clima_relieve` → `nisar ... capas` → `suelo_lluvia` → `vecindad` → `cobertura entrenar`. `clima_relieve` vuelve a poner la lluvia de POWER: después hay que repetir `suelo_lluvia`.
- **`src/suelo_lluvia.py`:** SoilGrids por WCS (`maps.isric.org/mapserv`, capas phh2o, clay, sand, soc; 0–30 cm ponderado; 12 KB por capa, guardadas en `datos/crudos/suelo/ZONA/`) y CHELSA V2.1 leído en remoto con rasterio `/vsicurl` (bio12 y pr_01..12, ~8 s por ventana). Valor del cuadro más cercano, sin interpolar. Escribe `ph`, `arcilla`, `arena`, `materia_organica`, `lluvia` (CHELSA) y `lluvia_power` (lo anterior), y `lluvia_mensual_ZONA.npz`. `rasterio` solo hace falta aquí; la app no lo importa. Fuera de Miniforge Prompt hay que definir `GDAL_DATA` o sale un aviso inofensivo.
- **CHELSA frente a POWER:** Santo Domingo 2.861–4.965 mm (POWER 1.559); Daule 1.304–1.889 (POWER 770). No se comprobó con estaciones del INAMHI.
- **Puntaje graduado (`src/aptitud.py`):** `cargar_requisitos()` une `requisitos_cultivos.csv` con `ecocrop_cultivos.csv` (columnas `temp_opt/abs`, `lluvia_opt/abs`, `ph_opt/abs`); `requisitos_cultivos.csv` no se tocó. Nota 1 en el rango ideal, 0 en el límite que aguanta. Si el cultivo no tiene esos rangos se usa la regla anterior (rango + margen). Altura y pendiente siguen como antes. La firma de `aptitud()` no cambió.
- **Lluvia del ciclo:** en cultivos `ciclo_corto`, si la celda trae `lluvia_mensual` (12 números), se prueba cada mes de siembra y se toma el mejor. Sin ese dato usa la lluvia del año y llover de más no resta. A nivel nacional la app pasa la lluvia mensual de POWER.
- **Constantes sin calibrar:** `PESO_EXCESO_LLUVIA = 0.5`, `AGUA_VECINOS_MAX = 0.5`, `AGUA_VECINOS_MINIMA = 0.05`, `BANDA_PUNTOS = 5`, `HECTAREAS_CON_EXPERIENCIA = 500`, `RADIO_VECINOS_M = 1000`.
- **Andinos:** `ecocrop_cultivos.csv` tiene columnas `temp_opt_*_ecuador_C` y `fuente_ecuador` para haba (7–14 °C), maíz suave (10–20) y quinua (9–16), de Basantes (2015) vía el catálogo del equipo. Los cultivos con altura mínima ≥ 1.500 m sin ese dato (papa, tomate de árbol) **no** usan la temperatura de EcoCrop (`ALTURA_CULTIVO_ANDINO_M`). El catálogo solo da para la papa temperaturas de día y de noche, que no son la media: falta una fuente (INIAP). **Avisar al programador de la Sierra.**
- **Se probaron y se descartaron** dos atajos para la lluvia de más: sin castigo, el maíz salía con 76 en Daule (donde hay 45 mil ha); quitando el castigo solo al ciclo corto salía primero en Santo Domingo con 3.500 mm. Por eso se hizo la lluvia del ciclo.
- **Vecinos (`src/vecindad.py`):** `agua_vecinos` = parte de los cuadros a menos de 1 km con encharcamiento ≥ 5 % (sin contar el propio). Daule: 30 % de las celdas con algún vecino con agua, 19 % con más del 10 %, 9 % con más del 30 %. Santo Domingo: 0 %. `resumen_vecinos()` es para la pantalla.
- **Provincia (`tablas/siembra_provincias.csv`):** la escribe `preparar_mercado`. `mercado.evidencia_local()` y `mercado.mas_sembrados()`. Santo Domingo: cacao 29.780 ha, plátano 17.784, piña 7.006, palma 5.937, yuca 4.323. Guayas: arroz 259.676, cacao 104.939, banano 75.858, maíz duro 45.313.
- **Orden nuevo:** franja de 5 puntos → evidencia de la provincia → mercado → preferencia → puntaje exacto. El usuario había pedido antes mercado primero; se puso la provincia delante por este pedido y **está avisado**: si prefiere mercado primero, es cambiar el orden de dos claves en `evaluar_todos()`.
- **Demos:** Santo Domingo → maíz duro 100, cacao 94, palma 91. Daule seco → plátano, palma, banano (100; arroz 78 sin riego, 96 con riego). Daule inundado → arroz 100 con o sin riego. Ya **no** hace falta marcar "Sí, tengo riego" en el terreno inundado.
- **Catálogo del equipo v0.7.2** (`Downloads/SMARTSEEDS_catalogo_integrado_v07.2.json`, 1,9 MB, no copiado al repositorio): sus EcoCrop coinciden con los nuestros. Sus reglas dicen que nada es "regla automática validada" y que su uso previsto es contrastar con datos satelitales en otro módulo: decirlo así en la entrega.
- **Archivo de estadísticas del equipo** (`CÓDIGO ESTADÍSTICAS AGROPECUARIAS.json`): sin fuentes; varias cifras no coinciden con la ESPAC ni con el SIPA (detalle en el README). No se usó. Pedir fuente y año.
- **Probado en pantalla:** punto en Santo Domingo y terreno inundado de Daule. **Solo por código:** terreno dibujado (100 celdas junto a la zona inundada: arroz 100), nivel nacional, Daule seco.
- **Idea pendiente (sigue abierta):** el mapa de uso de la tierra del MAG (SIGTIERRAS) diría qué cultivo hay en cada terreno vecino. Hay que pedir permiso para descargarlo; no se sabe el tamaño.

## Mercado por provincia (14 nov, 15:00)

- El usuario autorizó descargar los 4 archivos oficiales. Están en `datos/crudos/mercado/` (no se suben): `superficie-produccion.xlsx` y `precios-productor-ponderado.xlsx` del SIPA, y los tabulados de la ESPAC 2024 y 2025 (descomprimidos en `espac_2024/` y `espac_2025/`, solo para comprobar). Ahí mismo quedó `mercado_anterior_dic_dic.csv`, la tabla de 6 cultivos anterior.
- `python -m src.preparar_mercado` escribe `tablas/mercado.csv`: **45 filas** = 13 cultivos nacionales + 32 por provincia (16 provincias). Sin datos: **haba** (5 meses de precio, solo Carchi) y **quinua** (sin precios; además la ESPAC 2025 ya no trae su tabla por provincia y da 56 ha en el país).
- **Método:** superficie plantada 2024 → 2025 (suma de Solo + Asociado + Invernadero = total del INEC). Precio: promedio en USD/kg de los pares provincia-mes que existen en los dos años. Umbrales elegidos por el equipo, sin calibrar: `MESES_MINIMOS = 6`, `HECTAREAS_MINIMAS = 500`. Una fila de provincia solo se escribe si la superficie **y** el precio son de esa provincia (no se mezcla superficie provincial con precio nacional).
- **Comprobado:** los totales nacionales del Excel del SIPA son idénticos a los tabulados de la ESPAC en los 15 cultivos y los dos años; también arroz y cacao en Guayas, Santo Domingo y Cotopaxi.
- **Cambió el método del precio** respecto a la primera versión (antes dic 2024 contra dic 2025 del boletín; ahora año contra año). Efecto: palma pasó de media a **alta**; cacao sigue saturado pero con −13 % en vez de −44 %. El usuario está avisado; si prefiere lo anterior, la copia está en `datos/crudos/mercado/`.
- Ojo con el período: yuca da +5 % año contra año pero −45 % de diciembre a diciembre; café +33 % contra 0 %. El resultado depende mucho del período elegido.
- **Efecto en las demos:** Santo Domingo `?lat=-0.33&lon=-79.12` → maracuyá, plátano (alta, dato provincial) y maíz duro; el cacao queda "media" en Santo Domingo. Daule seco → maíz duro 100 pero **saturado en Guayas** (+27 % de superficie, −8 % de precio).
- Para la Sierra ya hay filas de Cotopaxi (cacao, plátano, papa) y Tungurahua (papa); papa saturada en las dos.
- El precio nacional es un promedio simple entre provincias, no el ponderado oficial del boletín (difieren: cacao dic 2025 204,81 contra 217,80 USD por quintal).
- En el Excel de precios hay datos de 2026 hasta octubre; no se usan porque no hay ESPAC 2026.

## Pedidos del programador de la Sierra (14 nov) y qué falta

Analizados contra la app actual. Nada de esto está hecho todavía, salvo lo marcado.

- **Dibujar el terreno en el mapa** (polígono irregular, terrenos grandes): **hecho el 14 nov.** En la app hay dos modos: tocar un punto o dibujar el contorno (`folium.plugins.Draw` + `st_folium`). El terreno dibujado se promedia con `src/terreno.py`; las firmas de `aptitud()` y `mercado()` no cambiaron. Límite: cada celda mide ~250 m (~6 ha).
  - Probado en pantalla: dibujar dentro de Daule (promedió 1.439 celdas) y fuera de las zonas (nivel nacional). La lista "tu terreno no es igual en todas partes" se probó solo por código (353 ha junto a la zona inundada: 57 % maíz duro, 43 % arroz). El botón de corregir el dibujo y el uso en celular no se probaron.
  - Los textos en español de los botones se inyectan con un `MacroElement` agregado al mapa **antes** de `Draw`; `get_root().script.add_child(...)` no funciona con `st_folium`.
  - Streamlit no recarga los módulos de `src/` ya importados: tras cambiarlos hay que **reiniciar** `streamlit run`.
  - Si hay varios dibujos se analiza el último. El modo dibujo no tiene enlace directo (`?lat=&lon=` es solo para el punto).
- **Heladas en la Sierra:** NASA POWER entrega `T2M_MIN` (comprobado: 1,9 °C mínimo en la celda de Latacunga/Ambato, a 2.958 m de altura media; `FROST_DAYS` da 0 ahí). Faltaría ajustarlo por altura por celda y una columna `tolera_heladas` con fuente en `requisitos_cultivos.csv`.
- **Suelo del terreno:** la app no lo mide. Ya se muestra el suelo que prefiere cada cultivo (hecho). Para usarlo en el puntaje falta un mapa de suelo (SoilGrids: pH y textura; no es de la NASA).
- **Qué hay sembrado y sobreproducción:** NISAR a 80 m y sin datos de campo no distingue papa de maíz; no prometerlo. Lo viable: superficie y rendimiento por cultivo y provincia de la ESPAC en `tablas/mercado.csv` (hoy vacía), mostrar quintales por cuadra y el aviso de mercado saturado (la regla ya existe), y usar el radar solo para "hay cultivo / suelo desnudo / inundado".
- **Uso del suelo ("franja agrícola"):** no hay capa de cobertura; la app recomienda aunque el punto sea ciudad, bosque o páramo.

## Pendientes, por prioridad

1. **Segunda zona con inundación real:** hecha (Daule, ver arriba). La época lluviosa ya está cubierta con Sentinel-1 (ver "Radar de la época lluviosa"). Queda calibrar los umbrales de agua con datos de campo.
2. **Requisitos de cultivos:** `tablas/requisitos_cultivos.csv` tiene valores **preliminares** escritos de memoria. Verificar con FAO EcoCrop / INIAP. Los 5 cultivos de Sierra se agregaron solo para probar.
   - El equipo entregó `catalogo_cultivos_v01.json` (14 nov): 15 cultivos con **suelo** (pH, textura, drenaje, materia orgánica, salinidad) de tres fuentes con página, y 5 candidatos sin datos (rosa, clavel, aguacate, mora, uvilla). Se copió tal cual a `tablas/suelo_cultivos.csv` y la app lo muestra en la ficha del cultivo **sin usarlo en el puntaje** (el catálogo pide no tratarlo como umbral, y la app no mide el suelo del terreno).
   - El catálogo **no trae altura, temperatura ni lluvia**. Sin esos rangos no se pueden puntuar los 9 cultivos nuevos (fréjol, arveja, lenteja, chocho, trigo, cebada, amaranto, tomate, soya): pedirlos al equipo, de las mismas fuentes.
   - El "Maíz" del catálogo (libro de cultivos andinos) se asoció a `maiz_suave`; falta confirmarlo con el equipo.
3. **Mercado:** hecho para 13 cultivos (nacional y por provincia). Faltan haba y quinua (sin precios en el SIPA) y decidir con el equipo los umbrales (6 meses, 500 ha) y el período del precio.
4. **Subir a GitHub** (repositorio público) y publicar en Streamlit Community Cloud con `requirements.txt`.
5. Mejoras de la app: textos en inglés. (El gráfico de la serie del radar y la capa NISAR sobre el mapa ya están hechos.)
6. Integrar la zona de la Sierra (Cotopaxi y Tungurahua) que prepara el otro programador.

## Limitaciones a declarar en la entrega

- NASA POWER da un valor por celda de ~50 km: la lluvia es la misma en toda una zona.
- La temperatura por celda se ajusta por altura con un gradiente fijo de 6,5 °C por km.
- El umbral de agua (HH < −18 dB) y la escala de humedad (0,5 m³/m³ = saturado) son valores iniciales sin calibrar.
- El análisis de NISAR cubre solo la época seca de 2026. El invierno se mira con otro radar (Sentinel-1, banda C), de un solo año, y los dos radares coinciden poco cuadro por cuadro (27 %).
- El tipo de terreno se aprendió de un mapa de 2021 (ESA WorldCover), no de trabajo de campo: coincide con él en el 79 % de los cuadros con un tipo dominante incluidos en la evaluación, y "agua" y "pasto" son sus clases más débiles.
- El suelo (SoilGrids) y la lluvia local (CHELSA) vienen de mapas mundiales hechos con modelos: son una orientación, no una medición del terreno. No son de la NASA.
- Los rangos de los cultivos (FAO EcoCrop) son mundiales y el catálogo del equipo pide no tratarlos como reglas validadas. Los pesos de la lluvia de más, del agua en los vecinos y la franja de 5 puntos no están calibrados.
- "Cómo les va a los cultivos cerca" es un dato de la provincia (ESPAC), no de los terrenos vecinos.
- El mercado compara solo dos años (2024 y 2025); el dato por provincia de la ESPAC viene de una encuesta por muestreo y el precio nacional es un promedio simple entre provincias.

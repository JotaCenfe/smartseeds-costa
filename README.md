# SmartSeeds · Equipo Condor Mission
### NASA Space Apps Challenge 2026 · Sede Sangolquí · Reto: Dancing with the SARs

**SmartSeeds** es una app donde el agricultor marca su terreno y recibe qué cultivos le convienen,
explicando por qué: lo que su suelo permite (según el radar NISAR y datos de la NASA) y lo que el
mercado necesita (según datos agrícolas del Ecuador).

> **Regla del concurso:** el desarrollo empieza el **sábado 14 a las 9:00**. Antes solo se preparan
> herramientas, cuentas, lectura y verificación de datos.
> **Envío:** domingo 15 antes de las **23:59** (meta del equipo: 21:00).

---

## 1. La idea en una página

### Por qué NISAR
En las zonas agrícolas del Ecuador casi siempre hay nubes y los satélites ópticos fallan.
NISAR (NASA-ISRO) es un radar que **ve a través de las nubes**, de día y de noche, cada 12 días y gratis.
Su banda L atraviesa la vegetación.

### Qué aporta el radar al agricultor

| Capa NISAR | Pregunta que responde |
|---|---|
| Humedad del suelo | ¿Tu terreno retiene agua o se seca rápido? |
| Encharcamiento / inundación | ¿Se te inunda en época de lluvia? |
| Actividad de la vegetación | ¿Qué se cultiva alrededor, cuándo se cosecha, hubo tala? |
| Estabilidad del terreno (opcional) | ¿La ladera es estable para cultivos permanentes? |

### Cómo recomienda
1. **Aptitud física (0–100) por cultivo:** altura y pendiente (NASADEM) + clima (NASA POWER) + capas NISAR + requisitos de cada cultivo (FAO EcoCrop / INIAP).
2. **Indicador de mercado:** tendencias de producción (ESPAC del INEC) + precios (MAG) → oportunidad alta / media / mercado saturado. Es una **recomendación**, no una orden.
3. **Resultado:** los 3 mejores cultivos, cada uno con sus razones en lenguaje sencillo.

### Escala: nacional + zonas detalladas

| Nivel | Cobertura | Datos |
|---|---|---|
| **Nacional** | Todo Ecuador | Clima, relieve, suelo, mercado por provincia (datos livianos) |
| **Detallado con NISAR** | 2 zonas de demostración | Humedad, encharcamiento y vegetación a 20–30 m (precalculado) |

Cada pasada de NISAR pesa varios GB, por eso el detalle se procesa por zonas.
**Zonas propuestas:** una de la **Costa** (Santo Domingo de los Tsáchilas) y una de la **Sierra** (por definir).

**Validación:** ¿la app recomienda los cultivos que ya prosperan en cada zona?

---

## 2. Datos ya verificados (13 nov) – Santo Domingo de los Tsáchilas

Recuadro: lon −79.40 a −79.00, lat −0.45 a −0.05

- **NISAR GCOV:** serie de **11 fechas** (path 76, ascendente), del 19 jun al 29 oct 2026, cada 12 días.
  También series descendentes de 10 fechas (path 112) y otra ascendente (path 4).
  Cada serie se analiza por separado (no se mezclan geometrías).
- **NISAR SME2:** 52 productos. Parece ser la **humedad de suelo nivel 3 de NISAR** → confirmar en la NISAR Data User Guide.
- **NASA POWER:** 24,3 °C media anual, ~1.560 mm/año. Celdas de ~50 km: comparar con INAMHI y declararlo como limitación.
- **SMAP:** 36 archivos en octubre 2026 (respaldo de humedad).

⚠️ Las fechas NISAR disponibles son de **época seca** (jun–oct). Para encharcamiento conviene buscar
datos BETA de la época lluviosa (ene–may): cambiar `INICIO` en `verificar_instalacion.py` a `"2025-10-01"`.

---

## 3. Recursos

### NASA (recursos oficiales del reto)
| Recurso | Para qué |
|---|---|
| ASF Vertex – https://search.asf.alaska.edu | Buscar y descargar NISAR |
| NISAR Data User Guide – https://nisar-docs.asf.alaska.edu | Entender productos y bandas (GCOV, SME2) |
| NASA Earthdata Search – https://search.earthdata.nasa.gov | NASADEM, SMAP, IMERG |
| Intro to SAR / Intro to Remote Sensing (Earthdata) | Entender el radar en 1 hora (todo el equipo) |
| NASA ARSET Trainings | Capacitación de NISAR, con material en español |
| NISAR StoryMaps y Applications White Papers | Argumentos para el pitch (buscar el de agricultura) |
| Tutorial SAR en Python y QGIS (Agencia Espacial Canadiense, GitHub) | Código de partida |

### NASA (adicionales)
| Recurso | Para qué |
|---|---|
| NASA POWER – https://power.larc.nasa.gov | Temperatura y lluvia promedio de todo el país |
| NASADEM | Altura y pendiente |
| SMAP | Humedad de suelo nacional (baja resolución) |

### Agencias socias (suman puntos)
| Recurso | Para qué |
|---|---|
| Sentinel-1 (ESA) | Radar con historia larga si a NISAR le faltan fechas |
| SAOCOM (CONAE, Argentina) | Radar banda L; requiere registro (opcional) |

### Ecuador
| Fuente | Qué buscar |
|---|---|
| INEC – ESPAC | Superficie, producción y rendimiento por cultivo y provincia (últimos 5 años) |
| MAG – SIPA | Precios al productor |
| Geoportal del MAG | Zonificación agroecológica / aptitud agrícola (validación) |
| INIAP | Guías técnicas de cultivos para Ecuador |
| INAMHI | Estaciones meteorológicas |
| Banco Central del Ecuador | Exportaciones por producto |
| MapBiomas Ecuador | Uso actual del suelo (validación) |
| SoilGrids (ISRIC) – https://soilgrids.org | Textura y pH del suelo (fuente externa, no NASA) |
| FAO EcoCrop | Requisitos de cada cultivo |

---

## 4. Tareas de investigación (esta noche)

**Cultivos (Mecánico 1)**
- [ ] Lista final de ~15 cultivos (≈8 Costa, ≈5 Sierra, ≈2 Amazonía)
- [ ] Completar `requisitos_cultivos.csv`: altura, temperatura, lluvia, pendiente máx., tolerancia al encharcamiento, pH

**Mercado (Mecánico 2)**
- [ ] Descargar ESPAC de los últimos años
- [ ] Precios del SIPA de esos cultivos
- [ ] Proponer la regla del indicador (ej.: "saturado" si la superficie creció más de X % y el precio bajó)

**Radar (Jorge)**
- [ ] Confirmar qué es SME2 en la NISAR Data User Guide
- [ ] Leer la parte de GCOV: HH, HV y retrodispersión
- [ ] Ver la capacitación ARSET de NISAR
- [ ] Buscar datos de época lluviosa (ver sección 2)

**Diseño**
- [ ] Logo e identidad de SmartSeeds
- [ ] Boceto de 3 pantallas: elegir terreno · resultados · ficha del cultivo
- [ ] Guion del video de 30 s (sin imágenes con derechos de autor)

**Todos**
- [ ] Datos oficiales del peso de la agricultura en empleo y PIB (INEC / BCE) para el pitch
- [ ] Si se puede: conversación corta con un agricultor (cómo decide qué sembrar). Con su permiso; sin menores de 18 años
- [ ] Definir la zona de la Sierra

---

## 5. Instalación (Windows) – probada el 13 nov

### Cuentas (cada integrante)
- [ ] Inscrito en la sede **Sangolquí** y en el equipo **Condor Mission** (Members) — **obligatorio**
- [ ] NASA Earthdata Login – https://urs.earthdata.nasa.gov
- [ ] Entrar una vez a ASF Vertex con esa cuenta
- [ ] GitHub y Streamlit Community Cloud

### Programas (en PowerShell, uno por uno)
```
winget install -e --id CondaForge.Miniforge3 --accept-source-agreements --accept-package-agreements
winget install -e --id Git.Git --accept-source-agreements --accept-package-agreements
winget install -e --id OSGeo.QGIS_LTR --accept-source-agreements --accept-package-agreements
```
(QGIS es opcional y pesa más de 1 GB.) En VS Code, instalar las extensiones **Python** y **Jupyter** de Microsoft.

### Entorno de Python (en **Miniforge Prompt**, no en PowerShell)
Copiar los archivos del proyecto a `C:\condor` y ejecutar uno por uno:
```
cd C:\condor
mamba create -n condor -c conda-forge python=3.11 -y
conda activate condor
mamba install -c conda-forge asf_search earthaccess requests h5py xarray rioxarray rasterio geopandas -y
mamba install -c conda-forge scikit-image scikit-learn openpyxl matplotlib plotly jupyterlab streamlit folium -y
pip install streamlit-folium fpdf2
python verificar_instalacion.py
```
> Usar **mamba** y por partes. Con `conda env update/create` del archivo completo, el paso
> "Solving environment" se quedó trabado más de 10 minutos.

### VS Code
1. **File → Open Folder → C:\condor**
2. Si aparece la barra azul "Restricted Mode": **Manage → Trust**
3. `Ctrl + Shift + P` → **Python: Select Interpreter** → **condor (3.11)**
   (no el "Recommended": ese no tiene las librerías)

### Cada vez que abras Miniforge Prompt
```
cd C:\condor
conda activate condor
```

### Probar Streamlit
```
streamlit hello
```
Se abre en http://localhost:8501. Con la **Network URL**, los compañeros en la misma wifi pueden verla.
Para cerrarlo: `Ctrl + C`.

---

## 6. Estructura del repositorio

```
smartseeds/
├── environment.yml
├── verificar_instalacion.py
├── README.md
├── datos/
│   ├── crudos/          # descargas (NO se suben a GitHub: son pesadas)
│   └── procesados/      # capas listas para la app (GeoTIFF/PNG pequeños, CSV)
├── tablas/
│   ├── requisitos_cultivos.csv
│   └── mercado.csv
├── notebooks/           # pruebas y análisis
├── src/
│   ├── nisar.py         # capas de humedad, encharcamiento y vegetación
│   ├── clima_relieve.py # NASA POWER y NASADEM
│   ├── aptitud.py       # puntaje de aptitud por cultivo
│   └── mercado.py       # indicador de oportunidad
└── app/
    └── app.py           # interfaz en Streamlit
```

---

## 7. Sábado: acuerdos de 9:00 a 10:00

- [ ] Zonas de demostración (Costa + Sierra), en recuadro lon/lat
- [ ] Lista final de cultivos
- [ ] Formato de la tabla por celda: `celda, lat, lon, altura, pendiente, temp, lluvia, humedad, encharcamiento, vegetacion`
- [ ] Escala de aptitud 0–100 y niveles de mercado: oportunidad alta / media / saturado

---

## 8. Entrega (domingo)

- [ ] Página del proyecto **en inglés** (resumen, descripción, datos NASA, referencias)
- [ ] Demo: video **≤ 30 s** con subtítulos en inglés, o **≤ 7 diapositivas** en inglés (si se pasan, quedan fuera de la evaluación global)
- [ ] App publicada y repositorio público en GitHub
- [ ] **Todas** las referencias citadas, incluido código abierto
- [ ] Al menos un dato o recurso de la NASA (tenemos varios)
- [ ] Uso de IA declarado: imágenes o videos generados con marca de agua; código y datos indicados en el texto
- [ ] Sin imágenes con derechos de autor sin permiso, ni de menores de 18 años
- [ ] Clic en **"Submit for Judging"** antes de las 23:59

**Criterios de evaluación (1 a 5 cada uno):** impacto · creatividad · validez · relevancia · presentación.

---

## 9. Código: estado al sábado 14 (11:00)

### Ejecutar (Miniforge Prompt, entorno `condor`)
```
cd C:\condor
conda activate condor
python tests/prueba_rapida.py        # comprueba la lógica (sin internet)
streamlit run app/app.py             # abre la app en http://localhost:8501
```

### Qué funciona ya
| Archivo | Estado |
|---|---|
| `app/app.py` | Mapa: tocas un terreno y muestra los 3 mejores cultivos con sus razones. Nivel nacional con clima real de NASA POWER. |
| `src/terreno.py` | **Terreno dibujado.** En la app se elige "✏️ Dibujar mi terreno" y se marcan las esquinas (todas las que hagan falta, para seguir curvas y linderos). Con el botón ✎ se arrastran las esquinas para corregir y se crean esquinas nuevas desde los puntos medios. Calcula el tamaño en hectáreas y cuadras y **pesa cada cuadro de datos (~250 m) según la parte que el terreno ocupa de él**, así el resultado sigue la forma dibujada. Si el terreno es grande, dice qué cultivo conviene en cada parte. Un terreno que cabe en un solo cuadro (~6 ha) usa ese cuadro: los datos no tienen más detalle. |
| `src/cobertura.py` | **Tipo de terreno según el radar.** Un modelo de agrupamiento (KMeans) entrenado con las pasadas de NISAR separa: zona construida, agua, terreno que se inunda, cultivo de ciclo corto en actividad, árboles o vegetación densa y vegetación baja. La app lo muestra, avisa si el punto es zona construida y deja lo construido fuera del análisis de un terreno dibujado. |
| `src/config.py` | Rutas, zonas de demostración y formato de la tabla por celda. **Aquí se agrega la zona de la Sierra.** |
| `src/aptitud.py` | Puntaje 0–100 por cultivo y razones en lenguaje sencillo. Incluye la regla del **riego** (ver abajo). |
| `src/mercado.py` | Regla alta / media / saturado sobre `tablas/mercado.csv`. Usa la fila de la provincia y, si no hay, la nacional. Devuelve "sin datos" si el cultivo no está. |
| `src/preparar_mercado.py` | Arma `tablas/mercado.csv` con los archivos oficiales de la ESPAC y de precios del SIPA (se ejecuta una vez, sin internet). |
| `src/recomendar.py` | Une aptitud + mercado. También adjunta a cada cultivo el **suelo que prefiere** (pH, textura, drenaje) leído de `tablas/suelo_cultivos.csv`. |
| `tablas/suelo_cultivos.csv` | Suelo preferido de 15 cultivos, copiado del catálogo del equipo (`catalogo_cultivos_v01`, 14 nov) con su fuente y página. Se **muestra** en la ficha del cultivo, pero **no entra en el puntaje**: son rangos reportados por cada manual y la app todavía no mide el suelo del terreno. |
| `src/clima_relieve.py` | NASA POWER probado. NASADEM → tabla por celda: probado. Santo Domingo ya está en `datos/procesados/celdas_santo_domingo.csv` (32.400 celdas de ~250 m). Para otra zona: `python -m src.clima_relieve NOMBRE_ZONA`. |
| `src/nisar.py` | **Probado con datos reales.** Lee en remoto solo el recorte de la zona (~15 MB por archivo en vez de 7 GB). Santo Domingo ya tiene 11 fechas GCOV y 10 fechas SME2 procesadas. |

### Riego, empates y tiempos de cultivo (14 nov)
La app hace dos preguntas sencillas al agricultor antes de recomendar.

**¿Tienes riego en tu terreno?**
- El riego solo arregla la **falta de agua** (poca lluvia o suelo que se seca rápido). No cambia la
  altura, la temperatura, la pendiente, el exceso de lluvia ni las inundaciones.
- Tampoco borra la falta: la **reduce**. Mientras más agua haya que regar, menos puntos. Así, marcar
  "sí tengo riego" no pone a todos los cultivos en 100.
- Fórmula: nota de lluvia con riego = 1 − 0,5 × (parte del agua que falta). Si la lluvia cubre el 77 % de
  lo que pide el cultivo, la nota es 0,89; si no lloviera nada, sería 0,5. El 0,5 es un valor inicial
  **sin calibrar**.
- Ejemplo real, terreno seco de Daule (770 mm de lluvia): sin riego, arroz 48 y banano 33; con riego,
  arroz 92 y banano 88. El maíz duro sigue en 100 porque no le falta agua. En Santo Domingo el riego no
  cambia nada, porque ahí la lluvia alcanza.
- La app dice cuánta agua falta ("tendrás que regar lo que falta: unos 230 mm al año").

**¿Qué buscas?** (cosechar pronto / un cultivo para muchos años)
- Muchos cultivos empatan en el mismo puntaje (en Santo Domingo, 8 sacan 100). Antes se mostraban los
  tres primeros de la tabla. Ahora los empatados se ordenan por mercado y luego por esta respuesta:
  "pronto" pone primero al que da cosecha más rápido; "muchos años" pone primero a los permanentes.
- **No cambia el puntaje**, solo el orden entre empatados. La app avisa qué otros cultivos tienen la misma
  aptitud que el tercero.
- Cada cultivo muestra cuánto tarda la primera cosecha y de qué tipo es (columnas `ciclo_meses` y `tipo`
  de `requisitos_cultivos.csv`, todavía **preliminares**). No hay datos de costos: solo se dice que un
  cultivo permanente suele pedir más inversión al inicio.

### Vista satelital, tipo de terreno, mercado y EcoCrop (14 nov, tarde)

**Fondos del mapa** (se cambian en el cuadro de la esquina superior derecha del mapa):
- *Croquis*: OpenStreetMap, con calles y nombres.
- *Foto satelital*: imágenes de alta resolución de Esri World Imagery; se ven las parcelas reales y sirve
  para dibujar el lindero. No es de la NASA: hay que citarla.
- *NASA 31 oct (óptico)*: imagen diaria del sensor VIIRS (satélite Suomi NPP) servida por NASA GIBS, del
  mismo día de la última pasada de NISAR sobre Daule. Tiene ~250 m de detalle y muestra las nubes: sirve
  para explicar por qué hace falta un radar.

**Tipo de terreno (modelo entrenado con las pasadas de NISAR):** `python -m src.cobertura entrenar`
- Cada cuadro se describe por cómo se comportó el radar en las 10 pasadas: brillo medio de HH y HV, cuánto
  cambió entre fechas, la fecha más oscura, cuántas veces tuvo agua y la diferencia HH − HV.
- KMeans (8 grupos) junta los cuadros parecidos, sin datos de campo. Se entrenó con 57.035 cuadros de las
  dos zonas. Cada grupo recibe nombre con reglas físicas del radar (umbrales en `src/cobertura.py`).
- Resultado: Santo Domingo 92 % vegetación densa, 6 % vegetación baja, 2 % zona construida. Daule 67 %
  vegetación baja, 14 % cultivo de ciclo corto en actividad, 11 % vegetación densa, 6 % terreno que se
  inunda, 2 % zona construida.
- Comprobación (solo con lugares conocidos): el centro de Santo Domingo y el de Salitre salen como zona
  construida; el terreno inundado de Daule, como terreno que se inunda.
- **Límites:** no distingue qué cultivo es; con cuadros de ~250 m solo ve las zonas más construidas (los
  pueblos con muchos árboles salen en parte como vegetación densa); no se comprobó en el campo.
- Entrenar necesita scikit-learn (entorno de desarrollo). La app publicada no: lee la columna `cobertura`.

**Mercado con datos reales, por provincia** (`tablas/mercado.csv`, 45 filas, se compara 2024 con 2025).
La tabla ya no se escribe a mano: la arma `python -m src.preparar_mercado` con dos archivos oficiales
guardados en `datos/crudos/mercado/` (no se suben a GitHub; las direcciones están al inicio de ese programa).

Filas nacionales (13 de los 15 cultivos):
| Cultivo | Superficie | Precio al productor | Resultado | Rinde (t/ha) |
|---|---|---|---|---|
| Plátano | −16,9 % | +90,5 % | Oportunidad alta | 6,81 |
| Maracuyá | −8,2 % | +14,7 % | Oportunidad alta | 10,55 |
| Palma aceitera | −4,1 % | +7,5 % | Oportunidad alta | 19,99 |
| Banano | +19,4 % | +24,6 % | Oportunidad media | 44,05 |
| Café | +44,4 % | +33,0 % | Oportunidad media | 0,24 |
| Yuca | +33,0 % | +4,9 % | Oportunidad media | 5,87 |
| Maíz duro | +9,5 % | −7,5 % | Oportunidad media | 5,09 |
| Arroz | −10,5 % | −24,4 % | Oportunidad media | 5,02 |
| Maíz suave | −29,8 % | −26,9 % | Oportunidad media | 1,37 |
| Tomate de árbol | −40,8 % | +4,9 % | Oportunidad media | 15,50 |
| Cacao | +13,3 % | −13,2 % | Mercado saturado | 0,82 |
| Piña | +51,7 % | −2,7 % | Mercado saturado | 68,18 |
| Papa | +16,7 % | −32,1 % | Mercado saturado | 14,35 |

Además hay 32 filas por provincia (16 provincias). En las zonas del proyecto: Santo Domingo (cacao, plátano,
maracuyá, yuca, piña), Guayas (cacao, banano, maíz duro, arroz), Cotopaxi (cacao, plátano, papa) y
Tungurahua (papa). Si un cultivo no tiene fila de la provincia, la app usa la nacional y lo dice.
La provincia puede cambiar el resultado: el cacao está saturado en el país y en Guayas, pero no en
Santo Domingo (−0,8 % de superficie); el maíz duro es "media" en el país y "saturado" en Guayas (+27,1 %).

- **Superficie y rendimiento:** INEC, ESPAC 2024 y 2025, por provincia, de la base histórica que publica el
  MAG-SIPA (`superficie-produccion.xlsx`). Se comprobó que sus totales nacionales de los 15 cultivos y
  varios valores por provincia son iguales a los tabulados oficiales de la ESPAC (`Tabulados_csv.zip`).
- **Precio:** MAG-SIPA, precio mensual al productor por provincia (`precios-productor-ponderado.xlsx`).
  Se compara el promedio de 2024 con el de 2025 usando solo los meses (y provincias) que tienen precio en
  los dos años. Un producto por cultivo (por ejemplo cacao CCN51 almendra seca, papa superchola).
- **No se escribe la fila** (la app dice "sin datos") si hay menos de 6 meses con precio en los dos años o
  si la provincia tiene menos de 500 ha del cultivo. Los dos umbrales los eligió el equipo.
- **Sin datos:** haba (solo 5 meses con precio, y en una provincia) y quinua (sin precios en 2024–2025).
- La app muestra además cuánto rinde el cultivo en toneladas por hectárea y quintales por cuadra, ahora
  con el dato de la provincia cuando existe. Cada fila guarda los números originales en la columna `notas`.
- **Cambio respecto a la primera versión (6 cultivos):** antes el precio comparaba solo diciembre de 2024
  con diciembre de 2025 (boletín del SIPA). Ahora compara los dos años completos, igual que la superficie.
  Por eso el cacao pasó de −43,6 % a −13,2 % (sigue saturado) y la palma de −10,4 % a +7,5 % (pasó de
  "media" a "alta": el precio subió en el promedio del año, aunque bajó al final de 2025).
- **Límites:** el precio nacional es un promedio simple entre provincias, no el ponderado oficial; la ESPAC
  es una encuesta y el dato de una provincia tiene más error que el nacional; la ESPAC no separa café
  robusta de arábigo; para el banano se usa el precio "spot"; maíz suave y haba usan solo una de sus dos
  formas (seco y tierna). Hay precios de 2026 (hasta octubre) que no se usan porque aún no hay ESPAC 2026.
- Entre cultivos empatados en aptitud va primero el de mejor mercado, y el "saturado" va al final.

**FAO EcoCrop** (`tablas/ecocrop_cultivos.csv`): rangos óptimos y absolutos de temperatura, lluvia y pH,
altitud máxima y ciclo de los 15 cultivos, copiados de la ficha oficial de cada uno
(`ecocrop.apps.fao.org`, licencia CC BY 4.0). **Todavía no se usan en el puntaje.** Una simulación mostró:
- En Santo Domingo los empates en 100 bajan de 8 a 3 (cacao, palma, piña), lo que mejora el resultado.
- Pero EcoCrop es mundial: sin un límite de altura propio del Ecuador pone haba y maíz suave con 100 en
  Daule, y baja la papa a 71 a 3.000 m y a 45 a 3.500 m. Por eso no se adoptó sin acuerdo del equipo.

### El radar a la vista en la app (14 nov)
- **Gráfico por terreno:** en las zonas detalladas, debajo de los datos del radar, hay un desplegable
  "📈 Ver lo que vio el radar en cada pasada". Muestra tres gráficos pequeños, uno por medida:
  vegetación, agua sobre el terreno y humedad del suelo, fecha por fecha. Sirve para un punto y para un
  terreno dibujado (promedia sus celdas). Ejemplo real, terreno inundado de Daule: el agua cubre el 92 %
  del terreno en junio, baja al 8 % en septiembre y vuelve al 75 % a fines de octubre.
- **Capa sobre el mapa:** encima del mapa se elige qué pintar (agua, vegetación o humedad). Cada capa usa
  un solo color, de claro (poco) a oscuro (mucho); en gris, donde el radar no tiene datos.
- **Corrección:** sobre el agua el índice de vegetación sale alto por error (HH y HV son casi ruido). Ahora
  las pasadas en que más de la mitad de la celda era agua no cuentan para la vegetación. Cambió la
  vegetación de 1.439 celdas de Daule (4 %); el resto de la tabla quedó igual.
- La app lee `nisar_ZONA.npz` y `humedad_ZONA.npz` (unos 3 MB por zona); no procesa nada en vivo.

### NISAR: cómo se procesó y qué salió (14 nov, Santo Domingo)
```
python -m src.nisar santo_domingo procesar   # GCOV: HH y HV por celda y fecha (~8 min)
python -m src.nisar santo_domingo humedad    # SME2: humedad de suelo (~4 min)
python -m src.nisar santo_domingo capas      # llena vegetacion, encharcamiento y humedad en la tabla
```
- **Datos usados:** GCOV `frequencyB` (HH y HV a 80 m), órbita 76 ascendente, 19 jun – 29 oct 2026; SME2 (humedad de suelo nivel 3, 200 m), 19 jun – 17 oct 2026.
- **Cobertura:** el radar cubre el **76 %** de las celdas. La franja oeste (longitud menor a −79,35) queda fuera de esta órbita; ahí la app muestra "sin dato". Opciones: mover el recuadro al este o sumar la órbita 112.
- **Retrodispersión:** HH mediana −6,0 dB y HV −11,4 dB: paisaje de vegetación densa.
- **Vegetación (RVI):** entre 0,83 y 0,95 en casi toda la zona. Se muestra, pero no entra en el puntaje.
- **Encharcamiento:** prácticamente 0 % en toda la zona. Son fechas de **época seca**, y a 80 m los ríos angostos no se distinguen.
- **Humedad (SME2):** media 0,26 m³/m³ (52 % de saturación). La NASA marca como "recomendado" solo el **6 %** de las celdas (vegetación densa); en el resto se muestra el valor pero no cuenta en el puntaje.
- **Limitación a declarar:** en esta zona y época, las capas NISAR todavía no cambian el orden de los cultivos. Para que el radar pese en la recomendación hacen falta fechas de época lluviosa o una zona con inundación real (por ejemplo, arroceras de Los Ríos o Guayas).
- La app acepta un enlace directo a un terreno: `http://localhost:8501/?lat=-0.33&lon=-79.12`.

### NISAR: segunda zona, Daule – Salitre – Samborondón (14 nov)
Zona arrocera de Guayas. Recuadro: lon −80.05 a −79.65, lat −2.05 a −1.65. Se procesó con los mismos
comandos, usando `daule` como nombre de zona.
- **Por qué esta zona:** se midió el agua visible (HH menor a −18 dB) en una fecha de cada candidata.
  21 de junio: Babahoyo 1,5 %, Daule 1,5 %, Vinces 0,1 %. 31 de octubre: Daule 4,0 %, Babahoyo 3,0 %.
  En la imagen del radar lo oscuro tiene forma de ríos y de parcelas, no de ruido.
- **Datos usados:** GCOV `frequencyB`, órbita 112 descendente (frames 89 y 90), **10 fechas**, 21 jun – 31 oct 2026.
- **Cobertura:** el radar cubre el **100 %** de las celdas (32.400 celdas de ~250 m).
- **Retrodispersión:** HH mediana −8,2 dB y HV −16,8 dB. Vegetación (RVI) entre 0,33 y 0,80:
  campo abierto y cultivos, no bosque denso como en Santo Domingo.
- **Encharcamiento:** el 7,2 % de las celdas tuvo agua en al menos el 5 % de las pasadas, el 3,8 % en al
  menos el 10 % y el 0,3 % en al menos el 30 %. El agua visible baja de 1,5 % (junio) a 0,1 % (septiembre)
  y sube a 4,0 % a fines de octubre.
- **Humedad (SME2):** 9 fechas, 21 jun – 19 oct 2026. Media 0,27 m³/m³ (53 % de saturación), con dato en el
  97 % de las celdas. La NASA marca como "recomendado" el dato en el **49 %** de las celdas (en Santo Domingo
  era el 6 %), así que aquí la humedad sí cuenta en el puntaje de la mitad de los terrenos.
- **Aquí NISAR sí cambia la recomendación.** Terreno inundado (`?lat=-1.9356&lon=-79.6511`, agua en el 37 %
  de las pasadas): el único cultivo que supera el mínimo es **arroz** (49/100 sin riego, 92/100 con riego).
  Terreno seco (`?lat=-1.8156&lon=-79.6733`): maíz duro 100, maracuyá 92 y yuca 92.
- **Limitaciones:** NASA POWER da 770 mm de lluvia al año para toda la zona, por eso sin riego el arroz
  pierde puntos por "llueve poco"; hay que marcar "Sí, tengo riego". El umbral de −18 dB no está calibrado:
  una superficie lisa y oscura puede ser agua, un arrozal inundado o suelo liso recién preparado.

### Pendientes por rol
- **Cultivos:** `tablas/requisitos_cultivos.csv` tiene valores **preliminares** (aproximados). Verificar cada uno con FAO EcoCrop / INIAP y quitar la palabra PRELIMINAR de la columna `notas`.
  El catálogo del equipo trae el **suelo** (pH, textura, drenaje) pero no la altura, la temperatura ni la lluvia que usa el puntaje. Para poder recomendar los cultivos nuevos del catálogo (fréjol, arveja, lenteja, chocho, trigo, cebada, amaranto, tomate, soya) falta sacar esos tres rangos de las mismas fuentes y agregarlos a `requisitos_cultivos.csv`. Rosa, clavel, aguacate, mora y uvilla todavía no tienen ningún dato.
- **Mercado:** `tablas/mercado.csv` ya tiene 13 cultivos a nivel nacional y 32 filas por provincia. Faltan haba y quinua (el SIPA no tiene precios suficientes) y los cultivos nuevos del catálogo.
- **Radar:** la segunda zona ya está (Daule, ver arriba). Falta calibrar el umbral de agua y buscar fechas de época lluviosa. Cada archivo GCOV pesa ~7 GB: no descargar, usar la lectura remota.
- **Programación:** textos en inglés para la entrega y publicar la app (cuando estén unidas la Costa y la Sierra). El gráfico del radar y la capa sobre el mapa ya están.

### Uso de IA (declarar en la página del proyecto)
La estructura y el código inicial se escribieron con ayuda de un asistente de IA (Claude, de Anthropic)
y fueron revisados por el equipo.

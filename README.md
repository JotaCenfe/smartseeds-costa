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
| `src/config.py` | Rutas, zonas de demostración y formato de la tabla por celda. **Aquí se agrega la zona de la Sierra.** |
| `src/aptitud.py` | Puntaje 0–100 por cultivo y razones en lenguaje sencillo. |
| `src/mercado.py` | Regla alta / media / saturado. Devuelve "sin datos" hasta llenar `tablas/mercado.csv`. |
| `src/recomendar.py` | Une aptitud + mercado. |
| `src/clima_relieve.py` | NASA POWER probado. NASADEM → tabla por celda: probado. Santo Domingo ya está en `datos/procesados/celdas_santo_domingo.csv` (32.400 celdas de ~250 m). Para otra zona: `python -m src.clima_relieve NOMBRE_ZONA`. |
| `src/nisar.py` | **Probado con datos reales.** Lee en remoto solo el recorte de la zona (~15 MB por archivo en vez de 7 GB). Santo Domingo ya tiene 11 fechas GCOV y 10 fechas SME2 procesadas. |

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

### Pendientes por rol
- **Cultivos:** `tablas/requisitos_cultivos.csv` tiene valores **preliminares** (aproximados). Verificar cada uno con FAO EcoCrop / INIAP y quitar la palabra PRELIMINAR de la columna `notas`.
- **Mercado:** llenar `tablas/mercado.csv` (una fila por cultivo y provincia, o `nacional`): `var_superficie_pct` (ESPAC) y `var_precio_pct` (SIPA).
- **Radar:** decidir la segunda zona (una con inundación real haría brillar a NISAR) y buscar fechas de época lluviosa. Cada archivo GCOV pesa ~7 GB: no descargar, usar la lectura remota.
- **Programación:** gráfico de la serie del radar por terreno, capa NISAR sobre el mapa, textos en inglés para la entrega, subir a GitHub.

### Uso de IA (declarar en la página del proyecto)
La estructura y el código inicial se escribieron con ayuda de un asistente de IA (Claude, de Anthropic)
y fueron revisados por el equipo.

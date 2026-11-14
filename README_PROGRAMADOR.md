# SmartSeeds · Guía del programador
### Equipo Condor Mission · NASA Space Apps 2026 · Sede Sangolquí

Guía práctica para preparar la computadora y trabajar en el código de SmartSeeds.
Probada en Windows el 13 de noviembre de 2026.

> El desarrollo del proyecto empieza el **sábado 14 a las 9:00**. Los ejemplos de esta guía son
> de práctica y para aprender las herramientas; el código de SmartSeeds se escribe desde el sábado.

---

## 1. Instalación (una sola vez)

### 1.1 Programas (en PowerShell)
Pega cada línea por separado y acepta los permisos de administrador:
```
winget install -e --id CondaForge.Miniforge3 --accept-source-agreements --accept-package-agreements
winget install -e --id Git.Git --accept-source-agreements --accept-package-agreements
winget install -e --id OSGeo.QGIS_LTR --accept-source-agreements --accept-package-agreements
```
- QGIS es opcional (más de 1 GB), pero ayuda a ver los mapas de radar sin programar.
- Si `winget` no se reconoce: Microsoft Store → actualizar **App Installer**.
- Cuidado al pegar: un carácter extra al inicio (por ejemplo `}winget`) da error de "token inesperado".

### 1.2 VS Code
- Extensiones (`Ctrl + Shift + X`): **Python** y **Jupyter**, ambas de Microsoft.

### 1.3 Entorno de Python (en **Miniforge Prompt**, no en PowerShell)
Copia los archivos del proyecto a `C:\condor` y ejecuta uno por uno, esperando a que cada uno termine:
```
cd C:\condor
mamba create -n condor -c conda-forge python=3.11 -y
conda activate condor
mamba install -c conda-forge asf_search earthaccess requests h5py xarray rioxarray rasterio geopandas -y
mamba install -c conda-forge scikit-image scikit-learn openpyxl matplotlib plotly jupyterlab streamlit folium -y
pip install streamlit-folium fpdf2
```
> **Importante:** usa **mamba** y por partes. Con `conda env create/update -f environment.yml`
> el paso "Solving environment" se quedó trabado más de 10 minutos.

### 1.4 Verificar
```
python verificar_instalacion.py
```
- Sección 1: todas las librerías en **OK**.
- Sección 2: escribe `s` e inicia sesión en Earthdata (queda guardado).
- Secciones 3 a 5: disponibilidad de NISAR, NASA POWER y SMAP.

Verificación rápida solo de librerías:
```
python -c "import numpy, pandas, h5py, xarray, rioxarray, rasterio, geopandas, skimage, sklearn, openpyxl, matplotlib, plotly, asf_search, earthaccess, streamlit, folium, streamlit_folium, fpdf; print('TODAS LAS LIBRERIAS OK')"
```
(El aviso "missing ScriptRunContext" es de Streamlit y se ignora.)

### 1.5 Conectar VS Code al entorno
1. **File → Open Folder → C:\condor**
2. Si aparece la barra azul **Restricted Mode**: **Manage → Trust** (si no, no deja elegir Python).
3. `Ctrl + Shift + P` → **Python: Select Interpreter** → **condor (3.11.x)**.
   ⚠️ No elijas el que dice "Recommended" (Python 3.13): no tiene las librerías.
4. Abajo a la derecha debe decir **3.11.x ('condor')**.

### 1.6 Cuentas
- NASA Earthdata Login – https://urs.earthdata.nasa.gov (y entrar una vez a https://search.asf.alaska.edu)
- GitHub – https://github.com
- Streamlit Community Cloud – https://streamlit.io/cloud (para publicar la app)

---

## 2. Rutina de cada día

Cada vez que abras **Miniforge Prompt**:
```
cd C:\condor
conda activate condor
```
Debe decir `(condor) C:\condor>` al inicio.

| Para… | Comando |
|---|---|
| Ejecutar un script | `python archivo.py` |
| Abrir notebooks | `jupyter lab` |
| Correr la app | `streamlit run app/app.py` |
| Detener la app | `Ctrl + C` (o cerrar la ventana) |
| Ver la app | http://localhost:8501 |
| Que el equipo vea la app | La **Network URL** que muestra Streamlit (misma wifi) |

---

## 3. Git y GitHub (trabajo en equipo)

### Configuración (una vez)
```
git config --global user.name "Tu Nombre"
git config --global user.email "tu_correo_de_github"
```

### Obtener el repositorio
```
cd C:\
git clone https://github.com/USUARIO/smartseeds.git
cd smartseeds
```

### Ciclo de trabajo
```
git pull                         # SIEMPRE antes de empezar
git add .
git commit -m "Describe el cambio"
git push
```
Reglas del equipo:
- Haz `git pull` antes de trabajar y antes de `git push`.
- Cada uno trabaja en sus propios archivos (ver estructura) para evitar conflictos.
- **No subir datos crudos** (pesan GB). Solo capas procesadas pequeñas.

### `.gitignore` (crear en la raíz del repositorio)
```
datos/crudos/
*.h5
*.hdf5
*.nc
__pycache__/
.ipynb_checkpoints/
.netrc
_netrc
.env
```

---

## 4. Estructura del repositorio

```
smartseeds/
├── README.md
├── README_PROGRAMADOR.md
├── environment.yml
├── requirements.txt         # solo para publicar la app en Streamlit Cloud
├── verificar_instalacion.py
├── datos/
│   ├── crudos/              # descargas (NO se suben)
│   └── procesados/          # capas listas para la app (GeoTIFF/PNG pequeños, CSV)
├── tablas/
│   ├── requisitos_cultivos.csv
│   └── mercado.csv
├── notebooks/               # pruebas y exploración
├── src/
│   ├── nisar.py             # capas de humedad, encharcamiento y vegetación
│   ├── clima_relieve.py     # NASA POWER y NASADEM
│   ├── aptitud.py           # puntaje de aptitud por cultivo
│   └── mercado.py           # indicador de oportunidad
└── app/
    └── app.py               # interfaz en Streamlit
```

### Contratos entre módulos (acordar el sábado a las 9:00)
| Pieza | Formato |
|---|---|
| Zona | `(lon_min, lat_min, lon_max, lat_max)` en grados |
| Tabla por celda | `celda, lat, lon, altura, pendiente, temp, lluvia, humedad, encharcamiento, vegetacion` |
| Aptitud | `aptitud(fila_celda, fila_cultivo) -> 0..100` |
| Mercado | `mercado(cultivo, provincia) -> "alta" / "media" / "saturado"` |
| Recomendación | lista de 3 cultivos con puntaje y razones en texto |

---

## 5. Datos: cómo se accede (ejemplos de práctica)

### 5.1 Datos ya verificados (Santo Domingo de los Tsáchilas)
Recuadro: lon −79.40 a −79.00, lat −0.45 a −0.05
- **NISAR GCOV:** 11 fechas (path 76, ascendente), 19 jun – 29 oct 2026, cada 12 días.
  También path 112 descendente (10 fechas) y path 4 ascendente (10 fechas).
  **No mezclar geometrías** en una misma serie.
- **NISAR SME2:** 52 productos (probablemente humedad de suelo nivel 3; confirmar en la User Guide).
- **NASA POWER:** 24,3 °C y ~1.560 mm/año (celda de ~50 km; comparar con INAMHI).
- **SMAP:** 36 archivos en octubre.
- Las fechas NISAR son de **época seca**. Para época lluviosa, probar `INICIO = "2025-10-01"` en el script de verificación.

### 5.2 Buscar y descargar NISAR (asf_search)
```python
import getpass
import asf_search as asf

zona = "POLYGON((-79.40 -0.45, -79.00 -0.45, -79.00 -0.05, -79.40 -0.05, -79.40 -0.45))"
res = asf.search(dataset="NISAR", intersectsWith=zona,
                 start="2026-06-17", end="2026-11-13")

# Quedarse con GCOV de UNA geometría (misma órbita)
gcov = [r for r in res
        if "GCOV" in str(r.properties.get("processingLevel", "")).upper()
        and r.properties.get("pathNumber") == 76
        and r.properties.get("flightDirection") == "ASCENDING"]
for r in gcov:
    p = r.properties
    print(p["startTime"][:10], p.get("fileName"), round((p.get("bytes") or 0) / 1e9, 2), "GB")

# Descargar (pesan GB: empieza con UNO para probar)
sesion = asf.ASFSession().auth_with_creds(input("Usuario Earthdata: "), getpass.getpass("Clave: "))
gcov[0].download(path="datos/crudos", session=sesion)
```

### 5.3 Explorar un archivo GCOV (HDF5)
```python
import h5py
ruta = "datos/crudos/NOMBRE_DEL_ARCHIVO.h5"
with h5py.File(ruta, "r") as f:
    f.visit(print)          # lista todos los grupos y datasets del archivo
```
- Busca las bandas de covarianza (ruta típica: `/science/LSAR/GCOV/grids/frequencyA/HHHH` y `HVHV`).
  **Confirma la ruta real** con `f.visit(print)` y la NISAR Data User Guide.
- Los valores vienen en potencia lineal. Para trabajar en decibeles:
  ```python
  import numpy as np
  hv_db = 10 * np.log10(np.clip(hv, 1e-6, None))
  ```
- Ideas de lectura de las capas:
  - **Vegetación:** HV sube con más biomasa (serie en el tiempo → crecimiento, cosecha, tala).
  - **Encharcamiento:** agua abierta = señal muy baja (oscuro); bosque inundado = muy alta.
  - **Humedad:** en suelo descubierto, HH sube cuando el suelo está más húmedo.
- Reduce el ruido (speckle) antes de analizar, por ejemplo con un filtro de mediana:
  ```python
  from scipy.ndimage import median_filter
  hv_filtrado = median_filter(hv_db, size=5)
  ```

### 5.4 Clima con NASA POWER (sin registro)
```python
import requests
url = "https://power.larc.nasa.gov/api/temporal/climatology/point"
params = {"parameters": "T2M,PRECTOTCORR", "community": "AG",
          "longitude": -79.2, "latitude": -0.25, "format": "JSON"}
d = requests.get(url, params=params, timeout=60).json()["properties"]["parameter"]
temp_anual = d["T2M"]["ANN"]                    # °C
lluvia_anual = d["PRECTOTCORR"]["ANN"] * 365    # mm/año
```

### 5.5 Relieve con NASADEM (earthaccess)
```python
import earthaccess
earthaccess.login()   # usa la sesión guardada
gr = earthaccess.search_data(short_name="NASADEM_HGT",
                             bounding_box=(-79.40, -0.45, -79.00, -0.05))
archivos = earthaccess.download(gr, "datos/crudos/nasadem")
```
Pendiente aproximada a partir de la altura (celdas de ~30 m):
```python
import numpy as np
dz_dy, dz_dx = np.gradient(altura, 30, 30)
pendiente_grados = np.degrees(np.arctan(np.hypot(dz_dx, dz_dy)))
```

### 5.6 Humedad de suelo SMAP (respaldo)
```python
gr = earthaccess.search_data(short_name="SPL3SMP_E",
                             bounding_box=(-79.40, -0.45, -79.00, -0.05),
                             temporal=("2026-10-01", "2026-10-31"))
```

### 5.7 Recortar y guardar capas pequeñas para la app
```python
import rioxarray
capa = rioxarray.open_rasterio("datos/crudos/capa.tif", masked=True)
recorte = capa.rio.clip_box(minx=-79.40, miny=-0.45, maxx=-79.00, maxy=-0.05)
recorte.rio.to_raster("datos/procesados/capa_zona.tif")
```

### 5.8 Tablas de Excel (ESPAC, precios)
```python
import pandas as pd
espac = pd.read_excel("tablas/espac.xlsx", sheet_name=0)   # revisar el nombre de la hoja
print(espac.head())
```

---

## 6. Streamlit: lo básico para la interfaz

Cada línea de Python pone un elemento en pantalla. No hace falta HTML ni JavaScript.
Cuando guardas el archivo, la app se actualiza sola en el navegador.

### Ejemplo de práctica (guárdalo como `practica.py` y ejecuta `streamlit run practica.py`)
```python
import streamlit as st
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Práctica", layout="wide")
st.title("Mi primera app")

col_mapa, col_datos = st.columns([2, 1])

with col_mapa:
    mapa = folium.Map(location=[-0.25, -79.2], zoom_start=11)
    salida = st_folium(mapa, height=450, width=None)

with col_datos:
    clic = salida.get("last_clicked") if salida else None
    if clic:
        st.success(f"Tocaste: {clic['lat']:.4f}, {clic['lng']:.4f}")
    else:
        st.info("Toca un punto en el mapa")
    opcion = st.selectbox("Elige una opción", ["A", "B", "C"])
    valor = st.slider("Un valor", 0, 100, 50)
    st.metric("Resultado", f"{valor} / 100")
```

### Componentes que más vamos a usar
| Componente | Para qué |
|---|---|
| `st.title`, `st.header`, `st.markdown` | Textos y títulos |
| `st.columns` | Dividir la pantalla en columnas |
| `st.sidebar` | Menú lateral |
| `st.selectbox`, `st.slider`, `st.button` | Controles |
| `st.metric` | Números destacados (puntaje de aptitud) |
| `st.dataframe` | Tablas |
| `st.plotly_chart` | Gráficos interactivos (series del radar, mercado) |
| `st_folium` | Mapa interactivo donde el usuario toca su terreno |
| `st.tabs` | Pestañas (por ejemplo: Terreno · Cultivos · Mercado) |
| `@st.cache_data` | Guardar resultados para que la app no recalcule todo |

Documentación: https://docs.streamlit.io · Galería de ejemplos: `streamlit hello`

### Regla de oro para que la app sea rápida
**Todo lo pesado se calcula antes** (notebooks o scripts en `src/`) y se guarda en `datos/procesados/`.
La app **solo lee** esos archivos pequeños; nunca descarga ni procesa NISAR en vivo.

---

## 7. Publicar la app (domingo)

1. Subir el repositorio a GitHub (público).
2. Crear `requirements.txt` en la raíz **solo con lo que usa la app**:
   ```
   streamlit
   folium
   streamlit-folium
   pandas
   numpy
   plotly
   rasterio
   ```
3. En https://streamlit.io/cloud → **New app** → elegir el repositorio y `app/app.py`.
4. Probar el enlace en una ventana privada del navegador (los jueces deben abrirlo sin login).
5. Recomendado por la guía de envío: pedir la clasificación del sitio en FortiGuard para evitar bloqueos.

> Streamlit Cloud tiene memoria limitada: la app debe leer solo capas procesadas y pequeñas.

---

## 8. Problemas comunes

| Problema | Solución |
|---|---|
| "Solving environment" no avanza | Cerrar la ventana (o Administrador de tareas) y usar `mamba` por partes |
| `Ctrl + C` no responde | Cerrar la ventana con la X o desde el Administrador de tareas |
| `conda` no se reconoce | Usar **Miniforge Prompt**, no PowerShell ni CMD |
| Dice `(base)` en vez de `(condor)` | `conda activate condor` |
| VS Code no deja elegir Python | Barra azul "Restricted Mode" → **Manage → Trust** |
| VS Code usa otro Python | `Ctrl + Shift + P` → Select Interpreter → **condor** |
| `ModuleNotFoundError` | `mamba install -c conda-forge NOMBRE -y` (o `pip install NOMBRE`) |
| `streamlit` no se reconoce | Activar el entorno: `conda activate condor` |
| Puerto 8501 ocupado | `streamlit run app/app.py --server.port 8502` |
| Error 401 al descargar | Entrar una vez a ASF Vertex con la cuenta Earthdata y repetir |
| Aviso "FutureWarning" o "ScriptRunContext" | Es inofensivo, se ignora |

---

## 9. Recordatorios del concurso

- Todo el equipo inscrito en la sede **Sangolquí** y en el equipo **Condor Mission**.
- Código abierto y repositorio público.
- **Citar todas las referencias**, incluido código abierto y ejemplos usados.
- **Declarar el uso de IA**: código y datos indicados en el texto; imágenes o videos generados con marca de agua.
- Usar al menos un dato de la NASA (tenemos NISAR, NASA POWER, NASADEM y SMAP).

Recursos clave:
- NISAR Data User Guide – https://nisar-docs.asf.alaska.edu
- ASF Vertex – https://search.asf.alaska.edu
- Documentación de asf_search – https://docs.asf.alaska.edu/asf_search/basics/
- NASA POWER – https://power.larc.nasa.gov
- Streamlit – https://docs.streamlit.io

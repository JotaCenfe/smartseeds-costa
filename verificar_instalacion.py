"""
Verificación del entorno y de los datos - Condor Mission (NASA Space Apps 2026)
Enfoque agrícola: recomendación de cultivos con NISAR.

Uso (con el entorno activado):
    conda activate condor
    python verificar_instalacion.py

Revisa:
  1. Que todas las librerías funcionen.
  2. (Opcional) Inicia sesión en NASA Earthdata y guarda las credenciales.
  3. Qué productos NISAR hay sobre la zona de demostración y en qué fechas
     (para las capas de humedad, encharcamiento y vegetación hace falta una
     SERIE de pasadas con la misma geometría).
  4. Que la API de clima NASA POWER responda para la zona.
  5. Que haya datos de humedad de suelo SMAP (respaldo si NISAR no basta).

Solo consulta disponibilidad: no descarga ni procesa datos del proyecto.
"""
import importlib
import sys
from collections import defaultdict

# ===========================================================================
# CAMBIEN AQUÍ LA ZONA DE DEMOSTRACIÓN (recuadro en grados: lon/lat)
# Por defecto: alrededores de Santo Domingo de los Tsáchilas (~45 x 45 km).
# ===========================================================================
LON_MIN, LAT_MIN, LON_MAX, LAT_MAX = -79.40, -0.45, -79.00, -0.05
INICIO, FIN = "2026-06-17", "2026-11-13"   # productos NISAR provisionales

ZONA_WKT = (f"POLYGON(({LON_MIN} {LAT_MIN}, {LON_MAX} {LAT_MIN}, {LON_MAX} {LAT_MAX}, "
            f"{LON_MIN} {LAT_MAX}, {LON_MIN} {LAT_MIN}))")
LON_C, LAT_C = (LON_MIN + LON_MAX) / 2, (LAT_MIN + LAT_MAX) / 2

# ---------------------------------------------------------------------------
# 1. Librerías
# ---------------------------------------------------------------------------
PAQUETES = [
    ("numpy", "numpy"), ("pandas", "pandas"), ("scipy", "scipy"),
    ("h5py", "h5py"), ("xarray", "xarray"), ("rioxarray", "rioxarray"),
    ("rasterio", "rasterio"), ("geopandas", "geopandas"), ("shapely", "shapely"),
    ("pyproj", "pyproj"), ("scikit-image", "skimage"), ("scikit-learn", "sklearn"),
    ("openpyxl", "openpyxl"), ("matplotlib", "matplotlib"), ("plotly", "plotly"),
    ("asf_search", "asf_search"), ("earthaccess", "earthaccess"),
    ("requests", "requests"), ("streamlit", "streamlit"), ("folium", "folium"),
    ("streamlit-folium", "streamlit_folium"), ("fpdf2", "fpdf"),
]

print(f"Python {sys.version.split()[0]}\n")
print("1) Librerías")
fallos = []
for nombre, modulo in PAQUETES:
    try:
        m = importlib.import_module(modulo)
        print(f"   OK    {nombre:18s} {getattr(m, '__version__', '')}")
    except Exception as e:  # noqa: BLE001
        print(f"   FALLA {nombre:18s} -> {e}")
        fallos.append(nombre)
print("\n   Todas funcionan." if not fallos else
      f"\n   Fallan: {', '.join(fallos)}\n   Ejecuta: conda env update -f environment.yml --prune")

# ---------------------------------------------------------------------------
# 2. Login Earthdata (se guarda en el archivo .netrc)
# ---------------------------------------------------------------------------
print("\n2) NASA Earthdata")
if input("   ¿Iniciar sesión en Earthdata ahora? (s/n): ").strip().lower() == "s":
    try:
        import earthaccess
        ok = earthaccess.login(strategy="interactive", persist=True)
        print("   Sesión iniciada y guardada." if ok else "   No se pudo iniciar sesión.")
    except Exception as e:  # noqa: BLE001
        print(f"   Error: {e}")
else:
    print("   Omitido.")

# ---------------------------------------------------------------------------
# 3. Productos NISAR sobre la zona
# ---------------------------------------------------------------------------
print(f"\n3) NISAR sobre la zona ({LAT_MIN}, {LON_MIN}) a ({LAT_MAX}, {LON_MAX})")
try:
    import asf_search as asf
    res = asf.search(dataset="NISAR", intersectsWith=ZONA_WKT, start=INICIO, end=FIN)
    print(f"   Productos encontrados (todos los tipos): {len(res)}")

    por_tipo = defaultdict(int)
    gcov = defaultdict(list)   # (path, frame, dirección) -> fechas
    for r in res:
        p = r.properties
        tipo = str(p.get("processingLevel", "") or "?")
        por_tipo[tipo] += 1
        archivo = str(p.get("fileName", "") or p.get("fileID", ""))
        if "GCOV" in tipo.upper() or "GCOV" in archivo.upper():
            clave = (p.get("pathNumber"), p.get("frameNumber"), p.get("flightDirection"))
            gcov[clave].append(str(p.get("startTime", ""))[:10])

    print("   Por tipo de producto:")
    for t, n in sorted(por_tipo.items()):
        print(f"     {t:12s} {n}")
    print("   (Si aparece un producto de humedad de suelo de nivel 3, anótenlo.)")

    if gcov:
        print("\n   Series GCOV por geometría (misma órbita = comparables):")
        mejor = max(gcov.items(), key=lambda kv: len(set(kv[1])))
        for (path, frame, d), fechas in sorted(gcov.items(), key=lambda kv: -len(set(kv[1]))):
            f = sorted(set(fechas))
            print(f"     path {path}, frame {frame}, {d}: {len(f)} fechas -> {', '.join(f)}")
        n = len(set(mejor[1]))
        if n >= 4:
            print(f"\n   BIEN: la mejor serie tiene {n} fechas. Alcanza para las capas de NISAR.")
        elif n >= 2:
            print(f"\n   JUSTO: la mejor serie tiene {n} fechas. Sirve, pero con poca historia.")
        else:
            print("\n   POCO: solo una fecha por geometría. Consideren ampliar la zona o cambiarla.")
    else:
        print("\n   No hay productos GCOV en esa zona y fechas. Revisen en search.asf.alaska.edu.")
except Exception as e:  # noqa: BLE001
    print(f"   No se pudo consultar ASF: {e}")

# ---------------------------------------------------------------------------
# 4. NASA POWER (clima promedio de la zona, sin registro)
# ---------------------------------------------------------------------------
print("\n4) NASA POWER (clima promedio en el centro de la zona)")
try:
    import requests
    url = "https://power.larc.nasa.gov/api/temporal/climatology/point"
    params = {"parameters": "T2M,PRECTOTCORR", "community": "AG",
              "longitude": round(LON_C, 3), "latitude": round(LAT_C, 3), "format": "JSON"}
    r = requests.get(url, params=params, timeout=60)
    r.raise_for_status()
    datos = r.json()["properties"]["parameter"]
    t_anual = datos["T2M"].get("ANN")
    p_dia = datos["PRECTOTCORR"].get("ANN")
    print(f"   OK. Temperatura media anual: {t_anual} °C")
    if p_dia is not None:
        print(f"       Lluvia media: {p_dia} mm/día (~{round(p_dia * 365)} mm/año)")
except Exception as e:  # noqa: BLE001
    print(f"   No respondió NASA POWER: {e}")

# ---------------------------------------------------------------------------
# 5. SMAP (humedad de suelo, respaldo de baja resolución)
# ---------------------------------------------------------------------------
print("\n5) SMAP humedad de suelo (respaldo)")
try:
    import earthaccess
    gr = earthaccess.search_data(short_name="SPL3SMP_E",
                                 bounding_box=(LON_MIN, LAT_MIN, LON_MAX, LAT_MAX),
                                 temporal=("2026-10-01", "2026-10-31"), count=50)
    print(f"   Archivos SMAP (octubre 2026) sobre la zona: {len(gr)}")
except Exception as e:  # noqa: BLE001
    print(f"   No se pudo consultar SMAP: {e}")

print("\nListo. Copia el resultado de las secciones 3 a 5 para revisarlo.")

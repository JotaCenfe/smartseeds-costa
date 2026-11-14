"""
Clima (NASA POWER) y relieve (NASADEM).

Dos usos:
  1. La app llama a `clima_power(lat, lon)` en vivo: es liviano y no pide registro.
  2. Antes de la demo se ejecuta UNA vez por zona:
         python -m src.clima_relieve santo_domingo
     Descarga NASADEM (pide la sesión de Earthdata ya guardada), calcula altura y
     pendiente y guarda `datos/procesados/celdas_<zona>.csv` con el formato acordado.
     Las columnas de NISAR (humedad, encharcamiento, vegetacion) quedan vacías
     hasta que `src/nisar.py` las llene.
"""
from __future__ import annotations

import math
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from .config import (COLUMNAS_CELDA, DATOS_CRUDOS, DATOS_PROCESADOS, PASO_CELDA_SEG,
                     ZONAS)

URL_POWER = "https://power.larc.nasa.gov/api/temporal/climatology/point"
MESES = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
DIAS_MES = [31, 28.25, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
GRADIENTE_C_POR_M = 0.0065   # la temperatura baja ~6,5 °C por cada 1000 m de altura


# ---------------------------------------------------------------------------
# Clima: NASA POWER
# ---------------------------------------------------------------------------
def clima_power(lat: float, lon: float) -> dict:
    """Clima promedio de varios años en un punto (NASA POWER, comunidad AG).

    Devuelve:
        temp            °C, media anual
        lluvia          mm por año
        altura_power    m, altura PROMEDIO de la celda de POWER (~50 km): es aproximada
        temp_mensual    lista de 12 valores (°C)
        lluvia_mensual  lista de 12 valores (mm por mes)
    """
    params = {"parameters": "T2M,PRECTOTCORR", "community": "AG",
              "longitude": round(lon, 3), "latitude": round(lat, 3), "format": "JSON"}
    r = requests.get(URL_POWER, params=params, timeout=60)
    r.raise_for_status()
    datos = r.json()
    par = datos["properties"]["parameter"]

    def limpio(v):
        return None if v is None or v <= -900 else float(v)   # -999 = sin dato

    temp = limpio(par["T2M"].get("ANN"))
    lluvia_dia = limpio(par["PRECTOTCORR"].get("ANN"))
    coords = datos.get("geometry", {}).get("coordinates", [])
    return {
        "temp": temp,
        "lluvia": None if lluvia_dia is None else lluvia_dia * 365,
        "altura_power": float(coords[2]) if len(coords) > 2 else None,
        "temp_mensual": [limpio(par["T2M"].get(m)) for m in MESES],
        "lluvia_mensual": [None if limpio(par["PRECTOTCORR"].get(m)) is None
                           else limpio(par["PRECTOTCORR"].get(m)) * d
                           for m, d in zip(MESES, DIAS_MES)],
    }


def corregir_temp_por_altura(temp, altura_power, altura_real):
    """Ajusta la temperatura de POWER a la altura real del terreno.

    POWER da un promedio de ~50 km. En la Sierra un terreno puede estar mucho más
    alto o más bajo que ese promedio, así que se corrige con el gradiente térmico.
    Acepta números o arreglos de numpy.
    """
    return temp - GRADIENTE_C_POR_M * (altura_real - altura_power)


# ---------------------------------------------------------------------------
# Relieve: NASADEM
# ---------------------------------------------------------------------------
def nombre_tile(lat_sur: int, lon_oeste: int) -> str:
    """Nombre del tile NASADEM cuya esquina suroeste es (lat_sur, lon_oeste). Ej.: s01w080"""
    ns = "n" if lat_sur >= 0 else "s"
    ew = "e" if lon_oeste >= 0 else "w"
    return f"{ns}{abs(lat_sur):02d}{ew}{abs(lon_oeste):03d}"


def descargar_nasadem(recuadro) -> list[Path]:
    """Descarga los tiles NASADEM_HGT que cubren el recuadro (usa la sesión Earthdata guardada)."""
    import earthaccess
    earthaccess.login()
    destino = DATOS_CRUDOS / "nasadem"
    destino.mkdir(parents=True, exist_ok=True)
    resultados = earthaccess.search_data(short_name="NASADEM_HGT", bounding_box=tuple(recuadro))
    return [Path(a) for a in earthaccess.download(resultados, str(destino))]


def leer_hgt(ruta: Path) -> np.ndarray:
    """Lee un tile NASADEM (.zip o .hgt): matriz 3601 x 3601 de alturas en metros.

    La fila 0 es el borde NORTE del tile; cada píxel mide 1 segundo de arco (~30 m).
    """
    ruta = Path(ruta)
    if ruta.suffix.lower() == ".zip":
        with zipfile.ZipFile(ruta) as z:
            interno = next(n for n in z.namelist() if n.lower().endswith(".hgt"))
            crudo = z.read(interno)
    else:
        crudo = ruta.read_bytes()
    altura = np.frombuffer(crudo, dtype=">i2").astype("float32").reshape(3601, 3601)
    altura[altura <= -32000] = np.nan   # huecos sin dato
    return altura


def pendiente_grados(altura: np.ndarray, lat: float, paso_seg: float = 1.0) -> np.ndarray:
    """Pendiente en grados a partir de una matriz de alturas (fila 0 = norte)."""
    metros_lat = 30.87 * paso_seg                       # 1" de latitud ≈ 30,87 m
    metros_lon = metros_lat * math.cos(math.radians(lat))
    dz_dy, dz_dx = np.gradient(altura, metros_lat, metros_lon)
    return np.degrees(np.arctan(np.hypot(dz_dx, dz_dy)))


def _mosaico(recuadro, carpeta: Path):
    """Une los tiles que cubren el recuadro. Devuelve (matriz, lat_norte, lon_oeste)."""
    lon_min, lat_min, lon_max, lat_max = recuadro
    lat0, lat1 = math.floor(lat_min), math.floor(lat_max - 1e-9)
    lon0, lon1 = math.floor(lon_min), math.floor(lon_max - 1e-9)
    filas, cols = (lat1 - lat0 + 1) * 3600 + 1, (lon1 - lon0 + 1) * 3600 + 1
    mosaico = np.full((filas, cols), np.nan, dtype="float32")
    encontrados = 0
    for lat_sur in range(lat0, lat1 + 1):
        for lon_oeste in range(lon0, lon1 + 1):
            tile = nombre_tile(lat_sur, lon_oeste)
            candidatos = [p for p in carpeta.glob("*") if tile in p.name.lower()
                          and p.suffix.lower() in (".zip", ".hgt")]
            if not candidatos:
                continue   # sin tile: mar o no descargado
            f = (lat1 - lat_sur) * 3600
            c = (lon_oeste - lon0) * 3600
            mosaico[f:f + 3601, c:c + 3601] = leer_hgt(candidatos[0])
            encontrados += 1
    if encontrados == 0:
        raise FileNotFoundError(
            f"No hay tiles NASADEM en {carpeta}. Ejecuta primero la descarga "
            "(python -m src.clima_relieve NOMBRE_ZONA).")
    return mosaico, lat1 + 1, lon0


def construir_tabla_celdas(clave_zona: str, descargar: bool = True) -> pd.DataFrame:
    """Crea la tabla por celda de una zona y la guarda en datos/procesados/."""
    zona = ZONAS[clave_zona]
    recuadro = zona["recuadro"]
    lon_min, lat_min, lon_max, lat_max = recuadro
    carpeta = DATOS_CRUDOS / "nasadem"
    if descargar:
        descargar_nasadem(recuadro)

    mosaico, lat_norte, lon_oeste = _mosaico(recuadro, carpeta)

    # Recorte al recuadro (índices en segundos de arco desde la esquina noroeste)
    f0 = round((lat_norte - lat_max) * 3600)
    c0 = round((lon_min - lon_oeste) * 3600)
    n_f = (round((lat_max - lat_min) * 3600) // PASO_CELDA_SEG) * PASO_CELDA_SEG
    n_c = (round((lon_max - lon_min) * 3600) // PASO_CELDA_SEG) * PASO_CELDA_SEG
    altura = mosaico[f0:f0 + n_f, c0:c0 + n_c]
    pendiente = pendiente_grados(altura, (lat_min + lat_max) / 2)

    # Promedio por bloques de PASO x PASO píxeles
    def bloques(m):
        p = PASO_CELDA_SEG
        return np.nanmean(m.reshape(n_f // p, p, n_c // p, p), axis=(1, 3))

    alt_c, pen_c = bloques(altura), bloques(pendiente)
    paso = PASO_CELDA_SEG / 3600
    lats = lat_max - (np.arange(alt_c.shape[0]) + 0.5) * paso
    lons = lon_min + (np.arange(alt_c.shape[1]) + 0.5) * paso
    lon_m, lat_m = np.meshgrid(lons, lats)

    # Clima: un valor de POWER para la zona; la temperatura se ajusta por altura
    clima = clima_power((lat_min + lat_max) / 2, (lon_min + lon_max) / 2)
    temp = corregir_temp_por_altura(clima["temp"], clima["altura_power"], alt_c)

    n = alt_c.size
    tabla = pd.DataFrame({
        "celda": np.arange(n),
        "lat": lat_m.ravel().round(5),
        "lon": lon_m.ravel().round(5),
        "altura": alt_c.ravel().round(0),
        "pendiente": pen_c.ravel().round(1),
        "temp": np.asarray(temp).ravel().round(1),
        "lluvia": round(clima["lluvia"]),
        "humedad": np.nan,          # lo llena src/nisar.py
        "encharcamiento": np.nan,   # lo llena src/nisar.py
        "vegetacion": np.nan,       # lo llena src/nisar.py
    })[COLUMNAS_CELDA]

    DATOS_PROCESADOS.mkdir(parents=True, exist_ok=True)
    tabla.to_csv(ruta_celdas(clave_zona), index=False)
    return tabla


# ---------------------------------------------------------------------------
# Lectura para la app
# ---------------------------------------------------------------------------
def ruta_celdas(clave_zona: str) -> Path:
    return DATOS_PROCESADOS / f"celdas_{clave_zona}.csv"


def cargar_celdas(clave_zona: str) -> pd.DataFrame | None:
    """Tabla por celda ya procesada de una zona, o None si todavía no existe."""
    ruta = ruta_celdas(clave_zona)
    return pd.read_csv(ruta) if ruta.exists() else None


def celda_mas_cercana(tabla: pd.DataFrame, lat: float, lon: float) -> dict:
    d2 = (tabla["lat"] - lat) ** 2 + (tabla["lon"] - lon) ** 2
    return tabla.loc[d2.idxmin()].to_dict()


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ZONAS:
        print("Uso: python -m src.clima_relieve ZONA     Zonas:", ", ".join(ZONAS))
        sys.exit(1)
    t = construir_tabla_celdas(sys.argv[1], descargar="--sin-descarga" not in sys.argv)
    print(f"Listo: {len(t)} celdas -> {ruta_celdas(sys.argv[1])}")
    print(t.describe().loc[["min", "mean", "max"], ["altura", "pendiente", "temp", "lluvia"]].round(1))

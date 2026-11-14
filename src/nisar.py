"""
Capas del radar NISAR (banda L): vegetación, encharcamiento y humedad.

Cada archivo GCOV pesa ~7 GB, así que NO se descargan: se abre cada archivo en
remoto y se lee solo el recorte de la zona (unos pocos MB). Todo se ejecuta ANTES
de la demo; la app solo lee el resultado.

    python -m src.nisar santo_domingo buscar     # lista la serie (no lee datos)
    python -m src.nisar santo_domingo procesar   # lee los recortes -> datos/procesados/nisar_<zona>.npz
    python -m src.nisar santo_domingo humedad    # lee la humedad de suelo SME2 -> humedad_<zona>.npz
    python -m src.nisar santo_domingo capas      # calcula las capas y llena la tabla por celda

Estructura confirmada con un archivo real (14 nov):
    /science/LSAR/GCOV/grids/frequencyA   HHHH, HVHV a 10 m
    /science/LSAR/GCOV/grids/frequencyB   HHHH, HVHV a 80 m   <- se usa esta: basta para celdas de ~250 m
    Valores en potencia lineal (gamma0); proyección UTM (en esta órbita, EPSG 32718).

descargar() y leer_banda() (archivo local completo) quedan por si se quiere bajar
UN archivo para verlo en QGIS; no se han probado.
"""
from __future__ import annotations

import getpass
import time
from pathlib import Path

import numpy as np

from .config import DATOS_CRUDOS, DATOS_PROCESADOS, ZONAS, forma_rejilla

RUTA_GCOV = "/science/LSAR/GCOV/grids/frequency{frecuencia}"
UMBRAL_AGUA_DB = -18.0        # HH por debajo de esto = agua abierta. CALIBRAR con la zona.
RUTA_SME2 = "/science/LSAR/SME2/grids"   # humedad de suelo nivel 3, celdas de 200 m
HUMEDAD_SATURACION = 0.5      # m³/m³ que se toma como suelo saturado (humedad = 1)
PENDIENTE_MAX_AGUA = 10.0     # en laderas más inclinadas lo oscuro es sombra del radar, no agua


# ---------------------------------------------------------------------------
# Búsqueda y descarga (ASF)
# ---------------------------------------------------------------------------
def _wkt(recuadro) -> str:
    a, b, c, d = recuadro
    return f"POLYGON(({a} {b}, {c} {b}, {c} {d}, {a} {d}, {a} {b}))"


def buscar_serie(clave_zona: str, inicio="2026-06-17", fin="2026-11-14", producto="GCOV") -> list:
    """Productos (GCOV o SME2) de UNA sola geometría (misma órbita) sobre la zona, por fecha."""
    import asf_search as asf
    zona = ZONAS[clave_zona]
    res = asf.search(dataset="NISAR", intersectsWith=_wkt(zona["recuadro"]), start=inicio, end=fin)
    serie = [r for r in res
             if producto in str(r.properties.get("processingLevel", "")).upper()
             and r.properties.get("pathNumber") == zona["nisar_path"]
             and str(r.properties.get("flightDirection", "")).upper() == zona["nisar_direccion"]]
    return sorted(serie, key=lambda r: r.properties.get("startTime", ""))


def resumen(serie) -> list[dict]:
    """Fecha, nombre y tamaño de cada producto (para imprimir o revisar)."""
    def gigas(p):
        b = p.get("bytes") or 0
        if isinstance(b, dict):   # en NISAR viene un diccionario por archivo (.h5, .png…)
            b = (b.get(p.get("fileName")) or {}).get("bytes", 0)
        return round(b / 1e9, 2)

    return [{"fecha": str(r.properties.get("startTime", ""))[:10],
             "frame": r.properties.get("frameNumber"),
             "archivo": r.properties.get("fileName"),
             "GB": gigas(r.properties)} for r in serie]


def descargar(serie, carpeta: Path | None = None):
    """Descarga los productos indicados. Pide usuario y clave de Earthdata en la consola."""
    import asf_search as asf
    carpeta = carpeta or DATOS_CRUDOS / "nisar"
    carpeta.mkdir(parents=True, exist_ok=True)
    sesion = asf.ASFSession().auth_with_creds(input("Usuario Earthdata: "),
                                              getpass.getpass("Clave: "))
    for r in serie:
        r.download(path=str(carpeta), session=sesion)


# ---------------------------------------------------------------------------
# Lectura de un archivo GCOV (HDF5)
# ---------------------------------------------------------------------------
def explorar(ruta) -> None:
    """Imprime todos los grupos y datasets del archivo (para confirmar las rutas)."""
    import h5py
    with h5py.File(ruta, "r") as f:
        f.visit(print)


def leer_banda(ruta, banda="HVHV", frecuencia="A"):
    """Lee una banda de covarianza (potencia lineal). Devuelve (matriz, x, y, epsg)."""
    import h5py
    grupo = RUTA_GCOV.format(frecuencia=frecuencia)
    with h5py.File(ruta, "r") as f:
        if grupo not in f or banda not in f[grupo]:
            raise KeyError(f"No existe {grupo}/{banda} en {ruta}. "
                           "Ejecuta explorar(ruta) y corrige RUTA_GCOV.")
        g = f[grupo]
        datos = g[banda][()].astype("float32")
        x, y = g["xCoordinates"][()], g["yCoordinates"][()]
        epsg = int(g["projection"][()]) if "projection" in g else None
    datos[datos <= 0] = np.nan
    return datos, x, y, epsg


# ---------------------------------------------------------------------------
# Cálculo de las capas (entradas: pilas de fechas con forma [fecha, fila, columna])
# ---------------------------------------------------------------------------
def a_db(potencia):
    """Potencia lineal -> decibeles."""
    return 10 * np.log10(np.clip(potencia, 1e-6, None))


def filtrar_speckle(imagen, tam=5):
    """Reduce el ruido granulado del radar con un filtro de mediana."""
    from scipy.ndimage import median_filter
    return median_filter(imagen, size=tam)


def capa_vegetacion(hh, hv):
    """Índice de vegetación del radar (RVI de dos polarizaciones), promedio en el tiempo.

    RVI = 4·HV / (HH + HV): cerca de 0 en suelo desnudo, más alto con más vegetación.
    """
    with np.errstate(invalid="ignore", divide="ignore"):
        rvi = 4 * hv / (hh + hv)
    return np.nanmean(np.clip(rvi, 0, 1), axis=0)


def capa_encharcamiento(hh, umbral_db=UMBRAL_AGUA_DB):
    """Fracción de fechas (0 a 1) en que el píxel se vio como agua abierta (HH muy bajo)."""
    agua = np.where(np.isnan(hh), np.nan, (a_db(hh) < umbral_db).astype("float32"))
    return np.nanmean(agua, axis=0)


def humedad_relativa(hh):
    """Humedad relativa por fecha (0 = lo más seco visto en el píxel, 1 = lo más húmedo).

    Método de detección de cambios: en un mismo píxel, HH sube cuando el suelo se moja.
    OJO: es relativa a cada píxel. Para comparar terrenos entre sí conviene usar el
    producto de humedad de suelo de NISAR (SME2) cuando se confirme en la User Guide.
    """
    db = a_db(hh)
    seco, mojado = np.nanmin(db, axis=0), np.nanmax(db, axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        return (db - seco) / (mojado - seco)


# ---------------------------------------------------------------------------
# Llevar una capa a la tabla por celda
# ---------------------------------------------------------------------------
def agregar_a_celdas(tabla, columna, capa, x, y, epsg, ventana=9):
    """Escribe en `tabla[columna]` el valor de la capa en el centro de cada celda.

    La capa se suaviza con una ventana (en píxeles) parecida al tamaño de la celda.
    x, y son las coordenadas del archivo GCOV y epsg su proyección.
    """
    from pyproj import Transformer
    from scipy.ndimage import uniform_filter
    suave = uniform_filter(np.nan_to_num(capa, nan=float(np.nanmean(capa))), size=ventana)
    a_capa = Transformer.from_crs(4326, epsg, always_xy=True)
    xs, ys = a_capa.transform(tabla["lon"].to_numpy(), tabla["lat"].to_numpy())
    col = np.round((xs - x[0]) / (x[1] - x[0])).astype(int)
    fil = np.round((ys - y[0]) / (y[1] - y[0])).astype(int)
    dentro = (fil >= 0) & (fil < capa.shape[0]) & (col >= 0) & (col < capa.shape[1])
    valores = np.full(len(tabla), np.nan)
    valores[dentro] = suave[fil[dentro], col[dentro]]
    tabla[columna] = valores
    return tabla


# ---------------------------------------------------------------------------
# Lectura remota: solo el recorte de la zona, sin descargar el archivo
# ---------------------------------------------------------------------------
def sesion_remota():
    """Sesión para leer archivos de Earthdata por internet (usa el login guardado)."""
    import earthaccess
    earthaccess.login()
    return earthaccess.get_fsspec_https_session()


def _ventana(g, recuadro):
    """Índices (f0, f1, c0, c1) de la ventana del grupo `g` que cubre el recuadro, y x, y, epsg."""
    from pyproj import Transformer
    x, y = g["xCoordinates"][()], g["yCoordinates"][()]
    epsg = int(g["projection"][()])
    dx, dy = x[1] - x[0], y[1] - y[0]            # dy es negativo: la fila 0 es el norte

    lon_min, lat_min, lon_max, lat_max = recuadro
    lons = np.linspace(lon_min, lon_max, 5)
    lats = np.linspace(lat_min, lat_max, 5)
    borde_lon, borde_lat = np.meshgrid(lons, lats)
    xs, ys = Transformer.from_crs(4326, epsg, always_xy=True).transform(borde_lon.ravel(),
                                                                         borde_lat.ravel())
    c0 = max(0, int(np.floor((min(xs) - x[0]) / dx)))
    c1 = min(len(x), int(np.ceil((max(xs) - x[0]) / dx)) + 1)
    f0 = max(0, int(np.floor((max(ys) - y[0]) / dy)))
    f1 = min(len(y), int(np.ceil((min(ys) - y[0]) / dy)) + 1)
    if c0 >= c1 or f0 >= f1:
        return None
    return f0, f1, c0, c1, x[c0:c1], y[f0:f1], epsg


def leer_recorte(f, recuadro, frecuencia="B", bandas=("HHHH", "HVHV")):
    """Lee de un archivo GCOV ya abierto (h5py) solo la ventana que cubre el recuadro.

    Devuelve (dict banda -> matriz, x, y, epsg), o None si el archivo no toca la zona.
    """
    g = f[RUTA_GCOV.format(frecuencia=frecuencia)]
    v = _ventana(g, recuadro)
    if v is None:
        return None
    f0, f1, c0, c1, x, y, epsg = v
    # `mask` = número de subfranja de las muestras válidas; 0 = inválida, 255 = sin dato.
    # Las inválidas traen valores casi cero que parecerían agua: hay que descartarlas.
    mascara = g["mask"][f0:f1, c0:c1]
    valido = (mascara > 0) & (mascara < 255)
    datos = {}
    for b in bandas:
        m = g[b][f0:f1, c0:c1].astype("float32")
        m[~valido | ~np.isfinite(m) | (m <= 0)] = np.nan
        datos[b] = m
    return datos, x, y, epsg


def leer_recorte_sme2(f, recuadro, _=None):
    """Lee de un archivo SME2 abierto la humedad de suelo (m³/m³) de la ventana de la zona.

    Devuelve ({"sm": humedad, "rec": 1 si la NASA recomienda el dato / 0 si no}, x, y, epsg).
    En vegetación densa la mayoría de los datos viene marcada como "no recomendado".
    """
    g = f[RUTA_SME2]
    v = _ventana(g, recuadro)
    if v is None:
        return None
    f0, f1, c0, c1, x, y, epsg = v
    sm = g["soilMoisture"][f0:f1, c0:c1].astype("float32")
    calidad = g["retrievalQualityFlag"][f0:f1, c0:c1]
    valido = np.isfinite(sm) & (sm > 0) & (calidad >= 0)       # -9999 = sin dato
    sm[~valido] = np.nan
    rec = np.where(valido, ((calidad & 1) == 0).astype("float32"), np.nan)   # bit 0 = 0: recomendado
    return {"sm": sm, "rec": rec}, x, y, epsg


def _leer_remoto_con_reintentos(url, recuadro, frecuencia, intentos=4, lector=None):
    """Abre el archivo en remoto y lee el recorte. Reintenta si el servidor falla (403, cortes)."""
    import h5py
    ultimo = None
    for n in range(intentos):
        try:
            fs = sesion_remota()      # sesión nueva en cada intento: renueva el enlace firmado
            # Bloques de 1 MB guardados en memoria: baja ~15 MB por archivo, no los 7 GB
            with fs.open(url, mode="rb", block_size=1024 * 1024, cache_type="blockcache",
                         cache_options={"maxblocks": 512}) as fh, h5py.File(fh, "r") as f:
                return (lector or leer_recorte)(f, recuadro, frecuencia)
        except Exception as error:  # noqa: BLE001
            ultimo = error
            time.sleep(5 * (n + 1))
    raise ultimo


def _a_rejilla(valores, x, y, epsg, recuadro):
    """Suma y cuenta de píxeles válidos por celda (para promediar en potencia lineal)."""
    from pyproj import Transformer
    filas, columnas, paso = forma_rejilla(recuadro)
    lon_min, _, _, lat_max = recuadro
    xx, yy = np.meshgrid(x, y)
    lon, lat = Transformer.from_crs(epsg, 4326, always_xy=True).transform(xx.ravel(), yy.ravel())
    i = np.floor((lat_max - lat) / paso).astype(int)
    j = np.floor((lon - lon_min) / paso).astype(int)
    v = valores.ravel()
    ok = (i >= 0) & (i < filas) & (j >= 0) & (j < columnas) & np.isfinite(v)
    k = i[ok] * columnas + j[ok]
    suma = np.bincount(k, weights=v[ok], minlength=filas * columnas).reshape(filas, columnas)
    cuenta = np.bincount(k, minlength=filas * columnas).reshape(filas, columnas)
    return suma, cuenta


def ruta_serie(clave_zona: str) -> Path:
    return DATOS_PROCESADOS / f"nisar_{clave_zona}.npz"


def _ruta_parcial(clave_zona: str, frecuencia: str, fecha: str) -> Path:
    return DATOS_PROCESADOS / "_nisar_tmp" / f"{clave_zona}_{frecuencia}_{fecha}.npz"


def procesar_fecha(clave_zona: str, fecha: str, frecuencia="B"):
    """Lee en remoto los archivos de UNA fecha y guarda HH, HV y agua por celda."""
    recuadro = ZONAS[clave_zona]["recuadro"]
    filas, columnas, _ = forma_rejilla(recuadro)
    archivos = [r for r in buscar_serie(clave_zona, fecha, fecha + "T23:59:59")
                if str(r.properties["startTime"])[:10] == fecha]
    if not archivos:
        raise RuntimeError(f"No hay productos GCOV el {fecha}")
    acum = {n: np.zeros((filas, columnas)) for n in ("hh", "hv", "agua")}
    cuenta = np.zeros((filas, columnas))
    for r in archivos:
        t0 = time.time()
        rec = _leer_remoto_con_reintentos(r.properties["url"], recuadro, frecuencia)
        if rec is None:
            print(f"  {fecha} frame {r.properties['frameNumber']}: no toca la zona", flush=True)
            continue
        datos, x, y, epsg = rec
        s_hh, n = _a_rejilla(datos["HHHH"], x, y, epsg, recuadro)
        s_hv, _ = _a_rejilla(datos["HVHV"], x, y, epsg, recuadro)
        es_agua = np.where(np.isnan(datos["HHHH"]), np.nan,
                           (a_db(datos["HHHH"]) < UMBRAL_AGUA_DB).astype("float32"))
        s_agua, _ = _a_rejilla(es_agua, x, y, epsg, recuadro)
        acum["hh"] += s_hh
        acum["hv"] += s_hv
        acum["agua"] += s_agua
        cuenta += n
        print(f"  {fecha} frame {r.properties['frameNumber']}: ventana {datos['HHHH'].shape}, "
              f"{(n > 0).mean():.0%} de las celdas, {time.time() - t0:.0f} s", flush=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        capas = {n: np.where(cuenta > 0, acum[n] / cuenta, np.nan).astype("float32") for n in acum}
    parcial = _ruta_parcial(clave_zona, frecuencia, fecha)
    parcial.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(parcial, **capas)
    return parcial


def procesar_fecha_sme2(clave_zona: str, fecha: str):
    """Lee en remoto la humedad de suelo (SME2) de UNA fecha y la promedia por celda."""
    recuadro = ZONAS[clave_zona]["recuadro"]
    filas, columnas, _ = forma_rejilla(recuadro)
    archivos = [r for r in buscar_serie(clave_zona, fecha, fecha + "T23:59:59", producto="SME2")
                if str(r.properties["startTime"])[:10] == fecha]
    if not archivos:
        raise RuntimeError(f"No hay productos SME2 el {fecha}")
    s_sm, s_rec, cuenta = (np.zeros((filas, columnas)) for _ in range(3))
    for r in archivos:
        t0 = time.time()
        leido = _leer_remoto_con_reintentos(r.properties["url"], recuadro, None,
                                            lector=leer_recorte_sme2)
        if leido is None:
            continue
        datos, x, y, epsg = leido
        a, n = _a_rejilla(datos["sm"], x, y, epsg, recuadro)
        b, _ = _a_rejilla(datos["rec"], x, y, epsg, recuadro)
        s_sm += a
        s_rec += b
        cuenta += n
        print(f"  {fecha} frame {r.properties['frameNumber']}: humedad en "
              f"{(n > 0).mean():.0%} de las celdas, {time.time() - t0:.0f} s", flush=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        capas = {"sm": np.where(cuenta > 0, s_sm / cuenta, np.nan).astype("float32"),
                 "rec": np.where(cuenta > 0, s_rec / cuenta, np.nan).astype("float32")}
    parcial = _ruta_parcial(clave_zona, "SME2", fecha)
    parcial.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(parcial, **capas)
    return parcial


def ruta_humedad(clave_zona: str) -> Path:
    return DATOS_PROCESADOS / f"humedad_{clave_zona}.npz"


def procesar_serie(clave_zona: str, frecuencia="B", max_fechas=None, inicio="2026-06-17",
                   fin="2026-11-14", segundos_por_fecha=240, intentos=3, producto="GCOV"):
    """Lee en remoto toda la serie y guarda HH, HV y agua por celda y por fecha.

    Cada fecha se lee en un proceso aparte con límite de tiempo: la conexión a veces
    se queda colgada, y así solo se repite esa fecha. Las fechas ya leídas se
    conservan, de modo que se puede volver a ejecutar para completar las que falten.

    Guarda datos/procesados/nisar_<zona>.npz con:
        fechas  lista de fechas (texto)
        hh, hv  [fecha, fila, columna]  potencia lineal promedio de la celda (NaN = sin dato)
        agua    [fecha, fila, columna]  fracción de píxeles de la celda con HH < UMBRAL_AGUA_DB
    """
    import subprocess
    import sys

    from .config import RAIZ
    serie = buscar_serie(clave_zona, inicio, fin, producto=producto)
    fechas = sorted({str(r.properties["startTime"])[:10] for r in serie})[:max_fechas]
    es_gcov = producto == "GCOV"
    etiqueta = frecuencia if es_gcov else "SME2"
    orden = ["fecha", "{fecha}", frecuencia] if es_gcov else ["fecha_sme2", "{fecha}"]
    salida = ruta_serie(clave_zona) if es_gcov else ruta_humedad(clave_zona)

    pilas, fechas_ok = {}, []
    for fecha in fechas:
        parcial = _ruta_parcial(clave_zona, etiqueta, fecha)
        for intento in range(1, intentos + 1):
            if parcial.exists():
                break
            try:
                subprocess.run([sys.executable, "-W", "ignore", "-m", "src.nisar", clave_zona]
                               + [o.format(fecha=fecha) for o in orden],
                               cwd=RAIZ, timeout=segundos_por_fecha)
            except subprocess.TimeoutExpired:
                print(f"  {fecha}: se colgó (intento {intento} de {intentos})", flush=True)
        if not parcial.exists():
            print(f"  {fecha}: NO se pudo leer. Vuelve a ejecutar para reintentarla.", flush=True)
            continue
        p = np.load(parcial)
        for nombre in p.files:
            pilas.setdefault(nombre, []).append(p[nombre])
        fechas_ok.append(fecha)

    if not fechas_ok:
        raise RuntimeError("No se pudo leer ninguna fecha. Revisa el internet y el login de Earthdata.")
    np.savez_compressed(salida, fechas=np.array(fechas_ok),
                        **{n: np.array(v, dtype="float32") for n, v in pilas.items()})
    print(f"Fechas en la serie {producto}: {len(fechas_ok)} de {len(fechas)}", flush=True)
    return salida


def capas_a_tabla(clave_zona: str):
    """Calcula vegetación y encharcamiento con la serie guardada y llena la tabla por celda."""
    import warnings

    import pandas as pd

    from .clima_relieve import ruta_celdas
    s = np.load(ruta_serie(clave_zona))
    tabla = pd.read_csv(ruta_celdas(clave_zona))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)      # celdas sin ningún dato
        vegetacion = capa_vegetacion(s["hh"], s["hv"])
        encharcamiento = np.nanmean(s["agua"], axis=0)
    # En laderas inclinadas lo oscuro es sombra del radar, no agua acumulada
    pendiente = tabla["pendiente"].to_numpy().reshape(encharcamiento.shape)
    encharcamiento = np.where(pendiente > PENDIENTE_MAX_AGUA, 0.0, encharcamiento)
    encharcamiento = np.where(np.isnan(vegetacion), np.nan, encharcamiento)
    tabla["vegetacion"] = vegetacion.ravel().round(3)
    tabla["encharcamiento"] = encharcamiento.ravel().round(3)
    if ruta_humedad(clave_zona).exists():
        h = np.load(ruta_humedad(clave_zona))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            # humedad: 0 = seco, 1 = saturado (HUMEDAD_SATURACION m³/m³), promedio de la serie
            humedad = np.clip(np.nanmean(h["sm"], axis=0) / HUMEDAD_SATURACION, 0, 1)
            confiable = np.nanmean(h["rec"], axis=0)   # fracción de datos "recomendados" por la NASA
        tabla["humedad"] = humedad.ravel().round(3)
        tabla["humedad_confiable"] = confiable.ravel().round(2)
    tabla.to_csv(ruta_celdas(clave_zona), index=False)
    return tabla


if __name__ == "__main__":
    import sys
    clave = sys.argv[1] if len(sys.argv) > 1 else "santo_domingo"
    accion = sys.argv[2] if len(sys.argv) > 2 else "buscar"
    if accion == "buscar":
        for fila in resumen(buscar_serie(clave)):
            print(fila)
    elif accion == "procesar":
        n = int(sys.argv[3]) if len(sys.argv) > 3 else None
        print("Guardado:", procesar_serie(clave, max_fechas=n))
    elif accion == "humedad":
        print("Guardado:", procesar_serie(clave, producto="SME2"))
    elif accion == "fecha_sme2":
        procesar_fecha_sme2(clave, sys.argv[3])
    elif accion == "fecha":
        procesar_fecha(clave, sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "B")
    elif accion == "capas":
        t = capas_a_tabla(clave)
        print(t[[c for c in ("vegetacion", "encharcamiento", "humedad", "humedad_confiable")
                 if c in t]].describe().round(3))
        print(f"Celdas con dato de NISAR: {t['vegetacion'].notna().mean():.0%}")
    else:
        print("Uso: python -m src.nisar ZONA [buscar|procesar|humedad|capas]")

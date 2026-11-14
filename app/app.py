"""
SmartSeeds · interfaz en Streamlit.

Ejecutar desde la raíz del repositorio (con el entorno `condor` activado):
    streamlit run app/app.py

La app NO procesa radar en vivo: lee las tablas de `datos/procesados/` y solo
consulta en línea el clima de NASA POWER (es una consulta liviana).
"""
import sys
from pathlib import Path

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src.clima_relieve import cargar_celdas, celda_mas_cercana, clima_power, ruta_celdas  # noqa: E402
from src.config import CAPITALES, ZONAS, en_ecuador, provincia_sugerida, zona_de_punto  # noqa: E402
from src.mercado import ETIQUETAS  # noqa: E402
from src.recomendar import PUNTAJE_MINIMO, evaluar_todos  # noqa: E402

st.set_page_config(page_title="SmartSeeds", page_icon="🌱", layout="wide")

CENTRO_ECUADOR, ZOOM_ECUADOR = (-1.4, -78.6), 7
ICONO_MERCADO = {"alta": "🟢", "media": "🟡", "saturado": "🔴", "sin_datos": "⚪"}


# --- Datos (con caché para no repetir consultas) ----------------------------
@st.cache_data(ttl=24 * 3600, show_spinner="Consultando el clima en NASA POWER…")
def clima(lat: float, lon: float) -> dict:
    return clima_power(lat, lon)


@st.cache_data(show_spinner=False)
def celdas(clave_zona: str, _modificado: float) -> pd.DataFrame:
    return cargar_celdas(clave_zona)


def datos_del_terreno(lat: float, lon: float) -> tuple[dict, dict, str | None]:
    """Devuelve (celda, clima, clave_zona). La celda sigue el formato acordado."""
    c = clima(round(lat, 2), round(lon, 2))
    clave = zona_de_punto(lat, lon)
    if clave and ruta_celdas(clave).exists():
        tabla = celdas(clave, ruta_celdas(clave).stat().st_mtime)
        return celda_mas_cercana(tabla, lat, lon), c, clave
    celda = {"lat": lat, "lon": lon, "altura": c["altura_power"], "pendiente": None,
             "temp": c["temp"], "lluvia": c["lluvia"],
             "humedad": None, "encharcamiento": None, "vegetacion": None}
    return celda, c, None


def tiene(valor) -> bool:
    return valor is not None and not pd.isna(valor)


# --- Barra lateral ----------------------------------------------------------
with st.sidebar:
    st.title("🌱 SmartSeeds")
    st.caption("Equipo Condor Mission · NASA Space Apps 2026")
    opciones = {"Todo Ecuador": None} | {z["nombre"]: k for k, z in ZONAS.items()}
    vista = st.selectbox("Ir a", list(opciones))
    st.markdown(
        "**Cómo usarla**\n"
        "1. Toca tu terreno en el mapa.\n"
        "2. Mira qué cultivos le convienen y por qué.\n\n"
        "Los recuadros verdes son las zonas con detalle del radar **NISAR**."
    )
    st.divider()
    st.caption(
        "Datos: NASA POWER (clima), NASADEM (relieve), NISAR (radar), "
        "FAO EcoCrop (cultivos), INEC-ESPAC y MAG (mercado).\n\n"
        "⚠️ Versión en desarrollo: los requisitos de los cultivos son preliminares. "
        "Es una recomendación orientativa, no una orden."
    )

# --- Mapa -------------------------------------------------------------------
st.title("¿Qué me conviene sembrar?")

if opciones[vista]:
    lon_min, lat_min, lon_max, lat_max = ZONAS[opciones[vista]]["recuadro"]
    centro, zoom = ((lat_min + lat_max) / 2, (lon_min + lon_max) / 2), 11
else:
    centro, zoom = CENTRO_ECUADOR, ZOOM_ECUADOR

col_mapa, col_resultado = st.columns([3, 2], gap="large")

with col_mapa:
    mapa = folium.Map(location=centro, zoom_start=zoom, control_scale=True)
    for z in ZONAS.values():
        lon_min, lat_min, lon_max, lat_max = z["recuadro"]
        folium.Rectangle([(lat_min, lon_min), (lat_max, lon_max)], color="#2e7d32", weight=2,
                         fill=True, fill_opacity=0.05, tooltip=f"Zona detallada: {z['nombre']}",
                         interactive=False).add_to(mapa)
    marcador = folium.FeatureGroup(name="terreno")
    # Enlace directo a un terreno (útil para la demo): …/?lat=-0.33&lon=-79.12
    if "punto" not in st.session_state and {"lat", "lon"} <= set(st.query_params):
        try:
            st.session_state["punto"] = (float(st.query_params["lat"]), float(st.query_params["lon"]))
        except ValueError:
            pass
    punto = st.session_state.get("punto")
    if punto:
        folium.Marker(punto, tooltip="Tu terreno").add_to(marcador)
    salida = st_folium(mapa, height=560, use_container_width=True, center=centro, zoom=zoom,
                       feature_group_to_add=marcador, returned_objects=["last_clicked"],
                       key="mapa")
    clic = (salida or {}).get("last_clicked")
    if clic:
        nuevo = (round(clic["lat"], 5), round(clic["lng"], 5))
        if nuevo != punto:
            st.session_state["punto"] = nuevo
            st.rerun()

# --- Resultados -------------------------------------------------------------
with col_resultado:
    if not punto:
        st.info("👈 Toca un punto del mapa para analizar ese terreno.")
        st.stop()

    lat, lon = punto
    if not en_ecuador(lat, lon):
        st.warning("Ese punto está fuera del Ecuador continental. Elige otro terreno.")
        st.stop()

    try:
        celda, c, clave_zona = datos_del_terreno(lat, lon)
    except Exception as error:  # noqa: BLE001
        st.error(f"No se pudo consultar el clima de NASA POWER. Revisa tu internet.\n\n{error}")
        st.stop()

    st.subheader("Tu terreno")
    st.caption(f"Latitud {lat:.4f}, longitud {lon:.4f}")
    if clave_zona:
        st.success(f"Nivel detallado · {ZONAS[clave_zona]['nombre']}")
    elif zona_de_punto(lat, lon):
        st.warning("Zona detallada, pero todavía no se ha generado su tabla de celdas "
                   "(`python -m src.clima_relieve`). Se muestra el nivel nacional.")
    else:
        st.info("Nivel nacional: clima y altura aproximados (promedio de ~50 km).")

    (m1, m2), (m3, m4) = st.columns(2), st.columns(2)
    m1.metric("Altura", f"{celda['altura']:.0f} m" if tiene(celda["altura"]) else "—")
    m2.metric("Temperatura", f"{celda['temp']:.1f} °C" if tiene(celda["temp"]) else "—")
    m3.metric("Lluvia", f"{celda['lluvia']:.0f} mm" if tiene(celda["lluvia"]) else "—",
              help="Milímetros de lluvia por año")
    m4.metric("Pendiente", f"{celda['pendiente']:.0f}°" if tiene(celda["pendiente"]) else "—")

    if clave_zona:
        st.markdown("**Lo que vio el radar NISAR** (pasadas cada 12 días, a través de las nubes)")
        if tiene(celda.get("vegetacion")):
            n1, n2, n3 = st.columns(3)
            n1.metric("Vegetación", f"{celda['vegetacion']:.2f}",
                      help="Índice de vegetación del radar: 0 = suelo desnudo, 1 = vegetación densa")
            n2.metric("Encharcamiento", f"{celda['encharcamiento']:.0%}",
                      help="Parte de las pasadas en que el radar vio agua acumulada")
            n3.metric("Humedad", f"{celda['humedad']:.0%}" if tiene(celda.get("humedad")) else "—",
                      help="Humedad del suelo (producto SME2 de NISAR): 100 % = suelo saturado")
        else:
            st.caption("Este punto queda fuera de la franja que cubre el radar en esta órbita.")

    provincias = sorted(CAPITALES)
    sugerida = provincia_sugerida(lat, lon)
    provincia = st.selectbox("Provincia (para el mercado)", provincias,
                             index=provincias.index(sugerida), key=f"prov_{lat}_{lon}",
                             help="Se sugiere la más cercana; corrígela si no es la tuya.")

    todos = evaluar_todos(celda, provincia)
    mejores = [x for x in todos if x["puntaje"] >= PUNTAJE_MINIMO][:3]

    st.subheader("Cultivos recomendados")
    if not mejores:
        st.warning("Ningún cultivo de la lista alcanza una aptitud suficiente en este terreno.")
    for i, cultivo in enumerate(mejores, start=1):
        with st.container(border=True):
            a, b = st.columns([3, 1])
            a.markdown(f"### {i}. {cultivo['nombre']}")
            a.caption(f"*{cultivo['nombre_cientifico']}* · {str(cultivo['tipo']).replace('_', ' ')}")
            b.metric("Aptitud", f"{cultivo['puntaje']:.0f}/100")
            st.progress(min(1.0, cultivo["puntaje"] / 100))
            st.markdown(f"{ICONO_MERCADO[cultivo['mercado']]} **{ETIQUETAS[cultivo['mercado']]}** — "
                        f"{cultivo['mercado_texto']}")
            with st.expander("¿Por qué?", expanded=(i == 1)):
                for f in cultivo["factores"]:
                    icono = "•" if f["nota"] is None else "✅" if f["nota"] >= 1 else \
                            "⚠️" if f["nota"] > 0 else "❌"
                    st.markdown(f"{icono} {f['texto']}")

# --- Tabla completa ---------------------------------------------------------
with st.expander("Ver todos los cultivos evaluados"):
    st.dataframe(
        pd.DataFrame([{"Cultivo": x["nombre"], "Aptitud": x["puntaje"],
                       "Mercado": ETIQUETAS[x["mercado"]]} for x in todos]),
        hide_index=True, use_container_width=True,
        column_config={"Aptitud": st.column_config.ProgressColumn(
            "Aptitud (0–100)", min_value=0, max_value=100, format="%.0f")},
    )

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
import numpy as np
import pandas as pd
import streamlit as st
from branca.element import MacroElement
from folium.plugins import Draw
from jinja2 import Template
from streamlit_folium import st_folium

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src.clima_relieve import cargar_celdas, celda_mas_cercana, clima_power, ruta_celdas  # noqa: E402
from src.config import (CAPITALES, ZONAS, en_ecuador, forma_rejilla, provincia_sugerida,  # noqa: E402
                        zona_de_punto)
from src.nisar import cargar_series, ruta_serie, serie_del_terreno  # noqa: E402
from src.mercado import ETIQUETAS  # noqa: E402
from src.aptitud import AGUA_VISIBLE  # noqa: E402
from src.recomendar import PUNTAJE_MINIMO, empatados, evaluar_todos, reparto_mejor_cultivo  # noqa: E402
from src.terreno import area_texto, celda_promedio, celdas_del_terreno, vertices_de_geojson  # noqa: E402
from src.terreno import centro as centro_terreno  # noqa: E402  (aquí `centro` es el centro del mapa)

st.set_page_config(page_title="SmartSeeds", page_icon="🌱", layout="wide")

CENTRO_ECUADOR, ZOOM_ECUADOR = (-1.4, -78.6), 7
ICONO_MERCADO = {"alta": "🟢", "media": "🟡", "saturado": "🔴", "sin_datos": "⚪"}
MODO_PUNTO, MODO_DIBUJO = "📍 Tocar un punto", "✏️ Dibujar mi terreno"
RIEGO_NO, RIEGO_SI = "No, solo lluvia", "Sí, tengo riego"

# Capas del radar que se pueden pintar sobre el mapa: nombre -> columna de la tabla por celda.
# Cada capa usa UN solo color, de claro (poco) a oscuro (mucho).
CAPAS_RADAR = {"Nada": None, "Agua (dónde se encharca)": "encharcamiento",
               "Vegetación": "vegetacion", "Humedad del suelo": "humedad"}
RAMPA_AZUL = ((0x86, 0xB6, 0xEF), (0x0D, 0x36, 0x6B))
RAMPA_VERDE = ((0xC8, 0xE6, 0xC0), (0x00, 0x63, 0x00))
RAMPAS = {"encharcamiento": RAMPA_AZUL, "humedad": RAMPA_AZUL, "vegetacion": RAMPA_VERDE}
GRIS_SIN_RADAR = (137, 135, 129, 110)     # celdas que el radar no cubre
OPACIDAD_CAPA = 200                       # de 0 (invisible) a 255 (tapa el mapa)
AGUA_MUCHA = 0.5                          # agua en la mitad de las pasadas = azul más oscuro
COLOR_LINEA = {"light": "#2a78d6", "dark": "#3987e5"}

# Gráficos de la serie del radar: columna -> (título, cómo leerlo)
GRAFICOS_RADAR = {
    "vegetacion": ("Vegetación (0 = suelo desnudo, 100 = vegetación densa)",
                   "Si la línea sube, las plantas están creciendo. Si baja de golpe, suele ser "
                   "cosecha o preparación del terreno. No hay dato en las pasadas en que el "
                   "terreno estaba cubierto de agua."),
    "agua": ("Agua sobre el terreno (% del terreno)",
             "Parte del terreno que el radar vio cubierta de agua en cada pasada."),
    "humedad": ("Humedad del suelo (100 = suelo saturado)",
                "Humedad que midió el radar (producto SME2 de NISAR). Bajo vegetación muy "
                "densa es poco confiable."),
}
PREFERENCIAS = {"Cosechar pronto": "pronto", "Un cultivo para muchos años": "largo"}

# Textos en español de la herramienta de dibujo del mapa (vienen en inglés)
DIBUJO_EN_ESPANOL = """
if (window.L && L.drawLocal) {
    var d = L.drawLocal;
    d.draw.toolbar.buttons.polygon = 'Dibujar mi terreno (esquina por esquina)';
    d.draw.toolbar.buttons.rectangle = 'Dibujar un terreno rectangular';
    d.draw.toolbar.actions.text = 'Cancelar';
    d.draw.toolbar.actions.title = 'Cancelar el dibujo';
    d.draw.toolbar.finish.text = 'Terminar';
    d.draw.toolbar.finish.title = 'Terminar el dibujo';
    d.draw.toolbar.undo.text = 'Borrar la última esquina';
    d.draw.toolbar.undo.title = 'Borrar la última esquina marcada';
    d.draw.handlers.polygon.tooltip.start = 'Toca la primera esquina de tu terreno';
    d.draw.handlers.polygon.tooltip.cont = 'Toca la siguiente esquina';
    d.draw.handlers.polygon.tooltip.end = 'Toca la primera esquina otra vez para cerrar';
    d.draw.handlers.rectangle.tooltip.start = 'Mantén apretado y arrastra para dibujar';
    d.draw.handlers.simpleshape.tooltip.end = 'Suelta para terminar';
    d.edit.toolbar.buttons.edit = 'Corregir el dibujo';
    d.edit.toolbar.buttons.editDisabled = 'No hay nada que corregir';
    d.edit.toolbar.buttons.remove = 'Borrar el dibujo';
    d.edit.toolbar.buttons.removeDisabled = 'No hay nada que borrar';
    d.edit.toolbar.actions.save.text = 'Guardar';
    d.edit.toolbar.actions.cancel.text = 'Cancelar';
    d.edit.toolbar.actions.clearAll.text = 'Borrar todo';
    d.edit.handlers.edit.tooltip.text = 'Arrastra las esquinas para corregir';
    d.edit.handlers.edit.tooltip.subtext = 'Luego toca Guardar';
    d.edit.handlers.remove.tooltip.text = 'Toca el dibujo que quieres borrar';
}
"""


class TextosDibujo(MacroElement):
    """Elemento del mapa que solo traduce al español los textos de la herramienta de dibujo."""
    _template = Template("{% macro script(this, kwargs) %}" + DIBUJO_EN_ESPANOL + "{% endmacro %}")


# --- Datos (con caché para no repetir consultas) ----------------------------
@st.cache_data(ttl=24 * 3600, show_spinner="Consultando el clima en NASA POWER…")
def clima(lat: float, lon: float) -> dict:
    return clima_power(lat, lon)


# `modificado` es la fecha del archivo: si el archivo cambia, la caché se renueva sola.
@st.cache_data(show_spinner=False)
def celdas(clave_zona: str, modificado: float) -> pd.DataFrame:
    return cargar_celdas(clave_zona)


@st.cache_data(show_spinner=False)
def series_radar(clave_zona: str, modificado: float) -> dict | None:
    return cargar_series(clave_zona)


@st.cache_data(show_spinner=False)
def imagen_capa(clave_zona: str, columna: str, modificado: float) -> np.ndarray | None:
    """Imagen (fila, columna, RGBA) de una capa del radar, lista para ponerla sobre el mapa."""
    tabla = cargar_celdas(clave_zona)
    if tabla is None or columna not in tabla:
        return None
    filas, columnas, _ = forma_rejilla(ZONAS[clave_zona]["recuadro"])
    valor = tabla[columna].to_numpy(dtype="float64").reshape(filas, columnas)
    sin_radar = tabla["vegetacion"].isna().to_numpy().reshape(filas, columnas)
    if columna == "encharcamiento":           # solo se pinta donde hubo agua
        visible, tono = valor >= AGUA_VISIBLE, np.clip(valor / AGUA_MUCHA, 0, 1)
    else:
        visible, tono = ~np.isnan(valor), np.clip(valor, 0, 1)
    tono = np.nan_to_num(tono)
    claro, oscuro = RAMPAS[columna]
    imagen = np.zeros((filas, columnas, 4), dtype="uint8")
    for i in range(3):
        imagen[..., i] = (claro[i] + (oscuro[i] - claro[i]) * tono).astype("uint8")
    imagen[..., 3] = np.where(visible, OPACIDAD_CAPA, 0)
    imagen[sin_radar] = GRIS_SIN_RADAR
    return imagen


def leyenda_capa(columna: str) -> str:
    """Barrita de color con "poco" y "mucho" para explicar la capa pintada en el mapa."""
    claro, oscuro = ("#%02x%02x%02x" % c for c in RAMPAS[columna])
    return (f'<div style="display:flex;align-items:center;gap:8px;font-size:0.85rem">'
            f'<span>poco</span><div style="flex:1;max-width:220px;height:10px;border-radius:4px;'
            f'background:linear-gradient(90deg,{claro},{oscuro})"></div><span>mucho</span>'
            f'<span style="margin-left:12px;display:inline-block;width:12px;height:12px;'
            f'border-radius:3px;background:rgb(137,135,129)"></span><span>sin datos del radar</span>'
            f'</div>')


def datos_del_terreno(lat: float, lon: float, contorno=None):
    """Devuelve (celda, clima, clave_zona, celdas_del_contorno).

    La celda sigue el formato acordado. Si se dibujó un contorno dentro de una zona
    detallada, la celda es el PROMEDIO de las celdas que caen dentro del terreno y
    `celdas_del_contorno` es la tabla con esas celdas (None en los demás casos).
    """
    c = clima(round(lat, 2), round(lon, 2))
    clave = zona_de_punto(lat, lon)
    if clave and ruta_celdas(clave).exists():
        tabla = celdas(clave, ruta_celdas(clave).stat().st_mtime)
        if contorno:
            dentro = celdas_del_terreno(tabla, contorno)
            return celda_promedio(dentro, contorno), c, clave, dentro
        return celda_mas_cercana(tabla, lat, lon), c, clave, None
    celda = {"lat": lat, "lon": lon, "altura": c["altura_power"], "pendiente": None,
             "temp": c["temp"], "lluvia": c["lluvia"],
             "humedad": None, "encharcamiento": None, "vegetacion": None}
    return celda, c, None, None


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
        "1. Toca tu terreno en el mapa, o dibuja su contorno esquina por esquina.\n"
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
    modo = st.radio("¿Cómo quieres marcar tu terreno?", [MODO_PUNTO, MODO_DIBUJO], horizontal=True)
    capa = CAPAS_RADAR[st.selectbox(
        "Pintar sobre el mapa lo que vio el radar NISAR", list(CAPAS_RADAR),
        help="Pinta las zonas detalladas (recuadros verdes) con lo que midió el radar "
             "entre junio y octubre de 2026.")]
    if capa:
        st.markdown(leyenda_capa(capa), unsafe_allow_html=True)
    mapa = folium.Map(location=centro, zoom_start=zoom, control_scale=True)
    for clave, z in ZONAS.items():
        lon_min, lat_min, lon_max, lat_max = z["recuadro"]
        if capa and ruta_celdas(clave).exists():
            imagen = imagen_capa(clave, capa, ruta_celdas(clave).stat().st_mtime)
            if imagen is not None:
                folium.raster_layers.ImageOverlay(
                    imagen, bounds=[[lat_min, lon_min], [lat_max, lon_max]], origin="upper",
                    pixelated=True, interactive=False).add_to(mapa)
        folium.Rectangle([(lat_min, lon_min), (lat_max, lon_max)], color="#2e7d32", weight=2,
                         fill=True, fill_opacity=0.05, tooltip=f"Zona detallada: {z['nombre']}",
                         interactive=False).add_to(mapa)
    punto, contorno = None, None

    if modo == MODO_DIBUJO:
        # Herramienta de dibujo: solo polígono (terreno irregular) y rectángulo
        st.caption("Acerca el mapa a tu terreno, toca el botón ⬟ de la izquierda y marca cada "
                   "esquina. Para cerrar, toca otra vez la primera esquina.")
        TextosDibujo().add_to(mapa)         # antes de Draw: así los botones nacen en español
        Draw(draw_options={"polyline": False, "circle": False, "marker": False,
                           "circlemarker": False, "rectangle": True,
                           "polygon": {"allowIntersection": False, "showArea": False,
                                       "shapeOptions": {"color": "#e65100"}}},
             edit_options={"edit": True, "remove": True}).add_to(mapa)
        salida = st_folium(mapa, height=560, use_container_width=True, center=centro, zoom=zoom,
                           returned_objects=["all_drawings"], key="mapa_dibujo")
        dibujos = [v for v in map(vertices_de_geojson, (salida or {}).get("all_drawings") or [])
                   if v]
        if dibujos:
            contorno = dibujos[-1]          # si hay varios dibujos, se analiza el último
            if len(dibujos) > 1:
                st.caption("Hay varios dibujos: se analiza el último. Borra los demás con 🗑.")
    else:
        marcador = folium.FeatureGroup(name="terreno")
        # Enlace directo a un terreno (útil para la demo): …/?lat=-0.33&lon=-79.12
        if "punto" not in st.session_state and {"lat", "lon"} <= set(st.query_params):
            try:
                st.session_state["punto"] = (float(st.query_params["lat"]),
                                             float(st.query_params["lon"]))
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
    if modo == MODO_DIBUJO and not contorno:
        st.info("👈 Dibuja el contorno de tu terreno en el mapa para analizarlo.")
        st.stop()
    if modo == MODO_PUNTO and not punto:
        st.info("👈 Toca un punto del mapa para analizar ese terreno.")
        st.stop()

    lat, lon = centro_terreno(contorno) if contorno else punto
    if not en_ecuador(lat, lon):
        st.warning("Ese punto está fuera del Ecuador continental. Elige otro terreno.")
        st.stop()

    try:
        celda, c, clave_zona, celdas_contorno = datos_del_terreno(lat, lon, contorno)
    except Exception as error:  # noqa: BLE001
        st.error(f"No se pudo consultar el clima de NASA POWER. Revisa tu internet.\n\n{error}")
        st.stop()

    st.subheader("Tu terreno")
    if contorno:
        st.caption(f"Terreno dibujado · centro en latitud {lat:.4f}, longitud {lon:.4f}")
        st.metric("Tamaño de tu terreno", area_texto(contorno))
        if celdas_contorno is not None and len(celdas_contorno) > 1:
            st.caption(f"Se promediaron {len(celdas_contorno)} cuadros del mapa de ~250 m "
                       "que caen dentro de tu terreno.")
        elif celdas_contorno is not None:
            st.caption("Tu terreno es más pequeño que un cuadro del mapa (~250 m, unas 6 ha): "
                       "se usan los datos del cuadro donde está.")
    else:
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
            if celdas_contorno is not None and len(celdas_contorno) > 1:
                con_agua = (celdas_contorno["encharcamiento"] >= AGUA_VISIBLE).mean()
                st.caption(f"El radar vio agua acumulada en el {con_agua:.0%} de tu terreno "
                           "en alguna de sus pasadas.")
            # Serie del radar: lo que vio en cada pasada sobre este terreno
            numeros = (celdas_contorno["celda"].tolist() if celdas_contorno is not None
                       else [int(celda["celda"])])
            series = (series_radar(clave_zona, ruta_serie(clave_zona).stat().st_mtime)
                      if ruta_serie(clave_zona).exists() else None)
            serie = serie_del_terreno(series, numeros) if series else None
            if serie is not None:
                with st.expander("📈 Ver lo que vio el radar en cada pasada"):
                    tema = getattr(getattr(st.context, "theme", None), "type", None) or "light"
                    for columna, (titulo, ayuda) in GRAFICOS_RADAR.items():
                        datos = (serie[columna] * 100).dropna() if columna in serie else None
                        if datos is None or datos.empty:
                            continue
                        st.markdown(f"**{titulo}**")
                        st.line_chart(datos.rename("valor"), height=170,
                                      x_label="Fecha de la pasada",
                                      color=COLOR_LINEA.get(tema, COLOR_LINEA["light"]))
                        st.caption(ayuda)
        else:
            st.caption("Este punto queda fuera de la franja que cubre el radar en esta órbita.")

    provincias = sorted(CAPITALES)
    sugerida = provincia_sugerida(lat, lon)
    provincia = st.selectbox("Provincia (para el mercado)", provincias,
                             index=provincias.index(sugerida), key=f"prov_{lat}_{lon}",
                             help="Se sugiere la más cercana; corrígela si no es la tuya.")

    # Dos preguntas sencillas al agricultor. No dependen del terreno elegido: se conservan.
    riego = st.radio("¿Tienes riego en tu terreno?", [RIEGO_NO, RIEGO_SI], horizontal=True,
                     key="riego",
                     help="Con riego, la falta de lluvia resta menos puntos, pero no desaparece: "
                          "mientras más agua haya que regar, menos puntos. El riego no cambia "
                          "el clima, la pendiente ni las inundaciones.") == RIEGO_SI
    preferencia = PREFERENCIAS[st.radio(
        "¿Qué buscas?", list(PREFERENCIAS), horizontal=True, key="preferencia",
        help="No cambia el puntaje. Solo decide el orden cuando varios cultivos empatan.")]
    celda["riego"] = riego

    todos = evaluar_todos(celda, provincia, preferencia=preferencia)
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
            if cultivo.get("tiempo_texto"):
                st.markdown(f"⏱️ {cultivo['tiempo_texto']}")
            with st.expander("¿Por qué?", expanded=(i == 1)):
                for f in cultivo["factores"]:
                    icono = "•" if f["nota"] is None else "✅" if f["nota"] >= 1 else \
                            "⚠️" if f["nota"] > 0 else "❌"
                    st.markdown(f"{icono} {f['texto']}")
                if cultivo.get("suelo"):
                    st.markdown(f"🧪 **Suelo que prefiere:** {cultivo['suelo']['texto']}")
                    st.caption(f"Dato de referencia: la app todavía no mide el suelo de tu terreno, "
                               f"así que no cuenta en el puntaje. Fuente: {cultivo['suelo']['fuente']}")

    # Empates: se avisa cuáles otros cultivos tienen la misma aptitud que el tercero
    iguales = empatados(todos) if len(mejores) == 3 else []
    if iguales:
        st.info(f"**Con la misma aptitud ({mejores[-1]['puntaje']:.0f}/100) también están:** "
                + ", ".join(x["nombre"] for x in iguales)
                + ". Cuando varios cultivos empatan, se ordenan según lo que elegiste en "
                  "\"¿Qué buscas?\". Compara sus tiempos en la tabla de abajo.")

    # Terreno grande: no todo el terreno es igual, se muestra qué conviene en cada parte
    if celdas_contorno is not None and len(celdas_contorno) > 1:
        reparto = reparto_mejor_cultivo(celdas_contorno, riego=riego, preferencia=preferencia)
        if len(reparto) > 1:
            st.subheader("Tu terreno no es igual en todas partes")
            st.caption("Mejor cultivo en cada parte del terreno, mirando cuadro por cuadro:")
            for r in reparto:
                nombre = ("Ningún cultivo de la lista alcanza la aptitud mínima"
                          if r["cultivo"] == "ninguno" else r["nombre"])
                st.markdown(f"- **{r['fraccion']:.0%} del terreno:** {nombre}")

# --- Tabla completa ---------------------------------------------------------
with st.expander("Ver todos los cultivos evaluados"):
    st.dataframe(
        pd.DataFrame([{"Cultivo": x["nombre"], "Aptitud": x["puntaje"],
                       "Primera cosecha (meses)": x["meses"],
                       "Tipo": str(x["tipo"]).replace("_", " "),
                       "Mercado": ETIQUETAS[x["mercado"]]} for x in todos]),
        hide_index=True, use_container_width=True,
        column_config={
            "Aptitud": st.column_config.ProgressColumn(
                "Aptitud (0–100)", min_value=0, max_value=100, format="%.0f"),
            "Primera cosecha (meses)": st.column_config.NumberColumn(format="%d")},
    )

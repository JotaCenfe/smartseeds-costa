"""
Prueba rápida de la lógica (sin internet y sin datos descargados).

    python tests/prueba_rapida.py

Usa terrenos y matrices INVENTADOS solo para comprobar que las fórmulas se
comportan como se espera. No son datos del proyecto.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import nisar, terreno  # noqa: E402
from src.aptitud import aptitud, cargar_requisitos  # noqa: E402
from src.clima_relieve import corregir_temp_por_altura, nombre_tile, pendiente_grados  # noqa: E402
from src.config import provincia_sugerida, zona_de_punto  # noqa: E402
from src.mercado import clasificar, mercado  # noqa: E402
from src.recomendar import (empatados, evaluar_todos, recomendar, reparto_mejor_cultivo,  # noqa: E402
                            suelo_detalle, tiempo_texto)

req = cargar_requisitos().set_index("cultivo")

# --- Aptitud: un terreno de Costa y uno de Sierra ---------------------------
costa = {"altura": 420, "pendiente": 4, "temp": 24.3, "lluvia": 1560,
         "humedad": None, "encharcamiento": None, "vegetacion": None}
sierra = {"altura": 3000, "pendiente": 8, "temp": 12.0, "lluvia": 900,
          "humedad": None, "encharcamiento": None, "vegetacion": None}

assert aptitud(costa, req.loc["cacao"].to_dict()) == 100
assert aptitud(costa, req.loc["papa"].to_dict()) < 40
assert aptitud(sierra, req.loc["papa"].to_dict()) == 100
assert aptitud(sierra, req.loc["cacao"].to_dict()) < 40
assert aptitud({}, req.loc["cacao"].to_dict()) is None            # sin datos -> sin puntaje

# El encharcamiento castiga al cacao pero no al arroz
inundado = dict(costa, encharcamiento=0.5, pendiente=1)
assert aptitud(inundado, req.loc["cacao"].to_dict()) < aptitud(costa, req.loc["cacao"].to_dict())
assert aptitud(inundado, req.loc["arroz"].to_dict()) == 100

# La humedad poco confiable (vegetación densa) se informa pero no cambia el puntaje
mojado = dict(costa, humedad=0.95)
assert aptitud(dict(mojado, humedad_confiable=0.9), req.loc["cacao"].to_dict()) < 100
assert aptitud(dict(mojado, humedad_confiable=0.1), req.loc["cacao"].to_dict()) == 100

top = recomendar(costa, "Santo Domingo de los Tsáchilas")
assert len(top) == 3 and all(c["puntaje"] >= 40 for c in top)
assert not {"papa", "quinua", "haba"} & {c["cultivo"] for c in top}

# --- Riego: reduce la falta de agua, pero no la borra ni arregla otras cosas ---
seco = {"altura": 5, "pendiente": 2, "temp": 27.7, "lluvia": 770,           # como Daule
        "humedad": None, "encharcamiento": None, "vegetacion": None}
regado = dict(seco, riego=True)
for nombre in ("arroz", "banano", "cacao"):
    c = req.loc[nombre].to_dict()
    assert aptitud(seco, c) < aptitud(regado, c) < 100                       # mejora, pero no llega a 100
assert aptitud(regado, req.loc["arroz"].to_dict()) > aptitud(regado, req.loc["banano"].to_dict())  # falta menos agua
assert aptitud(regado, req.loc["maiz_duro"].to_dict()) == aptitud(seco, req.loc["maiz_duro"].to_dict()) == 100
assert aptitud(dict(costa, riego=True), req.loc["cacao"].to_dict()) == 100   # si llueve bastante, no cambia nada
assert aptitud(dict(sierra, riego=True), req.loc["cacao"].to_dict()) < 40    # el riego no quita el frío
assert aptitud(dict(inundado, riego=True), req.loc["cacao"].to_dict()) ==     aptitud(inundado, req.loc["cacao"].to_dict())                            # ni la inundación

# Si el radar vio agua en el terreno, al arroz no se le dice que "se seca rápido"
arrozal = dict(costa, pendiente=1, encharcamiento=0.37, humedad=0.25, humedad_confiable=0.9)
assert aptitud(arrozal, req.loc["arroz"].to_dict()) == 100

# --- Empates: el orden depende de lo que prefiere el agricultor, no de la tabla ---
pronto = evaluar_todos(costa, "Guayas", preferencia="pronto")
largo = evaluar_todos(costa, "Guayas", preferencia="largo")
assert [c["cultivo"] for c in pronto[:3]] == ["maiz_duro", "arroz", "maracuya"]      # 4, 4 y 8 meses
assert [c["cultivo"] for c in largo[:3]] == ["banano", "platano", "cafe_robusta"]    # permanentes primero
assert {c["cultivo"]: c["puntaje"] for c in pronto} == {c["cultivo"]: c["puntaje"] for c in largo}
assert {"cacao", "banano"} <= {c["cultivo"] for c in empatados(pronto)}              # empatados fuera del top 3
assert "4 meses" in tiempo_texto(req.loc["maiz_duro"].to_dict())
assert "3 años" in tiempo_texto(req.loc["cacao"].to_dict()) and tiempo_texto({}) is None

# --- Suelo (catálogo del equipo): se informa, pero no cambia el puntaje -------
suelo_cacao = suelo_detalle("cacao")
assert suelo_cacao and "pH entre 6 y 7" in suelo_cacao["texto"] and "Agrocalidad" in suelo_cacao["fuente"]
assert "pH" not in suelo_detalle("papa")["texto"]                  # pH de la papa: pendiente en el catálogo
assert suelo_detalle("banano") is None                             # no está en el catálogo -> sin dato
assert any(c["suelo"] for c in pronto if c["cultivo"] == "cacao")

# --- Mercado ----------------------------------------------------------------
assert clasificar(15, -3) == "saturado"
assert clasificar(2, 8) == "alta"
assert clasificar(2, 1) == "media"
assert mercado("cultivo_que_no_existe", "Guayas") == "sin_datos"

# --- Clima y relieve --------------------------------------------------------
assert abs(corregir_temp_por_altura(24.0, 500, 1500) - 17.5) < 1e-6   # 1000 m más alto = 6,5 °C menos
assert nombre_tile(-1, -80) == "s01w080" and nombre_tile(0, -79) == "n00w079"
plano = np.zeros((20, 20), dtype="float32")
rampa = np.tile(np.arange(20, dtype="float32") * 30.87, (20, 1)).T    # sube ~45° de fila en fila
assert pendiente_grados(plano, 0).max() == 0
assert abs(pendiente_grados(rampa, 0)[10, 10] - 45) < 0.5

# --- Zonas ------------------------------------------------------------------
assert zona_de_punto(-0.25, -79.2) == "santo_domingo"
assert zona_de_punto(-1.85, -79.85) == "daule"
assert zona_de_punto(-2.9, -79.0) is None
assert provincia_sugerida(-2.19, -79.9) == "Guayas"

# --- Terreno dibujado (contorno) --------------------------------------------
# Cuadrado de 0,01° x 0,01° en el ecuador: ~1112 m de lado -> ~123,6 hectáreas
cuadrado = [(-79.20, -0.01), (-79.19, -0.01), (-79.19, 0.0), (-79.20, 0.0)]
assert abs(terreno.area_m2(cuadrado) / 10_000 - 123.6) < 0.5
assert terreno.area_texto(cuadrado).endswith("cuadras)")
assert terreno.dentro([-79.195, -79.185], [-0.005, -0.005], cuadrado).tolist() == [True, False]
ele = [(0, 0), (2, 0), (2, 1), (1, 1), (1, 2), (0, 2)]              # terreno irregular en forma de L
assert terreno.dentro([0.5, 1.5, 1.5], [1.5, 0.5, 1.5], ele).tolist() == [True, True, False]
geo = {"geometry": {"type": "Polygon", "coordinates": [[[p[0], p[1]] for p in cuadrado + cuadrado[:1]]]}}
assert terreno.vertices_de_geojson(geo) == cuadrado
assert terreno.vertices_de_geojson({"geometry": {"type": "Point", "coordinates": [0, 0]}}) is None
tabla_inv = pd.DataFrame({"celda": [0, 1, 2], "lat": [-0.005, -0.006, -0.5], "lon": [-79.195, -79.194, -79.195],
                          "altura": [400.0, 440.0, 900.0], "pendiente": [2.0, 6.0, 30.0],
                          "temp": [24.0, 24.0, 20.0], "lluvia": [1560, 1560, 1560],
                          "humedad": [np.nan, np.nan, np.nan], "encharcamiento": [0.5, 0.0, 0.0],
                          "vegetacion": [0.5, 0.7, 0.9]})
adentro = terreno.celdas_del_terreno(tabla_inv, cuadrado)
assert adentro["celda"].tolist() == [0, 1]                           # la celda lejana queda fuera
prom = terreno.celda_promedio(adentro, cuadrado)
assert prom["altura"] == 420 and prom["encharcamiento"] == 0.25 and prom["humedad"] is None
chico = [(-79.3001, -0.4001), (-79.3000, -0.4001), (-79.3000, -0.4000)]   # más pequeño que una celda
assert len(terreno.celdas_del_terreno(tabla_inv, chico)) == 1        # usa la celda más cercana
partes = reparto_mejor_cultivo(adentro)
assert {p["cultivo"] for p in partes} == {"arroz", "maiz_duro"}      # la mitad inundada -> arroz
assert {p["cultivo"] for p in reparto_mejor_cultivo(adentro, preferencia="largo")} == {"arroz", "banano"}
assert abs(sum(p["fraccion"] for p in partes) - 1) < 1e-9

# --- Capas NISAR con matrices de prueba -------------------------------------
hh = np.full((4, 3, 3), 0.10, dtype="float32")     # 4 fechas, 3x3 píxeles, -10 dB
hv = np.full((4, 3, 3), 0.02, dtype="float32")
hh[:2, 0, 0] = 0.005                                # un píxel con agua en 2 de 4 fechas (-23 dB)
ench = nisar.capa_encharcamiento(hh)
assert ench[0, 0] == 0.5 and ench[1, 1] == 0
veg = nisar.capa_vegetacion(hh, hv)
assert abs(veg[1, 1] - 4 * 0.02 / 0.12) < 1e-5
rel = nisar.humedad_relativa(hh)
assert rel[0, 0, 0] == 0 and rel[3, 0, 0] == 1      # seco al inicio, húmedo al final
assert abs(nisar.a_db(np.array([0.1]))[0] + 10) < 1e-5

# Serie del radar de un terreno (lo que dibuja el gráfico de la app): 4 fechas, rejilla 3x3
agua = np.zeros((4, 3, 3), dtype="float32")
agua[:2, 0, 0] = 1.0                                # la celda 0 estuvo cubierta de agua 2 fechas
series = {"fechas": ["2026-06-21", "2026-07-03", "2026-07-15", "2026-07-27"],
          "hh": hh, "hv": hv, "agua": agua,
          "fechas_humedad": ["2026-06-21", "2026-07-03"],
          "sm": np.full((2, 3, 3), 0.25, dtype="float32")}
st0 = nisar.serie_del_terreno(series, [0])
assert st0["agua"].tolist() == [1, 1, 0, 0]
assert st0["vegetacion"].isna().tolist() == [True, True, False, False]   # sobre el agua no vale
assert st0["humedad"].iloc[0] == 0.5 and st0["humedad"].isna().sum() == 2   # 0,25 m³/m³ = 50 %
st2 = nisar.serie_del_terreno(series, [0, 4])       # terreno dibujado: promedio de 2 celdas
assert st2["agua"].tolist() == [0.5, 0.5, 0, 0]
vacio = dict(series, hh=np.full_like(hh, np.nan), hv=np.full_like(hv, np.nan))
assert nisar.serie_del_terreno(vacio, [0]) is None  # fuera de la franja del radar

print("TODO BIEN: aptitud, riego, empates, suelo, mercado, clima/relieve, zonas, terreno dibujado y capas NISAR.")

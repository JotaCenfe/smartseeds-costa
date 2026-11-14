"""
Prueba rápida de la lógica (sin internet y sin datos descargados).

    python tests/prueba_rapida.py

Usa terrenos y matrices INVENTADOS solo para comprobar que las fórmulas se
comportan como se espera. No son datos del proyecto.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import nisar  # noqa: E402
from src.aptitud import aptitud, cargar_requisitos  # noqa: E402
from src.clima_relieve import corregir_temp_por_altura, nombre_tile, pendiente_grados  # noqa: E402
from src.config import provincia_sugerida, zona_de_punto  # noqa: E402
from src.mercado import clasificar, mercado  # noqa: E402
from src.recomendar import recomendar  # noqa: E402

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
assert zona_de_punto(-2.9, -79.0) is None
assert provincia_sugerida(-2.19, -79.9) == "Guayas"

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

print("TODO BIEN: aptitud, mercado, clima/relieve, zonas y capas NISAR.")

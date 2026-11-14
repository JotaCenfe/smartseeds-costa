"""
Indicador de mercado: ¿conviene sembrar este cultivo según la oferta y el precio?

Contrato:  mercado(cultivo, provincia) -> "alta" / "media" / "saturado"
           (o "sin_datos" mientras la tabla no tenga ese cultivo)

Lee tablas/mercado.csv, que llena quien investiga ESPAC (INEC) y precios (MAG-SIPA):

    cultivo, provincia, var_superficie_pct, var_precio_pct, periodo, fuente, notas

  var_superficie_pct  cambio de la superficie sembrada en el periodo (%, ESPAC)
  var_precio_pct      cambio del precio al productor en el periodo (%, SIPA)
  provincia           nombre de la provincia, o "nacional" como valor general

Regla inicial (cambiar los umbrales aquí cuando el equipo los acuerde):
  saturado  la superficie creció más de 10 % Y el precio bajó
  alta      el precio subió más de 5 % Y la superficie no creció más de 10 %
  media     todo lo demás
"""
from __future__ import annotations

import pandas as pd

from .config import TABLAS

UMBRAL_SUPERFICIE_PCT = 10.0
UMBRAL_PRECIO_PCT = 5.0

ETIQUETAS = {
    "alta": "Oportunidad alta",
    "media": "Oportunidad media",
    "saturado": "Mercado saturado",
    "sin_datos": "Mercado: sin datos todavía",
}


def cargar_mercado(ruta=None) -> pd.DataFrame:
    ruta = ruta or TABLAS / "mercado.csv"
    if not ruta.exists():
        return pd.DataFrame(columns=["cultivo", "provincia", "var_superficie_pct",
                                     "var_precio_pct", "periodo", "fuente", "notas"])
    return pd.read_csv(ruta)


def clasificar(var_superficie_pct: float, var_precio_pct: float) -> str:
    """Aplica la regla a un par de variaciones (%)."""
    if var_superficie_pct > UMBRAL_SUPERFICIE_PCT and var_precio_pct < 0:
        return "saturado"
    if var_precio_pct > UMBRAL_PRECIO_PCT and var_superficie_pct <= UMBRAL_SUPERFICIE_PCT:
        return "alta"
    return "media"


def mercado_detalle(cultivo: str, provincia: str, tabla: pd.DataFrame | None = None) -> dict:
    """Devuelve {"nivel", "texto"} para un cultivo en una provincia."""
    tabla = cargar_mercado() if tabla is None else tabla
    filas = tabla[tabla["cultivo"].astype(str).str.lower() == str(cultivo).lower()]
    prov = filas[filas["provincia"].astype(str).str.lower() == str(provincia).lower()]
    if prov.empty:   # si no hay dato de la provincia, se usa el nacional
        prov = filas[filas["provincia"].astype(str).str.lower() == "nacional"]
    prov = prov.dropna(subset=["var_superficie_pct", "var_precio_pct"])
    if prov.empty:
        return {"nivel": "sin_datos", "texto": "Todavía no hay datos de mercado para este cultivo."}
    f = prov.iloc[0]
    sup, pre = float(f["var_superficie_pct"]), float(f["var_precio_pct"])
    nivel = clasificar(sup, pre)
    ambito = f["provincia"] if str(f["provincia"]).lower() != "nacional" else "el país"
    texto = (f"En {ambito} la superficie sembrada cambió {sup:+.0f} % y el precio "
             f"{pre:+.0f} % ({f.get('periodo', '')}; {f.get('fuente', '')}).")
    return {"nivel": nivel, "texto": texto}


def mercado(cultivo: str, provincia: str) -> str:
    return mercado_detalle(cultivo, provincia)["nivel"]

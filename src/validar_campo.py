"""
Validación con datos de campo: ¿la app recomienda lo que de verdad se siembra?

El MAG (proyecto SIGTIERRAS) visitó terrenos en 2014–2015 y anotó qué había sembrado en cada
punto. Aquí se compara eso con el puntaje que la app da HOY a ese mismo cultivo en ese sitio.

    python -m src.validar_campo ZONA descargar   # puntos de la zona -> datos/crudos/cultivos_mag/ZONA/
    python -m src.validar_campo ZONA medir       # imprime y guarda datos/procesados/validacion_campo_ZONA.json

Qué responde: de los terrenos donde un agricultor tenía cacao (o arroz, plátano…), ¿en cuántos
la app considera apto ese cultivo y en cuántos lo pone entre sus tres primeros?

Límites que hay que declarar:
  - Los puntos son de 2014–2015 y el radar de 2026.
  - Que un cultivo esté sembrado no prueba que sea la mejor opción; solo que es viable ahí.
  - Solo entran los cultivos que la app evalúa (tablas/requisitos_cultivos.csv).

Fuente: MAG – SIGTIERRAS, "Datos de campo Cobertura y Uso de la Tierra 1:25.000", geoservicio
http://geoportal.agricultura.gob.ec/sigtierras/cobertura_tierra/wfs
"""
from __future__ import annotations

import json
import sys
import unicodedata
from collections import Counter

import pandas as pd
import requests

from .clima_relieve import cargar_celdas, celda_mas_cercana
from .config import DATOS_CRUDOS, DATOS_PROCESADOS, ZONAS
from .recomendar import PUNTAJE_MINIMO, evaluar_todos
from .suelo_lluvia import cargar_lluvia_mensual, lluvia_mensual_de

WFS = "http://geoportal.agricultura.gob.ec/sigtierras/cobertura_tierra/wfs"
CAPA = "cobertura_tierra:vw_datos_campo_cobertura_uso_tierra"

# Nombre que anotó el MAG -> clave del cultivo en la app
EQUIVALENCIAS = {"PLATANO": "platano", "CACAO": "cacao", "YUCA": "yuca", "BANANO": "banano",
                 "MAIZ DURO": "maiz_duro", "MARACUYA": "maracuya", "PALMA AFRICANA": "palma_aceitera",
                 "PINA": "pina", "ARROZ": "arroz", "PAPA": "papa", "MAIZ SUAVE": "maiz_suave",
                 "HABA": "haba", "QUINUA": "quinua", "TOMATE DE ARBOL": "tomate_de_arbol"}


def _sin_tildes(texto) -> str:
    limpio = unicodedata.normalize("NFD", str(texto))
    limpio = "".join(c for c in limpio if unicodedata.category(c) != "Mn").upper()
    return " ".join(limpio.split())


def ruta_puntos(clave_zona: str):
    return DATOS_CRUDOS / "cultivos_mag" / clave_zona / "puntos_campo_sigtierras.geojson"


def descargar(clave_zona: str) -> None:
    a, b, c, d = ZONAS[clave_zona]["recuadro"]
    r = requests.get(WFS, timeout=300, params={
        "service": "WFS", "version": "1.1.0", "request": "GetFeature", "typeName": CAPA,
        "outputFormat": "application/json", "srsName": "EPSG:4326",
        "bbox": f"{a},{b},{c},{d},EPSG:4326", "maxFeatures": 20000})
    r.raise_for_status()
    # Se guarda solo lo necesario: sin responsables ni rutas de fotos
    limpio = [{"type": "Feature", "geometry": f["geometry"],
               "properties": {k: f["properties"].get(k) for k in
                              ("fechauctie", "clase", "tipo1", "cobertura1", "tipo2", "cobertura2", "riego")}}
              for f in r.json()["features"]]
    ruta = ruta_puntos(clave_zona)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps({"type": "FeatureCollection", "features": limpio}, ensure_ascii=False),
                    encoding="utf-8")
    print(f"{len(limpio)} puntos -> {ruta}")


def medir(clave_zona: str) -> dict:
    puntos = json.loads(ruta_puntos(clave_zona).read_text(encoding="utf-8"))["features"]
    celdas = cargar_celdas(clave_zona)
    if celdas is None or celdas.empty:
        raise ValueError(f"Falta la tabla de celdas procesadas para {clave_zona}.")
    mensual = cargar_lluvia_mensual(clave_zona)
    zona = ZONAS[clave_zona]
    provincia = zona["provincia"]
    oeste, sur, este, norte = zona["recuadro"]
    filas = []
    sin_equivalencia = Counter()
    fuera_de_la_zona = 0
    sin_puntaje = 0
    for p in puntos:
        lon, lat = p["geometry"]["coordinates"][:2]
        if not (oeste <= lon <= este and sur <= lat <= norte):
            fuera_de_la_zona += 1
            continue
        etiqueta = _sin_tildes(p["properties"].get("cobertura1") or "Sin etiqueta")
        cultivo = EQUIVALENCIAS.get(etiqueta)
        if cultivo is None:
            sin_equivalencia[etiqueta] += 1
            continue
        celda = celda_mas_cercana(celdas, lat, lon)
        if mensual is not None:
            celda["lluvia_mensual"] = lluvia_mensual_de(mensual, celda["celda"])
        orden = evaluar_todos(celda, provincia)
        puesto = next((i for i, c in enumerate(orden, start=1) if c["cultivo"] == cultivo), None)
        if puesto is None:
            sin_puntaje += 1
            continue
        elegibles = [c["cultivo"] for c in orden if c["puntaje"] >= PUNTAJE_MINIMO]
        filas.append({"cultivo": cultivo, "puntaje": orden[puesto - 1]["puntaje"],
                      "en_top_3": cultivo in elegibles[:3], "es_primero": cultivo in elegibles[:1],
                      "primero": elegibles[0] if elegibles else None})
    t = pd.DataFrame(filas, columns=["cultivo", "puntaje", "en_top_3", "es_primero", "primero"])

    def resumen(g: pd.DataFrame) -> dict:
        if g.empty:
            return {"puntos": 0, "puntaje_mediano": None, "apto_para_la_app": None,
                    "puntaje_70_o_mas": None, "entre_los_3_primeros": None, "es_el_primero": None}
        return {"puntos": int(len(g)),
                "puntaje_mediano": round(float(g["puntaje"].median()), 1),
                "apto_para_la_app": round(float((g["puntaje"] >= PUNTAJE_MINIMO).mean()), 3),
                "puntaje_70_o_mas": round(float((g["puntaje"] >= 70).mean()), 3),
                "entre_los_3_primeros": round(float(g["en_top_3"].mean()), 3),
                "es_el_primero": round(float(g["es_primero"].mean()), 3)}

    resultado = {"zona": clave_zona, "fuente": "MAG – SIGTIERRAS, datos de campo 2014–2015",
                 "puntos_recibidos": len(puntos), "fuera_de_la_zona": fuera_de_la_zona,
                 "sin_puntaje": sin_puntaje, "sin_equivalencia": dict(sin_equivalencia.most_common()),
                 "riego_asumido": False,
                 "todos": resumen(t),
                 "por_cultivo": {c: resumen(g) for c, g in t.groupby("cultivo") if len(g) >= 10},
                 "lo_que_la_app_pone_primero": t["primero"].value_counts().head(5).to_dict()}
    (DATOS_PROCESADOS / f"validacion_campo_{clave_zona}.json").write_text(
        json.dumps(resultado, ensure_ascii=False, indent=1), encoding="utf-8")

    r = resultado["todos"]
    print(f"\n[{clave_zona}] {r['puntos']} terrenos visitados con un cultivo que la app evalúa")
    print(f"   puntos recibidos: {len(puntos)} | fuera de la zona: {fuera_de_la_zona} | "
          f"sin equivalencia: {sum(sin_equivalencia.values())} | sin puntaje: {sin_puntaje}")
    if not r["puntos"]:
        print("   Sin puntos evaluables. Consulta las etiquetas de campo en el JSON generado.")
        return resultado
    print(f"   la app lo considera apto (≥ {PUNTAJE_MINIMO}): {r['apto_para_la_app']:.0%} | puntaje ≥ 70: "
          f"{r['puntaje_70_o_mas']:.0%} | entre los 3 primeros: {r['entre_los_3_primeros']:.0%} | "
          f"puntaje mediano {r['puntaje_mediano']}")
    for c, d in sorted(resultado["por_cultivo"].items(), key=lambda par: -par[1]["puntos"]):
        print(f"   {c:15s} {d['puntos']:4d} puntos | apto {d['apto_para_la_app']:.0%} | ≥ 70: "
              f"{d['puntaje_70_o_mas']:.0%} | top 3: {d['entre_los_3_primeros']:.0%} | mediano {d['puntaje_mediano']}")
    print("   lo que la app pone primero en esos terrenos:", resultado["lo_que_la_app_pone_primero"])
    return resultado


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] not in ZONAS:
        print("Uso: python -m src.validar_campo ZONA [descargar|medir]   Zonas:", ", ".join(ZONAS))
        sys.exit(1)
    descargar(sys.argv[1]) if sys.argv[2] == "descargar" else medir(sys.argv[1])

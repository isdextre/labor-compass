# -*- coding: utf-8 -*-
"""
api.py
PRÓXIMO — Machine Learning Engineer

API Flask que expone los 4 endpoints del rol:
  POST /api/industria_siguiente
  POST /api/probabilidad_exito
  POST /api/timeline
  POST /api/skills_faltantes

Corre con:  python api.py   (por defecto en http://localhost:5000)

Ejemplo rápido con curl:
  curl -X POST http://localhost:5000/api/industria_siguiente \
       -H "Content-Type: application/json" \
       -d '{"industria_actual": "Construcción", "region": "Total"}'
"""
from __future__ import annotations

import os

from flask import Flask, jsonify, request

from data_utils import (
    cargar_catalogo_inei,
    cargar_cursos,
    cargar_cv_ejemplos,
    cargar_industrias_especificas_demo,
    cargar_skills_por_ocupacion,
    industria_especifica_de_ocupacion,
    rama_de_ocupacion,
)
from modelo_tendencias import industria_siguiente as _industria_siguiente
from modelo_tendencias import obtener_tendencia
from modelo_reconversion import (
    cargar_modelo,
    predecir_probabilidad_exito,
    skills_faltantes as _skills_faltantes,
    timeline_estimado as _timeline_estimado,
)

BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")

app = Flask(__name__)

# --- Estado cargado una sola vez al iniciar el servidor ---
CATALOGO = cargar_catalogo_inei(DATA_DIR)
SKILLS_MAPPING = cargar_skills_por_ocupacion(os.path.join(DATA_DIR, "skills_por_ocupacion.json"))
CURSOS = cargar_cursos(os.path.join(DATA_DIR, "cursos.json"))
CV_EJEMPLOS = {c["user_id"]: c for c in cargar_cv_ejemplos(os.path.join(DATA_DIR, "cv_ejemplos.json"))}
TERRITORIO_DEMO = cargar_industrias_especificas_demo(os.path.join(DATA_DIR, "territorio_demo.json"))
MODELO_RF = cargar_modelo()


def _tendencia_para(nombre_original: str, rama: str, region: str) -> dict:
    """
    Intenta primero una industria ESPECÍFICA (ej. 'Minería', 'Energía solar')
    usando territorio_demo.json (dato demostrativo, no ARIMA); si no aplica,
    cae al modelo de tendencias real por rama INEI (ARIMA/fallback lineal).
    """
    industria_especifica = industria_especifica_de_ocupacion(nombre_original)
    region_match = next((r for r in TERRITORIO_DEMO if r.lower() == str(region).lower()), None)

    if industria_especifica and region_match and industria_especifica in TERRITORIO_DEMO[region_match]:
        variacion = TERRITORIO_DEMO[region_match][industria_especifica]
        clasificacion = "creciente" if variacion > 5 else ("decreciente" if variacion < -5 else "estable")
        return {
            "region": region_match,
            "industria": industria_especifica,
            "metrica": "variacion_pct_demo",
            "metodo": "dato_demostrativo (territorio_demo.json, no ARIMA — INEI no desagrega esta industria)",
            "variacion_proyectada_pct": variacion,
            "clasificacion": clasificacion,
        }

    return obtener_tendencia(region, rama, CATALOGO, metrica="salarios")


def _error(mensaje: str, codigo: int = 400):
    return jsonify({"error": mensaje}), codigo


@app.get("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "series_inei_cargadas": len(CATALOGO),
        "ocupaciones_con_skills": len(SKILLS_MAPPING),
        "cursos_cargados": len(CURSOS),
    })


# ---------------------------------------------------------------------------
# 1) industria_siguiente
# ---------------------------------------------------------------------------
@app.post("/api/industria_siguiente")
def industria_siguiente():
    """
    Body JSON:
      {
        "industria_actual": "Construcción",   // rama INEI, u ocupación (ver nota)
        "region": "Total",                     // opcional, default "Total"
        "metrica": "salarios",                 // opcional: "salarios" | "poblacion_miles"
        "top_n": 3                             // opcional
      }
    Si "industria_actual" no es una rama INEI sino una ocupación puntual
    (ej. "Mining Maintenance Technician"), se traduce automáticamente a su
    rama vía el mapeo interno OCUPACION_A_RAMA.
    """
    body = request.get_json(silent=True) or {}
    industria_actual = body.get("industria_actual")
    if not industria_actual:
        return _error("Falta 'industria_actual' en el body.")

    # si mandaron una ocupación puntual, la traducimos a rama INEI
    industria_actual = rama_de_ocupacion(industria_actual) or industria_actual

    region = body.get("region", "Total")
    metrica = body.get("metrica", "salarios")
    top_n = int(body.get("top_n", 3))

    resultado = _industria_siguiente(
        CATALOGO, industria_actual, region_nombre=region, metrica=metrica, top_n=top_n
    )
    if not resultado:
        return _error(
            f"No hay datos suficientes para region='{region}', metrica='{metrica}'.", 404
        )
    return jsonify({"industria_actual": industria_actual, "region": region, "recomendaciones": resultado})


# ---------------------------------------------------------------------------
# 2) skills_faltantes
# ---------------------------------------------------------------------------
@app.post("/api/skills_faltantes")
def skills_faltantes():
    """
    Body JSON:
      {
        "ocupacion_destino": "Solar Energy Technician",
        "skills_actuales": ["Industrial Safety", "..."]   // o
        "user_id": "USER_006"                              // usa su CV parseado
      }
    """
    body = request.get_json(silent=True) or {}
    ocupacion_destino = body.get("ocupacion_destino")
    if not ocupacion_destino:
        return _error("Falta 'ocupacion_destino' en el body.")
    if ocupacion_destino not in SKILLS_MAPPING:
        return _error(f"Ocupación destino desconocida: '{ocupacion_destino}'.", 404)

    skills_actuales = body.get("skills_actuales")
    if skills_actuales is None:
        user_id = body.get("user_id")
        cv = CV_EJEMPLOS.get(user_id)
        if not cv:
            return _error("Debes enviar 'skills_actuales' o un 'user_id' válido.")
        skills_actuales = cv["skills_identificadas"]

    faltantes = _skills_faltantes(ocupacion_destino, skills_actuales, SKILLS_MAPPING)
    return jsonify({
        "ocupacion_destino": ocupacion_destino,
        "skills_requeridas": SKILLS_MAPPING[ocupacion_destino],
        "skills_actuales": skills_actuales,
        "skills_faltantes": faltantes,
    })


# ---------------------------------------------------------------------------
# 3) timeline
# ---------------------------------------------------------------------------
@app.post("/api/timeline")
def timeline():
    """
    Body JSON:
      {
        "ocupacion_destino": "Solar Energy Technician",
        "skills_actuales": [...],       // o "user_id"
        "horas_por_semana": 8           // opcional, default 8
      }
    """
    body = request.get_json(silent=True) or {}
    ocupacion_destino = body.get("ocupacion_destino")
    if not ocupacion_destino:
        return _error("Falta 'ocupacion_destino' en el body.")
    if ocupacion_destino not in SKILLS_MAPPING:
        return _error(f"Ocupación destino desconocida: '{ocupacion_destino}'.", 404)

    skills_actuales = body.get("skills_actuales")
    if skills_actuales is None:
        user_id = body.get("user_id")
        cv = CV_EJEMPLOS.get(user_id)
        if not cv:
            return _error("Debes enviar 'skills_actuales' o un 'user_id' válido.")
        skills_actuales = cv["skills_identificadas"]

    horas_por_semana = float(body.get("horas_por_semana", 8))
    faltantes = _skills_faltantes(ocupacion_destino, skills_actuales, SKILLS_MAPPING)
    resultado = _timeline_estimado(faltantes, CURSOS, horas_por_semana=horas_por_semana)
    resultado["ocupacion_destino"] = ocupacion_destino
    resultado["skills_faltantes"] = faltantes
    return jsonify(resultado)


# ---------------------------------------------------------------------------
# 4) probabilidad_exito
# ---------------------------------------------------------------------------
@app.post("/api/probabilidad_exito")
def probabilidad_exito():
    """
    Body JSON (mínimo):
      {
        "edad": 45,
        "años_experiencia": 8,
        "industria_actual": "Minería" | "Mining Maintenance Technician",
        "industria_destino": "Energía solar" | "Solar Energy Technician",
        "ocupacion_destino": "Solar Energy Technician",   // para calcular skills/timeline
        "skills_actuales": [...]  // o "user_id"
        "region": "Total"          // opcional
      }

    Internamente:
      1. Usa el modelo de tendencias (ARIMA) para estimar cómo viene la
         industria actual y la destino.
      2. Usa skills_faltantes + timeline para estimar la brecha real.
      3. Alimenta todo eso al Random Forest.
    """
    body = request.get_json(silent=True) or {}
    requeridos = ["edad", "años_experiencia", "industria_actual", "industria_destino", "ocupacion_destino"]
    faltan = [c for c in requeridos if c not in body]
    if faltan:
        return _error(f"Faltan campos obligatorios: {faltan}")

    cv = CV_EJEMPLOS.get(body.get("user_id"))
    # si no mandan región explícita, usamos la del CV (importante para poder
    # usar los datos demostrativos por región de territorio_demo.json)
    region = body.get("region") or (cv.get("ubicacion") if cv else "Total")

    rama_actual = rama_de_ocupacion(body["industria_actual"]) or body["industria_actual"]
    rama_destino = rama_de_ocupacion(body["industria_destino"]) or body["industria_destino"]

    tendencia_actual = _tendencia_para(body["industria_actual"], rama_actual, region)
    tendencia_destino = _tendencia_para(body["industria_destino"], rama_destino, region)

    variacion_actual = tendencia_actual.get("variacion_proyectada_pct", 0.0)
    variacion_destino = tendencia_destino.get("variacion_proyectada_pct", 0.0)

    ocupacion_destino = body["ocupacion_destino"]
    skills_actuales = body.get("skills_actuales")
    if skills_actuales is None:
        skills_actuales = cv["skills_identificadas"] if cv else []

    faltantes = _skills_faltantes(ocupacion_destino, skills_actuales, SKILLS_MAPPING)
    timeline_info = _timeline_estimado(faltantes, CURSOS, horas_por_semana=body.get("horas_por_semana", 8))
    timeline_meses = body.get("timeline_meses", timeline_info["meses_estimados"] or 1.0)

    probabilidad = predecir_probabilidad_exito(
        MODELO_RF,
        edad=float(body["edad"]),
        años_experiencia=float(body["años_experiencia"]),
        tendencia_industria_actual_pct=variacion_actual,
        tendencia_industria_destino_pct=variacion_destino,
        n_skills_faltantes=len(faltantes),
        timeline_meses=timeline_meses,
    )

    return jsonify({
        "probabilidad_exito": round(probabilidad, 3),
        "probabilidad_exito_pct": round(probabilidad * 100, 1),
        "detalle": {
            "tendencia_industria_actual": tendencia_actual,
            "tendencia_industria_destino": tendencia_destino,
            "skills_faltantes": faltantes,
            "timeline_estimado_meses": timeline_meses,
        },
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)

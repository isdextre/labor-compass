# -*- coding: utf-8 -*-
"""
modelo_reconversion.py
PRÓXIMO — Machine Learning Engineer
"""
from __future__ import annotations

import os
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

from data_utils import cargar_cursos, cargar_skills_por_ocupacion

RUTA_MODELO_DEFAULT = os.path.join(os.path.dirname(__file__), "rf_reconversion.joblib")

# Features, en el orden en que entran al Random Forest.
FEATURES = [
    "edad",
    "años_experiencia",
    "tendencia_industria_actual_pct",   # variación proyectada de la industria actual (ARIMA)
    "tendencia_industria_destino_pct",  # variación proyectada de la industria destino (ARIMA)
    "n_skills_faltantes",
    "timeline_meses",
]


# ---------------------------------------------------------------------------
# 1) skills_faltantes
# ---------------------------------------------------------------------------

def skills_faltantes(
    ocupacion_destino: str,
    skills_actuales: list,
    skills_mapping: dict,
) -> list:
    """
    Devuelve las skills que pide `ocupacion_destino` y el candidato todavía no tiene.
    `skills_actuales` puede venir del CV parseado (cv_ejemplos.json) o de un
    perfil ingresado a mano.
    """
    requeridas = skills_mapping.get(ocupacion_destino, [])
    actuales_norm = {s.strip().lower() for s in skills_actuales}
    return [s for s in requeridas if s.strip().lower() not in actuales_norm]


# ---------------------------------------------------------------------------
# 2) timeline: cuánto toma cerrar la brecha de skills
# ---------------------------------------------------------------------------

def timeline_estimado(
    faltantes: list,
    cursos: list,
    horas_por_semana: float = 8.0,
) -> dict:
    """
    Cubre cada skill faltante con el curso más corto disponible que la enseñe
    (búsqueda voraz / greedy set-cover simplificado: suficiente para el MVP).
    Devuelve horas totales, semanas y meses estimados, y qué cursos se eligieron.
    """
    if not faltantes:
        return {
            "cursos_recomendados": [],
            "horas_totales": 0,
            "semanas_estimadas": 0,
            "meses_estimados": 0.0,
        }

    pendientes = set(faltantes)
    elegidos = []
    horas_totales = 0

    # Greedy set-cover: en cada paso, el curso que cubre más skills pendientes
    # (a igualdad, el más corto) hasta cubrir todo lo que se pueda.
    cursos_restantes = list(cursos)
    while pendientes and cursos_restantes:
        def cobertura(curso):
            return len(pendientes.intersection(curso.get("skills", [])))

        mejor = max(cursos_restantes, key=lambda c: (cobertura(c), -c.get("duracion_horas", 0)))
        if cobertura(mejor) == 0:
            break
        elegidos.append(mejor)
        horas_totales += mejor.get("duracion_horas", 0)
        pendientes -= set(mejor.get("skills", []))
        cursos_restantes.remove(mejor)

    semanas = horas_totales / horas_por_semana if horas_por_semana else 0
    return {
        "cursos_recomendados": [
            {"id": c["id"], "nombre": c["nombre"], "duracion_horas": c["duracion_horas"]}
            for c in elegidos
        ],
        "skills_sin_curso_disponible": sorted(pendientes),
        "horas_totales": horas_totales,
        "semanas_estimadas": round(semanas, 1),
        "meses_estimados": round(semanas / 4.33, 1),
    }


# ---------------------------------------------------------------------------
# 3) Random Forest de probabilidad de éxito
# ---------------------------------------------------------------------------

def generar_dataset_sintetico(n: int = 3000, semilla: int = 42) -> pd.DataFrame:
    """
    Genera ejemplos de entrenamiento sintéticos con una fórmula heurística
    explícita (ver docstring del módulo). Cada feature se muestrea dentro de
    rangos realistas y la probabilidad "real" que se le asigna combina:
      + industria destino con buena tendencia         -> sube la probabilidad
      - industria actual también en declive fuerte    -> sube ligeramente la
        motivación pero baja algo la probabilidad (más urgencia, menos margen)
      - más skills faltantes                          -> baja la probabilidad
      - timeline muy corto para la cantidad de skills  -> baja la probabilidad
      + más años de experiencia (transferibles)        -> sube un poco
      - edad muy alta reduce algo la probabilidad (sesgo real de mercado,
        no deseable pero documentado para poder auditarlo/corregirlo)
    Se agrega ruido gaussiano para que el modelo no memorice una fórmula exacta.
    """
    rng = np.random.default_rng(semilla)

    edad = rng.integers(18, 60, n)
    años_experiencia = np.clip(rng.normal(6, 4, n), 0, 35)
    tendencia_actual = rng.uniform(-40, 20, n)
    tendencia_destino = rng.uniform(-10, 60, n)
    n_skills_faltantes = rng.integers(0, 8, n)
    timeline_meses = rng.uniform(1, 18, n)

    score = 0.5
    score = score + 0.006 * tendencia_destino
    score = score - 0.003 * np.maximum(tendencia_actual, 0)  # dejar una industria que crecía cuesta un poco más
    score = score - 0.05 * n_skills_faltantes
    score = score + 0.01 * np.clip(años_experiencia, 0, 15)
    score = score - 0.15 * np.clip((n_skills_faltantes * 1.5 - timeline_meses) / 10, 0, None)
    score = score - np.where(edad > 50, 0.08, 0.0)
    score = score + rng.normal(0, 0.07, n)  # ruido
    probabilidad_exito = np.clip(score, 0.02, 0.98)

    return pd.DataFrame({
        "edad": edad,
        "años_experiencia": años_experiencia,
        "tendencia_industria_actual_pct": tendencia_actual,
        "tendencia_industria_destino_pct": tendencia_destino,
        "n_skills_faltantes": n_skills_faltantes,
        "timeline_meses": timeline_meses,
        "probabilidad_exito": probabilidad_exito,
    })


def entrenar_modelo(dataset: Optional[pd.DataFrame] = None) -> RandomForestRegressor:
    """
    Entrena el Random Forest. Si no se pasa `dataset`, usa el sintético.
    Para conectar datos reales: entrenar_modelo(pd.read_csv("transiciones_reales.csv"))
    con las mismas columnas de FEATURES + 'probabilidad_exito'.
    """
    if dataset is None:
        dataset = generar_dataset_sintetico()

    X = dataset[FEATURES]
    y = dataset["probabilidad_exito"]

    modelo = RandomForestRegressor(
        n_estimators=300,
        max_depth=8,
        min_samples_leaf=5,
        random_state=42,
    )
    modelo.fit(X, y)
    return modelo


def guardar_modelo(modelo, ruta: str = RUTA_MODELO_DEFAULT):
    import joblib
    joblib.dump(modelo, ruta)


def cargar_modelo(ruta: str = RUTA_MODELO_DEFAULT):
    import joblib
    if os.path.exists(ruta):
        return joblib.load(ruta)
    modelo = entrenar_modelo()
    guardar_modelo(modelo, ruta)
    return modelo


def predecir_probabilidad_exito(
    modelo,
    edad: float,
    años_experiencia: float,
    tendencia_industria_actual_pct: float,
    tendencia_industria_destino_pct: float,
    n_skills_faltantes: int,
    timeline_meses: float,
) -> float:
    fila = pd.DataFrame([{
        "edad": edad,
        "años_experiencia": años_experiencia,
        "tendencia_industria_actual_pct": tendencia_industria_actual_pct,
        "tendencia_industria_destino_pct": tendencia_industria_destino_pct,
        "n_skills_faltantes": n_skills_faltantes,
        "timeline_meses": timeline_meses,
    }])[FEATURES]
    return float(np.clip(modelo.predict(fila)[0], 0, 1))

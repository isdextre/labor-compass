# -*- coding: utf-8 -*-
"""
modelo_tendencias.py
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from data_utils import cargar_catalogo_inei  # noqa: F401 (uso típico desde fuera)

try:
    from pmdarima import auto_arima
    PMDARIMA_DISPONIBLE = True
except ImportError:
    PMDARIMA_DISPONIBLE = False

MIN_PUNTOS_HISTORICOS = 8  # con series de ~12-17 años, pedir 12 (como el script
                            # original) deja afuera casi todas las series reales.


def _ajustar_y_predecir(serie_datos: pd.Series, n_periods: int):
    """Devuelve (predicciones: np.ndarray, metodo: str)."""
    if PMDARIMA_DISPONIBLE:
        try:
            modelo = auto_arima(
                serie_datos,
                start_p=0, max_p=3,
                start_q=0, max_q=3,
                d=None,
                seasonal=False,
                suppress_warnings=True,
                stepwise=True,
            )
            prediccion = modelo.predict(n_periods=n_periods)
            return np.asarray(prediccion), f"auto_arima{modelo.order}"
        except Exception as e:  # series muy cortas/planas pueden hacer fallar el ajuste
            print(f"[modelo_tendencias] auto_arima falló ({e}); uso fallback lineal.")

    # Fallback: regresión lineal simple sobre el índice temporal.
    x = np.arange(len(serie_datos))
    pendiente, intercepto = np.polyfit(x, serie_datos.values, 1)
    x_futuro = np.arange(len(serie_datos), len(serie_datos) + n_periods)
    prediccion = pendiente * x_futuro + intercepto
    sufijo = "" if PMDARIMA_DISPONIBLE else " (pmdarima no instalado)"
    return prediccion, f"tendencia_lineal{sufijo}"


def obtener_tendencia(
    region_nombre: str,
    industria_nombre: str,
    catalogo: pd.DataFrame,
    metrica: Optional[str] = None,
    n_periods: int = 3,
) -> dict:
    """
    Firma equivalente a la función original del script
    (`obtener_tendencia(region, industria, datos_totales)`), pero ahora
    `datos_totales` es el catálogo normalizado (`cargar_catalogo_inei(...)`)
    en vez de un dict anidado a mano.

    metrica: 'salarios' | 'poblacion_miles' | None (toma la primera que
             encuentre para esa región+industria si no se especifica).
    n_periods: número de AÑOS a proyectar hacia adelante (no meses).
    """
    filtro = (catalogo["region"] == region_nombre) & (catalogo["industria"] == industria_nombre)
    if metrica:
        filtro &= (catalogo["metrica"] == metrica)
    filas = catalogo[filtro]

    if filas.empty:
        return {
            "error": (
                f"No se encontraron datos para region='{region_nombre}', "
                f"industria='{industria_nombre}'"
                + (f", metrica='{metrica}'" if metrica else "")
            )
        }

    fila = filas.iloc[0]
    serie_dict = fila["serie"]
    años = sorted(serie_dict.keys(), key=int)
    valores = [serie_dict[a] for a in años]

    if len(valores) < MIN_PUNTOS_HISTORICOS:
        return {"error": "No hay suficientes datos históricos para realizar una predicción"}

    serie_datos = pd.Series(valores, index=[int(a) for a in años])
    prediccion, metodo = _ajustar_y_predecir(serie_datos, n_periods)

    ultimo_año = int(años[-1])
    variacion_historica_pct = round((valores[-1] / valores[0] - 1) * 100, 2)
    variacion_proyectada_pct = round((float(prediccion[-1]) / valores[-1] - 1) * 100, 2)

    if variacion_proyectada_pct > 5:
        clasificacion = "creciente"
    elif variacion_proyectada_pct < -5:
        clasificacion = "decreciente"
    else:
        clasificacion = "estable"

    return {
        "region": region_nombre,
        "industria": industria_nombre,
        "metrica": fila["metrica"],
        "unidad": fila["unidad"],
        "metodo": metodo,
        "ultimo_año_dato": ultimo_año,
        "ultimo_valor": round(float(valores[-1]), 2),
        "variacion_historica_pct": variacion_historica_pct,
        "prediccion_por_año": {
            str(ultimo_año + i + 1): round(float(v), 2) for i, v in enumerate(prediccion)
        },
        "variacion_proyectada_pct": variacion_proyectada_pct,
        "clasificacion": clasificacion,
    }


def listar_series_disponibles(catalogo: pd.DataFrame) -> pd.DataFrame:
    """Útil para debug / para poblar selects en el frontend."""
    return (
        catalogo.dropna(subset=["industria"])[["region", "industria", "metrica"]]
        .drop_duplicates()
        .sort_values(["region", "industria"])
        .reset_index(drop=True)
    )


def ranking_industrias(
    catalogo: pd.DataFrame,
    region_nombre: str,
    metrica: Optional[str] = None,
    n_periods: int = 3,
) -> list:
    """Todas las industrias de una región, ordenadas de mayor a menor crecimiento proyectado."""
    disponibles = catalogo[catalogo["region"] == region_nombre]
    if metrica:
        disponibles = disponibles[disponibles["metrica"] == metrica]
    industrias = disponibles["industria"].dropna().unique()

    resultados = []
    for industria in industrias:
        r = obtener_tendencia(region_nombre, industria, catalogo, metrica=metrica, n_periods=n_periods)
        if "error" not in r:
            resultados.append(r)
    return sorted(resultados, key=lambda r: r["variacion_proyectada_pct"], reverse=True)


def industria_siguiente(
    catalogo: pd.DataFrame,
    industria_actual: str,
    region_nombre: str = "Total",
    metrica: str = "salarios",
    top_n: int = 3,
) -> list:
    """
    Endpoint `industria_siguiente`: dado que la industria actual del usuario
    puede estar en declive, devuelve las `top_n` industrias con mejor tendencia
    proyectada en esa región (excluyendo la actual).

    Por defecto usa metrica='salarios' y region='Total' porque son las series
    con mayor cobertura geográfica/histórica; si el candidato es de Lima,
    conviene además cruzar con metrica='poblacion_miles' (empleo real).
    """
    ranking = ranking_industrias(catalogo, region_nombre, metrica=metrica, n_periods=3)
    ranking = [r for r in ranking if r["industria"] != industria_actual]
    return ranking[:top_n]

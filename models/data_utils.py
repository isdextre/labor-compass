# -*- coding: utf-8 -*-
"""
data_utils.py

Capa de carga y normalización de datos. Ningún modelo (ARIMA ni Random Forest)
debería tener que saber cómo está estructurado cada JSON: este módulo se encarga
de eso una sola vez y expone estructuras limpias y consistentes para el resto
del sistema.

Fuentes que este módulo entiende:
  - inei_salarios_por_rama.json   -> series de SALARIO por rama_actividad y región
  - inei_ocupados_lima.json       -> series de EMPLEO (miles de personas) por rama,
                                      sólo para Lima
  - inei_ocupados_nacional.json   -> series de INGRESO por ámbito geográfico
                                      (nacional / área / región natural / departamento),
                                      SIN desagregación por industria
  - inei_consolidado.json         -> unión de los tres anteriores (si existe, se usa
                                      este archivo y se ignoran los individuales para
                                      no duplicar filas)
  - skills_por_ocupacion.json     -> ocupación -> lista de skills requeridas
  - cursos.json                   -> catálogo de cursos (skills que cubre, duración, etc.)

LIMITACIÓN DE DATOS IMPORTANTE :
  No existe, hoy, una sola fuente pública con (departamento x industria x año).
  - Empleo por industria: sólo para Lima.
  - Salario por industria: a nivel nacional ("Total") y por macro-región natural
    (Costa urbana / Sierra urbana / Selva urbana) — NO por departamento.
  - Ingreso por departamento: existe, pero sin desagregar por industria.
  Por lo tanto, el mapa por departamento del prototipo (territorio_demo.json) usa
  datos DEMOSTRATIVOS. Este módulo no inventa ese cruce; expone lo que los datos
  realmente permiten y dejamos la limitación documentada para el equipo.
"""
from __future__ import annotations

import glob
import json
import os
import re
from typing import Optional

import pandas as pd

# ---------------------------------------------------------------------------
# Carga básica
# ---------------------------------------------------------------------------

def cargar_datos_json(ruta_archivo: str):
    """Carga un archivo JSON. Devuelve {} / [] si no existe (no revienta el pipeline)."""
    try:
        with open(ruta_archivo, "r", encoding="utf-8") as archivo:
            return json.load(archivo)
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo en: {ruta_archivo}.")
        return {}
    except json.JSONDecodeError as e:
        print(f"Error: {ruta_archivo} no es un JSON válido ({e}).")
        return {}


def _limpiar_nombre(nombre: str) -> str:
    """INEI a veces marca notas al pie como 'Servicios 1/' -> lo dejamos en 'Servicios'."""
    return re.sub(r"\s*\d+/\s*$", "", str(nombre)).strip()


def _extraer_serie_anual(item: dict):
    """
    Encuentra, dentro de un registro, la clave que contiene la serie de tiempo
    (sin importar si se llama 'salarios_por_año', 'ingresos_por_año',
    'poblacion_miles', etc.): es el primer dict cuyas llaves son todas años (dígitos).
    """
    for key, value in item.items():
        if isinstance(value, dict) and value and all(str(k).isdigit() for k in value.keys()):
            return key, value
    return None, None


# ---------------------------------------------------------------------------
# Catálogo unificado de series INEI (para el modelo de tendencias / ARIMA)
# ---------------------------------------------------------------------------

def cargar_catalogo_inei(carpeta: str) -> pd.DataFrame:
    """
    Recorre los inei_*.json de `carpeta` y arma un catálogo único en formato largo:

        region | industria | metrica | unidad | fuente_tipo | n_datos | serie (dict año->valor)

    Si existe 'inei_consolidado.json' se usa ese (ya trae todo junto) y se ignoran
    los archivos individuales para no duplicar filas.
    """
    archivos = sorted(glob.glob(os.path.join(carpeta, "inei_*.json")))
    consolidados = [a for a in archivos if "consolidado" in os.path.basename(a)]
    if consolidados:
        archivos = consolidados

    filas = []
    for archivo in archivos:
        data = cargar_datos_json(archivo)
        if not isinstance(data, list):
            continue
        for item in data:
            col_serie, serie = _extraer_serie_anual(item)
            if not serie:
                continue

            tipo = item.get("tipo", "desconocido")
            industria = item.get("rama_actividad") or item.get("categoria")
            # a las series de empleo/salario por "tamaño de empresa" no las tratamos
            # como industria (no lo son), las dejamos con industria=None
            if item.get("subcategoria") == "tamaño_empresa":
                industria = None
            if industria:
                industria = _limpiar_nombre(industria)

            region = (
                item.get("region")
                or item.get("departamento")
                or item.get("area")
                or item.get("ambito")
                or ("Lima" if "lima" in tipo else "Nacional")
            )

            metrica = col_serie.replace("_por_año", "")  # salarios, ingresos, poblacion_miles

            filas.append({
                "fuente_tipo": tipo,
                "subcategoria": item.get("subcategoria"),
                "region": region,
                "industria": industria,
                "metrica": metrica,
                "unidad": item.get("unidad", "soles/mes" if metrica == "salarios" else ""),
                "n_datos": len(serie),
                "serie": serie,
            })

    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------
# Puente ocupación -> rama de actividad (INEI sólo maneja 5 ramas)
# ---------------------------------------------------------------------------
# NOTA: los datos de skills/ocupaciones (skills_por_ocupacion.json, cursos.json,
# CVs) trabajan a nivel de OCUPACIÓN puntual (ej. "Data Analyst"), mientras que
# INEI sólo clasifica la economía en 5 ramas (Construcción, Comercio, Servicios,
# Manufactura, Otros). Esta tabla es una aproximación razonable para el MVP y
# debería validarse con el equipo de producto/datos antes de escalar:
OCUPACION_A_RAMA = {
    "Retail Sales Associate": "Comercio",
    "Data Analyst": "Servicios",
    "Logistics Coordinator": "Servicios",
    "Finance Administrator": "Servicios",
    "Administrative Assistant": "Servicios",
    "Junior Software Engineer": "Servicios",
    "Healthcare Technician": "Servicios",
    "Manufacturing Technician": "Manufactura",
    "Sales Manager": "Comercio",
    "HR Specialist": "Servicios",
    "Marketing Coordinator": "Servicios",
    "Accountant": "Servicios",
    "Database Administrator": "Servicios",
    "Customer Service Representative": "Servicios",
    "Project Manager": "Servicios",
    "Electrical Technician": "Manufactura",
    "Quality Assurance Specialist": "Manufactura",
    "Supply Chain Analyst": "Servicios",
    "UX/UI Designer": "Servicios",
    "Business Analyst": "Servicios",
    # "Otros" en INEI agrupa sectores primarios/emergentes no desagregados
    # (minería, agro, pesca, energía) — es la mejor aproximación disponible hoy:
    "Mining Maintenance Technician": "Otros",
    "Solar Energy Technician": "Otros",
}


def rama_de_ocupacion(ocupacion: str) -> Optional[str]:
    return OCUPACION_A_RAMA.get(ocupacion)


# ---------------------------------------------------------------------------
# Industrias específicas (más finas que las 5 ramas de INEI)
# ---------------------------------------------------------------------------
# INEI no desagrega "Minería" ni "Energía solar" como ramas propias (ambas caen
# dentro de "Otros"), pero son justo el ejemplo insignia del pitch (minero ->
# técnico solar). territorio_demo.json sí las distingue, aunque son datos
# DEMOSTRATIVOS (ver su campo "_nota"), no una serie histórica real de INEI/MTPE.
# Se usan aquí como una señal complementaria y mejor que nada, dejando bien
# marcado en la respuesta que el método es "dato_demostrativo", no ARIMA.
OCUPACION_A_INDUSTRIA_ESPECIFICA = {
    "Mining Maintenance Technician": "Minería",
    "Solar Energy Technician": "Energía solar",
}


def industria_especifica_de_ocupacion(ocupacion: str) -> Optional[str]:
    return OCUPACION_A_INDUSTRIA_ESPECIFICA.get(ocupacion)


def cargar_industrias_especificas_demo(ruta_territorio_demo: str) -> dict:
    """{region_nombre: {industria_nombre: variacion_pct}} a partir de territorio_demo.json."""
    data = cargar_datos_json(ruta_territorio_demo)
    resultado = {}
    for region in data.get("regiones", []):
        resultado[region["nombre"]] = {
            i["nombre"]: i["variacion_pct"] for i in region.get("industrias_crecimiento", [])
        }
    return resultado


# ---------------------------------------------------------------------------
# Skills y cursos
# ---------------------------------------------------------------------------

def cargar_skills_por_ocupacion(ruta_archivo: str) -> dict:
    data = cargar_datos_json(ruta_archivo)
    return data.get("skills_mapping", {})


def cargar_cursos(ruta_archivo: str) -> list:
    data = cargar_datos_json(ruta_archivo)
    return data.get("cursos", [])


def cargar_cv_ejemplos(ruta_archivo: str) -> list:
    data = cargar_datos_json(ruta_archivo)
    return data.get("cv_parsed_examples", [])

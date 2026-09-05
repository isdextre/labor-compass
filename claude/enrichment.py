"""
Enrichment - conecta el Transition Radar con las señales de mercado REALES
============================================================================
Este módulo no reemplaza matching.py: lo complementa. matching.py calcula el
difficulty_score comparando dos listas de skills (nuestro catálogo simulado,
data/skills_por_ocupacion.json). Este módulo agrega, por encima de eso, datos
que SÍ vienen de un dataset real: 15,886 publicaciones de LinkedIn procesadas
en data/processed/05_FUTURE_WORK_market_demand.json.

Por qué existe este archivo separado y no se mete todo en app.py:
- Deja clarísimo, con una sola función `fuente()`, qué campo es real y cuál
  es simulado/demo — requisito explícito del proyecto (sección "Datos y
  transparencia" del spec).
- El dataset real de LinkedIn no tiene las mismas 22 ocupaciones específicas
  que inventamos para la demo (ej. "Solar Energy Technician" no existe como
  categoría en LinkedIn). Por eso mapeamos cada ocupación específica a la
  categoría amplia más parecida de las 11 que sí existen en el dataset real
  (OCCUPATION_TO_CATEGORY). Cuando el mapeo cae en "Other" lo decimos
  explícitamente en la respuesta, en vez de fingir precisión que no existe.
"""

import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
PROCESSED_DIR = os.path.join(DATA_DIR, 'processed')

# ----------------------------------------------------------------------------
# Mapeo: ocupación específica (nuestro catálogo demo) -> categoría amplia
# real de LinkedIn (una de las 11 en 05_FUTURE_WORK_market_demand.json)
# ----------------------------------------------------------------------------
OCCUPATION_TO_CATEGORY = {
    "Retail Sales Associate": "Retail & Customer Service",
    "Data Analyst": "Data & Analytics",
    "Logistics Coordinator": "Other",
    "Finance Administrator": "Finance & Accounting",
    "Administrative Assistant": "Administrative & Clerical",
    "Junior Software Engineer": "Engineering & Development",
    "Healthcare Technician": "Healthcare",
    "Manufacturing Technician": "Other",
    "Sales Manager": "Sales",
    "HR Specialist": "Human Resources",
    "Marketing Coordinator": "Marketing & Communications",
    "Accountant": "Finance & Accounting",
    "Database Administrator": "Engineering & Development",
    "Customer Service Representative": "Retail & Customer Service",
    "Project Manager": "Management & Leadership",
    "Electrical Technician": "Other",
    "Quality Assurance Specialist": "Engineering & Development",
    "Supply Chain Analyst": "Data & Analytics",
    "UX/UI Designer": "Engineering & Development",
    "Business Analyst": "Data & Analytics",
    "Mining Maintenance Technician": "Other",
    "Solar Energy Technician": "Other",
}

# Códigos de skill de LinkedIn -> etiqueta legible en español
SKILL_CODE_LABELS = {
    "IT": "Tecnología de la información",
    "MGMT": "Gestión / liderazgo de equipos",
    "MNFC": "Manufactura",
    "OTHR": "Habilidades generales",
    "HCPR": "Atención en salud",
    "SALE": "Ventas",
    "BD": "Desarrollo de negocio",
    "PRJM": "Gestión de proyectos",
    "ACCT": "Contabilidad",
    "FIN": "Finanzas",
    "ANLS": "Análisis de datos",
    "ADM": "Administración",
    "ENG": "Ingeniería",
    "DSGN": "Diseño",
    "CUST": "Atención al cliente",
    "HR": "Recursos humanos",
    "GENB": "Negocios generales",
    "MRKT": "Marketing",
    "WRT": "Redacción",
    "PR": "Relaciones públicas",
    "RSCH": "Investigación",
}

_market_demand_cache = None


def _cargar_market_demand():
    global _market_demand_cache
    if _market_demand_cache is not None:
        return _market_demand_cache
    path = os.path.join(PROCESSED_DIR, '05_FUTURE_WORK_market_demand.json')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            _market_demand_cache = json.load(f)
    except FileNotFoundError:
        _market_demand_cache = {'by_occupation': {}, 'metadata': {}}
    return _market_demand_cache


def señal_de_mercado(ocupacion: str):
    """
    Devuelve la señal de mercado REAL (calculada desde 15,886 empleos de
    LinkedIn) para la ocupación específica dada, mapeada a su categoría
    amplia más cercana.

    Siempre incluye:
    - `categoria_linkedin`: a qué categoría amplia se mapeó.
    - `es_categoria_generica`: True si el mapeo cayó en "Other" (el dataset
      no tiene una categoría específica para este rubro) — hay que mostrarlo
      con honestidad en la interfaz, no ocultarlo.
    - `fuente`: de dónde sale el dato.
    - `tipo_dato`: "calculado" (no es una opinión, es una cuenta real sobre
      un dataset real).
    """
    data = _cargar_market_demand()
    categoria = OCCUPATION_TO_CATEGORY.get(ocupacion)
    if not categoria:
        return None

    bloque = data.get('by_occupation', {}).get(categoria)
    if not bloque:
        return None

    skills_legibles = [
        SKILL_CODE_LABELS.get(codigo, codigo)
        for codigo in bloque.get('top_required_skills', [])
    ]

    return {
        'categoria_linkedin': categoria,
        'es_categoria_generica': categoria == 'Other',
        'position_count': bloque.get('position_count'),
        'growth_indicator': bloque.get('growth_indicator'),
        'remote_adoption_rate': bloque.get('remote_adoption_rate'),
        'salary_premium_senior_to_entry': bloque.get('salary_premium_senior_to_entry'),
        'top_required_skills': skills_legibles,
        'total_dataset_positions': data.get('metadata', {}).get('total_positions'),
        'fuente': 'LinkedIn Job Postings (Kaggle) — 15,886 publicaciones procesadas',
        'tipo_dato': 'calculado',
    }


def explicacion_categoria(categoria: str) -> str:
    """Texto corto para mostrar cuando el mapeo cae en una categoría genérica."""
    if categoria == 'Other':
        return (
            'El dataset de LinkedIn no tiene una categoría específica para este '
            'rubro; se muestra la señal de la categoría más cercana disponible '
            '("Otras industrias técnicas") en vez de inventar un dato que no existe.'
        )
    return f'Categoría de mercado más cercana según LinkedIn: {categoria}.'

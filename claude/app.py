"""
Transition Radar - Backend Flask
==================================

Sistema de recomendación de transición de carrera que integra:
- Parsing de CV simulado (datos de ejemplo)
- Matching semántico de ocupaciones basado en skills
- Recomendación inteligente de cursos por skills faltantes
- Apoyo emocional (wellness) basado en nivel de estrés/confianza
- Conexión a comunidades de peer support (cohorts)
- Validación contra mercado laboral peruano (INEI)

FLUJO PRINCIPAL:
1. Usuario: ocupación actual → skills actuales
2. Backend: busca ocupaciones objetivo con menor "difficulty"
3. Para cada ocupación objetivo: calcula skills faltantes
4. Busca cursos que enseñen esos skills (cursos.json)
5. Evalúa estado emocional → mensaje de bienestar
6. Sugiere cohort de peer support relevante
7. Devuelve ranking de oportunidades + plan de acción

DATOS UTILIZADOS:
- skills_por_ocupacion.json: mapeo ocupación → skills (CORE)
- cursos.json: catálogo de cursos disponibles (CORE)
- cv_ejemplos.json: ejemplos parseados para simulación (CORE)
- wellness_library.json: respuestas por estrés/confianza (OPCIONAL - UX)
- cohorts.json: grupos de peer support (OPCIONAL - comunidad)
- inei_consolidado.json: validación ocupaciones reales en Perú (OPCIONAL - contexto)
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import json
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)

# ============================================================================
# CARGAR DATOS AL INICIAR
# ============================================================================

DATA_DIR = 'data'

def cargar_json(filename):
    """Carga un archivo JSON desde la carpeta data/"""
    try:
        with open(os.path.join(DATA_DIR, filename), 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"⚠️  Archivo {filename} no encontrado")
        return {}

# DATOS CORE (necesarios para funcionamiento)
skills_data = cargar_json('skills_por_ocupacion.json')
SKILLS_MAP = skills_data.get('skills_mapping', {})

cursos_data = cargar_json('cursos.json')
CURSOS_DB = cursos_data.get('cursos', [])

cv_data = cargar_json('cv_ejemplos.json')
CV_EJEMPLOS = cv_data.get('cv_parsed_examples', [])

# DATOS OPCIONALES (enriquecen la experiencia pero no son core)
wellness_data = cargar_json('wellness_library.json')
WELLNESS_LIB = wellness_data.get('wellness_responses', [])

cohorts_data = cargar_json('cohorts.json')
COHORTS_DB = cohorts_data.get('cohorts', [])

inei_data = cargar_json('inei_consolidado.json')
INEI_DB = inei_data if inei_data else {}

print(f"✓ Cargados: {len(SKILLS_MAP)} ocupaciones, {len(CURSOS_DB)} cursos, {len(CV_EJEMPLOS)} CV ejemplos")
print(f"✓ Opcionales: {len(WELLNESS_LIB)} respuestas bienestar, {len(COHORTS_DB)} cohorts")


# ============================================================================
# ENDPOINT 1: Parse CV (simula extracción de datos)
# ============================================================================

@app.route('/api/parse-cv', methods=['POST'])
def parse_cv():
    """
    Simula parsing de CV del usuario.

    INPUT:
    {
        "cv_id": "USER_001"  (opcional - si no envía, devuelve primero)
    }

    OUTPUT:
    {
        "user_id": "USER_001",
        "nombre": "María García López",
        "ocupacion_actual": "Retail Sales Associate",
        "experiencia_años": 3,
        "salario_actual_usd": 450,
        "skills_identificadas": ["Communication", "Sales", "Customer Service"],
        "certificaciones": [],
        "ubicacion": "Lima"
    }
    """

    cv_id = request.json.get('cv_id') if request.json else None

    if cv_id:
        cv = next((c for c in CV_EJEMPLOS if c['user_id'] == cv_id), None)
    else:
        cv = CV_EJEMPLOS[0] if CV_EJEMPLOS else None

    if not cv:
        return jsonify({'error': 'No se encontraron CVs de ejemplo'}), 404

    return jsonify({
        'user_id': cv['user_id'],
        'nombre': cv['nombre'],
        'ocupacion_actual': cv['ocupacion_actual'],
        'experiencia_años': cv['experiencia_años'],
        'salario_actual_usd': cv['salario_actual_usd'],
        'skills_identificadas': cv['skills_identificadas'],
        'certificaciones': cv['certificaciones'],
        'ubicacion': cv.get('ubicacion', 'Lima'),
        'educacion': cv.get('educacion', 'N/A')
    }), 200


# ============================================================================
# ENDPOINT 2: Matching - Ocupaciones objetivo + Cursos
# ============================================================================

@app.route('/api/matching', methods=['POST'])
def matching():
    """
    Calcula ocupaciones objetivo posibles + cursos recomendados.

    INPUT:
    {
        "ocupacion_actual": "Retail Sales Associate",
        "skills_actuales": ["Communication", "Sales", ...] (opcional)
    }

    OUTPUT:
    [
        {
            "ocupacion_objetivo": "Sales Manager",
            "difficulty_score": 45.5,
            "skills_comunes": ["Communication"],
            "skills_faltantes": ["Leadership", "Excel", ...],
            "cursos_recomendados": [
                {
                    "id": "COURSE_005",
                    "nombre": "Agile Project Management",
                    "duracion_horas": 30,
                    "certificacion": true,
                    "skills_cubre": ["Leadership"]
                }
            ]
        },
        ...
    ]
    """

    data = request.json
    ocupacion_actual = data.get('ocupacion_actual')
    skills_actuales = data.get('skills_actuales')

    # Si no especifica skills, obtener del mapeo
    if not skills_actuales:
        skills_actuales = SKILLS_MAP.get(ocupacion_actual, [])

    if not skills_actuales:
        return jsonify({'error': f'Ocupación "{ocupacion_actual}" no encontrada'}), 400

    resultados = []

    # Iterar todas las ocupaciones objetivo
    for ocupacion_objetivo, skills_req in SKILLS_MAP.items():

        # No considerar la misma ocupación
        if ocupacion_objetivo == ocupacion_actual:
            continue

        # Calcular overlap de skills
        skills_comunes = set(skills_actuales) & set(skills_req)
        skills_faltantes = set(skills_req) - set(skills_actuales)

        # Difficulty Score: 0-100
        # 0 = ya tiene todos los skills (transición fácil)
        # 100 = no tiene ninguno (transición difícil)
        if len(skills_req) == 0:
            difficulty = 0
        else:
            difficulty = (len(skills_faltantes) / len(skills_req)) * 100

        # PASO CRÍTICO: Buscar cursos que cubran skills faltantes
        cursos_match = []
        for skill_faltante in skills_faltantes:
            for curso in CURSOS_DB:
                if skill_faltante in curso['skills']:
                    # Evitar duplicados
                    if not any(c['id'] == curso['id'] for c in cursos_match):
                        cursos_match.append({
                            'id': curso['id'],
                            'nombre': curso['nombre'],
                            'duracion_horas': curso['duracion_horas'],
                            'dificultad': curso['dificultad'],
                            'certificacion': curso['certificacion'],
                            'skills_cubre': [s for s in curso['skills'] if s in skills_faltantes]
                        })

        resultados.append({
            'ocupacion_objetivo': ocupacion_objetivo,
            'difficulty_score': round(difficulty, 1),
            'skills_comunes': list(skills_comunes),
            'skills_faltantes': list(skills_faltantes),
            'num_skills_faltantes': len(skills_faltantes),
            'cursos_recomendados': cursos_match[:5]  # Top 5 cursos
        })

    # Ordenar por difficulty (menor dificultad primero = transiciones más fáciles)
    resultados = sorted(resultados, key=lambda x: x['difficulty_score'])

    # Devolver top 5 ocupaciones objetivo
    return jsonify({
        'ocupacion_actual': ocupacion_actual,
        'skills_actuales': list(skills_actuales),
        'ocupaciones_objetivo': resultados[:5],
        'total_posibilidades': len(resultados),
        'timestamp': datetime.now().isoformat()
    }), 200


# ============================================================================
# ENDPOINT 3: Wellness - Apoyo emocional + Cohorts
# ============================================================================

@app.route('/api/wellness', methods=['POST'])
def wellness():
    """
    Proporciona apoyo emocional basado en estrés/confianza.
    También sugiere cohorts de peer support.

    INPUT:
    {
        "stress_level": 8,              (1-10, donde 10 = muy estresado)
        "confidence_level": 4,          (1-10, donde 10 = muy confiado)
        "ocupacion_objetivo": "Data Analyst"  (opcional)
    }

    OUTPUT:
    {
        "wellness_category": "high_stress",
        "mensaje": "It's completely normal to feel overwhelmed...",
        "accion_sugerida": "Schedule a 15-min wellness session",
        "cohort_recommendation": {
            "cohort_id": "COHORT_001",
            "nombre": "Tech Career Changers - Lima",
            "ubicacion": "Lima",
            "tasa_finalizacion": 0.75,
            "proxima_fecha": "2026-09-15"
        }
    }
    """

    data = request.json
    stress = data.get('stress_level', 5)
    confidence = data.get('confidence_level', 5)
    ocupacion_objetivo = data.get('ocupacion_objetivo', 'Data Analyst')

    # Categorizar estrés
    if stress > 7:
        stress_category = 'high_stress'
    elif stress > 3:
        stress_category = 'medium_stress'
    else:
        stress_category = 'low_stress'

    # Buscar mensaje wellness apropiado
    wellness_msg = next(
        (w for w in WELLNESS_LIB if w['tipo'] == stress_category),
        WELLNESS_LIB[0] if WELLNESS_LIB else {
            'respuesta': 'Keep going! You\'re on the right path.',
            'accion_sugerida': 'Continue with your learning plan'
        }
    )

    # Buscar cohort relevante por ocupación objetivo
    cohort = next(
        (c for c in COHORTS_DB if ocupacion_objetivo in c['ocupaciones_enfoque']),
        COHORTS_DB[0] if COHORTS_DB else None
    )

    cohort_info = None
    if cohort:
        cohort_info = {
            'cohort_id': cohort['cohort_id'],
            'nombre': cohort['nombre'],
            'ubicacion': cohort['ubicacion'],
            'ocupaciones_enfoque': cohort['ocupaciones_enfoque'],
            'tamaño_actual': cohort['tamaño_actual'],
            'tasa_finalizacion': cohort['tasa_finalizacion'],
            'proximidad_fecha': cohort['fecha_inicio'],
            'facilitador': cohort['facilitador']
        }

    return jsonify({
        'stress_level': stress,
        'confidence_level': confidence,
        'wellness_category': stress_category,
        'mensaje': wellness_msg.get('respuesta', ''),
        'accion_sugerida': wellness_msg.get('accion_sugerida', ''),
        'recurso': wellness_msg.get('recurso', ''),
        'cohort_recommendation': cohort_info,
        'timestamp': datetime.now().isoformat()
    }), 200


# ============================================================================
# ENDPOINT 4: Cursos - Catálogo completo
# ============================================================================

@app.route('/api/cursos', methods=['GET'])
def get_cursos():
    """
    Devuelve catálogo completo de cursos.

    OPCIONAL QUERY PARAMS:
    - skill: filtrar por skill específico
    - categoria: filtrar por categoría
    - dificultad: beginner, intermediate, advanced

    OUTPUT:
    {
        "total_cursos": 40,
        "cursos": [
            {
                "id": "COURSE_001",
                "nombre": "Python Fundamentals",
                "categoria": "Technology",
                "skills": ["Python", "Data Analysis"],
                "duracion_horas": 40,
                "dificultad": "beginner",
                "certificacion": true
            },
            ...
        ]
    }
    """

    skill = request.args.get('skill')
    categoria = request.args.get('categoria')
    dificultad = request.args.get('dificultad')

    cursos_filtrados = CURSOS_DB

    if skill:
        cursos_filtrados = [c for c in cursos_filtrados if skill in c['skills']]

    if categoria:
        cursos_filtrados = [c for c in cursos_filtrados if c['categoria'].lower() == categoria.lower()]

    if dificultad:
        cursos_filtrados = [c for c in cursos_filtrados if c['dificultad'] == dificultad]

    return jsonify({
        'total_cursos': len(cursos_filtrados),
        'cursos': cursos_filtrados
    }), 200


# ============================================================================
# ENDPOINT 5: Ocupaciones disponibles
# ============================================================================

@app.route('/api/ocupaciones', methods=['GET'])
def get_ocupaciones():
    """
    Devuelve lista de ocupaciones disponibles.

    OUTPUT:
    {
        "total_ocupaciones": 20,
        "ocupaciones": [
            {
                "nombre": "Data Analyst",
                "skills_requeridos": ["SQL", "Python", "Excel", ...]
            },
            ...
        ]
    }
    """

    ocupaciones = [
        {
            'nombre': ocu,
            'skills_requeridos': skills
        }
        for ocu, skills in SKILLS_MAP.items()
    ]

    return jsonify({
        'total_ocupaciones': len(ocupaciones),
        'ocupaciones': ocupaciones
    }), 200


# ============================================================================
# ENDPOINT 6: Cohorts disponibles
# ============================================================================

@app.route('/api/cohorts', methods=['GET'])
def get_cohorts():
    """
    Devuelve lista de cohorts de peer support.

    OPCIONAL: ?ubicacion=Lima

    OUTPUT:
    {
        "total_cohorts": 6,
        "cohorts": [
            {
                "cohort_id": "COHORT_001",
                "nombre": "Tech Career Changers - Lima",
                "ubicacion": "Lima",
                "ocupaciones_enfoque": ["Data Analyst", ...],
                "tasa_finalizacion": 0.75,
                "proxima_fecha": "2026-09-15"
            },
            ...
        ]
    }
    """

    ubicacion = request.args.get('ubicacion')

    cohorts_filtrados = COHORTS_DB
    if ubicacion:
        cohorts_filtrados = [c for c in cohorts_filtrados if c['ubicacion'].lower() == ubicacion.lower()]

    return jsonify({
        'total_cohorts': len(cohorts_filtrados),
        'cohorts': cohorts_filtrados
    }), 200


# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.route('/health', methods=['GET'])
def health():
    """Verifica que el servidor está activo y datos están cargados"""
    return jsonify({
        'status': 'ok',
        'data_loaded': {
            'skills_mapping': len(SKILLS_MAP),
            'cursos': len(CURSOS_DB),
            'cv_ejemplos': len(CV_EJEMPLOS),
            'wellness_responses': len(WELLNESS_LIB),
            'cohorts': len(COHORTS_DB)
        }
    }), 200


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint no encontrado'}), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({'error': 'Error interno del servidor'}), 500


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 Transition Radar Backend iniciando...")
    print("="*60)
    print(f"📊 Datos cargados: {len(SKILLS_MAP)} ocupaciones, {len(CURSOS_DB)} cursos")
    print(f"🎯 Endpoints disponibles:")
    print(f"   - POST /api/parse-cv")
    print(f"   - POST /api/matching")
    print(f"   - POST /api/wellness")
    print(f"   - GET  /api/cursos")
    print(f"   - GET  /api/ocupaciones")
    print(f"   - GET  /api/cohorts")
    print(f"   - GET  /health")
    print(f"\n🔗 http://localhost:5000")
    print("="*60 + "\n")

    app.run(debug=True, port=5000, host='127.0.0.1', use_reloader=False)

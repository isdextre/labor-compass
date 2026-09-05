"""
PRÓXIMO (antes "Transition Radar") - Backend Flask
====================================================

Sistema de inteligencia laboral que integra:
- Parsing de CV simulado (datos de ejemplo)
- Matching semántico de ocupaciones basado en skills (Transition Radar)
- Enriquecimiento con señales de mercado REALES (15,886 empleos de LinkedIn
  procesados) vía enrichment.py — ver ese archivo para el detalle de qué es
  real y qué es una aproximación.
- Recomendación inteligente de cursos por skills faltantes
- Apoyo emocional (wellness) basado en nivel de estrés/confianza
- Conexión a comunidades de peer support (cohorts)
- Validación contra mercado laboral peruano (INEI)
- Matching semántico reclutador -> candidatos (TF-IDF + similitud coseno)
- Explorador territorial (datos demostrativos, claramente etiquetados)

Todas las páginas HTML (landing, analizar, resultados, mentores, reclutador,
mapa) se sirven aquí mismo con Jinja — un solo comando (`python app.py`)
levanta todo, sin necesidad de abrir un archivo aparte con Live Server.
La mayor parte de las funcionalidades nuevas del brief (mentorías, estado
premium, hacks completados, candidatos guardados) NO requieren backend:
viven en localStorage en el navegador, como pide la sección de
"Persistencia ligera" del spec, porque esto es una demo de hackathon sin
sistema de cuentas ni pagos reales.
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import json
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from billing import tiene_acceso, marcar_como_premium
from datetime import datetime
from models.predictor import obtener_tendencia, cargar_datos_json
from cv_parser import parsear_cv
import enrichment

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_DISPONIBLE = True
except ImportError:
    SKLEARN_DISPONIBLE = False

app = Flask(__name__)
CORS(app)


# ============================================================================
# CARGAR DATOS AL INICIAR
# ============================================================================

# Ruta absoluta a data/ (independiente del directorio desde el que se ejecute
# `python app.py` — antes dependía de que el cwd fuera la raíz del repo).
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
RUTA_HISTORICO = "data/processed/datos_historicos.json"
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

# DATOS NUEVOS: reclutador y explorador territorial
candidatos_data = cargar_json('candidatos_reclutador.json')
CANDIDATOS_DB = candidatos_data.get('candidatos', [])

territorio_data = cargar_json('territorio_demo.json')
REGIONES_DB = territorio_data.get('regiones', [])

print(f"✓ Cargados: {len(SKILLS_MAP)} ocupaciones, {len(CURSOS_DB)} cursos, {len(CV_EJEMPLOS)} CV ejemplos")
print(f"✓ Opcionales: {len(WELLNESS_LIB)} respuestas bienestar, {len(COHORTS_DB)} cohorts")
print(f"✓ Nuevos: {len(CANDIDATOS_DB)} candidatos demo, {len(REGIONES_DB)} regiones territoriales")


# ============================================================================
# PÁGINAS (Jinja) — el "arquitectura de información" del producto
# ============================================================================

@app.route('/')
def pagina_landing():
    return render_template('landing.html')


@app.route('/analizar')
def pagina_analizar():
    return render_template('analizar.html')


@app.route('/resultados')
def pagina_resultados():
    return render_template('resultados.html')


@app.route('/mentores')
def pagina_mentores():
    return render_template('mentores.html')


@app.route('/reclutador')
def pagina_reclutador():
    return render_template('reclutador.html')


@app.route('/mapa')
def pagina_mapa():
    return render_template('mapa.html')


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
# ENDPOINT 2: Matching - Ocupaciones objetivo + Cursos (+ señal de mercado real)
# ============================================================================

@app.route('/api/matching', methods=['POST'])
def matching():
    """
    Calcula ocupaciones objetivo posibles + cursos recomendados.
    Además de lo que ya existía, cada ocupación objetivo ahora trae un bloque
    `señal_mercado` con datos REALES calculados desde 15,886 empleos de
    LinkedIn (ver enrichment.py). Si no hay mapeo disponible, el campo viene
    en null — nunca se inventa un número para rellenar el hueco.

    INPUT:
    {
        "ocupacion_actual": "Retail Sales Associate",
        "skills_actuales": ["Communication", "Sales", ...] (opcional)
    }
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
            'cursos_recomendados': cursos_match[:5],  # Top 5 cursos
            'señal_mercado': enrichment.señal_de_mercado(ocupacion_objetivo),
        })

    # Ordenar por difficulty (menor dificultad primero = transiciones más fáciles)
    resultados = sorted(resultados, key=lambda x: x['difficulty_score'])

    return jsonify({
        'ocupacion_actual': ocupacion_actual,
        'skills_actuales': list(skills_actuales),
        'señal_mercado_actual': enrichment.señal_de_mercado(ocupacion_actual),
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
    """Devuelve catálogo completo de cursos, con filtros opcionales."""

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
    """Devuelve lista de ocupaciones disponibles."""

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
    """Devuelve lista de cohorts de peer support."""

    ubicacion = request.args.get('ubicacion')

    cohorts_filtrados = COHORTS_DB
    if ubicacion:
        cohorts_filtrados = [c for c in cohorts_filtrados if c['ubicacion'].lower() == ubicacion.lower()]

    return jsonify({
        'total_cohorts': len(cohorts_filtrados),
        'cohorts': cohorts_filtrados
    }), 200


# ============================================================================
# ENDPOINT 7 (NUEVO): Reclutador - matching semántico por texto (TF-IDF)
# ============================================================================

@app.route('/api/recruiter/match', methods=['POST'])
def recruiter_match():
    """
    Recibe la descripción de un puesto en texto libre y devuelve los
    candidatos del pool demo ordenados por similitud de TEXTO (TF-IDF +
    similitud coseno de scikit-learn), no por coincidencia literal de
    palabras clave. Esto es real (se calcula en el momento), pero es
    importante ser honestos sobre qué tipo de "semántica" es: TF-IDF
    entiende qué palabras son distintivas de un texto y compara vectores,
    no capta sinónimos como lo haría un embedding neuronal — se lo
    decimos así al usuario en la interfaz (`metodo` en la respuesta).

    INPUT:
    {
        "titulo_puesto": "Técnico de energía solar",
        "descripcion": "Buscamos alguien con experiencia en mantenimiento
                         de equipos, trabajo de campo y conocimientos
                         eléctricos básicos, en Arequipa."
    }
    """
    data = request.json or {}
    titulo = data.get('titulo_puesto', '')
    descripcion = data.get('descripcion', '')
    texto_puesto = f"{titulo}. {descripcion}".strip()

    if not texto_puesto or texto_puesto == '.':
        return jsonify({'error': 'Escribe una descripción del puesto para buscar candidatos.'}), 400

    if not CANDIDATOS_DB:
        return jsonify({'error': 'No hay candidatos demo cargados.'}), 404

    if not SKLEARN_DISPONIBLE:
        return jsonify({'error': 'scikit-learn no está instalado en el entorno (pip install scikit-learn).'}), 500

    corpus = [texto_puesto] + [
        f"{c['ocupacion_actual']}. {c['resumen']}" for c in CANDIDATOS_DB
    ]

    vectorizer = TfidfVectorizer(stop_words=None)
    matriz = vectorizer.fit_transform(corpus)
    similitudes = cosine_similarity(matriz[0:1], matriz[1:])[0]

    resultados = []
    for candidato, similitud in zip(CANDIDATOS_DB, similitudes):
        resultados.append({
            'id': candidato['id'],
            'nombre': candidato['nombre'],
            'ocupacion_actual': candidato['ocupacion_actual'],
            'ubicacion': candidato['ubicacion'],
            'experiencia_años': candidato['experiencia_años'],
            'skills': candidato['skills'],
            'disponibilidad': candidato['disponibilidad'],
            'compatibilidad_pct': round(float(similitud) * 100, 1),
        })

    resultados = sorted(resultados, key=lambda r: r['compatibilidad_pct'], reverse=True)

    return jsonify({
        'puesto': {'titulo': titulo, 'descripcion': descripcion},
        'metodo': 'Similitud de texto TF-IDF + coseno (scikit-learn), calculada sobre el pool de candidatos demo.',
        'candidatos': resultados,
        'total_candidatos': len(resultados),
        'timestamp': datetime.now().isoformat(),
    }), 200


# ============================================================================
# ENDPOINT 8 (NUEVO): Explorador territorial
# ============================================================================

@app.route('/api/territorio', methods=['GET'])
def get_territorio():
    """
    Devuelve las regiones del explorador territorial. Datos demostrativos
    para el prototipo (no vienen de un pipeline en vivo de INEI/MTPE por
    región) — se etiquetan como tal en la respuesta y en la interfaz.
    """
    return jsonify({
        'regiones': REGIONES_DB,
        'es_demostrativo': True,
        'nota': territorio_data.get('_nota', ''),
        'fecha_actualizacion': territorio_data.get('fecha_actualizacion'),
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
            'cohorts': len(COHORTS_DB),
            'candidatos_reclutador': len(CANDIDATOS_DB),
            'regiones_territorio': len(REGIONES_DB),
        },
        'sklearn_disponible': SKLEARN_DISPONIBLE,
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

@app.route("/tendencia", methods=["GET"])
def tendencia():
    region = request.args.get("region")
    industria = request.args.get("industria")
    if not region or not industria:
        return jsonify({"error": "Faltan parámetros 'region' e 'industria'"}), 400
    datos = cargar_datos_json(RUTA_HISTORICO)
    resultado = obtener_tendencia(region, industria, datos)
    return jsonify(resultado)

@app.route("/api/verificar_acceso", methods=["POST"])
def verificar_acceso():
    user_id = request.json.get("user_id")
    resultado = tiene_acceso(user_id)
    return jsonify(resultado)

@app.route("/api/pagar_yape", methods=["POST"])
def pagar_yape():
    """
    DEMO ONLY: en producción esto sería un webhook real de Culqi/Mercado Pago
    confirmando que el pago por Yape se completó. Para el hackathon, simulamos
    que el usuario ingresa su número de operación de Yape y lo aceptamos.
    """
    user_id = request.json.get("user_id")
    numero_operacion = request.json.get("numero_operacion")  # el código que Yape genera

    if not numero_operacion or len(numero_operacion) < 6:
        return jsonify({"error": "Número de operación inválido"}), 400

    marcar_como_premium(user_id)
    return jsonify({"mensaje": "Pago verificado (simulado). Acceso premium activado.", "user_id": user_id})

from matching import matching_semantico

@app.route("/api/recruiter/match_semantico", methods=["POST"])
def match_semantico():
    puesto_texto = request.json.get("puesto_texto")
    candidatos = request.json.get("candidatos")
    if not puesto_texto or not candidatos:
        return jsonify({"error": "Faltan 'puesto_texto' o 'candidatos'"}), 400
    resultados = matching_semantico(puesto_texto, candidatos)
    return jsonify(resultados)

@app.route('/api/parse-cv-upload', methods=['POST'])
def parse_cv_upload():
    """
    Recibe un archivo real de CV (PDF, DOCX o TXT) vía form-data,
    extrae el texto y lo estructura con Gemini.

    INPUT: form-data con un campo "cv_file" (el archivo)
    OUTPUT: mismo formato que /api/parse-cv (simulado), pero con datos reales.
    """
    if 'cv_file' not in request.files:
        return jsonify({'error': "Falta el archivo. Envía un form-data con el campo 'cv_file'."}), 400

    archivo = request.files['cv_file']
    if archivo.filename == '':
        return jsonify({'error': 'No se seleccionó ningún archivo.'}), 400

    try:
        datos = parsear_cv(archivo, archivo.filename)
        return jsonify(datos), 200
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except RuntimeError as e:
        return jsonify({'error': str(e)}), 500
    except json.JSONDecodeError:
        return jsonify({'error': 'Gemini no devolvió un JSON válido. Intenta de nuevo.'}), 502
    except Exception as e:
        return jsonify({'error': f'Error inesperado: {str(e)}'}), 500
      
# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 PRÓXIMO Backend iniciando...")
    print("="*60)
    print(f"📊 Datos cargados: {len(SKILLS_MAP)} ocupaciones, {len(CURSOS_DB)} cursos")
    print(f"🎯 Páginas: /  /analizar  /resultados  /mentores  /reclutador  /mapa")
    print(f"🔌 Endpoints API:")
    print(f"   - POST /api/parse-cv")
    print(f"   - POST /api/matching")
    print(f"   - POST /api/wellness")
    print(f"   - GET  /api/cursos")
    print(f"   - GET  /api/ocupaciones")
    print(f"   - GET  /api/cohorts")
    print(f"   - POST /api/recruiter/match")
    print(f"   - GET  /api/territorio")
    print(f"   - GET  /health")
    print(f"\n🔗 http://127.0.0.1:5000")
    print(f"   - POST /api/verificar_acceso")
    print(f"   - POST /api/pagar_yape")
    print("="*60 + "\n")

    app.run(debug=True, port=5000, host='127.0.0.1', use_reloader=False)

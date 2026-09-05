# -*- coding: utf-8 -*-
"""
orchestrator.py — Une las piezas del agente de postulación.

Flujo completo:

    1. perfil guardado (una sola vez)  -> cargar_perfil()
    2. ofertas de los boards objetivo  -> greenhouse.listar_ofertas()
    3. ranking por afinidad con el CV  -> buscar_ofertas()
    4. formulario resuelto por oferta  -> preparar_postulacion()

El paso 3 usa TF-IDF + coseno, el mismo método que ya usa el endpoint del
reclutador en app.py. No es un embedding neuronal y no capta sinónimos; lo
decimos explícitamente en la respuesta (`metodo`) para no vender precisión
que no tenemos.
"""
import json
import os

from applier import greenhouse
from applier.answers import construir_borrador, payload_de_envio

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_DISPONIBLE = True
except ImportError:
    SKLEARN_DISPONIBLE = False


DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data")
PERFILES_DIR = os.path.join(DATA_DIR, "perfiles")
CV_DIR = os.path.join(DATA_DIR, "cv")
BOARDS_JSON = os.path.join(DATA_DIR, "greenhouse_boards.json")


# ============================================================================
# Perfil de postulación (se llena UNA vez; es lo que amortiza la fricción)
# ============================================================================

PERFIL_VACIO = {
    "first_name": "",
    "last_name": "",
    "email": "",
    "phone": "",
    "ubicacion": "",
    "linkedin": "",
    "portfolio": "",
    "autorizado_trabajar": True,
    "requiere_sponsorship": False,
    "salario_esperado_usd": None,
    "disponibilidad": "Inmediata",
    "ocupacion_actual": "",
    "experiencia_años": 0,
    "skills": [],
    "cv_texto": "",
    "cv_path": "",
}


def _ruta_perfil(user_id):
    return os.path.join(PERFILES_DIR, f"{user_id}.json")


def cargar_perfil(user_id):
    try:
        with open(_ruta_perfil(user_id), encoding="utf-8") as f:
            return {**PERFIL_VACIO, **json.load(f)}
    except FileNotFoundError:
        return None


def guardar_perfil(user_id, datos):
    os.makedirs(PERFILES_DIR, exist_ok=True)
    perfil = {**PERFIL_VACIO, **(cargar_perfil(user_id) or {}), **datos}
    perfil["user_id"] = user_id
    with open(_ruta_perfil(user_id), "w", encoding="utf-8") as f:
        json.dump(perfil, f, ensure_ascii=False, indent=2)
    return perfil


def perfil_completo(perfil):
    """Campos sin los cuales ninguna postulación de Greenhouse sale adelante."""
    faltan = [c for c in ("first_name", "last_name", "email") if not perfil.get(c)]
    return (not faltan), faltan


def _mapear_cv_estructurado(estructurado):
    """El JSON que devuelve cv_parser (mismo formato que /analizar) -> campos
    del perfil de postulación. A propósito NO toca email ni teléfono: esos son
    datos de identidad y se mantienen manuales (ver applier/answers.py)."""
    datos = {}

    nombre = (estructurado.get("nombre") or "").strip()
    if nombre:
        partes = nombre.split()
        datos["first_name"] = partes[0]
        datos["last_name"] = " ".join(partes[1:])

    if estructurado.get("ocupacion_actual"):
        datos["ocupacion_actual"] = estructurado["ocupacion_actual"]
    if estructurado.get("ubicacion"):
        datos["ubicacion"] = estructurado["ubicacion"]
    if isinstance(estructurado.get("experiencia_años"), (int, float)):
        datos["experiencia_años"] = estructurado["experiencia_años"]
    if estructurado.get("skills_identificadas"):
        datos["skills"] = estructurado["skills_identificadas"]

    return datos


def _guardar_archivo_cv(user_id, archivo, filename):
    """Guarda el archivo original del CV en data/cv/. Lo necesita el submitter
    para adjuntarlo en el formulario de Greenhouse (que pide un archivo, no
    texto)."""
    os.makedirs(CV_DIR, exist_ok=True)
    extension = os.path.splitext(filename)[1].lower() or ".pdf"
    destino = os.path.join(CV_DIR, f"{user_id}{extension}")
    archivo.seek(0)
    archivo.save(destino)
    archivo.seek(0)
    return destino


def importar_cv(user_id, archivo, filename):
    """Extrae el CV subido, lo estructura con Gemini (si hay API key) y lo
    fusiona en el perfil de postulación. Devuelve el perfil actualizado.

    Guarda tres cosas del CV:
    - `cv_texto`: contexto para que el agente redacte las respuestas abiertas.
    - `cv_path`: el archivo original, para adjuntarlo en el formulario.
    - campos estructurados (ocupación, skills, etc.) si Gemini está disponible.
    """
    from cv_parser import extraer_texto, estructurar_con_gemini

    cv_path = _guardar_archivo_cv(user_id, archivo, filename)

    texto = extraer_texto(archivo, filename)
    if not texto.strip():
        raise ValueError(
            "No se pudo extraer texto del archivo (¿es un PDF escaneado como imagen?)"
        )

    datos = {"cv_texto": texto[:8000], "cv_path": cv_path}

    try:
        datos.update(_mapear_cv_estructurado(estructurar_con_gemini(texto)))
    except Exception as e:
        # Sin GEMINI_API_KEY o si Gemini falla: igual guardamos el texto para
        # que el agente tenga contexto; los campos estructurados se completan
        # a mano.
        print(f"[applier] CV subido pero no estructurado: {e}")

    return guardar_perfil(user_id, datos)


def asegurar_cv_path(perfil):
    """Devuelve una ruta a un archivo de CV para adjuntar. Si el usuario subió
    uno, es ese. Si solo tenemos el texto (vino de /analizar), generamos un
    .txt al vuelo: Greenhouse acepta .txt como CV."""
    ruta = perfil.get("cv_path")
    if ruta and os.path.exists(ruta):
        return ruta

    texto = perfil.get("cv_texto")
    if not texto:
        return None

    os.makedirs(CV_DIR, exist_ok=True)
    destino = os.path.join(CV_DIR, f"{perfil.get('user_id', 'anon')}_generado.txt")
    with open(destino, "w", encoding="utf-8") as f:
        f.write(texto)
    return destino


def perfil_desde_analisis(user_id, cv_analisis):
    """Reusa el resultado del análisis de CV de /analizar (el objeto `cv` que
    el front guarda en localStorage) para poblar el perfil sin volver a pedir
    los datos. No trae texto crudo: /analizar no lo expone."""
    return guardar_perfil(user_id, _mapear_cv_estructurado(cv_analisis or {}))


# ============================================================================
# Boards objetivo
# ============================================================================

def cargar_boards():
    try:
        with open(BOARDS_JSON, encoding="utf-8") as f:
            return json.load(f).get("boards", [])
    except FileNotFoundError:
        return []


# ============================================================================
# Búsqueda + ranking
# ============================================================================

def _texto_perfil(perfil):
    partes = [
        perfil.get("ocupacion_actual", ""),
        " ".join(perfil.get("skills", [])),
        (perfil.get("cv_texto") or "")[:4000],
    ]
    return " ".join(p for p in partes if p).strip()


def buscar_ofertas(perfil, limite=15):
    """Trae las ofertas de todos los boards configurados y las ordena por
    afinidad con el perfil."""
    ofertas = []
    for board in cargar_boards():
        ofertas.extend(greenhouse.listar_ofertas(board["token"]))

    if not ofertas:
        return {"ofertas": [], "total_revisadas": 0, "metodo": "sin ofertas disponibles"}

    texto_perfil = _texto_perfil(perfil)

    if SKLEARN_DISPONIBLE and texto_perfil:
        corpus = [texto_perfil] + [
            f"{o['titulo']} {o['ubicacion']}" for o in ofertas
        ]
        matriz = TfidfVectorizer(stop_words="english").fit_transform(corpus)
        similitudes = cosine_similarity(matriz[0:1], matriz[1:])[0]
        for oferta, similitud in zip(ofertas, similitudes):
            oferta["afinidad_pct"] = round(float(similitud) * 100, 1)
        metodo = "TF-IDF + coseno entre tu CV y el título de cada oferta"
    else:
        for oferta in ofertas:
            oferta["afinidad_pct"] = None
        metodo = "sin ranking (falta scikit-learn o perfil sin CV)"

    ofertas.sort(key=lambda o: o.get("afinidad_pct") or 0, reverse=True)

    return {
        "ofertas": ofertas[:limite],
        "total_revisadas": len(ofertas),
        "metodo": metodo,
    }


# ============================================================================
# Preparar una postulación concreta
# ============================================================================

def preparar_postulacion(perfil, board_token, job_id):
    oferta = greenhouse.obtener_oferta(board_token, job_id)
    borrador = construir_borrador(perfil, oferta)
    borrador["payload"] = payload_de_envio(borrador)
    return borrador

# -*- coding: utf-8 -*-
"""
agente_postulacion.py — Simula un agente que postula automáticamente
al usuario Premium a las vacantes/industrias donde mejor matchea,
generando una carta de presentación personalizada con Gemini.

IMPORTANTE (para ser honestos en el pitch): esto NO se conecta a bolsas
de empleo externas reales (LinkedIn, Indeed, etc.) — esas no permiten
automatizar postulaciones vía scraping/bots sin violar sus términos.
Lo que hace es simular el flujo completo dentro de nuestro propio pool
de vacantes/empresas demo, con generación de contenido real (no fake).
"""
import os
from datetime import datetime

import google.generativeai as genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Postulaciones en memoria (para producción: tabla en BD)
postulaciones_por_usuario = {}  # {user_id: [postulacion, ...]}

PROMPT_CARTA = """Eres un asistente que escribe cartas de presentación breves y efectivas.

Datos del candidato:
- Nombre: {nombre}
- Ocupación actual: {ocupacion_actual}
- Experiencia: {experiencia_años} años
- Skills: {skills}

Vacante a la que postula:
- Puesto: {puesto}
- Empresa: {empresa}
- Skills requeridas: {skills_requeridas}

Escribe una carta de presentación de máximo 120 palabras, en español, profesional
pero cercana, destacando cómo la experiencia del candidato conecta con el puesto.
No inventes datos que no te di. Responde SOLO con el texto de la carta, sin
encabezados ni firma."""


def generar_carta(candidato: dict, vacante: dict) -> str:
    if not GEMINI_API_KEY:
        return f"[Carta simulada] Estimado equipo de {vacante['empresa']}, postulo con interés al puesto de {vacante['puesto']}..."

    modelo = genai.GenerativeModel("gemini-flash-latest")
    prompt = PROMPT_CARTA.format(
        nombre=candidato.get("nombre", ""),
        ocupacion_actual=candidato.get("ocupacion_actual", ""),
        experiencia_años=candidato.get("experiencia_años", ""),
        skills=", ".join(candidato.get("skills_identificadas", candidato.get("skills", []))),
        puesto=vacante["puesto"],
        empresa=vacante["empresa"],
        skills_requeridas=", ".join(vacante.get("skills_requeridas", [])),
    )
    respuesta = modelo.generate_content(prompt)
    return respuesta.text.strip()


def ejecutar_agente(candidato: dict, vacantes_candidatas: list, top_n: int = 3) -> list:
    """
    candidato: dict del CV parseado (viene de cv_parser.py o de CV_EJEMPLOS)
    vacantes_candidatas: lista de vacantes demo [{puesto, empresa, skills_requeridas, region}, ...]
    Devuelve la lista de postulaciones "enviadas", cada una con su carta generada.
    """
    resultados = []
    for vacante in vacantes_candidatas[:top_n]:
        carta = generar_carta(candidato, vacante)
        postulacion = {
            "puesto": vacante["puesto"],
            "empresa": vacante["empresa"],
            "carta_presentacion": carta,
            "fecha": datetime.now().isoformat(),
            "estado": "enviada",
        }
        resultados.append(postulacion)

    user_id = candidato.get("user_id", "anonimo")
    postulaciones_por_usuario.setdefault(user_id, []).extend(resultados)
    return resultados


def obtener_postulaciones(user_id: str) -> list:
    return postulaciones_por_usuario.get(user_id, [])

# -*- coding: utf-8 -*-
"""
greenhouse.py — Cliente de la Job Board API pública de Greenhouse.

Greenhouse expone el listado de ofertas de cada empresa sin autenticación:

    GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs
    GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs/{id}?questions=true

El segundo endpoint es el que hace viable a este agente: devuelve el esquema
COMPLETO del formulario de postulación (cada pregunta, su tipo, si es
obligatoria y — en los selects — las opciones válidas). O sea, no hay que
scrapear el HTML para saber qué pide cada oferta.

Nota sobre el envío: el POST documentado de Greenhouse
(`POST /v1/boards/{token}/jobs/{id}`) exige la Job Board API key DE LA EMPRESA,
que como terceros no tenemos. Por eso este MVP llega hasta el borrador y deja
el envío real como paso manual de 1 clic (ver applier/answers.py).
"""
import html
import re
import time

import requests

BASE = "https://boards-api.greenhouse.io/v1/boards"
TIMEOUT = 15

# Caché en memoria {url: (timestamp, payload)} — evita martillar la API de
# Greenhouse mientras el usuario navega la UI. 15 min es de sobra para un
# listado de ofertas que cambia como mucho una vez al día.
_cache = {}
CACHE_TTL = 15 * 60


def _get(url):
    ahora = time.time()
    if url in _cache:
        guardado_en, payload = _cache[url]
        if ahora - guardado_en < CACHE_TTL:
            return payload

    respuesta = requests.get(url, headers={"User-Agent": "PROXIMO/1.0"}, timeout=TIMEOUT)
    respuesta.raise_for_status()
    payload = respuesta.json()

    _cache[url] = (ahora, payload)
    return payload


def limpiar_html(texto):
    """La descripción viene como HTML escapado; la queremos en texto plano
    para el matching TF-IDF y para el prompt de Gemini."""
    if not texto:
        return ""
    plano = html.unescape(texto)
    plano = re.sub(r"<[^>]+>", " ", plano)
    return re.sub(r"\s+", " ", plano).strip()


def listar_ofertas(board_token):
    """Devuelve las ofertas de una empresa: título, ubicación y URL.

    A propósito NO pedimos `?content=true`: los boards grandes tienen cientos
    de ofertas y traer el cuerpo completo de cada una son megabytes y decenas
    de segundos. Para rankear el listado alcanza con el título; la descripción
    se baja después, solo para la oferta que el usuario elige (obtener_oferta).

    Si un board no existe o falla, devuelve lista vacía en vez de romper el
    barrido de los demás.
    """
    try:
        datos = _get(f"{BASE}/{board_token}/jobs")
    except Exception as e:
        print(f"[greenhouse] no se pudo leer el board '{board_token}': {e}")
        return []

    ofertas = []
    for job in datos.get("jobs", []):
        ofertas.append({
            "board_token": board_token,
            "id": job["id"],
            "titulo": job.get("title", ""),
            "empresa": job.get("company_name") or board_token,
            "ubicacion": (job.get("location") or {}).get("name", ""),
            "url": job.get("absolute_url", ""),
            "actualizado": job.get("updated_at", ""),
        })
    return ofertas


def obtener_oferta(board_token, job_id):
    """Oferta individual CON el esquema de preguntas del formulario."""
    datos = _get(f"{BASE}/{board_token}/jobs/{job_id}?questions=true")
    return {
        "board_token": board_token,
        "id": datos["id"],
        "titulo": datos.get("title", ""),
        "empresa": datos.get("company_name") or board_token,
        "ubicacion": (datos.get("location") or {}).get("name", ""),
        "url": datos.get("absolute_url", ""),
        "descripcion": limpiar_html(datos.get("content", "")),
        "preguntas": datos.get("questions", []),
        "preguntas_demograficas": datos.get("demographic_questions"),
        "compliance": datos.get("compliance", []),
    }

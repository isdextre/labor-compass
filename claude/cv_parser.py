# -*- coding: utf-8 -*-
"""
cv_parser.py — Extrae texto de un CV (PDF/DOCX/TXT) y lo estructura
con Gemini en el mismo formato que ya usa el resto del sistema.
"""
import io
import json
import os

import google.generativeai as genai

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


def extraer_texto(archivo, filename: str) -> str:
    """archivo: el objeto FileStorage que llega de request.files"""
    extension = filename.lower().split(".")[-1]

    if extension == "pdf":
        import PyPDF2
        lector = PyPDF2.PdfReader(archivo)
        return "\n".join(pagina.extract_text() or "" for pagina in lector.pages)

    elif extension == "docx":
        import docx
        documento = docx.Document(io.BytesIO(archivo.read()))
        return "\n".join(p.text for p in documento.paragraphs)

    elif extension == "txt":
        return archivo.read().decode("utf-8", errors="ignore")

    else:
        raise ValueError(f"Formato no soportado: .{extension} (usa PDF, DOCX o TXT)")


PROMPT_ESTRUCTURA = """Eres un extractor de datos de CVs. Analiza el siguiente texto de un CV
y devuelve SOLO un JSON válido (sin texto extra, sin markdown, sin ```), con esta estructura exacta:

{{
  "nombre": "string",
  "ocupacion_actual": "string (en inglés, título de ocupación tipo LinkedIn, ej: 'Data Analyst')",
  "experiencia_años": number,
  "salario_actual_usd": number o null si no se menciona,
  "skills_identificadas": ["skill1", "skill2", ...],
  "certificaciones": ["cert1", ...] o [] si no hay,
  "ubicacion": "string, ciudad/región",
  "educacion": "string, nivel/título más alto o 'N/A'"
}}

Texto del CV:
---
{texto_cv}
---

Responde SOLO el JSON, nada más."""


def estructurar_con_gemini(texto_cv: str) -> dict:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY no configurada en el entorno.")

    modelo = genai.GenerativeModel("gemini-1.5-flash")
    respuesta = modelo.generate_content(PROMPT_ESTRUCTURA.format(texto_cv=texto_cv[:8000]))

    texto_respuesta = respuesta.text.strip()
    # Por si Gemini igual envuelve en ```json ... ```
    if texto_respuesta.startswith("```"):
        texto_respuesta = texto_respuesta.strip("`")
        texto_respuesta = texto_respuesta.replace("json\n", "", 1).strip()

    return json.loads(texto_respuesta)


def parsear_cv(archivo, filename: str) -> dict:
    texto = extraer_texto(archivo, filename)
    if not texto.strip():
        raise ValueError("No se pudo extraer texto del archivo (¿es un PDF escaneado como imagen?)")
    datos = estructurar_con_gemini(texto)
    return datos

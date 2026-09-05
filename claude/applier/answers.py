# -*- coding: utf-8 -*-
"""
answers.py — Motor de respuestas: perfil del usuario -> formulario de una oferta.

Aquí Gemini actúa como AGENTE, no como generador de texto. Greenhouse nos
entrega el esquema completo de preguntas de cada oferta (etiqueta, tipo,
obligatoriedad y opciones válidas de cada select), así que le pasamos a Gemini
ese esquema junto con el perfil del usuario y le pedimos que resuelva el
formulario campo por campo, declarando para cada uno de dónde salió la
respuesta:

    origen = "perfil"  -> dato factual que estaba en el perfil del usuario
    origen = "ia"      -> texto que el modelo tuvo que redactar (requiere revisión)
    origen = "falta"   -> el perfil no tiene esa información (no se inventa)

Dos salvaguardas sobre el agente, porque esto se envía a nombre de una persona
real a un empleador real:

1. Los campos de identidad (nombre, apellido, email, teléfono, CV) NO pasan por
   Gemini. Se copian del perfil de forma determinista. Un modelo no debe poder
   alucinar el email al que van a responderle a alguien.
2. Todo lo que devuelve Gemini se VALIDA contra el esquema antes de aceptarse:
   en un select, la respuesta tiene que ser una de las opciones que Greenhouse
   declaró; si no lo es, el campo cae a "falta". El agente propone, el código
   verifica.

Si no hay GEMINI_API_KEY, el módulo cae a un set de reglas por regex sobre la
etiqueta de la pregunta: cubre menos casos, pero deja la demo funcionando.

De la clasificación de los campos sale el semáforo de la postulación:

    "auto"      -> todo salió del perfil: se podría enviar sin intervención
    "revisar"   -> hay texto generado: el usuario debe leerlo antes de enviar
    "bloqueado" -> falta un campo obligatorio: hay que completar el perfil
"""
import json
import os
import re
import unicodedata

try:
    import google.generativeai as genai
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
except ImportError:
    genai = None
    GEMINI_API_KEY = None


# ============================================================================
# Capa determinista: identidad (nunca pasa por el modelo)
# ============================================================================

CAMPOS_IDENTIDAD = {
    "first_name": "first_name",
    "last_name": "last_name",
    "email": "email",
    "phone": "phone",
}


def _norm(texto):
    """Normaliza para comparar respuestas contra las opciones de un select.

    Quita acentos a propósito: los catálogos de Greenhouse están en inglés
    ("Peru", "Mexico") y el agente responde desde un perfil en español
    ("Perú", "México"). Sin esto, la respuesta correcta se descartaba como
    inválida y la oferta quedaba bloqueada por un país que sí existía.
    """
    plano = unicodedata.normalize("NFKD", texto or "")
    plano = "".join(c for c in plano if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", plano.lower()).strip()


def _resolver_identidad(perfil, campo):
    """Devuelve (valor, origen) si el campo es de identidad; None si no lo es."""
    nombre = campo.get("name", "")

    if nombre in CAMPOS_IDENTIDAD:
        valor = perfil.get(CAMPOS_IDENTIDAD[nombre])
        return (valor, "perfil" if valor else "falta")

    if nombre == "resume" and campo.get("type") == "input_file":
        return ("[CV adjunto]" if perfil.get("cv_texto") else None,
                "perfil" if perfil.get("cv_texto") else "falta")

    return None


# ============================================================================
# El agente: Gemini resuelve el resto del formulario
# ============================================================================

PROMPT_AGENTE = """Eres el agente de postulaciones de un candidato. Tu trabajo es
RESOLVER el formulario de una oferta de empleo usando únicamente la información
del perfil del candidato.

PERFIL DEL CANDIDATO (única fuente de verdad sobre la persona):
{perfil}

OFERTA: {titulo} — {empresa} ({ubicacion})
DESCRIPCIÓN (extracto):
{descripcion}

CAMPOS A RESOLVER:
{campos}

REGLAS ESTRICTAS:
1. Nunca inventes hechos sobre el candidato: años de experiencia, títulos,
   empresas, certificaciones, salarios o fechas que no estén en el perfil.
2. Si el campo es de tipo "multi_value_single_select" o "multi_value_multi_select",
   el valor DEBE ser exactamente una de las opciones listadas, copiada literal.
3. Clasifica cada respuesta con "origen":
   - "perfil": la respuesta es un dato que está en el perfil, o la elección de
     una opción que se deduce directamente de un dato del perfil.
   - "ia": tuviste que redactar prosa nueva (cartas de motivación, "por qué
     quieres trabajar aquí", descripciones de proyectos).
   - "falta": el perfil no tiene la información necesaria. Prefiere "falta"
     antes que inventar.
4. Para las preguntas abiertas responde en 3-4 oraciones, en primera persona,
   en el mismo idioma de la pregunta, concreto y sin exagerar.
5. Preguntas demográficas o de diversidad (género, etnia, veteranía,
   discapacidad): elige la opción de "prefiero no responder" si existe; si no,
   marca "falta".
6. Preguntas que no son un hecho sobre el candidato sino administrativas
   —"¿cómo te enteraste de este puesto?", fuente de referencia, canal de
   contacto— NO son "falta": elige una opción válida y neutral como "Other",
   "Job Board" o "LinkedIn", con origen "perfil".

Devuelve SOLO un JSON válido, sin markdown, con esta forma exacta:
{{"nombre_del_campo": {{"valor": "...", "origen": "perfil|ia|falta", "razon": "breve"}}, ...}}
Usa como claves exactamente los nombres de campo indicados entre corchetes."""


def _describir_campo(pregunta, campo):
    """Serializa un campo del esquema de Greenhouse para el prompt."""
    linea = f"- [{campo.get('name')}] \"{pregunta.get('label')}\""
    linea += f" (tipo: {campo.get('type')}"
    linea += ", obligatorio)" if pregunta.get("required") else ", opcional)"

    descripcion = _limpiar(pregunta.get("description"))
    if descripcion:
        linea += f"\n    contexto: {descripcion}"

    opciones = campo.get("values", [])
    if opciones:
        etiquetas = ", ".join(f'"{o.get("label")}"' for o in opciones[:25])
        linea += f"\n    opciones válidas: {etiquetas}"
    return linea


def _limpiar(texto):
    if not texto:
        return ""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", texto)).strip()


def _resumen_perfil(perfil):
    return json.dumps({
        "nombre": f"{perfil.get('first_name', '')} {perfil.get('last_name', '')}".strip(),
        "email": perfil.get("email"),
        "telefono": perfil.get("phone"),
        "ubicacion": perfil.get("ubicacion"),
        "linkedin": perfil.get("linkedin"),
        "portafolio": perfil.get("portfolio"),
        "ocupacion_actual": perfil.get("ocupacion_actual"),
        "experiencia_años": perfil.get("experiencia_años"),
        "skills": perfil.get("skills", []),
        "autorizado_a_trabajar": perfil.get("autorizado_trabajar"),
        "requiere_sponsorship_de_visa": perfil.get("requiere_sponsorship"),
        "salario_esperado_usd_mes": perfil.get("salario_esperado_usd"),
        "disponibilidad": perfil.get("disponibilidad"),
        "cv": (perfil.get("cv_texto") or "")[:3000],
    }, ensure_ascii=False, indent=2)


def _invocar_agente(perfil, oferta, pendientes):
    """Una sola llamada a Gemini con todo el formulario: más barato que una
    llamada por campo y las respuestas quedan coherentes entre sí."""
    if not pendientes or not (genai and GEMINI_API_KEY):
        return {}

    prompt = PROMPT_AGENTE.format(
        perfil=_resumen_perfil(perfil),
        titulo=oferta.get("titulo", ""),
        empresa=oferta.get("empresa", ""),
        ubicacion=oferta.get("ubicacion", ""),
        descripcion=(oferta.get("descripcion") or "")[:3000],
        campos="\n".join(_describir_campo(p, c) for p, c in pendientes),
    )

    try:
        modelo = genai.GenerativeModel("gemini-flash-latest")
        texto = modelo.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"},
        ).text.strip()
        if texto.startswith("```"):
            texto = texto.strip("`").replace("json\n", "", 1).strip()
        return json.loads(texto)
    except Exception as e:
        print(f"[answers] el agente Gemini falló, se usan las reglas locales: {e}")
        return {}


def _validar(propuesta, campo):
    """El agente propone, el código verifica.

    Devuelve (valor, origen) ya saneado. En un select fuerza que la respuesta
    sea una opción real del catálogo de Greenhouse: si el modelo se inventó una
    etiqueta, el campo cae a "falta" en vez de mandar basura al empleador.
    """
    if not isinstance(propuesta, dict):
        return None, "falta"

    valor = propuesta.get("valor")
    origen = propuesta.get("origen")

    if origen not in ("perfil", "ia") or valor in (None, "", "null"):
        return None, "falta"

    opciones = campo.get("values", [])
    if opciones:
        for opcion in opciones:
            if _norm(opcion.get("label")) == _norm(str(valor)):
                return opcion.get("value"), origen
        return None, "falta"   # etiqueta inventada: se descarta

    return valor, origen


# ============================================================================
# Fallback sin API key: reglas por regex sobre la etiqueta
# ============================================================================

def _elegir_opcion(opciones, candidatos):
    for candidato in candidatos:
        objetivo = _norm(candidato)
        for opcion in opciones:
            if _norm(opcion.get("label")) == objetivo:
                return opcion.get("value")
    for candidato in candidatos:
        objetivo = _norm(candidato)
        for opcion in opciones:
            if objetivo and objetivo in _norm(opcion.get("label")):
                return opcion.get("value")
    return None


def _si_no(opciones, valor_bool):
    return _elegir_opcion(opciones, ["Yes", "Sí", "Si"] if valor_bool else ["No"])


REGLAS = [
    (r"linkedin", lambda p, c: p.get("linkedin")),
    (r"github", lambda p, c: p.get("portfolio")),
    (r"website|portfolio|personal site", lambda p, c: p.get("portfolio")),
    (r"authoriz(ed|ation) to work|legally authorized|right to work",
     lambda p, c: _si_no(c.get("values", []), p.get("autorizado_trabajar", True))),
    (r"sponsorship|visa|work permit",
     lambda p, c: _si_no(c.get("values", []), p.get("requiere_sponsorship", False))),
    (r"salary|compensation|pretensi|expected pay",
     lambda p, c: p.get("salario_esperado_usd")),
    (r"where.*work|current location|city|located|based", lambda p, c: p.get("ubicacion")),
    (r"worked (for|at).*(before|previously)|previously (employed|worked)",
     lambda p, c: _si_no(c.get("values", []), False)),
    (r"how did you hear|referral source|source",
     lambda p, c: _elegir_opcion(c.get("values", []), ["Other", "Job Board", "LinkedIn"])),
    (r"start date|availability|notice period|when can you", lambda p, c: p.get("disponibilidad")),
    (r"years of experience|años de experiencia", lambda p, c: p.get("experiencia_años")),
]


# Preguntas obligatorias que no son un hecho verificable sobre el candidato:
# cualquier opción válida es una respuesta honesta. Se listan explícitamente
# para no caer en la tentación de auto-responder cualquier select bloqueado.
PATRONES_ADMINISTRATIVOS = (
    r"how did you hear|how do you hear|where did you hear",
    r"referral source|source of (referral|application)|how were you referred",
    r"c[oó]mo te enteraste|d[oó]nde viste|fuente de",
)

OPCIONES_NEUTRALES = ("Other", "Otro", "Job Board", "Job Boards", "LinkedIn",
                      "Company Website", "Other (please specify)")


def _opcion_administrativa(pregunta, campo):
    """Si la pregunta es administrativa y obligatoria, devuelve el value de una
    opción neutral válida. None si no aplica o no hay opción razonable."""
    etiqueta = _norm(pregunta.get("label"))
    if not any(re.search(p, etiqueta) for p in PATRONES_ADMINISTRATIVOS):
        return None
    return _elegir_opcion(campo.get("values", []), list(OPCIONES_NEUTRALES))


def _resolver_por_reglas(perfil, pregunta, campo):
    etiqueta = _norm(pregunta.get("label"))
    for patron, resolver in REGLAS:
        if not re.search(patron, etiqueta):
            continue

        valor = resolver(perfil, campo)
        if valor in (None, ""):
            return None, "falta"

        # Misma salvaguarda que con el agente: en un select la respuesta tiene
        # que ser una opción real. Sin esto, una regla como la de ubicación
        # contesta "Lima, Perú" a un desplegable de países y Greenhouse lo
        # rechaza (o peor, se envía un campo inválido).
        opciones = campo.get("values", [])
        if opciones and not any(o.get("value") == valor for o in opciones):
            elegida = _elegir_opcion(opciones, [str(valor)])
            return (elegida, "perfil") if elegida is not None else (None, "falta")

        return valor, "perfil"
    return None, "falta"


# ============================================================================
# API pública del módulo
# ============================================================================

def construir_borrador(perfil, oferta):
    """Resuelve el formulario completo de una oferta contra el perfil.

    Devuelve un dict listo para pintar en la UI, con el semáforo ya calculado.
    """
    campos_resueltos = []
    pendientes = []          # [(pregunta, campo)] que va a resolver el agente

    for pregunta in oferta.get("preguntas", []):
        for campo in pregunta.get("fields", []):
            # Greenhouse ofrece el CV como archivo O como textarea; con el
            # archivo basta, no duplicamos pidiendo también resume_text.
            if campo.get("name") == "resume_text":
                continue

            registro = {
                "name": campo.get("name"),
                "label": pregunta.get("label"),
                "descripcion": _limpiar(pregunta.get("description")),
                "tipo": campo.get("type"),
                "requerido": pregunta.get("required", False),
                "valor": None,
                "origen": "falta",
                "opciones": [
                    {"label": o.get("label"), "value": o.get("value")}
                    for o in campo.get("values", [])
                ],
            }

            identidad = _resolver_identidad(perfil, campo)
            if identidad is not None:
                registro["valor"], registro["origen"] = identidad
            else:
                pendientes.append((pregunta, campo, registro))

            campos_resueltos.append(registro)

    # ---- El agente resuelve todo lo demás en una sola llamada -----------
    usando_agente = bool(genai and GEMINI_API_KEY) and bool(pendientes)
    propuestas = _invocar_agente(
        perfil, oferta, [(p, c) for p, c, _ in pendientes]
    ) if usando_agente else {}

    for pregunta, campo, registro in pendientes:
        if propuestas:
            valor, origen = _validar(propuestas.get(registro["name"]), campo)
        else:
            valor, origen = _resolver_por_reglas(perfil, pregunta, campo)

        # Red de seguridad para preguntas administrativas obligatorias
        # ("¿cómo te enteraste del puesto?"): no son un hecho del candidato,
        # cualquier opción válida sirve, y dejarlas en "falta" bloqueaba la
        # postulación entera por un desplegable intrascendente.
        if origen == "falta" and registro["requerido"] and campo.get("values"):
            valor_alterno = _opcion_administrativa(pregunta, campo)
            if valor_alterno is not None:
                valor, origen = valor_alterno, "perfil"

        registro["valor"], registro["origen"] = valor, origen

    # ---- Semáforo -------------------------------------------------------
    faltan_requeridos = [
        c["label"] for c in campos_resueltos
        if c["requerido"] and c["origen"] == "falta"
    ]
    hay_ia = any(c["origen"] == "ia" for c in campos_resueltos)

    if faltan_requeridos:
        modo = "bloqueado"
    elif hay_ia:
        modo = "revisar"
    else:
        modo = "auto"

    return {
        "oferta": {
            "id": oferta.get("id"),
            "board_token": oferta.get("board_token"),
            "titulo": oferta.get("titulo"),
            "empresa": oferta.get("empresa"),
            "ubicacion": oferta.get("ubicacion"),
            "url": oferta.get("url"),
        },
        "modo": modo,
        "motivo_bloqueo": faltan_requeridos,
        "resuelto_por": "gemini" if usando_agente else "reglas locales (sin GEMINI_API_KEY)",
        "campos": campos_resueltos,
        "resumen": {
            "total": len(campos_resueltos),
            "del_perfil": sum(1 for c in campos_resueltos if c["origen"] == "perfil"),
            "generados_ia": sum(1 for c in campos_resueltos if c["origen"] == "ia"),
            "sin_resolver": sum(1 for c in campos_resueltos if c["origen"] == "falta"),
        },
    }


def payload_de_envio(borrador):
    """El multipart exacto que se le mandaría a Greenhouse.

    En este MVP no se envía: se muestra para que el usuario vea qué se iba a
    mandar y postule con un clic desde `oferta.url`. El POST real requiere la
    Job Board API key de cada empresa (ver applier/greenhouse.py).
    """
    return {
        campo["name"]: campo["valor"]
        for campo in borrador["campos"]
        if campo["valor"] not in (None, "")
    }

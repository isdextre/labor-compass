# -*- coding: utf-8 -*-
"""
submitter.py — Envía la postulación llenando el formulario público de Greenhouse
con un navegador headless (Playwright).

Por qué esta vía y no la API: el POST documentado de Greenhouse exige la Job
Board API key de cada empresa, que como terceros no tenemos. El formulario
público de la página de carrera, en cambio, lo usa cualquier postulante sin
login ni key — y ese sí se puede automatizar.

Lo que NO se puede sortear con código, y por eso el submitter se detiene y lo
reporta en vez de "resolverlo":

- reCAPTCHA: si el board lo activa y salta un challenge, hace falta un humano
  (o un servicio de resolución pago). El submitter devuelve estado
  "bloqueado_captcha".
- Verificación por email: algunos boards mandan un correo que hay que confirmar
  para que la postulación cuente. Estado "bloqueado_verificacion_email".

Modos:
- "dry_run" (por defecto): llena todo el formulario y saca captura, pero NO
  hace clic en enviar. Sirve para ver exactamente qué se mandaría.
- "enviar": llena y envía de verdad.

Salvaguarda: `enviar_una` solo pulsa "enviar" si el borrador está en modo
"auto" (todos los campos salieron del perfil, sin texto de IA) o si se pasa
`permitir_revisar=True` de forma explícita — que es lo que hace el botón
"Enviar" de una postulación que el usuario ya revisó campo por campo.
"""
import os
import time

FALLBACK_URL = "https://job-boards.greenhouse.io/{token}/jobs/{job_id}"

# Estados terminales que devuelve enviar_una()
SIMULADO = "simulado"                       # dry_run: se llenó, no se envió
ENVIADO = "enviado"                         # confirmación de Greenhouse recibida
BLOQUEADO_CAPTCHA = "bloqueado_captcha"
BLOQUEADO_EMAIL = "bloqueado_verificacion_email"
RECHAZADO_FORM = "rechazado_por_formulario"  # Greenhouse marcó campos inválidos
SIN_SOPORTE = "no_soportado"                 # la empresa usa su propio sitio de carreras
ERROR = "error"


def _url_formulario(oferta):
    """Devuelve la URL del formulario de Greenhouse, o None si la empresa no
    usa un board hospedado por Greenhouse.

    Algunas empresas (Stripe, Databricks, Duolingo…) integran Greenhouse por
    detrás pero sirven el formulario desde su propio dominio, con maquetación
    propia. Ese no lo podemos automatizar de forma genérica, así que lo
    marcamos 'no_soportado' en vez de fallar con un timeout.
    """
    url = oferta.get("url", "")
    if "boards.greenhouse.io" in url or "job-boards.greenhouse.io" in url:
        return url.split("?")[0]
    if "greenhouse.io" in url:
        return url.split("?")[0]
    return None


def _mapear_valor_a_label(campo):
    """Un select del borrador trae `valor` = el value numérico de Greenhouse.
    El formulario web se maneja por el texto visible, así que lo traducimos."""
    valor = campo.get("valor")
    for opcion in campo.get("opciones", []):
        if str(opcion.get("value")) == str(valor):
            return opcion.get("label")
    return str(valor) if valor is not None else None


def _rellenar_select(page, campo):
    """Selecciona una opción en un combobox react-select de Greenhouse.

    El input del combobox lleva el MISMO id que el campo (role="combobox"),
    así que se llega a él con `#question_XXXX`. La secuencia que funciona es:
    click -> escribir el texto -> esperar a que aparezca el menú -> hacer clic
    en la opción. Confirmar con Enter es menos fiable: si el menú todavía no
    filtró, no selecciona nada y el campo queda vacío, que es justo lo que
    hacía que Greenhouse rechazara el formulario por campos obligatorios.

    Al final se verifica leyendo el `.select__single-value`, que es el texto
    que el propio componente pinta una vez que la opción quedó elegida.
    """
    etiqueta = _mapear_valor_a_label(campo)
    if not etiqueta:
        return False

    nombre = campo["name"]
    try:
        combo = page.locator(f"#{nombre}")
        combo.click()
        combo.press_sequentially(str(etiqueta), delay=35)
        page.wait_for_timeout(700)

        opciones = page.locator(f'[id^="react-select-{nombre}-option"]')
        if not opciones.count():
            print(f"[submitter] select '{nombre}': sin opciones para '{etiqueta}'")
            return False

        # Preferimos la opción cuyo texto coincide exacto; si no, la primera.
        elegido = opciones.first
        for i in range(opciones.count()):
            if opciones.nth(i).inner_text().strip().lower() == str(etiqueta).strip().lower():
                elegido = opciones.nth(i)
                break
        elegido.click()
        page.wait_for_timeout(350)

        marcado = page.locator(f"#{nombre}").locator(
            'xpath=ancestor::div[contains(@class,"select__control")]'
            '//div[contains(@class,"select__single-value")]'
        )
        if not marcado.count() or not marcado.first.inner_text().strip():
            print(f"[submitter] select '{nombre}' quedó sin selección")
            return False
        return True
    except Exception as e:
        print(f"[submitter] select '{nombre}' no se pudo llenar: {e}")
        return False


# El widget de teléfono de Greenhouse trae su propio desplegable "Country"
# (#country) que NO viene en el esquema de preguntas de la API. Se autodetecta
# del prefijo +XX del teléfono; si el usuario guardó su número sin prefijo, el
# desplegable queda vacío y Greenhouse rechaza el formulario. Lo llenamos a
# mano desde la ubicación del perfil.
PAIS_ES_EN = {
    "peru": "Peru", "mexico": "Mexico", "espana": "Spain", "brasil": "Brazil",
    "argentina": "Argentina", "chile": "Chile", "colombia": "Colombia",
    "ecuador": "Ecuador", "bolivia": "Bolivia", "uruguay": "Uruguay",
    "paraguay": "Paraguay", "venezuela": "Venezuela", "costa rica": "Costa Rica",
    "panama": "Panama", "guatemala": "Guatemala", "republica dominicana":
    "Dominican Republic", "estados unidos": "United States",
    "reino unido": "United Kingdom", "alemania": "Germany", "francia": "France",
    "italia": "Italy", "canada": "Canada", "portugal": "Portugal",
}


def _sin_acentos(texto):
    import unicodedata
    plano = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in plano if not unicodedata.combining(c))


def _pais_del_perfil(perfil):
    """Deduce el país desde `ubicacion` ("Lima, Perú" -> "Peru"). Devuelve el
    nombre en inglés, que es como están los catálogos de Greenhouse."""
    ubicacion = perfil.get("ubicacion") or ""
    if not ubicacion:
        return None
    ultimo = _sin_acentos(ubicacion.split(",")[-1].strip()).lower()
    return PAIS_ES_EN.get(ultimo, ultimo.title() if ultimo else None)


def _rellenar_pais_telefono(page, perfil):
    """Selecciona el país del widget de teléfono si quedó vacío."""
    try:
        combo = page.locator("#country")
        if not combo.count():
            return None
        marcado = combo.locator(
            'xpath=ancestor::div[contains(@class,"select__control")]'
            '//div[contains(@class,"select__single-value")]'
        )
        if marcado.count() and marcado.first.inner_text().strip():
            return True   # ya se autodetectó del prefijo del teléfono

        pais = _pais_del_perfil(perfil)
        if not pais:
            return False

        combo.click()
        combo.press_sequentially(pais, delay=35)
        page.wait_for_timeout(700)
        opciones = page.locator('[id^="react-select-country-option"]')
        if not opciones.count():
            print(f"[submitter] país de teléfono: sin opciones para '{pais}'")
            return False
        opciones.first.click()
        page.wait_for_timeout(300)
        return bool(marcado.count() and marcado.first.inner_text().strip())
    except Exception as e:
        print(f"[submitter] país de teléfono no se pudo llenar: {e}")
        return False


def _rellenar_texto(page, campo):
    """Escribe en un input/textarea con eventos de teclado reales.

    NO se usa page.fill(): el formulario de Greenhouse es React con inputs
    controlados y descarta el valor que fill() inyecta — reporta éxito y el
    campo queda vacío. press_sequentially() dispara keydown/input de verdad,
    que es lo que React escucha. Después leemos el valor de vuelta para
    confirmar que quedó puesto.
    """
    selector = f'#{campo["name"]}'
    esperado = str(campo["valor"])
    try:
        elemento = page.locator(selector)
        elemento.click()
        elemento.press_sequentially(esperado, delay=12)
        page.wait_for_timeout(120)
        if page.input_value(selector).strip() == "":
            print(f"[submitter] campo '{campo['name']}' quedó vacío tras escribir")
            return False
        return True
    except Exception as e:
        print(f"[submitter] campo '{campo['name']}' no se pudo llenar: {e}")
        return False


def _hay_captcha_visible(page):
    """reCAPTCHA con challenge visible (el clásico 'selecciona los semáforos').
    El invisible no se ve; ese lo detectamos después de enviar."""
    for sel in ('iframe[title*="recaptcha challenge"]',
                'iframe[src*="recaptcha"][title*="challenge"]',
                'div.g-recaptcha-bubble-arrow'):
        try:
            if page.locator(sel).first.is_visible(timeout=500):
                return True
        except Exception:
            pass
    return False


def _diagnostico_post_envio(page):
    cuerpo = ""
    try:
        cuerpo = page.inner_text("body")[:4000].lower()
    except Exception:
        pass

    if any(t in cuerpo for t in ("thank you for applying", "application submitted",
                                 "we received your application", "gracias por postular",
                                 "your application has been submitted")):
        return ENVIADO
    if "verify your email" in cuerpo or "check your email" in cuerpo or \
       "confirma tu correo" in cuerpo:
        return BLOQUEADO_EMAIL
    if _hay_captcha_visible(page):
        return BLOQUEADO_CAPTCHA
    # Greenhouse pinta un resumen de errores si algún campo requerido falla
    try:
        if page.locator('[aria-invalid="true"], .field-error, [id$="-error"]:visible').count():
            return RECHAZADO_FORM
    except Exception:
        pass
    return ERROR


def enviar_una(perfil, borrador, cv_path, modo="dry_run",
               permitir_revisar=False, screenshot_dir=None):
    """Llena (y opcionalmente envía) la postulación de UNA oferta.

    Devuelve dict: {estado, detalle, campos_llenados, campos_fallidos, captura}
    """
    from playwright.sync_api import sync_playwright

    oferta = borrador["oferta"]
    resultado = {
        "oferta": oferta,
        "estado": ERROR,
        "detalle": "",
        "campos_llenados": 0,
        "campos_fallidos": [],
        "captura": None,
    }

    if modo == "enviar":
        modo_borrador = borrador.get("modo")
        # "bloqueado" nunca se envía: le faltan campos obligatorios y el propio
        # Greenhouse la rechazaría. "revisar" solo con permiso explícito.
        if modo_borrador == "bloqueado":
            resultado["estado"] = ERROR
            resultado["detalle"] = (
                "Faltan campos obligatorios (%s). Complétalos en tu perfil."
                % ", ".join(borrador.get("motivo_bloqueo", [])[:3])
            )
            return resultado
        if modo_borrador != "auto" and not permitir_revisar:
            resultado["estado"] = ERROR
            resultado["detalle"] = ("La oferta tiene texto generado por IA; "
                                    "requiere revisión humana antes de enviar.")
            return resultado

    url = _url_formulario(oferta) or FALLBACK_URL.format(
        token=oferta["board_token"], job_id=oferta["id"]
    )
    if _url_formulario(oferta) is None and oferta.get("url"):
        resultado["estado"] = SIN_SOPORTE
        resultado["detalle"] = (
            "%s sirve el formulario desde su propio sitio de carreras; "
            "este agente solo automatiza boards hospedados por Greenhouse. "
            "Abre la oferta y postula manualmente." % oferta.get("empresa", "La empresa")
        )
        return resultado

    with sync_playwright() as p:
        navegador = p.chromium.launch(headless=True)
        pagina = navegador.new_page()
        try:
            pagina.goto(url, wait_until="networkidle", timeout=45000)
            pagina.wait_for_selector("#first_name, #email", timeout=15000)
            # El HTML llega renderizado por el servidor y React lo hidrata
            # después; si escribimos antes de eso, la hidratación borra todo.
            pagina.wait_for_timeout(1500)

            if _hay_captcha_visible(pagina):
                resultado["estado"] = BLOQUEADO_CAPTCHA
                resultado["detalle"] = "El formulario muestra un reCAPTCHA antes de enviar."
                return _cerrar(navegador, pagina, resultado, screenshot_dir)

            # ---- adjuntar CV ----
            if cv_path and os.path.exists(cv_path):
                try:
                    pagina.set_input_files("#resume", cv_path)
                except Exception as e:
                    resultado["campos_fallidos"].append(f"resume ({e})")

            # ---- rellenar cada campo del borrador ----
            for campo in borrador["campos"]:
                nombre = campo.get("name")
                if nombre in ("resume", "resume_text") or campo.get("valor") in (None, ""):
                    continue
                if campo.get("valor") == "[CV adjunto]":
                    continue

                ok = (_rellenar_select(pagina, campo) if campo.get("opciones")
                      else _rellenar_texto(pagina, campo))
                if ok:
                    resultado["campos_llenados"] += 1
                else:
                    resultado["campos_fallidos"].append(nombre)

            # El país del teléfono no es una pregunta de la API, pero Greenhouse
            # lo valida igual. Va después del teléfono para darle la chance de
            # autodetectarse del prefijo.
            if _rellenar_pais_telefono(pagina, perfil) is False:
                resultado["campos_fallidos"].append("country (teléfono)")

            if modo != "enviar":
                resultado["estado"] = SIMULADO
                resultado["detalle"] = "Formulario llenado. No se envió (dry_run)."
                return _cerrar(navegador, pagina, resultado, screenshot_dir)

            # ---- enviar ----
            boton = pagina.locator(
                'button:has-text("Submit application"), button:has-text("Submit Application"), '
                'button[aria-label*="Submit"]'
            ).last
            boton.scroll_into_view_if_needed()
            boton.click()
            pagina.wait_for_timeout(6000)

            resultado["estado"] = _diagnostico_post_envio(pagina)
            resultado["detalle"] = {
                ENVIADO: "Greenhouse confirmó la recepción.",
                BLOQUEADO_EMAIL: "Greenhouse pide verificar el correo para completar.",
                BLOQUEADO_CAPTCHA: "Saltó un reCAPTCHA al enviar.",
                RECHAZADO_FORM: "Greenhouse marcó campos inválidos o faltantes.",
                ERROR: "No se pudo confirmar el envío.",
            }[resultado["estado"]]
            return _cerrar(navegador, pagina, resultado, screenshot_dir)

        except Exception as e:
            resultado["estado"] = ERROR
            resultado["detalle"] = str(e)
            return _cerrar(navegador, pagina, resultado, screenshot_dir)


def _cerrar(navegador, pagina, resultado, screenshot_dir):
    if screenshot_dir:
        try:
            os.makedirs(screenshot_dir, exist_ok=True)
            ruta = os.path.join(
                screenshot_dir,
                f"{resultado['oferta']['board_token']}_{resultado['oferta']['id']}_{int(time.time())}.png",
            )
            pagina.screenshot(path=ruta, full_page=True)
            resultado["captura"] = ruta
        except Exception:
            pass
    try:
        navegador.close()
    except Exception:
        pass
    return resultado

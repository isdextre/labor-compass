# -*- coding: utf-8 -*-
"""
worker.py — Cola en memoria para los envíos con navegador.

Un envío con Playwright tarda entre 10 y 40 s, así que no se puede hacer dentro
del request HTTP. El front dispara el lote, este módulo lo procesa en un hilo
aparte, de a una postulación por vez (educado con los servidores de Greenhouse),
y el front consulta el avance con GET /api/postular/estado.

Es estado en memoria: si se reinicia Flask, el historial del lote se pierde.
Suficiente para el MVP; en producción esto sería una tabla + un worker real
(rq/celery).
"""
import threading
import time

from applier import orchestrator
from applier.submitter import enviar_una

# {user_id: {estado, modo, total, procesadas, en_curso, resultados: [...], iniciado}}
_LOTES = {}
_LOCK = threading.Lock()


def estado(user_id):
    with _LOCK:
        return dict(_LOTES.get(user_id, {"estado": "sin_lote"}))


def _procesar(user_id, perfil, tareas, modo, screenshot_dir, permitir_revisar):
    cv_path = orchestrator.asegurar_cv_path(perfil)

    for tarea in tareas:
        board_token = tarea["board_token"]
        job_id = tarea["job_id"]

        with _LOCK:
            _LOTES[user_id]["en_curso"] = f"{board_token}/{job_id}"

        try:
            borrador = orchestrator.preparar_postulacion(perfil, board_token, job_id)

            # Qué se envía de verdad:
            #   "auto"      -> siempre (todo salió del perfil)
            #   "revisar"   -> solo si el usuario lo pidió (permitir_revisar)
            #   "bloqueado" -> NUNCA: le faltan campos obligatorios y Greenhouse
            #                  la rechazaría igual; mejor llenarla y avisar.
            modo_borrador = borrador.get("modo")
            enviable = (modo_borrador == "auto"
                        or (modo_borrador == "revisar" and permitir_revisar))
            modo_real = modo if enviable else "dry_run"
            degradada = (modo == "enviar" and not enviable)

            res = enviar_una(perfil, borrador, cv_path, modo=modo_real,
                             permitir_revisar=permitir_revisar,
                             screenshot_dir=screenshot_dir)
            res["modo_borrador"] = borrador.get("modo")
            # Solo explicamos la degradación si el submitter llegó a simular.
            # Si devolvió algo más específico (no_soportado, captcha, error),
            # ese diagnóstico manda y no hay que pisarlo.
            if degradada and res.get("estado") == "simulado":
                if modo_borrador == "bloqueado":
                    res["detalle"] = (
                        "No se envió: faltan campos obligatorios (%s). "
                        "Complétalos en tu perfil y reintenta."
                        % ", ".join(borrador.get("motivo_bloqueo", [])[:3])
                    )
                else:
                    res["detalle"] = ("No se envió: tiene texto generado por IA y no "
                                      "marcaste 'incluir las que requieren revisión'. "
                                      "El formulario está lleno.")
        except Exception as e:
            res = {"oferta": {"board_token": board_token, "id": job_id},
                   "estado": "error", "detalle": str(e)}

        with _LOCK:
            _LOTES[user_id]["resultados"].append(res)
            _LOTES[user_id]["procesadas"] += 1

        time.sleep(2)  # cortesía entre envíos

    with _LOCK:
        _LOTES[user_id]["estado"] = "terminado"
        _LOTES[user_id]["en_curso"] = None


def encolar_lote(user_id, perfil, tareas, modo, screenshot_dir, permitir_revisar=False):
    """tareas: [{board_token, job_id}, ...]. modo: 'dry_run' | 'enviar'.

    permitir_revisar=True se usa solo para el envío de UNA oferta que el
    usuario ya revisó campo por campo en la UI.
    """
    with _LOCK:
        actual = _LOTES.get(user_id)
        if actual and actual.get("estado") == "procesando":
            return actual
        _LOTES[user_id] = {
            "estado": "procesando",
            "modo": modo,
            "total": len(tareas),
            "procesadas": 0,
            "en_curso": None,
            "resultados": [],
            "iniciado": time.time(),
        }

    hilo = threading.Thread(
        target=_procesar,
        args=(user_id, perfil, tareas, modo, screenshot_dir, permitir_revisar),
        daemon=True,
    )
    hilo.start()
    return estado(user_id)

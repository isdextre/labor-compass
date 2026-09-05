# claude/billing.py
# Simulación simple en memoria (para producción sería una tabla en la BD)
usuarios_usos = {}  # {user_id: cantidad_de_veces_que_uso}
usuarios_premium = set()  # {user_id, ...}

USOS_GRATIS = 1
PRECIO_MENSUAL = 5  # soles
NUMERO_YAPE = "957810982"

def tiene_acceso(user_id: str) -> dict:
    if user_id in usuarios_premium:
        return {"acceso": True, "razon": "premium"}

    usos = usuarios_usos.get(user_id, 0)

    if usos < USOS_GRATIS:
        return {"acceso": True, "razon": "uso_gratis", "usos_restantes": USOS_GRATIS - usos}

    return {
        "acceso": False,
        "razon": "limite_alcanzado",
        "precio_mensual": PRECIO_MENSUAL,
        "numero_yape": NUMERO_YAPE
    }

def registrar_uso(user_id: str):
    usuarios_usos[user_id] = usuarios_usos.get(user_id, 0) + 1

def marcar_como_premium(user_id: str):
    usuarios_premium.add(user_id)

    return {"acceso": False, "razon": "trial_vencido"}

def marcar_como_premium(user_id: str):
    usuarios_premium.add(user_id)

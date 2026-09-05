# claude/billing.py
from datetime import datetime, timedelta

# Simulación simple en memoria (para producción sería una tabla en la BD)
usuarios_trial = {}  # {user_id: fecha_inicio_trial}
usuarios_premium = set()  # {user_id, ...}

DIAS_TRIAL = 7
USOS_GRATIS_MATCHING = 3  # ej: 3 búsquedas de matching gratis, luego paga

def iniciar_trial(user_id: str):
    if user_id not in usuarios_trial:
        usuarios_trial[user_id] = datetime.now()

def tiene_acceso(user_id: str) -> dict:
    if user_id in usuarios_premium:
        return {"acceso": True, "razon": "premium"}

    inicio = usuarios_trial.get(user_id)
    if inicio is None:
        iniciar_trial(user_id)
        return {"acceso": True, "razon": "trial_iniciado"}

    dias_restantes = DIAS_TRIAL - (datetime.now() - inicio).days
    if dias_restantes > 0:
        return {"acceso": True, "razon": "trial_activo", "dias_restantes": dias_restantes}

    return {"acceso": False, "razon": "trial_vencido"}

def marcar_como_premium(user_id: str):
    usuarios_premium.add(user_id)

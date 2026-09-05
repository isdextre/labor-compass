"""
Punto de entrada WSGI para producción (Render, Railway, cualquier host con gunicorn).

Carga el Flask de `claude/app.py` por ruta explícita en vez de con `import app`,
porque en la raíz del repo existe también un paquete vacío `app/` que ganaría
la resolución del import y dejaría a gunicorn sin objeto WSGI.

El directorio de trabajo se mantiene en la raíz del repo: varios módulos
resuelven sus datos relativos a ella.

Uso:  gunicorn wsgi:app
"""
import importlib.util
import os
import sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.join(RAIZ, "claude")

# `claude/` en el path para los imports planos del backend (billing, cv_parser,
# enrichment, applier...), y la raíz para el paquete `models`.
for ruta in (APP_DIR, RAIZ):
    if ruta not in sys.path:
        sys.path.insert(0, ruta)

_spec = importlib.util.spec_from_file_location(
    "proximo_app", os.path.join(APP_DIR, "app.py")
)
_modulo = importlib.util.module_from_spec(_spec)
# Registrar antes de ejecutar: Flask deduce root_path (y con el templates/ y
# static/ de la app) a partir del modulo en sys.modules que le da su nombre.
sys.modules[_spec.name] = _modulo
_spec.loader.exec_module(_modulo)

app = _modulo.app

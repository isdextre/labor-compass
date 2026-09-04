"""
Configuración del proyecto workforce-shift
"""

from pathlib import Path

# Directorios
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / 'data'
RAW_DATA_DIR = DATA_DIR / 'raw'
PROCESSED_DATA_DIR = DATA_DIR / 'processed'
EXTERNAL_DATA_DIR = DATA_DIR / 'external'
LOGS_DIR = PROJECT_ROOT / 'logs'

# Crear directorios si no existen
for dir_path in [RAW_DATA_DIR, PROCESSED_DATA_DIR, EXTERNAL_DATA_DIR, LOGS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# Configuración de descarga
INEI_BASE_URL = "https://m.inei.gob.pe/media/MenuRecursivo/indices_tematicos"

INEI_FILES = {
    'salarios': {
        'filename': 'ing-cuad-5_4_1.xlsx',
        'desc': 'Ingreso promedio mensual por rama de actividad (2009-2021)',
        'tipo': 'salarios'
    },
    'ocupados_lima': {
        'filename': 'lima-cuad-3_5.xlsx',
        'desc': 'Población ocupada en Lima por rama de actividad (2006-2023)',
        'tipo': 'ocupados'
    },
    'ocupados_nacional': {
        'filename': 'ing-cuad-1_3_1.xlsx',
        'desc': 'Población ocupada nacional por ámbito/región/departamento (2009-2021)',
        'tipo': 'ocupados'
    }
}

# Configuración de logging
LOG_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'filename': LOGS_DIR / 'pipeline.log'
}

# Años de análisis
YEARS_SALARIOS = list(range(2009, 2022))  # 2009-2021
YEARS_OCUPADOS_LIMA = list(range(2006, 2024))  # 2006-2023
YEARS_OCUPADOS_NACIONAL = list(range(2009, 2022))  # 2009-2021

# Ramas de actividad
RAMAS_ACTIVIDAD = [
    'Manufactura',
    'Construcción',
    'Comercio',
    'Servicios',
    'Otros'
]

# Regiones naturales (para archivo salarios)
REGIONES_SALARIOS = [
    'Total',
    'Costa urbana',
    'Sierra urbana',
    'Selva urbana'
]

# Regiones naturales (para archivo nacional)
REGIONES_NACIONAL = [
    'Costa',
    'Sierra',
    'Selva'
]

# Áreas de residencia
AREAS_RESIDENCIA = ['Urbana', 'Rural']

# Departamentos del Perú
DEPARTAMENTOS_PERU = [
    'Amazonas', 'Áncash', 'Apurímac', 'Arequipa', 'Ayacucho',
    'Cajamarca', 'Prov. Const. Callao', 'Cusco', 'Huancavelica', 'Huánuco',
    'Ica', 'Junín', 'La Libertad', 'Lambayeque', 'Lima', 'Loreto',
    'Madre de Dios', 'Moquegua', 'Pasco', 'Piura', 'Puno', 'San Martín', 'Tacna', 'Tumbes', 'Ucayali'
]

# Configuración de exportación
EXPORT_FORMAT = 'json'  # 'json' o 'csv'
EXPORT_INDENT = 2

print(f"✓ Configuración cargada desde {__file__}")

"""
INEI Data Scraper - Workforce Shift Project
Extrae datos de ocupación y salarios por rama de actividad desde INEI
"""

import requests
import pandas as pd
import logging
import json
from pathlib import Path
from datetime import datetime
import urllib3

# Deshabilitar advertencias SSL (para Windows)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configurar logging
logging.basicConfig(
    filename='logs/inei_scraper.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class INEIScraper:
    """Scraper para descargar datos de INEI"""

    def __init__(self):
        self.base_url = "https://m.inei.gob.pe/media/MenuRecursivo/indices_tematicos"
        self.timeout = 30
        self.retries = 3

        # URLs de los archivos a descargar
        self.files = {
            'salarios': 'ing-cuad-5_4_1.xlsx',
            'ocupados_lima': 'lima-cuad-3_5.xlsx',
            'ocupados_general': 'peao-cuad-4_3_1.xlsx'
        }

        logger.info("Inicializando INEI Scraper")

    def descargar_archivo(self, nombre, filename):
        """Descarga un archivo XLSX desde INEI"""
        url = f"{self.base_url}/{filename}"

        try:
            logger.info(f"Descargando {nombre} desde {url}")
            response = requests.get(url, timeout=self.timeout, verify=False)
            response.raise_for_status()

            # Crear carpeta raw si no existe
            raw_path = Path('data/raw')
            raw_path.mkdir(parents=True, exist_ok=True)

            # Guardar archivo
            filepath = raw_path / filename
            with open(filepath, 'wb') as f:
                f.write(response.content)

            logger.info(f"✅ {nombre} descargado exitosamente en {filepath}")
            return filepath

        except requests.ConnectionError:
            logger.error(f"❌ Error de conexión al descargar {nombre}")
            raise
        except requests.HTTPError as e:
            logger.error(f"❌ Error HTTP {e.response.status_code} para {nombre}")
            raise
        except Exception as e:
            logger.error(f"❌ Error inesperado descargando {nombre}: {str(e)}")
            raise

    def limpiar_dataframe(self, df):
        """Limpia un dataframe de INEI: quita filas y columnas vacías"""
        try:
            # 1. Quitar filas completamente vacías
            df = df.dropna(how='all')

            # 2. Quitar columnas completamente vacías
            df = df.dropna(axis=1, how='all')

            # 3. Renombrar primera columna
            df = df.rename(columns={df.columns[0]: 'categoria'})

            # 4. Quitar filas que no tengan datos numéricos en las columnas principales
            # Mantener solo filas donde al menos una columna numérica tiene valor
            numeric_cols = df.columns[1:]
            df['tiene_numeros'] = df[numeric_cols].apply(
                lambda row: sum(1 for x in row if isinstance(x, (int, float)) and not pd.isna(x)) > 0,
                axis=1
            )
            df = df[df['tiene_numeros'] == True].drop('tiene_numeros', axis=1)

            # 5. Convertir valores a numérico
            for col in df.columns[1:]:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            logger.info(f"Dataframe limpio: {len(df)} filas")
            return df

        except Exception as e:
            logger.error(f"❌ Error limpiando dataframe: {str(e)}")
            raise

    def extraer_salarios(self, filepath):
        """Extrae datos de salarios por rama de actividad"""
        try:
            logger.info(f"Extrayendo salarios de {filepath}")

            # Leer Excel sin asumir header
            df = pd.read_excel(filepath, sheet_name=0, header=None)

            # Encontrar dónde empieza la tabla real (buscar "Rama de Actividad" o fila con años)
            header_row = None
            for idx, row in df.iterrows():
                if any(str(year) in str(cell) for year in range(2009, 2022) for cell in row):
                    header_row = idx - 1
                    break

            if header_row is None:
                logger.warning("No se encontró header automáticamente, usando row 3")
                header_row = 3

            # Reasignar header y reiniciar índice
            df.columns = df.iloc[header_row]
            df = df.iloc[header_row + 1:]
            df = df.reset_index(drop=True)

            # Limpiar
            df = self.limpiar_dataframe(df)

            # Renombrar columna de categoría
            df = df.rename(columns={'categoria': 'rama_actividad'})

            logger.info(f"✅ Extraídos {len(df)} registros")
            return df

        except Exception as e:
            logger.error(f"❌ Error extrayendo salarios: {str(e)}")
            raise

    def normalizar_a_json(self, df, output_name):
        """Convierte DataFrame a JSON normalizado"""
        try:
            # Crear estructura limpia
            datos = []

            for idx, row in df.iterrows():
                rama = row['rama_actividad']

                # Extraer columnas de años (2009-2021)
                salarios_por_año = {}
                for col in df.columns[1:]:
                    try:
                        año = int(col)
                        valor = float(row[col])
                        salarios_por_año[año] = valor
                    except (ValueError, TypeError):
                        continue

                if salarios_por_año:
                    datos.append({
                        'rama_actividad': rama,
                        'salarios_por_año': salarios_por_año,
                        'salario_min': min(salarios_por_año.values()),
                        'salario_max': max(salarios_por_año.values()),
                        'salario_2021': salarios_por_año.get(2021, None)
                    })

            # Guardar JSON
            processed_path = Path('data/processed')
            processed_path.mkdir(parents=True, exist_ok=True)

            output_file = processed_path / f"{output_name}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(datos, f, ensure_ascii=False, indent=2)

            logger.info(f"✅ JSON guardado en {output_file}")
            return datos

        except Exception as e:
            logger.error(f"❌ Error normalizando a JSON: {str(e)}")
            raise

    def ejecutar(self):
        """Ejecuta el pipeline completo"""
        try:
            logger.info("=" * 60)
            logger.info("INICIANDO SCRAPER INEI")
            logger.info("=" * 60)

            # Descargar archivos
            for nombre, filename in self.files.items():
                filepath = self.descargar_archivo(nombre, filename)

                # Procesar salarios
                if nombre == 'salarios':
                    df = self.extraer_salarios(filepath)
                    self.normalizar_a_json(df, 'inei_salarios_por_rama')

            logger.info("=" * 60)
            logger.info("✅ SCRAPER COMPLETADO EXITOSAMENTE")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"❌ Error en pipeline: {str(e)}")
            raise


if __name__ == "__main__":
    scraper = INEIScraper()
    scraper.ejecutar()
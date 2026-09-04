"""
Parsers específicos para los 3 archivos INEI:
1. ingcuad5_4_1.xlsx - Salarios por rama de actividad (2009-2021)
2. limacuad3_5.xlsx - Población ocupada en Lima (2006-2023)
3. ingcuad1_3_1.xlsx - Población ocupada nacional por ámbito/región/departamento (2009-2021)
"""

import pandas as pd
import json
from pathlib import Path
from typing import List, Dict, Any


class SalariosRamaParser:
    """Parser para ingcuad5_4_1.xlsx - Salarios por rama de actividad"""

    def __init__(self, filepath):
        self.filepath = filepath
        self.años = [str(year) for year in range(2009, 2022)]

    def procesar(self) -> List[Dict]:
        print("📊 Procesando: Salarios por rama de actividad (ingcuad5_4_1.xlsx)")

        df = pd.read_excel(self.filepath, sheet_name=0, header=None)
        df = df.iloc[3:37].reset_index(drop=True)  # Mantener solo datos relevantes

        datos = []
        regiones_map = {
            5: 'Total',
            16: 'Costa urbana',
            23: 'Sierra urbana',
            30: 'Selva urbana'
        }
        ramas_validas = ['Manufactura', 'Construcción', 'Comercio', 'Servicios', 'Otros']

        for region_row, region_name in regiones_map.items():
            # Extraer 5 filas posteriores a la etiqueta de región
            for i in range(1, 6):
                idx = region_row + i
                if idx < len(df):
                    row = df.iloc[idx]
                    rama = str(row[0]).strip()

                    # Verificar si es rama válida
                    if not any(r in rama for r in ramas_validas):
                        continue

                    salarios = {}
                    for año_idx, año in enumerate(self.años):
                        col_idx = año_idx + 1
                        if col_idx < len(row):
                            try:
                                valor = pd.to_numeric(row[col_idx], errors='coerce')
                                if pd.notna(valor):
                                    salarios[int(año)] = float(valor)
                            except:
                                pass

                    if salarios:
                        rama_limpia = rama.replace(' 1/', '').strip()
                        datos.append({
                            'tipo': 'salarios',
                            'rama_actividad': rama_limpia,
                            'region': region_name,
                            'salarios_por_año': salarios,
                            'salario_2009': salarios.get(2009),
                            'salario_2021': salarios.get(2021),
                            'variacion_pct': round((salarios.get(2021, 0) - salarios.get(2009, 0)) / salarios.get(2009, 1) * 100, 2) if salarios.get(2009) else None
                        })

        print(f"   ✓ Extraídos {len(datos)} registros")
        return datos


class OcupadosLimaParser:
    """Parser para limacuad3_5.xlsx - Población ocupada en Lima por rama"""

    def __init__(self, filepath):
        self.filepath = filepath

    def procesar(self) -> List[Dict]:
        print("📊 Procesando: Población ocupada Lima (limacuad3_5.xlsx)")

        df = pd.read_excel(self.filepath, sheet_name=0, header=None)

        datos = []

        # Extractores de secciones
        secciones = {
            'ramas_actividad': {
                'inicio': 7,  # Fila con "Ramas de actividad"
                'items': ['Manufactura', 'Construcción', 'Comercio', 'Servicios', 'Otros'],
                'count': 5
            },
            'tamaño_empresa': {
                'inicio': 14,  # Fila con "Tamaño de la empresa"
                'items': ['De 1 a 10', 'De 11 a 50', 'De 51 a más'],
                'count': 3
            },
            'categoria_ocupacion': {
                'inicio': 19,  # Fila con "Categoría de ocupación"
                'items': ['Empleador', 'Independiente', 'Empleado', 'Obrero', 'Familiar no Remunerado', 'Trabajador del Hogar'],
                'count': 6
            }
        }

        # Extraer años de headers (fila 3, columnas 2-17)
        años = []
        for col_idx in range(1, 18):
            try:
                año = int(pd.to_numeric(df.iloc[3, col_idx], errors='coerce'))
                años.append(año)
            except:
                pass

        # Procesar ramas de actividad
        for i in range(secciones['ramas_actividad']['count']):
            row_idx = secciones['ramas_actividad']['inicio'] + i + 1
            if row_idx < len(df):
                row = df.iloc[row_idx]
                categoria = str(row[0]).strip()

                valores = {}
                for año_idx, año in enumerate(años):
                    col_idx = año_idx + 1
                    if col_idx < len(row):
                        try:
                            valor = pd.to_numeric(row[col_idx], errors='coerce')
                            if pd.notna(valor):
                                valores[año] = float(valor)
                        except:
                            pass

                if valores:
                    datos.append({
                        'tipo': 'ocupados_rama_lima',
                        'categoria': categoria,
                        'subcategoria': 'rama_actividad',
                        'poblacion_miles': valores,
                        'poblacion_2006': valores.get(min(valores.keys())),
                        'poblacion_2023': valores.get(max(valores.keys())),
                        'unidad': 'miles de personas'
                    })

        # Procesar tamaño de empresa
        for i in range(secciones['tamaño_empresa']['count']):
            row_idx = secciones['tamaño_empresa']['inicio'] + i + 1
            if row_idx < len(df):
                row = df.iloc[row_idx]
                categoria = str(row[0]).strip()

                valores = {}
                for año_idx, año in enumerate(años):
                    col_idx = año_idx + 1
                    if col_idx < len(row):
                        try:
                            valor = pd.to_numeric(row[col_idx], errors='coerce')
                            if pd.notna(valor):
                                valores[año] = float(valor)
                        except:
                            pass

                if valores:
                    datos.append({
                        'tipo': 'ocupados_empresa_lima',
                        'categoria': categoria,
                        'subcategoria': 'tamaño_empresa',
                        'poblacion_miles': valores,
                        'poblacion_2006': valores.get(min(valores.keys())),
                        'poblacion_2023': valores.get(max(valores.keys())),
                        'unidad': 'miles de personas'
                    })

        print(f"   ✓ Extraídos {len(datos)} registros")
        return datos


class OcupadosNacionalParser:
    """Parser para ingcuad1_3_1.xlsx - Población ocupada nacional"""

    def __init__(self, filepath):
        self.filepath = filepath
        self.años = [str(year) for year in range(2009, 2022)]

    def procesar(self) -> List[Dict]:
        print("📊 Procesando: Población ocupada nacional (ingcuad1_3_1.xlsx)")

        df = pd.read_excel(self.filepath, sheet_name=0, header=None)

        datos = []

        # Secciones principales
        secciones = {
            'ambito_total': {'row': 8, 'label': 'Total nacional'},
            'area_residencia': {
                'inicio': 11,
                'items': {12: 'Urbana', 11: 'Rural'}  # Corregir índices según estructura
            },
            'region_natural': {
                'inicio': 15,
                'items': {15: 'Costa', 16: 'Sierra', 17: 'Selva'}
            },
            'departamentos': {
                'inicio': 20,
                'count': 24
            }
        }

        # Total nacional
        row = df.iloc[secciones['ambito_total']['row']]
        salarios = {}
        for año_idx, año in enumerate(self.años):
            col_idx = año_idx + 1
            if col_idx < len(row):
                try:
                    valor = pd.to_numeric(row[col_idx], errors='coerce')
                    if pd.notna(valor):
                        salarios[int(año)] = float(valor)
                except:
                    pass

        if salarios:
            datos.append({
                'tipo': 'ingreso_nacional',
                'ambito': 'Total nacional',
                'ingresos_por_año': salarios,
                'ingreso_2009': salarios.get(2009),
                'ingreso_2021': salarios.get(2021),
                'unidad': 'soles corrientes'
            })

        # Área de residencia
        for row_idx in range(11, 13):
            if row_idx < len(df):
                row = df.iloc[row_idx]
                area = str(row[0]).strip()

                if area not in ['Urbana', 'Rural']:
                    continue

                salarios = {}
                for año_idx, año in enumerate(self.años):
                    col_idx = año_idx + 1
                    if col_idx < len(row):
                        try:
                            valor = pd.to_numeric(row[col_idx], errors='coerce')
                            if pd.notna(valor):
                                salarios[int(año)] = float(valor)
                        except:
                            pass

                if salarios:
                    datos.append({
                        'tipo': 'ingreso_area_residencia',
                        'area': area,
                        'ingresos_por_año': salarios,
                        'ingreso_2009': salarios.get(2009),
                        'ingreso_2021': salarios.get(2021),
                        'unidad': 'soles corrientes'
                    })

        # Región natural
        for row_idx in range(15, 18):
            if row_idx < len(df):
                row = df.iloc[row_idx]
                region = str(row[0]).strip()

                if region not in ['Costa', 'Sierra', 'Selva']:
                    continue

                salarios = {}
                for año_idx, año in enumerate(self.años):
                    col_idx = año_idx + 1
                    if col_idx < len(row):
                        try:
                            valor = pd.to_numeric(row[col_idx], errors='coerce')
                            if pd.notna(valor):
                                salarios[int(año)] = float(valor)
                        except:
                            pass

                if salarios:
                    datos.append({
                        'tipo': 'ingreso_region_natural',
                        'region': region,
                        'ingresos_por_año': salarios,
                        'ingreso_2009': salarios.get(2009),
                        'ingreso_2021': salarios.get(2021),
                        'unidad': 'soles corrientes'
                    })

        # Departamentos
        for i in range(24):
            row_idx = 20 + i
            if row_idx < len(df):
                row = df.iloc[row_idx]
                departamento = str(row[0]).strip()

                if not departamento or departamento.startswith('Nota'):
                    continue

                salarios = {}
                for año_idx, año in enumerate(self.años):
                    col_idx = año_idx + 1
                    if col_idx < len(row):
                        try:
                            valor = pd.to_numeric(row[col_idx], errors='coerce')
                            if pd.notna(valor):
                                salarios[int(año)] = float(valor)
                        except:
                            pass

                if salarios:
                    datos.append({
                        'tipo': 'ingreso_departamento',
                        'departamento': departamento,
                        'ingresos_por_año': salarios,
                        'ingreso_2009': salarios.get(2009),
                        'ingreso_2021': salarios.get(2021),
                        'unidad': 'soles corrientes'
                    })

        print(f"   ✓ Extraídos {len(datos)} registros")
        return datos


class INEIPipeline:
    """Orquestador de los 3 parsers"""

    def __init__(self, dir_raw='data/raw', dir_processed='data/processed'):
        self.dir_raw = Path(dir_raw)
        self.dir_processed = Path(dir_processed)
        self.dir_processed.mkdir(parents=True, exist_ok=True)

    def ejecutar(self, files_map: Dict[str, str]):
        """
        files_map = {
            'salarios': 'ingcuad5_4_1.xlsx',
            'ocupados_lima': 'limacuad3_5.xlsx',
            'ocupados_nacional': 'ingcuad1_3_1.xlsx'
        }
        """

        print("\n" + "="*70)
        print("🚀 INICIANDO PIPELINE INEI")
        print("="*70 + "\n")

        todos_datos = []

        # 1. Salarios por rama
        if 'salarios' in files_map:
            parser = SalariosRamaParser(self.dir_raw / files_map['salarios'])
            datos = parser.procesar()
            todos_datos.extend(datos)
            self._guardar_json(datos, 'inei_salarios_por_rama.json')

        # 2. Ocupados Lima
        if 'ocupados_lima' in files_map:
            parser = OcupadosLimaParser(self.dir_raw / files_map['ocupados_lima'])
            datos = parser.procesar()
            todos_datos.extend(datos)
            self._guardar_json(datos, 'inei_ocupados_lima.json')

        # 3. Ocupados Nacional
        if 'ocupados_nacional' in files_map:
            parser = OcupadosNacionalParser(self.dir_raw / files_map['ocupados_nacional'])
            datos = parser.procesar()
            todos_datos.extend(datos)
            self._guardar_json(datos, 'inei_ocupados_nacional.json')

        # Guardar consolidado
        self._guardar_json(todos_datos, 'inei_consolidado.json')

        print("\n" + "="*70)
        print(f"✅ PIPELINE COMPLETADO")
        print(f"   📁 Total registros: {len(todos_datos)}")
        print(f"   📂 Guardados en: {self.dir_processed}")
        print("="*70 + "\n")

    def _guardar_json(self, datos: List[Dict], filename: str):
        filepath = self.dir_processed / filename

        # Convertir años a strings para JSON
        datos_json = []
        for item in datos:
            item_limpio = {**item}

            # Convertir dicts de años
            if 'salarios_por_año' in item_limpio:
                item_limpio['salarios_por_año'] = {str(k): v for k, v in item_limpio['salarios_por_año'].items()}
            if 'ingresos_por_año' in item_limpio:
                item_limpio['ingresos_por_año'] = {str(k): v for k, v in item_limpio['ingresos_por_año'].items()}
            if 'poblacion_miles' in item_limpio:
                item_limpio['poblacion_miles'] = {str(k): v for k, v in item_limpio['poblacion_miles'].items()}

            datos_json.append(item_limpio)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(datos_json, f, ensure_ascii=False, indent=2)

        print(f"   💾 {filename} ({len(datos_json)} registros)")


if __name__ == "__main__":
    pipeline = INEIPipeline()

    files = {
        'salarios': 'ingcuad5_4_1.xlsx',
        'ocupados_lima': 'limacuad3_5.xlsx',
        'ocupados_nacional': 'ingcuad1_3_1.xlsx'
    }

    pipeline.ejecutar(files)

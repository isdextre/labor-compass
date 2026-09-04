#!/usr/bin/env python3
"""
Script maestro para ejecutar el pipeline completo de extracción INEI
Uso: python3 run_pipeline.py [--download] [--force]
"""

import sys
import argparse
from pathlib import Path
from parse_all_inei import INEIPipeline


def main():
    parser = argparse.ArgumentParser(
        description='Pipeline de extracción de datos INEI'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Forzar re-procesamiento incluso si archivos procesados existen'
    )
    args = parser.parse_args()

    print("\n" + "="*70)
    print("🔧 WORKFORCE SHIFT - INEI DATA PIPELINE")
    print("="*70)

    # Verificar archivos raw
    dir_raw = Path('data/raw')
    required_files = [
        'ingcuad5_4_1.xlsx',
        'limacuad3_5.xlsx',
        'ingcuad1_3_1.xlsx'
    ]

    print("\n📂 Verificando archivos de entrada...")
    missing = []
    for file in required_files:
        filepath = dir_raw / file
        if filepath.exists():
            print(f"   ✓ {file}")
        else:
            print(f"   ✗ {file} (no encontrado)")
            missing.append(file)

    if missing:
        print(f"\n❌ Faltan {len(missing)} archivo(s). Descárgalos primero desde:")
        print("   https://m.inei.gob.pe/media/MenuRecursivo/indices_tematicos/")
        return 1

    # Ejecutar pipeline
    print("\n🚀 Iniciando extracción...")
    pipeline = INEIPipeline()

    files_map = {
        'salarios': 'ingcuad5_4_1.xlsx',
        'ocupados_lima': 'limacuad3_5.xlsx',
        'ocupados_nacional': 'ingcuad1_3_1.xlsx'
    }

    try:
        pipeline.ejecutar(files_map)
    except Exception as e:
        print(f"\n❌ Error durante la ejecución: {str(e)}")
        return 1

    # Resumen
    print("\n📊 RESUMEN DE DATOS EXTRAÍDOS")
    print("="*70)

    import json

    dir_processed = Path('data/processed')
    total_registros = 0

    for file in dir_processed.glob('*.json'):
        if file.name == 'inei_consolidado.json':
            continue
        with open(file) as f:
            data = json.load(f)
            total_registros += len(data)
            print(f"   📄 {file.name}: {len(data)} registros")

    print(f"\n   ✅ Total: {total_registros} registros extraídos")
    print(f"   📁 Guardados en: {dir_processed.absolute()}")

    return 0


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
"""
Script maestro para ejecutar el pipeline completo de extracción INEI
Uso: python3 run_pipeline.py [--download] [--force]
"""

import sys
import argparse
from pathlib import Path
from parse_all_inei import INEIPipeline
from download_inei import INEIDownloader


def main():
    parser = argparse.ArgumentParser(
        description='Pipeline de extracción de datos INEI'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Forzar re-procesamiento incluso si archivos procesados existen'
    )
    parser.add_argument(
        '--skip-download',
        action='store_true',
        help='Saltar descarga y usar archivos locales existentes'
    )
    args = parser.parse_args()

    print("\n" + "="*70)
    print("🔧 WORKFORCE SHIFT - INEI DATA PIPELINE")
    print("="*70)

    # Descargar/actualizar archivos INEI
    if not args.skip_download:
        downloader = INEIDownloader()
        if not downloader.download_all():
            print("\n⚠️  Algunos archivos no se descargaron. Continuando con archivos locales...")
    else:
        print("\n📂 Usando archivos locales existentes (--skip-download)...")

    # Renombrar archivos si es necesario
    dir_raw = Path('data/raw')
    file_mappings = [
        ('ing-cuad-5_4_1.xlsx', 'ingcuad5_4_1.xlsx'),
        ('lima-cuad-3_5.xlsx', 'limacuad3_5.xlsx'),
        ('ing-cuad-1_3_1.xlsx', 'ingcuad1_3_1.xlsx')
    ]

    for old_name, new_name in file_mappings:
        old_path = dir_raw / old_name
        new_path = dir_raw / new_name
        if old_path.exists() and not new_path.exists():
            old_path.rename(new_path)
            print(f"   📝 Renombrado: {old_name} → {new_name}")

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
        with open(file, encoding='utf-8') as f:
            data = json.load(f)
            total_registros += len(data)
            print(f"   📄 {file.name}: {len(data)} registros")

    print(f"\n   ✅ Total: {total_registros} registros extraídos")
    print(f"   📁 Guardados en: {dir_processed.absolute()}")

    return 0


if __name__ == '__main__':
    sys.exit(main())

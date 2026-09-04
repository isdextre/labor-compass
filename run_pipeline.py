#!/usr/bin/env python3
"""
Script maestro para ejecutar pipelines completos de extracción
Uso:
    python3 run_pipeline.py              # Solo INEI
    python3 run_pipeline.py --future-of-work    # Solo Future of Work
    python3 run_pipeline.py --all         # INEI + Future of Work
"""

import sys
import argparse
from pathlib import Path
from parse_all_inei import INEIPipeline
from extract_future_of_work import FutureOfWorkExtractor


def run_inei_pipeline():
    """Ejecuta pipeline INEI"""
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
        return False

    # Ejecutar pipeline INEI
    print("\n🚀 Iniciando extracción INEI...")
    pipeline = INEIPipeline()

    files_map = {
        'salarios': 'ingcuad5_4_1.xlsx',
        'ocupados_lima': 'limacuad3_5.xlsx',
        'ocupados_nacional': 'ingcuad1_3_1.xlsx'
    }

    try:
        pipeline.ejecutar(files_map)
    except Exception as e:
        print(f"\n❌ Error durante la ejecución INEI: {str(e)}")
        return False

    # Resumen INEI
    print("\n📊 RESUMEN - INEI")
    print("="*70)

    import json

    dir_processed = Path('data/processed')
    total_registros = 0

    for file in dir_processed.glob('inei_*.json'):
        with open(file) as f:
            data = json.load(f)
            total_registros += len(data)
            print(f"   📄 {file.name}: {len(data)} registros")

    print(f"\n   ✅ Total INEI: {total_registros} registros")
    print(f"   📁 Guardados en: {dir_processed.absolute()}")

    return True


def run_future_of_work_pipeline():
    """Ejecuta pipeline Future of Work"""
    print("\n" + "="*70)
    print("🚀 WORKFORCE SHIFT - FUTURE OF WORK PIPELINE (Kaggle LinkedIn)")
    print("="*70)

    # Verificar archivos Kaggle
    dir_raw = Path('data/raw')
    required_kaggle = ['job_postings.csv', 'job_skills.csv']

    print("\n📂 Verificando archivos Kaggle...")
    missing = []
    for file in required_kaggle:
        filepath = dir_raw / file
        if filepath.exists():
            print(f"   ✓ {file}")
        else:
            print(f"   ⚠️  {file} (opcional)")
            missing.append(file)

    if len(missing) == len(required_kaggle):
        print(f"\n❌ No se encontraron datos de Kaggle.")
        print("   Descarga desde: https://www.kaggle.com/datasets/...")
        return False

    # Ejecutar extractor Future of Work
    print("\n🚀 Iniciando extracción Future of Work...")
    extractor = FutureOfWorkExtractor(raw_dir='data/raw', output_dir='data/processed')

    try:
        success = extractor.ejecutar()
        return success
    except Exception as e:
        print(f"\n❌ Error durante la ejecución Future of Work: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Pipeline maestro para extracción de datos Workforce Shift'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Ejecutar INEI + Future of Work'
    )
    parser.add_argument(
        '--future-of-work',
        action='store_true',
        help='Solo ejecutar Future of Work (Kaggle LinkedIn)'
    )
    parser.add_argument(
        '--inei',
        action='store_true',
        help='Solo ejecutar INEI (default si no especifica nada)'
    )

    args = parser.parse_args()

    # Lógica de decisión
    run_inei = not args.future_of_work  # Default: run INEI unless --future-of-work specified
    run_future = args.future_of_work or args.all

    if args.all:
        run_inei = True
        run_future = True

    if args.inei:
        run_inei = True
        run_future = False

    # Ejecutar
    results = {}

    if run_inei:
        results['inei'] = run_inei_pipeline()

    if run_future:
        results['future_of_work'] = run_future_of_work_pipeline()

    # Resumen final
    print("\n" + "="*70)
    print("📊 RESUMEN FINAL")
    print("="*70)

    for pipeline, success in results.items():
        status = "✅ OK" if success else "❌ FAILED"
        print(f"   {pipeline:20} {status}")

    all_success = all(results.values())
    if all_success:
        print("\n🎉 Todos los pipelines completados exitosamente!")
        return 0
    else:
        print("\n⚠️  Algunos pipelines tuvieron errores.")
        return 1


if __name__ == '__main__':
    sys.exit(main())

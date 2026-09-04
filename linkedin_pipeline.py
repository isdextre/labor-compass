#!/usr/bin/env python3
"""
Pipeline completo: Descargar + Parsear LinkedIn + Cruzar con INEI
"""
import subprocess
import sys
import os

def run_step(name, cmd):
    """Ejecutar un paso del pipeline"""
    print(f"\n{'='*60}")
    print(f"▶️  {name}")
    print(f"{'='*60}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"❌ Error en: {name}")
        return False
    return True

def main():
    steps = [
        ("Descarga de LinkedIn desde Kaggle", "python download_linkedin.py"),
        ("Parseo de datos LinkedIn", "python parse_linkedin.py"),
    ]

    for name, cmd in steps:
        if not run_step(name, cmd):
            print(f"\n❌ Pipeline interrumpido en: {name}")
            sys.exit(1)

    print(f"\n{'='*60}")
    print("✅ Pipeline LinkedIn completado")
    print(f"{'='*60}")
    print("\n📊 Siguientes pasos:")
    print("  1. Revisar: data/processed/linkedin_insights.json")
    print("  2. Cruzar con INEI: data/processed/inei_consolidado.json")
    print("  3. Crear análisis de gap: demand (LinkedIn) vs supply (INEI)")

if __name__ == "__main__":
    main()

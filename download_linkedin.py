#!/usr/bin/env python3
"""
Descargar dataset de LinkedIn Jobs desde Kaggle
"""
import os
import subprocess
import json

DATASET = "nithapraveen/linkedin-job-postings"
OUTPUT_DIR = "data/raw"

def download_linkedin():
    """Descargar dataset de Kaggle"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"📥 Descargando {DATASET} desde Kaggle...")
    cmd = f"kaggle datasets download -d {DATASET} -p {OUTPUT_DIR}"

    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Error: {result.stderr}")
        return False

    print("✅ Descarga completada")

    # Descomprimir
    print("📦 Descomprimiendo...")
    import zipfile
    zip_path = f"{OUTPUT_DIR}/{DATASET.split('/')[-1]}.zip"
    if os.path.exists(zip_path):
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(OUTPUT_DIR)
        print("✅ Descompresión completada")

    return True

if __name__ == "__main__":
    download_linkedin()

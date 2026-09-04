#!/usr/bin/env python3
"""
Descargar archivos INEI más recientes desde la web
"""

import requests
import os
from pathlib import Path
from config import INEI_BASE_URL, INEI_FILES, RAW_DATA_DIR
import urllib3

# Desactivar advertencias SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class INEIDownloader:
    def __init__(self):
        self.base_url = INEI_BASE_URL
        self.files = INEI_FILES
        self.output_dir = RAW_DATA_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def download_file(self, file_key):
        """Descargar un archivo específico de INEI"""
        file_info = self.files[file_key]
        filename = file_info['filename']
        url = f"{self.base_url}/{filename}"
        filepath = self.output_dir / filename

        print(f"\n📥 {file_info['desc']}")
        print(f"   URL: {url}")

        try:
            response = requests.get(url, verify=False, timeout=30)
            response.raise_for_status()

            with open(filepath, 'wb') as f:
                f.write(response.content)

            size_mb = filepath.stat().st_size / (1024 * 1024)
            print(f"   ✓ Descargado: {filename} ({size_mb:.2f} MB)")
            return True

        except Exception as e:
            print(f"   ✗ Error descargando {filename}: {str(e)}")
            return False

    def download_all(self):
        """Descargar todos los archivos INEI"""
        print("\n" + "="*70)
        print("📥 DESCARGANDO DATOS INEI")
        print("="*70)

        success_count = 0
        for key in self.files.keys():
            if self.download_file(key):
                success_count += 1

        print("\n" + "="*70)
        print(f"✓ Descargados: {success_count}/{len(self.files)} archivos")
        print("="*70)

        return success_count == len(self.files)


if __name__ == '__main__':
    downloader = INEIDownloader()
    downloader.download_all()

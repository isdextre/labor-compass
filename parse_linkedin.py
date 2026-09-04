#!/usr/bin/env python3
"""
Parsear datos de LinkedIn Jobs y extraer insights de demanda laboral
"""
import pandas as pd
import json
import os
from pathlib import Path

RAW_DIR = "data/raw"
OUTPUT_DIR = "data/processed"

def find_linkedin_csv():
    """Buscar archivo CSV de LinkedIn en raw"""
    for root, dirs, files in os.walk(RAW_DIR):
        for file in files:
            if file.endswith('.csv') and 'linkedin' in file.lower():
                return os.path.join(root, file)
    return None

def parse_linkedin():
    """Parsear CSV de LinkedIn a JSON estructurado"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    csv_path = find_linkedin_csv()
    if not csv_path:
        print(f"❌ No se encontró CSV de LinkedIn en {RAW_DIR}")
        return False

    print(f"📖 Leyendo {csv_path}...")
    df = pd.read_csv(csv_path)

    print(f"📊 Total de registros: {len(df)}")
    print(f"Columnas: {list(df.columns)}")

    # Información clave a extraer
    insights = {
        "total_jobs": len(df),
        "unique_titles": df['job_title'].nunique() if 'job_title' in df.columns else 0,
        "unique_companies": df['company_name'].nunique() if 'company_name' in df.columns else 0,
        "top_job_titles": [],
        "top_industries": [],
        "location_distribution": {},
        "seniority_levels": {}
    }

    # Top job titles
    if 'job_title' in df.columns:
        top_titles = df['job_title'].value_counts().head(20).to_dict()
        insights["top_job_titles"] = top_titles
        print(f"\n🎯 Top 10 Job Titles:")
        for i, (title, count) in enumerate(list(top_titles.items())[:10], 1):
            print(f"  {i}. {title}: {count}")

    # Top industries
    if 'industry' in df.columns:
        top_ind = df['industry'].value_counts().head(15).to_dict()
        insights["top_industries"] = top_ind
        print(f"\n🏢 Top Industries:")
        for i, (ind, count) in enumerate(list(top_ind.items())[:10], 1):
            print(f"  {i}. {ind}: {count}")

    # Locations
    if 'location' in df.columns:
        loc_dist = df['location'].value_counts().head(20).to_dict()
        insights["location_distribution"] = loc_dist
        print(f"\n📍 Top Locations:")
        for i, (loc, count) in enumerate(list(loc_dist.items())[:5], 1):
            print(f"  {i}. {loc}: {count}")

    # Seniority
    if 'seniority_level' in df.columns:
        sen_levels = df['seniority_level'].value_counts().to_dict()
        insights["seniority_levels"] = sen_levels
        print(f"\n📈 Seniority Distribution:")
        for level, count in sen_levels.items():
            print(f"  {level}: {count}")

    # Guardar JSON
    output_file = os.path.join(OUTPUT_DIR, "linkedin_insights.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(insights, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Insights guardados en {output_file}")

    # Guardar también un sample reducido
    sample_cols = [c for c in df.columns if c in ['job_title', 'company_name', 'industry', 'location', 'seniority_level', 'salary']]
    sample_df = df[sample_cols].head(1000)
    sample_file = os.path.join(OUTPUT_DIR, "linkedin_sample.json")
    sample_df.to_json(sample_file, orient='records', indent=2, force_ascii=False)
    print(f"✅ Sample (1000 registros) guardado en {sample_file}")

    return True

if __name__ == "__main__":
    parse_linkedin()

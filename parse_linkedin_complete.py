#!/usr/bin/env python3
"""
Parsear TODOS los datos de LinkedIn (completo)
"""
import pandas as pd
import json
import os
from pathlib import Path

RAW_DIR = "data/raw"
OUTPUT_DIR = "data/processed"

def find_csv(filename_pattern):
    """Buscar archivo CSV en raw"""
    for root, dirs, files in os.walk(RAW_DIR):
        for file in files:
            if filename_pattern.lower() in file.lower() and file.endswith('.csv'):
                return os.path.join(root, file)
    return None

def parse_linkedin_complete():
    """Parsear TODOS los CSVs de LinkedIn"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("📊 LINKEDIN COMPLETE ANALYSIS")
    print("="*60)

    # 1. JOB POSTINGS (principal)
    print("\n1️⃣ Procesando job_postings.csv...")
    job_postings_path = find_csv("job_postings")
    if not job_postings_path:
        print("❌ No encontrado: job_postings.csv")
        return False

    df_jobs = pd.read_csv(job_postings_path, low_memory=False)
    print(f"   📈 Total de empleos: {len(df_jobs)}")
    print(f"   📋 Columnas: {list(df_jobs.columns)}")

    # 2. JOB SKILLS
    print("\n2️⃣ Procesando job_skills.csv...")
    job_skills_path = find_csv("job_skills")
    df_skills = pd.read_csv(job_skills_path) if job_skills_path else None
    if df_skills is not None:
        print(f"   🔧 Total skill records: {len(df_skills)}")
        print(f"   🔧 Columnas: {list(df_skills.columns)}")

    # 3. COMPANIES
    print("\n3️⃣ Procesando companies.csv...")
    companies_path = find_csv("companies")
    df_companies = pd.read_csv(companies_path) if companies_path else None
    if df_companies is not None:
        print(f"   🏢 Total de empresas: {len(df_companies)}")
        print(f"   🏢 Columnas: {list(df_companies.columns)}")

    # 4. JOB INDUSTRIES
    print("\n4️⃣ Procesando job_industries.csv...")
    job_industries_path = find_csv("job_industries")
    df_job_ind = pd.read_csv(job_industries_path) if job_industries_path else None
    if df_job_ind is not None:
        print(f"   🏭 Total registros: {len(df_job_ind)}")

    # 5. EMPLOYEE COUNTS
    print("\n5️⃣ Procesando employee_counts.csv...")
    emp_counts_path = find_csv("employee_counts")
    df_emp_counts = pd.read_csv(emp_counts_path) if emp_counts_path else None
    if df_emp_counts is not None:
        print(f"   👥 Total registros: {len(df_emp_counts)}")

    # ANÁLISIS AGREGADO
    print("\n" + "="*60)
    print("📊 ANÁLISIS AGREGADO")
    print("="*60)

    insights = {
        "metadata": {
            "total_job_postings": len(df_jobs),
            "data_sources": ["job_postings", "job_skills", "companies", "job_industries", "employee_counts"]
        },
        "jobs": {},
        "skills": {},
        "companies": {},
        "industries": {},
        "gap_analysis": {}
    }

    # JOBS ANALYSIS
    print("\n📌 TOP JOB TITLES:")
    if 'job_title' in df_jobs.columns:
        top_titles = df_jobs['job_title'].value_counts().head(20).to_dict()
        insights["jobs"]["top_titles"] = top_titles
        for i, (title, count) in enumerate(list(top_titles.items())[:10], 1):
            print(f"   {i}. {title}: {count}")

    if 'seniority_level' in df_jobs.columns:
        seniority = df_jobs['seniority_level'].value_counts().to_dict()
        insights["jobs"]["seniority_levels"] = seniority
        print("\n📈 SENIORITY DISTRIBUTION:")
        for level, count in seniority.items():
            print(f"   {level}: {count}")

    # SKILLS ANALYSIS
    print("\n🔧 TOP SKILLS (from job_skills.csv):")
    if df_skills is not None and 'skill_name' in df_skills.columns:
        top_skills = df_skills['skill_name'].value_counts().head(20).to_dict()
        insights["skills"]["top_skills"] = top_skills
        for i, (skill, count) in enumerate(list(top_skills.items())[:10], 1):
            print(f"   {i}. {skill}: {count}")

    # COMPANIES ANALYSIS
    print("\n🏢 TOP HIRING COMPANIES:")
    if df_companies is not None and 'company_name' in df_companies.columns:
        # Merge companies con jobs
        if 'company_id' in df_jobs.columns and 'company_id' in df_companies.columns:
            job_company_count = df_jobs['company_id'].value_counts().head(20)
            top_companies = {f"Company {cid}": count for cid, count in job_company_count.items()}
            insights["companies"]["top_hiring_company_ids"] = top_companies
            print(f"   (Basado en {len(job_company_count)} empresas únicas)")
            for i, (company_id, count) in enumerate(list(top_companies.items())[:10], 1):
                print(f"   {i}. {company_id}: {count} postings")

    # INDUSTRIES
    print("\n🏭 INDUSTRIES:")
    if 'industry' in df_jobs.columns:
        industries = df_jobs['industry'].value_counts().head(15).to_dict()
        insights["industries"]["top_industries"] = industries
        print(f"   Total industrias: {len(industries)}")
        for i, (ind, count) in enumerate(list(industries.items())[:10], 1):
            print(f"   {i}. {ind}: {count}")

    # SALARY (si existe)
    if 'salary' in df_jobs.columns:
        print("\n💰 SALARY INFO:")
        print(f"   Registros con salary: {df_jobs['salary'].notna().sum()}")

    # Guardar JSON completo
    output_file = os.path.join(OUTPUT_DIR, "linkedin_complete_insights.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(insights, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Insights guardados en {output_file}")

    # Guardar también CSVs procesados en output
    sample_cols = [c for c in df_jobs.columns if c in ['job_title', 'company_id', 'seniority_level', 'salary', 'job_description']]
    if sample_cols:
        sample_df = df_jobs[sample_cols].head(5000)
        sample_file = os.path.join(OUTPUT_DIR, "linkedin_jobs_sample.csv")
        sample_df.to_csv(sample_file, index=False)
        print(f"✅ Sample CSV guardado en {sample_file}")

    # Resumen
    print("\n" + "="*60)
    print("📊 RESUMEN FINAL")
    print("="*60)
    print(f"✅ Job Postings: {len(df_jobs)}")
    if df_skills is not None:
        print(f"✅ Skill Records: {len(df_skills)}")
    if df_companies is not None:
        print(f"✅ Companies: {len(df_companies)}")
    print(f"\n📁 Output files:")
    print(f"   - {output_file}")
    if sample_cols:
        print(f"   - {sample_file}")

    return True

if __name__ == "__main__":
    parse_linkedin_complete()

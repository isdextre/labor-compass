#!/usr/bin/env python3
"""
Extractor: Future of Work data from Kaggle LinkedIn Jobs
Convierte CSVs en JSONs estructurados para hackathon ideas

Uso:
    python extract_future_of_work.py
    python extract_future_of_work.py --output ./data/processed
"""

import pandas as pd
import json
import sys
import argparse
from pathlib import Path
from collections import defaultdict
import numpy as np


class FutureOfWorkExtractor:
    """Extrae datos de Future of Work desde Kaggle LinkedIn Jobs"""

    def __init__(self, raw_dir='data/raw', output_dir='data/processed'):
        self.raw_dir = Path(raw_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def load_data(self):
        """Carga CSVs de Kaggle"""
        print("📖 Cargando datos de Kaggle LinkedIn...")

        files = {
            'job_postings': self.raw_dir / 'job_postings.csv',
            'job_skills': self.raw_dir / 'job_skills.csv',
            'job_industries': self.raw_dir / 'job_industries.csv',
            'companies': self.raw_dir / 'companies.csv'
        }

        data = {}
        for key, filepath in files.items():
            if not filepath.exists():
                print(f"   ⚠️  {filepath.name} no encontrado (skipping)")
                continue
            try:
                data[key] = pd.read_csv(filepath, low_memory=False)
                print(f"   ✅ {filepath.name}: {len(data[key])} registros")
            except Exception as e:
                print(f"   ❌ Error leyendo {filepath.name}: {e}")

        return data

    def categorize_occupation(self, title):
        """Clasifica ocupaciones en 11 categorías"""
        title_lower = str(title).lower()

        patterns = {
            'Engineering & Development': ['engineer', 'developer', 'programmer', 'architect'],
            'Management & Leadership': ['manager', 'director', 'lead', 'principal', 'head', 'cto', 'cfo'],
            'Sales': ['sales', 'representative', 'account executive', 'business development'],
            'Data & Analytics': ['analyst', 'data', 'scientist', 'statistician'],
            'Administrative & Clerical': ['admin', 'assistant', 'coordinator', 'clerk', 'secretary'],
            'Finance & Accounting': ['finance', 'accountant', 'audit', 'controller', 'cpa'],
            'Marketing & Communications': ['marketing', 'brand', 'communications', 'social media', 'content'],
            'Human Resources': ['hr', 'recruit', 'talent', 'human resources'],
            'Healthcare': ['health', 'nurse', 'physician', 'medical', 'therapist'],
            'Retail & Customer Service': ['retail', 'cashier', 'store', 'customer service'],
        }

        for category, keywords in patterns.items():
            if any(kw in title_lower for kw in keywords):
                return category

        return 'Other'

    def add_seniority(self, jobs_df):
        """Agrega clasificación de seniority"""
        jobs_df['seniority'] = 'Mid-Level'

        senior_pattern = ['Senior', 'Lead', 'Principal', 'Manager', 'Director', 'Head']
        entry_pattern = ['Junior', 'Entry', 'Associate', 'Analyst', 'Coordinator', 'Intern']

        jobs_df.loc[jobs_df['title'].str.contains('|'.join(senior_pattern), case=False, na=False), 'seniority'] = 'Senior'
        jobs_df.loc[jobs_df['title'].str.contains('|'.join(entry_pattern), case=False, na=False), 'seniority'] = 'Entry-Level'

        return jobs_df

    def extract_occupation_taxonomy(self, jobs):
        """Genera: 01_FUTURE_WORK_occupation_taxonomy.json"""
        print("\n📋 Extrayendo: Occupation Taxonomy...")

        jobs['occupation_category'] = jobs['title'].apply(self.categorize_occupation)

        taxonomy = {}
        for category in jobs['occupation_category'].unique():
            cat_jobs = jobs[jobs['occupation_category'] == category]

            taxonomy[category] = {
                'job_count': len(cat_jobs),
                'avg_salary': float(cat_jobs[cat_jobs['med_salary'].notna()]['med_salary'].mean())
                              if cat_jobs['med_salary'].notna().any() else None,
                'seniority_distribution': cat_jobs['seniority'].value_counts().to_dict(),
                'remote_friendly': float(cat_jobs['remote_allowed'].sum() / len(cat_jobs))
                                  if len(cat_jobs) > 0 else 0,
                'top_titles': cat_jobs['title'].value_counts().head(5).to_dict(),
                'sample_positions': cat_jobs['title'].unique()[:3].tolist()
            }

        output_file = self.output_dir / '01_FUTURE_WORK_occupation_taxonomy.json'
        with open(output_file, 'w') as f:
            json.dump(taxonomy, f, indent=2, default=str)

        print(f"   ✅ {len(taxonomy)} ocupaciones mapeadas → {output_file.name}")
        return taxonomy, jobs

    def extract_skills_genealogy(self, jobs, skills_df):
        """Genera: 02_FUTURE_WORK_skills_genealogy.json"""
        print("\n📋 Extrayendo: Skills Genealogy...")

        job_skills_map = skills_df.groupby('job_id')['skill_abr'].apply(list).to_dict()

        skill_cooccurrence = defaultdict(lambda: defaultdict(int))
        for job_id, skill_list in job_skills_map.items():
            for i, skill1 in enumerate(skill_list):
                for skill2 in skill_list[i+1:]:
                    skill_cooccurrence[skill1][skill2] += 1
                    skill_cooccurrence[skill2][skill1] += 1

        skills_output = {
            'total_unique_skills': skills_df['skill_abr'].nunique(),
            'skill_frequencies': skills_df['skill_abr'].value_counts().head(25).to_dict(),
            'skill_dependencies': {
                skill: dict(sorted(deps.items(), key=lambda x: x[1], reverse=True)[:5])
                for skill, deps in dict(sorted(skill_cooccurrence.items(),
                                               key=lambda x: len(x[1]), reverse=True)[:20]).items()
            },
            'jobs_with_multiple_skills': sum(1 for sl in job_skills_map.values() if len(sl) > 1),
            'avg_skills_per_job': round(np.mean([len(sl) for sl in job_skills_map.values()]), 2)
        }

        output_file = self.output_dir / '02_FUTURE_WORK_skills_genealogy.json'
        with open(output_file, 'w') as f:
            json.dump(skills_output, f, indent=2, default=str)

        print(f"   ✅ {skills_output['total_unique_skills']} skills mapeados → {output_file.name}")
        return skills_output

    def extract_salary_transitions(self, jobs):
        """Genera: 03_FUTURE_WORK_salary_transitions.json"""
        print("\n📋 Extrayendo: Salary Transitions...")

        salary_transitions = {}
        jobs_with_sal = jobs[jobs['med_salary'].notna()].copy()

        for cat in jobs_with_sal['occupation_category'].unique():
            cat_data = jobs_with_sal[jobs_with_sal['occupation_category'] == cat]

            salary_transitions[cat] = {
                'current_avg_salary': float(cat_data['med_salary'].mean()),
                'salary_range': {
                    'min': float(cat_data['min_salary'].mean()),
                    'median': float(cat_data['med_salary'].median()),
                    'max': float(cat_data['max_salary'].mean())
                },
                'by_seniority': {
                    level: {
                        'avg_salary': float(cat_data[cat_data['seniority'] == level]['med_salary'].mean()),
                        'count': len(cat_data[cat_data['seniority'] == level])
                    }
                    for level in ['Entry-Level', 'Mid-Level', 'Senior']
                    if len(cat_data[cat_data['seniority'] == level]) > 0
                }
            }

        output_file = self.output_dir / '03_FUTURE_WORK_salary_transitions.json'
        with open(output_file, 'w') as f:
            json.dump(salary_transitions, f, indent=2, default=str)

        print(f"   ✅ Salary data para {len(salary_transitions)} ocupaciones → {output_file.name}")
        return salary_transitions

    def extract_seniority_progression(self, jobs):
        """Genera: 04_FUTURE_WORK_seniority_progression.json"""
        print("\n📋 Extrayendo: Seniority Progression...")

        seniority_progression = {}

        for cat in jobs['occupation_category'].unique():
            cat_jobs = jobs[jobs['occupation_category'] == cat]
            cat_with_sal = cat_jobs[cat_jobs['med_salary'].notna()]

            progression_data = {
                'occupation': cat,
                'total_positions': len(cat_jobs),
                'seniority_distribution': cat_jobs['seniority'].value_counts().to_dict(),
                'career_path': []
            }

            for level in ['Entry-Level', 'Mid-Level', 'Senior']:
                level_jobs = cat_with_sal[cat_with_sal['seniority'] == level]
                if len(level_jobs) > 0:
                    progression_data['career_path'].append({
                        'level': level,
                        'position_count': len(level_jobs),
                        'avg_salary': float(level_jobs['med_salary'].mean()),
                        'example_titles': level_jobs['title'].unique()[:3].tolist()
                    })

            if progression_data['career_path']:
                seniority_progression[cat] = progression_data

        output_file = self.output_dir / '04_FUTURE_WORK_seniority_progression.json'
        with open(output_file, 'w') as f:
            json.dump(seniority_progression, f, indent=2, default=str)

        print(f"   ✅ Career paths para {len(seniority_progression)} ocupaciones → {output_file.name}")
        return seniority_progression

    def extract_market_demand(self, jobs, skills_df):
        """Genera: 05_FUTURE_WORK_market_demand.json"""
        print("\n📋 Extrayendo: Market Demand...")

        market_demand = {'by_occupation': {}}

        for cat in jobs['occupation_category'].unique():
            cat_jobs = jobs[jobs['occupation_category'] == cat]
            salary_data = cat_jobs[pd.to_numeric(cat_jobs['med_salary'], errors='coerce').notna()]

            cat_job_ids = cat_jobs['job_id'].values
            cat_skills = skills_df[skills_df['job_id'].isin(cat_job_ids)]['skill_abr'].value_counts().head(5).index.tolist()

            entry_level_jobs = salary_data[salary_data['seniority'] == 'Entry-Level']
            senior_jobs = salary_data[salary_data['seniority'] == 'Senior']

            entry_avg = float(entry_level_jobs['med_salary'].mean()) if len(entry_level_jobs) > 0 else None
            senior_avg = float(senior_jobs['med_salary'].mean()) if len(senior_jobs) > 0 else None

            salary_premium = None
            if entry_avg and senior_avg and entry_avg > 0:
                salary_premium = round((senior_avg - entry_avg) / entry_avg * 100, 1)

            market_demand['by_occupation'][cat] = {
                'position_count': len(cat_jobs),
                'growth_indicator': 'high' if len(cat_jobs) > 500 else 'medium' if len(cat_jobs) > 200 else 'low',
                'remote_adoption_rate': round(float(cat_jobs['remote_allowed'].sum() / len(cat_jobs)), 3),
                'salary_premium_senior_to_entry': salary_premium,
                'top_required_skills': cat_skills,
                'seniority_distribution': cat_jobs['seniority'].value_counts().to_dict()
            }

        market_demand['metadata'] = {
            'total_positions': len(jobs),
            'total_occupations': len(jobs['occupation_category'].unique()),
            'data_quality': {
                'salary_coverage': f"{len(jobs[jobs['med_salary'].notna()]) / len(jobs) * 100:.1f}%",
                'remote_allowed_coverage': f"{len(jobs[jobs['remote_allowed'].notna()]) / len(jobs) * 100:.1f}%"
            }
        }

        output_file = self.output_dir / '05_FUTURE_WORK_market_demand.json'
        with open(output_file, 'w') as f:
            json.dump(market_demand, f, indent=2, default=str)

        print(f"   ✅ Market demand para {len(market_demand['by_occupation'])} ocupaciones → {output_file.name}")
        return market_demand

    def extract_occupation_transitions(self, jobs, skills_df):
        """Genera: 07_FUTURE_WORK_occupation_transitions.json"""
        print("\n📋 Extrayendo: Occupation Transitions...")

        occupation_skills = {}
        for cat in jobs['occupation_category'].unique():
            cat_job_ids = jobs[jobs['occupation_category'] == cat]['job_id'].values
            cat_skills = set(skills_df[skills_df['job_id'].isin(cat_job_ids)]['skill_abr'].unique())
            occupation_skills[cat] = cat_skills

        transitions = {}
        occupations = list(occupation_skills.keys())

        for occ1 in occupations:
            transitions[occ1] = {}
            for occ2 in occupations:
                if occ1 != occ2:
                    skills1 = occupation_skills[occ1]
                    skills2 = occupation_skills[occ2]
                    overlap = len(skills1 & skills2)
                    union = len(skills1 | skills2)
                    similarity = round(overlap / union * 100, 1) if union > 0 else 0

                    transitions[occ1][occ2] = {
                        'skill_similarity': similarity,
                        'common_skills': list(skills1 & skills2)[:3],
                        'transition_difficulty': 'Easy' if similarity > 70 else 'Moderate' if similarity > 40 else 'Hard'
                    }

        output_file = self.output_dir / '07_FUTURE_WORK_occupation_transitions.json'
        with open(output_file, 'w') as f:
            json.dump(transitions, f, indent=2, default=str)

        print(f"   ✅ Transition matrix para {len(transitions)} ocupaciones → {output_file.name}")
        return transitions

    def ejecutar(self):
        """Ejecuta extracción completa"""
        print("\n" + "="*80)
        print("🚀 FUTURE OF WORK DATA EXTRACTION")
        print("="*80)

        # Cargar datos
        data = self.load_data()

        if not data or 'job_postings' not in data:
            print("\n❌ No se encontraron datos de Kaggle. Verifica data/raw/")
            return False

        jobs = data['job_postings']
        skills_df = data.get('job_skills', pd.DataFrame())

        # Agregar clasificaciones
        jobs = self.add_seniority(jobs)

        # Extraer cada componente
        taxonomy, jobs = self.extract_occupation_taxonomy(jobs)

        if not skills_df.empty:
            self.extract_skills_genealogy(jobs, skills_df)
            self.extract_occupation_transitions(jobs, skills_df)
            self.extract_market_demand(jobs, skills_df)

        self.extract_salary_transitions(jobs)
        self.extract_seniority_progression(jobs)

        # Resumen
        print("\n" + "="*80)
        print("✅ EXTRACCIÓN COMPLETADA")
        print("="*80)
        print(f"\n📁 Archivos guardados en: {self.output_dir.absolute()}")
        print("\n📊 Archivos generados:")
        for f in sorted(self.output_dir.glob('0*_FUTURE_WORK*.json')):
            size_kb = f.stat().st_size / 1024
            print(f"   • {f.name} ({size_kb:.1f} KB)")

        return True


def main():
    parser = argparse.ArgumentParser(
        description='Extrae datos Future of Work desde Kaggle LinkedIn Jobs'
    )
    parser.add_argument(
        '--output',
        default='data/processed',
        help='Directorio de salida (default: data/processed)'
    )
    parser.add_argument(
        '--raw',
        default='data/raw',
        help='Directorio con CSVs de Kaggle (default: data/raw)'
    )

    args = parser.parse_args()

    extractor = FutureOfWorkExtractor(raw_dir=args.raw, output_dir=args.output)
    success = extractor.ejecutar()

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())

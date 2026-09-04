# 🚀 Future of Work - JSON Data Exports
## Kaggle LinkedIn Jobs → Structured Data for Hackathon Ideas

Generated: September 4, 2026  
Source: LinkedIn Job Postings Dataset (Kaggle)  
Records Processed: 15,886 job postings + 27,899 skill records

---

## 📊 JSON Files Explanation

### 1️⃣ `01_FUTURE_WORK_occupation_taxonomy.json`
**Purpose:** Occupational classification for Transition Radar & Wage Bridge Calculator

**Contents:**
- 11 occupation categories (Engineering, Sales, Admin, Finance, etc.)
- For each category:
  - `job_count`: Number of positions available
  - `avg_salary`: Average salary for the role
  - `seniority_distribution`: Entry-Level / Mid-Level / Senior split
  - `remote_friendly`: % of positions with remote work
  - `top_titles`: Most common job titles in this category
  - `sample_positions`: Example job titles

**Use Cases:**
- "What occupations are available?" → for Transition Radar initial selection
- "What's the salary for Admin roles?" → for Wage Bridge Calculator
- "Is Data Analytics remote-friendly?" → check remote_friendly score

**Example Structure:**
```json
{
  "Engineering & Development": {
    "job_count": 1993,
    "avg_salary": 89542.5,
    "seniority_distribution": {...},
    "remote_friendly": 0.147,
    "top_titles": {...}
  }
}
```

---

### 2️⃣ `02_FUTURE_WORK_skills_genealogy.json`
**Purpose:** Skill dependency mapping for Skills Genealogy idea

**Contents:**
- `total_unique_skills`: 35 skill categories (IT, SALE, MGMT, etc.)
- `skill_frequencies`: Top 25 most demanded skills
- `skill_dependencies`: Co-occurrence patterns (skills that appear together)
  - Shows which skills are prerequisite/related to others
  - Top 5 co-occurrences per skill

**Use Cases:**
- "What skills do I need to transition from Admin to Data?" → look at skill overlap
- "If I know IT, what other skills are naturally paired?" → see dependencies
- "Is SQL related to Python jobs?" → check co-occurrence

**Example Structure:**
```json
{
  "total_unique_skills": 35,
  "skill_frequencies": {
    "IT": 3841,
    "SALE": 2904,
    "MGMT": 2467
  },
  "skill_dependencies": {
    "IT": {"ENG": 850, "MNFC": 720, "BD": 650},
    "SALE": {"MGMT": 1200, "BD": 890}
  }
}
```

---

### 3️⃣ `03_FUTURE_WORK_salary_transitions.json`
**Purpose:** Salary data by occupation for Wage Bridge Calculator

**Contents:**
- For each occupation category:
  - `current_avg_salary`: Overall average salary
  - `salary_range`: min/median/max across all positions
  - `by_seniority`: Salary breakdown by Entry/Mid/Senior levels

**Use Cases:**
- "If I transition from Admin ($45k) to Data Analytics ($75k), what's my salary increase?" 
- "What's the salary range for Senior engineers vs Junior?" → see progression
- "How much do I earn if I stay in Retail vs move to Logistics?" → compare paths

**Example Structure:**
```json
{
  "Engineering & Development": {
    "current_avg_salary": 89542.5,
    "salary_range": {
      "min": 65000,
      "median": 85000,
      "max": 120000
    },
    "by_seniority": {
      "Entry-Level": {"avg_salary": 65000, "count": 450},
      "Mid-Level": {"avg_salary": 85000, "count": 1000},
      "Senior": {"avg_salary": 115000, "count": 543}
    }
  }
}
```

---

### 4️⃣ `04_FUTURE_WORK_seniority_progression.json`
**Purpose:** Career pathways within occupations (Entry → Mid → Senior)

**Contents:**
- For each occupation:
  - `career_path`: Array of progression steps
  - Each step shows:
    - `level`: Entry-Level, Mid-Level, or Senior
    - `position_count`: Number of openings at this level
    - `avg_salary`: Average salary at this level
    - `example_titles`: Real job titles at this level

**Use Cases:**
- "What's the typical career progression from Entry to Senior in Engineering?"
- "How many mid-level positions are available vs entry-level?" → pipeline depth
- "What titles exist at each seniority level?" → understand roles

**Example Structure:**
```json
{
  "Engineering & Development": {
    "career_path": [
      {
        "level": "Entry-Level",
        "position_count": 450,
        "avg_salary": 65000,
        "example_titles": ["Junior Developer", "Associate Engineer"]
      },
      {
        "level": "Mid-Level",
        "position_count": 1000,
        "avg_salary": 85000,
        "example_titles": ["Software Engineer", "Development Lead"]
      }
    ]
  }
}
```

---

### 5️⃣ `05_FUTURE_WORK_market_demand.json`
**Purpose:** Current market demand signals by occupation (for Policy Simulator)

**Contents:**
- `by_occupation`: For each role:
  - `position_count`: Number of open positions (demand indicator)
  - `growth_indicator`: 'high' / 'medium' / 'low' based on position count
  - `salary_premium_senior_to_entry`: % salary increase from Entry to Senior
  - `remote_adoption_rate`: % of positions with remote work
  - `top_required_skills`: Most common skills for this role
  - `seniority_distribution`: Entry/Mid/Senior split

**Use Cases:**
- "Which occupations have highest demand?" → sort by position_count
- "Is Data Analytics growing?" → check growth_indicator
- "Do Management roles pay more as you advance?" → see salary_premium
- "Can I work remote in my field?" → check remote_adoption_rate

**Example Structure:**
```json
{
  "by_occupation": {
    "Engineering & Development": {
      "position_count": 1993,
      "growth_indicator": "high",
      "salary_premium_senior_to_entry": 77.5,
      "remote_adoption_rate": 0.147,
      "top_required_skills": ["IT", "ENG", "MNFC"],
      "seniority_distribution": {"Entry-Level": 450, "Mid-Level": 1000, "Senior": 543}
    }
  },
  "metadata": {
    "total_positions": 15886,
    "total_occupations": 11,
    "data_quality": {"salary_coverage": "34.8%"}
  }
}
```

---

### 6️⃣ `07_FUTURE_WORK_occupation_transitions.json`
**Purpose:** Skill similarity between occupations (for Transition Radar matching)

**Contents:**
- For each occupation pair (e.g., Admin → Engineer):
  - `skill_similarity`: % overlap of skills required (0-100)
  - `common_skills`: Shared skills between roles
  - `transition_difficulty`: 'Easy' (>70% match) / 'Moderate' (40-70%) / 'Hard' (<40%)

**Use Cases:**
- "Can I transition from Admin to Data Analytics?" → check skill_similarity & transition_difficulty
- "What skills do Admin and Engineering have in common?" → see common_skills
- "Which occupations are easiest for me to move into?" → find high similarity scores
- "How many new skills do I need to learn?" → 100% - similarity% = new skills required

**Example Structure:**
```json
{
  "Administrative & Clerical": {
    "Finance & Accounting": {
      "skill_similarity": 65.3,
      "common_skills": ["IT", "ADM", "FIN"],
      "transition_difficulty": "Moderate"
    },
    "Data & Analytics": {
      "skill_similarity": 42.1,
      "common_skills": ["IT", "ANLS"],
      "transition_difficulty": "Hard"
    }
  }
}
```

---

## 🎯 How to Use These JSONs for Hackathon Ideas

### Idea #1: Transition Radar
**Primary files:**
- `07_FUTURE_WORK_occupation_transitions.json` → Show skill matches
- `04_FUTURE_WORK_seniority_progression.json` → Show career paths
- `05_FUTURE_WORK_market_demand.json` → Validate target role has jobs

**Logic:**
```
User input: "I'm an Admin worker"
→ Look up Admin in occupation_transitions.json
→ Show transition options sorted by skill_similarity (highest first)
→ Display: "You match 65% with Finance (Moderate difficulty)"
→ Use seniority_progression to show: "Enter as Junior Accountant ($45k), advance to Senior ($80k in 5 years)"
→ Validate demand: Check position_count for Finance roles is > 0
```

---

### Idea #2: Wage Bridge Calculator
**Primary files:**
- `03_FUTURE_WORK_salary_transitions.json` → Current and target salaries
- `04_FUTURE_WORK_seniority_progression.json` → Salary by level

**Logic:**
```
User input: "I'm Admin earning $45k, want to be Data Analyst"
→ Get current salary from occupation_taxonomy or salary_transitions
→ Get target salary from Data & Analytics in salary_transitions
→ Calculate: "Current: $45k → After 6mo training: $50k (entry-level Data role) → Year 1: $65k → Year 3: $85k"
→ Compare: "If you stayed in Admin, Year 3 = $50k (wage stagnation)"
→ ROI: "Investing 6 months = +$35k/year long-term"
```

---

### Idea #3: Skills Genealogy
**Primary files:**
- `02_FUTURE_WORK_skills_genealogy.json` → Skill dependencies & co-occurrence
- `07_FUTURE_WORK_occupation_transitions.json` → Common skills by transition

**Logic:**
```
User input: "I have IT skills, what can I transition to?"
→ Look up IT in skill_dependencies.json
→ Show: IT co-occurs with ENG (engineers), SALE (sales roles), MGMT (managers)
→ Find all occupations requiring IT
→ For each, show: "Engineering (needs IT + ENG + MNFC). You have IT. Gap: 2/3 skills"
→ Recommend: "Learn ENG + MNFC in X weeks" using salary payoff data
```

---

### Idea #4: Market Demand Signals
**Primary files:**
- `05_FUTURE_WORK_market_demand.json` → Position count & growth
- `01_FUTURE_WORK_occupation_taxonomy.json` → Category overview

**Logic:**
```
Hourly update (simulated):
→ Check position_count for each occupation
→ Compare to last week's data
→ Flag occupations with growing/declining demand
→ Alert: "Data Analytics +12% job openings this week vs last week — high demand!"
→ Counter-alert: "Administrative roles -8% openings — recommend transition now"
```

---

## 📈 Data Quality Notes

| Metric | Value | Coverage |
|--------|-------|----------|
| Total Jobs | 15,886 | 100% |
| Salary Data | 5,521 | 34.8% |
| Remote Allowed | 2,340 | 14.7% |
| Skill Records | 27,899 | ~175% (jobs have multiple skills) |
| Occupations | 11 categories | Coverage of all roles |

**Gaps:** Only 34.8% of jobs have salary data (Kaggle dataset limitation). Fill gaps with WEF global data + MTPE Peru salaries.

---

## 🔗 Integration Tips

1. **Combine with WEF data:** Kaggle shows current job market, WEF shows future trends (2026-2030)
2. **Add Peru context:** Map occupation_taxonomy to INEI ocupaciones
3. **Gender layer:** Kaggle doesn't have gender, but WEF does — cross reference
4. **Real-time updates:** These JSONs are snapshots. In production, refresh weekly

---

## 🚀 Next Steps

1. Load these JSONs into your hackathon codebase
2. Build frontend (React/Vue) that visualizes transitions
3. Use occupation_transitions.json as the core recommendation engine
4. Display salary_transitions data as ROI calculator
5. Add skill_genealogy as a dependency tree visualization

Good luck with the hackathon! 🎉

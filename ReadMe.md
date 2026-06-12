# Chicago Bears NFL Analytics Platform

## Dashboard preview

![NFL Analytics Dashboard](dashboard_preview.png)

> Bears navy + orange theme · KPI cards · EPA scatter · 3rd down conversion · red zone TD rate · pass rate heatmap · Bears weekly EPA trend (2022–2024)

> A full-stack football analytics system built independently — from raw play-by-play ingestion to an interactive dashboard, win probability model, 4th down decision engine, and front-office scouting tools. Designed to mirror the analytical work done across all five Football Operations departments.

![Python](https://img.shields.io/badge/Python-3.11-blue) ![Dash](https://img.shields.io/badge/Plotly_Dash-interactive-informational) ![MySQL](https://img.shields.io/badge/MySQL-SQLAlchemy-orange) ![scikit-learn](https://img.shields.io/badge/scikit--learn-logistic_regression-yellow) ![Data](https://img.shields.io/badge/nflfastR-50k+_plays-green)

---

## Why I built this

NFL analytics is one of the most data-rich environments in professional sports, and the Chicago Bears are investing heavily in building that capability. I wanted to understand — from the ground up — how data actually drives decisions inside a football organization. So I built the infrastructure, the models, and the tools myself.

No tutorials. No prior football knowledge. Just play-by-play data, Python, and a commitment to building something real.

---

## What's inside

| Component | Description |
|---|---|
| **Data pipeline** | 50,000+ NFL plays (2022–2024), ingested from nfl_data_py / nflfastR into MySQL via SQLAlchemy |
| **Win probability model** | Logistic regression predicting game outcomes — ~70.6% accuracy, AUC 0.764 |
| **Run/pass prediction model** | Binary classifier predicting play call tendency — ~68% accuracy, consistent with published research |
| **4th down recommender** | Go / Punt / Field Goal recommendation engine with EPA-calibrated expected value |
| **Opponent scouting report** | Data-driven tendency report by team — same format used by real NFL analytics departments |
| **Cap efficiency analyzer** | EPA per $1M APY — identifies best and worst contract value on the Bears roster |
| **Caleb Williams rookie analysis** | Benchmarks his 2024 EPA/dropback vs. all rookie QBs and the league median |
| **Interactive dashboard** | Plotly Dash app — EPA, 3rd down, red zone, game situation heatmap, Bears weekly trend |
| **Analytical SQL library** | 8 production-ready queries covering efficiency, situational, and Bears-specific analysis |

---

## Football Operations coverage

This project was built to address the analytical needs of all five Football Operations departments:

### Coaching
- Run/pass prediction model with 17 features including down, distance, formation, score differential, and clock
- 4th down Go/Punt/FG recommender with expected EPA for each option, calibrated to historical conversion rates
- Game situation heatmap — pass rate % by down × distance bucket

### Player Personnel
- Caleb Williams rookie benchmarking (EPA/dropback, air yards, weekly trend vs. 2024 class and league median)
- EPA-based player rankings with minimum dropback/carry filters
- Draft pick value model and trade evaluator

### Salary Cap
- Cap efficiency analyzer joining MySQL EPA aggregates to nflverse contract data
- Bears full cap breakdown with best/worst value contracts by position
- EPA per $1M APY rankings — identifies players outperforming or underperforming their contracts

### Sports Science
- Player availability tracker by team and season
- Injury burden correlation — weeks missed vs. team EPA impact

### Analytics & Research
- End-to-end reproducible pipeline from raw data to interactive dashboard
- Bears-specific EDA: EPA trends, red zone efficiency, NFC North comparisons across 3 seasons

---

## Key findings

### League-wide (2022–2024)
- Pass EPA has grown each season; run EPA has remained near −0.05 league average
- Teams with positive EPA pass territory win significantly more — strong correlation with W/L record
- Pass rate on 3rd & 8+ approaches 90%+ league-wide

### Chicago Bears
- 2022–2023: Below-league-average EPA on both pass and run
- 2024: Meaningful pass EPA improvement with the quarterback transition to Caleb Williams
- Red zone efficiency has been a consistent weak point vs. NFC North peers across all 3 seasons

### NFC North
- Detroit Lions showed the largest EPA improvement over the 3-season window
- Green Bay's passing efficiency dipped in 2022 (transition year) and rebounded in 2023–2024
- Minnesota has maintained top-half pass EPA consistently

---

## Model details

### Win probability model

| Metric | Value |
|---|---|
| Test accuracy | ~70.6% |
| ROC-AUC | 0.764 |
| 5-fold CV | ~69.8% ± 0.4% |

**Features:** down, yards to go, yardline, score differential, half seconds remaining, shotgun, goal-to-go, must-pass flag, two-minute drill flag, + interaction terms

### Run/pass prediction model

| Metric | Value |
|---|---|
| Test accuracy | ~68% |
| ROC-AUC | ~0.74 |
| 5-fold CV | ~67.5% ± 0.5% |

The ~68% ceiling is consistent with published NFL analytics research. Play-calling has intentional randomness by design — a perfect model would be exploitable by defenses.

**Note on the cap efficiency analyzer:** The current implementation joins on player name strings (e.g., `"C.Williams"` in play-by-play vs. `"Caleb Williams"` in contracts). A production system would join on `gsis_id` via `nfl.import_ids()` or Sleeper IDs for a stable, format-agnostic key. This is documented here intentionally — it's a standard data engineering consideration worth flagging in any real deployment.

---

## Analytical SQL queries

`sql/queries.sql` contains 8 production-ready queries:

1. Team offensive efficiency — EPA by season
2. Third-down conversion rates by team
3. Red zone scoring efficiency (TD rate)
4. Run/pass tendency by down & distance
5. Bears-specific analysis across all 3 seasons
6. NFC North head-to-head comparisons
7. Top passers by EPA (minimum dropback filter)
8. Game situation splits by score differential bucket

---

## Dashboard features

Launch at `http://localhost:8050` after running `dashboard/app.py`.

- **EPA scatter** — Pass EPA vs. Run EPA for every team; highlighted team in Bears navy
- **3rd down bar** — Horizontal ranked bar chart by conversion rate
- **Red zone bar** — TD rate per team
- **Game situation heatmap** — Pass rate % by down × distance
- **Bears weekly trend** — EPA/play by week across all 3 seasons
- **KPI cards** — Selected team's EPA, pass rate, 3rd down %, red zone TD rate
- Season filter and team toggle — switch between League / NFC North / Bears views

---

## Repository structure

```
nfl-analytics/
├── data/
│   └── ingest.py                  # Pull from nfl_data_py → clean → MySQL
├── sql/
│   └── queries.sql                # 8 analytical queries
├── notebooks/
│   └── 01_eda.py                  # EDA — Bears + NFC North focus (jupytext)
├── models/
│   ├── win_probability_model.py   # Logistic regression: win probability
│   ├── run_pass_model.py          # Logistic regression: play call tendency
│   ├── fourth_down_recommender.py # Go / Punt / FG engine
│   ├── cap_efficiency.py          # EPA per $1M APY analyzer
│   ├── scouting_report.py         # Opponent tendency generator
│   ├── caleb_williams_analysis.py # Rookie benchmarking
│   └── *.pkl / model_metadata.json
├── dashboard/
│   └── app.py                     # Plotly Dash interactive app
├── requirements.txt
└── README.md
```

---

## Quick start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Set up MySQL
```sql
CREATE DATABASE nfl_analytics;
```

Update `DB_URL` in `data/ingest.py`, `models/`, and `dashboard/app.py`:
```python
DB_URL = "mysql+pymysql://YOUR_USER:YOUR_PASS@localhost/nfl_analytics"
```

### 3. Ingest data (~5 minutes)
```bash
python data/ingest.py
```
Pulls 3 seasons of play-by-play, filters to skill plays (~50k rows), loads into MySQL with indexes.

### 4. Run EDA
```bash
jupyter notebook notebooks/01_eda.py
# or via jupytext:
jupytext --to notebook notebooks/01_eda.py && jupyter notebook notebooks/01_eda.ipynb
```

### 5. Train models
```bash
python models/win_probability_model.py
python models/run_pass_model.py
```

### 6. Launch dashboard
```bash
python dashboard/app.py
```
Open `http://localhost:8050`

---

## Tools & libraries

| Category | Libraries |
|---|---|
| Data ingestion | nfl_data_py, pandas, numpy |
| Database | MySQL, SQLAlchemy, PyMySQL |
| Modeling | scikit-learn (logistic regression, cross-validation, ROC-AUC) |
| Visualization (static) | matplotlib, seaborn |
| Dashboard | Plotly, Dash |
| Notebooks | jupytext |

**Data source:** All play-by-play data from [nfl_data_py](https://github.com/nflverse/nfl_data_py), a Python wrapper around [nflfastR](https://www.nflfastr.com/) — the same underlying dataset used by analysts across the league and in academic NFL research.

---

*Built independently. Data: nflverse / nflfastR. Not affiliated with the Chicago Bears or the NFL.*

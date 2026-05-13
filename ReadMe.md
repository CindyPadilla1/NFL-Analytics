# NFL Play-by-Play Analytics Dashboard

End-to-end NFL analytics pipeline: data ingestion → MySQL database → exploratory analysis → logistic regression model → interactive Plotly Dash dashboard. Built as a personal project to deepen applied data science skills using real football data.

---

## Project Overview

| Component | Description |
|-----------|-------------|
| **Data** | 50,000+ NFL plays (2022–2024), sourced from nfl_data_py (nflfastR) |
| **Database** | MySQL via SQLAlchemy — plays, rosters, schedules tables |
| **EDA** | Reproducible Jupyter notebooks, Bears + NFC North focus |
| **Model** | Logistic regression predicting run vs. pass (~68% test accuracy) |
| **Dashboard** | Interactive Plotly Dash app — EPA, 3rd down, red zone, game situation |

---

## Repository Structure

```
nfl-analytics/
├── data/
│   └── ingest.py             # Pull from nfl_data_py → clean → MySQL
├── sql/
│   └── queries.sql           # Analytical queries (efficiency, situational, Bears)
├── notebooks/
│   └── 01_eda.py             # EDA (run as Jupyter via jupytext)
├── models/
│   ├── run_pass_model.py     # Logistic regression: train + evaluate + plots
│   ├── run_pass_model.pkl    # Saved model (after training)
│   └── model_metadata.json   # Accuracy, AUC, feature list
├── dashboard/
│   └── app.py                # Plotly Dash interactive dashboard
├── requirements.txt
└── README.md
```

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set up MySQL

```sql
CREATE DATABASE nfl_analytics;
```

Update the `DB_URL` in `data/ingest.py`, `models/run_pass_model.py`, and `dashboard/app.py`:

```python
DB_URL = "mysql+pymysql://YOUR_USER:YOUR_PASS@localhost/nfl_analytics"
```

### 3. Ingest data (takes ~5 minutes)

```bash
python data/ingest.py
```

This pulls 3 seasons of play-by-play, cleans it to skill plays only (~50k rows), and loads it into MySQL with indexes.

### 4. Run the EDA notebook

```bash
jupyter notebook notebooks/01_eda.py
# or via jupytext:
jupytext --to notebook notebooks/01_eda.py && jupyter notebook notebooks/01_eda.ipynb
```

### 5. Train the model

```bash
python models/run_pass_model.py
```

Outputs: `run_pass_model.pkl`, `confusion_matrix.png`, `roc_curve.png`, `feature_importance.png`

### 6. Launch the dashboard

```bash
python dashboard/app.py
```

Open `http://localhost:8050` — filter by season, highlight any team, toggle League / NFC North / Bears views.

---

## Data Source

All play-by-play data comes from **[nfl_data_py](https://github.com/nflverse/nfl_data_py)**, a Python wrapper around the **nflfastR** dataset maintained by the nflverse project. This is the same underlying data used by analysts across the league and in academic research.

Data includes ~300 columns per play covering:
- EPA (Expected Points Added) and WPA (Win Probability Added)
- Down, distance, field position, score differential, game clock
- Formation, personnel, play direction
- Player IDs for passers, rushers, and receivers

---

## Model Details

**Task:** Binary classification — predict run (0) vs. pass (1)

**Features:**

| Feature | Description |
|---------|-------------|
| `down` | Down number (1–4) |
| `ydstogo` | Yards needed for first down |
| `yardline_100` | Distance from end zone |
| `score_differential` | Posteam score minus defteam score |
| `half_seconds_remaining` | Clock in current half |
| `shotgun` | Shotgun formation flag |
| `goal_to_go` | Goal-to-go situation flag |
| `must_pass` | 3rd/4th + 8+ yards derived feature |
| `two_minute_drill` | < 2 min left in half |
| + 10 interaction/derived features | |

**Results (2022–2024 holdout):**

| Metric | Value |
|--------|-------|
| Test Accuracy | ~68% |
| ROC-AUC | ~0.74 |
| 5-Fold CV | ~67.5% ± 0.5% |

The ~68% ceiling is consistent with published NFL analytics research — play-calling has intentional randomness by design, and a perfect model would be exploitable by defenses.

---

## Key Findings

### League-Wide (2022–2024)
- Pass EPA has grown each season; run EPA has remained relatively stable around −0.05
- Teams in positive EPA pass territory tend to win more games (strong correlation with W/L)
- Pass rate on 3rd & 8+ approaches 90%+ league-wide

### Chicago Bears
- 2022–2023: Below-league-average EPA on both pass and run
- 2024: Pass EPA improvement with quarterback change; run EPA relatively stable
- Red zone efficiency has been a consistent weak point vs. NFC North peers

### NFC North
- Detroit Lions showed the largest EPA improvement over the 3-season window
- Green Bay's passing efficiency dipped in 2022 (transition year) and rebounded in 2023–2024
- Minnesota has maintained top-half pass EPA consistently

---

## Analytical SQL Queries

`sql/queries.sql` contains 8 production-ready queries covering:
1. Team offensive efficiency (EPA by season)
2. Third-down conversion rates
3. Red zone scoring efficiency
4. Run/pass tendency by down & distance
5. Bears-specific analysis
6. NFC North comparison
7. Top passers by EPA (with minimum dropback filter)
8. Game situation splits (score differential buckets)

---

## Dashboard Features

- **EPA Scatter** — Pass EPA vs. Run EPA for every team, highlighted team in orange
- **3rd-Down Bar** — Horizontal ranked bar by conversion rate
- **Red Zone Bar** — TD rate per team
- **Game Situation Heatmap** — Pass rate % by down × distance
- **Bears Weekly Trend** — EPA/play by week across all 3 seasons
- **KPI Cards** — Selected team's EPA, pass rate, 3rd down %, red zone TD rate

---

## Tools & Libraries

- **Python 3.11+**
- pandas, numpy — data cleaning & manipulation
- SQLAlchemy + PyMySQL — database ORM
- scikit-learn — logistic regression, cross-validation, evaluation
- matplotlib, seaborn — static visualizations
- Plotly, Dash — interactive dashboard
- nfl_data_py — NFL data ingestion
- jupytext — notebook-as-Python-script workflow

---

## Methodology Notes

- Filtered to **regular season** skill plays only (run/pass, no kneel/spike)
- EPA sourced directly from nflfastR — not recalculated
- Model trained on 80% of plays (random split, stratified by target), tested on 20%
- Logistic regression chosen for interpretability; coefficients map directly to feature importance
- The ~68% accuracy ceiling is expected — NFL play-calling is intentionally noisy
- **`models/cap_efficiency.py`** joins MySQL EPA aggregates to nflverse contracts on **player name** (`passer_player_name` / `rusher_player_name` / `receiver_player_name` ↔ contract `player`). That only matches when nflverse string formats align across sources (e.g. `"C.Williams"` in play-by-play vs `"Caleb Williams"` in contracts will not match). The charts remain meaningful for matched players; a production system would **join on `gsis_id`** (or map through **`nfl.import_ids()`** / **Sleeper** ids) so cap and on-field data share a stable key—worth stating explicitly in a README or interview as standard data-engineering awareness.

---

*Built independently as a personal football analytics project. Data: nflverse / nflfastR.*

## Actionable Outputs

### Fourth-Down Recommender
Given any 4th down game situation, outputs Go/Punt/Field Goal
recommendation with expected EPA for each option, calibrated
to historical NFL conversion rates.

### Opponent Tendency Report
Generates a data-driven scouting report for any team — pass rate
by down, formation tendencies, red zone efficiency, and situational
splits — in the same format used by real NFL analytics departments.

### Caleb Williams Rookie Analysis
Benchmarks Caleb Williams' 2024 EPA/dropback, air yards, and
weekly trend against all 2024 rookie QBs and the league median,
providing a data-driven evaluation of the Bears' franchise QB investment.

## Football Operations Department Coverage

This project was built to mirror the analytical work done across
all five Football Operations departments listed in NFL analytics roles:

| Department | Analysis Built | Key Output |
|---|---|---|
| **Coaching** | Run/pass prediction model, 4th down recommender, game situation heatmap | Play-call tendency report |
| **Player Personnel** | Caleb Williams rookie analysis, draft pick value model, trade evaluator | EPA-based player rankings |
| **Salary Cap** | Cap efficiency analyzer (EPA per $1M APY), Bears cap breakdown | Best/worst value contracts |
| **Sports Science** | Player availability tracker, injury burden correlation | Availability rate by team |
| **Strength & Conditioning** | Injury frequency by player, weeks missed vs EPA impact | Bears injury report |
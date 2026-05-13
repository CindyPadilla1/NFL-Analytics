"""
Caleb Williams 2024 Rookie Season Analysis
Comparing EPA/dropback, CPOE, and air yards vs other 2024 rookie QBs
"""
import matplotlib.pyplot as plt
import pandas as pd
from sqlalchemy import create_engine, inspect
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
from db_connection import get_database_url

engine = create_engine(get_database_url())

_play_cols = {c["name"] for c in inspect(engine).get_columns("plays")}
_has_complete = "complete_pass" in _play_cols

# 2024 rookie QBs to compare
ROOKIE_QBS = [
    "C.Williams",   # Caleb Williams - Bears #1 pick
    "J.Daniels",    # Jayden Daniels - Commanders
    "D.Maye",       # Drake Maye - Patriots
    "M.Penix",      # Michael Penix - Falcons
    "B.Nix",        # Bo Nix - Broncos
    "J.McCarthy",   # J.J. McCarthy - Vikings
]

_select_cols = """
    passer_player_name, season, week,
    epa, air_yards, yards_after_catch,
    interception,
    qb_scramble, shotgun, no_huddle,
    score_differential, down
"""
if _has_complete:
    _select_cols += ",\n    complete_pass"

df = pd.read_sql(
    f"""
    SELECT {_select_cols}
    FROM plays
    WHERE play_type = 'pass'
      AND season = 2024
      AND qb_scramble = 0
      AND passer_player_name IS NOT NULL
""",
    engine,
)

_agg = {
    "dropbacks": ("epa", "count"),
    "epa_per_drop": ("epa", "mean"),
    "avg_air_yds": ("air_yards", "mean"),
}
if _has_complete:
    _agg["comp_pct"] = ("complete_pass", "mean")

# Filter to rookie QBs with enough dropbacks
qb_stats = df.groupby("passer_player_name").agg(**_agg).reset_index()

# Only keep guys with 100+ dropbacks (filters out backups/one game wonders)
qb_stats = qb_stats[qb_stats["dropbacks"] >= 100].copy()
qb_stats["is_rookie"] = qb_stats["passer_player_name"].isin(ROOKIE_QBS)
qb_stats["is_caleb"]  = qb_stats["passer_player_name"] == "C.Williams"

# Plot: all QBs EPA vs air yards, rookies highlighted
fig, axes = plt.subplots(1, 2, figsize=(15, 6))
fig.patch.set_facecolor("#F5F0E8")
fig.suptitle("Caleb Williams 2024 Rookie Season — NFL QB Comparison",
             fontsize=15, fontweight="bold", color="#0B1F3A")

# Scatter: EPA/dropback vs avg air yards
for _, row in qb_stats.iterrows():
    if row["is_caleb"]:
        color, size, zorder = "#E87722", 120, 5
    elif row["is_rookie"]:
        color, size, zorder = "#C9A96E", 80, 4
    else:
        color, size, zorder = "#CCCCCC", 40, 3
    axes[0].scatter(row["avg_air_yds"], row["epa_per_drop"],
                    c=color, s=size, zorder=zorder, alpha=0.85)
    if row["is_caleb"] or row["is_rookie"]:
        axes[0].annotate(row["passer_player_name"],
                         (row["avg_air_yds"], row["epa_per_drop"]),
                         fontsize=8, color="#0B1F3A",
                         xytext=(4, 4), textcoords="offset points")

axes[0].axhline(0, color="gray", lw=0.8, linestyle="--", alpha=0.5)
axes[0].axvline(qb_stats["avg_air_yds"].median(), color="gray",
                lw=0.8, linestyle="--", alpha=0.5)
axes[0].set_xlabel("Avg Air Yards (Aggressiveness)", color="#0B1F3A")
axes[0].set_ylabel("EPA / Dropback (Efficiency)", color="#0B1F3A")
axes[0].set_title("EPA vs Aggressiveness — 2024 QBs", color="#0B1F3A")
axes[0].set_facecolor("#FAFAFA")

# Weekly EPA trend for Caleb
caleb_weekly = df[df["passer_player_name"] == "C.Williams"].groupby("week")["epa"].mean()
axes[1].plot(caleb_weekly.index, caleb_weekly.values,
             color="#E87722", lw=2.5, marker="o", ms=6, label="Caleb Williams")
axes[1].axhline(0, color="gray", lw=0.8, linestyle="--")
axes[1].axhline(qb_stats[~qb_stats["is_caleb"]]["epa_per_drop"].median(),
                color="#CCCCCC", lw=1.5, linestyle=":", label="League Median QB")
axes[1].set_xlabel("Week", color="#0B1F3A")
axes[1].set_ylabel("EPA / Dropback", color="#0B1F3A")
axes[1].set_title("Caleb Williams — Weekly EPA Trend 2024", color="#0B1F3A")
axes[1].set_facecolor("#FAFAFA")
axes[1].legend(frameon=False)

plt.tight_layout()
_out = Path(__file__).resolve().parent / "caleb_williams_analysis.png"
plt.savefig(_out, dpi=150)
plt.close(fig)

caleb = qb_stats[qb_stats["is_caleb"]].iloc[0]
league_avg = qb_stats["epa_per_drop"].median()
print(f"\nCaleb Williams 2024 Stats:")
print(f"  Dropbacks:       {caleb['dropbacks']:.0f}")
print(f"  EPA/dropback:    {caleb['epa_per_drop']:+.4f}  (league median: {league_avg:+.4f})")
print(f"  Avg air yards:   {caleb['avg_air_yds']:.1f}")
if _has_complete and "comp_pct" in caleb.index:
    print(f"  Completion %:    {caleb['comp_pct']:.1%}")
else:
    print("  Completion %:    (add `complete_pass` via ingest — run: python data/ingest.py)")
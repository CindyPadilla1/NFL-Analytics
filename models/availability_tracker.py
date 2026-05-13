"""
Player Availability & Injury Impact Analyzer
Covers: Sports Science and Strength & Conditioning departments.

Answers:
- Which players missed the most games due to injury?
- What is the EPA impact when a key player is out?
- Which teams were most/least affected by injuries in 2022-2025?
"""

import nfl_data_py as nfl
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from sqlalchemy import create_engine
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
from db_connection import get_database_url

BEARS_NAVY   = "#0B1F3A"
BEARS_ORANGE = "#E87722"
BEARS_CREAM  = "#F5F0E8"

engine  = create_engine(get_database_url())
SEASONS = [2022, 2023, 2024, 2025]

#  1. Load injury report data
print("Loading injury report data...")
injuries = nfl.import_injuries(SEASONS)

# Practice participation statuses
# DNP = Did Not Participate, LP = Limited Participant, FP = Full Participant
# Game statuses: Out, Doubtful, Questionable, Probable

# 2. Availability rate by team
# Players listed as "Out" or "Doubtful" are effectively unavailable
injuries["unavailable"] = injuries["report_status"].isin(
    ["Out", "Doubtful"]
).astype(int)

team_availability = injuries.groupby(["season", "team"]).agg(
    total_player_weeks=("gsis_id", "count"),
    unavailable_weeks=("unavailable", "sum"),
).reset_index()
team_availability["availability_rate"] = (
                                                 1 - team_availability["unavailable_weeks"] /
                                                 team_availability["total_player_weeks"]
                                         ) * 100

#  3. Bears injury breakdown
bears_injuries = injuries[injuries["team"] == "CHI"].copy()

print(f"\n{'='*55}")
print(f"  CHICAGO BEARS AVAILABILITY REPORT (2022-2025)")
print(f"{'='*55}")

for season in [2022, 2023, 2024, 2025]:
    season_data = bears_injuries[bears_injuries["season"] == season]
    out_count   = (season_data["report_status"] == "Out").sum()
    total       = len(season_data)
    avail_rate  = (1 - out_count/total) * 100 if total > 0 else 0

    print(f"\n  {season}:")
    print(f"    Availability rate : {avail_rate:.1f}%")
    print(f"    Times listed Out  : {out_count}")

    # Most frequently injured Bears players
    top_injured = (
        season_data[season_data["report_status"] == "Out"]
        .groupby("full_name")["report_status"]
        .count()
        .sort_values(ascending=False)
        .head(5)
    )
    if len(top_injured):
        print(f"    Most missed time:")
        for player, weeks in top_injured.items():
            print(f"      {player}: {weeks} weeks listed Out")

#4. EPA impact of injuries — with/without key players
# Pull EPA from your play-by-play data
epa_df = pd.read_sql("""
    SELECT season, week, posteam, epa, play_type
    FROM plays WHERE posteam = 'CHI'
""", engine)

weekly_epa = epa_df.groupby(["season","week"])["epa"].mean().reset_index()
weekly_epa.columns = ["season","week","team_epa"]

# Merge with Bears injury report to correlate injuries with performance
bears_out_by_week = (
    bears_injuries[bears_injuries["report_status"] == "Out"]
    .groupby(["season","week"])["full_name"]
    .count()
    .reset_index()
)
bears_out_by_week.columns = ["season","week","players_out"]

merged = weekly_epa.merge(bears_out_by_week, on=["season","week"], how="left")
merged["players_out"] = merged["players_out"].fillna(0)

correlation = merged["team_epa"].corr(merged["players_out"])
if pd.notna(correlation):
    print(f"\n  Correlation (players out → EPA): {correlation:.3f}")
    if abs(correlation) > 0.1:
        if correlation < 0:
            print("  (More players listed Out tends to align with lower weekly EPA.)")
        else:
            print("  (Positive correlation — injury counts are a coarse weekly proxy; interpret cautiously.)")
else:
    print("\n  Correlation (players out → EPA): n/a (constant input)")

#  5. League-wide injury burden by team
fig, axes = plt.subplots(1, 2, figsize=(16, 6))
fig.patch.set_facecolor(BEARS_CREAM)
fig.suptitle("NFL Player Availability & Injury Burden (2022–2025)",
             fontsize=14, fontweight="bold", color=BEARS_NAVY)

# Availability rate by team (2024)
avail_2024 = (team_availability[team_availability["season"] == 2024]
              .sort_values("availability_rate", ascending=True))
colors = [BEARS_ORANGE if t == "CHI" else BEARS_NAVY
          for t in avail_2024["team"]]
axes[0].barh(avail_2024["team"], avail_2024["availability_rate"],
             color=colors, edgecolor="white", linewidth=0.4)
axes[0].set_title("Team Availability Rate — 2024", color=BEARS_NAVY,
                  fontweight="bold")
axes[0].set_xlabel("% Weeks Available (not Out/Doubtful)", color=BEARS_NAVY)
axes[0].set_facecolor("#FAFAFA")
axes[0].xaxis.set_major_formatter(mtick.PercentFormatter(xmax=100))

# Bears: weekly EPA vs players out
ax2 = axes[1]
ax2.set_facecolor("#FAFAFA")
for season, color in [
        (2022, "#C9A96E"),
        (2023, BEARS_NAVY),
        (2024, BEARS_ORANGE),
        (2025, "#888888"),
    ]:
    s = merged[merged["season"]==season]
    ax2.scatter(s["players_out"], s["team_epa"],
                color=color, label=str(season), alpha=0.7, s=50)
ax2.axhline(0, color="gray", lw=0.8, linestyle="--")
ax2.set_xlabel("Bears Players Listed Out That Week", color=BEARS_NAVY)
ax2.set_ylabel("Bears EPA / play", color=BEARS_NAVY)
ax2.set_title("Injury Burden vs Offensive Performance — CHI",
              color=BEARS_NAVY, fontweight="bold")
ax2.legend(frameon=False)

plt.tight_layout()
_out = Path(__file__).resolve().parent / "availability_tracker.png"
plt.savefig(_out, dpi=150)
plt.close(fig)
print(f"Saved {_out}")
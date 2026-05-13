"""
Salary Cap Efficiency Analyzer
Combines contract data (OverTheCap via nflverse) with on-field EPA
to answer: which players give the most production per cap dollar?

Covers the Salary Cap and Player Personnel departments.

Limitation: play-by-play uses abbreviated names (e.g. "C.Williams") while
contracts use full names ("Caleb Williams"). merge_cap_epa uses an inner
join on exact string match, so only rows where formats align are kept—the
output is still useful for many players, but coverage is incomplete. A
production pipeline would join on a shared player id (e.g. gsis_id from
pbp / rosters mapped to contracts, or sleeper_id via nfl.import_ids()).
"""

import nfl_data_py as nfl
import pandas as pd
import matplotlib.pyplot as plt
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

engine = create_engine(get_database_url())

#  1. Load contract data from nflverse (OverTheCap source)
print("Loading contract data from nflverse...")
contracts = nfl.import_contracts()   # pulls directly from nflverse/rotc

# Keep active contracts, skill positions only
skill_positions = ["QB","WR","RB","TE","OT","IOL","EDGE","IDL","CB","S","LB"]
contracts = contracts[
    (contracts["is_active"] == True) &
    (contracts["position"].isin(skill_positions))
    ].copy()

# nflverse OTC fields `apy` and `guaranteed` are already in millions (USD).
contracts["apy_millions"] = contracts["apy"]
contracts["guaranteed_millions"] = contracts["guaranteed"]

#  2. Load on-field production (EPA) from your MySQL database
print("Loading EPA production data...")
epa_passers = pd.read_sql("""
    SELECT passer_player_name AS player_name, season,
           COUNT(*) AS dropbacks,
           ROUND(AVG(epa), 4) AS epa_per_play,
           SUM(touchdown) AS touchdowns,
           SUM(interception) AS interceptions
    FROM plays
    WHERE play_type = 'pass' AND qb_scramble = 0
      AND passer_player_name IS NOT NULL
      AND season = 2024
    GROUP BY passer_player_name, season
    HAVING dropbacks >= 50
""", engine)

epa_rushers = pd.read_sql("""
    SELECT rusher_player_name AS player_name, season,
           COUNT(*) AS carries,
           ROUND(AVG(epa), 4) AS epa_per_play,
           ROUND(AVG(yards_gained), 2) AS yards_per_carry
    FROM plays
    WHERE play_type = 'run'
      AND rusher_player_name IS NOT NULL
      AND season = 2024
    GROUP BY rusher_player_name, season
    HAVING carries >= 50
""", engine)

epa_receivers = pd.read_sql("""
    SELECT receiver_player_name AS player_name, season,
           COUNT(*) AS targets,
           ROUND(AVG(epa), 4) AS epa_per_play,
           ROUND(SUM(yards_gained), 0) AS total_yards
    FROM plays
    WHERE play_type = 'pass'
      AND receiver_player_name IS NOT NULL
      AND season = 2024
    GROUP BY receiver_player_name, season
    HAVING targets >= 30
""", engine)

#  3. Cap Efficiency = EPA per million dollars of APY
def merge_cap_epa(epa_df, position_filter, min_salary_m=1.0):
    """Join EPA rows to contracts on player *name* (exact match).

    Known limitation: nflverse PBP names often differ from contract display
    names; inner join drops non-matching rows. Production systems resolve
    players via gsis_id (or similar) before joining cap to production.
    """
    merged = epa_df.merge(
        contracts[contracts["position"].isin(position_filter)]
        [["player","apy_millions","guaranteed_millions","position","team"]],
        left_on="player_name", right_on="player",
        how="inner"
    )
    merged = merged[merged["apy_millions"] >= min_salary_m].copy()
    # EPA per $1M APY — the core efficiency metric
    merged["epa_per_million"] = merged["epa_per_play"] / merged["apy_millions"] * 100
    return merged.sort_values("epa_per_million", ascending=False)

qb_eff  = merge_cap_epa(epa_passers,  ["QB"],       min_salary_m=2.0)
rb_eff  = merge_cap_epa(epa_rushers,  ["RB"],       min_salary_m=1.0)
wr_eff  = merge_cap_epa(epa_receivers,["WR","TE"],  min_salary_m=1.0)

#  4. Bears-specific cap analysis
# nflverse contracts use franchise names (e.g. "Bears"), not abbreviations.
bears_contracts = contracts[contracts["team"] == "Bears"].copy()
total_cap_millions = 279.0  # approximate 2025 NFL salary cap ($279M)
bears_spend = bears_contracts["apy_millions"].sum()
bears_cap_pct = bears_spend / total_cap_millions * 100

print(f"\n{'='*55}")
print(f"  CHICAGO BEARS CAP ANALYSIS")
print(f"{'='*55}")
print(f"  Active contracts : {len(bears_contracts)}")
print(f"  Total APY spend  : ${bears_spend:.1f}M")
print(f"  Cap utilization : {bears_cap_pct:.1f}%")
print(f"\n  Top 5 contracts by APY:")
top5 = bears_contracts.nlargest(5, "apy_millions")[
    ["player","position","apy_millions","guaranteed_millions"]
]
for _, r in top5.iterrows():
    print(f"    {r['player']:22s} {r['position']:5s} "
          f"${r['apy_millions']:.1f}M APY  "
          f"(${r['guaranteed_millions']:.0f}M guaranteed)")

# 5. Visualization
fig, axes = plt.subplots(1, 3, figsize=(18, 7))
fig.patch.set_facecolor(BEARS_CREAM)
fig.suptitle("NFL Cap Efficiency — EPA Production per $1M APY (2024)",
             fontsize=15, fontweight="bold", color=BEARS_NAVY)

def plot_efficiency(ax, df, title, name_col="player_name", top_n=15):
    df_plot = df.head(top_n).copy()
    colors = [BEARS_ORANGE if t == "Bears" else BEARS_NAVY
              for t in df_plot["team"]]
    ax.barh(df_plot[name_col], df_plot["epa_per_million"],
            color=colors, edgecolor="white", linewidth=0.5)
    ax.axvline(0, color="gray", lw=0.8, linestyle="--")
    ax.set_title(title, color=BEARS_NAVY, fontweight="bold")
    ax.set_xlabel("EPA per $1M APY", color=BEARS_NAVY)
    ax.set_facecolor("#FAFAFA")
    ax.invert_yaxis()

plot_efficiency(axes[0], qb_eff,  "QB Cap Efficiency")
plot_efficiency(axes[1], rb_eff,  "RB Cap Efficiency")
plot_efficiency(axes[2], wr_eff,  "WR/TE Cap Efficiency")

plt.tight_layout()
_out = Path(__file__).resolve().parent / "cap_efficiency.png"
plt.savefig(_out, dpi=150)
plt.close(fig)
print(f"\nSaved {_out}")
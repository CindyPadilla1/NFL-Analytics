"""
Fourth-Down Decision Model
For any 4th down situation, recommends: Go / Punt / Field Goal
based on win probability impact.
"""
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
from db_connection import get_database_url

engine = create_engine(get_database_url())

# Pull all 4th down plays (columns must match data/ingest.py KEEP_COLS)
df = pd.read_sql("""
    SELECT down, ydstogo, yardline_100, score_differential,
           game_seconds_remaining, play_type,
           first_down, touchdown, wpa, epa, season, posteam
    FROM plays
    WHERE down = 4
""", engine)

# Historical conversion rate by distance bucket
def conversion_rate(ydstogo):
    """What % of 4th down go-for-its convert, by distance."""
    bucket = df[
        (df["ydstogo"].between(max(1, ydstogo-1), ydstogo+1)) &
        (df["play_type"].isin(["run","pass"]))
        ]
    if len(bucket) < 10:
        return 0.45  # league average fallback
    return bucket["first_down"].mean()

def field_goal_probability(yardline_100):
    """Historical FG% by distance (yardline_100 = yards from end zone)."""
    # FG attempt distance = yardline + 17 (snap + end zone)
    fg_distance = yardline_100 + 17
    if fg_distance <= 30: return 0.96
    elif fg_distance <= 35: return 0.91
    elif fg_distance <= 40: return 0.84
    elif fg_distance <= 45: return 0.74
    elif fg_distance <= 50: return 0.61
    elif fg_distance <= 55: return 0.44
    else: return 0.20

def recommend(down, ydstogo, yardline_100, score_diff, seconds_remaining):
    """
    Returns recommendation dict with win probability estimates for each option.
    Simplified model using historical conversion rates + field position logic.
    """
    conv_rate   = conversion_rate(ydstogo)
    fg_prob     = field_goal_probability(yardline_100)
    in_fg_range = yardline_100 <= 52  # ~69-yard FG max

    # Expected EPA for each option
    epa_go    = conv_rate * 4.0 + (1 - conv_rate) * -2.0   # convert = ~4pts, fail = -2
    epa_fg    = fg_prob * 3.0 + (1 - fg_prob) * -0.5        # made FG = 3pts
    epa_punt  = -1.2                                          # avg punt flips field ~40yds

    # Late game override: down big = always go
    if score_diff < -8 and seconds_remaining < 300:
        epa_fg = epa_fg - 5   # FG doesn't help enough
        epa_punt = epa_punt - 10

    options = {"Go for it": epa_go, "Punt": epa_punt}
    if in_fg_range:
        options["Field Goal"] = epa_fg

    recommendation = max(options, key=options.get)
    return {
        "recommendation": recommendation,
        "expected_epa": {k: round(v, 3) for k, v in options.items()},
        "conversion_probability": round(conv_rate, 3),
        "fg_probability": round(fg_prob, 3) if in_fg_range else None,
    }

# Example: Bears-specific 4th down decisions in 2024
print("=== Bears 4th Down Decision Analysis 2024 ===\n")
bears_4th = df[(df["posteam"] == "CHI") & (df["season"] == 2024)]
print(f"Total 4th downs: {len(bears_4th)}")
print(f"Went for it:     {(bears_4th['play_type'].isin(['run','pass'])).sum()}")
print(f"Avg WPA on 4th:  {bears_4th['wpa'].mean():.4f}")

# Test the recommender
scenarios = [
    (4, 1, 35, -3, 1800),   # 4th & 1, FG range, tied-ish
    (4, 7, 45, -10, 600),   # 4th & 7, losing late
    (4, 2, 68, 0, 2400),    # 4th & 2, own territory
    (4, 1, 1,  3,  120),    # 4th & goal from 1, up 3, 2 min
]
print("\n=== Scenario Recommendations ===")
for ydstogo, yardline, score_diff, seconds in [(s[1],s[2],s[3],s[4]) for s in scenarios]:
    r = recommend(4, ydstogo, yardline, score_diff, seconds)
    print(f"4th & {ydstogo} from {yardline} yds, score diff {score_diff:+d}, "
          f"{seconds}s left → {r['recommendation']} "
          f"(conv: {r['conversion_probability']:.0%})")
"""
Opponent Tendency Report Generator
Produces a data-driven scouting report for any upcoming opponent.
Usage: python models/opponent_report.py --team GB --season 2024
"""
import argparse
import re
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
from db_connection import get_database_url


def _normalize_team(team: str) -> str:
    t = team.strip().upper()
    if not re.fullmatch(r"[A-Z]{2,3}", t):
        raise ValueError(f"Invalid team abbreviation: {team!r} (use 2–3 letters, e.g. GB)")
    return t


def generate_report(opponent: str, season: int) -> None:
    opponent = _normalize_team(opponent)
    engine = create_engine(get_database_url())
    df = pd.read_sql(
        text("""
            SELECT * FROM plays
            WHERE posteam = :team AND season = :season
        """),
        engine,
        params={"team": opponent, "season": season},
    )

    print(f"\n{'='*55}")
    print(f"  OPPONENT TENDENCY REPORT: {opponent} | {season}")
    print(f"{'='*55}")

    # Overall
    print(f"\n📊 OVERALL OFFENSE")
    print(f"  Plays analyzed : {len(df):,}")
    print(f"  EPA/play       : {df['epa'].mean():+.4f}")
    print(f"  Pass rate      : {(df['play_type']=='pass').mean():.1%}")

    # By down
    print(f"\n🏈 PASS RATE BY DOWN")
    for down in [1, 2, 3, 4]:
        d = df[df["down"] == down]
        if len(d) > 0:
            pr = (d["play_type"] == "pass").mean()
            epa = d["epa"].mean()
            print(f"  {down}{'st' if down==1 else 'nd' if down==2 else 'rd' if down==3 else 'th'} down: "
                  f"{pr:.0%} pass  |  EPA {epa:+.3f}  ({len(d)} plays)")

    # Formation tendency
    print(f"\n🎯 FORMATION TENDENCIES")
    shotgun_rate = df["shotgun"].mean()
    no_huddle    = df["no_huddle"].mean()
    print(f"  Shotgun rate   : {shotgun_rate:.1%}")
    print(f"  No-huddle rate : {no_huddle:.1%}")

    # Red zone
    print(f"\n🔴 RED ZONE (inside 20)")
    rz = df[df["red_zone"] == 1]
    if len(rz):
        print(f"  TD rate        : {rz['touchdown'].mean():.1%}")
        print(f"  Pass rate      : {(rz['play_type']=='pass').mean():.1%}")
        print(f"  EPA/play       : {rz['epa'].mean():+.4f}")

    # 3rd down
    print(f"\n📐 3RD DOWN")
    td3 = df[df["down"] == 3]
    if len(td3):
        print(f"  Conversion %   : {td3['third_down_converted'].mean():.1%}")
        print(f"  Avg distance   : {td3['ydstogo'].mean():.1f} yards")
        print(f"  Pass rate      : {(td3['play_type']=='pass').mean():.1%}")

    # Score situation splits
    print(f"\n📈 PASS RATE BY GAME SITUATION")
    for label, mask in [
        ("Leading 8+",   df["score_differential"] >= 8),
        ("Close (-7/+7)", df["score_differential"].between(-7, 7)),
        ("Trailing 8+",  df["score_differential"] <= -8),
    ]:
        sub = df[mask]
        if len(sub) > 20:
            print(f"  {label:15s}: {(sub['play_type']=='pass').mean():.0%} pass  "
                  f"|  EPA {sub['epa'].mean():+.3f}")

    print(f"\n{'='*55}\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--team",   default="GB",   help="Team abbreviation")
    parser.add_argument("--season", default=2024, type=int)
    args = parser.parse_args()
    generate_report(args.team, args.season)
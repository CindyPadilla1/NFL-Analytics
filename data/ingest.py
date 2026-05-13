"""
NFL Play-by-Play Data Ingestion Pipeline
Pulls 4 seasons of data from nfl_data_py (nflfastR source)
and loads into MySQL via SQLAlchemy.
"""

import sys
from pathlib import Path

import nfl_data_py as nfl
import pandas as pd
from sqlalchemy import create_engine, text
import logging

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
from db_connection import get_database_url

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# Config
SEASONS      = [2022, 2023, 2024, 2025]
PLAY_TYPES   = ["run", "pass"]   # filter to skill plays only

# Columns we actually need (keeps memory lean)
KEEP_COLS = [
    "play_id", "game_id", "season", "week", "game_date",
    "home_team", "away_team", "posteam", "defteam",
    "play_type", "down", "ydstogo", "yardline_100", "yards_gained",
    "score_differential", "half_seconds_remaining", "game_seconds_remaining",
    "epa", "wpa", "air_yards", "yards_after_catch",
    "complete_pass",  # pass plays: 1 = completion (rookie QB analysis)
    "first_down", "touchdown", "interception", "fumble",
    "formation", "pass_location", "run_location", "run_gap",
    "passer_player_name", "rusher_player_name", "receiver_player_name",
    "receiver_player_id", "passer_player_id", "rusher_player_id",
    "qb_scramble", "qb_kneel", "qb_spike",
    "red_zone",       # derived below
    "third_down_converted", "third_down_failed",
    "goal_to_go", "no_huddle", "shotgun",
    "season_type",    # REG / POST
]


def load_pbp(seasons: list[int]) -> pd.DataFrame:
    log.info(f"Pulling play-by-play for seasons: {seasons}")
    pbp = nfl.import_pbp_data(seasons)
    log.info(f"Raw rows: {len(pbp):,}   columns: {len(pbp.columns)}")
    return pbp


def clean(pbp: pd.DataFrame) -> pd.DataFrame:
    # Filter to run/pass plays only, regular season
    df = pbp[
        (pbp["play_type"].isin(PLAY_TYPES)) &
        (pbp["season_type"] == "REG") &
        (pbp["qb_kneel"] == 0) &
        (pbp["qb_spike"] == 0)
        ].copy()

    # Derive red zone flag
    df["red_zone"] = (df["yardline_100"] <= 20).astype(int)

    # Keep only columns that exist in the dataframe
    cols = [c for c in KEEP_COLS if c in df.columns]
    df = df[cols]

    # Fix types
    df["down"]       = df["down"].astype("Int64")
    df["first_down"] = df["first_down"].fillna(0).astype(int)
    df["touchdown"]  = df["touchdown"].fillna(0).astype(int)

    df = df.dropna(subset=["epa", "down", "ydstogo"])
    log.info(f"Clean rows after filtering: {len(df):,}")
    return df.reset_index(drop=True)


def load_to_db(df: pd.DataFrame, engine) -> None:
    log.info("Writing plays table to MySQL...")
    df.to_sql("plays", con=engine, if_exists="replace", index=False,
              chunksize=5000, method="multi")
    with engine.connect() as conn:
        conn.execute(text("CREATE INDEX idx_season  ON plays (season)"))
        # posteam is TEXT from pandas to_sql; MySQL needs a prefix length on TEXT indexes.
        conn.execute(text("CREATE INDEX idx_posteam ON plays (posteam(32))"))
        conn.execute(text("CREATE INDEX idx_down    ON plays (down)"))
        conn.commit()
    log.info("Done. Indexes created.")


def load_rosters(seasons: list[int], engine) -> None:
    log.info("Pulling seasonal rosters...")
    rosters = nfl.import_seasonal_rosters(seasons)
    keep = ["season","player_id","player_name","position","team","age",
            "years_of_experience","height","weight","college"]
    keep = [c for c in keep if c in rosters.columns]
    rosters[keep].to_sql("rosters", con=engine, if_exists="replace",
                         index=False, chunksize=2000, method="multi")
    log.info(f"Rosters loaded: {len(rosters):,} rows")


def load_schedules(seasons: list[int], engine) -> None:
    log.info("Pulling schedules...")
    sched = nfl.import_schedules(seasons)
    sched.to_sql("schedules", con=engine, if_exists="replace",
                 index=False, chunksize=1000, method="multi")
    log.info(f"Schedules loaded: {len(sched):,} rows")


if __name__ == "__main__":
    engine = create_engine(get_database_url(), echo=False)

    pbp     = load_pbp(SEASONS)
    df      = clean(pbp)
    load_to_db(df, engine)
    load_rosters(SEASONS, engine)
    load_schedules(SEASONS, engine)

    log.info("✅  Ingestion complete.")
    log.info(f"   Total skill plays loaded: {len(df):,}")
    log.info(f"   Seasons covered: {df['season'].unique().tolist()}")
    log.info(f"   Teams: {df['posteam'].nunique()}")
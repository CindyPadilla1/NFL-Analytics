"""
Draft capital vs realized value (nflverse)
Joins historical draft picks with the Hill trade-value chart and career AV (w_av).
Run: python models/draft_value.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import nfl_data_py as nfl
import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Recent drafts where outcomes are still forming (exclude current year if sparse)
DRAFT_SEASONS = list(range(2019, 2025))


def main() -> None:
    print("Loading draft picks and value chart...")
    picks = nfl.import_draft_picks(DRAFT_SEASONS)
    chart = nfl.import_draft_values()

    merged = picks.merge(chart, on="pick", how="left")
    merged["hill"] = merged["hill"].fillna(0)

    by_team = (
        merged.groupby("team", as_index=False)
        .agg(
            chart_capital=("hill", "sum"),
            career_av=("w_av", "sum"),
            picks=("pick", "count"),
        )
        .query("chart_capital > 0")
        .assign(
            av_per_100_chart=lambda d: (d["career_av"] / d["chart_capital"]) * 100
        )
        .sort_values("av_per_100_chart", ascending=False)
    )

    print(f"\nTeams ranked by career AV per 100 points of Hill chart capital ({DRAFT_SEASONS[0]}–{DRAFT_SEASONS[-1]}):")
    print(by_team.head(10).to_string(index=False))

    navy, orange, cream = "#0B1F3A", "#E87722", "#F5F0E8"
    fig, ax = plt.subplots(figsize=(12, 7))
    fig.patch.set_facecolor(cream)
    plot_df = by_team.head(20).sort_values("av_per_100_chart", ascending=True)
    colors = [orange if t == "CHI" else navy for t in plot_df["team"]]
    ax.barh(plot_df["team"], plot_df["av_per_100_chart"], color=colors, edgecolor="white", linewidth=0.5)
    ax.set_facecolor("#FAFAFA")
    ax.axvline(0, color="gray", lw=0.8, linestyle="--", alpha=0.6)
    ax.set_xlabel("Career AV per 100 pts Hill chart value (higher = better draft ROI)")
    ax.set_title(
        f"Draft efficiency snapshot — seasons {DRAFT_SEASONS[0]}–{DRAFT_SEASONS[-1]}",
        color=navy,
        fontweight="bold",
    )
    ax.tick_params(colors=navy)
    plt.tight_layout()
    out = Path(__file__).resolve().parent / "draft_value.png"
    plt.savefig(out, dpi=150)
    plt.close(fig)
    print(f"\nSaved {out}")


if __name__ == "__main__":
    main()

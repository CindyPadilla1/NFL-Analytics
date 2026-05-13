# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
# ---

# %% [markdown]
# # NFL Play-by-Play: Exploratory Data Analysis
# **Seasons:** 2022, 2023, 2024  |  **Source:** nfl_data_py (nflfastR)
#
# This notebook covers:
# 1. Data overview & quality checks
# 2. League-wide offensive efficiency trends
# 3. Chicago Bears deep-dive
# 4. NFC North comparison
# 5. Run/Pass tendency analysis
# 6. Red zone & third-down efficiency

# %%
import sys
from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import seaborn as sns
from sqlalchemy import create_engine

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
from db_connection import get_database_url

engine = create_engine(get_database_url())

# Bears color palette
NAVY   = "#0B1F3A"
ORANGE = "#E87722"
CREAM  = "#F5F0E8"
TAN    = "#C9A96E"

plt.rcParams.update({
    "figure.facecolor": CREAM,
    "axes.facecolor":   "#FAFAFA",
    "axes.edgecolor":   NAVY,
    "axes.labelcolor":  NAVY,
    "xtick.color":      NAVY,
    "ytick.color":      NAVY,
    "text.color":       NAVY,
    "font.family":      "serif",
})

# %% [markdown]
# ## 1. Data Overview

# %%
df = pd.read_sql("SELECT * FROM plays", engine)
print(f"Shape          : {df.shape}")
print(f"Seasons        : {sorted(df['season'].unique())}")
print(f"Teams          : {df['posteam'].nunique()}")
print(f"Play types     : {df['play_type'].value_counts().to_dict()}")
print(f"Missing EPA    : {df['epa'].isna().sum():,}")
print()
print(df.describe()[["epa","yards_gained","ydstogo","yardline_100"]].round(3))

# %%
# Null check on key cols
key_cols = ["epa","down","ydstogo","yardline_100","score_differential","play_type"]
print(df[key_cols].isna().sum())

# %% [markdown]
# ## 2. League-Wide Efficiency Trends

# %%
eff = df.groupby(["season","posteam"]).agg(
    plays        = ("play_id","count"),
    epa_per_play = ("epa","mean"),
    pass_epa     = ("epa", lambda x: x[df.loc[x.index,"play_type"]=="pass"].mean()),
    run_epa      = ("epa", lambda x: x[df.loc[x.index,"play_type"]=="run"].mean()),
    pass_rate    = ("play_type", lambda x: (x=="pass").mean()),
).reset_index()

fig, axes = plt.subplots(1, 3, figsize=(16, 5))
fig.suptitle("NFL Offensive Efficiency — 2022–2024", fontsize=16, fontweight="bold")

for ax, season in zip(axes, [2022, 2023, 2024]):
    s = eff[eff["season"] == season].sort_values("epa_per_play", ascending=True).tail(16)
    colors = [ORANGE if t == "CHI" else NAVY for t in s["posteam"]]
    ax.barh(s["posteam"], s["epa_per_play"], color=colors, edgecolor="white", linewidth=0.5)
    ax.axvline(0, color="gray", lw=0.8, linestyle="--")
    ax.set_title(str(season), fontsize=13)
    ax.set_xlabel("EPA / play")

plt.tight_layout()
plt.savefig("eda_league_efficiency.png", dpi=150)
plt.show()

# %% [markdown]
# ## 3. Chicago Bears Deep-Dive

# %%
chi = df[df["posteam"] == "CHI"].copy()

fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle("Chicago Bears — Offensive Analysis 2022–2024",
             fontsize=15, fontweight="bold")

# (a) EPA by play type per season
chi_epa = chi.groupby(["season","play_type"])["epa"].mean().unstack()
chi_epa.plot(kind="bar", ax=axes[0,0], color=[NAVY, ORANGE], edgecolor="white")
axes[0,0].set_title("EPA/play by Play Type")
axes[0,0].set_xlabel("")
axes[0,0].axhline(0, color="gray", lw=0.7, linestyle="--")
axes[0,0].legend(["Pass","Run"], frameon=False)

# (b) Weekly EPA trend
chi_wk = chi.groupby(["season","week"])["epa"].mean().reset_index()
for s, c in zip([2022, 2023, 2024], [TAN, NAVY, ORANGE]):
    d = chi_wk[chi_wk["season"] == s]
    axes[0,1].plot(d["week"], d["epa"], label=str(s), color=c, lw=2, marker="o", ms=4)
axes[0,1].axhline(0, color="gray", lw=0.7, linestyle="--")
axes[0,1].set_title("Weekly EPA/play")
axes[0,1].set_xlabel("Week")
axes[0,1].legend(frameon=False)

# (c) Pass rate by down
chi_down = chi.groupby("down").apply(
    lambda x: (x["play_type"]=="pass").mean()*100
).reset_index(name="pass_rate")
axes[1,0].bar(chi_down["down"], chi_down["pass_rate"],
              color=[TAN, NAVY, ORANGE, "#888"], edgecolor="white")
axes[1,0].set_title("Pass Rate by Down")
axes[1,0].set_xlabel("Down")
axes[1,0].yaxis.set_major_formatter(mtick.PercentFormatter())

# (d) Score-differential pass rate
bins    = [-30,-14,-7,-1,0,7,14,30]
labels  = ["<-14","-14 to -7","-7 to 0","0","0 to 7","7 to 14",">14"]
chi["sd_bin"] = pd.cut(chi["score_differential"], bins=bins, labels=labels)
sd_pass = chi.groupby("sd_bin", observed=True).apply(
    lambda x: (x["play_type"]=="pass").mean()*100
).reset_index(name="pass_rate")
axes[1,1].bar(range(len(sd_pass)), sd_pass["pass_rate"],
              color=NAVY, edgecolor="white")
axes[1,1].set_xticks(range(len(sd_pass)))
axes[1,1].set_xticklabels(sd_pass["sd_bin"], rotation=30, ha="right", fontsize=9)
axes[1,1].set_title("Pass Rate by Score Differential")
axes[1,1].yaxis.set_major_formatter(mtick.PercentFormatter())

plt.tight_layout()
plt.savefig("eda_bears_analysis.png", dpi=150)
plt.show()

# %% [markdown]
# ## 4. NFC North Comparison

# %%
north = df[df["posteam"].isin(["CHI","GB","MIN","DET"])].copy()
north_eff = north.groupby(["season","posteam"]).agg(
    epa  = ("epa","mean"),
    pass_epa = ("epa", lambda x: x[df.loc[x.index,"play_type"]=="pass"].mean()),
    run_epa  = ("epa", lambda x: x[df.loc[x.index,"play_type"]=="run"].mean()),
).reset_index()

fig, ax = plt.subplots(figsize=(11, 5))
colors_map = {"CHI": ORANGE, "GB": "#203731", "MIN": "#4F2683", "DET": "#0076B6"}
for team, grp in north_eff.groupby("posteam"):
    ax.plot(grp["season"], grp["epa"], label=team,
            color=colors_map[team], lw=2.5, marker="D", ms=7)
ax.axhline(0, color="gray", lw=0.7, linestyle="--")
ax.set_title("NFC North — EPA/play 2022–2024", fontsize=14, fontweight="bold")
ax.set_xlabel("Season")
ax.set_ylabel("EPA / play")
ax.legend(frameon=False)
ax.set_xticks([2022, 2023, 2024])
plt.tight_layout()
plt.savefig("eda_nfc_north.png", dpi=150)
plt.show()

# %% [markdown]
# ## 5. Run/Pass Tendency Heatmap

# %%
sit = df.groupby(["down","ydstogo"]).apply(
    lambda x: (x["play_type"]=="pass").mean()*100
).reset_index(name="pass_rate")
sit = sit[(sit["down"].between(1,4)) & (sit["ydstogo"] <= 15)]
pivot = sit.pivot(index="down", columns="ydstogo", values="pass_rate")

fig, ax = plt.subplots(figsize=(13, 5))
cmap = sns.diverging_palette(220, 30, as_cmap=True)
sns.heatmap(pivot, annot=True, fmt=".0f", cmap=cmap,
            center=60, linewidths=0.4, ax=ax,
            cbar_kws={"label": "Pass rate %"})
ax.set_title("Pass Rate % by Down & Distance to Go", fontsize=14, fontweight="bold")
ax.set_xlabel("Yards to go")
ax.set_ylabel("Down")
plt.tight_layout()
plt.savefig("eda_pass_rate_heatmap.png", dpi=150)
plt.show()

# %% [markdown]
# ## 6. Red Zone & Third Down

# %%
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Red zone TD rate
rz = df[df["red_zone"] == 1].groupby(["season","posteam"]).agg(
    plays = ("play_id","count"),
    td_rate = ("touchdown","mean"),
).reset_index()
rz2024 = rz[rz["season"] == 2024].sort_values("td_rate", ascending=True).tail(15)
colors_rz = [ORANGE if t == "CHI" else NAVY for t in rz2024["posteam"]]
axes[0].barh(rz2024["posteam"], rz2024["td_rate"]*100,
             color=colors_rz, edgecolor="white")
axes[0].set_title("Red Zone TD Rate — 2024")
axes[0].xaxis.set_major_formatter(mtick.PercentFormatter())

# Third-down conversion rate
td = df[df["down"] == 3].groupby(["season","posteam"])["third_down_converted"].mean().reset_index()
td2024 = td[td["season"] == 2024].sort_values("third_down_converted", ascending=True).tail(15)
colors_td = [ORANGE if t == "CHI" else NAVY for t in td2024["posteam"]]
axes[1].barh(td2024["posteam"], td2024["third_down_converted"]*100,
             color=colors_td, edgecolor="white")
axes[1].set_title("3rd-Down Conversion Rate — 2024")
axes[1].xaxis.set_major_formatter(mtick.PercentFormatter())

plt.suptitle("Special Situation Efficiency", fontsize=14, fontweight="bold")
plt.tight_layout()
plt.savefig("eda_special_situations.png", dpi=150)
plt.show()

print("\n✅  EDA complete. All charts saved.")
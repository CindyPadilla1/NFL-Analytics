"""
NFL Analytics Dashboard — Dash + Plotly
Run: python dashboard/app.py
Then open http://localhost:8050
"""

import warnings

# macOS / LibreSSL: urllib3 2.x warns before any SSL use; filter before deps import urllib3.
warnings.filterwarnings(
    "ignore",
    message="urllib3 v2 only supports OpenSSL 1.1.1+",
)

import sys
from pathlib import Path

import pandas as pd
import numpy as np
from sqlalchemy import create_engine
import dash
from dash import dcc, html, Input, Output, dash_table
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
from db_connection import get_database_url

#Config
BEARS_NAVY   = "#0B1F3A"
BEARS_ORANGE = "#E87722"
BEARS_CREAM  = "#F5F0E8"
BEARS_TAN    = "#C9A96E"

NFC_NORTH = ["CHI", "GB", "MIN", "DET"]

PLOT_LAYOUT = dict(
    paper_bgcolor="white",
    plot_bgcolor="#FAFAFA",
    font=dict(family="Georgia, serif", color=BEARS_NAVY),
    title_font=dict(size=16, color=BEARS_NAVY),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0)"),
    margin=dict(l=50, r=30, t=55, b=45),
)


# Data loading helpers
def get_engine():
    return create_engine(get_database_url(), echo=False)


def load_team_efficiency(engine) -> pd.DataFrame:
    return pd.read_sql("""
        SELECT season, posteam AS team,
               COUNT(*) AS plays,
               ROUND(AVG(epa), 4)  AS epa_per_play,
               ROUND(AVG(CASE WHEN play_type='pass' THEN epa END), 4) AS pass_epa,
               ROUND(AVG(CASE WHEN play_type='run'  THEN epa END), 4) AS run_epa,
               ROUND(AVG(CASE WHEN play_type='pass' THEN 1.0 ELSE 0 END)*100, 1) AS pass_rate
        FROM plays GROUP BY season, posteam
    """, engine)


def load_third_down(engine) -> pd.DataFrame:
    return pd.read_sql("""
        SELECT season, posteam AS team,
               COUNT(*) AS attempts,
               ROUND(AVG(third_down_converted)*100, 1) AS conv_pct,
               ROUND(AVG(ydstogo), 1) AS avg_distance
        FROM plays WHERE down = 3
        GROUP BY season, posteam
    """, engine)


def load_red_zone(engine) -> pd.DataFrame:
    return pd.read_sql("""
        SELECT season, posteam AS team,
               COUNT(*) AS rz_plays,
               SUM(touchdown) AS tds,
               ROUND(SUM(touchdown)/COUNT(*)*100, 1) AS td_rate
        FROM plays WHERE red_zone = 1
        GROUP BY season, posteam
    """, engine)


def load_situation_splits(engine) -> pd.DataFrame:
    return pd.read_sql("""
        SELECT
            down, ydstogo,
            ROUND(AVG(CASE WHEN play_type='pass' THEN 1.0 ELSE 0 END)*100, 1) AS pass_rate,
            ROUND(AVG(epa), 4) AS avg_epa,
            COUNT(*) AS plays
        FROM plays
        WHERE down IN (1,2,3,4) AND ydstogo <= 20
        GROUP BY down, ydstogo
        HAVING plays >= 30
    """, engine)


def load_bears_weekly(engine) -> pd.DataFrame:
    return pd.read_sql("""
        SELECT season, week,
               ROUND(AVG(epa), 4)  AS epa_per_play,
               ROUND(AVG(CASE WHEN play_type='pass' THEN epa END), 4) AS pass_epa,
               ROUND(AVG(CASE WHEN play_type='run'  THEN epa END), 4) AS run_epa,
               COUNT(*) AS plays
        FROM plays WHERE posteam = 'CHI'
        GROUP BY season, week ORDER BY season, week
    """, engine)


#Load on startup
engine     = get_engine()
df_eff     = load_team_efficiency(engine)
df_3rd     = load_third_down(engine)
df_rz      = load_red_zone(engine)
df_sit     = load_situation_splits(engine)
df_bears   = load_bears_weekly(engine)

SEASONS    = sorted(df_eff["season"].unique().tolist(), reverse=True)
ALL_TEAMS  = sorted(df_eff["team"].unique().tolist())


#  App
app = dash.Dash(__name__, title="NFL Analytics Dashboard")

#Layout
app.layout = html.Div(style={"fontFamily": "Georgia, serif",
                             "backgroundColor": BEARS_CREAM,
                             "minHeight": "100vh",
                             "padding": "0"}, children=[

    # Header
    html.Div(style={"background": BEARS_NAVY, "padding": "20px 40px",
                    "display": "flex", "alignItems": "center", "gap": "20px"}, children=[
        html.Div("🐻", style={"fontSize": "40px"}),
        html.Div([
            html.H1("NFL Play-by-Play Analytics",
                    style={"color": "white", "margin": 0,
                           "fontSize": "26px", "fontWeight": "normal"}),
            html.P("2022–2024 · nflfastR · MySQL + Python",
                   style={"color": BEARS_TAN, "margin": 0, "fontSize": "13px"}),
        ])
    ]),

    # Controls
    html.Div(style={"background": "white", "padding": "16px 40px",
                    "borderBottom": f"2px solid {BEARS_ORANGE}",
                    "display": "flex", "gap": "30px", "alignItems": "center",
                    "flexWrap": "wrap"}, children=[
        html.Div([
            html.Label("Season", style={"fontSize": "12px",
                                        "color": BEARS_NAVY, "display": "block"}),
            dcc.Dropdown(id="season-dd",
                         options=[{"label": s, "value": s} for s in SEASONS],
                         value=SEASONS[0], clearable=False,
                         style={"width": "120px"}),
        ]),
        html.Div([
            html.Label("Highlight Team", style={"fontSize": "12px",
                                                "color": BEARS_NAVY, "display": "block"}),
            dcc.Dropdown(id="team-dd",
                         options=[{"label": t, "value": t} for t in ALL_TEAMS],
                         value="CHI", clearable=False,
                         style={"width": "120px"}),
        ]),
        html.Div([
            html.Label("View", style={"fontSize": "12px",
                                      "color": BEARS_NAVY, "display": "block"}),
            dcc.RadioItems(id="view-radio",
                           options=[{"label": " League",   "value": "league"},
                                    {"label": " NFC North", "value": "division"},
                                    {"label": " Bears Only","value": "bears"}],
                           value="league",
                           labelStyle={"marginRight": "16px", "fontSize": "14px"},
                           inputStyle={"marginRight": "4px"}),
        ]),
    ]),

    # KPI cards
    html.Div(id="kpi-cards", style={"display": "flex", "gap": "16px",
                                    "padding": "24px 40px 0",
                                    "flexWrap": "wrap"}),

    # Charts row 1
    html.Div(style={"display": "grid",
                    "gridTemplateColumns": "1fr 1fr",
                    "gap": "20px",
                    "padding": "20px 40px"}, children=[
        dcc.Graph(id="epa-scatter", style={"background": "white",
                                           "borderRadius": "8px",
                                           "padding": "8px"}),
        dcc.Graph(id="third-down-bar", style={"background": "white",
                                              "borderRadius": "8px",
                                              "padding": "8px"}),
    ]),

    # Charts row 2
    html.Div(style={"display": "grid",
                    "gridTemplateColumns": "1fr 1fr",
                    "gap": "20px",
                    "padding": "0 40px"}, children=[
        dcc.Graph(id="red-zone-bar", style={"background": "white",
                                            "borderRadius": "8px",
                                            "padding": "8px"}),
        dcc.Graph(id="situation-heat", style={"background": "white",
                                              "borderRadius": "8px",
                                              "padding": "8px"}),
    ]),

    # Bears weekly trend (full width)
    html.Div(style={"padding": "20px 40px"}, children=[
        dcc.Graph(id="bears-trend", style={"background": "white",
                                           "borderRadius": "8px",
                                           "padding": "8px"}),
    ]),

    # Footer
    html.Div(style={"background": BEARS_NAVY, "padding": "16px 40px",
                    "marginTop": "10px"}, children=[
        html.P("Data source: nfl_data_py / nflfastR · Built with Python, Plotly Dash, MySQL",
               style={"color": BEARS_TAN, "margin": 0, "fontSize": "12px"}),
    ]),
])


# Callbacks
@app.callback(
    [Output("kpi-cards",     "children"),
     Output("epa-scatter",   "figure"),
     Output("third-down-bar","figure"),
     Output("red-zone-bar",  "figure"),
     Output("situation-heat","figure"),
     Output("bears-trend",   "figure")],
    [Input("season-dd",  "value"),
     Input("team-dd",    "value"),
     Input("view-radio", "value")],
)
def update(season, team, view):
    # Filter helpers
    def team_filter(df):
        if view == "division":
            return df[df["team"].isin(NFC_NORTH)]
        if view == "bears":
            return df[df["team"] == "CHI"]
        return df  # league

    eff  = df_eff[df_eff["season"] == season]
    td3  = df_3rd[df_3rd["season"] == season]
    rz   = df_rz[df_rz["season"] == season]

    eff_f = team_filter(eff)
    td3_f = team_filter(td3)
    rz_f  = team_filter(rz)

    # KPI cards
    team_row = eff[eff["team"] == team]
    td_row   = td3[td3["team"]  == team]
    rz_row   = rz[rz["team"]   == team]

    def kpi(label, value, suffix=""):
        return html.Div(style={
            "background": "white", "borderRadius": "8px",
            "padding": "16px 24px", "minWidth": "150px",
            "borderTop": f"3px solid {BEARS_ORANGE}",
        }, children=[
            html.P(label, style={"margin": "0 0 4px",
                                 "fontSize": "12px", "color": "#888"}),
            html.P(f"{value}{suffix}", style={"margin": 0,
                                              "fontSize": "24px",
                                              "fontWeight": "bold",
                                              "color": BEARS_NAVY}),
        ])

    epa_val   = f"{team_row['epa_per_play'].values[0]:+.3f}"   if len(team_row) else "—"
    pass_rate = f"{team_row['pass_rate'].values[0]:.1f}"       if len(team_row) else "—"
    conv      = f"{td_row['conv_pct'].values[0]:.1f}"          if len(td_row)  else "—"
    td_rate   = f"{rz_row['td_rate'].values[0]:.1f}"           if len(rz_row)  else "—"

    kpis = [
        kpi(f"{team} · EPA/play",           epa_val),
        kpi(f"{team} · Pass rate",          pass_rate, "%"),
        kpi(f"{team} · 3rd-down conv.",     conv,      "%"),
        kpi(f"{team} · Red-zone TD rate",   td_rate,   "%"),
    ]

    # EPA scatter
    colors_eff = [BEARS_ORANGE if t == team else
                  (BEARS_NAVY if t in NFC_NORTH else "#CCCCCC") for t in eff_f["team"]]
    sizes_eff  = [16 if t == team else (12 if t in NFC_NORTH else 8) for t in eff_f["team"]]
    fig_epa = go.Figure()
    fig_epa.add_trace(go.Scatter(
        x=eff_f["pass_epa"], y=eff_f["run_epa"],
        mode="markers+text",
        text=eff_f["team"],
        textposition="top center",
        marker=dict(color=colors_eff, size=sizes_eff, line=dict(width=1, color="white")),
        hovertemplate="<b>%{text}</b><br>Pass EPA: %{x:.3f}<br>Run EPA: %{y:.3f}<extra></extra>",
    ))
    fig_epa.add_hline(y=0, line_dash="dot", line_color="gray", opacity=0.4)
    fig_epa.add_vline(x=0, line_dash="dot", line_color="gray", opacity=0.4)
    fig_epa.update_layout(**PLOT_LAYOUT,
                          title=f"Pass vs Run EPA — {season}",
                          xaxis_title="Pass EPA/play",
                          yaxis_title="Run EPA/play",
                          )

    # Third-down bar
    td3_s = td3_f.sort_values("conv_pct", ascending=True).tail(20)
    colors_td = [BEARS_ORANGE if t == team else BEARS_NAVY for t in td3_s["team"]]
    fig_td = go.Figure(go.Bar(
        y=td3_s["team"], x=td3_s["conv_pct"],
        orientation="h",
        marker_color=colors_td,
        hovertemplate="<b>%{y}</b>: %{x:.1f}%<extra></extra>",
    ))
    fig_td.update_layout(**PLOT_LAYOUT,
                         title=f"3rd-Down Conversion Rate — {season}",
                         xaxis_title="Conversion %",
                         yaxis_title="",
                         height=450,
                         )

    #  Red zone bar
    rz_s = rz_f.sort_values("td_rate", ascending=True).tail(20)
    colors_rz = [BEARS_ORANGE if t == team else BEARS_NAVY for t in rz_s["team"]]
    fig_rz = go.Figure(go.Bar(
        y=rz_s["team"], x=rz_s["td_rate"],
        orientation="h",
        marker_color=colors_rz,
        hovertemplate="<b>%{y}</b>: %{x:.1f}%<extra></extra>",
    ))
    fig_rz.update_layout(**PLOT_LAYOUT,
                         title=f"Red Zone TD Rate — {season}",
                         xaxis_title="TD %",
                         yaxis_title="",
                         height=450,
                         )

    # Game situation heatmap
    pivot = df_sit.pivot_table(index="down", columns="ydstogo",
                               values="pass_rate", aggfunc="mean")
    fig_sit = go.Figure(go.Heatmap(
        z=pivot.values,
        x=[f"{c} yds" for c in pivot.columns],
        y=[f"Down {r}" for r in pivot.index],
        colorscale=[[0, "#0B1F3A"], [0.5, "#C9A96E"], [1, "#E87722"]],
        hovertemplate="Down %{y}<br>Distance %{x}<br>Pass rate: %{z:.1f}%<extra></extra>",
        colorbar=dict(title="Pass rate %"),
    ))
    fig_sit.update_layout(**PLOT_LAYOUT,
                          title="Pass Rate % by Down & Distance (all seasons)",
                          xaxis_title="Yards to go",
                          yaxis_title="",
                          )

    # Bears weekly EPA
    fig_bears = go.Figure()
    for s, color in zip(SEASONS, [BEARS_ORANGE, BEARS_NAVY, BEARS_TAN]):
        b = df_bears[df_bears["season"] == s]
        if b.empty:
            continue
        fig_bears.add_trace(go.Scatter(
            x=b["week"], y=b["epa_per_play"],
            name=str(s), mode="lines+markers",
            line=dict(color=color, width=2),
            marker=dict(size=6),
            hovertemplate=f"<b>{s}</b> Wk %{{x}}: %{{y:.3f}} EPA<extra></extra>",
        ))
    fig_bears.add_hline(y=0, line_dash="dot", line_color="gray", opacity=0.5)
    fig_bears.update_layout(**PLOT_LAYOUT,
                            title="Chicago Bears — Weekly EPA/play (2022–2024)",
                            xaxis_title="Week",
                            yaxis_title="EPA per play",
                            height=320,
                            )

    return kpis, fig_epa, fig_td, fig_rz, fig_sit, fig_bears


# Main
if __name__ == "__main__":
    app.run(debug=True, port=8050)
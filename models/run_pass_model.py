"""
Run/Pass Play-Call Prediction Model
Logistic Regression using game-situation variables
Target: ~68% accuracy on holdout test set
"""

import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    classification_report, confusion_matrix, roc_auc_score, roc_curve
)
from sklearn.pipeline import Pipeline
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import seaborn as sns
import joblib
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
from db_connection import get_database_url
MODEL_DIR = Path(__file__).parent
SEED      = 42


#  1. Load data
def load_data(engine) -> pd.DataFrame:
    query = """
        SELECT
            play_type,
            down,
            ydstogo,
            yardline_100,
            score_differential,
            half_seconds_remaining,
            game_seconds_remaining,
            shotgun,
            no_huddle,
            goal_to_go,
            red_zone,
            qb_scramble,
            season
        FROM plays
        WHERE play_type IN ('run','pass')
          AND down IS NOT NULL
          AND ydstogo IS NOT NULL
    """
    df = pd.read_sql(query, engine)
    print(f"Loaded {len(df):,} plays")
    return df


# 2. Feature engineering
def build_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    df = df.copy()

    # Binary target: 1 = pass, 0 = run
    y = (df["play_type"] == "pass").astype(int)

    # Interaction & derived features
    df["yardline_x_down"]      = df["yardline_100"] * df["down"]
    df["ydstogo_x_down"]       = df["ydstogo"] * df["down"]
    df["score_diff_abs"]       = df["score_differential"].abs()
    df["losing"]               = (df["score_differential"] < 0).astype(int)
    df["winning"]              = (df["score_differential"] > 0).astype(int)
    df["late_game"]            = (df["game_seconds_remaining"] < 600).astype(int)
    df["two_minute_drill"]     = (df["half_seconds_remaining"]  < 120).astype(int)
    df["3rd_or_4th"]           = (df["down"] >= 3).astype(int)
    df["must_pass"]            = (
            (df["down"] == 3) & (df["ydstogo"] >= 8)
    ).astype(int)
    df["short_yardage"]        = (df["ydstogo"] <= 2).astype(int)

    feature_cols = [
        "down", "ydstogo", "yardline_100", "score_differential",
        "half_seconds_remaining", "game_seconds_remaining",
        "shotgun", "no_huddle", "goal_to_go", "red_zone",
        "yardline_x_down", "ydstogo_x_down", "score_diff_abs",
        "losing", "winning", "late_game", "two_minute_drill",
        "3rd_or_4th", "must_pass", "short_yardage",
    ]

    X = df[feature_cols].fillna(0)
    return X, y


# 3. Train & evaluate
def train(X: pd.DataFrame, y: pd.Series):
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=SEED, stratify=y
    )

    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("clf",    LogisticRegression(max_iter=1000, C=1.0,
                                      class_weight="balanced",
                                      random_state=SEED)),
    ])

    # Cross-validation
    cv     = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    scores = cross_val_score(pipeline, X_train, y_train, cv=cv, scoring="accuracy")
    print(f"\n5-Fold CV Accuracy: {scores.mean():.4f} ± {scores.std():.4f}")

    # Final fit
    pipeline.fit(X_train, y_train)
    y_pred = pipeline.predict(X_test)
    y_prob = pipeline.predict_proba(X_test)[:, 1]

    test_acc = (y_pred == y_test).mean()
    auc      = roc_auc_score(y_test, y_prob)
    print(f"Test Accuracy : {test_acc:.4f}  ({test_acc*100:.1f}%)")
    print(f"ROC-AUC       : {auc:.4f}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=["Run","Pass"]))

    return pipeline, X_train, X_test, y_train, y_test, y_pred, y_prob


#  4. Plots
BEARS_NAVY  = "#0B1F3A"
BEARS_ORANGE = "#E87722"
BEARS_CREAM  = "#F5F0E8"

def plot_confusion(y_test, y_pred):
    cm = confusion_matrix(y_test, y_pred)
    fig, ax = plt.subplots(figsize=(6,5))
    fig.patch.set_facecolor(BEARS_CREAM)
    ax.set_facecolor(BEARS_CREAM)
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                xticklabels=["Run","Pass"], yticklabels=["Run","Pass"],
                ax=ax, linewidths=0.5)
    ax.set_xlabel("Predicted", fontsize=12, color=BEARS_NAVY)
    ax.set_ylabel("Actual",    fontsize=12, color=BEARS_NAVY)
    ax.set_title("Confusion Matrix — Run/Pass Prediction",
                 fontsize=14, fontweight="bold", color=BEARS_NAVY, pad=12)
    plt.tight_layout()
    fig.savefig(MODEL_DIR / "confusion_matrix.png", dpi=150)
    plt.close()
    print("Saved confusion_matrix.png")


def plot_roc(y_test, y_prob):
    fpr, tpr, _ = roc_curve(y_test, y_prob)
    auc          = roc_auc_score(y_test, y_prob)
    fig, ax = plt.subplots(figsize=(6,5))
    fig.patch.set_facecolor(BEARS_CREAM)
    ax.set_facecolor(BEARS_CREAM)
    ax.plot(fpr, tpr, color=BEARS_ORANGE, lw=2, label=f"AUC = {auc:.3f}")
    ax.plot([0,1],[0,1], "k--", alpha=0.4)
    ax.set_xlabel("False Positive Rate", color=BEARS_NAVY)
    ax.set_ylabel("True Positive Rate",  color=BEARS_NAVY)
    ax.set_title("ROC Curve — Run/Pass Model",
                 fontweight="bold", color=BEARS_NAVY)
    ax.legend(frameon=False)
    plt.tight_layout()
    fig.savefig(MODEL_DIR / "roc_curve.png", dpi=150)
    plt.close()
    print("Saved roc_curve.png")


def plot_feature_importance(pipeline, feature_names):
    coefs = pipeline.named_steps["clf"].coef_[0]
    imp   = pd.Series(coefs, index=feature_names).sort_values()
    fig, ax = plt.subplots(figsize=(8, 6))
    fig.patch.set_facecolor(BEARS_CREAM)
    ax.set_facecolor(BEARS_CREAM)
    colors = [BEARS_ORANGE if v > 0 else BEARS_NAVY for v in imp.values]
    imp.plot(kind="barh", ax=ax, color=colors, edgecolor="white", linewidth=0.5)
    ax.set_title("Feature Coefficients (Logistic Regression)\nPositive → predicts PASS",
                 fontweight="bold", color=BEARS_NAVY)
    ax.set_xlabel("Coefficient", color=BEARS_NAVY)
    ax.axvline(0, color="gray", linewidth=0.8, linestyle="--")
    plt.tight_layout()
    fig.savefig(MODEL_DIR / "feature_importance.png", dpi=150)
    plt.close()
    print("Saved feature_importance.png")


#  5. Save model + metadata
def save(pipeline, X, y_test, y_pred, y_prob):
    joblib.dump(pipeline, MODEL_DIR / "run_pass_model.pkl")

    acc = (y_pred == y_test).mean()
    meta = {
        "test_accuracy": round(float(acc), 4),
        "roc_auc":       round(float(roc_auc_score(y_test, y_prob)), 4),
        "n_features":    int(X.shape[1]),
        "features":      list(X.columns),
    }
    (MODEL_DIR / "model_metadata.json").write_text(json.dumps(meta, indent=2))
    print("Model + metadata saved.")


# Main
if __name__ == "__main__":
    engine = create_engine(get_database_url(), echo=False)
    df     = load_data(engine)
    X, y   = build_features(df)

    pipeline, X_train, X_test, y_train, y_test, y_pred, y_prob = train(X, y)

    plot_confusion(y_test, y_pred)
    plot_roc(y_test, y_prob)
    plot_feature_importance(pipeline, X.columns.tolist())
    save(pipeline, X, y_test, y_pred, y_prob)
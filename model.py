"""
Optional churn prediction model (scikit-learn).

Pipeline = preprocessing + classifier, so the exact same cleaning is applied
during training and when scoring new customers:
  numbers      -> fill gaps with the median, then standardise
  categories   -> fill gaps with the most common value, then one-hot encode
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score, precision_score,
                             recall_score, roc_auc_score, roc_curve)
from sklearn.model_selection import StratifiedKFold, cross_val_predict, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from . import config as C

ALGORITHMS = {
    "Logistic Regression": lambda seed: LogisticRegression(max_iter=1000, class_weight="balanced"),
    "Random Forest": lambda seed: RandomForestClassifier(n_estimators=200, max_depth=8, min_samples_leaf=10,
                                                         class_weight="balanced", random_state=seed, n_jobs=1),
    "Gradient Boosting": lambda seed: GradientBoostingClassifier(n_estimators=150, max_depth=3, learning_rate=0.08, random_state=seed),
}


class ModelError(Exception):
    """Raised when the data cannot support a model (friendly message inside)."""


def feature_lists(df: pd.DataFrame) -> tuple[list[str], list[str]]:
    numeric = [c for c in C.MODEL_NUMERIC if c in df.columns]
    categorical = [c for c in C.MODEL_CATEGORICAL if c in df.columns and df[c].nunique() <= 30]
    return numeric, categorical


def build_pipeline(numeric: list[str], categorical: list[str], algorithm: str, seed: int = 42) -> Pipeline:
    pre = ColumnTransformer([
        ("num", Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), numeric),
        ("cat", Pipeline([("impute", SimpleImputer(strategy="most_frequent")),
                          ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False))]), categorical),
    ])
    return Pipeline([("prep", pre), ("clf", ALGORITHMS[algorithm](seed))])


def train_and_evaluate(df: pd.DataFrame, algorithm: str = "Logistic Regression", test_size: float = 0.2, seed: int = 42) -> dict:
    """Train on a stratified split, evaluate on the hold-out set, and compute out-of-fold risk scores."""
    y = df["Churned"].astype(int)
    counts = y.value_counts()
    if len(counts) < 2 or counts.min() < 30:
        raise ModelError("The model needs at least 30 churned AND 30 retained customers. Widen the data or upload a bigger file.")
    numeric, categorical = feature_lists(df)
    if len(numeric) + len(categorical) < 3:
        raise ModelError("Too few usable feature columns to train a model.")
    features = numeric + categorical
    X = df[features]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, stratify=y, random_state=seed)
    pipe = build_pipeline(numeric, categorical, algorithm, seed)
    pipe.fit(X_train, y_train)
    proba_test = pipe.predict_proba(X_test)[:, 1]

    # Which original columns matter? Shuffle one column at a time and see how much AUC drops.
    perm = permutation_importance(pipe, X_test, y_test, scoring="roc_auc", n_repeats=5, random_state=seed, n_jobs=1)
    importance = (pd.DataFrame({"feature": features, "importance": perm.importances_mean, "std": perm.importances_std})
                  .sort_values("importance", ascending=False).reset_index(drop=True))

    # Out-of-fold probabilities: every customer is scored by a model that never saw them.
    folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
    oof = cross_val_predict(clone(pipe), X, y, cv=folds, method="predict_proba")[:, 1]

    fpr, tpr, _ = roc_curve(y_test, proba_test)
    return {
        "pipeline": pipe,
        "algorithm": algorithm,
        "features": features,
        "numeric": numeric,
        "categorical": categorical,
        "y_test": y_test.to_numpy(),
        "proba_test": proba_test,
        "auc": float(roc_auc_score(y_test, proba_test)),
        "cv_auc": float(roc_auc_score(y, oof)),
        "fpr": fpr,
        "tpr": tpr,
        "importance": importance,
        "oof_scores": pd.Series(oof, index=df.index, name="ChurnProbability"),
        "n_train": len(X_train),
        "n_test": len(X_test),
        "base_rate": float(y.mean()),
    }


def metrics_at_threshold(y_true, proba, threshold: float) -> dict:
    pred = (np.asarray(proba) >= threshold).astype(int)
    return {
        "accuracy": accuracy_score(y_true, pred),
        "precision": precision_score(y_true, pred, zero_division=0),
        "recall": recall_score(y_true, pred, zero_division=0),
        "f1": f1_score(y_true, pred, zero_division=0),
        "cm": confusion_matrix(y_true, pred, labels=[0, 1]),
    }


def predict_one(result: dict, values: dict) -> float:
    """Churn probability for one customer described by a {feature: value} dict."""
    row = pd.DataFrame([{f: values.get(f) for f in result["features"]}])
    return float(result["pipeline"].predict_proba(row)[0, 1])

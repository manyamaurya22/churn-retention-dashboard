"""
Central configuration for the dashboard.

Keeping constants in one file means you can change a colour, a threshold or a
column name in a single place instead of hunting through the whole project.
"""
from pathlib import Path

import numpy as np

# ----------------------------------------------------------------------------
# Paths & labels
# ----------------------------------------------------------------------------
APP_TITLE = "Customer Churn & Retention Intelligence"
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
TELCO_PATH = DATA_DIR / "telco_churn.csv"
TEMPLATE_PATH = DATA_DIR / "sample_template.csv"
CURRENCY = "$"

# ----------------------------------------------------------------------------
# Expected CSV schema
# ----------------------------------------------------------------------------
# Columns that MUST exist for the dashboard to work.
REQUIRED_COLUMNS = [
    "customerID",
    "tenure",
    "Contract",
    "PaymentMethod",
    "MonthlyCharges",
    "TotalCharges",
    "Churn",
]

# Columns that are used when present (charts / model features degrade gracefully).
OPTIONAL_COLUMNS = [
    "InternetService", "SignupDate", "gender", "SeniorCitizen", "Partner",
    "Dependents", "PhoneService", "MultipleLines", "OnlineSecurity",
    "OnlineBackup", "DeviceProtection", "TechSupport", "StreamingTV",
    "StreamingMovies", "PaperlessBilling",
]

COLUMN_HELP = {
    "customerID": "Unique ID per customer (text)",
    "tenure": "Months the customer has been with the company (number)",
    "Contract": "Contract type, e.g. Month-to-month / One year / Two year",
    "PaymentMethod": "How the customer pays, e.g. Electronic check",
    "MonthlyCharges": "Current monthly bill (number)",
    "TotalCharges": "Total billed so far (number; blanks are auto-filled)",
    "Churn": "Did the customer leave? Yes/No (also accepts 1/0, True/False)",
    "InternetService": "(optional) DSL / Fiber optic / No",
    "SignupDate": "(optional) Customer start date - enables the date filter",
}

# Model features. "gender" is deliberately NOT used as a predictor (fairness).
MODEL_NUMERIC = ["tenure", "MonthlyCharges", "TotalCharges"]
MODEL_CATEGORICAL = [
    "Contract", "PaymentMethod", "InternetService", "SeniorCitizen",
    "Partner", "Dependents", "PhoneService", "MultipleLines", "OnlineSecurity",
    "OnlineBackup", "DeviceProtection", "TechSupport", "StreamingTV",
    "StreamingMovies", "PaperlessBilling",
]

# ----------------------------------------------------------------------------
# Analysis settings
# ----------------------------------------------------------------------------
TENURE_BINS = [-0.01, 12, 24, 48, np.inf]
TENURE_LABELS = ["0-12 mo", "13-24 mo", "25-48 mo", "49+ mo"]

# Risk score = average (smoothed) historical churn rate of the segments a
# customer belongs to. Tiers compare that score with the overall churn rate.
RISK_DIMENSIONS = ["Contract", "TenureGroup", "PaymentMethod", "InternetService", "ChargeBand"]
RISK_SMOOTHING = 20          # pseudo-count that stops tiny groups looking extreme
RISK_HIGH_RATIO = 1.25       # score >= 1.25 x overall churn  -> High
RISK_MEDIUM_RATIO = 0.85     # score >= 0.85 x overall churn  -> Medium

MIN_ROWS = 50                # minimum rows accepted from an upload

# ----------------------------------------------------------------------------
# Design tokens (used by CSS and Plotly so everything matches)
# ----------------------------------------------------------------------------
PALETTE = {
    "bg": "#0B1020",
    "panel": "#111832",
    "panel_2": "#161F40",
    "border": "rgba(139,148,255,0.16)",
    "text": "#E6E9F5",
    "muted": "#8B94B8",
    "purple": "#8B5CF6",
    "blue": "#4F8CFF",
    "cyan": "#22D3EE",
    "rose": "#F472B6",
    "amber": "#FBBF24",
    "green": "#34D399",
}
CHURN_COLOR = PALETTE["rose"]
RETAIN_COLOR = PALETTE["blue"]
RISK_COLORS = {"Low": PALETTE["green"], "Medium": PALETTE["amber"], "High": PALETTE["rose"]}
SEQUENTIAL = [[0, "#4F8CFF"], [0.5, "#8B5CF6"], [1, "#F472B6"]]

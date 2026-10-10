"""
Synthetic customer-churn generator (fallback / demo data).

IMPORTANT: this data is *simulated*. It is clearly labelled as synthetic in the
app and must never be presented as real customer data. It exists so the project
still runs if the public IBM Telco file cannot be downloaded.

Run directly to write a CSV:
    python -m src.synthetic
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import DATA_DIR


def generate_synthetic_churn(n: int = 5000, seed: int = 42, snapshot: str = "2025-12-31") -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    snapshot_date = pd.Timestamp(snapshot)

    contract = rng.choice(["Month-to-month", "One year", "Two year"], n, p=[0.55, 0.22, 0.23])
    internet = rng.choice(["Fiber optic", "DSL", "No"], n, p=[0.42, 0.36, 0.22])
    payment = rng.choice(
        ["Electronic check", "Mailed check", "Bank transfer (automatic)", "Credit card (automatic)"],
        n, p=[0.34, 0.20, 0.23, 0.23],
    )
    senior = rng.choice(["No", "Yes"], n, p=[0.84, 0.16])
    partner = rng.choice(["Yes", "No"], n)
    paperless = rng.choice(["Yes", "No"], n, p=[0.6, 0.4])
    tech_support = np.where(internet == "No", "No internet service", rng.choice(["Yes", "No"], n, p=[0.35, 0.65]))

    # Tenure (months): longer contracts skew towards longer tenure.
    base = rng.gamma(shape=2.0, scale=14, size=n)
    tenure = np.clip(base * np.select([contract == "Two year", contract == "One year"], [1.5, 1.2], 0.8), 1, 72).round().astype(int)

    # Monthly charges depend on internet type + noise.
    monthly = np.select(
        [internet == "Fiber optic", internet == "DSL"],
        [rng.normal(88, 14, n), rng.normal(58, 11, n)],
        rng.normal(24, 5, n),
    ).clip(18, 120).round(2)
    total = (monthly * tenure * rng.normal(1.0, 0.03, n)).clip(min=monthly).round(2)

    # Churn probability from a simple logistic formula (documented, not hidden).
    z = (
        -1.1
        + np.select([contract == "Month-to-month", contract == "One year"], [1.4, 0.2], -0.9)
        - 0.035 * tenure
        + 0.012 * (monthly - 65)
        + np.where(payment == "Electronic check", 0.55, 0.0)
        + np.where(internet == "Fiber optic", 0.35, 0.0)
        + np.where(senior == "Yes", 0.3, 0.0)
        - np.where(tech_support == "Yes", 0.45, 0.0)
        + np.where(paperless == "Yes", 0.15, 0.0)
        + rng.normal(0, 0.35, n)
    )
    churn = rng.random(n) < 1 / (1 + np.exp(-z))

    signup = snapshot_date - pd.to_timedelta(tenure * 30 + rng.integers(0, 30, n), unit="D")

    return pd.DataFrame({
        "customerID": [f"SYN-{i:05d}" for i in range(1, n + 1)],
        "SignupDate": signup.strftime("%Y-%m-%d"),
        "tenure": tenure,
        "Contract": contract,
        "PaymentMethod": payment,
        "InternetService": internet,
        "SeniorCitizen": senior,
        "Partner": partner,
        "PaperlessBilling": paperless,
        "TechSupport": tech_support,
        "MonthlyCharges": monthly,
        "TotalCharges": total,
        "Churn": np.where(churn, "Yes", "No"),
    })


if __name__ == "__main__":
    out = DATA_DIR / "synthetic_churn.csv"
    out.parent.mkdir(exist_ok=True)
    generate_synthetic_churn().to_csv(out, index=False)
    print(f"Synthetic dataset written to {out}  (SIMULATED data - not real customers)")

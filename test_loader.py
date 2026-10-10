"""Edge-case tests for CSV validation. Run:  python tests/test_loader.py"""
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np
import pandas as pd

from src import data_loader as D

GOOD = D.template_dataframe()


def csv_bytes(df, enc="utf-8"):
    return io.BytesIO(df.to_csv(index=False).encode(enc))


def expect_error(name, source, must_contain):
    try:
        D.load_csv(source, "t")
    except D.DataValidationError as exc:
        text = " ".join(exc.messages).lower()
        assert must_contain.lower() in text, f"{name}: message missing '{must_contain}': {exc.messages}"
        print(f"ok  {name} -> {exc.messages[0]}")
        return
    raise AssertionError(f"{name}: expected a DataValidationError")


def big(n=120, **overrides):
    rng = np.random.default_rng(1)
    df = pd.DataFrame({
        "customerID": [f"C{i}" for i in range(n)], "tenure": rng.integers(0, 72, n),
        "Contract": rng.choice(["Month-to-month", "Two year"], n), "PaymentMethod": rng.choice(["Mailed check", "Credit card"], n),
        "MonthlyCharges": rng.uniform(20, 110, n).round(2), "Churn": rng.choice(["Yes", "No"], n),
    })
    df["TotalCharges"] = (df["tenure"] * df["MonthlyCharges"]).astype(object)
    for k, v in overrides.items():
        df[k] = v
    return df


expect_error("empty file", io.BytesIO(b""), "empty")
expect_error("header only", io.BytesIO(b"customerID,tenure\n"), "no data rows")
expect_error("missing columns", csv_bytes(pd.DataFrame({"customerID": [1], "tenure": [2]})), "missing required")
expect_error("typo hint", csv_bytes(big().rename(columns={"MonthlyCharges": "Monthly_Charge"})), "did you mean")
expect_error("bad churn values", csv_bytes(big(Churn="maybe")), "churn")
expect_error("too few rows", csv_bytes(big(10)), "usable rows")

# Messy-but-fixable data
messy = big()
messy.columns = ["customer_id", "TENURE", "contract", "payment method", "monthly charges", "Churn", "total_charges"]
messy.loc[0, "monthly charges"] = np.nan
messy.loc[1, "total_charges"] = " "
messy.loc[2, "Churn"] = np.nan
messy.loc[3, "customer_id"] = messy.loc[4, "customer_id"]
messy.loc[5, "contract"] = "  Two year "
df, rep = D.load_csv(csv_bytes(messy), "t")
assert df["Churned"].isin([0, 1]).all() and df["TotalCharges"].notna().all() and df["MonthlyCharges"].notna().all()
assert df["customerID"].is_unique and "Two year" in set(df["Contract"])
print("ok  messy file cleaned:", *rep["notes"], sep="\n    - ")

# Alternative churn encodings + latin-1 encoding
alt = big(Churn=np.random.default_rng(2).choice([1, 0], 120))
D.load_csv(csv_bytes(alt), "t")
latin = big(PaymentMethod="Tarjeta de crédito")
D.load_csv(csv_bytes(latin, "latin-1"), "t")
print("ok  1/0 churn labels and latin-1 encoding accepted")

# Invalid dates are ignored rather than crashing
bad_dates = big(SignupDate="not a date")
d, r = D.load_csv(csv_bytes(bad_dates), "t")
assert "SignupDate" not in d.columns
print("ok  unreadable SignupDate dropped with a note")
print("\nAll loader tests passed.")

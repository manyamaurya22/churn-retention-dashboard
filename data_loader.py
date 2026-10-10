"""
Loading, validating and cleaning customer data.

Everything that touches raw CSV data lives here, so the rest of the app can
assume the DataFrame is clean. Problems with an upload raise a
`DataValidationError` carrying friendly, human-readable messages.
"""
from __future__ import annotations

import difflib
import re
from pathlib import Path

import numpy as np
import pandas as pd

from . import config as C


class DataValidationError(Exception):
    """Raised when a dataset cannot be used. `.messages` is a list of strings."""

    def __init__(self, messages):
        self.messages = [messages] if isinstance(messages, str) else list(messages)
        super().__init__(" | ".join(self.messages))


# ----------------------------------------------------------------------------
# Reading
# ----------------------------------------------------------------------------
def read_csv_safely(source) -> pd.DataFrame:
    """Read a path or an uploaded file, trying common encodings."""
    last_error = None
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            if hasattr(source, "seek"):
                source.seek(0)
            df = pd.read_csv(source, encoding=encoding)
            break
        except UnicodeDecodeError as exc:
            last_error = exc
        except pd.errors.EmptyDataError:
            raise DataValidationError("The file is empty. Please upload a CSV that has a header row and data.")
        except pd.errors.ParserError as exc:
            raise DataValidationError(
                ["The file could not be parsed as a CSV.", f"Details: {str(exc)[:200]}",
                 "Tip: make sure it is comma-separated and saved as 'CSV (Comma delimited)'."]
            )
        except FileNotFoundError:
            raise DataValidationError(f"File not found: {source}")
    else:
        raise DataValidationError(f"Could not decode the file text encoding ({last_error}).")

    if df.empty:
        raise DataValidationError("The CSV has a header but no data rows.")
    return df


# ----------------------------------------------------------------------------
# Validation & cleaning
# ----------------------------------------------------------------------------
def _norm(name: str) -> str:
    """'Customer_ID ' -> 'customerid' so column names match loosely."""
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


def _canonical_columns(columns):
    """Map the file's column names onto our canonical names (case/space-insensitive)."""
    lookup = {_norm(c): c for c in C.REQUIRED_COLUMNS + C.OPTIONAL_COLUMNS}
    return {col: lookup[_norm(col)] for col in columns if _norm(col) in lookup and col != lookup[_norm(col)]}


def _normalise_churn(series: pd.Series) -> pd.Series:
    """Convert Yes/No, 1/0, True/False style values to 1/0 (NaN if unrecognised)."""
    yes = {"yes", "y", "1", "1.0", "true", "t", "churned", "left"}
    no = {"no", "n", "0", "0.0", "false", "f", "retained", "stayed", "active"}
    text = series.astype(str).str.strip().str.lower()
    out = pd.Series(np.nan, index=series.index)
    out[text.isin(yes)] = 1.0
    out[text.isin(no)] = 0.0
    return out


def validate_and_clean(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Validate the schema and clean values.

    Returns (clean_df, report) where report holds counts and a list of plain
    English notes describing what was changed - shown on the Data page so the
    cleaning is transparent rather than silent.
    """
    notes: list[str] = []
    df = raw.copy()
    rows_in = len(df)

    # 1) Column names -----------------------------------------------------
    df.columns = [str(c).strip() for c in df.columns]
    renames = _canonical_columns(df.columns)
    if renames:
        df = df.rename(columns=renames)
        notes.append("Renamed columns to the expected names: " + ", ".join(f"'{a}' -> '{b}'" for a, b in renames.items()))

    missing = [c for c in C.REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        messages = [f"Missing required column(s): {', '.join(missing)}."]
        for col in missing:
            close = difflib.get_close_matches(_norm(col), [_norm(c) for c in df.columns], n=1, cutoff=0.6)
            if close:
                original = next(c for c in df.columns if _norm(c) == close[0])
                messages.append(f"'{col}' not found - did you mean '{original}'? Rename it to '{col}'.")
        messages.append("Required columns: " + ", ".join(C.REQUIRED_COLUMNS))
        messages.append("Download the sample template on the 'Data & Export' page to see the expected format.")
        raise DataValidationError(messages)

    # 2) Text columns: trim whitespace -----------------------------------
    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].astype("object").where(df[col].isna(), df[col].astype(str).str.strip())
        df[col] = df[col].replace({"": np.nan})

    # 3) Churn label ------------------------------------------------------
    churn_num = _normalise_churn(df["Churn"])
    bad_churn = churn_num.isna()
    if bad_churn.all():
        sample = df["Churn"].dropna().astype(str).unique()[:5]
        raise DataValidationError([
            "The 'Churn' column has no recognisable values.",
            f"Found: {list(sample)}. Use Yes/No (or 1/0, True/False).",
        ])
    if bad_churn.any():
        notes.append(f"Dropped {int(bad_churn.sum())} row(s) with a missing/unrecognised Churn value.")
    df = df.loc[~bad_churn].copy()
    df["Churned"] = churn_num[~bad_churn].astype(int)
    df["Churn"] = np.where(df["Churned"] == 1, "Yes", "No")

    # 4) Numeric columns --------------------------------------------------
    for col in ("tenure", "MonthlyCharges", "TotalCharges"):
        df[col] = pd.to_numeric(df[col], errors="coerce")

    bad_tenure = df["tenure"].isna() | (df["tenure"] < 0)
    if bad_tenure.any():
        notes.append(f"Dropped {int(bad_tenure.sum())} row(s) with a missing or negative tenure.")
        df = df.loc[~bad_tenure].copy()

    bad_monthly = df["MonthlyCharges"].isna() | (df["MonthlyCharges"] < 0)
    if bad_monthly.any():
        median = df.loc[~bad_monthly, "MonthlyCharges"].median()
        if pd.isna(median):
            raise DataValidationError("'MonthlyCharges' has no valid numeric values.")
        df.loc[bad_monthly, "MonthlyCharges"] = median
        notes.append(f"Filled {int(bad_monthly.sum())} missing/negative MonthlyCharges value(s) with the median ({median:.2f}).")

    missing_total = df["TotalCharges"].isna() | (df["TotalCharges"] < 0)
    if missing_total.any():
        df.loc[missing_total, "TotalCharges"] = df.loc[missing_total, "tenure"] * df.loc[missing_total, "MonthlyCharges"]
        notes.append(
            f"Filled {int(missing_total.sum())} blank TotalCharges value(s) as tenure x MonthlyCharges "
            "(in the IBM data these are brand-new customers with tenure 0)."
        )

    # 5) IDs & duplicates -------------------------------------------------
    df["customerID"] = df["customerID"].fillna("").astype(str)
    blank_ids = df["customerID"] == ""
    if blank_ids.any():
        df.loc[blank_ids, "customerID"] = [f"UNKNOWN-{i}" for i in range(int(blank_ids.sum()))]
        notes.append(f"Assigned placeholder IDs to {int(blank_ids.sum())} row(s) with no customerID.")
    dupes = df.duplicated(subset="customerID", keep="first")
    if dupes.any():
        notes.append(f"Removed {int(dupes.sum())} duplicate customerID row(s) (kept the first).")
        df = df.loc[~dupes].copy()

    # 6) Categorical columns ---------------------------------------------
    if "SeniorCitizen" in df.columns:
        df["SeniorCitizen"] = df["SeniorCitizen"].map({0: "No", 1: "Yes", "0": "No", "1": "Yes"}).fillna(df["SeniorCitizen"])
    for col in [c for c in C.MODEL_CATEGORICAL if c in df.columns]:
        n_missing = int(df[col].isna().sum())
        if n_missing:
            df[col] = df[col].fillna("Unknown")
            notes.append(f"Filled {n_missing} missing value(s) in '{col}' with 'Unknown'.")
        df[col] = df[col].astype(str)

    # 7) Optional signup date --------------------------------------------
    if "SignupDate" in df.columns:
        parsed = pd.to_datetime(df["SignupDate"], errors="coerce")
        if parsed.notna().mean() < 0.5:
            df = df.drop(columns=["SignupDate"])
            notes.append("'SignupDate' could not be read as dates for most rows, so it was ignored.")
        else:
            df["SignupDate"] = parsed
            if parsed.isna().any():
                notes.append(f"{int(parsed.isna().sum())} row(s) have an unreadable SignupDate (kept, but excluded when a date filter is used).")

    # 8) Final sanity checks ---------------------------------------------
    if len(df) < C.MIN_ROWS:
        raise DataValidationError(
            f"Only {len(df)} usable rows remain after cleaning - at least {C.MIN_ROWS} are needed for meaningful analysis."
        )

    df = df.reset_index(drop=True)
    report = {
        "rows_in": rows_in,
        "rows_out": len(df),
        "rows_dropped": rows_in - len(df),
        "notes": notes or ["No cleaning was needed - the data was already tidy."],
        "optional_found": [c for c in C.OPTIONAL_COLUMNS if c in df.columns],
        "optional_missing": [c for c in C.OPTIONAL_COLUMNS if c not in df.columns],
    }
    return df, report


def load_csv(source, label: str, is_synthetic: bool = False) -> tuple[pd.DataFrame, dict]:
    """Read + clean in one step. Attaches the source label to the report."""
    raw = read_csv_safely(source)
    df, report = validate_and_clean(raw)
    report["source_label"] = label
    report["is_synthetic"] = is_synthetic
    return df, report


def template_dataframe() -> pd.DataFrame:
    """A tiny example file users can download to see the expected format."""
    return pd.DataFrame({
        "customerID": ["0001-AAAAA", "0002-BBBBB", "0003-CCCCC"],
        "tenure": [3, 28, 60],
        "Contract": ["Month-to-month", "One year", "Two year"],
        "PaymentMethod": ["Electronic check", "Mailed check", "Credit card (automatic)"],
        "MonthlyCharges": [79.85, 54.20, 99.10],
        "TotalCharges": [239.55, 1517.60, 5946.00],
        "Churn": ["Yes", "No", "No"],
        "InternetService": ["Fiber optic", "DSL", "Fiber optic"],
        "SignupDate": ["2025-09-15", "2023-08-30", "2020-12-31"],
    })

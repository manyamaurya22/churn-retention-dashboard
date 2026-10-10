"""
Customer Churn & Retention Intelligence Dashboard
Run with:  streamlit run app.py
"""
from __future__ import annotations

import io

import pandas as pd
import streamlit as st

from src import analysis as A
from src import config as C
from src import data_loader as D
from src.styles import inject_css
from src.synthetic import generate_synthetic_churn
from views import data_export, drivers, insights, model_page, overview, segments, trends

st.set_page_config(page_title="Churn Intelligence Dashboard", page_icon="\U0001F4CA", layout="wide", initial_sidebar_state="expanded")
inject_css()

CTX: dict = {}  # filled below; pages read from it when they run

SRC_TELCO = "IBM Telco (real public dataset)"
SRC_SYNTH = "Synthetic demo (simulated)"
SRC_UPLOAD = "Upload my own CSV"


# ----------------------------------------------------------------------------
# Cached data loaders (so reruns after a filter click are instant)
# ----------------------------------------------------------------------------
@st.cache_data(show_spinner="Loading dataset...")
def load_telco(mtime: float):
    df, rep = D.load_csv(C.TELCO_PATH, "IBM Telco Customer Churn (public dataset)")
    return A.enrich(df), rep


@st.cache_data(show_spinner="Generating synthetic dataset...")
def load_synthetic():
    buffer = io.StringIO()
    generate_synthetic_churn().to_csv(buffer, index=False)
    buffer.seek(0)
    df, rep = D.load_csv(buffer, "SYNTHETIC data - simulated, not real customers", is_synthetic=True)
    return A.enrich(df), rep


@st.cache_data(show_spinner="Validating your file...")
def load_upload(content: bytes, name: str):
    """Returns (df, report, errors). Errors are friendly messages, never a stack trace."""
    try:
        df, rep = D.load_csv(io.BytesIO(content), f"Uploaded file: {name}")
        return A.enrich(df), rep, None
    except D.DataValidationError as exc:
        return None, None, exc.messages
    except Exception as exc:  # last-resort safety net
        return None, None, [f"Unexpected problem reading the file: {exc}"]


def resolve_data(choice: str):
    """Pick the dataset, falling back gracefully if something is wrong."""
    if choice == SRC_UPLOAD:
        upload = st.sidebar.file_uploader("CSV file", type=["csv"], help="Needs: " + ", ".join(C.REQUIRED_COLUMNS))
        if upload is None:
            st.sidebar.info("Upload a CSV to analyse your own data. Showing the IBM Telco data meanwhile.")
        else:
            df, rep, errors = load_upload(upload.getvalue(), upload.name)
            if errors:
                st.error("**We couldn't use that file.** Please fix the following and upload again:\n\n" + "\n".join(f"- {e}" for e in errors))
                st.sidebar.warning("Upload failed - showing the bundled IBM data instead.")
            else:
                st.sidebar.success(f"Loaded {len(df):,} customers from {upload.name}")
                return df, rep, "upload", f"Uploaded: {upload.name}"
        choice = SRC_TELCO

    if choice == SRC_SYNTH:
        df, rep = load_synthetic()
        return df, rep, "synthetic", "SYNTHETIC \u00b7 simulated data"

    if C.TELCO_PATH.exists():
        try:
            df, rep = load_telco(C.TELCO_PATH.stat().st_mtime)
            return df, rep, "real", "IBM Telco \u00b7 public dataset"
        except D.DataValidationError as exc:
            st.warning("The bundled IBM file could not be read (" + "; ".join(exc.messages) + "). Using synthetic data instead.")
    else:
        st.warning("`data/telco_churn.csv` was not found. Run `python download_data.py` to fetch it. Using clearly-labelled synthetic data instead.")
    df, rep = load_synthetic()
    return df, rep, "synthetic", "SYNTHETIC \u00b7 simulated data"


def sidebar_filters(full: pd.DataFrame, key: str):
    """Build the filter widgets; returns (filtered_df, human-readable description)."""
    sb = st.sidebar
    sb.markdown('<div class="side-label">Filters</div>', unsafe_allow_html=True)
    changed = []

    contracts = sorted(full["Contract"].unique())
    sel_contract = sb.multiselect("Contract", contracts, default=contracts, key=f"f_contract_{key}")
    if set(sel_contract) != set(contracts):
        changed.append("Contract: " + (", ".join(sel_contract) or "none"))

    sel_internet = None
    if "InternetService" in full.columns:
        opts = sorted(full["InternetService"].unique())
        sel_internet = sb.multiselect("Internet service", opts, default=opts, key=f"f_internet_{key}")
        if set(sel_internet) != set(opts):
            changed.append("Internet: " + (", ".join(sel_internet) or "none"))

    pays = sorted(full["PaymentMethod"].unique())
    sel_pay = sb.multiselect("Payment method", pays, default=pays, key=f"f_pay_{key}")
    if set(sel_pay) != set(pays):
        changed.append("Payment: " + (", ".join(sel_pay) or "none"))

    t_min, t_max = int(full["tenure"].min()), int(full["tenure"].max())
    tenure_range = (t_min, t_max)
    if t_min < t_max:
        tenure_range = sb.slider("Tenure (months)", t_min, t_max, (t_min, t_max), key=f"f_tenure_{key}")
    if tenure_range != (t_min, t_max):
        changed.append(f"Tenure: {tenure_range[0]}-{tenure_range[1]} months")

    c_min, c_max = float(full["MonthlyCharges"].min()), float(full["MonthlyCharges"].max())
    charge_range = (c_min, c_max)
    if c_min < c_max:
        charge_range = sb.slider(f"Monthly charges ({C.CURRENCY})", float(int(c_min)), float(int(c_max) + 1),
                                 (float(int(c_min)), float(int(c_max) + 1)), step=1.0, key=f"f_charge_{key}")
    if charge_range != (float(int(c_min)), float(int(c_max) + 1)) and charge_range != (c_min, c_max):
        changed.append(f"Monthly charges: {C.CURRENCY}{charge_range[0]:.0f}-{charge_range[1]:.0f}")

    date_range = None
    if "SignupDate" in full.columns and full["SignupDate"].notna().any():
        d_min, d_max = full["SignupDate"].min().date(), full["SignupDate"].max().date()
        picked = sb.date_input("Signup date", value=(d_min, d_max), min_value=d_min, max_value=d_max, key=f"f_date_{key}")
        if isinstance(picked, (tuple, list)) and len(picked) == 2:
            date_range = picked
            if picked != (d_min, d_max):
                changed.append(f"Signup: {picked[0]} to {picked[1]}")
    else:
        sb.caption("No signup-date column in this data, so tenure is the time axis.")

    filtered = A.apply_filters(full, sel_contract, sel_internet, sel_pay, tenure_range, charge_range, date_range)
    return filtered, "; ".join(changed) if changed else "None (all customers)"


# ----------------------------------------------------------------------------
# Navigation (declared first so it renders at the top of the sidebar)
# ----------------------------------------------------------------------------
def _page(module, title, icon, path, default=False):
    return st.Page(lambda: module.render(CTX), title=title, icon=icon, url_path=path, default=default)


pages = [
    _page(overview, "Overview", ":material/dashboard:", "overview", default=True),
    _page(trends, "Trends & Retention", ":material/trending_up:", "trends"),
    _page(drivers, "Churn Drivers", ":material/analytics:", "drivers"),
    _page(segments, "Segments & Risk", ":material/group:", "segments"),
    _page(insights, "Insights", ":material/lightbulb:", "insights"),
    _page(model_page, "Predictive Model", ":material/model_training:", "model"),
    _page(data_export, "Data & Export", ":material/download:", "data"),
]
nav = st.navigation(pages)

st.sidebar.markdown('<div class="side-label">Data source</div>', unsafe_allow_html=True)
choice = st.sidebar.radio("Dataset", [SRC_TELCO, SRC_SYNTH, SRC_UPLOAD], label_visibility="collapsed")
df_full, data_report, source_kind, source_label = resolve_data(choice)
data_key = f"{source_kind}-{data_report['source_label']}-{len(df_full)}"

filtered, filter_text = sidebar_filters(df_full, data_key)
st.sidebar.caption(f"Showing **{len(filtered):,}** of {len(df_full):,} customers")

if filtered.empty:
    st.warning("No customers match the current filters. Widen the filters in the sidebar.")
    st.stop()

CTX.update(df=filtered, df_full=df_full, data_report=data_report, source_kind=source_kind, source_label=source_label,
           is_synthetic=bool(data_report.get("is_synthetic")), filter_text=filter_text)
nav.run()

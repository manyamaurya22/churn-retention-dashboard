"""Churn trends & retention analysis."""
import pandas as pd
import streamlit as st

from src import analysis as A
from src import charts as ch
from src.styles import kpi_cards, note, page_header, section, show_chart


def _retention_at(curve: pd.DataFrame, month: int) -> str:
    part = curve[curve["tenure"] <= month]
    if part.empty or curve["tenure"].max() < month:
        return "n/a"
    return f"{part['retention'].iloc[-1] * 100:.1f}%"


def render(ctx: dict) -> None:
    df = ctx["df"]
    page_header("Churn", "Trends & Retention", "How churn changes over a customer's life, and how retention differs between groups.",
                ctx["source_label"], ctx["source_kind"])

    curve = A.kaplan_meier(df)
    churned, active = df[df["Churned"] == 1], df[df["Churned"] == 0]
    kpi_cards([
        {"label": "12-month retention", "value": _retention_at(curve, 12), "sub": "still active after 1 year"},
        {"label": "24-month retention", "value": _retention_at(curve, 24), "sub": "still active after 2 years"},
        {"label": "Avg tenure \u00b7 churned", "value": f"{churned['tenure'].mean():.1f} mo" if len(churned) else "n/a", "sub": "how long leavers stayed",
         "accent": "linear-gradient(90deg,#F472B6,#8B5CF6)"},
        {"label": "Avg tenure \u00b7 active", "value": f"{active['tenure'].mean():.1f} mo" if len(active) else "n/a", "sub": "current customers so far",
         "accent": "linear-gradient(90deg,#4F8CFF,#22D3EE)"},
    ])

    section("Retention curves", "The share of customers still active after each month. Steeper drops mark risky periods.")
    options = ["None (all customers)"] + [c for c in ["Contract", "InternetService", "PaymentMethod", "Segment", "RiskTier"] if c in df.columns]
    group = st.selectbox("Compare retention by", options)
    group_col = None if group.startswith("None") else group
    curves = A.retention_curves(df, group_col)
    if curves.empty:
        st.info("Not enough customers in each group to draw reliable curves. Widen the filters.")
    else:
        show_chart(ch.retention_curve(curves, "Retention by " + (group_col or "all customers")))
    note("<b>How to read this:</b> customers who have not churned are still being observed, so a Kaplan-Meier estimate is used. "
         "It is fairer than plotting 1 &minus; churn rate, because active customers haven't had the chance to leave yet.")

    section("Churn across the customer lifetime")
    window = st.slider("Tenure window (months)", 3, 12, 6, step=1)
    left, right = st.columns([1.4, 1])
    with left:
        show_chart(ch.tenure_window_chart(A.churn_by_tenure_window(df, window)))
    with right:
        cohorts = A.signup_cohorts(df)
        if cohorts is not None and len(cohorts) > 1:
            show_chart(ch.signup_cohort_chart(cohorts))
        else:
            st.markdown("&nbsp;", unsafe_allow_html=True)
            note("<b>No signup-date column in this dataset.</b> The IBM Telco data has no calendar dates, so tenure (months) is used as the "
                 "time axis. If you upload a CSV with a <code>SignupDate</code> column, a date filter and a signup-cohort chart appear here automatically.")

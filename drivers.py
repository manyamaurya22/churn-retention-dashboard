"""Churn breakdown by the main business dimensions."""
import pandas as pd
import streamlit as st

from src import analysis as A
from src import charts as ch
from src import config as C
from src.styles import page_header, section, show_chart


def _table(table: pd.DataFrame, col: str, label: str) -> None:
    show = table[[col, "customers", "churn_rate", "share_of_churn", "avg_monthly"]].copy()
    show[col] = show[col].astype(str)
    st.dataframe(
        show.rename(columns={col: label}), hide_index=True, width="stretch",
        column_config={
            "customers": st.column_config.NumberColumn("Customers", format="%d"),
            "churn_rate": st.column_config.ProgressColumn("Churn rate", format="percent", min_value=0, max_value=1),
            "share_of_churn": st.column_config.NumberColumn("Share of churn", format="percent"),
            "avg_monthly": st.column_config.NumberColumn("Avg bill", format=f"{C.CURRENCY}%.2f"),
        },
    )


def _dimension_tab(df: pd.DataFrame, col: str, label: str, overall: float) -> None:
    table = A.churn_by(df, col)
    left, right = st.columns([1.5, 1])
    with left:
        show_chart(ch.churn_rate_bar(table, col, overall, f"Churn rate by {label.lower()}"))
    with right:
        st.markdown("&nbsp;", unsafe_allow_html=True)
        _table(table, col, label)


def render(ctx: dict) -> None:
    df = ctx["df"]
    overall = A.compute_kpis(df)["churn_rate"]
    page_header("Churn", "Drivers", "Which customer groups churn most? The dotted line is the overall churn rate for the current view.",
                ctx["source_label"], ctx["source_kind"])

    tabs = [("Contract", "Contract", "Contract type"), ("TenureGroup", "Tenure", "Tenure group"), ("PaymentMethod", "Payment", "Payment method")]
    if "InternetService" in df.columns:
        tabs.append(("InternetService", "Internet", "Internet service"))
    tabs.append(("ChargeBand", "Monthly charges", "Monthly charges"))
    tabs.append((None, "Contract \u00d7 Tenure", ""))

    ui_tabs = st.tabs([t[1] for t in tabs])
    for ui, (col, _, label) in zip(ui_tabs, tabs):
        with ui:
            if col is None:
                matrix = A.contract_tenure_matrix(df)
                show_chart(ch.heatmap(matrix, "Churn rate: contract type \u00d7 tenure group"))
                st.caption("Darker/pinker cells = higher churn. Blank cells have no customers.")
            elif col == "ChargeBand":
                _dimension_tab(df, col, label, overall)
                show_chart(ch.charges_distribution(df))
            else:
                _dimension_tab(df, col, label, overall)

"""Overview page: headline KPIs plus the most important charts."""
import streamlit as st

from src import analysis as A
from src import charts as ch
from src import config as C
from src.styles import insight_card, kpi_cards, page_header, section, show_chart


def render(ctx: dict) -> None:
    df, full = ctx["df"], ctx["df_full"]
    page_header("Customer Churn &", "Retention Intelligence",
                "Who is leaving, why it matters for revenue, and where to act first.", ctx["source_label"], ctx["source_kind"])

    k = A.compute_kpis(df)
    k_all = A.compute_kpis(full)
    filtered = len(df) != len(full)

    if filtered:
        diff = (k["churn_rate"] - k_all["churn_rate"]) * 100
        cls = "up" if diff > 0 else "down"
        arrow = "\u25b2" if diff > 0 else "\u25bc"
        all_rate = k_all["churn_rate"] * 100
        churn_sub = f'<span class="{cls}">{arrow} {abs(diff):.1f} pts</span> vs all customers ({all_rate:.1f}%)'
    else:
        churn_sub = f'{k["churned_customers"]:,} customers lost'

    kpi_cards([
        {"label": "Total customers", "value": f"{k['total_customers']:,}",
         "sub": f"{k['active_customers']:,} active \u00b7 {k['churned_customers']:,} churned"},
        {"label": "Churn rate", "value": f"{k['churn_rate'] * 100:.1f}%", "sub": churn_sub,
         "accent": "linear-gradient(90deg,#F472B6,#8B5CF6)"},
        {"label": "Retention rate", "value": f"{k['retention_rate'] * 100:.1f}%", "sub": "customers still with us",
         "accent": "linear-gradient(90deg,#4F8CFF,#22D3EE)"},
        {"label": "Monthly revenue", "value": f"{C.CURRENCY}{k['monthly_revenue']:,.0f}",
         "sub": f"from active customers \u00b7 avg bill {C.CURRENCY}{k['avg_monthly']:,.0f}"},
        {"label": "Revenue at risk", "value": f"{C.CURRENCY}{k['revenue_at_risk']:,.0f}",
         "sub": f"{k['at_risk_customers']:,} high-risk customers \u00b7 {k['at_risk_share'] * 100:.1f}% of revenue",
         "accent": "linear-gradient(90deg,#FBBF24,#F472B6)"},
    ])

    c1, c2 = st.columns([1, 1.5])
    with c1:
        show_chart(ch.churn_donut(k))
    with c2:
        show_chart(ch.retention_curve(A.retention_curves(df), "How long do customers stay?"))

    c3, c4 = st.columns([1.3, 1])
    with c3:
        show_chart(ch.tenure_window_chart(A.churn_by_tenure_window(df, 6)))
    with c4:
        show_chart(ch.churn_rate_bar(A.churn_by(df, "Contract"), "Contract", k["churn_rate"], "Churn rate by contract"))

    section("Top findings", "Auto-written from the data currently in view. See the Insights page for the full list.")
    for i, item in enumerate(A.generate_insights(df)[1:4]):
        insight_card(item, i)

"""Customer segmentation and high-risk customer insights."""
import streamlit as st

from src import analysis as A
from src import charts as ch
from src import config as C
from src.styles import kpi_cards, note, page_header, section, show_chart


def render(ctx: dict) -> None:
    df = ctx["df"]
    page_header("Segments &", "Risk", "Customer groups by lifecycle stage and spend, plus the active customers most likely to leave.",
                ctx["source_label"], ctx["source_kind"])

    # --- Segments ---------------------------------------------------------
    seg = A.segment_summary(df)
    left, right = st.columns([1.1, 1])
    with left:
        show_chart(ch.segment_bubbles(seg))
    with right:
        show_chart(ch.tenure_charge_scatter(df))

    st.dataframe(
        seg.rename(columns={"Segment": "Segment"})[["Segment", "customers", "share_of_customers", "churn_rate", "avg_tenure", "avg_monthly", "active_mrr", "revenue_lost"]],
        hide_index=True, width="stretch",
        column_config={
            "customers": st.column_config.NumberColumn("Customers", format="%d"),
            "share_of_customers": st.column_config.NumberColumn("Share of base", format="percent"),
            "churn_rate": st.column_config.ProgressColumn("Churn rate", format="percent", min_value=0, max_value=1),
            "avg_tenure": st.column_config.NumberColumn("Avg tenure (mo)", format="%.1f"),
            "avg_monthly": st.column_config.NumberColumn("Avg bill", format=f"{C.CURRENCY}%.2f"),
            "active_mrr": st.column_config.NumberColumn("Active MRR", format=f"{C.CURRENCY}%d"),
            "revenue_lost": st.column_config.NumberColumn("Revenue lost / mo", format=f"{C.CURRENCY}%d"),
        },
    )
    note("<b>Segments</b> split customers into <i>New</i> (12 months or less) vs <i>Established</i>, and <i>High</i> vs <i>Low spend</i> "
         "(above/below the median monthly bill). They are simple rules so anyone in the business can understand and act on them.")

    # --- Risk ---------------------------------------------------------------
    section("High-risk customers", "Active customers whose profile closely matches customers who already left.")
    k = A.compute_kpis(df)
    tiers = A.risk_tier_summary(df)
    c1, c2 = st.columns([1, 1.4])
    with c1:
        show_chart(ch.risk_tier_chart(tiers))
    with c2:
        kpi_cards([
            {"label": "High-risk customers", "value": f"{k['at_risk_customers']:,}", "sub": "active, flagged High", "accent": "linear-gradient(90deg,#F472B6,#8B5CF6)"},
            {"label": "Revenue at risk", "value": f"{C.CURRENCY}{k['revenue_at_risk']:,.0f}", "sub": f"{k['at_risk_share'] * 100:.1f}% of monthly revenue",
             "accent": "linear-gradient(90deg,#FBBF24,#F472B6)"},
        ])
        profile_cols = [c for c in ["Contract", "TenureGroup", "PaymentMethod", "InternetService"] if c in df.columns]
        col = st.selectbox("Compare high-risk vs other active customers by", profile_cols)
        profile = A.high_risk_profile(df, col)
        if profile.empty:
            st.info("No high-risk customers in the current view.")
        else:
            show_chart(ch.profile_comparison(profile, col))

    with st.expander("How is the risk tier calculated?"):
        st.markdown(
            "For each customer we look up the churn rate of the groups they belong to (contract, tenure group, payment method, "
            "internet service, charge band) and average them. A small smoothing term stops tiny groups from looking extreme. "
            f"**High** = score at least {C.RISK_HIGH_RATIO}\u00d7 the overall churn rate; **Medium** = at least {C.RISK_MEDIUM_RATIO}\u00d7; otherwise **Low**. "
            "It is a transparent, descriptive rule. The *Predictive Model* page offers a machine-learning alternative."
        )

    section("Customer call list")
    f1, f2 = st.columns([2, 1])
    with f1:
        chosen = st.multiselect("Risk tiers to include", ["High", "Medium", "Low"], default=["High"])
    with f2:
        top_n = st.number_input("Rows to show", min_value=10, max_value=5000, value=100, step=10)
    risky = A.high_risk_customers(df, tuple(chosen)) if chosen else None
    if risky is None or risky.empty:
        st.info("No active customers match this selection.")
    else:
        view = risky.copy()
        view["RiskScore"] = view["RiskScore"] * 100
        st.dataframe(
            view.head(int(top_n)), hide_index=True, width="stretch",
            column_config={
                "tenure": st.column_config.NumberColumn("Tenure (mo)", format="%d"),
                "MonthlyCharges": st.column_config.NumberColumn("Monthly bill", format=f"{C.CURRENCY}%.2f"),
                "RiskScore": st.column_config.ProgressColumn("Risk score", format="%.0f%%", min_value=0, max_value=100),
            },
        )
        st.caption(f"Showing {min(int(top_n), len(risky)):,} of {len(risky):,} customers \u00b7 sorted by risk score, then monthly bill.")
        st.download_button("Download this list (CSV)", risky.to_csv(index=False).encode("utf-8-sig"), "customer_call_list.csv", "text/csv")

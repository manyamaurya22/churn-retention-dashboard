"""Builds the downloadable Markdown summary report from the currently filtered data."""
from __future__ import annotations

from datetime import datetime

import pandas as pd

from . import analysis as A
from . import config as C


def _md_table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(v) for v in row) + " |")
    return "\n".join(lines)


def _breakdown_table(df: pd.DataFrame, col: str, label: str) -> str:
    t = A.churn_by(df, col)
    show = pd.DataFrame({
        label: t[col].astype(str),
        "Customers": t["customers"].map("{:,}".format),
        "Churned": t["churned"].map("{:,}".format),
        "Churn rate": (t["churn_rate"] * 100).map("{:.1f}%".format),
        "Share of all churn": (t["share_of_churn"] * 100).map("{:.1f}%".format),
    })
    return _md_table(show)


def build_report(df: pd.DataFrame, source_label: str, is_synthetic: bool, filter_text: str, total_rows: int) -> str:
    k = A.compute_kpis(df)
    out = [
        "# Customer Churn & Retention - Summary Report",
        f"_Generated {datetime.now():%d %b %Y, %H:%M}_",
        "",
        f"**Data source:** {source_label}" + ("  \n> **SYNTHETIC DATA** - simulated for demonstration; not real customers." if is_synthetic else ""),
        f"**Filters applied:** {filter_text}",
        f"**Customers in this report:** {len(df):,} of {total_rows:,}",
        "",
        "## Key metrics",
        "",
        _md_table(pd.DataFrame({
            "Metric": ["Total customers", "Churn rate", "Retention rate", "Monthly revenue (active customers)",
                       "Monthly revenue lost to churn", "Revenue at risk (high-risk active customers)", "High-risk active customers"],
            "Value": [f"{k['total_customers']:,}", f"{k['churn_rate'] * 100:.1f}%", f"{k['retention_rate'] * 100:.1f}%",
                      f"{C.CURRENCY}{k['monthly_revenue']:,.0f}", f"{C.CURRENCY}{k['revenue_lost']:,.0f}",
                      f"{C.CURRENCY}{k['revenue_at_risk']:,.0f} ({k['at_risk_share'] * 100:.1f}% of active revenue)", f"{k['at_risk_customers']:,}"],
        })),
        "",
        "## Key findings & recommendations",
        "",
    ]
    for i, item in enumerate(A.generate_insights(df), 1):
        out += [f"**{i}. {item['title']}**  ", f"{item['finding']}  ", f"*Recommended action:* {item['recommendation']}", ""]

    out += ["## Churn breakdowns", ""]
    for col, label in [("Contract", "Contract"), ("TenureGroup", "Tenure group"), ("PaymentMethod", "Payment method"),
                       ("InternetService", "Internet service"), ("ChargeBand", "Monthly charges")]:
        if col in df.columns and len(df):
            out += [f"### By {label.lower()}", "", _breakdown_table(df, col, label), ""]

    seg = A.segment_summary(df)
    out += ["## Customer segments", "", _md_table(pd.DataFrame({
        "Segment": seg["Segment"], "Customers": seg["customers"].map("{:,}".format),
        "Churn rate": (seg["churn_rate"] * 100).map("{:.1f}%".format),
        "Avg monthly bill": seg["avg_monthly"].map(lambda v: f"{C.CURRENCY}{v:,.2f}"),
        "Active MRR": seg["active_mrr"].map(lambda v: f"{C.CURRENCY}{v:,.0f}"),
    })), ""]

    out += [
        "## Method notes",
        "",
        "- Churn rate = churned customers / total customers in the filtered view.",
        "- Monthly revenue = sum of MonthlyCharges for customers who have not churned.",
        "- Risk tiers are rule-based: the average churn rate of the segments a customer belongs to (contract, tenure group, "
        "payment method, internet service, charge band) compared with the overall churn rate. Revenue at risk is the monthly "
        "charges of active customers in the High tier.",
        "- Findings show association, not proof of cause. Validate with experiments (e.g. A/B-tested retention offers) before large investments.",
    ]
    return "\n".join(out)

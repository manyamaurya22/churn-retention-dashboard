"""Insights & Recommendations in plain business language."""
import streamlit as st

from src import analysis as A
from src.styles import insight_card, note, page_header


def render(ctx: dict) -> None:
    df = ctx["df"]
    page_header("Insights &", "Recommendations", "What the data says, in plain language, and what to do about it. Rewritten automatically when filters change.",
                ctx["source_label"], ctx["source_kind"])
    for i, item in enumerate(A.generate_insights(df)):
        insight_card(item, i)
    note("<b>Read with care:</b> these findings describe <i>associations</i> in a snapshot of customers. They show where churn is concentrated, "
         "not proof of what causes it. Test retention ideas (for example with an A/B test on a small group) before rolling them out widely.")
    if ctx["is_synthetic"]:
        st.warning("These insights are based on SYNTHETIC (simulated) data and say nothing about real customers.")

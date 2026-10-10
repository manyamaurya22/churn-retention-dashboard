"""Optional machine-learning page: train, evaluate, explain, and be honest about limits."""
import pandas as pd
import streamlit as st

from src import charts as ch
from src import config as C
from src import model as M
from src.styles import kpi_cards, note, page_header, section, show_chart


@st.cache_data(show_spinner=False)
def _cached_train(df: pd.DataFrame, algorithm: str) -> dict:
    return M.train_and_evaluate(df, algorithm)


def render(ctx: dict) -> None:
    full = ctx["df_full"]
    page_header("Predictive", "Model", "An optional scikit-learn model that estimates each customer's likelihood of churning.",
                ctx["source_label"], ctx["source_kind"])
    note("<b>Optional extra.</b> The rest of the dashboard is pure descriptive analytics. This page trains on the <b>full dataset</b> "
         "(sidebar filters are ignored) with a stratified 80/20 train-test split. Read the limitations at the bottom before trusting any number.")

    algo = st.selectbox("Algorithm", list(M.ALGORITHMS), help="Logistic Regression is fastest and easiest to explain. Tree models can capture non-linear patterns but take longer.")
    try:
        with st.spinner(f"Training {algo} (includes 5-fold cross-validation)..."):
            result = _cached_train(full, algo)
    except M.ModelError as exc:
        st.error(str(exc))
        return
    except Exception as exc:  # unexpected problem: show a clear message instead of a stack trace
        st.error(f"The model could not be trained: {exc}")
        return

    section("Performance on unseen customers", f"Trained on {result['n_train']:,} customers, tested on {result['n_test']:,} the model never saw.")
    threshold = st.slider("Decision threshold - flag a customer as 'will churn' when probability is at least", 0.10, 0.90, 0.50, 0.05,
                          help="Lower = catch more churners (higher recall) but more false alarms (lower precision).")
    m = M.metrics_at_threshold(result["y_test"], result["proba_test"], threshold)
    kpi_cards([
        {"label": "ROC-AUC", "value": f"{result['auc']:.3f}", "sub": f"5-fold CV: {result['cv_auc']:.3f}"},
        {"label": "Recall", "value": f"{m['recall'] * 100:.1f}%", "sub": "of real churners caught", "accent": "linear-gradient(90deg,#F472B6,#8B5CF6)"},
        {"label": "Precision", "value": f"{m['precision'] * 100:.1f}%", "sub": "of flagged customers did churn", "accent": "linear-gradient(90deg,#4F8CFF,#22D3EE)"},
        {"label": "F1 score", "value": f"{m['f1'] * 100:.1f}%", "sub": "balance of precision & recall"},
        {"label": "Accuracy", "value": f"{m['accuracy'] * 100:.1f}%", "sub": f"'always retained' scores {(1 - result['base_rate']) * 100:.1f}%"},
    ])

    c1, c2 = st.columns(2)
    with c1:
        show_chart(ch.roc_chart(result["fpr"], result["tpr"], result["auc"]))
    with c2:
        show_chart(ch.confusion_chart(m["cm"]))
    c3, c4 = st.columns(2)
    with c3:
        show_chart(ch.importance_chart(result["importance"]))
    with c4:
        show_chart(ch.probability_hist(result["y_test"], result["proba_test"], threshold))
    st.caption("Feature importance uses permutation importance on the test set: shuffle one column and see how much the model gets worse. "
               "It shows what the model relies on, not what causes churn.")

    # --- Score active customers --------------------------------------------
    section("Highest-risk active customers (model view)",
            "Probabilities are out-of-fold: each customer was scored by a model that was not trained on them.")
    scored = full.assign(ChurnProbability=result["oof_scores"])
    active = scored[scored["Churned"] == 0]
    cols = [c for c in ["customerID", "Contract", "tenure", "MonthlyCharges", "PaymentMethod", "InternetService", "ChurnProbability"] if c in active.columns]
    top = active.sort_values("ChurnProbability", ascending=False)[cols].reset_index(drop=True)
    view = top.copy()
    view["ChurnProbability"] = view["ChurnProbability"] * 100
    st.dataframe(view.head(100), hide_index=True, width="stretch", column_config={
        "tenure": st.column_config.NumberColumn("Tenure (mo)", format="%d"),
        "MonthlyCharges": st.column_config.NumberColumn("Monthly bill", format=f"{C.CURRENCY}%.2f"),
        "ChurnProbability": st.column_config.ProgressColumn("Churn probability", format="%.0f%%", min_value=0, max_value=100),
    })
    st.download_button("Download all scored active customers (CSV)", top.to_csv(index=False).encode("utf-8-sig"), "model_scored_customers.csv", "text/csv")

    # --- What-if -------------------------------------------------------------
    with st.expander("Try a customer profile (what-if)"):
        values = {}
        cols_ui = st.columns(3)
        tenure = cols_ui[0].number_input("Tenure (months)", 0, int(full["tenure"].max()), 6)
        monthly = cols_ui[1].number_input("Monthly charges", float(full["MonthlyCharges"].min()), float(full["MonthlyCharges"].max()),
                                          float(round(full["MonthlyCharges"].median(), 2)), step=1.0)
        values.update({"tenure": tenure, "MonthlyCharges": monthly, "TotalCharges": tenure * monthly})
        cols_ui[2].caption("TotalCharges is set to tenure \u00d7 monthly charges.")
        for i, feat in enumerate(result["categorical"]):
            options = sorted(full[feat].astype(str).unique())
            values[feat] = cols_ui[i % 3].selectbox(feat, options, index=options.index(full[feat].astype(str).mode().iloc[0]), key=f"whatif_{feat}")
        show_chart(ch.gauge(M.predict_one(result, values)))
        st.caption("Class-balanced models over-estimate raw probabilities; treat this as a risk ranking score, not an exact chance.")

    # --- Limitations ------------------------------------------------------------
    section("Limitations - please read")
    st.markdown(
        """
- **Snapshot, not a forecast.** The labels say who *already* left. The model learns what churned customers look like; it does not know *when* an active customer might leave.
- **Correlation, not causation.** A feature that predicts churn is not necessarily the reason for churn.
- **One dataset, one split.** Results come from a single public dataset and may not transfer to another company. The cross-validated AUC is shown to check stability, but no model was tested on future data.
- **Thresholds are a business decision.** Catching more churners means more false alarms. The right balance depends on what a retention offer costs versus a lost customer is worth.
- **Probabilities are not calibrated.** Class balancing and tree models skew raw probabilities. Use them to *rank* customers.
- **Limited signals.** No usage, support-ticket, complaint or competitor data. Real models rely heavily on these.
- **Fairness.** `gender` is deliberately excluded. `SeniorCitizen` is included because it is in the data, but should be reviewed for fairness before any real-world use.
- **Not production-ready.** No monitoring, retraining schedule or data-drift checks. This is a learning and portfolio demonstration.
        """
    )
    if ctx["is_synthetic"]:
        st.warning("This model was trained on SYNTHETIC data. Its metrics only show that the pipeline works.")

"""Data quality, previews, downloads and project documentation."""
import streamlit as st

from src import config as C
from src import data_loader as D
from src.report import build_report
from src.styles import note, page_header, section
import src.analysis as A


def render(ctx: dict) -> None:
    df, full, rep = ctx["df"], ctx["df_full"], ctx["data_report"]
    page_header("Data &", "Export", "Check data quality, download the filtered data and a summary report, or learn how the project works.",
                ctx["source_label"], ctx["source_kind"])

    section("Downloads")
    report_md = build_report(df, ctx["source_label"], ctx["is_synthetic"], ctx["filter_text"], len(full))
    drop_cols = [c for c in ["Churned"] if c in df.columns]
    c1, c2, c3, c4 = st.columns(4)
    c1.download_button("Summary report (.md)", report_md.encode("utf-8"), "churn_summary_report.md", "text/markdown", width="stretch")
    c2.download_button("Filtered dataset (.csv)", df.drop(columns=drop_cols).to_csv(index=False).encode("utf-8-sig"),
                       "filtered_customers.csv", "text/csv", width="stretch")
    risky = A.high_risk_customers(df)
    c3.download_button("High-risk list (.csv)", risky.to_csv(index=False).encode("utf-8-sig"), "high_risk_customers.csv", "text/csv", width="stretch")
    c4.download_button("Upload template (.csv)", D.template_dataframe().to_csv(index=False).encode("utf-8"),
                       "upload_template.csv", "text/csv", width="stretch")
    st.caption(f"The report and filtered dataset reflect your current sidebar filters ({len(df):,} of {len(full):,} customers).")
    with st.expander("Preview the summary report"):
        st.markdown(report_md)

    section("Data quality", f"{rep['rows_in']:,} rows read \u2192 {rep['rows_out']:,} rows used")
    for n in rep["notes"]:
        st.markdown(f"- {n}")
    q1, q2 = st.columns(2)
    q1.markdown("**Required columns:** " + ", ".join(f"`{c}`" for c in C.REQUIRED_COLUMNS))
    q2.markdown("**Optional columns found:** " + (", ".join(f"`{c}`" for c in rep["optional_found"]) or "none"))
    if rep["optional_missing"]:
        with st.expander("Optional columns not in this dataset"):
            st.write(", ".join(rep["optional_missing"]))
            st.caption("Missing optional columns simply hide the related chart or model feature.")

    section("Data preview", "First 200 rows of the filtered data (including calculated columns).")
    st.dataframe(df.head(200), hide_index=True, width="stretch")

    section("Expected CSV format")
    st.table({"Column": list(C.COLUMN_HELP), "Meaning": list(C.COLUMN_HELP.values())})
    note("Column names are matched loosely (<code>Customer_ID</code>, <code>monthly charges</code> and <code>MonthlyCharges</code> all work). "
         "Unrecognised extra columns are ignored.")

    with st.expander("About this project: what each tool does"):
        st.markdown(
            """
| Tool | Role in this project |
|---|---|
| **Python** | The language that ties everything together: loads data, runs the analysis, trains the model and serves the app. |
| **Pandas & NumPy** | Clean the CSV (types, blanks, duplicates), then calculate every KPI, group-by table, retention curve and risk score. |
| **Plotly** | Draws the interactive charts (hover, zoom, legend toggles) in the dashboard's dark theme. |
| **Streamlit** | Turns the Python scripts into a web app: sidebar filters, pages, file upload and download buttons, with no HTML/JS required. |
| **scikit-learn** | Builds the optional churn model: preprocessing pipeline, classifiers, train/test split, cross-validation and evaluation metrics. |
            """
        )

# 📊 Customer Churn & Retention Intelligence Dashboard

An interactive analytics product built with **Python, Pandas, Plotly and Streamlit** that shows *who is leaving, how much revenue is at stake, and where to act first*, with an optional **scikit-learn** churn model.

> **Dataset:** the public [IBM Telco Customer Churn](https://github.com/IBM/telco-customer-churn-on-icp4d) dataset (7,043 real-world-style customers) is bundled in `data/telco_churn.csv`. A clearly labelled **synthetic** generator exists as a fallback. Synthetic data is never presented as real; the app shows a yellow **SYNTHETIC** badge and warnings whenever it is used.

<!-- Add 2-3 screenshots here after you run the app, e.g. ![Overview](docs/overview.png) -->

## ✨ Features

| Page | What it does |
|---|---|
| **Overview** | KPI cards (Total Customers, Churn Rate, Retention Rate, Monthly Revenue, Revenue at Risk), churn donut, retention curve, churn by tenure and contract, auto-written top findings |
| **Trends & Retention** | Kaplan-Meier retention curves (compare by contract, internet service, payment method, segment, risk tier), churn across the customer lifetime, signup-cohort trend when a `SignupDate` column exists |
| **Churn Drivers** | Churn by contract, tenure group, payment method, internet service, monthly charges, plus a contract × tenure heatmap |
| **Segments & Risk** | Rule-based segments (New/Established × High/Low spend), segment bubble map, risk tiers, revenue at risk, a downloadable high-risk customer call list |
| **Insights** | Plain-English findings and recommended actions, generated from the filtered data |
| **Predictive Model** | Logistic Regression / Random Forest / Gradient Boosting, ROC-AUC, precision, recall, F1, confusion matrix, adjustable threshold, permutation importance, what-if scorer, honest limitations |
| **Data & Export** | Cleaning report, data preview, summary report (`.md`), filtered dataset (`.csv`), high-risk list, upload template |

**Also included:** sidebar filters (contract, internet service, payment method, tenure, monthly charges, and signup date when available) · CSV upload with column validation and helpful error messages · dark-navy SaaS theme with responsive KPI cards and subtle animations.

## 🗂 Project structure

```
churn_dashboard/
├── app.py                  # Entry point: navigation, data source, sidebar filters
├── requirements.txt
├── README.md
├── download_data.py        # Re-downloads the IBM dataset
├── .streamlit/config.toml  # Dark theme + upload size
├── data/
│   ├── telco_churn.csv     # IBM Telco dataset (public)
│   └── sample_template.csv # Example upload format
├── src/
│   ├── config.py           # Column names, thresholds, colours (one place to tweak)
│   ├── data_loader.py      # Read, validate and clean CSVs (friendly errors)
│   ├── analysis.py         # KPIs, breakdowns, retention curves, risk score, insights
│   ├── charts.py           # All Plotly charts + shared dark theme
│   ├── model.py            # scikit-learn pipeline, evaluation, importance
│   ├── report.py           # Downloadable Markdown report
│   ├── styles.py           # CSS + KPI/insight card helpers
│   └── synthetic.py        # Labelled synthetic data generator (fallback)
├── views/                  # One file per dashboard page
│   └── overview.py · trends.py · drivers.py · segments.py · insights.py · model_page.py · data_export.py
└── tests/
    ├── smoke_test.py       # Renders every page headlessly; fails on any exception
    └── test_loader.py      # Bad-upload edge cases
```

## 🚀 Install and run (Windows)

Requires **Python 3.10 or newer** ([python.org](https://www.python.org/downloads/); tick *"Add Python to PATH"*).

Open **PowerShell** in the project folder:

```powershell
cd path\to\churn_dashboard
py -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

The dashboard opens at <http://localhost:8501>.

> If PowerShell blocks `activate`, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first, or use **Command Prompt** instead.

**Optional commands**

```powershell
python download_data.py          # re-download the IBM dataset
python -m src.synthetic          # write data\synthetic_churn.csv (simulated data)
python tests\test_loader.py      # CSV validation tests
python tests\smoke_test.py       # renders all pages with all data sources
```

macOS/Linux: replace the venv line with `python3 -m venv venv && source venv/bin/activate`.

## 📤 Uploading your own CSV

Choose **Upload my own CSV** in the sidebar. Required columns:

`customerID, tenure, Contract, PaymentMethod, MonthlyCharges, TotalCharges, Churn`

Optional (used when present): `InternetService, SignupDate, SeniorCitizen, Partner, Dependents, PhoneService, MultipleLines, OnlineSecurity, OnlineBackup, DeviceProtection, TechSupport, StreamingTV, StreamingMovies, PaperlessBilling`

The validator matches column names loosely (`Customer_ID` works), accepts `Yes/No`, `1/0`, `True/False` for churn, fills blank `TotalCharges`, removes duplicate IDs, tries several text encodings, and explains exactly what is wrong if the file can't be used (missing columns with "did you mean…" hints, empty file, unrecognised churn values, too few rows). Everything it changes is listed on the **Data & Export** page. A template is downloadable from the same page.

## 🧰 What each tool does in this project

- **Python**: the glue. Loads data, runs the analysis, trains the model and serves the app.
- **Pandas & NumPy**: clean the CSV (types, blanks, duplicates) and calculate every KPI, group-by table, retention curve and risk score. Nothing shown is hard-coded.
- **Plotly**: draws the interactive charts (hover, zoom, legend toggles) in a custom dark theme.
- **Streamlit**: turns Python into the web app: pages, sidebar filters, file upload, download buttons, caching.
- **scikit-learn**: the optional model: preprocessing pipeline, classifiers, stratified split, cross-validation, metrics, permutation importance.

## 📐 Key definitions

- **Churn rate** = churned customers ÷ total customers in the current view.
- **Monthly revenue** = sum of `MonthlyCharges` for customers who have *not* churned.
- **Revenue at risk** = monthly charges of *active* customers in the **High** risk tier.
- **Risk score** = average (smoothed) historical churn rate of the segments a customer belongs to: contract, tenure group, payment method, internet service, charge band. **High** ≥ 1.25× overall churn, **Medium** ≥ 0.85×. Thresholds are in `src/config.py`.
- **Retention curve** = Kaplan-Meier estimate, which correctly treats still-active customers as "not yet observed to leave".

## ⚠️ Honest limitations

- The IBM dataset is a **snapshot with no calendar dates**, so "trends" use *tenure* as the time axis. A true month-by-month trend needs a `SignupDate` (supported on upload).
- Insights show **association, not causation**. Validate with experiments before large investments.
- The rule-based risk score is computed on the same data it describes (descriptive, not predictive).
- The model is a learning demonstration: single dataset, no time-based validation, uncalibrated probabilities, no usage or support data, no monitoring. `gender` is deliberately excluded as a feature. See the in-app *Limitations* section.
- Charts and layout were built for modern desktop browsers; mobile layout is responsive but less tested.

## 📈 Results on the bundled data (computed by the app, not typed in)

With the IBM data: overall churn **26.5%**; month-to-month customers churn at **42.7%** versus **2.8%** on two-year contracts; the first 12 months have the highest churn; the model reaches **ROC-AUC ≈ 0.84**. Re-run the app to see current figures for any filter or upload.

## 🧪 Testing

`tests/smoke_test.py` renders every page against the IBM data, a filtered subset and the synthetic data, and `tests/test_loader.py` checks bad uploads. Both were run on Python 3.12 with the newest libraries *and* an older combination (Streamlit 1.52, pandas 2.2, scikit-learn 1.5).

## 💼 Using this in your portfolio

- Add 2-3 screenshots (Overview, Drivers, Model) to a `docs/` folder and link them above.
- Deploy free on [Streamlit Community Cloud](https://streamlit.io/cloud): push to GitHub, choose `app.py`, deploy.
- LinkedIn angle: *"Built an interactive churn analytics dashboard (Python, Pandas, Plotly, Streamlit, scikit-learn). Found that month-to-month contracts drive ~89% of churn and quantified revenue at risk."* Check these numbers in your own run before posting.

## 📚 Data credit

IBM Telco Customer Churn sample dataset, published by IBM in the [telco-customer-churn-on-icp4d](https://github.com/IBM/telco-customer-churn-on-icp4d) repository. Check the repository's licence before redistributing.

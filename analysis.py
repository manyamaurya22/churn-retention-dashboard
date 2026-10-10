"""
All numbers shown in the dashboard are calculated here with Pandas/NumPy.
Nothing is hard-coded: change the data and every KPI, chart and insight changes.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C


# ----------------------------------------------------------------------------
# Feature engineering
# ----------------------------------------------------------------------------
def _charge_bands(monthly: pd.Series) -> pd.Series:
    """Split MonthlyCharges into quartile bands labelled with their real ranges."""
    edges = monthly.quantile([0, 0.25, 0.5, 0.75, 1]).unique()
    if len(edges) < 3:
        return pd.Series(pd.Categorical(["All"] * len(monthly)), index=monthly.index)
    for fmt in ("{:.0f}", "{:.2f}"):
        labels = [f"{C.CURRENCY}{fmt.format(lo)}-{fmt.format(hi)}" for lo, hi in zip(edges[:-1], edges[1:])]
        if len(set(labels)) == len(labels):
            break
    return pd.cut(monthly, bins=edges, labels=labels, include_lowest=True, ordered=True)


def add_risk_scores(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transparent, rule-based risk score.

    For each dimension (contract, tenure group, payment method, ...) we look up
    the churn rate of the customer's segment (smoothed so tiny groups don't look
    extreme) and average them. High-risk = score well above the overall rate.
    This is *descriptive*; the Model page offers a predictive alternative.
    """
    out = df.copy()
    overall = out["Churned"].mean()
    dims = [d for d in C.RISK_DIMENSIONS if d in out.columns]
    k = C.RISK_SMOOTHING
    parts = []
    for dim in dims:
        stats = out.groupby(dim, observed=True)["Churned"].agg(["sum", "count"])
        rate = (stats["sum"] + k * overall) / (stats["count"] + k)
        rate.index = rate.index.astype(str)
        parts.append(out[dim].astype(str).map(rate).astype(float))
    out["RiskScore"] = pd.concat(parts, axis=1).mean(axis=1) if parts else overall

    if overall > 0:
        ratio = out["RiskScore"] / overall
        out["RiskTier"] = np.select(
            [ratio >= C.RISK_HIGH_RATIO, ratio >= C.RISK_MEDIUM_RATIO], ["High", "Medium"], "Low"
        )
    else:
        out["RiskTier"] = "Low"
    out["RiskTier"] = pd.Categorical(out["RiskTier"], categories=["Low", "Medium", "High"], ordered=True)
    return out


def enrich(df: pd.DataFrame) -> pd.DataFrame:
    """Add derived columns: tenure group, charge band, segment, risk score/tier."""
    out = df.copy()
    out["TenureGroup"] = pd.cut(out["tenure"], bins=C.TENURE_BINS, labels=C.TENURE_LABELS, ordered=True)
    out["ChargeBand"] = _charge_bands(out["MonthlyCharges"])

    median_charge = out["MonthlyCharges"].median()
    stage = np.where(out["tenure"] <= 12, "New", "Established")
    spend = np.where(out["MonthlyCharges"] >= median_charge, "High spend", "Low spend")
    out["Segment"] = pd.Series(stage, index=out.index) + " \u00b7 " + pd.Series(spend, index=out.index)

    return add_risk_scores(out)


# ----------------------------------------------------------------------------
# Filters
# ----------------------------------------------------------------------------
def apply_filters(df, contracts=None, internet=None, payments=None, tenure_range=None,
                  charge_range=None, date_range=None, risk_tiers=None) -> pd.DataFrame:
    mask = pd.Series(True, index=df.index)
    if contracts is not None:
        mask &= df["Contract"].isin(contracts)
    if internet is not None and "InternetService" in df.columns:
        mask &= df["InternetService"].isin(internet)
    if payments is not None:
        mask &= df["PaymentMethod"].isin(payments)
    if tenure_range is not None:
        mask &= df["tenure"].between(*tenure_range)
    if charge_range is not None:
        mask &= df["MonthlyCharges"].between(*charge_range)
    if date_range is not None and "SignupDate" in df.columns and len(date_range) == 2:
        start, end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
        mask &= df["SignupDate"].between(start, end)
    if risk_tiers is not None:
        mask &= df["RiskTier"].isin(risk_tiers)
    return df[mask]


# ----------------------------------------------------------------------------
# KPIs
# ----------------------------------------------------------------------------
def compute_kpis(df: pd.DataFrame) -> dict:
    total = len(df)
    churned = int(df["Churned"].sum())
    active = df[df["Churned"] == 0]
    high_risk_active = active[active["RiskTier"] == "High"]
    mrr = float(active["MonthlyCharges"].sum())
    at_risk = float(high_risk_active["MonthlyCharges"].sum())
    return {
        "total_customers": total,
        "churned_customers": churned,
        "active_customers": total - churned,
        "churn_rate": churned / total if total else 0.0,
        "retention_rate": 1 - churned / total if total else 0.0,
        "monthly_revenue": mrr,
        "revenue_lost": float(df.loc[df["Churned"] == 1, "MonthlyCharges"].sum()),
        "revenue_at_risk": at_risk,
        "at_risk_customers": len(high_risk_active),
        "at_risk_share": at_risk / mrr if mrr else 0.0,
        "avg_tenure": float(df["tenure"].mean()) if total else 0.0,
        "avg_monthly": float(df["MonthlyCharges"].mean()) if total else 0.0,
    }


# ----------------------------------------------------------------------------
# Breakdown tables
# ----------------------------------------------------------------------------
def churn_by(df: pd.DataFrame, col: str, sort_by_rate: bool | None = None) -> pd.DataFrame:
    """Churn statistics for every value of `col`."""
    tmp = df.assign(_lost=df["MonthlyCharges"] * df["Churned"])
    table = tmp.groupby(col, observed=True).agg(
        customers=("Churned", "size"),
        churned=("Churned", "sum"),
        avg_monthly=("MonthlyCharges", "mean"),
        avg_tenure=("tenure", "mean"),
        monthly_revenue_lost=("_lost", "sum"),
    ).reset_index()
    table["churn_rate"] = table["churned"] / table["customers"]
    total_churned = table["churned"].sum()
    table["share_of_churn"] = table["churned"] / total_churned if total_churned else 0.0
    if sort_by_rate is None:
        sort_by_rate = not isinstance(df[col].dtype, pd.CategoricalDtype)
    if sort_by_rate:
        table = table.sort_values("churn_rate", ascending=False)
    return table.reset_index(drop=True)


def churn_by_tenure_window(df: pd.DataFrame, window: int = 6) -> pd.DataFrame:
    """Churn rate for tenure windows (0-5, 6-11, ...) - the 'churn over customer life' trend."""
    start = (df["tenure"] // window * window).astype(int)
    table = df.assign(_start=start).groupby("_start").agg(
        customers=("Churned", "size"), churned=("Churned", "sum")
    ).reset_index()
    table["churn_rate"] = table["churned"] / table["customers"]
    table["label"] = table["_start"].astype(str) + "-" + (table["_start"] + window - 1).astype(str)
    return table


def kaplan_meier(df: pd.DataFrame) -> pd.DataFrame:
    """
    Retention curve: the probability a customer is still active after t months.

    Customers who have not churned are 'censored' (we only know they lasted at
    least `tenure` months), which is why a Kaplan-Meier estimate is more honest
    than simply plotting 1 - churn rate by tenure.
    """
    if df.empty:
        return pd.DataFrame({"tenure": [0], "retention": [1.0]})
    d = df.groupby("tenure")["Churned"].agg(["sum", "count"]).sort_index()
    at_risk = len(df) - d["count"].cumsum().shift(fill_value=0)
    survival = (1 - d["sum"] / at_risk).cumprod()
    curve = pd.DataFrame({"tenure": d.index.astype(float), "retention": survival.values})
    curve = pd.concat([pd.DataFrame({"tenure": [0.0], "retention": [1.0]}), curve], ignore_index=True)
    return curve.drop_duplicates("tenure", keep="last").reset_index(drop=True)


def retention_curves(df: pd.DataFrame, group_col: str | None = None, min_group_size: int = 30) -> pd.DataFrame:
    if not group_col:
        curve = kaplan_meier(df)
        curve["group"] = "All customers"
        return curve
    frames = []
    for name, part in df.groupby(group_col, observed=True):
        if len(part) >= min_group_size:
            curve = kaplan_meier(part)
            curve["group"] = str(name)
            frames.append(curve)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["tenure", "retention", "group"])


def signup_cohorts(df: pd.DataFrame) -> pd.DataFrame | None:
    """Churn rate by signup month (only when a SignupDate column exists)."""
    if "SignupDate" not in df.columns:
        return None
    valid = df.dropna(subset=["SignupDate"])
    if valid.empty:
        return None
    table = valid.assign(month=valid["SignupDate"].dt.to_period("M").dt.to_timestamp()).groupby("month").agg(
        customers=("Churned", "size"), churned=("Churned", "sum")
    ).reset_index()
    table["churn_rate"] = table["churned"] / table["customers"]
    return table


def contract_tenure_matrix(df: pd.DataFrame) -> pd.DataFrame:
    return df.pivot_table(index="Contract", columns="TenureGroup", values="Churned", aggfunc="mean", observed=True)


def segment_summary(df: pd.DataFrame) -> pd.DataFrame:
    tmp = df.assign(_active_mrr=df["MonthlyCharges"] * (1 - df["Churned"]), _lost=df["MonthlyCharges"] * df["Churned"])
    table = tmp.groupby("Segment").agg(
        customers=("Churned", "size"),
        churned=("Churned", "sum"),
        avg_monthly=("MonthlyCharges", "mean"),
        avg_tenure=("tenure", "mean"),
        active_mrr=("_active_mrr", "sum"),
        revenue_lost=("_lost", "sum"),
    ).reset_index()
    table["churn_rate"] = table["churned"] / table["customers"]
    table["share_of_customers"] = table["customers"] / table["customers"].sum()
    return table.sort_values("churn_rate", ascending=False).reset_index(drop=True)


def high_risk_customers(df: pd.DataFrame, tiers=("High",)) -> pd.DataFrame:
    """Active customers in the chosen risk tiers, biggest revenue exposure first."""
    cols = [c for c in ["customerID", "Segment", "Contract", "tenure", "MonthlyCharges",
                        "PaymentMethod", "InternetService", "RiskScore", "RiskTier"] if c in df.columns]
    active = df[(df["Churned"] == 0) & (df["RiskTier"].isin(tiers))]
    return active[cols].sort_values(["RiskScore", "MonthlyCharges"], ascending=False).reset_index(drop=True)


def risk_tier_summary(df: pd.DataFrame) -> pd.DataFrame:
    active = df[df["Churned"] == 0]
    table = active.groupby("RiskTier", observed=False).agg(
        customers=("Churned", "size"), monthly_revenue=("MonthlyCharges", "sum")
    ).reset_index()
    return table


def high_risk_profile(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """How the active high-risk group differs from all other active customers on one column."""
    active = df[df["Churned"] == 0]
    high = active[active["RiskTier"] == "High"]
    rest = active[active["RiskTier"] != "High"]
    if high.empty or rest.empty:
        return pd.DataFrame(columns=[col, "High-risk", "Other active"])
    a = high[col].astype(str).value_counts(normalize=True).rename("High-risk")
    b = rest[col].astype(str).value_counts(normalize=True).rename("Other active")
    out = pd.concat([a, b], axis=1).fillna(0)
    out.index.name = col
    return out.reset_index()


# ----------------------------------------------------------------------------
# Plain-English insights
# ----------------------------------------------------------------------------
def _pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def _money(x: float) -> str:
    return f"{C.CURRENCY}{x:,.0f}"


def _cap(text: str) -> str:
    """Capitalise the first letter only (str would lower-case the rest)."""
    for i, ch in enumerate(text):
        if ch.isalpha():
            return text[:i] + ch.upper() + text[i + 1:]
    return text


def _who(col: str, value) -> str:
    """Readable phrase for a category, e.g. InternetService='No' -> 'customers with no internet service'."""
    if col == "InternetService" and str(value).lower() in {"no", "none"}:
        return "customers with no internet service"
    if col == "TenureGroup":
        return f"customers in the {value} tenure band"
    return f"'{value}' customers"


def generate_insights(df: pd.DataFrame) -> list[dict]:
    """
    Turn the numbers into business-language findings + recommendations.
    Every sentence is filled in from the (filtered) data, so it stays correct
    when filters or uploads change. Returns a list of dicts:
    {title, finding, recommendation, level}.
    """
    insights: list[dict] = []
    if len(df) < 30:
        return [{"title": "Not enough data", "level": "info",
                 "finding": "Fewer than 30 customers match the current filters, so findings would be unreliable.",
                 "recommendation": "Widen the filters in the sidebar to see insights."}]

    k = compute_kpis(df)
    overall = k["churn_rate"]

    # 1) Headline ---------------------------------------------------------
    insights.append({
        "title": "Headline: how much are we losing?",
        "level": "high" if overall >= 0.25 else "medium" if overall >= 0.12 else "low",
        "finding": (f"{_pct(overall)} of customers ({k['churned_customers']:,} of {k['total_customers']:,}) have churned, "
                    f"taking {_money(k['revenue_lost'])} of monthly revenue with them. "
                    f"The remaining active base brings in {_money(k['monthly_revenue'])} per month."),
        "recommendation": "Treat retention as a revenue lever: even a small cut in churn protects recurring income every month.",
    })

    def worst_best(col, min_size=30):
        t = churn_by(df, col, sort_by_rate=True)
        t = t[t["customers"] >= min_size]
        return (t.iloc[0], t.iloc[-1]) if len(t) >= 2 else (None, None)

    # 2) Contract ---------------------------------------------------------
    worst, best = worst_best("Contract")
    if worst is not None and worst["churn_rate"] > 0:
        ratio = worst["churn_rate"] / best["churn_rate"] if best["churn_rate"] > 0 else np.inf
        ratio_text = f"{ratio:.1f}x" if np.isfinite(ratio) else "far"
        insights.append({
            "title": "Contract type is the strongest warning sign" if ratio >= 2 else "Contract type matters",
            "level": "high" if ratio >= 2 else "medium",
            "finding": (f"{_cap(_who('Contract', worst['Contract']))} churn at {_pct(worst['churn_rate'])}, which is {ratio_text} the rate of "
                        f"{_who('Contract', best['Contract'])} ({_pct(best['churn_rate'])}). They make up {_pct(worst['share_of_churn'])} of all churn."),
            "recommendation": (f"Offer targeted incentives (discounts, free upgrades, loyalty perks) to move '{worst['Contract']}' "
                               f"customers onto '{best['Contract']}' plans."),
        })

    # 3) Tenure -----------------------------------------------------------
    t = churn_by(df, "TenureGroup", sort_by_rate=False)
    if len(t) >= 2:
        first, last = t.iloc[0], t.iloc[-1]
        insights.append({
            "title": "The first year is the danger zone" if first["churn_rate"] > last["churn_rate"] * 1.5 else "Churn across customer lifetime",
            "level": "high" if first["churn_rate"] > last["churn_rate"] * 1.5 else "medium",
            "finding": (f"The {first['TenureGroup']} tenure band churns at {_pct(first['churn_rate'])} versus {_pct(last['churn_rate'])} "
                        f"for the {last['TenureGroup']} band. The earliest band alone accounts for {_pct(first['share_of_churn'])} of all churn."),
            "recommendation": "Invest in onboarding: welcome journeys, a check-in call at month 2-3 and quick fixes for early service problems.",
        })

    # 4) Payment method ---------------------------------------------------
    worst, best = worst_best("PaymentMethod")
    if worst is not None and worst["churn_rate"] - best["churn_rate"] >= 0.05:
        insights.append({
            "title": "Payment method is linked to loyalty",
            "level": "medium",
            "finding": (f"Customers paying by '{worst['PaymentMethod']}' churn at {_pct(worst['churn_rate'])} compared with "
                        f"{_pct(best['churn_rate'])} for '{best['PaymentMethod']}' - a gap of {(worst['churn_rate'] - best['churn_rate']) * 100:.1f} points."),
            "recommendation": f"Encourage a switch from '{worst['PaymentMethod']}' to automatic payments with a small bill credit; automatic billing removes a friction point.",
        })

    # 5) Internet service -------------------------------------------------
    if "InternetService" in df.columns:
        worst, best = worst_best("InternetService")
        if worst is not None and worst["churn_rate"] - best["churn_rate"] >= 0.05:
            insights.append({
                "title": "Service type shows uneven churn",
                "level": "medium",
                "finding": (f"{_cap(_who('InternetService', worst['InternetService']))} churn at {_pct(worst['churn_rate'])} (average bill {_money(worst['avg_monthly'])}/month) "
                            f"versus {_pct(best['churn_rate'])} for {_who('InternetService', best['InternetService'])}."),
                "recommendation": (f"Investigate quality, pricing and competitor offers for {_who('InternetService', worst['InternetService'])}. "
                                   "A high-churn product is often a value-for-money or reliability problem."),
            })

    # 6) Price ------------------------------------------------------------
    bands = churn_by(df, "ChargeBand", sort_by_rate=False)
    bands = bands[bands["customers"] >= 30]
    if len(bands) >= 3:
        low, high = bands.iloc[0], bands.iloc[-1]
        if high["churn_rate"] - low["churn_rate"] >= 0.05:
            insights.append({
                "title": "Higher bills come with higher churn",
                "level": "medium",
                "finding": (f"Customers paying {high['ChargeBand']} per month churn at {_pct(high['churn_rate'])}, "
                            f"versus {_pct(low['churn_rate'])} for those paying {low['ChargeBand']}."),
                "recommendation": "Review pricing and bundles for high-bill customers and make sure the value they receive is visible (e.g. add-ons, support).",
            })

    # 7) Revenue at risk --------------------------------------------------
    if k["at_risk_customers"] > 0:
        insights.append({
            "title": "Revenue currently at risk",
            "level": "high" if k["at_risk_share"] >= 0.25 else "medium",
            "finding": (f"{k['at_risk_customers']:,} active customers are flagged high-risk, representing {_money(k['revenue_at_risk'])} "
                        f"per month ({_pct(k['at_risk_share'])} of active monthly revenue)."),
            "recommendation": "Start a proactive retention campaign with this list (see Segments & Risk). Contact the highest-spend customers first.",
        })

    return insights

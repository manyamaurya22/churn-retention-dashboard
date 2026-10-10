"""
Plotly chart builders. Each function takes a DataFrame and returns a figure;
the Streamlit pages decide where to show them. A shared theme keeps every chart
visually consistent with the dark-navy dashboard.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from . import config as C

P = C.PALETTE
GROUP_COLORS = [P["purple"], P["blue"], P["cyan"], P["rose"], P["amber"], P["green"]]
FONT = "Inter, Segoe UI, system-ui, sans-serif"


def apply_theme(fig: go.Figure, title: str = "", height: int = 340, legend: bool = True) -> go.Figure:
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, color="#B8C0DD", size=12),
        title=dict(text=title, x=0.01, xanchor="left", y=0.97, font=dict(size=14, color="#FFFFFF")),
        height=height,
        margin=dict(l=12, r=12, t=52, b=12),
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="right", x=1, bgcolor="rgba(0,0,0,0)", font=dict(size=11)),
        hoverlabel=dict(bgcolor="#1B2550", bordercolor="#8B5CF6", font=dict(family=FONT, size=12, color="#FFFFFF")),
        transition=dict(duration=350),
    )
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.05)", zeroline=False, linecolor="rgba(255,255,255,0.10)", automargin=True)
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.06)", zeroline=False, linecolor="rgba(255,255,255,0.10)", automargin=True)
    return fig


def _pct_axis(fig, axis="y", rng=None):
    getattr(fig, f"update_{axis}axes")(tickformat=".0%", **({"range": rng} if rng else {}))


# ----------------------------------------------------------------------------
# Overview
# ----------------------------------------------------------------------------
def churn_donut(k: dict) -> go.Figure:
    fig = go.Figure(go.Pie(
        labels=["Retained", "Churned"], values=[k["active_customers"], k["churned_customers"]],
        hole=0.74, marker=dict(colors=[C.RETAIN_COLOR, C.CHURN_COLOR], line=dict(color="#0B1020", width=3)),
        textinfo="none", sort=False, hovertemplate="%{label}: %{value:,} customers (%{percent})<extra></extra>",
    ))
    fig.add_annotation(text=f"<b>{k['churn_rate'] * 100:.1f}%</b><br><span style='font-size:11px;color:#8B94B8'>churn rate</span>",
                       showarrow=False, font=dict(size=26, color="#FFFFFF"))
    return apply_theme(fig, "Customer base", 340)


def retention_curve(curves: pd.DataFrame, title="Retention curve (Kaplan-Meier)") -> go.Figure:
    fig = go.Figure()
    for i, (name, part) in enumerate(curves.groupby("group", sort=False)):
        color = GROUP_COLORS[i % len(GROUP_COLORS)]
        fig.add_trace(go.Scatter(
            x=part["tenure"], y=part["retention"], mode="lines", name=str(name), line=dict(width=3, color=color, shape="hv"),
            hovertemplate="Month %{x:.0f}: %{y:.1%} still active<extra>" + str(name) + "</extra>",
            fill="tozeroy" if curves["group"].nunique() == 1 else None, fillcolor="rgba(139,92,246,0.10)",
        ))
    fig.update_xaxes(title="Months since signup")
    _pct_axis(fig, "y", [0, 1.02])
    fig.update_yaxes(title="Customers still active")
    return apply_theme(fig, title, 340, legend=curves["group"].nunique() > 1)


def churn_rate_bar(table: pd.DataFrame, col: str, overall: float, title: str = "", height: int = 340) -> go.Figure:
    """Bars of churn rate per category with the overall average as a reference line."""
    t = table.copy()
    t[col] = t[col].astype(str)
    fig = go.Figure(go.Bar(
        x=t[col], y=t["churn_rate"], text=[f"{v * 100:.1f}%" for v in t["churn_rate"]], textposition="outside", cliponaxis=False,
        marker=dict(color=t["churn_rate"], colorscale=C.SEQUENTIAL, cmin=0, cmax=max(t["churn_rate"].max(), 0.01), line=dict(width=0)),
        customdata=np.stack([t["customers"], t["churned"], t["share_of_churn"]], axis=-1),
        hovertemplate=("<b>%{x}</b><br>Churn rate: %{y:.1%}<br>Customers: %{customdata[0]:,}<br>"
                       "Churned: %{customdata[1]:,}<br>Share of all churn: %{customdata[2]:.1%}<extra></extra>"),
    ))
    fig.add_hline(y=overall, line=dict(color="#A78BFA", width=1.5, dash="dot"),
                  annotation_text=f"Overall {overall * 100:.1f}%", annotation_position="top right",
                  annotation_font=dict(color="#A78BFA", size=11))
    _pct_axis(fig, "y", [0, max(t["churn_rate"].max() * 1.25, overall * 1.3, 0.05)])
    fig.update_yaxes(title="Churn rate")
    fig.update_xaxes(title="")
    return apply_theme(fig, title or f"Churn rate by {col}", height, legend=False)


def tenure_window_chart(table: pd.DataFrame) -> go.Figure:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=table["label"], y=table["customers"], name="Customers", marker=dict(color="rgba(79,140,255,0.28)"),
                         hovertemplate="%{x} months<br>%{y:,} customers<extra></extra>"), secondary_y=False)
    fig.add_trace(go.Scatter(x=table["label"], y=table["churn_rate"], name="Churn rate", mode="lines+markers",
                             line=dict(color=C.CHURN_COLOR, width=3, shape="spline"), marker=dict(size=7),
                             hovertemplate="%{x} months<br>Churn rate %{y:.1%}<extra></extra>"), secondary_y=True)
    fig.update_yaxes(title="Customers", secondary_y=False, showgrid=False)
    fig.update_yaxes(title="Churn rate", tickformat=".0%", secondary_y=True, rangemode="tozero")
    fig.update_xaxes(title="Tenure window (months)")
    return apply_theme(fig, "Churn over the customer lifetime", 340)


def signup_cohort_chart(table: pd.DataFrame) -> go.Figure:
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=table["month"], y=table["customers"], name="Signups", marker=dict(color="rgba(139,92,246,0.30)")), secondary_y=False)
    fig.add_trace(go.Scatter(x=table["month"], y=table["churn_rate"], name="Churn rate", mode="lines+markers",
                             line=dict(color=C.CHURN_COLOR, width=3, shape="spline")), secondary_y=True)
    fig.update_yaxes(title="Signups", secondary_y=False, showgrid=False)
    fig.update_yaxes(title="Churn rate", tickformat=".0%", secondary_y=True, rangemode="tozero")
    return apply_theme(fig, "Churn rate by signup month (cohorts)", 340)


# ----------------------------------------------------------------------------
# Drivers
# ----------------------------------------------------------------------------
def charges_distribution(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for label, flag, color in [("Retained", 0, C.RETAIN_COLOR), ("Churned", 1, C.CHURN_COLOR)]:
        fig.add_trace(go.Histogram(x=df.loc[df["Churned"] == flag, "MonthlyCharges"], name=label, nbinsx=30, opacity=0.7,
                                   marker=dict(color=color), histnorm="probability",
                                   hovertemplate=C.CURRENCY + "%{x}<br>%{y:.1%} of group<extra>" + label + "</extra>"))
    fig.update_layout(barmode="overlay", bargap=0.03)
    fig.update_xaxes(title=f"Monthly charges ({C.CURRENCY})")
    _pct_axis(fig, "y")
    fig.update_yaxes(title="Share of group")
    return apply_theme(fig, "Monthly charges: retained vs churned", 340)


def heatmap(matrix: pd.DataFrame, title: str) -> go.Figure:
    z = matrix.values
    fig = go.Figure(go.Heatmap(
        z=z, x=[str(c) for c in matrix.columns], y=[str(i) for i in matrix.index], colorscale=C.SEQUENTIAL, zmin=0,
        text=np.where(np.isnan(z), "", np.char.add(np.round(z * 100, 1).astype(str), "%")), texttemplate="%{text}",
        textfont=dict(color="#FFFFFF", size=13), xgap=3, ygap=3, colorbar=dict(tickformat=".0%", thickness=10, len=0.8),
        hovertemplate="%{y} / %{x}<br>Churn rate: %{z:.1%}<extra></extra>",
    ))
    return apply_theme(fig, title, 340, legend=False)


# ----------------------------------------------------------------------------
# Segments & risk
# ----------------------------------------------------------------------------
def segment_bubbles(seg: pd.DataFrame) -> go.Figure:
    fig = go.Figure(go.Scatter(
        x=seg["avg_tenure"], y=seg["avg_monthly"], mode="markers+text", text=seg["Segment"], textposition="top center",
        textfont=dict(color="#E6E9F5", size=11),
        marker=dict(size=seg["customers"], sizemode="area", sizeref=2.0 * seg["customers"].max() / (70 ** 2), sizemin=14,
                    color=seg["churn_rate"], colorscale=C.SEQUENTIAL, cmin=0, cmax=max(seg["churn_rate"].max(), 0.01),
                    line=dict(color="rgba(255,255,255,0.35)", width=1.5), opacity=0.9,
                    colorbar=dict(title="Churn", tickformat=".0%", thickness=10, len=0.8)),
        customdata=np.stack([seg["customers"], seg["churn_rate"], seg["active_mrr"]], axis=-1),
        hovertemplate=("<b>%{text}</b><br>Customers: %{customdata[0]:,}<br>Churn rate: %{customdata[1]:.1%}<br>"
                       "Avg tenure: %{x:.1f} mo<br>Avg bill: " + C.CURRENCY + "%{y:.0f}<br>Active MRR: " + C.CURRENCY + "%{customdata[2]:,.0f}<extra></extra>"),
    ))
    fig.update_xaxes(title="Average tenure (months)", rangemode="tozero")
    fig.update_yaxes(title=f"Average monthly bill ({C.CURRENCY})")
    return apply_theme(fig, "Segment map (bubble size = customers)", 380, legend=False)


def tenure_charge_scatter(df: pd.DataFrame, max_points: int = 1800, seed: int = 7) -> go.Figure:
    sample = df if len(df) <= max_points else df.sample(max_points, random_state=seed)
    fig = go.Figure()
    for label, flag, color in [("Retained", 0, C.RETAIN_COLOR), ("Churned", 1, C.CHURN_COLOR)]:
        part = sample[sample["Churned"] == flag]
        fig.add_trace(go.Scattergl(x=part["tenure"], y=part["MonthlyCharges"], mode="markers", name=label,
                                   marker=dict(size=6, color=color, opacity=0.55),
                                   hovertemplate="Tenure %{x} mo<br>Bill " + C.CURRENCY + "%{y:.0f}<extra>" + label + "</extra>"))
    fig.update_xaxes(title="Tenure (months)")
    fig.update_yaxes(title=f"Monthly charges ({C.CURRENCY})")
    return apply_theme(fig, f"Customers by tenure and bill (sample of {len(sample):,})", 380)


def risk_tier_chart(summary: pd.DataFrame) -> go.Figure:
    fig = go.Figure(go.Bar(
        x=summary["RiskTier"].astype(str), y=summary["monthly_revenue"],
        marker=dict(color=[C.RISK_COLORS[str(t)] for t in summary["RiskTier"]]),
        text=[f"{C.CURRENCY}{v:,.0f}" for v in summary["monthly_revenue"]], textposition="outside", cliponaxis=False,
        customdata=summary["customers"], hovertemplate="<b>%{x} risk</b><br>Active customers: %{customdata:,}<br>Monthly revenue: " + C.CURRENCY + "%{y:,.0f}<extra></extra>",
    ))
    fig.update_yaxes(title=f"Monthly revenue ({C.CURRENCY})", range=[0, summary["monthly_revenue"].max() * 1.18 if len(summary) else 1])
    return apply_theme(fig, "Active monthly revenue by risk tier", 340, legend=False)


def profile_comparison(profile: pd.DataFrame, col: str) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Bar(x=profile[col], y=profile["High-risk"], name="High-risk", marker=dict(color=C.CHURN_COLOR)))
    fig.add_trace(go.Bar(x=profile[col], y=profile["Other active"], name="Other active", marker=dict(color=C.RETAIN_COLOR)))
    fig.update_layout(barmode="group", bargap=0.25)
    _pct_axis(fig, "y")
    fig.update_yaxes(title="Share of group")
    return apply_theme(fig, f"Who are the high-risk customers? ({col})", 340)


# ----------------------------------------------------------------------------
# Model
# ----------------------------------------------------------------------------
def importance_chart(imp: pd.DataFrame, top: int = 10) -> go.Figure:
    t = imp.head(top).iloc[::-1]
    fig = go.Figure(go.Bar(x=t["importance"], y=t["feature"], orientation="h",
                           marker=dict(color=t["importance"], colorscale=C.SEQUENTIAL),
                           error_x=dict(type="data", array=t["std"], color="rgba(255,255,255,0.35)", thickness=1.2),
                           hovertemplate="<b>%{y}</b><br>AUC drop when shuffled: %{x:.3f}<extra></extra>"))
    fig.update_xaxes(title="Drop in ROC-AUC when the feature is shuffled")
    return apply_theme(fig, "What drives the model's predictions", 380, legend=False)


def roc_chart(fpr, tpr, auc: float) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=fpr, y=tpr, mode="lines", name=f"Model (AUC {auc:.3f})", line=dict(color=P["purple"], width=3),
                             fill="tozeroy", fillcolor="rgba(139,92,246,0.12)"))
    fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", name="Random guess", line=dict(color="#8B94B8", dash="dot")))
    fig.update_xaxes(title="False positive rate", range=[0, 1])
    fig.update_yaxes(title="True positive rate (recall)", range=[0, 1.02])
    return apply_theme(fig, "ROC curve", 340)


def confusion_chart(cm: np.ndarray) -> go.Figure:
    labels = ["Retained", "Churned"]
    fig = go.Figure(go.Heatmap(z=cm, x=[f"Predicted {l}" for l in labels], y=[f"Actual {l}" for l in labels], colorscale=C.SEQUENTIAL,
                               text=cm, texttemplate="%{text:,}", textfont=dict(size=18, color="#FFFFFF"), xgap=4, ygap=4,
                               showscale=False, hovertemplate="%{y}, %{x}: %{z:,}<extra></extra>"))
    fig.update_yaxes(autorange="reversed")
    return apply_theme(fig, "Confusion matrix (test set)", 340, legend=False)


def probability_hist(y_true, proba, threshold: float) -> go.Figure:
    fig = go.Figure()
    for label, flag, color in [("Actually retained", 0, C.RETAIN_COLOR), ("Actually churned", 1, C.CHURN_COLOR)]:
        fig.add_trace(go.Histogram(x=np.asarray(proba)[np.asarray(y_true) == flag], name=label, nbinsx=25, opacity=0.7, marker=dict(color=color)))
    fig.update_layout(barmode="overlay")
    fig.add_vline(x=threshold, line=dict(color="#FFFFFF", dash="dash", width=1.5), annotation_text=f"Threshold {threshold:.2f}", annotation_font=dict(size=11))
    fig.update_xaxes(title="Predicted churn probability", range=[0, 1])
    fig.update_yaxes(title="Customers")
    return apply_theme(fig, "Predicted probabilities by actual outcome (test set)", 340)


def gauge(prob: float) -> go.Figure:
    color = C.RISK_COLORS["High"] if prob >= 0.5 else C.RISK_COLORS["Medium"] if prob >= 0.25 else C.RISK_COLORS["Low"]
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=prob * 100, number=dict(suffix="%", font=dict(size=34, color="#FFFFFF")),
        gauge=dict(axis=dict(range=[0, 100], tickcolor="#8B94B8"), bar=dict(color=color, thickness=0.28), bgcolor="rgba(255,255,255,0.04)",
                   borderwidth=0, steps=[dict(range=[0, 25], color="rgba(52,211,153,0.12)"), dict(range=[25, 50], color="rgba(251,191,36,0.12)"),
                                         dict(range=[50, 100], color="rgba(244,114,182,0.14)")]),
    ))
    return apply_theme(fig, "Predicted churn probability", 260, legend=False)

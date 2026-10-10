"""Visual design: global CSS plus small HTML helpers (KPI cards, headers, insight cards)."""
from __future__ import annotations

import html

import streamlit as st

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, .stApp, [data-testid="stSidebar"] { font-family: 'Inter', 'Segoe UI', system-ui, sans-serif; }
.stApp {
  background:
    radial-gradient(1100px 560px at 88% -12%, rgba(139,92,246,0.15), transparent 60%),
    radial-gradient(900px 480px at -6% 8%, rgba(79,140,255,0.10), transparent 55%),
    #0B1020;
}
[data-testid="stHeader"] { background: transparent; }
#MainMenu, footer { visibility: hidden; }
.block-container { padding-top: 1.4rem; padding-bottom: 3rem; max-width: 1400px; }

/* Sidebar */
section[data-testid="stSidebar"] { background: #0D1328; border-right: 1px solid rgba(139,148,255,0.12); }
section[data-testid="stSidebar"] .block-container { padding-top: 1rem; }
.brand { display:flex; align-items:center; gap:10px; margin: 2px 0 12px; }
.brand-logo { width:34px; height:34px; border-radius:10px; display:grid; place-items:center; font-size:18px;
  background: linear-gradient(135deg,#8B5CF6,#4F8CFF); box-shadow: 0 6px 18px -6px rgba(139,92,246,.8); }
.brand-name { font-weight:700; font-size:.95rem; color:#fff; line-height:1.1; }
.brand-tag { font-size:.68rem; color:#8B94B8; letter-spacing:.06em; text-transform:uppercase; }
.side-label { font-size:.68rem; color:#8B94B8; letter-spacing:.09em; text-transform:uppercase; font-weight:600; margin: 14px 0 4px; }

/* Page header */
.page-title { font-size:1.6rem; font-weight:700; color:#fff; letter-spacing:-0.02em; margin:0; }
.page-title span { background: linear-gradient(90deg,#A78BFA,#60A5FA); -webkit-background-clip:text; background-clip:text; color:transparent; }
.page-sub { color:#8B94B8; font-size:.9rem; margin:4px 0 0; max-width: 900px; }
.badge { display:inline-block; padding:3px 10px; border-radius:999px; font-size:.7rem; font-weight:600; letter-spacing:.03em;
  border:1px solid rgba(139,148,255,.3); color:#C4B5FD; background: rgba(139,92,246,.12); margin-right:6px; }
.badge.real { color:#6EE7B7; border-color: rgba(52,211,153,.35); background: rgba(52,211,153,.10); }
.badge.synthetic { color:#FCD34D; border-color: rgba(251,191,36,.4); background: rgba(251,191,36,.10); }
.badge.upload { color:#93C5FD; border-color: rgba(79,140,255,.4); background: rgba(79,140,255,.10); }
.header-row { display:flex; justify-content:space-between; align-items:flex-end; gap:16px; flex-wrap:wrap; margin-bottom: 6px; }

/* KPI cards */
.kpi-grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap:14px; margin: 16px 0 22px; }
.kpi-card { position:relative; overflow:hidden; border-radius:16px; padding:16px 18px 15px;
  background: linear-gradient(160deg, rgba(22,31,64,.96), rgba(17,24,50,.96));
  border:1px solid rgba(139,148,255,.16);
  animation: fadeUp .55s ease both; transition: transform .2s ease, border-color .2s ease, box-shadow .25s ease; }
.kpi-card::before { content:""; position:absolute; left:0; right:0; top:0; height:3px; background: var(--accent, linear-gradient(90deg,#8B5CF6,#4F8CFF)); }
.kpi-card:hover { transform: translateY(-3px); border-color: rgba(139,92,246,.55); box-shadow: 0 12px 30px -14px rgba(139,92,246,.55); }
.kpi-label { font-size:.7rem; text-transform:uppercase; letter-spacing:.09em; color:#8B94B8; font-weight:600; }
.kpi-value { font-size:1.65rem; font-weight:700; color:#fff; margin-top:7px; line-height:1.1; letter-spacing:-0.02em; }
.kpi-sub { font-size:.76rem; color:#8B94B8; margin-top:7px; }
.kpi-sub .up { color:#F472B6; font-weight:600; } .kpi-sub .down { color:#34D399; font-weight:600; }

/* Section titles & cards */
.section-title { font-size:1.02rem; font-weight:600; color:#fff; margin: 22px 0 2px; }
.section-sub { font-size:.82rem; color:#8B94B8; margin: 0 0 10px; }
.note-box { border:1px solid rgba(139,148,255,.18); background: rgba(139,92,246,.07); border-radius:12px; padding:12px 14px; font-size:.85rem; color:#C9D1E8; }
div[data-testid="stPlotlyChart"] { background: rgba(17,24,50,.72); border:1px solid rgba(139,148,255,.13); border-radius:16px; padding:6px 8px; animation: fadeUp .6s ease both; }

/* Insight cards */
.insight { border-radius:14px; padding:15px 18px; margin: 0 0 12px; background: rgba(17,24,50,.8);
  border:1px solid rgba(139,148,255,.14); border-left:4px solid var(--lvl, #8B5CF6); animation: fadeUp .5s ease both; }
.insight h4 { margin:0 0 6px; font-size:.98rem; color:#fff; font-weight:600; }
.insight p { margin:0 0 8px; color:#C9D1E8; font-size:.9rem; line-height:1.55; }
.insight .reco { color:#E6E9F5; font-size:.88rem; }
.insight .reco b { color:#A78BFA; }
.chip { display:inline-block; font-size:.65rem; font-weight:700; letter-spacing:.08em; text-transform:uppercase; padding:2px 8px; border-radius:6px; margin-left:8px; vertical-align:middle;
  color: var(--lvl); border:1px solid var(--lvl); }

/* Streamlit widgets */
.stDownloadButton button, .stButton button { border-radius:10px; border:1px solid rgba(139,92,246,.55);
  background: linear-gradient(135deg, rgba(139,92,246,.28), rgba(79,140,255,.22)); color:#fff; font-weight:600; transition: all .2s ease; }
.stDownloadButton button:hover, .stButton button:hover { border-color:#A78BFA; transform: translateY(-1px); box-shadow: 0 8px 20px -10px rgba(139,92,246,.8); }
button[data-baseweb="tab"] { font-weight:600; }
[data-testid="stDataFrame"] { border:1px solid rgba(139,148,255,.14); border-radius:12px; overflow:hidden; }
[data-testid="stExpander"] { border:1px solid rgba(139,148,255,.14); border-radius:12px; background: rgba(17,24,50,.5); }
hr { border-color: rgba(139,148,255,.12); }

@keyframes fadeUp { from { opacity:0; transform: translateY(8px); } to { opacity:1; transform:none; } }
@media (prefers-reduced-motion: reduce) { .kpi-card, .insight, div[data-testid="stPlotlyChart"] { animation:none; } }
@media (max-width: 768px) {
  .block-container { padding: 1rem .8rem 2.5rem; }
  .kpi-value { font-size:1.35rem; } .page-title { font-size:1.3rem; }
}
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def page_header(title_plain: str, title_accent: str, subtitle: str, source_label: str = "", source_kind: str = "real") -> None:
    badge = f'<span class="badge {source_kind}">{html.escape(source_label)}</span>' if source_label else ""
    st.markdown(
        f'<div class="header-row"><div><p class="page-title">{html.escape(title_plain)} <span>{html.escape(title_accent)}</span></p>'
        f'<p class="page-sub">{html.escape(subtitle)}</p></div><div>{badge}</div></div>',
        unsafe_allow_html=True,
    )


def section(title: str, subtitle: str = "") -> None:
    sub = f'<p class="section-sub">{html.escape(subtitle)}</p>' if subtitle else ""
    st.markdown(f'<p class="section-title">{html.escape(title)}</p>{sub}', unsafe_allow_html=True)


def kpi_cards(cards: list[dict]) -> None:
    """cards: [{label, value, sub, accent?}] -> responsive grid of animated cards."""
    parts = []
    for i, c in enumerate(cards):
        accent = f"--accent:{c['accent']};" if c.get("accent") else ""
        parts.append(
            f'<div class="kpi-card" style="{accent}animation-delay:{i * 70}ms">'
            f'<div class="kpi-label">{html.escape(c["label"])}</div>'
            f'<div class="kpi-value">{html.escape(str(c["value"]))}</div>'
            f'<div class="kpi-sub">{c.get("sub", "")}</div></div>'
        )
    st.markdown('<div class="kpi-grid">' + "".join(parts) + "</div>", unsafe_allow_html=True)


LEVEL_COLORS = {"high": "#F472B6", "medium": "#FBBF24", "low": "#34D399", "info": "#4F8CFF"}
LEVEL_LABELS = {"high": "High priority", "medium": "Watch", "low": "Healthy", "info": "Note"}


def insight_card(item: dict, index: int = 0) -> None:
    lvl = item.get("level", "info")
    color = LEVEL_COLORS.get(lvl, "#8B5CF6")
    st.markdown(
        f'<div class="insight" style="--lvl:{color};animation-delay:{index * 60}ms">'
        f'<h4>{html.escape(item["title"])}<span class="chip">{LEVEL_LABELS.get(lvl, "")}</span></h4>'
        f'<p>{html.escape(item["finding"])}</p>'
        f'<div class="reco"><b>Recommended action:</b> {html.escape(item["recommendation"])}</div></div>',
        unsafe_allow_html=True,
    )


def note(text: str) -> None:
    st.markdown(f'<div class="note-box">{text}</div>', unsafe_allow_html=True)


def show_chart(fig) -> None:
    """Render a Plotly figure full-width without the busy modebar."""
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

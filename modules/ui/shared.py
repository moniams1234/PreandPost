"""shared.py — CSS injection, constants and shared UI helpers."""
from __future__ import annotations

import streamlit as st

BURG = "#6B0000"
ORG = "#FF5A1F"
GRN = "#0FA958"
RED = "#C91818"

LAYOUT = dict(
    paper_bgcolor="white",
    plot_bgcolor="white",
    title_font_color=BURG,
    height=300,
    margin=dict(t=42, b=28, l=12, r=12),
    font=dict(size=10),
)

CSS = """
<style>
[data-testid="stAppViewContainer"]  { background: #F7EFEA; }
[data-testid="stHeader"]            { background: transparent; }
[data-testid="stToolbar"]           { display: none; }
footer                              { visibility: hidden; }
.block-container { padding-top: 1.2rem; padding-bottom: 2rem; }

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #3A0000 0%, #5A0A0A 100%) !important;
    border-right: none !important;
    box-shadow: 4px 0 24px rgba(0,0,0,.35);
    display: block !important;
    visibility: visible !important;
    opacity: 1 !important;
}
[data-testid="stSidebar"] * { visibility: visible !important; color: #F5D9D0; }
[data-testid="stSidebar"] [data-testid="stRadio"] > div { gap: 4px !important; }
[data-testid="stSidebar"] [data-testid="stRadio"] label > div:first-child { display: none !important; }
[data-testid="stSidebar"] [data-testid="stRadio"] label {
    display: flex !important; align-items: center !important;
    width: 100% !important; padding: 10px 14px !important;
    border-radius: 10px !important; font-size: 0.88rem !important;
    font-weight: 500 !important; color: #F5D9D0 !important;
    cursor: pointer !important; transition: background .15s ease !important;
    border: 1px solid transparent !important; margin: 1px 0 !important;
    background: transparent !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
    background: rgba(255,90,31,.22) !important;
    border-color: rgba(255,90,31,.40) !important;
    color: #FFFFFF !important; transform: translateX(4px) !important;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label[aria-checked="true"] {
    background: linear-gradient(90deg, #FF5A1F 0%, #C91818 100%) !important;
    border-color: transparent !important; color: #FFFFFF !important;
    font-weight: 700 !important; box-shadow: 0 3px 12px rgba(255,90,31,.45) !important;
    transform: translateX(4px) !important;
}
[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.12) !important; margin: 10px 0 !important; }
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: #FF8C66 !important; }

h1 { color: #3A0000 !important; font-size: 1.65rem !important; font-weight: 800 !important; }
h2 { color: #6B0000 !important; font-size: 1.25rem !important; }
h3 { color: #6B0000 !important; font-size: 1.05rem !important; }

.stButton > button {
    background: linear-gradient(135deg,#6B0000 0%,#FF5A1F 100%) !important;
    color:#fff !important; border:none !important; border-radius:9px !important;
    padding:9px 24px !important; font-weight:700 !important; font-size:.92rem !important;
    box-shadow: 0 2px 8px rgba(107,0,0,.30) !important;
    transition: all .2s ease !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg,#3A0000 0%,#C91818 100%) !important;
    box-shadow: 0 5px 18px rgba(107,0,0,.50) !important; transform: translateY(-2px) !important;
}
.stDownloadButton > button {
    background: linear-gradient(135deg,#0FA958 0%,#0d8a47 100%) !important;
    color:#fff !important; border:none !important; border-radius:9px !important;
    padding:10px 28px !important; font-weight:700 !important; font-size:1.05rem !important;
    box-shadow: 0 2px 8px rgba(15,169,88,.35) !important;
}
.stDownloadButton > button:hover { filter: brightness(1.08); transform: translateY(-1px); }

.card {
    background: #FFFFFF; border-radius: 14px; padding: 20px 26px;
    box-shadow: 0 2px 16px rgba(107,0,0,.07); margin-bottom: 18px;
    border: 1px solid rgba(107,0,0,.06);
}
.kpi {
    background: #FFF; border-radius: 14px; padding: 18px 14px;
    box-shadow: 0 3px 14px rgba(107,0,0,.10);
    border-left: 4px solid #6B0000; text-align: center;
    margin-bottom: 10px; transition: transform .15s ease;
}
.kpi:hover  { transform: translateY(-2px); }
.kpi.g  { border-left-color: #0FA958; }
.kpi.o  { border-left-color: #FF5A1F; }
.kpi.r  { border-left-color: #C91818; }
.kpi.b  { border-left-color: #1565A0; }
.kpi .v { font-size: 1.45rem; font-weight: 800; color: #3A0000; line-height: 1.1; }
.kpi .l { font-size: .68rem; color: #6B6B6B; text-transform: uppercase;
           letter-spacing: .07em; margin-top: 5px; }
.stitle {
    color: #6B0000; font-size: 1.05rem; font-weight: 700;
    border-bottom: 2px solid #FF5A1F; padding-bottom: 5px; margin: 18px 0 13px;
}
.bok   { display:inline-block; background:#0FA958; color:#fff; border-radius:20px;
         padding:2px 9px; font-size:.72rem; font-weight:700; margin-left:6px; }
.bmiss { display:inline-block; background:#C91818; color:#fff; border-radius:20px;
         padding:2px 9px; font-size:.72rem; font-weight:700; margin-left:6px; }
.stTabs [data-baseweb="tab-list"] {
    background: #3A0000; border-radius: 10px 10px 0 0; gap: 2px; padding: 4px 6px;
}
.stTabs [data-baseweb="tab"] {
    color: #FAE8E0 !important; background: transparent !important;
    border-radius: 8px !important; font-weight: 500 !important; padding: 6px 14px !important;
}
.stTabs [aria-selected="true"] {
    background: #FF5A1F !important; color: #fff !important; font-weight: 700 !important;
}
[data-testid="stFileUploader"] {
    border: 2px dashed rgba(107,0,0,.25) !important;
    border-radius: 10px !important; background: rgba(107,0,0,.02) !important;
}
[data-testid="stFileUploader"]:hover { border-color: #FF5A1F !important; }
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def kpi_card(value: str, label: str, variant: str = "") -> str:
    cls = f"kpi {variant}".strip()
    return f'<div class="{cls}"><div class="v">{value}</div><div class="l">{label}</div></div>'


def section_title(text: str) -> None:
    st.markdown(f'<div class="stitle">{text}</div>', unsafe_allow_html=True)


def badge(ok: bool) -> str:
    if ok:
        return '<span class="bok">✓ OK</span>'
    return '<span class="bmiss">✗ brak</span>'

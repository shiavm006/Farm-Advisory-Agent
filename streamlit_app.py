import os
import streamlit as st
import pandas as pd
import pickle
import numpy as np
import time
import sys
from pathlib import Path
import plotly.graph_objects as go
from datetime import datetime
import streamlit.components.v1 as components

sys.path.insert(0, str(Path(__file__).parent))

# Load .env BEFORE any os.environ.get() checks (e.g. ANTHROPIC_API_KEY).
try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).parent / ".env")
except Exception:
    pass

from report_generator import generate_pdf_report, build_html_report

# ══════════════════════════════════════════════════════════════════════════════
#  PAGE CONFIG
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="CropCast",
    page_icon="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🌾</text></svg>",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════════════════
#  THEME — must be set before CSS
# ══════════════════════════════════════════════════════════════════════════════
if "theme" not in st.session_state:
    st.session_state.theme = "dark"
IS_DARK = st.session_state.theme == "dark"

if IS_DARK:
    _BG = "#080809"
    _BG2 = "#0f0f10"
    _SF = "#0f0f10"
    _SF2 = "#161618"
    _SF3 = "#1c1c1f"
    _BD = "#1f1f22"
    _BD2 = "#2a2a2f"
    _ACC = "#a8e063"
    _ACC2 = "#6abf3a"
    _TX = "#ececec"
    _TX2 = "#aaaaaa"
    _MU = "#555558"
    _LOGO_C = "#060806"
    _SB_BG = "#0b0b0c"  # slightly darker than main bg for sidebar
    _TOGGLE_LABEL = "Light Mode"
    _HERO_GR = "linear-gradient(135deg,#0a1406 0%,#0f1009 40%,#0a0a0b 100%)"
else:
    _BG = "#F5F2EC"
    _BG2 = "#EDE9E1"
    _SF = "#FFFFFF"
    _SF2 = "#F2EEE7"
    _SF3 = "#E8E4DC"
    _BD = "#DDD8CF"
    _BD2 = "#BBBAAF"
    _ACC = "#2C7A18"
    _ACC2 = "#4CA030"
    _TX = "#1A201C"
    _TX2 = "#4A5E4C"
    _MU = "#7A8A7A"
    _LOGO_C = "#FFFFFF"
    _SB_BG = "#EDE9E1"
    _TOGGLE_LABEL = "Dark Mode"
    _HERO_GR = "linear-gradient(135deg,#EAF5E6 0%,#D3ECCB 40%,#E8F5E0 100%)"

# ══════════════════════════════════════════════════════════════════════════════
#  GLOBAL CSS  — dark/light, editorial, mono-accented
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(
    f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:ital,wght@0,300;0,400;0,500;1,300&family=Outfit:wght@300;400;500;600;700&display=swap');

/* ── Tokens ── */
:root {{
    --bg:        {_BG};
    --surface:   {_SF};
    --surface2:  {_SF2};
    --surface3:  {_SF3};
    --border:    {_BD};
    --border2:   {_BD2};
    --accent:    {_ACC};
    --accent2:   {_ACC2};
    --accent-bg: rgba(168,224,99,0.06);
    --text:      {_TX};
    --text2:     {_TX2};
    --muted:     {_MU};
    --danger:    #ff6b6b;
    --r:         8px;
    --sidebar-w: 220px;
    --header-h:  0px;
}}

/* ── Reset & base ── */
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{ background: var(--bg) !important; transition: background .35s ease !important; }}
[class*="css"], .stApp {{ font-family: 'Outfit', sans-serif !important; background: var(--bg) !important; color: var(--text) !important; transition: background .35s ease, color .35s ease !important; }}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header, [data-testid="stDeployButton"], [data-testid="stToolbar"] {{ display: none !important; }}
/* Hide BOTH sidebar toggle controls — sidebar is permanently open */
[data-testid="stSidebarCollapseButton"] {{ display: none !important; }}
[data-testid="collapsedControl"] {{ display: none !important; }}

/* ── Main content area ── */
.main .block-container {{
    padding: 0 !important;
    margin: 0 !important;
    max-width: 100% !important;
}}
[data-testid="stAppViewContainer"], [data-testid="stAppViewBlockContainer"],
[data-testid="stMainBlockContainer"], .main, .stApp {{
    background: var(--bg) !important;
    transition: background .35s ease !important;
}}

/* ── Sidebar — always visible, force override Streamlit collapse transform ── */
section[data-testid="stSidebar"] {{
    background: {_SB_BG} !important;
    border-right: 1px solid var(--border) !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;
    transition: background .35s ease !important;
    transform: none !important;
    left: 0 !important;
    visibility: visible !important;
    display: flex !important;
}}
/* Override any collapsed-state transforms Streamlit applies */
section[data-testid="stSidebar"][aria-expanded="false"] {{
    transform: none !important;
    visibility: visible !important;
    display: flex !important;
}}
section[data-testid="stSidebar"] > div:first-child {{
    padding: 0 !important;
    height: 100vh !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;
    display: flex !important;
    flex-direction: column !important;
}}
section[data-testid="stSidebarContent"] {{
    padding: 0 !important;
    flex: 1 !important;
    display: flex !important;
    flex-direction: column !important;
    overflow-y: auto !important;
    overflow-x: hidden !important;
    scrollbar-width: thin;
    scrollbar-color: {_ACC}80 transparent;
}}
section[data-testid="stSidebarContent"]::-webkit-scrollbar {{
    width: 3px;
}}
section[data-testid="stSidebarContent"]::-webkit-scrollbar-track {{
    background: transparent;
}}
section[data-testid="stSidebarContent"]::-webkit-scrollbar-thumb {{
    background: {_ACC}66;
    border-radius: 10px;
}}
section[data-testid="stSidebarContent"]::-webkit-scrollbar-thumb:hover {{
    background: {_ACC}b3;
}}
/* Remove Streamlit's default sidebar inner padding wrapper */
section[data-testid="stSidebar"] .block-container {{
    padding: 0 !important;
    flex: 1 !important;
    display: flex !important;
    flex-direction: column !important;
    overflow: visible !important;
}}
/* Footer always at bottom */
.sbft {{ margin-top: auto !important; }}

/* ── Slider — clean minimal track + thumb ── */
div[data-testid="stSlider"] label {{
    font-size: .62rem !important; letter-spacing: .12em !important;
    text-transform: uppercase !important; color: var(--muted) !important;
    font-weight: 500 !important; font-family: 'DM Mono', monospace !important;
    margin-bottom: 6px !important;
}}
/* Track background */
div[data-baseweb="slider"] > div > div:first-child > div:first-child {{
    background: var(--border) !important;
    height: 3px !important;
    border-radius: 100px !important;
}}
/* Filled portion */
div[data-baseweb="slider"] div[role="progressbar"] {{
    background: var(--accent) !important;
    border-radius: 100px !important;
}}
/* Thumb */
div[data-baseweb="slider"] div[role="slider"] {{
    background: var(--accent) !important;
    border: 2px solid var(--bg) !important;
    box-shadow: 0 0 0 2px var(--accent) !important;
    width: 16px !important; height: 16px !important;
    border-radius: 50% !important;
    transition: box-shadow .18s ease, transform .15s ease !important;
}}
div[data-baseweb="slider"] div[role="slider"]:hover {{
    box-shadow: 0 0 0 5px {_ACC}44 !important;
    transform: scale(1.15) !important;
}}
/* Value tooltip */
div[data-baseweb="slider"] [data-testid="stThumbValue"] {{
    background: var(--surface3) !important;
    border: 1px solid var(--border2) !important;
    border-radius: 4px !important;
    color: var(--accent) !important;
    font-family: 'DM Mono', monospace !important;
    font-size: .65rem !important;
    padding: 2px 7px !important;
    letter-spacing: .04em !important;
}}
/* Tick bar labels */
[data-testid="stTickBarMin"], [data-testid="stTickBarMax"] {{
    color: var(--muted) !important; font-size: .58rem !important;
    font-family: 'DM Mono', monospace !important;
}}

/* ── Select ── */
[data-testid="stSelectbox"] > label {{
    font-family: 'DM Mono', monospace !important;
    font-size: .62rem !important; color: var(--muted) !important;
    text-transform: uppercase !important; letter-spacing: .12em !important; font-weight: 500 !important;
}}
div[data-baseweb="select"] > div {{
    background: var(--surface2) !important; border: 1px solid var(--border) !important;
    border-radius: var(--r) !important; color: var(--text) !important;
    font-size: .88rem !important; min-height: 42px !important;
    transition: border-color .18s ease, box-shadow .18s ease !important;
}}
div[data-baseweb="select"] > div:hover {{ border-color: var(--border2) !important; }}
div[data-baseweb="select"] > div:focus-within {{
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px {_ACC}22 !important;
}}
div[data-baseweb="select"] svg {{ fill: var(--muted) !important; }}
[data-baseweb="popover"],[data-baseweb="menu"] {{
    background: var(--surface) !important; border: 1px solid var(--border) !important;
    border-radius: var(--r) !important;
}}
[data-baseweb="menu"] li {{
    background: var(--surface) !important; color: var(--text) !important;
    font-size: .88rem !important; padding: 10px 16px !important;
    transition: background .12s ease !important;
}}
[data-baseweb="menu"] li:hover {{ background: var(--surface2) !important; }}
[data-baseweb="menu"] li[aria-selected="true"] {{ color: var(--accent) !important; }}

/* ── Number input ── */
[data-testid="stNumberInput"] > label {{
    font-family: 'DM Mono', monospace !important;
    font-size: .62rem !important; color: var(--muted) !important;
    text-transform: uppercase !important; letter-spacing: .12em !important; font-weight: 500 !important;
}}
div[data-testid="stNumberInput"] input {{
    background: var(--surface2) !important; border: 1px solid var(--border) !important;
    border-radius: var(--r) !important; color: var(--text) !important;
    font-size: .88rem !important; height: 42px !important;
    transition: border-color .18s ease, box-shadow .18s ease !important;
}}
div[data-testid="stNumberInput"] input:focus {{
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px {_ACC}22 !important; outline: none !important;
}}

/* ── Default button: reset so .cta and .btn-ghost can own their zones ── */
.stButton > button {{
    background: var(--surface2) !important;
    color: var(--text) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--r) !important;
    font-family: 'DM Mono', monospace !important;
    font-size: .78rem !important; font-weight: 400 !important;
    letter-spacing: .06em !important;
    padding: 14px 0 !important; width: 100% !important;
    transition: border-color .2s ease, color .2s ease, transform .15s ease !important;
    box-shadow: none !important;
}}
.stButton > button:hover {{
    border-color: var(--border2) !important; color: var(--text) !important;
    transform: translateY(-1px) !important;
}}
.stButton > button:active {{ transform: translateY(0) !important; }}

/* Download button */
.stDownloadButton > button {{
    background: transparent !important; color: var(--text2) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--r) !important;
    font-family: 'DM Mono', monospace !important;
    font-size: .75rem !important; font-weight: 400 !important;
    letter-spacing: .08em !important; text-transform: uppercase !important;
    padding: 11px 20px !important; width: auto !important;
    transition: border-color .2s ease, color .2s ease, box-shadow .2s ease, transform .15s ease !important;
}}
.stDownloadButton > button:hover {{
    border-color: var(--accent) !important; color: var(--accent) !important;
    box-shadow: 0 0 0 3px {_ACC}18 !important; transform: translateY(-1px) !important;
}}

/* ── Tabs ── */
[data-testid="stTabs"] [role="tablist"] {{
    background: var(--surface) !important;
    border-bottom: 1px solid var(--border) !important;
    gap: 0 !important; padding: 0 !important;
}}
[data-testid="stTabs"] [role="tab"] {{
    font-family: 'DM Mono', monospace !important;
    font-size: .72rem !important; color: var(--muted) !important;
    padding: 12px 20px !important; border-radius: 0 !important;
    border-bottom: 2px solid transparent !important;
    transition: color .2s, border-color .2s !important; letter-spacing: .06em !important;
}}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {{
    color: var(--accent) !important;
    border-bottom: 2px solid var(--accent) !important;
    background: transparent !important;
}}
[data-testid="stTabs"] [role="tab"]:hover {{ color: var(--text2) !important; }}
[data-testid="stTabs"] [role="tabpanel"] {{ padding: 20px 0 0 0 !important; }}

/* ── Plotly charts ── */
.stPlotlyChart {{ border-radius: var(--r); overflow: hidden; }}
.js-plotly-plot .plotly {{ background: transparent !important; }}

/* ── Animations ── */
@keyframes fadeUp {{
    from {{ opacity: 0; transform: translateY(16px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
}}
@keyframes fadeIn {{
    from {{ opacity: 0; }}
    to   {{ opacity: 1; }}
}}
@keyframes pulse {{
    0%, 100% {{ opacity: 1; }}
    50%       {{ opacity: 0.4; }}
}}
@keyframes spin {{
    to {{ transform: rotate(360deg); }}
}}
@keyframes dash {{
    to {{ stroke-dashoffset: 0; }}
}}
@keyframes countUp {{
    from {{ opacity: 0; transform: scale(0.85); }}
    to   {{ opacity: 1; transform: scale(1); }}
}}
@keyframes barGrow {{
    from {{ width: 0 !important; }}
    to   {{ width: var(--bar-w); }}
}}
.animate-fade-up  {{ animation: fadeUp 0.5s ease forwards; }}
.animate-fade-in  {{ animation: fadeIn 0.4s ease forwards; }}
.animate-count-up {{ animation: countUp 0.6s cubic-bezier(0.34,1.56,0.64,1) forwards; }}
</style>
""",
    unsafe_allow_html=True,
)

# ── Static CSS (preloader, page components — no dynamic tokens) ──
st.markdown(
    """
<style>
/* ── Preloader overlay ── */
.preloader {
    position: fixed; inset: 0; z-index: 9999;
    background: var(--bg);
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    gap: 24px;
    animation: fadeIn 0.3s ease;
}
.preloader-logo {
    font-family: 'DM Mono', monospace;
    font-size: 28px;
    color: var(--accent);
    letter-spacing: -1px;
}
.preloader-logo span { color: var(--muted); }
.preloader-bar-track {
    width: 160px; height: 2px;
    background: var(--surface3);
    border-radius: 2px;
    overflow: hidden;
}
.preloader-bar-fill {
    height: 100%;
    background: var(--accent);
    border-radius: 2px;
    animation: preload-progress 1.4s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}
@keyframes preload-progress {
    0%   { width: 0%; }
    40%  { width: 45%; }
    70%  { width: 72%; }
    90%  { width: 88%; }
    100% { width: 100%; }
}
.preloader-status {
    font-family: 'DM Mono', monospace;
    font-size: 11px;
    color: var(--muted);
    letter-spacing: 1.2px;
    text-transform: uppercase;
    animation: pulse 1.5s ease infinite;
}

/* ── Prediction loader ── */
.pred-loader {
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    gap: 20px;
    padding: 60px 0;
    animation: fadeIn 0.3s ease;
}
.pred-loader-ring {
    width: 52px; height: 52px;
    border: 2px solid var(--surface3);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.9s linear infinite;
}
.pred-loader-text {
    font-family: 'DM Mono', monospace;
    font-size: 12px; color: var(--muted);
    letter-spacing: 1.2px;
    text-transform: uppercase;
    animation: pulse 1.8s ease infinite;
}

/* ── Sidebar nav items ── */
.sb-brand {
    padding: 28px 20px 20px;
    border-bottom: 1px solid var(--border);
}
.sb-brand-name {
    font-family: 'DM Mono', monospace;
    font-size: 17px;
    font-weight: 500;
    color: var(--accent);
    letter-spacing: -0.5px;
    line-height: 1;
}
.sb-brand-sub {
    font-family: 'DM Mono', monospace;
    font-size: 10px;
    color: var(--muted);
    letter-spacing: 0.8px;
    margin-top: 4px;
    text-transform: uppercase;
}
.sb-nav-section {
    padding: 18px 16px 6px;
    font-family: 'DM Mono', monospace;
    font-size: 9px;
    color: var(--muted);
    letter-spacing: 1.6px;
    text-transform: uppercase;
}
.sb-nav-item {
    display: flex; align-items: center; gap: 10px;
    padding: 10px 16px;
    margin: 2px 8px;
    border-radius: 6px;
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
    font-family: 'Outfit', sans-serif;
    font-size: 13.5px;
    font-weight: 400;
    color: var(--text2);
    text-decoration: none;
}
.sb-nav-item:hover { background: var(--surface2); color: var(--text); }
.sb-nav-item.active {
    background: var(--accent-bg);
    color: var(--accent);
    border: 1px solid rgba(168,224,99,0.15);
}
.sb-nav-item.active .sb-icon { color: var(--accent); }
.sb-icon { font-size: 14px; opacity: 0.7; line-height: 1; }
.sb-status {
    position: absolute; bottom: 0; left: 0; right: 0;
    padding: 16px;
    border-top: 1px solid var(--border);
    font-family: 'DM Mono', monospace;
    font-size: 10px;
    color: var(--muted);
}
.sb-dot {
    display: inline-block;
    width: 6px; height: 6px;
    border-radius: 50%;
    background: var(--accent);
    margin-right: 6px;
    animation: pulse 2s ease infinite;
}

/* ── Page header ── */
.page-header {
    padding: 32px 36px 0;
    animation: fadeUp 0.4s ease both;
}
.page-title {
    font-size: 24px; font-weight: 600;
    color: var(--text);
    letter-spacing: -0.6px;
    line-height: 1.2;
}
.page-sub {
    font-family: 'DM Mono', monospace;
    font-size: 12px;
    color: var(--muted);
    margin-top: 5px;
    letter-spacing: 0.3px;
}
.page-content { padding: 24px 36px; }

/* ── Form card ── */
.form-section-label {
    font-family: 'DM Mono', monospace;
    font-size: 10px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 1.3px;
    margin-bottom: 14px;
    display: flex; align-items: center; gap: 8px;
}
.form-section-label::after {
    content: '';
    flex: 1; height: 1px;
    background: var(--border);
}

/* ── Result hero ── */
.result-hero {
    background: linear-gradient(135deg, #0a1406 0%, #0f1009 50%, #0a0a0b 100%);
    border: 1px solid rgba(168,224,99,0.2);
    border-radius: 12px;
    padding: 36px;
    text-align: center;
    position: relative;
    overflow: hidden;
    animation: fadeUp 0.5s ease both;
}
.result-hero::before {
    content: '';
    position: absolute;
    top: -40%; left: 50%; transform: translateX(-50%);
    width: 300px; height: 300px;
    background: radial-gradient(circle, rgba(168,224,99,0.06) 0%, transparent 70%);
    pointer-events: none;
}
.hero-label {
    font-family: 'DM Mono', monospace;
    font-size: 10px; color: var(--accent);
    letter-spacing: 2.5px; text-transform: uppercase;
    margin-bottom: 12px;
}
.hero-number {
    font-family: 'Outfit', sans-serif;
    font-size: 72px; font-weight: 700;
    color: var(--accent);
    letter-spacing: -4px; line-height: 1;
    animation: countUp 0.7s cubic-bezier(0.34,1.56,0.64,1) both 0.1s;
}
.hero-unit {
    font-family: 'DM Mono', monospace;
    font-size: 12px; color: var(--muted);
    margin-top: 8px; letter-spacing: 0.5px;
}
.hero-badge {
    display: inline-flex; align-items: center; gap: 6px;
    margin-top: 14px;
    padding: 5px 14px;
    background: rgba(168,224,99,0.1);
    border: 1px solid rgba(168,224,99,0.2);
    border-radius: 20px;
    font-family: 'DM Mono', monospace;
    font-size: 11px; color: var(--accent);
}

/* ── Metric cards ── */
.metric-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin: 16px 0;
}
.metric-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px 18px;
    transition: border-color 0.2s, transform 0.2s;
    animation: fadeUp 0.45s ease both;
}
.metric-card:hover { border-color: var(--border2); transform: translateY(-2px); }
.metric-label {
    font-family: 'DM Mono', monospace;
    font-size: 10px; color: var(--muted);
    text-transform: uppercase; letter-spacing: 1px;
    margin-bottom: 6px;
}
.metric-value {
    font-family: 'Outfit', sans-serif;
    font-size: 22px; font-weight: 700;
    color: var(--accent); letter-spacing: -1px; line-height: 1;
}
.metric-unit {
    font-family: 'DM Mono', monospace;
    font-size: 10px; color: var(--muted);
    margin-top: 3px;
}
.metric-card:nth-child(2) { animation-delay: 0.08s; }
.metric-card:nth-child(3) { animation-delay: 0.16s; }
.metric-card:nth-child(4) { animation-delay: 0.24s; }

/* ── Info row ── */
.info-row {
    display: flex; justify-content: space-between;
    align-items: center;
    padding: 11px 0;
    border-bottom: 1px solid var(--border);
    transition: background 0.15s;
}
.info-row:last-child { border-bottom: none; }
.info-row:hover { background: rgba(255,255,255,0.015); margin: 0 -8px; padding: 11px 8px; }
.info-key { font-family: 'DM Mono', monospace; font-size: 11.5px; color: var(--muted); }
.info-val { font-size: 13.5px; font-weight: 500; color: var(--text); }

/* ── Divider ── */
.divider { height: 1px; background: var(--border); margin: 24px 0; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--surface3); border-radius: 4px; }

/* ════════════════════════════════════════════════════
   RESPONSIVE — mobile-first overrides
   ════════════════════════════════════════════════════ */

/* Tablet — ≤ 1100px */
@media (max-width: 1100px) {
    .pg  { padding: 32px 32px 24px; }
    .sub { max-width: 100%; }
    .mgrid  { grid-template-columns: repeat(2, 1fr); }
    .metric-row { grid-template-columns: repeat(2, 1fr); }
    .abg { grid-template-columns: 1fr 1fr; }
    .ttl { font-size: 1.65rem; }
    .hn  { font-size: 4rem; }
    .fbn { width: 100px; }
}

/* Phablet — ≤ 768px */
@media (max-width: 768px) {
    :root { --sidebar-w: 0px !important; }

    /* Shrink sidebar to a top strip on small screens */
    section[data-testid="stSidebar"] {
        width: 100% !important; min-width: 100% !important; max-width: 100% !important;
        height: auto !important; position: relative !important;
        border-right: none !important; border-bottom: 1px solid var(--border) !important;
        overflow: visible !important;
    }
    section[data-testid="stSidebar"] > div:first-child {
        height: auto !important; flex-direction: row !important; flex-wrap: wrap !important;
    }

    /* Page padding */
    .pg  { padding: 22px 18px 18px; }
    .page-header { padding: 20px 18px 0; }
    .page-content { padding: 16px 18px; }

    /* Typography */
    .ttl { font-size: 1.35rem; }
    .hn  { font-size: 3rem; letter-spacing: -.04em; }
    .sub { font-size: .76rem; }

    /* Grids → 2 col */
    .mgrid  { grid-template-columns: repeat(2, 1fr); gap: 8px; }
    .metric-row { grid-template-columns: repeat(2, 1fr); gap: 8px; }
    .abg    { grid-template-columns: 1fr; gap: 8px; }

    /* Chips */
    .chip   { padding: 14px 12px; }
    .cv     { font-size: 1.25rem; }

    /* Feature bars */
    .fbn { width: 80px; font-size: 9px; }

    /* Result hero — smaller */
    .result-hero { padding: 24px 18px; }
    .hero-number { font-size: 52px; }

    /* Hero card */
    .hero { padding: 28px 18px; }

    /* Cards */
    .card { padding: 16px 14px; }
}

/* Mobile — ≤ 480px */
@media (max-width: 480px) {
    .pg  { padding: 18px 12px 14px; }
    .page-header { padding: 16px 12px 0; }
    .page-content { padding: 14px 12px; }

    .ttl { font-size: 1.15rem; }
    .hn  { font-size: 2.4rem; }
    .cv  { font-size: 1.1rem; }

    /* Single column */
    .mgrid  { grid-template-columns: 1fr; gap: 8px; }
    .metric-row { grid-template-columns: 1fr; gap: 8px; }
    .abg    { grid-template-columns: 1fr; }

    /* Feature bars */
    .fbn { width: 70px; font-size: 8.5px; }
    .fbp { width: 26px; font-size: 9px; }

    /* Insights stats: 2 col instead of 4 */
    [data-testid="stHorizontalBlock"]:has(.istat) {
        flex-wrap: wrap !important;
    }

    /* Reduce CTA padding slightly */
    .cta div[data-testid="stButton"] > button { padding: 16px 0 !important; }
}

/* ── Sidebar active nav item ── */
.sb-nav-active > button {
    background: rgba(168,224,99,0.08) !important;
    color: var(--accent) !important;
    border-left: 2px solid var(--accent) !important;
    border-radius: 0 6px 6px 0 !important;
}

/* ── Insights page ── */
.istat {
    text-align: center;
    padding: 22px 16px 18px;
    border-top: 2px solid var(--accent);
}
.istat-val {
    display: block;
    font-family: 'Outfit', sans-serif;
    font-size: 1.9rem; font-weight: 700;
    color: var(--accent); letter-spacing: -0.04em;
    line-height: 1; margin-bottom: 6px;
    animation: countUp 0.55s cubic-bezier(0.22,1,0.36,1) both;
}
.istat-lbl {
    font-family: 'DM Mono', monospace;
    font-size: 9px; letter-spacing: 0.18em;
    text-transform: uppercase; color: var(--muted); margin-bottom: 4px;
}
.istat-sub { font-size: 11px; color: var(--text2); line-height: 1.3; }

/* ── Config rows ── */
.cfg-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 9px 0; border-bottom: 1px solid var(--border);
    transition: background 0.15s;
}
.cfg-row:last-of-type { border-bottom: none; }
.cfg-row:hover { background: rgba(168,224,99,0.03); margin: 0 -8px; padding: 9px 8px; }
.cfg-k { font-family: 'DM Mono', monospace; font-size: 10.5px; color: var(--muted); }
.cfg-v { font-family: 'DM Mono', monospace; font-size: 11px; color: var(--text); font-weight: 500; }

/* ── Feature bars ── */
.fbr { display: flex; align-items: center; gap: 10px; margin-bottom: 9px; }
.fbn { width: 120px; font-family: 'DM Mono', monospace; font-size: 10.5px; color: var(--muted); text-align: right; flex-shrink: 0; }
.fbt { flex: 1; height: 3px; background: var(--surface3); border-radius: 2px; overflow: hidden; }
.fbf { height: 100%; background: linear-gradient(90deg, var(--accent), var(--accent2)); border-radius: 2px; animation: barGrow 0.85s cubic-bezier(0.22,1,0.36,1) both; }
.fbp { width: 32px; font-family: 'DM Mono', monospace; font-size: 10px; color: var(--accent); font-weight: 500; text-align: right; }

/* ── Performance bars ── */
.perf-row { display: flex; align-items: center; gap: 12px; padding: 9px 0; border-bottom: 1px solid var(--border); }
.perf-row:last-child { border-bottom: none; }
.perf-label { font-size: 11.5px; color: var(--text2); min-width: 80px; }
.perf-bar-wrap { flex: 1; height: 6px; background: var(--surface3); border-radius: 4px; overflow: hidden; }
.perf-bar { height: 100%; border-radius: 4px; animation: barGrow 0.9s cubic-bezier(0.22,1,0.36,1) both; background: linear-gradient(90deg, var(--accent2), var(--accent)); }
.perf-val { font-family: 'DM Mono', monospace; font-size: 11px; color: var(--accent); min-width: 40px; text-align: right; }

/* ── About page grid ── */
.abg { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 20px; }
.abt {
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--r); padding: 20px;
    transition: border-color 0.2s, transform 0.2s;
    animation: fadeUp 0.4s cubic-bezier(0.22,1,0.36,1) both;
}
.abt:hover { border-color: var(--accent); transform: translateY(-2px); }
.abt:nth-child(1) { animation-delay: 0.04s; } .abt:nth-child(2) { animation-delay: 0.10s; }
.abt:nth-child(3) { animation-delay: 0.16s; } .abt:nth-child(4) { animation-delay: 0.22s; }
.abl { font-family: 'DM Mono', monospace; font-size: 9px; letter-spacing: 0.18em; text-transform: uppercase; color: var(--accent); margin-bottom: 6px; }
.abv { font-family: 'Outfit', sans-serif; font-size: 1.5rem; font-weight: 600; color: var(--text); }
.abd { font-size: 12px; color: var(--muted); margin-top: 4px; line-height: 1.5; font-weight: 300; }

/* ── Model status badge ── */
.model-badge {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 4px 11px; border-radius: 100px;
    font-family: 'DM Mono', monospace; font-size: 10px; letter-spacing: 0.08em; text-transform: uppercase;
}
.badge-ok  { background: rgba(168,224,99,.1); color: var(--accent); border: 1px solid var(--accent); }
.badge-err { background: rgba(255,107,107,.1); color: #ff6b6b; border: 1px solid #ff6b6b; }
.badge-load{ background: rgba(85,85,88,.1);    color: var(--muted); border: 1px solid var(--border); }
.badge-dot { width: 5px; height: 5px; border-radius: 50%; background: currentColor; flex-shrink: 0; animation: pulse 2s ease infinite; }

/* ── Sidebar footer ── */
.sbft { padding: 13px 20px; border-top: 1px solid var(--border); font-family: 'DM Mono', monospace; font-size: 9px; color: var(--muted); letter-spacing: 0.06em; line-height: 1.75; margin-top: auto; }

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
/* ── Page wrapper (test.py vocabulary) ── */
@keyframes chLine  { from { width: 0; opacity: 0; } to { width: 100%; opacity: 1; } }
@keyframes dvDraw  { from { transform: scaleX(0); transform-origin: left; } to { transform: scaleX(1); transform-origin: left; } }
@keyframes pgIn    { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
@keyframes slideLeft { from { opacity: 0; transform: translateX(-14px); } to { opacity: 1; transform: none; } }

.pg  { padding: 44px 56px 36px; animation: pgIn .38s cubic-bezier(.22,1,.36,1) both; }
.ey  { font-size: .57rem; letter-spacing: .3em; text-transform: uppercase; color: var(--accent); margin-bottom: 8px; animation: slideLeft .4s ease .05s both; }
.ttl { font-family: 'Outfit', sans-serif; font-size: 2rem; font-weight: 600; color: var(--text); letter-spacing: -.025em; line-height: 1.1; margin-bottom: 8px; animation: fadeUp .42s cubic-bezier(.22,1,.36,1) .1s both; }
.sub { font-size: .82rem; color: var(--muted); font-weight: 300; line-height: 1.65; max-width: 480px; margin-bottom: 32px; animation: fadeUp .42s cubic-bezier(.22,1,.36,1) .18s both; }

/* ── Card / section container ── */
.card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--r); padding: 22px 24px; margin-bottom: 10px; transition: border-color .2s ease; }
.card:hover { border-color: var(--border2); }
.ch {
    font-size: .57rem; letter-spacing: .22em; text-transform: uppercase;
    color: var(--muted); padding-bottom: 14px; margin-bottom: 16px;
    display: flex; align-items: center; gap: 8px; position: relative;
}
.ch::after { content: ''; position: absolute; bottom: 0; left: 0; height: 1px; width: 0; background: var(--border); animation: chLine .6s cubic-bezier(.22,1,.36,1) .25s both; }

/* ── Animated divider ── */
.dv { height: 1px; background: transparent; margin: 20px 0; position: relative; }
.dv::after { content: ''; position: absolute; top: 0; left: 0; height: 1px; width: 100%; background: var(--border); animation: dvDraw .5s cubic-bezier(.22,1,.36,1) both; }

/* ── Metric chips ── */
.mgrid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 12px; }
.chip {
    background: var(--surface); border: 1px solid var(--border); border-radius: var(--r);
    padding: 18px 16px; transition: border-color .2s ease, transform .2s ease;
    animation: fadeUp .45s cubic-bezier(.22,1,.36,1) both;
}
.chip:hover { border-color: var(--accent); transform: translateY(-3px); }
.chip:nth-child(1) { animation-delay: .06s; } .chip:nth-child(2) { animation-delay: .12s; }
.chip:nth-child(3) { animation-delay: .18s; } .chip:nth-child(4) { animation-delay: .24s; }
.cl { font-size: .55rem; letter-spacing: .18em; text-transform: uppercase; color: var(--muted); margin-bottom: 6px; }
.cv { font-family: 'Outfit', sans-serif; font-size: 1.55rem; font-weight: 600; color: var(--text); line-height: 1.1; animation: countUp .5s cubic-bezier(.22,1,.36,1) .15s both; }
.cs { font-size: .58rem; color: var(--muted); margin-top: 2px; }
</style>
""",
    unsafe_allow_html=True,
)

# ── Dynamic CSS (hero gradient, button shimmer, nav-on active tinting) ──
st.markdown(
    f"""
<style>
/* ── Yield hero block ── */
.hero {{
    background: {_HERO_GR};
    border: 1px solid var(--border); border-radius: var(--r);
    padding: 44px 32px; text-align: center; position: relative; overflow: hidden;
    animation: fadeUp .65s cubic-bezier(.22,1,.36,1) both;
    transition: border-color .2s ease;
}}
.hero:hover {{ border-color: {_ACC}4d; }}
.hb  {{ font-size: .55rem; letter-spacing: .28em; text-transform: uppercase; color: var(--muted); margin-bottom: 12px; }}
.hn  {{ font-family: 'Outfit', sans-serif; font-size: 5rem; font-weight: 700; color: {_ACC2}; line-height: 1; letter-spacing: -.04em; animation: countUp .7s cubic-bezier(.22,1,.36,1) .2s both; }}
.hu  {{ font-size: .58rem; letter-spacing: .24em; text-transform: uppercase; color: var(--muted); margin-top: 8px; }}
.hbd {{ display: inline-block; margin-top: 16px; padding: 5px 16px; border-radius: 100px; font-size: .58rem; letter-spacing: .16em; text-transform: uppercase; border: 1px solid {_ACC}; color: {_ACC}; background: {_ACC}12; animation: countUp .5s cubic-bezier(.22,1,.36,1) .4s both; }}

/* ── Ghost / outline button wrapper ── */
.btn-ghost div[data-testid="stButton"] > button,
.btn-ghost div[data-testid="stDownloadButton"] > button {{
    background: transparent !important; color: var(--text2) !important;
    border: 1px solid var(--border2) !important; border-radius: 5px !important;
    padding: 14px 28px !important;
    font-family: 'DM Mono', monospace !important; font-size: .75rem !important;
    font-weight: 400 !important; letter-spacing: .08em !important;
    text-transform: uppercase !important; width: auto !important;
    position: relative !important; overflow: hidden !important;
    transition: border-color .2s ease, color .2s ease, box-shadow .2s ease, transform .15s ease !important;
}}
.btn-ghost div[data-testid="stButton"] > button::after,
.btn-ghost div[data-testid="stDownloadButton"] > button::after {{
    content: '' !important; position: absolute !important; inset: 0 !important;
    background: linear-gradient(110deg,transparent 25%,{_ACC}14 50%,transparent 75%) !important;
    transform: translateX(-120%) !important;
    transition: transform .5s ease !important; pointer-events: none !important;
}}
.btn-ghost div[data-testid="stButton"] > button:hover::after,
.btn-ghost div[data-testid="stDownloadButton"] > button:hover::after {{
    transform: translateX(120%) !important;
}}
.btn-ghost div[data-testid="stButton"] > button:hover,
.btn-ghost div[data-testid="stDownloadButton"] > button:hover {{
    border-color: var(--accent) !important; color: var(--accent) !important;
    box-shadow: 0 0 0 3px {_ACC}1a !important; transform: translateY(-1px) !important;
}}
.btn-ghost div[data-testid="stButton"] > button:active,
.btn-ghost div[data-testid="stDownloadButton"] > button:active {{
    transform: translateY(0) !important;
    box-shadow: 0 0 0 2px {_ACC}20 !important;
}}

/* ── CTA button wrapper (green filled, pulse glow) ── */
/* ── CTA button — flex layout so icon+text render inline ── */
.cta div[data-testid="stButton"] > button {{
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 12px !important;
}}
/* Static right-arrow icon injected before text via ::after (shimmer lives on ::before) */
.cta div[data-testid="stButton"] > button::after {{
    content: '' !important;
    display: inline-block !important;
    width: 18px !important; height: 18px !important;
    background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23060806' stroke-width='2.4' stroke-linecap='round' stroke-linejoin='round'%3E%3Cline x1='5' y1='12' x2='19' y2='12'/%3E%3Cpolyline points='12 5 19 12 12 19'/%3E%3C/svg%3E") no-repeat center !important;
    background-size: contain !important;
    flex-shrink: 0 !important;
    order: -1 !important;
    position: static !important;
    inset: auto !important;
    transform: none !important;
    transition: none !important;
    pointer-events: none !important;
}}

/* btn-ghost icon — inject via named wrapper so icon colour adapts */
.btn-ghost-ico div[data-testid="stButton"] > button,
.btn-ghost-ico div[data-testid="stDownloadButton"] > button {{
    display: flex !important;
    align-items: center !important;
    gap: 10px !important;
}}

@keyframes ctaPulse {{
    0%, 100% {{ box-shadow: 0 4px 20px {_ACC}4d !important; }}
    50%       {{ box-shadow: 0 6px 32px {_ACC}7a !important; }}
}}
.cta div[data-testid="stButton"] > button {{
    background: linear-gradient(135deg, {_ACC} 0%, {_ACC2} 100%) !important;
    color: {_LOGO_C} !important; border: none !important; border-radius: 5px !important;
    width: 100% !important; padding: 20px 0 !important;
    font-family: 'DM Mono', monospace !important; font-size: .82rem !important;
    font-weight: 600 !important; letter-spacing: .2em !important; text-transform: uppercase !important;
    box-shadow: 0 4px 20px {_ACC}4d !important;
    position: relative !important; overflow: hidden !important;
    animation: ctaPulse 3s ease infinite !important;
    transition: transform .15s ease, box-shadow .2s ease !important;
}}
.cta div[data-testid="stButton"] > button::before {{
    content: '' !important; position: absolute !important; inset: 0 !important;
    background: linear-gradient(110deg,transparent 20%,rgba(255,255,255,.12) 50%,transparent 80%) !important;
    transform: translateX(-120%) !important;
    transition: transform .6s ease !important; pointer-events: none !important;
}}
.cta div[data-testid="stButton"] > button:hover::before {{ transform: translateX(120%) !important; }}
.cta div[data-testid="stButton"] > button:hover {{
    transform: translateY(-2px) !important;
    box-shadow: 0 10px 40px {_ACC}66 !important;
    animation: none !important;
}}
.cta div[data-testid="stButton"] > button:active {{
    transform: translateY(0) !important; box-shadow: 0 4px 20px {_ACC}4d !important;
}}

/* ── Theme toggle sidebar button ── */
.theme-toggle-full div[data-testid="stButton"] > button {{
    background: transparent !important; border: none !important;
    border-left: 2px solid transparent !important; border-radius: 0 !important;
    color: var(--muted) !important; font-family: 'DM Mono', monospace !important;
    font-size: .72rem !important; font-weight: 400 !important; letter-spacing: .08em !important;
    padding: 12px 20px 12px 48px !important; width: 100% !important; text-align: left !important;
    position: relative !important; overflow: hidden !important;
    transition: background .18s ease, color .18s ease, border-color .18s ease !important;
}}
.theme-toggle-full div[data-testid="stButton"] > button:hover {{
    background: var(--surface2) !important; color: var(--accent) !important;
    border-left-color: var(--accent) !important;
}}

/* ── nav-on active sidebar item ── */
section[data-testid="stSidebar"] .nav-on .stButton > button {{
    background: {_ACC}14 !important;
    color: var(--accent) !important;
    border-left: 2px solid var(--accent) !important;
    font-weight: 500 !important;
}}
</style>
""",
    unsafe_allow_html=True,
)

# ══════════════════════════════════════════════════════════════════════════════
#  SESSION STATE INIT
# ══════════════════════════════════════════════════════════════════════════════
if "page" not in st.session_state:
    st.session_state.page = "model"
if "result" not in st.session_state:
    st.session_state.result = None
if "inputs" not in st.session_state:
    st.session_state.inputs = {}
if "app_loaded" not in st.session_state:
    st.session_state.app_loaded = False
if "advisory_result" not in st.session_state:
    st.session_state.advisory_result = None
# ── Chat state for the Advisory Agent ──────────────────────────────────────
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "chat_farm_ctx" not in st.session_state:
    st.session_state.chat_farm_ctx = {
        "crop": "Wheat",
        "area": "India",
        "year": 2024,
        "rainfall": 800.0,
        "temperature": 25.0,
        "pesticides": 100.0,
        "predicted_yield_tha": None,
        "predicted_yield_hg": None,
        "yield_risk": None,
        "yield_band": None,
        "benchmark_avg": None,
    }
if "chat_uploaded_text" not in st.session_state:
    st.session_state.chat_uploaded_text = ""
if "chat_uploaded_names" not in st.session_state:
    st.session_state.chat_uploaded_names = []
if "chat_context_synced" not in st.session_state:
    st.session_state.chat_context_synced = False

# ══════════════════════════════════════════════════════════════════════════════
#  APP PRELOADER
# ══════════════════════════════════════════════════════════════════════════════
if not st.session_state.app_loaded:
    loader_ph = st.empty()
    loader_ph.markdown(
        """
    <div class="preloader">
        <div>
            <svg width="40" height="40" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="20" cy="20" r="18" stroke="#1f1f22" stroke-width="2"/>
                <path d="M20 8 C14 8, 8 13, 8 20 C8 24, 10 27, 14 29" stroke="#a8e063" stroke-width="2" stroke-linecap="round"
                      stroke-dasharray="40" stroke-dashoffset="40" style="animation: dash 1s ease forwards 0.2s; fill: none;"/>
                <circle cx="20" cy="20" r="3" fill="#a8e063" opacity="0.6"/>
                <path d="M20 17 L20 12 M20 17 L24 15" stroke="#a8e063" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
        </div>
        <div class="preloader-logo">crop<span>cast</span></div>
        <div class="preloader-bar-track"><div class="preloader-bar-fill"></div></div>
        <div class="preloader-status">Initialising model engine</div>
    </div>
    <style>
    @keyframes dash { to { stroke-dashoffset: 0; } }
    </style>
    """,
        unsafe_allow_html=True,
    )
    time.sleep(1.6)
    loader_ph.empty()
    st.session_state.app_loaded = True
    st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
#  MODEL HELPERS
# ══════════════════════════════════════════════════════════════════════════════
HF_REPO = "shiavm006/Crop-yield_pridiction"


@st.cache_resource(show_spinner=False)
def load_artifacts():
    base = Path(__file__).parent / "model"

    def _load(p):
        with open(p, "rb") as f:
            return pickle.load(f)

    if (base / "model.pkl").exists():
        return (
            _load(base / "model.pkl"),
            _load(base / "scaler.pkl"),
            _load(base / "features.pkl"),
        )
    try:
        from huggingface_hub import hf_hub_download

        mp = hf_hub_download(repo_id=HF_REPO, filename="model.pkl")
        sp = hf_hub_download(repo_id=HF_REPO, filename="scaler.pkl")
        fp = hf_hub_download(repo_id=HF_REPO, filename="features.pkl")
        return _load(mp), _load(sp), _load(fp)
    except Exception as e:
        st.error(f"Model load failed: {e}")
        return None, None, None


@st.cache_data(show_spinner=False)
def load_options():
    csv_path = Path(__file__).parent / "Dataset" / "yield_df.csv"
    if not csv_path.exists():
        areas = [
            "Albania",
            "Algeria",
            "Angola",
            "Argentina",
            "Australia",
            "Brazil",
            "Canada",
            "China",
            "Egypt",
            "Ethiopia",
            "France",
            "Germany",
            "India",
            "Indonesia",
            "Iran",
            "Kenya",
            "Mexico",
            "Nigeria",
            "Pakistan",
            "Russia",
            "South Africa",
            "Spain",
            "Turkey",
            "United Kingdom",
            "United States of America",
        ]
        items = [
            "Cassava",
            "Maize",
            "Potatoes",
            "Rice, paddy",
            "Sorghum",
            "Soybeans",
            "Sweet potatoes",
            "Wheat",
            "Yams",
        ]
        return areas, items
    df = pd.read_csv(csv_path)
    return sorted(df["Area"].dropna().unique()), sorted(df["Item"].dropna().unique())


def get_feature_names(fc):
    if fc is None:
        return None
    if isinstance(fc, list):
        return fc
    if isinstance(fc, dict):
        return fc.get("feature_names") or fc.get("columns") or fc.get("names")
    if hasattr(fc, "get_feature_names_out"):
        return fc.get_feature_names_out().tolist()
    return None


def build_row(area, item, year, rainfall, pesticides, avg_temp, fnames):
    numeric = {
        "Year": year,
        "average_rain_fall_mm_per_year": rainfall,
        "pesticides_tonnes": pesticides,
        "avg_temp": avg_temp,
    }
    vals = []
    for name in fnames:
        if name in numeric:
            vals.append(numeric[name])
        elif name.startswith("Area_"):
            vals.append(1.0 if name == f"Area_{area}" else 0.0)
        elif name.startswith("Item_"):
            vals.append(
                1.0
                if (name == f"Item_{item}" or item in name.replace("_", " "))
                else 0.0
            )
        else:
            vals.append(0.0)
    return np.array([vals], dtype=float)


def make_factor_scores(rainfall, avg_temp, pesticides):
    rng = np.random.default_rng(int(rainfall + avg_temp * 100 + pesticides))
    return {
        "Rainfall": round(min(10, max(1, rainfall / 200)), 1),
        "Temperature": round(max(1, min(10, 10 - abs(avg_temp - 22) * 0.38)), 1),
        "Pesticides": round(min(10, max(1, pesticides / 80)), 1),
        "Season": round(float(rng.uniform(5.5, 8.5)), 1),
        "Soil Proxy": round(float(rng.uniform(5.0, 8.0)), 1),
    }


def make_trend(predicted, year):
    rng = np.random.default_rng(int(predicted) % 999)
    base = predicted * 0.76
    return [
        {
            "Year": y,
            "Yield": round(
                base
                + predicted * 0.059 * i
                + float(rng.uniform(-0.03, 0.03)) * predicted,
                0,
            ),
        }
        for i, y in enumerate(range(year - 4, year + 1))
    ]


def make_benchmarks(predicted, rainfall):
    rng = np.random.default_rng(int(predicted + rainfall) % 9999)
    return round(predicted * float(rng.uniform(0.76, 0.92)), 0), round(
        predicted * float(rng.uniform(0.58, 0.74)), 0
    )


def quality_band(y_hg_ha):
    y = y_hg_ha / 10_000  # convert to t/ha for band calc
    if y < 1.0:
        return "Poor", "#ff6b6b"
    if y < 3.0:
        return "Fair", "#d4a040"
    if y < 6.0:
        return "Good", "#a8e063"
    if y < 12.0:
        return "High", "#6abf3a"
    return "Exceptional", "#70d4a0"


# Feature importances (representative RF on FAO dataset)
FEATS = [
    ("Rainfall (mm)", 0.28),
    ("Avg Temp (°C)", 0.22),
    ("Pesticides", 0.19),
    ("Year", 0.16),
    ("Crop (OHE)", 0.15),
]


def gauge_fig(y_hg_ha):
    yv = round(y_hg_ha / 10_000, 2)
    band, bcol = quality_band(y_hg_ha)
    mx = max(20, yv * 1.4)
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=yv,
            number=dict(
                suffix=" t/ha", font=dict(family="Outfit", size=22, color="#ececec")
            ),
            gauge=dict(
                axis=dict(
                    range=[0, mx],
                    tickcolor="#555558",
                    tickfont=dict(size=8, color="#555558"),
                    nticks=5,
                ),
                bar=dict(color=bcol, thickness=0.22),
                bgcolor="#161618",
                bordercolor="#1f1f22",
                borderwidth=1,
                steps=[
                    dict(range=[0, 1], color="#161618"),
                    dict(range=[1, 3], color="rgba(255,107,107,.08)"),
                    dict(range=[3, 6], color="rgba(168,224,99,.08)"),
                    dict(range=[6, mx], color="rgba(168,224,99,.16)"),
                ],
                threshold=dict(line=dict(color=bcol, width=2), thickness=0.8, value=yv),
            ),
        )
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Mono, monospace", color="#555558", size=10),
        margin=dict(l=0, r=0, t=8, b=0),
        height=200,
    )
    return fig


def importance_fig():
    names = [f[0] for f in FEATS]
    vals = [round(f[1] * 100, 1) for f in FEATS]
    mx = max(vals)
    cols = [ACCENT if v == mx else (ACCENT2 if v > 18 else "#2a2a2f") for v in vals]
    fig = go.Figure(
        go.Bar(
            x=vals,
            y=names,
            orientation="h",
            marker=dict(color=cols, line=dict(width=0)),
            text=[f"{v}%" for v in vals],
            textposition="outside",
            textfont=dict(size=9, color="#555558"),
        )
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Mono, monospace", color="#555558", size=10),
        margin=dict(l=0, r=8, t=8, b=0),
        height=200,
        xaxis=dict(
            showgrid=True,
            gridcolor="#141416",
            range=[0, 35],
            ticksuffix="%",
            tickfont=dict(size=8),
        ),
        yaxis=dict(showgrid=False, tickfont=dict(size=10, color="#888")),
        bargap=0.38,
        showlegend=False,
    )
    return fig


def crop_yield_fig():
    crops = [
        "Cassava",
        "Maize",
        "Plantains",
        "Potatoes",
        "Rice",
        "Sorghum",
        "Soybeans",
        "Wheat",
        "Yams",
    ]
    yields = [9.8, 5.2, 6.5, 18.1, 4.6, 1.5, 2.8, 3.3, 8.4]
    cols = [ACCENT if y == max(yields) else "#2a2a2f" for y in yields]
    fig = go.Figure(
        go.Bar(
            x=crops,
            y=yields,
            marker_color=cols,
            marker_line_width=0,
            text=[str(v) for v in yields],
            textposition="outside",
            textfont=dict(size=9, color="#555558"),
        )
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Mono, monospace", color="#555558", size=10),
        margin=dict(l=0, r=0, t=8, b=0),
        height=220,
        xaxis=dict(
            gridcolor="#141416", tickfont=dict(size=9, color="#888"), tickangle=-20
        ),
        yaxis=dict(
            gridcolor="#141416",
            tickfont=dict(size=9),
            title=dict(text="Avg t/ha", font=dict(size=9, color="#555558")),
        ),
        bargap=0.35,
        showlegend=False,
    )
    return fig


def radar_fig(r):
    """Spider / radar chart normalising the four input dimensions to 0–100%."""
    cats = ["Rainfall", "Avg Temp", "Pesticides", "Year (recency)"]
    vals = [
        min(100, r.get("rainfall", 0) / 3000 * 100),
        min(100, r.get("avg_temp", 0) / 40 * 100),
        min(100, r.get("pesticides", 0) / 500 * 100),
        min(100, (r.get("year", 1990) - 1960) / (2024 - 1960) * 100),
    ]
    fig = go.Figure(
        go.Scatterpolar(
            r=vals + [vals[0]],
            theta=cats + [cats[0]],
            fill="toself",
            fillcolor="rgba(168,224,99,0.09)",
            line=dict(color=ACCENT, width=1.8),
            marker=dict(color=ACCENT, size=4),
            hovertemplate="%{theta}: %{r:.0f}%<extra></extra>",
        )
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Mono, monospace", color="#555558", size=10),
        margin=dict(l=24, r=24, t=16, b=16),
        height=260,
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                gridcolor="#1a1a1f",
                tickfont=dict(size=8, color="#444"),
                showline=False,
                ticksuffix="%",
            ),
            angularaxis=dict(gridcolor="#1a1a1f", tickfont=dict(size=9, color="#888")),
        ),
        showlegend=False,
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
#  PLOTLY THEME
# ══════════════════════════════════════════════════════════════════════════════
PL = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="DM Mono, monospace", color="#555558", size=10.5),
    margin=dict(l=4, r=4, t=30, b=4),
    xaxis=dict(
        gridcolor="#141416",
        linecolor="#1f1f22",
        zerolinecolor="#141416",
        tickfont=dict(size=10),
        title_font=dict(size=10),
    ),
    yaxis=dict(
        gridcolor="#141416",
        linecolor="#1f1f22",
        zerolinecolor="#141416",
        tickfont=dict(size=10),
        title_font=dict(size=10),
    ),
)
ACCENT = "#a8e063"
ACCENT2 = "#56ab2f"

# ══════════════════════════════════════════════════════════════════════════════
#  SVG ICONS
# ══════════════════════════════════════════════════════════════════════════════
ICONS = {
    "model": """<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a10 10 0 0 1 0 20"/><path d="M12 2a10 10 0 0 0 0 20"/><path d="M2 12h20"/><path d="M12 2c2.5 2.5 4 6 4 10s-1.5 7.5-4 10"/><path d="M12 2c-2.5 2.5-4 6-4 10s1.5 7.5 4 10"/></svg>""",
    "results": """<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>""",
    "download": """<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>""",
    "new": """<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-5.91"/></svg>""",
    "run": """<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>""",
    "insights": """<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M2 20h20"/><path d="M6 20V10l6-8 6 8v10"/><path d="M10 20v-5h4v5"/></svg>""",
    "about": """<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>""",
    "location": """<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>""",
    "weather": """<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9z"/></svg>""",
}


# ══════════════════════════════════════════════════════════════════════════════
#  LEFT SIDEBAR NAV
# ══════════════════════════════════════════════════════════════════════════════
def render_sidebar():
    model, _, _ = load_artifacts()
    MODEL_OK = model is not None

    # Theme state for this render
    _is_dark = st.session_state.get("theme", "dark") == "dark"
    _acc = _ACC
    _tog_lbl = _TOGGLE_LABEL

    # Sun/moon icon HTML island
    # Theme SVG Icon
    _theme_icon = (
        '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="12" r="4"/><line x1="12" y1="2" x2="12" y2="5"/><line x1="12" y1="19" x2="12" y2="22"/><line x1="4.22" y1="4.22" x2="6.34" y2="6.34"/><line x1="17.66" y1="17.66" x2="19.78" y2="19.78"/><line x1="2" y1="12" x2="5" y2="12"/><line x1="19" y1="12" x2="22" y2="12"/><line x1="4.22" y1="19.78" x2="6.34" y2="17.66"/><line x1="17.66" y1="6.34" x2="19.78" y2="4.22"/></svg>'
        if _is_dark
        else '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>'
    )

    with st.sidebar:
        # ── Sidebar button styles ───────────────────────────────────────────
        st.markdown(
            f"""
        <style>
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button {{
            background: transparent !important; border: none !important;
            border-left: 2px solid transparent !important; border-radius: 0 !important;
            color: var(--muted) !important; font-family: 'DM Mono', monospace !important;
            font-size: .78rem !important; font-weight: 400 !important;
            text-align: left !important; padding: 12px 20px 12px 48px !important;
            width: 100% !important; margin: 0 !important;
            transition: background .18s ease, color .18s ease, border-color .18s ease !important;
            box-shadow: none !important; letter-spacing: .04em !important;
        }}
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button:hover {{
            background: var(--surface2) !important; color: var(--text) !important;
            border-left-color: var(--border2) !important; transform: none !important;
        }}
        section[data-testid="stSidebar"] .nav-on div[data-testid="stButton"] > button {{
            background: {_acc}14 !important; color: var(--accent) !important;
            border-left: 2px solid var(--accent) !important; font-weight: 500 !important;
        }}
        section[data-testid="stSidebar"] button:disabled {{
            opacity: 0.28 !important; cursor: not-allowed !important;
        }}
        section[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"],
        section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div {{
            gap: 0 !important;
        }}
        section[data-testid="stSidebar"] .stButton {{ margin: 0 !important; padding: 0 !important; }}
        </style>
        """,
            unsafe_allow_html=True,
        )

        # ── Logo + Brand ───────────────────────────────────────────────────
        st.markdown(
            f"""
        <div style="padding:24px 20px 16px;display:flex;align-items:center;gap:12px;">
          <!-- CropCast SVG logo mark -->
          <div style="width:36px;height:36px;flex-shrink:0;background:{'rgba(168,224,99,0.12)' if _is_dark else 'rgba(44,122,24,0.1)'};
                      border:1px solid {'rgba(168,224,99,0.25)' if _is_dark else 'rgba(44,122,24,0.2)'};
                      border-radius:9px;display:flex;align-items:center;justify-content:center;">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
                 stroke="{_acc}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
              <!-- wheat stalk -->
              <line x1="12" y1="22" x2="12" y2="6"/>
              <!-- left leaves -->
              <path d="M12 10 C10 8, 7 8, 6 6 C8 6, 11 7, 12 10"/>
              <path d="M12 14 C10 12, 7 12, 5 10 C7 10, 11 11, 12 14"/>
              <!-- right leaves -->
              <path d="M12 10 C14 8, 17 8, 18 6 C16 6, 13 7, 12 10"/>
              <path d="M12 14 C14 12, 17 12, 19 10 C17 10, 13 11, 12 14"/>
              <!-- grain head -->
              <ellipse cx="12" cy="4.5" rx="2" ry="2.5"/>
            </svg>
          </div>
          <div>
            <div style="font-family:'Outfit',sans-serif;font-size:1.05rem;font-weight:700;
                        color:var(--text);letter-spacing:-.02em;line-height:1;">CropCast</div>
            <div style="font-size:.46rem;color:var(--muted);letter-spacing:.26em;
                        text-transform:uppercase;margin-top:3px;">Yield Intelligence</div>
          </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # ── Model status badge ─────────────────────────────────────────────
        if MODEL_OK:
            badge = '<span class="model-badge badge-ok"><span class="badge-dot"></span>Model Loaded</span>'
        else:
            badge = '<span class="model-badge badge-err"><span class="badge-dot"></span>Model Error</span>'
        st.markdown(
            f'<div style="padding:0 20px 12px;">{badge}</div>', unsafe_allow_html=True
        )

        # ── Divider ────────────────────────────────────────────────────────
        st.markdown(
            '<div style="height:1px;background:var(--border);margin:0;"></div>',
            unsafe_allow_html=True,
        )

        # ── Theme toggle ───────────────────────────────────────────────────
        st.markdown(
            f"""
        <div style="position:relative;height:0;overflow:visible;pointer-events:none;">
          <div style="position:absolute;top:0;left:16px;transform:translateY(22px) translateY(-50%);
                      color:var(--muted);line-height:0;">{_theme_icon}</div>
        </div>""",
            unsafe_allow_html=True,
        )
        st.markdown('<div class="theme-toggle-full">', unsafe_allow_html=True)
        if st.button(_tog_lbl, key="theme_btn", use_container_width=True):
            st.session_state.theme = "light" if _is_dark else "dark"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        # ── Nav header ────────────────────────────────────────────────────
        st.markdown(
            '<div style="height:1px;background:var(--border);margin:0;"></div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<div style="padding:12px 20px 6px;font-size:.44rem;color:var(--muted);letter-spacing:.28em;text-transform:uppercase;">Navigation</div>',
            unsafe_allow_html=True,
        )

        # ── Nav items ─────────────────────────────────────────────────────
        _nav = [
            ("model", ICONS["model"], "Predict Yield"),
            ("results", ICONS["results"], "Results"),
            ("insights", ICONS["insights"], "Model Insights"),
            ("advisory", "🤖", "Advisory Agent"),
            ("about", ICONS["about"], "About"),
        ]

        _result_pages = {"loading", "results"}

        for _key, _ico, _lb in _nav:
            is_active = st.session_state.page == _key or (
                _key == "results" and st.session_state.page in _result_pages
            )
            is_disabled = _key == "results" and not st.session_state.result

            st.markdown(
                f'<div class="{"nav-on" if is_active else ""}">', unsafe_allow_html=True
            )

            ic_col = "var(--accent)" if is_active else "var(--muted)"
            st.markdown(
                f"""
            <div style="position:relative;height:0;overflow:visible;pointer-events:none;">
              <div style="position:absolute;top:0;left:16px;transform:translateY(22px) translateY(-50%);
                          color:{ic_col};line-height:0;">{_ico}</div>
            </div>""",
                unsafe_allow_html=True,
            )

            if st.button(
                _lb, key=f"nav_{_key}", use_container_width=True, disabled=is_disabled
            ):
                if _key == "model":
                    st.session_state.page = "model"
                    st.session_state.result = None
                else:
                    st.session_state.page = _key
                st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)

        # ── Footer ────────────────────────────────────────────────────────
        st.markdown(
            """
        <div class="sbft">
            Random Forest &middot; 100 estimators<br>
            FAO Global Crop Dataset<br>
            UI: Streamlit Community Cloud &middot; Model: <code>shiavm006/Crop-yield_pridiction</code>
        </div>
        """,
            unsafe_allow_html=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE: MODEL
# ══════════════════════════════════════════════════════════════════════════════
def page_model():
    model, scaler, features_config = load_artifacts()
    areas, items = load_options()
    fnames = get_feature_names(features_config) or [
        "Year",
        "average_rain_fall_mm_per_year",
        "pesticides_tonnes",
        "avg_temp",
    ]

    st.markdown(
        """
    <div class="page-header">
        <div class="page-title">Configure Prediction</div>
        <div class="page-sub">Set environmental and crop parameters to run the yield model</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="page-content">', unsafe_allow_html=True)

    col_l, col_r = st.columns([1, 1], gap="large")

    with col_l:
        st.markdown(
            f"""<div class="form-section-label">{ICONS['location']} &nbsp;Location & Crop</div>""",
            unsafe_allow_html=True,
        )
        area = st.selectbox("Region / Country", options=areas, key="inp_area")
        item = st.selectbox("Crop Type", options=items, key="inp_item")
        year = st.slider(
            "Projection Year",
            min_value=1990,
            max_value=2030,
            value=2020,
            step=1,
            key="inp_year",
        )

    with col_r:
        st.markdown(
            f"""<div class="form-section-label">{ICONS['weather']} &nbsp;Environmental Conditions</div>""",
            unsafe_allow_html=True,
        )
        rainfall = st.slider(
            "Annual Rainfall (mm/year)",
            min_value=0,
            max_value=4000,
            value=1000,
            step=25,
            key="inp_rain",
        )
        avg_temp = st.slider(
            "Average Temperature (°C)",
            min_value=-5,
            max_value=45,
            value=20,
            step=1,
            key="inp_temp",
            format="%d °C",
        )
        pesticides = st.slider(
            "Pesticides Applied (tonnes)",
            min_value=0,
            max_value=5000,
            value=100,
            step=10,
            key="inp_pest",
        )

    st.markdown("<br>", unsafe_allow_html=True)

    btn_col, _ = st.columns([1, 2])
    with btn_col:
        st.markdown('<div class="cta">', unsafe_allow_html=True)
        run = st.button("Run Prediction", key="run_btn", use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    if run:
        if model is None:
            st.error("Model not available. Check model files.")
            return
        # Save inputs and navigate to full-page loading screen
        st.session_state.inputs = {
            "area": area,
            "item": item,
            "year": year,
            "rainfall": rainfall,
            "avg_temp": avg_temp,
            "pesticides": pesticides,
            "fnames": fnames,
        }
        st.session_state.page = "loading"
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE: RESULTS
# ══════════════════════════════════════════════════════════════════════════════
def page_results():
    if not st.session_state.result:
        st.markdown(
            """
        <div style="padding:80px 36px;text-align:center;">
            <div style="font-size:.65rem;color:var(--muted);letter-spacing:.18em;text-transform:uppercase;">
                No prediction data &mdash; run the model first
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )
        return

    r = st.session_state.result
    yv = round(r["yield_hg_ha"] / 10_000, 2)
    band, _ = quality_band(r["yield_hg_ha"])

    _, mc, _ = st.columns([0.02, 0.96, 0.02])
    with mc:
        # ── Page header ───────────────────────────────────────────────────────
        st.markdown(
            f"""
        <div class="pg">
          <div class="ey">Analysis Complete</div>
          <div class="ttl">Yield Report</div>
          <div class="sub">{r['item']} &mdash; {r['year']} &mdash; {r['rainfall']:,} mm rainfall</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # ── Download button at top ─────────────────────────────────────────────
        _, dlcol, _ = st.columns([0.01, 0.28, 0.71])
        with dlcol:
            st.markdown('<div class="btn-ghost">', unsafe_allow_html=True)
            st.download_button(
                "↓  Download Report",
                data=build_html_report(r).encode("utf-8"),
                mime="text/html",
                file_name=f"cropcast_{r['item'].replace(' ','_').replace(',','')}_{r['year']}.html",
                key="dl_top",
            )
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div class='dv'></div>", unsafe_allow_html=True)

        # ── Hero + Gauge ───────────────────────────────────────────────────────
        hc, gc = st.columns([1.5, 1])
        with hc:
            st.markdown(
                f"""
            <div class="hero">
              <div class="hb">{r['item']} &mdash; {r['year']}</div>
              <div class="hn">{yv}</div>
              <div class="hu">Tonnes per Hectare</div>
              <div class="hbd">{band}</div>
            </div>""",
                unsafe_allow_html=True,
            )
        with gc:
            st.markdown(
                '<div class="card"><div class="ch">Quality Gauge</div>',
                unsafe_allow_html=True,
            )
            st.plotly_chart(
                gauge_fig(r["yield_hg_ha"]),
                use_container_width=True,
                config={"displayModeBar": False},
            )
            st.markdown("</div>", unsafe_allow_html=True)

        # ── Metric chips ───────────────────────────────────────────────────────
        st.markdown(
            f"""
        <div class="mgrid">
          <div class="chip"><div class="cl">Predicted Yield</div><div class="cv">{yv}</div><div class="cs">t / ha</div></div>
          <div class="chip"><div class="cl">Rainfall</div><div class="cv">{r['rainfall']:,}</div><div class="cs">mm / year</div></div>
          <div class="chip"><div class="cl">Temperature</div><div class="cv">{r['avg_temp']}</div><div class="cs">°C avg</div></div>
          <div class="chip"><div class="cl">Pesticides</div><div class="cv">{r['pesticides']:,}</div><div class="cs">tonnes</div></div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # ── Radar + Feature Importance ─────────────────────────────────────────
        cc1, cc2 = st.columns(2)
        with cc1:
            st.markdown(
                '<div class="card"><div class="ch">Input Profile</div>',
                unsafe_allow_html=True,
            )
            st.plotly_chart(
                radar_fig(r), use_container_width=True, config={"displayModeBar": False}
            )
            st.markdown("</div>", unsafe_allow_html=True)
        with cc2:
            st.markdown(
                '<div class="card"><div class="ch">Feature Importance</div>',
                unsafe_allow_html=True,
            )
            st.plotly_chart(
                importance_fig(),
                use_container_width=True,
                config={"displayModeBar": False},
            )
            st.markdown("</div>", unsafe_allow_html=True)

        # ── Inline report preview ──────────────────────────────────────────────
        st.markdown(
            '<div class="card"><div class="ch">Consulting Report Preview</div>',
            unsafe_allow_html=True,
        )
        components.html(build_html_report(r), height=860, scrolling=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # ── New prediction button ──────────────────────────────────────────────
        st.markdown("<br>", unsafe_allow_html=True)
        _, nc, _ = st.columns([0.01, 0.28, 0.71])
        with nc:
            st.markdown('<div class="btn-ghost">', unsafe_allow_html=True)
            # Refresh icon overlay
            st.markdown(
                """
            <div style="position:relative;height:0;overflow:visible;pointer-events:none;z-index:9;">
              <div style="position:absolute;top:14px;left:28px;line-height:0;color:var(--text2);">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="1 4 1 10 7 10"/>
                  <path d="M3.51 15a9 9 0 1 0 .49-5.91"/>
                </svg>
              </div>
            </div>""",
                unsafe_allow_html=True,
            )
            if st.button("   New Prediction", key="new_pred"):
                st.session_state.page = "model"
                st.session_state.result = None
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<br><br>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE: LOADING  (full-viewport, no sidebar content scrolling behind it)
# ══════════════════════════════════════════════════════════════════════════════
def page_loading():
    inp = st.session_state.inputs
    # Full-page animated screen
    components.html(
        """<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400&family=DM+Sans:wght@300;400&display=swap');
*{box-sizing:border-box;margin:0;padding:0;}
html,body{height:100vh;background:#080809;overflow:hidden;}
.wrap{height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:28px;font-family:'DM Sans',sans-serif;}
.brand{font-family:'Fraunces',serif;font-size:1.05rem;color:#a8e063;letter-spacing:-.02em;opacity:0;animation:up .55s ease .1s forwards;}
.orb{width:62px;height:62px;position:relative;opacity:0;animation:up .45s ease .22s forwards;}
.rg{position:absolute;inset:0;border-radius:50%;border:1.5px solid transparent;}
.r1{border-top-color:#a8e063;animation:cw 1s linear infinite;}
.r2{inset:11px;border-right-color:#6abf3a;animation:ccw 1.55s linear infinite;opacity:.6;}
.r3{inset:21px;border-bottom-color:#333337;animation:cw 2.1s linear infinite;opacity:.35;}
.dc{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:5px;height:5px;border-radius:50%;background:#a8e063;}
@keyframes cw{to{transform:rotate(360deg)}}
@keyframes ccw{to{transform:rotate(-360deg)}}
.steps{display:flex;flex-direction:column;gap:10px;width:280px;opacity:0;animation:up .45s ease .36s forwards;}
.step{display:flex;align-items:center;gap:11px;}
.sd{width:6px;height:6px;border-radius:50%;background:#1f1f22;flex-shrink:0;transition:background .35s,transform .25s;}
.sd.on{background:#a8e063;animation:pulse 1.1s ease infinite;}
.sd.done{background:#a8e063;animation:none;transform:scale(.8);}
.sl{font-size:.7rem;color:#555558;transition:color .3s,opacity .3s;}
.sl.on{color:#ececec;} .sl.done{color:#aaaaaa;opacity:.7;}
@keyframes pulse{0%,100%{transform:scale(1);opacity:1}50%{transform:scale(1.8);opacity:.4}}
.bw{width:280px;height:1px;background:#1f1f22;overflow:hidden;opacity:0;animation:up .4s ease .44s forwards;}
.bf{height:100%;background:linear-gradient(90deg,#a8e063,#6abf3a);animation:grow 3s cubic-bezier(.4,0,.2,1) .5s forwards;}
@keyframes grow{from{width:0}to{width:88%}}
.hint{font-size:.56rem;letter-spacing:.2em;text-transform:uppercase;color:#555558;opacity:0;animation:up .4s ease .5s forwards;}
@keyframes up{from{opacity:0;transform:translateY(7px)}to{opacity:1;transform:none}}
</style></head><body>
<div class="wrap">
  <div class="brand">CropCast</div>
  <div class="orb">
    <div class="rg r1"></div><div class="rg r2"></div><div class="rg r3"></div>
    <div class="dc"></div>
  </div>
  <div class="steps">
    <div class="step"><div class="sd" id="d0"></div><div class="sl" id="l0">Loading model from HuggingFace</div></div>
    <div class="step"><div class="sd" id="d1"></div><div class="sl" id="l1">Encoding crop features (one-hot)</div></div>
    <div class="step"><div class="sd" id="d2"></div><div class="sl" id="l2">Scaling inputs via StandardScaler</div></div>
    <div class="step"><div class="sd" id="d3"></div><div class="sl" id="l3">Running Random Forest inference</div></div>
    <div class="step"><div class="sd" id="d4"></div><div class="sl" id="l4">Converting hg/ha \u2192 t/ha</div></div>
  </div>
  <div class="bw"><div class="bf"></div></div>
  <div class="hint">Querying FAO-trained model \u2014 please wait</div>
</div>
<script>
const ts=[250,680,1250,1900,2600];
ts.forEach((t,i)=>{
  setTimeout(()=>{
    if(i>0){document.getElementById('d'+(i-1)).className='sd done';document.getElementById('l'+(i-1)).className='sl done';}
    document.getElementById('d'+i).className='sd on';document.getElementById('l'+i).className='sl on';
  },t);
});
</script></body></html>""",
        height=500,
    )

    time.sleep(3.2)

    # Run actual prediction
    model, scaler, features_config = load_artifacts()
    fnames = (
        inp.get("fnames")
        or get_feature_names(features_config)
        or ["Year", "average_rain_fall_mm_per_year", "pesticides_tonnes", "avg_temp"]
    )
    X = build_row(
        inp["area"],
        inp["item"],
        inp["year"],
        inp["rainfall"],
        inp["pesticides"],
        inp["avg_temp"],
        fnames,
    )
    X_scaled = scaler.transform(X)
    pred = float(model.predict(X_scaled)[0])

    scores = make_factor_scores(inp["rainfall"], inp["avg_temp"], inp["pesticides"])
    b_avg, b_glob = make_benchmarks(pred, inp["rainfall"])
    trend = make_trend(pred, inp["year"])

    st.session_state.result = {
        "yield_hg_ha": round(pred, 0),
        "ci_low": round(pred * 0.90, 0),
        "ci_high": round(pred * 1.10, 0),
        "area": inp["area"],
        "item": inp["item"],
        "year": inp["year"],
        "rainfall": inp["rainfall"],
        "avg_temp": inp["avg_temp"],
        "pesticides": inp["pesticides"],
        "scores": scores,
        "benchmark_avg": b_avg,
        "benchmark_global": b_glob,
        "trend": trend,
    }
    st.session_state.page = "results"
    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE: INSIGHTS
# ══════════════════════════════════════════════════════════════════════════════
def page_insights():
    st.markdown(
        """
    <div class="page-header">
        <div class="page-title">Model Insights</div>
        <div class="page-sub">Performance metrics and feature analysis of the Random Forest Regressor trained on FAO global crop production data</div>
    </div>
    """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="page-content">', unsafe_allow_html=True)

    # ── Stat chips ────────────────────────────────────────────────────────────
    sc1, sc2, sc3, sc4 = st.columns(4)
    for col, val, lbl, sub, delay in [
        (sc1, "~0.94", "R\u00b2 Score", "Train set performance", "0.06s"),
        (sc2, "~0.87", "Test R\u00b2", "Generalisation score", "0.13s"),
        (sc3, "100", "Trees", "n_estimators", "0.20s"),
        (sc4, "5", "Features", "Year + climate + crop OHE", "0.27s"),
    ]:
        with col:
            st.markdown(
                f"""
            <div class="metric-card istat" style="animation-delay:{delay};">
                <span class="istat-val">{val}</span>
                <div class="istat-lbl">{lbl}</div>
                <div class="istat-sub">{sub}</div>
            </div>""",
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Feature importance chart + training config ─────────────────────────────
    ch1, ch2 = st.columns([3, 2], gap="large")
    with ch1:
        st.markdown(
            """<div class="metric-card"><div class="form-section-label">Feature Importance</div>""",
            unsafe_allow_html=True,
        )
        st.plotly_chart(
            importance_fig(), use_container_width=True, config={"displayModeBar": False}
        )
        st.markdown("</div>", unsafe_allow_html=True)
    with ch2:
        st.markdown(
            """
        <div class="metric-card">
            <div class="form-section-label">Training Config</div>
            <div class="cfg-row"><span class="cfg-k">algorithm</span><span class="cfg-v">RandomForestRegressor</span></div>
            <div class="cfg-row"><span class="cfg-k">n_estimators</span><span class="cfg-v">100</span></div>
            <div class="cfg-row"><span class="cfg-k">random_state</span><span class="cfg-v">42</span></div>
            <div class="cfg-row"><span class="cfg-k">scaler</span><span class="cfg-v">StandardScaler</span></div>
            <div class="cfg-row"><span class="cfg-k">numeric inputs</span><span class="cfg-v">Year, Rainfall, Temp, Pesticides</span></div>
            <div class="cfg-row"><span class="cfg-k">categorical</span><span class="cfg-v">Item (OHE, ~10 crops)</span></div>
            <div class="cfg-row"><span class="cfg-k">target unit</span><span class="cfg-v">hg/ha \u2192 t/ha</span></div>
            <div class="cfg-row" style="border-bottom:none"><span class="cfg-k">dataset</span><span class="cfg-v">FAO crop production</span></div>
        </div>""",
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Avg yield by crop ──────────────────────────────────────────────────────
    st.markdown(
        """<div class="metric-card"><div class="form-section-label">Average Yield by Crop (FAO t/ha)</div>""",
        unsafe_allow_html=True,
    )
    st.plotly_chart(
        crop_yield_fig(), use_container_width=True, config={"displayModeBar": False}
    )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Feature ranking + performance bars ────────────────────────────────────
    fr1, fr2 = st.columns([3, 2], gap="large")
    with fr1:
        st.markdown(
            """<div class="metric-card"><div class="form-section-label">Feature Ranking</div>""",
            unsafe_allow_html=True,
        )
        for i, (nm, imp) in enumerate(FEATS):
            pct = int(imp * 100)
            st.markdown(
                f"""
            <div class="fbr" style="animation-delay:{i*.06:.2f}s;">
                <div class="fbn">{nm}</div>
                <div class="fbt"><div class="fbf" style="width:{pct}%;animation-delay:{i*.06+.07:.2f}s;"></div></div>
                <div class="fbp">{pct}%</div>
            </div>""",
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)
    with fr2:
        st.markdown(
            """
        <div class="metric-card">
            <div class="form-section-label">Performance Breakdown</div>
            <div class="perf-row"><div class="perf-label">Train R\u00b2</div><div class="perf-bar-wrap"><div class="perf-bar" style="width:94%;"></div></div><div class="perf-val">~0.94</div></div>
            <div class="perf-row"><div class="perf-label">Test R\u00b2</div><div class="perf-bar-wrap"><div class="perf-bar" style="width:87%;background:linear-gradient(90deg,#56ab2f,#a8e063);"></div></div><div class="perf-val">~0.87</div></div>
            <div class="perf-row"><div class="perf-label">Rainfall imp.</div><div class="perf-bar-wrap"><div class="perf-bar" style="width:82%;background:linear-gradient(90deg,#3a9bd5,#a8e063);"></div></div><div class="perf-val">28%</div></div>
            <div class="perf-row"><div class="perf-label">Temp imp.</div><div class="perf-bar-wrap"><div class="perf-bar" style="width:72%;"></div></div><div class="perf-val">22%</div></div>
            <div class="perf-row" style="border-bottom:none;"><div class="perf-label">Crop OHE</div><div class="perf-bar-wrap"><div class="perf-bar" style="width:55%;"></div></div><div class="perf-val">15%</div></div>
        </div>""",
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)  # page-content


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE: ABOUT
# ══════════════════════════════════════════════════════════════════════════════
def page_about():
    st.markdown(
        """
    <div class="page-header">
        <div class="page-title">About CropCast</div>
        <div class="page-sub">A professional machine learning interface for global agricultural yield prediction, powered by a Random Forest Regressor trained on FAO crop production data and hosted on Hugging Face</div>
    </div>
    """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="page-content">', unsafe_allow_html=True)

    # ── Info cards grid ───────────────────────────────────────────────────────
    st.markdown('<div class="abg">', unsafe_allow_html=True)
    for lbl, val, desc in [
        ("Dataset", "FAO", "Global crop yield, rainfall, temperature, pesticides"),
        (
            "Algorithm",
            "Random Forest",
            "100 estimators \u00b7 sklearn \u00b7 StandardScaler pipeline",
        ),
        ("Target", "t / ha", "FAO hg/ha output converted to tonnes per hectare"),
        (
            "Hosting",
            "Streamlit + HF",
            "UI on Streamlit Community Cloud; model artifacts on Hugging Face (shiavm006/Crop-yield_pridiction)",
        ),
    ]:
        st.markdown(
            f"""
        <div class="abt">
            <div class="abl">{lbl}</div>
            <div class="abv">{val}</div>
            <div class="abd">{desc}</div>
        </div>""",
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Model features card ───────────────────────────────────────────────────
    st.markdown(
        """
    <div class="metric-card" style="margin-bottom:12px;">
        <div class="form-section-label">Model Features</div>
        <div style="font-size:13px;color:var(--muted);line-height:2;font-weight:300;">
            The model was trained on four numeric features and one one-hot encoded categorical:<br><br>
            <code style="background:var(--surface3);color:var(--accent);padding:2px 8px;border-radius:4px;font-size:11px;">Year</code>&nbsp;
            <code style="background:var(--surface3);color:var(--accent);padding:2px 8px;border-radius:4px;font-size:11px;">average_rain_fall_mm_per_year</code>&nbsp;
            <code style="background:var(--surface3);color:var(--accent);padding:2px 8px;border-radius:4px;font-size:11px;">avg_temp</code>&nbsp;
            <code style="background:var(--surface3);color:var(--accent);padding:2px 8px;border-radius:4px;font-size:11px;">pesticides</code>&nbsp;
            <code style="background:var(--surface3);color:var(--accent);padding:2px 8px;border-radius:4px;font-size:11px;">Item_*</code><br><br>
            <strong style="color:var(--text2);font-weight:500;">Area (country)</strong> was dropped &mdash; the model predicts yield purely from climate and crop type.<br>
            FAO output is in <strong style="color:var(--text2);">hg/ha</strong>; we divide by 10,000 to return <strong style="color:var(--accent);">t/ha</strong>.
        </div>
    </div>""",
        unsafe_allow_html=True,
    )

    # ── HuggingFace integration card ──────────────────────────────────────────
    st.markdown(
        """
    <div class="metric-card">
        <div class="form-section-label">HuggingFace Integration</div>
        <div style="font-size:13px;color:var(--muted);line-height:2.1;font-weight:300;">
            <strong style="color:var(--text2);font-weight:500;">Repo</strong> &mdash;
            <code style="background:var(--surface3);color:var(--accent);padding:2px 8px;border-radius:4px;font-size:11px;">shiavm006/Crop-yield_pridiction</code><br>
            <strong style="color:var(--text2);font-weight:500;">Files</strong> &mdash;
            <code style="background:var(--surface3);color:var(--accent);padding:2px 8px;border-radius:4px;font-size:11px;">model.pkl</code>&nbsp;
            <code style="background:var(--surface3);color:var(--accent);padding:2px 8px;border-radius:4px;font-size:11px;">scaler.pkl</code>&nbsp;
            <code style="background:var(--surface3);color:var(--accent);padding:2px 8px;border-radius:4px;font-size:11px;">features.pkl</code><br>
            <strong style="color:var(--text2);font-weight:500;">Loading</strong> &mdash;
            <code style="background:var(--surface3);color:var(--accent);padding:2px 8px;border-radius:4px;font-size:11px;">hf_hub_download(repo_id=HF_REPO, filename=...)</code> cached via
            <code style="background:var(--surface3);color:var(--accent);padding:2px 8px;border-radius:4px;font-size:11px;">@st.cache_resource</code><br>
            <strong style="color:var(--text2);font-weight:500;">Prediction</strong> &mdash;
            Build row &rarr; align to <code style="background:var(--surface3);color:var(--accent);padding:2px 8px;border-radius:4px;font-size:11px;">features.pkl</code> order
            &rarr; <code style="background:var(--surface3);color:var(--accent);padding:2px 8px;border-radius:4px;font-size:11px;">scaler.transform</code>
            &rarr; <code style="background:var(--surface3);color:var(--accent);padding:2px 8px;border-radius:4px;font-size:11px;">model.predict</code> &rarr; &divide; 10000
        </div>
    </div>""",
        unsafe_allow_html=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)  # page-content


# ══════════════════════════════════════════════════════════════════════════════
#  PAGE: ADVISORY AGENT  (conversational chat + doc upload)
# ══════════════════════════════════════════════════════════════════════════════
def _extract_uploaded_text(files) -> tuple[str, list[str]]:
    """Read a list of UploadedFile objects and return (combined_text, filenames)."""
    texts, names = [], []
    for f in files:
        try:
            name = f.name
            lower = name.lower()
            if lower.endswith(".pdf"):
                try:
                    from pypdf import PdfReader
                except ImportError:
                    texts.append(f"[{name}] (PDF support unavailable — install pypdf)")
                    names.append(name)
                    continue
                f.seek(0)
                reader = PdfReader(f)
                page_chunks = []
                for i, page in enumerate(reader.pages):
                    try:
                        page_chunks.append(page.extract_text() or "")
                    except Exception:
                        page_chunks.append("")
                texts.append(f"# {name}\n\n" + "\n\n".join(page_chunks).strip())
            else:
                f.seek(0)
                raw = f.read()
                try:
                    content = raw.decode("utf-8")
                except UnicodeDecodeError:
                    content = raw.decode("latin-1", errors="ignore")
                texts.append(f"# {name}\n\n{content}")
            names.append(name)
        except Exception as e:
            texts.append(f"[{getattr(f, 'name', 'file')}] (read error: {e})")
            names.append(getattr(f, "name", "unknown"))
    return ("\n\n---\n\n".join(t for t in texts if t).strip(), names)


def _ensure_yield_prediction(ctx: dict) -> dict:
    """Run the ML model to fill predicted_yield_tha/risk/band for the given context."""
    try:
        from agent.graph import run_agent
    except Exception as e:
        return {"error": f"Could not import agent: {e}"}
    try:
        result = run_agent(
            crop=ctx["crop"],
            area=ctx["area"],
            year=int(ctx["year"]),
            rainfall=float(ctx["rainfall"]),
            temperature=float(ctx["temperature"]),
            pesticides=float(ctx["pesticides"]),
            user_query="Generate a baseline advisory.",
        )
        ctx["predicted_yield_tha"] = result.get("predicted_yield_tha")
        ctx["predicted_yield_hg"] = result.get("predicted_yield_hg")
        ctx["yield_band"] = result.get("yield_band")
        ctx["yield_risk"] = result.get("yield_risk")
        ctx["benchmark_avg"] = result.get("benchmark_avg")
        return {"ok": True, "advisory": result}
    except Exception as e:
        return {"error": str(e)}


def page_advisory():
    CROPS = [
        "Wheat",
        "Rice, paddy",
        "Maize",
        "Potatoes",
        "Cassava",
        "Soybeans",
        "Sorghum",
        "Sweet potatoes",
    ]
    AREAS = sorted(
        [
            "India",
            "Brazil",
            "USA",
            "China",
            "Argentina",
            "Australia",
            "Canada",
            "France",
            "Germany",
            "Indonesia",
            "Mexico",
            "Nigeria",
            "Pakistan",
            "Russia",
            "Thailand",
            "Turkey",
            "Ukraine",
        ]
    )

    # ── Page-scoped chat styles (compact, uniform) ────────────────────────────
    st.markdown(
        """
    <style>
    /* Compact header for this page */
    .adv-head { padding: 22px 36px 6px; animation: fadeUp .4s ease both; }
    .adv-eyebrow { font-size: .58rem; letter-spacing: .22em; text-transform: uppercase;
                   color: var(--accent); margin-bottom: 6px; }
    .adv-title { font-family: 'Outfit', sans-serif; font-size: 1.55rem; font-weight: 600;
                 color: var(--text); letter-spacing: -.02em; line-height: 1.15; }
    .adv-sub { font-family: 'DM Mono', monospace; font-size: .74rem; color: var(--muted);
               margin-top: 4px; line-height: 1.5; max-width: 680px; }

    /* Compact status chip grid — always 5-up on desktop, collapses at narrow widths */
    .adv-chips {
        display: grid; grid-template-columns: repeat(5, minmax(0, 1fr));
        gap: 8px; margin: 14px 0 16px;
    }
    .adv-chip {
        background: var(--surface2); border: 1px solid var(--border);
        border-radius: 8px; padding: 9px 12px; min-width: 0;
    }
    .adv-chip-k { font-family: 'DM Mono', monospace; font-size: .55rem;
                  color: var(--muted); letter-spacing: .14em;
                  text-transform: uppercase; margin-bottom: 2px; }
    .adv-chip-v { font-size: .92rem; font-weight: 600; color: var(--text);
                  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    @media (max-width: 900px) { .adv-chips { grid-template-columns: repeat(3, 1fr); } }
    @media (max-width: 560px) { .adv-chips { grid-template-columns: repeat(2, 1fr); } }

    /* Unify toolbar buttons (neutralise the .cta gradient if it slips in) */
    .adv-toolbar div[data-testid="stButton"] > button {
        padding: 10px 0 !important; font-size: .72rem !important;
        letter-spacing: .06em !important; text-transform: none !important;
        background: var(--surface2) !important; color: var(--text) !important;
        border: 1px solid var(--border) !important; font-weight: 500 !important;
        animation: none !important; box-shadow: none !important;
    }
    .adv-toolbar div[data-testid="stButton"] > button:hover {
        border-color: var(--accent) !important; color: var(--accent) !important;
        box-shadow: none !important; transform: translateY(-1px) !important;
    }

    /* Empty-state card */
    .adv-empty {
        border: 1px dashed var(--border); border-radius: 12px;
        background: var(--surface2); padding: 26px 22px; text-align: center;
        margin: 4px 0 10px; animation: fadeUp .35s ease both;
    }
    .adv-empty h3 { font-family: 'Outfit', sans-serif; font-size: 1.05rem;
                    font-weight: 600; color: var(--text); margin-bottom: 6px; }
    .adv-empty p  { font-size: .82rem; color: var(--text2); line-height: 1.6;
                    max-width: 560px; margin: 0 auto 14px; }

    /* Suggestion pills (buttons inside .adv-pills are styled as pills) */
    .adv-pills div[data-testid="stButton"] > button {
        background: var(--surface3) !important; color: var(--text2) !important;
        border: 1px solid var(--border) !important; border-radius: 100px !important;
        padding: 8px 16px !important; font-size: .72rem !important;
        font-family: 'DM Mono', monospace !important; font-weight: 400 !important;
        letter-spacing: .02em !important; text-transform: none !important;
        width: auto !important; min-width: 0 !important;
        box-shadow: none !important; animation: none !important;
    }
    .adv-pills div[data-testid="stButton"] > button:hover {
        background: var(--accent-bg) !important;
        border-color: var(--accent) !important; color: var(--accent) !important;
    }

    /* Tame expander chrome */
    .stExpander { border: 1px solid var(--border) !important; border-radius: 8px !important; }
    .stExpander summary { font-size: .78rem !important; }

    /* Chat message tweaks */
    [data-testid="stChatMessageContent"] { font-size: .92rem; line-height: 1.65; }
    [data-testid="stChatMessage"] { background: transparent !important; }
    </style>
    """,
        unsafe_allow_html=True,
    )

    # ── Compact header ────────────────────────────────────────────────────────
    st.markdown(
        """
    <div class="adv-head">
        <div class="adv-eyebrow">Milestone 2 · Agentic AI</div>
        <div class="adv-title">CropCast Advisor · Chat with the Agent</div>
        <div class="adv-sub">Conversational agronomist · LangGraph + FAISS RAG + Claude. Upload a field report or ask anything about your farm.</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="page-content">', unsafe_allow_html=True)

    ctx = st.session_state.chat_farm_ctx

    # ── Status strip (always 5 chips, never wraps mid-row on desktop) ─────────
    risk_colors = {
        "Low Risk": "#a8e063",
        "Medium Risk": "#f5a623",
        "High Risk": "#ff6b6b",
    }
    band_colors = {
        "Excellent": "#a8e063",
        "Good": "#6abf3a",
        "Fair": "#f5a623",
        "Poor": "#ff6b6b",
    }

    def _chip(label, value, color="var(--text)"):
        return (
            f'<div class="adv-chip">'
            f'<div class="adv-chip-k">{label}</div>'
            f'<div class="adv-chip-v" style="color:{color};">{value}</div></div>'
        )

    yield_val = (
        f"{ctx.get('predicted_yield_tha')} t/ha"
        if ctx.get("predicted_yield_tha") is not None
        else "not run"
    )
    yield_col = (
        "var(--accent)"
        if ctx.get("predicted_yield_tha") is not None
        else "var(--text2)"
    )

    st.markdown(
        '<div class="adv-chips">'
        + _chip("Crop", ctx.get("crop") or "—")
        + _chip("Region", ctx.get("area") or "—")
        + _chip("Yield", yield_val, yield_col)
        + _chip(
            "Band",
            ctx.get("yield_band") or "—",
            band_colors.get(ctx.get("yield_band") or "", "var(--text)"),
        )
        + _chip(
            "Risk",
            ctx.get("yield_risk") or "—",
            risk_colors.get(ctx.get("yield_risk") or "", "var(--text)"),
        )
        + "</div>",
        unsafe_allow_html=True,
    )

    # ── Farm context + uploads (side-by-side expanders) ──────────────────────
    top_l, top_r = st.columns(2, gap="small")

    with top_l:
        with st.expander("🌾  Farm context", expanded=False):
            c1, c2 = st.columns(2)
            with c1:
                ctx["crop"] = st.selectbox(
                    "Crop",
                    CROPS,
                    index=CROPS.index(ctx["crop"]) if ctx["crop"] in CROPS else 0,
                    key="ch_crop",
                )
                ctx["area"] = st.selectbox(
                    "Region",
                    AREAS,
                    index=AREAS.index(ctx["area"]) if ctx["area"] in AREAS else 0,
                    key="ch_area",
                )
                ctx["year"] = st.number_input(
                    "Year", 1990, 2030, int(ctx["year"]), key="ch_year"
                )
            with c2:
                ctx["rainfall"] = st.number_input(
                    "Rainfall (mm/yr)",
                    0.0,
                    5000.0,
                    float(ctx["rainfall"]),
                    10.0,
                    key="ch_rain",
                )
                ctx["temperature"] = st.number_input(
                    "Avg temp (°C)",
                    -10.0,
                    50.0,
                    float(ctx["temperature"]),
                    0.5,
                    key="ch_temp",
                )
                ctx["pesticides"] = st.number_input(
                    "Pesticides (t)",
                    0.0,
                    50000.0,
                    float(ctx["pesticides"]),
                    10.0,
                    key="ch_pest",
                )

            cc1, cc2 = st.columns(2)
            with cc1:
                if st.button(
                    "Run ML prediction", use_container_width=True, key="ch_predict"
                ):
                    with st.spinner("Running Random Forest..."):
                        out = _ensure_yield_prediction(ctx)
                    if out.get("error"):
                        st.error(f"Prediction error: {out['error']}")
                    else:
                        st.success(
                            f"{ctx['predicted_yield_tha']} t/ha · "
                            f"{ctx['yield_band']} · {ctx['yield_risk']}"
                        )
            with cc2:
                if st.button(
                    "Reset context", use_container_width=True, key="ch_reset_ctx"
                ):
                    for k in (
                        "predicted_yield_tha",
                        "predicted_yield_hg",
                        "yield_band",
                        "yield_risk",
                        "benchmark_avg",
                    ):
                        ctx[k] = None
                    st.rerun()

    with top_r:
        with st.expander("📎  Upload field reports (PDF / TXT)", expanded=False):
            files = st.file_uploader(
                "Drop files — the agent reads them alongside its knowledge base.",
                type=["pdf", "txt", "md"],
                accept_multiple_files=True,
                key="ch_files",
                label_visibility="collapsed",
            )
            if files:
                text, names = _extract_uploaded_text(files)
                st.session_state.chat_uploaded_text = text
                st.session_state.chat_uploaded_names = names
                chars = len(text)
                st.success(f"Loaded {len(names)} file(s) · {chars:,} chars.")
            if st.session_state.chat_uploaded_names:
                st.caption(
                    "Active: "
                    + ", ".join(f"`{n}`" for n in st.session_state.chat_uploaded_names)
                )
                if st.button(
                    "Remove uploaded docs",
                    use_container_width=True,
                    key="ch_clear_files",
                ):
                    st.session_state.chat_uploaded_text = ""
                    st.session_state.chat_uploaded_names = []
                    st.rerun()

    # ── Chat toolbar (uniform 2-button row) ───────────────────────────────────
    st.markdown('<div class="adv-toolbar">', unsafe_allow_html=True)
    tb1, tb2, _tb_spacer = st.columns([0.22, 0.28, 0.50])
    with tb1:
        if st.button("🧹  New chat", use_container_width=True, key="ch_reset"):
            st.session_state.chat_messages = []
            st.rerun()
    with tb2:
        if st.button(
            "📋  Structured report",
            use_container_width=True,
            key="ch_full_report",
            help="Run the full LangGraph pipeline and post a structured advisory into the chat.",
        ):
            _run_structured_report_into_chat(ctx)
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Chat history render ───────────────────────────────────────────────────
    _SUGGESTIONS = [
        "Give me a full advisory for my current farm.",
        "What are the biggest risks to my yield this season?",
        "Which pests should I watch for right now?",
        "How should I plan irrigation for the next 4 weeks?",
        "Summarise the uploaded report and flag anything concerning.",
    ]

    if not st.session_state.chat_messages:
        st.markdown(
            '<div class="adv-empty">'
            "<h3>Hi, I'm CropCast Advisor.</h3>"
            "<p>Set your farm context, upload a field report, then ask me anything — "
            "yield drivers, irrigation plans, pest risks, or fertilizer timing.</p>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.markdown('<div class="adv-pills">', unsafe_allow_html=True)
        pcols = st.columns(len(_SUGGESTIONS))
        for i, (col, s) in enumerate(zip(pcols, _SUGGESTIONS)):
            with col:
                if st.button(s, key=f"ch_sugg_{i}", use_container_width=True):
                    st.session_state["__pending_prompt"] = s
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    for m in st.session_state.chat_messages:
        with st.chat_message(
            m["role"], avatar="🌾" if m["role"] == "assistant" else None
        ):
            st.markdown(m["content"])
            if m["role"] == "assistant" and m.get("sources"):
                with st.expander("📚  References used in this reply"):
                    for s in m["sources"]:
                        st.caption(f"• {s}")

    # ── Chat input + handler ──────────────────────────────────────────────────
    pending = st.session_state.pop("__pending_prompt", None)
    prompt = st.chat_input("Ask the agent about your farm…") or pending

    if prompt:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            st.warning(
                "`ANTHROPIC_API_KEY` not set — the agent will use a local (non-LLM) fallback response. "
                "Add the key to your `.env` to unlock full reasoning."
            )

        # Append user message + render immediately
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Build api-safe history (role/content only)
        api_history = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.chat_messages
            if m["role"] in ("user", "assistant")
        ]

        with st.chat_message("assistant", avatar="🌾"):
            placeholder = st.empty()
            placeholder.markdown("_Thinking…_")
            try:
                from agent.graph import run_chat

                result = run_chat(
                    messages=api_history,
                    farm_ctx=ctx,
                    uploaded_docs_text=st.session_state.chat_uploaded_text,
                )
            except Exception as e:
                placeholder.empty()
                st.error(f"Agent error: {e}")
                st.session_state.chat_messages.append(
                    {
                        "role": "assistant",
                        "content": f"I hit an error while reasoning: `{e}`. "
                        "Please check the Anthropic API key / network and try again.",
                        "sources": [],
                    }
                )
                return

            if result.get("error") and not result.get("assistant_reply"):
                reply = f"⚠️ {result['error']}"
                sources = []
            else:
                reply = (
                    result.get("assistant_reply")
                    or "I wasn't able to generate a response."
                )
                sources = result.get("source_files") or []

            placeholder.markdown(reply)
            if sources:
                with st.expander("📚  References used in this reply"):
                    for s in sources:
                        st.caption(f"• {s}")

        st.session_state.chat_messages.append(
            {
                "role": "assistant",
                "content": reply,
                "sources": sources,
            }
        )

    st.markdown("</div>", unsafe_allow_html=True)


def _run_structured_report_into_chat(ctx: dict) -> None:
    """Run the full LangGraph advisory pipeline and push a structured message into the chat."""
    try:
        from agent.graph import run_agent
    except Exception as e:
        st.session_state.chat_messages.append(
            {
                "role": "assistant",
                "content": f"Could not import agent: `{e}`",
                "sources": [],
            }
        )
        return

    user_msg = (
        f"Generate a full structured advisory for {ctx.get('crop','my crop')} "
        f"in {ctx.get('area','my region')}."
    )
    st.session_state.chat_messages.append({"role": "user", "content": user_msg})

    try:
        result = run_agent(
            crop=ctx.get("crop", "Wheat"),
            area=ctx.get("area", "India"),
            year=int(ctx.get("year", 2024) or 2024),
            rainfall=float(ctx.get("rainfall", 0) or 0),
            temperature=float(ctx.get("temperature", 0) or 0),
            pesticides=float(ctx.get("pesticides", 0) or 0),
            user_query=user_msg,
        )
    except Exception as e:
        st.session_state.chat_messages.append(
            {
                "role": "assistant",
                "content": f"Pipeline error: `{e}`",
                "sources": [],
            }
        )
        return

    # Sync predictions back into chat context
    ctx["predicted_yield_tha"] = result.get("predicted_yield_tha") or ctx.get(
        "predicted_yield_tha"
    )
    ctx["predicted_yield_hg"] = result.get("predicted_yield_hg") or ctx.get(
        "predicted_yield_hg"
    )
    ctx["yield_band"] = result.get("yield_band") or ctx.get("yield_band")
    ctx["yield_risk"] = result.get("yield_risk") or ctx.get("yield_risk")
    ctx["benchmark_avg"] = result.get("benchmark_avg") or ctx.get("benchmark_avg")

    if result.get("error"):
        st.session_state.chat_messages.append(
            {
                "role": "assistant",
                "content": f"⚠️ {result['error']}",
                "sources": [],
            }
        )
        return

    # Format as markdown
    md = []
    md.append("## Structured Farm Advisory\n")
    md.append(
        f"**Crop & field snapshot** — {ctx.get('crop')} in {ctx.get('area')}, "
        f"year {ctx.get('year')} · rainfall {ctx.get('rainfall')} mm · "
        f"temp {ctx.get('temperature')} °C · pesticides {ctx.get('pesticides')} t.\n"
    )
    md.append(
        f"**Predicted yield:** {result.get('predicted_yield_tha','—')} t/ha  \n"
        f"**Band:** {result.get('yield_band','—')}  ·  "
        f"**Risk:** {result.get('yield_risk','—')}  ·  "
        f"**Crop benchmark:** ~{result.get('benchmark_avg','—')} t/ha\n"
    )
    if result.get("field_summary"):
        md.append("### Field & Crop Summary\n" + result["field_summary"] + "\n")
    if result.get("recommendations"):
        md.append("### Recommended Actions")
        for i, r in enumerate(result["recommendations"], 1):
            md.append(f"{i}. {r}")
        md.append("")
    if result.get("sources"):
        md.append("### Agronomic References")
        for s in result["sources"]:
            md.append(f"> {s}")
        md.append("")
    if result.get("disclaimer"):
        md.append(f"> ⚠️ *{result['disclaimer']}*")

    st.session_state.chat_messages.append(
        {
            "role": "assistant",
            "content": "\n".join(md),
            "sources": result.get("source_files") or [],
        }
    )


# ══════════════════════════════════════════════════════════════════════════════
#  ROUTER
# ══════════════════════════════════════════════════════════════════════════════
render_sidebar()

if st.session_state.page == "model":
    page_model()
elif st.session_state.page == "loading":
    page_loading()
elif st.session_state.page == "results":
    page_results()
elif st.session_state.page == "insights":
    page_insights()
elif st.session_state.page == "advisory":
    page_advisory()
elif st.session_state.page == "about":
    page_about()

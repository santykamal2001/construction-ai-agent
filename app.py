"""
DEST AI Inspector — Professional Dashboard
Distinct Engineering Solutions, Inc.
"""
import json
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))

from src import database, vector_store
from src.agent import get_project_summary, query
from src.database import get_all_projects, get_project_stats
from src.processor import get_available_projects, process_project

st.set_page_config(
    page_title="DEST AI Inspector",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Design tokens — Clean Light Theme (Stripe × Notion × Linear) ─────────────
BG          = "#f8f9fc"
SURFACE     = "#ffffff"
SURFACE2    = "#f1f4f9"
SURFACE3    = "#e8edf5"
BORDER      = "#e2e8f0"
BORDER_MED  = "#cbd5e1"
ACCENT      = "#0ea5e9"        # sky blue — primary CTA
ACCENT_DIM  = "rgba(14,165,233,0.10)"
ACCENT2     = "#6366f1"        # indigo
ACCENT2_DIM = "rgba(99,102,241,0.10)"
GREEN       = "#10b981"
GREEN_DIM   = "rgba(16,185,129,0.10)"
AMBER       = "#f59e0b"
AMBER_DIM   = "rgba(245,158,11,0.10)"
DANGER      = "#ef4444"
DANGER_DIM  = "rgba(239,68,68,0.10)"
PURPLE      = "#8b5cf6"
PURPLE_DIM  = "rgba(139,92,246,0.10)"
TEXT        = "#0f172a"        # slate-900
TEXT_SUB    = "#475569"        # slate-600
TEXT_MUTED  = "#94a3b8"        # slate-400
SIDEBAR_BG  = "#1e293b"        # dark navy sidebar (contrast with light content)
SIDEBAR_TXT = "#e2e8f0"
SIDEBAR_MUTED = "#94a3b8"
SIDEBAR_SURFACE = "#273548"
SIDEBAR_BORDER  = "#334155"

CHART_THEME = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color=TEXT_SUB, family="'Plus Jakarta Sans', Inter, sans-serif", size=11),
    xaxis=dict(gridcolor="#e2e8f0", linecolor="#e2e8f0", tickcolor="#e2e8f0", showgrid=True),
    yaxis=dict(gridcolor="#e2e8f0", linecolor="#e2e8f0", tickcolor="#e2e8f0", showgrid=False),
    margin=dict(l=16, r=16, t=48, b=16),
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown(f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');

/* ── BASE ── */
html, body, [class*="css"], .stApp {{
    font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif !important;
    background-color: {BG} !important;
    color: {TEXT} !important;
}}

/* Hide ONLY the branding — keep header visible for sidebar toggle */
#MainMenu {{ visibility: hidden; }}
footer    {{ visibility: hidden; }}
header    {{ background: transparent !important; }}
[data-testid="stHeader"] {{ background: transparent !important; border-bottom: none !important; }}

/* Ensure sidebar collapse/expand button is always visible */
[data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"],
button[kind="header"],
.st-emotion-cache-1egp75h,
.st-emotion-cache-zq5wmm {{
    visibility: visible !important;
    opacity: 1 !important;
    display: flex !important;
}}

.block-container {{ padding: 1.2rem 2.4rem 3rem 2.4rem !important; max-width: 100% !important; }}

/* ── SIDEBAR (dark navy — beautiful contrast) ── */
[data-testid="stSidebar"] {{
    background: {SIDEBAR_BG} !important;
    border-right: 1px solid {SIDEBAR_BORDER} !important;
}}
[data-testid="stSidebar"] * {{ color: {SIDEBAR_TXT} !important; }}
[data-testid="stSidebar"] .stTextInput input {{
    background: {SIDEBAR_SURFACE} !important;
    border: 1px solid {SIDEBAR_BORDER} !important;
    border-radius: 8px !important;
    color: {SIDEBAR_TXT} !important;
    font-size: 13px !important;
}}
[data-testid="stSidebar"] div[data-baseweb="select"] > div {{
    background: {SIDEBAR_SURFACE} !important;
    border: 1px solid {SIDEBAR_BORDER} !important;
    color: {SIDEBAR_TXT} !important;
    border-radius: 8px !important;
}}
[data-testid="stSidebar"] hr {{
    border-color: {SIDEBAR_BORDER} !important; margin: 10px 0 !important; opacity: 1;
}}
[data-testid="stSidebar"] .stProgress > div > div > div > div {{
    background: linear-gradient(90deg, {ACCENT}, {ACCENT2}) !important;
}}
[data-testid="stSidebar"] .stProgress > div > div {{
    background: {SIDEBAR_SURFACE} !important;
}}
[data-testid="stSidebar"] [data-testid="stCheckbox"] label {{
    color: {SIDEBAR_MUTED} !important;
}}

/* ── TABS ── */
[data-testid="stTabs"] [data-baseweb="tab-list"] {{
    background: {SURFACE2} !important;
    border-radius: 10px !important;
    padding: 3px !important;
    border: 1px solid {BORDER} !important;
    gap: 2px !important;
    width: fit-content !important;
}}
[data-testid="stTabs"] [data-baseweb="tab"] {{
    background: transparent !important;
    border-radius: 7px !important;
    color: {TEXT_MUTED} !important;
    font-weight: 500 !important;
    font-size: 13px !important;
    padding: 7px 18px !important;
    border: none !important;
    transition: all 0.15s ease !important;
}}
[data-testid="stTabs"] [aria-selected="true"] {{
    background: {SURFACE} !important;
    color: {TEXT} !important;
    font-weight: 600 !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08), inset 0 1px 0 rgba(255,255,255,0.8) !important;
}}
[data-testid="stTabs"] [data-baseweb="tab-highlight"],
[data-testid="stTabs"] [data-baseweb="tab-border"] {{ display: none !important; }}

/* ── BUTTONS ── */
.stButton > button {{
    background: {SURFACE} !important;
    color: {TEXT_SUB} !important;
    border: 1px solid {BORDER_MED} !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    font-size: 13px !important;
    padding: 8px 16px !important;
    transition: all 0.15s ease !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
}}
.stButton > button:hover {{
    background: {SURFACE2} !important;
    border-color: {BORDER_MED} !important;
    color: {TEXT} !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08) !important;
}}
.stButton > button[kind="primary"] {{
    background: linear-gradient(135deg, {ACCENT} 0%, #0284c7 100%) !important;
    color: #ffffff !important;
    font-weight: 700 !important;
    border: none !important;
    box-shadow: 0 2px 10px rgba(14,165,233,0.30), inset 0 1px 0 rgba(255,255,255,0.15) !important;
}}
.stButton > button[kind="primary"]:hover {{
    background: linear-gradient(135deg, #38bdf8 0%, {ACCENT} 100%) !important;
    box-shadow: 0 5px 18px rgba(14,165,233,0.40) !important;
    transform: translateY(-1px) !important;
}}

/* ── INPUTS ── */
.stTextInput input, .stTextArea textarea {{
    background: {SURFACE} !important;
    border: 1.5px solid {BORDER} !important;
    border-radius: 10px !important;
    color: {TEXT} !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 14px !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04) !important;
    transition: border-color 0.15s, box-shadow 0.15s !important;
}}
.stTextInput input:focus, .stTextArea textarea:focus {{
    border-color: {ACCENT} !important;
    box-shadow: 0 0 0 3px rgba(14,165,233,0.12) !important;
}}
label, .stSelectbox label, .stTextInput label, .stTextArea label {{
    color: {TEXT_MUTED} !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.07em !important;
}}
.stTextArea textarea::placeholder, .stTextInput input::placeholder {{
    color: {TEXT_MUTED} !important;
}}

/* ── SELECTBOX ── */
div[data-baseweb="select"] > div {{
    background: {SURFACE} !important;
    border: 1.5px solid {BORDER} !important;
    border-radius: 8px !important;
    color: {TEXT} !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04) !important;
}}
div[data-baseweb="popover"] {{
    background: {SURFACE} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 8px !important;
    box-shadow: 0 8px 30px rgba(0,0,0,0.12) !important;
}}
div[data-baseweb="option"]:hover {{ background: {SURFACE2} !important; }}

/* ── METRICS ── */
[data-testid="metric-container"] {{
    background: {SURFACE} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 14px !important;
    padding: 18px 22px !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05) !important;
}}
[data-testid="metric-container"] [data-testid="stMetricLabel"] {{
    color: {TEXT_MUTED} !important;
    font-size: 11px !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    font-weight: 600 !important;
}}
[data-testid="metric-container"] [data-testid="stMetricValue"] {{
    color: {TEXT} !important;
    font-size: 28px !important;
    font-weight: 800 !important;
    letter-spacing: -0.03em !important;
}}

/* ── PROGRESS ── */
.stProgress > div > div > div > div {{
    background: linear-gradient(90deg, {ACCENT}, {ACCENT2}) !important;
    border-radius: 4px !important;
}}
.stProgress > div > div {{
    background: {SURFACE2} !important;
    border-radius: 4px !important;
    height: 5px !important;
}}

/* ── EXPANDER ── */
[data-testid="stExpander"] {{
    background: {SURFACE} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 10px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
}}
[data-testid="stExpander"] summary {{ color: {TEXT} !important; font-weight: 500 !important; font-size: 13px !important; }}

/* ── DATAFRAME ── */
[data-testid="stDataFrame"] {{
    background: {SURFACE} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 10px !important;
    overflow: hidden !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04) !important;
}}

/* ── MISC ── */
.stAlert {{ border-radius: 10px !important; font-size: 13px !important; }}
hr {{ border-color: {BORDER} !important; margin: 10px 0 !important; }}
.stSpinner > div {{ border-top-color: {ACCENT} !important; }}
[data-testid="stCheckbox"] label {{
    font-size: 13px !important; text-transform: none !important;
    letter-spacing: 0 !important; font-weight: 400 !important; color: {TEXT_SUB} !important;
}}

/* ══════════════════════════════════════════════════════
   CUSTOM COMPONENTS
══════════════════════════════════════════════════════ */

/* Sidebar logo */
.dest-logo {{
    display: flex; align-items: center; gap: 12px;
    padding: 20px 16px 16px;
}}
.dest-logo-icon {{
    width: 40px; height: 40px; border-radius: 10px;
    background: linear-gradient(135deg, {ACCENT} 0%, {ACCENT2} 100%);
    display: flex; align-items: center; justify-content: center;
    font-size: 18px; flex-shrink: 0;
    box-shadow: 0 4px 12px rgba(14,165,233,0.35);
}}
.dest-logo-title {{
    font-size: 14px; font-weight: 700; color: {SIDEBAR_TXT}; letter-spacing: -0.02em;
}}
.dest-logo-sub {{
    font-size: 9.5px; font-weight: 600; color: {ACCENT};
    text-transform: uppercase; letter-spacing: 0.1em; margin-top: 1px;
}}

/* Sidebar labels & stats */
.sidebar-label {{
    font-size: 10px; font-weight: 700; color: {SIDEBAR_MUTED};
    text-transform: uppercase; letter-spacing: 0.1em;
    padding: 10px 0 5px 0;
}}
.sidebar-stat {{
    background: {SIDEBAR_SURFACE}; border: 1px solid {SIDEBAR_BORDER};
    border-radius: 8px; padding: 9px 12px; margin: 3px 0;
    display: flex; justify-content: space-between; align-items: center;
}}
.sidebar-stat-label {{ font-size: 12px; color: {SIDEBAR_MUTED}; }}
.sidebar-stat-val   {{ font-size: 13px; font-weight: 700; color: {SIDEBAR_TXT}; }}
.sidebar-badge-green {{
    display: inline-flex; align-items: center; gap: 5px;
    background: rgba(16,185,129,0.15); border: 1px solid rgba(16,185,129,0.3);
    color: #34d399; border-radius: 6px; padding: 3px 9px;
    font-size: 11px; font-weight: 600;
}}
.sidebar-badge-red {{
    display: inline-flex; align-items: center; gap: 5px;
    background: rgba(239,68,68,0.15); border: 1px solid rgba(239,68,68,0.3);
    color: #f87171; border-radius: 6px; padding: 3px 9px;
    font-size: 11px; font-weight: 600;
}}

/* Page header */
.page-header {{
    display: flex; align-items: flex-start; justify-content: space-between;
    padding: 6px 0 18px;
    border-bottom: 1.5px solid {BORDER};
    margin-bottom: 22px;
}}
.page-title {{
    font-size: 24px; font-weight: 800; color: {TEXT};
    letter-spacing: -0.04em; line-height: 1.2;
}}
.page-sub {{
    font-size: 13px; color: {TEXT_MUTED}; margin-top: 4px; letter-spacing: -0.01em;
}}
.header-badges {{
    display: flex; gap: 7px; flex-wrap: wrap; align-items: center; padding-top: 4px;
}}

/* Section title */
.section-title {{
    font-size: 10.5px; font-weight: 700; color: {TEXT_MUTED};
    text-transform: uppercase; letter-spacing: 0.11em;
    margin: 22px 0 10px 0;
    display: flex; align-items: center; gap: 8px;
}}
.section-title::after {{
    content: ''; flex: 1; height: 1px;
    background: linear-gradient(90deg, {BORDER}, transparent);
}}

/* Badges */
.badge {{
    display: inline-flex; align-items: center; gap: 5px;
    border-radius: 6px; padding: 3px 9px;
    font-size: 11px; font-weight: 600; letter-spacing: 0.01em;
    white-space: nowrap;
}}
.badge-green  {{ background:{GREEN_DIM};  color:{GREEN};  border:1px solid rgba(16,185,129,0.25); }}
.badge-amber  {{ background:{AMBER_DIM};  color:{AMBER};  border:1px solid rgba(245,158,11,0.25); }}
.badge-red    {{ background:{DANGER_DIM}; color:{DANGER}; border:1px solid rgba(239,68,68,0.25);  }}
.badge-blue   {{ background:{ACCENT_DIM}; color:{ACCENT}; border:1px solid rgba(14,165,233,0.25); }}
.badge-purple {{ background:{PURPLE_DIM}; color:{PURPLE}; border:1px solid rgba(139,92,246,0.25); }}
.badge-gray   {{ background:rgba(148,163,184,0.12); color:{TEXT_MUTED}; border:1px solid rgba(148,163,184,0.25); }}

/* KPI cards */
.kpi-card {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 14px;
    padding: 20px 22px;
    position: relative; overflow: hidden;
    transition: border-color 0.2s, box-shadow 0.2s, transform 0.2s;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    height: 100%;
}}
.kpi-card:hover {{
    border-color: {BORDER_MED};
    box-shadow: 0 6px 20px rgba(0,0,0,0.09);
    transform: translateY(-2px);
}}
.kpi-accent-bar {{
    position: absolute; top: 0; left: 0; right: 0; height: 3px;
    border-radius: 14px 14px 0 0;
}}
.kpi-icon-wrap {{
    width: 34px; height: 34px; border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 16px; margin-bottom: 14px;
}}
.kpi-value {{
    font-size: 26px; font-weight: 800; color: {TEXT};
    letter-spacing: -0.04em; line-height: 1;
}}
.kpi-label {{
    font-size: 11px; font-weight: 600; color: {TEXT_MUTED};
    text-transform: uppercase; letter-spacing: 0.08em; margin-top: 7px;
}}
.kpi-sub {{ font-size: 11.5px; color: {TEXT_MUTED}; margin-top: 4px; }}

/* Chat */
.chat-row {{ display: flex; gap: 11px; align-items: flex-start; margin-bottom: 18px; }}
.chat-row.user {{ flex-direction: row-reverse; }}
.chat-avatar {{
    width: 30px; height: 30px; border-radius: 8px; flex-shrink: 0;
    display: flex; align-items: center; justify-content: center; font-size: 14px;
}}
.avatar-ai   {{ background: linear-gradient(135deg, #e0f2fe, {ACCENT}); }}
.avatar-user {{ background: linear-gradient(135deg, #ede9fe, {ACCENT2}); }}
.chat-content {{ flex: 1; max-width: calc(100% - 44px); }}
.chat-bubble {{
    padding: 13px 17px; border-radius: 14px;
    font-size: 13.5px; line-height: 1.75; color: {TEXT};
    word-break: break-word;
}}
.bubble-user {{
    background: {SURFACE2};
    border: 1px solid {BORDER};
    border-top-right-radius: 3px;
}}
.bubble-ai {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-top-left-radius: 3px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}}
.chat-meta-row {{
    display: flex; align-items: center; gap: 7px;
    margin-bottom: 7px; flex-wrap: wrap;
}}
.chat-ts {{ font-size: 10.5px; color: {TEXT_MUTED}; margin-top: 5px; }}
.chat-ts.right {{ text-align: right; }}

/* Safety banner */
.safety-banner {{
    background: {DANGER_DIM};
    border: 1px solid rgba(239,68,68,0.25);
    border-left: 3px solid {DANGER};
    border-radius: 0 10px 10px 0;
    padding: 10px 16px; margin: 6px 0;
    display: flex; align-items: center; gap: 10px;
    font-size: 13px; font-weight: 600; color: {DANGER};
}}

/* Quick pills */
.quick-pill {{
    display: inline-flex; align-items: center;
    background: {SURFACE}; border: 1px solid {BORDER};
    border-radius: 7px; padding: 6px 12px;
    font-size: 12px; font-weight: 500; color: {TEXT_SUB};
    cursor: pointer; margin: 2px;
    transition: all 0.15s ease;
}}
.quick-pill:hover {{ border-color: {ACCENT}; color: {ACCENT}; background: {ACCENT_DIM}; }}

/* Session history */
.history-item {{
    background: {SURFACE}; border: 1px solid {BORDER};
    border-radius: 10px; padding: 10px 13px; margin: 4px 0;
    display: flex; align-items: flex-start; gap: 10px;
    transition: border-color 0.15s, box-shadow 0.15s;
}}
.history-item:hover {{ border-color: {BORDER_MED}; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
.history-dot {{ width: 7px; height: 7px; border-radius: 50%; margin-top: 5px; flex-shrink: 0; }}
.history-q {{ font-size: 12px; font-weight: 500; color: {TEXT}; line-height: 1.4; }}
.history-meta {{ font-size: 10.5px; color: {TEXT_MUTED}; margin-top: 2px; }}

/* Empty state */
.empty-state {{
    text-align: center; padding: 36px 20px;
    background: {SURFACE}; border: 1.5px dashed {BORDER};
    border-radius: 14px; margin: 10px 0;
}}
.empty-icon {{ font-size: 28px; opacity: 0.35; margin-bottom: 10px; }}
.empty-text {{ font-size: 13px; color: {TEXT_MUTED}; }}

/* Thin divider */
.thin-divider {{ height: 1px; background: {BORDER}; margin: 16px 0; }}

/* Info box */
.info-box {{
    background: {ACCENT_DIM}; border: 1px solid rgba(14,165,233,0.2);
    border-radius: 10px; padding: 13px 18px;
    font-size: 13px; color: {TEXT_SUB}; margin-bottom: 16px;
}}

/* Welcome hero */
.welcome-hero {{
    background: linear-gradient(145deg, #ffffff 0%, #f0f7ff 60%, #f5f0ff 100%);
    border: 1px solid {BORDER}; border-radius: 20px;
    padding: 52px 44px; text-align: center; margin: 10px 0 28px;
    position: relative; overflow: hidden;
    box-shadow: 0 4px 24px rgba(0,0,0,0.05);
}}
.welcome-hero::before {{
    content: ''; position: absolute; top: -80px; right: -80px;
    width: 280px; height: 280px; border-radius: 50%;
    background: radial-gradient(circle, rgba(14,165,233,0.08) 0%, transparent 70%);
}}
.welcome-hero::after {{
    content: ''; position: absolute; bottom: -80px; left: -60px;
    width: 240px; height: 240px; border-radius: 50%;
    background: radial-gradient(circle, rgba(99,102,241,0.07) 0%, transparent 70%);
}}
.welcome-icon {{ font-size: 52px; margin-bottom: 14px; display: block; position: relative; z-index: 1; }}
.welcome-title {{
    font-size: 30px; font-weight: 800; color: {TEXT};
    letter-spacing: -0.04em; margin-bottom: 12px; position: relative; z-index: 1;
}}
.welcome-sub {{
    font-size: 15px; color: {TEXT_SUB}; line-height: 1.7;
    max-width: 500px; margin: 0 auto; position: relative; z-index: 1;
}}

/* Feature cards */
.feature-card {{
    background: {SURFACE}; border: 1px solid {BORDER};
    border-radius: 14px; padding: 22px 20px; height: 100%;
    transition: border-color 0.2s, transform 0.2s, box-shadow 0.2s;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}}
.feature-card:hover {{
    border-color: {BORDER_MED}; transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(0,0,0,0.08);
}}
.feature-num {{
    width: 26px; height: 26px; border-radius: 7px;
    background: {ACCENT_DIM}; border: 1px solid rgba(14,165,233,0.2);
    display: inline-flex; align-items: center; justify-content: center;
    font-size: 11px; font-weight: 700; color: {ACCENT}; margin-bottom: 12px;
}}
.feature-icon {{ font-size: 22px; margin-bottom: 10px; display: block; }}
.feature-title {{ font-size: 14px; font-weight: 700; color: {TEXT}; margin-bottom: 8px; }}
.feature-desc {{ font-size: 12px; color: {TEXT_SUB}; line-height: 1.65; }}

/* Pipeline blocks */
.pipe-block {{
    background: {SURFACE}; border: 1px solid {BORDER};
    border-radius: 12px; padding: 14px 18px; margin: 5px 0;
    display: flex; gap: 14px; align-items: flex-start;
    transition: border-color 0.15s, box-shadow 0.15s;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}}
.pipe-block:hover {{ border-color: {BORDER_MED}; box-shadow: 0 3px 12px rgba(0,0,0,0.07); }}
.pipe-icon {{
    width: 34px; height: 34px; border-radius: 8px; flex-shrink: 0;
    display: flex; align-items: center; justify-content: center; font-size: 15px;
}}
.pipe-title {{ font-size: 13px; font-weight: 700; color: {TEXT}; margin-bottom: 3px; }}
.pipe-desc {{ font-size: 12px; color: {TEXT_SUB}; line-height: 1.55; }}

/* Animations */
@keyframes fadeIn {{ from {{ opacity:0; transform:translateY(5px); }} to {{ opacity:1; transform:translateY(0); }} }}
.chat-row {{ animation: fadeIn 0.2s ease forwards; }}
@keyframes pulse {{ 0%,100% {{ opacity:1; }} 50% {{ opacity:0.35; }} }}
.live-dot {{
    display: inline-block; width: 6px; height: 6px; border-radius: 50%;
    background: {GREEN}; animation: pulse 2s infinite;
    margin-right: 4px; vertical-align: middle;
}}

</style>""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "session_queries" not in st.session_state:
    st.session_state.session_queries = []
if "quick_q" not in st.session_state:
    st.session_state.quick_q = ""

database.init_db()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div class="dest-logo">
        <div class="dest-logo-icon">🏗️</div>
        <div>
            <div class="dest-logo-title">DEST AI Inspector</div>
            <div class="dest-logo-sub">Distinct Engineering</div>
        </div>
    </div>""", unsafe_allow_html=True)

    st.divider()

    api_ok = bool(os.getenv("ANTHROPIC_API_KEY"))
    if api_ok:
        st.markdown('<span class="sidebar-badge-green"><span class="live-dot"></span>API Connected</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="sidebar-badge-red">⚠ API Key Missing — set ANTHROPIC_API_KEY in .env</span>', unsafe_allow_html=True)

    st.divider()

    st.markdown('<div class="sidebar-label">Project Folder</div>', unsafe_allow_html=True)
    sample_data_path = str(Path(__file__).parent / "sample_data")
    folder_path = st.text_input(
        "Folder", value=sample_data_path,
        placeholder="/path/to/projects", label_visibility="collapsed",
    )

    selected_project_name = None
    selected_project_path = None
    projects = []

    if folder_path and Path(folder_path).exists():
        projects = get_available_projects(folder_path)
        if projects:
            project_names = ["— Select a project —"] + [p.name for p in projects]
            sel = st.selectbox("Project", project_names, label_visibility="collapsed")
            if sel != "— Select a project —":
                selected_project_name = sel
                selected_project_path = next((str(p) for p in projects if p.name == sel), None)
        else:
            st.caption("No project folders found.")
    else:
        st.caption("Folder path not found.")

    st.divider()

    if selected_project_name:
        st.markdown('<div class="sidebar-label">Indexing</div>', unsafe_allow_html=True)
        force_reindex = st.checkbox("Force full reindex", help="Clears hash cache and re-extracts all files")

        if st.button("⬆  Index / Reindex Project", use_container_width=True, type="primary"):
            if force_reindex:
                for fp in database.get_project_file_paths(selected_project_name):
                    vector_store.delete_file_chunks(fp)
                database.reset_project_hashes(selected_project_name)
            with st.spinner("Indexing documents…"):
                pb = st.progress(0)
                st_txt = st.empty()

                def _prog(cur, tot, fname, stage=""):
                    pb.progress(int(cur / tot * 100) if tot else 0)
                    st_txt.caption(fname[:34] + "…" if len(fname) > 34 else fname)

                stats = process_project(selected_project_path, _prog)
                pb.progress(100)
                st_txt.empty()
            st.success(f"✓ {stats['processed']} indexed · {stats['skipped']} skipped · {stats['failed']} failed")

        st.divider()

        st.markdown('<div class="sidebar-label">Project Stats</div>', unsafe_allow_html=True)
        try:
            db_stats_sb = get_project_stats(selected_project_name)
            done_sb   = db_stats_sb.get("done", 0)
            total_sb  = db_stats_sb.get("total", 1) or 1
            chunks_sb = db_stats_sb.get("total_chunks", 0)
            failed_sb = db_stats_sb.get("failed", 0)

            st.progress(done_sb / total_sb)
            st.markdown(f"""
            <div class="sidebar-stat">
                <span class="sidebar-stat-label">Files indexed</span>
                <span class="sidebar-stat-val">{done_sb} / {total_sb}</span>
            </div>
            <div class="sidebar-stat">
                <span class="sidebar-stat-label">Knowledge chunks</span>
                <span class="sidebar-stat-val">{chunks_sb:,}</span>
            </div>
            <div class="sidebar-stat">
                <span class="sidebar-stat-label">Session queries</span>
                <span class="sidebar-stat-val">{len(st.session_state.session_queries)}</span>
            </div>""", unsafe_allow_html=True)
            if failed_sb:
                st.markdown(f'<span class="sidebar-badge-red" style="margin-top:6px">⚠ {failed_sb} file(s) failed</span>', unsafe_allow_html=True)
        except Exception:
            st.caption("Index a project to see stats.")

    st.divider()
    st.markdown(
        f'<div style="font-size:10px;color:{SIDEBAR_MUTED};padding:6px 0;text-align:center;">'
        'DEST AI Inspector v1.0<br>Powered by Claude Opus 4.6</div>',
        unsafe_allow_html=True,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────
def confidence_badge(score: float) -> str:
    pct = int(score * 100)
    if score >= 0.70:
        return f'<span class="badge badge-green">✓ High Confidence · {pct}%</span>'
    elif score >= 0.50:
        return f'<span class="badge badge-amber">◐ Medium · {pct}%</span>'
    else:
        return f'<span class="badge badge-red">✗ Low · {pct}%</span>'


def kpi_card(icon: str, icon_bg: str, accent: str, value, label: str, sub: str) -> str:
    return f"""
    <div class="kpi-card">
        <div class="kpi-accent-bar" style="background:linear-gradient(90deg,{accent},{accent}88)"></div>
        <div class="kpi-icon-wrap" style="background:{icon_bg}">{icon}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-label">{label}</div>
        <div class="kpi-sub">{sub}</div>
    </div>"""


def apply_chart(fig, height: int = 300):
    fig.update_layout(**CHART_THEME, height=height)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ══════════════════════════════════════════════════════════════════════════════
# WELCOME SCREEN
# ══════════════════════════════════════════════════════════════════════════════
if not selected_project_name:
    st.markdown(f"""
    <div class="welcome-hero">
        <span class="welcome-icon">🏗️</span>
        <div class="welcome-title">DEST AI Inspector</div>
        <div class="welcome-sub">
            AI-powered document intelligence for construction inspection teams at
            Distinct Engineering Solutions, Inc.<br>Select a project in the sidebar to get started.
        </div>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="section-title">How It Works</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4, gap="small")
    steps = [
        ("01", "📂", "Select Project",    "Choose a project folder containing inspection reports, PDFs, drawings, and field data."),
        ("02", "⚡", "Index Documents",   "AI reads all files — PDF, Word, Excel, PowerPoint — and builds a searchable knowledge base."),
        ("03", "💬", "Ask Questions",     "Ask anything in plain English. The AI retrieves the most relevant document sections instantly."),
        ("04", "📊", "Get Cited Answers", "Receive precise answers with source citations, confidence scores, and safety flags."),
    ]
    for col, (num, icon, title, desc) in zip([c1, c2, c3, c4], steps):
        with col:
            st.markdown(f"""
            <div class="feature-card">
                <div class="feature-num">{num}</div>
                <span class="feature-icon">{icon}</span>
                <div class="feature-title">{title}</div>
                <div class="feature-desc">{desc}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown('<div class="section-title" style="margin-top:28px">Example Questions</div>', unsafe_allow_html=True)
    sample_qs = [
        "🔍 What were the main inspection findings?",
        "⚠️ Any safety issues requiring immediate action?",
        "👷 Who worked on this project?",
        "🔧 What repairs are recommended?",
        "📊 What is the structural condition rating?",
        "🧱 What materials were used for fireproofing?",
        "📅 What inspections occurred last month?",
        "🧪 What tests were performed on site?",
    ]
    pills = "".join(f'<span class="quick-pill">{q}</span>' for q in sample_qs)
    st.markdown(f'<div style="padding:4px 0">{pills}</div>', unsafe_allow_html=True)

else:
    # ── Project header ────────────────────────────────────────────────────────
    try:
        _hstats  = get_project_stats(selected_project_name)
        _chunks  = _hstats.get("total_chunks", 0)
        _indexed = _hstats.get("done", 0)
        _total   = _hstats.get("total", 0)
    except Exception:
        _chunks = _indexed = _total = 0

    st.markdown(f"""
    <div class="page-header">
        <div>
            <div class="page-title">{selected_project_name}</div>
            <div class="page-sub">Construction Inspection Intelligence · {datetime.now().strftime("%B %d, %Y")}</div>
        </div>
        <div class="header-badges">
            <span class="badge badge-green"><span class="live-dot"></span>Live</span>
            <span class="badge badge-blue">📁 {_indexed}/{_total} Files</span>
            <span class="badge badge-gray">⊞ {_chunks:,} Chunks</span>
        </div>
    </div>""", unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs([
        "  💬  Ask AI  ",
        "  📊  Analytics  ",
        "  📄  Summary  ",
        "  ⚙️  System  ",
    ])

    # ════════════════════════════════════════════════════════════════════════
    # TAB 1 — ASK AI
    # ════════════════════════════════════════════════════════════════════════
    with tab1:
        left_col, right_col = st.columns([3, 1], gap="large")

        with left_col:
            st.markdown('<div class="section-title">Quick Questions</div>', unsafe_allow_html=True)
            quick_qs = [
                "Main inspection findings?",
                "Safety issues requiring action?",
                "Recommended repairs?",
                "Structural condition rating?",
                "Who worked on this project?",
                "Project scope and location?",
                "Materials used?",
                "Tests performed on site?",
            ]
            qcols = st.columns(4)
            for idx, qtext in enumerate(quick_qs):
                with qcols[idx % 4]:
                    if st.button(qtext, key=f"qq_{idx}", use_container_width=True):
                        st.session_state.quick_q = qtext

            st.markdown('<div class="thin-divider"></div>', unsafe_allow_html=True)

            user_question = st.text_area(
                "question",
                value=st.session_state.get("quick_q", ""),
                placeholder="Ask anything about this project — e.g. Who performed the density test on 12/19/2025?",
                height=90,
                key="question_input",
                label_visibility="collapsed",
            )

            b1, b2, _b3 = st.columns([1.1, 1.0, 4.5])
            ask_clicked = b1.button("Ask AI", type="primary", use_container_width=True)
            if b2.button("Clear Chat", use_container_width=True):
                st.session_state.chat_history = []
                st.session_state.session_queries = []
                st.session_state.quick_q = ""
                st.rerun()

            if ask_clicked and user_question.strip():
                if not api_ok:
                    st.markdown('<div class="safety-banner">⚠ API key not found. Set ANTHROPIC_API_KEY in your .env file and restart the app.</div>', unsafe_allow_html=True)
                else:
                    st.session_state.chat_history.append({
                        "role": "user",
                        "content": user_question,
                        "time": datetime.now().strftime("%H:%M"),
                    })
                    with st.spinner("Searching documents and generating answer…"):
                        result = query(user_question, project_folder=selected_project_name, n_results=8)

                    safety_flag = any(
                        w in result["answer"].lower()
                        for w in ["safety", "immediate", "priority 1", "hazard", "danger", "urgent"]
                    )
                    database.log_query(
                        project_folder=selected_project_name,
                        question=user_question,
                        answer_preview=result["answer"][:300],
                        chunks_used=result["chunks_used"],
                        top_score=result["top_relevance_score"],
                        mean_score=result["mean_relevance_score"],
                        min_score=result["min_relevance_score"],
                        source_files=result["source_files"],
                        latency_ms=result["latency_ms"],
                        had_safety=safety_flag,
                    )
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": result["answer"],
                        "sources": result["sources"],
                        "safety": safety_flag,
                        "meta": {
                            "score": result["mean_relevance_score"],
                            "chunks": result["chunks_used"],
                            "latency": result["latency_ms"],
                        },
                        "time": datetime.now().strftime("%H:%M"),
                    })
                    st.session_state.session_queries.append({
                        "question": user_question[:80],
                        "mean_score": result["mean_relevance_score"],
                        "latency_ms": result["latency_ms"],
                        "time": datetime.now().strftime("%H:%M"),
                    })
                    st.session_state.quick_q = ""

            elif ask_clicked:
                st.caption("Please enter a question first.")

            # ── Chat thread ──────────────────────────────────────────────
            if st.session_state.chat_history:
                st.markdown('<div class="thin-divider"></div>', unsafe_allow_html=True)
                for msg in reversed(st.session_state.chat_history):
                    if msg["role"] == "user":
                        st.markdown(f"""
                        <div class="chat-row user">
                            <div class="chat-avatar avatar-user">👤</div>
                            <div class="chat-content">
                                <div class="chat-bubble bubble-user">{msg["content"]}</div>
                                <div class="chat-ts right">{msg.get("time","")}</div>
                            </div>
                        </div>""", unsafe_allow_html=True)
                    else:
                        meta   = msg.get("meta", {})
                        score  = meta.get("score", 0)
                        chunks = meta.get("chunks", 0)
                        lat    = meta.get("latency", 0)

                        if msg.get("safety"):
                            st.markdown('<div class="safety-banner">⚠ Safety-critical information detected — review carefully before proceeding.</div>', unsafe_allow_html=True)

                        conf_b  = confidence_badge(score)
                        lat_b   = f'<span class="badge badge-gray">⏱ {lat}ms</span>'
                        chunk_b = f'<span class="badge badge-blue">⊞ {chunks} chunks</span>'
                        body    = msg["content"].replace("\n", "<br>")

                        st.markdown(f"""
                        <div class="chat-row">
                            <div class="chat-avatar avatar-ai">🤖</div>
                            <div class="chat-content">
                                <div class="chat-meta-row">{conf_b} {lat_b} {chunk_b}</div>
                                <div class="chat-bubble bubble-ai">{body}</div>
                                <div class="chat-ts">{msg.get("time","")}</div>
                            </div>
                        </div>""", unsafe_allow_html=True)

                        sources = msg.get("sources", [])
                        if sources:
                            with st.expander(f"📄 Source Documents · {len(sources)} chunks retrieved"):
                                import pandas as pd
                                src_df = pd.DataFrame([{
                                    "Document": s["file_name"],
                                    "Match":    s["relevance_score"],
                                    "Preview":  (s["excerpt"][:120] + "…") if len(s["excerpt"]) > 120 else s["excerpt"],
                                } for s in sources])
                                st.dataframe(
                                    src_df, use_container_width=True, hide_index=True,
                                    column_config={"Match": st.column_config.ProgressColumn(
                                        "Match", min_value=0, max_value=1, format="%.0%"
                                    )},
                                )
            else:
                st.markdown(f"""
                <div class="empty-state">
                    <div class="empty-icon">💬</div>
                    <div class="empty-text">Use a quick question above or type your own to start the conversation.</div>
                </div>""", unsafe_allow_html=True)

        with right_col:
            st.markdown('<div class="section-title">This Session</div>', unsafe_allow_html=True)
            if st.session_state.session_queries:
                for item in reversed(st.session_state.session_queries[-12:]):
                    score_pct = int(item["mean_score"] * 100)
                    dot_color = GREEN if item["mean_score"] >= 0.7 else (AMBER if item["mean_score"] >= 0.5 else DANGER)
                    st.markdown(f"""
                    <div class="history-item">
                        <div class="history-dot" style="background:{dot_color}"></div>
                        <div>
                            <div class="history-q">{item["question"]}</div>
                            <div class="history-meta">{item["time"]} · {score_pct}% · {item["latency_ms"]}ms</div>
                        </div>
                    </div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="empty-state">
                    <div class="empty-icon">📋</div>
                    <div class="empty-text">No queries yet this session.</div>
                </div>""", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    # TAB 2 — ANALYTICS
    # ════════════════════════════════════════════════════════════════════════
    with tab2:
        import pandas as pd
        import plotly.express as px
        import plotly.graph_objects as go

        db_stats  = get_project_stats(selected_project_name)
        q_summary = database.get_query_metrics_summary(selected_project_name)
        history   = database.get_query_history(selected_project_name, limit=200)

        done_files   = db_stats.get("done", 0)
        total_chunks = db_stats.get("total_chunks", 0)
        total_q      = int(q_summary.get("total_queries") or 0)
        avg_rel      = q_summary.get("avg_relevance") or 0
        avg_lat      = q_summary.get("avg_latency_ms") or 0
        safety_count = int(q_summary.get("safety_count") or 0)

        st.markdown('<div class="section-title">Knowledge Base Overview</div>', unsafe_allow_html=True)
        k1, k2, k3, k4, k5 = st.columns(5)
        with k1:
            st.markdown(kpi_card("📁", ACCENT2_DIM, ACCENT2, done_files, "Files Indexed", "in knowledge base"), unsafe_allow_html=True)
        with k2:
            st.markdown(kpi_card("⊞", ACCENT_DIM, ACCENT, f"{total_chunks:,}", "Text Chunks", "searchable segments"), unsafe_allow_html=True)
        with k3:
            st.markdown(kpi_card("🔍", PURPLE_DIM, PURPLE, total_q, "Total Queries", "questions asked"), unsafe_allow_html=True)
        with k4:
            rel_val = f"{int(avg_rel * 100)}%" if avg_rel else "—"
            st.markdown(kpi_card("🎯", AMBER_DIM, AMBER, rel_val, "Avg Retrieval Score", "across all queries"), unsafe_allow_html=True)
        with k5:
            lat_val   = f"{int(avg_lat)}ms" if avg_lat else "—"
            lat_color = DANGER if avg_lat > 2000 else GREEN
            lat_bg    = DANGER_DIM if avg_lat > 2000 else GREEN_DIM
            st.markdown(kpi_card("⚡", lat_bg, lat_color, lat_val, "Avg Response Time", "end-to-end latency"), unsafe_allow_html=True)

        st.markdown('<div class="section-title">Document Coverage</div>', unsafe_allow_html=True)
        try:
            with database.get_connection() as conn:
                file_rows = conn.execute("""
                    SELECT file_name, extension, file_size, status, chunk_count, processed_at
                    FROM files WHERE project_folder = ? ORDER BY chunk_count DESC
                """, (selected_project_name,)).fetchall()
        except Exception:
            file_rows = []

        if file_rows:
            file_df = pd.DataFrame([dict(r) for r in file_rows])

            fc1, fc2 = st.columns([2, 1], gap="medium")
            with fc1:
                plot_df = file_df[file_df["chunk_count"] > 0].copy()
                plot_df["short_name"] = plot_df["file_name"].apply(lambda x: x[:42] + "…" if len(x) > 42 else x)
                fig = px.bar(
                    plot_df, x="chunk_count", y="short_name", orientation="h",
                    title="Chunks per Document",
                    labels={"chunk_count": "Chunks", "short_name": ""},
                    color="chunk_count",
                    color_continuous_scale=[[0, "#bfdbfe"], [0.5, ACCENT2], [1, ACCENT]],
                )
                fig.update_layout(**CHART_THEME, height=320, coloraxis_showscale=False,
                                  title_font_size=12, title_font_color=TEXT_MUTED)
                fig.update_traces(marker_line_width=0)
                apply_chart(fig, 320)

            with fc2:
                ext_df = file_df.groupby("extension")["chunk_count"].sum().reset_index()
                ext_df.columns = ["Type", "Chunks"]
                fig2 = px.pie(
                    ext_df, values="Chunks", names="Type",
                    title="By File Type", hole=0.58,
                    color_discrete_sequence=[ACCENT, ACCENT2, AMBER, PURPLE, DANGER],
                )
                fig2.update_traces(textfont_size=11,
                                   marker=dict(line=dict(color="#ffffff", width=2)))
                fig2.update_layout(**CHART_THEME, height=320,
                                   title_font_size=12, title_font_color=TEXT_MUTED,
                                   legend=dict(font_color=TEXT_MUTED, bgcolor="rgba(0,0,0,0)", font_size=11))
                apply_chart(fig2, 320)

            st.markdown('<div class="section-title">File Details</div>', unsafe_allow_html=True)
            disp = file_df.copy()
            disp["file_size"] = disp["file_size"].apply(lambda x: f"{x/1024:.1f} KB" if x else "—")
            disp["processed_at"] = disp["processed_at"].apply(
                lambda x: datetime.fromtimestamp(x).strftime("%b %d, %Y %H:%M") if x else "—"
            )
            disp = disp.rename(columns={
                "file_name": "Document", "extension": "Type", "file_size": "Size",
                "status": "Status", "chunk_count": "Chunks", "processed_at": "Last Indexed",
            })
            max_chunks = int(disp["Chunks"].max()) if len(disp) else 1
            st.dataframe(disp, use_container_width=True, hide_index=True,
                column_config={"Chunks": st.column_config.ProgressColumn(
                    "Chunks", min_value=0, max_value=max_chunks, format="%d"
                )})
        else:
            st.markdown(f'<div class="empty-state"><div class="empty-icon">📁</div><div class="empty-text">No documents indexed yet.</div></div>', unsafe_allow_html=True)

        st.markdown('<div class="section-title">Retrieval Performance</div>', unsafe_allow_html=True)

        if not history:
            st.markdown(f'<div class="empty-state"><div class="empty-icon">📊</div><div class="empty-text">No queries yet — ask questions in the Ask AI tab to populate analytics.</div></div>', unsafe_allow_html=True)
        else:
            hist_df = pd.DataFrame(history)
            hist_df["asked_at_dt"] = pd.to_datetime(hist_df["asked_at"], unit="s")

            pc1, pc2 = st.columns(2, gap="medium")
            with pc1:
                fig_hist = px.histogram(
                    hist_df, x="mean_relevance_score", nbins=16,
                    title="Retrieval Score Distribution",
                    labels={"mean_relevance_score": "Avg Score", "count": "Queries"},
                    color_discrete_sequence=[ACCENT],
                )
                fig_hist.add_vline(x=0.70, line_dash="dash", line_color=ACCENT2,
                                   annotation_text="High", annotation_font_color=ACCENT2,
                                   annotation_position="top right")
                fig_hist.add_vline(x=0.50, line_dash="dash", line_color=AMBER,
                                   annotation_text="Threshold", annotation_font_color=AMBER,
                                   annotation_position="top left")
                fig_hist.update_traces(marker_line_width=0, opacity=0.85)
                fig_hist.update_layout(**CHART_THEME, height=280, title_font_size=12, title_font_color=TEXT_MUTED)
                apply_chart(fig_hist, 280)

            with pc2:
                fig_lat = px.line(
                    hist_df.sort_values("asked_at_dt"),
                    x="asked_at_dt", y="latency_ms",
                    title="Response Latency Over Time",
                    labels={"asked_at_dt": "", "latency_ms": "ms"},
                    color_discrete_sequence=[ACCENT2],
                )
                fig_lat.add_hline(y=2000, line_dash="dot", line_color=DANGER,
                                  annotation_text="2s target", annotation_font_color=DANGER)
                fig_lat.update_traces(line_width=2, fill="tozeroy",
                                      fillcolor="rgba(99,102,241,0.06)")
                fig_lat.update_layout(**CHART_THEME, height=280, title_font_size=12, title_font_color=TEXT_MUTED)
                apply_chart(fig_lat, 280)

            sc1, sc2 = st.columns(2, gap="medium")
            with sc1:
                sorted_df = hist_df.sort_values("asked_at_dt")
                fig_score = go.Figure()
                for col_name, name, color in [
                    ("top_relevance_score",  "Top Score",  ACCENT),
                    ("mean_relevance_score", "Avg Score",  ACCENT2),
                    ("min_relevance_score",  "Min Score",  TEXT_MUTED),
                ]:
                    fig_score.add_trace(go.Scatter(
                        x=sorted_df["asked_at_dt"], y=sorted_df[col_name],
                        name=name, line=dict(color=color, width=2), mode="lines",
                    ))
                fig_score.update_layout(
                    **CHART_THEME, height=280,
                    title="Score Bands Over Time", title_font_size=12, title_font_color=TEXT_MUTED,
                    legend=dict(bgcolor="rgba(0,0,0,0)", font_color=TEXT_SUB, orientation="h",
                                yanchor="bottom", y=1.02, xanchor="right", x=1),
                )
                apply_chart(fig_score, 280)

            with sc2:
                all_files: list = []
                for row in history:
                    try:
                        all_files.extend(json.loads(row["source_files"] or "[]"))
                    except Exception:
                        pass
                if all_files:
                    top_files = Counter(all_files).most_common(8)
                    cited_df = pd.DataFrame(top_files, columns=["Document", "Citations"])
                    cited_df["Short"] = cited_df["Document"].apply(lambda x: x[:36] + "…" if len(x) > 36 else x)
                    fig_cited = px.bar(
                        cited_df, x="Citations", y="Short", orientation="h",
                        title="Most Cited Documents",
                        labels={"Citations": "Times cited", "Short": ""},
                        color="Citations",
                        color_continuous_scale=[[0, "#bfdbfe"], [1, ACCENT]],
                    )
                    fig_cited.update_traces(marker_line_width=0)
                    fig_cited.update_layout(**CHART_THEME, height=280, coloraxis_showscale=False,
                                            title_font_size=12, title_font_color=TEXT_MUTED)
                    apply_chart(fig_cited, 280)
                else:
                    st.markdown(f'<div class="empty-state"><div class="empty-icon">📄</div><div class="empty-text">No citation data yet.</div></div>', unsafe_allow_html=True)

            st.markdown('<div class="section-title">Query Log</div>', unsafe_allow_html=True)
            table_df = hist_df[["asked_at_dt", "question", "mean_relevance_score",
                                 "chunks_used", "latency_ms", "had_safety_flag"]].copy()
            table_df["asked_at_dt"] = table_df["asked_at_dt"].dt.strftime("%b %d %H:%M")
            table_df["question"]    = table_df["question"].str[:80]
            table_df = table_df.rename(columns={
                "asked_at_dt": "Time", "question": "Question",
                "mean_relevance_score": "Score", "chunks_used": "Chunks",
                "latency_ms": "Latency (ms)", "had_safety_flag": "Safety",
            })
            st.dataframe(table_df, use_container_width=True, hide_index=True,
                column_config={
                    "Score":  st.column_config.ProgressColumn("Score",  min_value=0, max_value=1, format="%.0%"),
                    "Safety": st.column_config.CheckboxColumn("⚠ Safety"),
                })

            csv_bytes = table_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇  Export Query Log as CSV",
                data=csv_bytes,
                file_name=f"{selected_project_name}_queries.csv",
                mime="text/csv",
            )

    # ════════════════════════════════════════════════════════════════════════
    # TAB 3 — PROJECT SUMMARY
    # ════════════════════════════════════════════════════════════════════════
    with tab3:
        st.markdown('<div class="section-title">AI Project Summary</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="info-box">💡 Generates a comprehensive AI summary from all indexed documents — '
            'covering project scope, personnel, findings, safety concerns, and recommendations.</div>',
            unsafe_allow_html=True,
        )
        if st.button("Generate Project Summary", type="primary"):
            if not api_ok:
                st.error("API key not found. Set ANTHROPIC_API_KEY in your .env file and restart the app.")
            else:
                with st.spinner("Analyzing all project documents…"):
                    summary = get_project_summary(selected_project_name)
                st.markdown(
                    f'<div class="chat-bubble bubble-ai" style="margin-top:20px">'
                    f'{summary.replace(chr(10), "<br>")}</div>',
                    unsafe_allow_html=True,
                )

    # ════════════════════════════════════════════════════════════════════════
    # TAB 4 — SYSTEM
    # ════════════════════════════════════════════════════════════════════════
    with tab4:
        st.markdown('<div class="section-title">Pipeline Architecture</div>', unsafe_allow_html=True)
        pipeline = [
            ("🔍", ACCENT2,  "Document Scanner",
             "Walks the project directory tree and registers all supported files (PDF, DOCX, XLSX, PPTX, TXT, CSV) in SQLite with size and metadata."),
            ("⚡", "#0ea5e9","Deduplication Engine",
             "Computes MD5 hash of first+last 1MB per file. Unchanged files are skipped — only new or modified documents are reprocessed."),
            ("📄", PURPLE,   "Multi-Format Extractor",
             "PDF → PyMuPDF with PaddleOCR fallback for scanned pages. DOCX → python-docx with tables. XLSX → openpyxl. PPTX → python-pptx."),
            ("✂️", ACCENT,   "Semantic Chunker",
             "Splits text into 800-char overlapping chunks (150-char overlap) with sentence-boundary awareness to preserve context integrity."),
            ("🧠", AMBER,    "Embedding Engine",
             "Encodes each chunk using sentence-transformers all-MiniLM-L6-v2 fully locally — no API key needed for indexing."),
            ("🗄️", DANGER,   "Vector Store",
             "Stores embeddings in ChromaDB with cosine similarity indexing. Chunk metadata: file path, project folder, chunk index."),
            ("🤖", GREEN,    "RAG Query Layer",
             "Question → fetch 16 candidates → deduplicate (Jaccard > 0.85) → cap 3 chunks/file → Claude Opus 4.6 → cited answer with confidence metrics."),
        ]
        for icon, color, title, desc in pipeline:
            st.markdown(f"""
            <div class="pipe-block">
                <div class="pipe-icon" style="background:linear-gradient(135deg,{color}18,{color}28);color:{color}">{icon}</div>
                <div>
                    <div class="pipe-title">{title}</div>
                    <div class="pipe-desc">{desc}</div>
                </div>
            </div>""", unsafe_allow_html=True)

        st.markdown('<div class="section-title" style="margin-top:26px">Production Roadmap</div>', unsafe_allow_html=True)
        roadmap = [
            ("🗄️", "PostgreSQL",     "Replace SQLite for concurrent multi-user access and full ACID transactions."),
            ("🔎", "Qdrant Cluster",  "Replace local ChromaDB for distributed, production-scale vector search."),
            ("⚙️", "Redis Job Queue", "Background indexing workers so large uploads never block the UI."),
            ("👁️", "File Watcher",    "Auto-reindex when new documents are added to the project folder."),
            ("☁️", "S3 / MinIO",      "Object storage for raw extracted text — avoid re-extraction on redeploy."),
            ("🔐", "OAuth2 + RBAC",   "User authentication with role-based access: Inspector / PM / Admin."),
            ("📱", "Mobile PWA",      "Responsive layout for field inspectors working from phones on-site."),
            ("📡", "Webhooks",        "Push notifications when safety-critical findings are detected in new docs."),
        ]
        r1, r2 = st.columns(2, gap="medium")
        for i, (icon, title, desc) in enumerate(roadmap):
            col = r1 if i % 2 == 0 else r2
            with col:
                st.markdown(f"""
                <div class="pipe-block" style="margin:4px 0">
                    <div class="pipe-icon" style="background:{SURFACE2};color:{ACCENT}">{icon}</div>
                    <div>
                        <div class="pipe-title">{title}</div>
                        <div class="pipe-desc">{desc}</div>
                    </div>
                </div>""", unsafe_allow_html=True)

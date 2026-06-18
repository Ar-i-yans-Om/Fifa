"""
Siuuumulator — FIFA WC 2026 AI Prediction Dashboard
Read-only Streamlit UI. Never calls the pipeline; reads fixtures/results/predictions JSON.
Run:  streamlit run app.py
"""

import re
from pathlib import Path

import streamlit as st

import ui_data as D
import share_card as SC

# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE CONFIG
# ═══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Siuuumulator · WC 2026",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ═══════════════════════════════════════════════════════════════════════════════
#  COLOUR PALETTE  —  dark theme
# ═══════════════════════════════════════════════════════════════════════════════
BG            = "#0d1117"
SURFACE       = "#161b22"
SURFACE2      = "#1c2128"
SURFACE3      = "#21262d"
BORDER        = "#30363d"
TEXT          = "#f0f6fc"
MUTED         = "#8b949e"
ACCENT        = "#00c96e"
ACCENT_SOFT   = "#0a2318"
ACCENT_BORDER = "#1a5c38"
BLUE          = "#388bfd"
BLUE_SOFT     = "#0d1f3d"
BLUE_BORDER   = "#1e3a6e"
WIN           = "#388bfd"
DRAW          = "#6e7681"
LOSS          = "#f59e0b"
GOLD          = "#d97706"
RED           = "#f85149"

# ═══════════════════════════════════════════════════════════════════════════════
#  CSS
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

html, body, [class*="css"] {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}}

/* ── Base ── */
.stApp {{ background-color: {BG} !important; }}
.main, .block-container {{ background: transparent !important; }}
.block-container {{ padding-top: 1.8rem; max-width: 1200px; }}

/* Scrollbar */
::-webkit-scrollbar {{ width: 5px; height: 5px; }}
::-webkit-scrollbar-track {{ background: {BG}; }}
::-webkit-scrollbar-thumb {{ background: {BORDER}; border-radius: 3px; }}

/* ── HEADER ── */
.app-header {{
    position: relative; overflow: hidden;
    background: linear-gradient(135deg, #0d2035 0%, {BG} 65%);
    border: 1px solid {BORDER}; border-radius: 14px;
    padding: 32px 40px; margin-bottom: 22px;
}}
.app-header .pitch-svg {{
    position: absolute; top: 0; right: 0;
    width: 280px; height: 100%; pointer-events: none;
}}
.app-header .header-tag {{
    font-size: 11px; font-weight: 700; letter-spacing: 2px;
    text-transform: uppercase; color: {ACCENT}; margin-bottom: 8px;
}}
.app-header h1 {{
    font-size: 40px; font-weight: 900; color: {TEXT};
    letter-spacing: -1.5px; margin: 0 0 8px 0; line-height: 1;
}}
.app-header .sub {{
    font-size: 13px; font-weight: 500; color: {MUTED};
    margin: 0; white-space: nowrap; line-height: 1.55;
}}

/* ── ACCURACY BANNER ── */
.acc-banner {{
    display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
    background: {SURFACE}; border: 1px solid {BORDER};
    border-radius: 10px; padding: 12px 18px; margin-bottom: 18px;
}}
.acc-banner .title {{
    font-size: 11px; font-weight: 700; letter-spacing: 1px;
    text-transform: uppercase; color: {MUTED}; margin-right: 6px;
    flex-shrink: 0;
}}
.acc-stat {{
    display: flex; flex-direction: column; align-items: center;
    background: {SURFACE2}; border: 1px solid {BORDER};
    border-radius: 8px; padding: 6px 16px; min-width: 80px;
}}
.acc-stat .k {{
    font-size: 9.5px; font-weight: 700; color: {MUTED};
    text-transform: uppercase; letter-spacing: 0.8px;
}}
.acc-stat .v {{
    font-size: 16px; font-weight: 800; color: {TEXT}; line-height: 1.2;
}}
.acc-stat .v.green {{ color: {ACCENT}; }}
.acc-stat .v.blue  {{ color: {BLUE}; }}

/* ── PERFORMANCE TABLE (per-matchday breakdown) ── */
.perf-card {{
    background: {SURFACE}; border: 1px solid {BORDER};
    border-radius: 10px; padding: 14px 18px; margin-bottom: 18px;
}}
.perf-card .title {{
    font-size: 11px; font-weight: 700; letter-spacing: 1px;
    text-transform: uppercase; color: {MUTED}; margin-bottom: 10px;
}}
.perf-table {{ width: 100%; border-collapse: collapse; }}
.perf-table th {{
    font-size: 9.5px; font-weight: 700; color: {MUTED};
    text-transform: uppercase; letter-spacing: 0.8px;
    text-align: center; padding: 4px 10px; white-space: nowrap;
}}
.perf-table th.lbl-col, .perf-table td.lbl-col {{
    text-align: left; padding-left: 2px;
}}
.perf-table td {{
    text-align: center; padding: 7px 10px; white-space: nowrap;
    border-top: 1px solid {BORDER};
}}
.perf-table td.lbl {{
    font-size: 12px; font-weight: 700; color: {TEXT};
}}
.perf-table td.lbl .sub {{
    font-size: 9.5px; font-weight: 500; color: {MUTED}; margin-left: 6px;
}}
.perf-table td.v {{ font-size: 15px; font-weight: 800; color: {TEXT}; }}
.perf-table td.v.green {{ color: {ACCENT}; }}
.perf-table td.v.blue  {{ color: {BLUE}; }}
.perf-table tr.overall td {{ border-top: none; }}
.perf-table tr.overall td.lbl {{ color: {ACCENT}; }}
.perf-table tr.md-row td.lbl {{ color: {MUTED}; font-weight: 600; }}

/* ── TABS ── */
.stTabs [data-baseweb="tab-list"] {{
    gap: 0; border-bottom: 1px solid {BORDER}; background: transparent;
}}
.stTabs [data-baseweb="tab"] {{
    font-weight: 600; font-size: 14px; color: {MUTED};
    padding: 10px 22px; border-radius: 0; background: transparent;
    border-bottom: 2px solid transparent;
}}
.stTabs [aria-selected="true"] {{
    color: {ACCENT} !important; border-bottom: 2px solid {ACCENT};
}}
.stTabs [aria-disabled="true"] {{ color: #3d444d !important; }}

/* ── BUTTONS (group selector + LIVE/PROJECTED toggle) ── */
[data-testid="stButton"] button {{
    border-radius: 9px !important; font-weight: 700 !important;
    font-size: 12.5px !important; letter-spacing: 0.3px !important;
    padding: 7px 10px !important; transition: all 0.13s ease !important;
    min-height: 0 !important;
}}
[data-testid="stButton"] button[kind="primary"],
button[data-testid="stBaseButton-primary"] {{
    background: {ACCENT} !important; color: #04130b !important;
    border: 1px solid {ACCENT} !important;
    box-shadow: 0 2px 12px rgba(0,201,110,0.28) !important;
}}
[data-testid="stButton"] button[kind="primary"]:hover,
button[data-testid="stBaseButton-primary"]:hover {{
    background: #00e07d !important; border-color: #00e07d !important;
}}
[data-testid="stButton"] button[kind="primary"] p,
button[data-testid="stBaseButton-primary"] p {{ color: #04130b !important; }}
[data-testid="stButton"] button[kind="secondary"],
button[data-testid="stBaseButton-secondary"] {{
    background: {SURFACE} !important; color: {MUTED} !important;
    border: 1px solid {BORDER} !important; box-shadow: none !important;
}}
[data-testid="stButton"] button[kind="secondary"]:hover,
button[data-testid="stBaseButton-secondary"]:hover {{
    color: {TEXT} !important; border-color: {ACCENT} !important;
}}
[data-testid="stButton"] button[kind="secondary"] p,
button[data-testid="stBaseButton-secondary"] p {{ color: inherit !important; }}

/* ── STANDINGS TABLE ── */
.tbl-card {{
    border: 1px solid {BORDER}; border-radius: 10px;
    padding: 16px 18px 12px; background: {SURFACE};
    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
}}
.tbl-card.dim {{ opacity: 0.25; }}
.tbl-head {{
    display: flex; justify-content: space-between;
    align-items: center; margin-bottom: 10px;
}}
.tbl-head .lbl {{
    font-size: 11px; font-weight: 700; letter-spacing: 1.5px;
    text-transform: uppercase; color: {BLUE};
}}
.tbl-head .lbl.pred {{ color: {GOLD}; }}
.badge {{
    font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 20px;
    background: {BLUE_SOFT}; color: {BLUE}; letter-spacing: 1px;
    border: 1px solid {BLUE_BORDER};
}}
.badge.pred {{ background: #1a1200; color: {GOLD}; border-color: #4d3600; }}
table.stand {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
table.stand th {{
    text-align: left; color: {MUTED}; font-weight: 600; font-size: 11px;
    text-transform: uppercase; letter-spacing: 0.5px;
    padding: 4px 6px; border-bottom: 1px solid {BORDER};
}}
table.stand th.num, table.stand td.num {{ text-align: center; }}
table.stand td {{
    padding: 7px 6px; border-bottom: 1px solid {SURFACE3}; color: {TEXT};
}}
table.stand tr:last-child td {{ border-bottom: none; }}
table.stand td.team {{ font-weight: 600; }}
table.stand td.pts {{ font-weight: 800; color: {ACCENT}; }}
.pos {{
    display: inline-block; width: 20px; height: 20px; line-height: 20px;
    text-align: center; border-radius: 5px; font-size: 11px; font-weight: 700;
    background: {SURFACE3}; color: {MUTED};
}}
.pos.q {{ background: {ACCENT}; color: #000; }}
.delta-up   {{ color: #3fb950; font-weight: 700; }}
.delta-down {{ color: {RED};   font-weight: 700; }}
.delta-flat {{ color: {MUTED}; }}

/* ── MATCH BLOCK ── */
.match-teams {{
    display: flex; justify-content: space-between; align-items: center;
    font-size: 14px; font-weight: 600; color: {TEXT}; margin-bottom: 8px;
}}
.match-teams .vs {{ color: {MUTED}; font-weight: 500; font-size: 12px; }}
.match-headline {{
    font-size: 12px; color: {MUTED}; font-style: italic; line-height: 1.45;
    padding-left: 10px; border-left: 2px solid {ACCENT};
    margin-bottom: 8px;
}}
.prob-bar {{
    display: flex; width: 100%; height: 28px; border-radius: 6px;
    overflow: hidden; border: 1px solid {BORDER};
}}
.prob-seg {{
    display: flex; align-items: center; justify-content: center;
    font-size: 11px; font-weight: 700; white-space: nowrap;
}}
.prob-seg.seg-win  {{ background: {WIN};  color: #fff; }}
.prob-seg.seg-draw {{ background: {DRAW}; color: {TEXT}; }}
.prob-seg.seg-loss {{ background: {LOSS}; color: #000; }}
.prob-pending {{
    display: flex; align-items: center; justify-content: center;
    width: 100%; height: 28px; border-radius: 6px;
    background: {SURFACE2}; color: {MUTED};
    font-size: 12px; font-weight: 500; border: 1px solid {BORDER};
}}
.prob-legend {{
    display: flex; gap: 16px; margin: 6px 2px 0 2px;
    font-size: 11px; color: {MUTED};
}}
.prob-legend .k {{ display: flex; align-items: center; gap: 5px; }}
.dot {{ width: 8px; height: 8px; border-radius: 2px; display: inline-block; }}

/* ── DETAIL BLOCKS ── */
.detail-block .h {{
    font-size: 10px; font-weight: 700; letter-spacing: 1px;
    text-transform: uppercase; color: {MUTED}; margin-bottom: 4px;
}}
.detail-block .v {{ font-size: 17px; font-weight: 700; color: {TEXT}; }}
.scoreline-pill {{
    display: inline-block; background: {BLUE_SOFT}; color: {BLUE};
    font-weight: 600; padding: 3px 10px; border-radius: 6px;
    margin: 2px 4px 2px 0; font-size: 12px; border: 1px solid {BLUE_BORDER};
}}
.proj-note {{
    margin-top: 10px; padding: 8px 10px; border-radius: 6px;
    background: #1a1200; color: {GOLD}; font-size: 11.5px;
    font-weight: 600; border: 1px solid #4d3600;
}}

/* ── AI NARRATIVE ── */
.narrative-wrap {{
    background: {SURFACE2}; border: 1px solid {BORDER};
    border-radius: 8px; padding: 14px 16px; margin-top: 14px;
}}
.narrative-headline {{
    font-size: 13.5px; font-weight: 700; color: {TEXT}; margin-bottom: 8px; line-height: 1.4;
}}
.narrative-body {{
    font-size: 12.5px; color: {MUTED}; line-height: 1.65;
}}
.narrative-market {{
    font-size: 11.5px; color: {MUTED}; font-style: italic;
    padding-top: 8px; margin-top: 8px; border-top: 1px solid {BORDER};
}}
/* ── SCORELINE HEATMAP ── */
.hmap-wrap {{ margin-top: 16px; }}
.hmap-label {{
    font-size: 10px; font-weight: 700; letter-spacing: 1px;
    text-transform: uppercase; color: {MUTED}; margin-bottom: 10px;
}}
.hmap-sub {{ font-size: 11px; color: {MUTED}; margin-bottom: 8px; }}

/* ── MATCH MARKETS (grid-derived betting insights) ── */
.markets {{ margin-top: 16px; }}
.section-label {{
    font-size: 10px; font-weight: 700; letter-spacing: 1px;
    text-transform: uppercase; color: {MUTED}; margin-bottom: 10px;
}}
.mkt-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
.mkt {{
    background: {SURFACE2}; border: 1px solid {BORDER};
    border-radius: 9px; padding: 11px 13px;
}}
.mkt-top {{ display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 8px; }}
.mkt-name {{ font-size: 11px; font-weight: 600; color: {TEXT}; }}
.mkt-val {{ font-size: 14px; font-weight: 800; color: {ACCENT}; }}
.dualbar {{ display: flex; height: 7px; border-radius: 4px; overflow: hidden; background: {SURFACE3}; }}
.dualbar .seg-a {{ background: {ACCENT}; }}
.dualbar .seg-b {{ background: {BORDER}; }}
.mkt-foot {{ display: flex; justify-content: space-between; font-size: 10px; color: {MUTED}; margin-top: 5px; }}
.cs-row {{ display: flex; gap: 6px; align-items: stretch; }}
.cs {{ flex: 1; text-align: center; padding-top: 1px; }}
.cs-team {{ font-size: 10px; color: {MUTED}; margin-bottom: 2px; display: flex; align-items: center; justify-content: center; gap: 4px; white-space: nowrap; }}
.cs-pct {{ font-size: 15px; font-weight: 800; color: {TEXT}; }}
.gdist {{ display: flex; align-items: flex-end; gap: 4px; height: 44px; }}
.gbar {{ flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: flex-end; height: 100%; }}
.gbar .bar {{ width: 100%; min-height: 2px; background: {ACCENT_SOFT}; border: 1px solid {ACCENT_BORDER}; border-radius: 3px 3px 0 0; }}
.gbar .bar.peak {{ background: {ACCENT}; border-color: {ACCENT}; }}
.gbar .glab {{ font-size: 9px; color: {MUTED}; margin-top: 3px; }}

/* ── MODEL VS MARKET ── */
.mvm {{ margin-top: 12px; background: {SURFACE2}; border: 1px solid {BORDER};
        border-radius: 10px; padding: 13px 15px; }}
.mvm .section-label {{ margin-bottom: 11px; }}
.mvm-row {{ display: flex; align-items: center; gap: 11px; margin-bottom: 9px; }}
.mvm-tag {{ font-size: 11px; font-weight: 800; width: 54px; flex-shrink: 0;
            text-transform: uppercase; letter-spacing: 0.5px; }}
.mvm-tag .dot {{ display: inline-block; width: 7px; height: 7px; border-radius: 50%;
                 margin-right: 5px; vertical-align: middle; }}
.mvm-bar {{ flex: 1; display: flex; height: 26px; border-radius: 6px;
            overflow: hidden; border: 1px solid {BORDER}; }}
.mvm-seg {{ display: flex; align-items: center; justify-content: center;
            font-size: 11.5px; font-weight: 800; min-width: 0;
            border-right: 1px solid rgba(0,0,0,0.25); }}
.mvm-seg:last-child {{ border-right: none; }}
.mvm-seg.seg-win  {{ background: {WIN};  color: #fff; }}
.mvm-seg.seg-draw {{ background: {DRAW}; color: {TEXT}; }}
.mvm-seg.seg-loss {{ background: {LOSS}; color: #000; }}
.mvm-legend {{ display: flex; justify-content: space-between; gap: 6px;
               margin-top: 9px; }}
.mvm-legend span {{ display: flex; align-items: center; gap: 5px;
                    font-size: 10.5px; font-weight: 600; color: {MUTED}; }}
.mvm-legend i {{ width: 10px; height: 10px; border-radius: 3px; flex-shrink: 0; }}
.mvm-single {{ display: flex; align-items: center; gap: 10px; }}
.mvm-pill {{ flex: 1; background: {SURFACE}; border: 1px solid {BORDER};
             border-radius: 9px; padding: 11px 12px; text-align: center; }}
.mvm-pill .pk {{ font-size: 10px; color: {MUTED}; text-transform: uppercase;
                 letter-spacing: 0.5px; margin-bottom: 4px; }}
.mvm-pill .pv {{ font-size: 22px; font-weight: 900; line-height: 1; }}
.mvm-edge {{ font-size: 12px; font-weight: 800; padding: 7px 13px; border-radius: 9px;
             white-space: nowrap; border: 1px solid transparent; text-align: center;
             line-height: 1.25; }}
.mvm-edge .es {{ font-size: 15px; display: block; }}
.mvm-note {{ font-size: 11px; color: {MUTED}; line-height: 1.5; margin-top: 4px; }}

/* ── TOURNAMENT PULSE ── */
.pulse-stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 4px 0 24px; }}
.pstat {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 11px; padding: 15px 14px; text-align: center; }}
.pstat .pv {{ font-size: 25px; font-weight: 900; color: {TEXT}; line-height: 1; }}
.pstat .pv.green {{ color: {ACCENT}; }}
.pstat .pv.blue {{ color: {BLUE}; }}
.pstat .pk {{ font-size: 9.5px; font-weight: 700; letter-spacing: 0.8px; text-transform: uppercase; color: {MUTED}; margin-top: 7px; }}
.lb-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }}
.lb-card {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 13px; padding: 16px 18px 8px; }}
.lb-head {{ display: flex; align-items: baseline; gap: 8px; margin-bottom: 10px; }}
.lb-title {{ font-size: 14px; font-weight: 800; color: {TEXT}; }}
.lb-sub {{ font-size: 10.5px; color: {MUTED}; }}
.lb-row {{ display: flex; align-items: center; gap: 11px; padding: 9px 0; border-top: 1px solid {SURFACE3}; }}
.lb-row:first-of-type {{ border-top: none; }}
.lb-rank {{ width: 16px; font-size: 12px; font-weight: 800; color: {MUTED}; text-align: center; flex-shrink: 0; }}
.lb-match {{ flex: 1; min-width: 0; }}
.lb-teams {{ font-size: 12.5px; font-weight: 600; color: {TEXT}; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.lb-teams .vs {{ color: {MUTED}; font-weight: 500; margin: 0 4px; }}
.lb-meta {{ font-size: 10px; color: {MUTED}; margin-top: 1px; }}
.lb-val {{ font-size: 13.5px; font-weight: 800; flex-shrink: 0; white-space: nowrap; display: flex; align-items: center; gap: 5px; }}
.lb-chip {{ font-size: 11.5px; font-weight: 800; padding: 3px 9px; border-radius: 20px; white-space: nowrap; display: inline-flex; align-items: center; gap: 4px; }}

/* ── KNOCKOUT BRACKET ── */
.champ {{ text-align: center; padding: 26px 20px 8px; }}
.champ .ct {{ font-size: 10px; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; color: {ACCENT}; margin-bottom: 8px; }}
.champ .ctrophy {{ font-size: 30px; line-height: 1; }}
.champ .cname {{ font-size: 30px; font-weight: 900; color: {TEXT}; letter-spacing: -0.5px; margin-top: 6px; }}
.champ .cname img {{ height: 30px !important; border-radius: 2px; vertical-align: middle; margin-right: 8px; }}
.bk-banner {{ background: #1a1200; border: 1px solid #4d3600; color: {GOLD}; font-size: 12px;
              font-weight: 600; border-radius: 8px; padding: 9px 14px; margin: 6px 0 18px; text-align: center; }}
.bracket {{ display: flex; gap: 12px; align-items: stretch; overflow-x: auto; padding-bottom: 12px; }}
.bk-col {{ display: flex; flex-direction: column; min-width: 168px; flex: 1; }}
.bk-col-head {{ font-size: 10px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase;
                color: {MUTED}; text-align: center; margin-bottom: 10px; padding-bottom: 8px;
                border-bottom: 1px solid {BORDER}; }}
.bk-col-body {{ flex: 1; display: flex; flex-direction: column; justify-content: space-around; gap: 8px; }}
.bk-tie {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 9px; padding: 5px; position: relative; }}
.bk-team {{ display: flex; align-items: center; gap: 6px; padding: 5px 7px; border-radius: 6px;
            font-size: 12px; font-weight: 600; color: {MUTED}; }}
.bk-team img {{ height: 11px !important; border-radius: 1px; flex-shrink: 0; margin: 0 !important; }}
.bk-team .bk-name {{ flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.bk-team .bk-slot {{ font-size: 8px; font-weight: 800; color: {MUTED}; letter-spacing: 0.3px;
                     min-width: 15px; text-align: center; flex-shrink: 0; opacity: 0.75; }}
.bk-team .bk-score {{ font-weight: 800; color: {MUTED}; font-variant-numeric: tabular-nums; }}
.bk-team.win {{ color: {TEXT}; background: {ACCENT_SOFT}; }}
.bk-team.win .bk-score {{ color: {ACCENT}; }}
.bk-aet {{ position: absolute; top: -7px; right: 8px; font-size: 8px; font-weight: 700;
           letter-spacing: 0.5px; background: {SURFACE3}; border: 1px solid {BORDER};
           color: {MUTED}; padding: 1px 5px; border-radius: 10px; }}
.bk-col.bk-final .bk-tie {{ border-color: {ACCENT}; box-shadow: 0 0 18px rgba(0,201,110,0.12); }}

/* ── EXPANDER ── */
details[data-testid="stExpander"], div[data-testid="stExpander"] {{
    background: {SURFACE} !important; border: 1px solid {BORDER} !important;
    border-radius: 8px !important;
}}
details[data-testid="stExpander"] summary,
div[data-testid="stExpander"] summary {{
    display: flex !important; align-items: center !important;
    justify-content: center !important; color: {MUTED} !important;
    font-weight: 500 !important;
}}
details[data-testid="stExpander"] summary p,
div[data-testid="stExpander"] summary p,
div[data-testid="stExpander"] summary span {{
    color: {MUTED} !important; font-weight: 500 !important;
    text-align: center !important;
}}
div[data-testid="stExpander"] summary svg {{
    fill: {MUTED} !important; color: {MUTED} !important;
}}

/* ── MATCHDAY DIVIDER ── */
.md-divider {{
    display: flex; align-items: center; gap: 10px; margin: 22px 0 10px 0;
}}
.md-divider .lbl {{
    font-size: 12px; font-weight: 700; letter-spacing: 0.8px;
    text-transform: uppercase; color: {TEXT}; white-space: nowrap;
}}
.md-divider .line {{ flex: 1; height: 1px; background: {BORDER}; }}
.md-divider .tag {{ font-size: 10px; font-weight: 600; color: {MUTED}; }}

/* ── HOW IT WORKS ── */
.how-hero {{
    text-align: center; padding: 36px 20px 28px;
}}
.how-hero .hw-title {{
    font-size: 28px; font-weight: 900; color: {TEXT};
    letter-spacing: -0.5px; margin-bottom: 10px;
}}
.how-hero .hw-sub {{
    font-size: 15px; color: {MUTED};
    max-width: 600px; margin: 0 auto; line-height: 1.65;
}}


.di-body {{ flex: 1; }}

/* ── AGENT FLOW DIAGRAM ── */
.flow {{
    max-width: 560px; margin: 8px auto 40px;
    display: flex; flex-direction: column; align-items: center; gap: 0;
}}
.flow .node {{
    padding: 11px 20px; border-radius: 11px; font-size: 13.5px; font-weight: 700;
    border: 1.5px solid; text-align: center; white-space: nowrap; min-width: 180px;
}}
.flow .node-common {{ background: {ACCENT_SOFT}; border-color: {ACCENT_BORDER}; color: {ACCENT}; }}
.flow .node-judge {{
    background: linear-gradient(135deg, {ACCENT_SOFT} 0%, {BLUE_SOFT} 100%);
    border-color: {ACCENT}; color: {TEXT}; box-shadow: 0 0 22px rgba(0,201,110,0.18);
}}
.flow .arrow {{ color: {ACCENT}; font-size: 17px; line-height: 1; padding: 6px 0; opacity: 0.85; }}
.flow .merge-note {{ font-size: 11px; color: {MUTED}; font-style: italic; margin-top: 5px; }}
.flow .parallel {{
    width: 100%; background: rgba(56,139,253,0.05);
    border: 1px solid {BLUE_BORDER}; border-radius: 16px; padding: 16px 16px 20px;
}}
.flow .parallel-label {{
    text-align: center; font-size: 10px; font-weight: 700; letter-spacing: 1.5px;
    text-transform: uppercase; color: {BLUE}; margin-bottom: 16px;
}}
.flow .cols {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 14px; align-items: start; }}
.flow .col {{ display: flex; flex-direction: column; align-items: center; gap: 5px; }}
.flow .col-head {{
    font-size: 9.5px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase;
    color: {MUTED}; margin-bottom: 3px;
}}
.flow .mini {{
    width: 100%; padding: 7px 4px; border-radius: 8px; font-size: 11.5px;
    font-weight: 600; text-align: center;
}}
.flow .mini-team {{ background: {BLUE_SOFT}; border: 1px solid {BLUE_BORDER}; color: {BLUE}; }}
.flow .mini-market {{ background: {SURFACE2}; border: 1px solid {BORDER}; color: {MUTED}; }}
.flow .tinyarrow {{ color: {BLUE_BORDER}; font-size: 11px; line-height: 1; }}
.how-steps {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 14px; margin: 28px 0 32px;
}}
.how-step {{
    background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 12px;
    padding: 20px 22px; transition: border-color 0.15s ease;
}}
.how-step:hover {{ border-color: {ACCENT}; }}
.how-step .hs-icon {{ font-size: 22px; margin-bottom: 10px; }}
.how-step .hs-num {{
    font-size: 10px; font-weight: 700; letter-spacing: 1.5px;
    text-transform: uppercase; color: {ACCENT}; margin-bottom: 4px;
}}
.how-step .hs-title {{
    font-size: 15px; font-weight: 700; color: {TEXT}; margin-bottom: 6px;
}}
.how-step .hs-desc {{
    font-size: 13px; color: {MUTED}; line-height: 1.6;
}}
.diff-card {{
    background: {SURFACE}; border: 1px solid {BORDER};
    border-radius: 12px; padding: 26px 30px; margin-bottom: 16px;
}}
.diff-card .dc-title {{
    font-size: 15px; font-weight: 800; color: {TEXT};
    margin-bottom: 18px; letter-spacing: -0.2px;
}}
.diff-item {{
    display: flex; gap: 14px; align-items: flex-start;
    padding-bottom: 14px; margin-bottom: 14px;
    border-bottom: 1px solid {BORDER};
}}
.diff-item:last-child {{ border-bottom: none; padding-bottom: 0; margin-bottom: 0; }}
.diff-item .di-icon {{ font-size: 18px; flex-shrink: 0; margin-top: 1px; }}
.diff-item .di-title, .diff-item .di-body .di-title {{
    font-size: 14px; font-weight: 700; color: {TEXT}; margin-bottom: 3px;
}}
.diff-item .di-desc, .diff-item .di-body .di-desc {{ font-size: 13px; color: {MUTED}; line-height: 1.55; }}

/* ── GENERIC ── */
.stCaption, [data-testid="stCaptionContainer"] {{ color: {MUTED} !important; }}
.stMarkdown p {{ color: {MUTED} !important; }}
.stAlert {{ background: {SURFACE} !important; border: 1px solid {BORDER} !important; }}
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
#  COUNTRY FLAGS  — image-based via flagcdn.com (renders on all OS/browsers)
# ═══════════════════════════════════════════════════════════════════════════════
_ISO: dict[str, str] = {
    "Algeria": "dz", "Argentina": "ar", "Australia": "au",
    "Austria": "at", "Belgium": "be", "Bosnia and Herzegovina": "ba",
    "Brazil": "br", "Canada": "ca", "Cape Verde": "cv",
    "Colombia": "co", "Croatia": "hr", "Curacao": "cw", "Curaçao": "cw",
    "Czechia": "cz", "DR Congo": "cd", "Ecuador": "ec", "Egypt": "eg",
    "England": "gb-eng", "France": "fr", "Germany": "de", "Ghana": "gh",
    "Haiti": "ht", "Iran": "ir", "Iraq": "iq", "Ivory Coast": "ci",
    "Japan": "jp", "Jordan": "jo", "Korea Republic": "kr",
    "Mexico": "mx", "Morocco": "ma", "Netherlands": "nl",
    "New Zealand": "nz", "Norway": "no", "Panama": "pa",
    "Paraguay": "py", "Portugal": "pt", "Qatar": "qa",
    "Saudi Arabia": "sa", "Scotland": "gb-sct", "Senegal": "sn",
    "South Africa": "za", "Spain": "es", "Sweden": "se",
    "Switzerland": "ch", "Tunisia": "tn", "Türkiye": "tr",
    "United States": "us", "Uruguay": "uy", "Uzbekistan": "uz",
}

_FLAG_BASE = "https://flagcdn.com/20x15"


def flag_img(team: str, h: int = 13) -> str:
    code = _ISO.get(team, "")
    if not code:
        return ""
    return (
        f'<img src="{_FLAG_BASE}/{code}.png" '
        f'style="height:{h}px;border-radius:1px;vertical-align:middle;'
        f'margin-right:5px;display:inline-block">'
    )


def flagged(team: str) -> str:
    img = flag_img(team)
    return f"{img}{team}"


# ═══════════════════════════════════════════════════════════════════════════════
#  HEADER
# ═══════════════════════════════════════════════════════════════════════════════
_PITCH_SVG = """
<svg class="pitch-svg" viewBox="0 0 280 120" xmlns="http://www.w3.org/2000/svg">
  <rect x="8" y="8" width="264" height="104" rx="5"
        fill="none" stroke="rgba(0,201,110,0.28)" stroke-width="1.2"/>
  <line x1="140" y1="8" x2="140" y2="112"
        stroke="rgba(0,201,110,0.22)" stroke-width="1.2"/>
  <circle cx="140" cy="60" r="26" fill="none"
          stroke="rgba(0,201,110,0.25)" stroke-width="1.2"/>
  <circle cx="140" cy="60" r="3" fill="rgba(0,201,110,0.45)"/>
  <rect x="8"   y="32" width="52" height="56" fill="none"
        stroke="rgba(0,201,110,0.20)" stroke-width="1"/>
  <rect x="220" y="32" width="52" height="56" fill="none"
        stroke="rgba(0,201,110,0.20)" stroke-width="1"/>
  <rect x="8"   y="44" width="24" height="32" fill="none"
        stroke="rgba(0,201,110,0.15)" stroke-width="1"/>
  <rect x="248" y="44" width="24" height="32" fill="none"
        stroke="rgba(0,201,110,0.15)" stroke-width="1"/>
</svg>"""

st.markdown(
    f"""
    <div class="app-header">
      {_PITCH_SVG}
      <div class="header-tag">⚽ FIFA World Cup 2026</div>
      <h1>Siuuumulator</h1>
      <p class="sub">
        AI-powered match prediction engine &nbsp;·&nbsp; multi-agent pipeline &nbsp;·&nbsp; full scoreline distributions &nbsp;·&nbsp; live data
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ═══════════════════════════════════════════════════════════════════════════════
#  DATA  (cached; busts when any source file changes)
# ═══════════════════════════════════════════════════════════════════════════════
@st.cache_data(show_spinner=False)
def _bundle(_fx_m, _rs_m, _pr_m):
    return D.load_fixtures(), D.load_results(), D.load_predictions()


def _mtime(p: Path) -> float:
    try:
        return p.stat().st_mtime
    except OSError:
        return 0.0


fixtures, results, predictions = _bundle(
    _mtime(D.FIXTURES_FILE), _mtime(D.RESULTS_FILE), _mtime(D.PREDICTIONS_FILE)
)
GROUPS = D.groups_in_order(fixtures)

# ═══════════════════════════════════════════════════════════════════════════════
#  ACCURACY BANNER  (only shown when matches have been played)
# ═══════════════════════════════════════════════════════════════════════════════
_acc = D.accuracy_summary(fixtures, results, predictions)
if _acc["total_played"] > 0:
    _md_rows = D.accuracy_by_matchday(fixtures, results, predictions)

    def _perf_row(summ: dict, label: str, sublabel: str = "",
                  row_class: str = "md-row") -> str:
        oa  = summ["outcome_accuracy"]
        ep  = summ["exact_pct"]
        avs = summ["avg_score"]
        wp  = summ["with_prediction"]
        tp  = summ["total_played"]
        oa_cls = " green" if (oa or 0) >= 50 else ""
        sub = f"<span class='sub'>{sublabel}</span>" if sublabel else ""
        return f"""
          <tr class="{row_class}">
            <td class="lbl-col lbl">{label}{sub}</td>
            <td class="v{oa_cls}">{f'{oa}%' if oa is not None else '—'}</td>
            <td class="v">{f'{ep}%' if ep is not None else '—'}</td>
            <td class="v blue">{f'{avs}/100' if avs is not None else '—'}</td>
            <td class="v">{wp}/{tp}</td>
          </tr>"""

    _rows_html = _perf_row(_acc, "Overall", "all matchdays", "overall")
    for _r in _md_rows:
        _rows_html += _perf_row(_r, f"MD{_r['md']}", "", "md-row")

    st.markdown(
        f"""
        <div class="perf-card">
          <div class="title">📊&nbsp; Model Performance</div>
          <table class="perf-table">
            <thead>
              <tr>
                <th class="lbl-col">Matchday</th>
                <th>Outcome Accuracy</th>
                <th>Exact Score</th>
                <th>Avg Score</th>
                <th>Predicted</th>
              </tr>
            </thead>
            <tbody>{_rows_html}</tbody>
          </table>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ═══════════════════════════════════════════════════════════════════════════════
#  RENDER HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _condense_grid(grid: list, max_display: int = 4) -> list:
    """Condense any NxN grid to (max_display+1)x(max_display+1) by summing overflow into the last bucket."""
    n = len(grid)
    m = max_display + 1
    if n <= m:
        return grid
    out = [[0.0] * m for _ in range(m)]
    for i in range(n):
        ri = min(i, m - 1)
        row = grid[i] if isinstance(grid[i], list) else []
        for j in range(len(row)):
            ci = min(j, m - 1)
            v = float(row[j]) if isinstance(row[j], (int, float)) else 0.0
            out[ri][ci] += v
    return out


def scoreline_heatmap_html(grid, home: str, away: str) -> str:
    """HTML colour-coded scoreline probability table (rows=home, cols=away). Always 5x5."""
    if not grid or not isinstance(grid, list) or not grid[0]:
        return ""
    grid = _condense_grid(grid, max_display=4)
    n = len(grid)
    flat = [float(p) for row in grid for p in row if isinstance(p, (int, float))]
    p_max = max(flat) if flat else 1.0
    if p_max <= 0:
        p_max = 1.0

    def _bg(prob: float) -> str:
        # Gamma-compress and apply a floor so even ~0% cells have a faint green tint
        t = (prob / p_max) ** 0.45
        t_vis = 0.13 + t * 0.87          # floor at 13% so gradient is always visible
        # dark-green (#0d2a1a) → bright-green (#00c96e)
        r = int(0x0d + (0x00 - 0x0d) * t_vis)
        g = int(0x2a + (0xc9 - 0x2a) * t_vis)
        b = int(0x1a + (0x6e - 0x1a) * t_vis)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _fg(prob: float) -> str:
        t = (prob / p_max) ** 0.45
        return TEXT if t > 0.58 else MUTED

    labels = ["0", "1", "2", "3", "4+"][:n]

    col_heads = "".join(
        f'<th style="font-size:11px;font-weight:600;color:{MUTED};'
        f'padding:2px 6px 6px;text-align:center;min-width:52px">{l}</th>'
        for l in labels
    )
    rows_html = ""
    for ri, row in enumerate(grid):
        cells = ""
        for ci in range(n):
            prob = float(row[ci]) if ci < len(row) and isinstance(row[ci], (int, float)) else 0.0
            pct = prob * 100
            txt = f"{pct:.1f}%" if pct >= 0.2 else "·"
            cells += (
                f'<td style="text-align:center;padding:8px 4px;border-radius:5px;'
                f'min-width:52px;font-size:12px;font-weight:700;'
                f'border:1px solid {BORDER};'
                f'background:{_bg(prob)};color:{_fg(prob)}">{txt}</td>'
            )
        rows_html += (
            f'<tr><td style="padding:3px 10px 3px 0;font-size:11px;'
            f'font-weight:700;color:{MUTED};text-align:right;'
            f'white-space:nowrap">{labels[ri]}</td>{cells}</tr>'
        )

    return f"""
    <div class="hmap-wrap">
      <div class="hmap-label">Scoreline probability grid</div>
      <div class="hmap-sub">
        Rows&nbsp;=&nbsp;<strong style="color:{TEXT}">{home} goals</strong>
        &nbsp;&middot;&nbsp;
        Cols&nbsp;=&nbsp;<strong style="color:{TEXT}">{away} goals</strong>
        &nbsp;&middot;&nbsp; Brighter&nbsp;=&nbsp;more likely
      </div>
      <div style="overflow-x:auto">
        <table style="border-collapse:separate;border-spacing:4px">
          <thead>
            <tr><td style="min-width:32px"></td>{col_heads}</tr>
          </thead>
          <tbody>{rows_html}</tbody>
        </table>
      </div>
    </div>
    """


def markets_html(ins: dict, home: str, away: str) -> str:
    """Grid-derived betting markets: Over/Under, BTTS, clean sheets, goal curve."""
    if not ins:
        return ""
    o, u = ins["over25"], ins["under25"]
    by, bn = ins["btts"], ins["btts_no"]
    hcs, acs = ins["home_cs"], ins["away_cs"]
    exp = ins["exp_total"]
    gd = ins["goal_dist"]

    def dual(a_pct: int, b_pct: int) -> str:
        return (f'<div class="dualbar"><div class="seg-a" style="width:{a_pct}%"></div>'
                f'<div class="seg-b" style="width:{b_pct}%"></div></div>')

    # collapse total-goals distribution into 0,1,2,3,4,5+ buckets
    buckets: dict[int, int] = {}
    for k, v in gd.items():
        buckets[min(k, 5)] = buckets.get(min(k, 5), 0) + v
    peak = max(buckets, key=buckets.get) if buckets else -1
    maxv = max(buckets.values()) if buckets else 1
    bars = ""
    for k in range(6):
        v = buckets.get(k, 0)
        ht = int(3 + (v / maxv) * 35) if maxv else 3
        lab = "5+" if k == 5 else str(k)
        cls = "bar peak" if k == peak else "bar"
        bars += (f'<div class="gbar"><div class="{cls}" style="height:{ht}px" '
                 f'title="{v}%"></div><div class="glab">{lab}</div></div>')

    fh, fa = flag_img(home, 11), flag_img(away, 11)
    return (
        '<div class="markets">'
        '<div class="section-label">&#9889; Match markets '
        '<span style="font-weight:500;text-transform:none;letter-spacing:0;opacity:0.65">'
        '&middot; read off the full scoreline grid</span></div>'
        '<div class="mkt-grid">'
        '<div class="mkt"><div class="mkt-top"><span class="mkt-name">Over 2.5 goals</span>'
        f'<span class="mkt-val">{o}%</span></div>{dual(o, u)}'
        f'<div class="mkt-foot"><span>Over {o}%</span><span>Under {u}%</span></div></div>'
        '<div class="mkt"><div class="mkt-top"><span class="mkt-name">Both teams score</span>'
        f'<span class="mkt-val">{by}%</span></div>{dual(by, bn)}'
        f'<div class="mkt-foot"><span>Yes {by}%</span><span>No {bn}%</span></div></div>'
        '<div class="mkt"><div class="mkt-top"><span class="mkt-name">Clean sheet</span>'
        f'<span class="mkt-val" style="color:{MUTED};font-size:11px;font-weight:600">keeps a 0</span></div>'
        f'<div class="cs-row"><div class="cs"><div class="cs-team">{fh}{home}</div>'
        f'<div class="cs-pct">{hcs}%</div></div><div class="cs"><div class="cs-team">{fa}{away}</div>'
        f'<div class="cs-pct">{acs}%</div></div></div></div>'
        '<div class="mkt"><div class="mkt-top"><span class="mkt-name">Total goals</span>'
        f'<span class="mkt-val">{exp}<span style="font-size:10px;color:{MUTED};font-weight:600"> exp</span></span></div>'
        f'<div class="gdist">{bars}</div></div>'
        '</div></div>'
    )


def model_vs_market_html(div: dict, home: str, away: str) -> str:
    """Visual divergence between the model and the betting market."""
    if not div:
        return ""
    if div["mode"] == "full":
        m, k = div["model"], div["market"]

        def bar(d: dict) -> str:
            def seg(cls: str, pct: int) -> str:
                # hide the number on very thin slivers so it doesn't overflow
                label = pct if pct >= 8 else ""
                return (f'<div class="mvm-seg {cls}" '
                        f'style="width:{pct}%">{label}</div>')
            return (
                '<div class="mvm-bar">'
                f'{seg("seg-win", d["home"])}'
                f'{seg("seg-draw", d["draw"])}'
                f'{seg("seg-loss", d["away"])}'
                '</div>'
            )
        return (
            '<div class="mvm"><div class="section-label">&#9878; Model vs market</div>'
            f'<div class="mvm-row"><span class="mvm-tag" style="color:{ACCENT}">'
            f'<span class="dot" style="background:{ACCENT}"></span>Model</span>{bar(m)}</div>'
            f'<div class="mvm-row"><span class="mvm-tag" style="color:{TEXT}">'
            f'<span class="dot" style="background:{MUTED}"></span>Market</span>{bar(k)}</div>'
            f'<div class="mvm-legend">'
            f'<span><i style="background:{WIN}"></i>{home} win</span>'
            f'<span><i style="background:{DRAW}"></i>Draw</span>'
            f'<span><i style="background:{LOSS}"></i>{away} win</span>'
            f'</div></div>'
        )
    # single-side comparison (favourite win prob)
    team, mp, kp, edge = div["team"], div["model_pct"], div["market_pct"], div["edge"]
    if edge > 0:
        col, bg, bd, txt = ACCENT, ACCENT_SOFT, ACCENT_BORDER, "value edge"
    elif edge < 0:
        col, bg, bd, txt = RED, "#1f0a0a", "#5c1a1a", "market higher"
    else:
        col, bg, bd, txt = MUTED, SURFACE3, BORDER, "in line"
    sign = f"+{edge}" if edge > 0 else str(edge)
    return (
        f'<div class="mvm"><div class="section-label">&#9878; Model vs market '
        f'&middot; {team} to win</div><div class="mvm-single">'
        f'<div class="mvm-pill"><div class="pk">Model</div>'
        f'<div class="pv" style="color:{ACCENT}">{mp}%</div></div>'
        f'<div class="mvm-pill"><div class="pk">Market</div>'
        f'<div class="pv" style="color:{TEXT}">{kp}%</div></div>'
        f'<div class="mvm-edge" style="background:{bg};color:{col};border-color:{bd}">'
        f'<span class="es">{sign}%</span>{txt}</div>'
        f'</div></div>'
    )


def standings_html(rows: list[dict], predicted: bool = False) -> str:
    head = (
        "<tr><th>#</th><th>Team</th>"
        "<th class='num'>P</th><th class='num'>W</th><th class='num'>D</th>"
        "<th class='num'>L</th><th class='num'>GD</th><th class='num'>Pts</th>"
        + ("<th class='num'>±</th>" if predicted else "")
        + "</tr>"
    )
    body = ""
    for i, r in enumerate(rows, start=1):
        gd = r["GD"]
        gd_s = f"+{gd}" if gd > 0 else str(gd)
        pos_cls = "pos q" if i <= 2 else "pos"
        delta_cell = ""
        if predicted:
            mv  = r.get("delta", "flat")
            sym = {"up": "▲", "down": "▼", "flat": "—"}[mv]
            cls = {"up": "delta-up", "down": "delta-down", "flat": "delta-flat"}[mv]
            delta_cell = f"<td class='num {cls}'>{sym}</td>"
        body += (
            f"<tr><td><span class='{pos_cls}'>{i}</span></td>"
            f"<td class='team'>{flagged(r['team'])}</td>"
            f"<td class='num'>{r['P']}</td><td class='num'>{r['W']}</td>"
            f"<td class='num'>{r['D']}</td><td class='num'>{r['L']}</td>"
            f"<td class='num'>{gd_s}</td><td class='num pts'>{r['Pts']}</td>"
            f"{delta_cell}</tr>"
        )
    return f"<table class='stand'>{head}{body}</table>"


def standings_card(rows, kind: str, focused: bool, status=None) -> None:
    label     = "Current Table" if kind == "current" else "Predicted Table"
    lbl_cls   = "lbl" if kind == "current" else "lbl pred"
    badge_cls = "badge" if kind == "current" else "badge pred"
    badge     = "LIVE" if kind == "current" else "PROJECTED"
    dim       = "" if focused else "dim"
    inner     = standings_html(rows, predicted=(kind == "predicted"))

    note = ""
    if kind == "predicted" and status is not None:
        if status["total"] and status["predicted"] == 0 and status["played"] == 0:
            note = ("<div class='proj-note'>No predictions yet — run the pipeline "
                    "to project this group.</div>")
        elif not status["fully_projected"]:
            done = status["played"] + status["predicted"]
            note = (f"<div class='proj-note'>Partial · {done}/{status['total']} "
                    f"fixtures covered. Remaining assume current standing.</div>")

    st.markdown(
        f"<div class='tbl-card {dim}'>"
        f"<div class='tbl-head'>"
        f"<span class='{lbl_cls}'>{label}</span>"
        f"<span class='{badge_cls}'>{badge}</span>"
        f"</div>{inner}{note}</div>",
        unsafe_allow_html=True,
    )


def _call_html(label: str, val) -> str:
    colors = {
        "Bullseye":  ACCENT,
        "On Target": GOLD,
        "Off Target": RED,
    }
    if val in colors:
        body = f"<div class='v' style='color:{colors[val]}'>{val}</div>"
    else:
        body = f"<div class='v' style='color:{MUTED}'>—</div>"
    return f"<div class='detail-block'><div class='h'>{label}</div>{body}</div>"


@st.cache_data(show_spinner=False)
def _build_card_cached(fid, home, away, group, md, pa, pd, pb,
                       scoreline, headline, hc, ac, accuracy) -> bytes:
    """Cached PNG build — only re-renders when a match's data actually changes."""
    return SC.build_match_card(
        home=home, away=away, group=group, md=md,
        pa=pa, pd=pd, pb=pb, scoreline=scoreline, headline=headline,
        home_code=hc, away_code=ac, accuracy=accuracy,
    )


def match_block(m: dict) -> None:
    home, away = m["home"], m["away"]
    pa, pd, pb = m["prob_home_win"], m["prob_draw"], m["prob_away_win"]
    have = m["has_prediction"] and None not in (pa, pd, pb)
    p    = predictions.get(m["fixture_id"], {})

    headline  = (p.get("headline") or "").strip()
    grid      = p.get("scoreline_grid")

    # ── Team header ──
    st.markdown(
        f"<div class='match-teams'>"
        f"<span>{flagged(home)}</span>"
        f"<span class='vs'>vs</span>"
        f"<span>{flagged(away)}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ── AI headline preview ──
    if headline and have:
        st.markdown(
            f"<div class='match-headline'>{headline}</div>",
            unsafe_allow_html=True,
        )

    # ── Probability bar ──
    if have:
        st.markdown(
            f"""
            <div class="prob-bar">
              <div class="prob-seg seg-win"  style="width:{pa}%">{pa}%</div>
              <div class="prob-seg seg-draw" style="width:{pd}%">{pd}%</div>
              <div class="prob-seg seg-loss" style="width:{pb}%">{pb}%</div>
            </div>
            <div class="prob-legend">
              <span class="k">
                <span class="dot" style="background:{WIN}"></span>{home} win
              </span>
              <span class="k">
                <span class="dot" style="background:{DRAW}"></span>Draw
              </span>
              <span class="k">
                <span class="dot" style="background:{LOSS}"></span>{away} win
              </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div class='prob-pending'>Prediction pending — run the pipeline</div>",
            unsafe_allow_html=True,
        )

    # ── Match details expander ──
    with st.expander("Match details", expanded=False):
        if not m["has_prediction"]:
            st.caption("No prediction available for this fixture yet.")
        else:
            eg   = m.get("expected_goals") or {}
            tops = m.get("top_scorelines") or []
            sl   = m.get("predicted_scoreline")

            # Row 1: xG | Predicted scoreline | Most likely scorelines
            cols = st.columns(3)
            with cols[0]:
                xg = "—"
                if eg.get("home") is not None and eg.get("away") is not None:
                    xg = f"{eg['home']:.1f} – {eg['away']:.1f}"
                st.markdown(
                    f"<div class='detail-block'><div class='h'>Expected Goals</div>"
                    f"<div class='v'>{xg}</div></div>",
                    unsafe_allow_html=True,
                )
            with cols[1]:
                sl_display = "—"
                if sl:
                    _m = re.search(r"(\d+)\s*-\s*(\d+)", str(sl))
                    if _m:
                        sl_display = f"{home} {_m.group(1)}-{_m.group(2)} {away}"
                st.markdown(
                    f"<div class='detail-block'><div class='h'>Predicted Scoreline</div>"
                    f"<div class='v'>{sl_display}</div></div>",
                    unsafe_allow_html=True,
                )
            with cols[2]:
                if tops:
                    pills = "".join(
                        f"<span class='scoreline-pill'>"
                        f"{t.get('score')} · {t.get('prob')}%</span>"
                        for t in tops
                    )
                else:
                    pills = f"<div class='v' style='color:{MUTED}'>—</div>"
                st.markdown(
                    f"<div class='detail-block'><div class='h'>Top Scorelines</div>"
                    f"{pills}</div>",
                    unsafe_allow_html=True,
                )
            # Row 3: Actual result (if played)
            actual = m.get("actual_score", "—")
            ps     = m.get("prediction_score")
            call   = m.get("outcome_call")
            if actual != "—":
                st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
                cols3 = st.columns(3)
                with cols3[0]:
                    st.markdown(
                        f"<div class='detail-block'><div class='h'>Actual Scoreline</div>"
                        f"<div class='v'>{actual}</div></div>",
                        unsafe_allow_html=True,
                    )
                with cols3[1]:
                    ps_val = f"{ps}%" if ps is not None else "—"
                    tip = (
                        "100·√(p_actual ÷ p_top): how likely the actual scoreline "
                        "was on the model's grid, relative to the most-likely cell. "
                        "100% = perfect top pick."
                    )
                    info = (
                        f"<span title=\"{tip}\" "
                        f"style='cursor:help;color:{MUTED};font-weight:600'>&#9432;</span>"
                    )
                    st.markdown(
                        f"<div class='detail-block'><div class='h'>Score {info}</div>"
                        f"<div class='v'>{ps_val}</div></div>",
                        unsafe_allow_html=True,
                    )
                with cols3[2]:
                    st.markdown(_call_html("Final Outcome", call),
                                unsafe_allow_html=True)

            # Model vs market divergence bar
            div = D.market_divergence(p)
            if div:
                st.html(model_vs_market_html(div, home, away))

            # Scoreline heatmap
            if grid:
                hmap = scoreline_heatmap_html(grid, home, away)
                if hmap:
                    st.markdown(hmap, unsafe_allow_html=True)

            # Match markets (grid-derived betting insights)
            ins = D.grid_insights(grid)
            if ins:
                st.html(markets_html(ins, home, away))

            # Shareable card (built only on demand)
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            fid = m["fixture_id"]
            ckey = f"card_open_{fid}"
            sc_cols = st.columns([1, 1.4, 1])
            with sc_cols[1]:
                if st.button("🖼  Make a shareable card", key=f"mkcard_{fid}",
                             width="stretch"):
                    st.session_state[ckey] = True
            if st.session_state.get(ckey):
                with st.spinner("Rendering card…"):
                    png = _build_card_cached(
                        fid, home, away, p.get("group"), m.get("md"),
                        pa, pd, pb, m.get("predicted_scoreline"), headline,
                        _ISO.get(home, ""), _ISO.get(away, ""),
                        _acc.get("outcome_accuracy"),
                    )
                st.image(png, width="stretch")
                st.download_button(
                    "⬇  Download PNG", png,
                    file_name=f"{home}_vs_{away}_prediction.png".replace(" ", "_"),
                    mime="image/png", key=f"dlcard_{fid}", width="stretch",
                )

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)


def render_group(letter: str) -> None:
    cur     = D.current_standings(fixtures, results, letter)
    pred    = D.predicted_standings(fixtures, results, predictions, letter)
    matches = D.match_predictions(fixtures, predictions, results, letter)
    status  = D.group_prediction_status(fixtures, results, predictions, letter)

    state_key = f"focus_{letter}"
    if state_key not in st.session_state:
        st.session_state[state_key] = "LIVE"
    focus = st.session_state[state_key]

    _, tc, _ = st.columns([1.4, 2, 1.4])
    with tc:
        bl, bp = st.columns(2, gap="small")
        with bl:
            if st.button(
                "● LIVE", key=f"live_{letter}", width="stretch",
                type="primary" if focus == "LIVE" else "secondary",
            ):
                st.session_state[state_key] = "LIVE"
                st.rerun()
        with bp:
            if st.button(
                "◆ PROJECTED", key=f"proj_{letter}", width="stretch",
                type="primary" if focus == "PROJECTED" else "secondary",
            ):
                st.session_state[state_key] = "PROJECTED"
                st.rerun()

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    c1, c2 = st.columns(2, gap="medium")
    with c1:
        standings_card(cur,  "current",   focused=(focus == "LIVE"))
    with c2:
        standings_card(pred, "predicted", focused=(focus == "PROJECTED"),
                       status=status)

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
    st.markdown(
        f"<div style='font-size:15px;font-weight:700;color:{TEXT};"
        f"margin-bottom:2px'>Match Probabilities</div>",
        unsafe_allow_html=True,
    )
    st.caption("Win · Draw · Loss projection per group fixture")
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    by_md    = status["by_md"]
    last_md  = None
    for m in matches:
        md = m.get("md")
        if md != last_md:
            slot  = by_md.get(md, {})
            done  = slot.get("played", 0) + slot.get("predicted", 0)
            total = slot.get("total", 0)
            tag   = f"{done}/{total} predicted" if total else ""
            st.markdown(
                f"<div class='md-divider'>"
                f"<span class='lbl'>Matchday {md}</span>"
                f"<span class='line'></span>"
                f"<span class='tag'>{tag}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
            last_md = md
        match_block(m)


# ═══════════════════════════════════════════════════════════════════════════════
#  TOURNAMENT PULSE
# ═══════════════════════════════════════════════════════════════════════════════
def _lb_row(rank: int, i: dict, val_html: str) -> str:
    teams = (
        f"{flag_img(i['home'], 11)}{i['home']}"
        f"<span class='vs'>v</span>"
        f"{flag_img(i['away'], 11)}{i['away']}"
    )
    meta = f"Group {i['group']} &middot; MD{i['md']}"
    return (
        f"<div class='lb-row'><div class='lb-rank'>{rank}</div>"
        f"<div class='lb-match'><div class='lb-teams'>{teams}</div>"
        f"<div class='lb-meta'>{meta}</div></div>"
        f"<div class='lb-val'>{val_html}</div></div>"
    )


def _lb_card(title: str, icon: str, sub: str, rows: str) -> str:
    return (
        f"<div class='lb-card'><div class='lb-head'>"
        f"<span class='lb-title'>{icon} {title}</span>"
        f"<span class='lb-sub'>{sub}</span></div>{rows}</div>"
    )


def render_tournament_insights() -> None:
    ti = D.tournament_insights(fixtures, predictions, results)
    if not ti:
        st.markdown(
            f"""
            <div style="text-align:center;padding:70px 20px">
              <div style="font-size:34px;margin-bottom:14px">📡</div>
              <div style="font-size:19px;font-weight:800;color:{TEXT};margin-bottom:8px">
                No pulse yet
              </div>
              <div style="font-size:13px;color:{MUTED};max-width:360px;margin:0 auto;line-height:1.6">
                Run the prediction pipeline and the tournament's biggest storylines
                will surface here.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    ag = ti["avg_goals"]
    ag_s = f"{ag}" if ag is not None else "—"

    # ── value picks: signed model–market gap on the favoured side ──
    vp_rows = ""
    for n, i in enumerate(ti["value_picks"], 1):
        e = i["edge"]
        col = ACCENT if e > 0 else RED
        bg = ACCENT_SOFT if e > 0 else "#1f0a0a"
        sign = f"+{e}" if e > 0 else str(e)
        chip = (
            f"<span class='lb-chip' style='background:{bg};color:{col}'>"
            f"{flag_img(i['edge_team'], 10)}{sign}%</span>"
        )
        vp_rows += _lb_row(n, i, chip)

    # ── goal fests: P(over 2.5) ──
    gf_rows = ""
    for n, i in enumerate(ti["goal_fests"], 1):
        val = (
            f"<span style='color:{ACCENT}'>{i['over25']}%</span>"
            f"<span style='color:{MUTED};font-size:10px;font-weight:600'>o2.5</span>"
        )
        gf_rows += _lb_row(n, i, val)

    # ── coin flips: how low the strongest single outcome is ──
    cf_rows = ""
    for n, i in enumerate(ti["coin_flips"], 1):
        val = (
            f"<span style='color:{TEXT}'>{i['max3']}%</span>"
            f"<span style='color:{MUTED};font-size:10px;font-weight:600'>top pick</span>"
        )
        cf_rows += _lb_row(n, i, val)

    # ── one-sided: biggest favourite ──
    os_rows = ""
    for n, i in enumerate(ti["one_sided"], 1):
        val = (
            f"{flag_img(i['fav_team'], 10)}"
            f"<span style='color:{ACCENT}'>{i['fav_prob']}%</span>"
        )
        os_rows += _lb_row(n, i, val)

    st.html(
        f"""
        <div class="how-hero" style="padding:30px 20px 14px">
          <div class="hw-title" style="font-size:26px">Tournament Pulse</div>
          <div class="hw-sub">
            The model's sharpest reads across all 12 groups &mdash; where it sees
            value, goals, chaos, and the safest bankers.
          </div>
        </div>
        <div class="pulse-stats">
          <div class="pstat"><div class="pv">{ti['count']}<span style="font-size:14px;color:{MUTED}">/{ti['total']}</span></div><div class="pk">Matches analysed</div></div>
          <div class="pstat"><div class="pv green">{ag_s}</div><div class="pk">Avg goals / match</div></div>
          <div class="pstat"><div class="pv blue">{ti['value_edges']}</div><div class="pk">Market gaps found</div></div>
          <div class="pstat"><div class="pv">{ti['high_conf']}</div><div class="pk">High-confidence calls</div></div>
        </div>
        <div class="lb-grid">
          {_lb_card("Biggest market gaps", "&#128176;", "model vs market &middot; signed edge", vp_rows)}
          {_lb_card("Goal-fests", "&#128293;", "likeliest to go over 2.5", gf_rows)}
          {_lb_card("Coin-flips", "&#9878;", "lower top pick = more open", cf_rows)}
          {_lb_card("Safest bankers", "&#127919;", "biggest single favourite", os_rows)}
        </div>
        <div style="height:18px"></div>
        """
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  KNOCKOUT BRACKET
# ═══════════════════════════════════════════════════════════════════════════════
def render_knockout_bracket() -> None:
    bk = D.knockout_bracket(fixtures, results, predictions)
    if not bk:
        st.markdown(
            f"""
            <div style="text-align:center;padding:70px 20px">
              <div style="font-size:36px;margin-bottom:16px">🏆</div>
              <div style="font-size:20px;font-weight:800;color:{TEXT};
                          letter-spacing:-0.3px;margin-bottom:8px">Knockout Bracket</div>
              <div style="font-size:13px;color:{MUTED};max-width:400px;
                          margin:0 auto;line-height:1.6">
                Needs the full field of 32 qualifiers. Run more of the group stage
                through the pipeline and the projected bracket — all the way to a
                champion — will appear here.
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    champ = bk["champion"]
    cols_html = ""
    for rnd in bk["rounds"]:
        final_cls = " bk-final" if rnd["name"] == "Final" else ""
        ties_html = ""
        for t in rnd["ties"]:
            hi, lo = t["score"].split("-")
            a, b, w = t["a"], t["b"], t["winner"]
            a_sc, b_sc = (hi if a == w else lo), (hi if b == w else lo)
            a_cls = " win" if a == w else ""
            b_cls = " win" if b == w else ""
            aet = "<div class='bk-aet'>AET</div>" if t["aet"] else ""
            # FIFA slot labels (1E / 2C / 3F) — only present on Round-of-32 ties
            a_slot = f"<span class='bk-slot'>{t['a_slot']}</span>" if t.get("a_slot") else ""
            b_slot = f"<span class='bk-slot'>{t['b_slot']}</span>" if t.get("b_slot") else ""
            ties_html += (
                f"<div class='bk-tie'>{aet}"
                f"<div class='bk-team{a_cls}'>{a_slot}{flag_img(a, 11)}"
                f"<span class='bk-name'>{a}</span><span class='bk-score'>{a_sc}</span></div>"
                f"<div class='bk-team{b_cls}'>{b_slot}{flag_img(b, 11)}"
                f"<span class='bk-name'>{b}</span><span class='bk-score'>{b_sc}</span></div>"
                f"</div>"
            )
        cols_html += (
            f"<div class='bk-col{final_cls}'>"
            f"<div class='bk-col-head'>{rnd['name']}</div>"
            f"<div class='bk-col-body'>{ties_html}</div></div>"
        )

    banner = ""
    if bk["partial"]:
        banner = (
            f"<div class='bk-banner'>&#9888; Projection in progress &mdash; "
            f"{bk['groups_projected']}/{bk['groups_total']} groups fully predicted. "
            f"Qualifiers &amp; matchups firm up as more of the group stage runs.</div>"
        )

    champ_block = (
        f"<div class='champ'><div class='ct'>Projected Champion</div>"
        f"<div class='ctrophy'>&#127942;</div>"
        f"<div class='cname'>{flag_img(champ, 30)}{champ}</div></div>"
    )
    st.html(champ_block + banner + f"<div class='bracket'>{cols_html}</div>")


# ═══════════════════════════════════════════════════════════════════════════════
#  HOW IT WORKS
# ═══════════════════════════════════════════════════════════════════════════════
def render_how_it_works() -> None:
    st.html(
        f"""
        <div class="how-hero">
          <div class="hw-title">How Siuuumulator Works</div>
          <div class="hw-sub">
            Most football predictors flip a weighted coin. We built something closer to
            a courtroom: a pipeline of AI agents, each with a distinct role, converging
            on one shared goal &mdash; figure out what&rsquo;s most likely to happen on the pitch.
          </div>
        </div>

        <div class="flow">
          <div class="node node-common">&#127919;&nbsp; Manager</div>
          <div class="arrow">&#8595;</div>
          <div class="node node-common">&#128269;&nbsp; Researcher</div>
          <div class="arrow">&#8595;</div>
          <div class="parallel">
            <div class="parallel-label">&#8644;&nbsp; runs in parallel &middot; branches never see each other</div>
            <div class="cols">
              <div class="col">
                <div class="col-head">Team A</div>
                <div class="mini mini-team">Alchemist</div>
                <div class="tinyarrow">&#8595;</div>
                <div class="mini mini-team">Strategist</div>
                <div class="tinyarrow">&#8595;</div>
                <div class="mini mini-team">Scout</div>
                <div class="tinyarrow">&#8595;</div>
                <div class="mini mini-team">Tactician</div>
              </div>
              <div class="col">
                <div class="col-head">Market</div>
                <div class="mini mini-market">Bookmaker</div>
                <div class="tinyarrow">&#8595;</div>
                <div class="mini mini-market" style="opacity:0.55">END</div>
              </div>
              <div class="col">
                <div class="col-head">Team B</div>
                <div class="mini mini-team">Alchemist</div>
                <div class="tinyarrow">&#8595;</div>
                <div class="mini mini-team">Strategist</div>
                <div class="tinyarrow">&#8595;</div>
                <div class="mini mini-team">Scout</div>
                <div class="tinyarrow">&#8595;</div>
                <div class="mini mini-team">Tactician</div>
              </div>
            </div>
          </div>
          <div class="arrow">&#8595;</div>
          <div class="node node-common">&#9917;&nbsp; Pitch Simulator</div>
          <div class="merge-note">the only point where the two teams meet</div>
          <div class="arrow">&#8595;</div>
          <div class="node node-common">&#127922;&nbsp; Chaos Agent</div>
          <div class="arrow">&#8595;</div>
          <div class="node node-judge">&#9878;&nbsp; Judge &nbsp;&rarr;&nbsp; final report</div>
        </div>

        <div class="how-steps">

          <div class="how-step">
            <div class="hs-icon">&#128269;</div>
            <div class="hs-num">Step 1</div>
            <div class="hs-title">The Researcher</div>
            <div class="hs-desc">
              Goes online before every prediction. Reads injury bulletins, squad news,
              recent match reports. Then calculates each squad&rsquo;s fitness score using
              real travel distances, altitude differences between cities, and the number
              of days since their last game. No stale data.
            </div>
          </div>

          <div class="how-step">
            <div class="hs-icon">&#128373;</div>
            <div class="hs-num">Steps 2&ndash;5 &nbsp;&middot;&nbsp; run twice in parallel</div>
            <div class="hs-title">The Scout Squads</div>
            <div class="hs-desc">
              Each team gets four dedicated agents who <em>never</em> see the other
              team&rsquo;s analysis. The <strong>Alchemist</strong> reads squad chemistry.
              The <strong>Strategist</strong> weighs tournament context. The
              <strong>Scout</strong> studies opponent weaknesses. The
              <strong>Tactician</strong> builds a blind game plan. Two fully isolated
              pipelines, run in parallel.
            </div>
          </div>

          <div class="how-step">
            <div class="hs-icon">&#9917;</div>
            <div class="hs-num">Step 6</div>
            <div class="hs-title">The Pitch Simulator</div>
            <div class="hs-desc">
              The only moment the two teams ever &ldquo;meet&rdquo; in the model. One impartial
              agent reads both blind tactical plans side by side and estimates expected
              goals for each team in normal play. Everything else stays isolated &mdash;
              this is the single merge point.
            </div>
          </div>

          <div class="how-step">
            <div class="hs-icon">&#127922;</div>
            <div class="hs-num">Step 7</div>
            <div class="hs-title">The Chaos Agent</div>
            <div class="hs-desc">
              Because football isn&rsquo;t always normal. Generates red card, VAR penalty,
              and key injury scenarios &mdash; then calculates the exact probability weight of
              each one. No dice rolling. Just maths. Every black-swan event is
              accounted for precisely, not sampled randomly.
            </div>
          </div>

          <div class="how-step">
            <div class="hs-icon">&#128202;</div>
            <div class="hs-num">Step 8</div>
            <div class="hs-title">The Bookmaker</div>
            <div class="hs-desc">
              Reads current betting market odds as an independent reference. The model
              knows what the market thinks before the Judge makes its call &mdash; useful for
              spotting where our predictions diverge from public consensus.
            </div>
          </div>

          <div class="how-step">
            <div class="hs-icon">&#9878;</div>
            <div class="hs-num">Step 9</div>
            <div class="hs-title">The Judge</div>
            <div class="hs-desc">
              Combines all probability-weighted scenarios into one precise mathematical
              mixture. Compares model versus market. Writes the final report:
              win/draw/loss odds, most-likely scorelines, a full narrative, and a
              confidence rating. Everything you see on this page comes from here.
            </div>
          </div>

        </div>

        <div class="diff-card">
          <div class="dc-title">Why it&rsquo;s different</div>

          <div class="diff-item">
            <div class="di-icon">&#128683;</div>
            <div class="di-body">
              <div class="di-title">No Monte Carlo &mdash; no dice rolling</div>
              <div class="di-desc">
                Most simulators run 10,000 random simulations and count outcomes.
                We enumerate every scenario mathematically with exact probabilities
                and combine them into one precise distribution. No noise. The same
                inputs always produce the same prediction.
              </div>
            </div>
          </div>

          <div class="diff-item">
            <div class="di-icon">&#128274;</div>
            <div class="di-body">
              <div class="di-title">Structural isolation between teams</div>
              <div class="di-desc">
                Team A&rsquo;s four-agent analysis chain and Team B&rsquo;s are architecturally
                separated &mdash; they share no edges in the graph. This prevents one team&rsquo;s
                strengths from unconsciously biasing the other side&rsquo;s analysis, a subtle
                problem that affects models where both teams share the same context.
              </div>
            </div>
          </div>

          <div class="diff-item">
            <div class="di-icon">&#127760;</div>
            <div class="di-body">
              <div class="di-title">Live data, not a spreadsheet</div>
              <div class="di-desc">
                The Researcher calls the internet before every prediction. Real injury
                news, actual travel logistics, real venue altitudes. The model knows
                if your striker trained this morning &mdash; or didn&rsquo;t.
              </div>
            </div>
          </div>

          <div class="diff-item">
            <div class="di-icon">&#128208;</div>
            <div class="di-body">
              <div class="di-title">Full scoreline distributions, not just winners</div>
              <div class="di-desc">
                We don&rsquo;t just pick a side. We compute a probability for every possible
                scoreline from 0-0 to 4-4 and beyond. The heatmap grid in each
                match detail is the model&rsquo;s complete view of what could happen &mdash;
                which exact score is most likely and how probable every alternative is.
              </div>
            </div>
          </div>

        </div>

        <div style="text-align:center;padding:20px 0 32px;font-size:12px;color:{MUTED};
                    line-height:1.8;border-top:1px solid {BORDER};margin-top:8px">
          Built with <strong style="color:{TEXT}">LangGraph</strong>
          &nbsp;&middot;&nbsp; Powered by <strong style="color:{TEXT}">Google Gemini</strong>
          &nbsp;&middot;&nbsp; <span style="color:{ACCENT}">Siuuumulator</span> &copy; 2026
        </div>
        """
    )



# ═══════════════════════════════════════════════════════════════════════════════
#  TOP-LEVEL TABS
# ═══════════════════════════════════════════════════════════════════════════════
tab_groups, tab_pulse, tab_bracket, tab_how = st.tabs(
    ["Groups", "Tournament Pulse", "Knockout Bracket", "How It Works"]
)

with tab_groups:
    if not GROUPS:
        st.warning(
            "No fixtures found. Check that data/fixtures.json exists at the project root."
        )
    else:
        if (st.session_state.get("active_group") not in GROUPS):
            st.session_state["active_group"] = GROUPS[0]
        active_group = st.session_state["active_group"]

        st.markdown(
            f"<div style='font-size:11px;font-weight:700;letter-spacing:1.5px;"
            f"text-transform:uppercase;color:{MUTED};margin:2px 0 8px'>"
            f"Select Group</div>",
            unsafe_allow_html=True,
        )
        per_row = 6
        for start in range(0, len(GROUPS), per_row):
            chunk = GROUPS[start:start + per_row]
            cols = st.columns(per_row, gap="small")
            for i, g in enumerate(chunk):
                with cols[i]:
                    if st.button(
                        f"Group {g}", key=f"gbtn_{g}", width="stretch",
                        type="primary" if g == active_group else "secondary",
                    ):
                        st.session_state["active_group"] = g
                        st.rerun()

        st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
        render_group(active_group)

with tab_pulse:
    render_tournament_insights()

with tab_bracket:
    render_knockout_bracket()

with tab_how:
    render_how_it_works()

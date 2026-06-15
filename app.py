"""
FIFA WC 2026 SIMULATION ENGINE — Dashboard UI
=============================================
Streamlit dashboard. Reads data via ui_data.py (fixtures + results + predictions).
The UI is a thin render layer: it never calls the pipeline, only reads JSON the
pipeline writes. See ui_data.py for the predictions.json contract.

Run:  streamlit run app.py
"""

import base64
import re
from functools import lru_cache
from pathlib import Path

import streamlit as st

import ui_data as D

# --------------------------------------------------------------------------- #
#  ASSETS  (theme images live in ./assets, anchored to this file so the path
#  resolves identically locally and on Streamlit Cloud / Linux deploy)
# --------------------------------------------------------------------------- #
ASSETS = Path(__file__).parent / "assets"
HEADER_IMG = ASSETS / "Siuumulator-header.png"
THEME_GROUP_IMG = ASSETS / "Group-stage-theme-siumulator.png"
THEME_KNOCKOUT_IMG = ASSETS / "knockout-stage-siumulator.png"


@lru_cache(maxsize=8)
def _data_uri(path_str):
    """Read an image file and return a base64 data-URI, or '' if missing.

    Inlining keeps the image baked into the served HTML, so there is never a
    runtime file-path lookup to break between local and deployed environments.
    """
    p = Path(path_str)
    try:
        raw = p.read_bytes()
    except OSError:
        return ""
    return "data:image/png;base64," + base64.b64encode(raw).decode("ascii")

# --------------------------------------------------------------------------- #
#  PAGE CONFIG
# --------------------------------------------------------------------------- #
st.set_page_config(
    page_title="FIFA WC 2026 Simulation Engine",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --------------------------------------------------------------------------- #
#  THEME PALETTE  (dark "glass" theme to match the SIUUUMULATOR slate)
# --------------------------------------------------------------------------- #
PRIMARY = "#0a1424"      # deep navy base (matches group-theme darkest tone)
BLUE = "#2f6bff"         # electric blue accent (the chalkboard blue)
BLUE_SOFT = "#16244a"    # translucent-ish soft blue panel tint
WIN = "#2f6bff"          # home-win bar
DRAW = "#5a6b86"         # draw bar (muted slate-blue, readable on dark)
LOSS = "#c9a227"         # away-win bar (gold accent, ties to knockout theme)
INK = "#eaf1ff"          # primary text on dark (near-white, blue tint)
MUTED = "#8fa3c4"        # secondary/label text on dark
GOLD = "#e9b949"         # gold highlight (titles / pred labels)
CARD_BG = "rgba(16, 26, 50, 0.72)"      # dark glass card fill
CARD_BORDER = "rgba(120, 150, 220, 0.18)"
CARD_BG_SOLID = "#0e1830"               # opaque fallback for nested rows

st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Barlow+Condensed:wght@600;700;800&display=swap');

    html, body, [class*="css"] {{ font-family: 'Inter', -apple-system, sans-serif; }}

    /* ---------- DARK THEME BASE ----------
       The page background is set per-active-tab further down via .stApp[data-theme].
       Default (group) tone here so first paint is never white. */
    .stApp {{
        background-color: {PRIMARY};
        background-position: center top;
        background-size: cover;
        background-attachment: fixed;
        background-repeat: no-repeat;
    }}
    /* dark scrim over the textured image so cards/text stay readable */
    .stApp::before {{
        content: ""; position: fixed; inset: 0; z-index: 0;
        background: linear-gradient(180deg,
            rgba(8,14,28,0.55) 0%, rgba(8,14,28,0.78) 60%, rgba(8,14,28,0.88) 100%);
        pointer-events: none;
    }}
    .block-container {{ padding-top: 1.2rem; max-width: 1180px; position: relative; z-index: 1; }}
    /* lift Streamlit's own containers above the scrim */
    .main, .block-container, [data-testid="stHeader"] {{ background: transparent !important; }}
    [data-testid="stHeader"] {{ z-index: 2; }}

    /* ---------- HEADER IMAGE ---------- */
    /* PNG is cropped tight to the artwork (aspect ~4.29:1), so width:100% +
       height:auto renders it large and full-width with no padding/clipping.
       max-width caps it on very wide screens; tune that if you want. */
    .app-header-img {{
        display: block;
        width: 100%;
        height: auto;
        max-width: 1180px;
        margin: 6px auto 16px auto;
        filter: drop-shadow(0 6px 18px rgba(0,0,0,0.40));
    }}

    /* ---------- TABS ---------- */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 4px; border-bottom: 1px solid {CARD_BORDER}; background: transparent;
    }}
    .stTabs [data-baseweb="tab"] {{
        font-weight: 600; font-size: 14px; color: {MUTED};
        padding: 8px 16px; border-radius: 8px 8px 0 0; background: transparent;
    }}
    .stTabs [aria-selected="true"] {{
        color: {INK} !important;
        background: {BLUE_SOFT};
        border-bottom: 2px solid {GOLD};
    }}
    .stTabs [aria-disabled="true"] {{ color: #46577a !important; }}

    /* ---------- SEGMENTED CONTROL (LIVE | PROJECTED), centered ---------- */
    div[data-testid="stSegmentedControl"] {{
        width: 100% !important; display: flex !important;
        justify-content: center !important; align-items: center !important;
    }}
    div[data-testid="stSegmentedControl"] > * {{
        margin-left: auto !important; margin-right: auto !important;
        display: inline-flex !important; width: fit-content !important;
        background: rgba(8,14,28,0.55) !important; border-radius: 10px; padding: 3px;
        gap: 3px; border: 1px solid {CARD_BORDER} !important;
    }}
    div[data-testid="stSegmentedControl"] button {{
        border: 1px solid transparent !important;
        background: transparent !important;
        color: {MUTED} !important;
        font-weight: 700 !important; font-size: 12px !important;
        letter-spacing: 1.5px !important;
        padding: 6px 22px !important; border-radius: 8px !important;
        box-shadow: none !important; outline: none !important;
    }}
    div[data-testid="stSegmentedControl"] button p {{ color: {MUTED} !important; }}
    div[data-testid="stSegmentedControl"] button:hover,
    div[data-testid="stSegmentedControl"] button:focus,
    div[data-testid="stSegmentedControl"] button:active {{
        color: {INK} !important; border-color: {CARD_BORDER} !important;
        box-shadow: none !important; outline: none !important;
    }}
    div[data-testid="stSegmentedControl"] button[aria-checked="true"],
    div[data-testid="stSegmentedControl"] button[aria-selected="true"],
    div[data-testid="stSegmentedControl"] button[data-selected="true"],
    div[data-testid="stSegmentedControl"] button[kind="segmented_controlActive"] {{
        background: {BLUE} !important;
        color: #ffffff !important;
        border-color: {BLUE} !important;
        box-shadow: 0 2px 8px rgba(47,107,255,0.35) !important;
    }}
    div[data-testid="stSegmentedControl"] button[aria-checked="true"] *,
    div[data-testid="stSegmentedControl"] button[aria-selected="true"] *,
    div[data-testid="stSegmentedControl"] button[data-selected="true"] *,
    div[data-testid="stSegmentedControl"] button[kind="segmented_controlActive"] * {{
        color: #ffffff !important;
    }}

    /* ---------- STANDINGS TABLE (dark glass) ---------- */
    .tbl-card {{
        border: 1px solid {CARD_BORDER}; border-radius: 12px;
        padding: 14px 16px 10px 16px;
        background: {CARD_BG};
        backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
        box-shadow: 0 6px 24px rgba(0,0,0,0.35); transition: all .25s ease;
    }}
    .tbl-card.dim {{ opacity: 0.40; filter: grayscale(0.3); }}
    .tbl-head {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; }}
    .tbl-head .lbl {{ font-size:12px; font-weight:700; letter-spacing:1.5px; text-transform:uppercase; color:{BLUE}; }}
    .tbl-head .lbl.pred {{ color:{GOLD}; }}
    .badge {{ font-size:10px; font-weight:700; padding:2px 8px; border-radius:20px;
        background:{BLUE_SOFT}; color:{INK}; letter-spacing:1px; border:1px solid {CARD_BORDER}; }}
    table.stand {{ width:100%; border-collapse:collapse; font-size:13.5px; }}
    table.stand th {{ text-align:left; color:{MUTED}; font-weight:600; font-size:11px;
        text-transform:uppercase; letter-spacing:0.5px; padding:4px 6px; border-bottom:1px solid {CARD_BORDER}; }}
    table.stand th.num, table.stand td.num {{ text-align:center; }}
    table.stand td {{ padding:7px 6px; border-bottom:1px solid rgba(120,150,220,0.10); color:{INK}; }}
    table.stand tr:last-child td {{ border-bottom:none; }}
    table.stand td.team {{ font-weight:600; }}
    table.stand td.pts {{ font-weight:800; color:{GOLD}; }}
    .pos {{ display:inline-block; width:20px; height:20px; line-height:20px; text-align:center;
        border-radius:6px; font-size:11px; font-weight:700; background:rgba(120,150,220,0.14); color:{MUTED}; margin-right:2px; }}
    .pos.q {{ background:{BLUE}; color:#fff; }}
    .delta-up {{ color:#34d399; font-weight:700; }}
    .delta-down {{ color:#f87171; font-weight:700; }}
    .delta-flat {{ color:{MUTED}; }}

    /* ---------- MATCH PROB BAR ---------- */
    .match-teams {{ display:flex; justify-content:space-between; font-size:14px;
        font-weight:600; color:{INK}; margin-bottom:6px; }}
    .match-teams .vs {{ color:{MUTED}; font-weight:500; font-size:12px; }}
    .prob-bar {{ display:flex; width:100%; height:34px; border-radius:8px; overflow:hidden;
        box-shadow: inset 0 0 0 1px {CARD_BORDER}; }}
    .prob-seg {{ display:flex; align-items:center; justify-content:center; font-size:12.5px;
        font-weight:700; color:#fff; white-space:nowrap; transition:all .3s ease; }}
    .seg-win {{ background:{WIN}; }}
    .seg-draw {{ background:{DRAW}; color:{INK}; }}
    .seg-loss {{ background:{LOSS}; color:#1a1303; }}
    .prob-pending {{ display:flex; align-items:center; justify-content:center; width:100%;
        height:34px; border-radius:8px; background:rgba(8,14,28,0.45); color:{MUTED};
        font-size:12px; font-weight:600; box-shadow: inset 0 0 0 1px {CARD_BORDER}; }}
    .prob-legend {{ display:flex; gap:18px; margin:4px 2px 0 2px; font-size:11px; color:{MUTED}; }}
    .prob-legend .k {{ display:flex; align-items:center; gap:5px; }}
    .dot {{ width:9px; height:9px; border-radius:3px; display:inline-block; }}

    /* ---------- DETAIL DROPDOWN ---------- */
    .detail-block .h {{ font-size:10.5px; font-weight:700; letter-spacing:1px; text-transform:uppercase;
        color:{MUTED}; margin-bottom:4px; }}
    .detail-block .v {{ font-size:18px; font-weight:800; color:{INK}; font-family:'Barlow Condensed',sans-serif; }}
    .scoreline-pill {{ display:inline-block; background:{BLUE_SOFT}; color:{INK}; font-weight:700;
        padding:3px 10px; border-radius:7px; margin:2px 6px 2px 0; font-size:12.5px; border:1px solid {CARD_BORDER}; }}
    .proj-note {{ margin-top:10px; padding:7px 10px; border-radius:8px; background:rgba(233,185,73,0.10);
        color:{GOLD}; font-size:11.5px; font-weight:600; border:1px solid rgba(233,185,73,0.30); }}

    /* ---------- EXPANDER ("Match details") ---------- */
    details[data-testid="stExpander"], div[data-testid="stExpander"] {{
        background: {CARD_BG} !important; border: 1px solid {CARD_BORDER} !important;
        border-radius: 10px !important; backdrop-filter: blur(8px);
    }}
    details[data-testid="stExpander"] summary,
    div[data-testid="stExpander"] summary {{
        display: flex !important; align-items: center !important;
        justify-content: center !important; text-align: center !important;
        color: {INK} !important; font-weight: 600 !important;
    }}
    details[data-testid="stExpander"] summary p,
    div[data-testid="stExpander"] summary p,
    div[data-testid="stExpander"] summary span {{
        color: {INK} !important; font-weight: 600 !important;
        text-align: center !important; width: auto !important; flex: 0 0 auto !important;
    }}
    div[data-testid="stExpander"] summary svg {{ fill: {INK} !important; color: {INK} !important; }}
    .md-divider {{ display:flex; align-items:center; gap:10px; margin:18px 0 10px 0; }}
    .md-divider .lbl {{ font-family:'Barlow Condensed',sans-serif; font-size:14px; font-weight:700;
        letter-spacing:1.5px; text-transform:uppercase; color:{GOLD}; white-space:nowrap; }}
    .md-divider .line {{ flex:1; height:1px; background:{CARD_BORDER}; }}
    .md-divider .tag {{ font-size:10px; font-weight:600; color:{MUTED}; }}

    /* generic: any stray Streamlit caption/markdown text stays light on dark */
    .stCaption, [data-testid="stCaptionContainer"], .stMarkdown p {{ color:{MUTED} !important; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------- #
#  HEADER  (image banner; falls back to text if the asset is missing)
# --------------------------------------------------------------------------- #
_header_uri = _data_uri(str(HEADER_IMG))
if _header_uri:
    st.markdown(
        f"<img class='app-header-img' src='{_header_uri}' alt='SIUUUMULATOR' />",
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        "<div style='font-family:\"Barlow Condensed\",sans-serif;font-size:38px;"
        "font-weight:800;letter-spacing:1.5px;color:#e9b949;margin:6px 0 4px 0'>"
        "SIUUUMULATOR</div>"
        "<div style='font-size:12.5px;font-weight:500;letter-spacing:2px;"
        "text-transform:uppercase;color:#8fa3c4;margin-bottom:16px'>"
        "FIFA WC 2026 Simulation Engine · Multi-Agent Match Prediction</div>",
        unsafe_allow_html=True,
    )

# --------------------------------------------------------------------------- #
#  LOAD DATA (cached; invalidates when any source file's mtime changes)
# --------------------------------------------------------------------------- #
@st.cache_data(show_spinner=False)
def _bundle(_fx_m, _rs_m, _pr_m):
    return D.load_fixtures(), D.load_results(), D.load_predictions()


def _mtime(p):
    try:
        return p.stat().st_mtime
    except OSError:
        return 0.0


fixtures, results, predictions = _bundle(
    _mtime(D.FIXTURES_FILE), _mtime(D.RESULTS_FILE), _mtime(D.PREDICTIONS_FILE)
)

GROUPS = D.groups_in_order(fixtures)

# --------------------------------------------------------------------------- #
#  RENDER HELPERS
# --------------------------------------------------------------------------- #
def standings_html(rows, predicted=False):
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
            mv = r.get("delta", "flat")
            sym = {"up": "▲", "down": "▼", "flat": "—"}[mv]
            cls = {"up": "delta-up", "down": "delta-down", "flat": "delta-flat"}[mv]
            delta_cell = f"<td class='num {cls}'>{sym}</td>"
        body += (
            f"<tr><td><span class='{pos_cls}'>{i}</span></td>"
            f"<td class='team'>{r['team']}</td>"
            f"<td class='num'>{r['P']}</td><td class='num'>{r['W']}</td>"
            f"<td class='num'>{r['D']}</td><td class='num'>{r['L']}</td>"
            f"<td class='num'>{gd_s}</td><td class='num pts'>{r['Pts']}</td>"
            f"{delta_cell}</tr>"
        )
    return f"<table class='stand'>{head}{body}</table>"


def standings_card(rows, kind, focused, status=None, show_header=True):
    label = "Current Table" if kind == "current" else "Predicted Table"
    lbl_cls = "lbl" if kind == "current" else "lbl pred"
    badge = "LIVE" if kind == "current" else "PROJECTED"
    dim = "" if focused else "dim"
    inner = standings_html(rows, predicted=(kind == "predicted"))

    note = ""
    if kind == "predicted" and status is not None:
        if status["total"] and status["predicted"] == 0 and status["played"] == 0:
            note = ("<div class='proj-note'>No predictions yet — run the pipeline "
                    "to project this group.</div>")
        elif not status["fully_projected"]:
            done = status["played"] + status["predicted"]
            note = (f"<div class='proj-note'>Partial projection · {done}/{status['total']} "
                    f"matches predicted. Remaining fixtures assume current standing.</div>")

    header = ""
    if show_header:
        header = (f"<div class='tbl-head'><span class='{lbl_cls}'>{label}</span>"
                  f"<span class='badge'>{badge}</span></div>")

    st.markdown(
        f"""
        <div class="tbl-card {dim}">
            {header}
            {inner}
            {note}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _call_html(label, val):
    """Render the Outcome Call verdict as a coloured word (no emoji), or — if ungraded."""
    colors = {"Bullseye": "#16a34a", "On Target": "#d97706", "Off Target": "#dc2626"}
    if val in colors:
        body = f"<div class='v' style='color:{colors[val]}'>{val}</div>"
    else:
        body = "<div class='v'>—</div>"
    return f"<div class='detail-block'><div class='h'>{label}</div>{body}</div>"


def match_block(m):
    a, b = m["home"], m["away"]
    pa, pd, pb = m["prob_home_win"], m["prob_draw"], m["prob_away_win"]
    have = m["has_prediction"] and None not in (pa, pd, pb)

    st.markdown(
        f"<div class='match-teams'><span>{a}</span>"
        f"<span class='vs'>vs</span><span>{b}</span></div>",
        unsafe_allow_html=True,
    )

    if have:
        st.markdown(
            f"""
            <div class="prob-bar">
                <div class="prob-seg seg-win"  style="width:{pa}%">{pa}%</div>
                <div class="prob-seg seg-draw" style="width:{pd}%">{pd}%</div>
                <div class="prob-seg seg-loss" style="width:{pb}%">{pb}%</div>
            </div>
            <div class="prob-legend">
                <span class="k"><span class="dot" style="background:{WIN}"></span>{a} win</span>
                <span class="k"><span class="dot" style="background:{DRAW}"></span>Draw</span>
                <span class="k"><span class="dot" style="background:{LOSS}"></span>{b} win</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div class='prob-pending'>Prediction pending — run the pipeline for this fixture</div>",
            unsafe_allow_html=True,
        )

    # ---- per-match detail dropdown (collapsed by default) ----
    with st.expander("Match details", expanded=False):
        if not m["has_prediction"]:
            st.caption("No prediction available for this fixture yet.")
        else:
            eg = m.get("expected_goals") or {}
            tops = m.get("top_scorelines") or []
            sl = m.get("predicted_scoreline")   # bare score like "2-0" from predictions.json

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
                # extract just the "h-a" digits, so names are added exactly once
                # even if an older predictions.json baked names into the string.
                sl_display = "—"
                if sl:
                    _m = re.search(r"(\d+)\s*-\s*(\d+)", str(sl))
                    if _m:
                        sl_display = f"{a} {_m.group(1)}-{_m.group(2)} {b}"
                st.markdown(
                    f"<div class='detail-block'><div class='h'>Predicted Scoreline</div>"
                    f"<div class='v'>{sl_display}</div></div>",
                    unsafe_allow_html=True,
                )
            with cols[2]:
                if tops:
                    pills = "".join(
                        f"<span class='scoreline-pill'>{t.get('score')} · {t.get('prob')}%</span>"
                        for t in tops
                    )
                else:
                    pills = "<div class='v'>—</div>"
                st.markdown(
                    f"<div class='detail-block'><div class='h'>Most Likely Scorelines</div>"
                    f"{pills}</div>",
                    unsafe_allow_html=True,
                )

            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

            cols2 = st.columns(3)
            with cols2[0]:
                st.markdown(
                    f"<div class='detail-block'><div class='h'>Actual Scoreline</div>"
                    f"<div class='v'>{m.get('actual_score', '—')}</div></div>",
                    unsafe_allow_html=True,
                )
            with cols2[1]:
                ps = m.get("prediction_score")
                ps_val = f"{ps}%" if ps is not None else "—"
                tip = ("100·√(p_actual ÷ p_top): the actual scoreline's probability "
                       "on the model's grid relative to the most-likely scoreline. "
                       "100% = the actual result was the model's top pick.")
                info = (f"<span title=\"{tip}\" "
                        f"style='cursor:help;color:{MUTED};font-weight:600'>&#9432;</span>")
                st.markdown(
                    f"<div class='detail-block'><div class='h'>Prediction Score {info}</div>"
                    f"<div class='v'>{ps_val}</div></div>",
                    unsafe_allow_html=True,
                )
            with cols2[2]:
                st.markdown(_call_html("Final Outcome", m.get("outcome_call")),
                            unsafe_allow_html=True)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)


def render_group(letter):
    cur = D.current_standings(fixtures, results, letter)
    pred = D.predicted_standings(fixtures, results, predictions, letter)
    matches = D.match_predictions(fixtures, predictions, results, letter)
    status = D.group_prediction_status(fixtures, results, predictions, letter)

    # focus state
    state_key = f"focus_state_{letter}"
    if state_key not in st.session_state:
        st.session_state[state_key] = "LIVE"
    focus = st.session_state[state_key]

    # --- centered LIVE | PROJECTED toggle ---
    tl, tc, tr = st.columns([2, 1, 2])
    with tc:
        sc = st.segmented_control(
            "focus", ["LIVE", "PROJECTED"],
            default=focus, key=f"seg_{letter}",
            label_visibility="collapsed",
        )
    if sc and sc != focus:
        st.session_state[state_key] = sc
        st.rerun()

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    # --- the two tables (headers rendered inside the cards) ---
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        standings_card(cur, "current", focused=(focus == "LIVE"))
    with c2:
        standings_card(pred, "predicted", focused=(focus == "PROJECTED"),
                       status=status)

    st.markdown("<div style='height:22px'></div>", unsafe_allow_html=True)
    st.markdown(
        "<div style=\"font-family:'Barlow Condensed',sans-serif;font-size:22px;"
        "font-weight:700;color:#eaf1ff;letter-spacing:0.5px;text-transform:uppercase\">"
        "Match Probabilities</div>",
        unsafe_allow_html=True,
    )
    st.caption("Win / Draw / Loss projection per group fixture")
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # group fixtures by matchday with a divider per MD
    by_md = status["by_md"]
    last_md = None
    for m in matches:
        md = m.get("md")
        if md != last_md:
            slot = by_md.get(md, {})
            done = slot.get("played", 0) + slot.get("predicted", 0)
            total = slot.get("total", 0)
            tag = f"{done}/{total} predicted" if total else ""
            st.markdown(
                f"<div class='md-divider'><span class='lbl'>Matchday {md}</span>"
                f"<span class='line'></span><span class='tag'>{tag}</span></div>",
                unsafe_allow_html=True,
            )
            last_md = md
        match_block(m)


# --------------------------------------------------------------------------- #
#  TOP-LEVEL TABS
# --------------------------------------------------------------------------- #
tab_groups, tab_bracket = st.tabs(["Groups", "Predicted Knockout Bracket"])

# --- theme background follows the visually-active top-level tab ---------------
# Streamlit renders BOTH tab panels in the DOM at once and marks the inactive
# one with [hidden] / aria-hidden. We can't branch in Python (both `with`
# blocks run every rerun), so we drive the .stApp background purely in CSS:
#   default        -> group-stage theme
#   knockout panel visible -> knockout theme
# The selector keys off the 2nd tabpanel (index 1) NOT being hidden.
_group_uri = _data_uri(str(THEME_GROUP_IMG))
_knock_uri = _data_uri(str(THEME_KNOCKOUT_IMG))
if _group_uri or _knock_uri:
    st.markdown(
        f"""
        <style>
        /* default page background = group-stage theme */
        .stApp {{ background-image: url('{_group_uri}'); }}
        /* when the knockout tab panel (2nd tablist child) is the visible one,
           swap the whole-page background to the knockout theme.              */
        .stApp:has(
            [data-baseweb="tab-panel"]:nth-of-type(2):not([hidden]):not([aria-hidden="true"])
        ) {{
            background-image: url('{_knock_uri}');
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

with tab_groups:
    if not GROUPS:
        st.warning("No fixtures found. Check that data/fixtures.json exists at the project root.")
    else:
        group_tabs = st.tabs([f"Group {g}" for g in GROUPS])
        for tab, g in zip(group_tabs, GROUPS):
            with tab:
                render_group(g)

with tab_bracket:
    st.markdown(
        "<div style='text-align:center;padding:60px 20px'>"
        "<div style=\"font-family:'Barlow Condensed',sans-serif;font-size:30px;"
        "font-weight:800;letter-spacing:1px;color:#e9b949\">KNOCKOUT BRACKET</div>"
        "<div style='font-size:13px;font-weight:600;letter-spacing:1.5px;"
        "text-transform:uppercase;color:#8fa3c4;margin-top:8px'>"
        "Coming soon — the predicted bracket will render here once the group "
        "stage is fully projected.</div></div>",
        unsafe_allow_html=True,
    )

"""
ui_data.py — data layer for the FIFA WC 2026 dashboard.

Keeps all file I/O and standings math out of app.py so the UI stays a thin
render layer. Reads three files from data/:

    fixtures.json     static  — 72 fixtures (id/group/md/home/away/date/venue/city)
    results.json      live    — played scores (home_score/away_score/played)
    predictions.json  NEW     — pipeline output, keyed by fixture_id (see CONTRACT)

The pipeline writes predictions.json; the UI only ever READS. Current table is
computed here from fixtures+results; predicted table is derived from the
per-match predictions so there's only one thing to persist.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from collections import defaultdict

# --------------------------------------------------------------------------- #
#  PATHS
#  app.py lives at project root (beside match_runner.py); data/ sits alongside.
# --------------------------------------------------------------------------- #
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"

FIXTURES_FILE = DATA_DIR / "fixtures.json"
RESULTS_FILE = DATA_DIR / "results.json"
PREDICTIONS_FILE = DATA_DIR / "predictions.json"


# --------------------------------------------------------------------------- #
#  predictions.json CONTRACT  (the pipeline must write this shape)
# --------------------------------------------------------------------------- #
#   {
#     "A1": {
#       "fixture_id": "A1", "group": "A",
#       "home": "Mexico", "away": "Curaçao",
#       "prob_home_win": 62, "prob_draw": 24, "prob_away_win": 14,
#       "expected_goals": {"home": 1.9, "away": 0.7},
#       "predicted_scoreline": "2-0",
#       "top_scorelines": [ {"score": "2-0", "prob": 18}, ... ]
#     }, ...
#   }
# Probabilities are percentages (ints summing to ~100). Extra fields are fine —
# the UI renders what's present and skips what's missing.
# --------------------------------------------------------------------------- #


# --------------------------------------------------------------------------- #
#  LOW-LEVEL LOADERS
# --------------------------------------------------------------------------- #
def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def load_fixtures() -> list[dict]:
    """
    Return list of fixture dicts. Tolerates a bare list, or a dict wrapping the
    list under 'matches' (the real file's shape) or 'fixtures'.
    """
    raw = _load_json(FIXTURES_FILE, [])
    if isinstance(raw, dict):
        raw = raw.get("matches") or raw.get("fixtures") or []
    return raw


def load_results() -> dict:
    """
    Return a map fixture_id -> {home_score, away_score, played}.
    Tolerates a list of result rows or a dict keyed by fixture id.
    """
    raw = _load_json(RESULTS_FILE, {})
    out: dict[str, dict] = {}
    if isinstance(raw, dict):
        # could already be keyed by id, or wrapped under "results"
        raw = raw.get("results", raw)
    if isinstance(raw, dict):
        for fid, row in raw.items():
            if isinstance(row, dict):
                out[fid] = row
    elif isinstance(raw, list):
        for row in raw:
            fid = row.get("id") or row.get("fixture_id")
            if fid:
                out[fid] = row
    return out


def load_predictions() -> dict:
    """Return map fixture_id -> prediction dict (see CONTRACT). Empty if file absent."""
    raw = _load_json(PREDICTIONS_FILE, {})
    if isinstance(raw, dict):
        return raw.get("predictions", raw)
    return {}


# --------------------------------------------------------------------------- #
#  GROUP / FIXTURE HELPERS
# --------------------------------------------------------------------------- #
def groups_in_order(fixtures: list[dict]) -> list[str]:
    """Distinct group letters present in fixtures, sorted (A, B, C ...)."""
    gs = {f.get("group") for f in fixtures if f.get("group")}
    return sorted(gs)


def teams_in_group(fixtures: list[dict], group: str) -> list[str]:
    """Distinct team names appearing as home/away within a group."""
    teams: list[str] = []
    for f in fixtures:
        if f.get("group") != group:
            continue
        for k in ("home", "away"):
            t = f.get(k)
            if t and t not in teams:
                teams.append(t)
    return teams


def fixtures_in_group(fixtures: list[dict], group: str) -> list[dict]:
    rows = [f for f in fixtures if f.get("group") == group]
    rows.sort(key=lambda f: (f.get("md", 0), f.get("id", "")))
    return rows


def matchdays_in_group(fixtures: list[dict], group: str) -> list[int]:
    """Distinct matchday numbers present in a group, sorted."""
    mds = {f.get("md") for f in fixtures_in_group(fixtures, group) if f.get("md")}
    return sorted(mds)


def group_prediction_status(fixtures: list[dict], results: dict,
                            predictions: dict, group: str) -> dict:
    """
    Summarise how much of a group has been predicted vs played, per matchday.
    Lets the UI tell the user the projected table is partial (e.g. only MD1 run).

    Returns:
        {
          "total": 6, "played": 0, "predicted": 2, "pending": 4,
          "by_md": {1: {"total":2,"played":0,"predicted":2,"pending":0}, ...},
          "fully_projected": False   # every unplayed fixture has a prediction
        }
    """
    fxs = fixtures_in_group(fixtures, group)
    by_md: dict[int, dict] = {}
    played = predicted = pending = 0

    for f in fxs:
        fid, md = f.get("id"), f.get("md", 0)
        slot = by_md.setdefault(md, {"total": 0, "played": 0, "predicted": 0, "pending": 0})
        slot["total"] += 1
        if results.get(fid, {}).get("played"):
            played += 1; slot["played"] += 1
        elif _is_populated(predictions.get(fid)):
            predicted += 1; slot["predicted"] += 1
        else:
            pending += 1; slot["pending"] += 1

    return {
        "total": len(fxs), "played": played,
        "predicted": predicted, "pending": pending,
        "by_md": dict(sorted(by_md.items())),
        "fully_projected": pending == 0,
    }


# --------------------------------------------------------------------------- #
#  STANDINGS
# --------------------------------------------------------------------------- #
def _blank_row(team: str) -> dict:
    return {"team": team, "P": 0, "W": 0, "D": 0, "L": 0,
            "GF": 0, "GA": 0, "Pts": 0}


def _h2h_table(teams: set, matches: list[tuple]) -> dict:
    """
    Mini-table (Pts / GF / GA) built from ONLY the matches played between the
    given `teams`. `matches` is a list of (home, home_goals, away, away_goals).
    Used to resolve teams that are level on the overall criteria.
    """
    rec = {t: {"Pts": 0, "GF": 0, "GA": 0} for t in teams}
    for h, hs, a, as_ in matches:
        if h not in teams or a not in teams:
            continue
        rec[h]["GF"] += hs; rec[h]["GA"] += as_
        rec[a]["GF"] += as_; rec[a]["GA"] += hs
        if hs > as_:
            rec[h]["Pts"] += 3
        elif hs < as_:
            rec[a]["Pts"] += 3
        else:
            rec[h]["Pts"] += 1; rec[a]["Pts"] += 1
    return rec


def _sort_table(rows: list[dict], matches: list[tuple]) -> list[dict]:
    """
    Rank a group per the official FIFA World Cup 2026 tie-break order.

    Overall criteria (all group matches):
      1. points  2. goal difference  3. goals for
    Then, for teams still level on all three, the same measures applied to ONLY
    the matches played between those tied teams (head-to-head):
      4. h2h points  5. h2h goal difference  6. h2h goals for

    (The remaining FIFA criteria — fair-play conduct points and the drawing of
    lots — need disciplinary data we don't track, so ties surviving the
    head-to-head stage keep their overall order.)

    `matches` is a list of (home, home_goals, away, away_goals) tuples for the
    group's played/projected fixtures, used to build the head-to-head tables.
    """
    def overall_key(r):
        return (r["Pts"], r["GF"] - r["GA"], r["GF"])

    rows = sorted(rows, key=overall_key, reverse=True)

    # Resolve each block of teams that are level on all three overall criteria.
    out, i = [], 0
    while i < len(rows):
        j = i + 1
        while j < len(rows) and overall_key(rows[j]) == overall_key(rows[i]):
            j += 1
        block = rows[i:j]
        if len(block) > 1:
            rec = _h2h_table({r["team"] for r in block}, matches)
            block = sorted(
                block,
                key=lambda r: (rec[r["team"]]["Pts"],
                               rec[r["team"]]["GF"] - rec[r["team"]]["GA"],
                               rec[r["team"]]["GF"]),
                reverse=True,
            )
        out.extend(block)
        i = j
    return out


def current_standings(fixtures: list[dict], results: dict, group: str) -> list[dict]:
    """
    Build the live table for a group from played results only.
    Each row: team, P, W, D, L, GF, GA, GD, Pts (sorted).
    """
    table = {t: _blank_row(t) for t in teams_in_group(fixtures, group)}
    played: list[tuple] = []

    for f in fixtures_in_group(fixtures, group):
        res = results.get(f.get("id"), {})
        if not res.get("played"):
            continue
        h, a = f.get("home"), f.get("away")
        hs, as_ = res.get("home_score"), res.get("away_score")
        if h not in table or a not in table or hs is None or as_ is None:
            continue
        played.append((h, hs, a, as_))
        for t, gf, ga in ((h, hs, as_), (a, as_, hs)):
            row = table[t]
            row["P"] += 1
            row["GF"] += gf
            row["GA"] += ga
        if hs > as_:
            table[h]["W"] += 1; table[h]["Pts"] += 3; table[a]["L"] += 1
        elif hs < as_:
            table[a]["W"] += 1; table[a]["Pts"] += 3; table[h]["L"] += 1
        else:
            table[h]["D"] += 1; table[a]["D"] += 1
            table[h]["Pts"] += 1; table[a]["Pts"] += 1

    rows = _sort_table(list(table.values()), played)
    for r in rows:
        r["GD"] = r["GF"] - r["GA"]
    return rows


def _parse_scoreline(sl) -> tuple:
    """
    Extract (home_goals, away_goals) from a predicted scoreline string such as
    'Mexico 2-0 South Africa' or a bare '2-0'. The format is always
    'HOME h-a AWAY', so the first number is the home goals. Returns (None, None)
    if no score can be parsed.
    """
    if not sl:
        return None, None
    m = re.search(r"(\d+)\s*-\s*(\d+)", str(sl))
    if not m:
        return None, None
    return int(m.group(1)), int(m.group(2))


def predicted_standings(fixtures: list[dict], results: dict,
                        predictions: dict, group: str) -> list[dict]:
    """
    Projected final table built PURELY from the model's predicted scorelines.

    Every group fixture that has a populated prediction contributes its
    PREDICTED scoreline — W/D/L, GF, GA and GD are all derived from that
    scoreline, never from the actual result. Actual results are intentionally
    ignored here, so this table does NOT change when live scores are entered;
    it is the model's standalone view of how the group should finish.

    Fixtures whose prediction hasn't been generated yet (skeleton entries) are
    skipped, so before the whole group is run the projection is partial — the
    UI surfaces that via group_prediction_status().

    Rows carry a 'delta' (up/down/flat) showing where each team sits in this
    projection relative to the current live table — purely a visual comparison;
    it does not alter the projected figures.
    """
    table = {t: _blank_row(t) for t in teams_in_group(fixtures, group)}
    played: list[tuple] = []

    for f in fixtures_in_group(fixtures, group):
        pred = predictions.get(f.get("id"))
        if not _is_populated(pred):
            continue
        h, a = f.get("home"), f.get("away")
        if h not in table or a not in table:
            continue

        hg, ag = _parse_scoreline(pred.get("predicted_scoreline"))
        if hg is None or ag is None:
            continue

        played.append((h, hg, a, ag))
        table[h]["P"] += 1; table[a]["P"] += 1
        table[h]["GF"] += hg; table[h]["GA"] += ag
        table[a]["GF"] += ag; table[a]["GA"] += hg

        if hg > ag:
            table[h]["W"] += 1; table[h]["Pts"] += 3; table[a]["L"] += 1
        elif hg < ag:
            table[a]["W"] += 1; table[a]["Pts"] += 3; table[h]["L"] += 1
        else:
            table[h]["D"] += 1; table[a]["D"] += 1
            table[h]["Pts"] += 1; table[a]["Pts"] += 1

    rows = _sort_table(list(table.values()), played)
    for r in rows:
        r["GD"] = r["GF"] - r["GA"]

    # movement vs the current live ordering (comparison overlay only)
    cur_pos = {r["team"]: i for i, r in
               enumerate(current_standings(fixtures, results, group))}
    for new_pos, r in enumerate(rows):
        old = cur_pos.get(r["team"], new_pos)
        r["delta"] = "up" if new_pos < old else "down" if new_pos > old else "flat"
    return rows


def _is_populated(p: dict) -> bool:
    """A prediction counts as 'present' only if the pipeline has filled it in."""
    if not p:
        return False
    if any(p.get(k) is not None for k in
           ("prob_home_win", "prob_draw", "prob_away_win", "predicted_scoreline")):
        return True
    return bool(p.get("top_scorelines"))


def prediction_score(grid, actual_score):
    """
    0–100: how close reality was to the model's best guess, on the model's own
    probability scale. score = 100 * sqrt(p_actual / p_top) — non-linear, so an
    actual that matched a near-tied 2nd-most-likely cell still scores high, while
    the tail drops off smoothly. grid[i][j] = P(home i, away j) as a fraction.
    Returns None if the grid or actual score is unavailable.
    """
    if not grid or not actual_score or "-" not in str(actual_score):
        return None
    try:
        ah, aa = (int(x) for x in str(actual_score).split("-", 1))
    except ValueError:
        return None
    flat = [p for row in grid for p in row]
    p_top = max(flat) if flat else 0
    if p_top <= 0:
        return None
    # Clamp the actual scoreline onto the grid: a result beyond the grid's max
    # (e.g. 7-1 on a 0..4 grid) maps to the edge cell so it scores against the
    # tail probability instead of falling off the grid and reading 0%.
    ah = min(ah, len(grid) - 1)
    aa = min(aa, len(grid[ah]) - 1)
    p_actual = grid[ah][aa]
    return round(100 * (p_actual / p_top) ** 0.5)


def _outcome_call(pred: dict, actual_score):
    """
    Qualitative verdict comparing the predicted scoreline to the actual one at the
    OUTCOME level:
      'Bullseye'   - predicted scoreline exactly equals the actual scoreline
      'On Target'  - same result (home win / draw / away win), different score
      'Off Target' - the predicted result didn't happen
      None         - not played yet (or the scoreline can't be parsed)
    """
    if not actual_score or "-" not in str(actual_score):
        return None
    try:
        ah, aa = (int(x) for x in str(actual_score).split("-", 1))
    except ValueError:
        return None
    phg, pag = _parse_scoreline(pred.get("predicted_scoreline"))
    if phg is None or pag is None:
        return None
    if phg == ah and pag == aa:
        return "Bullseye"
    pred_out = "H" if phg > pag else "A" if pag > phg else "D"
    act_out = "H" if ah > aa else "A" if aa > ah else "D"
    return "On Target" if pred_out == act_out else "Off Target"


def _accuracy_accumulate(fixtures: list[dict], results: dict,
                         predictions: dict) -> dict:
    """
    Tally prediction accuracy over the supplied fixtures.
    Shared core for both the aggregate and per-matchday summaries.
    """
    total_played = 0
    with_prediction = 0
    bullseye = 0
    on_target = 0
    off_target = 0
    scores: list[int] = []

    for f in fixtures:
        fid = f.get("id")
        res = results.get(fid, {})
        if not res.get("played"):
            continue
        total_played += 1
        p = predictions.get(fid, {})
        if not _is_populated(p):
            continue
        hs, as_ = res.get("home_score"), res.get("away_score")
        if hs is None or as_ is None:
            continue
        with_prediction += 1
        actual = f"{hs}-{as_}"
        call = _outcome_call(p, actual)
        if call == "Bullseye":
            bullseye += 1
        elif call == "On Target":
            on_target += 1
        elif call == "Off Target":
            off_target += 1
        sc = prediction_score(p.get("scoreline_grid"), actual)
        if sc is not None:
            scores.append(sc)

    outcome_acc = (
        round(100 * (bullseye + on_target) / with_prediction)
        if with_prediction else None
    )
    exact_pct = round(100 * bullseye / with_prediction) if with_prediction else None
    avg_score = round(sum(scores) / len(scores)) if scores else None

    return {
        "total_played": total_played,
        "with_prediction": with_prediction,
        "bullseye": bullseye,
        "on_target": on_target,
        "off_target": off_target,
        "outcome_accuracy": outcome_acc,
        "exact_pct": exact_pct,
        "avg_score": avg_score,
    }


def accuracy_summary(fixtures: list[dict], results: dict, predictions: dict) -> dict:
    """
    Aggregate prediction accuracy across all played matches.
    Returns counts and rates; all values are None/0 when no played matches exist.
    """
    return _accuracy_accumulate(fixtures, results, predictions)


def accuracy_by_matchday(fixtures: list[dict], results: dict,
                         predictions: dict) -> list[dict]:
    """
    Per-matchday prediction accuracy, one row per matchday that has at least
    one played match, in matchday order. Each row is an accuracy_summary dict
    with an extra "md" key. The UI pairs these rows with the aggregate banner.
    """
    by_md: dict[int, list[dict]] = {}
    for f in fixtures:
        md = f.get("md")
        if md is None:
            continue
        by_md.setdefault(md, []).append(f)

    rows: list[dict] = []
    for md in sorted(by_md):
        summ = _accuracy_accumulate(by_md[md], results, predictions)
        if summ["total_played"] == 0:
            continue
        rows.append({"md": md, **summ})
    return rows


def grid_insights(grid) -> dict | None:
    """
    Derive betting-style insights from the full Poisson scoreline grid.
    grid[i][j] = P(home i goals, away j goals) as a fraction. Values are
    re-normalised so percentages are honest even if the grid doesn't sum to 1.

    Returns None when no usable grid is present. Otherwise:
        {
          "over25": 58, "under25": 42,      # P(total goals >= 3) and complement
          "btts": 47, "btts_no": 53,        # both teams score (>=1 each)
          "home_cs": 38, "away_cs": 12,     # clean-sheet prob for each side
          "ml_total": 2, "ml_total_prob": 27,  # most-likely total goals + its prob
          "exp_total": 2.8,                 # expected total goals
          "goal_dist": {0: 6, 1: 18, 2: 27, ...},  # P(total goals = k), %, summing ~100
        }
    """
    if not grid or not isinstance(grid, list) or not grid or not grid[0]:
        return None

    total = over25 = btts = home_cs = away_cs = 0.0
    goal_dist: dict[int, float] = {}
    for i, row in enumerate(grid):
        if not isinstance(row, list):
            continue
        for j, p in enumerate(row):
            if not isinstance(p, (int, float)):
                continue
            p = float(p)
            if p <= 0:
                continue
            total += p
            tg = i + j
            goal_dist[tg] = goal_dist.get(tg, 0.0) + p
            if tg >= 3:
                over25 += p
            if i >= 1 and j >= 1:
                btts += p
            if j == 0:            # away scored 0 -> home keeps a clean sheet
                home_cs += p
            if i == 0:            # home scored 0 -> away keeps a clean sheet
                away_cs += p

    if total <= 0:
        return None

    over25 /= total; btts /= total; home_cs /= total; away_cs /= total
    goal_dist = {k: v / total for k, v in goal_dist.items()}
    ml_total = max(goal_dist, key=goal_dist.get)
    exp_total = sum(k * v for k, v in goal_dist.items())

    return {
        "over25": round(over25 * 100),
        "under25": round((1 - over25) * 100),
        "btts": round(btts * 100),
        "btts_no": round((1 - btts) * 100),
        "home_cs": round(home_cs * 100),
        "away_cs": round(away_cs * 100),
        "ml_total": ml_total,
        "ml_total_prob": round(goal_dist[ml_total] * 100),
        "exp_total": round(exp_total, 1),
        "goal_dist": {k: round(v * 100) for k, v in sorted(goal_dist.items())},
    }


def _pct(x):
    """Coerce a probability that may be a fraction (0.52) or percent (52) to an int %."""
    if not isinstance(x, (int, float)):
        return None
    v = float(x)
    if v <= 1.0:
        v *= 100
    return int(round(v))


def market_divergence(pred: dict) -> dict | None:
    """
    Compare the model's win/draw/loss probabilities against the betting market.

    Prefers a STRUCTURED 'market_probs' object (implied_home_win/draw/away_win),
    which the pipeline can persist for an exact three-way comparison. Falls back
    to a conservative parse of the prose 'model_vs_market' field — only when a
    market percentage for the model's favoured side can be extracted with
    confidence — yielding a single favourite-win-probability comparison.

    Returns None when neither is available. Shapes:
        full   -> {"mode":"full", "model":{"home","draw","away"},
                                   "market":{"home","draw","away"}}
        single -> {"mode":"single", "side":"home"|"away", "team":str,
                   "model_pct":int, "market_pct":int, "edge":int}
    """
    mh, md_, ma = pred.get("prob_home_win"), pred.get("prob_draw"), pred.get("prob_away_win")

    # 1) Structured market probabilities (exact, future-proof)
    mp = pred.get("market_probs") or pred.get("market")
    if isinstance(mp, dict):
        mk_home = _pct(mp.get("implied_home_win", mp.get("home")))
        mk_draw = _pct(mp.get("implied_draw", mp.get("draw")))
        mk_away = _pct(mp.get("implied_away_win", mp.get("away")))
        if None not in (mk_home, mk_draw, mk_away) and None not in (mh, md_, ma):
            return {
                "mode": "full",
                "model": {"home": int(mh), "draw": int(md_), "away": int(ma)},
                "market": {"home": mk_home, "draw": mk_draw, "away": mk_away},
            }

    # 2) Conservative parse of the prose, for the model's favoured side only.
    #    Deliberately strict: it is better to show no bar than a wrong one.
    text = (pred.get("model_vs_market") or "").strip()
    if not text or mh is None or ma is None:
        return None
    if int(mh) >= int(ma):
        side, team, model_pct = "home", pred.get("home"), int(mh)
    else:
        side, team, model_pct = "away", pred.get("away"), int(ma)

    # Confidence gate: the prose must actually quote the model's favourite
    # probability. Without that anchor we can't trust which side a market % is for.
    if not re.search(rf"(?<!\d){model_pct}\s*%", text):
        return None

    tm = re.escape(str(team)) if team else None
    market_pct = None
    # Patterns are tried in order of how unambiguously they tie a market % to the
    # model's favourite. Each anchors on the model %, the team, or the word market.
    patterns = []
    if tm:
        #  "<Team> <model>% vs [market] <market>%"   (e.g. "Sweden 50% vs market 76%")
        patterns.append(
            rf"{tm}[^.]{{0,40}}?{model_pct}\s*%\s*vs\.?\s*(?:market(?:'s)?\s*)?(\d{{1,3}})\s*%")
    #  "<model>% ... market('s) ... <market>%"        (e.g. "67% ... the market's 52%")
    patterns.append(
        rf"{model_pct}\s*%[^.]{{0,60}}?market(?:'s)?[^.%]{{0,20}}?(\d{{1,3}})\s*%")
    #  "market('s) ... <market>% ... <model>%"        (e.g. "market favors Brazil at 58% ... 46%")
    patterns.append(
        rf"market(?:'s)?[^.]{{0,60}}?(\d{{1,3}})\s*%[^.]{{0,40}}?(?<!\d){model_pct}\s*%")
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            market_pct = int(m.group(1))
            break

    if market_pct is None or not (0 <= market_pct <= 100):
        return None
    # Final guard: a figure far from the favourite's scale is a mis-parse, not a
    # real divergence — skip rather than mislead.
    if market_pct == model_pct or abs(market_pct - model_pct) > 40:
        return None

    return {
        "mode": "single",
        "side": side,
        "team": team,
        "model_pct": model_pct,
        "market_pct": market_pct,
        "edge": model_pct - market_pct,
    }


def _enrich_match(f: dict, p: dict) -> dict:
    """Flatten one predicted fixture into the metrics the Pulse tab ranks on."""
    grid = p.get("scoreline_grid")
    eg = p.get("expected_goals") or {}
    ph, pd_, pa = p.get("prob_home_win"), p.get("prob_draw"), p.get("prob_away_win")
    home, away = f.get("home"), f.get("away")
    ins = grid_insights(grid) or {}

    egh, ega = eg.get("home"), eg.get("away")
    exp_total = ins.get("exp_total")
    if exp_total is None and egh is not None and ega is not None:
        exp_total = round(egh + ega, 1)

    fav_side = "home" if (ph or 0) >= (pa or 0) else "away"
    fav_team = home if fav_side == "home" else away
    fav_prob = ph if fav_side == "home" else pa
    three = [x for x in (ph, pd_, pa) if x is not None]
    max3 = max(three) if three else None

    div = market_divergence(p)
    edge = edge_team = None
    if div:
        if div["mode"] == "single":
            edge, edge_team = div["edge"], div["team"]
        else:
            fs = "home" if div["model"]["home"] >= div["model"]["away"] else "away"
            edge = div["model"][fs] - div["market"][fs]
            edge_team = home if fs == "home" else away

    return {
        "fixture_id": f.get("id"), "group": f.get("group"), "md": f.get("md"),
        "home": home, "away": away,
        "ph": ph, "pd": pd_, "pa": pa,
        "exp_total": exp_total, "over25": ins.get("over25"), "btts": ins.get("btts"),
        "fav_team": fav_team, "fav_prob": fav_prob, "max3": max3,
        "edge": edge, "edge_team": edge_team,
        "confidence": (p.get("confidence") or "").lower(),
    }


def tournament_insights(fixtures: list[dict], predictions: dict,
                        results: dict) -> dict | None:
    """
    Cross-group storylines for the 'Tournament Pulse' tab, built purely from the
    fixtures that have been predicted so far. Returns None when nothing is
    predicted yet. Each leaderboard is a list of enriched match dicts.
    """
    items = [
        _enrich_match(f, predictions[f.get("id")])
        for f in fixtures
        if _is_populated(predictions.get(f.get("id")))
    ]
    if not items:
        return None

    goals = [i["exp_total"] for i in items if i["exp_total"] is not None]
    avg_goals = round(sum(goals) / len(goals), 1) if goals else None

    value_picks = sorted(
        (i for i in items if i["edge"] is not None),
        key=lambda i: abs(i["edge"]), reverse=True,
    )[:5]
    goal_fests = sorted(
        (i for i in items if i["over25"] is not None),
        key=lambda i: (i["over25"], i["exp_total"] or 0), reverse=True,
    )[:5]
    coin_flips = sorted(
        (i for i in items if i["max3"] is not None),
        key=lambda i: i["max3"],
    )[:5]
    one_sided = sorted(
        (i for i in items if i["fav_prob"] is not None),
        key=lambda i: i["fav_prob"], reverse=True,
    )[:5]

    return {
        "count": len(items),
        "total": len(fixtures),
        "avg_goals": avg_goals,
        "high_conf": sum(1 for i in items if i["confidence"] == "high"),
        "value_edges": sum(1 for i in items if i["edge"] is not None),
        "value_picks": value_picks,
        "goal_fests": goal_fests,
        "coin_flips": coin_flips,
        "one_sided": one_sided,
    }


def team_form(fixtures: list[dict], predictions: dict) -> dict:
    """
    Per-team attacking/defensive form distilled from the group-stage predictions.
    For every team: mean expected goals scored (attack) and conceded (defence)
    across the fixtures that have a populated prediction. Teams with no predicted
    match fall back to a neutral 1.3/1.3 baseline so the bracket still resolves.
    """
    acc: dict[str, dict] = {}
    for f in fixtures:
        p = predictions.get(f.get("id"))
        if not _is_populated(p):
            continue
        eg = p.get("expected_goals") or {}
        egh, ega = eg.get("home"), eg.get("away")
        if egh is None or ega is None:
            continue
        h, a = f.get("home"), f.get("away")
        acc.setdefault(h, {"gf": 0.0, "ga": 0.0, "n": 0})
        acc.setdefault(a, {"gf": 0.0, "ga": 0.0, "n": 0})
        acc[h]["gf"] += egh; acc[h]["ga"] += ega; acc[h]["n"] += 1
        acc[a]["gf"] += ega; acc[a]["ga"] += egh; acc[a]["n"] += 1

    form: dict[str, dict] = {}
    for t in {f.get(k) for f in fixtures for k in ("home", "away") if f.get(k)}:
        d = acc.get(t)
        if d and d["n"]:
            gf, ga = d["gf"] / d["n"], d["ga"] / d["n"]
        else:
            gf = ga = 1.3
        form[t] = {"gf": round(gf, 2), "ga": round(ga, 2),
                   "rating": round(gf - ga, 3), "n": (d["n"] if d else 0)}
    return form


def _poisson_pmf(lam: float, k: int) -> float:
    return math.exp(-lam) * lam ** k / math.factorial(k)


def _resolve_tie(a: str, b: str, form: dict, max_goals: int = 6) -> dict:
    """
    Project a single knockout tie between team a and team b from their form.
    Independent Poissons with blended lambdas; draws are split so the winner is
    whichever side is likeliest in 90 mins, with knockout draws flagged a.e.t.
    """
    fa = form.get(a, {"gf": 1.3, "ga": 1.3})
    fb = form.get(b, {"gf": 1.3, "ga": 1.3})
    lam_a = min(4.0, max(0.2, (fa["gf"] + fb["ga"]) / 2))
    lam_b = min(4.0, max(0.2, (fb["gf"] + fa["ga"]) / 2))

    pa = [_poisson_pmf(lam_a, i) for i in range(max_goals + 1)]
    pb = [_poisson_pmf(lam_b, j) for j in range(max_goals + 1)]

    p_a_win = p_b_win = p_draw = 0.0
    best_dec, best_dec_p = None, -1.0   # most-likely decisive scoreline
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            pij = pa[i] * pb[j]
            if i > j:
                p_a_win += pij
            elif j > i:
                p_b_win += pij
            else:
                p_draw += pij
            if i != j and pij > best_dec_p:
                best_dec_p, best_dec = pij, (i, j)

    a_stronger = p_a_win >= p_b_win
    winner, loser = (a, b) if a_stronger else (b, a)
    # most-likely decisive score, oriented so the winner's tally is first
    si, sj = best_dec or (1, 0)
    hi, lo = (max(si, sj), min(si, sj))
    score = f"{hi}-{lo}"
    # if 90-min most-likely cell was a draw, label it as settled after extra time
    aet = (p_draw >= max(p_a_win, p_b_win))
    win_prob = round(100 * (p_a_win if a_stronger else p_b_win)
                     / max(1e-9, p_a_win + p_b_win))
    return {"winner": winner, "loser": loser, "score": score,
            "aet": aet, "win_prob": win_prob}


# ─────────────────────────────────────────────────────────────────────────────
#  OFFICIAL 2026 WORLD CUP KNOCKOUT STRUCTURE
#  Source: FIFA / Wikipedia "2026 FIFA World Cup knockout stage".
#  The bracket is FIXED by group-finish position — it is NOT re-seeded by team
#  strength. The 12 group winners, 12 runners-up and 8 best third-placed teams
#  drop into predetermined Round-of-32 slots (FIFA match numbers 73–88). Eight
#  of those 16 matches pit a group winner against a third-placed team; FIFA
#  allocates those eight thirds to slots by WHICH GROUP they came from, via the
#  eligibility table below (a winner never meets a third from its own group).
# ─────────────────────────────────────────────────────────────────────────────

# Each R32 match -> its two slots. Slot codes:
#   ("1", "E")  -> winner of group E
#   ("2", "C")  -> runner-up of group C
#   ("3", None) -> a best-third team, assigned via _THIRD_ELIGIBILITY
_R32_MATCHES = {
    73: (("2", "A"), ("2", "B")),
    74: (("1", "E"), ("3", None)),
    75: (("1", "F"), ("2", "C")),
    76: (("1", "C"), ("2", "F")),
    77: (("1", "I"), ("3", None)),
    78: (("2", "E"), ("2", "I")),
    79: (("1", "A"), ("3", None)),
    80: (("1", "L"), ("3", None)),
    81: (("1", "D"), ("3", None)),
    82: (("1", "G"), ("3", None)),
    83: (("2", "K"), ("2", "L")),
    84: (("1", "H"), ("2", "J")),
    85: (("1", "B"), ("3", None)),
    86: (("1", "J"), ("2", "H")),
    87: (("1", "K"), ("3", None)),
    88: (("2", "D"), ("2", "G")),
}

# For each match whose second slot is a best-third, the GROUPS whose third-placed
# team may be slotted there (FIFA's third-place allocation eligibility).
_THIRD_ELIGIBILITY = {
    74: set("ABCDF"),
    77: set("CDFGH"),
    79: set("CEFHI"),
    80: set("EHIJK"),
    81: set("BEFIJ"),
    82: set("AEHIJ"),
    85: set("EFGIJ"),
    87: set("DEIJL"),
}

# Bracket leaf order: the 16 R32 matches laid out so that resolving adjacent
# pairs round-by-round reproduces the official R16 → QF → SF → Final tree.
_R32_LEAF_ORDER = [74, 77, 73, 75, 83, 84, 81, 82,
                   76, 78, 79, 80, 86, 88, 85, 87]


def _allocate_thirds(third_groups: list[str]) -> dict[int, str] | None:
    """
    Assign the eight qualifying third-placed teams (identified by their group
    letter) to the eight R32 slots reserved for thirds, honouring FIFA's
    per-slot eligibility table. Returns {match_number: group_letter}, or None if
    no valid assignment exists. Solved as an exact bipartite matching; the most
    constrained slots are filled first and groups are tried alphabetically, so
    the projection is deterministic and stable run-to-run.
    """
    groups = sorted(set(third_groups))
    if len(groups) != 8:
        return None
    # fill the most constrained slots first (fewer eligible groups → fewer choices)
    slots = sorted(_THIRD_ELIGIBILITY,
                   key=lambda m: len(_THIRD_ELIGIBILITY[m] & set(groups)))
    assignment: dict[int, str] = {}
    used: set[str] = set()

    def backtrack(i: int) -> bool:
        if i == len(slots):
            return True
        m = slots[i]
        for g in groups:                      # alphabetical → deterministic
            if g in used or g not in _THIRD_ELIGIBILITY[m]:
                continue
            assignment[m] = g
            used.add(g)
            if backtrack(i + 1):
                return True
            used.remove(g)
            del assignment[m]
        return False

    return assignment if backtrack(0) else None


def qualifiers(fixtures: list[dict], results: dict, predictions: dict) -> dict:
    """
    Determine the 32 qualified teams from the projected group tables:
    the top two of every group plus the eight best third-placed teams
    (ranked across groups by Pts, then GD, then GF).

    Returns {"teams": [ordered-by-rating list of qualifier dicts], "thirds": [...],
             "groups_projected": int, "groups_total": int}. Each qualifier dict:
        {"team", "group", "pos" (1/2/3), "pts", "gd", "gf"}.
    """
    groups = groups_in_order(fixtures)
    status_full = 0
    direct: list[dict] = []
    thirds: list[dict] = []
    for g in groups:
        rows = predicted_standings(fixtures, results, predictions, g)
        st = group_prediction_status(fixtures, results, predictions, g)
        if st["fully_projected"]:
            status_full += 1
        for pos, r in enumerate(rows, 1):
            entry = {"team": r["team"], "group": g, "pos": pos,
                     "pts": r["Pts"], "gd": r["GD"], "gf": r["GF"]}
            if pos <= 2:
                direct.append(entry)
            elif pos == 3:
                thirds.append(entry)

    thirds.sort(key=lambda e: (e["pts"], e["gd"], e["gf"]), reverse=True)
    best_thirds = thirds[:8]
    quals = direct + best_thirds

    form = team_form(fixtures, predictions)
    for q in quals:
        q["rating"] = form.get(q["team"], {}).get("rating", 0.0)
    quals.sort(key=lambda q: q["rating"], reverse=True)

    return {"teams": quals, "thirds_cut": best_thirds,
            "groups_projected": status_full, "groups_total": len(groups)}


def knockout_bracket(fixtures: list[dict], results: dict, predictions: dict) -> dict | None:
    """
    Build the projected knockout bracket (Round of 32 → Final) on the OFFICIAL
    2026 World Cup structure: qualifiers are slotted by their LIVE group finish
    (winner / runner-up / best-third, from played results only) into FIFA's fixed
    bracket positions, NOT re-seeded by strength. Each tie is then resolved with
    _resolve_tie (which still uses the model's xG form for the outcome).

    groups_projected counts groups whose every match has been played, so the
    bracket field firms up as real results come in (0 → 12).

    Returns None if the field is not the expected 12 groups, or the eight best
    thirds cannot be legally allocated. Output:
        {"rounds": [ {"name", "ties": [ {a,b,winner,loser,score,aet,win_prob,
                                         a_group,b_group,a_slot,b_slot,match} ] }, ... ],
         "champion": team, "groups_projected": int, "groups_total": int,
         "partial": bool}
    a_slot / b_slot are the FIFA slot labels ("1E", "2C", "3F" …); 'match' is the
    FIFA match number for Round-of-32 ties.
    """
    groups = groups_in_order(fixtures)
    if len(groups) < 12:
        return None

    standings = {g: current_standings(fixtures, results, g) for g in groups}
    if any(len(standings[g]) < 3 for g in groups):
        return None

    def _complete(g: str) -> bool:                # every group match played
        stt = group_prediction_status(fixtures, results, predictions, g)
        return stt["total"] > 0 and stt["played"] == stt["total"]
    status_full = sum(1 for g in groups if _complete(g))

    pos1 = {g: standings[g][0]["team"] for g in groups}
    pos2 = {g: standings[g][1]["team"] for g in groups}
    pos3 = {g: standings[g][2]["team"] for g in groups}

    # best 8 third-placed teams, ranked across groups by Pts → GD → GF
    thirds = sorted(
        ({"group": g, "pts": standings[g][2]["Pts"],
          "gd": standings[g][2]["GD"], "gf": standings[g][2]["GF"]} for g in groups),
        key=lambda e: (e["pts"], e["gd"], e["gf"]), reverse=True)
    third_slot = _allocate_thirds([e["group"] for e in thirds[:8]])
    if third_slot is None:
        return None
    third_team = {m: pos3[g] for m, g in third_slot.items()}   # match → third team

    def team_for(slot, match_no):
        kind, grp = slot
        return pos1[grp] if kind == "1" else pos2[grp] if kind == "2" else third_team[match_no]

    def label_for(slot, match_no):
        kind, grp = slot
        return f"1{grp}" if kind == "1" else f"2{grp}" if kind == "2" else f"3{third_slot[match_no]}"

    form = team_form(fixtures, predictions)
    group_of = {standings[g][p]["team"]: g for g in groups for p in range(3)}

    # ── Round of 32, in bracket-leaf order so the tree resolves correctly ──
    r32 = []
    for m in _R32_LEAF_ORDER:
        sa, sb = _R32_MATCHES[m]
        a, b = team_for(sa, m), team_for(sb, m)
        res = _resolve_tie(a, b, form)
        res.update({"a": a, "b": b,
                    "a_group": group_of.get(a), "b_group": group_of.get(b),
                    "a_slot": label_for(sa, m), "b_slot": label_for(sb, m),
                    "match": m})
        r32.append(res)

    rounds = [{"name": "Round of 32", "ties": r32}]
    current = [t["winner"] for t in r32]
    for name in ["Round of 16", "Quarter-finals", "Semi-finals", "Final"]:
        ties, nxt = [], []
        for k in range(0, len(current), 2):
            a, b = current[k], current[k + 1]
            res = _resolve_tie(a, b, form)
            res.update({"a": a, "b": b,
                        "a_group": group_of.get(a), "b_group": group_of.get(b)})
            ties.append(res)
            nxt.append(res["winner"])
        rounds.append({"name": name, "ties": ties})
        current = nxt

    return {
        "rounds": rounds,
        "champion": current[0] if current else None,
        "groups_projected": status_full,
        "groups_total": len(groups),
        "partial": status_full < len(groups),
    }


def match_predictions(fixtures: list[dict], predictions: dict,
                      results: dict, group: str) -> list[dict]:
    """
    Per-fixture prediction rows for the probability bars + detail dropdowns.
    Always returns a row per group fixture; fixtures whose prediction entry is
    still all-null (skeleton, not yet run) render as 'pending'.

    `predicted_scoreline` is passed through verbatim from predictions.json.
    `actual_score` comes from results.json ("—" until the match is played), and
    `prediction_score` grades the prediction against that actual once known
    (None until then).
    """
    out = []
    for f in fixtures_in_group(fixtures, group):
        fid = f.get("id")
        p = predictions.get(fid, {})
        grid = p.get("scoreline_grid")

        res = results.get(fid, {})
        actual = None
        if res.get("played") and res.get("home_score") is not None \
                and res.get("away_score") is not None:
            actual = f"{res['home_score']}-{res['away_score']}"

        out.append({
            "fixture_id": fid,
            "home": f.get("home"),
            "away": f.get("away"),
            "md": f.get("md"),
            "prob_home_win": p.get("prob_home_win"),
            "prob_draw": p.get("prob_draw"),
            "prob_away_win": p.get("prob_away_win"),
            "expected_goals": p.get("expected_goals"),
            "predicted_scoreline": p.get("predicted_scoreline"),
            "top_scorelines": p.get("top_scorelines"),
            "actual_score": actual or "—",
            "prediction_score": prediction_score(grid, actual),
            "outcome_call": _outcome_call(p, actual),
            "has_prediction": _is_populated(p),
        })
    return out

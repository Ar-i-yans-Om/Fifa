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


def _sort_table(rows: list[dict]) -> list[dict]:
    """FIFA tie-break order: points, then goal difference, then goals for."""
    return sorted(
        rows,
        key=lambda r: (r["Pts"], r["GF"] - r["GA"], r["GF"]),
        reverse=True,
    )


def current_standings(fixtures: list[dict], results: dict, group: str) -> list[dict]:
    """
    Build the live table for a group from played results only.
    Each row: team, P, W, D, L, GF, GA, GD, Pts (sorted).
    """
    table = {t: _blank_row(t) for t in teams_in_group(fixtures, group)}

    for f in fixtures_in_group(fixtures, group):
        res = results.get(f.get("id"), {})
        if not res.get("played"):
            continue
        h, a = f.get("home"), f.get("away")
        hs, as_ = res.get("home_score"), res.get("away_score")
        if h not in table or a not in table or hs is None or as_ is None:
            continue
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

    rows = _sort_table(list(table.values()))
    for r in rows:
        r["GD"] = r["GF"] - r["GA"]
    return rows


def predicted_standings(fixtures: list[dict], results: dict,
                        predictions: dict, group: str) -> list[dict]:
    """
    Projected final table. Starts from actual played results, then for every
    UNPLAYED fixture awards points by the prediction's most-likely outcome
    (home win / draw / away win). Expected goals feed GF/GA when present so the
    projected GD is meaningful; falls back to the predicted scoreline, else 0.

    Returns rows tagged with 'delta' (up/down/flat) vs the current table.
    """
    # baseline = whatever has actually been played
    base_current = {r["team"]: r for r in current_standings(fixtures, results, group)}
    table = {t: dict(base_current.get(t, _blank_row(t))) for t in teams_in_group(fixtures, group)}
    for r in table.values():
        r.pop("GD", None)  # recompute at the end

    for f in fixtures_in_group(fixtures, group):
        fid = f.get("id")
        if results.get(fid, {}).get("played"):
            continue  # already counted in baseline
        pred = predictions.get(fid)
        if not _is_populated(pred):
            continue  # skeleton entry, pipeline hasn't run this fixture yet
        h, a = f.get("home"), f.get("away")
        if h not in table or a not in table:
            continue

        ph = pred.get("prob_home_win", 0)
        pd = pred.get("prob_draw", 0)
        pa = pred.get("prob_away_win", 0)

        # expected goals -> projected GF/GA (rounded), else parse scoreline
        eg = pred.get("expected_goals") or {}
        hg, ag = eg.get("home"), eg.get("away")
        if hg is None or ag is None:
            sl = pred.get("predicted_scoreline")
            if sl and "-" in sl:
                try:
                    hg, ag = (int(x) for x in sl.split("-", 1))
                except ValueError:
                    hg, ag = 0, 0
            else:
                hg, ag = 0, 0
        hg_r, ag_r = round(hg), round(ag)

        table[h]["P"] += 1; table[a]["P"] += 1
        table[h]["GF"] += hg_r; table[h]["GA"] += ag_r
        table[a]["GF"] += ag_r; table[a]["GA"] += hg_r

        outcome = max((ph, "H"), (pd, "D"), (pa, "A"))[1]
        if outcome == "H":
            table[h]["W"] += 1; table[h]["Pts"] += 3; table[a]["L"] += 1
        elif outcome == "A":
            table[a]["W"] += 1; table[a]["Pts"] += 3; table[h]["L"] += 1
        else:
            table[h]["D"] += 1; table[a]["D"] += 1
            table[h]["Pts"] += 1; table[a]["Pts"] += 1

    rows = _sort_table(list(table.values()))
    for r in rows:
        r["GD"] = r["GF"] - r["GA"]

    # movement vs current ordering
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


def match_predictions(fixtures: list[dict], predictions: dict,
                      group: str) -> list[dict]:
    """
    Per-fixture prediction rows for the probability bars + detail dropdowns.
    Always returns a row per group fixture; fixtures whose prediction entry is
    still all-null (skeleton, not yet run) render as 'pending'.

    `predicted_scoreline` is passed through verbatim from predictions.json —
    the scoreline (a bare score like "2-0") is computed by match_runner when it
    writes the file. The UI does not derive or override it.
    """
    out = []
    for f in fixtures_in_group(fixtures, group):
        fid = f.get("id")
        p = predictions.get(fid, {})
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
            "has_prediction": _is_populated(p),
        })
    return out
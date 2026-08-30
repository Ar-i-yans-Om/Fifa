# Siuuumulator — FIFA World Cup 2026 AI Predictor

A read-only Streamlit dashboard that visualises a multi-agent AI's match-by-match
predictions for the **2026 FIFA World Cup** — full scoreline distributions, group
tables, a live knockout bracket, and an end-of-tournament model **report card**.

🔗 **Live app:** https://wc-agentic-simulator.streamlit.app/

> The predictions come from a separate engine — the
> [WC_Simulator](https://github.com/Ar-i-yans-Om/WC_Simulator) multi-agent pipeline.
> This repo is the **dashboard only**: it reads the engine's JSON output and never
> calls the model. One-way data flow, so the UI stays fast.

---

## How it turned out

The tournament is complete — **Spain beat Argentina 1-0 (a.e.t.) in the final**.
The model's own bracket had crowned **Argentina**, who reached the final and lost,
so the champion call came agonisingly close. Across all **104 matches** the model
hit **~71% outcome accuracy**, peaking at **100% in the quarter-finals**. See the
**Report Card** tab for the full grade — accuracy by stage, sharpest reads, and
biggest misses (backing Germany over Paraguay was the costliest).

## What's in the dashboard

| Tab | What it shows |
|---|---|
| **Groups** | Live vs projected group tables, and a rich card per fixture — win/draw/loss bar, xG, predicted scoreline, the full Poisson scoreline heatmap, grid-derived betting markets, model-vs-market divergence, and a shareable PNG card. |
| **Tournament Pulse** | Cross-group storylines: biggest market gaps, goal-fests, coin-flips, safest bankers. |
| **Knockout Matches** | The same rich cards for every knockout tie (R32 → Final), grouped into per-round sub-tabs, with the model's two-way "who advances" call and a ✓/✗ verdict. |
| **Knockout Bracket** | The live bracket, driven by the real feeder tree — real results where played, model prediction otherwise, form projection as a fallback, all the way to the champion. |
| **Report Card** | The end-of-tournament grade: final four, the model's champion call vs reality, outcome accuracy by stage, and its best calls / biggest misses. |
| **How It Works** | The multi-agent pipeline explained. |

## How the predictions are made

The engine models each match as two isolated team analyses (chemistry, game
theory, scouting, tactics) that collide in a Pitch Simulator, then weights in
black-swan scenarios and folds everything into a Poisson **mixture**
distribution. See the engine repo for the full architecture.

Knockouts are graded on **advancement** (who went through), not the draw-inclusive
scoreline — a knockout has no draws.

## Run it locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Data contract

The dashboard reads three files from `data/` (written by the engine):

- `fixtures.json` — 104 fixtures (72 group + 32 knockout `M73`–`M104`). Knockout
  ties carry a `round` and slot-reference `home`/`away` (`1A`/`2B`/`3E` group slots,
  `W77`/`L101` match slots) that resolve from results.
- `results.json` — scores as `{id, home_score, away_score, played}`; a level knockout
  tie decided on penalties adds `"winner": "<team>"`.
- `predictions.json` — per-fixture model output (probabilities, expected goals,
  scoreline grid, narrative, market anchor).

`ui_data.py` is the data layer (loading, standings, bracket resolution, accuracy);
`app.py` is the render layer; `share_card.py` builds the shareable PNGs.

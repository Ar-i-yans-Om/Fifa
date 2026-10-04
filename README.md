# Siuuumulator — FIFA World Cup 2026 AI Predictor

An AI "coaching staff" that predicted all 104 matches of the 2026 FIFA World Cup —
every group game and the whole knockout bracket — with a probability for every
possible scoreline, not just a winner.

🔗 **Live app:** https://wc-agentic-simulator.streamlit.app/

---

## How it turned out

**Spain won the World Cup**, beating Argentina 1-0 after extra time. The model's
bracket had crowned **Argentina**, who reached the final and lost, so the
champion call came agonisingly close.

Across all 104 matches the model called **71% of outcomes**, including all four
quarter-finals. Its costliest miss was backing Germany against Paraguay, who went
through on penalties. The **Report Card** tab has the full grade.

## What's in the app

| Tab | What you'll see |
|---|---|
| **Groups** | Live and projected tables for all 12 groups, plus a card for every match: win/draw/loss odds, expected goals, the predicted score, a heatmap of every possible scoreline, betting-style markets (over/under, both teams to score), how the model compared with the bookmakers, and a shareable image. |
| **Tournament Pulse** | Storylines across the groups: the biggest gaps between model and market, the likeliest goal-fests, the true coin-flips and the safest bets. |
| **Knockout Matches** | The same rich cards for every knockout tie, Round of 32 to the Final, with the model's pick to advance and a ✓ / ✗ once the result was in. |
| **Knockout Bracket** | The full bracket, from the Round of 32 to the champion. |
| **Report Card** | The final four, the model's champion call against reality, accuracy round by round, and its sharpest calls and biggest misses. |
| **How It Works** | The pipeline, explained step by step. |

## How it works

Think of it as a national team's backroom staff, rebuilt as AI agents:

- **The Researcher** reads the latest team news (injuries, suspensions, likely
  line-ups) and works out each squad's fitness from real travel distances, rest
  days, altitude and climate.
- **Two isolated team rooms.** Each side gets its own chemistry analyst,
  tournament strategist, opposition scout and head coach. Neither room ever sees
  the other's thinking, just like two rival camps.
- **The Pitch Simulator** is the only place the two game plans meet. It sets how
  many goals each team should expect.
- **The Chaos Agent** accounts for red cards, VAR penalties and injuries, each
  weighted by how likely it is rather than rolled like a dice.
- **The Bookmaker** brings in the betting market as an outside reference.
- **The Judge** turns it all into a probability for every scoreline, and from
  there the win / draw / loss odds.

Knockout ties are graded on **who went through**, since a knockout can't end in a
draw.

Curious about the engine underneath? It's open source:
[WC_Simulator](https://github.com/Ar-i-yans-Om/WC_Simulator).

## Run it locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

The app only reads the prediction files in `data/`, so it needs no API keys.

---

Built with LangGraph, Google Gemini and Streamlit.

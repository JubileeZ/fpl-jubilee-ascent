# Outfield return minutes

## Verdict

Three-fixture minutes MAE improved in both models: Confirmed Champion **47.99 → 38.03**, Participation State Hybrid **40.85 → 35.93**. First-fixture MAE **45.07 → 15.19** and **37.22 → 22.44**, respectively. [Results](results.jsonl), summary rows keyed by model.

Three overrides, zero false restorations. Palmer forecast 60, played 57. Gabriel forecast 65, played 76. Guimarães forecast 65, played 74. Palmer's GW13 clearance and Salah's fit benchings produced no restoration. Removing earlier Palmer case avoids overlapping outcomes and retains improvement in both models (53.46 → 41.01 and 44.93 → 38.77).

Manual review supported for one fixture after evidence of match readiness. Case count limits inference about false restorations. Later projections inherit native estimates and can remain depressed. No multi-fixture curve or transfer decision tested.

## Method

Five sourced 2025–26 player-deadlines, four distinct players. Compare native minutes with first-fixture-only override. Same pre-deadline inputs, Confirmed Champion and Participation State Hybrid. Fixed review queue uses Confirmed Champion points and documented leads, with 4 GK / 10 DEF / 10 MID / 6 FWD. Historical market reconstructed from players with pre-deadline observations. Receipts sampled for this test. Full historical club scan and User Squad unavailable.

Established starter = at least five starts in six eligible fixtures immediately preceding injury or role change. Count fit benchings. Exclude documented unavailable fixtures and injury-onset match. Match player identity across seasons by Official code when current season has insufficient history. Match-fit reference = median minutes from starts in eligible window.

- Available with uncertain readiness or fit selection change: leave minutes alone.
- Return appearance and explicit start readiness with workload uncertainty: 60 minutes, capped at match-fit reference.
- Return appearance followed by readiness evidence without reported setback: 65 minutes, capped at match-fit reference.
- Write first fixture only. Later predictions inherit native minutes.

**Minutes MAE** = mean absolute difference between projected and Official FPL minutes per player-fixture. Lower ↓. Ideal 0. **False restoration** = upward override for a player who does not start first fixture. Lower ↓. Ideal 0 alongside count of overrides.

Run `uv run --locked python docs/research/outfield-return-minutes/runner.py` from repository root. [Raw results](results.jsonl) include per-fixture starts, observed minutes, both forecasts, healthy references, and model summaries. Archive checks enforce unique player-fixture keys, valid timestamps, binary start flags, 0–90 minutes, and three matched outcomes per case. Forecast builder uses 2024–25 seed with pre-deadline 2025–26 history. Native forecasts approximate current behavior when no analyst override exists. Historical flag snapshots and analyst decisions unavailable. No validation-season or live changes.

## Frozen evidence

- **Palmer GW13, available.** Maresca said Palmer was available and still working back to full fitness. No appearance since injury at evidence cutoff. GW2–3 documented absence omitted from healthy window. GW4 bench appearance retained. [Late withdrawal](https://www.chelseafc.com/en/news/article/enzo-maresca-issues-cole-palmer-update) · [Brentford team news](https://www.chelseafc.com/en/news/article/enzo-maresca-confirms-chelsea-team-news-for-brentford-2025) · [Arsenal team news](https://www.chelseafc.com/en/news/article/enzo-maresca-confirms-chelsea-team-news-for-arsenal)
- **Palmer GW15, managed and ready to start.** Played 29 minutes at Leeds. Maresca confirmed readiness to start, with full-match fitness uncertain. [Bournemouth briefing](https://www.chelseafc.com/en/news/article/enzo-maresca-cole-palmer-is-ready-to-play-from-the-start)
- **Salah GW15, selection change.** Two league non-starts with no new injury and role selection still open. [Pre-Leeds briefing](https://www.liverpoolfc.com/news/leeds-united-v-liverpool-team-news-0)
- **Gabriel GW19, returned.** Came on against Brighton after documented injury spell. [Injury briefing](https://www.premierleague.com/en/news/4466322) · [Pre-Villa update](https://www.bbc.co.uk/sport/football/live/cp39e3w93d3t?page=3)
- **Bruno Guimarães GW34, returned.** Comeback appearance against Bournemouth, followed by group training before Arsenal. Earlier GW23–24 missed through ankle injury and excluded from healthy window. [Villa absence](https://www.newcastleunited.com/en/news/confirmed-line-aston-villa-h-25-26) · [Liverpool absence](https://www.newcastleunited.com/en/news/confirmed-line-up-three-changes-at-anfield) · [Bournemouth match report](https://www.newcastleunited.com/en/news/afc-bournemouth-h-report-25-26) · [Pre-Arsenal training update](https://www.newcastleunited.com/en/news/toon-in-training-bruno-guimaraes-and-co-prepare-for-arsenal-task)

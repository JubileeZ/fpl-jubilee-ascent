# Learned score from component forecasts

- **Issue** [#205](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/205)
- **Baseline** `def_xg_shrink_challenger`
- **Prototype** [`component_score_head`](prototypes/component_score_head/prototypes.py)
- **Scope** One fixed candidate under [ADR 0071](../../adr/0071-certified-solver-budget-and-milp-qualification-calibration.md).

## Design

- Target signed native FPL points per player and fixture, including recorded zero-minute outcomes.
- Input 13 Champion scoring components, projected minutes, projected BPS, projected ICT, and position indicators interacted with projected appearance points.
- Project BPS and ICT from completed performances available at each issue. Shrink each player's per-minute rate toward the position pool with 360 pseudo-minutes, then multiply by projected fixture minutes.
- Fit Gaussian identity-link ridge with penalty `0.01` on RMS-scaled columns and no free intercept. Use Champion points until at least four labeled issue Gameweeks. Preserve zero-exposure and blank projections. Apply the first-target fit across all six leads.
- Keep component forecasts available for individual guards. Reconcile learned total as component sum plus an explicit `score_head_adjustment`.
- Train on earlier first-target Champion forecasts reconstructed from their own issue-time inputs. Match settled rows by player, Gameweek, and fixture using only the current staged history. Fit anew at each deadline. Exclude unmatched rows and forecasts with zero projected minutes.
- Ledger screen distinguishes this direct score fit from `b2_res_*`, which learned a residual or hurdle from a face-value base reconstructed inside its fit history. Existing lock retained.

## Evaluation

- S-1 Dev `2025-26` with `2024-25` seed. Full GW1–38 independent Strategic six-Gameweek rolling arms, `600s` certified limit per solve and `0.0` target gap. Require admitted GW1–7 parity.
- S-2 Historical Filter `2024-25` with `2023-24` seed. Single frozen candidate after a Dev pass, with a fresh same-host Champion arm and admitted GW1 parity.
- Admitted prefixes provide independent parity checks. Later origins use pinned historical fixture and availability inputs with reconstructed as-of history. `2026-27` outcomes sealed.

### Metric Definitions & Direction

- **Net FPL points** = realized credited squad points less transfer hits, summed over the replay. Higher is better. Qualification needs candidate minus Champion strictly positive in both seasons.
- **Segment delta** = paired net-point difference divided by Gameweeks in each segment. Higher is better. Floors `−8.9`, `−4.7`, `−4.2` points/GW for GW1–4, GW5–19, GW20–38.
- **Projection guards** compare fixture projections aggregated to player-Gameweek totals against outcomes at leads 0–5. Lower mean squared error for points and scoring terms and lower mean absolute error for minutes are better. Benchmark Champion loss plus the frozen guard margin. Definitions and calibration in [the evaluator](../../../backtesting/promotion_evidence.py).
- **First-target fixture MSE** = sum of squared errors in signed FPL points divided by matched player-fixture rows with positive projected minutes. Lower is better. Benchmark paired Champion MSE over the same rows. Diagnostic for forecast accuracy.

## Reproduction

Use the historical replay inputs and receipt manifests listed in the [pre-slate report](pre-slate-search-2026-11-21.md). The prototype requires the research replay path to build its training inputs from earlier origins. These runner changes are bound into the new protocol hash. Re-verify earlier S-2 reservations from their original pinned checkout.

```bash
topic=docs/research/candidate-ideation
lane="$topic/prototypes/component_score_head"
work=.tmp/agent/explore-candidate/component-score-head
reviewed=baf8d1bb5d4a1e1e66044320959715218c1eda23529af41c288583d0efd233c5
PYTHONPATH=. uv run python -u "$topic/run_s1_replay.py" --work "$work"
PYTHONPATH=. uv run python -u "$topic/run_s1_replay.py" --work "$work" \
  --prototype "$lane/prototypes.py" --variant component_score_head --reviewed-sha256 "$reviewed"
```

Set `champion_run` and `candidate_run` to the replay directories printed by each command.

```bash
PYTHONPATH=. uv run python "$topic/audit_historical_prefix.py" \
  --champion "$champion_run" --candidate "$candidate_run" --prototype "$lane/prototypes.py" \
  --reviewed-sha256 "$reviewed" --out "$lane/s1_prefix_parity.csv"
PYTHONPATH=. uv run python "$topic/compare_historical_replays.py" \
  --champion "$champion_run" --candidate "$candidate_run" --out "$lane/s1"
```

After an S-1 pass, run both S-2 arms sequentially with [the development pin](prototypes/component_score_head/development_selection.json).

```bash
PYTHONPATH=. uv run python -u "$topic/run_s2_filter.py" \
  --pin "$lane/development_selection.json" --arm champion
PYTHONPATH=. uv run python -u "$topic/run_s2_filter.py" \
  --pin "$lane/development_selection.json" --arm candidate
```

Set `champion_run` and `candidate_run` to the printed S-2 replay directories.

```bash
PYTHONPATH=. uv run python "$topic/audit_historical_prefix.py" \
  --pin "$lane/development_selection.json" --champion "$champion_run" \
  --candidate "$candidate_run" --prototype "$lane/prototypes.py" \
  --reviewed-sha256 "$reviewed" --out "$lane/s2_prefix_parity.csv"
PYTHONPATH=. uv run python "$topic/compare_historical_replays.py" \
  --season 2024-25 --pin "$lane/development_selection.json" \
  --prefix-parity "$lane/s2_prefix_parity.csv" --champion "$champion_run" \
  --candidate "$candidate_run" --out "$lane/s2"
```

## Results

First-target fixture MSE fell from `5.3151` to `5.2830` points² over `20,484` matched rows (`0.60%` lower). GW5–38, when the learned layer was active, fell from `5.2639` to `5.2279` over `18,243` rows (`0.68%` lower). All 13 component forecasts and projected minutes matched the Champion exactly across all six leads. [Weekly fixture counts and squared-error sums](prototypes/component_score_head/s1_fixture_mse.csv)

**S-1 Dev PASS.** Candidate `2,237`, Champion `2,167`, delta `+70` net points. Segment deltas `0 / +45 / +25` points. All `15/15` projection guards and `3/3` segment floors passed. Six-lead player-Gameweek points MSE rose by `0.0028` points² in the clustered guard with 95% upper bound `0.0220` within margin `0.2067`. Paired block-bootstrap interval `−1.11` to `+4.71` points/Gameweek includes zero. [S-1 summary](prototypes/component_score_head/s1/summary.json) · [Weekly paired scores](prototypes/component_score_head/s1/paired_weekly_scores.csv) · [Projection guards](prototypes/component_score_head/s1/projection_guards.csv)

Both arms reproduced admitted GW1–7 independently. All 14 forecast hashes and settled outcomes matched. Maximum absolute difference across fixture-level scores, components, minutes, and adjustment `0.0`. [Prefix parity](prototypes/component_score_head/s1_prefix_parity.csv)

**S-2 Historical Filter FAIL.** Frozen candidate `2,160`, Champion `2,299`, delta `−139` net points. Segment deltas `0 / −84 / −55` points. The GW5–19 segment averaged `−5.60` points/Gameweek, below its `−4.70` floor. All `14/14` applicable projection guards passed. Both admitted GW1 checks reproduced solver-input hashes and settled outcomes exactly. Paired block-bootstrap interval `−9.03` to `+0.26` points/Gameweek includes zero. [S-2 summary](prototypes/component_score_head/s2/summary.json) · [Weekly paired scores](prototypes/component_score_head/s2/paired_weekly_scores.csv) · [Projection guards](prototypes/component_score_head/s2/projection_guards.csv) · [Prefix parity](prototypes/component_score_head/s2_prefix_parity.csv)

**Disposition.** Zero Win-Both qualifiers. Candidate Ledger Dead lock through the `2027-11-23` revisit date applies to the tested direct ridge specification. The first-target accuracy diagnostic covers the combined feature set, so it cannot isolate the contributions of projected BPS or ICT. [Development pin](prototypes/component_score_head/development_selection.json) · [S-2 reservation](prototypes/component_score_head/s2_attempt.json) · [S-2 protocol](prototypes/component_score_head/s2_protocol.json)

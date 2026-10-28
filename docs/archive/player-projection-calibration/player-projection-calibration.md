# Player Projection Calibration & Tier De-biasing

**Updated**: 2026-10-01T23:20:00+07:00  
**Data stamp**: 2025-26 archive GW1–38 (seed 2024-25); 2024-25 archive GW1–38 (seed none); code at HEAD  
**Season**: Multi-season (2025/26 dev, 2024/25 confirm)  
**Status**: Completed — Candidate Confirm-Fail / Dead (revisit after 2027-10-01)  
**Purpose**: Evaluate calibration mechanisms to resolve extreme player projections (e.g. Haaland 8.5–9.8 pts/GW vs 7.2 historical average) and under-projection of budget starters (−1.5 pt signed bias) under ADR 0054 formation-constrained regret.  
**Scope**: 2 exploratory lanes (Lane 1 `lane_bon` bonus pool saturation with zero-sum fixture conservation; Lane 2 `lane_att` top-end attack de-biasing and regulation minutes clamping), 15 smoke prototype evaluations, and 1 frozen Candidate (`calibrated_rate_challenger`).  
**Related**: [Candidate Ledger](../candidate-ledger/candidate-ledger.md) · [Eval canon](../INDEX.md) · [ADR 0054](../../adr/0054-formation-constrained-xi-regret-and-playable-pool-guardrails.md) · [ADR 0047](../../adr/0047-two-season-promotion-protocol.md)  
**Artifact**: [smoke_results.csv](smoke_results.csv) — 15 smoke prototype evaluations; [candidate_gate.csv](candidate_gate.csv) — dev and confirm promotion gate runs  

## Sources

- **Repository code**: `models/def_xg_shrink_challenger.py`, `models/hold_chase_challenger.py`, `models/learned_start_challenger.py`, `features/builder.py`, `backtesting/walkforward.py`
- **Historical archive**: `data/archive/2025-26/processed` (GW1–38), `data/archive/2024-25/processed` (GW1–38)
- **Prototypes**: `.tmp/agent/explore-candidate/lane_bon/prototypes.py`, `.tmp/agent/explore-candidate/lane_att/prototypes.py`

**Source boundary**: Prototype source code verified with `smoke.py --audit_only` (`AUDIT PASS`, no leakage, no season literals, no undeclared columns).

## Agent Prompt

```text
Full redo docs/research/player-projection-calibration/player-projection-calibration.md

1. Re-read all primary sources and inspect current repository conventions.
2. Verify smoke_results.csv and candidate_gate.csv match candidate ledger evidence.
3. Keep filename stable; update cross-links when sibling notes change.
```

## Method

**Method type**: Empirical backtest / Model Candidate evaluation (ADR 0054 legal formation XI regret protocol).

**Inputs**:
- `features_df`: Feature Contract as-of target Gameweek (points-in-time).
- `history_df`: Finished `player_performances` rows prior to target deadline.

**Procedure**:
1. Diagnose root causes of extreme projections:
   - Winner-take-all Plackett-Luce bonus pool with low temperature $T=6.0$ awarding Haaland ~2.8 bonus points/match.
   - Heuristic top-end multipliers in `hold_chase_challenger` (`_XG_SHARP_SLOPE = 0.25` inflating xG by up to +25%; `_MINS_TILT = 1.04` projecting 93.6 minutes per start).
   - Heuristic 5% down-trim (`_XG_TRIM_FACTOR = 0.95`) on low-xG players penalizing budget starters.
2. Formulate and test Lane 1 (`lane_bon`): soft ceiling $B_{\max} \in [1.20, 1.50]$ on individual bonus points with zero-sum fixture redistribution to starters.
3. Formulate and test Lane 2 (`lane_att`): clamp starting minutes to 90.0, eliminate or dampen xG sharp slope, and remove the 5% low-xG penalty.
4. Promote dev paper winner to registered Candidate `calibrated_rate_challenger` and run confirmation season (2024-25).

### Metric Definitions & Direction

| Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|---|---|---|---|---|---|
| Formation XI Regret | `combined_delta` | Mean per-GW actual point gap: Champion − Candidate on legal 11-man formation | Higher is better $\uparrow$ | $> 0$, $P \ge 0.60$, $\ge 2/3$ segs | Primary promotion gate metric (ADR 0054) |
| Captaincy Regret | `cap_regret` | Point gap between optimal hindsight captain and projected captain | Lower is better $\downarrow$ | $\le \text{Champion} + 0.15$ | Guardrail preventing elite captain errors |
| Playable Pool Bias | `bias_playable` | Mean signed error ($xP - \text{actual}$) for players with $xP \ge 2.0$ or mins $\ge 30$ | Closer to 0 is better | $\le \text{Champion}$ | Guardrail preventing inflation of active assets |

## Findings

### Lane 1 (`lane_bon`): Bonus Saturation & Redistribution
All 5 variants produced negative deltas on dev season:
- `bon_bmax120`: delta −0.1614 (1/3 segs, boot P 0.377)
- `bon_bmax130`: delta −0.1614 (1/3 segs, boot P 0.377)
- `bon_bmax140`: delta −0.1614 (1/3 segs, boot P 0.377)
- `bon_bmax130_nosave`: delta −0.3841 (0/3 segs, boot P 0.204)
- `bon_bmax150`: delta −0.2691 (1/3 segs, boot P 0.306)

*Mechanism insight*: While capping Haaland's single-match bonus expectancy (~2.8 pts) matches historical reality (~1.14 pts), in FPL forwards score exclusively through goals and bonus (no clean sheet or defcon points). Shaving bonus points from top forwards lowered their expected value relative to defenders, causing the formation optimizer to under-select premium attackers, reducing realized XI points.

### Lane 2 (`lane_att`): Attack De-biasing & Minutes Clamping
- Partial de-biasing (`att2_nosharp_notilt`: slope 0.0, tilt 1.0, but retaining low-xG trim 0.95) produced high delta (+0.6764) but failed Captaincy Regret guardrail (4.997 vs 4.831 + 0.15 limit).
- Symmetric calibration (`att2_nosharp_notrim_notilt`: slope 0.0, untrim 1.0, tilt 1.0) achieved a **decisive dev gate PASS**:
  - `combined_delta`: **+0.3549**
  - `segs`: **2/3**
  - `boot_p_gt0`: **0.901**
  - All guardrails passed (Captaincy Regret, Playable Pool Bias, Playable Pool MAE, xMins, Spearman).

### Confirmation Gate (`calibrated_rate_challenger`)
Frozen Candidate evaluated on 2024-25 confirmation season:

| Season | Role | combined_delta | Segments | Boot P | Guardrails | Verdict |
|---|---|---|---|---|---|---|
| **2025-26** | Dev | **+0.3549** | **2/3** | **0.9006** | **PASS** | **PASS** |
| **2024-25** | Confirm | **−0.4488** | **1/3** | **0.2372** | **PASS** | **FAIL** |

*Root cause of confirm failure*: In the 2024-25 season (characterized by extreme haul clustering from Cole Palmer, Haaland, and Saka), the +25% sharp slope on xG helped the model lock onto premium attackers during high-variance hauls. Removing the slope improved efficiency on 2025-26 (+0.355 pts/GW) but penalized haul capture in 2024-25 (−0.449 pts/GW).

## Decision & Candidate Ledger Impact

1. Under ADR 0047, promotion requires gate PASS on both development and confirmation seasons. `calibrated_rate_challenger` failed confirmation season and is NOT promoted.
2. Champion `def_xg_shrink_challenger` (ADR 0055) stands as Model Champion.
3. Levers logged in Candidate Ledger:
   - *Plackett-Luce bonus saturation with zero-sum fixture conservation*: Dead until 2027-10-01.
   - *Top-end attack de-biasing + low-xG untrimming + regulation 90-min clamping*: Dead until 2027-10-01.

# Champion Event Component gap (mse_share)

**Updated**: 2026-09-26T00:30:00+07:00  
**Data stamp**: 2025-26 archive GW1–38; 2026-27 finished GW1–5; companions include `goals_path_challenger` + `defence_link_challenger` (k_cs=1.296903, k_gc=1.145226)  
**Season**: 2025/26 gate · 2026/27 sanity  
**Status**: Active  
**Purpose**: Rank which Event Component drives Model Champion Official MSE; demote finish/link noise via Process G/A and Poisson-xGC CS/GC twins; name Candidate improve target.  
**Scope**: Comparison Slate walk-forward + catalog `goals_path_challenger` (#116) + `defence_link_challenger` (#118). Realized `mse_share` primary. Twins diagnostic only. Not Historical Promotion Gate. Not Extended Process Points. Not Blended component ledger.  
**Related**: [ADR 0038](../../adr/0038-process-points-eval-target.md) · [ADR 0044](../../adr/0044-blended-eval-target-promotion-primary.md) · [champion signed bias](../champion-signed-bias-2025-26/champion-signed-bias-2025-26.md) · [INDEX](../INDEX.md) · [archive testing](../../testing/archive-testing.md) · map [#110](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/110) · [#116](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/116) · [#118](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/118)  
**Artifact**: [component_gap_summary.csv](component_gap_summary.csv) `mse_share` · [component_gap_totals.csv](component_gap_totals.csv) `realized_mae` · [calibrate_goals_k.py](calibrate_goals_k.py) · [calibrate_defence_k.py](calibrate_defence_k.py)

> `Updated` is last note revision time. `Data stamp` is freshness of data or source evidence. Do not add duplicate `Last update` fields.

## Sources

- **Primary**: Grill design 2026-09-25 (mse_share + twins + demotion) — role: ranking object and twin policy
- **Repository data**: `data/archive/2025-26/processed` GW1–38 seed `2024-25`; `data/archive/2026-27/processed` finished GW1–5 seed `2025-26`; `config/model_selection.json`; `uv run python docs/research/champion-component-gap/runner.py`

**Source boundary**: Archive exploratory (`snapshot_backed=false`). Poisson-xGC overstates CS vs Realized (known link bias). Missing actuals filled 0 at player/gameweek grain.

## Agent Prompt

```text
Full redo docs/research/champion-component-gap/champion-component-gap.md

1. Require archives 2025-26 + 2024-25; 2026-27 for sanity.
2. Run: uv run python docs/research/champion-component-gap/runner.py
3. Refresh Findings from component_gap_summary.csv:
   - Gate: evaluation_season=2025-26 pool=all position=ALL model=hold_chase_challenger
   - Rank by |mse_share|; read demotion_label on twin components
   - Sanity: evaluation_season=2026-27 finished GWs
   - Compare slate Δshare vs calibrated_matchup_hybrid / participation_state_hybrid
4. Totals context: component_gap_totals.csv realized|process|blend MAE
5. Do not snapshot numeric totals in this prompt. Scratch under .tmp/agent/; delete before finish.
```

## Method

**Method type**: Walk-forward backtest + additive MSE attribution

**Inputs**:
- Comparison Slate from `config/model_selection.json`
- Evaluation windows + Prior-Season Seeds as in Agent Prompt
- Official `expected_goals` / `expected_assists` / on-pitch `expected_goals_conceded`

**Procedure**:
1. `run_walkforward_backtest` per model/window (Realized component ledger).
2. Attach twins: Process G/A pts; Poisson-xGC CS/GC (`λ` = Official on-pitch xGC; not Feature Contract `per90_goals_conceded`).
3. `mse_share_c = mean(e_c · e) / mean(e²)` with `e = proj − actual` on Realized.
4. Dual pool `all` / `mins_60`; Position `ALL` + GKP/DEF/MID/FWD.
5. Demotion: twin shrink `≥ 0.50` and `|signed_bias| ≤ 0.05` → `variance`; CS/GC shrink with large Realized bias → `link-bias`; else `structural`.
6. Write companions. Primary crown = top `|mse_share|` after demotion read.

**Definitions and assumptions**:
- Primary ranking never uses twin actuals
- Twin λ source ≠ Champion λ (Feature Contract GC rate)
- θ = 0.50; τ = 0.05 (stated constants; τ near Champion bias companion scale)
- `demotion_label=no_twin` when no twin applies (avoid CSV token `n/a` — pandas NA)

### Metric Definitions & Direction

| Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|---|---|---|---|---|---|
| Component MSE share | `mse_share` | $\mathrm{mean}(e_c\cdot e)/\mathrm{mean}(e^2)$ | Rank by $\|\,\|$ | Top structural after demotion | Gap Event Component |
| Twin shrink | `twin_shrink` | $1 - \|mse\_share\_twin\|/\|mse\_share\|$ | Higher → more noise | ≥ 0.50 triggers demotion check | Finish/link noise fraction |
| Twin link bias | `twin_link_bias` | $\mathrm{mean}(twin_c - actual_c)$ | Near zero | Context | Poisson-xGC CS overstatement |
| Demotion label | `demotion_label` | `structural` / `variance` / `link-bias` / `no_twin` | Context | structural = Candidate lever | Decision label |

**Validation boundary**: Exploratory archive. 2026-27 unfinished season. No Availability Snapshots.

## Source synthesis

### Main claims

- Additive MSE partition attributes Official squared error to Event Components.
- Process G/A and Poisson-xGC twins diagnose noise; Blended stays promotion totals only (ADR 0044).

### Source rationale

- Grill probes: Realized primary; twins + demotion; Extended Process deferred.

## Project interpretation

### Decision rules

- Crown = highest `|mse_share|` on Champion gate row (`pool=all`, `position=ALL`) after applying `demotion_label`.
- `variance` → do not open Candidate on that component rate.
- `link-bias` on CS/GC → Candidate targets Poisson CS link / calibration, not only λ inputs.
- `structural` → Candidate lever mapped to that Event Component.
- If slate parent shows same top structural component, gap is inherited; else hold-chase-specific.
- `mins_60` slice = rate check; may demote attack noise that `all` keeps as structural.

### Practical implications

- Step-1 diagnosis complete when crown named. Step-2 = Candidate design for crown.

## Findings

### Evidence

- Gate Champion `hold_chase_challenger` `2025-26` `pool=all` `position=ALL`: top `mse_share` = `xp_goals` with `demotion_label=structural` (twin shrink clears θ but `|signed_bias|` exceeds τ). Source: [component_gap_summary.csv](component_gap_summary.csv) `mse_share` / `demotion_label`.
- Same gate: `xp_clean_sheet` and `xp_assists` → `variance` (finish/CS noise). Next non-twin mass: `xp_bonus`, `xp_minutes`.
- `mins_60` same gate: `xp_goals` → `variance`; `xp_clean_sheet` → `link-bias` (Poisson twin shrinks share but Realized CS bias remains). Rate-view crown after variance skip = CS link / then `xp_bonus`.
- Position secondary (`pool=all`): GKP/DEF top raw share = `xp_clean_sheet` (`variance`); MID/FWD = `xp_goals` (`structural`).
- Slate: `calibrated_matchup_hybrid` and `participation_state_hybrid` same gate crown `xp_goals` `structural` — gap **inherited**, not hold-chase-only.
- Sanity `2026-27` GW1–5 Champion `pool=all`: same pattern — `xp_goals` `structural`; CS/assists `variance`.
- Totals: Champion gate Realized MAE below parents ([component_gap_totals.csv](component_gap_totals.csv) `realized_mae`); component crown still goals.

### Alternatives

- Rank by component MAE — rejected.
- Blended / Extended Process primary — rejected (grill).
- Open Candidate on CS from `all`-pool raw rank-2 — rejected (`variance`).

### Open questions

- Bonus / minutes / Defcon / cards Candidate if goals+defence residual MSE reorders.
- Admission race for `defence_link_challenger` (#112) then soft pre-gate flip → `--apply`.

## Post-goals residual (#116)

Catalog Candidate `goals_path_challenger`: identity xG sharp/ceiling off; `_GOAL_WEIGHT_SCALE=0.891559` from [calibrate_goals_k.py](calibrate_goals_k.py) on 2025-26 gate after identity sharp.

| Row | Champion | goals_path |
|---|---|---|
| 2025-26 `all`/`ALL` `xp_goals` | bias +0.075 `structural` \|mse_share\| 0.327 | bias +0.047 **`variance`** \|mse_share\| 0.322 |
| 2025-26 `mins_60`/`ALL` `xp_clean_sheet` | link-bias −0.188 | link-bias −0.188 |
| 2025-26 `mins_60`/`ALL` `xp_conceded` | variance +0.048 | variance +0.048 |

**Soft pre-gate goals arm (#115):** PASS — Candidate improves `|mse_share|`, `|bias|`, and clears `structural`→`variance` vs Champion on gate `xp_goals`. Source: [component_gap_summary.csv](component_gap_summary.csv).

## Post-defence residual (#118)

Flip Candidate `defence_link_challenger`: subclass goals_path; post-link `_CS_SCALE=1.296903` / `_GC_SCALE=1.145226` from [calibrate_defence_k.py](calibrate_defence_k.py) (mins_60 CS ALL; mins_60 GKP+DEF conceded; τ=0.05).

| Row | Champion | defence_link |
|---|---|---|
| 2025-26 `mins_60`/`ALL` `xp_clean_sheet` | bias −0.188 `link-bias` \|mse_share\| 0.196 | bias −0.050 **`variance`** \|mse_share\| 0.194 |
| 2025-26 `mins_60` GKP+DEF `xp_conceded` (combined) | bias +0.099 | bias +0.050 |
| 2025-26 `mins_60`/`GKP` `xp_conceded` | bias +0.096 `link-bias` \|mse_share\| 0.082 | bias +0.043 **`variance`** \|mse_share\| 0.086 |
| 2025-26 `mins_60`/`DEF` `xp_conceded` | bias +0.099 `link-bias` \|mse_share\| 0.050 | bias +0.052 `link-bias` \|mse_share\| 0.054 |
| 2025-26 `all`/`ALL` `xp_goals` (inherited) | bias +0.075 `structural` | bias +0.047 **`variance`** |

**Soft pre-gate defence arm (#115):** CS **PASS** — `|bias|`→τ, `link-bias`→`variance`, `|mse_share|`↓. Conceded **mixed** — combined `|bias|`→τ and GKP clears label; DEF still `link-bias` (|bias| 0.052); `|mse_share|` slightly ↑ vs Champion. Document before admission (#112). Source: [component_gap_summary.csv](component_gap_summary.csv).

## Admission race (#119)

Hand dry-run Historical Promotion Gate (Blended primary, Realized+Process guardrails) with each slate seat as reference: [admission_race_119.json](admission_race_119.json).

| Reference seat | passed | primary | delta | segments | guardrails |
|---|---|---|---|---|---|
| `calibrated_matchup_hybrid` | **PASS** | decision_regret | +1.169 | 3/3 | True |
| `participation_state_hybrid` | **PASS** | decision_regret | +1.169 | 3/3 | True |

**Seat outcome:** beat both → replace worse Blended primary. Primaries tied; replace `calibrated_matchup_hybrid` (slightly worse MAE). Slate now: Champion `hold_chase_challenger`; Candidates `participation_state_hybrid`, `defence_link_challenger`.

**Soft pre-gate flip checklist** ([soft_pre_gate_119.json](soft_pre_gate_119.json)): goals PASS · CS PASS · conceded **FAIL** (`|mse_share|` ↑). **No Champion `--apply`** until conceded soft bar settled (map fog).

## Decision

- **Gap Event Component (step-1 crown):** `xp_goals` — structural on gate `all`/`ALL`; inherited across Comparison Slate.
- **Goals Candidate shipped (#116):** `goals_path_challenger` — soft pre-gate goals arm PASS; not on Comparison Slate (parent only).
- **Flip Candidate shipped (#118) + admitted (#119):** `defence_link_challenger` on Comparison Slate; soft pre-gate CS PASS / conceded FAIL for Champion apply.
- **Eval metrics locked** in [INDEX Eval canon](../INDEX.md) — Blended for promotion; Realized `mse_share` + twins for component gap. Soft pre-gate before `--apply` (#115).

## Risks and unknowns

- τ=0.05 near goals + defence biases — Candidate sits on τ edge; small τ change flips label.
- Conceded soft pre-gate: bias cleared but `|mse_share|` not improved — blocks Champion `--apply` until fog settled.
- Both seats shared identical decision_regret primary on dry-run; MAE tie-break used for worse-seat rule.
- Fill-0 actuals on `pool=all` inflate minutes-related shares.
- Poisson-xGC CS overstatement documented; `link-bias` expected often on CS.
- 2026-27 sanity: short window only — provisional archive.

## Appendix

- Runner: [runner.py](runner.py) · Calibrate: [calibrate_goals_k.py](calibrate_goals_k.py) · [calibrate_defence_k.py](calibrate_defence_k.py)
- Admission: [admission_race_119.json](admission_race_119.json) · Soft pre-gate: [soft_pre_gate_119.json](soft_pre_gate_119.json)
- Glossary: Process Points · Poisson-xGC Twin · Extended Process Points in `CONTEXT.md`

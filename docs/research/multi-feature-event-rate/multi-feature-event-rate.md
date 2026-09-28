# Multi-feature Event Rate (explore-candidate 2026-09-28)

**Updated**: 2026-09-28T13:30:00+07:00  
**Data stamp**: 2025-26 archive GW1–38 seed 2024-25 (dev season); point-in-time features (ADR 0046); recompute 2026-09-28  
**Season**: 2025/26 (dev). 2026-27 GW6+ holdout pending (GW6 unfinished)  
**Status**: Active — Candidate `multi_feature_assist_challenger` dev gate PASS; not on Comparison Slate; not promoted  
**Purpose**: Test user idea: project Event Rates from several signals jointly (xG/xA, threat/creativity, opponent xG conceded, own-team xG, home) instead of one per90 signal × fixture multiplier.  
**Scope**: Goals, assists, goals conceded / clean sheet rates on Champion `face_value_challenger`. Excluded: minutes, bonus, saves, defcon; official FDR as GLM input (see Method).  
**Related**: [Candidate Ledger](../candidate-ledger/candidate-ledger.md) · [face-value-challenger](../face-value-challenger/face-value-challenger.md) · [Eval canon](../INDEX.md) · [ADR 0046](../../adr/0046-point-in-time-backtest-and-statistical-gate.md)  
**Artifact**: [smoke_results.csv](smoke_results.csv) `combined_delta` / `segs` / `boot_p_gt0` (frozen smoke snapshot) · [candidate_gate_summary.csv](candidate_gate_summary.csv) `combined_delta` / `*_regret` / `blend_mae` (regenerable via `runner.py`)

## Sources

- **Primary**: `backtesting/model_evaluation.py` `compare_to_reference` — gate rule (Blended `top_11_regret`, ≥1% effect, block-bootstrap P ≥ 0.95, ≥2/3 segments, guardrails)
- **Primary**: `models/multi_feature_assist_challenger.py` — frozen Candidate
- **Repository data**: `data/archive/2025-26/processed` (target), `data/archive/2024-25/processed` (seed) — cutoff 2025-26 GW38

**Source boundary**: Smoke rows from `.agents/skills/explore-candidate/smoke.py` over scratch prototypes (deleted); Candidate reproduces prototype `a_xa_l10` exactly (`freeze` row). Gate rows regenerable.

## Agent Prompt

```text
Full redo docs/research/multi-feature-event-rate/multi-feature-event-rate.md

1. uv run python docs/research/multi-feature-event-rate/runner.py  (~10 min, 2 procs)
2. Refresh Findings from candidate_gate_summary.csv columns combined_delta, *_regret, blend_mae, realized_mae, process_mae, abs_bias, spearman, boot_p_gt0.
3. smoke_results.csv frozen; do not regenerate.
4. Holdout (once, after 2026-27 GW6+ finished): uv run python -m commands.evaluate_model_promotion --config <scratch config with candidate> --data_dir data/archive/2026-27/processed --seed_season 2025-26 --gw_range 6-<last finished GW>; log date + verdict in Candidate Ledger row.
5. Scratch under .tmp/agent/ only; delete before finish.
```

## Method

**Method type**: Walk-forward backtest, lever ablation (explore-candidate Scoped mode)

**Inputs**: Champion `face_value_challenger`; 18 round-1 prototypes (3 lanes × 6), 6 round-2 stacks; blended eval target.

**Procedure**:
1. Per event, ridge Poisson GLM (log link, IRLS, intercept free, standardized covariates) on log-multiplier over player's own as-of base rate: rate/90 = base/90 × exp(b0 + b·z). b = 0 → base rate.
2. Training rows = current-season appearances (minutes > 0) at GW g ≥ 2; every covariate from rows before g; offset log(minutes/90 × base). Refit each `predict` on history passed to `fit`.
3. Covariates: goals — log xG/90 (slope), log(threat/90+1), log opp xG conceded/match, log team xG/match, home [+ finishing offset, position]. Assists — log xA/90, log(creativity/90+1), same fixture terms. GC — log player on-pitch xGC/90, log opp xG/match, log own xG conceded/match, home. Club rates rebuilt from fixture pairs (`opponent_club_id` → other side), shrunk 4 matches to league mean; player rates recency-decay 0.95, 360-min shrink to position mean (builder-style).
4. Targets per grid: realized count, Official expected (xG/xA/xGC), or 50/50 blend. Ridge λ 10 / 100. Ablations: no fixture terms, no slope, opponent-only.
5. Cold start: < 3 history GWs → Champion unchanged. GKs keep Champion goals/assists.
6. Round 2: stack lane winners (assists + GC / goals); reproduce winner.
7. Freeze winning prototype as `multi_feature_assist_challenger`; freeze check + official dry gate (`commands.evaluate_model_promotion`, scratch config; production config untouched).

**Definitions and assumptions**:
- Delta = Champion regret − Candidate regret; positive = Candidate better.
- Official FDR not a GLM covariate: history rows carry no FDR, model may not read files, archive FDR is residual terminal input (ADR 0046). As-of opponent xG rates = data-driven FDR substitute.
- Leakage audit: smoke `--audit_only` PASS on all prototype files; runtime guard (fit history < target GW, no terminal columns) PASS on every run.

### Metric Definitions & Direction

| Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|---|---|---|---|---|---|
| Blended top-11 regret | `top_11_regret` | Mean GW (best-11 blended − projected-top-11 blended) | Lower $\downarrow$ | < Champion | Gate primary |
| Combined delta | `combined_delta` | Champion regret − Candidate regret | Higher $\uparrow$ | ≥ `min_effect` (1% Champion regret) | Gate primary delta |
| Bootstrap P | `boot_p_gt0` | Block-bootstrap share of GW resamples with mean delta > 0 | Higher $\uparrow$ | ≥ 0.95 | Gate robustness |
| Segment wins | `segs` / `segment_wins` | Seasonal segments (cold/early-mid/late) with regret delta > 0 | Higher $\uparrow$ | ≥ 2/3 | Gate robustness |
| Guardrails | `blend_mae`, `realized_mae`, `process_mae`, `abs_bias`, `spearman`, `xmins_mae` | ADR 0044/0046 | MAE/bias/xMins $\downarrow$; Spearman $\uparrow$ | within Champion tolerance | Gate guardrails |
| Assist bias | `assist_bias_realized` | mean(`xp_assists` − realized assist points) | Near 0 | 0 | Component calibration context; not gate |

**Validation boundary**: One dev season, 38 GWs, 24 variants tried → selection luck possible (1 of 18 round-1 variants passes). Sealed holdout (2026-27 GW6+) not yet run.

## Project interpretation

### Decision rules

- Multi-feature assist rate trained on xA beats Champion's xA × attack_multiplier on ranking; accuracy flat.
- Realized-assist or blended target hurts (FPL assists noisier than xA; realized target trips Realized MAE guardrail).
- Goals: fixture terms carry signal (no-fixture ablation negative), but no goals variant wins > 1/3 segments.
- GC: realized-target GLM near-miss (+0.99, 2/3, P 0.92); own-defence term needed (opp-only negative).
- Stacks raise point delta (best +1.52) but P < 0.95; gains not additive → stay single-lever.

### Practical implications

- Live path (`run_model`, `dashboard`, `export_dashboard`) calls `fit(history)` → Candidate works live, not only in backtest.
- Refit cost ≈ 1–3 s per `predict` (history loop per GW).

## Findings

### Round 1 lanes (`smoke_results.csv` lane `mfer_r1`)

| Lane | Best variant | `combined_delta` | `segs` | `boot_p_gt0` | Pass |
|---|---|---:|---:|---:|---|
| Goals | `g_blend_finpos_l10` | +0.547 | 1 | 0.698 | no |
| Assists | `a_xa_l10` | **+0.901** | 2 | **0.976** | **yes** |
| GC / CS | `c_gc_l10` | +0.986 | 2 | 0.923 | no |

16/18 variants positive delta. Negative: `g_blend_nofix_l10` −0.263, `c_blend_opponly_l10` −0.313.

### Round 2 stacks (`smoke_results.csv` lane `mfer_r2`)

`s_a_repro` reproduces +0.9014 exactly. Stacks: `s_acgfp` +1.524 (2/3, P 0.891), `s_ag` +1.213 (1/3), `s_ac100` +0.955 (P 0.879), `s_ac` +0.858 (P 0.888), `s_acg` +0.412 (1/3). None pass.

### Candidate gate (`candidate_gate_summary.csv`)

`multi_feature_assist_challenger` vs `face_value_challenger`: PASS, `combined_delta` +0.901 (min 0.720), 2/3 segments, boot P 0.976, guardrails pass. Regret 71.08 vs 71.98; early-mid 74.62 vs 76.52; late 67.24 vs 67.54; cold start tie (GLM inactive < 3 GWs). Blend MAE 0.8993 vs 0.8987; Realized MAE 0.9701 vs 0.9693 (within tolerance); \|bias\| 0.0006 vs 0.0032; Spearman 0.6931 vs 0.6929. Official dry gate (`commands.evaluate_model_promotion`) identical.

## Decision

**Verdict**: `multi_feature_assist_challenger` = dev-season gate PASS; frozen. Promotion blocked on sealed holdout + user decision.

**Recommended action**:
- User decision: add to `config/model_selection.json` `candidates` (max 2 → replaces one current entry).
- After 2026-27 GW6+ finished: one holdout gate run; log in Candidate Ledger.
- `--apply` only on user's words; Champion change → ADR.

**Trigger / kill switch**:
- Holdout FAIL (any gate rule) → mark ledger row Dead (revisit evidence + 1 year).

## Risks and unknowns

- Forking paths: 24 variants on one season; P 0.976 not multiplicity-adjusted.
- Win concentrated in early-mid segment; late edge small (+0.31).
- Accuracy not improved; win = ranking of assist-heavy players.
- Training uses current-season history only (no seed) → inactive GW1–3; early behavior = Champion.

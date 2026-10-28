# Multi-feature Event Rate (explore-candidate 2026-09-28)

**Updated**: 2026-09-28T13:45:00+07:00  
**Data stamp**: 2025-26 archive GW1–38 seed 2024-25 (dev); 2024-25 archive GW1–38 no seed (confirmation, ADR 0047); point-in-time features (ADR 0046); recompute 2026-09-28  
**Season**: 2025/26 (dev) + 2024/25 (confirmation)  
**Status**: Closed — `multi_feature_assist_challenger` dev PASS, 2024-25 boot P 0.896 (FAIL at 0.95, PASS at 0.60 bar) → promoted to Champion (ADR 0048; also passes 0.60 bar both seasons, ADR 0049); goals/GC/stack levers Dead  
**Purpose**: Test user idea: project Event Rates from several signals jointly (xG/xA, threat/creativity, opponent xG conceded, own-team xG, home) instead of one per90 signal × fixture multiplier.  
**Scope**: Goals, assists, goals conceded / clean sheet rates on Champion `face_value_challenger`. Excluded: minutes, bonus, saves, defcon; official FDR as GLM input (see Method).  
**Related**: [Candidate Ledger](../candidate-ledger/candidate-ledger.md) · [face-value-challenger](../face-value-challenger/face-value-challenger.md) · [Eval canon](../INDEX.md) · [ADR 0046](../../adr/0046-point-in-time-backtest-and-statistical-gate.md) · [ADR 0047](../../adr/0047-two-season-promotion-gate.md) · [ADR 0048](../../adr/0048-champion-multi-feature-assist-challenger.md)  
**Artifact**: [smoke_results.csv](smoke_results.csv) `combined_delta` / `segs` / `boot_p_gt0` (frozen smoke snapshot) · [candidate_gate_summary.csv](candidate_gate_summary.csv) `combined_delta` / `*_regret` / `blend_mae` (regenerable via `runner.py`) · [confirmation_gate_summary.csv](confirmation_gate_summary.csv) `gate_passed` / `combined_delta` / `boot_p_gt0` (official `commands.evaluate_model_promotion` verdicts, both seasons)

## Sources

- **Primary**: `backtesting/model_evaluation.py` `compare_to_reference` — gate rule (Blended `top_11_regret`, ≥1% effect, block-bootstrap P ≥ 0.95 at search time; 0.60 both seasons after ADR 0049, ≥2/3 segments, guardrails)
- **Primary**: `models/multi_feature_assist_challenger.py` — frozen Candidate
- **Repository data**: `data/archive/2025-26/processed` (target), `data/archive/2024-25/processed` (seed) — cutoff 2025-26 GW38

**Source boundary**: Smoke rows from `.agents/skills/explore-candidate/smoke.py` over scratch prototypes (deleted); Candidate reproduces prototype `a_xa_l10` exactly (`freeze` row). Gate rows regenerable.

## Agent Prompt

```text
Full redo docs/research/multi-feature-event-rate/multi-feature-event-rate.md

1. uv run python docs/research/multi-feature-event-rate/runner.py  (~10 min, 2 procs)
2. Refresh Findings from candidate_gate_summary.csv columns combined_delta, *_regret, blend_mae, realized_mae, process_mae, abs_bias, spearman, boot_p_gt0.
3. smoke_results.csv frozen; do not regenerate.
4. confirmation_gate_summary.csv = official gate verdicts; 2024-25 run is one-shot (ADR 0047); rows at bootstrap_min_p 0.95 and 0.60 (ADR 0048 re-score, same run); do not re-run.
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
| Bootstrap P | `boot_p_gt0` | Block-bootstrap share of GW resamples with mean delta > 0 | Higher $\uparrow$ | ≥ `bootstrap_min_p` (0.95 dev; 0.60 confirmation at search time, ADR 0048; 0.60 both, ADR 0049) | Gate robustness |
| Segment wins | `segs` / `segment_wins` | Seasonal segments (cold/early-mid/late) with regret delta > 0 | Higher $\uparrow$ | ≥ 2/3 | Gate robustness |
| Guardrails | `blend_mae`, `realized_mae`, `process_mae`, `abs_bias`, `spearman`, `xmins_mae` | ADR 0044/0046 | MAE/bias/xMins $\downarrow$; Spearman $\uparrow$ | within Champion tolerance | Gate guardrails |
| Assist bias | `assist_bias_realized` | mean(`xp_assists` − realized assist points) | Near 0 | 0 | Component calibration context; not gate |

**Validation boundary**: One dev season, 38 GWs, 24 variants tried → selection luck possible (1 of 18 round-1 variants passes). 2024-25 confirmation run once (FAIL 0.95 / PASS 0.60); 2026-27 GW6+ untouched.

## Project interpretation

#### Confirmation season (`confirmation_gate_summary.csv`, ADR 0047)

2024-25 GW1–38, no seed, `commands.evaluate_model_promotion` (Assistant Manager elements excluded): `combined_delta` +0.796 (min 0.630), 3/3 segments, `boot_p_gt0` 0.896 → FAIL at pre-registered 0.95; **PASS** at user-lowered 0.60 bar (ADR 0048, same run re-scored). Direction consistent with dev season.

## Decision

**Verdict**: Promoted to Champion 2026-09-28 (ADR 0048, provisional). User lowered 2024-25 bootstrap bar to 0.60 after seeing verdict; `face_value_challenger` → Candidate.

**Recommended action**:
- Weekly projections use `multi_feature_assist_challenger` (dashboard reads `config/model_selection.json`).
- No retune of assist GLM grid without new evidence.

**Trigger / kill switch**:
- 2026-27 GW6+ post-promotion check (ADR 0047) FAIL → revert to `face_value_challenger` on user's words; log in Ledger.

## Risks and unknowns

- Forking paths: 24 variants on one season; P 0.976 not multiplicity-adjusted.
- Confirmation bar lowered post-hoc (after 2024-25 verdict seen); P 0.896 ≈ 1-in-10 chance 2024-25 gain = noise.
- Win concentrated in early-mid segment; late edge small (+0.31).
- Accuracy not improved; win = ranking of assist-heavy players.
- Official FDR never compared head-to-head vs as-of opponent xG substitute (unavailable in `fit` history).
- Training uses current-season history only (no seed) → inactive GW1–3; early behavior = Champion.

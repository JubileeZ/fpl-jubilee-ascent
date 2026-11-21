# Sparse Champion Confirmation & Statistical Early-Harm Certification

**Updated**: 2026-11-20T17:13:41+00:00  
**Data stamp**: Synthetic 38-GW paths (`N=20,000`/scenario; `2026-27` untouched) — 2026-11-20  
**Season**: Synthetic Multi-Slate (`M=1`, `M=2`, 38 GWs)  
**Status**: Active — Certified  
**Purpose**: Calibrate and certify ADR 0070 sparse (`GW15`/`GW30`/`GW38`) confirmation thresholds, GW1–4 net-points material-loss floor, and statistical Early-Harm mode across shared-Champion correlated paths without accessing `2026-27` outcomes.  
**Scope**: Preregistered synthetic certification (`seed=20101` tuning, `seed=20102` primary held-out, `seed=20103` predeclared advisory fallback); excludes live `2026-27` validation outcomes and MILP replay execution.  
**Related**: [ADR 0070](../../adr/0070-weekly-planner-selection-and-champion-adoption.md) · [Implementation Spec](../../product/champion-adoption-implementation.md) · Issue [#201](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/201)  
**Artifact**: [certification_summary.csv](certification_summary.csv) · [certification_result.json](certification_result.json) · [preregistration_manifest.json](preregistration_manifest.json) · [parity_check.json](parity_check.json)

## Sources

- **Repository code**: `backtesting/sparse_certification.py`, `backtesting/evidence_statistics.py`, `backtesting/promotion_evidence.py`, `backtesting/evaluation_protocol.py`
- **Specifications**: `docs/adr/0070-weekly-planner-selection-and-champion-adoption.md`, `docs/product/champion-adoption-implementation.md`, issues `#195`, `#196`, `#201`
- **Scale reference**: `docs/research/backtesting-promotion-foundation/smoke_gate_calibration.csv` (`4.0` pts/GW paired differential SD) & `docs/adr/0069-annual-rolling-validation-and-dual-tier-promotion.md` (`18.56` pts/GW Champion dispersion)

**Source boundary**: Simulation-only certification on independent non-live synthetic seeds (`20101`, `20102`, `20103`). Zero `2026-27` outcomes inspected or used. Live Champion adoption additionally requires empirical admission, frozen slate registration, and explicit human approval.

## Agent Prompt

```text
Full redo docs/research/sparse-confirmation-certification/sparse-confirmation-certification.md

1. Re-run: uv run python -m commands.certify_sparse_confirmation
2. Inspect parity_check.json (max_abs_numeric_diff <= 1e-10, binary_agreement_rate == 1.0).
3. Read certification_summary.csv columns: false_null_ever_pass_upper95, correct_confirmation_by_gw38_lower95, terminal_false_exclusion_upper95, statistical_false_exclusion_flag_upper95.
4. Read certification_result.json fields: certified, certified_mode, certification_digest, statistical_protocol_hash.
5. Never use 2026-27 outcomes or alter preregistered seeds (20101, 20102, 20103).
```

## Method

**Method type**: Preregistered Monte Carlo calibration and held-out certification with vectorized-vs-scalar numerical parity verification.

**Inputs**:
- `backtesting/sparse_certification.py` (`build_preregistration_manifest`, `verify_vectorized_vs_scalar_parity`, `tune_sparse_protocol`, `certify_sparse_confirmation`)
- Tuning seed `20101`, held-out primary seed `20102`, predeclared advisory fallback seed `20103`

**Procedure**:
1. Pin evaluator file hashes, simulator config, scenario grid, seeds, acceptance bounds, and retry budget (`max_retries=0` primary, `1` predeclared advisory fallback) in `preregistration_manifest.json`.
2. Verify vectorized NumPy Kendall-PW + Bartlett HAC + Early-Harm + GW1–4 evaluator parity against scalar `run_kendall_pw_hac_test` & `evaluate_early_harm_fallback` across `525` prefixes (`56` edge cases).
3. Calibrate `M=1`/`M=2` per-look superiority alphas (`GW15`/`GW30`/`GW38`) and `gw1_4_material_loss_limit` (FPL net points on `sigma_delta=4.0` pts/GW scale) strictly on `seed=20101`.
4. Evaluate all 24 scenarios on held-out `seed=20102` (`statistical_early_harm_mode="enforced"`, `N=20,000`).
5. Execute predeclared `statistical_early_harm_mode="advisory"` fallback on untouched `seed=20103` only if statistical Early-Harm fails its `<= 5%` false terminal exclusion gate while false full pass `<= 5%` and GW38 power `>= 1/3` both hold.

### Metric Definitions & Direction

| Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|---|---|---|---|---|---|
| **False Full Pass Upper 95%** | `false_null_ever_pass_upper95` | One-sided 95% Clopper-Pearson upper bound on `k/N` where any true-null finalist clears full pass across registered looks | Lower $\downarrow$ | `<= 0.05` | Strong family-wise false-promotion error control across `M <= 2` and `(15,30,38)` |
| **Primary GW38 Confirmation Lower 95%** | `correct_confirmation_by_gw38_lower95` | One-sided 95% Clopper-Pearson lower bound on cumulative `+0.40` SD confirmation by GW38 in primary mixed-null `M=2` scenario | Higher $\uparrow$ | `>= 0.3333` (`1/3`) | Minimum required detection power for genuine `+0.40` SD improvement |
| **Terminal False Exclusion Upper 95%** | `terminal_false_exclusion_upper95` | One-sided 95% Clopper-Pearson upper bound on slates where >=1 non-harmful finalist is terminally excluded | Lower $\downarrow$ | `<= 0.05` | Protects non-harmful finalists from irreversible mid-season exclusion |
| **Statistical Harm Flag Upper 95%** | `statistical_false_exclusion_flag_upper95` | One-sided 95% Clopper-Pearson upper bound on slates where >=1 non-harmful finalist triggers cumulative or completed-segment statistical Early-Harm (`p_harm <= 0.025`) | Lower $\downarrow$ | `<= 0.05` (enforced gate) / Diagnostic (advisory) | Measures statistical Early-Harm false-flag rate driving enforced vs advisory separation |
| **Harmful Detection Rate** | `harmful_any_detected_rate` | Share of harmful scenarios flagged by statistical Early-Harm or excluded by GW1–4 floor | Higher $\uparrow$ | Maximized | Diagnostics on `-0.40`/`-0.60`/`-0.80` SD & severe GW1–4 collapse |

**Validation boundary**: Synthetic AR(1) + Gaussian/Student-$t(5)$ + scheduled GW15/19/30/34 shock model with shared Champion noise (`rho_champ=0.50`). Real FPL replay transitions may exhibit non-stationary transfer-state coupling beyond AR(1) + shocks.

## Project interpretation

### Calibrated Parameters (from `seed=20101`)

- **Calibrated `gw1_4_material_loss_limit`**: `25.0` net FPL points (on `4.0` pts/GW scale)
- **`M=1` calibrated superiority alphas** (`scale=0.6921`): GW15=`0.00003461`, GW30=`0.00173025`, GW38=`0.02733795`
- **`M=2` calibrated superiority alphas** (`scale=0.4830`): GW15=`0.00000604`, GW30=`0.00060375`, GW38=`0.00953925`

## Findings

### Parity Check (`parity_check.json`)

- Prefixes checked: `525` (`56` edge cases) — `max_abs_numeric_diff=1.228e-11`, `binary_agreement_rate=1.0000`, `passed=True`.

### Primary Enforced Run (`seed=20102`)

- Worst null-containing false full pass upper 95%: `0.045844` (`ok=True`)
- Primary `+0.40` SD GW38 confirmation lower 95%: `0.369557` (`ok=True`)
- Worst non-harmful statistical Early-Harm false exclusion upper 95%: `0.231271` (`ok=False`)

### Predeclared Advisory Fallback Run (`seed=20103`)

- Triggered because enforced statistical Early-Harm exceeded `0.05` false exclusion (`0.231271`) while false full pass and GW38 power held.
- Worst null-containing false full pass upper 95%: `0.044100` (`ok=True`)
- Primary `+0.40` SD GW38 confirmation lower 95%: `0.366517` (`ok=True`)
- Worst non-harmful terminal false exclusion (GW1–4 floor only) upper 95%: `0.021446` (`ok=True`)

### Scenario Results (`fallback_advisory` — `certification_summary.csv`)

| Scenario | Slate | Regime | Guards GW | False Pass (k/N, upper95) | GW38 Power (k/N, lower95) | Term Excl (k/N, upper95) | Stat Harm Flag (k/N, upper95) | Harm Det (k/N) |
|---|---:|---|---:|---|---|---|---|---|
| `m1_null_mild_gw15` | 1 | mild | 15 | 823/20000 (0.043535) | n/a | 42/20000 (0.002715) | 2570/20000 (0.132457) | n/a |
| `m1_null_mild_gw30` | 1 | mild | 30 | 780/20000 (0.041327) | n/a | 34/20000 (0.002263) | 2497/20000 (0.128760) | n/a |
| `m1_null_persistent_gw15` | 1 | persistent | 15 | 834/20000 (0.044100) | n/a | 192/20000 (0.010814) | 2633/20000 (0.135647) | n/a |
| `m1_null_persistent_gw30` | 1 | persistent | 30 | 740/20000 (0.039271) | n/a | 176/20000 (0.009966) | 2665/20000 (0.137267) | n/a |
| `m2_null_mild_gw15` | 2 | mild | 15 | 704/20000 (0.037419) | n/a | 91/20000 (0.005414) | 4394/20000 (0.224571) | n/a |
| `m2_null_mild_gw30` | 2 | mild | 30 | 715/20000 (0.037985) | n/a | 83/20000 (0.004979) | 4282/20000 (0.218927) | n/a |
| `m2_null_persistent_gw15` | 2 | persistent | 15 | 797/20000 (0.042200) | n/a | 381/20000 (0.020718) | 4606/20000 (0.235251) | n/a |
| `m2_null_persistent_gw30` | 2 | persistent | 30 | 712/20000 (0.037831) | n/a | 395/20000 (0.021446) | 4683/20000 (0.239129) | n/a |
| `m2_mixed_r1_imp_r2_null_mild_gw15` | 2 | mild | 15 | 353/20000 (0.019260) | 7443/20000 (0.366517) | 54/20000 (0.003386) | 2600/20000 (0.133976) | n/a |
| `m2_mixed_r1_null_r2_imp_mild_gw15` | 2 | mild | 15 | 381/20000 (0.020718) | 7464/20000 (0.367564) | 55/20000 (0.003441) | 2631/20000 (0.135546) | n/a |
| `m2_mixed_r1_imp_r2_null_persistent_gw15` | 2 | persistent | 15 | 464/20000 (0.025028) | 3527/20000 (0.171927) | 243/20000 (0.013503) | 2942/20000 (0.151283) | n/a |
| `m2_mixed_r1_null_r2_imp_persistent_gw15` | 2 | persistent | 15 | 428/20000 (0.023161) | 3506/20000 (0.170888) | 249/20000 (0.013819) | 2951/20000 (0.151738) | n/a |
| `m2_mixed_r1_imp_r2_null_mild_gw30` | 2 | mild | 30 | 389/20000 (0.021134) | 7491/20000 (0.368909) | 50/20000 (0.003163) | 2497/20000 (0.128760) | n/a |
| `m2_mixed_r1_null_r2_imp_mild_gw30` | 2 | mild | 30 | 404/20000 (0.021914) | 7389/20000 (0.363826) | 47/20000 (0.002996) | 2562/20000 (0.132052) | n/a |
| `m1_power_pos020_mild_gw15` | 1 | mild | 15 | n/a | 4082/20000 (0.199419) | 4/20000 (0.000458) | 579/20000 (0.030977) | n/a |
| `m2_power_pos020_mixed_mild_gw15` | 2 | mild | 15 | 354/20000 (0.019312) | 2342/20000 (0.113377) | 54/20000 (0.003386) | 2771/20000 (0.142632) | n/a |
| `m1_power_pos060_mild_gw15` | 1 | mild | 15 | n/a | 16496/20000 (0.820319) | 0/20000 (0.000150) | 11/20000 (0.000910) | n/a |
| `m2_power_pos060_mixed_mild_gw15` | 2 | mild | 15 | 381/20000 (0.020718) | 13771/20000 (0.683119) | 41/20000 (0.002659) | 2482/20000 (0.128000) | n/a |
| `m1_harm_neg040_mild_gw15` | 1 | mild | 15 | n/a | n/a | n/a | n/a | 13402/20000 (0.670100) |
| `m1_harm_neg060_mild_gw15` | 1 | mild | 15 | n/a | n/a | n/a | n/a | 17838/20000 (0.891900) |
| `m1_harm_neg080_mild_gw15` | 1 | mild | 15 | n/a | n/a | n/a | n/a | 19576/20000 (0.978800) |
| `m1_harm_neg060_persistent_gw15` | 1 | persistent | 15 | n/a | n/a | n/a | n/a | 13100/20000 (0.655000) |
| `m1_harm_severe_gw1_4_mild_gw15` | 1 | mild | 15 | n/a | n/a | n/a | n/a | 19299/20000 (0.964950) |
| `m2_harm_r1_neg060_r2_null_mild_gw15` | 2 | mild | 15 | 364/20000 (0.019833) | n/a | 37/20000 (0.002433) | 2466/20000 (0.127190) | 17914/20000 (0.895700) |

## Decision

**Verdict**: `certified=True`, `certified_mode=advisory`, `certification_seed=20103`, `live_adoption_blocked=False` (`certification_digest=9e7234b17fc73543eb8330817f3d5ec519735de4f3264485f2592c7f46d53c56`).

**Recommended action**:
- Freeze calibrated `v2.0` protocol (`statistical_protocol_hash=036164c091033ed85ead3a112811c7659472cb3808be2393fd7d4c3943bdbe53`) with `certification_digest` bound prior to any prospective slate access.
- Retain `GW15`/`GW30`/`GW38` sparse confirmation cadence (weekly expansion remains gated on paired speed and power criteria).

## Risks and unknowns

- Realized 6-GW rolling MILP transfer trajectories can exhibit non-AR(1) chip-week or price-lock jumps not captured by Gaussian/Student-$t(5)$ innovations.
- Synthetic certification does not authorize live Champion adoption on its own; empirical admission, frozen slate registration, pilot acceptance, and explicit human approval remain mandatory.

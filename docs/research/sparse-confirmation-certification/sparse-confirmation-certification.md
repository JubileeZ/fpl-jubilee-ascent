# Sparse Champion Confirmation & Statistical Early-Harm Certification

**Updated**: 2026-11-22T15:52:40+00:00  
**Data stamp**: Synthetic 38-GW paths (`N=20,000`/scenario; `2026-27` untouched) — 2026-11-22  
**Season**: Synthetic Multi-Slate (`M=1`, `M=2`, 38 GWs)  
**Status**: Active — Certified  
**Purpose**: Calibrate and certify ADR 0070 sparse (`GW15`/`GW30`/`GW38`) confirmation thresholds, scale-free advisory GW1–4 diagnostics, and decoupled fixed-FPL-pts/yr empirical power diagnostics across shared-Champion correlated paths without accessing `2026-27` outcomes.  
**Scope**: Preregistered synthetic certification (`seed=21101` tuning, `seed=21102` primary held-out, `seed=21103` predeclared advisory fallback); excludes live `2026-27` validation outcomes and MILP replay execution.  
**Related**: [ADR 0070](../../adr/0070-weekly-planner-selection-and-champion-adoption.md) · [ADR 0071](../../adr/0071-certified-solver-budget-and-milp-qualification-calibration.md) · [Implementation Spec](../../product/champion-adoption-implementation.md) · Issues [#201](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/201) & [#211](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/211)  
**Artifact**: [certification_summary.csv](certification_summary.csv) · [empirical_power_diagnostics.csv](empirical_power_diagnostics.csv) · [certification_result.json](certification_result.json) · [preregistration_manifest.json](preregistration_manifest.json) · [parity_check.json](parity_check.json)

## Sources

- **Repository code**: `backtesting/sparse_certification.py`, `backtesting/evidence_statistics.py`, `backtesting/promotion_evidence.py`, `backtesting/evaluation_protocol.py`
- **Specifications**: `docs/adr/0070-weekly-planner-selection-and-champion-adoption.md` (amended 2026-11-22), `docs/adr/0071-certified-solver-budget-and-milp-qualification-calibration.md`, `docs/product/champion-adoption-implementation.md`, issues `#195`, `#196`, `#201`, `#211`
- **Scale reference**: Empirical non-live `EXT-01_1`..`EXT-05_1` `S-1`/`S-2` rolling-MILP weekly deltas (`8.5` pts/GW pooled non-zero active SD, `11.0` pts/GW upper stress, locked-GW1/GW2 empirical ramp) and `ADR 0071` `cold_start` tolerance (`-8.9` pts/GW × `4` GWs = `35.6` pts)

**Source boundary**: Simulation-only certification on independent non-live synthetic seeds (`21101`, `21102`, `21103`). Zero `2026-27` outcomes inspected or used. Live Champion adoption additionally requires empirical admission, frozen slate registration, and explicit human approval.

## Agent Prompt

```text
Full redo docs/research/sparse-confirmation-certification/sparse-confirmation-certification.md

1. Re-run: uv run python -m commands.certify_sparse_confirmation
2. Inspect parity_check.json (max_abs_numeric_diff <= 1e-10, binary_agreement_rate == 1.0).
3. Read certification_summary.csv columns: false_null_ever_pass_upper95, correct_confirmation_by_gw38_lower95, terminal_false_exclusion_upper95, statistical_false_exclusion_flag_upper95.
4. Read empirical_power_diagnostics.csv columns: gw15_power, gw30_power, single_season_gw38_power, two_season_76gw_power.
5. Read certification_result.json fields: certified, certified_mode, certification_digest, statistical_protocol_hash, empirical_power_diagnostics.
6. Never use 2026-27 outcomes or alter preregistered seeds (21101, 21102, 21103) without manifest bump.
```

## Method

**Method type**: Preregistered Monte Carlo calibration and held-out certification with vectorized-vs-scalar numerical parity verification and decoupled fixed-pts/yr power diagnostics.

**Inputs**:
- `backtesting/sparse_certification.py` (`build_preregistration_manifest`, `verify_vectorized_vs_scalar_parity`, `tune_sparse_protocol`, `certify_sparse_confirmation`, `compute_empirical_power_diagnostics`)
- Tuning seed `21101`, held-out primary seed `21102`, predeclared advisory fallback seed `21103`

**Procedure**:
1. Pin evaluator file hashes, simulator config, scenario grid, seeds, acceptance bounds, and retry budget (`max_retries=0` primary, `1` predeclared advisory fallback) in `preregistration_manifest.json`.
2. Verify vectorized NumPy Kendall-PW + Bartlett HAC + Early-Harm + GW1–4 evaluator parity against scalar `run_kendall_pw_hac_test` & `evaluate_early_harm_fallback` across `525` prefixes (`56` edge cases).
3. Calibrate scale-free `M=1`/`M=2` per-look superiority alphas (`GW15`/`GW30`/`GW38`) strictly on `seed=21101` without borrowing exclusion from `gw1_4_material_loss_limit`, and align advisory `gw1_4_material_loss_limit` (`35.6` pts) with `ADR 0071` `cold_start` (`-8.9` pts/GW × 4).
4. Evaluate all 30 scenarios on held-out `seed=21102` (`statistical_early_harm_mode="enforced"`, `N=20,000`).
5. Execute predeclared `statistical_early_harm_mode="advisory"` fallback on untouched `seed=21103` only if statistical Early-Harm fails its `<= 5%` false terminal exclusion gate while false full pass `<= 5%` and standardized `+0.40 SD` SNR efficiency `>= 1/3` both hold; record fixed-pts/yr (`+40/+60/+80`) empirical power diagnostics across `sigma_gw in {8.5, 11.0}`.

### Metric Definitions & Direction

| Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|---|---|---|---|---|---|
| **False Full Pass Upper 95%** | `false_null_ever_pass_upper95` | One-sided 95% Clopper-Pearson upper bound on `k/N` where any true-null finalist clears full pass across registered looks | Lower $\downarrow$ | `<= 0.05` | Strong family-wise false-promotion error control across `M <= 2` and `(15,30,38)` |
| **Standardized +0.40 SD GW38 Lower 95%** | `correct_confirmation_by_gw38_lower95` | One-sided 95% Clopper-Pearson lower bound on cumulative `+0.40 SD` confirmation by GW38 in `m2_mixed_r1_imp_r2_null_mild_gw15` | Higher $\uparrow$ | `>= 0.3333` (`1/3`) | Scale-invariant standardized SNR efficiency gate (reported separately from fixed-pts/yr empirical power) |
| **Terminal False Exclusion Upper 95%** | `terminal_false_exclusion_upper95` | One-sided 95% Clopper-Pearson upper bound on slates where >=1 non-harmful finalist is terminally excluded | Lower $\downarrow$ | `<= 0.05` | Protects non-harmful finalists (`advisory` mode restricts terminal exclusion to mandatory projection guard `FAIL`) |
| **Statistical Harm Flag Upper 95%** | `statistical_false_exclusion_flag_upper95` | One-sided 95% Clopper-Pearson upper bound on slates where >=1 non-harmful finalist triggers cumulative or completed-segment statistical Early-Harm (`p_harm <= 0.025`) | Lower $\downarrow$ | `<= 0.05` (enforced gate) / Diagnostic (advisory) | Measures statistical Early-Harm false-flag rate driving enforced vs advisory separation |
| **Harmful Detection Rate** | `harmful_any_detected_rate` | Share of harmful scenarios flagged by statistical Early-Harm or GW1–4 advisory/enforced floor | Higher $\uparrow$ | Maximized | Diagnostics on `-0.40`/`-0.60`/`-0.80` SD, `-40` pt GW1–4 collapse, and empirical `-40`/`-80` pts/yr harm |
| **GW15 Power (`empirical_power_diagnostics.csv`)** | `gw15_power` | Point estimate `k/N` clearing calibrated superiority threshold `a15` at `GW15` (`phi=0.10`, locked GW1/GW2) | Higher $\uparrow$ | Diagnostic | Single-arm early confirmation probability at `GW15` |
| **GW30 Power (`empirical_power_diagnostics.csv`)** | `gw30_power` | Point estimate `k/N` clearing calibrated superiority threshold `a30` at `GW30` (`phi=0.10`, locked GW1/GW2) | Higher $\uparrow$ | Diagnostic | Single-look `GW30` confirmation probability under empirical variance |
| **1-Season GW38 Power (`empirical_power_diagnostics.csv`)** | `single_season_gw38_power` | Cumulative sequential confirmation probability `k/N` clearing `a15` at `GW15`, `a30` at `GW30`, or `a38` at `GW38` (`phi=0.10`, locked GW1/GW2) | Higher $\uparrow$ | Diagnostic | 38-GW empirical power for fixed `+40/+60/+80` pts/yr gains across `sigma_gw in {8.5, 11.0}` |
| **2-Season 76-GW Carryover Power (`empirical_power_diagnostics.csv`)** | `two_season_76gw_power` | Confirmation probability `k/N` over concatenated 2-season `76`-GW carryover evaluated at `a38` (`phi=0.10`, locked GW1/GW2 per season) | Higher $\uparrow$ | Diagnostic | Illustrates multi-season confirmation power motivating GW38 summer carryover policy |

**Validation boundary**: Synthetic AR(1) + Gaussian/Student-$t(5)$ + scheduled GW15/19/30/34 shock model with shared Champion noise (`rho_champ=0.50`). Real FPL replay transitions exhibit locked-GW1/GW2 zero deltas and candidate-dependent weekly SD (`0.0–12.2` pts/GW).

## Project interpretation

### Calibrated Parameters (from `seed=21101`)

- **Advisory `gw1_4_material_loss_limit`**: `35.6` net FPL points (advisory-only in `advisory` mode; aligned to ADR 0071 `cold_start` `-8.9` pts/GW × 4; terminal exclusion restricted to mandatory projection guard `FAIL`)
- **Nominal empirical `fpl_delta_sd_per_gw`**: `8.5` pts/GW (superiority alphas are 100% scale-free; power evaluated separately in fixed pts/yr below)
- **`M=1` calibrated superiority alphas** (`scale=0.6738`): GW15=`0.00003369`, GW30=`0.00168450`, GW38=`0.02661510`
- **`M=2` calibrated superiority alphas** (`scale=0.4802`): GW15=`0.00000600`, GW30=`0.00060025`, GW38=`0.00948395`

## Findings

### Parity Check (`parity_check.json`)

- Prefixes checked: `525` (`56` edge cases) — `max_abs_numeric_diff=2.728e-11`, `binary_agreement_rate=1.0000`, `passed=True`.

### Primary Enforced Run (`seed=21102`)

- Worst null-containing false full pass upper 95%: `0.043997` (`ok=True`)
- Standardized `+0.40` SD GW38 confirmation lower 95%: `0.367763` (`ok=True`)
- Worst non-harmful statistical Early-Harm false exclusion upper 95%: `0.225226` (`ok=False`)

### Predeclared Advisory Fallback Run (`seed=21103`)

- Triggered because enforced statistical Early-Harm exceeded `0.05` false exclusion (`0.225226`) while false full pass and standardized `+0.40 SD` SNR efficiency held.
- Worst null-containing false full pass upper 95%: `0.042662` (`ok=True`)
- Standardized `+0.40` SD GW38 confirmation lower 95%: `0.369009` (`ok=True`)
- Worst non-harmful terminal false exclusion upper 95%: `0.000150` (`ok=True`, `advisory` mode restricts terminal exclusion to guard `FAIL`)

### Decoupled Fixed-FPL-Points Empirical Power Diagnostics (Locked GW1/2, `phi=0.10` — `empirical_power_diagnostics.csv`)

| Slate `M` | `sigma_gw` (pts/GW) | True Gain (`pts/yr`) | GW15 Power | GW30 Power | 1-Season GW38 Power | 2-Season `76`-GW Carryover Power |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 8.5 | +40 | 0.0000 | 0.0209 | 0.1303 | 0.1919 |
| 1 | 8.5 | +60 | 0.0000 | 0.0434 | 0.2165 | 0.3488 |
| 1 | 8.5 | +80 | 0.0001 | 0.0710 | 0.3277 | 0.5447 |
| 1 | 11.0 | +40 | 0.0000 | 0.0158 | 0.1015 | 0.1412 |
| 1 | 11.0 | +60 | 0.0001 | 0.0273 | 0.1578 | 0.2422 |
| 1 | 11.0 | +80 | 0.0001 | 0.0427 | 0.2278 | 0.3678 |
| 2 | 8.5 | +40 | 0.0000 | 0.0109 | 0.0708 | 0.1067 |
| 2 | 8.5 | +60 | 0.0000 | 0.0255 | 0.1263 | 0.2233 |
| 2 | 8.5 | +80 | 0.0000 | 0.0427 | 0.2037 | 0.3856 |
| 2 | 11.0 | +40 | 0.0000 | 0.0086 | 0.0535 | 0.0716 |
| 2 | 11.0 | +60 | 0.0000 | 0.0156 | 0.0867 | 0.1328 |
| 2 | 11.0 | +80 | 0.0000 | 0.0251 | 0.1333 | 0.2343 |

### Scenario Results (`fallback_advisory` — `certification_summary.csv`)

| Scenario | Slate | Regime | Guards GW | False Pass (k/N, upper95) | GW38 Power (k/N, lower95) | Term Excl (k/N, upper95) | Stat Harm Flag (k/N, upper95) | Harm Det (k/N) |
|---|---:|---|---:|---|---|---|---|---|
| `m1_null_mild_gw15` | 1 | mild | 15 | 771/20000 (0.040864) | n/a | 0/20000 (0.000150) | 2575/20000 (0.132710) | n/a |
| `m1_null_mild_gw30` | 1 | mild | 30 | 792/20000 (0.041943) | n/a | 0/20000 (0.000150) | 2497/20000 (0.128760) | n/a |
| `m1_null_persistent_gw15` | 1 | persistent | 15 | 765/20000 (0.040556) | n/a | 0/20000 (0.000150) | 2690/20000 (0.138533) | n/a |
| `m1_null_persistent_gw30` | 1 | persistent | 30 | 762/20000 (0.040402) | n/a | 0/20000 (0.000150) | 2583/20000 (0.133115) | n/a |
| `m2_null_mild_gw15` | 2 | mild | 15 | 693/20000 (0.036853) | n/a | 0/20000 (0.000150) | 4120/20000 (0.210760) | n/a |
| `m2_null_mild_gw30` | 2 | mild | 30 | 719/20000 (0.038191) | n/a | 0/20000 (0.000150) | 4330/20000 (0.221346) | n/a |
| `m2_null_persistent_gw15` | 2 | persistent | 15 | 772/20000 (0.040916) | n/a | 0/20000 (0.000150) | 4688/20000 (0.239380) | n/a |
| `m2_null_persistent_gw30` | 2 | persistent | 30 | 806/20000 (0.042662) | n/a | 0/20000 (0.000150) | 4567/20000 (0.233286) | n/a |
| `m2_mixed_r1_imp_r2_null_mild_gw15` | 2 | mild | 15 | 384/20000 (0.020874) | 7493/20000 (0.369009) | 0/20000 (0.000150) | 2534/20000 (0.130634) | n/a |
| `m2_mixed_r1_null_r2_imp_mild_gw15` | 2 | mild | 15 | 393/20000 (0.021342) | 7353/20000 (0.362031) | 0/20000 (0.000150) | 2503/20000 (0.129064) | n/a |
| `m2_mixed_r1_imp_r2_null_persistent_gw15` | 2 | persistent | 15 | 395/20000 (0.021446) | 3443/20000 (0.167770) | 0/20000 (0.000150) | 2871/20000 (0.147691) | n/a |
| `m2_mixed_r1_null_r2_imp_persistent_gw15` | 2 | persistent | 15 | 389/20000 (0.021134) | 3470/20000 (0.169106) | 0/20000 (0.000150) | 2981/20000 (0.153255) | n/a |
| `m2_mixed_r1_imp_r2_null_mild_gw30` | 2 | mild | 30 | 393/20000 (0.021342) | 7410/20000 (0.364872) | 0/20000 (0.000150) | 2535/20000 (0.130685) | n/a |
| `m2_mixed_r1_null_r2_imp_mild_gw30` | 2 | mild | 30 | 376/20000 (0.020458) | 7445/20000 (0.366617) | 0/20000 (0.000150) | 2471/20000 (0.127443) | n/a |
| `m1_power_pos020_mild_gw15` | 1 | mild | 15 | n/a | 4025/20000 (0.196594) | 0/20000 (0.000150) | 566/20000 (0.030305) | n/a |
| `m2_power_pos020_mixed_mild_gw15` | 2 | mild | 15 | 366/20000 (0.019937) | 2370/20000 (0.114757) | 0/20000 (0.000150) | 2840/20000 (0.146123) | n/a |
| `m1_power_pos060_mild_gw15` | 1 | mild | 15 | n/a | 16519/20000 (0.821480) | 0/20000 (0.000150) | 15/20000 (0.001155) | n/a |
| `m2_power_pos060_mixed_mild_gw15` | 2 | mild | 15 | 345/20000 (0.018842) | 13803/20000 (0.684726) | 0/20000 (0.000150) | 2395/20000 (0.123592) | n/a |
| `m1_harm_neg040_mild_gw15` | 1 | mild | 15 | n/a | n/a | n/a | n/a | 13757/20000 (0.687850) |
| `m1_harm_neg060_mild_gw15` | 1 | mild | 15 | n/a | n/a | n/a | n/a | 18149/20000 (0.907450) |
| `m1_harm_neg080_mild_gw15` | 1 | mild | 15 | n/a | n/a | n/a | n/a | 19627/20000 (0.981350) |
| `m1_harm_neg060_persistent_gw15` | 1 | persistent | 15 | n/a | n/a | n/a | n/a | 14034/20000 (0.701700) |
| `m1_harm_severe_gw1_4_mild_gw15` | 1 | mild | 15 | n/a | n/a | n/a | n/a | 13540/20000 (0.677000) |
| `m2_harm_r1_neg060_r2_null_mild_gw15` | 2 | mild | 15 | 375/20000 (0.020406) | n/a | 0/20000 (0.000150) | 2529/20000 (0.130381) | 18027/20000 (0.901350) |
| `m1_empirical_pos40_pts_yr` | 1 | mild | 15 | n/a | 2559/20000 (0.124080) | 0/20000 (0.000150) | 797/20000 (0.042200) | n/a |
| `m1_empirical_pos60_pts_yr` | 1 | mild | 15 | n/a | 4288/20000 (0.209633) | 0/20000 (0.000150) | 439/20000 (0.023732) | n/a |
| `m1_empirical_pos80_pts_yr` | 1 | mild | 15 | n/a | 6443/20000 (0.316709) | 0/20000 (0.000150) | 244/20000 (0.013556) | n/a |
| `m2_empirical_pos60_mixed_pts_yr` | 2 | mild | 15 | 332/20000 (0.018164) | 2445/20000 (0.118456) | 0/20000 (0.000150) | 2535/20000 (0.130685) | n/a |
| `m1_empirical_neg40_pts_yr` | 1 | mild | 15 | n/a | n/a | n/a | n/a | 5114/20000 (0.255700) |
| `m1_empirical_neg80_pts_yr` | 1 | mild | 15 | n/a | n/a | n/a | n/a | 9575/20000 (0.478750) |

## Decision

**Verdict**: `certified=True`, `certified_mode=advisory`, `certification_seed=21103`, `live_adoption_blocked=False` (`certification_digest=243962e549d2516b2008d96f874a569e0b208cea28b2c72912d5e4889b8cfb6a`).

**Recommended action**:
- Freeze calibrated `v2.0` protocol (`statistical_protocol_hash=1e818b27815aee47302d73e5872ca1f82eb9919bbe6ad9ada98f65bb5dbd74c1`) with `certification_digest` bound prior to any prospective slate access.
- Retain `GW15`/`GW30`/`GW38` sparse confirmation cadence (weekly Transfer Planner leader selection captures practical value during the season; GW38 summer-rollover carryover policy tracked pre-`2027-28`).

## Risks and unknowns

- Realized 6-GW rolling MILP transfer trajectories show candidate-dependent weekly dispersion (`0.0–12.2` pts/GW), limiting single-season formal confirmation power for realistic `+40..+80 pts/yr` challengers and leaving multi-season GW38 carryover policy pending pre-`2027-28`.
- Synthetic certification does not authorize live Champion adoption on its own; empirical admission, frozen slate registration, pilot acceptance, and explicit human approval remain mandatory.

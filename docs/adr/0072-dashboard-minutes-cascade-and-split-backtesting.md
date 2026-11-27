# Dashboard Minutes Cascade Parity & Split Backtesting (ADR 0072)

**Status**: Accepted (2026-11-27, `/grill-with-docs` Q1–Q10 under Wayfinder Map [#249](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/249))

**Amends**: [ADR 0052](0052-projection-parity-cli-dashboard.md) (Projection Parity Invariant extends to default `Minutes Cascade`), [ADR 0056](0056-operational-zero-availability-hard-dnp.md) (Oracle Participation State bypass + operational `step = 0..5` boundary), [ADR 0066](0066-backtesting-and-promotion-foundation.md) §2 (Oracle Participation State + State-Stratified `xMins` diagnostics). Preserves [ADR 0069](0069-annual-rolling-validation-and-dual-tier-promotion.md) and [ADR 0071](0071-certified-solver-budget-and-milp-qualification-calibration.md) promotion authority.

---

## Context

1. **CLI vs Dashboard drift after PR #248:** CLI `injury_triage + solve` applied `SP_Soft_Shield_M1` (`Internal Minutes Baseline` + `Soft Empirical Broad Pool Shield`), whereas `commands.export_dashboard` (`run_dashboard_export`) exported pure Layer 1 (`ADR 0056` immediate hard-DNP only).
2. **Horizon tail mismatch:** `SOFT_UNKNOWN_CURVE` and `SOFT_DOUBTFUL_CURVES` were calibrated on `S-1` for `step = 0..5`, but dashboard exports span up to `GW38` (`H <= 19`). Clamping `step >= 6` at `step = 5` caps recovery across whole season.
3. **Confounded component diagnostics:** Existing `oracle_minutes=True` routed scalar `actual_minutes` through `scale_states_to_target()`, leaking wrong `p_start` / `p_60` appearance points for cameos; `commands.evaluate_minutes` lacked per-state conditional duration (`xmins_if_start`, `xmins_if_sub_in`), multi-horizon decay, and position splits. Meanwhile `SP_Soft_Shield_M1` beat `L1_native` on `S-1` (`+87`) but trailed untuned `S-2` (`-28`), and `M4` club outfield inflation cut raw MAE (`10.48m`) while losing `-86` (`S-1`) / `-48` (`S-2`) MILP pts.

---

## Decisions

1. **Default Dashboard `SP_Soft_Shield_M1` & `ADR 0052` Parity (`Track A`, `#250`):**
   - `run_dashboard_export()` runs automated `SP_Soft_Shield_M1` by default per exported model (using each model's own native `projected_minutes` as `native_mins_map` and aligning `step = 0` at `target_start`), maintaining exact `ADR 0052` parity across `dashboard_data.json`, `data/{model}.csv`, Dashboard Explorer/Planner, and default CLI solves.
   - `soft_curve` (`status='i'` unknown return, `status='n'` non-loan, `status='d'`/`chance < 100`) is bounded strictly to `step = 0..5` (`SOFT_CURVE_MAX_STEP = 5`) and reverts to native Layer 1 for `step >= 6`; `status='u'`, parsed `return_gw` hard guards, and `M1` GKP span remaining horizon.
   - Dashboard exports never silently read local `data/planner/xmins_override.csv`; explicit `--xmins_override` (opt-in) and `--no-minutes-cascade` (pure Layer 1 opt-out) supported; `meta.minutes_cascade` stamped in `dashboard_data.json`. `ADR 0069` validation captures remain pure Layer 1.

2. **Split Component Diagnostics Feeding (Not Replacing) `ADR 0071` Gate (`Track B`, `#251`):**
   - Split backtesting (**State-Stratified `xMins`** + **Oracle Participation State Event Evaluation**) serves strictly as component diagnostic and fast screen; **Integrated 6-GW Rolling Strategic MILP Net FPL Points (`ADR 0066` / `ADR 0071`)** remains sole Champion promotion gate.
   - **Oracle Participation State:** Fixture-grain `(player_id, gameweek_id, fixture_id)` injection of exact realized `(Start, Sub-in, DNP)` (`starts == 1`, fallback `minutes >= 60` only when `starts` absent), `actual_minutes`, and `p_60` (`minutes >= 60`), bypassing `scale_states_to_target` and `ADR 0056` overrides (`|projected_minutes - actual_minutes| <= 1e-6`, `|xp_minutes - actual_xp_minutes| <= 1e-6`), blocked in `backtesting/forecast_adapter.py`, with dual-pool (`all_players` + `appeared`) reporting.
   - **State-Stratified `xMins`:** `commands/evaluate_minutes.py` stratifies along canonical 3 states (`Start`, `Sub-in`, `DNP`), conditional duration errors (`xmins_if_start`, `xmins_if_sub_in`, `p_dnp`), `p_60_if_start` calibration, `GKP/DEF/MID/FWD` splits, and `--horizon` (`t=0..5`) decay without adding extra model sub-states upfront.

3. **Layer 1 Candidate vs Layer 2/3 Boundary (`Track C`, `#252`):**
   - `Soft Empirical Broad Pool Shield` stays permanently in **Layer 3b** (pre-deadline API availability).
   - `M1` GKP stays live in **Layer 2 (`Internal Minutes Baseline`)**; pure point-in-time history `M1` GKP solo (zero `status`/`chance`/`news` reads, distinct from dead-locked softmax/linear `min_05_*`) is eligible as `#205` Layer 1 Candidate evaluated under Track B diagnostics + `ADR 0071` Win-Both (`S-1` + `S-2`) without prematurely sealing the slate (`M=1` default / batch-before-freeze respected).

---

## Considered Options

- **Dashboard on pure Layer 1 or Transfer-Planner-only cascade:** Rejected; violates `ADR 0052` parity between CLI solver and Dashboard Explorer/Squad Board.
- **Auto-loading local `data/planner/xmins_override.csv` on Dashboard Refresh:** Rejected; leaks local user overrides into credential-free `commands.dashboard` deployments (`ADR 0060`).
- **Promote standalone `xMins` / Oracle-Event winners directly:** Rejected (`M4` counterexample: improved MAE `10.48m` while losing `-86` MILP pts).

---

## Consequences

- Tracks A & B cleanly rotate `core_closure_hash()` while `podium_sealed=false` (`#205`).
- All product projections align by default on automated Official-data `SP_Soft_Shield_M1` while historical & `ADR 0069` validation stay strictly pure Layer 1.

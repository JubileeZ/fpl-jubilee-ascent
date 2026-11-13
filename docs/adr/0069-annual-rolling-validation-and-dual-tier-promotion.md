# Annual Rolling Validation and Dual-Tier Promotion Governance (ADR 0069)

**Status**: Accepted (2026-11-13, Wayfinder Map [#184](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/184) governance reset)  
**Scope Note (Policy vs Implementation)**: Policy effective immediately. Hardcoded runtime/test `2026-27 GW6+` guards (`backtesting/data_admission.py`, `backtesting/confirmation_registry.py`, `backtesting/live_capture.py`, `.agents/skills/ideate-candidate/generate_prompt.py`, plus `tests/`) remain in force until refactored into `config/season_lifecycle.json` under [#185](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/185) and [#187](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/187). Existing Champion `def_xg_shrink_challenger` and `candidate_ledger.csv` Dead Lever locks remain unchanged.

**Amends / Supersedes**:
- Supersedes Section 8 (`#180`, 2026-11-12) and static `2026-27 GW6+` holdout/provisional-ban clauses of [ADR 0066](0066-backtesting-and-promotion-foundation.md); **retains ADR 0066 Sections 1–7 intact** (6-GW rolling replay net FPL points primary, neutral `£100.0m` GW1 ownership anchor, `GW1` locked / `GW2+` transfers / `1..5 FT`, 15 projection guards, non-wrapping MBB `L=5`, `FWER <= 0.05`, 4-way verdicts, immutable attempt registry, manual `adopt_champion`, frozen [ADR 0065](0065-strategic-arm-horizon-penalty-scaling-and-ft-schedule.md) Strategic constants).
- Amends [ADR 0046](0046-point-in-time-backtest-and-statistical-gate.md) and [ADR 0047](0047-two-season-promotion-gate.md): replaces static `2026-27 GW6+` freeze and archive-only serial confirmation with annual rolling quarantine (`S`, `S-1`, `S-2`) and Dual-Tier `Provisional Active` operation.
- Amends [ADR 0064](0064-promotion-gate-and-evaluation-rigor-overhaul.md): aligns two-season warm-seeded evaluation with annual rolling filter (`S-1` + `S-2`) preceding `Provisional Active` validation on `S`.
- Preserves Wayfinder Map #174 completed engineering specifications `#175`–`#179` (freshness rules, `< gw` lineage audit, `#177` source review, unified `mode="empirical"` architecture, Stage A->B replay controls & guards).

---

## Context

Static multi-year `2026-27 GW6+` locks combined with Section 8 of ADR 0066 (deferring validation until `2027-28 GW1–38` via unattended `-30m` live collection and banning provisional operation) prevented promising candidates validated across two past seasons from predicting in the current season for 1.5+ years and imposed fragile automated cron collection requirements. Meanwhile, public repository [`Randdalf/fplcache`](https://github.com/Randdalf/fplcache) already archives 4x-daily FPL `bootstrap-static` `.json.xz` snapshots pre-deadline (verified `0.63h–12.35h` before every `2026-27 GW1–10` deadline).

---

## Decisions

### 1. Annual Rolling Firewall & Summer Rollover (`config/season_lifecycle.json`)
Replace hardcoded year checks (`2023-24`, `2024-25`, `2025-26`, `2026-27`) with config-driven `SeasonLifecycle` roles updated on annual rollover:
- **Current Validation Season `S` (`2026-27`)**: Strictly quarantined from model training, parameter tuning, and candidate ideation. Generates weekly runtime projections and runs frozen validation checkpoints only. Inside replay/prediction, `model.fit()` sees strictly `gameweek_id < gw` rows plus prior-season seed (`S-1`).
- **Development Season `S-1` (`2025-26`)**: Sole season authorized for candidate ideation, parameter sweeps, and tuning (warm-seeded by `S-2`).
- **Historical Filter Season `S-2` (`2024-25`)**: Untuned cross-check season (seeded by `2023-24`, `position_id==5` excluded); candidate must beat `Confirmed Champion` on both `S-1` and `S-2` without severe segment harm to qualify for `Provisional Active`.
- **Annual Summer Rollover**: After `S` finishes `GW38` (`data_checked=True`): `S -> S-1` (unlocked for next-cycle development), `S-1 -> S-2`, new season opens as quarantined `S`. Reigning `Confirmed Champion` carries forward into new `GW1`; any unconfirmed `Provisional Active` either clears `GW38` final review (`adopt_champion`) or resets cleanly before new `GW1`.

### 2. Canonical Pre-Deadline Source: `Randdalf/fplcache` (`<= 24h`) & Attribution
- **Canonical Validation Bootstrap Base**: Admit `S` (`2026-27 GW1–38` and subsequent `S`) using [`Randdalf/fplcache`](https://github.com/Randdalf/fplcache) (`The Unlicense`, public domain, 4x-daily automated `bootstrap-static` `.json.xz`) within `<= 24h` before each official GW deadline (`8h` target / `24h` hard cap per `#175`). Eliminates mandatory unattended `-30m` collector automation (`optional higher-freshness local receipts accepted when manually present`).
- **Settled Outcomes & Fixtures**: Pair `fplcache` pre-deadline bootstrap with verified pre-deadline schedule provenance (`#185`) and independent official FPL outcome settlement (`captured_at >= max(kickoff) + 24h`, `finished=True`, `data_checked=True`, `#178` rules).
- **Mandatory Disclosed Limitations**: Record structured mirror limitations (`<= 24h` deadline lag missing late press-conference team news, e.g. `12.35h` at `2026-27 GW10`; historical exploratory diagnostics performed on `2026-27 GW1–5` prior to reset).
- **Attribution**: Formally credit [`Randdalf/fplcache`](https://github.com/Randdalf/fplcache) (`Unlicense`) in `README.md`, `ADR 0069`, and validation/research artifacts.

### 3. One-Shot Frozen-Candidate Firewall on `S`
- Candidates evaluated on `S` must freeze model source hash, parameter hash, and `protocol_hash` in `confirmation_registry.jsonl` **before** accessing `S`.
- **Strict Non-Retuning Rule**: Inspecting `S GW1..X` results, tweaking model logic or parameters on `S-1`, and re-testing the modified candidate on the already-observed `S GW1..X` window is strictly prohibited.

### 4. Dual-Tier Weekly Operation (`Confirmed Champion` + `Provisional Active`)
- **Qualification (`max 2` frozen finalists)**: Up to `2` frozen finalists (`_MAX_CANDIDATES = 2` in `models/selection.py`) clearing `Confirmed Champion` on both `S-1` and `S-2` (`plus projection/segment sanity checks`) enter confirmation slate; `#1` enters **`Provisional Active`**.
- **Weekly Predictions & Default Solver**: **Both** `Confirmed Champion` and `Provisional Active` project weekly side-by-side (`config/model_selection.json`, Explorer/export surfaces). When `Provisional Active` exists, it drives the **default weekly Transfer Plan** (`Confirmed Champion` immediately selectable for comparison).
- **Early-Harm Fallback**: Before permanent confirmation checkpoints, if `Provisional Active` violates calibrated early live/validation harm thresholds (`#186`), default reverts immediately to `Confirmed Champion` (or promotes pre-frozen finalist `#2` if eligible).
- **Manual Final Adoption**: Permanently updating `"champion"` in `config/model_selection.json` stays gated by explicit manual `adopt_champion` (`--approval_ref`, `--bundle_hash`, `--expected_champion`; zero unattended auto-overwrite).

### 5. Neutral `£100m` GW1 Benchmark & Checkpoints (`GW15` / `GW30` / `GW38`)
- **Benchmark Estimand**: Retain `ADR 0066` Sections 1–7 primary scorecard: independent 6-GW rolling Strategic transfer replay initialized from neutral `£100.0m` GW1 ownership anchor (`GW1` squad locked; transfers begin `GW2`; `1 <= FT <= 5`; `-4` hit cost; `ADR 0065` Strategic constants). Weekly operational Transfer Plan continues solving on user's actual live squad (`dashboard/planner_service.py` / `commands.solve`).
- **Permanent Confirmation Threshold**: Retain search-family `FWER <= 0.05` across `M <= 2` frozen finalists plus substantive projection guards and segment loss floors to permanently replace `Confirmed Champion` (exact null-calibrated inference & harm parameters set in `#186`).
- **Pre-Declared Checkpoints**:
  - **`GW15` (`>= 15` GWs)**:
    - Clears `<= 5%` FWER + zero harm -> eligible for early manual confirmation (`retiring prior Confirmed Champion`).
    - Trails `Confirmed Champion` or hits harm limit -> drop `Provisional Active`; test pre-frozen `#2` podium candidate (`within M <= 2 FWER budget`).
    - Ahead/even without `<= 5%` statistical certainty -> retain Dual-Tier cleanly (`Provisional Active` remains weekly default) until **`GW30` / `GW38`**.
  - **`GW30` / `GW38`**: Final in-season confirmation vs drop decision prior to summer rollover.

---

## Considered Options

1. **Wait for `2027-28 GW1–38` unattended `-30m` live capture (`ADR 0066` Section 8)** — *Rejected*: blocks production benefit from two-season-validated improvements for 1.5+ years and relies on unbuilt unattended cron infrastructure.
2. **Provisional-off single-tier + pure raw points lead at `GW15` (`no statistical bar`)** — *Rejected*: single `18.56` pts/GW Champion dispersion (`2025-26`) creates excessive luck-driven champion churn at `15` GWs, while Dual-Tier `Provisional Active` captures timely gains without compromising permanent Champion integrity.
3. **Exclude `2026-27 GW1–10` and start strictly from `GW11` (`2026-11-21`)** — *Rejected*: leaves `GW1–10` verified pre-deadline `Randdalf/fplcache` snapshots unused and delays `15`-GW check from `GW15` to `GW25`.

---

## Consequences

- Candidate ideation/search resumes on a clean, leak-free annual cycle (`S-1` Dev, `S-2` Filter, `S` Quarantined Validation) as soon as `#185`–`#188` complete.
- Promising candidates act immediately via Dual-Tier `Provisional Active` without weakening `<= 5%` FWER permanent champion standards or manual adoption control.
- Explicit attribution to `Randdalf/fplcache` and structured `-24h` lag disclosure keep reproducibility audit-ready without unattended cron fragility.

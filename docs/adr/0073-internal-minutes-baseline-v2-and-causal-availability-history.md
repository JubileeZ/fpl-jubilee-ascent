# Internal Minutes Baseline v2, Causal Availability History & Layer 1 Pure-History Screen (ADR 0073)

**Status**: Proposed (2026-11-28, `/grill-with-docs` Q1–Q7 under Wayfinder Map [#256](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/256); Tracks [#257](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/257), [#258](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/258), [#259](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/259))

**Amends**: [ADR 0072](0072-dashboard-minutes-cascade-and-split-backtesting.md) (upgrades Layer 2 `Internal Minutes Baseline` scope beyond `SP_Soft_Shield_M1` to selective healthy outfield starter floors, documented-injury returners, Shield fixes, and optional downward overflow cap). Preserves [ADR 0052](0052-projection-parity-cli-dashboard.md), [ADR 0069](0069-annual-rolling-validation-and-dual-tier-promotion.md), and [ADR 0071](0071-certified-solver-budget-and-milp-qualification-calibration.md).

---

## Context

1. **Outfield divergence vs external `xMins` (`2026-27 GW13–22` diagnostic):** Under `SP_Soft_Shield_M1`, healthy outfielders fall straight through to Layer 1 (`def_xg_shrink_challenger`) while GKP `M1` is already `0.48m` MAE (`0.00m` bias). Full-pool comparison against Solio (`data/external/solio/2026-27/gw13_2026-11-28T2323.csv`, `n = 568`, `MAE = 8.81m`) decomposes main errors into:
   - **Bucket A (`18.4%`):** Fit-starter horizon decay & single-exit distortion (`LearnedStartChallengerModel` `0.5^h` decay into injury-depressed `p_champ`, `< 45m` injury exits lowering `xmins_if_start`, `Trailing Start Window` `STATE_PRIOR_STRENGTH = 1.0` price-band dilution).
   - **Bucket B (`10.9%`):** Documented-injury returners now `status='a', chance=100%` (skipped by Shield; prior-season seed dropped at `GW2+`).
   - **Bucket C (`21.5%`):** `SP_Soft_Shield_M1` bugs (`soft_curve` scaling depressed `native_mins_map`, `45m` `filter_depressed_post_return` cliff, outfield `d` curve applied to GKP, blind `status='s'` restoration).
   - **Bucket D (`21.9%`):** Unconstrained club outfield totals (`> 900m` overflow when injured stars return without trimming stand-ins).
2. **Dead-lever & MILP risk boundary:** Prior `M4` club outfield upward reconciliation (`890m`) cut MAE (`10.48m`) while losing `-86` (`S-1`) / `-48` (`S-2`) rolling MILP pts; blind unflagged `M2` spiked `false_start_pct` and lost `-51` Legal XI pts; `pos_cap_*`, `form_slot_*`, `min_04_*`, `A2 nailed_*`, `a3r2_*`, and `m1_gkp_solo` remain dead-locked in `candidate_ledger.csv`.

---

## Decisions

1. **Path 1 Sequencing:** Upgrade Layer 2 (`Internal Minutes Baseline v2`, [#257](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/257) → [#258](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/258)) first while keeping Layer 1 frozen; then execute Phase 2 Layer 1 pure-history diagnostics & candidate screening ([#259](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/259)).
2. **Q1 Two-Stage Dual-Win Gate (preserves `ADR 0072`):** Every Layer 2 `v2` change must beat `SP_Soft_Shield_M1` on **both** Stage 1 (`t=0..5` state-stratified `xMins` quality + `false_start_pct`) **and** Stage 2 (certified `600s` `gap=0.0` 6-GW rolling Strategic MILP Net Points on `S-1` `2025-26` `> 2,207` and untuned `S-2` `2024-25` `> 2,308` without degrading `false_start_pct` or `t0_xp_mae`). `2026-27` Solio CSV strictly read-only diagnostic (zero `2026-27` tuning under `ADR 0069`).
3. **Q3 & Q5 `Causal Availability History`:** Layer 2 reads pre-deadline availability snapshots strictly `< target_gw` (`S-1`/`S-2` `data/reports/empirical_mirrors/*/bootstraps/gw*.json.xz`; live `data/processed/availability_history.parquet` synced in `commands/refresh_data.py` from `origin/availability-snapshots` + live captures), with clean graceful fallback to single-snapshot mode when absent.
4. **Q6 Bucket C & Bucket A/B Concrete Mechanics:**
   - **Bucket C (`#257`):** Scale `soft_curve` from healthy `fit_mins * n_fix` for tenured starters; replace hard `45m` `filter_depressed_post_return` cutoff with relative threshold (`native_mins < 0.85 * fit_mins * n_fix`); calibrate GKP-specific `d` (`75/50/25`) curve on `S-1`; gate `status='s'` restoration by pre-ban start rate (`start_rate * fit_mins`).
   - **Bucket A (`#258`):** Compute healthy-only start rate (excluding `< target_gw` `i`/`s`/`u` or `chance <= 25` GWs) and outlier-robust median `fit_mins` (excluding `< 45m` early injury/red exits); emit selective horizon-stable floor for currently healthy (`status='a', chance=100`) established starters while leaving rotation/fringe players on native Layer 1.
   - **Bucket B (`#258`, anti-`M2`):** Fire post-clear recovery ramp **strictly only** when `Causal Availability History` proves recent flagged absence (`i`/`s` or `chance <= 50`), now `status='a', chance=100`, with pre-injury current-season or prior-season seed tenure; never fire on unflagged absences.
5. **Q2 & Q2-rev `Downward Overflow Cap` (`Bucket D-lite`, `#258`):** Isolated toggleable component: never inflate clubs `<= 900m` per fixture; when returning incumbents push club outfield sum `> 900m` per fixture, trim only surplus above `900m` downward off lower-tenure same-position (`position_id`) stand-ins. Ship enabled **only** if clearing Q1 Two-Stage Dual-Win Gate on top of Buckets A+B+C; else leave teammate displacement manual in Layer 3a.
6. **Q4 Phase 2 Layer 1 Pure-History Screening (`#259`):** Run `ADR 0072` Track B (`commands/evaluate_minutes.py --horizon`) on `S-1` first; screen up to 3 isolated pure-history levers (`xmins_if_start` outlier robustness, `Trailing Start Window` prior dilution, `ADR 0053` `0.5^h` decay audit) strictly outside `models/`; advance Stage 1 xMins winners only to `ADR 0071` Win-Both + `15/15` guards, logging all outcomes in `candidate_ledger.csv`.
7. **Q7 Governance Sync:** Record `ADR 0073` (`Proposed` → `Accepted` on `#258` merge) and sync `CONTEXT.md` glossary (`Internal Minutes Baseline`, `Causal Availability History`, `Downward Overflow Cap`).

---

## Considered Options

- **Standalone xMins MAE gate without rolling MILP check:** Rejected; `M4` improved MAE (`10.48m`) while losing `-86` (`S-1`) / `-48` (`S-2`) MILP pts by flattening starter-floor risk separation.
- **Layer 1 first or simultaneous Layer 1 + Layer 2 edits:** Rejected; Layer 1 cannot read availability flags (dead `a3r2_*`), faces `15/15` guards + dead locks, and confounds causal Layer 2 vs Layer 1 attribution.
- **Single-snapshot-only Layer 2 or upward `890m` club reconciliation (`M4`):** Rejected; single-snapshot cannot separate documented injury from tactical drop (`M2` `-51` Legal XI pts), and upward inflation destroys starter-floor separation.

---

## Consequences

- Layer 2 `v2` ships incrementally via [#257](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/257) and [#258](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/258) under default CLI/Dashboard parity (`ADR 0052` / `ADR 0072`), while `ADR 0069` pure Layer 1 captures remain untouched.
- Phase 2 ([#259](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/259)) isolates pure-history Layer 1 diagnostics and Candidate evaluation cleanly under `ADR 0071` and `#205` without premature slate sealing.

# Certified Solver Budget & Rolling-MILP Qualification Calibration (ADR 0071)

**Status**: Accepted (2026-11-22, `/grill-with-docs` session under Map [#205](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/205) / [#207](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/207))

**Amends**: [ADR 0069](0069-annual-rolling-validation-and-dual-tier-promotion.md) (podium ranking, rolling-MILP segment floors, batch-before-freeze / `M=1` slate discipline), [ADR 0066](0066-backtesting-and-promotion-foundation.md) / `CONTEXT.md` `Certified Quality Policy` (`time_limit_seconds` cap & CLI/runner defaults). Preserves [ADR 0070](0070-weekly-planner-selection-and-champion-adoption.md) live confirmation certification and `EXT-01_1` Dead lock (`revisit_after=2027-11-22`).

---

## Context

1. **Certified timeout cliff (`#207`, `freeze` CI default):** `EXT-01_1` S-2 GW24 timed out at `180s` (`0.091%` relative gap) on PR `#204` host while solving exact `OPTIMAL` (`gap=0.0`, `147.53s`) on Apple M2 (`#208`), with Champion GW7 peaking at `132.78s` (`74%–82%` of `180s` cap). Meanwhile, `commands.produce_validation_evidence freeze` defaulted `--time-limit-seconds` to `60.0s` under `.github/workflows/validation-collector.yml`, creating imminent CI `TIME_LIMIT` failures on slower Ubuntu runners.
2. **Segment floor scale mismatch:** `backtesting/promotion_evidence.py` (`_passes_segment_floors`) and `compare_historical_replays.py` reused legacy single-GW regret tolerances (`-0.25 / -0.15 / -0.13` pts/GW from [ADR 0062](0062-non-catastrophic-segment-loss-promotion-guardrail.md)/[ADR 0064](0064-promotion-gate-and-evaluation-rigor-overhaul.md), calibrated for paired `SD ≈ 2.2` pts/GW) on 6-GW rolling-MILP replays (`ext_01_1_a10` empirical weekly `SD ≈ 11.0` pts/GW, lag-1 `phi ≈ 0.10`, `SE_season ≈ 74.8` pts). At MILP scale, `-0.25/-0.15/-0.13` corresponds to `z ≈ -0.045 SE`, destroying `85%–89%` of two-season Win-Both power (`+50` pts/yr power `55.9% -> 8.3%` at `G=1`). `_passes_segment_floors` also silently ignored unknown or missing segment keys.
3. **Winner's curse vs. `0.5*(S1+S2)` average (`#205` Monte Carlo & governance audit):** At `sigma_gw=11.0, phi=0.10`, picking max `S-1` across `G=2..6` variants given `S-1 > 0` injects `+66..+83.5` pts (`+0.88..+1.12 SE`) selection bias on pure nulls. Unweighted `0.5*(delta_S1 + delta_S2) > 0` lets `48%–70%` of nulls pass into `M <= 2` sealed slates while [ADR 0070](0070-weekly-planner-selection-and-champion-adoption.md) statistical Early-Harm is certified `advisory` only (`3.87%` terminal exclusion at `-0.60 SD`) and filling slot `#2` halves `GW38` confirmation power (`12.63% -> 6.20%` at `+50`).
4. **K=3 GW1-anchor trap & GW4 Wildcard collapse:** Both `S-1` and `S-2` Shared Chip Calendars deploy Wildcard 1 at `GW4` (`12–13` transfers), collapsing distinct `GW1` ownership anchors onto nearly identical squads. Any future multi-trajectory `S-2` variance reduction requires distinct predeclared chip calendars rather than `GW1`-only anchor swaps.

---

## Decisions

1. **Certified Solver Budget (`600s` cap & defaults, exact optimality):**
   - Retain `mode="certified"`, `target_gap=0.0`, `require_proven_optimal=True`, `raise_on_failure=True`.
   - Raise certified ceiling `MAX_CERTIFIED_TIME_LIMIT_SECONDS = 600.0` (`backtesting/rolling_replay.py`); set `DEFAULT_CERTIFIED_TIME_LIMIT_SECONDS = 600.0` in `commands.produce_validation_evidence freeze`, `run_s1_replay.py`, and `run_s2_filter.py`. Keep `QualityPolicy.time_limit_seconds` dataclass default (`60.0`) and verification backwards-compatible across `(0.0, 600.0]`.
   - Reject hardware-dependent best-feasible `TIME_LIMIT` incumbents (`run_s2_incumbent_diagnostic.py` remains non-qualifying diagnostic only; close [#207](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/207)).

2. **Qualification Gate & `30/70` Podium Ranking:**
   - Retain Win-Both historical gate (`delta_s1 > 0.0` AND `delta_s2 > 0.0` + `15/15` applicable projection guards). Reject `0.5*(delta_S1 + delta_S2) > 0` average gating.
   - Change `rank_and_freeze_podium` ranking key from `mean_two_season_delta` (`50/50`) to `podium_ranking_score = 0.3 * delta_s1 + 0.7 * delta_s2` (`PODIUM_S1_WEIGHT=0.3`, `PODIUM_S2_WEIGHT=0.7`; tie-break `-delta_s2`, `candidate_name`) to downweight `S-1` variant-selection bias.
   - Reserve 3-predeclared-chip-calendar `S-2` Win-Both evaluation as a follow-up option only if `#206` (`EXT-02_1`–`EXT-04_1`) shows recurring `S-2` path noise despite improved projection MSE.

3. **Rolling-MILP Segment Floors (`z = -1.50 SE`) & Strict Key Validation:**
   - Add `MILP_SEGMENT_REGRESSION_TOLERANCES = {"cold_start": 8.9, "early_mid": 4.7, "late": 4.2}` pts/GW (`-35.6 / -70.5 / -79.8` cum pts; calibrated to `z = -1.50 SE` at `sigma_gw=11.0, phi=0.10`: `SE_cold=5.925`, `SE_mid=3.119`, `SE_late=2.775` pts/GW, retaining `93%` of unconstrained Win-Both power) in `backtesting/promotion_evidence.py` and `compare_historical_replays.py`.
   - Enforce exact key validation `("cold_start", "early_mid", "late")` in `_passes_segment_floors` and `compare_historical_replays.py` (raise `ValueError` on missing/unknown keys or non-finite/bool values). Leave legacy single-GW regret tolerances (`0.25 / 0.15 / 0.13`) in `backtesting/promotion.py` untouched.

4. **Batch-Before-Freeze & `M = 1` Default Slate Discipline:**
   - Evaluate bounded `#206` ideation queue (`EXT-02_1` -> `EXT-03_1` -> `EXT-04_1`; `EXT-05_1` last only if `0` qualify) completely before proposing slate freeze (`+39%` expected `#1` quality vs sequential first-2 admission).
   - Default to sealing `M = 1` top finalist unless two genuinely strong qualifiers emerge (preserving `M=1` GW38 confirmation alpha `0.02734` vs `0.00954`).

5. **Preserved Locks & Separate `ADR 0070` `gw1_4` Follow-Up:**
   - Preserve `EXT-01_1` `dead` lock until `2027-11-22` (respecting `candidate-ledger.md` non-reopen rule).
   - Track recalibration of `ADR 0070` `gw1_4_material_loss_limit = 25.0` pts (which yields `14.67%` null / `10.69%` `+40` false terminal exclusion at `sigma_gw=11.0` vs `<= 5%` target; `~68.75` pts restores `0.18%`) as a separate Map `#190` issue before `CHAMPION_ADOPTION_LIVE_ENABLED=true`, leaving current `certification_result.json` digest untouched now.

---

## Consequences

- Eliminates CI/historical `TIME_LIMIT` aborts without sacrificing cross-host `OPTIMAL` determinism.
- Restores rolling-MILP two-season Win-Both power (`8.3% -> 51.9%` at `+50` pts/yr, `G=1`) while blocking `S-1` winner's-curse overfits from wasting scarce `M <= 2` season slots.
- Modifies `backtesting/rolling_replay.py` and `backtesting/promotion_evidence.py`, cleanly rotating `core_closure_hash()` before `#206` (`EXT-02_1`) begins; archived `EXT-01_1` artifacts remain untouched.

---

## Empirical Verification Note (2026-11-24, Map #235 / #237 / #240)

- **Single-read `col_value` extraction (`backtesting/native_transfer_solver.py`):** Cuts per-GW solution extraction `~1,300×–1,800×` (`~129s → 0.09s`), reducing 38-GW certified `threads=1`, `gap=0.0` replay wall time (`2025-26`: `10.52m → 8.33m`, `2024-25`: `15.09m → 13.14m`, `38/38 OPTIMAL`, `0` diffs, exact `2,120` / `2,336` parity). Editing `native_transfer_solver.py` cleanly rotates `replay_solver_identity` while `podium_sealed=false` (`provisional_active=null`).
- **Certified `threads=1`, `gap=0.0`, `seed=42`, static seed + `disable_submip=True` preserved:** `#237` benchmarks on 21 hardest GWs rejected HiGHS primal heuristics-on (`+15%–36%` slower), `LP-kernel-all`, `no-seed`, `tight_bounds` (`170.2s` GW07 regression), and non-zero certified gaps (`0.10%` flipped GW05 `-35` pts on `2024-25`). Multi-trajectory / parallel prep scripts use machine-adaptive physical/P-core sizing (`solver/parallelism.py`).

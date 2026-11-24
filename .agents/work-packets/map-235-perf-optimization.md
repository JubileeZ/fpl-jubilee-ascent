# Active Task: Map #235 Performance Optimization Spec & Handoff (#240)

- **Status:** In Progress
- **Objective:** Complete [Approve final performance optimization specification and implementation handoff](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/240) under [[Wayfinder Map] Accelerate Backtesting Replay, Pytest Suite, and Live H=10 MILP Performance](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/235), then implement approved optimizations.
- **Acceptance:** `#240` HITL grilling approved and closed; ordered production implementation plan + ADR/CI updates finalized; finished Work Packet + `.agents/handoff-pointer` deleted on completion.
- **Issue/Ticket:** Map `#235`, next open ticket `#240` (closed: `#236`, `#237`, `#238`, `#239`).

## Work Packet (SFDBN)

- **Status:** Benchmarks `#236`–`#239` complete and closed on GitHub; `#240` sole open ticket on Map `#235`; ready for cross-device pickup.
- **Files:** Handoff docs (`docs/agents/current-state.md`, `ROADMAP.md`, `.agents/handoff-pointer`, `.agents/work-packets/map-235-perf-optimization.md`); remote throwaway prototypes on `origin/prototype/237-native-solver-bench` (`9697eb61`: `backtesting/prototype_237_native_solver_bench.py`), `origin/prototype/238-pytest-bench` (`3dd914b1`: `tests/prototype_238_verification_bench.py`, `tests/prototype_238_heavy_hitters_bench.py`), `origin/prototype/239-live-h10-bench` (`e7f99b5e`: `solver/prototype_239_live_h10_bench.py`). Target production files for `#240`: `backtesting/native_transfer_solver.py`, `docs/research/strategic-ft-calibration/runner.py`, `backtesting/{promotion_evidence,portable_evidence,forecast_store}.py`, `commands/{produce_validation_evidence,export_dashboard,solve,transfer_plan_scenarios}.py`, `features/builder.py`, `solver/solver.py`, `tests/`, `pyproject.toml`, `.github/workflows/pytest.yml`.
- **Decisions:**
  - `#236` (`#issuecomment-7129117954`): priority Backtest Replay -> Pytest/CI -> Live H=10; zero accuracy/coverage loss; keep `ADR 0071` certified `gap=0.0`/`threads=1`/`seed=42`; keep `LIVE_SOLVER_REL_GAP=0.0`; `pytest-xdist` default once parallel-safe.
  - `#237` (`#issuecomment-7132710038`): adopt single-read `col_value` extraction (`2025-26` `10.52m->8.33m`, `2024-25` `15.09m->13.14m`, `38/38` OPTIMAL exact parity `2,120`/`2,336`); keep static seed + `disable_submip=True` and `ADR 0071` `gap=0.0`/`threads=1` (reject `tight_bounds`, LP-fixing, heuristics-on, non-zero certified gaps); carry machine-adaptive physical/P-core parallelism + redundant-code cleanup.
  - `#238` (`#issuecomment-7134614874`): adopt `pytest-xdist --dist worksteal` with portable cross-OS physical/P-core/cgroup worker sizing (`-n 0` override); add `filelock` dev dep for cross-worker `retained_template` & `retained_verified_checkpoint` sharing; add stdlib `ContextVar` call-scoped verify/replay cache (`vce` `10.5x`, `pve` `4.7x`, 100% hash parity); fix `commands/export_dashboard.py` hot loops/duplicates + audit `features/builder.py` (`30.6s`); fix `tests/test_xmins_override.py` `tmp_path` isolation + module fixture (`50.71s->13.20s`); expand `@pytest.mark.slow` (~7-8 tests `>=15s`) with 100% tests in 4-vCPU CI `-n 4 --dist worksteal`.
  - `#239` (`#issuecomment-7136874274`): adopt `V3+` exact formulation tightening in `solver/solver.py` (`k`-domination `-15.5%` pool, inactive chip/squad omission, compact joint FT replacing `big_m=20`, exact LP equalities & unused slack removal -> `-74.5%` constraints, `H=6` `32.8–64.7s Optimal`, `H=10` `+1.22` to `+3.30` xP) + drop redundant `git` subprocess calls in `prep_data`; reject `V4` warm starts; keep `LIVE_SOLVER_REL_GAP=0.0` (diagnostic `gap=0.005` took `46.5–93.3s` & flipped GW12 transfers on `3/3` arms; document exact `H=10` `138–181s` vs `<=45s` aspiration); adopt machine-adaptive live HiGHS threading (`min(4, cores)` single-arm `174.1s Optimal`, `min(4, max(1, cores // 3))` per concurrent scenario arm with `resetGlobalScheduler`/process safety).
- **Blocked:** None.
- **Next:** New device/session: `git pull`, read `.agents/handoff-pointer` -> bind this packet, fetch `#235` & `#240` (`git fetch origin` if inspecting `origin/prototype/237..239-*`), then execute HITL grilling for `#240` to approve final spec, ADR/governance updates (`replay_solver_identity` rotation, `ADR 0071` notes, `2,120` vs `2,138` baseline note), and ordered implementation plan.

## Todo
- [x] `#236` targets, priority, governance boundaries
- [x] `#237` native replay solver benchmark (`origin/prototype/237-native-solver-bench` @ `9697eb61`)
- [x] `#238` pytest/CI profiling & verification cache benchmark (`origin/prototype/238-pytest-bench` @ `3dd914b1`)
- [x] `#239` live `H=10` MILP tightening benchmark (`origin/prototype/239-live-h10-bench` @ `e7f99b5e`)
- [ ] `#240` approve final performance optimization spec & ordered implementation handoff
- [ ] Implement approved optimizations, verify (`ruff`, `pytest`, `verify.sh`), delete this packet & `.agents/handoff-pointer`, close `#240` & `#235`

## Blockers / Notes
- Exact `def_xg_shrink_challenger` `2025-26` baseline on `main @ 3b6a183e` = `2,120` (`2024-25` = `2,336`) due to PR `#234` 5-FT overflow hold waiver (after `proto230_gw_trajectories.csv` `2,138`).
- Keep `2026-27` sealed (`ADR 0069`); never weaken `ADR 0071` certified `gap=0.0`/`threads=1` or test assertions; never merge throwaway `prototype/*` branches to `main`.
- Cross-device portability required (Linux physical cores, macOS Apple Silicon P-cores / Intel physical cores, Windows, 4-vCPU CI).

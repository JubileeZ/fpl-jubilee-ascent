# Active Task: Point-in-Time Participation Model Validation

- **Status:** In progress — temporal leakage safeguards and snapshot capture workflow implemented; real snapshot holdout not collected.
- **Objective:** Establish a promotion-safe backtest for `participation_state_hybrid` without terminal-metadata or delayed-performance leakage.
- **Acceptance:** Verified pre-deadline snapshot for every holdout Gameweek; baseline comparison; xP/xMins acceptance gate; default promotion only after all gates pass.

## Work Packet (SFDBN)

- **Status:** Checkpoint ready; validation blocked on snapshot history.
- **Files:** `features/builder.py`, `features/availability_snapshots.py`, `commands/backtest.py`, `.github/workflows/capture_availability_snapshot.yml`, regression tests.
- **Decisions:** Require immutable snapshots for promotion mode; reject missing/tampered packages; filter model fit and features by kickoff deadline; keep `metrics_component_hybrid` as baseline.
- **Blocked:** No historical pre-deadline snapshot packages exist; remote workflow has not been pushed or activated.
- **Next:** Commit checkpoint, push/enable snapshot workflow, collect holdout packages, run full comparison, promote only if acceptance gate passes.

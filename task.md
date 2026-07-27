# Active Task: Point-in-Time Participation Model Validation

- **Status:** In progress — `participation_state_hybrid` provisionally promoted; live confirmation not collected.
- **Objective:** Automate Candidate comparison and provisional promotion while preserving strict snapshot-backed validation.
- **Acceptance:** Historical Promotion Gate for registered Candidates; committed model-selection configuration and Promotion Evidence Record; two four-Gameweek Live Validation Windows for provisional confirmation; strict snapshot mode rejects missing or tampered packages.

## Work Packet (SFDBN)

- **Status:** Design agreed; core implementation in progress.
- **Files:** `config/model_selection.json`, `models/selection.py`, `backtesting/promotion.py`, `backtesting/model_evaluation.py`, `commands/compare_models.py`, `commands/evaluate_model_promotion.py`, `.github/workflows/evaluate_model_promotion.yml`, regression tests.
- **Decisions:** Automatic Historical Promotion for explicitly registered Candidates; committed Comparison Slate and Promotion Evidence Record; archive evidence may provisionally promote; snapshots support validated promotion; live reassessment report-only.
- **Blocked:** No historical pre-deadline snapshot packages exist; remote workflow has not been pushed or activated.
- **Next:** Push workflow, collect two Live Validation Windows, add live reassessment reporting.

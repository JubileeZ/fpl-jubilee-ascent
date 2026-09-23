# Active Task: CLI Champion Default and No Hit Setting

- **Status:** Done
- **Objective:** Make CLI commands default to active Model Champion, support --champion / champion aliases, add --no_hit to commands.solve, update README.
- **Acceptance:** Commands default to Champion; --no_hit sets weekly_hit_limit=0; self-healing config; README & tests pass.
- **Issue/Ticket:** User request

## Work Packet (SFDBN)

- **Status:** Done — delete this packet after Checkpoint
- **Files:** `models/__init__.py`, `models/selection.py`, `commands/run_model.py`, `commands/solve.py`, `commands/report.py`, `commands/decision_regret.py`, `commands/export_dashboard.py`, `README.md`, `docs/model_name.md`, `.cursor/rules/model-names.mdc`, `CONTEXT.md`, tests
- **Decisions:** Make model arg optional defaulting to Champion; add resolve_model_or_champion; add --no_hit/--no-hit flag; update docs and tests.
- **Blocked:** None
- **Next:** None

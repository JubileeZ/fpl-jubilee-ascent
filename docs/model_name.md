# Projection model names

CLI identifier is `BaseModel.name`, not the Python filename. `models.get_model(name)` scans `models/*.py` and returns the class whose `name` property matches.

Live Model Champion is `config/model_selection.json` `champion`. Transfer Plan always uses that Champion: dashboard **Solve scenarios** and `commands.solve`. Explorer Primary defaults to Champion; `--model` / the in-page Primary control may select any catalog name.

## Catalog

| Name | Module | Role | What it does |
|------|--------|------|----------------|
| `calibrated_matchup_hybrid` | `models/calibrated_matchup_hybrid.py` | Model Champion | Calibrated Matchup Share (shrunk delta s=0.40, Bayesian positional priors, decoupled saves/defcon) with mutually exclusive participation states and model-only penalty isolation. Not Dual-Vector Strength |
| `participation_state_hybrid` | `models/participation_state_hybrid.py` | Model Candidate | Event scoring from the hybrid, with mutually exclusive DNP / Start / Sub-in minutes |
| `metrics_component_hybrid` | `models/metrics_component_hybrid.py` | Catalog | Calibrated Event Component reconstruct through the scoring matrix (ADR 0005 / 0007). Ancestor of participation; not a registered Model Candidate |
| `component_baseline` | `models/component_baseline.py` | Baseline | Per-90 Event Rates through the scoring matrix; Prior-Season Seed / Position-Price |
| `linear_baseline` | `models/linear_baseline.py` | Baseline | Rolling points × Modified FDR × availability; Cold-Start projects ~0 |

Fallback if `model_selection.json` missing: `calibrated_matchup_hybrid` (`models.DEFAULT_MODEL_NAME`). Unknown/retired Primary POST → Champion. Passing `--champion` or `"champion"` resolves dynamically to the active Champion.

## Commands that take a name

| Command | Argument | Default |
|---------|----------|---------|
| `uv run python -m commands.run_model [NAME]` | positional optional, `--model`, or `--champion` | Champion (`config/model_selection.json`) |
| `uv run python -m commands.backtest NAME` | positional | required |
| `uv run python -m commands.report` | `--model` optional or `--champion` | Champion (`config/model_selection.json`) |
| `uv run python -m commands.dashboard --model NAME` | `--model` optional | Champion; Primary for Explorer / Dream Team; Transfer Plan Scenarios stay Champion; `--models` exports a Comparison Slate |
| `uv run python -m commands.decision_regret` | `--model` optional or `--champion` | Champion (`config/model_selection.json`) |
| `uv run python -m commands.solve` | `--model` optional, `--champion`, `--no_hit` | Champion (`config/model_selection.json`); stale `data/user_settings.json` `datasource` is ignored |

Outputs: `data/<name>.csv` projections; `data/reports/top_picks_<name>.csv` from `commands.report`.

## Examples

```bash
uv run python -m commands.run_model --horizon 5
uv run python -m commands.solve --horizon 6 --no_hit
uv run python -m commands.report --horizon 5
uv run python -m commands.backtest metrics_component_hybrid --gw_range 20-30 --seed_season 2025-26
uv run python -m commands.dashboard --model participation_state_hybrid
```

`--seed_season` is required for Cold-Start backtests of seed-based models (`component_baseline`, `metrics_component_hybrid`, `participation_state_hybrid`). Evaluation season cannot be its own Prior-Season Seed.

## Adding a name

1. New file under `models/` (not `base.py` / `__init__.py`).
2. Subclass `BaseModel`; `name` property is the CLI string (snake_case, unique).
3. `predict` returns ProjectionContract rows: `player_id`, `fixture_id`, `gameweek_id`, `projected_points`, `projected_minutes`.
4. Add the name to this catalog table.
5. Promotion into Champion / Comparison Slate is `config/model_selection.json`, not discovery.

Vocabulary: Model Champion, Model Candidate, Primary Projection Model in `CONTEXT.md`.

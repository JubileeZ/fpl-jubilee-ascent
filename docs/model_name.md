# Projection model names

CLI identifier is `BaseModel.name`, not the Python filename. `models.get_model(name)` scans `models/*.py` and returns the class whose `name` property matches.

Live Model Champion is `config/model_selection.json` `champion`. Transfer Plan always uses that Champion: dashboard **Solve scenarios** and `commands.solve`. Explorer Primary defaults to Champion; `--model` / the in-page Primary control may select any catalog name.

## Catalog

| Name | Module | Role | What it does |
|------|--------|------|----------------|
| `learned_start_challenger` | `models/learned_start_challenger.py` | Model Champion | `multi_feature_assist_challenger` + ridge-logistic learned p_start (lags/minutes/since-start/position/club share; GW ≥ 5; per-GW start mass rescaled to `multi_feature_assist_challenger` total, delta to/from p_dnp) + bonus pool weighted by P(60+). Promoted 2026-09-28 (ADR 0050, gate ADR 0049). Evidence `docs/research/dual-lane-candidate-search/candidate_gate.csv` |
| `multi_feature_assist_challenger` | `models/multi_feature_assist_challenger.py` | Model Candidate | `face_value_challenger` with multi-feature assist rate: ridge Poisson GLM (target Official xA, λ 10) over as-of xA/90, creativity/90, opponent xG conceded, own-team xG, home; trained on current-season history each predict; <3 history GWs → `face_value_challenger` assists. Promoted 2026-09-28 (ADR 0048); former Champion, displaced by `learned_start_challenger` (ADR 0050). Evidence `docs/research/multi-feature-event-rate` |
| `face_value_challenger` | `models/face_value_challenger.py` | Model Candidate | `hold_chase_challenger` with face-value xG/xA attack (no in-season weight refit), minute-pooled goal finishing offset (shrink 1800 min), mid-range start shrink k=0.15. Former Champion (ADR 0045); stays on Comparison Slate |
| `hold_chase_challenger` | `models/hold_chase_challenger.py` | Catalog | `calibrated_matchup_hybrid` plus start-persistence participation, top-end ordering emphasis, relaxed hard-fixture defense. Former Champion; displaced from Comparison Slate by `learned_start_challenger` promotion (2026-09-28) |
| `goals_path_challenger` | `models/goals_path_challenger.py` | Catalog | Goals-path Candidate (#111/#116): `hold_chase_challenger` without xG sharp/ceiling tilt; data-driven `goal_weights` scale. Parent of flip Candidate; not on Comparison Slate |
| `defence_link_challenger` | `models/defence_link_challenger.py` | Catalog | Flip-path Candidate (#117/#118/#119): `goals_path_challenger` plus post-link `k_cs`/`k_gc`. Displaced from Comparison Slate by `multi_feature_assist_challenger` (2026-09-28) |
| `bonus_arm_challenger` | `models/bonus_arm_challenger.py` | Catalog | Bonus-arm Candidate (#127/#129): `defence_link_challenger` plus data-driven `_XBPS_WEIGHTS` + `_BONUS_SOFTMAX_T`. Displaced from Comparison Slate by `face_value_challenger` (2026-09-28) |
| `calibrated_matchup_hybrid` | `models/calibrated_matchup_hybrid.py` | Catalog | Calibrated Matchup Share (shrunk delta s=0.40, Bayesian positional priors, decoupled saves/defcon) with mutually exclusive participation states and model-only penalty isolation. Not Dual-Vector Strength. Displaced from Comparison Slate by #119 |
| `participation_state_hybrid` | `models/participation_state_hybrid.py` | Catalog | Event scoring from the hybrid, with mutually exclusive DNP / Start / Sub-in minutes. Displaced from Comparison Slate by #130 |
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

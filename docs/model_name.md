# Projection model names

CLI identifier is `BaseModel.name`, not the Python filename. `models.get_model(name)` scans `models/*.py` and returns the class whose `name` property matches.

Live Model Champion is `config/model_selection.json` `champion`. Transfer Plan always uses that Champion: dashboard **Solve scenarios** and `commands.solve`. Explorer Primary defaults to Champion; `--model` / the in-page Primary control may select any catalog name.

## Catalog

| Name | Module | Role | What it does |
|------|--------|------|----------------|
| `def_xg_shrink_challenger` | `models/def_xg_shrink_challenger.py` | Model Champion | `learned_start_challenger` + DEF xG/90 shrunk to as-of DEF mean with 2400 pseudo-minutes (others 360); applied as ratio on `per90_xg` (decay 0.95). Idea ATK-04. Promoted 2026-10-01 (ADR 0055): dev +0.793 P 0.944, 2024-25 +0.594 P 0.863 under ADR 0054 legal XI eval. Evidence `docs/research/formation-eval-retest/candidate_gate.csv` |
| `club_def_prior_challenger` | `models/club_def_prior_challenger.py` | Model Candidate | `learned_start_challenger` + DEF xG/90 (360 pseudo-min, decay 0.95) shrunk toward as-of club x DEF pooled xG/90 (itself shrunk to DEF mean, 5 matches) instead of DEF mean; ratio on `per90_xg`. Idea ATK-05. Promoted 2026-09-29 (ADR 0051); displaced by `def_xg_shrink_challenger` (ADR 0055). Evidence `docs/research/component-model-ideas/candidate_gate.csv` |
| `cs_exposure_challenger` | `models/cs_exposure_challenger.py` | Catalog | `club_def_prior_challenger` + CS exposure over 60+ starts: GK and DEF clean-sheet exposure uses as-of player mean start minutes given >=60 minutes, shrunk to 85.0 min with K=4 starts. Idea DEF-02. Dev PASS, confirm (2024-25) FAIL; not on Comparison Slate. Evidence `docs/research/component-model-ideas/candidate_gate.csv` |
| `schedule_congestion_challenger` | `models/schedule_congestion_challenger.py` | Catalog | `club_def_prior_challenger` + schedule-congestion start shift: logit shift (-0.2) on learned p_start for fixtures occurring <3.5 days after previous kickoff. Idea MIN-07. Dev PASS; not on Comparison Slate. Evidence `docs/research/component-model-ideas/candidate_gate.csv` |
| `learned_start_challenger` | `models/learned_start_challenger.py` | Model Candidate | `multi_feature_assist_challenger` + ridge-logistic learned p_start (lags/minutes/since-start/position/club share; GW ≥ 5; per-GW start mass rescaled to `multi_feature_assist_challenger` total, delta to/from p_dnp) + bonus pool weighted by P(60+). Promoted 2026-09-28 (ADR 0050, gate ADR 0049); displaced by `club_def_prior_challenger` (ADR 0051). Evidence `docs/research/dual-lane-candidate-search/candidate_gate.csv` |
| `asymmetric_finishing_challenger` | `models/asymmetric_finishing_challenger.py` | Catalog | `learned_start_challenger` + asymmetric goal finishing shrinkage: residual = goals - xG, K_pos=1500 (form/skill), K_neg=3000 (faster regression to mean for cold streaks). Dev PASS, confirm (2024-25) FAIL; not on Comparison Slate. Evidence `docs/research/asymmetric-finishing-challenger/candidate_gate.csv` |
| `multi_feature_assist_challenger` | `models/multi_feature_assist_challenger.py` | Catalog | `face_value_challenger` with multi-feature assist rate: ridge Poisson GLM (target Official xA, λ 10) over as-of xA/90, creativity/90, opponent xG conceded, own-team xG, home; trained on current-season history each predict; <3 history GWs → `face_value_challenger` assists. Promoted 2026-09-28 (ADR 0048); former Champion; left Comparison Slate 2026-10-01 (ADR 0055, max 2 Candidates) |
| `face_value_challenger` | `models/face_value_challenger.py` | Catalog | `hold_chase_challenger` with face-value xG/xA attack (no in-season weight refit), minute-pooled goal finishing offset (shrink 1800 min), mid-range start shrink k=0.15. Former Champion (ADR 0045); left Comparison Slate 2026-09-29 (ADR 0051, max 2 Candidates) |
| `hold_chase_challenger` | `models/hold_chase_challenger.py` | Catalog | `calibrated_matchup_hybrid` plus start-persistence participation, top-end ordering emphasis, relaxed hard-fixture defense. Former Champion; displaced from Comparison Slate by `learned_start_challenger` promotion (2026-09-28) |
| `goals_path_challenger` | `models/goals_path_challenger.py` | Catalog | Goals-path Candidate (#111/#116): `hold_chase_challenger` without xG sharp/ceiling tilt; data-driven `goal_weights` scale. Parent of flip Candidate; not on Comparison Slate |
| `position_goals_challenger` | `models/position_goals_challenger.py` | Catalog | Position-split goals: FWD keeps hold-chase sharp and full goal weights; other positions use goals-path scale and identity xG. Ceiling tilt on all positions. Not on Comparison Slate |
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

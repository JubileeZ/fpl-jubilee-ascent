# Historical Promotion Gate plumbing (#114)

**Updated**: 2026-09-25T22:30:00+07:00  
**Data stamp**: code + evidence opened 2026-09-25 (Champion apply evidence `20260924T170031Z`)  
**Status**: Active — research answer for wayfinder #114  
**Purpose**: Inventory what must be true in-repo for a new Model Candidate to run the Historical Promotion Gate on **2025-26** (Blended primary, Realized/Process guardrails) and name gaps that block a goals-path Candidate today.  
**Scope**: Facts from code/docs/evidence only. Not Candidate design. Not product changes.  
**Related**: [ADR 0044](../../adr/0044-blended-eval-target-promotion-primary.md) · [Eval canon](../INDEX.md) · [model_name.md](../../model_name.md) · [component-gap note](champion-component-gap.md) · map [#110](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/110) · ticket [#114](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/114)

## Sources

- `commands/evaluate_model_promotion.py`, `commands/compare_models.py`
- `backtesting/promotion.py`, `backtesting/model_evaluation.py`
- `models/selection.py`, `models/__init__.py`, `docs/model_name.md`
- `config/model_selection.json`
- `CONTEXT.md` (Candidate Registration / Admission / Historical Promotion Gate)
- `docs/research/INDEX.md` Eval canon; `docs/adr/0044-blended-eval-target-promotion-primary.md`
- Hold-chase apply evidence: `data/reports/promotion_evidence/20260924T170031Z-hold_chase_challenger.{json,md}`
- Prior dry-run recipe (commit `1049432` work packet): `--gw_range 1-38 --data_dir data/archive/2025-26/processed --seed_season 2024-25 --season 2025-26`
- Archives present: `data/archive/2025-26/processed`, `data/archive/2024-25/processed`
- Registered names today: `calibrated_matchup_hybrid`, `component_baseline`, `hold_chase_challenger`, `linear_baseline`, `metrics_component_hybrid`, `participation_state_hybrid`

## Checklist — required steps for a new Candidate on the 2025-26 gate

### 1. Catalog registration (discovery)

1. Add `models/<name>.py` subclassing `BaseModel` with unique snake_case `name`.
2. `predict` returns ProjectionContract rows (`player_id`, `fixture_id`, `gameweek_id`, `projected_points`, `projected_minutes`).
3. Add catalog row in `docs/model_name.md` (Role = Model Candidate when on slate).
4. Confirm discovery: `models.list_model_names()` / `get_model(<name>)` — no separate registry file.

Authority: `docs/model_name.md` “Adding a name”; `models/__init__.py` `_iter_registered_models`.

### 2. Comparison Slate admission (`config/model_selection.json`)

1. Place `<name>` in `candidates` (max **2**; `models/selection.py` `_MAX_CANDIDATES`).
2. Do **not** hand-edit `champion` for a gate flip — Champion write is `--apply` only (`promote_candidate`).
3. When slate already has two Candidates (**current state**): glossary **Candidate Admission** requires beating an existing Candidate and replacing that seat; Champion stays. Helper `replace_candidate()` exists in `backtesting/model_evaluation.py` but has **no CLI**. Practical admission today = committed JSON seat swap (or library call) so the new name appears in `candidates`, then run the Champion gate.

Current slate (opened this session):

```json
"champion": "hold_chase_challenger",
"candidates": ["calibrated_matchup_hybrid", "participation_state_hybrid"],
"promotion_status": "provisional"
```

Hold-chase precedent: slate had one open seat; registration was append to `candidates` (commit `1049432`). Goals-path does not have that free seat.

Authority: `CONTEXT.md` Candidate Registration / Admission / Comparison Slate; `models/selection.py`.

### 3. Run Historical Promotion Gate (Blended + guardrails)

Command:

```bash
# Dry-run (no config write, no evidence files)
uv run python -m commands.evaluate_model_promotion \
  --gw_range 1-38 \
  --data_dir data/archive/2025-26/processed \
  --seed_season 2024-25 \
  --season 2025-26

# Apply (writes slate if PASS + Promotion Evidence Record)
uv run python -m commands.evaluate_model_promotion \
  --gw_range 1-38 \
  --data_dir data/archive/2025-26/processed \
  --seed_season 2024-25 \
  --season 2025-26 \
  --apply
```

Facts:

| Item | In-repo behavior |
|------|------------------|
| Dry-run flag | **No** `--dry-run`. Dry-run = omit `--apply`. |
| Primary eval target | Hardcoded `eval_target="blended_points"` in `_run_model` (ADR 0044). No `--eval_target` on this CLI (unlike `commands.backtest`). |
| Realized / Process guardrails | `compare_to_reference` builds `reference_windows` for `actual_points` + `process_points` MAE vs Champion; regression fails gate. |
| Other Champion guardrails | xMins MAE ≤ Champion; \|bias\| ≤ Champion; Spearman ≥ Champion (`metrics_meet_guardrails`). |
| Pass rule | Combined primary improve **and** ≥2/3 seasonal segments **and** all guardrails (`evaluate_historical_promotion_gate`). |
| Primary metric | `decision_regret` when informative, else `xp_mae` / MAE. |
| Models evaluated | Champion + every name in `candidates` (order); `--apply` promotes **first** passing Candidate only. |
| Read-only sibling | `commands.compare_models` — same blended walk-forward, no config/evidence write. |

Authority: `commands/evaluate_model_promotion.py`; `backtesting/model_evaluation.py` `compare_to_reference`; `backtesting/promotion.py`; ADR 0044; INDEX Eval canon.

### 4. Evidence report paths

- Directory: `data/reports/promotion_evidence/`
- Files (only when `--apply`): `{UTC stamp}-{selection_after.champion}.json` and `.md`
- Record fields: evaluated_at, evaluation_season, git_commit, selection_before/after, per-candidate passed / eval_target / primary_metric / delta / segment_wins / guardrails / reasons / snapshot_backed
- Archive-only runs set `snapshot_backed=false` → `promotion_status` stays **`provisional`** (ADR 0010 / CONTEXT Provisional Historical Promotion)
- Latest hold-chase apply: `data/reports/promotion_evidence/20260924T170031Z-hold_chase_challenger.{json,md}` — season `2025-26`, `eval_target: blended_points`, challenger PASS / `participation_state_hybrid` FAIL

Dry-run prints PASS/FAIL to stdout only; **does not** write evidence.

### 5. Data prerequisites (present today)

- Evaluation archive: `data/archive/2025-26/processed`
- Prior-Season Seed: `data/archive/2024-25/processed` via `--seed_season 2024-25` (Cold-Start / ADR 0024 clock)
- Optional strict snapshots: `--require_snapshots` + `--snapshot_root` + `--season` (validated path; live Availability Snapshots still absent per current-state)

## Gaps that block a goals-path Candidate today

1. **No goals-path model in catalog** — diagnosis names crown `xp_goals` / `structural` (`component_gap_summary.csv`); no `models/*.py` goals Candidate; lever set still open (#111). Gate cannot run on a name that `get_model` cannot resolve.

2. **Comparison Slate seats full (2/2)** — cannot Candidate-Register without displacing `calibrated_matchup_hybrid` or `participation_state_hybrid`. Which seat + Admission bar = open grilling (#112).

3. **Candidate-vs-Candidate Admission not automated** — `evaluate_model_promotion` / `compare_models` only gate Candidates **vs Champion**. Glossary Admission (beat existing Candidate, replace seat) has library helper `replace_candidate` but **no command**. Seat change is a committed config edit before the Champion gate can see the new name.

4. **Design not plumbing for a class-based Candidate** — if goals arm ships as a registered `BaseModel` (hold-chase pattern), WalkforwardConfig already supports blended gate. Contrast: fixture-downside-scale note still blocked because variant lives in builder params without WalkforwardConfig expression — that is a **different** gap, not goals-path unless goals reuses that pattern.

5. **Not blockers for plumbing itself** (named so they are not mistaken for gate gaps): Extra residual gate bar (#115); CS-link arm (#113); Live Validation Windows; Availability Snapshots (provisional is allowed); INDEX wording `--eval_target blend` vs hardcoded promotion CLI.

## Resolution comment (paste for #114)

Historical Promotion Gate plumbing for a new Candidate on **2025-26** is already wired: register a `BaseModel` + `docs/model_name.md` row, put the name in `config/model_selection.json` `candidates` (max 2), then dry-run / `--apply` via `uv run python -m commands.evaluate_model_promotion --gw_range 1-38 --data_dir data/archive/2025-26/processed --seed_season 2024-25 --season 2025-26` (omit `--apply` for dry-run; no separate `--dry-run` flag). Primary is hardcoded Blended (`blended_points`, ADR 0044); Realized + Process MAE plus xMins/\|bias\|/Spearman are Champion guardrails; `--apply` writes `data/reports/promotion_evidence/{UTC}-{champion}.{json,md}` (hold-chase precedent `20260924T170031Z-hold_chase_challenger.*`). Goals-path is blocked today by (1) no goals Candidate implementation/catalog name, (2) slate already full so Admission requires replacing an existing Candidate, and (3) Candidate-vs-Candidate Admission not exposed as a CLI—only Champion gate + manual/`replace_candidate` seat swap. Full note: `docs/research/champion-component-gap/gate-plumbing-114.md`.

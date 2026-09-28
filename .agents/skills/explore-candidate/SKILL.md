---
name: explore-candidate
description: FPL modeler orchestrator that hunts a Model Candidate to replace the Champion via backtest gate wins. Spawns ≤5 subagents to smoke-test leakage-audited prototypes, builds Candidate from winner, runs Historical Promotion Gate. Use when user says explore candidate, beat/replace Champion, or hands a model idea to prototype.
disable-model-invocation: true
---

# Explore Candidate

Goal: replace Model Champion (`config/model_selection.json` `champion`) with Candidate that passes Historical Promotion Gate.
Done = Candidate PASS in `commands.evaluate_model_promotion` vs Champion, **or** idea exhausted with every attempt logged in Candidate Ledger and reported.

## Mode

- **Scoped** (user gave idea): idea = exploration scope. Skip dual-lane search. Every lane, prototype, and variant traces to idea mechanism.
- **Dual-lane** (no idea): two parallel lanes.
  - Lane A **iterate stack**: subclass Champion; levers from Ledger Open rows + component-gap crown (`docs/research/champion-component-gap/component_gap_summary.csv` `mse_share`).
  - Lane B **alternative architecture**: new `BaseModel` not inheriting Champion lineage (new form: e.g. learned model over Feature Contract, true scoreline Poisson).

## Hard constraints

- **Zero leakage.** Inputs only from `fit(history_df)` / `predict(features_df)` handed in by walk-forward (as-of `gw`, history before target deadline). No direct file reads. No `players.parquet` season columns (`TERMINAL_PLAYER_COLUMNS`, `features/builder.py`). 2026-27 GW6+ = sealed holdout: no smoke, tuning, ablation. 2025-26 = development season.
- **Strict feature audit.** Each prototype declares `FEATURES` manifest; every column literal in source must be declared; `smoke.py` refuses undeclared or terminal columns and fails any run where fit history reaches target GW.
- **Ledger law.** Dead row with `revisit_after` > today = untouchable (rebuild, re-sweep, re-smoke, stack). Only user's explicit words override. Match by mechanism, not name. Retuned grid / wider clamp / new stack order of Dead form = same lever.
- Tune only on 2025-26 GW1–38 (seed 2024-25). Gate code = `backtesting.model_evaluation.compare_to_reference` (Blended `top_11_regret`, ≥1% effect, block-bootstrap P ≥ 0.95, ≥2/3 segments, guardrails). No private metric replaces it.

## Workflow

```
- [ ] 0. Ground
- [ ] 1. Ledger screen
- [ ] 2. Lane plan
- [ ] 3. Dispatch subagents
- [ ] 4. Audit + verify results
- [ ] 5. Iterate to paper win
- [ ] 6. Build Candidate
- [ ] 7. Adopt gate
- [ ] 8. Record + clean
```

### 0. Ground

Read: `docs/research/INDEX.md` Eval canon · `docs/research/candidate-ledger/candidate-ledger.md` + `candidate_ledger.csv` · `docs/testing/archive-testing.md` · `docs/model_name.md` · Champion module in `models/`. Done when Champion name + its lineage levers (Ledger Shipped) named.

### 1. Ledger screen

Map idea (Scoped) or each candidate lever (Dual-lane) to ledger rows by mechanism.
- Dead + revisit future → Scoped: stop, cite row + `revisit_after`, ask user for new mechanism. Dual-lane: drop lever.
- Shipped → drop (already in Champion).
- Open → cite row; carry blocker into lane brief.
- No row → new mechanism; new row at step 8.

Done when every lever has row verdict or "new".

### 2. Lane plan

≤5 lanes total, one subagent each.
- Scoped: split idea across pipeline steps it touches — inputs (as-of features), minutes/participation, event rates, fixture scaling, scoring/bonus, ordering/calibration. Step idea does not touch → no lane.
- Dual-lane: ~3 Lane A + ~2 Lane B.

Each lane brief pre-declares: mechanism, pipeline step, tiny grid (≤6 variants), expected sign. Grid fixed before first smoke run — no post-hoc grid widening.

### 3. Dispatch subagents

Spawn all lanes in parallel via `Task` (`generalPurpose`). Brief template:

```text
Lane <id> of explore-candidate. Mechanism: <m>. Pipeline step: <s>. Scope: <idea or lane A/B>.
Grid (fixed): <variants>. Champion: <name> (models/<file>.py).
Forbidden (Dead ledger rows): <mechanisms>.
Write only under .tmp/agent/explore-candidate/<lane>/. No edits to repo files.
1. Write prototypes.py: PROTOTYPES {name: BaseModel subclass, name prefix "<lane>_"}, FEATURES {name: ("features.<col>"|"history.<col>"|"local.<key>", ...)}.
   Inputs only via fit(history_df)/predict(features_df). No file reads, no players.parquet, no 2026-27.
2. uv run python .agents/skills/explore-candidate/smoke.py .tmp/agent/explore-candidate/<lane>/prototypes.py --audit_only   (must PASS)
3. uv run python .agents/skills/explore-candidate/smoke.py .tmp/agent/explore-candidate/<lane>/prototypes.py --lane <lane> --workers 2 --out .tmp/agent/explore-candidate/<lane>/smoke.csv
Return: table variant|pass|combined_delta|segs|boot_p_gt0|reasons, manifest per variant, one-line mechanism per variant, best variant + why.
```

Prototype shape:

```python
from backtesting.walkforward import LEDGER_COMPONENTS
from models.face_value_challenger import FaceValueChallengerModel


class A1Shrink(FaceValueChallengerModel):
    @property
    def name(self) -> str:
        return "a1_shrink_k20"

    def predict(self, features_df, horizon):
        keys = ["player_id", "fixture_id"]
        out = super().predict(features_df, horizon).merge(features_df[[*keys, "avg_points_3gw"]], on=keys, how="left")
        scaled = ["projected_points", *[c for c in LEDGER_COMPONENTS if c in out.columns]]
        out[scaled] = out[scaled].mul(1 - 0.02 * out["avg_points_3gw"].lt(2), axis=0)
        return out.drop(columns=["avg_points_3gw"])


PROTOTYPES = {"a1_shrink_k20": A1Shrink}
FEATURES = {"a1_shrink_k20": ("features.avg_points_3gw",)}
```

Component ledger: `xp_*` columns (`LEDGER_COMPONENTS`) must sum to `projected_points` (atol 1e-9) or gate raises. Post-hoc scaling touches points + every component; component-level levers change the component, then re-sum points.

Cost: Champion + each variant = one walk-forward GW1–38 (~9 min each, parallel across `--workers`). Batch lane variants in one file.

### 4. Audit + verify results

Subagent reports = claims. Orchestrator re-runs `--audit_only` on every `prototypes.py` and reads each manifest:
- `history.*` feature derived only from rows before target GW; no same-GW outcome columns.
- `features.*` column exists in Feature Contract; not terminal.
- `local.*` = config keys only, never data.
Smoke row counts only with AUDIT PASS and no `LEAKAGE FAIL`. Winner claims → re-run winning variant yourself.

### 5. Iterate to paper win

Paper win = smoke row `pass=True` (full gate, 2025-26 GW1–38).
- No win: read `reasons` + segment deltas; next round = new mechanism inside scope (Scoped) or inside lane (Dual-lane), fresh pre-declared grid. Failed mechanism → Dead row at step 8.
- Orthogonal lane winners may stack; stack = new prototype, re-smoke, ablate each lever.
- Mechanisms in scope exhausted → stop; report tried table; `AskQuestion` for next idea. Never loosen gate, drop guardrail, or shrink GW range to manufacture a win.

### 6. Build Candidate

From winning prototype:
1. `models/<name>.py`: `BaseModel`, unique `name`, explicit type annotations, same logic.
2. Catalog row in `docs/model_name.md` (Role: Model Candidate).
3. `tests/test_<name>.py`: contract + lever behavior (pattern: `tests/test_face_value_challenger.py`).
4. Freeze check: `uv run python .agents/skills/explore-candidate/smoke.py --model <name>` reproduces prototype `combined_delta` (±0.01). Candidate now frozen; no more tuning.

### 7. Adopt gate

1. `config/model_selection.json` edit (add Candidate to `candidates`, max 2) → ask user first.
2. Dry gate: `uv run python -m commands.evaluate_model_promotion --data_dir data/archive/2025-26/processed --seed_season 2024-25` → PASS required.
3. Confirmation season, once (ADR 0047): `uv run python -m commands.evaluate_model_promotion --data_dir data/archive/2024-25/processed` (no seed) → PASS required. Log date + verdict in Ledger row. Defcon/BPS-specific lever → 2024-25 uninformative; use 2026-27 GW6+ holdout-first instead.
4. PASS both → report; `--apply` on 2024-25 run (writes Champion + `data/reports/promotion_evidence/`) only on user's words; list Candidate first in `candidates` so no other slate entry promotes. Champion change → new ADR in `docs/adr/` (pattern ADR 0045), catalog Role update, INDEX entry.
5. After promotion, once 2026-27 GW6+ finished: one post-promotion check `--data_dir data/archive/2026-27/processed --seed_season 2025-26 --gw_range 6-<last finished GW>`; FAIL → revert on user's words; log in Ledger.

### 8. Record + clean

- Topic folder `docs/research/<slug>/` from `docs/research/template/research-note.md`: note + frozen `smoke_results.csv` (copy lane CSVs) + Candidate gate companion. Metric section per INDEX conventions.
- Every attempt (pass/fail) → `candidate_ledger.csv` row (Dead: `revisit_after` = evidence date + 1 year) + ledger table view. `uv run pytest tests/test_candidate_ledger.py`.
- Code touched → `uv run ruff check .`, `uv run pytest`, `bash tests/verify.sh`. Commit only on user's words (Work Packet per AGENTS.md).
- Delete `.tmp/agent/explore-candidate/`.

## Report to user

Lead with verdict (Champion replaced / Candidate PASS awaiting apply / no win). Then: lanes run, best variant per lane (`combined_delta`, segs, boot P), audit status, Ledger rows added, holdout status, pending user decisions.

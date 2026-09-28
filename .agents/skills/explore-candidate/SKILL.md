---
name: explore-candidate
description: FPL modeler orchestrator that hunts a Model Candidate to replace the Champion via backtest gate wins. Runs AFK as a /goal; spawns ≤5 subagents to smoke-test leakage-audited prototypes, builds Candidate from winner, gates it on dev + confirmation seasons, queues adoption for human. Use when user says explore candidate, beat/replace Champion, or hands a model idea to prototype.
disable-model-invocation: true
---

# Explore Candidate

Goal: replace Model Champion (`config/model_selection.json` `champion`) with Candidate that passes Historical Promotion Gate on both ADR 0047 seasons.

## Run contract (AFK by default)

Runs unattended (Ralph-style loop). Human enters only at Human Gates and Exit.

- **Arm goal.** First invocation in conversation, no goal active: call `CreateGoal` once (per `/goal` contract) with objective:
  `explore-candidate <scope or "dual-lane">: frozen Candidate passing Historical Promotion Gate on dev + confirm seasons via smoke.py, adoption queued in Human Queue — or scope exhausted with every attempt in Candidate Ledger. State: .agents/work-packets/explore-candidate-<slug>.md`
  Goal already active → skip. Then start step 0 same turn.
- **Disk = memory.** Chat is not state. Work Packet `.agents/work-packets/explore-candidate-<slug>.md` (from `.agents/work-packet.md.tmpl`) holds: mode, scope, current step, round, per-lane mechanism / grid / best smoke row, ledger verdicts, `## Human Queue`. Scratch `.tmp/agent/explore-candidate/` persists across iterations. Every invocation: packet exists → resume at its `Next`; else create. Update packet after every step; iteration ends with `Next` = exact next action.
- **Never block mid-run.** No `AskQuestion` before Exit. Decision needing human → append to `## Human Queue` (question · options · default taken · evidence path) → take default → continue. Harness/gate crash (traceback, not verdict) ≠ FAIL: queue traceback + command, no ledger verdict; blocks that step only.
- **Human Gates** (queue only; AFK never executes): `config/model_selection.json` edit · `commands.evaluate_model_promotion --apply` · Dead-row override · commit / push · Champion-change ADR acceptance (draft allowed, status Proposed).
- **Progress guard.** Lane closes after 2 consecutive rounds with no new best `combined_delta`. Mechanism already in lane CSVs or ledger never re-smoked. All lanes closed → Exit.
- **Exit.**
  - (a) Candidate frozen + dev PASS + confirm PASS → Human Queue holds adoption → goal complete.
  - (b) Scope exhausted, every attempt in ledger → goal complete (verdict: no win).
  - (c) Only Human Queue items remain (e.g. every scoped mechanism Dead) → BLOCKED; goal stays active.
  - At Exit: write report (template below) into packet + topic note; write packet id to `.agents/handoff-pointer`; run goal completion audit, `UpdateGoal complete` for (a)/(b); final turn presents Human Queue via `AskQuestion`.

## Mode

- **Scoped** (user gave idea): idea = exploration scope. Skip dual-lane search. Every lane, prototype, and variant traces to idea mechanism.
- **Dual-lane** (no idea): two parallel lanes.
  - Lane A **iterate stack**: subclass Champion; levers from Ledger Open rows + component-gap crown (`docs/research/champion-component-gap/component_gap_summary.csv` `mse_share`).
  - Lane B **alternative architecture**: new `BaseModel` not inheriting Champion lineage (new form: e.g. learned model over Feature Contract, true scoreline Poisson).

## Seasons (never hard-code)

Roles resolve from `data/archive/YYYY-YY` each run: `uv run python .agents/skills/explore-candidate/smoke.py --show_seasons`. Complete = every fixture finished; seed = prior archive season if present.
- **dev** = latest complete season. Selection + tuning here only.
- **confirm** = second-latest complete season (ADR 0047). One run per frozen Candidate, never tuned on.
- **holdout** = incomplete live season. Sealed (ADR 0046 GW6+): no smoke, tuning, ablation; post-promotion check only.

Record resolved names in packet at step 0; roles roll forward automatically when a season completes. Commands, prototypes, and briefs name roles, never years.

## Hard constraints

- **Zero leakage.** Inputs only from `fit(history_df)` / `predict(features_df)` handed in by walk-forward (as-of `gw`, history before target deadline). No direct file reads. No `players.parquet` season columns (`TERMINAL_PLAYER_COLUMNS`, `features/builder.py`). Prototype source holds no season literal (audit refuses). Holdout sealed.
- **Strict feature audit.** Each prototype declares `FEATURES` manifest; every column literal in source must be declared; `smoke.py` refuses undeclared or terminal columns and fails any run where fit history reaches target GW.
- **Ledger law.** Dead row with `revisit_after` > today = untouchable (rebuild, re-sweep, re-smoke, stack). Only user's explicit words override. Match by mechanism, not name. Retuned grid / wider clamp / new stack order of Dead form = same lever.
- Gate code = `backtesting.model_evaluation.compare_to_reference` (Blended `top_11_regret`, delta > 0 (no min effect), block-bootstrap P ≥ 0.60 dev + confirm per ADR 0049, ≥2/3 segments, guardrails). No private metric replaces it. Never loosen gate, drop guardrail, or shrink GW range to manufacture a win.

## Workflow

```
- [ ] 0. Ground (arm goal, packet)
- [ ] 1. Ledger screen
- [ ] 2. Lane plan
- [ ] 3. Dispatch subagents
- [ ] 4. Audit + verify results
- [ ] 5. Iterate to paper win
- [ ] 6. Build Candidate
- [ ] 7. Adopt gate
- [ ] 8. Record + Exit
```

### 0. Ground

Arm goal + create/resume packet (Run contract). Run `smoke.py --show_seasons`; record roles in packet. Read: `docs/research/INDEX.md` Eval canon · `docs/research/candidate-ledger/candidate-ledger.md` + `candidate_ledger.csv` · `docs/testing/archive-testing.md` · `docs/model_name.md` · ADR 0046 + 0047 · Champion module in `models/`. Done when Champion name + its lineage levers (Ledger Shipped) in packet.

### 1. Ledger screen

Map idea (Scoped) or each candidate lever (Dual-lane) to ledger rows by mechanism.
- Dead + revisit future → Human Queue "override Dead row <lever>?" (default: no). Drop mechanism; continue with remaining in-scope mechanisms. None left → Exit (c).
- Shipped → drop (already in Champion).
- Open → cite row; carry blocker into lane brief.
- No row → new mechanism; new row at step 8.

Done when every lever has row verdict or "new" in packet.

### 2. Lane plan

≤5 lanes total, one subagent each.
- Scoped: split idea across pipeline steps it touches — inputs (as-of features), minutes/participation, event rates, fixture scaling, scoring/bonus, ordering/calibration. Step idea does not touch → no lane.
- Dual-lane: ~3 Lane A + ~2 Lane B.

Each lane brief pre-declares: mechanism, pipeline step, tiny grid (≤6 variants), expected sign. Grid fixed in packet before first smoke run — no post-hoc grid widening.

### 3. Dispatch subagents

Spawn all lanes in parallel via `Task` (`generalPurpose`). Brief template:

```text
Lane <id> of explore-candidate. Mechanism: <m>. Pipeline step: <s>. Scope: <idea or lane A/B>.
Grid (fixed): <variants>. Champion: <name> (models/<file>.py).
Forbidden (Dead ledger rows): <mechanisms>.
Write only under .tmp/agent/explore-candidate/<lane>/. No edits to repo files. Unattended: never ask user; report blockers.
1. Write prototypes.py: PROTOTYPES {name: BaseModel subclass, name prefix "<lane>_"}, FEATURES {name: ("features.<col>"|"history.<col>"|"local.<key>", ...)}.
   Inputs only via fit(history_df)/predict(features_df). No file reads, no players.parquet, no season literals.
2. uv run python .agents/skills/explore-candidate/smoke.py .tmp/agent/explore-candidate/<lane>/prototypes.py --audit_only   (must PASS)
3. uv run python .agents/skills/explore-candidate/smoke.py .tmp/agent/explore-candidate/<lane>/prototypes.py --lane <lane> --workers 2 --out .tmp/agent/explore-candidate/<lane>/smoke.csv
Return: table variant|pass|combined_delta|segs|boot_p_gt0|reasons, manifest per variant, one-line mechanism per variant, best variant + why.
```

Prototype shape (Champion class = whatever `config/model_selection.json` names; example uses current one):

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

Cost: Champion + each variant = one full-season walk-forward (~9 min each, parallel across `--workers`). Batch lane variants in one file.

### 4. Audit + verify results

Subagent reports = claims. Orchestrator re-runs `--audit_only` on every `prototypes.py` and reads each manifest:
- `history.*` feature derived only from rows before target GW; no same-GW outcome columns.
- `features.*` column exists in Feature Contract; not terminal.
- `local.*` = config keys only, never data.
Smoke row counts only with AUDIT PASS and no `LEAKAGE FAIL`. Winner claims → re-run winning variant yourself. Record verified rows in packet.

### 5. Iterate to paper win

Paper win = verified smoke row `pass=True` (full gate, dev season, full season range).
- No win: read `reasons` + segment deltas; next round = new mechanism inside scope (Scoped) or inside lane (Dual-lane), fresh pre-declared grid. Failed mechanism → Dead row at step 8. Apply progress guard.
- Orthogonal lane winners may stack; stack = new prototype, re-smoke, ablate each lever.
- All lanes closed → step 8, Exit (b).

### 6. Build Candidate

From winning prototype:
1. `models/<name>.py`: `BaseModel`, unique `name`, explicit type annotations, same logic.
2. Catalog row in `docs/model_name.md` (Role: Model Candidate).
3. `tests/test_<name>.py`: contract + lever behavior (pattern: `tests/test_face_value_challenger.py`).
4. Freeze check: `uv run python .agents/skills/explore-candidate/smoke.py --model <name> --out docs/research/<slug>/candidate_gate.csv` reproduces prototype `combined_delta` (±0.01) = dev gate row. Candidate now frozen; no more tuning.

### 7. Adopt gate

1. Dev PASS = step 6 row.
2. Confirmation (ADR 0047), once: `uv run python .agents/skills/explore-candidate/smoke.py --model <name> --season confirm --out docs/research/<slug>/candidate_gate.csv`. Harness refuses repeat runs, prototypes, partial GW range, scratch `--out`. Ledger `result` records `confirm <confirm season> PASS|FAIL <delta> <segs> boot P <p>` (harness reads this to block repeats).
   - FAIL → Dead ledger row; back to step 5 if scope remains, else Exit (b).
   - Lever depends on scoring rule absent in confirm season (e.g. defcon points, BPS weights) → skip confirm (uninformative); Human Queue "holdout-first per ADR 0046; wait holdout GW6+"; Exit (c).
3. PASS both → Human Queue adoption bundle:
   - add Candidate first in `config/model_selection.json` `candidates`;
   - `uv run python -m commands.evaluate_model_promotion --data_dir data/archive/<confirm season>/processed --confirmation --apply` — deterministic replay of same gate (bootstrap seed 0), not new look; verdict must match smoke confirm row;
   - draft ADR (status Proposed, pattern ADR 0045) + catalog Role update + INDEX entry;
   - post-promotion holdout check once holdout GW6+ finished (`--data_dir data/archive/<holdout season>/processed --seed_season <dev season> --gw_range 6-<last finished>`); FAIL → revert on user's words.

### 8. Record + Exit

- Topic folder `docs/research/<slug>/` from `docs/research/template/research-note.md`: note + frozen `smoke_results.csv` (concat lane CSVs) + `candidate_gate.csv`. Metric section per INDEX conventions.
- Every attempt (pass/fail) → `candidate_ledger.csv` row (Dead: `revisit_after` = evidence date + 1 year) + ledger table view. `uv run pytest tests/test_candidate_ledger.py`.
- Code touched → `uv run ruff check .`, `uv run pytest`, `bash tests/verify.sh`. Failures fixed before Exit.
- Delete `.tmp/agent/explore-candidate/` only at Exit (a)/(b); keep for (c).
- Exit per Run contract.

## Report

```markdown
**Verdict:** Candidate <name> PASS dev + confirm, adoption awaiting you | no win | BLOCKED on Human Queue
**Lanes:** <lane> · mechanism · best variant · combined_delta · segs · boot P
**Audit:** all prototypes AUDIT PASS, no LEAKAGE FAIL (or list)
**Ledger:** rows added/updated
**Human Queue:** numbered items with default taken + exact command
```

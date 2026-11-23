# Static goals and assists qualification

Standalone qualification of EXT-40 static controls reproduced under EXT-41. Fixed `lambda=0.03`. Each arm changes only its target Event Component. Both use Champion participation and the same native scoring ledger. [Early diagnostic](ext41-gw1-4-attack-screen.md)

**Disposition:** Zero Win-Both qualifiers. Goals demonstrated a historical regression and enters the Candidate Ledger with a 2027-11-24 revisit date. Assists missed the Development score requirement with an inconclusive interval.

## Goals

**2025–26 Development PASS.** Static goals finished at 2,172 net points versus Champion's 2,167. All 15 projection guards and all three segment floors passed. The independent GW1–7 audit matched forecast inputs and settled outcomes at all 14 model-origins. GW1–4 fixture forecasts and weekly net and hit scores reproduced the original diagnostic. [Development summary](prototypes/static_goals_a/s1/summary.json) · [Weekly scores](prototypes/static_goals_a/s1/paired_weekly_scores.csv) · [Projection guards](prototypes/static_goals_a/s1/projection_guards.csv) · [Prefix parity](prototypes/static_goals_a/s1_prefix_parity.csv)

**2024–25 Historical Filter FAIL.** Frozen static goals scored 2,161 net points against 2,299 for Champion, a loss of 138. All 14 applicable projection guards and both admitted GW1 parity checks passed. GW5–19 averaged −5.27 points per Gameweek against the −4.70 segment floor. The historical paired bootstrap interval was −8.55 to −0.13 points per Gameweek. [Filter summary](prototypes/static_goals_a/s2/summary.json) · [Weekly scores](prototypes/static_goals_a/s2/paired_weekly_scores.csv) · [Projection guards](prototypes/static_goals_a/s2/projection_guards.csv) · [Prefix parity](prototypes/static_goals_a/s2_prefix_parity.csv) · [Frozen selection](prototypes/static_goals_a/development_selection.json)

## Assists

**2025–26 Development FAIL.** Static assists finished at 2,157 against 2,167 for Champion, a loss of ten. All 15 projection guards, all three segment floors and all 14 admitted-prefix checks passed. GW1–4 fixture forecasts and net and hit scores reproduced exactly. The historical paired bootstrap interval was −2.34 to +1.24 points per Gameweek. The negative total ended qualification at Development. [Development summary](prototypes/static_assists_a/s1/summary.json) · [Weekly scores](prototypes/static_assists_a/s1/paired_weekly_scores.csv) · [Projection guards](prototypes/static_assists_a/s1/projection_guards.csv) · [Prefix parity](prototypes/static_assists_a/s1_prefix_parity.csv)

## Evidence and protocol

Certified rolling Strategic replay, six-Gameweek planning horizon, zero target gap, 600-second cap per solve. Independent ownership trajectories use the same neutral opening anchor and native chip calendar. Paired native FPL net points subtract hit costs. Qualification requires a positive net difference and all applicable projection and segment guards in both seasons. [Historical boundaries](../adr/0069-annual-rolling-validation-and-dual-tier-promotion.md) · [Qualification policy](../adr/0071-certified-solver-budget-and-milp-qualification-calibration.md)

Recomputed all three paired season results from 38 unique weekly rows per test. Hit counts in the paired score tables represent four FPL points per hit. Verified weekly gross-to-net reconciliation, checkpoint counts, reviewed source hashes and all independent prefix matches. Branch includes `origin/main` at `2dfdc1bf`. Historical replay protocol and Champion fingerprints still match. Repository suite passed 1,245 tests on the merged tree.

The 2024–25 Filter training panel uses only dated 2023–24 source receipts. It retains 10,033 examples per head from 36 source origins. GW1 had no eligible prior history and GW27 lacked an admissible fixture snapshot. Manifests and referenced bytes bind the cohort before either Filter run. Native assist targets for this source and destination reflect an inference from the published rule history. [Source origins](prototypes/static_attack_counts/evidence/filter_training_origins.json) · [Seed manifest](prototypes/static_attack_counts/evidence/filter_training_seed.json) · [Coverage](prototypes/static_attack_counts/evidence/filter_training_coverage.csv) · [2024–25 rules changes](https://www.premierleague.com/en/news/4059044) · [Assist rule example across the two seasons](https://www.premierleague.com/en/news/4199449) · [2025–26 rules changes](https://www.premierleague.com/en/news/4373187)

## Reproduction

Use repository root, Python 3.14, and pinned `uv.lock`. Rebuild admitted Dev inputs and original Arm A references before starting the common Champion replay.

```bash
export PYTHONPATH=.:docs/research/candidate-ideation
work="$PWD/.tmp/agent/explore-candidate/static-attack-counts"
uv run --locked python -m prototypes.ext_40.prepare "$work"
uv run --locked python -m prototypes.ext_41_preflight "$work"
uv run --locked python -m prototypes.ext_41.run "$work"
export STATIC_ATTACK_MIRROR_ROOT="$work/mirror"
uv run --locked python -c 'import os; from pathlib import Path; import historical_replay_inputs as inputs; import run_s1_replay as replay; inputs.MIRROR_ROOT = Path(os.environ["STATIC_ATTACK_MIRROR_ROOT"]); replay.main()' --work "$work"
```

Run one lane at a time. Compute `reviewed` from the exact, reviewed prototype file. Set `arm` to `goals_a` first and `assists_a` after the goals disposition.

```bash
prototype="docs/research/candidate-ideation/prototypes/static_${arm}/prototypes.py"
reviewed=$(sha256sum "$prototype" | cut -d ' ' -f 1)
uv run --locked python -m static_attack_qualification --work "$work" --arm "$arm" --reviewed-sha256 "$reviewed"
uv run --locked python -m compare_historical_replays --champion "$champion_run" --candidate "$candidate_run" --out "$work/$arm/s1"
```

Use the replay directories the qualification command prints. A Dev winner requires its frozen selection pin for the Filter. Rehydrate each pinned Filter source file by URL and SHA-256 under `$work/mirror`, preserving each `local_relpath`. Copy the two retained Filter training manifests into `$work` and set `STATIC_ATTACK_FILTER_SOURCE_ROOT="$work"`. Run the standard [frozen Filter commands](component-score-head.md#reproduction) for both arms and the independent prefix check. For a scratch mirror, set `MIRROR_ROOT` in `s2_historical_replay_inputs`, `audit_historical_prefix`, and `commands.run_stage_a_and_b` to `$work/mirror` before dispatching their respective runners.

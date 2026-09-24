# Active Task: Downside-only attack scale experiment

- **Status:** In Progress
- **Objective:** Downside-only attack multiplier (MID/FWD, capped [0.7, 1.0]) vs Champion; swing via hard side with easy ceiling untouched
- **Acceptance:** Overlay downside tests green; runner writes downside_swing_summary.csv with blend MAE, easy cap, hard floor, coherence swings; ruff + full pytest + verify.sh green
- **Issue/Ticket:** New topic docs/research/fixture-downside-scale/

## Work Packet (SFDBN)

- **Status:** Experiment won; verdict committed. Open for phase 2 (gate plumbing + admission)
- **Files:** features/matchup_share.py, features/builder.py (passthrough already generic), docs/research/fixture-downside-scale/runner.py + note, tests/test_matchup_share.py
- **Decisions:** Downside-only [0.7, 1.0] MID/FWD; conceded-delta path untouched; share-gating retained; coherence measured (attack + clean swings must move consistently)
- **Blocked:** None
- **Next:** Read EASY_DIFF constants, then RED tests

## Todo
- [x] Mirror hard-slice constants + RED downside tests
- [x] Green: overlay downside mode + topic runner + note
- [x] Verify: ruff, targeted pytest, full suite, verify.sh, self-review
- [x] Launch full run, commit code
- [ ] Phase 2: gate plumbing + admission run

## Blockers / Notes
- No mypy/pyright configured; ruff is the gate
- Hard floor −0.450 starting guess (mirror of easy cap), flagged in note

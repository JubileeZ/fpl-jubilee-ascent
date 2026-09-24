# Active Task: Fixture-swing candidates experiment

- **Status:** In Progress
- **Objective:** Builder passthrough + overlay ratio mode + three-arm runner (Champion / additive-adjusted / multiplicative)
- **Acceptance:** Overlay ratio unit tests + builder passthrough green; runner runs three arms writing candidate_swing_summary.csv; ruff + full pytest + verify.sh green
- **Issue/Ticket:** docs/research/fixture-swing-candidates/fixture-swing-candidates.md

## Work Packet (SFDBN)

- **Status:** Code committed; three-arm run launched post-commit
- **Files:** features/matchup_share.py, features/builder.py, docs/research/fixture-swing-candidates/runner.py, tests/test_matchup_share.py
- **Decisions:** Model-effect-only via explicit params, defaults frozen; easy cap +0.450; directional swing (grilled 2026-09-24)
- **Blocked:** None
- **Next:** Read builder signature + existing tests, then RED tests

## Todo
- [x] Map builder kwargs seam + existing matchup tests
- [x] Red: ratio-mode + passthrough tests
- [x] Green: overlay attack_scale, builder passthrough, topic runner
- [x] Verify: ruff, targeted pytest, full suite, verify.sh, self-review
- [ ] Launch three-arm run in background, commit code

## Blockers / Notes
- No mypy/pyright configured; ruff is the gate
- Experiment runtime ~75 min; code commits before results land

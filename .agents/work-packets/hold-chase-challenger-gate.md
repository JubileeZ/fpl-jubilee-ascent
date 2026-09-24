# Active Task: Hold-chase challenger gate

- **Status:** In Progress — challenger implemented, dry-run gate PASSED, `--apply` rerun pending
- **Objective:** Promote `hold_chase_challenger` to Champion via Historical Promotion Gate
- **Acceptance:** `--apply` run writes evidence + promoted slate; verdict posted on issue; issue closed
- **Issue/Ticket:** [Challenger implementation plus gate run](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/108)

## Work Packet (SFDBN)

- **Status:** Dry run 1-38 GW 2025-26 / 2024-25 seed: challenger PASS (blend win, 2/3 segments, guardrails); `participation_state_hybrid` FAIL. `--apply` rerun launched, device moved mid-run.
- **Files:** `models/hold_chase_challenger.py` (new), `config/model_selection.json` (challenger registered 2nd candidate), `docs/model_name.md` (catalog row)
- **Decisions:** Challenger subclasses Champion; levers = nailed-lift/fringe-decay participation, high-xG sharpen + ceiling minutes tilt, hard-fixture defensive relax (easy untouched). Claim = assigned issue to JubileeZ.
- **Blocked:** None. Needs ~95 min compute for `--apply`.
- **Next:** On new device: `git pull`, then `uv run python -m commands.evaluate_model_promotion --gw_range 1-38 --data_dir data/archive/2025-26/processed --seed_season 2024-25 --season 2025-26 --apply`. If PASS repeats: verify `config/model_selection.json` champion + evidence in `data/reports/promotion_evidence/`, post resolution comment on issue, close issue, append pointer to map #106 Decisions-so-far. If FAIL: remove challenger from slate (kill with numbers) and record verdict instead.

## Todo

- [x] Implement challenger model + catalog + slate registration
- [x] Ruff + 419 pytest + 3-GW smoke backtest
- [x] Dry-run gate → PASS
- [ ] `--apply` gate → promote + evidence
- [ ] Resolution comment + close issue + map pointer

## Blockers / Notes

- Gate logs buffer to stdout; no per-GW progress visible. Dry run took 96 min.
- Do NOT hand-edit champion; promotion only via `--apply`.

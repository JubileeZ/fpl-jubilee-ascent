# Active Task: Champion adoption launch

- **Status:** In Progress
- **Objective:** Implement Champion adoption (#198, #201, #200) on canonical review branches, run read-only production preflight, and execute isolated private GitHub pilot (#199).
- **Acceptance:** Verified #201 certification, #198 portable evidence & fixture inventory, #200 protected adoption & planner freshness, read-only production preflight, and isolated pilot pass/fail report with open gates documented.
- **Issue/Ticket:** [Wayfinder map](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/190), [#198](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/198), [#199](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/199), [#200](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/200), [#201](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/201).

## Work Packet (SFDBN)

- **Status:** In Progress — #201, #198, #200 code/tests/reviews complete and pushed on canonical review branches (`feat/sparse-confirmation-certification`, `feat/portable-checkpoint-evidence`, `feat/protected-champion-adoption`, `feat/champion-adoption-v1`); read-only production preflight and local pilot acceptance harness complete; awaiting operator prerequisites for live isolated private GitHub pilot (#199).
- **Files:** `backtesting/sparse_certification.py`, `backtesting/portable_evidence.py`, `backtesting/adoption_transaction.py`, `models/planner_selection.py`, `commands/certify_sparse_confirmation.py`, `commands/inventory_pilot_fixture.py`, `commands/produce_validation_evidence.py`, `commands/manage_champion_adoption.py`, `docs/research/sparse-confirmation-certification/`, `docs/testing/pilot-fixture-inventory.md`, `docs/testing/production-preflight-report.json`.
- **Decisions:** Certified sparse confirmation in predeclared `advisory` statistical Early-Harm mode (`seed=20103`, digest `9e7234b1...`). Recorded `has_admissible_historical_gw15_passing_fixture=False` with 6 missing prerequisites (no `>=15`-GW non-live empirical prefix on disk). Left live rollout disabled (`CHAMPION_ADOPTION_LIVE_ENABLED=false`).
- **Blocked:** Live isolated private GitHub pilot (#199) requires operator-authorized private pilot repo, separate GitHub App installation, controlled test inbox/mail provider secrets, and protected environment approval, plus admissible historical `>=15`-GW passing fixture for positive native path.
- **Next:** Await operator pilot repository, App installation, test inbox, and approval instructions to run live #199 pilot from pinned canonical commit on `feat/champion-adoption-v1`.

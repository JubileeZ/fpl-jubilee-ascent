# Weekly Transfer Planner Selection and Champion Adoption (ADR 0070)

**Status**: Accepted design (2026-11-18). Implementation and numerical calibration pending.

**Scope**: Amend [ADR 0069](0069-annual-rolling-validation-and-dual-tier-promotion.md) sections 4–5 as changes ship. Preserve annual firewall, sealed slate of up to two frozen finalists, independent Strategic replay, empirical admission, and explicit human adoption authority.

## Weekly Transfer Planner selection

- Rank Confirmed Champion and eligible frozen finalists by cumulative realized net FPL points (official points minus Hits) on same verified, contiguous settled Gameweeks. Compare independent replays from neutral GW1 anchor. Use highest scorer for next Transfer Plan on actual User Squad. Prefer Champion on tie with Champion or missing comparable evidence. Preserve explicit model override. Show model, comparison scores, and latest settled Gameweek in preflight.
- Ordinary points deficit changes weekly model choice. Keep trailing finalist eligible for later confirmation, including at GW15. Keep eligibility independent of `provisional_active`. Early-Harm or demonstrated mandatory guard failure can exclude finalist under registered rules. Calibrate irreversible harm decisions across repeated checks before expanding their cadence. Inconclusive guard blocks adoption while finalist remains eligible.

## Adoption trigger and approval

- Initial rollout: automate evidence collection, settlement checks, and existing GW15/GW30/GW38 formal evaluations. Design target: first verified full pass at any settled Gameweek from GW15 through GW38. Require statistical superiority to frozen Confirmed Champion plus required projection and segment safeguards.
- Compare current three looks, GW15/GW23/GW30/GW38, and weekly looks under null and improving-model scenarios before using new thresholds. Preserve serial dependence and shared Champion across finalists. Require season-wide false-promotion rate ≤5% across weeks and frozen finalists. Prefer weekly confirmation if it materially reduces time to confirmation while preserving GW38 power. Calibrate outside quarantined live validation season. Register approved protocol before accessing active-season evidence for slate. Retain current schedule until calibration passes and new protocol is registered.
- First verified passing result produces one email linking to protected GitHub Actions approval. Bind approval to immutable evidence bundle, bundle hash, and expected Confirmed Champion. After approval, re-verify bundle and current selection, run `adopt_champion`, and land selection plus adoption receipt through permitted branch workflow. Require fresh approval for changed evidence or Champion. Keep weekly serving updates independent of pending checkpoint evidence. No unattended Champion change.

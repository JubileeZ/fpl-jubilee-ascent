# Champion adoption implementation

Status: implementation queued. Authority: [ADR 0070](../adr/0070-weekly-planner-selection-and-champion-adoption.md) (amended 2026-11-21 for GitHub-native Adoption Review Issue default, optional webhook, and $0 public pilot parity), [Wayfinder decisions](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/190).

## Parallel entry points

### [Certify sparse Champion confirmation and statistical Early-Harm](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/201)

- Use non-live paths. Pin evaluator revision, simulator, scenario grid, independent tuning and held-out seeds, run size, acceptance rules, and retry budget before certification. Cover shared Champion, serial dependence, both slate sizes, mixed nulls in both ranks, and early/late safeguards. Compare optimized runner with scalar evaluator if applicable.
- Version frozen protocol and bind digest to slate before active-season access. Preserve legacy reads. Replace hardcoded policy for new version, including eligibility independent of provisional serving. Use fixed complete prefixes at GW15/GW30/GW38, original slate multiplicity and thresholds, availability-driven skip, unused error spending, and registered UTC expiry. Apply completed segments plus calibrated GW1–4 net-points floor and full-prefix cumulative harm. Inconclusive required safeguard blocks look and preserves eligibility.
- Report one-sided 95% bounds and event counts. Require per-scenario false full pass upper bound ≤5%, separate statistical false terminal exclusion upper bound ≤5%, and primary GW38 correct confirmation lower bound ≥1/3. Predeclare advisory fallback and certify resulting policy on untouched paths. Record failed certification and block live adoption. Weekly expansion remains conditional on [paired speed and power criteria](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/196#issuecomment-7043351900).

### [Build portable checkpoint evidence and verify the pilot fixture](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/198)

- Start with admissible non-live fixture inventory. Retained GW15 fixture reconstructs with inconclusive verdict. Record a true passing fixture's provenance, digest and fresh-root verdict, or name missing prerequisites. Synthetic fixtures support wiring and rejection cases.
- Implement [evidence-store decision](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/193#issuecomment-7014840996). Consolidate registry and replay on `validation-evidence`, publish immutable passing snapshots, keep checkpoint evaluator offline/read-only. Pin exact model module/class and runtime closure. Exercise relocation, registry advancement, common-prefix reuse, and fail-closed treatment of evidence gaps.

## Dependent work

### [Implement protected Champion adoption and planner freshness](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/200)

Integrate portable evidence contract. Work on synthetic fault paths can begin before positive fixture exists. Persist one active request per slate; deduplicate notices by durable request ID and reconcile uncertain delivery. Bind protected approval to immutable evidence, expected Champion and exact authorized change. After green checks, GitHub App acquires reservation shared with Exclusion Ledger writers, rechecks eligibility under reservation, and merges selection and receipt atomically. Disable independent auto-merge. Reconcile unknown merge outcomes from protected `main` before retry or release. Retain request priority, rejection behavior and slate closure on merge.

Planner selects highest eligible net points on verified common prefix, retains explicit override and uses Champion for ties or missing comparison. Fresh solve after remote adoption requires manual sync. GitHub outage uses local Champion with unverified status.

### [Run the isolated GitHub Champion adoption pilot](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/199)

Run [acceptance checklist](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/197#issuecomment-7043511729) after evidence and transaction integration. Develop and fix in `fpl-jubilee-ascent`. Copy exact canonical commit one way to private or $0 public parity pilot repository. Use separate App installation, state and controlled inbox/review surface with production-equivalent protections. Retain source SHA, workflow runs, request/slate IDs, delivery evidence, merge and receipt in pilot report. Positive native path requires admitted historical passing fixture. Missing fixture blocks pilot acceptance while synthetic cases can proceed.

## Live activation

Require passing pilot, read-only production parity preflight, certified preregistered protocol, qualifying prior-season baseline, sealed slate with ≥1 qualified finalist, and complete admissible common prefix. Named operator signs off on named season and checkpoint. Surface blocker and recovery action for missing gates; permit readiness checks inside annual firewall. Weekly serving, recurring checks and adoption requests retain their respective gates.

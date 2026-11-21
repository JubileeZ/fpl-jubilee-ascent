# Champion Adoption Pilot & Production Preflight Report

**Tested Canonical Branch:** `feat/champion-adoption-v1` (`origin/feat/champion-adoption-v1`, verified code commit [`06b96f0a`](https://github.com/JubileeZ/fpl-jubilee-ascent/commit/06b96f0a85038ee64ceb8a22af00ab106a7e83e0) over checkpoint `8248c4ce`; `1217` pytest passed, `29/29` `verify.sh` passed, `0` ruff/scoped pyright errors)
**Base `main` Commit:** `86d16bb057fc848997190118db0963d952e20e66` (untouched)
**Live Rollout Status:** Disabled (`CHAMPION_ADOPTION_LIVE_ENABLED=false`)
**Quarantine Status:** `2026-27` active-season outcomes untouched

---

## 1. End-to-End Requirement & Gate Checklist

| Gate / Deliverable | Ticket | Status | Evidence & Artifact |
|---|---|---|---|
| Non-live sparse confirmation & Early-Harm certification (`N=20,000` / scenario, scalar parity, `<=5%` false pass, `>=1/3` GW38 power, `<=5%` false terminal exclusion) | [#201](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/201#issuecomment-7048590496) | **PASS (`certified=True`, `advisory` mode)** | `docs/research/sparse-confirmation-certification/certification_result.json` (`digest=9e7234b17fc73543eb8330817f3d5ec519735de4f3264485f2592c7f46d53c56`, `statistical_protocol_hash=036164c091033ed85ead3a112811c7659472cb3808be2393fd7d4c3943bdbe53`) |
| Portable checkpoint evidence producer (`collect`/`freeze`/`replay`/`scorecard`/`bootstrap-s1-baseline`), relative POSIX paths, `blobs/<sha256>`, `serving_model_closure_hash`, fresh-root snapshot verifier | [#198](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/198#issuecomment-7048590775) | **PASS** | `backtesting/portable_evidence.py`, `commands/produce_validation_evidence.py`, `.github/workflows/validation-collector.yml`, `tests/test_portable_evidence.py`, `tests/test_produce_validation_evidence.py` |
| Real native verifier pass on admissible historical (`>=15`-GW non-live empirical) evidence | [#198](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/198#issuecomment-7048590775), [#199](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/199#issuecomment-7048591328) | **OPEN (Blocked by missing historical data)** | `docs/testing/pilot-fixture-inventory.md` (`has_admissible_historical_gw15_passing_fixture=False`; `2025-26` stops `GW1..7`, `2024-25` stops `GW1..1`, `2023-24` `0`; retained GW15 fixture reconstructs `inconclusive`, `bundle_hash=9f99c4b8...`) |
| Protected adoption transaction (atomic `adopt_champion`, 1 active request/slate, 30d default expiry, `(net_delta, -podium_index)` priority, webhook/outbox single deduplicated notice + lost-ack reconciliation, shared reservation with `ExclusionLedger` writers, App-token PR API merge without auto-merge, interrupted-merge reconciliation) | [#200](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/200#issuecomment-7048591053) | **PASS (Local Harness + Workflow Audit)** | `backtesting/adoption_transaction.py`, `commands/manage_champion_adoption.py`, `.github/workflows/champion-adoption-{request,pr-checks,merge}.yml`, `tests/test_adoption_transaction.py`, `tests/test_pilot_acceptance_harness.py` |
| Weekly Transfer Planner selection, remote protected `main` freshness (`StaleCheckoutError` manual-sync guard, live `"unverified"` offline Champion-only fallback, root+season evidence sync, never auto-pull), injury-audit rerun model pinning | [#200](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/200#issuecomment-7048591053) | **PASS (Local Harness)** | `models/planner_selection.py`, `models/selection.py`, `commands/solve.py`, `commands/export_dashboard.py`, `commands/dashboard.py`, `solver/transfer_plan.py`, `dashboard/*`, `tests/test_planner_freshness.py` |
| Isolated Private/Free-Parity GitHub Pilot live execution (`JubileeZ/fpl-champion-adoption-pilot`, $0 GitHub Free amendment [#199#issuecomment-7057665143](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/199#issuecomment-7057665143), `8/10` preflight) | [#199](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/199#issuecomment-7048591328) | **PARTIAL PASS (Control/Notice/Queue/Fail-Closed PASS; Positive Passing Merge OPEN)** | Live webhook notice + native GitHub email, `champion-adoption-approval` human approve/reject, GitHub App `5858656` token minting, single-notice dedup (`1`), overlapping pass queue (`0` premature notices), `validation-collector.yml` (`availability`), and fail-closed reject (`0` PRs, `main` unchanged) PASS (Section 6); positive native passing merge + `StaleCheckoutError` OPEN (`has_admissible_historical_gw15_passing_fixture=False`) |
| Read-only production preflight attestation (`JubileeZ/fpl-jubilee-ascent`) | [#199](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/199#issuecomment-7048591328) | **PASS (Preflight executed read-only at `2026-11-21T06:30:27Z`; `4/10` live gates pass, `6/10` open/blocked)** | `docs/testing/production-preflight-report.json` (`mail_delivery_and_reconciliation`: `mode=github_review_issue`, `shared_reservation_wiring`: `true`) |

---

## 2. Sparse Confirmation Certification Summary (#201)

- **Parity (`docs/research/sparse-confirmation-certification/parity_check.json`):** `525` sampled prefixes + `56` edge cases; `max_abs_numeric_diff = 1.2278178473934531e-11 <= 1e-10`; `binary_agreement_rate = 1.0`.
- **Tuning (`seed=20101`):** `gw1_4_material_loss_limit = 25.0` net FPL pts; `M=1` alphas `(3.461e-05, 0.00173025, 0.02733795)`; `M=2` alphas `(6.04e-06, 0.00060375, 0.00953925)`.
- **Primary Enforced (`seed=20102`):** `worst_false_full_pass_upper_95 = 0.045844 <= 0.05` (PASS), `primary_gw38_power_lower_95 = 0.369557 >= 1/3` (PASS), `worst_statistical_false_exclusion_upper_95 = 0.231271 > 0.05` (FAIL -> triggered predeclared `advisory` fallback on untouched `seed=20103`).
- **Certified Predeclared Advisory Fallback (`seed=20103`):**
  - `worst_false_full_pass_upper_95 = 0.044100 <= 0.05` (`834 / 20,000` in `m1_null_persistent_gw15`) — **PASS**
  - `primary_gw38_power_lower_95 = 0.366517 >= 1/3` (`7,443 / 20,000` in `m2_mixed_r1_imp_r2_null_mild_gw15`; reversed order `7,464 / 20,000`, `lower_95 = 0.367564`) — **PASS**
  - `worst_terminal_false_exclusion_upper_95 = 0.021446 <= 0.05` (`395 / 20,000` in `m2_null_persistent_gw30`) — **PASS**

---

## 3. Local Pilot Acceptance Matrix (`tests/test_pilot_acceptance_harness.py`)

| Scenario Category | Verified Cases | Result |
|---|---|---|
| Portable snapshot verification | Fresh-root relocation + canonical registry advancement; rejection of altered archive bytes, runtime closure mismatch, expected Champion mismatch, invalid approved revision, and synthetic (`empirical_admission=False`) bundles | **PASS** |
| Single notice & reconciliation | Deduplicated send by durable `request_id`; simulated provider acceptance + lost ack reconciled without resend; unresolved `"unknown"` delivery status blocks blind resend (`UnresolvedDeliveryError`) | **PASS** |
| Human approval & queue priority | Pending/rejected requests leave selection & receipt unchanged; terminal rejection closes request and promotes next eligible pass for fresh review; simultaneous passes apply `(net_delta, -podium_index)` tie-break | **PASS** |
| Atomic reserved merge & races | Green required checks + disabled auto-merge -> 1 atomic merge of selection + matching `(request_id, slate_id)` receipt + slate closure; post-green-check exclusion race & competing exclusion writer under reservation blocked; pre-ack and post-ack interrupted merges retain `merge_outcome_unknown` reservation and reconcile from protected `main` | **PASS** |
| Weekly planner freshness & rerun pinning | Verified common-prefix net-points ranking, tie-breaks, terminal exclusion override rejection, `--xmins-override` rerun model pinning, post-adoption `StaleCheckoutError` blocking fresh plan even when local scorecard matches local Champion, manual-sync recovery, and offline `"unverified"` Confirmed Champion-only fallback | **PASS** |

---

## 4. Read-Only Production Preflight Summary (`docs/testing/production-preflight-report.json`)

- **Passing (`4/10`):** `certified_protocol`, `live_rollout_disabled`, `mail_delivery_and_reconciliation` (`mode="github_review_issue"` per 2026-11-21 ADR 0070 amendment), `shared_reservation_wiring`.
- **Open / Blocked (`6/10`):** `admissible_historical_passing_fixture`, `branch_protection_main`, `protected_environment`, `github_app_and_no_bypass`, `immutable_evidence_and_releases`, `sealed_slate_and_operator_signoff`.
- **Live Activation Ready:** `false` (remains disabled pending infrastructure provisioning on `main`, qualified frozen slate, complete admissible prefix, and explicit operator sign-off).

---

## 5. Next-Step Runbook (Operator Manual vs Agent-Automatable)

| Step | Operator Must Do Yourself | Agent Can Do With Explicit Authorization |
|---|---|---|
| **1. Merge `feat/champion-adoption-v1` -> `main`** | Review & approve [PR #202](https://github.com/JubileeZ/fpl-jubilee-ascent/pull/202) on GitHub; click Merge on protected `main`; keep `CHAMPION_ADOPTION_LIVE_ENABLED` unset/`false`. | Push updates & summary onto `feat/champion-adoption-v1` (`PR #202`). |
| **2. Retire pilot repo & apply `$0` production protections** | Switch App `5858656`'s GitHub App installation from the pilot repo to `JubileeZ/fpl-jubilee-ascent` (reusing existing `.pem`; optional `MAIL_PROVIDER_WEBHOOK_URL`). | Delete throwaway `JubileeZ/fpl-champion-adoption-pilot`; initialize `validation-evidence`, `main` branch protection, `champion-adoption-approval` reviewer, and `App` secrets on `JubileeZ/fpl-jubilee-ascent` (`8/10` preflight, live disabled). |
| **3. Historical passing fixture ([#198](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/198)/[#199](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/199))** | Supply authentic non-live `>=15`-GW pre-deadline mirror archive if available, or keep gate **OPEN** until prospective `2027-28 GW1–15` capture (without relaxing `empirical_admission.py`). | Run `commands.inventory_pilot_fixture` and `commands.produce_validation_evidence` (`collect`/`freeze`/`replay`) on any authentic archive supplied; update `docs/testing/pilot-fixture-inventory.md`. |
| **4. Candidate Search & Slate** | Approve & seal any qualifying `M <= 2` Comparison Slate and choose `approval_reference` before freezing. | Run `ideate-candidate` / `explore-candidate` loops on `2025-26` (`S-1`) + `2024-25` (`S-2`), keeping `2026-27` outcomes quarantined. |
| **5. Production live activation** | Explicitly authorize & set `CHAMPION_ADOPTION_LIVE_ENABLED=true` once all 10 gates pass. | Run read-only `commands.manage_champion_adoption production-preflight --repo JubileeZ/fpl-jubilee-ascent` and confirm `10/10` pass. |

### Fastest Order to Proceed
1. Review & merge canonical **[PR #202](https://github.com/JubileeZ/fpl-jubilee-ascent/pull/202)** (`feat/champion-adoption-v1` → `main`), keeping `CHAMPION_ADOPTION_LIVE_ENABLED` false.
2. Switch App `5858656` installation to `JubileeZ/fpl-jubilee-ascent` and authorize the agent to delete `JubileeZ/fpl-champion-adoption-pilot` + configure `$0` GitHub Free protections & secrets on `JubileeZ/fpl-jubilee-ascent` (`8/10` preflight; GitHub-native `Adoption Review Issue` + Environment email already satisfy notice delivery with zero webhook server).
3. Decide historical `>=15`-GW archive vs prospective `2027-28 GW1–15` capture (`#198`), and run `ideate-candidate` / `explore-candidate` to qualify an `M <= 2` slate.

---

## 6. Live Isolated GitHub Pilot Results (`#199`)

- **Pilot Repository:** [JubileeZ/fpl-champion-adoption-pilot](https://github.com/JubileeZ/fpl-champion-adoption-pilot) (`main` seeded from `3f6babc3`; switched to public at $0 per operator GitHub Free amendment [#199#issuecomment-7057665143](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/199#issuecomment-7057665143); GitHub App `5858656`; Webhook.site endpoint + native GitHub approval emails).
- **Pilot Preflight (`2026-11-21T05:39:00Z`):** **8/10 PASS** (`branch_protection_main`, `certified_protocol`, `github_app_and_no_bypass`, `immutable_evidence_and_releases`, `live_rollout_disabled`, `mail_delivery_and_reconciliation`, `protected_environment`, `shared_reservation_wiring`); only `admissible_historical_passing_fixture` and `sealed_slate_and_operator_signoff` open.

| Run | Workflow / Scenario | Request ID / Slate | Observed Result |
|---|---|---|---|
| [`44871876505`](https://github.com/JubileeZ/fpl-champion-adoption-pilot/actions/runs/44871876505) | `champion-adoption-request.yml` (`decision=reject`, synthetic wiring) | `req-2025-26-gw15-6581bd69563bdb3d` (`pilot-synth-wiring-01`) | **PASS** — `enqueue-and-notify` sent webhook notice (`provider_message_id="webhook-site-ok"`), native email received; operator approved `champion-adoption-approval`; `apply-human-disposition` minted App `5858656` token & recorded hash-chained `rejected`; pilot `main` unchanged (`0` PRs). |
| [`44872502162`](https://github.com/JubileeZ/fpl-champion-adoption-pilot/actions/runs/44872502162) | `validation-collector.yml` (`action=availability`) | `2025-26` | **PASS** — `capture-availability-snapshot` succeeded (`collect-and-evaluate` skipped). |
| [`44872504434`](https://github.com/JubileeZ/fpl-champion-adoption-pilot/actions/runs/44872504434) | `champion-adoption-request.yml` (Q1 pass 1; operator clicked Approve) | `req-2025-26-gw15-2a80ff77b631cfe5` (`pilot-synth-queue-02`) | **FAIL-CLOSED + DEFECT CAUGHT** — `apply-human-disposition` failed closed (`Snapshot archive not found`) opening `0` PRs and leaving pilot `main` unchanged; exposed premature `record_approval` ordering before `adopt_champion` in `_prepare_adoption_pr_command`, now fixed & regression-tested on `feat/champion-adoption-v1` (PR #202). |
| [`44872620511`](https://github.com/JubileeZ/fpl-champion-adoption-pilot/actions/runs/44872620511) | `champion-adoption-request.yml` (Q2 duplicate notice check, cancelled after test) | `req-2025-26-gw15-2a80ff77b631cfe5` (`pilot-synth-queue-02`) | **PASS** — `enqueue-and-notify` succeeded without resending; `notifications.jsonl` contains **exactly `1` `delivered` record** for this `request_id`; cancel triggered `handle-environment-rejection` (`success`), running `--advance-queue` fail-closed against queued Q3 (`stale_closed`). |
| [`44872815585`](https://github.com/JubileeZ/fpl-champion-adoption-pilot/actions/runs/44872815585) | `champion-adoption-request.yml` (Q3 overlapping pass 2; prior [`44872623664`](https://github.com/JubileeZ/fpl-champion-adoption-pilot/actions/runs/44872623664) cancelled by GH >1 pending concurrency limit) | `req-2025-26-gw15-87ddf7a46ef34e44` (`pilot-synth-queue-02`) | **PASS** — `enqueue-and-notify` persisted `status="queued"` (`club_def_prior_challenger`, `net_delta=11.0`) with **`0` premature notices**; downstream approval jobs cleanly skipped. |
| [`44872625528`](https://github.com/JubileeZ/fpl-champion-adoption-pilot/actions/runs/44872625528) | `champion-adoption-request.yml` (F1 staged synthetic archive; operator clicked Reject at Environment) | `req-2025-26-gw15-31723fbd7fc08d78` (`pilot-synth-failclosed-03`) | **PASS** — `enqueue-and-notify` delivered `1` notice; Environment reject triggered `handle-environment-rejection` (`success`), closing request `rejected` (`0` PRs, `main` unchanged). |

- **Pilot Invariant Summary:** `0` PRs opened on `JubileeZ/fpl-champion-adoption-pilot`, pilot `config/model_selection.json` unchanged (`champion="def_xg_shrink_challenger"`). Positive native-verifier passing merge, receipt, and live `StaleCheckoutError` remain **OPEN** until an authentic `>=15`-GW non-live passing fixture exists (`#198`).

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
| Isolated Private GitHub Pilot live execution (1 delivered notice, 1 human approval, 1 App merge + receipt on private pilot repo) | [#199](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/199#issuecomment-7048591328) | **OPEN (Awaiting operator pilot repo, App, test inbox, approval & historical passing fixture)** | Local acceptance harness `5/5` tests PASS covering `#197` matrix (`tests/test_pilot_acceptance_harness.py`); live GitHub dispatch awaiting operator pilot environment |
| Read-only production preflight attestation (`JubileeZ/fpl-jubilee-ascent`) | [#199](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/199#issuecomment-7048591328) | **PASS (Preflight executed read-only at `2026-11-21T03:47:37Z`; `3/10` live gates pass, `7/10` open/blocked)** | `docs/testing/production-preflight-report.json` (`shared_reservation_wiring`: `workflows_present=true`, `shared_concurrency_group=true`, `no_direct_main_push=true`, `collector_exclusion_reservation=true`, `coordinator_wired=true`) |

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

- **Passing (`3/10`):** `certified_protocol`, `live_rollout_disabled`, `shared_reservation_wiring`.
- **Open / Blocked (`7/10`):** `admissible_historical_passing_fixture`, `branch_protection_main`, `protected_environment`, `github_app_and_no_bypass`, `immutable_evidence_and_releases`, `mail_delivery_and_reconciliation`, `sealed_slate_and_operator_signoff`.
- **Live Activation Ready:** `false` (remains disabled pending isolated live GitHub pilot, infrastructure provisioning, qualified frozen slate, complete admissible prefix, and explicit operator sign-off).

---

## 5. Next-Step Runbook (Operator Manual vs Agent-Automatable)

| Step | Operator Must Do Yourself | Agent Can Do With Explicit Authorization |
|---|---|---|
| **1. Merge `feat/champion-adoption-v1` -> `main`** | Review & approve PR on GitHub; click Merge on protected `main`; keep `CHAMPION_ADOPTION_LIVE_ENABLED` unset/`false`. | Open PR from `feat/champion-adoption-v1` -> `main` with verification summary. |
| **2. Isolated private GitHub pilot ([#199](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/199))** | Create private pilot repo; register & install dedicated GitHub App (Contents + Pull requests write); add `CHAMPION_ADOPTION_APP_ID`, `CHAMPION_ADOPTION_APP_PRIVATE_KEY`, and mail webhook secrets (or pick `outbox_dir`) in GitHub UI; click Approve/Reject at `champion-adoption-approval`; verify notice delivery. | Push pinned commit `06b96f0a` one-way to pilot repo; initialize orphan `validation-evidence` branch; configure non-secret repo protection & `champion-adoption-approval` environment if token allows; dispatch/monitor workflows; test failure/retry/planner-sync; verify receipt on pilot `main`; update this report & `#199`. |
| **3. Historical passing fixture ([#198](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/198)/[#199](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/199))** | Supply authentic non-live `>=15`-GW pre-deadline mirror archive if available, or keep gate **OPEN** until prospective `2027-28 GW1–15` capture (without relaxing `empirical_admission.py`). | Run `commands.inventory_pilot_fixture` and `commands.produce_validation_evidence` (`collect`/`freeze`/`replay`) on any authentic archive supplied; update `docs/testing/pilot-fixture-inventory.md`. |
| **4. Candidate Search & Slate** | Approve & seal any qualifying `M <= 2` Comparison Slate and choose `approval_reference` before freezing. | Run `ideate-candidate` / `explore-candidate` loops on `2025-26` (`S-1`) + `2024-25` (`S-2`), keeping `2026-27` outcomes quarantined. |
| **5. Production live activation** | Provision App, secrets, mail provider, branch protection, and environment on `JubileeZ/fpl-jubilee-ascent`; explicitly authorize & set `CHAMPION_ADOPTION_LIVE_ENABLED=true` once all 10 gates pass. | Run read-only `commands.manage_champion_adoption production-preflight --repo JubileeZ/fpl-jubilee-ascent` and update `docs/testing/production-preflight-report.json` to confirm `10/10` pass. |

### Fastest Order to Proceed
1. Authorize agent: open PR `feat/champion-adoption-v1` -> `main` (operator reviews & merges).
2. Either create private pilot repo + GitHub App + secrets and authorize agent to mirror `06b96f0a` and run `#199`, **or** authorize `ideate-candidate` / `explore-candidate` search first while holding live pilot setup for later.

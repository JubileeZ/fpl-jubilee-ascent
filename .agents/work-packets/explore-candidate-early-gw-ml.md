# Active Task: explore-candidate-early-gw-ml

- **Status:** Completed (Exit b: scope exhausted, verdict no win)
- **Objective:** Evaluate candidate models tackling early GW prediction and ML sample maturity against Champion `adaptive_causal_challenger` on dev (2025-26) and confirm (2024-25) seasons via smoke.py.
- **Acceptance:** Frozen Candidate passing Historical Promotion Gate (ADR 0047, ADR 0049, ADR 0054 formation_xi_regret, ADR 0062 segment guardrails) on dev + confirm seasons, adoption queued in Human Queue — or scope exhausted with attempts recorded in Candidate Ledger.
- **Issue/Ticket:** explore-candidate Scoped mode (Early GW ML Exploration under /goal)

## Work Packet (SFDBN)

- **Status:** Completed (Exit b: all 4 lanes and stack explored across 22 prototypes; best candidate bounded_causal_challenger won dev +0.156 P 0.803, failed confirm -2.280 P 0.012; lever logged Dead; Champion adaptive_causal_challenger stands)
- **Files:**
  - `docs/research/early-gw-ml-exploration/early-gw-ml-exploration.md`
  - `docs/research/early-gw-ml-exploration/smoke_results.csv`
  - `docs/research/early-gw-ml-exploration/candidate_gate.csv`
  - `models/bounded_causal_challenger.py`
  - `tests/test_bounded_causal_challenger.py`
  - `docs/model_name.md`
  - `docs/research/candidate-ledger/candidate_ledger.csv`
  - `docs/research/candidate-ledger/candidate-ledger.md`
  - `docs/research/INDEX.md`
  - `docs/agents/current-state.md`
  - `.agents/work-packets/explore-candidate-early-gw-ml.md`
- **Decisions:**
  - Lane 1 (`lane1_ess_ramp`): 3 variants passed dev (`lane1_ramp_gw12_s8` +0.158, `lane1_ramp_gw10_s10` +0.091, `lane1_ramp_gw8_s12` +0.080).
  - Lane 2 (`lane2_staggered_ladder`): all 5 variants failed dev (-0.245 to -1.299) due to un-damped step activation.
  - Lane 3 (`lane3_prior_anchoring`): `lane3_anchor_clamp10_gw10` won dev (+0.156, boot P 0.803).
  - Lane 4 (`lane4_hybrid_ladder`): all 5 variants failed dev (-0.097 to -0.499).
  - Stack protocol: both stack variants failed dev (-0.120).
  - Frozen candidate `bounded_causal_challenger` built and evaluated on confirmation season (`2024–25` unseeded under ADR 0047): failed with -2.280 pts/GW, boot P 0.012, early_mid -5.775 < -0.15.
  - Root cause: In unseeded confirmation seasons, within-season ML models cannot condition on sufficient player history in GW1–15, leading to severe captaincy regret regressions. Champion `adaptive_causal_challenger` stability across GW1–19 is mathematically necessary for unseeded confirmation regimes.
  - Lever logged Dead in Candidate Ledger (`revisit_after = 2027-10-23`).
- **Blocked:** None
- **Next:** Await user review of early-GW exploration findings and candidate ledger updates.

## Human Queue
- [ ] Acknowledge Dead-lever verdict for Bounded Causal ML Challenger (revisit after 2027-10-23).

## Lane Inventory & Results
| Lane | Mechanism | Best Variant | dev combined_delta | segs | boot P | Verdict |
|---|---|---|---|---|---|---|
| `lane1_ess_ramp` | Continuous ESS minutes ramp | `lane1_ramp_gw12_s8` | +0.1576 | 1/3 | 0.6553 | PASS (dev) |
| `lane2_staggered_ladder` | Component-staggered activation ladder | `lane2_h1_h3_gw10` | -0.0967 | 0/3 | 0.0000 | FAIL (dev: abrupt step induces early_mid regression) |
| `lane3_prior_anchoring` | Empirical Bayes prior anchoring / talisman floor | `lane3_anchor_clamp10_gw10` | +0.1555 | 1/3 | 0.8030 | PASS (dev) / FAIL (confirm -2.280 P 0.012) |
| `lane4_hybrid_ladder` | Hybrid ladder with continuous event ramp | `lane4_hybrid_h1_h3_gw10_g_ramp14` | -0.0967 | 0/3 | 0.0000 | FAIL (dev: un-damped H1 volatility) |
| `stack` | Compound ramp + clamp | `stack_ramp10_clamp10` | -0.1196 | 0/3 | 0.0000 | FAIL (dev) |

## Todo
- [x] 0. Ground (arm goal, packet, seasons, champion)
- [x] 1. Ledger screen (Dead rows excluded: schedule congestion, sum p_start=11, unseeded tenure decay, natural rate calibration)
- [x] 2. Lane plan (4 lanes pre-declared)
- [x] 3. Dispatch lanes (prototypes.py, audit, smoke.py across 22 prototypes)
- [x] 4. Audit + verify results (all AUDIT PASS, no LEAKAGE FAIL)
- [x] 5. Iterate to paper win (`bounded_causal_challenger` dev PASS +0.156 P 0.803)
- [x] 6. Build Candidate (`models/bounded_causal_challenger.py`, tests, catalog, freeze check passed)
- [x] 7. Adopt gate (Confirmation season FAIL -2.280 P 0.012; Dead row logged)
- [x] 8. Record + Exit (research note, smoke_results.csv, candidate_gate.csv, candidate ledger, INDEX updated)

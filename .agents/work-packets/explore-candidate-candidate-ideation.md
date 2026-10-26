# Active Task: explore-candidate-candidate-ideation

- **Status:** Completed (Exit b: queue exhausted, verdict no win)
- **Objective:** Frozen Candidate passing Historical Promotion Gate on dev (2025-26) and confirm (2024-25) seasons via smoke.py, adoption queued in Human Queue — or scope exhausted with every attempt in Candidate Ledger.
- **Acceptance:** Exit (a)/(b)/(c) per .agents/skills/explore-candidate/SKILL.md
- **Issue/Ticket:** docs/research/candidate-ideation/idea_queue.csv

## Run state

- **Mode:** Queue · scope docs/research/candidate-ideation/idea_queue.csv · slug candidate-ideation
- **Seasons:**
  - dev: 2025-26 GW1-38 seed 2024-25
  - confirm: 2024-25 GW1-38 seed 2023-24
  - holdout: 2026-27 (sealed live season; never run here)
- **Champion:** `adaptive_causal_challenger` (`models/adaptive_causal_challenger.py`)
- **Champion Shipped Lineage Levers:**
  1. Face-value G/A weights (1.0 xG; 0 threat); no in-season ridge refit (`face_value_challenger`, ADR 0045)
  2. Minute-pooled goal finishing offset K=1800 (`face_value_challenger`, ADR 0045)
  3. Start-probability shrink k=0.15 (`face_value_challenger`, ADR 0045)
  4. Calibrated Matchup Share -> Club Strength -> neutral fixture scale (ADR 0040)
  5. Participation penalty + calibrated matchup hybrid base (ADR 0041)
  6. Learned start probability (ridge-logistic, per-GW mass preserved to Champion total) + P(60)-weighted bonus pool (`learned_start_challenger`, ADR 0050)
  7. Multi-feature Poisson GLM assist rate (xA target; xA/creativity/opp xG conceded/team xG/home) (`multi_feature_assist_challenger`, ADR 0048)
  8. Position-specific xG/xA rate shrink K (DEF xG 2400 pseudo-min vs flat 360; FWD 900; as-of split-half K; + xA) (`def_xg_shrink_challenger`, ADR 0055)
  9. Club x DEF xG rate prior (DEF xG/90 shrinks 360 pseudo-min toward as-of club x DEF pooled rate; club prior shrunk 5 matches to DEF mean) (`club_def_prior_challenger`, ADR 0051)
  10. Adaptive Causal ML Challenger (100% Champion stability GW1-19; Late Season ML activation GW20+; Ridge p_start + start duration + shrunk xG goals + LOO assist finishing; congestion excluded) (`adaptive_causal_challenger`, ADR 0063)
- **Step:** 8 done (Exit (b))
- **Scratch:** `.tmp/agent/explore-candidate/` cleaned up at Exit

## Report

**Verdict:** Queue exhausted (Exit b: no win); Model Champion `adaptive_causal_challenger` stands unchanged.
**Summary:**
- `EXT-01`: Dead row 61 match (`Empirical-Bayes P(60|state) Beta-binomial`; revisit after 2027-09-29) -> `dead-match`
- `EXT-02`: Dead row 11 match (`Assist finishing offsets pooled`; revisit after 2027-09-28) -> `dead-match`
- `EXT-03`: Dead row 11 match (`Assist finishing offsets pooled`; revisit after 2027-09-28) -> `dead-match`
- `EXT-04`: Dead row 72 match (`Club SoT volume x pooled save rate`; revisit after 2027-09-29) -> `dead-match`
- `EXT-05`: Evaluated across 4 grid variants on dev season (2025–26 GW1–38). All 4 variants failed dev gate (combined $\Delta = -1.0036$ pts/GW, boot $P = 0.0116$, segs 1/3, catastrophic early_mid regression $-2.643 < -0.15$ pts/GW, xMins MAE regressed). Lever logged Dead in `candidate_ledger.csv` (`revisit_after = 2027-10-26`) -> `fail`
- `EXT-06`: Dead row 81 match (`Defcon venue and opposition pressure scaling`; revisit after 2027-09-30) & ARCH-12 -> `dead-match`
**Audit:** all prototypes AUDIT PASS, no LEAKAGE FAIL
**Ledger:** Row 94 added to `candidate_ledger.csv`: Price-Stratified Huber-Regularized Continuous-N_eff Causal Panel (Dead until 2027-10-26)

## Work Packet (SFDBN)

- **Status:** Completed (Exit b: queue exhausted, verdict no win)
- **Files:**
  - `docs/research/candidate-ideation/idea_queue.csv`
  - `docs/research/candidate-ideation/smoke_results.csv`
  - `docs/research/candidate-ideation/candidate-ideation.md`
  - `docs/research/candidate-ledger/candidate_ledger.csv`
  - `docs/research/candidate-ledger/candidate-ledger.md`
  - `docs/research/INDEX.md`
  - `docs/agents/current-state.md`
  - `.agents/work-packets/explore-candidate-candidate-ideation.md`
  - `.agents/handoff-pointer`
- **Decisions:**
  - Screened all 6 queued candidate proposals against Candidate Ledger; 5 matched dead levers.
  - Lane `ext_05` proved that early activation of within-season ML models (even with Huber loss and price-tier centering) causes catastrophic regression in early_mid (-2.643 pts/GW) due to short-panel non-stationarity.
  - Champion `adaptive_causal_challenger` stability across GW1–19 is confirmed mathematically necessary.
  - Queue is 100% complete; lever logged Dead; Champion stands.
- **Blocked:** None
- **Next:** Await human review of ideation queue resolution.

## Human Queue

- [x] Override Dead row 61 for EXT-01 (Beta-Binomial P(60|state); revisit after 2027-09-29)? User decision: No (respect Dead lever lock).
- [x] Override Dead row 81 for EXT-06 (Defcon venue/opposition pressure scaling; revisit after 2027-09-30)? User decision: No (respect Dead lever lock).
- [x] Acknowledge Dead row 94 for EXT-05 (Price-Stratified Huber Causal Panel; revisit after 2027-10-26). User decision: Yes (acknowledged Dead row 94).

## Lane Inventory & Results

| Lane | Mechanism | Best Variant | dev combined_delta | segs | boot P | Verdict |
|---|---|---|---|---|---|---|
| `ext_05` | Price-stratified Huber causal panel + continuous N_eff ramp | `ext_05_n4000_n8000_d135_l75` | −1.0036 | 1/3 | 0.0116 | FAIL (dev: early_mid catastrophic regression −2.643 < −0.15; guardrails failed) |

## Todo

- [x] 0. Ground (arm goal, packet, seasons, champion)
- [x] 1. Ledger screen (5 dead-match rows, 1 new)
- [x] 2. Lane plan (ext_05 fixed grid)
- [x] 3. Dispatch subagents / prototypes (all AUDIT PASS)
- [x] 4. Audit + verify results (dev smoke completed via smoke.py)
- [x] 5. Iterate to paper win (all variants failed dev; queue exhausted)
- [x] 8. Record + Exit (smoke_results.csv, candidate_ledger.csv, candidate-ledger.md, idea_queue.csv, candidate-ideation.md, INDEX, current-state updated)

# Candidate Ideation & External Model Collaboration

**Updated**: 2026-11-11 (+00:00)
**Data stamp**: 152 development smoke rows, 120 unique saved variants; EXT-35 terminal companion additionally records three inert admission refusals; no confirmation or holdout results
**Season**: Multi-season (2024-25, 2025-26, 2026-27)  
**Status**: Eligible queue exhausted; EXT-35 inconclusive after no development win; EXT-10/13/37 blocked; zero promotions; Champion unchanged
**Purpose**: Generate, curate, and queue innovative candidate projection model hypotheses from frontier LLMs for empirical gating.  
**Scope**: Ingests external model ideation proposals, filters against proven dead-lever archetypes, and executes autonomous gating via `explore-candidate`.  
**Related**: [Eval canon](../INDEX.md) · [Candidate Ledger](../candidate-ledger/candidate-ledger.md) · [ADR 0068](../../adr/0068-two-axis-pre-execution-candidate-review.md) · [ADR 0066](../../adr/0066-backtesting-and-promotion-foundation.md) · [ADR 0064](../../adr/0064-promotion-gate-and-evaluation-rigor-overhaul.md) · [ADR 0063](../../adr/0063-champion-adaptive-causal-challenger.md)  
**Artifact**: [idea_queue.csv](idea_queue.csv) `order` / `idea_id` / `tier` / `status` / `spec_path` — primary candidate work queue index.  
**Dossiers**: [ideas/](ideas/) — full LaTeX formulations, cold-start strategies, and Python code skeletons.  
**Smoke Results**: [smoke_results.csv](smoke_results.csv) — empirical dev-season gate runs across prototype variants.
**Agent Reports**: [Minutes](minutes-ideation-response.md) · [Attack](attack-ideation-response.md) · [Defense](defense-ideation-response.md) · [Fixtures](fixtures-ideation-response.md); frontier language-model review, 2026-11-09.

LLM references: capability-neutral; specialist role, date, source artifact for provenance. No fixed provider/model/version recommendations. FPL projection-model identifiers retained for reproducibility.

---

## Batch 8 EXT-35 execution (2026-11-11)

**Verdict:** No development winner. All four fixed variants executed on resolved development 2025-26 GW1-38, seed 2024-25. One variant failed Tier 2 on an oracle formation-regret tie (`combined_delta=0`, `boot_p_gt0=0`); three failed inertness admission with zero oracle-regret delta and maximum playable projection shifts below 0.01. Complete terminal coverage: [execution_results.csv](prototypes/ext_35/execution_results.csv), columns `screen_outcome`, `execution_status`, `oracle_regret_delta`, `max_playable_projection_shift`. One genuine screen row appended to `smoke_results.csv`; refused variants remain separate rather than fabricated as valid screen rows.

Both source-review axes passed before compute. Full 380-cell event-on/off by native/oracle diagnostic retained; independent verification passed state/rate identity, component accounting, source/artifact hashes, squad constraints, canonical selections, paired scores and interactions. Native states exactly matched Champion; tiny rate intervention did not improve oracle selection. No assertion that minutes caused earlier failures. [Source/reviews/paired companions](prototypes/ext_35/README.md).

Harness exit 2 reflects caught inertness refusals, not a traceback or leakage finding. Scientific verdict remains inconclusive; queue EXT-35 `inconclusive`, ledger row `open`, locks unchanged. No Tier 3, confirmation, Candidate registration, parameter expansion, or production change. Remaining EXT-10/13/37 blocked; default skip. Source and execution validations: 1036 tests pass, Ruff clean.

Capture limitation: core manifest did not hash feature frames or rate diagnostics at capture. Post-processing records current hashes with explicit limitation. Retained evidence remains diagnostic, not admitted promotion evidence.

## Near-miss ideation (2026-11-10, paper intake)

Three specialist agents inspected promising failed OPEN mechanisms and actual scoring paths. Added EXT-35 fixed-K lagged creative-role prior and EXT-37 baseline-preserving hazard residual; four preregistered variants each, partial implementation skeletons. EXT-35 eligible for implementation; EXT-37 blocked pending exact overlay context reconstruction/applicability. Lexical Dead matches reviewed and retained with explicit distinctions; locks unchanged. No new model execution or empirical improvement claimed. [Review, provenance, diagnostic prerequisite](near-miss-ideation-2026-11-10.md) · [Source proposals](near-miss-ideation-response.md).

## Batch 7 Exploration Execution (2026-11-10, completed)

**Verdict:** Batch 7 completed under ADR 0068 Two-Axis Pre-Execution Candidate Review Protocol: no win (all tested candidates EXT-32, EXT-33, EXT-34 passed dual-axis review and demonstrated positive Tier 2 Oracle signals, but failed the Tier 3 Development Screen); entire 34-idea candidate ideation queue exhausted; Model Champion `def_xg_shrink_challenger` stands unchanged.

- **Smoke Evaluation (`ext_32`, `ext_33`, `ext_34` — 18 variants total, all `AUDIT PASS`, zero `LEAKAGE FAIL`)**:
  - **Lane `ext_32` (`EXT-32`: Smooth Sigmoid Attacking-Role Stratification for Fullbacks, 6 variants: $\tau_{\text{threat}} \in [14.0, 18.0], K_{\text{OOP}} \in [600, 1000], M_0 \in [360, 450], \gamma_{\text{oop}} \in [0.20, 0.25], s_{\text{threat}} \in [2.5, 3.5]$)**:
    - Passed ADR 0068 Two-Axis Review Gate (Reviewer A Spec/Math PASS, Reviewer B Standards/Arch PASS).
    - All 6 variants passed Tier 2 Oracle Event Gate ($\Delta = +0.1889$ to $+0.2164$, $P = 0.778$ to $0.826$), confirming oracle-level event ranking improvement.
    - Under Tier 3 walkforward evaluation with predicted minutes, all variants failed the Development Screen: $\Delta = -0.0187$ to $-0.3521$, $P = 0.137$ to $0.514$, segs 1/3, with late-season segment regression ($-0.202$ to $-0.838 < -0.13$).
    - Best variant: `ext_32_t18_k800_m360` ($\Delta = -0.0187$, segs 1/3, boot $P = 0.514$).
    - Eliminating threshold chatter improved stability vs EXT-20, but full-season walkforward under predicted minutes does not beat Champion.
    - Diagnostic failure; `open` status preserved in `candidate_ledger.csv`; no new Dead lock.
  - **Lane `ext_33` (`EXT-33`: Truly Asymmetric Convex-Balanced Clean Sheet Hazard, 6 variants: $\alpha_{\text{cs}} \in [0.18, 0.26], \rho_{\text{cs}} \in [0.20, 0.33], K_{\text{cs}} \in [6.0, 10.0]$)**:
    - Passed ADR 0068 Two-Axis Review Gate (Reviewer A Spec/Math PASS, Reviewer B Standards/Arch PASS).
    - 4 of 6 variants passed Tier 2 Oracle Event Gate ($\Delta = +0.3957$ to $+0.5386$, $P = 0.826$ to $0.937$); 2 variants failed Tier 2 captaincy regret guardrail ($+0.2691 > +0.1500$).
    - Under Tier 3 walkforward evaluation with predicted minutes, all 4 Tier 2 passers failed the Development Screen: $\Delta = -0.0371$ to $-0.3092$, $P = 0.143$ to $0.292$, segs 1/3, with cold-start regression ($-0.787 < -0.25$) and early-mid segment regression ($-0.611$ to $-0.944 < -0.15$).
    - Best variant: `ext_33_a18_r33_k6` ($\Delta = -0.0371$, segs 1/3, boot $P = 0.229$).
    - Asymmetric hazard decay protects green fixtures vs EXT-23, but match-level xG uncertainty still induces early-mid season drag.
    - Diagnostic failure; `open` status preserved in `candidate_ledger.csv`; no new Dead lock.
  - **Lane `ext_34` (`EXT-34`: Unified Fullback Attacking-Role and Matchup Clean-Sheet Hazard, 6 variants: $\tau_{\text{threat}} \in [15.0, 18.0], K_{\text{OOP}} \in [600, 800], \alpha_{\text{cs}} \in [0.18, 0.22]$)**:
    - Passed ADR 0068 Two-Axis Review Gate (Reviewer A Spec/Math PASS, Reviewer B Standards/Arch PASS).
    - All 6 variants passed Tier 2 Oracle Event Gate with exceptionally strong deltas ($\Delta = +0.6137$ to $+0.9109$, $P = 0.961$ to $0.995$), confirming massive positive signal when playing time is known.
    - Under Tier 3 walkforward evaluation with predicted minutes, all variants failed the Development Screen: $\Delta = -0.0988$ to $-0.7011$, $P = 0.048$ to $0.427$, segs 0/3 to 1/3, with cold-start regression ($-0.787 < -0.25$) and early-mid segment regression ($-0.350$ to $-0.542 < -0.15$).
    - Best variants: `ext_34_t18_k600_a22` and `ext_34_t18_k800_a22` ($\Delta = -0.0988$, segs 1/3, boot $P = 0.427$).
    - Synergistic combination retains strong event signal but is constrained by interaction with predicted minutes.
    - Diagnostic failure; `open` status preserved in `candidate_ledger.csv`; no new Dead lock.

---

## Batch 6 Exploration Execution (2026-11-10, completed)

**Verdict:** Batch 6 completed: no win (all tested candidates EXT-26, EXT-27, EXT-28, EXT-31 failed the Development Screen; EXT-29 & EXT-30 dead-match); entire 31-idea candidate ideation queue exhausted; Model Champion `def_xg_shrink_challenger` stands unchanged.

- **Smoke Evaluation (`ext_26`, `ext_27`, `ext_28`, `ext_31` — 24 variants total, all `AUDIT PASS`, zero `LEAKAGE FAIL`)**:
  - **Lane `ext_26` (`EXT-26`: Projected Goal Margin Minutes Trim Modulation, 6 variants: $\psi_{\text{margin}} \in [1.5, 4.0], \tau_{\text{margin}} \in [0.5, 1.0]$)**:
    - All 6 variants failed Tier 1 Minutes Gate (`pass=False`): Candidate MAE degraded on Champion (13.728..13.753 vs 13.704 baseline), with bootstrap win probability 0.000 (< 0.65 threshold).
    - Under Tier 3 walkforward evaluation, all variants produced negative combined primary delta ($\Delta = -0.1046$ to $-0.3317$, $P = 0.031$ to $0.358$), with severe regressions in early-mid segment ($-0.840$ to $-1.816 < -0.15$). Best variant: `ext_26_p40_t10` ($\Delta = -0.1046$, segs 1/3, boot $P = 0.358$).
    - Trimming starting minutes based on team-opponent goal margin harmed both minutes calibration and transfer/lineup decisions.
    - All 6 variants failed the Development Screen (`pass=False`). Logged as diagnostic failure in `idea_queue.csv` (`status: fail`); no new Dead lock.
  - **Lane `ext_27` (`EXT-27`: Venue-Decoupled Home Advantage, 6 variants: $\eta \in [0.50, 1.00]$, scope $\in \{\text{all}, \text{att}, \text{def}\}$)**:
    - 5 of 6 variants recorded non-positive Oracle Regret Delta ($\Delta = -1.1543$ to $+0.0000, P = 0.000$ to $0.476$).
    - Variant `ext_27_e100_all` achieved positive raw delta ($\Delta = +0.2357$), but failed the bootstrap confidence threshold ($P = 0.504 < 0.65$).
    - Decoupling venue scaling from official ratings did not improve lineup or transfer efficiency over the Champion.
    - All 6 variants failed the Development Screen (`pass=False`). Logged as diagnostic failure in `idea_queue.csv` (`status: fail`); no new Dead lock.
  - **Lane `ext_28` (`EXT-28`: Schedule-Neutralized Attack Baselines, 6 variants: $\phi \in [0.50, 1.00]$, mode $\in \{\text{all}, \text{xg}, \text{xa}, \text{in\_season}\}$)**:
    - 5 of 6 variants recorded non-positive Oracle Regret Delta ($\Delta = -0.0657$ to $-0.5032, P = 0.100$ to $0.237$).
    - Variant `ext_28_phi050` achieved positive raw delta ($\Delta = +0.0142$), but failed the bootstrap confidence threshold ($P = 0.486 < 0.65$).
    - De-biasing historical player attacking rates by opponent concession intensity did not improve formation XI lineup selection.
    - All 6 variants failed the Development Screen (`pass=False`). Logged as diagnostic failure in `idea_queue.csv` (`status: fail`); no new Dead lock.
  - **Lane `ext_31` (`EXT-31`: Opponent-Sample-Reliability Matchup Share: Promoted-Club Cold Start, 6 variants: $K_t \in [10, 38]$, rule $\in \{\text{geo}, \text{min}\}$, $w_{\text{floor}} \in [0.0, 0.25]$)**:
    - All 6 variants failed Tier 2 Oracle Event Gate (`pass=False`, `segs=0/3`, `boot_p_gt0=0.394`, `combined_delta` `-0.1745` to `-0.2503`).
    - Attenuating fixture swing multipliers for newly promoted clubs degraded formation XI selection, as official pre-season club ratings already capture baseline concession differentials well enough that dampening them deprives the optimizer of actionable fixture contrast.
    - All 6 variants failed the Development Screen (`pass=False`). Logged as diagnostic failure in `idea_queue.csv` (`status: fail`); no new Dead lock.

---

## Batch 5 Exploration Execution (2026-11-09, completed)

**Verdict:** Batch 5 completed: no win (all 5 fixture impact candidates EXT-21 through EXT-25 failed the Development Screen); Model Champion `def_xg_shrink_challenger` stands unchanged.

- **Smoke Evaluation (`ext_21` through `ext_25` — 30 variants total, all `AUDIT PASS`, zero `LEAKAGE FAIL`)**:
  - **Lane `ext_21` (`EXT-21`: Bounded Soft-Saturating Matchup Factor on Open-Play Goal Expectancy, 6 variants: $\gamma_{\text{fix}} \in [0.10, 0.22], \kappa_{\text{scale}} \in [0.8, 1.2]$)**:
    - 5 of 6 variants achieved positive mean Oracle Regret Delta: `ext_21_g22_k12` ($\Delta = +1.1651$), `ext_21_g20_k10` ($\Delta = +1.0455$), `ext_21_g18_k08` ($\Delta = +0.8525$), `ext_21_g15_k12` ($\Delta = +0.3370$), `ext_21_g15_k10` ($\Delta = +0.3041$), `ext_21_g10_k08` ($\Delta = +0.0900$).
    - However, 4 variants failed Tier 2 due to captaincy regret degradation ($+0.1720$ to $+0.2397 > +0.1500$ guardrail) or insufficient bootstrap probability ($P = 0.268$ to $0.577 < 0.65$).
    - Only `ext_21_g22_k12` passed Tier 2 ($\Delta = +1.1651, P = 0.728$).
    - Under Tier 3 full walkforward with predicted minutes, `ext_21_g22_k12` failed the Development Screen: $\Delta = -0.4082$ pts/GW, boot $P = 0.418 < 0.75$, segs 1/3, with cold-start regression ($-1.774 < -0.25$) and catastrophic early-mid regression ($-0.796 < -0.15$).
    - All 6 variants failed the Development Screen (`pass=False`). Logged as diagnostic failure in `idea_queue.csv` (`status: fail`); no new Dead lock.
  - **Lane `ext_22` (`EXT-22`: Venue-Conditioned Empirical Bayes Attacking Output Dynamics, 6 variants: $\beta_{\text{venue}} \in [0.06, 0.14], K_{\text{venue}} \in [4.0, 8.0]$)**:
    - All 6 variants failed Tier 2 Oracle Event Gate (`pass=False`, `segs=0/3`, `boot_p_gt0=0.030` to `0.176`, `combined_delta` `-0.6420` to `-1.5578`). Best variant: `ext_22_b06_k4` ($\Delta = -0.6420, P = 0.156$).
    - Multiplying player attacking rates by venue coefficients degraded formation XI lineup selection as home advantage is already implicitly absorbed in baseline outputs and match difficulty ratings.
    - All 6 variants failed the Development Screen (`pass=False`). Logged as diagnostic failure in `idea_queue.csv` (`status: fail`); no new Dead lock.
  - **Lane `ext_23` (`EXT-23`: Asymmetric Log-Linear Defensive Quality Decay for Clean Sheets, 6 variants: $\alpha_{\text{cs}} \in [0.12, 0.24], K_{\text{cs}} \in [4.0, 6.0]$)**:
    - All 6 variants achieved positive mean Oracle Regret Delta: `ext_23_a18_k6` ($\Delta = +0.6257$), `ext_23_a20_k4` ($\Delta = +0.4372$), `ext_23_a16_k4` ($\Delta = +0.2739$), `ext_23_a15_k6` ($\Delta = +0.2103$), `ext_23_a12_k4` ($\Delta = +0.0363$), `ext_23_a24_k6` ($\Delta = +0.0183$).
    - However, all 6 variants failed Tier 2 Oracle Event Gate due to severe captaincy regret degradation ($+0.2850$ to $+0.3495 > +0.1500$ guardrail) and insufficient bootstrap probability ($P = 0.414$ to $0.646 < 0.65$).
    - All 6 variants failed the Development Screen (`pass=False`). Logged as diagnostic failure in `idea_queue.csv` (`status: fail`); no new Dead lock.
  - **Lane `ext_24` (`EXT-24`: Price-Conditioned Fixture Sensitivity for Budget Midfielders and Forwards, 6 variants: $\gamma_{\text{budget}} \in [0.15, 0.35], \text{cutoff} \in [55.0, 60.0]$)**:
    - 5 of 6 variants exhibited non-positive oracle regret delta ($\Delta = +0.0000$ to $-0.4061, P = 0.000$ to $0.139$).
    - Variant `ext_24_g30_c55` achieved positive oracle delta ($\Delta = +0.1247$), but failed the bootstrap confidence threshold ($P = 0.606 < 0.65$).
    - All 6 variants failed the Development Screen (`pass=False`). Logged as diagnostic failure in `idea_queue.csv` (`status: fail`); no new Dead lock.
  - **Lane `ext_25` (`EXT-25`: Adversary Concession Profiling by Outfielder Style Contrast, 6 variants: $\xi_{\text{modality}} \in [0.08, 0.18], K_{\text{modality}} \in [360, 540]$)**:
    - All 6 variants failed Tier 2 Oracle Event Gate (`pass=False`, `segs=0/3`, `boot_p_gt0=0.010` to `0.162`, `combined_delta` `-0.0078` to `-0.6484`). Best variant: `ext_25_x08_k360` ($\Delta = -0.0078, P = 0.162$).
    - Shifting attacking expectancy between xG and xA based on fixture difficulty degraded formation XI lineup selection across all variants.
    - All 6 variants failed the Development Screen (`pass=False`). Logged as diagnostic failure in `idea_queue.csv` (`status: fail`); no new Dead lock.

---

## Batch 4 Re-evaluation Execution (2026-11-09, completed)

**Verdict:** Batch 4 re-evaluation completed (both reopened candidates `EXT-08` and `EXT-20` failed Dev under £100.0m 15-player squad + bench auto-subs metric); Model Champion `def_xg_shrink_challenger` stands unchanged.

Evaluated Batch 4 reopened candidates (`EXT-08` and `EXT-20`) against Champion `def_xg_shrink_challenger` on Dev 2025-26 (GW1-38, seed 2024-25) under aligned £100.0m 15-player squad + auto-subs metric:
- **Smoke Evaluation (`ext_08`, `ext_20` — 10 variants total, all `AUDIT PASS`, zero `LEAKAGE FAIL`)**:
  - **Lane `ext_08` (`EXT-08`: Joint own-xG/xA Process Intensity & Allocation Likelihood, 4 variants: $K_{\text{mix}} \in [2.0, 16.0]$)**:
    - All 4 variants failed Tier 2 Oracle Event Gate (`pass=False`, `segs=0/3`, `boot_p_gt0=0.000` to `0.077`, `combined_delta` `-0.0953` to `+0.0000`). Best variants: `k4`, `k8`, `k16` ($\Delta = +0.0000$, $P = 0.000$); `k2` ($\Delta = -0.0953$, $P = 0.077$). Coupling xG and xA did not improve £100.0m lineup selection. Diagnostic failure; no new Dead Lever lock; `status: fail` in queue.
  - **Lane `ext_20` (`EXT-20`: Endogenous Attacking-Role Stratification & Threat-Adaptive Shrinkage for Out-of-Position Defenders, 6 variants: $\tau_{\text{threat}} \in [12.0, 18.0], K_{\text{OOP}} \in [800, 1600], \gamma_{\text{oop}} \in [0.15, 0.25]$)**:
    - 4 of 6 variants passed Tier 2 Oracle Event Gate under £100m metric: `ext_20_t18_k800` ($\Delta = +0.3916$, $P = 0.995$), `ext_20_t18_k1200` ($\Delta = +0.3876$, $P = 0.995$), `ext_20_t15_k1200` ($\Delta = +0.2745$, $P = 0.856$), `ext_20_t15_k800` ($\Delta = +0.2745$, $P = 0.856$); `ext_20_t12_k1600` failed Tier 2 ($\Delta = +0.0258$, $P = 0.481 < 0.65$); `ext_20_t12_k1200` failed Tier 2 ($\Delta = -0.2107$, $P = 0.150$).
    - All 4 Tier 2 passers failed Tier 3 full walkforward: best variant `ext_20_t15_k800` achieved positive delta $\Delta = +0.0563$ pts/GW, but bootstrap $P(\Delta > 0) = 0.671 < 0.75$ and won 1/3 segments; `ext_20_t18_k800` and `t18_k1200` regressed to $\Delta = -0.0875$ (late segment catastrophic regression $-0.230 < -0.13$); `ext_20_t15_k1200` regressed to $\Delta = -0.2005$ ($P = 0.046$). All 6 variants failed the Development Screen (`pass=False`). Diagnostic failure; no new Dead Lever lock; `status: fail` in queue.

---

## Batch 3 Exploration Execution (2026-11-05, completed)

**Verdict:** Queue exhausted (Exit b: no win); Model Champion `def_xg_shrink_challenger` stands unchanged.

Evaluated Batch 3 (`EXT-14` through `EXT-19`) against Champion `def_xg_shrink_challenger` on Dev 2025-26 (GW1-38, seed 2024-25):
- **Ledger Screen (`dead-match`)**:
  - `EXT-15` (Territorial Possession-Tilt & Deep-Block Defcon Elasticity): Matched active Dead Lever Row 81 (`Defcon venue and opposition pressure scaling`, `revisit_after = 2027-09-30`); dropped at Step 1 and queued in Human Queue (default: no override).
  - `EXT-16` (Co-Starter Playmaker Gravity & Non-Zero-Sum Space-Creation Synergy): Matched active Dead Lever Row 56 (`Start vs sub attack intensity`, `revisit_after = 2027-09-29`); queued in Human Queue (default: no override).
  - `EXT-17` (Position-Conditioned Exponential Micro-Cycle Fatigue & Ironman Stamina Resistance): Matched active Dead Lever Row 53 / Row 83 (`Learned participation variants` / `Schedule-congestion start shift`, `revisit_after = 2027-09-28` / `2027-09-30`); queued in Human Queue (default: no override).
- **Smoke Evaluation (`ext_14`, `ext_18`, `ext_19` — 18 variants total, all `AUDIT PASS`, zero `LEAKAGE FAIL`)**:
  - **Lane `ext_14` (`EXT-14`: Continuous Match-Tempo & Counter-Transition Attack Elasticity, 6 variants)**: All 6 variants failed Tier 2 Oracle Event Gate (`pass=False`, `segs=0/3`, `boot_p_gt0=0.000`, `combined_delta` `-0.6045` to `-0.8001`). Best variant: `ext_14_a15_b06` (`alpha_tempo=0.15, beta_trans=0.06`, `combined_delta = -0.6045`). Increasing `beta_trans` monotonically degraded Oracle Formation XI regret as demeaned tempo/transition elasticity distorted attacker rankings relative to Champion `def_xg_shrink_challenger`. Logged Dead until `2027-11-05`.
  - **Lane `ext_18` (`EXT-18`: Starter-Role Conditioning & Set-Piece Share Persistence for Budget Enablers, 6 variants)**: All 6 variants failed Tier 2 Oracle Event Gate (`pass=False`, `segs=0/3`, `boot_p_gt0=0.000`, `combined_delta` `-0.2407` to `-1.1320`). Best variant: `ext_18_k540_g015` (`k_atk=540, gamma_role=0.15`, `combined_delta = -0.2407`). Stronger attacker shrinkage ($K_{\text{ATK}} \in \{630, 720\}$) and creative-share prior conditioning over-compressed attacking differentials and inflated high-creativity deep playmakers whose set-piece volume does not translate into direct goal threat (xG). Logged Dead until `2027-11-05`.
  - **Lane `ext_19` (`EXT-19`: Opponent Speculative Shot-Volume & Goalkeeper Save-Floor Elasticity, 6 variants)**: All 6 variants failed Tier 2 Oracle Event Gate (`pass=False`, `segs=0/3`, `boot_p_gt0=0.000`, `combined_delta` `-0.1279` to `-0.4712`). Best variant: `ext_19_k900_xi035` (`k_gk=900, xi_saves=0.35`, `combined_delta = -0.1279`). Scaling GKP `per90_saves` upward against high-threat opponents over-projected GKP returns in fixtures where high opponent threat converted into goals conceded rather than net fantasy points. Logged Dead until `2027-11-05`.

---

## Candidate Ideation Review (Batch 6: 2026-11-09)

Five candidate proposals received from external frontier model collaboration evaluating fixture difficulty and venue impact across scoring components:

1. **EXT-27: Venue-Decoupled Home Advantage** (`xp_goals`, `xp_assists`, `xp_clean_sheets`): Decouples league-wide home advantage factor from team-strength ratio shrinkage ($s=0.40$), preventing double-attenuation of home advantage across all clubs. Screened against dead lever `Defcon venue and opposition pressure scaling` (cleared as false positive; Defcon-specific). Status: `untested`.
2. **EXT-28: Schedule-Neutralized Attack Baselines** (`xp_goals`, `xp_assists`): De-biases historical per-90 xG/xA by dividing completed fixture output by pre-match attacking multiplier ($\tilde x = x / (1 + \phi(m-1))$), preventing double-counting easy fixture runs in shrunk baselines. Screened against dead lever `Penalty-taker signal from per90 only` (cleared as false positive; taker-specific). Status: `untested`.
3. **EXT-29: Opponent Positional Concession Share (Mean-Preserving)** (`xp_goals`, `xp_assists`): Opponent concession contrasts by MID/FWD profile normalized to zero-sum position weights. Matched active Dead Lever `Opponent conditional attacking role allocation (EXT-11)` (locked until `2027-10-28`). Status: `dead-match`.
4. **EXT-30: Component-Specific Matchup Elasticity from Team-Level Calibration Slopes** (`xp_goals`, `xp_assists`, `xp_clean_sheets`): Estimates independent $s_{\text{att}}$ and $s_{\text{def}}$ from team-level log-link regressions, capped at 0.60. Matched active Dead Lever Row 21 `Fixture swing multiplicative (s_att) and additive arms` (locked until `2027-09-24`). Status: `dead-match`.
5. **EXT-31: Opponent-Sample-Reliability Matchup Share (Promoted-Club Cold Start)** (`xp_goals`, `xp_assists`, `xp_clean_sheets`): Cold-start attenuation dampening matchup multiplier ($s_{\text{eff}} = s \cdot \hat w_{\text{pair}}$) for low-sample/promoted clubs early in season without altering established club projections. Status: `untested`.

Queue dossiers:
- [EXT-27: Venue-Decoupled Home Advantage](ideas/EXT-27-venue-decoupled-home-advantage.md)
- [EXT-28: Schedule-Neutralized Attack Baselines](ideas/EXT-28-schedule-neutralized-attack-baselines.md)
- [EXT-29: Opponent Positional Concession Share](ideas/EXT-29-opponent-positional-concession-share-mean-preserving.md)
- [EXT-30: Component-Specific Matchup Elasticity](ideas/EXT-30-component-specific-matchup-elasticity-from-team-level-calibration-slopes.md)
- [EXT-31: Opponent-Sample-Reliability Matchup Share](ideas/EXT-31-opponent-sample-reliability-matchup-share-promoted-club-cold-start.md)

---

## Candidate Ideation Review (Batch 5: 2026-11-09)

Six targeted candidate proposals generated to ensure fixture difficulty and venue gradients exert a calibrated, principled impact on player projections without repeating raw multiplier overprediction (ARCH-05) or collapsing to flat neutral multipliers. Ingested into `idea_queue.csv` and `ideas/` dossiers:

1. **EXT-21: Bounded Soft-Saturating Matchup Factor on Open-Play Goal Expectancy** (`xp_goals`): Hyperbolic tangent saturating elasticity factor ($\gamma_{\text{fix}} \in [0.10, 0.22]$) on open-play xG conditioned on rival xGC gap, with invariant penalty baseline ($0.15$ xG/90). Status: `untested`.
2. **EXT-22: Venue-Conditioned Empirical Bayes Attacking Output Dynamics** (`xp_goals`, `xp_assists`): Empirical Bayes home-away coefficient ($\beta_{\text{venue}} \in [0.06, 0.14]$) capturing the ~24% Premier League home goal advantage with geometric mean unity across balanced schedules. Status: `untested`.
3. **EXT-23: Asymmetric Log-Linear Defensive Quality Decay for Clean Sheets** (`xp_clean_sheet`, `xp_conceded`): Log-linear hazard multiplier ($\alpha_{\text{cs}} \in [0.12, 0.24]$) on pitch goal-concession intensity replacing flat linear shifts, collapsing clean-sheet probabilities non-linearly against top-tier attacks. Status: `untested`.
4. **EXT-24: Price-Conditioned Fixture Sensitivity for Budget Midfielders and Forwards** (`xp_goals`, `xp_assists`): Inverse price-band elasticity ($\le £6.0\text{m}$) elevating budget starters in favorable fixtures (+15%–30%) while preserving premium talisman projections. Status: `untested`.
5. **EXT-25: Adversary Concession Profiling by Outfielder Style Contrast** (`xp_goals`, `xp_assists`): Attacking style index ($\text{xG} / (\text{xG}+\text{xA})$) matched against opponent concession modality (threat vs creativity conceded) via bounded contrast adjustment. Status: `untested`.
6. **EXT-26: Projected Goal Margin Minutes Trim Modulation** (`xp_minutes`): Non-linear blowout hazard offset ($\psi_{\text{margin}} \in [1.5, 4.0]$ mins) trimming expected playing duration in heavily favored matches without altering $p_{\text{start}}$. Status: `untested`.

Queue dossiers:
- [EXT-21: Soft-Saturating Matchup Factor](ideas/EXT-21-bounded-soft-saturating-matchup-factor-on-open-play-goal-expectancy.md)
- [EXT-22: Venue-Conditioned Dynamics](ideas/EXT-22-venue-conditioned-empirical-bayes-attacking-output-dynamics.md)
- [EXT-23: Log-Linear Defensive Quality Decay](ideas/EXT-23-asymmetric-log-linear-defensive-quality-decay-for-clean-sheets.md)
- [EXT-24: Budget Price-Conditioned Sensitivity](ideas/EXT-24-price-conditioned-fixture-sensitivity-for-budget-midfielders-and-forwards.md)
- [EXT-25: Adversary Concession Profiling](ideas/EXT-25-adversary-concession-profiling-by-outfielder-style-contrast.md)
- [EXT-26: Goal Margin Playing Duration Trim](ideas/EXT-26-projected-goal-margin-minutes-trim-modulation.md)

---

## Candidate Ideation Review (Batch 4: 2026-11-06)

One targeted candidate proposal generated to resolve Defender Out-of-Position (OOP) attacking suppression under Champion `def_xg_shrink_challenger` ($K_{\text{DEF}} = 2400$):

1. **EXT-20: Endogenous Attacking-Role Stratification & Threat-Adaptive Shrinkage for Out-of-Position Defenders** (`xp_goals`): Stratifies defenders based on pre-deadline in-game threat volume ($\hat{\Theta}_i(g) \ge \tau_{\text{threat}}$); traditional defenders retain $K_{\text{DEF}}=2400$, while OOP attacking defenders adapt to $K_{\text{OOP}} \in [450, 900]$ and threat-elevated xG prior. Status: `untested`.

Queue dossier:
- [EXT-20: Threat-Adaptive Defender Shrinkage](ideas/EXT-20-endogenous-attacking-role-stratification-threat-adaptive-shrinkage-defenders.md)

---

## Agent Ideation Review (Batch 3: 2026-11-03)

Six candidate proposals generated against Champion `def_xg_shrink_challenger`, ADR 0066/0064 promotion gates, and 94 active Candidate Ledger dead levers. Ingested into `idea_queue.csv` and `ideas/` dossiers:

1. **EXT-14: Continuous Match-Tempo & Counter-Transition Attack Elasticity** (`xp_goals`, `xp_assists`): Point-in-time EB club tempo index + player directness score, zero-centered across active outfielders per GW. Status: `untested`.
2. **EXT-15: Territorial Possession-Tilt & Deep-Block Defcon Elasticity** (`xp_defcon`): Player-level EB defcon shrinkage ($K_{\text{defcon}} \in [900, 1500]$) combined with opponent-vs-own creative siege tilt. Status: `untested`.
3. **EXT-16: Co-Starter Playmaker Gravity & Non-Zero-Sum Space-Creation Synergy** (`xp_goals`): Strictly complementary playmaker availability synergy; reduces teammate xG when playmakers ruled out ($p_{\text{start}}=0$). Flagged dead-match on ledger row 55; pending audit.
4. **EXT-17: Position-Conditioned Exponential Micro-Cycle Fatigue & Ironman Stamina Resistance** (`xp_minutes`): Acute workload exponential kernel with player ironman resistance index; flagged dead-match on ledger row 52 / schedule provenance.
5. **EXT-18: Starter-Role Conditioning & Set-Piece Share Persistence for Budget Enablers** (`xp_goals`, `xp_assists`): Role-conditioned creative-share xG prior ($K_{\text{ATK}} \in [450, 720]$) for MID/FWD while locking $K_{\text{DEF}}=2400$. Status: `untested`.
6. **EXT-19: Opponent Speculative Shot-Volume & Goalkeeper Save-Floor Elasticity** (`xp_saves`): Restores opponent shot-threat modulation to individual goalkeeper `per90_saves` baseline. Status: `untested`.

Queue dossiers:
- [EXT-14: Continuous Match-Tempo Elasticity](ideas/EXT-14-continuous-match-tempo-counter-transition-attack-elasticity.md)
- [EXT-15: Territorial Defcon Elasticity](ideas/EXT-15-territorial-possession-tilt-deep-block-defcon-elasticity.md)
- [EXT-16: Playmaker Gravity Synergy](ideas/EXT-16-co-starter-playmaker-gravity-non-zero-sum-space-creation-synergy.md)
- [EXT-17: Micro-Cycle Fatigue Recovery](ideas/EXT-17-position-conditioned-exponential-micro-cycle-fatigue-ironman-stamina-resistance.md)
- [EXT-18: Budget Role Prior Persistence](ideas/EXT-18-starter-role-conditioning-set-piece-share-persistence-for-budget-enablers.md)
- [EXT-19: Goalkeeper Save Opportunity Elasticity](ideas/EXT-19-opponent-speculative-shot-volume-goalkeeper-save-floor-elasticity.md)

---

## Exploration execution (2026-10-28, completed)

Mode: default queue. All 13 queue ideas evaluated or screened. Fixed grids from dossiers; no widening. Dev 2025-26 GW1-38 seeded 2024-25; confirm 2024-25 seeded 2023-24; live holdout sealed.
- Five dead-matches: EXT-01, EXT-02, EXT-03, EXT-04, EXT-06 (dropped at step 1 ledger screen).
- Seven dev failures: EXT-05 (Huber panel), EXT-07 (exposure replay), EXT-08 (joint xGI allocation k2-k16; reopened 2026-11-06 per user directive), EXT-09 (binomial anchor exposure), EXT-11 (opponent role allocation lambda 25-100), EXT-12 (change detection h48/h24 phi05/10). All logged Dead in `candidate_ledger.csv` (EXT-08 now open).
- Two blocked mechanisms: EXT-10 (blocked on dead EXT-07 decoder prerequisite and absent seed hazard summaries); EXT-13 (blocked on deadline-valid schedule provenance).
- Champion `def_xg_shrink_challenger` stands unchanged. Exit (b) (verdict: no win).

Audited implementations and synthetic checks preserved in [prototypes/](prototypes/README.md). Parent independently audited manifests (`AUDIT PASS`) and ran preserved checks (`checks.py`, `checks_role.py`). Zero leakage. Full pytest suite passes; `verify.sh` passes; Ruff clean. Work Packet: `.agents/work-packets/explore-candidate-candidate-ideation.md`; handoff pointer committed.

<!-- exploration-results:start -->
## Completed development evidence

Generated from [smoke_results.csv](smoke_results.csv), keyed by `variant`; cached columns `combined_delta`, `segs`, `boot_p_gt0`, `guardrails_passed`, `pass`. Full failed-mechanism reasons retained in companion. Partial grid rows never imply whole-lane verdict.

- `ext_05_n3000_n7000_d120_l100`: FAIL; dev 2025-26 GW1-38; delta -1.003553 points/GW; 1/3 segments; bootstrap P 0.01160; guardrails False.
- `ext_05_n3500_n7500_d150_l100`: FAIL; dev 2025-26 GW1-38; delta -1.003553 points/GW; 1/3 segments; bootstrap P 0.01160; guardrails False.
- `ext_05_n3500_n7500_d135_l50`: FAIL; dev 2025-26 GW1-38; delta -1.003553 points/GW; 1/3 segments; bootstrap P 0.01160; guardrails False.
- `ext_05_n4000_n8000_d135_l75`: FAIL; dev 2025-26 GW1-38; delta -1.003553 points/GW; 1/3 segments; bootstrap P 0.01160; guardrails False.
- `ext_09_binomial_fixture_exposure`: FAIL; dev 2025-26 GW1-38; delta +0.000000 points/GW; 0/3 segments; bootstrap P 0.00000; guardrails True.
- `ext_07_replay_final_states`: FAIL; dev 2025-26 GW1-38; delta -0.605263 points/GW; 0/3 segments; bootstrap P 0.20845; guardrails False.
- `ext_11_role_l100`: FAIL; dev 2025-26 GW1-38; delta -0.170921 points/GW; 0/3 segments; bootstrap P 0.00000; guardrails False.
- `ext_11_role_l50`: FAIL; dev 2025-26 GW1-38; delta -0.436974 points/GW; 0/3 segments; bootstrap P 0.00000; guardrails False.
- `ext_11_role_l25`: FAIL; dev 2025-26 GW1-38; delta -0.867500 points/GW; 0/3 segments; bootstrap P 0.00000; guardrails False.
- `ext_12_h48_phi10`: FAIL; dev 2025-26 GW1-38; delta +0.000000 points/GW; 0/3 segments; bootstrap P 0.00000; guardrails False.
- `ext_12_h24_phi05`: FAIL; dev 2025-26 GW1-38; delta +0.000000 points/GW; 0/3 segments; bootstrap P 0.00000; guardrails False.
- `ext_12_h48_phi05`: FAIL; dev 2025-26 GW1-38; delta +0.000000 points/GW; 0/3 segments; bootstrap P 0.00000; guardrails False.
- `ext_12_h24_phi10`: FAIL; dev 2025-26 GW1-38; delta +0.000000 points/GW; 0/3 segments; bootstrap P 0.00000; guardrails False.
- `track_a_h1_only`: FAIL; dev 2025-26 GW1-38; delta -0.285921 points/GW; 0/3 segments; bootstrap P 0.74215; guardrails False.
- `track_a_h3_only`: FAIL; dev 2025-26 GW1-38; delta -0.137763 points/GW; 0/3 segments; bootstrap P 0.00000; guardrails True.
- `track_a_mins_h1_h3`: FAIL; dev 2025-26 GW1-38; delta -0.502632 points/GW; 0/3 segments; bootstrap P 0.50385; guardrails False.
- `track_a_group_b_assists`: PASS; dev 2025-26 GW1-38; delta +0.287500 points/GW; 1/3 segments; bootstrap P 0.78905; guardrails True.
- `track_a_mins_h1_h3_coherent`: FAIL; dev 2025-26 GW1-38; delta -1.583947 points/GW; 0/3 segments; bootstrap P 0.04190; guardrails False.
- `track_a_no_goals_h1_h3_b`: FAIL; dev 2025-26 GW1-38; delta -0.276053 points/GW; 0/3 segments; bootstrap P 0.69955; guardrails False.
- `ext_14_a10_b08`: FAIL; dev 2025-26 GW1-38; delta -0.627763 points/GW; 0/3 segments; bootstrap P 0.00000; guardrails False.
- `ext_14_a14_b10`: FAIL; dev 2025-26 GW1-38; delta -0.800132 points/GW; 0/3 segments; bootstrap P 0.00000; guardrails False.
- `ext_14_a18_b12`: FAIL; dev 2025-26 GW1-38; delta -0.800132 points/GW; 0/3 segments; bootstrap P 0.00000; guardrails False.
- `ext_14_a12_b15`: FAIL; dev 2025-26 GW1-38; delta -0.800132 points/GW; 0/3 segments; bootstrap P 0.00000; guardrails False.
- `ext_14_a08_b12`: FAIL; dev 2025-26 GW1-38; delta -0.668158 points/GW; 0/3 segments; bootstrap P 0.00000; guardrails False.
- `ext_14_a15_b06`: FAIL; dev 2025-26 GW1-38; delta -0.604474 points/GW; 0/3 segments; bootstrap P 0.00000; guardrails False.
- `ext_18_k540_g022`: FAIL; dev 2025-26 GW1-38; delta -0.325789 points/GW; 0/3 segments; bootstrap P 0.00000; guardrails False.
- `ext_18_k540_g015`: FAIL; dev 2025-26 GW1-38; delta -0.240658 points/GW; 0/3 segments; bootstrap P 0.00000; guardrails False.
- `ext_18_k630_g018`: FAIL; dev 2025-26 GW1-38; delta -0.626579 points/GW; 0/3 segments; bootstrap P 0.00000; guardrails False.
- `ext_18_k720_g020`: FAIL; dev 2025-26 GW1-38; delta -1.131974 points/GW; 0/3 segments; bootstrap P 0.00000; guardrails False.
- `ext_18_k450_g015`: FAIL; dev 2025-26 GW1-38; delta -0.370789 points/GW; 0/3 segments; bootstrap P 0.00000; guardrails False.
- `ext_18_k630_g012`: FAIL; dev 2025-26 GW1-38; delta -0.999079 points/GW; 0/3 segments; bootstrap P 0.00000; guardrails False.
- `ext_19_k720_xi030`: FAIL; dev 2025-26 GW1-38; delta -0.267632 points/GW; 0/3 segments; bootstrap P 0.00000; guardrails False.
- `ext_19_k720_xi045`: FAIL; dev 2025-26 GW1-38; delta -0.357105 points/GW; 0/3 segments; bootstrap P 0.00000; guardrails False.
- `ext_19_k900_xi035`: FAIL; dev 2025-26 GW1-38; delta -0.127895 points/GW; 0/3 segments; bootstrap P 0.00000; guardrails False.
- `ext_19_k900_xi050`: FAIL; dev 2025-26 GW1-38; delta -0.217368 points/GW; 0/3 segments; bootstrap P 0.00000; guardrails False.
- `ext_19_k540_xi035`: FAIL; dev 2025-26 GW1-38; delta -0.278158 points/GW; 0/3 segments; bootstrap P 0.00000; guardrails False.
- `ext_19_k1080_xi040`: FAIL; dev 2025-26 GW1-38; delta -0.471184 points/GW; 0/3 segments; bootstrap P 0.00000; guardrails False.
- `ext_20_t12_k1600`: FAIL; dev 2025-26 GW1-38; delta -0.215526 points/GW; 0/3 segments; bootstrap P 0.12340; guardrails False.
- `ext_20_t15_k800`: FAIL; dev 2025-26 GW1-38; delta +0.066842 points/GW; 0/3 segments; bootstrap P 0.59890; guardrails False.
- `ext_20_t12_k1200`: FAIL; dev 2025-26 GW1-38; delta -0.777632 points/GW; 0/3 segments; bootstrap P 0.00000; guardrails True.
- `ext_20_t18_k1200`: FAIL; dev 2025-26 GW1-38; delta -0.215263 points/GW; 0/3 segments; bootstrap P 0.00000; guardrails True.
- `ext_20_t18_k800`: FAIL; dev 2025-26 GW1-38; delta -0.215263 points/GW; 0/3 segments; bootstrap P 0.00000; guardrails True.
- `ext_20_t15_k1200`: FAIL; dev 2025-26 GW1-38; delta -0.365921 points/GW; 0/3 segments; bootstrap P 0.00110; guardrails True.
- `ext_08_k2`: FAIL; dev 2025-26 GW1-38; delta +0.000000 points/GW; 0/3 segments; bootstrap P 0.00000; guardrails False.
- `ext_08_k4`: FAIL; dev 2025-26 GW1-38; delta +0.000000 points/GW; 0/3 segments; bootstrap P 0.00000; guardrails False.
- `ext_08_k8`: FAIL; dev 2025-26 GW1-38; delta -0.042500 points/GW; 0/3 segments; bootstrap P 0.66535; guardrails True.
- `ext_08_k16`: FAIL; dev 2025-26 GW1-38; delta -0.231974 points/GW; 0/3 segments; bootstrap P 0.03445; guardrails True.

<!-- exploration-results:end -->

## Agent Ideation Review (Batch 2: 2026-10-28)

Three independent specialist reviews; lanes: minutes/budget starters, attacking events, defensive/GKP events. Full prompt plus all 93 ledger rows screened. Reports contain eight specialist proposals; shared exposure reconstruction merged into one mechanism, leaving seven unique hypotheses. Ranking below reflects source evidence and implementation feasibility, never measured predictive improvement.

1. **Exposure-coherent participation reconstruction**: First investigate deterministic correctness. Late ML writes final participation/minutes and `xp_minutes`, while event values remain copied from earlier `champ_proj`; attack multipliers act on those earlier values. Replay unchanged scoring links at final coherent states, preserving rates and GW1-19 fallback. Minutes and defense agents found same path independently. Before any experiment, resolve probability simplex, capped conditional-duration/P(60) semantics, inherited effective rate transformations, and single bonus allocation. See [source assembly](../../../models/ml_component_challenger.py#L366).
2. **Joint xGI intensity and allocation**: First standalone event-rate hypothesis. Joint own xG/xA process model shares information between total involvement and shooter/creator allocation. Nonzero cross-signal derivative distinguishes proposal from independent scalar shrinkage. Existing history sufficient; four proposed variants. Untested generalized likelihood and prior coupling remain risks.
3. **Binomial fixture opportunities in inherited start anchor**: Replace player-GW any-start Bernoulli target with starts out of observed fixture opportunities. Active causal panel already fixture-level; proposal targets inherited learned-start anchor only. Singleton variant; effect may be narrow or absorbed by existing mass preservation/H1. Never infer missing rows as DNP.
4. **Full-duration survival likelihood**: Replace H3 duration-offset likelihood with censored starting-duration survival model; derive mean minutes and P(60) jointly. Distinct from direct Beta-binomial threshold fit. Requires explicit immutable seed-hazard summaries and coherent decoder; four proposed variants. Short-panel uncertainty remains unresolved.
5. **Opponent conditional attacking-role allocation**: Relative opponent-by-attacker-profile concession signal, with total attacking expectation preserved. Distinctness depends on conditional role contrasts, not scalar opponent strength. Three proposed variants. Coarse profiles, schedule composition, and final normalization ordering require care.
6. **Sequential attacking-opportunity change detection**: Continuous xG/xA rate-change likelihood against stationary reference. Four proposed variants; highest numerical/false-change risk among event proposals. No participation HMM or fixed-decay retune.
7. **Habit-adjusted cumulative playing dose**: Deferred pending schedule provenance. Actual recent played-minute dose relative to habitual exposure supplies proposed new signal, beyond fixed rest-day congestion shift. Historical scheduled dates must have been known at each deadline; final archive schedule alone insufficient. Missing provenance requires fallback or separately specified deadline-only dose. Four variants remain paper specification, not executable queue work.

### Source corrections and decision

Default Champion uses `clip((GW-3)/5, 0, 1)`, already full weight at GW20; documented five-GW late ramp is not executed. Active constructor leaves `use_neff_alpha=False`; continuous N_eff helper is optional. Prompt corrected without model behavior change. Warm seed enters feature construction; model-fit history must not be assumed to contain raw prior-season rows.

Decision: seven deduplicated hypotheses added to queue with full dossiers, source context, and mechanism audits. Six `untested`; workload `blocked (historical schedule provenance)`. Survival carries `after:EXT-07`; prerequisite failure never authorizes stacking a dead lever. Prior six verdict rows preserved. No candidate implementations, empirical runs, ledger verdicts, or holdout inspection. Mechanism screens provisional until implementation matches stated distinctions; recheck authoritative ledger before experimentation.

Queue dossiers, in priority order:

- [EXT-07: Exposure reconstruction](ideas/EXT-07-exposure-coherent-participation-reconstruction.md).
- [EXT-08: Joint xGI intensity/allocation](ideas/EXT-08-joint-xgi-intensity-and-allocation.md).
- [EXT-09: Binomial fixture opportunities](ideas/EXT-09-binomial-fixture-exposure-for-the-inherited-start-anchor.md).
- [EXT-10: Duration survival](ideas/EXT-10-full-duration-survival-likelihood-for-starting-players.md), after EXT-07.
- [EXT-11: Opponent role allocation](ideas/EXT-11-opponent-conditional-attacking-role-allocation.md).
- [EXT-12: Opportunity change detection](ideas/EXT-12-sequential-attacking-opportunity-change-detection.md).
- [EXT-13: Habit-adjusted playing dose](ideas/EXT-13-habit-adjusted-cumulative-playing-dose.md), blocked.

Priority: deterministic state/exposure audit, then joint xGI coupling. Treat remaining mechanisms independently; shared decoder prerequisite must not conceal incremental effects of new estimated heads. Expected gains, occurrence frequency of state inconsistencies, and promotion success unknown.

Reproduce: regenerate prompt, read three named agent reports and current ledger, recheck referenced source paths, consolidate shared mechanism once. Preserve GW1-19 parity, confirmation freeze, and sealed 2026-27 GW6+ boundary. Report contains no new empirical metric cache.

## Queue Exploration Verdict (Batch 1: 2026-10-26)

**Verdict:** Queue exhausted (Exit b: no win); Model Champion `adaptive_causal_challenger` stands unchanged.

### Queue Status & Results Summary

| Order | Idea ID | Component | Mechanism | Status | dev combined_delta | segs | boot P | Nearest Ledger Row / Verdict |
|---|---|---|---|---|---|---|---|---|
| 1 | `EXT-01` | `xp_minutes` | Asymmetric Conditional Substitution Hazard & Beta-Binomial 60-Min Survival | `dead-match` | — | — | — | Dead Row 61: `Empirical-Bayes P(60\|state) Beta-binomial` (revisit 2027-09-29) |
| 2 | `EXT-02` | `xp_goals` | State-Decoupled Cameo Event Intensity & Late-Game Fatigue | `dead-match` | — | — | — | Dead Row 11: `Assist finishing offsets (goals+assists pooled)` (revisit 2027-09-28) |
| 3 | `EXT-03` | `xp_assists` | Leave-One-Out Teammate Receiver Finishing Multiplier | `dead-match` | — | — | — | Dead Row 11: `Assist finishing offsets (goals+assists pooled)` (revisit 2027-09-28) |
| 4 | `EXT-04` | `xp_saves` | Shot-Quality Decoupled Goalkeeper Save Volume | `dead-match` | — | — | — | Dead Row 72: `Club SoT volume x pooled save rate` (revisit 2027-09-29) |
| 5 | `EXT-05` | `xp_minutes` | Price-Stratified Huber Causal Panel + Continuous $N_{\text{eff}}$ Ramp | `fail` | −1.0036 | 1/3 | 0.0116 | All 4 variants failed dev; early_mid catastrophic regression (−2.643 < −0.15) |
| 6 | `EXT-06` | `xp_defcon` | Opponent Possession-Adjusted Defcon Threshold Survival | `dead-match` | — | — | — | Dead Row 81: `Defcon venue and opposition pressure scaling` (revisit 2027-09-30) & ARCH-12 |

---

## Detailed Findings: EXT-05 (Lane `ext_05`)

### Hypothesis & Formulation

`EXT-05` attempted to address potential budget-enabler misranking under the £83.5m Constrained Legal Formation XI by:
1. Replacing global squared-error Ridge with L2-penalized Huber regression ($\delta \in [1.20, 1.50]$) on player duration offsets.
2. Partitioning players into 3 price tiers (Budget $\le £5.5\text{m}$, Mid $£5.6\text{m}–£7.9\text{m}$, Premium $\ge £8.0\text{m}$) and centering ML adjustments within each tier on playable assets.
3. Replacing the discrete GW 20 step ramp in `adaptive_causal_challenger` with continuous effective sample-size blending $N_{\text{eff}, g} = 0.5 N_{\text{seed}} + N_{\text{in\_season}, <g}$ with $N_{\min} \in [3000, 4000]$ and $N_{\text{full}} \in [7000, 8000]$.

### Empirical Results (Dev Season 2025–26 GW1–38)

| Variant | $N_{\min}$ | $N_{\text{full}}$ | Huber $\delta$ | L2 $\lambda$ | dev combined_delta | segs | boot P | Guardrails | Reasons |
|---|---|---|---|---|---|---|---|---|---|
| `ext_05_n3000_n7000_d120_l100` | 3000 | 7000 | 1.20 | 100.0 | −1.0036 | 1/3 | 0.0116 | FAIL | early_mid catastrophic regression (−2.643 < −0.15); xMins MAE regressed |
| `ext_05_n3500_n7500_d150_l100` | 3500 | 7500 | 1.50 | 100.0 | −1.0036 | 1/3 | 0.0116 | FAIL | early_mid catastrophic regression (−2.643 < −0.15); xMins MAE regressed |
| `ext_05_n3500_n7500_d135_l50` | 3500 | 7500 | 1.35 | 50.0 | −1.0036 | 1/3 | 0.0116 | FAIL | early_mid catastrophic regression (−2.643 < −0.15); xMins MAE regressed |
| `ext_05_n4000_n8000_d135_l75` | 4000 | 8000 | 1.35 | 75.0 | −1.0036 | 1/3 | 0.0116 | FAIL | early_mid catastrophic regression (−2.643 < −0.15); xMins MAE regressed |

### Root Cause Analysis

In a warm-seeded regime ($N_{\text{seed}} \approx 7600$), effective sample size $N_{\text{eff}, g} = 0.5(7600) + N_{\text{in\_season}} \ge 3800$ immediately crosses $N_{\min} = 3500$ in the opening gameweeks. Consequently, continuous $N_{\text{eff}}$ shrinkage activates within-season ML models during the `early_mid` window (GW5–19).

Even with Huber regularization and price-tier centering, within-season causal ML features (such as 6-GW rolling starts, early hook rates, and short turnaround indicators) are highly non-stationary across early gameweeks due to squad rotation, cup fixtures, and managerial tactics. Activating ML before round-robin schedule completion (>19 matches) induces severe captaincy regret and minutes volatility ($\Delta_{\text{early\_mid}} = -2.643$ pts/GW, xMins MAE 13.81 vs 13.65).

This reinforces the core architecture of Model Champion `adaptive_causal_challenger`: 100% Champion stability across GW1–19 is mathematically necessary to protect against short-panel volatility.

The lever is logged as **Dead** in `docs/research/candidate-ledger/candidate_ledger.csv` (`revisit_after = 2027-10-26`).

---

## Metrics Documentation

### 1. Combined Regret Delta ($\Delta_{\text{combined}}$)
- **Definition**: Difference in Blended Constrained Legal Formation XI Regret between Champion and Candidate: $\Delta = \overline{\text{Regret}}_{\text{champ}} - \overline{\text{Regret}}_{\text{cand}}$.
- **Direction**: Higher $\uparrow$ is better (positive indicates Candidate achieves lower regret than Champion).
- **Ideal Benchmark**: $\Delta > 0.0$ pts/GW with no minimum effect (ADR 0049, ADR 0064).

### 2. Moving Block Bootstrap Probability ($P(\Delta > 0)$)
- **Definition**: Non-wrapping paired Moving Block Bootstrap probability ($L=5$ blocks, 20,000 draws, seed 0) that paired weekly regret difference is strictly positive.
- **Direction**: Higher $\uparrow$ is better.
- **Ideal Benchmark**: $P \ge 0.75$ on Dev season, $P \ge 0.65$ on Confirmation season, $P \ge 0.85$ Pooled Stratified (ADR 0064).

### 3. Non-Catastrophic Segment Loss Floors
- **Definition**: Segment-level regret delta evaluated across three seasonal partitions:
  - Cold Start (GW1–4): $\Delta \ge -0.25$ pts/GW
  - Early-Mid (GW5–19): $\Delta \ge -0.15$ pts/GW
  - Late (GW20–38): $\Delta \ge -0.13$ pts/GW
  - Active-Window In-Season Win: $\max(\Delta_{\text{early\_mid}}, \Delta_{\text{late}}) > 0$
- **Direction**: Higher $\uparrow$ is better.
- **Ideal Benchmark**: All segment floors satisfied with $\ge 1$ active in-season win.

---

## Sources & Ideation Pipeline

- **Primary**: Frontier LLM Collaborations via structured prompt briefs.
- **Repository data**: [`candidate_ledger.csv`](../candidate-ledger/candidate_ledger.csv), [`config/model_selection.json`](../../config/model_selection.json), [`backtesting/promotion.py`](../../backtesting/promotion.py).

```mermaid
flowchart LR
    State["Repo State\n(Champion, Dead Levers, ADR 0064 Gate)"] --> GenPrompt["generate_prompt.py\n(Dynamic Prompt Builder)"]
    GenPrompt --> PromptFile["candidate_model_ideation_prompt.md"]
    PromptFile --> ExtLLM["Frontier language-model review"]
    ExtLLM --> Response["Raw Model Ideas"]
    Response --> Ingest["ingest_ideas.py\n(Schema & Dead-Lever Validator)"]
    Ingest --> Queue["idea_queue.csv\n(explore-candidate Default Queue)"]
    Queue --> ExploreSkill["/explore-candidate\n(Autonomous Smoke & Gating)"]
```

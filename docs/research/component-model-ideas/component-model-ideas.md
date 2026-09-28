# Component model ideas (idea backlog for explore-candidate)

**Updated**: 2026-09-29T02:50:00+07:00  
**Data stamp**: Code at `730e831`; archives 2024-25 + 2025-26 (`data/archive/*/processed`); smoke/gate runs 2026-09-29 vs `learned_start_challenger`  
**Season**: Multi-season (dev 2025-26, confirm 2024-25; 2026-27 GW6+ sealed)  
**Status**: Active — Queue batches 1–2 done (10 ideas); ATK-05 promoted (ADR 0051); 19 rows untested vs new Champion  
**Purpose**: Per ledger component: how Champion models it today + new model ideas, queued for `explore-candidate` Queue mode runs until all tried  
**Scope**: All 13 `LEDGER_COMPONENTS` + `projected_minutes`. Excludes Dead-ledger mechanisms, solver, fixture-scale Open row (Dual-Vector shrunk)  
**Related**: [Candidate Ledger](../candidate-ledger/candidate-ledger.md) · [Eval canon](../INDEX.md) · [champion-component-gap](../champion-component-gap/champion-component-gap.md) · [dual-lane-candidate-search](../dual-lane-candidate-search/dual-lane-candidate-search.md)  
**Artifact**: [component_list.csv](component_list.csv) (component → Champion form, inputs, `mse_share_2025_26_hold_chase`, `idea_ids`) · [idea_queue.csv](idea_queue.csv) (`order`, `tier`, `status`, `ledger_result` — work queue)

## Sources

- **Repository code**: `models/learned_start_challenger.py`, `multi_feature_assist_challenger.py`, `face_value_challenger.py`, `hold_chase_challenger.py`, `calibrated_matchup_hybrid.py`, `participation_state_hybrid.py`, `metrics_component_hybrid.py`, `scoring_matrix.py`; `features/builder.py`, `features/matchup_share.py`; `backtesting/walkforward.py` — cutoff 2026-09-28
- **Repository data**: `champion-component-gap/component_gap_summary.csv` `mse_share` (model `hold_chase_challenger`, 2025-26, `pool=all`, `position=ALL`); ledger `candidate_ledger.csv`
- **Subagent exploration** (4 read-only lanes, 2026-09-28): minutes, attack, defence, bonus/cards + Feature Contract inventory

**Source boundary**: Code facts spot-verified this session (bonus T 6.0 on participation-mixed `xbps`; GC NegBin r=3 vs CS Poisson; CS exposure = mean start minutes; `per90_bonus` / `per90_clean_sheets` unused by Champion lineage; `mse_share` values). Per-idea evidence numbers (ratios, dispersion, split-half r) = subagent in-memory aggregates, **unvalidated** — re-derive inside smoke prototype before trusting.

## Agent Prompt

```text
/explore-candidate docs/research/component-model-ideas/idea_queue.csv
```

Skill Queue mode owns batching, `conflicts_with`, Stack protocol, row `status` updates (`.agents/skills/explore-candidate/SKILL.md`). Ruling on `needs ruling` row → user edits `status` to `untested`.

## Method

**Method type**: Code trace + source synthesis (no backtest)

**Procedure**:
1. Trace Champion lineage per component (file:line).
2. Inventory Feature Contract (66 cols) + `history_df` (37 cols 2025-26) as-of safety.
3. Screen each candidate mechanism vs ledger Dead/Shipped rows by mechanism.
4. Per surviving idea: mechanism, inputs, hook, nearest ledger row + why different, confirm-season informativeness, fixed grid.

**Definitions**: tier `P1` strongest evidence + informative on both gate seasons; `P2` plausible; `P3` weak / small effect; `RULING` Dead-adjacent (user must rule before smoke); `HOLDOUT` defcon-only (2024-25 has no defcon → confirm uninformative).

### Metric Definitions & Direction

| Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|---|---|---|---|---|---|
| Component MSE share | `mse_share` | $\mathrm{mean}(e_c\cdot e)/\mathrm{mean}(e^2)$ on Realized ledger | Context (rank by magnitude) | `component_list.csv` `mse_share_2025_26_hold_chase` | Which component drives squared error; prioritisation only, not gate |
| Gate delta | `combined_delta` | Blended `top_11_regret` Champion − Candidate | Higher $\uparrow$ | > 0, boot P ≥ 0.60 dev + confirm, ≥2/3 segs | Promotion primary (ADR 0049) |

**Validation boundary**: `mse_share` measured on former Champion `hold_chase_challenger`, not recomputed for `learned_start_challenger`.

## Findings — component list (Champion today)

Full table: [component_list.csv](component_list.csv). Summary (2025-26 `mse_share`, `hold_chase_challenger`):

| Component | Champion form (owner) | `mse_share` |
|---|---|---|
| `xp_goals` | xG/90 + minute-pooled finishing offset K1800; hold_chase sharp tilt; matchup additive (`face_value_challenger`) | 0.327 structural |
| `xp_clean_sheet` | exp(−λ·mean start mins/90)·p60 Poisson (`calibrated_matchup_hybrid`) | 0.177 |
| `xp_bonus` | Plackett-Luce, logits `xbps`/6 on participation-mixed `xbps`, weight P(60+), pool 6 (`learned_start_challenger`) | 0.155 |
| `xp_minutes` / `projected_minutes` | state mix; ridge-logistic p_start GW≥5 mass-preserved (`learned_start_challenger`) | 0.145 |
| `xp_assists` | ridge Poisson GLM on Official xA (`multi_feature_assist_challenger`) | 0.104 |
| `xp_defcon` | 2·P(NegBin ≥ 10/12), pooled r 8.5/7.0 | 0.062 |
| `xp_conceded` | −E[⌊X/2⌋], X ~ NegBin r=3 | 0.013 structural |
| `xp_saves`, `xp_penalties_saved`, `xp_own_goals`, cards, `xp_penalties_missed` | per90 rate × mins, 360-min shrink | ≤ 0.006 each |

**Structural observations (drive ideas):**
- Bonus counts participation twice: mixed `xbps` in logit **and** P(60) mass weight → mins_60 bonus under-projection.
- CS uses Poisson, GC uses NegBin r=3 on same λ — inconsistent; data suggests goals-against not overdispersed.
- CS exposure = mean minutes over all starts, incl. early exits.
- From GW5 builder `p_start` only sets start-mass total; per-player ranking = learned model. Builder-side p_start levers mostly inert after GW4; `p_60_*`, `xmins_*`, `p_sub_in` still builder.
- No suspension logic anywhere; backtest `chance_of_playing` = 100 (no snapshots).
- Penalty isolation inert in backtest (`penalties_order` terminal → dropped).
- Unused as-of-safe columns: `history.bps`, `bonus`, `influence`, `team_h_score`/`team_a_score`, `yellow_cards`/`red_cards` (raw), `clean_sheets`, `expected_goals_conceded` (string in 2025-26 → `pd.to_numeric`), `defensive_contribution`, `kickoff_time`; `features.per90_bonus`, `per90_clean_sheets`, `now_cost`.
- Missing data: shots, touches, fouls, referee, lineups, set-piece order history, event timing, target-fixture `kickoff_time` in features, 2024-25 defcon.

## Findings — idea list

Queue order + status: [idea_queue.csv](idea_queue.csv). Detail below. Evidence numbers unvalidated (see Source boundary).

### Minutes / participation

**MIN-01 Suspension ledger (P1).** Rule-based DNP hazard from as-of history: 5th PL yellow by GW19 → miss next club fixture; 10th by GW32 → miss next two; red → DNP prob h1/h2/h3 for next 3 fixtures. `p_dnp += h·(p_start+p_sub_in)`, others scaled (1−h). Hook: post-step after `blend_states`. Evidence: 5th-yellow → next DNP 44/44 (2024-25), 23/23 (2025-26); red → 0.85/0.37/0.33. Learned lags see recent start → rate suspended players high. Also fixes live multi-GW horizon (hard DNP only immediate GW). Not Dead post-absence/benched hazard (disciplinary count, not absence state). Risk: cup-served bans, appeals invisible.

**MIN-02 Empirical-Bayes P(60|state) (P1).** Beta-binomial `(k + n0·p_pos)/(n + n0)`, n0 per position by method of moments (≈5–8 DEF/MID, FWD higher; GKP → pool). Builder pseudo-count ≈0.3–0.5 starts + 3-start window → noisy. Overwrites `p_60_if_*` → flows to `xp_minutes`, CS eligibility, bonus weight. `xmins_*` untouched (not Dead xMins compression).

**MIN-03 Route displaced start mass to bench (P2).** Start-mass cuts currently go 100% to DNP; empirically ~45% of started-last-not-this became subs. Route share r to `p_sub_in`. Risk: xMins up → |bias| guardrail.

**MIN-04 Incumbent-return displacement (P2).** Zero-sum club × position: incumbent back after 2+ DNPs takes start mass from stand-ins (stand-in start rate 0.85 → ~0.60 on return). Not Dead return ramp (cross-player). Risk: position coarse (CB vs FB).

**MIN-07 Schedule-congestion start shift (P3, blocked).** Log-odds shift for <3.5 rest days after mass preservation. Needs new `features.kickoff_time`.

**MIN-05 GKP slot accounting (RULING).** Club GKP start probs sum to 1 per fixture. Form close to Dead per-club mass.

**MIN-06 Latent-role HMM (RULING).** Hidden roles with EM transitions replace ridge-logistic. Same inputs as Dead learned participation variants; new form.

### Attack

**ATK-01 Position FPL-assist conversion (P1).** FPL awards more assists than xA: A/xA ≈ DEF 1.1–1.3, MID 1.35, FWD 2.1 (both seasons). Multiply GLM rate by `1 + α(c_pos − 1)`, c_pos as-of shrunk. Not Dead per-player assist offsets. Risk: +≈0.01 mean → |bias| edge; mass-neutral variants in grid. Check 2024-25 assist rule differences.

**ATK-02 Club-coherent assist mass (P2).** League assists/goal ≈0.92 vs xA/xG ≈0.64; Champion ≈0.66. Club-fixture assist mass = ρ·Σ projected goals, allocated by GLM rate × xMins. Mutually exclusive with ATK-01.

**ATK-03 Start vs sub attack intensity (P1).** Sub per90 xG/xA 1.2–1.7× start (pooled by position). Split player pooled rate into start/sub rates via pooled ratio ρ. Cameo-heavy players currently overrated when projected to start. Not Dead venue-split (pooled ratio, not per-player split).

**ATK-04 Position-specific rate shrink K (P1).** Split-half reliability of xG/90: DEF r≈0.3 (K≈2600–3400), FWD K≈560–1860, MID ≈ current 360. DEF goals = 6 pts → noisy DEF xG = optimizer's-curse picks. Apply via ratio on `per90_xg` (keeps matchup addon). Not Dead finishing K (rate, not offset).

**ATK-05 Club × position rate prior (P2).** Club-pooled DEF xG/90 split-half r ≈0.5–0.6 vs player ≈0.3 (set-piece structure). Gate separately from ATK-04.

**ATK-06 Teammate-absence share redistribution (P3).** Absent players' expected club xG share → present same-group teammates. Weak in backtest (absence only via learned p_start).

**ATK-07 Penalty-miss de-noising (P2).** One miss → ~−0.1/match forever for takers. Pool or heavy shrink. `mse_share` 0.0006 → small.

### Defence / goalkeeper

**DEF-01 One fitted goals-against distribution (P1).** Team goals-against var/mean ≈1.0; conditional on xGC bin var/mean 0.6–0.8 (underdispersed). Keep λ; same family (COM-Poisson ν ≥ 1) for P(0) and E[⌊X/2⌋]; drop GC NegBin r=3. CS over-projected GK/DEF +0.02, GC over-penalised. Not Dead k_cs/k_gc (non-uniform, λ untouched). Dixon-Coles ruled out (marginal P(0) unchanged).

**DEF-02 CS exposure over 60+ starts (P1).** CS scoring needs 60+; exposure should be E[mins | start, 60+] (≈85 vs 82 mean; rotation-prone 78 vs 70). GC exposure unchanged. Player-specific, xMins untouched.

**DEF-05+06 Rare-event pooled rates (P2 bundle).** Pen saves (only 11–14 GKP saves/season; one save → ~0.9 pts/90 inflation; bias +0.0055) and own goals: heavy shrink to as-of league rate.

**DEF-08 Club SoT volume × pooled save rate (P3, flag).** Saves = club shots-on-target faced (saves+GC)/90 × shrunk save rate. Keeper save-rate spread ≈ binomial noise. Same pooling class as Dead club-pooled GC → flag before smoke.

**DEF-09 Back-line personnel λ adjust (P3).** λ × exp(β·absent regular back-line share). New signal; weak in backtest.

**DEF-03 Defcon within-player dispersion + minutes mixture (HOLDOUT).** Current r reproduces pooled spread; within-player var/mean ≈1.36 → r≈20. Integrate over 60+ vs early-exit path.

**DEF-04 Defcon Beta-binomial hit rate (HOLDOUT).** Learn hit frequency directly, prior = NB-implied p0.

**DEF-07 Defcon venue + opposition pressure (HOLDOUT).** DEF away +8% defcon count; pooled venue ratio × opp xG^β.

### Bonus / cards

**BON-01 State-conditional bonus logits (P1).** Remove double participation count: logit on start-state `xbps` (and sub-state entrant), weight stays P(60). Targets mins_60 bonus bias −0.106 (DEF/MID). Fixture total fixed → |bias| safe. Not Dead T sweep (only moves p_start < 1 players).

**BON-03 Result-coupled two-stage pool (P2).** P(W/D/L) via Skellam from team λ; shrunk team share of bonus given result; within-team Plackett-Luce. Winners take ~65% of bonus.

**BON-02 Correlated Monte-Carlo BPS rank (P2).** Per-fixture draws: team goals → scorers, shared CS, defcon, saves, states; BPS with Champion weights; mean Plackett-Luce. Not Dead heteroscedastic Normal (correlated discrete team events). Runtime risk.

**BON-04 Fitted Plackett-Luce rank model (RULING).** Ridge utility by PL likelihood on observed top-3 BPS; adds `bps`/`influence` history. Highest collision risk with Dead calibrated weights / residual BPS.

**CRD-02 Pooled red-card rate (P2).** One red → rate up to 0.12/90 vs median 0.002 → −0.36 xP can drop player from top-11. Pool, K ≥ 9000.

**CRD-01 EB yellow rate fitted K (P3).** DEF split-half r 0.25 → 360-min shrink too weak. Method-of-moments K.

**CRD-03 Minutes-state + venue card hazard (P3).** Sub yellow per appearance 0.06–0.08 vs linear 0.036; away 0.16 vs home 0.13. Stack with CRD-01/02.

### Rejected directions (Dead or inert)

Team-goal share × team λ (Dead scoreline / team λ) · prior-season seed blending (ADR 0024; 2024-25 no seed) · NegBin/haul goals (xp_goals linear → no top-11 effect) · GBM/ranking loss on same signals (Dead GLM / learned residual) · per-player conversion shrink (Shipped K1800 + Dead asymmetric) · DEF goal dampening (Dead position-split) · threat-informed xG prior (Dead `g_xg_l10`) · set-piece order (terminal) · Elo/state-space team defence (Dead λ-level rows) · opponent-scaled saves (reverses ADR 0040) · learned 4-state / survival minutes (Dead learned participation) · score-state early subs (Dead margin trim) · xbps reweight / expanded BPS terms (Dead bonus_arm class) · 4-yellow caution effect (inconsistent across seasons).

## Findings — Queue run 2026-09-29 (batches 1–2)

Evidence: [smoke_results.csv](smoke_results.csv) `variant` / `combined_delta` / `segs` / `boot_p_gt0` (58 rows: 51 lane + 7 stack, dev 2025-26 GW1–38 vs `learned_start_challenger`) · [candidate_gate.csv](candidate_gate.csv) `season` / `pass` (frozen Candidates, dev + confirm). Every prototype AUDIT PASS, no LEAKAGE FAIL; every winner re-run by orchestrator (identical).

| Idea | Verdict | Best variant (dev) | Confirm 2024-25 |
|---|---|---|---|
| ATK-05 club × DEF xG prior | `confirm-pass` → Champion | `atk_05_def_k5` +0.504 2/3 P 0.955 | +0.080 2/3 P 0.619 PASS |
| ATK-04 position rate shrink K | `confirm-fail` | `atk_04_def2400` +0.707 3/3 P 0.959 | −0.076 1/3 P 0.385 FAIL |
| DEF-01 goals-against shape | `pass-dev` (Open) | `def_01_nu1p0` (Poisson GC) +0.371 2/3 P 0.989 | not run (dropped by stack ablation) |
| ATK-02 club assist mass | `pass-dev` (Open) | `atk_02_w05_real` +0.173 2/3 P 0.655 | not run (dropped by stack ablation) |
| MIN-01 suspension ledger | `fail` | `v4_preserve_mass` +0.593 1/3 | — |
| ATK-03 start vs sub intensity | `fail` | `ga_k0` +0.176 1/3 | — |
| ATK-01 position assist conversion | `fail` | `a05_k50_fwd` +0.073 1/3 | — |
| MIN-02 EB P(60) | `fail` | `n0_10` −0.074 | — |
| BON-03 result-coupled bonus | `fail` | `comps_k10` −0.216 | — |
| BON-01 state bonus logits | `fail` | all −0.687 | — |

Stack (batch 2, `stack_b2_*`): all three −0.252 FAIL; ATK-05 + DEF-01 +0.417; ATK-05 + ATK-02 −0.200; DEF-01 + ATK-02 +0.054 → levers not additive; frozen pick = single ATK-05. DEF xG levers pass dev strongly; ATK-04 did not transfer to 2024-25, ATK-05 did (narrowly).

## Decision

Champion → `club_def_prior_challenger` ([ADR 0051](../../adr/0051-champion-club-def-prior-challenger.md)); 2026-27 GW6+ post-promotion check pending. Next Queue run re-screens remaining rows vs new Champion (DEF-02 next; DEF-01 / ATK-02 Open rows need re-smoke vs new Champion). Queue = [idea_queue.csv](idea_queue.csv). Run `/explore-candidate idea_queue.csv` (Queue mode): batches by `order`, stacks winners, one confirm per frozen pick. RULING rows wait for user's words. HOLDOUT rows wait until 2026-27 GW6+ protocol allows (ADR 0046) or user decides.

## Risks and unknowns

- Evidence numbers = unvalidated subagent aggregates; `mse_share` from former Champion.
- Several ideas add projected mass (ATK-01/02, MIN-03) → |bias| ≤ +0.01 guardrail binding; grids include mass-neutral variants.
- 2024-25 scoring differences (assists, BPS, no defcon) may make some levers uninformative on confirm; re-check per idea before gate.
- Ledger class titles broad (e.g. "Non-flat bonus"); log each new mechanism as new row with explicit difference.
- Champion change moves hooks (`replaces` column).

---
idea_id: EXT-35
name: Leave-Player-and-Club-Out Creative-Role Kernel Prior at Fixed Defender K
tier: P1
component: xp_goals
status: inconclusive
replaces: "Replace only the DEF prior inside models/def_xg_shrink_challenger.py::shrunk_xg_rates as used by DefXgShrinkChallengerModel.predict. New rate numerator uses mu_i; K remains 2400 and non-DEF rates remain exact Champion values. Apply new_rate / rate_360 once to original features.per90_xg, then enter LearnedStartChallengerModel.predict through the same parent call used by existing prototypes; do not call the DEF-shrink wrapper again. This preserves builder warm seed and matchup overlays and prevents double shrinkage."
grid: "h=0.45,k_pool=7200,exclude_target_club=True,cap=0.02; h=0.70,k_pool=7200,exclude_target_club=True,cap=0.02; h=0.45,k_pool=14400,exclude_target_club=True,cap=0.02; h=0.45,k_pool=7200,exclude_target_club=False,cap=0.02"
inputs: features.player_id; features.position_id; features.club_id; features.gameweek_id; features.per90_xg; features.per90_xa; features.xmins_if_start; features.xmins_if_sub_in; history.player_id; history.fixture_id; history.gameweek_id; history.was_home; history.opponent_club_id; history.minutes; history.expected_goals; history.creativity
nearest_ledger_row: "Club x DEF pooled prior stacked with K=2400 shrinkage (club prior 5 matches; DEF K 1800-2400)"
spec_path: ideas/EXT-35-leave-player-and-club-out-creative-role-kernel-prior-at-fixed-defender-k.md
---

# EXT-35: Leave-Player-and-Club-Out Creative-Role Kernel Prior at Fixed Defender K

## 1. Concept & Football Hypothesis

Defenders with sustained creative involvement may belong to different attacking populations. Estimate their transferable xG prior from other defenders' subsequent observed attacking production, using each donor's creative role measured before its match. Keep individual xG shrinkage at K_DEF=2400. Learn whether the relationship is positive, negative, or absent; do not assume that creative defenders deserve an uplift.

   Failure evidence motivating redesign: `docs/research/candidate-ideation/smoke_results.csv`, filter `date=2026-11-09`, `variant=ext_20_t15_k800`: `combined_delta=0.056315789473671884`, `boot_p_gt0=0.67085`, `guardrails_passed=True`. Filter `date=2026-11-10`, `variant=ext_32_t18_k800_m360`: `combined_delta=-0.018684210526330958`, `boot_p_gt0=0.5145`, `reasons` includes late-segment regression. Same file/date, `variant=ext_34_t18_k800_a22`: `combined_delta=-0.09881578947369007`, `boot_p_gt0=0.426625`, `reasons` includes cold-start and early-mid regression. All are `legacy_proxy_diagnostic`, `scientific_verdict=inconclusive`, `dead_lever_authority=False`; none establishes promotion failure under ADR 0066's authoritative estimand.

   `docs/research/candidate-ledger/candidate_ledger.csv` `tried_as/result` for `smoke ext_32_*` and `smoke ext_34_*` reports all variants passing Tier 2 but failing Tier 3. This raises a transport question. It does not prove threshold chatter, transfer churn, minutes error, or any causal failure mechanism. Actual `docs/research/candidate-ideation/prototypes/ext_20/prototypes.py`, `ext_32/prototypes.py`, and `ext_34/prototypes.py` simultaneously change individual xG shrinkage and prior elevation; EXT-34 additionally changes conceded hazard. Hypothesized cause: selective amplification of noisy own attacking history. This cause remains unverified.

   Eligibility comparison: EXT-20/32/34 remain OPEN, but their K<2400 implementations overlap locked ARCH-03. This proposal never imports that component. Dead EXT-18 (`Starter-role conditioning and set-piece creative-share xG shrinkage for budget enablers`) deterministically sets a prior proportional to the target player's own creativity and changes attacker K; its actual `prototypes/ext_18/prototypes.py` contains `base_prior * (1 + gamma_role * rel_cre)`. A defender-only copy of that formula would be dead-match. Here the effect comes from leave-player-out, lagged donor xG outcomes through a nonparametric kernel, with fixed K and no prespecified sign. Dead `Club x DEF pooled prior stacked with K=2400 shrinkage` uses the target club's mean; the primary variant excludes every donor row from that club. Dead multi-feature Poisson goals GLM estimates regression coefficients from player/fixture predictors; this proposal estimates a regularized conditional population prior, without goals targets, fitted slopes, own xG in role, or fixture scaling. These are structural distinctions, not permission to reopen those dead mechanisms. If implementation falls back to own-creativity scaling, same-club prior, lower K, or direct goals residual regression, label dead-match and stop.

## 2. Mathematical Formulation

Let g be target deadline and H_<g the supplied observed history. Use current point-in-time DEF classification only for players in the current known universe; unknown historical identities excluded. For each donor match t<g, reconstruct creative role from rows u<t, excluding the entire donor match's GW. Define C_jt as creativity sum, M_jt as minutes sum, and cbar_t as pooled defender creativity/90 from that same earlier history. Use unweighted cumulative role summaries; no same-match creativity enters its xG response:

   c_jt = log(1 + [90 C_jt + 360 cbar_t] / [(M_jt + 360) * 10]); r_jt = M_jt / (M_jt + 360).

   Target c_ig and r_ig use all H_<g analogously. Role scaling 10 ICT units/90 and role pseudo-minutes 360 are fixed design constants, not empirical claims. With no prior defender minutes, omit the donor response; with no target role history, delta_i=0. Define base donor weight b_jt = 0.95^(g-t) r_jt. Exclude j=i and, for primary variants, rows whose observed historical club equals `features.club_id` for i. Historical club is reconstructed from both sides of (`fixture_id`, `was_home`, `opponent_club_id`), never assigned from current club.

   Cap each donor player's total weighted exposure at 900 minutes by multiplying its b_jt by min(1, 900 / sum_t b_jt minutes_jt). This limits repeated appearances from one player; 900 is fixed design. Let the resulting weights be b'_jt. Define baseline donor mean mu_-i = 90 sum b'_jt xG_jt / sum b'_jt minutes_jt.

   Kernel weights q_jt = b'_jt exp[-(c_ig-c_jt)^2/(2 h^2)]. Let E_j = sum_t q_jt minutes_jt and N_eff = (sum_j E_j)^2 / sum_j E_j^2. Define regularized conditional rate:

   mu_role,i = [90 sum q_jt xG_jt + K_pool mu_-i] / [sum q_jt minutes_jt + K_pool].

   delta_i = r_ig [N_eff/(N_eff+8)] clip(mu_role,i - mu_-i, -0.02, 0.02).

   Rates in xG/90; 0.02 cap is preregistered engineering bound. Let mu_DEF be the Champion's existing pooled defender prior; xG_i^w and M_i^w use the exact existing `shrunk_xg_rates` decay 0.95 and per-player age anchor. Set mu_i=max(0,mu_DEF+delta_i) and:

   lambda_i* = [90 xG_i^w + 2400 mu_i] / [M_i^w+2400].

   Counterfactual per row, away from prior nonnegativity clipping: lambda_i* - lambda_i,Champion = 2400 delta_i/(M_i^w+2400). Adding an own xG impulse while holding creativity/minutes fixed leaves delta_i unchanged; direct own-xG coefficient stays 90/(M_i^w+2400), rather than increasing to a coefficient with K_OOP<2400. The Champion's existing dependence of mu_DEF on own xG is retained. Nonnegativity clipping can suppress its response; it cannot increase direct own-xG weight. Raising own creativity alone cannot force a positive delta: donor predictive shape determines sign. With a flat donor relationship, delta_i tends to zero. These counterfactuals distinguish the proposal from both deterministic creative-share elevation and shrinkage relaxation.

## 3. Decoupled Architecture Placement

M_events, `xp_goals`; existing `xbps` and `xp_bonus` recomputed through inherited scoring. No M_mins intervention, no start/sub event intensity split, no clean-sheet or conceded-hazard change. The latter components remain available as matched controls in the diagnostic.

## 4. Replaces / Integration Hook

Replace only the DEF prior inside `models/def_xg_shrink_challenger.py::shrunk_xg_rates` as used by `DefXgShrinkChallengerModel.predict`. New rate numerator uses mu_i; K remains 2400 and non-DEF rates remain exact Champion values. Apply `new_rate / rate_360` once to original `features.per90_xg`, then enter `LearnedStartChallengerModel.predict` through the same parent call used by existing prototypes; do not call the DEF-shrink wrapper again. This preserves builder warm seed and matchup overlays and prevents double shrinkage.

### Required diagnostic before model search

Implementation admission clarification, 2026-11-10, before empirical execution: inherited HoldChase xG sharp/trim preparation can move the ceiling mask controlling its 1.04 duration tilt. Preserve registered event-rate formula and inherited goal transforms, but neutralize incidental minutes changes. For each supplied conditional-duration column, multiply input by `baseline_tilt / candidate_tilt`, using exact inherited sharp/trim constants and baseline Champion versus candidate prepared rates. Parent's unchanged tilt then restores baseline conditional durations. Missing columns stay absent; missing/nonfinite values must reproduce baseline parent handling rather than invent duration evidence. No start-probability, P(60), cap, global constant, or assist-GLM change. Synthetic boundary cases and full-development paired state tensors must verify equality before smoke. If exact parity fails, stop for repair rather than treating the exposure change as candidate signal.

 for each frozen variant, retain one identical pre-deadline rate tensor and compare candidate versus Champion under (a) identical predicted participation states and (b) one identical externally reconstructed oracle-state tensor. Save all `p_start`, `p_sub_in`, `p_dnp`, `xmins_if_start`, `xmins_if_sub_in`, `p_60_if_start`, `p_60_if_sub_in`, component outputs, selection, and scores; hash rates and state tensors. The existing oracle inserts realized minutes through `external_xmins`, then `target_to_states` reconstructs states. Nonlinear eligibility and bonus can therefore differ even with unchanged rates. Compare rate deltas within each state condition, then their interaction. Neither this comparison nor an oracle sign flip demonstrates a minutes-model cause. No adjustment of p_start, p60, duration, bonus law, or scoring rule is permitted as a response to this diagnostic.

   Diagnostic companion contract: development-only per-row records with `variant`, `player_id`, `gameweek_id`, `state_condition`, `rate_hash`, `state_hash`, `champ_xg_rate`, `candidate_xg_rate`, `prior_delta`, `donor_n_eff`, `xp_goals_delta`, `xp_bonus_delta`, `selected_champ`, `selected_candidate`. Additional paired GW records: `score_delta`, `selection_overlap`, and `churn_delta`. This is a prospective output schema, not an existing evidence claim.

## 5. Parameter Sweep Grid

`h=0.45,k_pool=7200,exclude_target_club=True,cap=0.02; h=0.70,k_pool=7200,exclude_target_club=True,cap=0.02; h=0.45,k_pool=14400,exclude_target_club=True,cap=0.02; h=0.45,k_pool=7200,exclude_target_club=False,cap=0.02`

### Preregistration

   Last variant is the club-exclusion ablation: still kernel-conditioned donor pooling across every eligible club and target-player exclusion. It cannot choose same-club donors alone, compute a target-club mean, or substitute a club prior when kernel support is absent. A same-club fallback is dead-match and forbidden in every variant. Include exact zero-delta Champion identity control in synthetic verification, not as a smoke contender. Freeze the four-variant family before any development run. No parameter retuning from Tier-2/Tier-3 sign differences; no K sweep. Exclude future confirmation/holdout results from variant selection.

## 6. Small-Sample & Cold-Start Strategy

Existing warm seed N_prior=1 remains in `features.per90_xg`; new correction is computed only from history actually supplied to `fit`. Current `backtesting/walkforward.py` calls `fit(history_before_target(df_perf,...))`, while prior-season seeding occurs in the builder. Do not assume seed match rows reach fit. At empty current history, exact Champion fallback; at limited history, target role reliability, donor reliability, donor exposure cap, K_pool, and effective-player count attenuate correction continuously. No new global N_eff activation ramp, no early causal-ML activation, no GW-dependent switch; specifically do not reuse locked EXT-05's N_min/N_full ramp. Existing inherited models retain their activation behavior. If seed donor data is added later, that changes the registered design and requires an explicit point-in-time identity/position contract before testing.

## 7. Budget-Constrained Optimizer Interaction

Retain heavy individual shrinkage so a header haul cannot lower K. A bounded, learned population prior could distinguish repeat attacking involvement at a budget DEF price without converting recent individual xG noise into a large point forecast. The mechanism can also reduce a prior when similar creative roles predict less xG. No claimed savings, net-score gain, or churn reduction until measured. Oracle evidence addresses only a diagnostic screen; selection must succeed under predicted states and the 15-player £100m rolling replay, native net score, substantive guards, segment loss floors, and churn ≤ Champion+0.50 players/GW. Freeze any retained candidate before the one registered 2024-25 confirmation with 2023-24 seed; 2026-27 GW6+ remains sealed.

   Metrics: role-prior delta = mu_i-mu_DEF, signed estimate, ideal zero when no transferable role signal; donor effective count = (sum E_j)^2/sum E_j^2, higher means broader independent support, no success cutoff; paired score delta = Candidate minus Champion native net FPL points, higher better, ideal positive with admitted inference; selection overlap = intersection size/union size, Jaccard descriptive diagnostic, direction/ideal N/A; supporting squad churn = mean_g(15 - |S_g intersection S_(g-1)|), lower better, Candidate minus Champion ideal ≤0 and guard ≤0.50 players/GW, using `backtesting/metrics.py::compute_top_15_squad_churn_by_gameweek` and `top_15_squad_churn`. Preserve this supporting diagnostic separately from actual transfers in rolling replay.

## 8. Point-in-Time Feature Requirements

`features.player_id; features.position_id; features.club_id; features.gameweek_id; features.per90_xg; features.per90_xa; features.xmins_if_start; features.xmins_if_sub_in; history.player_id; history.fixture_id; history.gameweek_id; history.was_home; history.opponent_club_id; history.minutes; history.expected_goals; history.creativity`

### Input provenance

   All manifest fields exist in the generated Operational Data Catalog. `features.club_id` and position map come from the target as-of FeatureContract. Inputs are the caller's completed, strictly pre-deadline `history_before_target` slice, with history identity and fixture context already reconciled. Construct donor panel strictly from DEF rows (`position_id==2` after mapping from current FeatureContract); exclude unknown identities. Build each donor's role from strictly earlier GWs in that supplied slice; all same-GW rows excluded even if ordered earlier by kickoff. Historical club comes only from a valid two-sided fixture context. Target role uses the full supplied slice; projection horizons use that same information set without fabricated future updates. Missing/malformed required creativity or fixture-side identity gives delta=0 for affected observations, never imputed from terminal totals. Reject nonfinite or negative minutes/xG/creativity; empty/invalid identity pools give baseline. Reconstructed rates must be finite and nonnegative, otherwise exact original Champion feature/rate fallback. No news, availability, set-piece rank, ownership, external tactical labels, tracking, or minute-level streams required. The diagnostic may retain inherited participation outputs but they are not new model covariates.

## 9. Python Code Skeleton (Optional)

Valid Python core and explicit partial integration contract. Panel construction and prediction wiring must be implemented and leakage-audited before registration; this skeleton deliberately raises at prediction instead of silently testing the unchanged Champion.

```python
from __future__ import annotations

import numpy as np
import pandas as pd

from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel


def donor_prior_delta(
    panel: pd.DataFrame,
    player_id: int,
    club_id: int,
    target_gw: int,
    role: float,
    role_reliability: float,
    bandwidth: float = 0.45,
    k_pool: float = 7200.0,
    exclude_target_club: bool = True,
) -> float:
    required = {"player_id", "club", "position_id", "gameweek_id", "minutes", "expected_goals",
                "lag_role", "lag_role_reliability"}
    if panel.empty or not required.issubset(panel.columns):
        return 0.0
    if (not np.isfinite([role, role_reliability, bandwidth, k_pool]).all()
            or role < 0.0 or bandwidth <= 0.0 or k_pool <= 0.0):
        return 0.0
    rows = panel[list(required)].apply(pd.to_numeric, errors="coerce")
    rows = rows.replace([np.inf, -np.inf], np.nan).dropna()
    rows = rows.loc[(rows["player_id"] != player_id)
                    & (rows["position_id"] == 2)
                    & (rows["gameweek_id"] < target_gw)
                    & (rows["minutes"] > 0.0)
                    & (rows["expected_goals"] >= 0.0)
                    & (rows["lag_role"] >= 0.0)
                    & (rows["player_id"] > 0)
                    & (rows["club"] > 0)].copy()
    if exclude_target_club:
        rows = rows.loc[rows["club"] != club_id].copy()
    if rows.empty or role_reliability <= 0.0:
        return 0.0
    minutes = rows["minutes"].astype(float)
    xg = rows["expected_goals"].astype(float)
    base = np.power(0.95, target_gw - rows["gameweek_id"].astype(float))
    base = base * rows["lag_role_reliability"].astype(float).clip(0.0, 1.0)
    donor_exposure = (base * minutes).groupby(rows["player_id"]).sum()
    cap_scale = (900.0 / donor_exposure.clip(lower=1e-12)).clip(upper=1.0)
    base = base * rows["player_id"].map(cap_scale)
    total_exposure = float((base * minutes).sum())
    if total_exposure <= 0.0:
        return 0.0
    donor_mean = 90.0 * float((base * xg).sum()) / total_exposure
    distance = (rows["lag_role"].astype(float) - role) / bandwidth
    weight = base * np.exp(-0.5 * distance.pow(2))
    exposure = (weight * minutes).groupby(rows["player_id"]).sum()
    exposure_sum = float(exposure.sum())
    square_sum = float(exposure.pow(2).sum())
    if exposure_sum <= 0.0 or square_sum <= 0.0:
        return 0.0
    n_eff = exposure_sum**2 / square_sum
    role_mean = (90.0 * float((weight * xg).sum()) + k_pool * donor_mean)
    role_mean /= exposure_sum + k_pool
    delta = float(np.clip(role_reliability, 0.0, 1.0) * n_eff / (n_eff + 8.0)
                  * np.clip(role_mean - donor_mean, -0.02, 0.02))
    return delta if np.isfinite(delta) else 0.0


class CreativeRoleKernelPriorChallengerModel(DefXgShrinkChallengerModel):
    @property
    def name(self) -> str:
        return "creative_role_kernel_prior_challenger"

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        raise NotImplementedError(
            "Build lagged donor panel and replace DEF prior at fixed K=2400 "
            "before registering this skeleton for smoke."
        )
```

Review risks: creativity is an imperfect role proxy; kernel conditioning may contain little predictive information; apparent role effect may reflect club environment or finishing noise; same current universe position mapping remains an inherited limitation; early donor scarcity may make the prototype inert. The club-exclusion ablation tests environmental dependence. Audit invariants with synthetic rows: target's own xG perturbation leaves `donor_prior_delta` unchanged; target's own club rows do not enter primary donor pool; changing any donor match's same-row creativity cannot change its own lagged role; future rows cannot affect rates; missing context gives baseline; per-row K exactly 2400. If no predictive donor relationship remains or integrated score/guards fail, retain the inconclusive diagnostic outcome without recycling lower-K prototypes.

## Ledger Audit & Revisit Justification
- **Flagged Match**: `Club x DEF pooled prior stacked with K=2400 shrinkage (club prior 5 matches; DEF K 1800-2400)`
- **Audit Status**: Paper semantic review complete; lexical flag retained
- **Rationale**: Paper eligibility reviewed: lagged creativity kernel across donor clubs, target-player xG excluded, fixed K=2400; not target-club mean. Lexical flag retained. Partial skeleton; integration and ADR 0068 reviews required before smoke; no new empirical evidence.

## Intake review

Paper eligibility reviewed: lagged creativity kernel across donor clubs, target-player xG excluded, fixed K=2400; not target-club mean. Lexical flag retained. Partial skeleton; integration and ADR 0068 reviews required before smoke; no new empirical evidence.

Review record: [Near-miss ideation](../near-miss-ideation-2026-11-10.md). Execution requires separate implementation admission; AST validity does not establish model correctness.

## Development execution, 2026-11-11

Development 2025-26 no winner: four frozen variants executed; one Tier 2 nonpass (oracle delta 0, P 0); three invalid/inert screen admissions (max playable shift 0.004793/0.009150/0.009393 < 0.01). Full native/oracle projection diagnostic retained. No Tier 3 or confirmation; scientific inconclusive; no new Dead lock.

Implemented source, reviews, complete terminal coverage, paired diagnostic companions: [EXT-35 execution artifacts](../prototypes/ext_35/README.md). Original skeleton retained as proposal history; frozen executable remains unregistered. No scale expansion or post-result retuning.

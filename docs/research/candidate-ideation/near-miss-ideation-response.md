# Near-miss specialist proposals

Source: specialist roles, 2026-11-10. Paper proposals only; partial implementation contracts. Final intake decisions and review: near-miss-ideation-2026-11-10.md.

### Candidate EXT-35: Leave-Player-and-Club-Out Creative-Role Kernel Prior at Fixed Defender K

1. **Concept & Football Hypothesis**: Defenders with sustained creative involvement may belong to different attacking populations. Estimate their transferable xG prior from other defenders' subsequent observed attacking production, using each donor's creative role measured before its match. Keep individual xG shrinkage at K_DEF=2400. Learn whether the relationship is positive, negative, or absent; do not assume that creative defenders deserve an uplift.

   Failure evidence motivating redesign: `docs/research/candidate-ideation/smoke_results.csv`, filter `date=2026-11-09`, `variant=ext_20_t15_k800`: `combined_delta=0.056315789473671884`, `boot_p_gt0=0.67085`, `guardrails_passed=True`. Filter `date=2026-11-10`, `variant=ext_32_t18_k800_m360`: `combined_delta=-0.018684210526330958`, `boot_p_gt0=0.5145`, `reasons` includes late-segment regression. Same file/date, `variant=ext_34_t18_k800_a22`: `combined_delta=-0.09881578947369007`, `boot_p_gt0=0.426625`, `reasons` includes cold-start and early-mid regression. All are `legacy_proxy_diagnostic`, `scientific_verdict=inconclusive`, `dead_lever_authority=False`; none establishes promotion failure under ADR 0066's authoritative estimand.

   `docs/research/candidate-ledger/candidate_ledger.csv` `tried_as/result` for `smoke ext_32_*` and `smoke ext_34_*` reports all variants passing Tier 2 but failing Tier 3. This raises a transport question. It does not prove threshold chatter, transfer churn, minutes error, or any causal failure mechanism. Actual `docs/research/candidate-ideation/prototypes/ext_20/prototypes.py`, `ext_32/prototypes.py`, and `ext_34/prototypes.py` simultaneously change individual xG shrinkage and prior elevation; EXT-34 additionally changes conceded hazard. Hypothesized cause: selective amplification of noisy own attacking history. This cause remains unverified.

   Eligibility comparison: EXT-20/32/34 remain OPEN, but their K<2400 implementations overlap locked ARCH-03. This proposal never imports that component. Dead EXT-18 (`Starter-role conditioning and set-piece creative-share xG shrinkage for budget enablers`) deterministically sets a prior proportional to the target player's own creativity and changes attacker K; its actual `prototypes/ext_18/prototypes.py` contains `base_prior * (1 + gamma_role * rel_cre)`. A defender-only copy of that formula would be dead-match. Here the effect comes from leave-player-out, lagged donor xG outcomes through a nonparametric kernel, with fixed K and no prespecified sign. Dead `Club x DEF pooled prior stacked with K=2400 shrinkage` uses the target club's mean; the primary variant excludes every donor row from that club. Dead multi-feature Poisson goals GLM estimates regression coefficients from player/fixture predictors; this proposal estimates a regularized conditional population prior, without goals targets, fitted slopes, own xG in role, or fixture scaling. These are structural distinctions, not permission to reopen those dead mechanisms. If implementation falls back to own-creativity scaling, same-club prior, lower K, or direct goals residual regression, label dead-match and stop.

2. **Mathematical Formulation**: Let g be target deadline and H_<g the supplied observed history. Use current point-in-time DEF classification only for players in the current known universe; unknown historical identities excluded. For each donor match t<g, reconstruct creative role from rows u<t, excluding the entire donor match's GW. Define C_jt as creativity sum, M_jt as minutes sum, and cbar_t as pooled defender creativity/90 from that same earlier history. Use unweighted cumulative role summaries; no same-match creativity enters its xG response:

   c_jt = log(1 + [90 C_jt + 360 cbar_t] / [(M_jt + 360) * 10]); r_jt = M_jt / (M_jt + 360).

   Target c_ig and r_ig use all H_<g analogously. Role scaling 10 ICT units/90 and role pseudo-minutes 360 are fixed design constants, not empirical claims. With no prior defender minutes, omit the donor response; with no target role history, delta_i=0. Define base donor weight b_jt = 0.95^(g-t) r_jt. Exclude j=i and, for primary variants, rows whose observed historical club equals `features.club_id` for i. Historical club is reconstructed from both sides of (`fixture_id`, `was_home`, `opponent_club_id`), never assigned from current club.

   Cap each donor player's total weighted exposure at 900 minutes by multiplying its b_jt by min(1, 900 / sum_t b_jt minutes_jt). This limits repeated appearances from one player; 900 is fixed design. Let the resulting weights be b'_jt. Define baseline donor mean mu_-i = 90 sum b'_jt xG_jt / sum b'_jt minutes_jt.

   Kernel weights q_jt = b'_jt exp[-(c_ig-c_jt)^2/(2 h^2)]. Let E_j = sum_t q_jt minutes_jt and N_eff = (sum_j E_j)^2 / sum_j E_j^2. Define regularized conditional rate:

   mu_role,i = [90 sum q_jt xG_jt + K_pool mu_-i] / [sum q_jt minutes_jt + K_pool].

   delta_i = r_ig [N_eff/(N_eff+8)] clip(mu_role,i - mu_-i, -0.02, 0.02).

   Rates in xG/90; 0.02 cap is preregistered engineering bound. Let mu_DEF be the Champion's existing pooled defender prior; xG_i^w and M_i^w use the exact existing `shrunk_xg_rates` decay 0.95 and per-player age anchor. Set mu_i=max(0,mu_DEF+delta_i) and:

   lambda_i* = [90 xG_i^w + 2400 mu_i] / [M_i^w+2400].

   Counterfactual per row, away from prior nonnegativity clipping: lambda_i* - lambda_i,Champion = 2400 delta_i/(M_i^w+2400). Adding an own xG impulse while holding creativity/minutes fixed leaves delta_i unchanged; direct own-xG coefficient stays 90/(M_i^w+2400), rather than increasing to a coefficient with K_OOP<2400. The Champion's existing dependence of mu_DEF on own xG is retained. Nonnegativity clipping can suppress its response; it cannot increase direct own-xG weight. Raising own creativity alone cannot force a positive delta: donor predictive shape determines sign. With a flat donor relationship, delta_i tends to zero. These counterfactuals distinguish the proposal from both deterministic creative-share elevation and shrinkage relaxation.

3. **Decoupled Architecture Placement**: M_events, `xp_goals`; existing `xbps` and `xp_bonus` recomputed through inherited scoring. No M_mins intervention, no start/sub event intensity split, no clean-sheet or conceded-hazard change. The latter components remain available as matched controls in the diagnostic.

4. **Replaces / Integration Hook**: Replace only the DEF prior inside `models/def_xg_shrink_challenger.py::shrunk_xg_rates` as used by `DefXgShrinkChallengerModel.predict`. New rate numerator uses mu_i; K remains 2400 and non-DEF rates remain exact Champion values. Apply `new_rate / rate_360` once to original `features.per90_xg`, then enter `LearnedStartChallengerModel.predict` through the same parent call used by existing prototypes; do not call the DEF-shrink wrapper again. This preserves builder warm seed and matchup overlays and prevents double shrinkage.

### Required diagnostic before model search

 for each frozen variant, retain one identical pre-deadline rate tensor and compare candidate versus Champion under (a) identical predicted participation states and (b) one identical externally reconstructed oracle-state tensor. Save all `p_start`, `p_sub_in`, `p_dnp`, `xmins_if_start`, `xmins_if_sub_in`, `p_60_if_start`, `p_60_if_sub_in`, component outputs, selection, and scores; hash rates and state tensors. The existing oracle inserts realized minutes through `external_xmins`, then `target_to_states` reconstructs states. Nonlinear eligibility and bonus can therefore differ even with unchanged rates. Compare rate deltas within each state condition, then their interaction. Neither this comparison nor an oracle sign flip demonstrates a minutes-model cause. No adjustment of p_start, p60, duration, bonus law, or scoring rule is permitted as a response to this diagnostic.

   Diagnostic companion contract: development-only per-row records with `variant`, `player_id`, `gameweek_id`, `state_condition`, `rate_hash`, `state_hash`, `champ_xg_rate`, `candidate_xg_rate`, `prior_delta`, `donor_n_eff`, `xp_goals_delta`, `xp_bonus_delta`, `selected_champ`, `selected_candidate`. Additional paired GW records: `score_delta`, `selection_overlap`, and `churn_delta`. This is a prospective output schema, not an existing evidence claim.

5. **Parameter Sweep Grid**: `h=0.45,k_pool=7200,exclude_target_club=True,cap=0.02; h=0.70,k_pool=7200,exclude_target_club=True,cap=0.02; h=0.45,k_pool=14400,exclude_target_club=True,cap=0.02; h=0.45,k_pool=7200,exclude_target_club=False,cap=0.02`

### Preregistration

   Last variant is the club-exclusion ablation: still kernel-conditioned donor pooling across every eligible club and target-player exclusion. It cannot choose same-club donors alone, compute a target-club mean, or substitute a club prior when kernel support is absent. A same-club fallback is dead-match and forbidden in every variant. Include exact zero-delta Champion identity control in synthetic verification, not as a smoke contender. Freeze the four-variant family before any development run. No parameter retuning from Tier-2/Tier-3 sign differences; no K sweep. Exclude future confirmation/holdout results from variant selection.

6. **Small-Sample & Cold-Start Strategy**: Existing warm seed N_prior=1 remains in `features.per90_xg`; new correction is computed only from history actually supplied to `fit`. Current `backtesting/walkforward.py` calls `fit(history_before_target(df_perf,...))`, while prior-season seeding occurs in the builder. Do not assume seed match rows reach fit. At empty current history, exact Champion fallback; at limited history, target role reliability, donor reliability, donor exposure cap, K_pool, and effective-player count attenuate correction continuously. No new global N_eff activation ramp, no early causal-ML activation, no GW-dependent switch; specifically do not reuse locked EXT-05's N_min/N_full ramp. Existing inherited models retain their activation behavior. If seed donor data is added later, that changes the registered design and requires an explicit point-in-time identity/position contract before testing.

7. **Budget-Constrained Optimizer Interaction**: Retain heavy individual shrinkage so a header haul cannot lower K. A bounded, learned population prior could distinguish repeat attacking involvement at a budget DEF price without converting recent individual xG noise into a large point forecast. The mechanism can also reduce a prior when similar creative roles predict less xG. No claimed savings, net-score gain, or churn reduction until measured. Oracle evidence addresses only a diagnostic screen; selection must succeed under predicted states and the 15-player £100m rolling replay, native net score, substantive guards, segment loss floors, and churn ≤ Champion+0.50 players/GW. Freeze any retained candidate before the one registered 2024-25 confirmation with 2023-24 seed; 2026-27 GW6+ remains sealed.

   Metrics: role-prior delta = mu_i-mu_DEF, signed estimate, ideal zero when no transferable role signal; donor effective count = (sum E_j)^2/sum E_j^2, higher means broader independent support, no success cutoff; paired score delta = Candidate minus Champion native net FPL points, higher better, ideal positive with admitted inference; selection overlap = intersection size/union size, Jaccard descriptive diagnostic, direction/ideal N/A; supporting squad churn = mean_g(15 - |S_g intersection S_(g-1)|), lower better, Candidate minus Champion ideal ≤0 and guard ≤0.50 players/GW, using `backtesting/metrics.py::compute_top_15_squad_churn_by_gameweek` and `top_15_squad_churn`. Preserve this supporting diagnostic separately from actual transfers in rolling replay.

8. **Point-in-Time Feature Requirements**: `features.player_id; features.position_id; features.club_id; features.gameweek_id; features.per90_xg; history.player_id; history.fixture_id; history.gameweek_id; history.was_home; history.opponent_club_id; history.minutes; history.expected_goals; history.creativity`

### Input provenance

   All manifest fields exist in the generated Operational Data Catalog. `features.club_id` and position map come from the target as-of FeatureContract. Inputs are the caller's completed, strictly pre-deadline `history_before_target` slice, with history identity and fixture context already reconciled. Construct donor panel strictly from DEF rows (`position_id==2` after mapping from current FeatureContract); exclude unknown identities. Build each donor's role from strictly earlier GWs in that supplied slice; all same-GW rows excluded even if ordered earlier by kickoff. Historical club comes only from a valid two-sided fixture context. Target role uses the full supplied slice; projection horizons use that same information set without fabricated future updates. Missing/malformed required creativity or fixture-side identity gives delta=0 for affected observations, never imputed from terminal totals. Reject nonfinite or negative minutes/xG/creativity; empty/invalid identity pools give baseline. Reconstructed rates must be finite and nonnegative, otherwise exact original Champion feature/rate fallback. No news, availability, set-piece rank, ownership, external tactical labels, tracking, or minute-level streams required. The diagnostic may retain inherited participation outputs but they are not new model covariates.

9. **Python Code Skeleton (Optional)**: Valid Python core and explicit partial integration contract. Panel construction and prediction wiring must be implemented and leakage-audited before registration; this skeleton deliberately raises at prediction instead of silently testing the unchanged Champion.

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


### Candidate EXT-37: Baseline-Preserving Opponent Hazard Curvature Residual

1. **Concept & Football Hypothesis**: Retain Champion's warm-start valuation, hard-fixture adjustment, calibrated opponent evidence, and participation engine. Change only how opponent attacking excess maps into concession hazard. An exponential concession link has curvature beyond Champion's additive opponent adjustment; this is the football hypothesis, not an observed improvement. EXT-33 instead removed incumbent hard-fixture behavior and applied opponent information twice. Proposed residual cancels the exact incumbent opponent addon before substituting curvature, with no standalone FDR signal and no effect when information is absent. Parent: open EXT-33; EXT-23 / EXT-34 failure evidence motivates baseline preservation and component isolation, not another combined attack/defence stack.

2. **Mathematical Formulation**: At forecast origin, reconstruct the exact opponent xG estimate already used by `features.matchup_share._club_rates`, including shipped last-10-fixture, venue blending, and league shrinkage. Let \(\delta_{c,v}=\widehat{xG}_{c,v}-\bar{xG}\), \(s=0.40\), incoming unclamped rate \(a_i=b_i+s\delta_{c,v}\), and inherited hard-fixture multiplier \(h(d)=1+0.15(d-3)/2\) when \(d\ge4\), otherwise 1. Champion concession hazard before minutes is \(\lambda_0=\max(0.05,h(d)a_iD_i)\), with existing `defence_multiplier` \(D_i\). The baseline is reconstructed only when overlay applicability and unclamped inversion are established; otherwise exact Champion identity.

   Define \(x_i=s\delta_{c,v}/b_i\) and asymmetric log link \(L_\rho(x)=x\) for \(x\ge0\), \(\rho x\) for \(x<0\), fixed \(\rho=0.25\). Counterfactual rate before inherited hard-fixture factor: \(a_i^{alt}=b_i\exp[L_\rho(x_i)]\). Local tough-fixture slope at neutral is fixed to incumbent \(s\), not swept. No FDR term appears in \(L\).

   Exact replacement residual: \(u_i=\log(a_i^{alt}/a_i)=\log(b_i/a_i)+L_\rho(s\delta/b_i)\). Reliability \(\omega_c=n_c/(n_c+10)\), with \(n_c\) count of distinct current-season opponent club fixtures, capped at shipped 10-fixture window. Bounded residual \(\epsilon_i=\omega_c\operatorname{clip}(u_i,-B_-,B_+)\); tough side \(B_-=B_+=\log(1.10)\), easy side \(B_-=B_+=\log(1.03)\). Final rate \(a_i^*=a_i\exp(\epsilon_i)\); actual event hook receives \(h(d)a_i\) and multiplies it by \(\exp(\epsilon_i)\) exactly once. Thus \(\lambda^*=\max(0.05,h(d)a_iD_i\exp(\epsilon_i))\). At zero information, neutral opponent, or invalid baseline reconstruction, \(\epsilon_i=0\).

   Existing scoring laws remain: \(P(CS\mid state)=P(60+\mid state)\exp[-\lambda^*m_{CS}/90]\); conceded penalty remains Champion NegBin \(r=3\). Bounded residual alters hazard, never P(60), minute exposure, distribution family, or points directly. For tough opponents \(u=x-\log(1+x)\), exposing curvature rather than reapplying the first-order opponent effect. Tough-side slope at neutral remains \(s\); full \(\rho=0.25\) variant has easy-side slope \(s[1-\omega_c(1-\rho)]\), so green-side intervention includes first-order attenuation. For admissible \(x>-1\), both residual branches satisfy \(u\ge0\); every nonidentity intervention increases concession hazard and reduces CS probability relative to Champion. No symmetric upward/downward calibration claimed. Better calibration remains a testable hypothesis.

3. **Decoupled Architecture Placement**: xp_clean_sheets

   `M_events`: `xp_clean_sheet`, `xp_conceded`, corresponding `xbps`, inherited bonus allocation. No changes to `M_mins`, goals, assists, penalties, saves, defcon, card rates. Public smoke manifest uses plural component routing `xp_clean_sheets`; actual ledger field remains singular `xp_clean_sheet`.

4. **Replaces / Integration Hook**: Subclass `DefXgShrinkChallengerModel`; leave `predict` parent call and `_apply_hard_fixture_defence` inherited. Before parent prediction, prepare per-(player, fixture) residuals from original incoming features. Override `_project_event_components`: copy row, multiply only its already hard-fixture-adjusted `per90_goals_conceded` by prepared residual factor, then call `super()._project_event_components` once. This traverses inherited multi-feature assist override and base scoring; it updates clean-sheet xBPS before inherited Plackett-Luce bonus allocation. Never bypass `DefXgShrinkChallengerModel.predict`; never pre-apply hard fixture multiplier to features passed to parent.

### Execution prerequisite

 reconstruct exact default overlay context using shared helper semantics, not an approximate new club mean. Current-season `fit()` history can infer historical club from exactly two opponent IDs per completed fixture, or use verified historical club field; never map old player appearances to current club. Preserve historical `was_home`, group by fixture/club/gameweek/venue, match `_club_fixture_xg` and `_club_rates`, establish default overlay enabled with `shrink_def=0.40`. Skip clipped `a_i<=0.05+epsilon`, missing/incomplete fixture sides, absent opponent, invalid `b_i`, or non-default unknown overlay. No inference of overlay applicability merely from `defence_multiplier==1`. Until exact context parity and applicability are implemented/reviewed, prototype status is **blocked**, not runnable or smoke-ready.

5. **Parameter Sweep Grid**: mode=full,bound_scale=1.0,rho=0.25; mode=hard_only,bound_scale=1.0,rho=0.25; mode=full,bound_scale=0.5,rho=0.25; mode=identity,bound_scale=0.0,rho=0.25

### Preregistration

Four preregistered variants total; identity is inertness/inheritance ablation, excluded from candidate selection. Hard-only separates tough-fixture curvature from green-side damping; half-bound checks selection sensitivity. Fix \(s=0.40\), window 10, reliability denominator 10, \(\rho=0.25\); no global GC/CS scale sweep, no new FDR coefficient, no calendar activation gate, no per-position minutes retraining.

   Before selection evidence: require shared-state paired decomposition with (a) Champion rates + native states, (b) candidate rates + same native states, (c) same rates under oracle states for both, and component accounting including bonus. Report projection difference by baseline hazard / P(60) strata using predetermined bins, not archive-derived thresholds. Only development data in future authorized execution; freeze before any registered confirmation. Supporting legacy screen cannot authorize adoption; ADR 0066 rolling replay remains promotion primary.

6. **Small-Sample & Cold-Start Strategy**: Exact Champion fallback at absent current-season opponent evidence; retains warm historical builder seed and inherited DEF K=2400, finishing K=1800, assist GLM, learned starts. Continuous opponent fixture reliability replaces EXT-33's information-free cold-start FDR replacement. No estimation of short-panel player fixed effects; Nickell-bias correction unnecessary for this deterministic residual. `N_eff=0.5*N_seed+N_inseason` panel ramp is not mechanically added to a club-fixture signal with different units. If future learned head is added, it becomes a new preregistration; no claimed access to seed rows absent from `fit()`.

7. **Budget-Constrained Optimizer Interaction**: Maximum 10% tough / 3% easy hazard perturbation before reliability, independent of cost. Budget defenders receive no price bonus; an enabler gains value only through inherited minutes, attack, and conditional defensive ledger. Hypothesis: retaining cold-start rankings and separating residual curvature limits forced squad switches caused by removed hard-fixture logic. Cannot guarantee churn or net score: MILP selection discontinuities can turn tiny valuation changes into costly replacements. Measure actual 15-player £100m rolling replay net score; guard excess churn ≤0.50 players/GW, segment loss floors, CS/GC guards, and captaincy guard. Expected gains and reduced churn remain untested.

8. **Point-in-Time Feature Requirements**: features.player_id; features.fixture_id; features.gameweek_id; features.position_id; features.club_id; features.opponent_id; features.is_home; features.difficulty; features.per90_goals_conceded; features.defence_multiplier; history.player_id; history.fixture_id; history.gameweek_id; history.opponent_club_id; history.was_home; history.minutes; history.expected_goals; history.expected_assists; history.expected_goals_conceded

### Input provenance

Existing inherited covariates remain supplied unchanged. Derived locals `club_id`, `club_fixture_xg`, `league_xg`, `opp_xg`, `delta_def`, `n_club_fixtures`, `raw_gc`, `residual_by_fixture` are transformations of manifest, not new telemetry. Current catalog source: `docs/research/candidate-ideation/candidate_model_ideation_prompt.md`, Observed Operational Data Catalog. Exact builder source: `features/matchup_share.py::_club_fixture_xg`, `_blended_rate`, `_club_rates`, `apply_matchup_share_overlay`. Histories strictly before forecast deadline; no archive totals, target results, terminal availability, current-season hindsight, or external data.

Unavailable provenance is a blocker: overlay-applied flag and configured shrink coefficient are not admitted FeatureContract inputs. Execution must obtain verified default-build configuration or an explicit shared intermediate/provenance extension before activation; never add invented `features.matchup_overlay_applied`, `features.matchup_delta_defence`, or historical baseline-hazard fields to allowed manifest. Such fields do not exist in present catalog. Nondefault/unknown configuration remains blocked.

9. **Python Code Skeleton**: Typed partial implementation; deliberately raises on unavailable exact context. Not an executable candidate prototype. Context reconstruction/admission is required work; no silent identity fallback during a purported nonidentity experiment. Core scalar residual and inherited hook are concrete; inheritance preserved.

```python
from __future__ import annotations

import math
from typing import Literal

import pandas as pd

from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel

Mode = Literal["full", "hard_only", "identity"]


def hazard_residual(
    incoming_gc: float, delta_def: float, n_club: int,
    *, mode: Mode, bound_scale: float, rho: float = 0.25,
) -> float:
    if not all(math.isfinite(value) for value in (incoming_gc, delta_def, bound_scale, rho)):
        return 1.0
    if bound_scale < 0.0 or not 0.0 <= rho <= 1.0:
        raise ValueError("Require nonnegative bound scale and rho in [0, 1].")
    if mode == "identity" or n_club <= 0 or incoming_gc <= 0.050001:
        return 1.0
    raw_gc = incoming_gc - 0.40 * delta_def
    if not math.isfinite(raw_gc) or raw_gc <= 0.05:
        return 1.0
    if mode == "hard_only" and delta_def < 0.0:
        return 1.0
    x = 0.40 * delta_def / raw_gc
    log_link = x if delta_def >= 0.0 else rho * x
    innovation = math.log(raw_gc / incoming_gc) + log_link
    bound = bound_scale * math.log(1.10 if delta_def >= 0.0 else 1.03)
    n_eff = min(n_club, 10)
    reliability = n_eff / (n_eff + 10.0)
    return math.exp(reliability * min(bound, max(-bound, innovation)))


class BaselinePreservingDefenceResidualModel(DefXgShrinkChallengerModel):
    def __init__(self, mode: Mode = "full", bound_scale: float = 1.0) -> None:
        super().__init__()
        self.mode = mode
        self.bound_scale = bound_scale
        self._defence_history = pd.DataFrame()
        self._residual_by_fixture: dict[tuple[int, int], float] = {}

    @property
    def name(self) -> str:
        return "baseline_preserving_defence_residual"

    def fit(self, history_df: pd.DataFrame) -> None:
        super().fit(history_df)
        self._defence_history = history_df.copy()

    def _prepare_exact_context(
        self, features_df: pd.DataFrame,
    ) -> dict[tuple[int, int], float]:
        if self.mode == "identity" or self._defence_history.empty:
            return {}
        raise NotImplementedError(
            "Require exact shipped overlay reconstruction, applicability admission, "
            "and unclamped baseline parity before nonidentity execution."
        )

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        self._residual_by_fixture = self._prepare_exact_context(features_df)
        return super().predict(features_df, horizon)

    def _project_event_components(
        self, row: pd.Series, position: str, expected_minutes: float,
        *, clean_sheet_minutes: float, p_sixty_mins: float,
    ) -> dict[str, float]:
        adjusted = row.copy()
        fixture_id = row.get("fixture_id")
        if fixture_id is not None and not pd.isna(fixture_id):
            key = (int(row["player_id"]), int(fixture_id))
            factor = self._residual_by_fixture.get(key, 1.0)
            adjusted["per90_goals_conceded"] = float(row["per90_goals_conceded"]) * factor
        return super()._project_event_components(
            adjusted, position, expected_minutes,
            clean_sheet_minutes=clean_sheet_minutes, p_sixty_mins=p_sixty_mins,
        )
```

## Dead-overlap assessment and risks

- **Open-parent refinement, not new empirical evidence**: EXT-33 remains `open`; this removes incumbent cancellation and duplicate first-order opponent usage. Do not claim a novel football signal or proven minutes fix.
- **Closest active Dead classes**: `Raw FDR as attack/defence multiplier fallback`, `Opponent-relative team Poisson lambda rate multiplier`, `Dual-Vector ratios shrunk toward 1.0`, `Post-hoc CS/GC retune k_cs/k_gc`, `Goals-conceded shape Poisson`, `CS exposure over 60+ starts`, `Multi-feature Poisson GLM goals-conceded rate`. Source: full `docs/research/candidate-ledger/candidate_ledger.csv`, `lever`, `status`, `revisit_after`, `result`.
- **Distinction**: no raw FDR fallback, no strength-ratio multiplier, no global points or hazard scale, no GC likelihood-family change, no minute/60+ exposure change, no GC GLM fit. Local opponent-conditional log residual removes exact shipped additive term, retains inherited hard factor, and is bounded/reliability-shrunk. This distinction is credible only if exact baseline replacement is implemented. If execution merely multiplies incoming rate by `exp(alpha*z)`, or sweeps `s`/global GC scales, classify as rejected overlap rather than relabeling.
- **Residual overlap risk: medium**. Broad readings of dead opponent-rate scaling may include any nonlinear opponent link. Queue as **blocked** pending two-axis reviewer clearance, with open EXT-33 parent and exact subtraction proof. No authority to reopen listed Dead classes.
- **Signal risk: high**. No new covariate: functional-form repair may simply remove spurious oracle gains. Evidence does not establish curvature as useful; zero improvement is plausible. Reject rather than expanding grid if core and ablations fail.
- **Integration risk: high until context parity**. Incoming FeatureContract lacks explicit overlay-applied marker. Default smoke can establish configuration, but arbitrary caller cannot infer it from multiplier value. Exact context requires shared helper parity / provenance; unknown configuration must preserve Champion and be reported, not silently counted as activated.
- **No second proposal**: suggested P(60), exposure, GC shape, keeper variance, club-pooled GC, and global CS scaling changes overlap active Dead classes. EXT-38 intentionally unused.


## Evidence and failure interpretation

- Production `models/hold_chase_challenger.py::_apply_hard_fixture_defence` multiplies incoming `per90_goals_conceded` by 1.075 at difficulty 4 and 1.15 at difficulty 5. EXT-23 / EXT-33 / EXT-34 prototype classes replace that method with identity: `docs/research/candidate-ideation/prototypes/ext_23/prototypes.py`, `ext_33/prototypes.py`, `ext_34/prototypes.py`, method `_apply_hard_fixture_defence`. Their cold starts change even without club-history evidence.
- Production opponent xG already affects incoming concession rate: `features/matchup_share.py::apply_matchup_share_overlay`, local `delta_def = opp_xg - league_xg`, output `per90_goals_conceded = max(0.05, per90_gc + shrink_def * delta_def)`, `MATCHUP_SHRINK_DEF=0.40`. EXT-33 then multiplies that already adjusted rate by another function of opponent xG. Convex FDR/xG weighting inside EXT-33 does not remove duplication relative to incoming FeatureContract.
- Saved EXT-23 row `variant=ext_23_a20_k4`: `combined_delta=+0.2338157894736952`, `boot_p_gt0=0.5964`, `segs=2`, `reasons` includes early-mid −0.693. Saved EXT-33 row `variant=ext_33_a18_r33_k6`: `combined_delta=-0.03710526315788343`, `boot_p_gt0=0.229475`, early-mid −0.611 and cold-start −0.787 in `reasons`. Saved EXT-34 rows `ext_34_t18_k600_a22` / `ext_34_t18_k800_a22`: `combined_delta=-0.09881578947369007`, `boot_p_gt0=0.426625`, early-mid −0.350 and cold-start −0.787. Source: `docs/research/candidate-ideation/smoke_results.csv`, named rows + columns. Evidence columns identify `legacy_proxy_diagnostic`, `scientific_verdict=inconclusive`, `dead_lever_authority=False`; these are diagnostic failures, not promotion verdicts or new Dead locks.
- Oracle success followed by predicted-state failure is consistent with dependence on participation and selection; it does not establish minutes as cause. `backtesting/walkforward.py::run_walkforward_backtest` injects oracle inputs before prediction. Oracle `external_xmins` also changes state probabilities / P(60) / bonus eligibility through `target_to_states`; isolate effects with frozen rates and matched state inputs before causal claims.
- Warm seed belongs to builder inputs, not automatically every fitted model head. `backtesting/walkforward.py::run_walkforward_backtest` passes `seed_processed_dir` to `build_features`, then calls `model.fit(history_before_target(df_perf, ...))` on current-season performance history. EXT-33 `fit()` therefore does not acquire prior-season club xG merely because builder has warm-seeded rates.

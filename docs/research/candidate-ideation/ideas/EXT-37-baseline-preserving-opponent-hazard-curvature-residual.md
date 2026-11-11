---
idea_id: EXT-37
name: Baseline-Preserving Opponent Hazard Curvature Residual
tier: P1
component: xp_clean_sheets
status: blocked
replaces: "Subclass DefXgShrinkChallengerModel; leave predict parent call and _apply_hard_fixture_defence inherited. Before parent prediction, prepare per-(player, fixture) residuals from original incoming features. Override _project_event_components: copy row, multiply only its already hard-fixture-adjusted per90_goals_conceded by prepared residual factor, then call super()._project_event_components once. This traverses inherited multi-feature assist override and base scoring; it updates clean-sheet xBPS before inherited Plackett-Luce bonus allocation. Never bypass DefXgShrinkChallengerModel.predict; never pre-apply hard fixture multiplier to features passed to parent."
grid: "mode=full,bound_scale=1.0,rho=0.25; mode=hard_only,bound_scale=1.0,rho=0.25; mode=full,bound_scale=0.5,rho=0.25; mode=identity,bound_scale=0.0,rho=0.25"
inputs: features.player_id; features.fixture_id; features.gameweek_id; features.position_id; features.club_id; features.opponent_id; features.is_home; features.difficulty; features.per90_goals_conceded; features.defence_multiplier; history.player_id; history.fixture_id; history.gameweek_id; history.opponent_club_id; history.was_home; history.minutes; history.expected_goals; history.expected_assists; history.expected_goals_conceded
nearest_ledger_row: Incumbent-return displacement (zero-sum club x position start mass transfer from stand-ins to returning incumbent after 2+ DNPs)
spec_path: ideas/EXT-37-baseline-preserving-opponent-hazard-curvature-residual.md
---

# EXT-37: Baseline-Preserving Opponent Hazard Curvature Residual

## 1. Concept & Football Hypothesis

Retain Champion's warm-start valuation, hard-fixture adjustment, calibrated opponent evidence, and participation engine. Change only how opponent attacking excess maps into concession hazard. An exponential concession link has curvature beyond Champion's additive opponent adjustment; this is the football hypothesis, not an observed improvement. EXT-33 instead removed incumbent hard-fixture behavior and applied opponent information twice. Proposed residual cancels the exact incumbent opponent addon before substituting curvature, with no standalone FDR signal and no effect when information is absent. Parent: open EXT-33; EXT-23 / EXT-34 failure evidence motivates baseline preservation and component isolation, not another combined attack/defence stack.

## 2. Mathematical Formulation

At forecast origin, reconstruct the exact opponent xG estimate already used by `features.matchup_share._club_rates`, including shipped last-10-fixture, venue blending, and league shrinkage. Let \(\delta_{c,v}=\widehat{xG}_{c,v}-\bar{xG}\), \(s=0.40\), incoming unclamped rate \(a_i=b_i+s\delta_{c,v}\), and inherited hard-fixture multiplier \(h(d)=1+0.15(d-3)/2\) when \(d\ge4\), otherwise 1. Champion concession hazard before minutes is \(\lambda_0=\max(0.05,h(d)a_iD_i)\), with existing `defence_multiplier` \(D_i\). The baseline is reconstructed only when overlay applicability and unclamped inversion are established; otherwise exact Champion identity.

   Define \(x_i=s\delta_{c,v}/b_i\) and asymmetric log link \(L_\rho(x)=x\) for \(x\ge0\), \(\rho x\) for \(x<0\), fixed \(\rho=0.25\). Counterfactual rate before inherited hard-fixture factor: \(a_i^{alt}=b_i\exp[L_\rho(x_i)]\). Local tough-fixture slope at neutral is fixed to incumbent \(s\), not swept. No FDR term appears in \(L\).

   Exact replacement residual: \(u_i=\log(a_i^{alt}/a_i)=\log(b_i/a_i)+L_\rho(s\delta/b_i)\). Reliability \(\omega_c=n_c/(n_c+10)\), with \(n_c\) count of distinct current-season opponent club fixtures, capped at shipped 10-fixture window. Bounded residual \(\epsilon_i=\omega_c\operatorname{clip}(u_i,-B_-,B_+)\); tough side \(B_-=B_+=\log(1.10)\), easy side \(B_-=B_+=\log(1.03)\). Final rate \(a_i^*=a_i\exp(\epsilon_i)\); actual event hook receives \(h(d)a_i\) and multiplies it by \(\exp(\epsilon_i)\) exactly once. Thus \(\lambda^*=\max(0.05,h(d)a_iD_i\exp(\epsilon_i))\). At zero information, neutral opponent, or invalid baseline reconstruction, \(\epsilon_i=0\).

   Existing scoring laws remain: \(P(CS\mid state)=P(60+\mid state)\exp[-\lambda^*m_{CS}/90]\); conceded penalty remains Champion NegBin \(r=3\). Bounded residual alters hazard, never P(60), minute exposure, distribution family, or points directly. For tough opponents \(u=x-\log(1+x)\), exposing curvature rather than reapplying the first-order opponent effect. Tough-side slope at neutral remains \(s\); full \(\rho=0.25\) variant has easy-side slope \(s[1-\omega_c(1-\rho)]\), so green-side intervention includes first-order attenuation. For admissible \(x>-1\), both residual branches satisfy \(u\ge0\); every nonidentity intervention increases concession hazard and reduces CS probability relative to Champion. No symmetric upward/downward calibration claimed. Better calibration remains a testable hypothesis.

## 3. Decoupled Architecture Placement

xp_clean_sheets

   `M_events`: `xp_clean_sheet`, `xp_conceded`, corresponding `xbps`, inherited bonus allocation. No changes to `M_mins`, goals, assists, penalties, saves, defcon, card rates. Public smoke manifest uses plural component routing `xp_clean_sheets`; actual ledger field remains singular `xp_clean_sheet`.

## 4. Replaces / Integration Hook

Subclass `DefXgShrinkChallengerModel`; leave `predict` parent call and `_apply_hard_fixture_defence` inherited. Before parent prediction, prepare per-(player, fixture) residuals from original incoming features. Override `_project_event_components`: copy row, multiply only its already hard-fixture-adjusted `per90_goals_conceded` by prepared residual factor, then call `super()._project_event_components` once. This traverses inherited multi-feature assist override and base scoring; it updates clean-sheet xBPS before inherited Plackett-Luce bonus allocation. Never bypass `DefXgShrinkChallengerModel.predict`; never pre-apply hard fixture multiplier to features passed to parent.

### Execution prerequisite

 reconstruct exact default overlay context using shared helper semantics, not an approximate new club mean. Current-season `fit()` history can infer historical club from exactly two opponent IDs per completed fixture, or use verified historical club field; never map old player appearances to current club. Preserve historical `was_home`, group by fixture/club/gameweek/venue, match `_club_fixture_xg` and `_club_rates`, establish default overlay enabled with `shrink_def=0.40`. Skip clipped `a_i<=0.05+epsilon`, missing/incomplete fixture sides, absent opponent, invalid `b_i`, or non-default unknown overlay. No inference of overlay applicability merely from `defence_multiplier==1`. Until exact context parity and applicability are implemented/reviewed, prototype status is **blocked**, not runnable or smoke-ready.

## 5. Parameter Sweep Grid

mode=full,bound_scale=1.0,rho=0.25; mode=hard_only,bound_scale=1.0,rho=0.25; mode=full,bound_scale=0.5,rho=0.25; mode=identity,bound_scale=0.0,rho=0.25

### Preregistration

Four preregistered variants total; identity is inertness/inheritance ablation, excluded from candidate selection. Hard-only separates tough-fixture curvature from green-side damping; half-bound checks selection sensitivity. Fix \(s=0.40\), window 10, reliability denominator 10, \(\rho=0.25\); no global GC/CS scale sweep, no new FDR coefficient, no calendar activation gate, no per-position minutes retraining.

   Before selection evidence: require shared-state paired decomposition with (a) Champion rates + native states, (b) candidate rates + same native states, (c) same rates under oracle states for both, and component accounting including bonus. Report projection difference by baseline hazard / P(60) strata using predetermined bins, not archive-derived thresholds. Only development data in future authorized execution; freeze before any registered confirmation. Supporting legacy screen cannot authorize adoption; ADR 0066 rolling replay remains promotion primary.

## 6. Small-Sample & Cold-Start Strategy

Exact Champion fallback at absent current-season opponent evidence; retains warm historical builder seed and inherited DEF K=2400, finishing K=1800, assist GLM, learned starts. Continuous opponent fixture reliability replaces EXT-33's information-free cold-start FDR replacement. No estimation of short-panel player fixed effects; Nickell-bias correction unnecessary for this deterministic residual. `N_eff=0.5*N_seed+N_inseason` panel ramp is not mechanically added to a club-fixture signal with different units. If future learned head is added, it becomes a new preregistration; no claimed access to seed rows absent from `fit()`.

## 7. Budget-Constrained Optimizer Interaction

Maximum 10% tough / 3% easy hazard perturbation before reliability, independent of cost. Budget defenders receive no price bonus; an enabler gains value only through inherited minutes, attack, and conditional defensive ledger. Hypothesis: retaining cold-start rankings and separating residual curvature limits forced squad switches caused by removed hard-fixture logic. Cannot guarantee churn or net score: MILP selection discontinuities can turn tiny valuation changes into costly replacements. Measure actual 15-player £100m rolling replay net score; guard excess churn ≤0.50 players/GW, segment loss floors, CS/GC guards, and captaincy guard. Expected gains and reduced churn remain untested.

## 8. Point-in-Time Feature Requirements

features.player_id; features.fixture_id; features.gameweek_id; features.position_id; features.club_id; features.opponent_id; features.is_home; features.difficulty; features.per90_goals_conceded; features.defence_multiplier; history.player_id; history.fixture_id; history.gameweek_id; history.opponent_club_id; history.was_home; history.minutes; history.expected_goals; history.expected_assists; history.expected_goals_conceded

### Input provenance

Existing inherited covariates remain supplied unchanged. Derived locals `club_id`, `club_fixture_xg`, `league_xg`, `opp_xg`, `delta_def`, `n_club_fixtures`, `raw_gc`, `residual_by_fixture` are transformations of manifest, not new telemetry. Current catalog source: `docs/research/candidate-ideation/candidate_model_ideation_prompt.md`, Observed Operational Data Catalog. Exact builder source: `features/matchup_share.py::_club_fixture_xg`, `_blended_rate`, `_club_rates`, `apply_matchup_share_overlay`. Histories strictly before forecast deadline; no archive totals, target results, terminal availability, current-season hindsight, or external data.

Unavailable provenance is a blocker: overlay-applied flag and configured shrink coefficient are not admitted FeatureContract inputs. Execution must obtain verified default-build configuration or an explicit shared intermediate/provenance extension before activation; never add invented `features.matchup_overlay_applied`, `features.matchup_delta_defence`, or historical baseline-hazard fields to allowed manifest. Such fields do not exist in present catalog. Nondefault/unknown configuration remains blocked.

## 9. Python Code Skeleton

Typed partial implementation; deliberately raises on unavailable exact context. Not an executable candidate prototype. Context reconstruction/admission is required work; no silent identity fallback during a purported nonidentity experiment. Core scalar residual and inherited hook are concrete; inheritance preserved.

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

## Ledger Audit & Revisit Justification
- **Flagged Match**: `Incumbent-return displacement (zero-sum club x position start mass transfer from stand-ins to returning incumbent after 2+ DNPs)`
- **Audit Status**: Paper semantic review complete; lexical flag retained
- **Rationale**: Blocked: exact incoming matchup-overlay applicability/provenance and subtraction parity unavailable in current candidate context; implement and review before smoke. Lexical incumbent-return displacement flag unrelated: no participation mass redistribution. Paper mechanism distinct conditional on exact addon replacement; no new empirical evidence.

## Intake review

Blocked: exact incoming matchup-overlay applicability/provenance and subtraction parity unavailable in current candidate context; implement and review before smoke. Lexical incumbent-return displacement flag unrelated: no participation mass redistribution. Paper mechanism distinct conditional on exact addon replacement; no new empirical evidence.

Review record: [Near-miss ideation](../near-miss-ideation-2026-11-10.md). Execution requires separate implementation admission; AST validity does not establish model correctness.

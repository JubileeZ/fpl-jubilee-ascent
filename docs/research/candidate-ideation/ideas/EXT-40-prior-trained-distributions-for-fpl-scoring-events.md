---
idea_id: EXT-40
name: Prior-trained distributions for FPL scoring events
tier: P1
component: all
status: closed
replaces: "Compose DefXgShrinkChallengerModel forecast at the same issue with an explicit staged training context. The initial arms use public Champion fixture output p_start, p_sub_in, p_dnp, xmins_if_start, and xmins_if_sub_in as issued. Replace only xp_goals or xp_assists after the parent allocation and recompute projected_points from the full ledger. Keep xBPS inputs and realized projected bonus at Champion values for both main attack tests so the attack comparison is isolated. Preserve every model-eligible output key and both projections' externally supplied playing-time behavior. If the experimental component is missing support on a row, retain the original row component exactly. With every head disabled return the original Champion prediction unchanged. The later coherent stages need explicit adapters for distributional minutes, defence, and fixture-level bonus before the corresponding conversion. Use models.scoring_matrix.event_points and backtesting.season_rules.get_rules with the version supplied by the issue harness. Apply integer rules before expectation, with all 13 signed components included and zero score/zero exposure on blanks. Check the identity against backtesting.empirical_admission settled scoring and backtesting.forecast_export validation before optimizing. In an enabled arm require $|\\text{projected_points}-\\sum_c\\text{xp}_c|\\le10^{-9}$ on every row. Any later linked-bonus variant must be measured separately from a frozen-bonus attack arm."
grid: "component=goals,lambda=0.03; component=assists,lambda=0.03; component=goals,lambda=0.10; component=assists,lambda=0.10"
inputs: features.player_id; features.code; features.position_id; features.gameweek_id; features.fixture_id; features.is_home; features.opponent_id; history.player_id; history.gameweek_id; history.fixture_id; history.kickoff_time; history.opponent_club_id; history.minutes; history.expected_goals; history.expected_assists; history.goals_scored; history.assists
nearest_ledger_row: ATK-02 club-coherent assist mass; multi-feature goals Poisson GLM; ml_component_challenger; component_score_head; EXT-38
spec_path: ideas/EXT-40-prior-trained-distributions-for-fpl-scoring-events.md
---

# EXT-40: Prior-trained distributions for FPL scoring events

GW1–4 development screen closed. See [executed results](../ext40-gw1-4-attack-screen.md).

## 1. Concept & Football Hypothesis

A player's recent shot and chance-creation profile can change the distribution of official goals and assists at a given level of baseline production. Fit the realized counts directly and apply native FPL scoring fixture by fixture. Use an earlier season to train the relationship, so the first forecast can use it before any current-season labels arrive. Goals-only and assists-only are the first comparisons. Each can change the expected score even with Champion participation and bonus held fixed.

The input signal is the recent change in process rate relative to the player's longer baseline, with distinct fitted effects on one-event and multiple-event outcomes. EXT-38 estimated occurrence and amount of published xG. This candidate has one likelihood over mutually exclusive scoring-event counts and an ablation for the added form signal. It does not use a total-points loss or residual, player finishing estimates, recipient attribution, or the earlier ridge-start and leave-one-out assist stack.

## 2. Mathematical Formulation

Train separate count distributions for each event. For goals, set $y$ to settled `goals_scored` and $u$ to published match xG. For assists, the deployment target is settled native `assists` and $u$ is published match xA. Start with outfield rows. Goalkeeper attacking heads require independent support. Treat durations and event counts as separate observed outcomes in the factorization $P(M,Y)=P(M)P(Y\mid M)$. Fit $P(Y\mid M)$ on positive-minute labels, with $e=\min(M,90)/90$ representing the exposure of the label, and retain genuine zero event counts. Supply only issued Champion participation and duration to prediction. On issued and settled DNPs the attacking count is zero. Missing outcomes remain missing.

For each player and event, compute a pooled rate $r=(\sum wu+450b_p/90)/(\sum wm+450)\times90$, where $b_p$ is the minutes-weighted position mean per 90 from the eligible prefix. At issue index $t$, an observation at index $h<t$ gets $w=0.95^{t-1-h}$. Use source indices 1–38 and destination indices 39–76; a source training origin uses only its own prefix, and a destination origin uses the source plus eligible current rows. Compute $r_4$ with the same rule over observations in $t-4\le h<t$, using $r$ in place of $b_p$. Delayed settlement removes observations without moving the window. Use $d=\operatorname{clip}(\log[(0.05+r_4)/(0.05+r)],-1,1)$. No observations in the four-week window gives $d=0$. Missing historical process fields remove the corresponding example or route it to a position-level prediction under Section 6. No player IDs or price variables enter the fitted design matrix.

Use a shared fixture block $x_f=(I(\mathrm{home}),o_f)$. For $o_f$, sum published opponent-facing player xG within each complete settled `(season, fixture, opponent_club_id)` group, yielding one xGC observation for that opponent and fixture. Use earlier receipts only. Shrink the opponent's mean over eligible same-season fixtures toward the corresponding league mean $b$ with eight pseudo-fixtures. Set $o_f=\operatorname{clip}(\log[(0.1+\mathrm{shrunk\ mean})/(0.1+b)],-0.5,0.5)$. At a season start or with no usable opponent observations, use $o_f=0$. This prevents numeric FPL club IDs crossing season boundaries and treats unobserved promoted clubs neutrally until they have data. Read home/opponent from the dated source fixture for training and the issued fixture for prediction. A source outcome-only row with unknown deadline fixture context is omitted. Both controls and the full head use this same block and source-availability rules.

For each event and positive exposure, define reference probabilities $q_j(e,r)$ for the four categories $j=0,1,2,3+$ under a Poisson count with mean $\mu=e\max(0.01,r)$. The Poisson law is a scoring reference measure. A single penalized multinomial likelihood learns separate relative log odds for exact singles, exact doubles and the upper tail:

$$P_\theta(Y\in j\mid e,r,d,p,x_f)=\frac{q_j(e,r)\exp([1,\log(1+r),I(p),x_f,d,d^2]^\top\theta_j)}{\sum_k q_k(e,r)\exp([1,\log(1+r),I(p),x_f,d,d^2]^\top\theta_k)},\qquad \theta_0=0.$$

In this equation $I(p)$ is treatment-coded official position with MID as the reference. The matched static control drops $d,d^2$. Fit both heads on identical rows and weights. Fit the prior by minimizing source mean negative log likelihood plus $\lambda\sum_j\|\theta_j\|_2^2/2$ across the three non-reference categories. For current updates minimize $a$ times current same-regime mean negative log likelihood plus $\lambda\sum_j\|\theta_j-\theta_{\mathrm{prior},j}\|_2^2/2$, with $a=G/(G+8)$ for $G$ distinct eligible current-season label Gameweeks. At $G=0$ use $\theta_{\mathrm{prior}}$ exactly. Fit preprocessing without target labels and log source and current support. Retain strictly positive probabilities in suitable log space. For $Y\ge 3$, preserve the reference law within that category and use its exact conditional mean $\mu P_{\mu}(Y\ge2)/P_{\mu}(Y\ge3)$. Forecast $\sum_j P_j\,E(Y\mid j)$, then average over Champion did-not-play, start and cameo states. This preserves the contribution of four-plus events. A zero-exposure state has a point mass at zero. Fit and infer the same conditional law. The initial serve approximation treats the issued conditional mean duration as the duration within each playing state. Keep a same-approximation static control and audit this approximation separately when the minutes arm supplies a discrete duration distribution.

Construct the same process predictors at source and destination origins. For source training enumerate confirmed source player-fixtures with observed positive-minute labels, build predictors on strictly earlier settled source rows and use the player's source-period position. For target-season updates regenerate these predictors at each earlier issue or reuse immutable issue records. Join the labels as they are made available, using `(season, player_id, gameweek_id, fixture_id)`. No filtering by target-week role or outcome other than the explicit positive-exposure training condition. Include source and destination zero-minute outcomes in unconditional evaluation where recorded. Use source native assist labels only if the source and destination definitions are documented as equivalent. Otherwise fit the prior head to four soft process targets $P_{\mathrm{Pois}(u)}(j)$ using that fixture's settled xA. In 2025–26 with the 2024–25 seed, this is a process-only GW1 bridge. The first destination native labels enter at their own settlement. If the bridge's xA coverage is unavailable, keep Champion and fail early preflight. [Official 2025/26 changes to assists and BPS](https://www.premierleague.com/en/news/4373187).

## 3. Decoupled Architecture Placement

First two arms replace the goal or assist expectation independently in the Event Rate Engine. The remaining points ledger follows below. Prototype the later arms only after establishing label coverage and auditing each new mechanism against Candidate Ledger locks. For any discrete count model, score $E[s_c(Y)]$ over integer outcomes using the native scoring function. Aggregate fixtures into Gameweeks after scoring each fixture, including double Gameweeks. Finish with the sum of all 13 expected ledger contributions.

| Component | Learned target and official conversion | Isolation and support |
|---|---|---|
| `xp_goals` | Official goal count. Multiply expected count by native position and season goal points. | Goals-only arm, initially outfield. Keep native goalkeeper goal weight and the baseline keeper estimate until supported. |
| `xp_assists` | Official awarded assist count. Multiply expected count by 3. | Assists-only arm, initially outfield. Process prior by rule regime as above. |
| `xp_minutes` | Joint distribution of DNP, positive start minutes and positive cameo minutes. Fit multinomial duration-bin logits with past counts and prior start/cameo probabilities, with within-bin conditional means from settled durations. Score $P(M>0)+P(M\ge60)$ and report $E(M)$. | Later. Fit against issue-eligible roster with known zeros. Test isolated minutes points and xMins, then a separate coherent propagation arm which re-integrates other event laws over its duration states. Preserve hard exclusions, blanks and explicit minutes overrides. |
| `xp_clean_sheet` | Joint categorical outcome over the recorded clean-sheet flag and individual goals conceded. Use 60-minute and position eligibility from the dated native scoring context and score the observed award. | Later. At fit verify the zero/one award and eligibility support, including any unusual cases. Carry a consistent pair of marginals into the joint defence arm. Compare each isolated component first. |
| `xp_conceded` | Same joint count of recorded individual goals conceded and clean-sheet flag. For eligible positions compute $-E[\lfloor C/2\rfloor]$ from count tails. | Later. This learns discrete probabilities directly, with no team scoreline Poisson or separate shape swap. Train from official charged counts. Do not infer an individual's charged count from the final club score. |
| `xp_saves` | Count of official goalkeeper saves. Fit ordered native save bands with $s=0,1,2,\ldots$ representing $3s\le Y<3(s+1)$. Score $\sum_{k\ge1}P(Y\ge3k)$. | Later, keeper-only. Use distinct conditional threshold evidence. No standalone negative-binomial dispersion substitution. |
| `xp_defcon` | Native hit label from the official recorded action count at 10 for DEF and 12 for MID/FWD. Model the duration-conditioned threshold outcome. Two points per hit. | Later. 2023–24 and 2024–25 are natively inapplicable, with two-point forecast structurally zero. For 2025–26 GW1–4 there is no compatible prior-season Defcon panel. Preserve Champion until dedicated admitted data establishes same-rule support. Missing data cannot yield zero labels. |
| `xp_bonus` | Official categorical award 0/1/2/3 for a fixture. Fit the joint assignment distribution over observed native tie patterns with probability proportional to the product of fitted category odds among eligible player assignments, normalized over rule-valid assignments. Score each marginal $\sum_k kP(B=k)$. | Later. Requires fixture-complete player rows and verified native tie rules, including tied-place awards. Validate legal draws and nonzero bonuses on known ties. With incomplete rows or unverified rules, retain the fixture's Champion bonus. A redesigned head tests official awards, without refitting xBPS weights or Plackett–Luce temperature. |
| `xp_yellow_cards` | Official yellow count. Learn distribution of the booked/not-booked outcome with its positive-count tail if present. Apply native card deduction. | Later. Verify zero-minute cards and red coexistence against official settlement. Do not create a zero-minute event from exposure alone. |
| `xp_red_cards` | Official red count, with an optional joint card outcome if isolated results justify it. Apply native red deduction and validate coexistence with yellow. | Later, contingent on authenticated positive support across weeks and source-to-target card-definition parity. |
| `xp_penalties_saved` | Official fixture penalty saves. Apply goalkeeper saving-penalty points to expected count. | Later. Requires eligible keeper rows with verified positive and negative coverage. Penalty attempts and conversion are unobserved. Use unconditional fixture count with categorical head only if support passes. |
| `xp_penalties_missed` | Official penalty misses. Apply native deduction to expected count. | Later. No inference of attempts from xG or assignment from terminal taker order. Keep the existing component if authentic support is insufficient. |
| `xp_own_goals` | Official own goals. Apply native deduction to expected count. | Later. Keep existing estimate if authentic support cannot support a candidate. No pooled rare-event bundle. |

All later arms use the same separation of model target, discrete expectation, and score conversion, without assuming one probability model fits every event. For discrete count heads with a final pooled category, specify a distribution inside that category before any fit and average the native scoring function over it. For sparse penalty, red and own-goal heads, require at least 30 genuine positive labels over at least 10 distinct eligible Gameweeks in an admitted compatible source panel plus a nonempty set of verified negatives. Validate row provenance, rather than inferring support from a column name or zero-filled ingest. Until a component's support and ledger checks pass it remains baseline-backed and is excluded from claims of learned coverage. Preserve each component's native applicability independently.

## 4. Replaces / Integration Hook

Compose `DefXgShrinkChallengerModel` forecast at the same issue with an explicit staged training context. The initial arms use public Champion fixture output `p_start`, `p_sub_in`, `p_dnp`, `xmins_if_start`, and `xmins_if_sub_in` as issued. Replace only `xp_goals` or `xp_assists` after the parent allocation and recompute `projected_points` from the full ledger. Keep xBPS inputs and realized projected bonus at Champion values for both main attack tests so the attack comparison is isolated. Preserve every model-eligible output key and both projections' externally supplied playing-time behavior. If the experimental component is missing support on a row, retain the original row component exactly. With every head disabled return the original Champion prediction unchanged. The later coherent stages need explicit adapters for distributional minutes, defence, and fixture-level bonus before the corresponding conversion. Use `models.scoring_matrix.event_points` and `backtesting.season_rules.get_rules` with the version supplied by the issue harness. Apply integer rules before expectation, with all 13 signed components included and zero score/zero exposure on blanks. Check the identity against `backtesting.empirical_admission` settled scoring and `backtesting.forecast_export` validation before optimizing. In an enabled arm require $|\text{projected_points}-\sum_c\text{xp}_c|\le10^{-9}$ on every row. Any later linked-bonus variant must be measured separately from a frozen-bonus attack arm.

## 5. Parameter Sweep Grid

`component=goals,lambda=0.03; component=assists,lambda=0.03; component=goals,lambda=0.10; component=assists,lambda=0.10`

## 6. Small-Sample & Cold-Start Strategy

Use exactly the lifecycle-authorized preceding season. Roll every training origin as-of within the source season. A pinned final source panel may supply settled outcome labels, but must not supply source-time covariates derived from terminal player metadata or later rows. Use independently dated prior fixture/availability data wherever source inclusion or timing depends on it. When a dated source roster is missing for an attack training origin, the positive-exposure conditional likelihood may use settled rows from the source season, provided official position is verified for that fixture and the predictor panel uses only verified earlier fixture records. Drop rows whose provenance is insufficient. This permission does not apply to minutes or unconditional labels that need the actual pre-deadline risk set. Distinguish source prefix reconstruction from strict admitted issue-time evidence. Never use terminal roster, price, opponent strength, future settlement or availability as covariates. The Phase 1 attack features require no prior-season Champion forecasts. Any later feature that depends on those forecasts must rebuild them with their source-specific information set.

Read seed player positions and source element IDs from the pinned `seed_players` table or staged `players.parquet`, checking that the position was effective for the source fixture against dated roster information or verified season-level immutability. The `forecast_adapter` empirical stage rewrites `code` into `seed:<token>` or `absent:<id>` after the normal admitted ID mapping. Where that adapter is used, resolve original identity from the code-verified pre-stage roster mapping before any token rewrite. Reject secondary name-only links for the learner. Code collisions and unresolved identities fall back to pooled inference. Log the raw seed column mask and support by category and position before testing. No premise of a valid individual link for every issued player.

With no current-season history there is a fitted prior across the entire eligible league from source-season rolling rows. For linked players, use official immutable `code` with verified unique season mapping for source-to-destination process history, using the destination issue position. Never join numeric element IDs between seasons. A promoted-club player with prior verified Premier League history can retain it. A player with no linked history uses destination position exposure-weighted source pool, with $d=0$ until own evidence arrives. This includes newly listed players and promoted players outside the previous Premier League. The model contains no club parameters. Missing stable identity also uses the position pool. An unsupported position or missing pooled head returns the exact Champion component with a recorded fall-back reason. Account separately for played, linked-history, position-only, and fallback rows. No activation-by-Gameweek threshold. Demonstrate a changed goal estimate in both the live-updating and frozen-prior variants at GW1 with zero current labels. Require the assist head to do the same and disclose the process-only nature of the seed when definitions change. If seed inputs cannot be admitted or do not change GW1 projections, fail the early-start preflight for that head and stop its advancement.

## 7. Full Squad & Budget-Constrained Optimizer Interaction

The components use league-wide training and set-piece-agnostic prior process rates. Price stays in the same optimizer constraints and away from the fitted head. The working hypothesis is that a pooled form signal improves selection among similarly priced regular starters without promoting a recent one-event cameo into a transfer target. Report transfers, credited XI choices, captain choices, gross points, transfer hits and net points. Report the £4.5m–£5.5m band and the total squad separately using issue-time prices, as well as players lacking a prior identity. Common eligible fixture/player/lead keys across variants. Hold fixed the £100m 15-player neutral GW1 start, max three players per club, native rules, chips, auto-subs, solver options, inputs and quality certificates. Use six-Gameweek rolling Strategic replay with 600s certified cap and zero gap target when qualified. The legal formation XI is an intermediate diagnostic. Apply existing churn and projection guards and canonical segment floors.

Run the two first named arms before the alternate penalties. For each comparison use the identical static control with `d` and `d²` disabled, Champion, and a prior-only diagnostic holding the GW1 fitted coefficients fixed through GW4 while refreshing admissible issue covariates. These controls are fixed designs. Register goals plus assists as a separate combination if both isolated results advance. Run later isolated arms before combining verified heads. Any combined candidate must itself qualify, including the early-start screen.

Preregister a GW1–4 table before running. For each head and comparator, report paired native fixture component MSE (mean squared error, lower is better), signed bias (forecast minus outcome, ideal zero), categorical log loss on the common unconditional counts (lower is better), and fixture/lead coverage and Champion fallback rate. For Champion's log-loss diagnostic, derive its per-90 count mean by dividing its unconditional expected event count by its expected exposure. Apply that rate in reference count laws calibrated to each state duration, and mix by Champion state probabilities with point mass at zero for DNP. Mark this comparator distribution as derived. Report paired legal credited XI and independent rolling net decisions (higher is better), including the frozen-prior arm. The candidate-specific early advancement screen requires lower pooled GW1–4 component MSE than Champion and the matched static control, a changed legal XI or rolling decision, and nonnegative GW1–4 rolling net points versus Champion. Apply the ADR 0071 material-harm floor separately. Four Gameweeks are a weak inference base and the screen does not grant promotion. Repeat overall and segment cuts through GW38 with canonical common-population guards, leave-one-component-out ledger attribution, decision ablation and full six-lead replay. Native realized net points, paired by Gameweek, remain the primary comparison.

Develop on 2025–26 with 2024–25 seed. Require independently reproduced admitted development prefix and explicit receipt versus reconstruction provenance. Freeze at most one winner before a single untouched 2024–25 Historical Filter test with 2023–24 seed, subject to the corresponding admission and guard checks. Freeze code, component switches, prior construction algorithm, hyperparameters, support rules, evaluation masks and issue update protocol. Refit the frozen recipe with the authorized source and each new issued receipt according to that protocol, and preserve the prior-only diagnostic as a distinct no-update control. Apply active ADR 0069–0071 replay rules, including qualification in both seasons and all applicable projection and segment gates. Keep 2026–27 sealed from this work. Selection and any adoption follow the existing registered protocol.

## 8. Point-in-Time Feature Requirements

`features.player_id; features.code; features.position_id; features.gameweek_id; features.fixture_id; features.is_home; features.opponent_id; history.player_id; history.gameweek_id; history.fixture_id; history.kickoff_time; history.opponent_club_id; history.minutes; history.expected_goals; history.expected_assists; history.goals_scored; history.assists`

## 9. Python Code Skeleton (Optional)

```python
from __future__ import annotations

from collections.abc import Callable
from typing import Literal

import pandas as pd

from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel


class PriorTrainedScoringEvents(DefXgShrinkChallengerModel):
    def __init__(
        self,
        component: Literal["goals", "assists"],
        predict_component: Callable[[pd.DataFrame, pd.DataFrame], pd.Series],
    ) -> None:
        super().__init__()
        self.component = component
        self.predict_component = predict_component

    @property
    def name(self) -> str:
        return f"prior_trained_{self.component}"

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        baseline = super().predict(features_df, horizon)
        # Bound predictor owns the staged seed, current receipt, model fit and cutoff.
        # Join by full fixture key and return baseline-indexed native point expectations.
        # Missing values mean unsupported. Supported blanks explicitly return zero.
        expected_points = self.predict_component(features_df, baseline)
        if not expected_points.index.equals(baseline.index):
            raise ValueError("Component predictions must match baseline fixture rows")
        result = baseline.copy()
        component_column = f"xp_{self.component}"
        result[component_column] = expected_points.combine_first(result[component_column])
        ledger = [column for column in baseline.columns if column.startswith("xp_")]
        if len(ledger) != 13:
            raise ValueError("Expected the 13 native scoring components")
        result["projected_points"] = result[ledger].sum(axis=1)
        return result
```

Use typed issue context containing source-panel digest, season, cutoff, fixture availability, canonical fixture keys and settled receipt digest. Keep the fitting recipe out of the prediction lambda. Use a candidate-specific factory in the research harness before considering normal registration. Reuse a cached prior only when its pinned source and specification match. Digest the immutable fit inputs and all fixture forecasts. Verify that appending, changing or deleting target and later rows, late-settling earlier rows, and changing unobserved future fixtures or terminal metadata leave already-issued results identical. Inject duplicated fixture rows and invalid/nonfinite inputs and require rejection. Verify nonzero GW1 prior effects, Champion parity with disabled heads, unchanged unrelated components, DGW fixture additivity, BGW zeros, hard-DNP or explicit override preservation, finite score identity, and deterministic repeated predictions. Round-trip integer cases using native appearance 0/1/59/60, concession 1/2/3/4, saves 2/3/5/6, DEF/MID/FWD Defcon boundaries, and native goalkeeper goal weights. Confirm that only the registered component changes before adding the later coherent arms.

## Candidate Ledger audit

- Automated ATK-02 match from shared goals and assists terms. ATK-02 rescales club assist mass by a club goals-to-assists ratio. EXT-40 fits player-fixture event-count probabilities without club mass rescaling.
- Goals Poisson GLM lock covers fitted mean rate from xG, threat and matchup. EXT-40 tests recent relative form in a prior-trained categorical count likelihood against an otherwise identical static control.
- `ml_component_challenger` lock covers earlier ridge participation, goals residual and recipient-finishing stack. `component_score_head` fits total fantasy points. EXT-40 starts with native event counts and fixed participation. EXT-38 targets published xG.
- Queued scope covers goals-only and assists-only implementation and comparison. Remaining component designs require separate provenance, support and lock checks before implementation.

[Candidate Ledger](../../candidate-ledger/candidate-ledger.md) · [EXT-38 development screen](../ext38-deadline-backtest.md)

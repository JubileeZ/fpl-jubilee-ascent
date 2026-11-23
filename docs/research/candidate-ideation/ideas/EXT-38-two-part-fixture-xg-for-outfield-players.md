---
idea_id: EXT-38
name: Two-part fixture xG for outfield players
tier: P1
component: xp_goals
status: closed
replaces: "Override _project_event_components on a DefXgShrinkChallengerModel subclass. In fit, store the eligible staged history after the parent fit. In predict, use the deadline position map to prepare player estimates, then delegate through the inherited prediction chain. For an eligible state with m > 0 projected minutes and a positive incoming per90_xg, pass a copy of the row with per90_xg = max(0, incoming per90_xg + (two_part_xg \u2212 single_mean_xg) \u00d7 90/m). Call the inherited scorer once so its finishing offset, matchup scaling, penalty handling, native points, and xBPS consume the adjustment in their normal order. Preserve the participation mixture and all other scoring inputs. Score each fixture separately and aggregate through the existing replay."
grid: "k=8,k_def=16; k=16,k_def=32"
inputs: features.player_id; features.position_id; features.gameweek_id; features.fixture_id; features.per90_xg; history.player_id; history.gameweek_id; history.fixture_id; history.minutes; history.expected_goals
nearest_ledger_row: "EXT-12: Sequential attacking opportunity change detection"
spec_path: ideas/EXT-38-two-part-fixture-xg-for-outfield-players.md
---

# EXT-38: Two-part fixture xG for outfield players

## 1. Concept & Football Hypothesis

Players with equal xG per 90 can differ in how often they register positive fixture xG and how large their positive totals are. Estimate and pool those quantities separately across DEF, MID, and FWD. A player's past xG can capture attacking involvement within any official FPL position, including when their tactical role differs from their FPL listing. Test whether the product forecasts future xG better than a single pooled mean.

## 2. Mathematical Formulation

At issue Gameweek t, use staged, settled player-fixture rows from Gameweeks before t. Set y to recorded fixture xG, e to min(minutes, 90)/90, z to 1[y > 0], and w to 0.95^(t − 1 − row Gameweek). Keep genuine zero xG on positive-minute rows. Parse xG and minutes numerically. Exclude missing, nonfinite, or negative values and zero-minute rows from fitting. Require unique (player_id, gameweek_id, fixture_id) keys. Pool DEF, MID, and FWD separately using each player's official position at the issue deadline. Let K = k_def for DEF and K = k for MID and FWD.

- **Occurrence.** Model q(e) = 1 − exp(−λe). Fit one λ per position by maximizing weighted Bernoulli log likelihood, then fit one λ per player using the same likelihood with K pseudo-fixtures at e = 1 and positive fraction q_position(1). Use a bounded scalar fit on [10⁻⁶, 20].
- **Positive amount.** Use duration bands (0, 30], (30, 60], (60, 90] minutes. Within the predicted duration band, estimate a player's conditional amount as (Σ w y + K a_position) / (Σ w + K), using only positive-xG appearances in that band. Use the position's weighted positive-xG mean in the band as a_position, falling back to its all-band positive mean.
- **Prediction.** Cap duration at 90 minutes for both estimators. Two-part xG is q(e) × a_player for the projected duration, and zero at zero exposure. For the matched single-mean control, estimate xG per 90 as (Σ w y + K r_position) / (Σ w e + K), where r_position = Σ w y / Σ w e over the same position pool. Multiply by e. Use the same screened rows, position pools, recency, durations, and K for both models.

## 3. Decoupled Architecture Placement

xp_goals. Apply the correction to DEF, MID, and FWD. Estimate state-conditional fixture xG from the same projected start and cameo minutes used by the Champion. Use current-season process history to estimate the correction and carry the Champion's seeded rate through to scoring, including its defender shrinkage. Preserve the player's official FPL position for scoring and squad constraints. Use zero direct xG correction for goalkeepers.

## 4. Replaces / Integration Hook

Override _project_event_components on a DefXgShrinkChallengerModel subclass. In fit, store the eligible staged history after the parent fit. In predict, use the deadline position map to prepare player estimates, then delegate through the inherited prediction chain. For an eligible state with m > 0 projected minutes and a positive incoming per90_xg, pass a copy of the row with per90_xg = max(0, incoming per90_xg + (two_part_xg − single_mean_xg) × 90/m). Call the inherited scorer once so its finishing offset, matchup scaling, penalty handling, native points, and xBPS consume the adjustment in their normal order. Preserve the participation mixture and all other scoring inputs. Score each fixture separately and aggregate through the existing replay.

## 5. Parameter Sweep Grid

`k=8,k_def=16; k=16,k_def=32`

Both variants cover all outfield positions. Double DEF pooling weight as a fixed design choice for sparser player-level evidence. Retain the same K in the two-part estimator and the matched control at each position.

## 6. Small-Sample & Cold-Start Strategy

Use the unchanged Champion branch if the player has no valid positive-minute history, their position has no positive-xG labels, or the state has zero projected exposure. Within a usable pool, missing player positives in a band inherit the position mean through pooling. Keep the stock blank and hard-DNP paths. The aggregate xG feed includes penalties and is rounded. Interpret occurrence as positive published fixture xG. Leave the inherited penalty handling in place.

## 7. Budget-Constrained Optimizer Interaction

Development screen in S-1 (2025–26, 2024–25 seed). At each issue, emit predictions for the available leads 0–5 using the same origin history and weight states with the Champion's issued probabilities. On the common settled DEF/MID/FWD player-fixture population, compare unconditional fixture xG MSE (mean squared difference from published xG, lower is better) and signed bias (mean predicted minus recorded xG, ideal zero) by lead and official position. Include recorded zero-minute fixtures in scoring. Compare the candidate's exposure-scaled xG input against both the matched single-mean forecast and the unmodified Champion xG input scaled by projected exposure. Require lower pooled xG MSE than both comparators and a change in actual planning decisions before considering a replay winner. Confirm that setting the two-part correction to zero reproduces Champion outputs.

Report changes in defender transfers and starts, plus an S-1 diagnostic using the same variant with DEF correction set to zero on the constrained formation XI screen. For attacking involvement, also report xG results for each official position's top quartile of lagged xG/90 among players with at least 360 settled minutes by the issue deadline. Keep that subset diagnostic. Tactical position is unobserved in these inputs.

Use full GW1–38 six-Gameweek Strategic rolling MILP, 600s certified cap and zero target gap. Primary metric is native realized squad points less hits, summed across Gameweeks. Require positive paired net points vs Champion, applicable projection guards, segment floors, and admitted GW1–7 parity. Freeze at most one S-1 winner before the S-2 filter (2024–25, 2023–24 seed, admitted GW1 parity). Keep S (2026–27) sealed. Apply [ADR 0071](../../../adr/0071-certified-solver-budget-and-milp-qualification-calibration.md) and the [replay input audit](../pre-slate-search-2026-11-21.md). Report results on reconstructed origins with their provenance limitation.

## 8. Point-in-Time Feature Requirements

`features.player_id; features.position_id; features.gameweek_id; features.fixture_id; features.per90_xg; history.player_id; history.gameweek_id; history.fixture_id; history.minutes; history.expected_goals`

## 9. Python Code Skeleton

```python
from __future__ import annotations

import pandas as pd

from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel


class TwoPartFixtureXgChallengerModel(DefXgShrinkChallengerModel):
    """Prototype skeleton for EXT-38."""

    def __init__(self, k: float, k_def: float) -> None:
        super().__init__()
        self.k = k
        self.k_def = k_def

    def _project_event_components(
        self,
        row: pd.Series,
        position: str,
        expected_minutes: float,
        *,
        clean_sheet_minutes: float,
        p_sixty_mins: float,
    ) -> dict[str, float]:
        raise NotImplementedError("Fit both xG estimates and apply the state-level correction")
```

## Leakage acceptance checks

- At deadline t, use only earlier gameweeks with fixtures evidenced as settled by the staged history. Both legs of a Double Gameweek use the same origin cutoff. Rebuild fits and pools from each origin's own staged history. Keep forecast issue, target, player, and fixture keys separate, and join labels after issuance.
- Mutate or remove target-and-later realized xG, minutes, xA, BPS, ICT, and points upstream of staging. Require identical fit inputs and forecasts for every lead at t. Delay settlement on an earlier fixture and check that neither part of the fit can see its label until the next eligible origin. Test numeric-string xG, zero vs missing xG, and duplicate keys.
- Reuse the [#205 forecast-then-label pattern](../component-score-head.md) for research diagnostics. Forecast xG is a pre-deadline model output. Recorded target-fixture xG is a post-settlement label.

## Ledger review

- Source — FPL modeling ideation, 2026-11-23. Disposition — closed after development forecast screen.
- Closest mechanism — `EXT-12` estimates changes in latent attacking opportunity over time with a Tweedie likelihood. This proposal uses fixed recency and explicitly estimates occurrence and positive xG amount for each duration.
- `b2_res_*` estimates a hurdle or residual on total FPL points. `component_score_head` refits total fixture points from forecast components. `EXT-08` models joint xG/xA allocation. This proposal estimates aggregate fixture xG alone and uses the existing scorer.
- `EXT-20` and `EXT-32` use threat to identify attacking defenders and relax defender shrinkage. EXT-38 uses the same two-part xG mechanism across every outfield position and retains the Champion defender prior and scoring.
- Intake keyword match — `cs_exposure_challenger` modifies defensive clean-sheet exposure given a 60+ minute start. This proposal uses projected duration as exposure for attacking xG and leaves clean-sheet exposure untouched. Reviewed as distinct. Existing locks apply.
- [Candidate Ledger](../../candidate-ledger/candidate_ledger.csv).

## Development result

Both fixed variants trail their matched single-mean xG controls on 2025–26 GW1–38. Weekly legal XI screen completed. [Deadline-safe backtest results and reproduction](../ext38-deadline-backtest.md).

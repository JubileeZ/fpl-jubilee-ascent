---
idea_id: EXT-41
name: Champion component features for event counts
tier: P1
component: all
status: closed
conflicts_with: after:EXT-40
spec_path: ideas/EXT-41-champion-component-features-for-event-counts.md
---

# EXT-41: Champion component features for event counts

## 1. Hypothesis

Issue-time Champion components summarize information from model branches that use different inputs. Test whether projected goals, assists, minutes, defensive events and bonus improve forecasts of official goals and assists beyond EXT-40's process and fixture inputs. Fallback experiment if either EXT-40 attack component misses its early gate.

## 2. Model

Reuse [EXT-40](EXT-40-prior-trained-distributions-for-fpl-scoring-events.md) categorical count likelihood, exposure reference, priors and exact upper-tail mean. Append signed `log1p(abs(xp_c))` for each enabled Champion component. Center and scale using training-only means and standard deviations from the source season, with unit scale for zero variance. Keep transforms frozen for current-season updates. Treat the Champion vector as issued before the deadline, preserving legitimate zeroes and native position eligibility.

For each target train three matched arms on identical keys and with identical prior weighting and regularization. Use EXT-40's static specification as the common base. Its recent-form terms missed the GW1–4 comparison in both components. Arm A uses no Champion components. Arm B adds only the same-component prediction. Arm C adds all 13. A→B tests direct forecast signal. B→C tests incremental context from the other components. No independent retuning, residual-to-points loss, or learned total-points output.

## 3. Forecast assembly

Estimate native goal or assist counts for each participation scenario. Weight with the original Champion state probabilities. Apply official position and season rules, replace only the targeted points component, and reconcile the signed ledger to `projected_points`. Preserve the original snapshot even when both attack components advance. The goals head and assists head consume the same unchanged Champion feature vector. Neither consumes the other's experimental outputs.

## 4. Issue-time boundary

Reuse EXT-40 historical and target primitives. Add `backtesting.forecast_export.REQUIRED_COMPONENTS` from immutable Champion output keyed by issue season, deadline, lead, target Gameweek, fixture and player. Produce source-season Champion forecasts by replaying each source issue using only its own date-admitted feature inputs and earlier settled history. A prior-season model trained on full-source labels cannot regenerate its own training predictors. Preserve source rules, projected values, model hash and input digests. Treat any forecast issued at or after the target kickoff or lacking verified issue inputs as unavailable. Join official event labels after forecast issuance. Match lead-0 training rows between arms. Report leads 0–5 separately on common evaluation keys.

## 5. Fixed comparisons

Goals and assists separately. Use fixed `lambda=0.03` from the first EXT-40 attack arms for all comparisons. Preserve the predeclared A, B and C feature blocks. Run an unchanged Champion arm. Arm C is the advancement arm. Require C to beat A and B on forecast error to attribute value to the full feature block. If only B beats A, report same-component value and no demonstrated value from adding the rest. Source-constant features keep zero fitted coefficients, including `xp_defcon` under 2024–25 rules. Eligible 2025–26 updates can estimate a previously constant feature only after nonzero native-rule support enters the fit.

## 6. GW1 support

Fit source coefficients before the first target-season deadline. GW1 target-season data may enter the issued Champion features if available before the deadline. It supplies zero training labels. Use EXT-40's assist xA bridge if the source and destination FPL assist rule definitions differ. Keep the source-only GW1–4 comparator, pre-deadline roster as-of rules, stable player identity and position fallback. Require forecast differences at GW1, including reporting for players without prior identity. Missing source-season issue forecasts or unusable features block this experiment. Do not substitute forecasts reconstructed from terminal snapshots.

## 7. Gate

Apply the EXT-40 GW1–4 gate independently to each attack component. Require lower fixture component MSE than Champion and the matched static control, at least one changed selection or rolling decision, and nonnegative paired rolling net points. Compare C with A and B as declared above. Screen on S-1 Dev. Fit no data from active validation. Combine only isolated passers from both components and rerun the early gate and signed-ledger checks on the combined arm.

## 8. Implementation checks

- Verify unique issue keys, source feature digests and feature cutoff. Test that target/later labels, terminal metadata and candidate-generated components cannot alter issued Champion feature rows.
- Assert frozen source coefficients at GW1 with zero target-season labels. Assert all 13 signed components sum to each fixture xP. Preserve blanks, hard DNPs, explicit minutes overrides and double-Gameweek fixture independence.
- Compare on common populations. Report missing prior coverage and genuine Champion fallback separately. Do not advance if common early comparison loses affected players through missingness.

## 9. Candidate Ledger audit

`component_score_head` fit direct fixture total-points ridge from Champion forecasts. `b2_res_*` fit a hurdle or total-point residual on a reconstructed baseline. EXT-41 fits realized event-count distributions and uses official scoring for points conversion. No use of BPS or ICT outcomes as features, no retry of either locked specification. Queue after EXT-40 and revisit the ledger before implementation.

[Candidate Ledger](../../candidate-ledger/candidate-ledger.md) · [Direct score-head experiment](../component-score-head.md)

[GW1–4 results and reproduction](../ext41-gw1-4-attack-screen.md) · [Cross-device exploration handoff](../ext40-ext41-exploration-handoff.md)

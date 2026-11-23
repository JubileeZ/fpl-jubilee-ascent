# EXT-40 GW1–4 attack screen

**Disposition.** Both components ran at GW1 with zero current-season training labels. All four dynamic goal and assist variants beat Champion on fixture component MSE and trailed their matched static controls. No early gate pass, candidate rolling replay, combined arm or promotion claim. No new Dead Lever lock. [Original dossier](ideas/EXT-40-prior-trained-distributions-for-fpl-scoring-events.md) · [Queued Champion-feature follow-up](ideas/EXT-41-champion-component-features-for-event-counts.md)

## Historical scope

S-1 Dev 2025–26 GW1–4, trained initially on 2024–25. Source positions and codes from dated official rosters. Earlier process features from eligible published receipts. Both heads fit 9,294 source examples from 33 Gameweeks. Source GW1–2 lacked usable earlier labels for the baseline. Source GW23, GW33 and GW35 lacked a supported pre-deadline fixture snapshot. Assist prior used soft xA count categories across the change in native assist rules. Post-GW1 online updates used only native labels available at each issue. The frozen prior comparator retained source coefficients through GW4. [Source origins](prototypes/ext_40/evidence/source_origins.csv) · [Category support](prototypes/ext_40/evidence/source_category_support.csv) · [Issue provenance](prototypes/ext_40/evidence/issue_provenance.csv)

With no destination labels at GW1, each dynamic and frozen-prior head changed 454 immediate player-fixture projections. Predictions retained Champion playing states and other scoring components, and used point-in-time fixture, venue and roster context. Forecast windows retained six Gameweeks. Primary accuracy diagnostic used 2,501 matched lead-0 outfield player-fixture rows per arm, including recorded zero-minute outcomes. Unmatched labels reported, excluded uniformly. [Issue results](prototypes/ext_40/evidence/by_issue.csv) · [Lead coverage](prototypes/ext_40/evidence/fixture_lead_coverage.csv)

## Forecast and decision results

- **Goals.** Best dynamic MSE **0.87923850** versus Champion **0.93910309** and matched static **0.87923248** at λ=0.03. Dynamic legal credited XI **205**, Champion **174**. Three Gameweeks changed starters. λ=0.10 also missed its static comparison.
- **Assists.** Best dynamic MSE **0.35062071** versus Champion **0.35215628** and matched static **0.35061999** at λ=0.10. Dynamic legal credited XI **187**, Champion **174**. Two Gameweeks changed starters. λ=0.03 also missed its static comparison.
- **Champion replay.** Independently completed certified six-Gameweek rolling replay through GW4, scoring **220 net** with paired opening anchor `opening-anchor-809d4afb3e40c205`. Byte-for-byte Champion forecasts matched the forecast-screen reference at all four issues. No dynamic variant qualified for candidate rolling replay. Candidate rolling net, hit differences and ADR 0071 floor comparison unmeasured. The legal credited XI points provide decision diagnostics. [Champion scores](prototypes/ext_40/evidence/champion_scores.csv)

[All arms](prototypes/ext_40/evidence/summary.csv) · [Bound experiment identity](prototypes/ext_40/evidence/run_identity.json)

## Metric definitions

- **Component MSE.** Mean squared error between fixture component xP and native settled points for that component. Lower is better. Matched static and Champion both required for advancement, with strict lower MSE. **Signed bias.** Mean forecast minus settled component points, ideal zero.
- **Categorical log loss.** Mean negative log probability of the settled 0/1/2/3+ count class. Lower is better. Exact assist log loss is infinite in all arms because two observations received zero probability on the realized class. Separately labeled clipped log loss uses machine-tiny probability as the diagnostic floor. Same fixture cohorts and Champion participation across arms.
- **Legal credited XI points.** Official points credited to legal XI after auto-subs and before captain multipliers. Higher is better. Compare same-week independent £100m squad and formation against Champion. **Rolling net points.** Credited points with applicable captain/chip effects minus hit costs across a carried ownership trajectory. Higher is better. Benchmark same-policy Champion. Short early window provides a screen, with no promotion authority.

## Reproduction

From repository root, use `.tmp/agent/explore-candidate/ext_40` for work. Add repository root and `docs/research/candidate-ideation` to `PYTHONPATH`.

1. Run `python -m prototypes.ext_40.prepare .tmp/agent/explore-candidate/ext_40` to recover pinned sources and stage admitted Dev receipts.
2. Run `python -m prototypes.ext_40.audit`, then `python -m prototypes.ext_40.run .tmp/agent/explore-candidate/ext_40` for all isolated forecast variants and controls.
3. For the Champion only, set `historical_replay_inputs.MIRROR_ROOT` to the absolute `<work>/mirror` path and run `run_s1_replay.main()` with `--work <work> --through 4`. Standard solver policy, neutral opening anchor, native chip calendar and certified zero-gap acceptance.
4. Reconcile active arm summaries against the paired Champion and the matched static arm for the same λ. Advance to candidate rolling replay only after both forecast comparisons pass. This screen advanced zero arms.

## Verification

Spec/math and standards reviews passed. Staged feature audit passed. 87 focused tests and repository Ruff check passed. Pyright reported pandas typing diagnostics in the research code. Git Bash sandbox initialization blocked `tests/verify.sh`.

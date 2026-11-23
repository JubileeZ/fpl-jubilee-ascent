# EXT-41 GW1–4 attack screen

**Disposition.** Both full-feature arms missed their forecast gate. All three feature blocks reduced lead-0 Event Component MSE versus the Model Champion, but the static count model was best for both goals and assists. Neither the same-component feature nor the full feature block improved on static. No EXT-41 rolling or combined arm advanced. [Fixed specification](ideas/EXT-41-champion-component-features-for-event-counts.md) · [Forecast results](prototypes/ext_41/evidence/summary.csv)

## Forecast results

S-1 Dev 2025–26 GW1–4. Fit on 2024–25 source origins, fixed `lambda=0.03`, and only previously settled destination labels at each deadline. Arm A used static process and fixture features. Arm B added the matching issue-time Champion component. Arm C added all 13 issue-time Champion components. The source-only C diagnostic froze its coefficients throughout GW1–4.

| Event Component | Champion | A (static) | B (matching component) | C (all 13) | C (source-only) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Goals MSE | 0.93910309 | **0.87923248** | 0.88015395 | 0.88427109 | 0.88391723 |
| Assists MSE | 0.35215628 | **0.35063795** | 0.35071008 | 0.35146875 | 0.35137233 |

Each comparison used 2,501 matched outfield player-fixture observations, including recorded zero-minute events. No unmatched lead-0 labels. Reported all six leads separately, using the same cohort per lead and origin across arms. At GW1 each A/B/C head fit zero Dev labels and changed 454 nonblank outfield forecasts, including 131 without a source identity. Target and later label mutations left admitted history unchanged at every Dev origin. Independent terminal metadata mutation left each Champion forecast exactly unchanged. [Issue metrics](prototypes/ext_41/evidence/by_issue.csv) · [Leads](prototypes/ext_41/evidence/by_lead.csv) · [Input provenance](prototypes/ext_41/evidence/issue_provenance.csv)

Source coverage reproduced 9,294 of 9,294 rows per head across 33 deadline-bound forecast origins. The retained Champion source digest was reproduced with CRLF line endings. This run binds LF source bytes and freshly generated projection hashes. Arm A reproduced EXT-40's static MSE within `1e-12`, with exact paired row counts, GW1 forecast differences and legal XI results. [Source coverage](prototypes/ext_41/evidence/source_coverage.csv) · [Static parity](prototypes/ext_41/evidence/static_control_parity.csv) · [Run identity](prototypes/ext_41/evidence/run_identity.json)

## Static models

The static heads needed strictly lower lead-0 component MSE than Champion and at least one changed legal XI to earn separate certified paired rolling replays. Goals changed the starting XI in three Gameweeks, with 205 credited points versus 174 for Champion. Assists changed it in two, with 187 credited points. Both qualified.

| Replay arm | GW1 net | GW2 net | GW3 net | GW4 net | Total net | Delta vs Champion | Hit points |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Champion | 58 | 33 | 44 | 85 | 220 | 0 | 8 |
| Static goals | 58 | 57 | 39 | 71 | 225 | +5 | 8 |
| Static assists | 58 | 33 | 44 | 88 | 223 | +3 | 8 |

All 12 solves reported OPTIMAL with zero relative gap under the 600s certified policy. Each arm used the same neutral GW1 ownership anchor and native chip calendar. The Champion net trace reproduced the EXT-40 reference at all four deadlines. Static goals gained 24 points in GW2 and gave back 19 across GW3–4. Static assists gained all three points in GW4. This diagnostic covers four Gameweeks. Season-level qualification requires separate evaluation. [Replay decisions and certificates](prototypes/ext_41/evidence/rolling_decisions.csv)

## Metrics

- **Event Component MSE** is the mean squared difference between fixture component xP and native settled component points. Lower is better, with an ideal value of zero. Arm C needed strictly lower MSE than Champion, A and B. **Signed bias** is the mean forecast minus settled component points, ideally zero.
- **Categorical log loss** is the mean negative log probability of the settled 0/1/2/3+ count. Lower is better, with an ideal value of zero. Exact zero assigned probability produces infinite loss. The clipped diagnostic floors probabilities at the smallest positive normal float.
- **Legal credited XI points** count the points after autosubs in an independent legal £100m squad and starting XI at each deadline, before captain multipliers. Higher is better. The benchmark is the same-week Champion. **Rolling net points** count points credited along a carried ownership trajectory, with applicable captain/chip effects, less official hit penalties. Higher is better. The benchmark is the same-policy Champion from the shared opening anchor.

## Reproduction

Use Python 3.14 and the pinned `uv.lock`. Run from the repository root.

```sh
export PYTHONPATH=.:docs/research/candidate-ideation
work=.tmp/agent/explore-candidate/ext_40
uv run --locked python -m prototypes.ext_40.prepare "$work"
uv run --locked python -m prototypes.ext_40.audit
uv run --locked python -m prototypes.ext_41_preflight "$work"
uv run --locked python -m prototypes.ext_41.run "$work"
uv run --locked python -m prototypes.ext_41.replay "$work" champion
uv run --locked python -m prototypes.ext_41.replay "$work" goals_a
uv run --locked python -m prototypes.ext_41.replay "$work" assists_a
```

Replay arms serially. Forecast runner refuses to overwrite a completed run.

## Verification

Both prototype reviews passed. Focused regression tests and Ruff passed. Recomputed forecast MSE and replay net totals from individual issue records. Independently validated solver certificates, shared replay protocol and opening anchor. Optional Pyright reported pandas typing and test import-resolution diagnostics.

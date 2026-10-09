# Dashboard Responsive Layout

Status: implemented; checks complete except actual browser zoom. Q1–Q9 + shared understanding approved through `/implement`, 2026-10-09. Existing behavior: [integration](dashboard-planner-integration.md), [planner](streamlit-transfer-planner.md). Direction: [DESIGN.md](../../DESIGN.md).

## Agreed Behavior

- Four surfaces: Transfer Planner, Explorer, Research, Model Methodology
- Content width controls reflow; sidebar open/closed, resized windows, browser zoom
- Navigation initially collapsed; page switching reachable; compact outer spacing
- Readable text and ≥44px controls; full labels wrap; vertical scroll preferred over shrinking
- Gameweek, scenario, squad, transfers prominent; secondary/advanced controls expandable
- Position groups and separate bench retained; player columns reduce to one when required
- Player inspection: focused native dialog; Close/Back to squad; no background scroll jump on opening/closing
- Native dialog on wide screens too: consistent keyboard/focus handling, full squad width, no empty details column
- Explorer charts stack when available width insufficient; essential table columns Player, Position, Price, projection first
- Additional table columns retained; table-local horizontal scroll; no page-wide horizontal overflow
- Research prose, methodology explanations/code formulas wrap to content width; rendered KaTeX equations retain local horizontal scroll where mathematical layout cannot wrap
- Resize preserves Gameweek, scenario, player selection, unsaved control values, saved draft, What-If state
- Existing features, Apple utility palette/type, shared services retained; deployment deferred

## Verification

- Existing agreed seams: planner edit/lineup/save APIs, job status/result APIs, Streamlit user flows
- TDD for focused inspection/close/edit flow; existing planner regression coverage retained
- Browser widths: 320, 390, 768, 870, 1024, 1440px; navigation open/closed
- Actual 200% browser zoom; keyboard focus, Escape/close, label wrapping, contained table scroll
- Sidebar overlays content where native small-screen navigation requires; main content usable after closing
- Use cached data for visual checks; test fixtures prevent external HTTP
- Review baseline previously approved `3253282`; responsive change emphasis starting `25ec50d`
- No administrator installs or system settings changes

## Delivery Evidence

- Full suite: 547 passed; pre-existing constant-input correlation warning
- Ruff + Pyright clean; delivery gate 123 passed
- New regressions: focused planner inspection/close/sell; focused Explorer inspection/close preserves What-If + saved draft
- Existing UI regressions: vacancy replacement/reload, captain/vice/bench, scenario confirmation, horizon/chips, retained results, stale browser protection
- Four pages × six widths × two navigation states: 48 browser checks; no page-wide horizontal overflow; complete button/player labels; tables retain local scroll
- Planner keyboard Tab/Enter opens selected Player; native Escape closes inspection/replacement; close retains squad scroll position
- Replacement candidates and Explorer inspection fit 320/390px dialogs; closing preserves draft/What-If state
- Inputs + native comboboxes measured 44px; long Research topic repeated as wrapping full-title caption
- Explorer selected filter tags wrap; container expands without overlapping subsequent controls; six widths/navigation states rechecked
- Explorer squad comparison cached by dataset/model/Gameweeks/squad; unchanged inputs avoid expensive recalculation during inspection
- Actual 200% browser zoom unverified: available in-app browser exposes no native zoom control; keyboard zoom shortcuts leave viewport/device pixel ratio unchanged. Narrow-width reflow verified; no browser/system installation

### Standards Review

One P3 documentation inconsistency: old adjacent-details composition contradicted focused dialog. Corrected. Follow-up: zero remaining findings; no actionable code smells.

### Spec Review

Zero confirmed functional findings or scope creep. Requested verification of control heights and Research math/table overflow completed; local KaTeX scrolling explicitly documented. Actual zoom limitation retained.

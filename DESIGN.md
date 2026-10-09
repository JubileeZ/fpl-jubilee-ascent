# FPL Jubilee Ascent Design

Apple utility/configurator direction, replacing Antigravity styling. Reference: user-supplied `DESIGN-apple.md`; palette, typography, restrained controls adapted to weekly FPL planning. Canonical Streamlit dashboard: Transfer Planner, Explorer, Research, Model Methodology.

## Product and Scope

Single-manager projection + transfer planning workspace. One native Streamlit dashboard, prepared for later private deployment. All four surfaces share navigation, theme, job coordination. Product behavior: [planner spec](docs/product/streamlit-transfer-planner.md).

Dashboard integration agreed 2026-10-09: normal dashboard command opens same complete Streamlit app. Native Explorer selection/replacement/swap controls; persistent transfer draft/results; isolated What-If and advanced results. Scope: [integration spec](docs/product/dashboard-planner-integration.md).

## Character

Calm, readable, direct. Squad and transfer decisions carry emphasis. Apple store utility surfaces guide layout; compact workspace density keeps selected Gameweek, Starting XI, bench, and transfers close together.

`ENERGY 1 / RHYTHM 2 / MOTION 1`

- Energy: quiet chrome; blue reserved for actions and selection.
- Rhythm: spacious section boundaries; compact player and transfer rows.
- Motion: brief pressed-state feedback; respect reduced-motion preference.

## Tokens

- `canvas`: `#ffffff`; pitch, player details, utility surfaces.
- `background`: `#f5f5f7`; page and bench grouping.
- `ink`: `#1d1d1f`; body, headings, numerical values.
- `muted`: `#333333`; supporting text. Reference's faint grey text excluded from small text on off-white surfaces.
- `action`: `#0066cc`; primary actions, links, selected controls.
- `focus`: `#0071e3`; visible keyboard outline with offset.
- `divider`: `#e0e0e0`; decorative section separation.
- `control-border`: `#86868b`; input/control boundaries requiring non-text contrast.
- `on-action`: `#ffffff`; filled blue button labels.
- Spacing: 4 / 8 / 12 / 17 / 24 / 32 / 48px; section gaps 24–32px; player rows 8–12px.
- Radius: utility controls 8px; grouped containers 18px; primary CTA and search capsule 9999px.
- Elevation: flat workspace; use borders and spacing to distinguish surfaces.

## Typography

System font stack: `-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`. Apple platforms use native system typography; Windows/Linux retain native fallback. No bundled font required.

- Page title: 28–34px, weight 600; modest negative letter spacing.
- Section heading: 21px, weight 600.
- Body: 17px, weight 400, line-height 1.47.
- Labels and compact rows: 14px, weight 400 or 600, line-height at least 1.43.
- Values: tabular numerals within system font; aligned units and decimal columns.

## Planner Composition

- Header: product name; data freshness; Refresh action.
- Plan controls: horizon, selected Gameweek, Optimal / No Hit / Conservative selector.
- Primary workspace: selected-week pitch + bench; adjacent player details or replacement search.
- Transfer summary: outgoing/incoming players, provisional or confirmed plan costs, Expected GW Score, recommendation provenance.
- Solver actions: Generate plan, Optimize remaining transfers, Reset to solver; explicit running/error state near action.
- Player click: details. Separate Sell from selected Gameweek, Bench this week, Replace actions.
- Empty replacement slots: bench area, labelled Position + Add player. Vacancies remain visible when Starting XI incomplete.
- Status: readable Draft / Needs recalculation / Solver recommendation labels. Text carries meaning; colour supplements selection only.

## Controls and Responsive Behavior

- Filled blue primary action; neutral secondary controls; explicit labels for destructive draft edits.
- Selected scenario/Player: blue outline plus text/state accessible to assistive technology.
- Real football pitch markings establish Starting Shape; player labels remain readable on white pitch.
- Desktop: pitch and details beside each other within 1440px content limit.
- Narrow screens: controls wrap; details move below pitch; bench remains separate; transfer rows stack.
- Touch targets: minimum 44px; keyboard reachability + visible focus; Escape closes dismissible panels or cancels confirmation. Native Streamlit reruns do not guarantee focus returns to originating Player; Tab resumes navigation.
- Text at 200% zoom reflows; dialogs/search avoid clipped content.
- Loading, empty, stale, incomplete, infeasible, and error states name cause + next action.

## Content and Verification

Display actual player data and projections only. Missing values labelled unavailable; vacant slots have no fabricated Player, Price, or xP. Icons only for meaningful controls; product name supplies wordmark. No new photography, logo, or avatar assets required.

Before UI delivery: verify text contrast ≥4.5:1, large text and control/focus boundaries ≥3:1; exercise keyboard, mobile, 200% zoom, all data states, player actions, and solver result recovery. Design-doc review does not establish implemented UI compliance.

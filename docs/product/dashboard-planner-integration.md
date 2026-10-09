# Dashboard Planner Integration

Status: accepted, 2026-10-09; Q1–Q12 + shared understanding agreed. One native Streamlit product. Implementation in progress. Existing planner behavior: [spec](streamlit-transfer-planner.md). Visual direction: [DESIGN.md](../../DESIGN.md).

## Agreed Scope

- Normal entry point: `uv run python -m commands.dashboard`, default port 8000
- Transfer Planner surface: replace old branching UI with agreed single editable Gameweek plan directly within dashboard
- Apple utility design: navigation, Explorer, Transfer Planner, Research, Model Methodology
- Existing surface functions preserved, including Explorer filters/charts, Squad What-If, Dream Team, research companions, methodology
- Shared Python planner + solver engine; single saved draft and completed results
- Opening view: Transfer Planner on first visit; subsequent visits restore last selected surface
- Old branching plans: retain downloadable backups; no implicit conversion into single editable draft
- Deployment preparation: same complete dashboard via private Docker hosting; Streamlit hosting option documented; deployment deferred
- New work packet: `dashboard-planner-integration`
- Existing deployment deferral retained

## Integration Findings

- `commands.dashboard` serves `dashboard/dist` when present; otherwise raw dashboard source
- Raw HTML mounts `src/main.jsx`; checkout lacks package manifest, dependency lock, installed JavaScript dependencies, and dist output
- Main dashboard still uses legacy planner API; solver response populates hidden legacy plan DOM
- `Planner`, `PlanStore`, `PlannerJobs`, and planner service independent from Streamlit; HTTP adapter can reuse behavior
- Existing dashboard job coordinator excludes its own refresh/Dream Team/solver jobs; new planner registry currently separate
- Branching saves (`user_plans.json`) distinct from new editable draft (`data/planner/draft.json`)
- Existing deployment container launches Streamlit only

## Accepted One-Product Architecture

- Streamlit becomes full dashboard: Transfer Planner, Explorer, Research, Model Methodology
- Normal dashboard command launches same Streamlit app; existing standalone command becomes alias
- Existing Python data/model/solver services reused; no embedded second dashboard server
- Plotly point selections + dataframe row selections preserve Player inspection
- Native click/selection controls for Squad What-If replacements, legal XI swaps, and bench order; replace drag/drop
- Shared job coordinator covers refresh, planner solve, Dream Team, and advanced solves
- Sources: [Streamlit navigation](https://docs.streamlit.io/develop/api-reference/navigation/st.navigation), [Plotly selection](https://docs.streamlit.io/develop/api-reference/charts/st.plotly_chart)

## Persistence and Concurrency

- One persistent draft, three scenario policies; shared across launch commands
- Optimistic saved-draft digest; stale browser write rejected; reload latest draft explicitly
- One application process; shared exclusive queue for Refresh, planner solve, Dream Team, advanced strategy solve
- Browser-independent job records/results; process restart marks unfinished workers interrupted
- Explorer What-If session-only; original User Squad baseline; no saved planner mutation
- Dream Team and advanced results isolated from saved draft; retain downloadable results with source provenance
- Existing branching plans retained verbatim as downloadable backups; no automatic conversion
- Default view Transfer Planner; persist last visited surface

## Acceptance Basis

- Previously agreed player inspection, sell/bench split, vacancy replacement, legal XI, manual overrides, scenario policies, persistent jobs, future ownership/invalidation preserved
- Normal dashboard renders new planner without separate launcher or hidden solver output
- Shared saved plans survive reload and launcher changes; stale input/results visible
- Existing Explorer/Research/Methodology functions retained under new styling
- Working UI states, keyboard, responsive layout, contrast, and solver-result behavior verified before delivery

## Delivery Verification

Pending final gate, browser checks, and two-axis review. Tests cover navigation/reopen, Player edits/recovery, stale-tab writes, shared job exclusion, independent What-If, legal swaps, selling-price accounting. No deployment performed.

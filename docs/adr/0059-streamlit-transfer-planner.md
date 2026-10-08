# Single Editable Transfer Plan in Streamlit

**Status:** Accepted, 2026-10-08. Implementation authorized through `/implement`; supersedes ADR 0058's branching UI for new Streamlit planner. Existing React dashboard retained for Explorer and legacy access.

Replace branching canvas with single editable Gameweek plan. Player click opens details; distinct sell/bench actions update ownership or selected-week lineup. Automatic legal XI + manual overrides, persistent incomplete drafts, visible solver recommendations, and future-week recalculation address user's planning workflow. Retain Optimal / No Hit / Conservative and ADR 0057 solver settings.

Streamlit planner adapts existing Python models/solver; existing Explorer and other dashboard surfaces retained during migration. Apple utility/configurator styling replaces Antigravity design direction in `DESIGN.md`. Prepare private deployment; publish only on later request.

**Considered:** Retain branching React canvas; migrate whole dashboard immediately; run transfer solver after every edit. Chosen scope reduces planning complexity, preserves existing surfaces, and keeps inexpensive lineup recalculation separate from long MILP jobs.

**Consequences:** Persist draft separately from solver recommendation with provenance; maintain job status beyond current short polling window; invalidate dependent future recommendations without dropping explicit user choices. Browser Session State insufficient for saved plans. Hosting capacity + Linux dependency installation require validation. Behavioral acceptance: [product spec](../product/streamlit-transfer-planner.md).

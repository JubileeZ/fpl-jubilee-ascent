# One Native Streamlit Dashboard

**Status:** Accepted, 2026-10-09. User Q1–Q12 + shared understanding agreed. Supersedes ADR 0059's separate-interface migration approach; planner behavior retained.

Normal `commands.dashboard` launches complete Streamlit app on port 8000. Alternate `commands.streamlit_planner` launches same `streamlit_app.py`. Transfer Planner, Explorer, Research, Model Methodology share Apple utility design and one job coordinator. Deployment uses same app; deployment deferred.

**Reason:** Separate planner launcher left normal dashboard unchanged. Missing JavaScript build manifest/dist made raw JSX fallback unusable. User requests one product for local use and later hosting.

**Considered:** Rebuild React dashboard with Python API; embed dashboard in Streamlit; migrate all four surfaces natively. Native migration removes second UI/runtime while preserving Python projection/solver services. Tradeoff: native replacements, legal XI swaps, and bench-order controls replace drag/drop.

**Consequences:** Single persistent draft; compare-and-save prevents stale browser overwrites. Shared exclusive queue covers all heavy jobs within one application process. What-If remains ephemeral; advanced results isolated. Legacy branching saves retained as downloads. Existing HTTP helpers retained for compatibility/tests; no default legacy server. Container hosts complete dashboard with persistent data volume; Linux build + hosting capacity validation deferred.

Acceptance: [integration spec](../product/dashboard-planner-integration.md).

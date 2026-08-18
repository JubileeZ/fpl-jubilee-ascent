# Defensive Composite Score replaces RQI for rotation ranking

Research ranks a Defensive Rotation Set by Defensive Composite Score: $\text{DCS} = 0.60\,S_{\text{Score}} + 0.40\,S_{\text{Risk}}$. $S_{\text{Score}}$ is the min-max of Opportunity-Cost Adjusted Score (weekly rotated xP minus $\gamma$ times spend above the position floor). RQI and OC-RQI are historical labels in archived notes only. ADR 0013 clauses 1–3 (bottom-up rates, dual-vector strength, recency shrinkage) still stand.

**Status:** Accepted. Supersedes ADR 0013 clause 4.

**Considered:** Keep RQI; rank by OC-Score alone; rank by $\max(xP)$ only. Rejected: RQI mixed fixture ease into the points term without an explicit risk factor; OC-Score-only ignores fixture risk; $\max(xP)$ ignores capital drag.

**Consequences:** Live notes, INDEX, and `run_defensive_rotation_analysis.py` publish `dcs` / `oc_score`. Canonical Preseason Chip Path 15-man keepers are a MILP squad pick, not the DCS goalkeeper pair.

# FPL Official Rules Registry

Official Premier League Fantasy scoring rules, definitions, and season-specific adjustments.

## Purpose

Official FPL rules and point allocations may evolve between seasons (such as the 2025/26 Defensive Contributions and BPS scoring threshold adjustments). This directory maintains immutable, season-tagged snapshots of official rules to anchor historical backtests and provide clear audit trails for changes in scoring code.

Code implementation lives in [`models/scoring_matrix.py`](../../models/scoring_matrix.py), with native-season execution scoring contexts in [`models/native_scoring_context.py`](../../models/native_scoring_context.py) and [`backtesting/season_rules.py`](../../backtesting/season_rules.py), and ledger reconciliation in [`backtesting/projection_guards.py`](../../backtesting/projection_guards.py) (ADR 0066).

---

## Season Rules Registry

| Season | Documentation | Primary Additions / Scoring Notes | Status |
|--------|---------------|-----------------------------------|--------|
| **2026/27** | [`scoring-rules-2026-27.md`](scoring-rules-2026-27.md) | Official `native-2026-27-v1`: same scoring matrix + Defensive Contributions as 2025/26, 2 chip sets (`GW1–19`, `GW20–38`), cap 5 FT, no GW15 AFCON topup. Verified 2026-11-15. | Active Quarantined Validation (`S`) |
| **2025/26** | [`scoring-rules-2025-26.md`](scoring-rules-2025-26.md) | Official scoring matrix, 60+ min thresholds, Defensive Contributions (CBIT 10 / CBIRT 12), and BPS system. Captured 2026-07-26. | Dev Season (`S-1`) |
| **2024/25** | Historical pre-defcon rules | `native-2024-25-v1` (GK goal 10, cap 5 FT, chip transfer preservation, no defensive contributions). | Historical Filter (`S-2`) |

---

## Annual Update Protocol

When the Premier League publishes new official game rules for an upcoming season:
1. Verify rule deltas against official Premier League sources ([premierleague.com/news](https://www.premierleague.com/en/news)).
2. Create `docs/rules/scoring-rules-YYYY-YY.md` detailing the scoring matrix and component rules.
3. If point matrices or event component definitions changed, update [`models/scoring_matrix.py`](../../models/scoring_matrix.py) with season conditionality and draft an Architecture Decision Record in [`docs/adr/`](../adr/).
4. Register the new season row in this `README.md`.

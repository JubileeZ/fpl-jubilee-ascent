# Testing Guide & Verification Architecture

Standards, commands, and verification protocols for FPL-Jubilee-Ascent.

## Test Commands Quick Reference

| Level | Command | Scope |
|-------|---------|-------|
| **Lint & Style** | `uv run ruff check .` | Static analysis and code style linting across the entire repository. |
| **Test Suite** | `uv run pytest` | Full automated test suite (unit tests, integration tests, contract compliance). |
| **Delivery Gate** | `bash tests/verify.sh` | Mandatory pre-commit gate: runs linting, structural checks, and core test suites. |
| **Backtest Smoke** | `uv run python .agents/skills/explore-candidate/smoke.py --show_seasons` | Inspects available historical seasons and smoke harness configuration. |

---

## Testing Layers

### 1. Unit & Functional Tests (`tests/`)
- **Location**: `tests/`
- **Scope**: Core mathematical models, scoring matrices, feature transformers, projection contracts, MILP solver wrappers, and Streamlit components.
- **Safety Invariant**: Test commands must **never** make real external HTTP requests to Premier League servers; all network communication must use HTTPX mocks or static fixtures.

### 2. Delivery Gate (`tests/verify.sh`)
- Executed prior to proposing commits or concluding work sessions.
- Checks:
  - Required operational agent docs exist (`current-state.md`, `progress.md`, `issue-tracker.md`, `triage-labels.md`, `domain.md`).
  - Ruff linter exits cleanly with zero errors.
  - Complete test suite passes.

### 3. Historical Backtesting & Archive Testing
- **Specification**: [`archive-testing.md`](archive-testing.md)
- **Mandate**: **MUST** be read before executing historical backtesting or historical data exploration.
- **Key Concepts**:
  - Point-in-time feature isolation: features must never leak post-kickoff information into target gameweek predictions (`model.fit()` uses strictly `< gw` + prior-season seed).
  - Development Season (`S-1` = `2025-26`, seed `2024-25`): Parameter tuning and prototype exploration.
  - Historical Filter (`S-2` = `2024-25`, seed `2023-24`): Un-tuned cross-check before Dual-Tier `Provisional Active`.
  - Active Validation (`S` = `2026-27`, ADR 0069): Quarantined from training/tuning; validates frozen finalists via `Randdalf/fplcache` (`<= 24h`) at `GW15`/`GW30`/`GW38` (`legacy static GW6+ code locks migrating under #185`).

### 4. Promotion & Operator Workflow
- **Specification**: [`operator-workflow.md`](operator-workflow.md) · [ADR 0066](../adr/0066-backtesting-and-promotion-foundation.md) · [ADR 0069](../adr/0069-annual-rolling-validation-and-dual-tier-promotion.md)
- **Lifecycle**: `register -> capture/generate -> verify/admit -> replay -> evaluate -> recommend -> human adopt -> prospective review/rollback`.
- **Primary Estimand**: Rolling 6-GW Strategic transfer plan net score from neutral GW1 ownership anchor.
- **Manual Adoption**: CLI and CI are read-only; Champion adoption requires explicit verified bundle and human approval.

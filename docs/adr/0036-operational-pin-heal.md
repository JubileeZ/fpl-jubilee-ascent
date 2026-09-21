# Official Operational tables heal from Live Season Pin on resolve

Pull updates the Live Season Pin without rewriting gitignored `data/processed`. Projection preferred leftover processed Official tables, so machines disagreed after pin sync. **Decision:** on operational resolve, copy pin Official processed parquets into `data/processed` when bytes differ (pin wins); leave User Squad and other non-Official files untouched. Refresh still writes processed then pins — matching sides make heal a no-op. Covers dashboard open/export/Refresh paths and CLI `run_model` / `solve` via the same resolver.

**Status:** Accepted. Amends ADR 0032 sync consequences (pin remains Official-only; heal is local Operational align, not a git action).

**Considered:** Prefer pin in resolver without copying; refuse until manual sync; heal only on dashboard; mtime-newer gate. Rejected: prefer-without-copy leaves CLI `solve` on stale disk; refuse breaks pull-and-run; dashboard-only leaves CLI drift; mtime is flaky across OSes. Rare Refresh-crash-before-pin loses newest processed until re-Refresh — accepted.

**Consequences:** `heal_operational_official_from_pin` in `features/season_archive.py`; `resolve_operational_processed_dir` always heals first. INFO log when a heal copies. Tests: `tests/test_operational_pin_heal.py`.

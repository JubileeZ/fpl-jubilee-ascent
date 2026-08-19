# Scale saves/defcon by defence_multiplier

**Objective:** Champion `xp_saves` / `xp_defcon` follow fixture defence difficulty; research CSVs and notes match rebuilt outputs.
**Acceptance:** pytest + ruff pass; Canonical S1 `gw1-6_wc4_summary.csv` = 356.61; Dual-Vector WC4 FH12 = 1175.12; GKP DCS GW1–19 Rushworth+Donnarumma 123.20 / 85.78.

## Work Packet (SFDBN)

- **Status:** Complete. Uncommitted tree aligned; ready to push.
- **Files:** `models/metrics_component_hybrid.py`; ADR 0005; research runners/CSVs/notes; `docs/agents/current-state.md`.
- **Decisions:** Production `_fixture_maps` FDR fallback unchanged. Dual-Vector remains research sibling. Missing strength → Official FDR for saves/defcon.
- **Blocked:** None.
- **Next:**
  - [ ] Promote Dual-Vector / overwrite Canonical only on explicit request.
  - [ ] Full `refresh_data` when element summaries exist (Stage 2 rates skipped this rebuild).

# Publish weekly select-11 plans

**Objective:** Write GW starting XIs into research notes + CSV companions from published starter flags / Dual-Vector 15s.
**Acceptance:** Canonical `gw1-6_select_11.csv` GW1=15 / GW2–6=11; week xP matches summary; Dual-Vector WC4 `first_half_select_11.csv` 19 GWs; notes §Select 11; `tests/test_select_11_plan.py` pass.

## Work Packet (SFDBN)

- **Status:** Done on disk. Not committed. Canonical §3 + Dual-Vector Select 11 table live.
- **Files:** `export_select_11.py` (Stage 3 + first-half); `gw1-6_select_11.csv`; `first_half_select_11.csv`; Stage 3 / first-half notes; `tests/test_select_11_plan.py`.
- **Decisions:** Live XI = Canonical GW1–6 FDR-xP. Dual-Vector XI applies FTs at recorded GWs (may ≠ `first_half_weeks.csv` after GW4; max |Δ| 1.92 at GW6).
- **Blocked:** None.
- **Next:**
  - [ ] Commit/push select-11 CSVs, exporters, notes, tests on request.
  - [ ] Promote Dual-Vector / overwrite Canonical only on explicit request.

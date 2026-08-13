# Task Work Packet

## Work Packet (SFDBN)

- **Status:** Complete / Verified
- **Files:** `docs/research/gw1-6-preseason-pipeline/01-expected-role-gw1-5/refresh_expected_role.py`, `docs/research/ownership-value-explorer/plot_ownership_value_explorer.py`, pipeline CSVs + explorer HTML, research notes, `tests/test_expected_role_name_match.py`, `tests/test_ownership_value_explorer.py`
- **Decisions:** Lineup matching uses FPL first/second/web name. Bruno G. = Guimarães at ARS (Rotation). B.Fernandes = United nailed. Virgil matches Van Dijk. Explorer table lists all 357 rows.
- **Blocked:** None.
- **Next:** None.
- **Objective:** Validate ownership explorer missing players (Virgil) and Bruno G vs Bruno F club mix-up; fix matching and dashboard list.
- **Acceptance:**
  - [x] Bruno G. club_short ARS not MUN; B.Fernandes MUN nailed; Virgil LIV nailed
  - [x] Explorer HTML has searchable full player table; Virgil avg xMins ≥ 45
  - [x] Stage 2–3 rebuilt; S1 drafts B.Fernandes not Bruno G.
  - [x] Tests green; ruff clean

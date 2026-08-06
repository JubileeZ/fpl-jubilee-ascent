# FPL 2026/27 Expected Role (GW1–5) — 20-Club Audit & Mins Priors

**Updated**: 2026-08-06T22:49:00+07:00  
**Data stamp**: Scout team-news, Meerkat predicted XIs, FFS summer transfers, and official club evidence audited through 2026-08-06; `players.parquet` 2026-07-29  
**Season**: 2026/27  
**Status**: Active Research Model  
**Purpose**: Assign fit-conditional Expected Role, dated Availability Status, and Participation State priors across all 20 Premier League clubs for GW1–5 projections seeding  
**Scope**: 340-player XI Contention Set across all 20 Clubs; Draft Shortlist = Nailed Starter + Regular Starter; Availability Overlay separately filters `eligible`, `watch`, `exclude_gw1`, and `exclude_gw1-5`.  
**Related**: [Preseason Pipeline Master README](../README.md) · [Expected Stats (Stage 2)](../02-expected-stats-gw1-5/expected-stats-gw1-5.md) · [GW1–6 Chip Matrix (Stage 3)](../03-gw1-6-chip-wc4-squads/gw1-6-chip-wc4-squads.md)  
**Artifacts**:
- [Expected Role CSV (Pipeline)](../../../data/research/gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.csv)
- [Expected Role CSV (Legacy Link)](../../../data/research/expected-role-gw1-5/expected-role-gw1-5.csv)

---

## Sources

- **Primary**: [Fantasy Football Scout Team News](https://www.fantasyfootballscout.co.uk/team-news) — accessed 2026-08-06; predicted XIs & injury flags.
- **Primary**: [FPL GW1 Predicted Line-ups — FPL Meerkat / fpl.page](https://fpl.page/article/fpl-gw1-predicted-lineups-2627) — accessed 2026-08-06; 🟢 Nailed markers & tactical notes.
- **Primary**: [Confirmed Summer Transfers — Fantasy Football Scout](https://www.fantasyfootballscout.co.uk/fpl-2026-27-transfer-news-confirmed-summer-signings) via [fpl-summer-transfers.md](../../fpl-preseason-guide/fpl-summer-transfers.md) — register through 2026-08-05.
- **Primary**: Premier League & Official Club News (Arsenal medical update for Saliba, Liverpool update for Mac Allister & Jacquet, Man City update for Rodri, Spurs press conference confirming Kinsky #1).
- **Repository data**: `data/processed/players.parquet` + `clubs.parquet` — player mapping & local freshness.

---

## Agent Prompt (Parameterized for Reproducible Redo)

```text
Full redo docs/research/gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.md:

Inputs & Horizon:
- Data Sources: FFS Team News, FPL Meerkat (fpl.page), FFS Summer Transfers register, and official Premier League / Club fitness updates.
- Roster: data/processed/players.parquet, data/processed/clubs.parquet.
- Output: data/research/gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.csv and mirrored data/research/expected-role-gw1-5/expected-role-gw1-5.csv.

Procedure:
1. Re-scrape and synthesize starter predictions across all 20 Premier League clubs using Playwright or web search.
2. Resolve conflicts conservatively:
   - Nailed Starter (0.90/0.05/0.05/85/20): Unanimous agreement + full fitness.
   - Regular Starter (0.75/0.10/0.15/80/20): Disagreement between sources or minor pre-season disruption.
   - Rotation Risk (0.40/0.25/0.35/70/20): Rotation/sharing hazard.
   - Cameo (0.10/0.35/0.55/60/15): Backup option.
3. Attach Availability Status separately (eligible, watch, exclude_gw1, exclude_gw1-5). Do not demote fit-role for temporary absence.
4. Execute docs/research/gw1-6-preseason-pipeline/01-expected-role-gw1-5/refresh_expected_role.py to write CSV.
5. Verify pre-commit delivery gates (uv run ruff check ., uv run pytest, bash tests/verify.sh).
```

---

## Method

1. **XI Contention Set Assembly**: Extract XI Contention candidates per club from dual lineup sources and confirmed summer transfers.
2. **Expected Role Assignment**: Apply strict conflict resolution (Nailed vs Regular → Regular; Regular vs Rotation → Rotation).
3. **Availability Overlay**: Overlay current fitness/transfer status (`eligible`, `watch`, `exclude_gw1`, `exclude_gw1-5`) without altering underlying fit-role priors ($p_{\text{start}}$, $p_{\text{sub}}$, $p_{\text{dnp}}$).
4. **Draft Shortlist Filtering**: Export `Nailed Starter` and `Regular Starter` rows with `draft_availability=eligible` for human draft & solver ingestion.

---

## Key Findings across 20 Clubs

1. **Goalkeeper Starters Locked**:
   - **Antonin Kinsky (TOT)**: Confirmed #1 GK by De Zerbi (`Nailed Starter`, `p_start=0.90`).
   - **James Trafford (LEE)**: Completed £40m record transfer to Leeds as starting GK (`Nailed Starter`).
   - **Carl Rushworth (COV)**: Signed £22m from Brighton following Dovin ACL tear (`exclude_gw1-5`).
   - **Konstantinos Tzolakis (HUL)**: Signed £20m from Olympiacos (`Nailed Starter`).

2. **Major Availability Exclusions**:
   - **William Saliba (ARS)**: Back rehabilitation (`exclude_gw1-5`).
   - **Rodri (MCI)**: Back surgery recovery (`exclude_gw1`).
   - **Alexis Mac Allister (LIV)** & **Bukayo Saka (ARS)**: Post-World Cup fitness management (`watch`).
   - **Maxence Lacroix (CHE)** & **Morgan Rogers (CHE)**: Nailed starters for Chelsea following summer moves.

---

## Verification & Delivery

- CSV exported to `data/research/gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.csv` and `data/research/expected-role-gw1-5/expected-role-gw1-5.csv`.
- All 340 XI Contention rows validated.

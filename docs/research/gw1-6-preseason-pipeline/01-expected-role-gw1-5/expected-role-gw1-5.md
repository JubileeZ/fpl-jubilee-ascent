# FPL 2026/27 Expected Role (GW1–5) — 20-Club Audit & Mins Priors

**Updated**: 2026-08-10T06:25:00+07:00  
**Data stamp**: FFS Team News + FPL Meerkat scraped 2026-08-10; official overlays 2026-08-10; `players.parquet` 2026-07-29  
**Season**: 2026/27  
**Status**: Active Research Model  
**Purpose**: Assign fit-conditional Expected Role, dated Draft Availability, and Participation State priors across all 20 clubs for GW1–5 seeding  
**Scope**: XI Contention Set (scaffold + FFS XI injects); Draft Shortlist = Nailed + Regular; Availability Overlay separately applies `eligible`, `watch`, `exclude_gw1`, `exclude_gw1-5`  
**Related**: [Preseason Pipeline Master README](../README.md) · [Expected Stats (Stage 2)](../02-expected-stats-gw1-5/expected-stats-gw1-5.md) · [GW1–6 Chip Matrix (Stage 3)](../03-gw1-6-chip-wc4-squads/gw1-6-chip-wc4-squads.md)  
**Artifacts**:
- [Expected Role CSV](../../../data/research/gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.csv)

---

## Sources

- **Primary**: [Fantasy Football Scout Team News](https://www.fantasyfootballscout.co.uk/team-news) — accessed 2026-08-10; predicted XIs (11 per club).
- **Primary**: [FPL GW1 Predicted Line-ups — FPL Meerkat / fpl.page](https://fpl.page/article/fpl-gw1-predicted-lineups-2627) — accessed 2026-08-10; 🟢 nailed markers.
- **Primary**: [Confirmed Summer Transfers — Fantasy Football Scout](https://www.fantasyfootballscout.co.uk/fpl-2026-27-transfer-news-confirmed-summer-signings) via [fpl-summer-transfers.md](../../fpl-preseason-guide/fpl-summer-transfers.md).
- **Primary**: Official club fitness overlays (Saliba, Rodri, Mac Allister, Saka).
- **Repository data**: `data/processed/players.parquet` + `clubs.parquet`.

---

## Agent Prompt

```text
Full redo docs/research/gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.md:

1. Run refresh_expected_role.py (HTTP scrape FFS + Meerkat; inject missing FFS XI; conflict rules; API + official availability).
2. Conflict rules:
   - Nailed Starter: in FFS XI AND Meerkat 🟢 (0.90/0.05/0.05/85/20)
   - Regular Starter: in exactly one starter signal (0.75/0.10/0.15/80/20)
   - Rotation: previously draft-role but absent from both current signals
3. Availability separate from fit-role. Do not demote fit-role for temporary absence.
4. Verify gates.
```

---

## Method

1. **HTTP scrape**: FFS predicted XI names per club; Meerkat first 🟢 line per club (HTML-unescaped).
2. **Inject**: FFS XI players missing from scaffold matched via `players.parquet` and appended.
3. **Expected Role assignment**: unanimous dual-source → Nailed; single-source → Regular; lost both signals → Rotation.
4. **Availability Overlay**: API chance/status hints, then official overlays. Scoring overlays applied downstream in `availability_priors.py` (Watch haircut; Exclude GW1–5 = GW1–5 only).
5. **Draft Shortlist**: Nailed + Regular with non-`not_role_eligible` availability for human draft / solver ingestion.

---

## Findings

- Contention set: **351** rows after 11 FFS XI injects (was 340). Roles: Nailed 78 · Regular 149 · Rotation 84 · Cameo 40.
- Availability: eligible 214 · not_role_eligible 114 · exclude_gw1 13 · watch 8 · exclude_gw1-5 2.
- **Rushworth (COV)**: injected from FFS XI → Regular Starter, eligible.
- **Kinsky (TOT)**: Regular Starter (FFS XI; Meerkat GK not unanimous).
- **Saliba (ARS)**: `exclude_gw1-5`. **Mac Allister (LIV)** / **Saka (ARS)**: `watch`.
- **Bruno Guimarães (ARS)** / transfer club moves applied before role rebuild.

---

## Decision

**Verdict**: Automated dual-source rebuild is the Stage 1 Method of record. Unanimous Nailed rule is stricter than prior hand labels (fewer Nailed, more Regular).

**Recommended Action**: Re-scrape before material pre-GW1 news; keep official availability overlays dated.

---

## Risks and unknowns

- Meerkat article dated late July; FFS Team News moves faster — dual-source Nailed can lag.
- Name-matching failures leave some FFS names unmatched (no inject).
- Scaffold still seeds Rotation/Cameo membership; inject adds starters only.
- API `chance_of_playing` soft-hints may over-tag `exclude_gw1` / `watch`.

---

## Verification & Delivery

- CSV: `data/research/gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.csv` (351 rows).

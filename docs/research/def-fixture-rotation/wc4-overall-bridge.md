# Constrained WC4 Bridge — Best Overall (any clubs, 1–2 swaps)

**Updated**: 2026-08-14T01:30:00+07:00  
**Data stamp**: Stage 2 ADR-0014 rates 2026-08-14; BB1 club matrix + GW4–19 5-way club matrix (`def_bb1_wc4_club_matrix.csv`, `def_club_5way_rotation_matrix.csv`)  
**Season**: 2026/27  
**Status**: Active  
**Purpose**: Rank the best 4–5 unique GW1–3 defender club sets that reach a strong GW4–19 4–5 unique set after 1 or 2 club-slot replacements. No Sunderland requirement.  
**Scope**: Club-slot Hamming 1–2. Excludes 2–3 unique pre-sets. Does not re-run the full 5-DEF player combinatorics.  
**Related**: [Parent rotation study](def-fixture-rotation.md) · [SUN-constrained WC4 bridge](wc4-sun-bridge.md)

**Sources**: `data/processed/fixtures.parquet`, `data/research/def-fixture-rotation/def_bb1_wc4_club_matrix.csv`, `data/research/def-fixture-rotation/def_club_5way_rotation_matrix.csv`, `data/research/def-fixture-rotation/def_bb1_wc4_tier_lineups.csv`  
**Artifact**: [`def_wc4_overall_bridge_matrix.csv`](../../../data/research/def-fixture-rotation/def_wc4_overall_bridge_matrix.csv)  
**Script**: [`run_def_rotation_analysis.py`](run_def_rotation_analysis.py)

## Agent Prompt

```text
Refresh docs/research/def-fixture-rotation/wc4-overall-bridge.md

1. Re-read parent def-fixture-rotation.md Method and this note.
2. uv run python docs/research/def-fixture-rotation/run_def_rotation_analysis.py --overall-bridge-only
3. Rebuild Top 10, 1-SUN vs 0-SUN vs 2-SUN split, and player maps from def_wc4_overall_bridge_matrix.csv.
4. Do not silently change ranking filters (GW1-3 eff FDR <= 2.3636, GW1 FDR <= 2.4, 100% zero-diff).
5. Update Updated, Data stamp, Findings, Decision.
6. Scratch under .tmp/agent/ only; delete before finish.
```

**Refresh (this report only):**

```bash
uv run python docs/research/def-fixture-rotation/run_def_rotation_analysis.py --overall-bridge-only
```

Both bridges: `--bridges-only`. Full parent pipeline (slow): run the script with no flags, or `uv run python docs/research/gw1-6-preseason-pipeline/refresh_downstream.py` after a Stage 2 rate change.

## Method

**Method type**: empirical analysis on existing club FDR matrices.

**Inputs**: all BB1 clash-free 4–5 unique club sets (5,623 scored); GW4–19 4–5 unique club sets.

**Procedure**: same scorer as the SUN sibling (`run_wc4_bridge_analysis` with `sun_counts=None`). Path FDR = (11 × GW1–3 effective FDR + 48 × GW4–19 rotated FDR) / 59. Published Top 10 uses the same GW1–3 / GW1 / 100% zero-diff filter.

**Difference vs SUN report**: pre-sets are not required to hold Sunderland. MUN doubles and other 2-slot fodder compete on the same path FDR.

## Findings

5,623 pre-sets scored; 261 pass the published filter. Path FDR of the Top 10 is **2.4237**, all 2 swaps, all 100% zero-diff onto `AVL-CHE-LIV-MCI-NFO` or `BOU-CHE-EVE-LIV-NFO`.

**Overall vs SUN-only**

| Pattern | Example | Role |
| --- | --- | --- |
| **MUN double, 0 SUN** | `LIV-MCI-MUN-MUN-NFO` | **Unconstrained #1.** Dump both MUN → AVL + CHE. Tied path FDR with SUN doubles. |
| **SUN double, 2 SUN** | `LIV-MCI-NFO-SUN-SUN` | Tied #1 on path FDR / correlation. See SUN sibling. |
| **5 unique, 1 SUN** | `LIV-MCI-MUN-NFO-SUN` | Best 5-unique in this Top 10 (rank 7). Dump MUN + SUN. |
| **5 unique, 0 SUN** | — | None in the published Top 10. Keeping 5 unique without SUN means the two dump slots are not a same-club double, which loses the GW1–3 FDR/corr tie-break vs MUN/SUN doubles. |

MUN GW1–3 is HUL A FDR2, IPS H FDR2, EVE A FDR3 — the same “easy then dump” shape as SUN, without promoted-side defensive-rate risk.

**1-swap is not in this Top 10** under the GW1 ≤ 2.4 filter. Closest 1-swap onto `AVL-CHE-LIV-MCI-NFO` is `CHE-LIV-MCI-MUN-NFO` → AVL (GW1 FDR 2.6, path FDR 2.4407). Use 2 swaps if GW1 quality is a hard constraint.

### Top 10

| Rank | GW1–3 set | SUN | Unique | GW1–3 eff FDR | GW1 FDR | r | WC4 out → in | GW4–19 destination | Path FDR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **1** | **LIV-MCI-MUN-MUN-NFO** | 0 | 4 | 2.3636 | 2.4 | **-0.3000** | MUN,MUN → AVL,CHE | **AVL-CHE-LIV-MCI-NFO** | **2.4237** |
| **2** | LIV-MCI-NFO-SUN-SUN | 2 | 4 | 2.3636 | 2.4 | -0.3000 | SUN,SUN → AVL,CHE | AVL-CHE-LIV-MCI-NFO | 2.4237 |
| **3** | AVL-LIV-MUN-MUN-NFO | 0 | 4 | 2.3636 | 2.4 | -0.2366 | MUN,MUN → CHE,MCI | AVL-CHE-LIV-MCI-NFO | 2.4237 |
| **4** | AVL-LIV-NFO-SUN-SUN | 2 | 4 | 2.3636 | 2.4 | -0.2366 | SUN,SUN → CHE,MCI | AVL-CHE-LIV-MCI-NFO | 2.4237 |
| **5** | AVL-MCI-MUN-MUN-NFO | 0 | 4 | 2.3636 | 2.4 | -0.2366 | MUN,MUN → CHE,LIV | AVL-CHE-LIV-MCI-NFO | 2.4237 |
| **6** | AVL-MCI-NFO-SUN-SUN | 2 | 4 | 2.3636 | 2.4 | -0.2366 | SUN,SUN → CHE,LIV | AVL-CHE-LIV-MCI-NFO | 2.4237 |
| **7** | **LIV-MCI-MUN-NFO-SUN** | **1** | **5** | 2.3636 | 2.4 | -0.2000 | MUN,SUN → AVL,CHE | **AVL-CHE-LIV-MCI-NFO** | **2.4237** |
| **8** | CHE-LIV-MUN-MUN-NFO | 0 | 4 | 2.3636 | 2.4 | -0.1382 | MUN,MUN → BOU,EVE | BOU-CHE-EVE-LIV-NFO | 2.4237 |
| **9** | CHE-LIV-NFO-SUN-SUN | 2 | 4 | 2.3636 | 2.4 | -0.1382 | SUN,SUN → BOU,EVE | BOU-CHE-EVE-LIV-NFO | 2.4237 |
| **10** | CHE-MCI-MUN-MUN-NFO | 0 | 4 | 2.3636 | 2.4 | -0.1382 | MUN,MUN → AVL,LIV | AVL-CHE-LIV-MCI-NFO | 2.4237 |

Ranks 1 / 3 / 5 / 10 are the no-Sunderland paths. Rank 7 is the best 5-unique (needs 1 SUN). Ranks 8–9 go to the Bournemouth–Everton variant of the 2.4375 FDR tier.

### Representative player maps

| Role | Club set | Spend | Lineup | Notes |
| --- | --- | --- | --- | --- |
| **GW1–3 pick (no SUN)** | LIV-MCI-MUN-MUN-NFO | £24.5m | Jacquet (LIV £5.0m) + Gvardiol (MCI £5.5m) + Shaw (MUN £4.5m) + Maguire (MUN £5.0m) + Jair Cunha (NFO £4.5m) | BB-RQI 72.71; 61.05 xP / 11 starts |
| **WC4 (no SUN path)** | AVL-CHE-LIV-MCI-NFO | £24.5m | Maatsen (AVL £4.5m) + Colwill (CHE £5.0m) + Jacquet + Gvardiol + Jair Cunha | Shaw + Maguire → Maatsen + Colwill |
| **GW1–3 pick (5 unique)** | LIV-MCI-MUN-NFO-SUN | £24.5m | Jacquet + Gvardiol + Shaw + Jair Cunha + Ballard (SUN £5.0m) | BB-RQI 71.08; 59.10 xP / 11 starts |
| **WC4 (5 unique path)** | AVL-CHE-LIV-MCI-NFO | £24.5m | Maatsen + Colwill + Jacquet + Gvardiol + Jair Cunha | Shaw + Ballard → Maatsen + Colwill |

## Decision

**Verdict**: Unconstrained pick is `LIV-MCI-MUN-MUN-NFO` — dump both United defenders at WC4 for Villa + Chelsea. Sunderland is not required for the best path FDR.

**Recommended action**: Use this note when club choice is open. Use [wc4-sun-bridge.md](wc4-sun-bridge.md) when 1–2 SUN is a hard constraint. Prefer rank 7 (`LIV-MCI-MUN-NFO-SUN`) if 5 unique clubs in GW1–3 matters more than a MUN double.

**Trigger / kill switch**: United or Forest XI breaks GW1–3; or GW4–19 refresh moves `AVL-CHE-LIV-MCI-NFO` off 2.4375 / 100% zero-diff.

## Risks and unknowns

- MUN double shares GW1–2 wipeout risk (both face HUL then IPS). 5 unique (rank 7) insulates that at equal path FDR, worse pairwise correlation.
- Shaw / Maguire minutes and United defensive rates are prior-season; same hybrid scorer as the parent study.
- 1-swap elite cores exist at GW1 FDR 2.6; excluded here by the GW1 ≤ 2.4 filter.

# Constrained WC4 Bridge — 1–2 Sunderland (GW1–3 → 1–2 swaps → GW4–19)

**Updated**: 2026-08-14T02:30:00+07:00  
**Data stamp**: Stage 2 ADR-0014 rates 2026-08-14; dest picker correlation-first among 2.4375 / 100% zero-diff  
**Season**: 2026/27  
**Status**: Active  
**Purpose**: Rank 4–5 unique GW1–3 defender club sets that already hold 1–2 Sunderland and reach a strong GW4–19 4–5 unique set after 1 or 2 club-slot replacements.  
**Scope**: Club-slot Hamming 1–2. Excludes 2–3 unique pre-sets. Does not re-run the full 5-DEF player combinatorics.  
**Related**: [Parent rotation study](def-fixture-rotation.md) · [Overall WC4 bridge (no SUN filter)](wc4-overall-bridge.md)

**Sources**: `data/processed/fixtures.parquet`, `data/research/def-fixture-rotation/def_bb1_wc4_club_matrix.csv`, `data/research/def-fixture-rotation/def_club_5way_rotation_matrix.csv`, `data/research/def-fixture-rotation/def_bb1_wc4_tier_lineups.csv`  
**Artifact**: [`def_wc4_sun_bridge_matrix.csv`](../../../data/research/def-fixture-rotation/def_wc4_sun_bridge_matrix.csv)  
**Script**: [`run_def_rotation_analysis.py`](run_def_rotation_analysis.py)

## Agent Prompt

```text
Refresh docs/research/def-fixture-rotation/wc4-sun-bridge.md

1. Re-read parent def-fixture-rotation.md Method and this note.
2. uv run python docs/research/def-fixture-rotation/run_def_rotation_analysis.py --sun-bridge-only
3. Rebuild Top 10, SUN verdict, and player maps from def_wc4_sun_bridge_matrix.csv.
4. Do not silently change ranking filters (GW1-3 eff FDR <= 2.3636, GW1 FDR <= 2.4, 100% zero-diff). Dest tie-break is correlation-first (more negative wins).
5. Update Updated, Data stamp, Findings, Decision.
6. Scratch under .tmp/agent/ only; delete before finish.
```

**Refresh (this report only):**

```bash
uv run python docs/research/def-fixture-rotation/run_def_rotation_analysis.py --sun-bridge-only
```

Both bridges: `--bridges-only`. Full parent pipeline (slow): run the script with no flags, or `uv run python docs/research/gw1-6-preseason-pipeline/refresh_downstream.py` after a Stage 2 rate change.

## Method

**Method type**: empirical analysis on existing club FDR matrices.

**Inputs**: BB1 clash-free 4–5 unique club sets with SUN count in {1, 2}; GW4–19 4–5 unique club sets.

**Procedure**:
1. Distance = 5 minus multiset overlap of the five club slots. Keep 1 or 2.
2. One destination per pre-set: 100% zero-diff first, then path FDR, then dest rot FDR, then dest correlation-first (more negative wins), then easy%, GW1 FDR, fewer swaps.
3. Path FDR = (11 × GW1–3 effective FDR + 48 × GW4–19 rotated FDR) / 59.
4. Published Top 10: GW1–3 effective FDR ≤ 2.3636, GW1 avg FDR ≤ 2.4, destination 100% zero-diff. Rank by path FDR, GW1 FDR, n_swaps, GW1–3 correlation.

**Definitions**: slot swap = one defender's club changes at WC4. Not a free-transfer count in the solver.

## Findings

Independent GW1–3 and GW4–19 top-10s are **not** 1–2 swaps apart. `ARS-MUN-MUN-NFO-SUN` (BB1 rank 1) is **4 slot changes** from `AVL-BOU-CHE-LIV-NFO` (GW4–19 rank 1) and from `AVL-CHE-LIV-MCI-NFO` (rank 3). 1,469 SUN-holding pre-sets scored.

**Sunderland verdict**

| Question | Verdict | Evidence |
| --- | --- | --- |
| 1 SUN in GW1–3? | **Endorse** | Best 4–5 unique BB1 FDR without SUN is 2.3636; with SUN is 2.2727. SUN GW1–3: IPS A FDR2, FUL H FDR2, BRE A FDR3. |
| 2 SUN in GW1–3? | **Endorse only as WC4 fodder** | 2-SUN 4-club sets match 1-SUN path FDR when both dump into a 2.4375 dest. Cost: double-up wipeout on GW1–2 (both face IPS then FUL). |
| Keep 1 SUN after WC4? | **Optional, strictly worse** | Best GW4–19 5-club with SUN is 2.4792 / 100% zero-diff (`BHA-COV-LIV-MCI-SUN`) vs 2.4375 without. Path FDR 2.4407 vs 2.4237. |
| Keep 2 SUN after WC4? | **Reject** | Best GW4–19 with 2 SUN is 2.5208. SUN GW4–19 mean FDR 3.19 (6 of 16 GWs ≥ 4, including GW4 ARS H4 and GW5 MCI A5). |
| Classic `ARS-MUN-NFO-SUN` BB1 core? | **Reject for this constraint** | Hamming 3–4 to both 2.4375 dests. Best 2-swap lands on 2.4792, not 2.4375. |

**Recommended pick:** `LIV-MCI-MUN-NFO-SUN` (rank 4, 1 SUN, 5 unique). Same path FDR as the 2-SUN leaders, better single-match wipeout insulation. Dump MUN + SUN → AVL + CHE onto `AVL-CHE-LIV-MCI-NFO` (only 2-swap 2.4375 dest from that pre-set).

If 2 SUN is the lean: `LIV-MCI-NFO-SUN-SUN` (rank 1) also dumps onto `AVL-CHE-LIV-MCI-NFO`. Pre-sets that already hold AVL+LIV+NFO dump onto corr-first dest `AVL-BOU-CHE-LIV-NFO`.

### Top 10

| Rank | GW1–3 set (SUN count) | Unique | GW1–3 eff FDR | GW1 FDR | r | WC4 out → in | GW4–19 destination | GW4–19 rot FDR | Path FDR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **1** | **LIV-MCI-NFO-SUN-SUN (2)** | 4 | 2.3636 | 2.4 | **-0.3000** | SUN,SUN → AVL,CHE | **AVL-CHE-LIV-MCI-NFO** | **2.4375** | **2.4237** |
| **2** | AVL-LIV-NFO-SUN-SUN (2) | 4 | 2.3636 | 2.4 | -0.2366 | SUN,SUN → BOU,CHE | **AVL-BOU-CHE-LIV-NFO** | **2.4375** | 2.4237 |
| **3** | AVL-MCI-NFO-SUN-SUN (2) | 4 | 2.3636 | 2.4 | -0.2366 | SUN,SUN → CHE,LIV | AVL-CHE-LIV-MCI-NFO | 2.4375 | 2.4237 |
| **4** | **LIV-MCI-MUN-NFO-SUN (1)** | **5** | 2.3636 | 2.4 | -0.2000 | MUN,SUN → AVL,CHE | **AVL-CHE-LIV-MCI-NFO** | **2.4375** | **2.4237** |
| **5** | CHE-LIV-NFO-SUN-SUN (2) | 4 | 2.3636 | 2.4 | -0.1382 | SUN,SUN → AVL,BOU | AVL-BOU-CHE-LIV-NFO | 2.4375 | 2.4237 |
| **6** | CHE-MCI-NFO-SUN-SUN (2) | 4 | 2.3636 | 2.4 | -0.1382 | SUN,SUN → AVL,LIV | AVL-CHE-LIV-MCI-NFO | 2.4375 | 2.4237 |
| **7** | AVL-LIV-MUN-NFO-SUN (1) | 5 | 2.3636 | 2.4 | -0.1366 | MUN,SUN → BOU,CHE | AVL-BOU-CHE-LIV-NFO | 2.4375 | 2.4237 |
| **8** | AVL-MCI-MUN-NFO-SUN (1) | 5 | 2.3636 | 2.4 | -0.1366 | MUN,SUN → CHE,LIV | AVL-CHE-LIV-MCI-NFO | 2.4375 | 2.4237 |
| **9** | AVL-CHE-NFO-SUN-SUN (2) | 4 | 2.3636 | 2.4 | -0.0652 | SUN,SUN → BOU,LIV | AVL-BOU-CHE-LIV-NFO | 2.4375 | 2.4237 |
| **10** | CHE-LIV-MUN-NFO-SUN (1) | 5 | 2.3636 | 2.4 | -0.0382 | MUN,SUN → AVL,BOU | AVL-BOU-CHE-LIV-NFO | 2.4375 | 2.4237 |

Ranks 2 / 5 / 7 / 9 / 10 land on corr-first dest `AVL-BOU-CHE-LIV-NFO`. Ranks 1 / 3 / 4 / 6 / 8 keep City (`AVL-CHE-LIV-MCI-NFO`) because that is the only 2-swap 2.4375 dest from those pre-sets.

**1-swap is not in this Top 10.** Best 1-swap onto `AVL-CHE-LIV-MCI-NFO` is `AVL-CHE-LIV-MCI-SUN` → NFO, but GW1 avg FDR is 2.8.

### Representative player maps

| Role | Club set | Spend | Lineup | Notes |
| --- | --- | --- | --- | --- |
| **GW1–3 pick (1 SUN)** | LIV-MCI-MUN-NFO-SUN | £24.5m | Jacquet (LIV £5.0m) + Gvardiol (MCI £5.5m) + Shaw (MUN £4.5m) + Jair Cunha (NFO £4.5m) + Ballard (SUN £5.0m) | BB-RQI 71.08; 59.10 xP / 11 starts |
| **WC4 (keep City)** | AVL-CHE-LIV-MCI-NFO | £24.5m | Maatsen (AVL £4.5m) + Colwill (CHE £5.0m) + Jacquet + Gvardiol + Jair Cunha | Shaw + Ballard → Maatsen + Colwill |
| **GW1–3 pick (2 SUN)** | LIV-MCI-NFO-SUN-SUN | £24.5m | Jacquet + Gvardiol + Jair Cunha + Meunier (SUN £4.5m) + Ballard (SUN £5.0m) | BB-RQI 72.71; 60.29 xP / 11 starts |
| **WC4 (corr-first dest)** | AVL-BOU-CHE-LIV-NFO | £25.5m | Pau (AVL £4.5m) + Hill (BOU £5.5m) + Lacroix (CHE £6.0m) + Jacquet + Jair Cunha | From AVL-LIV-NFO-SUN-SUN dump both SUN → BOU+CHE |

## Decision

**Verdict**: Endorse 1 SUN for GW1–3; dump SUN at WC4. Pick `LIV-MCI-MUN-NFO-SUN` → AVL + CHE onto `AVL-CHE-LIV-MCI-NFO`. Standalone GW4–19 #1 is `AVL-BOU-CHE-LIV-NFO` (best corr); take it when the pre-set already holds AVL+LIV+NFO.

**Recommended action**: Open this note for SUN-constrained WC4 planning. Use the overall sibling if Sunderland is not required.

**Trigger / kill switch**: SUN starting XI breaks, or GW4–19 FDR matrix refresh moves the 2.4375 / 100% zero-diff tier.

## Risks and unknowns

- Club-slot model, not player minutes haircuts. O'Nien is Regular with thin usable mins.
- Path FDR ignores attack-quota / premium MID-FWD crowding beyond the existing max-2 top-attack DEF rule.
- Unconstrained ranking (MUN double instead of SUN) lives in [wc4-overall-bridge.md](wc4-overall-bridge.md).

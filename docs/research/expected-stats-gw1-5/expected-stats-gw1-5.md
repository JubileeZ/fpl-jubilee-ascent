# Expected Stats & GW1–5 Points Projection Research Note

**Updated**: 2026-08-02T00:55:00+07:00  
**Data stamp**: Expected Role Table 2026-08-01; 2025/26 archive 2026-07-29; FPL API elements summary 2026-07-29; grill lock 2026-08-02; best-guess Defcon 2026-08-02  
**Season**: 2026/27  
**Status**: Active Research Model (Non-Full-Season Candidate)  
**Purpose**: Build Event Rates for XI Contention Set via Permanent Player Code Mapping + usable-season recency blend; project GW1–5 $xP$ through `ParticipationStateHybridModel.predict`.  
**Scope**: XI Contention rates (Nailed / Regular / Rotation / Cameo); Draft Shortlist projections export (Nailed + Regular).  
**Related**: [Expected Role GW1–5](../expected-role-gw1-5/expected-role-gw1-5.md) · [Repo Structure Guide](README.md) · ADR 0004 · ADR 0005  
**Artifacts**:
- [Expected Stats CSV](../../../data/research/expected-stats-gw1-5/expected-stats-gw1-5.csv)
- [GW1–5 Projections CSV](../../../data/research/expected-stats-gw1-5/gw1-5_projections.csv)

---

## Sources

- Expected Role Table + priors: `data/research/expected-role-gw1-5/expected-role-gw1-5.csv`
- Prior-season archive (code-mapped): `data/archive/2025-26/processed/`
- `history_past` season totals: `data/raw/element_summary_{id}.json`
- External research packages when no Usable Season remains (xG/xA/saves; Defcon from CBIT/CBITR, FPL Defcon, or best-guess when any data exists)
- Fixtures / club strengths: `data/processed/fixtures.parquet`, `clubs.parquet`

---

## Agent Prompt

```text
Rebuild expected-stats-gw1-5 per grill lock:

1. XI Contention Set rates via build_expected_stats.py (code map, usable seasons >=450 mins,
   recency 50/50, external only if no usable FPL year; Defcon CBIT/best-guess or baseline).
2. Project via project_expected_points.py → ParticipationStateHybridModel.predict
   with attack/defence multipliers from club strengths; Softmax bonus over full XI Contention;
   export Draft Shortlist (Nailed+Regular) projections CSV.
3. Update this note Findings; flag any remaining fallback_baseline or stale downstream consumers.
4. ruff check docs/research/expected-stats-gw1-5/
```

---

## Method

### 1. Event Rates (grill lock)
- **Identity**: Permanent Player Code Mapping to archive `id` (ADR 0004).
- **Window**: 2023/24, 2024/25, 2025/26. Prefer archive match logs for 2025/26; else `history_past`.
- **Usable Season**: minutes ≥ 450. Thin/missing years dropped.
- **Blend**: 50% latest Usable Season + 50% mean of older Usable Seasons (no double-count). Single usable → 100%.
- **Gap fill**: external research package only if zero Usable Seasons; else position baseline.
- **Defcon**: FPL `defensive_contribution` or CBIT/CBITR when complete. Else best-guess from partial scout/FBref/Opta (`defcon_cbit=True`). Position baseline only when no Defcon evidence.

### 2. $xP$ reconstruction
- Feature-like rows GW1–5 with Expected Role Priors + availability excludes.
- `attack_multiplier` / `defence_multiplier` from club strength vectors (`features.builder._fixture_maps`); FDR fallback only if strengths missing.
- Score via `ParticipationStateHybridModel.predict` (NegBin Defcon threshold, Softmax bonus).
- Bonus competitors = full XI Contention Set; CSV export = Nailed + Regular only.

---

## Findings

### 1. Top Draft Shortlist (GW1–5 aggregate $xP$, post best-guess Defcon)

| Rank | Player | Club | Pos | GW1 | GW2 | GW3 | GW4 | GW5 | Total |
|------|--------|------|-----|-----|-----|-----|-----|-----|-------|
| 1 | Haaland | MCI | FWD | 5.54 | 5.44 | 6.91 | 4.15 | 6.86 | **28.90** |
| 2 | Palmer | CHE | MID | 4.86 | 5.97 | 3.01 | 6.04 | 4.78 | **24.66** |
| 3 | Vuskovic | BHA | DEF | 4.71 | 3.68 | 5.81 | 5.73 | 3.74 | **23.67** |
| 4 | B.Fernandes | MUN | MID | 5.52 | 5.48 | 4.46 | 3.59 | 4.52 | **23.57** |
| 5 | O'Reilly | MCI | DEF | 4.31 | 4.28 | 4.99 | 3.63 | 4.98 | **22.19** |
| 6 | Gabriel | ARS | DEF | 5.30 | 3.88 | 3.89 | 4.52 | 4.54 | **22.14** |
| 7 | Sarr | CRY | MID | 4.38 | 3.47 | 4.44 | 5.41 | 4.36 | **22.06** |

Haaland stays #1 (~0.83 xG/90). Vuskovic jumps to #4 after best-guess CBIT Defcon 12.45. Isak still diluted by 2025/26 at 694 mins (≥450 floor).

### 2. Rate source mix (340 XI Contention rows)
- `fpl_recency_50_50`: 199 · `fpl_single_usable_season`: 81 · `external_3season_research`: 22 · `fallback_baseline`: 38 (Rotation/Cameo only)

### 3. Draft Shortlist research (2026-08-02)
- **Zero** Nailed/Regular on `fallback_baseline` after packages for Thomas, Wright, Butland, Slater, Ömür, Matusiwa, Emersonn + CBIT/CBITR upgrades.
- **Best-guess Defcon** enabled for remaining 7 with any Defcon evidence (`defcon_cbit=True`): Vuskovic 12.45, Amenda 8.03, Wright 5.28, Ömür 8.32, Matusiwa 13.57, Maeda 7.69, Emersonn 2.78.
- **Zero** Draft externals still on pure position-baseline Defcon.
- Remaining 38 baseline rows are Rotation/Cameo (bonus pool only).

---

## Decision

**Verdict**: Approved rebuild per grill lock. Best-guess Defcon for partial sources. Chip sim re-run 2026-08-02: BB1 299.78 / BB2 297.77 / Standard 283.84.

**Recommended Action**:
- Optional: Rotation/Cameo baseline packages if Softmax bonus rivals matter.
- Tighten Defcon sources when full CBIT/CBITR tables land (Vuskovic HSV, Emersonn Toulouse).
- Consider raising Usable Season floor above 450 if injury seasons like Isak 2025/26 should drop from “latest”.

---

## Risks and Unknowns

- Usable Season floor 450 still admits some thin injury years into the “latest” 50% slot.
- Best-guess Defcon from incomplete CBIT/scout samples may over/understate threshold hit rate.
- Softmax over XI Contention dilutes bonus vs shortlist-only (expected).
- Research path still not live Expected Role → Participation State wiring (Q1→C later).

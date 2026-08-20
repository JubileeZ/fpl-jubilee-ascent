# Operational First-Half Plan (GW1–19)

**Updated**: 2026-08-20T17:17:28+07:00
**Data stamp**: Stage 2 rates 2026-08-18; First-Half WC4 15s 2026-08-19; frozen XI scored 2026-08-20; GW1 deadline 2026-08-21T17:30:00Z
**Season**: 2026/27 · First-Half Horizon GW1–19
**Status**: Active user playbook. Consumes Canonical + First-Half calendars. Does not replace either.
**Purpose**: Locked GW1–19 playbook: same pre-WC 15 as both WC4 calendars; First-Half Wildcard 15; Set 1 chips BB1+WC4+FH12+TC17; bank-state Free Transfer hurdles; frozen XI (no greedy FT CSV).
**Scope**: Greenfield Draft 15. Owned 15s freeze through WC4 except DNP. FH12 15 rebuild at deadline. Transfer Plan / DCS do not replace owned keepers before GW4.
**Related**: [First-Half Chip Path](../gw1-19-first-half-chip-path/gw1-19-first-half-chip-path.md) · [Canonical Stage 3](../gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6-chip-wc4-squads.md) · [DCS](../defensive-fixture-rotation/defensive-fixture-rotation.md) · [CONTEXT.md](../../../CONTEXT.md) · [Exporter](export_operational_plan.py)
**Artifacts**:
- [Summary](../../../data/research/gw1-19-operational-plan/operational_summary.csv)
- [Weeks](../../../data/research/gw1-19-operational-plan/operational_weeks.csv)
- [Select 11](../../../data/research/gw1-19-operational-plan/operational_select_11.csv)
- [Squads](../../../data/research/gw1-19-operational-plan/operational_squads.csv)
- [FT hurdles](../../../data/research/gw1-19-operational-plan/operational_ft_hurdles.csv)

---

## Sources

- **Repository**: First-Half `first_half_squads.csv` `wc=4` pre-WC / WC rebuild / FH; `gw1-19_projections.csv`; Canonical `gw1-6_wc4_summary.csv` `total_6gw_xp` — cutoff 2026-08-19
- **Rules (as recorded)**: Set 1 expires GW19; max 5 banked FTs; WC/FH preserve bank — [first-half chip strategy note](../fpl-first-half-chip-strategy/fpl-first-half-chip-strategy.md)

**Source boundary**: Dual-Vector Cold-Start xP. FH snapshot is August rental, not the deadline 15. Solver `ft_value` 1.5 is a holding premium; this plan uses bank-state hurdles instead.

## Agent Prompt

```text
Refresh docs/research/gw1-19-operational-plan/gw1-19-operational-plan.md

1. Re-read CONTEXT.md Operational First-Half Plan, Canonical Preseason Chip Path, First-Half Chip Path.
2. uv run python docs/research/gw1-19-operational-plan/export_operational_plan.py
3. Do not run first_half greedy FTs. Do not replace Canonical Stage 3 or first_half_transfers.csv.
4. Identity: data/research/gw1-19-operational-plan/operational_summary.csv frozen_19gw_xi_xp
5. Update Updated, Data stamp, Findings, Decision, week table from operational_weeks.csv.
6. Scratch only under .tmp/agent/; delete before finish.
```

## Method

**Method type**: decision capture + frozen-15 Dual-Vector XI (no greedy FTs)

**Inputs**:
- `first_half_squads.csv` WC4 pre-WC and WC rebuild
- `gw1-19_projections.csv` + `run_chip_path.score_week`
- Bank-state hurdle table (locked)

**Procedure**:
1. Copy WC4 pre-WC 15 as GW1 draft (matches Canonical pre-WC IDs).
2. Lock transfers GW2–3 except flagged DNP. Bench Boost GW1. Wildcard GW4 to First-Half rebuild 15 (Isak stays).
3. Score each GW max-xP legal XI on the **owned** 15. GW12 uses August FH snapshot only as a placeholder; rebuild that 15 at the GW12 deadline.
4. Post-WC Free Transfers: remaining First-Half total (this GW through 19, undiscounted, skip FH week on owned 15s). Spend only if gain > hurdle for FTs at that deadline. Hits if gain > 4 or DNP.
5. Do not apply `first_half_transfers.csv`.

**Definitions and assumptions**:
- GW1 = 0 FTs (draft). After GW1 deadline = 1 FT for GW2. +1 per week, cap 5. WC does not spend the bank.
- Bank 5: first FT use-or-lose. Bank 4 is not cap.
- Gain = remaining GW→19 Dual-Vector week scores, not this week only, not GW20–38, not Planning Horizon 6.

### Metric Definitions & Direction

| Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|---|---|---|---|---|---|
| Frozen XI First-Half xP | `frozen_19gw_xi_xp` | Sum of `operational_weeks.csv` `week_xp` (XI + captain extra; TC = +2× cap) | Higher $\uparrow$ | Identity column; not `total_19gw_xp` | Owned 15s frozen; August FH snapshot at GW12 |
| First-Half Chip Path Total xP | `total_19gw_xp` | First-Half ranking incl. greedy FTs | Higher $\uparrow$ | `first_half_summary.csv` | Sibling calendar. Not this playbook |
| Canonical 6GW xP | `total_6gw_xp` | Stage 3 BB1+WC4 locked path | Higher $\uparrow$ | `gw1-6_wc4_summary.csv` | GW1–6 only; no FH/TC |
| FT hurdle | `hurdle_xp` | Remaining-horizon gain needed to spend | Context | `operational_ft_hurdles.csv` | Falls toward 0 at cap (first FT) |

**Validation boundary**: Cold-Start Dual-Vector. No live results. GW12 XI in the CSV is a snapshot.

## Source synthesis

### Main claims

- Canonical and First-Half WC4 share the same pre-WC 15.
- First-Half WC4 winner calendar: BB1, WC4, FH12, TC17. Greedy FTs after WC, threshold 0.05, no FT-bank term.
- Production Transfer Plan `ft_value` 1.5 prices **holding** an extra FT. Cap-5 incoming FT is wasted if unspent.

### Source rationale

- Greedy log max `approx_gain` 0.656 < 1.5 → flat solver FT value would skip all nine moves.
- Use-or-lose at 5 reverses that for the **first** FT at cap.

## Project interpretation

### Decision rules

- If choosing one playbook now: Operational First-Half Plan OP1.
- If a starter is flagged DNP: transfer even when below hurdle.
- If confirmed DGW/BGW or Haaland out GW17: re-run First-Half calendar; do not keep FH12/TC17 blindly.
- If Transfer Plan disagrees before GW4: ignore. After GW4 it may **measure** a swap; take it only if remaining GW→19 gain beats the hurdle.

### Practical implications

- Copy pre-WC 15 at GW1. Do not spend the post-GW1 FT before Wildcard unless DNP.
- Wildcard to First-Half 15, not Canonical João Pedro rebuild.
- Rebuild FH12 15 near that deadline. August FH snapshot is not owned.

## Findings

### Evidence

- **OP1 chips**: BB1, WC4, FH12, TC17. `operational_summary.csv`.
- **Frozen XI total**: **1182.14** (`frozen_19gw_xi_xp`). Not a reprint of First-Half **1175.12** (`total_19gw_xp`).
- **Pre-WC 15** (£100.0m): Donnarumma, Verbruggen; Gabriel, Guéhi, Calafiori, Vuskovic, Wieffer; Tzolis, Tavernier, Schade, Scott, Maeda; Haaland, Isak, Calvert-Lewin. Same IDs as Canonical pre-WC and First-Half WC4 pre-WC.
- **WC rebuild 15** (£100.0m): Donnarumma, Tzolakis; same five DEFs; Tzolis, Palmer, Sarr, Crooks, Slater; Haaland, Isak, Walle Egeli. Isak stays. Canonical post-WC (João Pedro, Horníček, Palacios) out.
- **FT bank**: GW1 draft 0 → roll GW2–3 → WC preserves 3 → GW5 has 4 (hurdle 1.0) → GW6 hits cap 5 (first FT hurdle 0.2). Canonical CSV `banked_fts_gw6` = 4; this plan treats GW6 as cap 5 after a GW5 roll.
- **GW15 captain**: Tzolis (`operational_weeks.csv`). Not Haaland.

#### Week xP (frozen 15s)

Companion: `operational_weeks.csv`. GW12 = August FH snapshot.

| GW | Chip | Form | C | week_xp | Owned 15 |
|---|---|---|---|---|---|
| 1 | BB | BB-15 | Haaland | 79.24 | pre-WC |
| 2 |  | 5-3-2 | Haaland | 61.76 | pre-WC |
| 3 |  | 5-3-2 | Haaland | 60.65 | pre-WC |
| 4 | WC | 5-3-2 | Haaland | 60.76 | WC rebuild |
| 5 |  | 5-3-2 | Haaland | 59.24 | WC rebuild |
| 6 |  | 5-3-2 | Haaland | 61.94 | WC rebuild |
| 7 |  | 5-3-2 | Haaland | 60.64 | WC rebuild |
| 8 |  | 5-3-2 | Haaland | 61.61 | WC rebuild |
| 9 |  | 5-3-2 | Haaland | 56.62 | WC rebuild |
| 10 |  | 5-3-2 | Haaland | 62.24 | WC rebuild |
| 11 |  | 5-3-2 | Haaland | 61.80 | WC rebuild |
| 12 | FH | 4-4-2 | Isak | 58.49 | snapshot only |
| 13 |  | 5-3-2 | Haaland | 61.03 | WC rebuild |
| 14 |  | 5-3-2 | Haaland | 62.80 | WC rebuild |
| 15 |  | 5-3-2 | Tzolis | 59.61 | WC rebuild |
| 16 |  | 5-3-2 | Haaland | 59.27 | WC rebuild |
| 17 | TC | 5-3-2 | Haaland | 70.88 | WC rebuild |
| 18 |  | 5-3-2 | Haaland | 64.87 | WC rebuild |
| 19 |  | 5-3-2 | Haaland | 58.69 | WC rebuild |

Post-WC owned XI shape (except GW12): Donnarumma; five DEFs; Tzolis, Palmer, Sarr; Haaland, Isak. Bench: Walle Egeli, Tzolakis, Crooks, Slater. Starters: `operational_select_11.csv`.

#### FT hurdles

Companion: `operational_ft_hurdles.csv`. Gain = remaining GW→19 Dual-Vector xP (skip FH on owned 15s).

| FTs at deadline | Spend if gain > |
|---|---|
| 5, first FT | 0.2 |
| 5, extra FTs | hurdle for bank after spend |
| 4 | 1.0 |
| 3 | 1.5 |
| 1–2 | 2.5 or DNP |
| 0 | hit > 4 or DNP |

### Alternatives

- Canonical-only: hold FH/TC; different WC 15. Rejected: spend Set 1 by GW19.
- First-Half greedy FT CSV: 9 moves, threshold 0.05. Rejected: not MILP FT value; ping-pong. Cap-5 first FT may still take some of those GW6 swaps if remaining-horizon gain > 0.2.
- WC3 calendar: different GW1 15. Rejected: WC4 already locked.

## Decision

**Verdict**: Play **Operational First-Half Plan OP1**. Identity `operational_summary.csv` `frozen_19gw_xi_xp` (**1182.14** on this Dual-Vector frozen-XI pass). Chips BB1, WC4, FH12, TC17. Keepers = MILP pair in the 15s, not DCS Raya+fodder.

**Recommended action**:
- GW1: copy pre-WC 15; Bench Boost; captain Haaland.
- GW2–3: roll FTs except DNP.
- GW4: Wildcard to WC rebuild 15.
- GW5+: bank-state hurdles; remaining First-Half total.
- GW12: rebuild Free Hit 15 at deadline.
- GW15: captain Tzolis on this sheet.
- GW17: Triple Captain Haaland.

**Trigger / kill switch**:
- Confirmed blank/double or Haaland out GW17 → re-run First-Half `run_chip_path.py`, then refresh this exporter.
- Flagged DNP on a starter → transfer regardless of hurdle.

## Risks and unknowns

- `frozen_19gw_xi_xp` ≠ First-Half `total_19gw_xp` (greedy FTs + different week scoring).
- August FH snapshot will be wrong by GW12.
- Expected Role frozen GW1–5 for Dual-Vector 19-week sheet.
- Canonical `banked_fts_gw6` = 4 vs this plan’s cap-5 at GW6 after GW5 roll.
- Transfer Plan is Champion + Official Fixture Difficulty; Dual-Vector playbook until a swap clears the hurdle.

## Refresh checklist

- [x] `Updated` ISO 8601 with timezone
- [x] `Data stamp` evidence cutoff
- [x] Season GW1–19
- [x] Source vs interpretation split
- [x] Agent Prompt points at `export_operational_plan.py`
- [x] Live Canonical / First-Half greedy CSV / production builder untouched

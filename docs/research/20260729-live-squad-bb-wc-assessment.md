# FPL 2026/27 Live Squad vs BB→WC Strategy

**Date**: 2026-07-29 (squad refresh ~11:00 ICT)  
**Status**: Current entry audit — refresh after each `commands.refresh_data`  
**Entry**: 822158  
**Strategy ref**: [`20260728-bb-then-wc-strategy-plan.md`](20260728-bb-then-wc-strategy-plan.md) (authored 2026-07-28)  
**Index**: [`20260729-bb-wc-research-index.md`](20260729-bb-wc-research-index.md)  
**Source**: `data/raw/my_team_822158.json` · bank £0.0 · value £100.0m · transfers **unlimited**

---

## Verdict

Live squad is a **Squad C–shaped** build (LIV triple + Ballard) with **Palmer instead of Bruno**, **Shaw instead of Maguire**, **Kayode instead of Mitchell**. Chip path still valid; biggest strategy gap is GW1–2 captaincy without Bruno.

| Dimension | Call |
| --- | --- |
| Overall fit | ~70% — rentals + keep core mostly right; opener premium wrong |
| Closest template | Strategy Squad C (Wirtz triple) with safer United DEF |
| Blocker before GW1 | Confirm Wirtz XI; decide Palmer→Bruno funding |
| BB readiness | Good if Ballard / Wirtz / Thomas / Xhaka / Kayode all start |

---

## Current squad (822158)

| Pos | XI / Bench | Player | Club | £ | Strategy bucket | Fit |
| --- | --- | --- | ---: | ---: | --- | --- |
| GKP | XI | Kinsky | TOT | 4.5 | Keep | Aligns (CS thesis) |
| GKP | Bench | Verbruggen | BHA | 4.5 | Keep | Aligns |
| DEF | XI | Ballard | SUN | 5.0 | Keep/flex | Aligns; minutes risk |
| DEF | XI | N.Williams | NFO | 5.0 | Keep | Aligns |
| DEF | XI | Shaw | MUN | 4.5 | Keep/flex | Safer than Maguire for BB |
| DEF | Bench | Kayode | BRE | 4.5 | Flex | OK; strategy preferred Mitchell |
| DEF | Bench | Thomas | COV | 4.0 | BB floor | Aligns |
| MID | XI | Palmer | CHE | 9.5 | Keep/flex | Price lock OK; **weaker GW1–2 than Bruno** |
| MID | XI | Szoboszlai | LIV | 7.0 | Keep | Aligns |
| MID | XI | Wirtz | LIV | 7.5 | Rental | **LIV triple** — XI-gated |
| MID | XI | Mbeumo | MUN | 8.0 | Rental | Aligns United sprint |
| MID | Bench | Xhaka | SUN | 5.5 | BB floor | Aligns; 2 SUN with Ballard |
| FWD | XI | Haaland (C) | MCI | 15.5 | Keep | Aligns |
| FWD | XI | Isak | LIV | 9.0 | Keep | Aligns |
| FWD | XI | Calvert-Lewin | LEE | 6.0 | Rental | Aligns Leeds bridge |

**Club counts:** LIV 3 · SUN 2 · MUN 2 · others 1. Legal.

**Formation lean:** 3-4-3 (Kinsky; Ballard, N.Williams, Shaw; Palmer, Szobo, Wirtz, Mbeumo; Haaland, Isak, CLD).

---

## Score vs strategy rules

| Rule | Status |
| --- | --- |
| Dual locked GKs (Kinsky path) | Pass |
| Keep core Haaland / Szobo / Isak | Pass |
| United / Leeds fixture rentals | Pass (Mbeumo + CLD) |
| BB floor starters (Thomas, Xhaka) | Pass if both start |
| Bruno captain engine GW1–2 | **Fail** — Palmer owned instead |
| LIV double default (Wirtz gated) | **Risk** — triple already in |
| Mitchell value DEF | Miss — Kayode/Shaw instead |
| Maguire only if XI-confirmed | N/A — Shaw chosen (safer) |
| ≤3/club · £100 · bank | Pass |

---

## Diff vs recommended Squad B

| Squad B wants | Live has | Delta |
| --- | --- | --- |
| Bruno £12.0 | Palmer £9.5 | −£2.5; lose HUL/IPS armband |
| Mitchell £4.5 | Kayode £4.5 | Same price; lower DEF ceiling |
| Cash £4.5 | Shaw £4.5 | United minutes safer; less G/A than Cash |
| Ndiaye £6.0 | Wirtz £7.5 | +£1.5; LIV triple concentration |
| Ballard | Ballard | Match |
| Kinsky / Verbruggen / N.Williams / Thomas / Mbeumo / Haaland / Isak / CLD / Xhaka / Szobo | Same set | Match |

---

## Priority moves (unlimited window)

1. **Confirm Wirtz XI** — if soft, sell first (frees budget toward Bruno).  
2. **Palmer → Bruno** if chasing strategy captaincy (~£2.5; typically needs Wirtz → cheaper mid).  
3. Optional: **Kayode → Mitchell** (same £4.5).  
4. Keep **Shaw** unless Maguire is locked for HUL/IPS.

Example funding path (illustrative): Wirtz £7.5 → Ndiaye £6.0 (−£1.5) + further −£1.0 DEF/mid tweak → Palmer £9.5 → Bruno £12.0. Re-check club limits after any LIV cut.

---

## Chip status (as of refresh)

| Chip | Status |
| --- | --- |
| Bench Boost (1st half) | Available |
| Triple Captain (1st half) | Available |
| Wildcard / Free Hit | Not returned on this API payload — re-check before booking GW4 WC |

Planned cadence (from strategy): BB GW2 preferred · WC ~GW4 · do not burn TC on BB week.

---

## Captain plan on current XV

| GW | Armband | Vice | Note |
| ---: | --- | --- | --- |
| 1 | Haaland (BOU H) | Mbeumo (HUL A) / Isak | No Bruno — Haaland default |
| 2 | Haaland or Isak (NFO H) | Mbeumo (IPS H) | Weaker than Bruno IPS H |
| 3 | Haaland (COV H) | Isak | Soft City home |
| 4 | WC week | — | Sell Mbeumo/CLD/Wirtz-if-soft |

---

## How to refresh this note

1. `uv run python -m commands.refresh_data`  
2. Re-extract picks from `data/raw/my_team_*.json`  
3. Re-score against [`20260728-bb-then-wc-strategy-plan.md`](20260728-bb-then-wc-strategy-plan.md)  
4. Update this file (or write a new dated assessment); leave the strategy plan unchanged unless rules change.

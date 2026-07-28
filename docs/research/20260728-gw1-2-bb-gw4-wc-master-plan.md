# FPL 2026/27 Strategy Master Plan: GW1–2 Bench Boost → GW4 Wildcard

**Date**: 2026-07-28  
**Strategy**: Pre-season unlimited transfers → GW1 or GW2 Bench Boost → GW4 Wildcard Rebuild  
**Inputs**: [`my_team_822158.json`](../../data/raw/my_team_822158.json) · [`20260728-early-wildcard-gw1-3-bridge.md`](20260728-early-wildcard-gw1-3-bridge.md) · [`20260728-full-squad-cheap-back-wild-attack.md`](20260728-full-squad-cheap-back-wild-attack.md) · [`20260728-gkp-def-budget-ratings.md`](20260728-gkp-def-budget-ratings.md) · [`20260728-pl-nailed-regular-starters.md`](20260728-pl-nailed-regular-starters.md)  
**Constraints**: £100.0m budget · ≤3 players per club · 15 active starters  

---

## Original User Intent & Rationale (Prompt-Ready Context)

```yaml
role: FPL Strategy & Selection Agent
objective: Evaluate original squad (my_team_822158.json) against GW1–3 bridge strategy, run GW1–2 Bench Boost, and execute GW4 Wildcard rebuild.
horizon: GW1–3 Sprint → GW4 Wildcard Reset
constraints:
  budget: £100.0m
  club_limit: ≤3 per team
  squad_size: 15 active 90-min starters (for Bench Boost)

core_thesis:
  1_unlimited_pre_gw1:
    - Use pre-season free reset to build 15 active starters.
    - Maximize Bench Boost (BB) payload in GW1 or GW2.
  2_gw1_3_fixture_sprint:
    - Focus starting XI strictly on GW1–3 fixture FDR (Liverpool 2.50, Man Utd GW1–3 sprint, Man City soft homes).
    - Treat short-term fixture picks (Maguire, Mbeumo, Wilson) as planned Layer B sells for GW4.
  3_mandatory_price_locks:
    - Hold high-ownership template risers (Haaland, Palmer, Isak, Szoboszlai, João Pedro) from GW1.
    - Protect team value against early price rises before Wildcard.
  4_gw4_wildcard_rebuild:
    - GW4 is designated Wildcard week (Man Utd face Man City in GW4).
    - Flush Layer B bridge assets; rebuild for long-term season structure (GW4–10+).

chip_flexibility:
  bench_boost: GW1 (immediate 15-starter payload) OR GW2 (confirm GW1 XIs; target MUN vs IPS & LIV vs NFO)
  wildcard: GW4 TARGETED (flush bridge assets before MUN vs MCI derby; optional slip to GW5 if extra data required)
```

---

## Master GW1–GW4 Fixture Difficulty Matrix

| Team | Avg FDR (GW1–4) | GW1 | GW2 | GW3 | GW4 (WC Week) | Fixture Assessment |
| --- | ---: | --- | --- | --- | --- | --- |
| **Liverpool** | **2.50** | NEW (A) `[3]` | NFO (H) `[3]` | IPS (A) `[2]` | **FUL (H)** `[2]` | **#1 Easiest Run in PL** — 4 winnable, high-scoring games |
| **Brentford** | **2.75** | TOT (H) `[3]` | LEE (A) `[3]` | SUN (H) `[2]` | **BOU (A)** `[3]` | Consistent low difficulty, avoids top 4 |
| **Brighton** | **2.75** | AVL (H) `[3]` | CHE (A) `[4]` | LEE (H) `[2]` | **COV (A)** `[2]` | GW3–4 ultra-soft vs promoted/mid-table |
| **Leeds** | **2.75** | NFO (A) `[3]` | BRE (H) `[3]` | BHA (A) `[3]` | **NEW (H)** `[2]` | Balanced early schedule, avoids City/Arsenal |
| **Man Utd** | **2.75** | **HUL (A)** `[2]` | **IPS (H)** `[2]` | **EVE (A)** `[3]` | **MCI (H)** `[4]` | **Best GW1–3 Sprint** → Drops off GW4 (WC Exit Trigger) |
| **Spurs** | **2.75** | BRE (A) `[3]` | NEW (H) `[2]` | NFO (A) `[3]` | **EVE (H)** `[3]` | Solid early games, avoids top 3 |
| **Sunderland** | **2.75** | IPS (A) `[2]` | FUL (H) `[2]` | BRE (A) `[3]` | **ARS (H)** `[4]` | Strong GW1–2 for cheap enablers (Xhaka, Hume) |
| **Aston Villa** | **3.00** | BHA (A) `[3]` | ARS (H) `[4]` | HUL (A) `[2]` | **NFO (H)** `[3]` | Mixed early run |
| **Chelsea** | **3.00** | FUL (A) `[3]` | BHA (H) `[2]` | ARS (A) `[5]` | **HUL (H)** `[2]` | BHA (H) in GW2 and HUL (H) in GW4 are prime |
| **Palace** | **3.00** | EVE (A) `[3]` | MCI (H) `[4]` | FUL (A) `[3]` | **IPS (H)** `[2]` | Solid GW1, GW3, GW4 |
| **Man City** | **3.00** | **BOU (H)** `[3]` | CRY (A) `[3]` | **COV (H)** `[2]` | **MUN (A)** `[4]` | **2 Soft Homes in GW1–3** for Haaland |
| **Arsenal** | **3.25** | COV (H) `[2]` | AVL (A) `[4]` | CHE (H) `[4]` | **SUN (A)** `[3]` | Tough GW2–3 sequence (Villa A, Chelsea H) |
| **Everton** | **3.25** | CRY (H) `[3]` | BOU (A) `[3]` | MUN (H) `[4]` | **TOT (A)** `[3]` | Tough mid-run |
| **Hull City** | **3.25** | MUN (H) `[4]` | COV (A) `[2]` | AVL (H) `[3]` | **CHE (A)** `[4]` | Promoted, heavy defensive workload |
| **Ipswich** | **3.25** | SUN (H) `[2]` | MUN (A) `[4]` | LIV (H) `[4]` | **CRY (A)** `[3]` | Meets Man Utd & Liverpool in GW2–3 |
| **Newcastle** | **3.25** | LIV (H) `[4]` | TOT (A) `[3]` | BOU (H) `[3]` | **LEE (A)** `[3]` | Tough opener vs Liverpool |
| **Forest** | **3.25** | LEE (H) `[2]` | LIV (A) `[4]` | TOT (H) `[3]` | **AVL (A)** `[4]` | GW2 Liverpool away trip |
| **Bournemouth**| **3.50** | MCI (A) `[5]` | EVE (H) `[3]` | NEW (A) `[3]` | **BRE (H)** `[3]` | Toughest opener (Man City away) |
| **Coventry** | **3.50** | ARS (A) `[5]` | HUL (H) `[2]` | MCI (A) `[5]` | **BHA (H)** `[2]` | Plays Arsenal (GW1) and Man City (GW3) |
| **Fulham** | **3.50** | CHE (H) `[4]` | SUN (A) `[3]` | CRY (H) `[3]` | **LIV (A)** `[4]` | Meets Chelsea (GW1) and Liverpool (GW4) |

---

## Flexible Chip Execution Framework

### Bench Boost Window (GW1 vs GW2)
- **GW1 BB**: Maximum 15-starter deployment; avoids risk of GW1 injuries or surprise benchings affecting GW2.
- **GW2 BB**: Allows 1 week of PL XI confirmation; targets ultra-prime home fixtures (MUN vs IPS H, LIV vs NFO H, LEE vs BRE H).

### Wildcard 1 Window (GW4 Targeted)
- **GW4 WC (TARGETED — USER LEAN)**: Man Utd face Man City in GW4. Cleanly flushes Layer B bridge assets (Maguire, Mbeumo, Wilson) right after their GW1–3 fixture sprint without burning free transfers.
- **GW5 WC (FALLBACK)**: Optional 1-week slip if post-transfer deadline (1 Sep) data requires extra verification.

---

## Primary Squad Selection — "João Pedro + Leeds Bridge" (£100.0m)

Optimized for form protection, mandatory price-locks, and GW1–3 fixture sprint.

| Pos | Player | Club | £ | Tier | GW1–3 Fixture Sprint | Strategy Role |
| --- | --- | --- | ---: | --- | --- | --- |
| **GKP** | Verbruggen | BHA | 4.5 | N | SHU (A) · IPS (H) · MCI (A) | BB Locked Starter 1 |
| **GKP** | Kinsky | TOT | 4.5 | N | BUR (H) · LEI (A) · WHU (H) | BB Locked Starter 2 |
| **DEF** | Maguire | MUN | 5.0 | R | **HUL (A) · IPS (H) · EVE (A)** | **Layer B Bridge (Sell GW4)** |
| **DEF** | N.Williams | NFO | 5.0 | N | LEE (H) · LIV (A) · MUN (H) | Layer A Core |
| **DEF** | Mitchell | CRY | 4.5 | N | CHE (A) · MCI (H) · AST (A) | Layer A Core |
| **DEF** | Thomas | COV | 4.0 | N | SUN (A) · STO (H) · WAT (A) | **BB Promoted DEFCON Enabler** |
| **DEF** | O'Shea | IPS | 4.0 | N | ARS (H) · MUN (A) · MCI (H) | **BB Promoted DEFCON Enabler** |
| **MID** | Palmer | CHE | 9.5 | N | CRY (H) · WOL (A) · MCI (H) | **Price Lock & Haul Core** |
| **MID** | Mbeumo | MUN | 8.0 | N | **HUL (A) · IPS (H) · EVE (A)** | **Layer B Bridge (Sell GW4)** |
| **MID** | Szoboszlai | LIV | 7.0 | N | **NEW (A) · NFO (H) · IPS (A)** | **Price Lock & PL #1 FDR** |
| **MID** | H.Wilson | LEE | 6.5 | N | **NFO (A) · BRE (H) · BHA (A)** | **Layer B Bridge (Sell GW4)** |
| **MID** | Xhaka | SUN | 5.5 | N | COV (H) · SOU (A) · MID (H) | BB Nailed 90-min Floor |
| **FWD** | Haaland | MCI | 15.5 | N | **BOU (H) · CRY (A) · COV (H)** | **Price Lock & Captain Engine** |
| **FWD** | Isak | LIV | 9.0 | N | **NEW (A) · NFO (H) · IPS (A)** | **Price Lock & PL #1 FDR #9** |
| **FWD** | João Pedro | CHE | 7.5 | N | **CRY (H) · WOL (A) · MCI (H)** | **Price Lock (Pre-season hat-trick)** |
| **Total**| | | **100.0** | | | **15 Active Starters · Max 3/club** |

---

## Alternative Squad Selection — "Wirtz Triple Liverpool + United Bridge" (£100.0m)

Use if pre-season friendlies confirm Wirtz is starting as primary creator and João Pedro faces rotation.

| Pos | Player | Club | £ | Tier | GW1–3 Fixture Sprint | Strategy Role |
| --- | --- | --- | ---: | --- | --- | --- |
| **GKP** | Verbruggen | BHA | 4.5 | N | SHU (A) · IPS (H) · MCI (A) | BB Locked Starter 1 |
| **GKP** | Kinsky | TOT | 4.5 | N | BUR (H) · LEI (A) · WHU (H) | BB Locked Starter 2 |
| **DEF** | Maguire | MUN | 5.0 | R | HUL (A) · IPS (H) · EVE (A) | Layer B Bridge (Sell GW4) |
| **DEF** | N.Williams | NFO | 5.0 | N | LEE (H) · LIV (A) · MUN (H) | Layer A Core |
| **DEF** | Mitchell | CRY | 4.5 | N | CHE (A) · MCI (H) · AST (A) | Layer A Core |
| **DEF** | Hume | SUN | 4.5 | N | COV (H) · SOU (A) · MID (H) | BB Solid Floor |
| **DEF** | Thomas | COV | 4.0 | N | SUN (A) · STO (H) · WAT (A) | BB Promoted DEFCON Enabler |
| **MID** | Palmer | CHE | 9.5 | N | CRY (H) · WOL (A) · MCI (H) | Layer A Core |
| **MID** | Mbeumo | MUN | 8.0 | N | HUL (A) · IPS (H) · EVE (A) | Layer B Bridge (Sell GW4) |
| **MID** | Szoboszlai | LIV | 7.0 | N | NEW (A) · NFO (H) · IPS (A) | Layer A Core |
| **MID** | Wirtz | LIV | 7.5 | R | NEW (A) · NFO (H) · IPS (A) | BB Active Power-Bench |
| **MID** | Xhaka | SUN | 5.5 | N | COV (H) · SOU (A) · MID (H) | BB Nailed Floor |
| **FWD** | Haaland | MCI | 15.5 | N | BOU (H) · CRY (A) · COV (H) | Layer A Core |
| **FWD** | Isak | LIV | 9.0 | N | NEW (A) · NFO (H) · IPS (A) | Layer A Core |
| **FWD** | Solanke | TOT | 6.0 | R | BUR (H) · LEI (A) · WHU (H) | Short-term Starter |
| **Total**| | | **100.0** | | | **15 Active Starters** |

---

## GW4 Wildcard Rebuild Mechanics

In GW4, United play City (MCI H), ending EV advantage of Maguire/Mbeumo.

1. **Sell Bridge Assets (GW4)**: Maguire (£5.0m), Mbeumo (£8.0m), H.Wilson (£6.5m).
2. **Reinvest into Improving Fixtures**: Target Arsenal DEFs (Gabriel £8.0m / Calafiori £5.5m), Palace/Bournemouth DEFs (Muñoz £5.5m / Truffert £5.5m), or Saka (£9.5m) / Semenyo (£8.5m).
3. **Retain Price-Locked Core**: Hold Haaland, Palmer, Isak, Szoboszlai, João Pedro into season-long build.

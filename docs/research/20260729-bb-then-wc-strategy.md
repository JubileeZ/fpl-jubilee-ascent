# FPL 2026/27 — BB Early → WC Rebuild

**Date**: 2026-07-29  
**Data stamp**: bootstrap / entry 822158 refreshed **2026-07-29 ~11:00 ICT**  
**Status**: Strategy + live assessment — RoleScore-backed picks · line-sums verified  
**Horizon**: Unlimited → BB (GW2 preferred) → WC ~GW4 · GW1 Fri 21 Aug 2026  
**Constraint**: £100.0m · ≤3/club · **15 starters** on BB week  
**Entry**: 822158 · bank £0.0 · value £100.0m · transfers **unlimited**  
**Baseline**: [`20260729-pl-starter-rolescore.md`](20260729-pl-starter-rolescore.md)  
**Also**: [`20260728-gkp-def-budget-ratings.md`](20260728-gkp-def-budget-ratings.md) · PL Scout FDR  
**WC detail**: [`20260729-gw4-wildcard-chelsea-liverpool.md`](20260729-gw4-wildcard-chelsea-liverpool.md) — GW4 target · CHE turn · LIV core · price hedge  

**Supersedes**: split strategy/assessment/index notes; prior nailed-starters filter → RoleScore baseline.

---

## Verdict

| Decision | Call | RoleScore anchor |
| --- | --- | --- |
| Chip path | Unlimited → BB GW2 → WC ~GW4 | — |
| Spine | **Haaland + B.Fernandes + Szoboszlai + Isak** | 90 / 100 / 82 / 67* |
| Default | **Squad B £100.0** | — |
| Live 822158 | ~70% fit — LIV triple + Ballard; Palmer not Bruno | — |
| Blocker | Confirm Wirtz XI; fund Palmer→Bruno; **Thomas vs Amenda** | Wirtz RS 65 R |
| Kinsky | Accept dual with Verbruggen | 66 N (THIN Ext) |
| Ballard | Playable threat-CB — fitness gate | 74 R · thr90 15.5 |
| O'Shea not Diop | BB floor | 70 N vs 29 B |
| Ampadu not Mainoo | £5.5 flex | 86 N vs 48 B |
| Anderson | Avoid | 66 R wrong role + GW1 WC |

\*Isak RS conservative (THIN / injury-wrecked LIV sample); Ext = **R lean** preferred 9 until friendlies clear fitness.

Core idea: **keep post-WC assets**, **rent ~3-week fixtures**, **Wildcard when United hit City**.

---

## Math audit (re-verified 2026-07-29)

| Template | Sum | Notes |
| --- | ---: | --- |
| Squad A | **100.0** | GKP 9 + DEF 22.5 + MID 36.5 + FWD 32.0 |
| Squad B | **100.0** | GKP+DEF 31.5 + MID 38.0 + FWD 30.5 |
| Squad C | **100.0** | 9 + 23 + 38 + 30 |
| Live 822158 | **100.0** | bank 0 |
| Broken historical B (Cash+Ndiaye+CLD) | **101.0** | do not use |

Prices from `players.parquet` (`now_cost`/10). **B.Fernandes** £12.0 ≠ Spurs Fernandes £6.0. Leeds mid = **Wilson** £6.5.

---

## Pick dossiers (why this name)

### GK — Kinsky + Verbruggen (not Leno dual)

| | Kinsky | Leno | Verbruggen |
| --- | ---: | ---: | ---: |
| £ | 4.5 | 4.5 | 4.5 |
| Ext / RS | N / 66 | N / 84 | N / 95 |
| 25/26 starts | 7 | 38 | 38 |
| mps | 90 | 90 | 90 |

**Why Kinsky:** De Zerbi No.1 + contract signal; CS differential thesis. Stats THIN — trust Ext. **Why Verbruggen second:** ironman dual lock. Never Kinsky+Dubravka.

### DEF — Ballard (not Maguire as structure)

| | Ballard | Maguire | Shaw | Mukiele |
| --- | ---: | ---: | ---: | ---: |
| £ | 5.0 | 5.0 | 4.5 | 5.5 |
| Ext / RS | R / 74 | R / 67 | N / 86 | N / 86 |
| starts / mps | 24 / **89.3** | 19 / 86.8 | 38 / 84.7 | 32 / 87.0 |
| **thr90** | **15.5** | 10.0 | 2.7 | 7.8 |

**Why Ballard:** per-90 threat elite for CB; plays ~90 when selected; in strongest SUN XI. Injury-limited start *count*, not soft output. **Fitness gate** (45' vs LIV return) before BB bank. Maguire = GW1–3 rental while **De Ligt out until autumn**. Shaw = safer minutes / lower ceiling. Mukiele = safer SUN if Ballard soft.

### DEF — Mitchell (not Kayode as value) · O'Shea (not Diop)

| | Mitchell | Kayode | Cash | O'Shea | Diop |
| --- | ---: | ---: | ---: | ---: | ---: |
| £ | 4.5 | 4.5 | 4.5 | 4.0 | 4.0 |
| Ext / RS | N / 84 | N / 87 | N / 87 | N / **70** | B / **29** |
| thr90 | 6.7 | 3.6 | 6.6 | — | 3.4 |

**Mitchell > vibes:** ironman + usable G/A; thr90 ≈ Cash. Kayode = pure minutes enabler. **O'Shea:** IPS captain / only clear N; Diop competes same side unless back 3. Cash upgrade needs −£0.5 elsewhere (Squad B uses O'Shea to hit £100).

### DEF — Thomas BB floor (Amenda kill switch)

Ext R→B if **Amenda £17m** starts · RS 49 · NO_PL_MINS.  
**Keep Thomas only if** friendly XI confirms over Amenda; else swap → **van Ewijk** £4.0 (same budget, safer mins, weaker DEFcon).

### MID — Bruno not Palmer · Ampadu not Mainoo · Szobo not Wirtz-default

| | Bruno | Palmer | Ampadu | Mainoo | Szobo | Wirtz | Xhaka | Ndiaye |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| £ | 12.0 | 9.5 | 5.5 | 5.5 | 7.0 | 7.5 | 5.5 | 6.0 |
| Ext / RS | N / **100** | N / 81 | N / **86** | B / **48** | N / 82 | R / 65 | N / 85 | N / 90 |
| xGI90 | 0.68 | 0.60 | 0.13 | 0.10 | 0.32 | **0.45** | 0.15 | 0.36 |

**Bruno:** HUL A / IPS H captaincy. **Ampadu:** ironman DM + Scout DC; Mainoo = mid-trio B + WC rest. **Szobo** default LIV; **Wirtz** only if XI locked (rates excellent, new-manager dock). **Xhaka** BB floor SUN. Ndiaye higher attack than Ampadu but +£0.5 breaks Squad B unless funded.

### FWD — Haaland / Isak / CLD

| | Haaland | Isak | CLD | Wright |
| --- | ---: | ---: | ---: | ---: |
| £ | 15.5 | 9.0 | 6.0 | 5.5 |
| Ext / RS | N / 90 | N / 67* | N / 94 | N / 70 |
| Flag | IRONMAN | THIN | IRONMAN | NO_PL |

\*Trust Isak Ext+xGI90 (0.35) / thr90 (24.8) over 8-start totals — **fitness-gated R lean**, not ironman N. CLD Leeds bridge with Ampadu (2 LEE). Wright = alt £100 path if drop CLD. Mbeumo or **Cunha** both OK for United sprint (fade Amad).

### Avoid — Anderson

37-start ironman **wrong role** at City. DEFcon haul from pressing mid will not repeat.

---

## Chip path

1. Pre-GW1 unlimited → 15 expected starters.  
2. BB GW2 preferred (Bruno IPS H, LIV NFO H).  
3. WC ~GW4 (United vs City ends sprint).  
4. Save FH / TC — no TC on BB week.

### User biases

| Bias | Stance vs RoleScore |
| --- | --- |
| Kinsky over Leno | Agree differential — Ext N despite THIN |
| Threat CB (Ballard) over Mitchell | Partial — Ballard thr90 wins; Mitchell RS/minutes win; own both roles in templates |
| Maguire ceiling | True when starting — rental only |
| Bruno captain | Strongly agree (RS 100) |

---

## Squad A — User original (£100.0)

| Pos | Player | Club | £ | Bucket |
| --- | --- | ---: | ---: | --- |
| GKP | Verbruggen | BHA | 4.5 | Keep |
| GKP | Kinsky | TOT | 4.5 | Keep |
| DEF | Maguire | MUN | 5.0 | Rental |
| DEF | N.Williams | NFO | 5.0 | Keep |
| DEF | Mitchell | CRY | 4.5 | Keep |
| DEF | Thomas | COV | 4.0 | BB floor |
| DEF | O'Shea | IPS | 4.0 | BB floor |
| MID | Palmer | CHE | 9.5 | Flex |
| MID | Mbeumo | MUN | 8.0 | Rental |
| MID | Szoboszlai | LIV | 7.0 | Keep |
| MID | Wilson | LEE | 6.5 | Rental |
| MID | Xhaka | SUN | 5.5 | BB floor |
| FWD | Haaland | MCI | 15.5 | Keep |
| FWD | Isak | LIV | 9.0 | Keep |
| FWD | João Pedro | CHE | 7.5 | Keep |
| | **Total** | | **100.0** | |

**Weak:** no Bruno GW1–2 armband.

### A′ Ballard (£100.0)

Mitchell → Ballard (+0.5); Wilson → Ndiaye (−0.5).

---

## Squad B — Recommended (£100.0)

| Pos | Player | Club | £ | Bucket | RS lean |
| --- | --- | ---: | ---: | --- | --- |
| GKP | Verbruggen | BHA | 4.5 | Keep | 95 |
| GKP | Kinsky | TOT | 4.5 | Keep | 66 |
| DEF | Ballard | SUN | 5.0 | Keep/flex | 74 |
| DEF | N.Williams | NFO | 5.0 | Keep | 87 |
| DEF | Mitchell | CRY | 4.5 | Keep | 84 |
| DEF | O'Shea | IPS | 4.0 | BB floor | 70 |
| DEF | Thomas | COV | 4.0 | BB floor | 49† |
| MID | B.Fernandes | MUN | 12.0 | Keep | 100 |
| MID | Mbeumo | MUN | 8.0 | Rental | 81 |
| MID | Szoboszlai | LIV | 7.0 | Keep | 82 |
| MID | Ampadu | LEE | 5.5 | Flex | 86 |
| MID | Xhaka | SUN | 5.5 | BB floor | 85 |
| FWD | Haaland | MCI | 15.5 | Keep | 90 |
| FWD | Isak | LIV | 9.0 | Keep | 67* |
| FWD | Calvert-Lewin | LEE | 6.0 | Rental | 94 |
| | **Total** | | **100.0** | | |

GKP+DEF £31.5 + MID £38.0 + FWD £30.5 = **£100.0**.  
Clubs: 2 MUN · 2 LIV · 2 SUN · 2 LEE.  
†**Thomas kill switch:** if Amenda starts Coventry friendlies → Thomas → van Ewijk £4.0 (total still £100).

| Variant | Δ | Total |
| --- | --- | ---: |
| Maguire for Ballard | £0 | 100.0 if XI locked |
| Ndiaye for Ampadu | +£0.5 | **100.5 invalid** unless cut elsewhere |
| Cash for O'Shea | +£0.5 | **100.5 invalid** alone |
| Alt: Ndiaye + Wright (drop CLD) | £0 | 100.0 |

---

## Squad C — Wirtz triple if XI locked (£100.0)

| Pos | Players | £ |
| --- | --- | ---: |
| GKP | Verbruggen, Kinsky | 9.0 |
| DEF | Maguire, Ballard, N.Williams, Thomas, O'Shea | 23.0 |
| MID | Bruno 12, Szobo 7, Wirtz 7.5, Ndiaye 6, Xhaka 5.5 | 38.0 |
| FWD | Haaland 15.5, Isak 9, Wright 5.5 | 30.0 |
| | **Total** | **100.0** |

**Kill switch:** Wirtz / Maguire / Ballard fails friendly XI → Squad B.  
Meerkat (28 Jul) lists Wirtz in LIV XI — raises odds vs 21 Jul note; still Iraola-new → confirm.

---

## Live squad 822158

| Pos | Slot | Player | £ | vs B |
| --- | --- | --- | ---: | --- |
| GKP | XI | Kinsky | 4.5 | Match |
| GKP | Bench | Verbruggen | 4.5 | Match |
| DEF | XI | Ballard | 5.0 | Match |
| DEF | XI | N.Williams | 5.0 | Match |
| DEF | XI | Shaw | 4.5 | Prefer O'Shea (−0.5) |
| DEF | Bench | Kayode | 4.5 | Prefer Mitchell |
| DEF | Bench | Thomas | 4.0 | Match |
| MID | XI | Palmer | 9.5 | Prefer Bruno (+2.5) |
| MID | XI | Szoboszlai | 7.0 | Match |
| MID | XI | Wirtz | 7.5 | Prefer Ampadu if not locked |
| MID | XI | Mbeumo | 8.0 | Match |
| MID | Bench | Xhaka | 5.5 | Match |
| FWD | XI | Haaland (C) | 15.5 | Match |
| FWD | XI | Isak | 9.0 | Match |
| FWD | XI | Calvert-Lewin | 6.0 | Match |
| | | **Total** | **100.0** | |

Clubs: LIV 3 · SUN 2 · MUN 2. Legal.

### Funding → Squad B (£0 net)

| Move | Δ £ | RoleScore logic |
| --- | ---: | --- |
| Palmer → B.Fernandes | +2.5 | 81 → 100; captaincy |
| Wirtz → Ampadu | −2.0 | 65 R → 86 N unless Wirtz locks |
| Shaw → O'Shea | −0.5 | 86 → 70; frees budget / BB floor |
| Kayode → Mitchell | 0.0 | 87 → 84; better thr90 |
| **Net** | **0.0** | |

### Chips (API)

| Chip | Status |
| --- | --- |
| BB / TC (1st half) | Available |
| WC / FH | Not on payload — re-check before GW4 |

### Captain on current XV

| GW | C | VC |
| ---: | --- | --- |
| 1 | Haaland (BOU H) | Mbeumo / Isak |
| 2 | Haaland or Isak | Mbeumo (IPS H) |
| 3 | Haaland (COV H) | Isak |
| 4 | WC | — |

---

## Chip calendar

```text
Pre-GW1   Unlimited → Squad B / A / C (Wirtz locked)
GW1       No chip. Bruno (HUL A) or Haaland (BOU H).
GW2       BENCH BOOST. Bruno (IPS H). Vice Isak (NFO H).
GW3       Haaland (COV H).
GW4       WILDCARD — sell rentals.
```

## GW4 sell / hold

| Sell | Hold |
| --- | --- |
| Maguire, Mbeumo, CLD / Wilson / Ampadu, Wirtz if soft, O'Shea/Thomas if flop | Haaland, Bruno, Szobo, Isak, N.Williams, Verbruggen, Kinsky if thesis holds, Ballard if mins stick |

## Decision tree

```text
Wirtz locked XI in friendlies?
├─ YES → Squad C (3×LIV)
└─ NO
   ├─ Maguire+Ballard CB stack? → A′ / C sans Wirtz
   ├─ Bruno + Kinsky? → Squad B (default)
   └─ Palmer + João Pedro? → Squad A
```

---

## Bottom line

1. **Squad B £100** — O'Shea + Ampadu (not Cash + Ndiaye; not Mainoo).  
2. Picks reproved via RoleScore: O'Shea≻Diop, Ampadu≻Mainoo, Ballard rates≻raw starts, Bruno≻Palmer early, Kinsky Ext≻sample.  
3. Live gap = Palmer / Wirtz / Shaw-Kayode vs Bruno / Ampadu / O'Shea-Mitchell.  
4. Refresh baseline + this file after each `commands.refresh_data`.  
5. Pre-deadline gates: Wirtz XI · Ballard full 90 · **Thomas vs Amenda** · Isak fitness · Maguire CB.

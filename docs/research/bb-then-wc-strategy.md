# FPL 2026/27 — BB Early → WC Rebuild

**Updated**: 2026-07-29T22:20:00+07:00  
**Data stamp**: bootstrap / entry **822158** refreshed **2026-07-29 ~22:17 ICT** (Playwright auth)  
**Status**: Strategy + live assessment — RoleScore-backed · line-sums verified  
**Horizon**: Unlimited → BB (GW2 preferred) → WC ~GW4 · GW1 Fri 21 Aug 2026  
**Constraint**: £100.0m · ≤3/club · **15 starters** on BB week  
**Entry**: 822158 · bank £0.0 · value £100.0m · transfers **unlimited**  
**Baseline**: [`pl-starter-rolescore.md`](pl-starter-rolescore.md)  
**Also**: [`gkp-def-budget-ratings.md`](gkp-def-budget-ratings.md) · PL Scout FDR  
**WC detail**: [`gw4-wildcard-chelsea-liverpool.md`](gw4-wildcard-chelsea-liverpool.md)

## Agent Prompt

```
Full redo docs/research/bb-then-wc-strategy.md

1. uv run python -m commands.refresh_data (must auth entry; read data/raw/my_team_<entry>.json if parquet picks stale)
2. Re-read pl-starter-rolescore.md + gkp-def-budget-ratings.md for Ext/RS/prices.
3. Re-verify Squad A/B/C line-sums to £100.0 from players.parquet. Rebuild live 822158 gap table from my-team payload. Chip path Unlimited→BB GW2→WC~GW4.
4. RoleScore-backed pick dossiers. Fold Georginio/Rutter only if owned or BB shortlist wants BHA attack. Thomas→van Ewijk if Amenda starts.
5. Update **Updated** + **Data stamp**. Keep slug filename + sibling links.
6. Delete .tmp/agent/ scratch when done.
```

---

## Verdict

| Decision | Call | RoleScore anchor |
| --- | --- | --- |
| Chip path | Unlimited → BB GW2 → WC ~GW4 | — |
| Spine | **Haaland + B.Fernandes + Szoboszlai + Isak** | 89 / 98 / 84 / 62* |
| Default | **Squad B £100.0** (live already ~match) | — |
| Live 822158 | **~95% fit** — Bruno+Ampadu+Georginio owned; Shaw vs O'Shea; Georginio vs CLD | — |
| Blocker | Confirm Wirtz only if pivoting to C; **Thomas vs Amenda**; Ballard 90s | Wirtz RS 67 R |
| Kinsky | Keep dual with Verbruggen | 71 N (THIN Ext) |
| Ballard | Playable threat-CB — fitness gate | 74 R · thr90 15.5 |
| Georginio | **Owned bench** — BHA #9 thesis; confirm 90s before XI | 75 R lean |
| O'Shea not Diop | Prefer O'Shea if swapping Shaw | 70 N vs 27 B |
| Ampadu | Owned — keep | 86 N |
| Anderson | Avoid | 68 R wrong role |

\*Isak RS conservative (THIN); Ext = **R lean** preferred 9 until friendlies clear fitness.

Core idea: **keep post-WC assets**, **rent ~3-week fixtures**, **Wildcard when United hit City**.

---

## Math audit (re-verified 2026-07-29 ~22:17)

| Template | Sum | Notes |
| --- | ---: | --- |
| Squad A | **100.0** | GKP 9 + DEF 22.5 + MID 36.5 + FWD 32.0 |
| Squad B | **100.0** | GKP+DEF 31.5 + MID 38.0 + FWD 30.5 |
| Squad B′ (live twin) | **100.0** | Shaw+Georginio instead of O'Shea+CLD |
| Squad C | **100.0** | 9 + 23 + 38 + 30 |
| Live 822158 | **100.0** | bank 0 |

Prices from `players.parquet` (`now_cost`/10). **B.Fernandes** £12.0 ≠ Spurs Fernandes. Leeds mid = **Wilson** £6.5 (not BRE Wilson FWD).

---

## Pick dossiers (why this name)

### GK — Kinsky + Verbruggen (not Leno dual)

| | Kinsky | Leno | Verbruggen |
| --- | ---: | ---: | ---: |
| £ | 4.5 | 4.5 | 4.5 |
| Ext / RS | N / 71 | N / 84 | N / 95 |
| 25/26 starts | 7 | 38 | 38 |

**Why Kinsky:** De Zerbi No.1 + EO 17.3% differential. Stats THIN — trust Ext. Never Kinsky+Dubravka (Dubravka EO 24.8% trap).

### DEF — Ballard (threat-CB) · Mitchell · N.Williams

| | Ballard | Maguire | Shaw | Mukiele | Mitchell |
| --- | ---: | ---: | ---: | ---: | ---: |
| £ | 5.0 | 5.0 | 4.5 | 5.5 | 4.5 |
| Ext / RS | R / 74 | R / 67 | N / 86 | N / 86 | N / 84 |
| thr90 | **15.5** | 10.0 | 2.7 | 7.8 | 6.7 |

**Ballard:** per-90 threat elite; Meerkat strongest SUN XI. Fitness/Europa gate. Shaw = safer mins in live XV; O'Shea frees £0.5 if needed.

### DEF — Thomas BB floor (Amenda kill switch)

Ext R→B if **Amenda** starts · RS 49 · Meerkat expects Amenda into COV side.  
**Live owns Thomas** — swap → **van Ewijk** £4.0 if friendlies confirm Amenda CB.

### MID — Bruno owned · Ampadu owned · Szobo default

| | Bruno | Palmer | Ampadu | Mainoo | Szobo | Wirtz | Xhaka |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| £ | 12.0 | 9.5 | 5.5 | 5.5 | 7.0 | 7.5 | 5.5 |
| Ext / RS | N / **98** | N / 83 | N / **86** | B / **46** | N / 84 | R / 67 | N / 85 |
| xGI90 | 0.68 | 0.60 | 0.13 | 0.10 | 0.32 | **0.45** | 0.15 |

**Live already solved** Palmer→Bruno and Wirtz→Ampadu gaps from prior note.

### FWD — Haaland / Isak / Georginio (not CLD default)

| | Haaland | Isak | Georginio | CLD | Wright |
| --- | ---: | ---: | ---: | ---: | ---: |
| £ | 15.5 | 9.0 | 5.5 | 6.0 | 5.5 |
| Ext / RS | N / 89 | R / 62* | R lean / **75** | N / 94 | N / 70 |
| Flag | IRONMAN | THIN | LIMITED | IRONMAN | NO_PL |

**Georginio fold:** live bench after Welbeck→CHE opens BHA #9. Prefer full 90s before promoting to XI over CLD bridge. CLD still valid if Rutter soft / Conf. rotation.

### Avoid — Anderson

37-start ironman **wrong role** at City. DEFcon haul from pressing mid will not repeat.

---

## Chip path

1. Pre-GW1 unlimited → 15 expected starters.  
2. BB GW2 preferred (Bruno IPS H, LIV NFO H).  
3. WC ~GW4 (United vs City ends sprint).  
4. Save FH / TC — no TC on BB week.

### API chips (822158 @ refresh)

| Chip | Status |
| --- | --- |
| BB (1st half) | Available (`active`) |
| TC (1st half) | **Unavailable** |
| WC / FH | Not on first-half payload — re-check before GW4 |

### User biases

| Bias | Stance vs RoleScore |
| --- | --- |
| Kinsky over Leno | Agree differential — Ext N despite THIN |
| Threat CB (Ballard) | Agree rates; Mitchell also owned — good |
| Bruno captain | Owned + C — agree (RS 98) |
| Georginio BHA #9 | Owned — Ext R lean; confirm minutes |

---

## Squad A — Palmer path (£100.0)

| Pos | Player | Club | £ | Bucket |
| --- | --- | ---: | ---: | --- |
| GKP | Verbruggen | BHA | 4.5 | Keep |
| GKP | Kinsky | TOT | 4.5 | Keep |
| DEF | Maguire | MUN | 5.0 | Rental |
| DEF | N.Williams | NFO | 5.0 | Keep |
| DEF | Mitchell | CRY | 4.5 | Keep |
| DEF | Thomas | COV | 4.0 | BB floor† |
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

**Weak:** no Bruno GW1–2 armband. Live already left this path.

---

## Squad B — Recommended (£100.0)

| Pos | Player | Club | £ | Bucket | RS lean |
| --- | --- | ---: | ---: | --- | --- |
| GKP | Verbruggen | BHA | 4.5 | Keep | 95 |
| GKP | Kinsky | TOT | 4.5 | Keep | 71 |
| DEF | Ballard | SUN | 5.0 | Keep/flex | 74 |
| DEF | N.Williams | NFO | 5.0 | Keep | 92 |
| DEF | Mitchell | CRY | 4.5 | Keep | 84 |
| DEF | O'Shea | IPS | 4.0 | BB floor | 70 |
| DEF | Thomas | COV | 4.0 | BB floor† | 49 |
| MID | B.Fernandes | MUN | 12.0 | Keep | 98 |
| MID | Mbeumo | MUN | 8.0 | Rental | 81 |
| MID | Szoboszlai | LIV | 7.0 | Keep | 84 |
| MID | Ampadu | LEE | 5.5 | Flex | 86 |
| MID | Xhaka | SUN | 5.5 | BB floor | 85 |
| FWD | Haaland | MCI | 15.5 | Keep | 89 |
| FWD | Isak | LIV | 9.0 | Keep | 62* |
| FWD | Calvert-Lewin | LEE | 6.0 | Rental | 94 |
| | **Total** | | **100.0** | | |

†**Thomas kill switch:** Amenda starts → Thomas → van Ewijk £4.0.

### Squad B′ — Live twin (£100.0)

Same as B but **Shaw £4.5** for O'Shea (−£0? wait +£0.5) and **Georginio £5.5** for CLD (−£0.5) → net £0.

| Pos | vs B | £ |
| --- | --- | ---: |
| Shaw replaces O'Shea | +0.5 | 4.5 |
| Georginio replaces CLD | −0.5 | 5.5 |
| | **Net** | **100.0** |

**Prefer B′ while:** Rutter friendlies look locked AND Shaw mins preferred over IPS formation risk. Flip to pure B if Rutter soft or need O'Shea BB minutes.

| Variant | Δ | Total |
| --- | ---: | ---: |
| Maguire for Ballard | £0 | 100.0 if XI locked |
| Ndiaye for Ampadu | +£0.5 | **100.5 invalid** alone |
| Cash for O'Shea | +£0.5 | **100.5 invalid** alone |
| Alt: Ndiaye + Wright (drop CLD/Georginio) | £0 | 100.0 |

---

## Squad C — Wirtz triple if XI locked (£100.0)

| Pos | Players | £ |
| --- | --- | ---: |
| GKP | Verbruggen, Kinsky | 9.0 |
| DEF | Maguire, Ballard, N.Williams, Thomas, O'Shea | 23.0 |
| MID | Bruno 12, Szobo 7, Wirtz 7.5, Ndiaye 6, Xhaka 5.5 | 38.0 |
| FWD | Haaland 15.5, Isak 9, Wright 5.5 | 30.0 |
| | **Total** | **100.0** |

**Kill switch:** Wirtz / Maguire / Ballard fails friendly XI → Squad B/B′.  
Meerkat lists Wirtz in LIV XI — still Iraola-new → confirm.

---

## Live squad 822158

| Pos | Slot | Player | £ | vs B / B′ |
| --- | --- | --- | ---: | --- |
| GKP | XI | Kinsky | 4.5 | Match |
| DEF | XI | Ballard | 5.0 | Match |
| DEF | XI | Thomas | 4.0 | Match† Amenda |
| DEF | XI | Shaw | 4.5 | B′ (B prefers O'Shea) |
| MID | XI | Ampadu | 5.5 | Match |
| MID | XI | Szoboszlai | 7.0 | Match |
| MID | XI | B.Fernandes (C) | 12.0 | Match |
| MID | XI | Mbeumo (VC) | 8.0 | Match |
| MID | XI | Xhaka | 5.5 | Match |
| FWD | XI | Haaland | 15.5 | Match |
| FWD | XI | Isak | 9.0 | Match |
| GKP | Bench | Verbruggen | 4.5 | Match |
| FWD | Bench | Georginio | 5.5 | B′ (B prefers CLD) |
| DEF | Bench | Mitchell | 4.5 | Match |
| DEF | Bench | N.Williams | 5.0 | Match |
| | | **Total** | **100.0** | |

Clubs: 3 MUN · 2 LIV · 2 SUN · 2 BHA. Legal.

### Optional polish → pure Squad B (£0 net)

| Move | Δ £ | Logic |
| --- | ---: | --- |
| Shaw → O'Shea | −0.5 | BB floor / frees budget |
| Georginio → Calvert-Lewin | +0.5 | Ironman LEE bridge if Rutter soft |
| **Net** | **0.0** | |

Or keep B′: promote Georginio to XI when #9 locked; bench Shaw/Thomas as needed.

### Captain on current XV

| GW | C | VC |
| ---: | --- | --- |
| 1 | B.Fernandes (HUL A) or Haaland (BOU H) | Mbeumo / Isak |
| 2 | Bruno (IPS H) | Isak (NFO H) / Haaland |
| 3 | Haaland (COV H) | Isak |
| 4 | WC | — |

---

## Chip calendar

```text
Pre-GW1   Unlimited → Squad B / B′ / C (Wirtz locked)
GW1       No chip. Bruno (HUL A) or Haaland (BOU H).
GW2       BENCH BOOST. Bruno (IPS H). Vice Isak (NFO H).
GW3       Haaland (COV H).
GW4       WILDCARD — sell rentals (see gw4-wildcard note).
```

## GW4 sell / hold

| Sell | Hold |
| --- | --- |
| Maguire if owned, Mbeumo, CLD/Wilson/Ampadu if soft, Wirtz if soft, O'Shea/Thomas if flop, Shaw if CB flux | Haaland, Bruno, Szobo, Isak, N.Williams, Verbruggen, Kinsky if thesis holds, Ballard if mins stick, Georginio if #9 locked |

## Decision tree

```text
Live already ~Squad B′?
├─ YES (current) → polish Thomas/Amenda + Rutter 90s; BB GW2
└─ NO → fund Bruno + Ampadu first

Wirtz locked XI in friendlies?
├─ YES → consider Squad C (3×LIV)
└─ NO → stay B / B′

Rutter full 90s + Welbeck medical clears?
├─ YES → keep Georginio (B′); promote to XI when needed
└─ NO → Georginio → CLD / Wright
```

---

## Bottom line

1. **Live 822158 ≈ Squad B′** — Bruno + Ampadu already owned; Georginio folds BHA #9 thesis onto bench.  
2. Residual gates: **Thomas vs Amenda**, Ballard 90s, Isak fitness, Rutter lock.  
3. Optional: Shaw→O'Shea if wanting pure BB floor / IPS minutes.  
4. BB GW2 · WC ~GW4 (detail in sibling note).  
5. Refresh after every `commands.refresh_data`; re-auth if parquet picks look wrong vs `my_team_822158.json`.

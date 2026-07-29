# FPL 2026/27 — GW4 Wildcard: Chelsea Turn + Liverpool Core

**Date**: 2026-07-29  
**Data stamp**: bootstrap / entry 822158 · fixtures · prices refreshed **2026-07-29 ~11:00 ICT**  
**Status**: WC target squads + price-risk plan — RoleScore-backed · line-sums verified  
**Parent strategy**: [`20260729-bb-then-wc-strategy.md`](20260729-bb-then-wc-strategy.md) (BB GW2 → WC ~GW4)  
**Baseline**: [`20260729-pl-starter-rolescore.md`](20260729-pl-starter-rolescore.md)  
**Also**: [`20260728-gkp-def-budget-ratings.md`](20260728-gkp-def-budget-ratings.md)  
**Entry**: 822158 · live XV £100.0 · bank £0.0 · chips: BB/TC available; WC/FH re-check before GW4  

---

## Verdict

| Decision | Call | Support |
| --- | --- | --- |
| WC week | **GW4 deadline** (activate after GW3) | CHE HUL FDR 2 · MUN MCI FDR 4 · CHE/LIV avg FDR **2.8** vs MUN **3.2** (GW4–8) |
| Spine keep | Haaland · Szoboszlai · Isak* · Palmer | RS 90 / 82 / 67* / 81 · already in live XV |
| Sell at WC | **Mbeumo** (and other United rentals if owned) | Soft fixtures end; 13.5% EO · not the keep-Bruno case |
| Bruno | **Keep if owned** / acquire on optimal path | RS **100** · 0.68 xGI90 · 35 starts · exception to United fade |
| Chelsea add | Palmer (owned) + **Rogers** on blend path | CHE FDR run; Rogers 32.9% EO = price-riser risk |
| LIV triple | Keep on blend only if **Wirtz XI locked** | Wirtz RS 65 R · 0.45 xGI90 / thr90 25.2 · XI-gated |
| Bank | **£0.5m** unspent on both templates | Hedge five net £0.1 adverse price moves |
| Default | **Optimal** = 1 CHE / 2 LIV · **Blend** = 2 CHE / 3 LIV | User bias = blend |

\*Isak fitness-gated (THIN LIV sample).

---

## Why GW4 (not GW5)

Chip path from parent note: Unlimited → BB GW2 → **WC ~GW4**. Trigger = United sprint ends vs City.

| Club | GW4 | GW5 | GW6 | GW7 | GW8 | Avg FDR |
| --- | --- | --- | --- | --- | ---: | ---: |
| **Chelsea** | H Hull (2) | A Brentford (3) | H Bournemouth (3) | A Everton (3) | H Spurs (3) | **2.8** |
| **Liverpool** | H Fulham (2) | A Bournemouth (3) | H Man City (4) | A Brentford (3) | H Brighton (2) | **2.8** |
| **Man Utd** | H Man City (4) | A Fulham (3) | H Spurs (3) | A Leeds (3) | H Bournemouth (3) | **3.2** |

Source: `commands.fdr_report` · `data/processed/fixtures.parquet` · GW4–8 · lower = easier.

**Why not slip to GW5?** GW4 is the clean swing: Chelsea open vs Hull at home while United host City. Waiting one more week burns the Hull fixture and forces a hit/FT plan into a worse United slate without gaining a clearer Chelsea shape read than friendlies + GW1–3 already provide.

**Activate** after the final GW3 kickoff; **lock** after last-minute XI / fitness news before GW4 deadline.

---

## Price-change risk (how to not miss targets)

FPL selling price captures ~half of rises. If Rogers / Palmer / template assets rise while you wait, a tight WC rebuild can land **£0.5–0.9 short**.

### Evidence (this season so far)

| Snapshot | Captured (UTC) | Movement on named targets |
| --- | --- | --- |
| 1 | 2026-07-25 18:58 | — |
| 2 | 2026-07-27 11:13 | none |
| 3 | 2026-07-29 04:01 | none |

`commands.price_report` · three GW1 snapshots · Palmer / Rogers / Wirtz / Szoboszlai / Isak / Mbeumo / Bruno / Haaland all **£0.0** change since season start. **No trend yet** — ownership / transfer volume still the leading indicator.

### Ownership (risers to respect)

| Player | Club | £ | % owned | Role in plan |
| --- | ---: | ---: | ---: | --- |
| Rogers | CHE | 7.5 | **32.9** | Highest EO among CHE attackers not Palmer — **buy early on WC** |
| B.Fernandes | MUN | 12.0 | 48.7 | Template premium — own or fund deliberately |
| Szoboszlai | LIV | 7.0 | 47.1 | Keep |
| Haaland | MCI | 15.5 | 75.2 | Keep |
| Palmer | CHE | 9.5 | 13.2 | Keep (already owned live) |
| Mbeumo | MUN | 8.0 | 13.5 | Planned sell |
| Wirtz | LIV | 7.5 | 10.7 | Keep only if XI locked |
| Isak | LIV | 9.0 | 11.5 | Keep if fit |

### Operating rules

1. On WC activation: order buys **Rogers → Palmer (if missing) → Isak/Wirtz confirmation** before luxury DEF upgrades.  
2. Leave **£0.5m bank** — not empty ITB as the whole hedge; ownership of targets is still #1.  
3. Do **not** force a third Chelsea player until Alonso shape / WB minutes clear (club clarity = Low in RoleScore note).  
4. If only one move is needed (e.g. Mbeumo → Rogers) and all XI gates pass, prefer **1 FT** over burning WC solely for that swap — WC is for multi-slot rebuild + bank structure.  
5. Re-run `uv run python -m commands.price_report` after each refresh in GW1–3.

---

## Live squad gap (822158 → WC)

| Slot | Live | Optimal WC | Blend WC |
| --- | --- | --- | --- |
| GKP | Kinsky + Verbruggen | Verbruggen + Steele (−0.5) | Match (dual starters) |
| DEF | Ballard, N.Williams, Shaw, Kayode, Thomas | Cash, Mitchell, Kayode, O'Shea, Thomas | Match live (keep Ballard thesis) |
| MID | Palmer, Szobo, **Wirtz**, **Mbeumo**, Xhaka | Bruno, Palmer, Szobo, Ampadu, Xhaka | Palmer, Wirtz, Szobo, **Rogers**, Xhaka |
| FWD | Haaland, Isak, CLD | Haaland, Isak, Wright | Match (keep CLD bridge) |

**Minimum blend move:** Mbeumo £8.0 → Rogers £7.5 · frees £0.5 · becomes the bank cushion.

---

## Plan A — Optimal (role + fixture)

**£99.5 · bank £0.5 · 1 Chelsea · 2 Liverpool · 0 United (Bruno kept if acquired)**

| Pos | Player | Club | £ | Bucket | RS / key rates | Why |
| --- | --- | ---: | ---: | --- | --- | --- |
| GKP | Verbruggen | BHA | 4.5 | Keep | 95 · 38 starts | Ironman dual-lock half |
| GKP | Steele | BHA | 4.0 | Enabler | — | Bench; frees £0.5 vs second £4.5 |
| DEF | Cash | AVL | 4.5 | Keep | 87 · 3G3A | Best G/A among £4.5 locked FBs |
| DEF | Mitchell | CRY | 4.5 | Keep | 84 · thr90 6.7 | Value ironman WB |
| DEF | Kayode | BRE | 4.5 | Keep | 87 · 37 starts | Minutes + DEFcon |
| DEF | O'Shea | IPS | 4.0 | Floor | 70 N | BB/WC floor · not Diop |
| DEF | Thomas | COV | 4.0 | Floor† | 49 | Amenda kill switch → van Ewijk |
| MID | B.Fernandes | MUN | 12.0 | Keep | **100** · xGI90 **0.68** | Premium exception to United fade |
| MID | Palmer | CHE | 9.5 | Keep | 81 · xGI90 0.60 | CHE fixture engine |
| MID | Szoboszlai | LIV | 7.0 | Keep | 82 · 36 starts | Default LIV mid |
| MID | Ampadu | LEE | 5.5 | Flex | 86 N | Ironman DM + DC · not Mainoo |
| MID | Xhaka | SUN | 5.5 | Floor | 85 | BB floor continuity |
| FWD | Haaland | MCI | 15.5 | Keep | 90 | Captain magnet |
| FWD | Isak | LIV | 9.0 | Keep* | 67* · xGI90 0.35 | Fitness gate |
| FWD | Wright | COV | 5.5 | Floor | 70 N | Champ pens · £100 path |
| | **Total** | | **99.5** | | | |

Math: GKP 8.5 + DEF 21.5 + MID 39.5 + FWD 30.0 = **99.5**.

### Why this over forcing Chelsea triple / LIV triple

- Bruno’s rates beat any second United attacker; Mbeumo is the rental to cut.  
- Palmer alone is enough CHE attack exposure until WB/CB minutes settle (James EO 8.1% but volatility; Chalobah 2.1%).  
- Szobo + Isak = LIV double default; Wirtz deferred until Ext moves R→N in friendlies (parent decision tree).

---

## Plan B — Blend (user: Chelsea fund + 3 Liverpool)

**£99.5 · bank £0.5 · 2 Chelsea · 3 Liverpool · keep Kinsky / Ballard bias**

| Pos | Player | Club | £ | Bucket | RS / key rates | Why |
| --- | --- | ---: | ---: | --- | --- | --- |
| GKP | Kinsky | TOT | 4.5 | Keep | 66 N THIN | User differential · De Zerbi No.1 |
| GKP | Verbruggen | BHA | 4.5 | Keep | 95 | Dual playing GK |
| DEF | Ballard | SUN | 5.0 | Keep* | 74 · thr90 **15.5** | Threat-CB · fitness gate |
| DEF | N.Williams | NFO | 5.0 | Keep | 87 | Glasner WB |
| DEF | Shaw | MUN | 4.5 | Flex | 86 · 38 starts | Safer mins than Maguire rental |
| DEF | Kayode | BRE | 4.5 | Keep | 87 | Minutes floor |
| DEF | Thomas | COV | 4.0 | Floor† | 49 | Same Amenda kill switch |
| MID | Palmer | CHE | 9.5 | Keep | 81 · 0.60 xGI90 | Owned live |
| MID | Rogers | CHE | 7.5 | **Buy** | N lean · 32.9% EO | Funds from Mbeumo · fixture turn |
| MID | Wirtz | LIV | 7.5 | Keep* | 65 R · **0.45** xGI90 · thr90 **25.2** | Triple only if XI locked |
| MID | Szoboszlai | LIV | 7.0 | Keep | 82 | Locked LIV mid |
| MID | Xhaka | SUN | 5.5 | Floor | 85 | Enabler |
| FWD | Haaland | MCI | 15.5 | Keep | 90 | Keep |
| FWD | Isak | LIV | 9.0 | Keep* | 67* | Completes triple |
| FWD | Calvert-Lewin | LEE | 6.0 | Bridge | 94 · thr90 33.9 | Early Leeds · sell later if needed |
| | **Total** | | **99.5** | | | |

Math: GKP 9.0 + DEF 23.0 + MID 37.0 + FWD 30.5 = **99.5**.

### Material WC move

| Out | £ | In | £ | Δ | Logic |
| --- | ---: | --- | ---: | ---: | --- |
| Mbeumo | 8.0 | Rogers | 7.5 | −0.5 | Sell United rental → Chelsea fixture asset; bank +0.5 |

Optional later (same WC or FT): CLD → Wright / Ndiaye if Leeds form soft; Shaw → Mitchell if United CB/LB flux.

### Accept vs Optimal

| Trade-off | Cost | User gain |
| --- | --- | --- |
| No Bruno | Lose 0.68 xGI90 captain engine | Keep Palmer + Rogers CHE double |
| Wirtz kept | RS 65 R + new-manager risk | 3 LIV + elite per-90 rates |
| Kinsky dual | Sample THIN vs Leno path | Differential CS thesis |
| Ballard | Fitness / Europa rotation | thr90 elite among CBs |

---

## Kill switches (fail → replace, don’t protect club count)

| Gate | Fail action | Why |
| --- | --- | --- |
| Wirtz not in decisive friendly / GW1–3 XI | Wirtz → Ampadu (−£2.0 spare) or → Enzo if CHE locked | Rates ≠ minutes |
| Isak soft / injured | Isak → João Pedro £7.5 or Watkins path | THIN sample already |
| Ballard not full 90 | Ballard → Mukiele £5.5 (fund −£0.5 elsewhere) or Hume £4.5 | thr90 useless without mins |
| Thomas loses to Amenda | Thomas → van Ewijk £4.0 | Same budget · safer starts |
| Rogers EO spike + price rise before WC | Own him earlier via FT in GW3 if free | 32.9% EO = primary price risk |

---

## Captain / chip notes (around WC)

| GW | Context | Armband lean |
| ---: | --- | --- |
| 1–3 | Pre-WC · BB GW2 | Bruno if owned · else Haaland / Isak |
| 4 | WC week · CHE HUL · LIV FUL | Haaland or Palmer/Rogers · **not** United |
| 5+ | Post-WC settle | Haaland default · CHE attackers while FDR ≤3 |

Save FH / TC. Do not TC on BB week (parent strategy).

---

## Decision tree

```text
WC timing
├─ After GW3 + before GW4 deadline → YES (default)
└─ Slip GW5 only if CHE shape chaos OR multiple soft XI fails in GW4

Structure
├─ Priority = RoleScore + minutes → Plan A (Optimal)
└─ Priority = CHE double + LIV triple + Kinsky/Ballard → Plan B (Blend)
      └─ Wirtz XI fail? → drop to LIV double (Szobo+Isak) + Ampadu

Price
├─ Own Rogers/Palmer before chasing DEF upgrades
└─ Always leave £0.5 unless a fifth starter requires the penny
```

---

## Bottom line

1. **Aim WC for GW4** — Chelsea/Liverpool FDR **2.8** vs United **3.2**; United vs City is the natural sell trigger.  
2. **Price hedge** = own high-EO targets (esp. Rogers 32.9%) + **£0.5 bank**; current snapshots show £0 movement — risk is forward, not historical.  
3. **Optimal** = Bruno + Palmer + LIV double + £99.5 structure.  
4. **Blend** = keep live LIV triple + Palmer, **Mbeumo → Rogers**, retain Kinsky/Ballard, same £99.5.  
5. Refresh after every `commands.refresh_data`; re-verify Wirtz / Isak / Ballard / Thomas gates before lock.

---

## Redo

```bash
uv run python -m commands.refresh_data
uv run python -m commands.fdr_report --start_gw 4 --horizon 5
uv run python -m commands.price_report
```

Then update prices, EO, and kill-switch status in this file’s date stamp.

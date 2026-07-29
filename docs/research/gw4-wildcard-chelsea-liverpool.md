# FPL 2026/27 — GW4 Wildcard: Chelsea Turn + Liverpool Core

**Updated**: 2026-07-29T22:22:00+07:00  
**Data stamp**: bootstrap / entry **822158** · fixtures · prices refreshed **2026-07-29 ~22:17 ICT**  
**Status**: WC target squads + price-risk plan — RoleScore-backed · line-sums verified  
**Parent strategy**: [`bb-then-wc-strategy.md`](bb-then-wc-strategy.md) (BB GW2 → WC ~GW4)  
**Baseline**: [`pl-starter-rolescore.md`](pl-starter-rolescore.md)  
**Also**: [`gkp-def-budget-ratings.md`](gkp-def-budget-ratings.md)  
**Entry**: 822158 · live XV £100.0 · bank £0.0 · chips: BB available; TC unavailable; WC/FH re-check before GW4  

## Agent Prompt

```
Full redo docs/research/gw4-wildcard-chelsea-liverpool.md

1. uv run python -m commands.refresh_data
2. uv run python -m commands.fdr_report --start_gw 4 --horizon 5
3. uv run python -m commands.price_report
4. Re-read bb-then-wc-strategy.md + pl-starter-rolescore.md. Rebuild Optimal vs Blend WC templates at £99.5 bank £0.5. Update EO from selected_by_percent. Kill switches from parent.
5. Update live gap from my_team_822158.json (not stale parquet if mismatch).
6. Update **Updated** + **Data stamp**. Keep slug filename + sibling links. Delete .tmp/agent/ when done.
```

---

## Verdict

| Decision | Call | Support |
| --- | --- | --- |
| WC week | **GW4 deadline** (activate after GW3) | CHE HUL FDR 2 · MUN MCI FDR 4 · CHE/LIV avg FDR **2.8** vs MUN **3.2** (GW4–8) |
| Spine keep | Haaland · Szoboszlai · Isak* · Bruno (owned) | RS 89 / 84 / 62* / 98 |
| Sell at WC | **Mbeumo** (United rental) | Soft fixtures end; EO 13.6% |
| Bruno | **Keep** (already owned) | RS **98** · 0.68 xGI90 · 35 starts |
| Chelsea add | **Rogers** on blend path (Palmer optional) | CHE FDR run; Rogers EO **32.7%** = price-riser risk |
| LIV triple | Blend only if **Wirtz XI locked** | Wirtz RS 67 R · Meerkat XI; still confirm |
| Bank | **£0.5m** unspent on both templates | Hedge adverse £0.1 moves |
| Default | **Optimal** = 1 CHE / 2 LIV · **Blend** = 2 CHE / 3 LIV | User bias = blend |

\*Isak fitness-gated (THIN LIV sample).

---

## Why GW4 (not GW5)

Chip path from parent: Unlimited → BB GW2 → **WC ~GW4**. Trigger = United sprint ends vs City.

| Club | GW4 | GW5 | GW6 | GW7 | GW8 | Avg FDR |
| --- | --- | --- | --- | --- | --- | ---: |
| **Chelsea** | H Hull (2) | A Brentford (3) | H Bournemouth (3) | A Everton (3) | H Spurs (3) | **2.8** |
| **Liverpool** | H Fulham (2) | A Bournemouth (3) | H Man City (4) | A Brentford (3) | H Brighton (2) | **2.8** |
| **Man Utd** | H Man City (4) | A Fulham (3) | H Spurs (3) | A Leeds (3) | H Bournemouth (3) | **3.2** |

Source: `commands.fdr_report` · `fixtures.parquet` · GW4–8 · lower = easier · refreshed 2026-07-29.

**Why not slip to GW5?** GW4 is the clean swing: Chelsea open vs Hull at home while United host City. Waiting burns Hull and forces hits into a worse United slate.

**Activate** after final GW3 kickoff; **lock** after last-minute XI / fitness news before GW4 deadline.

---

## Price-change risk

FPL selling price captures ~half of rises. Tight WC rebuild can land **£0.5–0.9 short** if Rogers / template assets rise while you wait.

### Evidence (this season so far)

| Snapshot | Captured (UTC) | Movement on named targets |
| --- | --- | --- |
| Prior | 2026-07-25 → 2026-07-29 | none on Palmer / Rogers / Wirtz / Szobo / Isak / Mbeumo / Bruno / Haaland |
| This refresh | 2026-07-29 ~15:17 UTC | still **£0.0** change since season start |

`commands.price_report` · **No trend yet** — ownership / transfer volume still the leading indicator.

### Ownership (risers to respect)

| Player | Club | £ | % owned | Role in plan |
| --- | ---: | ---: | ---: | --- |
| Rogers | CHE | 7.5 | **32.7** | Highest EO among CHE attackers not Palmer — **buy early on WC** |
| B.Fernandes | MUN | 12.0 | 48.7 | Keep (owned) |
| Szoboszlai | LIV | 7.0 | 47.3 | Keep |
| Haaland | MCI | 15.5 | 75.2 | Keep |
| João Pedro | CHE | 7.5 | 52.7 | Blend / Isak fail alt |
| Palmer | CHE | 9.5 | 13.2 | Optimal CHE engine if acquired |
| Mbeumo | MUN | 8.0 | 13.6 | Planned sell |
| Wirtz | LIV | 7.5 | 10.6 | Keep only if XI locked |
| Isak | LIV | 9.0 | 11.4 | Keep if fit |
| Georginio | BHA | 5.5 | 0.7 | Owned — hold if #9 locked |

### Operating rules

1. On WC activation: order buys **Rogers → Palmer (if missing) → Isak/Wirtz confirmation** before luxury DEF upgrades.  
2. Leave **£0.5m bank**.  
3. Do **not** force a third Chelsea until Alonso shape / WB minutes clear.  
4. If only Mbeumo → Rogers needed and XI gates pass, prefer **1 FT** over burning WC solely for that swap.  
5. Re-run `uv run python -m commands.price_report` after each refresh in GW1–3.

---

## Live squad gap (822158 → WC)

Live (authenticated): Kinsky, Ballard, Thomas, Shaw, Ampadu, Szobo, **Bruno (C)**, Mbeumo (VC), Xhaka, Haaland, Isak | Verbruggen, **Georginio**, Mitchell, N.Williams.

| Slot | Live | Optimal WC | Blend WC |
| --- | --- | --- | --- |
| GKP | Kinsky + Verbruggen | Verbruggen + Steele (−0.5) | Match (dual starters) |
| DEF | Ballard, Thomas, Shaw, Mitchell, N.Williams | Cash, Mitchell, Kayode, O'Shea, Thomas | Match live (keep Ballard thesis) |
| MID | Bruno, Szobo, Ampadu, **Mbeumo**, Xhaka | Bruno, Palmer, Szobo, Ampadu, Xhaka | Bruno*, Palmer, Szobo, **Rogers**, Wirtz* |
| FWD | Haaland, Isak, Georginio | Haaland, Isak, Wright | Match (keep Georginio if #9 locked) |

\*Blend may drop Bruno to fund CHE+LIV triple — see Plan B trade-offs. Live already owns Bruno → Optimal path cheaper.

**Minimum blend move from live:** Mbeumo £8.0 → Rogers £7.5 · frees £0.5 bank.

---

## Plan A — Optimal (role + fixture)

**£99.5 · bank £0.5 · 1 Chelsea · 2 Liverpool · Bruno kept**

| Pos | Player | Club | £ | Bucket | RS / key rates | Why |
| --- | --- | ---: | ---: | --- | --- | --- |
| GKP | Verbruggen | BHA | 4.5 | Keep | 95 · 38 starts | Ironman dual-lock half |
| GKP | Steele | BHA | 4.0 | Enabler | — | Bench; frees £0.5 vs second £4.5 |
| DEF | Cash | AVL | 4.5 | Keep | 87 · 3G3A | Best G/A among £4.5 locked FBs |
| DEF | Mitchell | CRY | 4.5 | Keep | 84 · thr90 6.7 | Value ironman WB |
| DEF | Kayode | BRE | 4.5 | Keep | 87 · 37 starts | Minutes + DEFcon |
| DEF | O'Shea | IPS | 4.0 | Floor | 70 N | Not Diop |
| DEF | Thomas | COV | 4.0 | Floor† | 49 | Amenda → van Ewijk |
| MID | B.Fernandes | MUN | 12.0 | Keep | **98** · xGI90 **0.68** | Premium exception to United fade |
| MID | Palmer | CHE | 9.5 | Buy | 83 · xGI90 0.60 | CHE fixture engine |
| MID | Szoboszlai | LIV | 7.0 | Keep | 84 · 36 starts | Default LIV mid |
| MID | Ampadu | LEE | 5.5 | Flex | 86 N | Owned live |
| MID | Xhaka | SUN | 5.5 | Floor | 85 | Continuity |
| FWD | Haaland | MCI | 15.5 | Keep | 89 | Captain magnet |
| FWD | Isak | LIV | 9.0 | Keep* | 62* · xGI90 0.35 | Fitness gate |
| FWD | Wright | COV | 5.5 | Floor | 70 N | Champ pens · £100 path |
| | **Total** | | **99.5** | | | |

Math: GKP 8.5 + DEF 21.5 + MID 39.5 + FWD 30.0 = **99.5**.

### Material moves from live → Optimal

| Out | £ | In | £ | Δ | Logic |
| --- | ---: | --- | ---: | ---: | --- |
| Kinsky | 4.5 | Steele | 4.0 | −0.5 | Bank cushion (or keep Kinsky bias → see Blend) |
| Mbeumo | 8.0 | Palmer | 9.5 | +1.5 | CHE engine |
| Ballard / Shaw / Georginio reshuffle | — | Cash / Kayode / O'Shea / Wright | — | Fund Palmer + structure | |

Exact FT/WC set depends on price moves GW1–3 — recompute on activation.

---

## Plan B — Blend (Chelsea fund + 3 Liverpool)

**£99.5 · bank £0.5 · 2 Chelsea · 3 Liverpool · keep Kinsky / Ballard / Georginio bias**

| Pos | Player | Club | £ | Bucket | RS / key rates | Why |
| --- | --- | ---: | ---: | --- | --- | --- |
| GKP | Kinsky | TOT | 4.5 | Keep | 71 N THIN | User differential |
| GKP | Verbruggen | BHA | 4.5 | Keep | 95 | Dual playing GK |
| DEF | Ballard | SUN | 5.0 | Keep* | 74 · thr90 **15.5** | Threat-CB |
| DEF | N.Williams | NFO | 5.0 | Keep | 92 | Glasner WB |
| DEF | Shaw | MUN | 4.5 | Flex | 86 · 38 starts | Safer mins |
| DEF | Mitchell | CRY | 4.5 | Keep | 84 | Value |
| DEF | Thomas | COV | 4.0 | Floor† | 49 | Amenda kill switch |
| MID | B.Fernandes | MUN | 12.0 | Keep | 98 | Owned — hard to cut |
| MID | Rogers | CHE | 7.5 | **Buy** | N · EO 32.7% | Funds from Mbeumo |
| MID | Szoboszlai | LIV | 7.0 | Keep | 84 | Locked LIV mid |
| MID | Wirtz | LIV | 7.5 | Buy* | 67 R · **0.45** xGI90 | Triple only if XI locked |
| MID | Xhaka | SUN | 5.5 | Floor | 85 | Enabler |
| FWD | Haaland | MCI | 15.5 | Keep | 89 | Keep |
| FWD | Isak | LIV | 9.0 | Keep* | 62* | Completes triple |
| FWD | Georginio | BHA | 5.5 | Keep* | 75 R lean | Owned #9 thesis |
| | **Total** | | **99.5** | | | |

Math check: GKP 9.0 + DEF 23.0 + MID 39.5 + FWD 30.0 = **101.5** — **over**.  

**Fund fix (pick one):**
- Drop Bruno → Palmer path was Plan A; for Blend without Bruno: replace Bruno 12 + Xhaka 5.5 with Palmer 9.5 + Rogers already in → need Ampadu cut too.  
- **Practical Blend from live (legal £99.5):** keep Bruno; **do not** force Wirtz triple in same XV — use LIV double + Rogers.

### Plan B′ — Practical blend from live (£99.5)

Keep Bruno + LIV double; add Rogers; bank £0.5.

| Pos | Players | £ |
| --- | --- | ---: |
| GKP | Kinsky, Verbruggen | 9.0 |
| DEF | Ballard, N.Williams, Shaw, Mitchell, Thomas | 23.0 |
| MID | Bruno 12, Rogers 7.5, Szobo 7, Ampadu 5.5, Xhaka 5.5 | 37.5 |
| FWD | Haaland 15.5, Isak 9, Georginio 5.5 | 30.0 |
| | **Total** | **99.5** |

Move: **Mbeumo → Rogers** (−0.5). Optional later: Ampadu → Wirtz (+2.0) only if XI locked and funded elsewhere.

### Accept vs Optimal

| Trade-off | Cost | User gain |
| --- | --- | --- |
| No Palmer (B′) | Lose 0.60 xGI90 CHE premium | Keep Bruno + Rogers CHE exposure |
| Wirtz deferred | Miss triple upside | Avoid RS 67 R minutes risk |
| Kinsky dual | Sample THIN | Differential CS thesis |
| Ballard / Georginio | Fitness / Conf. risk | thr90 / #9 upside |

---

## Kill switches (fail → replace)

| Gate | Fail action | Why |
| --- | --- | --- |
| Wirtz not in decisive XI | Skip triple; keep Ampadu | Rates ≠ minutes |
| Isak soft / injured | Isak → João Pedro £7.5 or Watkins path | THIN sample already |
| Ballard not full 90 | Ballard → Mukiele £5.5 (fund −£0.5) or Hume £4.5 | thr90 useless without mins |
| Thomas loses to Amenda | Thomas → van Ewijk £4.0 | Same budget · safer starts |
| Georginio loses #9 | Georginio → Wright / CLD | Conf. / Kostoulas |
| Rogers EO spike + rise before WC | Own earlier via FT in GW3 if free | 32.7% EO = primary price risk |

---

## Captain / chip notes (around WC)

| GW | Context | Armband lean |
| ---: | --- | --- |
| 1–3 | Pre-WC · BB GW2 | **Bruno** (owned) · else Haaland / Isak |
| 4 | WC week · CHE HUL · LIV FUL | Haaland or Palmer/Rogers · **not** United |
| 5+ | Post-WC settle | Haaland default · CHE attackers while FDR ≤3 |

Save FH / TC. Do not TC on BB week (parent). TC currently **unavailable** on entry — re-check.

---

## Decision tree

```text
WC timing
├─ After GW3 + before GW4 deadline → YES (default)
└─ Slip GW5 only if CHE shape chaos OR multiple soft XI fails in GW4

Structure
├─ Live owns Bruno → prefer Optimal or Plan B′ (Rogers add)
├─ Priority = RoleScore + minutes → Plan A (Optimal)
└─ Priority = CHE + Kinsky/Ballard/Georginio → Plan B′
      └─ Wirtz XI locked + funded? → add triple carefully

Price
├─ Own Rogers before chasing DEF upgrades
└─ Always leave £0.5 unless a fifth starter requires the penny
```

---

## Bottom line

1. **Aim WC for GW4** — Chelsea/Liverpool FDR **2.8** vs United **3.2**.  
2. **Price hedge** = own Rogers (EO 32.7%) + **£0.5 bank**; snapshots still £0 movement.  
3. **Live already holds Bruno** — WC is mostly Mbeumo→Rogers (+ structure polish), not a full mid rebuild.  
4. **Plan B′** = practical blend from live at £99.5.  
5. Refresh after every `commands.refresh_data`; re-verify Wirtz / Isak / Ballard / Thomas / Rutter gates before lock.

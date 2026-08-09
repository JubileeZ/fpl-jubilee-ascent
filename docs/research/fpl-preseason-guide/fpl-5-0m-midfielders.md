# FPL 2026/27: Best £5.0m Midfielders

**Updated**: 2026-08-09T17:55:00+07:00  
**Data stamp**: Fantasy Football Scout article published 2026-08-05 (modified 2026-08-05); accessed 2026-08-09; cross-checked against expected-role-gw1-5.md and fpl-summer-transfers.md  
**Season**: 2026/27  
**Status**: Active  
**Purpose**: Assess £5.0m budget midfielders for FPL 2026/27 squad structure, Bench Boost enablers, attacking value, and Defensive Contribution (DefCon) reliability  
**Scope**: All 89 midfielders priced at £5.0m in FPL 2026/27 across all 20 Premier League clubs  
**Related**: [Pre-season guide](fpl-preseason-guide.md) · [£4.5m midfielders](fpl-4-5m-midfielders.md) · [£6.0m midfielders](fpl-6-0m-midfielders.md) · [£6.5m–£7.0m midfielders](fpl-6-5m-7-0m-midfielders.md) · [£7.5m+ midfielders](fpl-7-5m-midfielders.md) · [Summer transfers](fpl-summer-transfers.md)

> Note revision created 2026-08-09 from Fantasy Football Scout full price-bracket review. Primary article published 2026-08-05. Source claims cross-checked with expected-role-gw1-5.md and fpl-summer-transfers.md.

## Sources

- **Primary**: [Best £5.0m midfielders for FPL 2026/27: All 89 assessed — Fantasy Football Scout](https://www.fantasyfootballscout.co.uk/2026/08/05/best-5-0m-midfielders-for-fpl-2026-27-all-89-assessed) — published 2026-08-05; accessed 2026-08-09; role: comprehensive £5.0m midfielder analysis (all 89 players), Opta xGI / DefCon rates, and club depth assessments
- **Cross-check**: [Expected Role GW1–5](../gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.md) — updated 2026-08-06; role: starter status, minutes expectations, availability overlays
- **Cross-check**: [Confirmed Summer Transfers](fpl-summer-transfers.md) — updated 2026-08-09; role: confirmed transfer moves (Norgaard, Lukic, Bamba, Morita, Schlager, Steur)

**Source boundary**: Source claims cross-checked against internal project notes. No live FPL API refresh or solver optimization run performed in this note.

## Agent Prompt

```text
Full redo docs/research/fpl-preseason-guide/fpl-5-0m-midfielders.md

1. Re-read source URL using Playwright headless browser rendering (`wait_until='domcontentloaded'`).
2. Confirm title, author, publication/update date, prices, roles, and quoted statistics.
3. Extract full text, 20-club analysis table, and statistical tables for all covered £5.0m midfielders.
4. Transcribe 100% of Opta statistical images (xGI per minute, DefCons per 90, and player DefCon rates) into Markdown tables.
5. Keep Source synthesis strictly separate from Project interpretation.
6. Update Updated ISO timestamp, Data stamp, Sources, Findings, Decision, and Risks.
7. Run pre-commit gate checks (`uv run ruff check .`, `uv run pytest`, `bash tests/verify.sh`); delete `.tmp/agent/` scratch files before finishing.
```

## Method

**Method type**: Source synthesis / price bracket analysis & cross-check audit

**Inputs**:
- Fantasy Football Scout article (`best-5-0m-midfielders-for-fpl-2026-27-all-89-assessed`)
- Expected Role GW1–5 note (`expected-role-gw1-5.md`)
- Confirmed Summer Transfers register (`fpl-summer-transfers.md`)

**Procedure**:
1. Extract club-by-club analysis for all 89 players across all 20 Premier League clubs.
2. Transcribe Opta statistical images: Minutes per Expected Goal Involvement (xGI) and DefCons per 90 minutes.
3. Categorize £5.0m midfielders into Attacking Midfielders/Wingers, Defensive Contribution Anchors, Bench Boost Targets, and Non-Starters/Avoids.
4. Record source synthesis and project decision rules.

**Definitions and assumptions**:
- **£5.0m MID**: Midfielders priced exactly at £5.0m in FPL 2026/27.
- **DefCon**: Defensive Contribution points awarded under 2025/26+ FPL scoring matrix (tackles, interceptions, clearances, blocks, ball recoveries).

## Source synthesis

### Club-by-Club Assessment: All 89 £5.0m Midfielders

| Player(s) | Club | Scout Assessment & Minutes Outlook |
|---|---|---|
| Norgaard | ARS | Transfer to Everton imminent. Would be an FPL non-starter at Arsenal, but high appeal at Everton after posting the 2nd-best DefCon success rate (50%) of any FPL midfielder at Brentford in 2024/25. |
| Bogarde, Barkley, Kamara, Onana, Iling Jr, Alysson | AVL | Iling Jr has had 4 loan spells away; Alysson awaits first PL start. Onana out injured for months; Bogarde & Barkley managed only 18 league starts combined in 2025/26. Kamara is best bet for regular minutes post-injury, but 9.43 DefCons/90 lacks appeal. |
| Cook, Gannon-Doak, Adams, Brooks, Christie, Toth, Adli | BOU | Cook, Adams, Christie, Toth locked in fierce battle for 2 central slots. Cook posted best DefCon rate in article (14.03/90 in 2025/26), but European rotation threatens starts. Christie suspended GW1. On flanks, Gannon-Doak, Brooks, Adli sit behind Tavernier (£6.0m) and Rayan (£6.5m); Gannon-Doak impressed in pre-season. |
| Janelt, Carvalho, Milambo, Yarmoliuk, Dasilva | BRE | Yarmoliuk and Janelt averaged >11.0 DefCons/90 in 2025/26, but arrival of Mamadou Sangare (£5.5m) and presence of Mathias Jensen (£5.5m) cloud minutes. Carvalho, Milambo, Dasilva recovering from major injuries. |
| Gomez, Baleba, Yohanna, Buonanotte | BHA | Buonanotte out of favor with Hurzeler. Yohanna (18yo arrival) will be integrated slowly. Baleba posted 11.22 DefCons/90 (down from previous seasons). **Diego Gomez** is the standout attacking option: started 22 of last 24 PL matches when fit; Kaoru Mitoma's injury secures his RW starting spot early. |
| Lavia | CHE | Injury-prone (15 league starts in 3 seasons); future uncertain and midfield reinforcement expected if Enzo Fernandez moves. |
| Onyeka, Grimes, Rudoni, Sakamoto, Eccles | COV | Four could start GW1 (Eccles is backup). Sakamoto faces competition from Loum Tchaouna (£5.5m). Rudoni (13 returns in 30 apps in 2025/26) recovering from shoulder surgery. **Matt Grimes** and **Frank Onyeka** helm midfield: Grimes had team-best 86 key passes + set-pieces, 9.6 DefCons/90 in Championship. |
| Lerma, Kamada, Devenny, Esse, Franca, Doucoure, Rak-Sakyi | CRY | Franca, Esse, Rak-Sakyi loaned last season. Lerma, Kamada, Doucoure battle Will Hughes (£4.5m) and Adam Wharton (£5.5m) for 2 spots under Pierre Sage. Doucoure back fit (averaged >12.0 DefCons/90 in preceding 3 seasons). |
| Iroegbunam, Armstrong, Alcaraz, Rohl | EVE | Hackney (£5.5m) and Norgaard arrivals limit Iroegbunam. **Merlin Rohl** started on right flank in final 4 games of 2025/26 and scored in pre-season; one to monitor. |
| Berge, Cairney, Lukic | FUL | Central competition with Alex Iwobi used centrally in pre-season; Lukic linked with exit (transferred to Ipswich 8 Aug). Low DefCon output. |
| Belloumi, Millar, Omur, Kamara, Akintola, Morita | HUL | Massive overhaul under Jakirovic. Hidemasa Morita arrived on free and offers DefCon potential if starting. Belloumi and Millar may start early on flanks before new arrivals bed in. |
| Nunez, Matusiwa, Burns, Ogbene, Szmodics, Mehmeti | IPS | Szmodics/Ogbene/Burns departing/departed. Mehmeti inconsistent. **Azor Matusiwa** made 45 starts in 2025/26 and averaged 11.75 DefCons/90, but carries a minor injury concern for GW1; Florentino Luis (£16m) arrival adds competition/pairing. |
| Longstaff, Gelhardt, Gnonto, James, Gruev, Tanaka | LEE | Gruev injured. Longstaff (10 starts) and Tanaka (14 starts) unnailed; Harry Wilson arrival and Anton Stach playing deeper affects Tanaka. Gnonto (4 starts) and James (6 starts) fringe; Gelhardt likely loaned. |
| Nyoni, Bajcetic, Koumas | LIV | Fringe youth prospects; negligible GW1 starter chance. |
| Echeverri, Phillips, Monga | MCI | Minimal first-team starting prospects. |
| Andrey Santos, Ugarte, J Fletcher, Lacey, Collyer | MUN | Ugarte out long term. Youth trio will recede as seniors return. **Andrey Santos** is standout: 12.85 DefCons/90 at Strasbourg as deep-lying pivot (vs 8.84 when pushed forward at Chelsea); likely starter at base of United midfield for GW1. |
| Ramsey, Willock, Steur, Bamba | NEW | Managerless and unsettled. Young arrivals Steur and Bamba integrated slowly, though **Aladji Bamba** posted 11.7 DefCons/90 in limited time. **Jacob Ramsey** gets game-time boost following Gordon/Guimaraes/Tonali departures. |
| Dominguez, Sangare, Schlager | NFO | Competing for 2 spots under Glasner. **Ibrahim Sangare** averaged 11.58 DefCons/90 in 2025/26. Schlager arrived on free. |
| Sadiki, Adingra, Mundle, Rigg, Jocelin, Angulo | SUN | Sadiki is regular starter but poor fantasy return (2 returns, 12.1% DefCon success rate). Wingers are fringe/rotation. |
| Sarr, Gray, Moore | TOT | Arrivals of Tonali (£100m) and Mateus Fernandes (£85m) severely dent xMins of Pape Matar Sarr and Archie Gray. |

### 2025/26 Opta Statistical Data

#### Current £5.0m Midfielders Sorted by Minutes per Expected Goal Involvement (xGI) — Premier League Only

| Name | Team | Cost | Mins | Mins/Goal | Mins/Shot | Mins In Box | Mins On Target | Mins/Touch | Mins/CC | Mins/Cross | Mins/xA | Mins/xG | Mins/xGI |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Brooks (David) | BOU | 5.0 | 1307 | 1307.0 | 27.2 | 37.3 | 100.5 | 17.9 | 50.0 | 22.2 | 396.1 | 224.2 | **143.2** |
| Gomez (Diego) | BHA | 5.0 | 2134 | 426.8 | 50.8 | 76.2 | 152.4 | 26.7 | 102.0 | 101.6 | 1248.0 | 339.3 | **266.8** |
| Adli | BOU | 5.0 | 1213 | 404.3 | 60.7 | 93.3 | 134.8 | 25.8 | 76.0 | 30.3 | 748.8 | 466.5 | **287.4** |
| Devenny | CRY | 5.0 | 863 | 863.0 | 66.4 | 86.3 | 215.8 | 27.0 | 123.0 | 53.9 | 2271.1 | 329.4 | **287.7** |
| Longstaff (Sean) | LEE | 5.0 | 1077 | 538.5 | 67.3 | 119.7 | 269.3 | 53.9 | 43.0 | 19.9 | 563.9 | 861.6 | **340.8** |

#### Current £5.0m Midfielders Sorted by DefCons per 90 Minutes — Premier League Only

| Name | Team | Cost | App | Mins | CS/90 | GC/90 | DefCon/90 | DC% | Clr/90 | Blks/90 | Int/90 | Rec/90 | Tackles Tot/90 | Tackles Won/90 | Tackle Win % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Cook (Lewis) | BOU | 5.0 | 18 | 924 | 0.10 | 1.85 | **14.03** | 38.9% | 2.53 | 0.58 | 2.34 | 6.04 | 2.53 | 1.56 | 61.5% |
| Ugarte | MUN | 5.0 | 22 | 971 | 0.09 | 2.13 | **13.16** | 18.2% | 1.85 | 0.46 | 1.85 | 4.73 | 4.26 | 2.69 | 63.0% |
| Adams (Tyler) | BOU | 5.0 | 25 | 1795 | 0.35 | 1.40 | **11.68** | 32.0% | 2.11 | 0.45 | 1.65 | 4.81 | 2.66 | 1.15 | 43.4% |
| Sangare (Ibrahim) | NFO | 5.0 | 28 | 2083 | 0.35 | 1.12 | **11.58** | 32.1% | 2.16 | 0.82 | 1.08 | 4.93 | 2.59 | 1.30 | 50.0% |
| Yarmoliuk | BRE | 5.0 | 37 | 2682 | 0.27 | 1.41 | **11.41** | 29.7% | 1.38 | 0.47 | 0.94 | 6.28 | 2.35 | 1.51 | 64.3% |
| Sarr (Pape Matar) | TOT | 5.0 | 26 | 1465 | 0.18 | 1.41 | **11.37** | 15.4% | 2.89 | 0.61 | 1.11 | 4.73 | 2.03 | 1.29 | 63.6% |
| Baleba | BHA | 5.0 | 31 | 1677 | 0.38 | 1.02 | **11.22** | 12.9% | 1.72 | 0.32 | 1.56 | 5.64 | 1.99 | 1.07 | 54.1% |
| Mvom Onana | AVL | 5.0 | 25 | 1778 | 0.30 | 1.32 | **11.19** | 28.0% | 2.99 | 0.86 | 1.27 | 3.64 | 2.43 | 1.52 | 62.5% |
| Janelt | BRE | 5.0 | 25 | 1500 | 0.30 | 1.26 | **11.04** | 28.0% | 2.04 | 0.48 | 1.80 | 5.10 | 1.62 | 0.96 | 59.3% |

#### Historical DefCon Baseline: Christian Norgaard (Brentford 2024/25)

| Name | Team | Cost | App | Mins | CS/90 | GC/90 | DefCon/90 | DC% | Clr/90 | Blks/90 | Int/90 | Rec/90 | Tackles Tot/90 | Tackles Won/90 | Tackle Win % |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Norgaard | BRE | 5.0 | 34 | 2818 | 0.19 | 1.44 | **12.93** | **50.0%** | 2.04 | 0.64 | 1.56 | 6.16 | 2.52 | 1.56 | 62.0% |

## Project interpretation

### Decision rules

1. **Attacking Pick**: **Diego Gomez (Brighton, £5.0m)** is the clear #1 attacking midfielder at £5.0m with Kaoru Mitoma injured; secure starter on the right wing with 266.8 mins/xGI.
2. **DefCon Value Pick**: **Christian Norgaard (£5.0m)** post-Everton transfer is the top defensive contribution target (50% match DefCon hit rate at Brentford); **Andrey Santos (Man United, £5.0m)** is top GW1 Bench Boost pivot starter.
3. **Set-Piece / BB2 Pick**: **Matt Grimes (Coventry, £5.0m)** offers primary corner/free-kick duties and high baseline minutes for GW2 Bench Boost against Hull.

### Practical implications

- £5.0m midfield bracket bifurcates cleanly between high-variance attacking wingers (Gomez, Rohl, Ramsey) and high-floor DefCon anchors (Norgaard, Santos, Grimes, Matusiwa, Sangare).
- Provides budget flexibility to fund dual £10m+ premiums (Haaland + Palmer/Salah/Bruno).

## Findings

### Evidence

- Diego Gomez (266.8 mins/xGI) and David Brooks (143.2 mins/xGI, unnailed) lead attacking rates.
- Lewis Cook (14.03/90) and Christian Norgaard (12.93/90, 50% hit rate) lead DefCon efficiency.
- Andrey Santos (Man Utd, £5.0m) projected to start deep pivot with Ugarte injured and seniors returning late.

## Decision

**Verdict**: Diego Gomez (£5.0m) recommended for attacking upside; Christian Norgaard (£5.0m) and Andrey Santos (£5.0m) recommended for DefCon floor / Bench Boost configurations.

## Risks and unknowns

- Everton midfield hierarchy with Norgaard and Hackney arrivals.
- Lewis Cook / Tyler Adams rotation risk with Bournemouth in Europe.
- Diego Gomez minutes once Mitoma returns from injury.

## Refresh checklist

- [x] Recheck source page using Playwright rendering.
- [x] Transcribe all 20-club player breakdowns and statistical images into Markdown.
- [x] Cross-check with `expected-role-gw1-5.md` and `fpl-summer-transfers.md`.
- [x] Delete `.tmp/agent/` scratch files before completion.

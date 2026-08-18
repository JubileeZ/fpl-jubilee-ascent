# FPL 2026/27: Best £4.5m–£5.5m Forwards

**Updated**: 2026-08-18T15:05:00+07:00
**Data stamp**: Fantasy Football Scout article modified 2026-08-07 (unchanged on 2026-08-13 recheck); accessed 2026-08-13; Playwright recheck 2026-08-18: article:modified_time unchanged.
**Season**: 2026/27  
**Status**: Active  
**Purpose**: Assess £4.5m–£5.5m budget forwards for FPL 2026/27 third-forward enablers, Bench Boost options, and penalty-taking starters  
**Scope**: All 39 forwards priced at £4.5m, £5.0m, and £5.5m in FPL 2026/27  
**Related**: [Pre-season guide](fpl-preseason-guide.md) · [£6.0m–£6.5m forwards](fpl-6-0m-6-5m-forwards.md) · [£7.0m+ forwards](fpl-7-0m-forwards.md) · [Expected role GW1–5](../gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.md) · [Summer transfers](fpl-summer-transfers.md)

> Note revision created 2026-08-09 from Fantasy Football Scout full price-bracket review. Primary article published 2026-08-07. Source claims cross-checked with expected-role-gw1-5.md and fpl-summer-transfers.md.

## Sources

- **Primary**: [Best £4.5m-£5.5m forwards for FPL 2026/27: All 39 assessed — Fantasy Football Scout](https://www.fantasyfootballscout.co.uk/2026/08/07/best-4-5m-5-5m-forwards-for-fpl-2026-27-all-39-assessed) — published 2026-08-07; accessed 2026-08-13; role: comprehensive budget forward price bracket analysis (all 39 players), Championship underlying stats, and £4.5m enabler audit
- **Cross-check**: [Expected Role GW1–5](../gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.md) — updated 2026-08-06; role: starter status, minutes expectations, availability overlays
- **Cross-check**: [Confirmed Summer Transfers](fpl-summer-transfers.md) — updated 2026-08-09; role: confirmed transfer moves (Welbeck to Chelsea £5m, Garcia to Fulham £34.2m, Emersonn to Ipswich £26m, Kusi-Asare to Fulham £5.2m)

**Source boundary**: Source claims cross-checked against internal project notes. No live FPL API refresh or solver optimization run performed in this note.

## Agent Prompt

```text
Full redo docs/research/fpl-preseason-guide/fpl-4-5m-5-5m-forwards.md

1. Re-read source URL using Playwright headless browser rendering (`wait_until='domcontentloaded'`).
2. Confirm title, author, publication/update date, prices, roles, and quoted statistics.
3. Extract full text and analysis for all covered £4.5m–£5.5m forwards.
4. Transcribe 100% of Opta/Fotmob statistical images and both full tables (Other £5.0m-£5.5m forwards table and all 10 £4.5m forwards table) into Markdown tables.
5. Keep Source synthesis strictly separate from Project interpretation.
6. Update Updated ISO timestamp, Data stamp, Sources, Findings, Decision, and Risks.
7. Run pre-commit gate checks (`uv run ruff check .`, `uv run pytest`, `bash tests/verify.sh`); delete `.tmp/agent/` scratch files before finishing.
```

## Method

**Method type**: Source synthesis / price bracket analysis & cross-check audit

**Inputs**:
- Fantasy Football Scout article (`best-4-5m-5-5m-forwards-for-fpl-2026-27-all-39-assessed`)
- Expected Role GW1–5 note (`expected-role-gw1-5.md`)
- Confirmed Summer Transfers register (`fpl-summer-transfers.md`)

**Procedure**:
1. Extract profiles for all standout £5.5m forward options (Rutter/Kostoulas, Haji Wright, Beto/Barry, Muniz, McBurnie, Emersonn).
2. Transcribe the complete table of other £5.0m–£5.5m forwards (12 club entries).
3. Transcribe the complete table of all 10 £4.5m forwards.
4. Transcribe Fotmob / Opta underlying metrics (Championship top scorers, Beto vs Barry minutes/xGI comparison).
5. Synthesize decision rules for budget enabler selection.

**Definitions and assumptions**:
- **£4.5m–£5.5m FWD**: All forwards priced at £4.5m, £5.0m, or £5.5m in FPL 2026/27.

## Source synthesis

### Standout £5.5m Forward Options

- **Georginio Rutter & Charalampos Kostoulas (Brighton, £5.5m)**:
  - Following Danny Welbeck's (£6.0m) transfer to Chelsea, Rutter (reclassified to FWD; 3 goals, 5 assists in 20 starts in 2025/26) and 19-year-old Kostoulas (£30m signing; scored twice in pre-season) compete to lead Brighton's attack.
  - Stefanos Tzimas (£5.5m) and Evan Ferguson (£5.0m) are recovering from long-term injuries.
  - Fabian Hurzeler confirmed both will get opportunities, but a new striker signing remains possible.
- **Haji Wright (Coventry, £5.5m)**:
  - 17 goals (2 penalties), 1 assist in 31 starts in the Championship (joint-2nd in Golden Boot).
  - Led the entire Championship for expected goals (18.3 xG).
  - On penalties; expected to start ahead of Ellis Simms (£5.0m) and Brandon Thomas-Asante (£5.0m).
  - Prime candidate for a GW2 Bench Boost when Coventry hosts Hull City.
- **Oli McBurnie (Hull, £5.5m)**:
  - 17 goals (3 penalties), 7 assists in regular season + late play-off final winner vs Middlesbrough.
  - Overachieved 12.05 xG (18 total goals); 100% of goals inside the box.
  - Hull's undisputed talisman on penalties (scored 2 in pre-season).
- **Beto & Thierno Barry (Everton, £5.5m)**:
  - Shared #9 duties in 2025/26: Beto (9 goals, 1 assist, 1649 mins, 180.6 mins/xGI); Barry (8 goals, 1999 mins, 231.9 mins/xGI).
  - High substitution rate (frequent early sub for each other) and David Moyes' conservative attack limits appeal.
- **Rodrigo Muniz (Fulham, £5.5m)**:
  - Fantasy appeal blunted by Gonzalo Garcia's (£6.0m) £34.2m arrival from Real Madrid under Arbeloa. Difficult opening fixtures.
- **Emersonn (Ipswich, £5.5m)**:
  - £24m club-record arrival from Toulouse (6 goals, 2 assists in Ligue 1); aerial target competing with George Hirst (£5.0m) and Chuba Akpom (£5.0m). Tricky early fixtures (Man Utd GW2, Liverpool GW3).

---

### 2025/26 Statistical Comparisons

#### Championship Top Scorers (2025/26) — Fotmob Data

| Rank | Player | Club | Goals | Penalty Goals |
|---|---|---|---|---|
| 1 | Zan Vipotnik | Swansea | 23 | 5 |
| 2 | **Haji Wright** | **Coventry** | **17** | **2** |
| 3 | **Oli McBurnie** | **Hull** | **17** | **3** |

#### Everton Forwards Comparison (2025/26)

| Name | Team | Cost | Mins | I | C | T | II | Goal | Shot | In Box | On Target | Touch In Box | CC | Cross | xA | xG | xGI |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Beto** | EVE | 5.5 | 1649 | 428 | 159 | 657 | 124.5 | 183.2 | 38.3 | 39.3 | 97.0 | 17.0 | 137.0 | 824.5 | 7495.5 | **185.1** | **180.6** |
| **Barry** | EVE | 5.5 | 1999 | 309 | 208 | 503 | 102.0 | 249.9 | 52.6 | 55.5 | 142.8 | 21.3 | 167.0 | 499.8 | 4253.2 | **245.3** | **231.9** |

---

### Other £5.0m–£5.5m Forwards Assessment

| Player | Price | Club | Scout Notes |
|---|---|---|---|
| Abraham | £5.5m | AVL | Backup to Ollie Watkins (£8.0m); linked with exit. Brian Madjo (unpriced) scored 4 in pre-season and could be 2nd in line. |
| Unal | £5.5m | BOU | Backup limited to 214 minutes in 2025/26; linked with departure. |
| Wilson (Callum) | £5.5m | BRE | Backup to Igor Thiago (£8.0m); impact substitute role. |
| Delap, Guiu, Emegha | £5.5m / £5.0m / £5.0m | CHE | Behind Joao Pedro (£7.5m) and Danny Welbeck (£6.0m). Delap/Guiu linked with exits; Emegha injured (hamstring). |
| Markelo | £5.0m | COV | Barely featured in Championship; exit expected. |
| Nketiah | £5.5m | CRY | Scored 3 in pre-season, but behind Jean-Philippe Mateta (£6.5m) and Jorgen Strand Larsen (£6.0m). |
| Al-Hamadi | £5.0m | IPS | Loaned to Luton last season; searching for new club. |
| Nmecha, Piroe | £5.5m / £5.0m | LEE | Backups to Dominic Calvert-Lewin (£6.0m). Nmecha scored 6 league goals last season. |
| Zirkzee | £5.5m | MUN | Only 5 league goals in last 2 seasons; return to Italy expected. |
| Awoniyi, Kalimuendo | £5.5m / £5.5m | NFO | Behind Igor Jesus (£6.0m) and Chris Wood (£6.0m) in Glasner's hierarchy. |
| Isidor | £5.5m | SUN | Europa League rotation behind Brian Brobbey (£6.0m). |

---

### Full Assessment: All 10 £4.5m Forwards

| Player | Club | Status & FPL Viability |
|---|---|---|
| **Furo** | BRE | Summer arrival from Club Brugge; signing for the future, occasional bench cameos. |
| **Mheuka** | CHE | Available for loan to the Championship. |
| **Kusi-Asare** | FUL | 18yo signed permanently from Bayern; 3rd choice behind Garcia and Muniz (49 mins in 2025/26). |
| **Destan** | HUL | Backup to McBurnie; aiming for impact off bench. |
| **Walle Egeli** | **IPS** | **Standout £4.5m option**. £17.5m Norwegian winger/No. 10 reclassified as FWD. Scored 4 goals and 2 assists in 18 league starts in 2025/26; played pre-season minutes under O'Neil; genuine bench/sub minutes potential. |
| **Joseph** | LEE | Target for Elche; expected to leave Leeds. |
| **Danns** | LIV | Missed US pre-season tour with injury; loan expected. |
| **Obi** | MUN | Loan to FC Koln expected. |
| **Neave** | NEW | Featured 13 minutes in 2025/26; loan move expected. |
| **Scarlett** | TOT | Loan to Championship/Europe expected. |

## Project interpretation

### Decision rules

1. **Top £5.5m Starters**:
   - **Haji Wright (Coventry, £5.5m)**: Proven penalty taker with Championship-leading 18.3 xG; prime candidate for early Bench Boost (GW2 vs Hull).
   - **Oli McBurnie (Hull, £5.5m)**: Talisman on penalties (18 goals in 2025/26); undisputed starter.
   - **Georginio Rutter (Brighton, £5.5m)**: Highest ceiling if securing Welbeck's vacant starting spot.
2. **Top £4.5m Bench Enabler**:
   - **Sindre Walle Egeli (Ipswich, £4.5m)**: Only £4.5m forward with realistic Premier League minutes (18 starts, 4 goals, 2 assists in 2025/26).
3. **Avoids**:
   - Rodrigo Muniz (displaced by Garcia), Beto/Barry (unpredictable rotation), and all non-Egeli £4.5m forwards (headed out on loan).

### Practical implications

- Enables viable 3-5-2 or 3-4-3 structures with Haji Wright or Georginio Rutter as cheap 3rd forwards (£5.5m), or enables ultra-cheap bench funding via Walle Egeli (£4.5m).

## Findings

### Evidence

- Haji Wright led the Championship in xG (18.3) and scored 17 goals on penalties.
- Oli McBurnie scored 18 goals in all competitions and takes penalties for Hull.
- Sindre Walle Egeli is the only £4.5m forward with starting experience (18 league starts in 2025/26).
- Welbeck's move to Chelsea vacated Brighton's #9 role for Rutter and Kostoulas.

## Decision

**Verdict**: Haji Wright (£5.5m) and Oli McBurnie (£5.5m) are the top starting budget forward picks; Sindre Walle Egeli (£4.5m) is the only viable £4.5m forward enabler.

## Risks and unknowns

- Coventry / Hull attacking efficiency stepping up from the Championship.
- Brighton potential late striker signing before the September 1 transfer deadline.
- Walle Egeli's minutes under Gary O'Neil following Emersonn's arrival.

## Refresh checklist

- [x] Recheck source page using Playwright rendering.
- [x] Transcribe all player analysis and tables (including all 10 £4.5m forwards) into Markdown.
- [x] Cross-check with `expected-role-gw1-5.md` and `fpl-summer-transfers.md`.
- [x] Delete `.tmp/agent/` scratch files before completion.

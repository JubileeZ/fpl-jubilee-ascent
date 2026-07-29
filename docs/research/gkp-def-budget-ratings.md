# FPL Budget GKP/DEF Ratings & Squad Selection

**Updated**: 2026-07-29T22:18:00+07:00  
**Data stamp**: bootstrap / players.parquet refreshed **2026-07-29 ~22:17 ICT** (entry 822158 auth)  
**Season**: 2026/27 launch prices · GW1 Fri 21 Aug 2026  
**Scope**: 44 GKPs (≤ £4.5m) + 175 DEFs (≤ £5.5m) from live FPL bootstrap  
**Constraints**: 2 GKPs (one £4.5m + one £4.0–£4.5m) · 5 DEFs ≤ £22.5m · 7 players ≤ £31.0m total  
**Sibling**: [`pl-starter-rolescore.md`](pl-starter-rolescore.md) · [`bb-then-wc-strategy.md`](bb-then-wc-strategy.md)  
**Sources**: FPL API prices/status/prior-season totals · Meerkat GW1 XI (28 Jul) · club/transfer press (Trafford LEE; Amenda COV; Lacroix CHE)  
**Not used**: repo projection models

## Agent Prompt

```
Full redo docs/research/gkp-def-budget-ratings.md

1. uv run python -m commands.refresh_data (auth via .env; Playwright Chromium if needed)
2. From data/processed/players.parquet: rate all GKP ≤£4.5 and DEF ≤£5.5 for 2026/27 set-and-forget (1–10). Weights: minutes/role, CS+DEFcon, attack upside, price efficiency, injury/transfer risk.
3. Recommend 7 under £31.0 (2 GKP + 5 DEF ≤£22.5). Flag dual-club GK traps (never Kinsky+Dubravka). Sync Spurs GK, Trafford LEE, Amenda vs Thomas COV, O'Shea vs Diop IPS with pl-starter-rolescore.md.
4. Rebuild full club directory from live bootstrap. Independent of projection models.
5. Update header **Updated** (ISO+timezone) and **Data stamp**. Keep slug filename. Cross-link sibling research slugs.
6. Delete .tmp/agent/ scratch when done.
```

## Method

Ratings = **2026/27 set-and-forget outlook** (1–10), not last-season points rank alone.

| Weight | GKP | DEF |
| --- | --- | --- |
| Minutes / role security | Locked No.1 vs cover | Regular starter vs rotation |
| Team defensive outlook | CS + save volume | CS + DEFcon (≥10 actions → +2) |
| Upside | Fixtures / club strength | Goals + assists + set-piece / long-throw |
| Price efficiency | £4.0–£4.5 bracket | Prefer ≤ £5.0 unless ceiling clear |
| Risk | Injury, transfer, dual-club GK trap | New manager / promoted PL step-up |

Prior-season FPL totals = **2025/26** bootstrap carryover (promoted show 0).

## Verdict — Recommended 7

### Goalkeepers (£9.0m) — two locked starters

| Player | Club | Price | Role | Rating | Why |
| --- | --- | --- | --- | ---: | --- |
| **Verbruggen** | Brighton | £4.5m | Set-and-forget No.1 | **9.4** | Consensus best sub-£5.0m GK. 38 starts / 130 pts / 10 CS. Meerkat 🟢. |
| **Leno** | Fulham | £4.5m | Second starter | **8.8** | Locked 38 starts / 122 pts / 9 CS. Avoids Spurs dual-club trap. |

**Reject as dual starter**: Kinsky + Dubravka. De Zerbi No.1 = **Kinsky** (EO 17.3%); **Dubravka** cover only (EO 24.8% trap).

**Differential path** (user bias / live 822158): Verbruggen + **Kinsky** £4.5 — Ext N despite THIN sample (7 starts). Accept vs Leno.

**If free £0.5m**: Verbruggen £4.5 + £4.0 bench (Steele / Austin / Heaton / Dennis).

**Leeds GK watch**: Trafford terms agreed MCI→LEE £40m+£5m (await announce). Perri £4.5 lean until flip; Trafford likely £5.0+ out of this band.

### Defenders (£22.5m)

| Player | Club | Price | Attack / floor | Rating | Why |
| --- | --- | --- | ---: | --- |
| **Mitchell** | Crystal Palace | £4.5m | 1G 3A · 12 CS · 135 pts | **9.2** | Sage WB continuity; Meerkat 🟢. |
| **N.Williams** | Nott'm Forest | £5.0m | 2G 3A · 128 pts | **9.1** | Glasner RWB build-around. |
| **Kayode** | Brentford | £4.5m | 1G 2A · 37 starts | **8.8** | Ironman RB + DEFcon / long throws. |
| **Cash** | Aston Villa | £4.5m | **3G 3A** · 34 starts | **8.7** | Clearest £4.5 G/A among locked FBs. |
| **O'Shea** | Ipswich | £4.0m | Captain N lean | **8.0** | Prefer over Diop (B / same-side CB) for BB floor. |

**Budget**: GKP £9.0 + DEF £22.5 = **£31.0m**.

**Thomas demote**: Amenda £17m+ signed; Meerkat expects Amenda into COV XI. Thomas RS kill-switch active → prefer **van Ewijk** £4.0 (EO 17.0%) for start security if keeping promoted DEF, or O'Shea path above.

**Ballard alt**: thr90 15.5 elite CB — fitness/Europa gate; pair with Mitchell/N.Williams if dropping Kayode/Cash.

### Strong alternatives (same budget)

| Swap | For | Δ | Note |
| --- | --- | ---: | --- |
| van Ewijk | O'Shea / Thomas | 0 | Safer COV mins if Amenda starts CB |
| Hume | Cash | 0 | SUN RB ironman |
| Shaw | Cash | 0 | Template LB; lower G/A |
| Mukiele | N.Williams + O'Shea → Mukiele + Diop | 0 | Attack volume; £5.5 tax |
| Ballard | Kayode | +0.5 | Needs fund from GKP enabler path |
| Truffert | needs £1 squeeze | — | Best ceiling; budget breaker |

## Top tiers (quick reference)

### GKP shortlist (playable)

| Rank | Player | Price | Rating | Note |
| ---: | --- | ---: | ---: | --- |
| 1 | Verbruggen | £4.5 | 9.4 | Default set-and-forget |
| 2 | Leno | £4.5 | 8.8 | Best second starter |
| 3 | Kinsky | £4.5 | 8.6 | Spurs No.1 (~90% Meerkat) |
| 4 | Petrović | £4.5 | 8.2 | 11 CS; Europe rotation |
| 5 | Perri | £4.5 | 6.0 | LEE lean until Trafford announced |

All other ≤ £4.5 GKPs: **≤ 4.5** (cover / unused).

### DEF shortlist (attack + DEFcon)

| Rank | Player | Price | Rating | Note |
| ---: | --- | ---: | ---: | --- |
| 1 | Truffert | £5.5 | 9.3 | Ceiling; budget squeeze |
| 2 | Mitchell | £4.5 | 9.2 | Value king |
| 3 | N.Williams | £5.0 | 9.1 | Glasner upside |
| 4 | Mukiele | £5.5 | 9.0 | Attack + volume |
| 5 | Muñoz | £5.5 | 8.9 | Higher G/A than Mitchell |
| 6 | Kayode | £4.5 | 8.8 | Minutes + DEFcon |
| 7 | Cash | £4.5 | 8.7 | Attack profile |
| 8 | Van Hecke | £5.0 | 8.6 | Spurs CB |
| 9 | Chalobah | £5.5 | 8.5 | Goal threat; Alonso unknown |
| 10 | Ballard | £5.0 | 8.4 | thr90 elite; fitness gate |
| 11 | Hume | £4.5 | 8.2 | Cheap SUN starter |
| 12 | Shaw | £4.5 | 8.1 | Template LB |
| 13 | van Ewijk | £4.0 | 8.0 | COV RB lean vs Amenda CB |
| 14 | O'Shea | £4.0 | 8.0 | IPS captain N |
| 15 | Thomas | £4.0 | 7.5 | Amenda kill switch |

## Full directory (1–10)

Status/price from live FPL API (**2026-07-29 ~22:17 ICT**). Pts/starts/G/A/CS = 2025/26 unless promoted (0).

### Arsenal
* **GKP (≤ £4.5m)**: none in band
* **DEF**:
  * **Calafiori** (£5.5 · a) — **6.5** — 109 pts, 1G 2A, 22 starts
  * **Hincapie** (£5.5 · a) — **6.5** — 87 pts, 1G 2A, 20 starts
  * **White** (£5.5 · i · Knee injury - Expected back 21 Aug) — **4.5** — 45 pts, 0G 1A, 9 starts
  * **Mosquera** (£5.5 · a) — **4.5** — 40 pts, 9 starts

### Aston Villa
* **GKP**:
  * **M.Bizot** (£4.5 · a) — **4.5** — 16 pts, 6 starts; 1 CS
* **DEF**:
  * **Cash** (£4.5 · a) — **8.7** — 117 pts, 3G 3A, 34 starts
  * **Konsa** (£4.5 · a) — **7.5** — 100 pts, 0G 1A, 34 starts
  * **Digne** (£4.5 · a) — **6.5** — 97 pts, 0G 7A, 21 starts
  * **Pau** (£4.5 · a) — **5.5** — 64 pts, 0G 2A, 18 starts
  * **Maatsen** (£4.5 · a) — **5.5** — 54 pts, 0G 1A, 17 starts
  * **Mings** (£4.5 · a) — **5.5** — 50 pts, 0G 1A, 15 starts
  * **Lindelöf** (£4.5 · a) — **5.5** — 29 pts, 0G 1A, 11 starts
  * **A.García** (£4 · a) — **4.5** — 5 pts, 1 starts
  * **Nedeljkovic** (£4 · a) — **3.5** — 0 PL mins / promoted or new

### Bournemouth
* **GKP**:
  * **Petrović** (£4.5 · a) — **8.2** — 124 pts, 38 starts; 11 CS
  * **Forster** (£4 · a) — **3.5** — 0 PL mins
  * **Dennis** (£4 · a) — **3.0** — 0 PL mins
* **DEF**:
  * **Truffert** (£5.5 · a) — **9.3** — 165 pts, 1G 6A, 38 starts
  * **Hill** (£5.5 · a) — **6.5** — 110 pts, 0G 3A, 22 starts
  * **Diakité** (£5 · a) — **5.5** — 46 pts, 15 starts
  * **Milosavljević** (£5 · a) — **4.5** — 19 pts, 4 starts
  * **Smith** (£4.5 · a) — **5.5** — 58 pts, 0G 2A, 14 starts
  * **J.Araujo** (£4.5 · a) — **3.5** — 0 PL mins / promoted or new
  * **Soler** (£4 · a) — **3.5** — 0 PL mins / promoted or new

### Brentford
* **GKP**:
  * **Valdimarsson** (£4.5 · a) — **4.5** — 1 pts, 1 starts; 0 CS
* **DEF**:
  * **Collins** (£5.5 · a) — **7.5** — 129 pts, 1G 2A, 32 starts
  * **Van den Berg** (£5 · a) — **7.5** — 113 pts, 0G 3A, 30 starts
  * **Kayode** (£4.5 · a) — **8.8** — 113 pts, 1G 2A, 37 starts
  * **Ajer** (£4.5 · a) — **6.5** — 76 pts, 0G 2A, 20 starts
  * **Henry** (£4.5 · a) — **5.5** — 52 pts, 0G 2A, 14 starts
  * **Hickey** (£4.5 · a) — **4.5** — 37 pts, 8 starts
  * **Pinnock** (£4.5 · a) — **4.5** — 14 pts, 4 starts
  * **Ji-soo** (£4.5 · a) — **3.5** — 0 PL mins / promoted or new
  * **Schuster** (£4.5 · a) — **3.5** — 0 PL mins / promoted or new

### Brighton
* **GKP**:
  * **Verbruggen** (£4.5 · a) — **9.4** — 130 pts, 38 starts; 10 CS
  * **Rushworth** (£4.5 · a) — **3.5** — 0 PL mins
  * **Steele** (£4 · a) — **3.0** — 0 PL mins
* **DEF**:
  * **Struijk** (£5 · a) — **7.5** — 108 pts, 0G 1A, 33 starts
  * **Wieffer** (£5 · a) — **6.5** — 94 pts, 2G 4A, 23 starts
  * **Svoboda** (£5 · a) — **3.5** — 0 PL mins / promoted or new
  * **Vuskovic** (£5 · a) — **3.5** — 0 PL mins / promoted or new
  * **F.Kadıoğlu** (£4.5 · a) — **7.5** — 118 pts, 1G 2A, 34 starts
  * **Dunk** (£4.5 · a) — **7.5** — 100 pts, 1G 1A, 31 starts
  * **De Cuyper** (£4.5 · a) — **5.5** — 84 pts, 2G 3A, 17 starts
  * **Boscagli** (£4.5 · a) — **4.5** — 39 pts, 0G 1A, 9 starts
  * **Coppola** (£4.5 · a) — **4.5** — 10 pts, 2 starts
  * **Igor** (£4.5 · a) — **4.5** — 6 pts, 1 starts
  * **Costinha** (£4.5 · a) — **3.5** — 0 PL mins / promoted or new

### Chelsea
* **GKP**:
  * **Penders** (£4.5 · a) — **3.5** — 0 PL mins
* **DEF**:
  * **Chalobah** (£5.5 · a) — **8.5** — 136 pts, 3G 1A, 31 starts
  * **James** (£5.5 · a) — **8.2** — 115 pts, 2G 6A, 20 starts
  * **Palestra** (£5.5 · a) — **3.5** — 0 PL mins / promoted or new
  * **Gusto** (£5 · a) — **7.8** — 96 pts, 2G 3A, 26 starts
  * **Fofana** (£5 · s · Suspended until 6 Sep) — **6.5** — 65 pts, 0G 2A, 20 starts
  * **Colwill** (£5 · a) — **4.5** — 8 pts, 2 starts
  * **Acheampong** (£4.5 · a) — **4.5** — 39 pts, 1G 0A, 8 starts
  * **Tosin** (£4.5 · a) — **4.5** — 34 pts, 8 starts
  * **Hato** (£4.5 · a) — **5.5** — 19 pts, 12 starts
  * **B.Badiashile** (£4.5 · a) — **4.5** — 7 pts, 6 starts
  * **M.Sarr** (£4.5 · a) — **4.5** — 3 pts, 1 starts
  * **Disasi** (£4.5 · a) — **3.5** — 0 PL mins / promoted or new
  * **Anselmino** (£4.5 · a) — **3.5** — 0 PL mins / promoted or new

### Coventry City
* **GKP**:
  * **Wilson** (£4.5 · a) — **5.0** — 0 PL mins
  * **Dovin** (£4 · a) — **3.5** — 0 PL mins
* **DEF**:
  * **Thomas** (£4 · a) — **7.5** — 0 PL mins / promoted or new
  * **Kitching** (£4 · a) — **3.5** — 0 PL mins / promoted or new
  * **van Ewijk** (£4 · a) — **8.0** — 0 PL mins / promoted or new
  * **Dasilva** (£4 · a) — **3.5** — 0 PL mins / promoted or new
  * **Kesler-Hayden** (£4 · a) — **3.5** — 0 PL mins / promoted or new
  * **Bidwell** (£4 · a) — **3.5** — 0 PL mins / promoted or new
  * **Latibeaudiere** (£4 · a) — **3.5** — 0 PL mins / promoted or new
  * **Woolfenden** (£4 · a) — **3.5** — 0 PL mins / promoted or new
  * **Brau** (£4 · a) — **3.5** — 0 PL mins / promoted or new
  * **Amenda** (£4 · a) — **6.5** — 0 PL mins / promoted or new

### Crystal Palace
* **GKP**:
  * **Benitez** (£4.5 · a) — **4.5** — 7 pts, 1 starts; 1 CS
  * **Matthews** (£4 · a) — **3.5** — 0 PL mins
* **DEF**:
  * **Muñoz** (£5.5 · a) — **8.9** — 136 pts, 4G 4A, 29 starts
  * **Richards** (£5 · a) — **7.5** — 128 pts, 1G 0A, 31 starts
  * **Canvot** (£5 · a) — **5.5** — 72 pts, 14 starts
  * **Mitchell** (£4.5 · a) — **9.2** — 135 pts, 1G 3A, 36 starts
  * **Chadi Riad** (£4.5 · a) — **4.5** — 20 pts, 0G 1A, 6 starts
  * **Sosa** (£4.5 · a) — **3.5** — 0 PL mins / promoted or new
  * **Cardines** (£4.5 · a) — **4.5** — 2 pts, 1 starts
  * **Mingueza** (£4.5 · a) — **3.5** — 0 PL mins / promoted or new

### Everton
* **GKP**:
  * **King** (£4.5 · a) — **3.5** — 0 PL mins
* **DEF**:
  * **Branthwaite** (£5.5 · a) — **4.5** — 32 pts, 1G 1A, 7 starts
  * **Keane** (£5 · a) — **7.5** — 131 pts, 3G 1A, 29 starts
  * **O'Brien** (£5 · a) — **7.5** — 116 pts, 1G 3A, 35 starts
  * **Mykolenko** (£4.5 · a) — **6.5** — 95 pts, 0G 1A, 33 starts
  * **Patterson** (£4.5 · a) — **4.5** — 22 pts, 3 starts
  * **Aznou** (£4 · a) — **3.5** — 0 PL mins / promoted or new

### Fulham
* **GKP**:
  * **Leno** (£4.5 · a) — **8.8** — 122 pts, 38 starts; 9 CS
  * **Lecomte** (£4 · a) — **3.5** — 0 PL mins
  * **McNally** (£4 · a) — **3.5** — 0 PL mins
* **DEF**:
  * **Andersen** (£5 · s · Suspended until 29 Aug) — **7.5** — 123 pts, 0G 1A, 33 starts
  * **Bassey** (£4.5 · a) — **7.5** — 103 pts, 1G 1A, 28 starts
  * **Sessegnon** (£4.5 · a) — **6.5** — 95 pts, 3G 3A, 20 starts
  * **Tete** (£4.5 · a) — **6.5** — 81 pts, 1G 0A, 21 starts
  * **Robinson** (£4.5 · a) — **5.5** — 65 pts, 1G 0A, 17 starts
  * **Castagne** (£4.5 · a) — **6.5** — 61 pts, 0G 2A, 20 starts
  * **J.Cuenca** (£4.5 · a) — **5.5** — 39 pts, 11 starts

### Hull City
* **GKP**:
  * **Butland** (£4.5 · a) — **5.5** — 0 PL mins
  * **Phillips** (£4 · a) — **3.5** — 0 PL mins
  * **Cartwright** (£4 · u · Has joined Grimsby Town on loan for the ) — **3.5** — 0 PL mins
  * **Lo-Tutala** (£4 · a) — **3.5** — 0 PL mins
* **DEF**:
  * **Egan** (£4 · a) — **3.5** — 0 PL mins / promoted or new
  * **Hughes** (£4 · a) — **3.5** — 0 PL mins / promoted or new
  * **Ajayi** (£4 · a) — **3.5** — 0 PL mins / promoted or new
  * **Coyle** (£4 · a) — **3.5** — 0 PL mins / promoted or new
  * **Drameh** (£4 · a) — **3.5** — 0 PL mins / promoted or new
  * **Giles** (£4 · a) — **3.5** — 0 PL mins / promoted or new
  * **Jacob** (£4 · a) — **3.5** — 0 PL mins / promoted or new
  * **McCarthy** (£4 · a) — **3.5** — 0 PL mins / promoted or new
  * **McNair** (£4 · a) — **3.5** — 0 PL mins / promoted or new
  * **Targett** (£4 · a) — **3.5** — 0 PL mins / promoted or new

### Ipswich Town
* **GKP**:
  * **Walton** (£4.5 · a) — **3.5** — 0 PL mins
  * **Scherpen** (£4.5 · a) — **3.5** — 0 PL mins
  * **Van Oevelen** (£4.5 · a) — **3.5** — 0 PL mins
  * **Button** (£4 · a) — **3.5** — 0 PL mins
  * **Palmer** (£4 · a) — **5.5** — 0 PL mins
* **DEF**:
  * **Diop** (£4 · a) — **7.0** — 31 pts, 1G 0A, 8 starts
  * **Kipré** (£4 · a) — **3.5** — 0 PL mins / promoted or new
  * **O'Shea** (£4 · a) — **8.0** — 0 PL mins / promoted or new
  * **Davis** (£4 · a) — **7.2** — 0 PL mins / promoted or new
  * **Greaves** (£4 · a) — **6.5** — 0 PL mins / promoted or new
  * **Johnson** (£4 · a) — **3.5** — 0 PL mins / promoted or new
  * **Furlong** (£4 · a) — **3.5** — 0 PL mins / promoted or new

### Leeds
* **GKP**:
  * **Perri** (£4.5 · a) — **6.0** — 43 pts, 16 starts; 3 CS
* **DEF**:
  * **Bijol** (£5 · a) — **6.5** — 99 pts, 1G 3A, 21 starts
  * **Muharemović** (£5 · a) — **3.5** — 0 PL mins / promoted or new
  * **Rodon** (£4.5 · a) — **7.5** — 109 pts, 2G 0A, 33 starts
  * **Bogle** (£4.5 · a) — **6.5** — 96 pts, 1G 5A, 32 starts
  * **Justin** (£4.5 · a) — **6.5** — 94 pts, 2G 1A, 21 starts
  * **Gudmundsson** (£4.5 · a) — **6.5** — 68 pts, 31 starts
  * **Bornauw** (£4.5 · a) — **4.5** — 25 pts, 5 starts

### Liverpool
* **GKP**:
  * **Woodman** (£4 · a) — **4.5** — 6 pts, 2 starts; 0 CS
  * **Pecsi** (£4 · a) — **3.5** — 0 PL mins
  * **Jaros** (£4 · a) — **3.5** — 0 PL mins
  * **Davies** (£4 · a) — **3.5** — 0 PL mins
* **DEF**:
  * **Kerkez** (£5.5 · a) — **7.8** — 85 pts, 2G 1A, 27 starts
  * **Frimpong** (£5.5 · a) — **5.5** — 63 pts, 0G 5A, 12 starts
  * **Bradley** (£5 · i · Knee injury - Unknown return date) — **5.5** — 42 pts, 0G 2A, 12 starts
  * **Gomez** (£5 · i · Muscular injury - Unknown return date) — **4.5** — 33 pts, 0G 2A, 7 starts
  * **Jacquet** (£5 · a) — **3.5** — 0 PL mins / promoted or new
  * **Tsimikas** (£5 · a) — **3.5** — 0 PL mins / promoted or new
  * **Lucky** (£4 · a) — **3.5** — 0 PL mins / promoted or new
  * **Leoni** (£4 · i · Knee injury - Unknown return date) — **3.5** — 0 PL mins / promoted or new
  * **Ramsay** (£4 · a) — **3.5** — 0 PL mins / promoted or new

### Man City
* **GKP**:
  * **Bettinelli** (£4.5 · a) — **3.5** — 0 PL mins
* **DEF**:
  * **Rúben** (£5.5 · a) — **6.5** — 113 pts, 2G 0A, 24 starts
  * **Gvardiol** (£5.5 · a) — **5.5** — 79 pts, 2G 2A, 16 starts
  * **Khusanov** (£5.5 · a) — **5.5** — 67 pts, 15 starts
  * **Aït-Nouri** (£5.5 · a) — **5.5** — 60 pts, 0G 2A, 12 starts
  * **Alleyne** (£5 · a) — **4.5** — 5 pts, 2 starts
  * **Lewis** (£4.5 · a) — **4.5** — 19 pts, 0G 1A, 4 starts
  * **Vitor Reis** (£4.5 · a) — **3.5** — 0 PL mins / promoted or new

### Man Utd
* **GKP**:
  * **Darlow** (£4.5 · d · Unspecified injury - 75% chance of playi) — **6.5** — 71 pts, 22 starts; 5 CS
  * **Bayindir** (£4.5 · a) — **4.5** — 11 pts, 6 starts; 0 CS
  * **Heaton** (£4 · a) — **3.0** — 0 PL mins
* **DEF**:
  * **Dalot** (£5 · a) — **8.0** — 111 pts, 1G 6A, 29 starts
  * **Maguire** (£5 · a) — **7.2** — 90 pts, 1G 2A, 19 starts
  * **Yoro** (£5 · a) — **5.5** — 56 pts, 0G 1A, 18 starts
  * **Martinez** (£5 · d · Thigh injury - 75% chance of playing) — **5.5** — 51 pts, 13 starts
  * **De Ligt** (£5 · i · Back injury - Unknown return date) — **5.5** — 43 pts, 1G 0A, 13 starts
  * **Shaw** (£4.5 · a) — **8.1** — 113 pts, 1G 1A, 38 starts
  * **Mazraoui** (£4.5 · a) — **5.5** — 53 pts, 11 starts
  * **Heaven** (£4.5 · a) — **5.5** — 42 pts, 0G 1A, 11 starts
  * **Fredricson** (£4 · a) — **3.5** — 0 PL mins / promoted or new
  * **Amass** (£4 · a) — **3.5** — 0 PL mins / promoted or new

### Newcastle
* **GKP**:
  * **Gillespie** (£4.5 · a) — **3.5** — 0 PL mins
  * **Jaouen** (£4.5 · a) — **3.5** — 0 PL mins
* **DEF**:
  * **Thiaw** (£5 · a) — **7.5** — 126 pts, 4G 0A, 33 starts
  * **Burn** (£5 · a) — **6.5** — 93 pts, 1G 3A, 25 starts
  * **Botman** (£5 · a) — **6.5** — 89 pts, 1G 1A, 21 starts
  * **Hall** (£5 · a) — **6.5** — 79 pts, 1G 2A, 24 starts
  * **Livramento** (£5 · d · Calf injury - 75% chance of playing) — **5.5** — 59 pts, 0G 1A, 14 starts
  * **Schär** (£5 · a) — **5.5** — 51 pts, 11 starts
  * **A.Murphy** (£4 · a) — **3.5** — 0 PL mins / promoted or new

### Nott'm Forest
* **GKP**:
  * **John** (£4.5 · a) — **4.5** — 11 pts, 5 starts; 1 CS
* **DEF**:
  * **Milenković** (£5.5 · a) — **7.5** — 119 pts, 0G 1A, 37 starts
  * **Murillo** (£5.5 · d · Muscle injury - 75% chance of playing) — **6.5** — 83 pts, 1G 0A, 25 starts
  * **N.Williams** (£5 · a) — **9.1** — 128 pts, 2G 3A, 36 starts
  * **Morato** (£5 · a) — **5.5** — 53 pts, 1G 0A, 14 starts
  * **Aina** (£4.5 · a) — **5.5** — 67 pts, 0G 2A, 18 starts
  * **Savona** (£4.5 · i · Knee injury - Unknown return date) — **5.5** — 39 pts, 2G 0A, 11 starts
  * **Jair Cunha** (£4.5 · a) — **4.5** — 13 pts, 6 starts
  * **Netz** (£4.5 · a) — **4.5** — 11 pts, 3 starts
  * **Abbott** (£4 · a) — **4.5** — 3 pts, 2 starts
  * **O.Richards** (£4 · a) — **3.5** — 0 PL mins / promoted or new
  * **Bindon** (£4 · a) — **3.5** — 0 PL mins / promoted or new

### Spurs
* **GKP**:
  * **Vicario** (£4.5 · a) — **5.0** — 90 pts, 31 starts; 7 CS
  * **Kinsky** (£4.5 · a) — **8.6** — 20 pts, 7 starts; 2 CS
  * **Austin** (£4 · a) — **3.0** — 0 PL mins
  * **Dubravka** (£4 · a) — **4.5** — 96 pts, 35 starts; 4 CS
* **DEF**:
  * **Pedro Porro** (£5.5 · a) — **7.5** — 117 pts, 1G 3A, 32 starts
  * **Van Hecke** (£5 · a) — **8.6** — 148 pts, 3G 3A, 36 starts
  * **Van de Ven** (£5 · a) — **7.5** — 116 pts, 4G 1A, 35 starts
  * **Romero** (£5 · a) — **6.5** — 91 pts, 4G 1A, 22 starts
  * **Danso** (£5 · a) — **5.5** — 63 pts, 17 starts
  * **Spence** (£4.5 · a) — **6.5** — 78 pts, 23 starts
  * **Robertson** (£4.5 · a) — **5.5** — 55 pts, 1G 0A, 11 starts
  * **Udogie** (£4.5 · a) — **5.5** — 29 pts, 0G 1A, 14 starts
  * **Phillips** (£4.5 · a) — **3.5** — 0 PL mins / promoted or new
  * **Davies** (£4 · a) — **4.5** — 10 pts, 1G 0A, 2 starts
  * **Souza** (£4 · a) — **4.5** — 3 pts, 2 starts
  * **Byfield** (£4 · a) — **3.5** — 0 PL mins / promoted or new
  * **Rowswell** (£4 · a) — **3.5** — 0 PL mins / promoted or new

### Sunderland
* **GKP**:
  * **Ellborg** (£4.5 · a) — **4.5** — 16 pts, 3 starts; 1 CS
  * **Patterson** (£4 · a) — **3.5** — 0 PL mins
* **DEF**:
  * **Mukiele** (£5.5 · a) — **9.0** — 151 pts, 3G 5A, 32 starts
  * **Alderete** (£5 · a) — **8.0** — 125 pts, 1G 1A, 32 starts
  * **Ballard** (£5 · a) — **8.4** — 116 pts, 2G 2A, 24 starts
  * **Hume** (£4.5 · a) — **8.2** — 110 pts, 2G 1A, 34 starts
  * **Reinildo** (£4.5 · a) — **6.8** — 74 pts, 0G 2A, 23 starts
  * **Seelt** (£4.5 · a) — **4.5** — 2 pts, 1 starts
  * **Meunier** (£4.5 · a) — **3.5** — 0 PL mins / promoted or new
  * **O'Nien** (£4 · a) — **4.5** — 26 pts, 0G 1A, 5 starts
  * **Masuaku** (£4 · a) — **4.5** — 1 pts, 2 starts
  * **Hjelde** (£4 · a) — **3.5** — 0 PL mins / promoted or new


## Decision notes

1. **Dubravka ≠ Spurs starter** — cover only; EO trap.
2. **Kinsky = Spurs set-and-forget** under De Zerbi.
3. **No reliable playing £4.0 GK** at launch — dual £4.5 preferred.
4. **Trafford → LEE** terms agreed — Perri/LEE GK band may flip after announce.
5. **Amenda → COV** demotes Thomas BB floor until friendly XI clears.
6. **O'Shea ≻ Diop** for IPS £4.0 (RoleScore N vs B).
7. Ratings ignore repo xP; re-check XI leaks before GW1.

## Checklist before GW1

- [ ] Kinsky starts Spurs pre-season finales
- [ ] Vicario exit / Dubravka still cover
- [ ] Trafford announced + Perri exit path
- [ ] Sage XI still uses Mitchell/Muñoz as WBs
- [ ] Glasner XI still uses N.Williams RWB
- [ ] Coventry CB: Thomas vs Amenda vs van Ewijk
- [ ] Any new £4.0–£4.5 GK loan that actually starts

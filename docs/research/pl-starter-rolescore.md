# FPL 2026/27 — Starter RoleScore Baseline

**Updated**: 2026-07-29T22:18:00+07:00  
**Data stamp**: FPL bootstrap / `players.parquet` **2026-07-29 ~22:17 ICT** · entry **822158** auth  
**Season**: 2026/27 pre-season · GW1 deadline Fri 21 Aug 2026  
**Purpose**: Minutes-aware starter baseline for squad building — not GW1 XI only  
**Downstream**: [`bb-then-wc-strategy.md`](bb-then-wc-strategy.md) · [`gkp-def-budget-ratings.md`](gkp-def-budget-ratings.md)  
**Supersedes**: dated `20260728-*` / `20260729-*` copies (renamed to stable slugs)

**Sources**
- Primary stats: FPL API prior-season totals in live bootstrap (mins, starts, threat, xG/xA, CS)
- External XI: [FPL Dashboard / Meerkat](https://fpl.page/article/fpl-gw1-predicted-lineups-2627) (**28 Jul 2026**) · club press
- Transfer overlay: Welbeck → CHE medical / 2yr terms (Romano) · Trafford LEE £40m+£5m terms · Lacroix CHE (£52m) · Amenda COV £17m+

## Agent Prompt

```
Full redo docs/research/pl-starter-rolescore.md

1. uv run python -m commands.refresh_data
2. Keep Method (tiers N/R/B/X + sample flags + RoleScore formula) unchanged unless user asks.
3. Recompute Ext from Meerkat/FFS/club press; recompute RoleScore shortlist from players.parquet (prices, starts, mps, thr90, xGI90).
4. Refresh case dossiers, club cards, clarity ranking, open battles. Apply latest transfer overlay (Welbeck/Rutter, Trafford, Lacroix, Amenda, etc.).
5. Update **Updated** (ISO+timezone) + **Data stamp**. Filename stays pl-starter-rolescore.md. Cross-link bb-then-wc-strategy.md + gkp-def-budget-ratings.md.
6. Scratch under .tmp/agent/ only; delete when done.
```

---

## Method

### Tiers (external verdict)

| Tier | Code | Start share when fit | Use |
| --- | --- | --- | --- |
| Nailed | N | ≥ ~85% | Core shortlist |
| Regular | R | ~60–84% | In scope; flag risk |
| Battle | B | ~30–59% | Named thesis only |
| Reserve | X | < ~30% | Out of scope |

### Why raw 2025/26 totals mislead

| Flag | Meaning | How to read |
| --- | --- | --- |
| **IRONMAN** | ≥28 starts · ≥85 mins/start | Trust volume + rates |
| **LIMITED_SAMPLE** | 10–27 starts · ≥900 mins | Trust **per-90** + Ext; totals understate ceiling |
| **THIN** | <10 starts | Ext dominates; rates only if mins/start ~90 |
| **NO_PL_MINS** | Promoted / new | Ext + Champ/career only — bootstrap zeros |

**Ballard:** 24 starts / 2144 mins but **89.3 mps** · **thr90 15.5** (elite DEF ≥10 starts). Injury-limited start *count*, not soft intensity. Meerkat strongest SUN XI includes Ballard 🟢.

**Isak / Kinsky:** THIN at current clubs. Prefer Ext + per-90. Isak = **R lean** (preferred 9, fitness-gated). Kinsky = **N** De Zerbi No.1 (~90%).

### RoleScore (0–100)

```text
Ext map: N=100, R=70, B=40, X=10  (R lean / N lean → interpolate, e.g. 85)
AttackProxy: DEF = threat/90 ÷ 20; MID/FWD = xGI/90 ÷ 0.6; GKP = CS÷15  (capped)
MgrPen: new manager −5..−10; promoted club −15

IRONMAN/OK:
  0.45·Ext + 0.25·(starts/38·100) + 0.15·(mins_per_start/90·100) + 0.15·AttackProxy + MgrPen

LIMITED / THIN:
  0.50·Ext + 0.20·volume + 0.15·mps + 0.15·AttackProxy + MgrPen

NO_PL_MINS:
  0.70·Ext + 0.30·50 + MgrPen
```

**Rule:** pick on **Ext + mins/start + per-90**, not raw points alone. RoleScore = sort key, not projection.

---

## Case-by-case (BB / strategy relevant)

### O'Shea vs Diop / Greaves / Davis (IPS £4.0)

| Player | Ext | RoleScore | PL 25/26 | Why |
| --- | --- | ---: | --- | --- |
| **O'Shea** | N | **70** | NO_PL_MINS | Captain; clearest week-in starter under O’Neil |
| Greaves | R | 49 | NO_PL_MINS | Needs back-3 locked with O’Shea |
| Davis | R | 49 | NO_PL_MINS | FB/WB lean; system unknown |
| Diop | B | **27** | THIN | Right-sided CB vs captain; EO 20.8% trap |

**Pick O'Shea for BB floor.** Diop popular ≠ default.

### Ampadu vs Mainoo / Aaronson / Stach (LEE £5.5 flex)

| Player | Ext | RoleScore | starts | mps | xGI90 | Why |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| **Ampadu** | N | **86** | 35 | 89.1 | 0.13 | Meerkat 🟢; DC path |
| Stach | R | 71 | 28 | 84.6 | 0.28 | Partner when fit |
| **Mainoo** | B | **46** | 16 | 103* | 0.10 | Mid-trio rotation |

\*High mps on few starts ≠ nailed. **Ampadu not Mainoo** at same £5.5.

### Ballard vs Maguire vs Shaw vs Mukiele

| Player | Ext | RoleScore | starts | mps | **thr90** | Flag | Why |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| Shaw | N | 86 | 38 | 84.7 | 2.7 | OK | Carrick LB lock |
| Mukiele | N | 86 | 32 | 87.0 | 7.8 | IRONMAN | Safer SUN if Ballard soft |
| Mitchell | N | 84 | 36 | 90.4 | 6.7 | IRONMAN | Value WB |
| Kayode | N | 87 | 37 | 88.1 | 3.6 | IRONMAN | Minutes king |
| **Ballard** | R | **74** | 24 | **89.3** | **15.5** | LIMITED | Meerkat strongest XI; Europa watch |
| Maguire | R | 67 | 19 | 86.8 | 10.0 | LIMITED | De Ligt out until autumn rental |

### Bruno vs Palmer (captain engine)

| Player | Ext | RoleScore | starts | mps | xGI90 | Why |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| **B.Fernandes** | N | **98** | 35 | 87.6 | 0.68 | HUL/IPS GW1–2 armband |
| Palmer | N | 83 | 24 | 81.4 | 0.60 | LIMITED; Alonso lock; weaker early FDR |

### Wirtz vs Szoboszlai (LIV)

| Player | Ext | RoleScore | starts | mps | xGI90 / thr90 | Why |
| --- | --- | ---: | ---: | ---: | --- | --- |
| Szoboszlai | N | 84 | 36 | 89.8 | 0.32 / 11.6 | Default LIV mid |
| Wirtz | R | 67 | 27 | 87.9 | **0.45 / 25.2** | Meerkat XI 🟢; Iraola-new → still confirm |

**Double default (Szobo + Isak); triple if Wirtz friendlies lock.** Meerkat already lists Wirtz — raises odds vs early Jul.

### Kinsky vs Leno vs Verbruggen

| Player | Ext | RoleScore | starts | mps | Flag | Why |
| --- | --- | ---: | ---: | ---: | --- | --- |
| Verbruggen | N | 95 | 38 | 90 | IRONMAN | Dual-lock half |
| Leno | N | 84 | 38 | 90 | IRONMAN | Safer CS history |
| **Kinsky** | N | **71** | 7 | 90 | THIN | De Zerbi No.1; sample tiny |

Never pair Kinsky + Dubravka as dual starters.

### Thomas vs van Ewijk (COV) BB floor

| Player | Ext | RS | Caveat |
| --- | --- | ---: | --- |
| **Thomas** | R→**B** if Amenda starts | 49 | Champ DEFcon; **Amenda £17m+** — Meerkat expects into side |
| **van Ewijk** | R / N lean RB | 49 | Safer mins (EO 17%); weaker DEFcon |

**BB floor:** prefer **van Ewijk** until friendlies clear Thomas over Amenda; live 822158 still holds Thomas — kill switch armed.

### Anderson (MCI) — avoid DEFcon repeat

Ext R · RoleScore 68 · 37 starts ironman at prior club. Role change into City possession ≠ Forest pressing DEFcon. Meerkat 🟢 — high volume, wrong FPL job.

### Rutter vs Kostoulas / Tzimas (BHA #9 after Welbeck → CHE)

**Transfer:** Welbeck agreed CHE two-year deal; medical next; Brighton approved. Treat **gone for XI** until collapse. Meerkat: “decision about starting #9”; only Groß 🟢 among BHA attackers.

| Player | Ext | RoleScore | starts | mps | xGI90 | thr90 | Flag | Why |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| **Georginio (Rutter)** | **R lean** | **75** | 20 | 88.8 | 0.29 | 22.7 | LIMITED | FPL FWD £5.5; preferred #9 path |
| Welbeck | was N → **B at CHE** | — | 26 | 86.5 | 0.55 | 32.1 | LIMITED | Experience 9 behind João Pedro |
| Kostoulas | B | — | 2 | — | — | — | THIN | Teen CF; Conference minutes |
| Tzimas | X/B | — | 1 | — | — | — | THIN | Knee — not GW1 lock |

**Pick thesis:** Rutter = minutes-aware BHA #9 while Welbeck exits — Ext **R lean** (map 85 → RS **75**). Kill switches: Conf. League CF rotation; Kostoulas/Tzimas; new CF. **Already in live 822158 bench** — confirm 90s in friendlies before XI.

---

## Core shortlist table (verified 2026-07-29 ~22:17 ICT)

Prices = live bootstrap. RoleScore from formula above.

### High confidence (RoleScore ≥ 80 or clear N ironman)

| Player | Pos | Club | £ | Ext | RS | starts | mps | thr90 | xGI90 | Flag |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| B.Fernandes | MID | MUN | 12.0 | N | 97.6 | 35 | 87.6 | 18.0 | 0.68 | IRONMAN |
| Verbruggen | GKP | BHA | 4.5 | N | 95.0 | 38 | 90.0 | — | — | IRONMAN |
| Calvert-Lewin | FWD | LEE | 6.0 | N | 93.5 | 30 | 90.7 | 33.9 | 0.55 | IRONMAN |
| N.Williams | DEF | NFO | 5.0 | N | 91.5 | 36 | 89.0 | 10.7 | 0.17 | IRONMAN |
| Ndiaye | MID | EVE | 6.0 | N | 89.5 | 32 | 86.9 | 18.7 | 0.36 | IRONMAN |
| Haaland | FWD | MCI | 15.5 | N | 88.8 | 34 | 86.9 | 46.3 | 0.86 | IRONMAN |
| Wilson | MID | LEE | 6.5 | N | 88.9 | 32 | 83.6 | 20.2 | 0.36 | OK |
| Cash | DEF | AVL | 4.5 | N | 87.1 | 34 | 88.7 | 6.6 | 0.12 | IRONMAN |
| Kayode | DEF | BRE | 4.5 | N | 86.7 | 37 | 88.1 | 3.6 | 0.12 | IRONMAN |
| Mukiele | DEF | SUN | 5.5 | N | 86.4 | 32 | 87.0 | 7.8 | 0.14 | IRONMAN |
| Shaw | DEF | MUN | 4.5 | N | 86.2 | 38 | 84.7 | 2.7 | 0.08 | OK |
| Ampadu | MID | LEE | 5.5 | N | 86.2 | 35 | 89.1 | 4.8 | 0.13 | IRONMAN |
| Xhaka | MID | SUN | 5.5 | N | 84.7 | 32 | 90.7 | 3.1 | 0.15 | IRONMAN |
| Rogers | MID | CHE | 7.5 | N | 83.8 | 37 | 88.6 | 23.9 | 0.31 | IRONMAN |
| Szoboszlai | MID | LIV | 7.0 | N | 83.7 | 36 | 89.8 | 11.6 | 0.32 | IRONMAN |
| Mitchell | DEF | CRY | 4.5 | N | 83.7 | 36 | 90.4 | 6.7 | 0.11 | IRONMAN |
| Palmer | MID | CHE | 9.5 | N | 83.2 | 24 | 81.4 | 25.2 | 0.60 | LIMITED |
| Mbeumo | MID | MUN | 8.0 | R | 80.6 | 31 | 84.2 | 30.4 | 0.58 | OK |

### In-scope with caveats

| Player | Pos | Club | £ | Ext | RS | starts | mps | thr90 | xGI90 | Flag | Caveat |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| **Georginio** | FWD | BHA | 5.5 | R lean | **75.2** | 20 | 88.8 | 22.7 | 0.29 | LIMITED | Preferred #9 post-Welbeck; Conf. risk |
| Ballard | DEF | SUN | 5.0 | R | 74.2 | 24 | 89.3 | **15.5** | 0.13 | LIMITED | Europa; Meerkat strongest XI |
| Stach | MID | LEE | 6.0 | R | 71.0 | 28 | 84.6 | 12.0 | 0.28 | OK | Fit-dependent |
| Kinsky | GKP | TOT | 4.5 | N | 70.7 | 7 | 90.0 | — | — | THIN | No.1 by De Zerbi |
| Wright | FWD | COV | 5.5 | N | 70.0 | 0 | — | — | — | NO_PL | Champ pens |
| O'Shea | DEF | IPS | 4.0 | N | 70.0 | 0 | — | — | — | NO_PL | Captain; formation watch |
| Anderson | MID | MCI | 6.5 | R | 68.1 | 37 | 90.1 | 8.4 | 0.21 | IRONMAN | **Avoid DEFcon thesis** |
| Wirtz | MID | LIV | 7.5 | R | 67.2 | 27 | 87.9 | **25.2** | 0.45 | LIMITED | XI-gated triple; Meerkat 🟢 |
| Maguire | DEF | MUN | 5.0 | R | 67.0 | 19 | 86.8 | 10.0 | 0.09 | LIMITED | GW1–3 rental only |
| Isak | FWD | LIV | 9.0 | R lean | 61.8 | 8 | 86.8 | 24.8 | 0.35 | THIN | Fitness-gated preferred 9 |
| Thomas | DEF | COV | 4.0 | R→B | 49.0 | 0 | — | — | — | NO_PL | Amenda kill switch |
| van Ewijk | DEF | COV | 4.0 | R | 49.0 | 0 | — | — | — | NO_PL | Safer mins alt |
| Mainoo | MID | MUN | 5.5 | B | 45.8 | 16 | 103 | 5.1 | 0.10 | LIMITED | Not BB flex |
| Diop | DEF | IPS | 4.0 | B | 26.8 | 8 | 101 | 3.4 | 0.09 | THIN | EO trap; only with back 3 |
| Welbeck | FWD | BHA* | 6.0 | B@CHE | — | 26 | 86.5 | 32.1 | 0.55 | LIMITED | *medical→CHE; fade |

---

## Club cards (Meerkat 28 Jul + transfer overlay 29 Jul)

Format: manager · **N** / **R** · battles. Meerkat 🟢 = predicted nailed.

### Arsenal — Arteta
- **N**: Raya, Gabriel, Timber, Rice, Saka  
- **R**: Mosquera (Saliba long-term), LB battle, Gyökeres  

### Aston Villa — Emery
- **N**: Martinez, Konsa, Cash, Watkins, Kamara lean  
- **R**: midfield after Rogers exit  

### Bournemouth — Rose (new)
- **N**: Petrović, Truffert, Scott, Tavernier lean  
- **Uncertainty**: high — new manager + Europe  

### Brentford — Andrews
- **N**: Kelleher, Collins, Kayode, Schade, Thiago  
- **Stable spine**

### Brighton — Hürzeler
- **N**: Verbruggen · Groß lean (Meerkat 🟢)  
- **R lean**: **Georginio** preferred #9 after **Welbeck → CHE medical**  
- **R**: Kadıoğlu, Dunk, Vušković, Wieffer — Conf. League noise  
- **B**: attack share; Kostoulas / Tzimas CF depth  
- **Out path**: Welbeck (treat gone); Mitoma hamstring watch  

### Chelsea — Alonso (new)
- **N**: Sánchez, Caicedo, Enzo, Palmer, João Pedro, Rogers · **Lacroix** (deal ~£52m)  
- **Battles**: shape 3 vs 4; WB; James as RCB in back-5 lean  
- **In**: **Welbeck** medical / 2yr — **B starts** behind João Pedro  
- **Flags**: Fofana ban; Delap / Jackson exit risk rises with Welbeck  

### Coventry — Lampard (promoted)
- **N lean**: Wright  
- **R**: van Ewijk; Thomas **only if** starts over **Amenda** (Meerkat expects Amenda in)  
- All provisional  

### Crystal Palace — Sage (new)
- **N**: Henderson, Mitchell, Muñoz, Sarr lean, Richards lean  
- **Risk**: **Lacroix → CHE** — CB flux; Europa  

### Everton — Moyes
- **N**: Pickford, Tarkowski, Ndiaye, Dewsbury-Hall lean  
- **Note**: Ndiaye exit rumour — monitor  

### Fulham — Arbeloa (new)
- **N**: Leno · Robinson, Bassey, Iwobi lean  
- Thin attack N list  

### Hull — promoted
- **N lean**: McBurnie; **Butland** #1  
- Fade defence early  

### Ipswich — O’Neil (promoted)
- **N**: O'Shea lean · Matusiwa lean  
- **R/B**: Greaves, Davis, Diop (back 3?)  
- Highest uncertainty  

### Leeds — Farke
- **N**: Ampadu, Wilson, Calvert-Lewin, Stach (fit) · **Trafford*** (terms agreed — Meerkat 🟢*)  
- **R**: Rodon, Gudmundsson; GK flips once Trafford announced / Perri exits  

### Liverpool — Iraola (new)
- **N**: Alisson, Virgil, Szoboszlai, Gravenberch · Kerkez lean · Jacquet CB lean  
- **R**: Wirtz (Meerkat XI), Isak (fitness), Mac Allister  
- Confirm Wirtz in friendlies before triple  

### Man City — Maresca (new)
- **N**: Donnarumma, Haaland, Guéhi lean, Semenyo lean, Anderson lean  
- Classic rotation elsewhere  

### Man Utd — Carrick
- **N**: Lammens, Shaw, B.Fernandes, Dalot lean  
- **R**: Maguire (De Ligt out until autumn), Mbeumo / Cunha near-every-week  
- **B**: Mainoo / Santos / Tielemans mid trio  

### Newcastle — Howe
- Thin N list; **Bruno G** Arsenal saga → CM risk; Thiaw / Pope / Livramento lean  

### Nott'm Forest — Glasner
- **N**: Sels, N.Williams, Milenković, Murillo lean, Gibbs-White, Aina lean  

### Sunderland — Le Bris
- **N**: Roefs, Mukiele, Alderete, Reinildo lean, Xhaka, Le Fée, Sadiki, Brobbey  
- **R**: **Ballard** in strongest XI when fit (Meerkat 🟢); Europa → more rotation  

### Spurs — De Zerbi
- **N**: **Kinsky** (~90% No.1), Van de Ven, Van Hecke, Porro  
- Never dual-start Kinsky + Dubravka  

---

## Clarity ranking

| Clarity | Clubs |
| --- | --- |
| High | BRE, EVE, LEE attack/mid, MUN attack, SUN spine |
| Medium | AVL, CRY, NFO, TOT (GK+CB), LIV (confirm Wirtz) |
| Low | BHA (#9 clearer; rest noisy), CHE, MCI, FUL, NEW, BOU |
| Very low | COV, HUL, IPS |

---

## Open battles before lock

1. Ipswich back 3 vs 4 (O'Shea±Diop±Greaves)  
2. Sunderland CB (Ballard fitness vs Mukiele/Alderete/Reinildo)  
3. Coventry CB (**Thomas vs Amenda**) — else van Ewijk  
4. Liverpool Wirtz under Iraola · Isak fitness  
5. United CB (Maguire vs Martinez/Yoro while De Ligt out) + mid trio  
6. Palace CB after Lacroix → CHE  
7. Leeds GK (**Trafford** terms — await announcement / Perri exit)  
8. **Brighton #9** — Rutter lock vs Kostoulas/Tzimas/Conf. · confirm Welbeck medical clears  
9. Spurs front / LB · City non-Haaland · Ndiaye sale · CHE CF pecking order post-Welbeck  

---

## How to use

1. Filter analysis to Ext **N+R** (and BB floors with named thesis).  
2. Prefer **mps ≥ 85** when Ext tied.  
3. Prefer **thr90 / xGI90** when flag = LIMITED/THIN.  
4. Promoted: Ext first; RoleScore capped until PL mins.  
5. Feed pick disputes into [`bb-then-wc-strategy.md`](bb-then-wc-strategy.md).

## Redo

`uv run python -m commands.refresh_data` → recompute RoleScore CSV → update **Updated** / **Data stamp**. See Agent Prompt above.

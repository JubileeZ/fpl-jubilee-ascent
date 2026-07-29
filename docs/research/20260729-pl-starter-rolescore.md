# FPL 2026/27 — Starter RoleScore Baseline

**Date**: 2026-07-29  
**Data stamp**: FPL bootstrap / `players.parquet` refreshed **2026-07-29 ~11:00 ICT**  
**Season**: 2026/27 pre-season · GW1 deadline Fri 21 Aug 2026  
**Purpose**: Minutes-aware starter baseline for squad building — not GW1 XI only  
**Supersedes**: `20260728-pl-nailed-regular-starters.md` (deleted 2026-07-29)  
**Downstream**: [`20260729-bb-then-wc-strategy.md`](20260729-bb-then-wc-strategy.md)

**Sources**
- Primary stats: FPL API prior-season totals in live bootstrap (mins, starts, threat, xG/xA, CS)
- External XI: [FPL Dashboard / Meerkat](https://fpl.page/article/fpl-gw1-predicted-lineups-2627) (**28 Jul 2026** = primary refresh) · [FFS team-news](https://www.fantasyfootballscout.co.uk/team-news/) still stamped **21–22 Jul** (unchanged as of 29 Jul) · [PL Scout](https://www.premierleague.com/en/news/4681112/early-scout-selection-the-best-fantasy-squad-for-202627) · club press (Kinsky; Ballard; O’Shea; Amenda; De Ligt)
- Case digests (merged 29 Jul): DEF / MID-FWD-GK / club-XI sub-research

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

**Ballard example:** 24 starts / 2144 mins looks mid-table, but **89.3 mins/start** and **threat/90 = 15.5** (elite among DEF with ≥10 starts). Early-season injury → low start count, not low intensity when selected. Pre-season 2026: ankle surgery return, 45 mins vs Liverpool.

**Isak / Kinsky:** THIN PL samples at current clubs (Isak injury-wrecked ~694 LIV mins; Kinsky late De Zerbi run). Prefer Ext + per-90 over totals. Isak = **R/N lean** (preferred 9, fitness-gated) — not ironman N until friendlies clear.

### RoleScore (0–100)

```text
Ext map: N=100, R=70, B=40, X=10
AttackProxy: DEF = threat/90 ÷ 20; MID/FWD = xGI/90 ÷ 0.6; GKP = CS÷15  (capped)
MgrPen: new manager −5..−10; promoted club −15

IRONMAN/OK:
  0.45·Ext + 0.25·(starts/38·100) + 0.15·(mins_per_start/90·100) + 0.15·AttackProxy + MgrPen

LIMITED / THIN:
  0.50·Ext + 0.20·volume + 0.15·mps + 0.15·AttackProxy + MgrPen   # Ext upweighted

NO_PL_MINS:
  0.70·Ext + 0.30·50 + MgrPen   # no fake PL rates
```

**Rule:** pick on **Ext + mins/start + per-90**, not raw points alone. RoleScore is a sort key, not a projection.

---

## Case-by-case (BB / strategy relevant)

### O'Shea vs Diop / Greaves / Davis (IPS £4.0)

| Player | Ext | RoleScore | PL 25/26 | Why |
| --- | --- | ---: | --- | --- |
| **O'Shea** | N | **70** | NO_PL_MINS | Club captain; local press: only clear week-in starter under O’Neil |
| Greaves | R | 49 | NO_PL_MINS | Needs back-3 to be locked with O’Shea |
| Davis | R | 49 | NO_PL_MINS | FB/WB lean; system unknown |
| Diop | B | 29 | THIN (Fulham mins) | Right-sided CB vs captain; only both start if back 3 |

**Pick O'Shea for BB floor** — highest Ext among £4.0 IPS DEF; Diop is the rival not the default. Re-check formation in friendlies.

### Ampadu vs Mainoo / Aaronson / Stach (LEE £5.5 flex)

| Player | Ext | RoleScore | starts | mps | xGI90 | Why |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| **Ampadu** | N | **86** | 35 | 89.1 | 0.13 | Meerkat 🟢; PL Scout DC standout at £5.5 |
| Stach | R | 71 | 28 | 84.6 | 0.28 | Partner when fit; not the cheaper lock |
| Aaronson | B | 59 | 30 | 81.6 | 0.30 | Attack upside; rotation |
| **Mainoo** | B | **48** | 16 | 103* | 0.10 | WC rest + Santos/Tielemans/Mainoo trio rotation; LIMITED_SAMPLE |

\*High mps on few starts ≠ nailed. **Ampadu not Mainoo:** price same £5.5, Ampadu has ironman N + DC path; Mainoo is B with GW1 rest risk.

### Ballard vs Maguire vs Shaw vs Mukiele

| Player | Ext | RoleScore | starts | mps | **thr90** | Flag | Why |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| Shaw | N | 86 | 38 | 84.7 | 2.7 | OK | Carrick LB lock; low attack |
| Mukiele | N | 86 | 32 | 87.0 | 7.8 | IRONMAN | Safer SUN DEF if Ballard soft |
| Mitchell | N | 84 | 36 | 90.4 | 6.7 | IRONMAN | Better than “CS-only WB” |
| Kayode | N | 87 | 37 | 88.1 | 3.6 | IRONMAN | Minutes king; low threat |
| **Ballard** | R | **74** | 24 | **89.3** | **15.5** | LIMITED | Per-90 CB threat elite; XI in strongest SUN; ankle monitor |
| Maguire | R | 67 | 19 | 86.8 | 10.0 | LIMITED | De Ligt out until autumn; GW1–3 rental |

**Ballard thesis holds on rates:** threat/90 ≫ Maguire/Shaw; plays full 90 when picked. Risk = fitness ramp (45' vs LIV) + Europa — confirm full 90s before BB bank. Maguire = GW1–3 rental while **De Ligt out until autumn**; Shaw = safer minutes / lower ceiling.

### Bruno vs Palmer (captain engine)

| Player | Ext | RoleScore | starts | mps | xGI90 | Why |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| **B.Fernandes** | N | **100** | 35 | 87.6 | 0.68 | HUL/IPS GW1–2 armband |
| Palmer | N | 81 | 24 | 81.4 | 0.60 | LIMITED; Alonso lock but weaker early fixtures |

### Wirtz vs Szoboszlai (LIV)

| Player | Ext | RoleScore | starts | mps | xGI90 thr90 | Why |
| --- | --- | ---: | ---: | ---: | --- | --- |
| Szoboszlai | N | 82 | 36 | 89.8 | 0.32 / 11.6 | Default LIV mid |
| Wirtz | R | 65 | 27 | 87.9 | 0.45 / **25.2** | Meerkat XI; Iraola new → still XI-gated for triple |

**Double default (Szobo + Isak); triple only if Wirtz friendlies lock.** Wirtz rates scream starter; RoleScore docks new-manager Ext.

### Kinsky vs Leno vs Verbruggen

| Player | Ext | RoleScore | starts | mps | Flag | Why |
| --- | --- | ---: | ---: | ---: | --- | --- |
| Verbruggen | N | 95 | 38 | 90 | IRONMAN | Dual-lock half |
| Leno | N | 84 | 38 | 90 | IRONMAN | Safer CS history; user prefers Kinsky diff |
| **Kinsky** | N | **66** | 7 | 90 | THIN | De Zerbi No.1 + new deal; sample tiny — Ext over stats |

Never pair Kinsky + Dubravka as dual starters.

### Thomas vs van Ewijk (COV) BB floor

| Player | Ext | RS | Caveat |
| --- | --- | ---: | --- |
| **Thomas** | R→**B** if Amenda starts | 49 | Champ DEFcon + set-piece; **Amenda £17m** challenges CB |
| **van Ewijk** | R / N lean RB | — | 43/44 Champ starts; safer mins, weaker DEFcon |

**BB floor:** Thomas only if friendly XI confirms over Amenda; else **van Ewijk** for start security (same £4.0).

### Anderson (MCI) — avoid DEFcon repeat

Ext R · RoleScore 66 · 37 starts ironman at prior club. **Role change** into City possession ≠ Forest pressing DEFcon. High volume, wrong job.

---

## Core shortlist table (verified 2026-07-29)

Prices = live bootstrap. RoleScore from formula above.

### High confidence (RoleScore ≥ 80 or clear N ironman)

| Player | Pos | Club | £ | Ext | RS | starts | mps | thr90 | xGI90 | Flag |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| B.Fernandes | MID | MUN | 12.0 | N | 99.6 | 35 | 87.6 | 18.0 | 0.68 | IRONMAN |
| Verbruggen | GKP | BHA | 4.5 | N | 95.0 | 38 | 90.0 | — | — | IRONMAN |
| Calvert-Lewin | FWD | LEE | 6.0 | N | 93.6 | 30 | 90.7 | 33.9 | 0.55 | IRONMAN |
| Haaland | FWD | MCI | 15.5 | N | 89.8 | 34 | 86.9 | 46.3 | 0.86 | IRONMAN |
| Ndiaye | MID | EVE | 6.0 | N | 89.5 | 32 | 86.9 | 18.7 | 0.36 | IRONMAN |
| Wilson | MID | LEE | 6.5 | N | 88.9 | 32 | 83.6 | 20.2 | 0.36 | OK |
| Cash | DEF | AVL | 4.5 | N | 87.1 | 34 | 88.7 | 6.6 | 0.12 | IRONMAN |
| Kayode | DEF | BRE | 4.5 | N | 86.7 | 37 | 88.1 | 3.6 | 0.12 | IRONMAN |
| N.Williams | DEF | NFO | 5.0 | N | 86.5 | 36 | 89.0 | 10.7 | 0.17 | IRONMAN |
| Mukiele | DEF | SUN | 5.5 | N | 86.4 | 32 | 87.0 | 7.8 | 0.14 | IRONMAN |
| Shaw | DEF | MUN | 4.5 | N | 86.2 | 38 | 84.7 | 2.7 | 0.08 | OK |
| Ampadu | MID | LEE | 5.5 | N | 86.2 | 35 | 89.1 | 4.8 | 0.13 | IRONMAN |
| Xhaka | MID | SUN | 5.5 | N | 84.8 | 32 | 90.7 | 3.1 | 0.15 | IRONMAN |
| Mitchell | DEF | CRY | 4.5 | N | 83.7 | 36 | 90.4 | 6.7 | 0.11 | IRONMAN |
| Szoboszlai | MID | LIV | 7.0 | N | 81.7 | 36 | 89.8 | 11.6 | 0.32 | IRONMAN |
| Palmer | MID | CHE | 9.5 | N | 81.2 | 24 | 81.4 | 25.2 | 0.60 | LIMITED |
| Mbeumo | MID | MUN | 8.0 | R | 80.6 | 31 | 84.2 | 30.4 | 0.58 | OK |

### In-scope with caveats (use per-90 / Ext)

| Player | Pos | Club | £ | Ext | RS | starts | mps | thr90 | xGI90 | Flag | Caveat |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| Ballard | DEF | SUN | 5.0 | R | 74.2 | 24 | 89.3 | **15.5** | 0.13 | LIMITED | Ankle return; Europa rotation |
| Stach | MID | LEE | 6.0 | R | 71.0 | 28 | 84.6 | 12.0 | 0.28 | OK | Fit-dependent |
| Wright | FWD | COV | 5.5 | N | 70.0 | 0 | — | — | — | NO_PL | Champ pens |
| O'Shea | DEF | IPS | 4.0 | N | 70.0 | 0 | — | — | — | NO_PL | Captain; formation watch |
| Maguire | DEF | MUN | 5.0 | R | 67.0 | 19 | 86.8 | 10.0 | 0.09 | LIMITED | GW1–3 rental only |
| Isak | FWD | LIV | 9.0 | R lean | 67.3 | 8 | 86.8 | 24.8 | 0.35 | THIN | Fitness-gated preferred 9 |
| Kinsky | GKP | TOT | 4.5 | N | 65.7 | 7 | 90.0 | — | — | THIN | No.1 by De Zerbi; sample thin |
| Wirtz | MID | LIV | 7.5 | R | 65.2 | 27 | 87.9 | **25.2** | 0.45 | LIMITED | XI-gated triple |
| Anderson | MID | MCI | 6.5 | R | 66.1 | 37 | 90.1 | 8.4 | 0.21 | IRONMAN | **Avoid DEFcon thesis** · GW1 WC |
| Thomas | DEF | COV | 4.0 | R→B | 49.0 | 0 | — | — | — | NO_PL | Amenda kill switch |
| Mainoo | MID | MUN | 5.5 | B | 48.0 | 16 | 103 | 5.1 | 0.10 | LIMITED | Not BB flex |
| Diop | DEF | IPS | 4.0 | B | 28.7 | 8 | 101 | 3.4 | 0.09 | THIN | Only with back 3 |

---

## Club cards (refreshed 28–29 Jul 2026)

Format: manager · **N** / **R** · battles. Meerkat 🟢 = predicted nailed.

### Arsenal — Arteta
- **N**: Raya, Gabriel, Timber, Rice, Saka  
- **R**: Mosquera (Saliba long-term), LB battle, Gyökeres  
- **Out**: Saliba long-term  

### Aston Villa — Emery
- **N**: Martinez, Konsa, Cash, Watkins  
- **R**: midfield after Rogers exit; Kamara path  

### Bournemouth — Rose (new)
- **N**: Petrović, Truffert, Scott, Tavernier lean  
- **Uncertainty**: high — new manager + Europe  

### Brentford — Andrews
- **N**: Kelleher, Collins, Kayode, Schade, Thiago  
- **Stable spine**

### Brighton — Hürzeler
- **N**: Verbruggen  
- **R**: high rotation; **Welbeck → CHE talks** (27 Jul) → #9 unsettled  
- High B risk for FPL  

### Chelsea — Alonso (new)
- **N**: Sánchez, Caicedo, Enzo, Palmer, João Pedro, Rogers  
- **Battles**: shape 3 vs 4; WB; **Lacroix agreed ~£52m** (BBC 24 Jul) → CB up  
- **Flags**: Fofana ban; Enzo/James GW1 WC  

### Coventry — Lampard (promoted)
- **N lean**: Wright  
- **R**: van Ewijk; Thomas **only if** starts over **Amenda**  
- All provisional  

### Crystal Palace — Sage (new)
- **N**: Henderson, Mitchell, Muñoz, Sarr lean  
- **Risk**: **Lacroix → CHE** — CB flux; Europa  

### Everton — Moyes
- **N**: Pickford, Tarkowski, Ndiaye, Dewsbury-Hall lean  
- **Note**: Ndiaye exit rumour — monitor  

### Fulham — Arbeloa (new)
- **N**: Leno  
- **R**: Robinson, Bassey, Iwobi — thin attack N list  

### Hull — promoted
- **N lean**: McBurnie; **Butland** #1 (clearer than dual GK)  
- Fade defence early  

### Ipswich — O’Neil (promoted)
- **N**: O'Shea, Matusiwa lean  
- **R/B**: Greaves, Davis, Diop (back 3?), Emersonn  
- Highest uncertainty  

### Leeds — Farke
- **N**: Ampadu, Wilson, Calvert-Lewin, Stach (fit)  
- **R**: Rodon, Gudmundsson; **Trafford** club-record deal close (28 Jul) — GK flips; England WC doubt if signed  

### Liverpool — Iraola (new)
- **N**: Alisson, Virgil, Szoboszlai, Gravenberch  
- **R**: Kerkez, Wirtz, Isak (fitness), Mac Allister (GW1 WC soft), Jacquet CB lean  
- **Still**: confirm Wirtz in friendlies before triple  

### Man City — Maresca (new)
- **N**: Donnarumma, Haaland, Guéhi lean, Semenyo lean, Anderson lean  
- Classic rotation elsewhere; Anderson also GW1 WC doubtful  

### Man Utd — Carrick
- **N**: Lammens, Shaw, B.Fernandes, Dalot lean  
- **R**: Maguire (De Ligt out until autumn), Mbeumo / Cunha near-every-week  
- **B**: Mainoo / Santos / Tielemans mid trio  

### Newcastle — Howe
- Thin N list; **Bruno G** Arsenal saga → CM risk; Thiaw / Pope lean  

### Nott'm Forest — Glasner
- **N**: Sels, N.Williams, Milenković, Murillo lean, Gibbs-White, Aina lean  

### Sunderland — Le Bris
- **N**: Roefs, Mukiele, Alderete, Reinildo lean, Xhaka, Le Fée, Sadiki, Brobbey  
- **R**: **Ballard** in strongest XI when fit; Europa → more rotation  

### Spurs — De Zerbi
- **N**: **Kinsky** (~90% No.1), Van de Ven, Van Hecke, Porro  
- Never dual-start Kinsky + Dubravka  

---

## Clarity ranking

| Clarity | Clubs |
| --- | --- |
| High | BRE, EVE, LEE attack/mid, MUN attack, SUN spine |
| Medium | AVL, CRY, NFO, TOT (GK+CB), LIV (confirm Wirtz) |
| Low | BHA, CHE, MCI, FUL, NEW, BOU |
| Very low | COV, HUL, IPS |

---

## Open battles before lock

1. Ipswich back 3 vs 4 (O'Shea±Diop±Greaves)  
2. Sunderland CB (Ballard fitness vs Mukiele/Alderete/Reinildo)  
3. Coventry CB (**Thomas vs Amenda**) — else van Ewijk  
4. Liverpool Wirtz under Iraola · Isak fitness  
5. United CB (Maguire vs Martinez/Yoro while De Ligt out) + mid trio  
6. Palace CB after Lacroix → CHE  
7. Leeds GK (Trafford close)  
8. Spurs front / LB · City non-Haaland · Ndiaye sale  

---

## How to use

1. Filter analysis to Ext **N+R** (and BB floors with named thesis).  
2. Prefer **mps ≥ 85** when Ext tied.  
3. Prefer **thr90 / xGI90** when flag = LIMITED/THIN.  
4. Promoted: Ext first; RoleScore capped until PL mins.  
5. Feed pick disputes into [`20260729-bb-then-wc-strategy.md`](20260729-bb-then-wc-strategy.md).

## Redo

`uv run python -m commands.refresh_data` → rebuild `.tmp/agent/stats-baseline-*.csv` + RoleScore → update this file’s date stamp.

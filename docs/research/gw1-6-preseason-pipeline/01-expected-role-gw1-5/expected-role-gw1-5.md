# FPL 2026/27 Expected Role (GW1–5) — 20-Club Audit & Mins Priors

**Updated**: 2026-08-15T13:40:00+07:00  
**Data stamp**: FFS Team News + FPL Meerkat scraped 2026-08-13; official overlays 2026-08-15; World Cup 2026 fitness audit; `players.parquet` 2026-07-29  
**Season**: 2026/27  
**Status**: Active Research Model  
**Purpose**: Assign fit-conditional Expected Role, dated Draft Availability, and Participation State priors across all 20 clubs for GW1–5 seeding  
**Scope**: XI Contention Set (scaffold + FFS XI injects); Draft Shortlist = Nailed + Regular; Availability Overlay separately applies `eligible`, `watch`, `exclude_gw1`, `exclude_gw1-5`  
**Related**: [Preseason Pipeline Master README](../README.md) · [Expected Stats (Stage 2)](../02-expected-stats-gw1-5/expected-stats-gw1-5.md) · [GW1–6 Chip Matrix (Stage 3)](../03-gw1-6-chip-wc4-squads/gw1-6-chip-wc4-squads.md)  
**Artifacts**:
- [Expected Role CSV](../../../../data/research/gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.csv)

---

## Sources

- **Primary**: [Fantasy Football Scout Team News](https://www.fantasyfootballscout.co.uk/team-news) — accessed 2026-08-13; predicted XIs (11 per club).
- **Primary**: [FPL GW1 Predicted Line-ups — FPL Meerkat / fpl.page](https://fpl.page/article/fpl-gw1-predicted-lineups-2627) — accessed 2026-08-13; 🟢 nailed markers.
- **Primary**: [Confirmed Summer Transfers — Fantasy Football Scout](https://www.fantasyfootballscout.co.uk/fpl-2026-27-transfer-news-confirmed-summer-signings) via [fpl-summer-transfers.md](../../fpl-preseason-guide/fpl-summer-transfers.md).
- **Primary**: Official club fitness overlays (Saliba, Rodri, Mac Allister, Saka).
- **Repository data**: `data/processed/players.parquet` + `clubs.parquet`.

---

## Agent Prompt & Reproducibility Instructions

```text
Run parameterized GW1-5 Expected Role Rebuild (Stage 1):

1. Command: uv run python docs/research/gw1-6-preseason-pipeline/01-expected-role-gw1-5/refresh_expected_role.py
   - HTTP scrape FFS Team News (https://www.fantasyfootballscout.co.uk/team-news) for 20 predicted XIs (11 per club).
   - HTTP scrape FPL Meerkat (https://fpl.page/article/fpl-gw1-predicted-lineups-2627) for 🟢 nailed starter markers.
   - Inject missing FFS XI starters into contention scaffold from data/processed/players.parquet.
   - Apply conflict rules:
     * Nailed Starter: in FFS XI AND Meerkat 🟢 (0.90/0.05/0.05/85/20)
     * Regular Starter: in exactly one starter signal (0.75/0.10/0.15/80/20)
     * Rotation: previously draft-role but absent from both current signals (0.40/0.25/0.35/70/20)
     * Cameo: bench depth (0.10/0.35/0.55/60/15)
   - Merge API status/chance flags from players.parquet and apply official club availability overlays.
   - Separate fit-role from availability (do not demote fit-role for temporary injury).
   - Export CSV to data/research/gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.csv.
2. If a new Nailed/Regular has no 2025/26 Prior-Season Seed, add CAREER_INDIVIDUAL_RATES in
   02-expected-stats-gw1-5/build_expected_stats.py then run refresh_downstream.py (not a second scrape).
3. Synchronize 20-club markdown tables in expected-role-gw1-5.md with the generated CSV.
4. Verification: uv run pytest, uv run ruff check .
```

---

## Method

1. **HTTP scrape**: FFS predicted XI names per club; Meerkat first 🟢 line per club (HTML-unescaped).
2. **Inject**: FFS XI players missing from scaffold matched via `players.parquet` first/second/web name (rejects `Bruno G.` vs `Bruno Fernandes`; accepts `Van Dijk` vs `Virgil`).
3. **Expected Role assignment**: unanimous dual-source → Nailed; single-source → Regular; lost both signals → Rotation. Same identity matcher as inject.
4. **Availability Overlay**: API chance/status hints, then official overlays. Scoring overlays applied downstream in `availability_priors.py` (Watch haircut; Exclude GW1–5 = GW1–5 only).
5. **Draft Shortlist**: Nailed + Regular with non-`not_role_eligible` availability for human draft / solver ingestion.

---

## Findings

### 1. High-Level Summary & Role Distribution

- Contention set: **564** rows. Roles: Nailed 92 · Regular 158 · Rotation 112 · Cameo 119 · Out of Contention 83.
- Draft Eligible: **250** players (Nailed 92 + Regular 158).
- Availability: eligible 238 · not_role_eligible 287 · exclude_gw1 19 · watch 10 · exclude_gw1-5 10.
- **Injected Starters**: Touré (NEW MID), Steur (NEW MID), Meunier (SUN DEF), Walle Egeli (IPS FWD), Moore (TOT MID), Rushworth (COV GKP).
- **Kinsky (TOT)**: Regular Starter (FFS XI; Meerkat GK not unanimous).
- **Saliba (ARS)**: `exclude_gw1-5`. **Mac Allister (LIV)** / **Saka (ARS)**: `watch`.
- **Bruno Guimarães (ARS)**: transfer overlay applied; Rotation — not in current FFS/Meerkat Arsenal XI. **B.Fernandes (MUN)** and **Virgil (LIV)** nailed (identity match fix; previously swapped/dropped).

### 2. 20-Club Player Role & Draft Availability Breakdown

Complete roster of all 564 players across the 20 Premier League clubs in the FPL API, showing assigned fit-role, baseline starter probability ($p_{\text{start}}$), Draft Availability overlay, and source signals.

#### 1. Arsenal (`ARS`) — 28 players
- **Summary**: Nailed: 2 · Regular: 12 · Rotation: 6 · Cameo: 5 · Out of Contention: 3 | Draft Eligible: 14

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Raya** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Arrizabalaga** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Reserve/third-choice goalkeeper. |
| **Meslier** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Reserve/third-choice goalkeeper. |
| **Gabriel** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Calafiori** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **J.Timber** | DEF | Regular Starter | 0.75 | `exclude_gw1` | First-choice full-back recovering from minor groin strain; expected back GW2. |
| **Mosquera** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **White** | DEF | Regular Starter | 0.75 | `watch` | First-choice right-back competing with Mosquera; resuming full training. |
| **Hincapie** | DEF | Rotation | 0.40 | `not_role_eligible` | Confirmed summer signing; Meerkat notes left-CB usage but Scout starts Calafiori, so minutes shared. |
| **Saliba** | DEF | Rotation | 0.40 | `exclude_gw1-5` | Key defender undergoing back rehabilitation, expected to return around GW5-6. |
| **Dowman** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Lewis-Skelly** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Martinelli** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (Meerkat 🟢 / predicted). |
| **Rice** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (Meerkat 🟢 / predicted). |
| **Saka** | MID | Regular Starter | 0.75 | `watch` | Talisman winger managing workload after international tournament; expected to start or feature heavily. |
| **Tzolis** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Eze** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Madueke** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Zubimendi** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Ødegaard** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Merino** | MID | Cameo | 0.10 | `not_role_eligible` | Squad rotation/bench option outside primary XI contention. |
| **Nelson** | MID | Cameo | 0.10 | `not_role_eligible` | Fringe squad player with limited minutes. |
| **Nwaneri** | MID | Cameo | 0.10 | `not_role_eligible` | Fringe squad player with limited minutes. |
| **Nørgaard** | MID | Cameo | 0.10 | `not_role_eligible` | Fringe squad player with limited minutes. |
| **Fábio Vieira** | MID | Out of Contention | 0.00 | `not_role_eligible` | Academy / developmental reserve not in first-team XI contention. |
| **Gyökeres** | FWD | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Havertz** | FWD | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **G.Jesus** | FWD | Cameo | 0.10 | `not_role_eligible` | Fringe squad player with limited minutes. |

#### 2. Aston Villa (`AVL`) — 28 players
- **Summary**: Nailed: 5 · Regular: 6 · Rotation: 3 · Cameo: 10 · Out of Contention: 4 | Draft Eligible: 11

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Martinez** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **M.Bizot** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Reserve/third-choice goalkeeper. |
| **Cash** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Konsa** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Maatsen** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Pau** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Lindelöf** | DEF | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **A.García** | DEF | Cameo | 0.10 | `not_role_eligible` | Fringe squad player with limited minutes. |
| **Digne** | DEF | Cameo | 0.10 | `not_role_eligible` | Scout starts Maatsen at LB; Digne is the veteran backup/impact option. |
| **Mings** | DEF | Cameo | 0.10 | `not_role_eligible` | Squad rotation/bench option outside primary XI contention. |
| **Nedeljkovic** | DEF | Out of Contention | 0.00 | `not_role_eligible` | Academy / developmental reserve not in first-team XI contention. |
| **Kamara** | MID | Nailed Starter | 0.90 | `watch` | Starting defensive midfield anchor; monitored for GW1 fitness. |
| **Barkley** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Buendía** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Gomes** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **McGinn** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Garnacho** | MID | Rotation | 0.40 | `not_role_eligible` | Confirmed Chelsea loan; Meerkat explicitly frames as bench/CL rotation, not a locked XI starter. |
| **Manzambi** | MID | Rotation | 0.40 | `not_role_eligible` | £50m signing; Meerkat says likely Rogers replace but Scout XI omits him for Barkley/Buendía/McGinn — conservative Rotation. |
| **Alysson** | MID | Cameo | 0.10 | `not_role_eligible` | Fringe squad player with limited minutes. |
| **Bailey** | MID | Cameo | 0.10 | `not_role_eligible` | Not in Scout XI or Meerkat greens; wide rotation behind Buendía/Garnacho/McGinn. |
| **Bogarde** | MID | Cameo | 0.10 | `not_role_eligible` | Squad rotation/bench option outside primary XI contention. |
| **Burrowes** | MID | Cameo | 0.10 | `not_role_eligible` | Fringe squad player with limited minutes. |
| **George Hemmings** | MID | Cameo | 0.10 | `not_role_eligible` | Fringe squad player with limited minutes. |
| **Guessand** | MID | Cameo | 0.10 | `not_role_eligible` | Attacking depth only; neither Scout XI nor Meerkat green for early GW starts. |
| **Iling Jr** | MID | Out of Contention | 0.00 | `not_role_eligible` | Academy / developmental reserve not in first-team XI contention. |
| **Onana** | MID | Out of Contention | 0.00 | `exclude_gw1` | Long-term injury absence (Knee injury - Unknown return date). |
| **Watkins** | FWD | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Abraham** | FWD | Cameo | 0.10 | `exclude_gw1` | Injury / fitness concern (Shoulder injury - Expected back 23 Aug). |

#### 3. Bournemouth (`BOU`) — 25 players
- **Summary**: Nailed: 7 · Regular: 4 · Rotation: 3 · Cameo: 8 · Out of Contention: 3 | Draft Eligible: 11

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Petrović** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Dennis** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Reserve/third-choice goalkeeper. |
| **Forster** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Reserve/third-choice goalkeeper. |
| **Hill** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Truffert** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Smith** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Diakité** | DEF | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Milosavljević** | DEF | Cameo | 0.10 | `not_role_eligible` | CB depth after Senesi exit; Scout prefers Hill/Diakité pairing for early XI. |
| **Soler** | DEF | Cameo | 0.10 | `not_role_eligible` | Fringe squad player with limited minutes. |
| **J.Araujo** | DEF | Out of Contention | 0.00 | `not_role_eligible` | Academy / developmental reserve not in first-team XI contention. |
| **Adams** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Rayan** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Scott** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Tavernier** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Kluivert** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Kroupi.Jr** | MID | Regular Starter | 0.75 | `exclude_gw1-5` | Highly rated attacking midfielder sidelined with foot injury for opening fixtures. |
| **Christie** | MID | Rotation | 0.40 | `exclude_gw1` | Central midfield rotation; suspended for GW1 opening match. |
| **Adli** | MID | Cameo | 0.10 | `not_role_eligible` | Squad rotation/bench option outside primary XI contention. |
| **Brooks** | MID | Cameo | 0.10 | `not_role_eligible` | Squad rotation/bench option outside primary XI contention. |
| **Cook** | MID | Cameo | 0.10 | `not_role_eligible` | Midfield depth behind Adams/Scott; not in Scout predicted XI. |
| **Gannon-Doak** | MID | Cameo | 0.10 | `not_role_eligible` | Fringe squad player with limited minutes. |
| **Tóth.A** | MID | Cameo | 0.10 | `not_role_eligible` | Fringe squad player with limited minutes. |
| **Evanilson** | FWD | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Rodríguez** | FWD | Rotation | 0.40 | `not_role_eligible` | Confirmed £25.7m striker; Meerkat frames as competing with Evanilson for the No.9 shirt. |
| **Enes Ünal** | FWD | Cameo | 0.10 | `not_role_eligible` | Fringe squad player with limited minutes. |

#### 4. Brentford (`BRE`) — 26 players
- **Summary**: Nailed: 6 · Regular: 4 · Rotation: 4 · Cameo: 9 · Out of Contention: 3 | Draft Eligible: 10

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Kelleher** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Valdimarsson** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Reserve/third-choice goalkeeper. |
| **Collins** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Kayode** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Ajer** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Van den Berg** | DEF | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Henry** | DEF | Cameo | 0.10 | `not_role_eligible` | Squad rotation/bench option outside primary XI contention. |
| **Hickey** | DEF | Cameo | 0.10 | `not_role_eligible` | Fringe squad player with limited minutes. |
| **Pinnock** | DEF | Cameo | 0.10 | `not_role_eligible` | Fringe squad player with limited minutes. |
| **Schuster** | DEF | Cameo | 0.10 | `not_role_eligible` | Confirmed May signing; Meerkat lists Schuster as defensive backup, not XI contention starter. |
| **Ji-soo** | DEF | Out of Contention | 0.00 | `not_role_eligible` | Academy / developmental reserve not in first-team XI contention. |
| **O.Dango** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Schade** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Janelt** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Jensen** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Lewis-Potter** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Carvalho** | MID | Rotation | 0.40 | `exclude_gw1` | Attacking midfield rotation recovering from knee issue. |
| **Milambo** | MID | Rotation | 0.40 | `not_role_eligible` | Young midfield signing providing depth behind Janelt and Jensen. |
| **Yarmoliuk** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Anthony** | MID | Cameo | 0.10 | `not_role_eligible` | Confirmed £15m signing; Meerkat explicitly lists Anthony as backup to Schade/Dango band. |
| **Damsgaard** | MID | Cameo | 0.10 | `not_role_eligible` | Creative depth outside Scout XI; competes with Jensen for advanced mid minutes. |
| **Dasilva** | MID | Cameo | 0.10 | `not_role_eligible` | Fringe squad player with limited minutes. |
| **Henderson** | MID | Out of Contention | 0.00 | `not_role_eligible` | Left Brentford as a free agent. |
| **Thiago** | FWD | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Furo** | FWD | Cameo | 0.10 | `not_role_eligible` | Fringe squad player with limited minutes. |
| **Wilson** | FWD | Cameo | 0.10 | `not_role_eligible` | Free signing Callum Wilson; backup to nailed Thiago rather than early draft starter. |

#### 5. Brighton (`BHA`) — 32 players
- **Summary**: Nailed: 5 · Regular: 7 · Rotation: 5 · Cameo: 10 · Out of Contention: 5 | Draft Eligible: 12

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Verbruggen** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Rushworth** | GKP | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Steele** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Reserve/third-choice goalkeeper. |
| **Dunk** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Vuskovic** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Wieffer** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **F.Kadıoğlu** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (Meerkat 🟢 / predicted). |
| **De Cuyper** | DEF | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Boscagli** | DEF | Cameo | 0.10 | `not_role_eligible` | Fringe squad player with limited minutes. |
| **Coppola** | DEF | Cameo | 0.10 | `not_role_eligible` | Fringe squad player with limited minutes. |
| **Igor** | DEF | Cameo | 0.10 | `not_role_eligible` | Fringe squad player with limited minutes. |
| **Struijk** | DEF | Cameo | 0.10 | `not_role_eligible` | Confirmed £20m signing from Leeds; Meerkat explicitly benches Struijk behind Dunk/Vuskovic. |
| **Costinha** | DEF | Out of Contention | 0.00 | `not_role_eligible` | Academy / developmental reserve not in first-team XI contention. |
| **Svoboda** | DEF | Out of Contention | 0.00 | `not_role_eligible` | Academy / developmental reserve not in first-team XI contention. |
| **Groß** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Ayari** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Gomez** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Hinshelwood** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Minteh** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Baleba** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Mitoma** | MID | Rotation | 0.40 | `exclude_gw1` | First-team winger sidelined by hamstring injury for GW1. |
| **Buonanotte** | MID | Cameo | 0.10 | `not_role_eligible` | Fringe squad player with limited minutes. |
| **Howell** | MID | Cameo | 0.10 | `not_role_eligible` | Fringe squad player with limited minutes. |
| **O'Riley** | MID | Cameo | 0.10 | `not_role_eligible` | Fringe squad player with limited minutes. |
| **Oriola** | MID | Cameo | 0.10 | `not_role_eligible` | Fringe squad player with limited minutes. |
| **Watson** | MID | Cameo | 0.10 | `not_role_eligible` | Fringe squad player with limited minutes. |
| **Yohanna** | MID | Out of Contention | 0.00 | `not_role_eligible` | Academy / developmental reserve not in first-team XI contention. |
| **Georginio** | FWD | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Tzimas** | FWD | Rotation | 0.40 | `not_role_eligible` | Young striker providing depth behind Georginio Rutter. |
| **Welbeck** | FWD | Rotation | 0.40 | `not_role_eligible` | Confirmed £5m transfer to Chelsea as forward depth. |
| **Kostoulas** | FWD | Cameo | 0.10 | `not_role_eligible` | Fringe squad player with limited minutes. |
| **Ferguson** | FWD | Out of Contention | 0.00 | `exclude_gw1-5` | Long-term ankle injury keeps him out of opening gameweeks. |

#### 6. Chelsea (`CHE`) — 33 players
- **Summary**: Nailed: 7 · Regular: 9 · Rotation: 6 · Cameo: 8 · Out of Contention: 3 | Draft Eligible: 16

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Sánchez** | GKP | Nailed Starter | 0.90 | `eligible` | First-choice goalkeeper for Chelsea. |
| **Jörgensen** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Backup/reserve goalkeeper behind established starter. |
| **Penders** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Backup/reserve goalkeeper behind established starter. |
| **Colwill** | DEF | Nailed Starter | 0.90 | `eligible` | First-choice left center-back. |
| **James** | DEF | Nailed Starter | 0.90 | `eligible` | First-choice captain and RB. |
| **Lacroix** | DEF | Nailed Starter | 0.90 | `eligible` | First-choice goalkeeper. |
| **Hato** | DEF | Regular Starter | 0.75 | `eligible` | Established squad player for CHE; role Regular Starter. |
| **Palestra** | DEF | Regular Starter | 0.75 | `eligible` | Starting wing-back / full-back. |
| **Chalobah** | DEF | Rotation | 0.40 | `not_role_eligible` | Senior squad rotation player for CHE. |
| **Gusto** | DEF | Rotation | 0.40 | `not_role_eligible` | Established squad player for CHE; role Rotation. |
| **Tosin** | DEF | Rotation | 0.40 | `not_role_eligible` | Established squad player for CHE; role Rotation. |
| **Acheampong** | DEF | Cameo | 0.10 | `not_role_eligible` | Depth / cameo bench player for CHE. |
| **Anselmino** | DEF | Cameo | 0.10 | `not_role_eligible` | Depth / cameo bench player for CHE. |
| **B.Badiashile** | DEF | Cameo | 0.10 | `not_role_eligible` | Depth / cameo bench player for CHE. |
| **Disasi** | DEF | Cameo | 0.10 | `not_role_eligible` | Depth / cameo bench player for CHE. |
| **M.Sarr** | DEF | Cameo | 0.10 | `not_role_eligible` | Depth / cameo bench player for CHE. |
| **Fofana** | DEF | Out of Contention | 0.00 | `not_role_eligible` | Injured/suspended: Suspended until 6 Sep |
| **Caicedo** | MID | Nailed Starter | 0.90 | `eligible` | Established squad player for CHE; role Nailed Starter. |
| **Enzo** | MID | Nailed Starter | 0.90 | `eligible` | Talisman and primary creator/penalty taker. |
| **D.Essugo** | MID | Regular Starter | 0.75 | `eligible` | Confirmed £5m depth move to Chelsea. |
| **Estêvão** | MID | Regular Starter | 0.75 | `eligible` | Starting wide forward / winger. |
| **Gittens** | MID | Regular Starter | 0.75 | `eligible` | Starting defensive midfielder. |
| **Lavia** | MID | Regular Starter | 0.75 | `eligible` | Established squad player for CHE; role Regular Starter. |
| **Neto** | MID | Regular Starter | 0.75 | `eligible` | Starting midfielder in midfield pivot. |
| **Palmer** | MID | Regular Starter | 0.75 | `eligible` | Starting central midfielder. |
| **Rogers** | MID | Regular Starter | 0.75 | `eligible` | £117m summer signing from Aston Villa; regular attacking starter. |
| **Quenda** | MID | Rotation | 0.40 | `not_role_eligible` | Established squad player for CHE; role Rotation. |
| **João Pedro** | FWD | Nailed Starter | 0.90 | `eligible` | Established squad player for CHE; role Nailed Starter. |
| **Delap** | FWD | Rotation | 0.40 | `not_role_eligible` | Senior squad rotation player for CHE. |
| **N.Jackson** | FWD | Rotation | 0.40 | `not_role_eligible` | Senior squad rotation player for CHE. |
| **Emegha** | FWD | Cameo | 0.10 | `not_role_eligible` | Depth / cameo bench player for CHE. |
| **Marc Guiu** | FWD | Cameo | 0.10 | `not_role_eligible` | Depth / cameo bench player for CHE. |
| **Mheuka** | FWD | Cameo | 0.10 | `not_role_eligible` | Depth / cameo bench player for CHE. |

#### 7. Coventry City (`COV`) — 28 players
- **Summary**: Nailed: 0 · Regular: 13 · Rotation: 5 · Cameo: 8 · Out of Contention: 2 | Draft Eligible: 13

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Wilson** | GKP | Rotation | 0.40 | `not_role_eligible` | Established squad player for COV; role Rotation. |
| **Dovin** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Backup/reserve goalkeeper behind established starter. |
| **Amenda** | DEF | Regular Starter | 0.75 | `eligible` | Starting central defender. |
| **Kitching** | DEF | Regular Starter | 0.75 | `eligible` | Starting left-back. |
| **Thomas** | DEF | Regular Starter | 0.75 | `eligible` | Key central defender for Coventry. |
| **van Ewijk** | DEF | Regular Starter | 0.75 | `eligible` | First-choice right-back. |
| **Dasilva** | DEF | Rotation | 0.40 | `not_role_eligible` | Established squad player for COV; role Rotation. |
| **Bidwell** | DEF | Cameo | 0.10 | `not_role_eligible` | Depth / cameo bench player for COV. |
| **Brau** | DEF | Cameo | 0.10 | `not_role_eligible` | Depth / cameo bench player for COV. |
| **Kesler-Hayden** | DEF | Cameo | 0.10 | `not_role_eligible` | Depth / cameo bench player for COV. |
| **Latibeaudiere** | DEF | Cameo | 0.10 | `not_role_eligible` | Depth / cameo bench player for COV. |
| **Woolfenden** | DEF | Cameo | 0.10 | `not_role_eligible` | Depth / cameo bench player for COV. |
| **Andrews** | MID | Regular Starter | 0.75 | `eligible` | Central forward. |
| **Eccles** | MID | Regular Starter | 0.75 | `eligible` | Attacking midfield creator. |
| **Grimes** | MID | Regular Starter | 0.75 | `eligible` | Midfield regular. |
| **Mason-Clark** | MID | Regular Starter | 0.75 | `eligible` | Attacking winger. |
| **Onyeka** | MID | Regular Starter | 0.75 | `eligible` | Established squad player for COV; role Regular Starter. |
| **Sakamoto** | MID | Regular Starter | 0.75 | `eligible` | Creative attacking midfielder. |
| **Torp** | MID | Regular Starter | 0.75 | `eligible` | Central midfielder with set-piece threat. |
| **Rudoni** | MID | Rotation | 0.40 | `not_role_eligible` | Established squad player for COV; role Rotation. |
| **Tchaouna** | MID | Rotation | 0.40 | `not_role_eligible` | Established squad player for COV; role Rotation. |
| **Borges Rodrigues** | MID | Cameo | 0.10 | `not_role_eligible` | Depth / cameo bench player for COV. |
| **Shepherd** | MID | Cameo | 0.10 | `not_role_eligible` | Depth / cameo bench player for COV. |
| **Thomas-Asante** | FWD | Regular Starter | 0.75 | `eligible` | Starting forward / wide attacker. |
| **Wright** | FWD | Regular Starter | 0.75 | `eligible` | First-choice talisman forward. |
| **Simms** | FWD | Rotation | 0.40 | `not_role_eligible` | Established squad player for COV; role Rotation. |
| **Markelo** | FWD | Cameo | 0.10 | `not_role_eligible` | Established squad player for COV; role Cameo. |
| **Bassette** | FWD | Out of Contention | 0.00 | `not_role_eligible` | Injured/suspended: Has joined KVC Westerlo on loan for the rest of the season |

#### 8. Crystal Palace (`CRY`) — 28 players
- **Summary**: Nailed: 7 · Regular: 8 · Rotation: 4 · Cameo: 6 · Out of Contention: 3 | Draft Eligible: 15

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Henderson** | GKP | Nailed Starter | 0.90 | `eligible` | Established squad player for CRY; role Nailed Starter. |
| **Benitez** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Backup/reserve goalkeeper behind established starter. |
| **Matthews** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Backup/reserve goalkeeper behind established starter. |
| **Canvot** | DEF | Nailed Starter | 0.90 | `eligible` | First-choice right wing-back. |
| **Muñoz** | DEF | Nailed Starter | 0.90 | `eligible` | Established squad player for CRY; role Nailed Starter. |
| **Richards** | DEF | Nailed Starter | 0.90 | `eligible` | Starting central defender. |
| **Sosa** | DEF | Nailed Starter | 0.90 | `eligible` | First-choice left wing-back. |
| **Cardines** | DEF | Regular Starter | 0.75 | `eligible` | First-choice center forward. |
| **Chadi Riad** | DEF | Regular Starter | 0.75 | `eligible` | Established squad player for CRY; role Regular Starter. |
| **Mitchell** | DEF | Regular Starter | 0.75 | `eligible` | Starting central defender. |
| **Mingueza** | DEF | Rotation | 0.40 | `not_role_eligible` | Established squad player for CRY; role Rotation. |
| **Devenny** | MID | Nailed Starter | 0.90 | `eligible` | Key attacking midfielder / winger. |
| **Sarr** | MID | Nailed Starter | 0.90 | `eligible` | Established squad player for CRY; role Nailed Starter. |
| **Johnson** | MID | Regular Starter | 0.75 | `eligible` | Starting defensive midfielder. |
| **Kamada** | MID | Regular Starter | 0.75 | `eligible` | Winger / midfield starter. |
| **Wharton** | MID | Regular Starter | 0.75 | `eligible` | Attacking midfielder. |
| **Lerma** | MID | Rotation | 0.40 | `not_role_eligible` | Established squad player for CRY; role Rotation. |
| **Yeremy** | MID | Rotation | 0.40 | `not_role_eligible` | Established squad player for CRY; role Rotation. |
| **Doucouré** | MID | Cameo | 0.10 | `not_role_eligible` | Depth / cameo bench player for CRY. |
| **Drakes-Thomas** | MID | Cameo | 0.10 | `not_role_eligible` | Depth / cameo bench player for CRY. |
| **Esse** | MID | Cameo | 0.10 | `not_role_eligible` | Established squad player for CRY; role Cameo. |
| **Hughes** | MID | Cameo | 0.10 | `not_role_eligible` | Depth / cameo bench player for CRY. |
| **J.Rak-Sakyi** | MID | Cameo | 0.10 | `not_role_eligible` | Depth / cameo bench player for CRY. |
| **M.França** | MID | Cameo | 0.10 | `not_role_eligible` | Depth / cameo bench player for CRY. |
| **Nketiah** | FWD | Regular Starter | 0.75 | `eligible` | Established squad player for CRY; role Regular Starter. |
| **Strand Larsen** | FWD | Regular Starter | 0.75 | `eligible` | Established squad player for CRY; role Regular Starter. |
| **Mateta** | FWD | Rotation | 0.40 | `not_role_eligible` | Established squad player for CRY; role Rotation. |
| **Uche** | FWD | Out of Contention | 0.00 | `not_role_eligible` | Injured/suspended: has returned to Getafe CF |

#### 9. Everton (`EVE`) — 23 players
- **Summary**: Nailed: 10 · Regular: 6 · Rotation: 4 · Cameo: 1 · Out of Contention: 2 | Draft Eligible: 16

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Pickford** | GKP | Nailed Starter | 0.90 | `eligible` | Established squad player for EVE; role Nailed Starter. |
| **King** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Backup/reserve goalkeeper behind established starter. |
| **Travers** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Backup/reserve goalkeeper behind established starter. |
| **Aznou** | DEF | Nailed Starter | 0.90 | `eligible` | First-choice left-back. |
| **Branthwaite** | DEF | Nailed Starter | 0.90 | `eligible` | First-choice England #1 goalkeeper. |
| **Mykolenko** | DEF | Nailed Starter | 0.90 | `eligible` | Key young center back. |
| **O'Brien** | DEF | Nailed Starter | 0.90 | `eligible` | Defensive anchor and captain. |
| **Tarkowski** | DEF | Nailed Starter | 0.90 | `eligible` | Established squad player for EVE; role Nailed Starter. |
| **Patterson** | DEF | Regular Starter | 0.75 | `eligible` | Starting defender / right-back. |
| **Keane** | DEF | Rotation | 0.40 | `not_role_eligible` | Established squad player for EVE; role Rotation. |
| **Dewsbury-Hall** | MID | Nailed Starter | 0.90 | `eligible` | Established squad player for EVE; role Nailed Starter. |
| **Dibling** | MID | Nailed Starter | 0.90 | `eligible` | Key attacking talisman. |
| **Iroegbunam** | MID | Nailed Starter | 0.90 | `eligible` | Primary midfield creator and set-piece taker. |
| **Ndiaye** | MID | Nailed Starter | 0.90 | `eligible` | Established squad player for EVE; role Nailed Starter. |
| **Armstrong** | MID | Regular Starter | 0.75 | `eligible` | Attacking midfielder / winger. |
| **Garner** | MID | Regular Starter | 0.75 | `exclude_gw1` | Central midfielder. (Injured: Groin injury - Expected back 22 Aug) |
| **Hackney** | MID | Regular Starter | 0.75 | `eligible` | Starting midfielder. |
| **Röhl** | MID | Regular Starter | 0.75 | `eligible` | Established squad player for EVE; role Regular Starter. |
| **George** | MID | Rotation | 0.40 | `not_role_eligible` | Established squad player for EVE; role Rotation. |
| **McNeil** | MID | Rotation | 0.40 | `not_role_eligible` | Established squad player for EVE; role Rotation. |
| **Alcaraz** | MID | Cameo | 0.10 | `not_role_eligible` | Depth / cameo bench player for EVE. |
| **Barry** | FWD | Regular Starter | 0.75 | `eligible` | Center forward starter. |
| **Beto** | FWD | Rotation | 0.40 | `not_role_eligible` | Established squad player for EVE; role Rotation. |

#### 10. Fulham (`FUL`) — 21 players
- **Summary**: Nailed: 6 · Regular: 8 · Rotation: 3 · Cameo: 1 · Out of Contention: 3 | Draft Eligible: 14

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Leno** | GKP | Nailed Starter | 0.90 | `eligible` | Established squad player for FUL; role Nailed Starter. |
| **Lecomte** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Backup/reserve goalkeeper behind established starter. |
| **McNally** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Backup/reserve goalkeeper behind established starter. |
| **Bassey** | DEF | Nailed Starter | 0.90 | `eligible` | Established squad player for FUL; role Nailed Starter. |
| **Robinson** | DEF | Nailed Starter | 0.90 | `eligible` | Established squad player for FUL; role Nailed Starter. |
| **J.Cuenca** | DEF | Regular Starter | 0.75 | `eligible` | Established squad player for FUL; role Regular Starter. |
| **Sessegnon** | DEF | Regular Starter | 0.75 | `eligible` | Attacking midfielder / winger. |
| **Tete** | DEF | Regular Starter | 0.75 | `eligible` | Established squad player for FUL; role Regular Starter. |
| **Castagne** | DEF | Rotation | 0.40 | `not_role_eligible` | Established squad player for FUL; role Rotation. |
| **Andersen** | DEF | Out of Contention | 0.00 | `not_role_eligible` | Injured/suspended: Suspended until 29 Aug |
| **Kevin** | MID | Nailed Starter | 0.90 | `eligible` | First-choice left-back and creator. |
| **Reed** | MID | Nailed Starter | 0.90 | `eligible` | Key attacking winger. |
| **Smith Rowe** | MID | Nailed Starter | 0.90 | `eligible` | First-choice center back. |
| **Berge** | MID | Regular Starter | 0.75 | `eligible` | Established squad player for FUL; role Regular Starter. |
| **Bobb** | MID | Regular Starter | 0.75 | `eligible` | Starting center back. |
| **Iwobi** | MID | Regular Starter | 0.75 | `eligible` | Starting right-back. |
| **King** | MID | Regular Starter | 0.75 | `eligible` | Starting midfield pivot. |
| **Lukić** | MID | Rotation | 0.40 | `not_role_eligible` | Established squad player for FUL; role Rotation. |
| **Cairney** | MID | Cameo | 0.10 | `not_role_eligible` | Established squad player for FUL; role Cameo. |
| **Kusi-Asare** | FWD | Regular Starter | 0.75 | `eligible` | Attacking midfielder. |
| **Muniz** | FWD | Rotation | 0.40 | `not_role_eligible` | Established squad player for FUL; role Rotation. |

#### 11. Hull City (`HUL`) — 29 players
- **Summary**: Nailed: 0 · Regular: 9 · Rotation: 6 · Cameo: 9 · Out of Contention: 5 | Draft Eligible: 9

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Butland** | GKP | Rotation | 0.40 | `not_role_eligible` | Signed from Rangers (£3m); in competition with Konstantinos Tzolakis for #1 goalkeeper spot. |
| **Cartwright** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Loaned out to Grimsby Town for the 2026/27 season. |
| **Lo-Tutala** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Third-choice goalkeeper; outside the active matchday squad. |
| **Phillips** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Backup goalkeeper behind Jack Butland and new signings; no first-team starts projected. |
| **Ajayi** | DEF | Regular Starter | 0.75 | `eligible` | Key starting centre-back in preseason friendlies and FFS predicted XI. |
| **Coyle** | DEF | Regular Starter | 0.75 | `eligible` | Club captain and starting right-back in FFS predicted XI. |
| **Egan** | DEF | Regular Starter | 0.75 | `eligible` | Starting centre-back alongside Semi Ajayi in Hull City back four per FFS predicted XI. |
| **Giles** | DEF | Regular Starter | 0.75 | `eligible` | Starting left-back and primary set-piece/corner taker in FFS predicted XI. |
| **Hughes** | DEF | Rotation | 0.40 | `not_role_eligible` | Centre-back rotation option competing with Egan, Ajayi, and newly signed Nobel Mendy. |
| **Targett** | DEF | Rotation | 0.40 | `not_role_eligible` | Signed on free transfer from Newcastle; experienced competition at left-back. |
| **Drameh** | DEF | Cameo | 0.10 | `not_role_eligible` | Fullback depth providing cover for Coyle and Giles. |
| **Jacob** | DEF | Cameo | 0.10 | `not_role_eligible` | Backup left-back providing cover behind Ryan Giles. |
| **McNair** | DEF | Cameo | 0.10 | `not_role_eligible` | Veteran defensive cover for centre-back and central midfield. |
| **McCarthy** | DEF | Out of Contention | 0.00 | `not_role_eligible` | Fringe youth defender outside senior matchday squad. |
| **Belloumi** | MID | Regular Starter | 0.75 | `eligible` | Starting right winger and primary creator/set-piece taker in FFS predicted XI. |
| **Crooks** | MID | Regular Starter | 0.75 | `eligible` | Starting advanced box-to-box midfielder in FFS predicted XI. |
| **Millar** | MID | Regular Starter | 0.75 | `eligible` | Starting left winger in FFS predicted XI; regular preseason starter. |
| **Slater** | MID | Regular Starter | 0.75 | `eligible` | Starting central midfield engine and set-piece taker in FFS predicted XI. |
| **Kamara** | MID | Rotation | 0.40 | `not_role_eligible` | Winger and attacking midfield rotation challenger. |
| **Morita** | MID | Rotation | 0.40 | `not_role_eligible` | Free transfer signing from Sporting CP; competing for starting central midfield berth. |
| **Ömür** | MID | Rotation | 0.40 | `not_role_eligible` | Attacking playmaker competing with Crooks, Belloumi, and Millar. |
| **Akintola** | MID | Cameo | 0.10 | `not_role_eligible` | Wide attacking bench option. |
| **Dowell** | MID | Cameo | 0.10 | `not_role_eligible` | Attacking midfield option from the bench. |
| **Gyabi** | MID | Cameo | 0.10 | `not_role_eligible` | Central midfield cover behind Slater and Morita/Crooks. |
| **Zambrano** | MID | Cameo | 0.10 | `not_role_eligible` | Young midfielder signed from Maribor; developmental squad option. |
| **Matazo** | MID | Out of Contention | 0.00 | `exclude_gw1-5` | Sidelined with significant knee injury; unknown return date. |
| **McBurnie** | FWD | Regular Starter | 0.75 | `eligible` | Hull City talisman striker and first-choice penalty taker (18 goals in 2025/26). |
| **Burstow** | FWD | Cameo | 0.10 | `not_role_eligible` | Young forward providing bench attacking depth. |
| **Destan** | FWD | Cameo | 0.10 | `not_role_eligible` | Backup centre-forward behind McBurnie. |

#### 12. Ipswich Town (`IPS`) — 29 players
- **Summary**: Nailed: 0 · Regular: 10 · Rotation: 11 · Cameo: 5 · Out of Contention: 3 | Draft Eligible: 10

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Scherpen** | GKP | Regular Starter | 0.75 | `eligible` | Transferred from Union SG; projected starting #1 goalkeeper in FFS predicted XI. |
| **Van Oevelen** | GKP | Rotation | 0.40 | `not_role_eligible` | New signing from FC Volendam (£3.4m); competing with Scherpen and Walton. |
| **Walton** | GKP | Rotation | 0.40 | `not_role_eligible` | Goalkeeper depth competing with Scherpen and Van Oevelen. |
| **Button** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Veteran 4th choice goalkeeper. |
| **Palmer** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Third-choice goalkeeper. |
| **Davis** | DEF | Regular Starter | 0.75 | `eligible` | Undisputed starting left-back and premier set-piece/corner creator. |
| **Diop** | DEF | Regular Starter | 0.75 | `eligible` | Confirmed £8.5m signing from Fulham; starting centre-back in FFS predicted XI. |
| **Greaves** | DEF | Regular Starter | 0.75 | `eligible` | Key starting centre-back alongside Issa Diop in FFS predicted XI. |
| **O'Shea** | DEF | Regular Starter | 0.75 | `eligible` | Versatile defensive starter across CB/RB in FFS predicted XI. |
| **Furlong** | DEF | Rotation | 0.40 | `not_role_eligible` | Right-back competitor battling Ben Johnson and Dara O'Shea. |
| **Johnson** | DEF | Rotation | 0.40 | `not_role_eligible` | Fullback cover at right-back and wing-back. |
| **Kipré** | DEF | Rotation | 0.40 | `not_role_eligible` | Centre-back rotation option behind Diop, Greaves, and O'Shea. |
| **Fatawu** | MID | Regular Starter | 0.75 | `eligible` | Confirmed £20m signing from Leicester; starting right winger in FFS predicted XI. |
| **Maeda** | MID | Regular Starter | 0.75 | `eligible` | Confirmed £10m transfer from Celtic; starting left winger in FFS predicted XI. |
| **Núñez** | MID | Regular Starter | 0.75 | `eligible` | Starting playmaker and midfield distributor in FFS predicted XI. |
| **Clarke** | MID | Rotation | 0.40 | `not_role_eligible` | High-quality wide rotation option competing with Philogene, Maeda, and Fatawu. |
| **Matusiwa** | MID | Rotation | 0.40 | `exclude_gw1` | Midfield starter candidate sidelined with muscular injury; expected back early season. |
| **Mehmeti** | MID | Rotation | 0.40 | `not_role_eligible` | Attacking midfielder competing for minutes in the creative line. |
| **Philogene** | MID | Rotation | 0.40 | `not_role_eligible` | Attacking winger in close rotation for wide starting spots. |
| **Szmodics** | MID | Rotation | 0.40 | `not_role_eligible` | Attacking midfielder / second-striker sharing minutes with Nunez and wingers. |
| **Burns** | MID | Cameo | 0.10 | `not_role_eligible` | Winger rotation / impact substitute behind Fatawu and Maeda. |
| **McAteer** | MID | Cameo | 0.10 | `not_role_eligible` | Midfield bench option. |
| **Ogbene** | MID | Cameo | 0.10 | `not_role_eligible` | Pacy winger offering late substitution threat. |
| **Taylor** | MID | Out of Contention | 0.00 | `exclude_gw1` | Sidelined with knee injury; out for GW1. |
| **Emersonn** | FWD | Regular Starter | 0.75 | `eligible` | Signed from Toulouse; starting striker in FFS predicted XI. |
| **Walle Egeli** | FWD | Regular Starter | 0.75 | `eligible` | Young Norwegian forward starting on the right/frontline in FFS predicted XI. |
| **Hirst** | FWD | Rotation | 0.40 | `not_role_eligible` | Striker rotation competing with Emersonn and Walle Egeli. |
| **Akpom** | FWD | Cameo | 0.10 | `not_role_eligible` | Experienced forward depth and substitute option. |
| **Al-Hamadi** | FWD | Cameo | 0.10 | `not_role_eligible` | Forward depth option off the bench. |

#### 13. Leeds (`LEE`) — 24 players
- **Summary**: Nailed: 6 · Regular: 4 · Rotation: 5 · Cameo: 7 · Out of Contention: 2 | Draft Eligible: 10

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Perri** | GKP | Rotation | 0.40 | `not_role_eligible` | In competition with newly signed £45m goalkeeper James Trafford for starting berth. |
| **Muharemović** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. Starting CB anchor from Sassuolo. |
| **Rodon** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. Central defensive pillar. |
| **Bijol** | DEF | Regular Starter | 0.75 | `eligible` | Starting centre-back alongside Rodon/Muharemovic in FFS predicted XI. |
| **Bogle** | DEF | Regular Starter | 0.75 | `eligible` | Attacking right-back starting in FFS predicted XI. |
| **Justin** | DEF | Regular Starter | 0.75 | `eligible` | Starting full-back in FFS predicted XI with versatility on left and right. |
| **Gudmundsson** | DEF | Rotation | 0.40 | `not_role_eligible` | Left-back depth competing with James Justin. |
| **Bornauw** | DEF | Cameo | 0.10 | `not_role_eligible` | Centre-back cover behind Rodon, Bijol, and Muharemovic. |
| **Ampadu** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. Team captain & defensive midfield anchor. |
| **Stach** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. Core midfield controller. |
| **Wilson** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. Team talisman & set-piece taker. |
| **Okafor** | MID | Regular Starter | 0.75 | `eligible` | Starting attacking forward/winger in Meerkat 🟢 predicted lineup from Milan. |
| **Aaronson** | MID | Rotation | 0.40 | `not_role_eligible` | Attacking midfield rotation behind Wilson and Okafor. |
| **Longstaff** | MID | Rotation | 0.40 | `not_role_eligible` | Central midfield depth behind Stach and Ampadu. |
| **Tanaka** | MID | Rotation | 0.40 | `not_role_eligible` | Progressive central midfielder rotating in engine room. |
| **Gelhardt** | MID | Cameo | 0.10 | `not_role_eligible` | Attacking option providing late substitute minutes. |
| **Gnonto** | MID | Cameo | 0.10 | `not_role_eligible` | Winger impact substitute behind Wilson and Okafor. |
| **Gruev** | MID | Cameo | 0.10 | `not_role_eligible` | Defensive midfield cover for Ethan Ampadu. |
| **James** | MID | Cameo | 0.10 | `not_role_eligible` | Pacy wide substitute offering direct attacking threat. |
| **Harrison** | MID | Out of Contention | 0.00 | `not_role_eligible` | Permanent transfer to MLS New England Revolution. |
| **Calvert-Lewin** | FWD | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. Starting #9 centre-forward talisman. |
| **Nmecha** | FWD | Cameo | 0.10 | `not_role_eligible` | Backup striker behind Calvert-Lewin. |
| **Piroe** | FWD | Cameo | 0.10 | `not_role_eligible` | Forward / second-striker depth providing bench goal threat. |
| **Mateo Joseph** | FWD | Out of Contention | 0.00 | `exclude_gw1` | Sidelined with knee injury; unknown return date. |

#### 14. Liverpool (`LIV`) — 34 players
- **Summary**: Nailed: 8 · Regular: 4 · Rotation: 6 · Cameo: 4 · Out of Contention: 12 | Draft Eligible: 12

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **A.Becker** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. Undisputed #1 goalkeeper. |
| **Mamardashvili** | GKP | Rotation | 0.40 | `not_role_eligible` | Elite backup goalkeeper behind Alisson; cup/rotation keeper. |
| **Davies** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Reserve goalkeeper. |
| **Jaros** | GKP | Out of Contention | 0.00 | `exclude_gw1` | Injured goalkeeper (knee injury); unknown return date. |
| **Pecsi** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Academy goalkeeper outside matchday squad. |
| **Woodman** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Third-choice goalkeeper. |
| **Jacquet** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. Starting CB alongside Virgil van Dijk. |
| **Kerkez** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. Undisputed first-choice left-back. |
| **Virgil** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. Team captain and defensive pillar. |
| **Frimpong** | DEF | Regular Starter | 0.75 | `eligible` | Signed from Leverkusen; starting right-back/wing-back in FFS predicted XI. |
| **Gomez** | DEF | Rotation | 0.40 | `exclude_gw1` | Versatile defensive rotation option currently nursing muscular injury. |
| **Tsimikas** | DEF | Rotation | 0.40 | `not_role_eligible` | Backup left-back providing cover for Milos Kerkez. |
| **Bradley** | DEF | Cameo | 0.10 | `exclude_gw1` | Right-back challenger behind Frimpong; currently recovering from knee injury. |
| **Leoni** | DEF | Out of Contention | 0.00 | `exclude_gw1` | Youth defender recovering from knee injury. |
| **Lucky** | DEF | Out of Contention | 0.00 | `not_role_eligible` | Academy defender outside senior squad. |
| **Ramsay** | DEF | Out of Contention | 0.00 | `not_role_eligible` | Fringe right-back outside matchday squad. |
| **Gravenberch** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. Starting #6 pivot controller. |
| **Szoboszlai** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. Key dynamic midfield starter. |
| **Wirtz** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. Marquee £7.5m playmaker talisman. |
| **Gakpo** | MID | Regular Starter | 0.75 | `eligible` | Starting left winger in FFS predicted XI. |
| **Mac Allister** | MID | Regular Starter | 0.75 | `watch` | Core midfield starter managed for post-tournament fitness. |
| **Ngumoha** | MID | Regular Starter | 0.75 | `eligible` | Breakout teenage winger starting in FFS predicted XI across preseason. |
| **C.Jones** | MID | Rotation | 0.40 | `not_role_eligible` | Central midfield rotation option behind Gravenberch, Szoboszlai, and Mac Allister. |
| **Chiesa** | MID | Rotation | 0.40 | `not_role_eligible` | Experienced forward/winger rotation providing depth across frontline. |
| **Elliott** | MID | Rotation | 0.40 | `not_role_eligible` | Attacking midfield / right wing rotation option. |
| **Endo** | MID | Cameo | 0.10 | `watch` | Veteran defensive midfield cover; 75% flag with ankle knock. |
| **Munoz** | MID | Cameo | 0.10 | `not_role_eligible` | Spanish winger providing attacking depth. |
| **Bajcetic** | MID | Out of Contention | 0.00 | `exclude_gw1` | Hamstring injury; expected back late August. |
| **Koumas** | MID | Out of Contention | 0.00 | `not_role_eligible` | Youth forward outside senior matchday squad. |
| **McConnell** | MID | Out of Contention | 0.00 | `not_role_eligible` | Reserve midfielder. |
| **Nyoni** | MID | Out of Contention | 0.00 | `not_role_eligible` | Young midfield prospect outside primary senior squad. |
| **Isak** | FWD | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. Elite #9 centre-forward talisman. |
| **Ekitiké** | FWD | Cameo | 0.10 | `exclude_gw1` | Striker challenger behind Isak currently sidelined with Achilles injury. |
| **Danns** | FWD | Out of Contention | 0.00 | `exclude_gw1` | Injured young forward (unspecified injury); out for GW1. |

#### 15. Man City (`MCI`) — 30 players
- **Summary**: Nailed: 6 · Regular: 9 · Rotation: 7 · Cameo: 1 · Out of Contention: 7 | Draft Eligible: 15

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Donnarumma** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. Undisputed starting #1 goalkeeper. |
| **Trafford** | GKP | Nailed Starter | 0.90 | `eligible` | Confirmed £45m transfer to Leeds United as their undisputed #1 starting goalkeeper. |
| **Bettinelli** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Third-choice goalkeeper. |
| **Matheus N.** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. Nailed right-back in Pep Guardiola setup. |
| **Guéhi** | DEF | Regular Starter | 0.75 | `eligible` | Starting centre-back alongside Ruben Dias in Meerkat 🟢 predicted lineup. |
| **Gvardiol** | DEF | Regular Starter | 0.75 | `eligible` | Starting left-back / left centre-back in FFS predicted XI. |
| **Khusanov** | DEF | Regular Starter | 0.75 | `eligible` | Starting centre-back option in FFS predicted XI. |
| **O'Reilly** | DEF | Regular Starter | 0.75 | `eligible` | Starting versatile fullback/midfielder in Meerkat 🟢 predicted lineup. |
| **Rúben** | DEF | Regular Starter | 0.75 | `eligible` | Starting central defender in FFS predicted XI. |
| **Aït-Nouri** | DEF | Rotation | 0.40 | `not_role_eligible` | Left-back / wing-back rotation option competing with Gvardiol and O'Reilly. |
| **Lewis** | DEF | Rotation | 0.40 | `not_role_eligible` | Inverted fullback and midfield utility sub providing depth across backline. |
| **Alleyne** | DEF | Out of Contention | 0.00 | `not_role_eligible` | Youth centre-back outside primary senior lineup. |
| **Vitor Reis** | DEF | Out of Contention | 0.00 | `not_role_eligible` | Young Brazilian centre-back in developmental squad. |
| **Anderson** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. £116m marquee midfield engine. |
| **Semenyo** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. Key marquee attacker (£8.5m). |
| **Doku** | MID | Regular Starter | 0.75 | `eligible` | Starting left winger in FFS predicted XI offering direct 1v1 threat. |
| **Foden** | MID | Regular Starter | 0.75 | `eligible` | Starting creative playmaker / winger in FFS predicted XI. |
| **Reijnders** | MID | Regular Starter | 0.75 | `eligible` | Starting central midfielder in FFS predicted XI alongside Anderson. |
| **Rodrigo** | MID | Regular Starter | 0.75 | `exclude_gw1` | Key defensive midfield anchor recovering from back surgery. |
| **Cherki** | MID | Rotation | 0.40 | `not_role_eligible` | Dynamic attacking playmaker rotating across attacking midfield and wide slots. |
| **Grealish** | MID | Rotation | 0.40 | `watch` | Creative winger / attacking midfield rotation; managing minor foot knock (75% flag). |
| **Kovačić** | MID | Rotation | 0.40 | `not_role_eligible` | Experienced midfield rotation option in double pivot. |
| **N.Gonzalez** | MID | Rotation | 0.40 | `not_role_eligible` | Central midfield rotation option behind Reijnders, Anderson, and Rodri. |
| **Savinho** | MID | Rotation | 0.40 | `not_role_eligible` | Winger rotation competing with Doku, Semenyo, and Cherki. |
| **Echeverri** | MID | Out of Contention | 0.00 | `not_role_eligible` | Young Argentine playmaker in developmental phase. |
| **Monga** | MID | Out of Contention | 0.00 | `not_role_eligible` | Academy winger. |
| **Mukasa** | MID | Out of Contention | 0.00 | `not_role_eligible` | Academy midfielder. |
| **Phillips** | MID | Out of Contention | 0.00 | `not_role_eligible` | Out of favour central midfielder outside matchday plans. |
| **Haaland** | FWD | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. Premier League top striker talisman. |
| **Marmoush** | FWD | Cameo | 0.10 | `not_role_eligible` | Attacking forward backup behind Haaland and wide starters. |

#### 16. Man Utd (`MUN`) — 33 players
- **Summary**: Nailed: 5 · Regular: 7 · Rotation: 8 · Cameo: 7 · Out of Contention: 6 | Draft Eligible: 12

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Lammens** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed; uncontested starting goalkeeper. |
| **Bayindir** | GKP | Cameo | 0.10 | `not_role_eligible` | Reserve goalkeeper behind Lammens and Darlow. |
| **Darlow** | GKP | Cameo | 0.10 | `not_role_eligible` | Signed on free transfer from Leeds as senior backup GKP behind Lammens. |
| **Heaton** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Veteran third/fourth choice goalkeeper outside matchday squad. |
| **Dalot** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed; first-choice right back. |
| **Maguire** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed; started final friendly as defensive anchor. |
| **Shaw** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed; regular starter at left-back. |
| **Heaven** | DEF | Regular Starter | 0.75 | `eligible` | Started final friendly vs AC Milan; selected in FFS predicted starting XI at center-back. |
| **Martinez** | DEF | Rotation | 0.40 | `not_role_eligible` | Managing thigh injury recovery; featured as second-half substitute vs AC Milan. |
| **Mazraoui** | DEF | Rotation | 0.40 | `not_role_eligible` | Started at RB in final friendly; versatile fullback cover competing with Dalot and Shaw. |
| **Yoro** | DEF | Rotation | 0.40 | `not_role_eligible` | Central defensive rotation option behind Maguire and Heaven/Martinez. |
| **Amass** | DEF | Cameo | 0.10 | `not_role_eligible` | Youth backup left-back behind Shaw and Mazraoui. |
| **De Ligt** | DEF | Cameo | 0.10 | `exclude_gw1-5` | Sidelined with back injury with unknown return date; CB depth behind Maguire, Heaven, and Yoro. |
| **Fredricson** | DEF | Out of Contention | 0.00 | `not_role_eligible` | Academy center-back depth; outside senior matchday squad. |
| **B.Fernandes** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed; club captain and primary talisman. |
| **Amad** | MID | Regular Starter | 0.75 | `eligible` | Started right wing in final friendly vs AC Milan; FFS predicted XI starter. |
| **Andrey Santos** | MID | Regular Starter | 0.75 | `eligible` | Started final preseason friendly vs AC Milan; secured starting midfield pivot spot under Carrick. |
| **Cunha** | MID | Regular Starter | 0.75 | `eligible` | Started as central striker in final preseason friendly vs AC Milan; key Carrick attacking focal point. |
| **Dorgu** | MID | Regular Starter | 0.75 | `eligible` | FFS predicted XI left winger; started final preseason friendly vs AC Milan under Carrick. |
| **Mbeumo** | MID | Regular Starter | 0.75 | `eligible` | FFS predicted XI starting attacker; marquee signing after World Cup rest. |
| **Tielemans** | MID | Regular Starter | 0.75 | `watch` | Started final preseason friendly vs AC Milan; key Carrick double-pivot midfield signing. |
| **Mainoo** | MID | Rotation | 0.40 | `not_role_eligible` | Midfield rotation challenger behind Santos and Tielemans. |
| **Mount** | MID | Rotation | 0.40 | `not_role_eligible` | Attacking midfield and wide rotation option behind Bruno, Amad, and Mbeumo. |
| **Rashford** | MID | Rotation | 0.40 | `not_role_eligible` | Rotated on bench in final friendly; competing with Dorgu, Cunha, and Amad. |
| **Collyer** | MID | Cameo | 0.10 | `not_role_eligible` | Academy defensive midfielder on fringe of first-team squad. |
| **J.Fletcher** | MID | Cameo | 0.10 | `not_role_eligible` | Academy midfielder featured as late preseason substitute. |
| **Lacey** | MID | Cameo | 0.10 | `not_role_eligible` | Young winger featured on preseason bench. |
| **Bendito Mantato** | MID | Out of Contention | 0.00 | `not_role_eligible` | Academy development player; outside matchday squad. |
| **Fletcher** | MID | Out of Contention | 0.00 | `not_role_eligible` | Academy prospect outside senior rotation. |
| **Ugarte** | MID | Out of Contention | 0.00 | `exclude_gw1-5` | Long-term knee injury; excluded from matchday squads pending recovery. |
| **Zirkzee** | FWD | Rotation | 0.40 | `not_role_eligible` | Backup striker option featured from bench in preseason. |
| **Šeško** | FWD | Rotation | 0.40 | `not_role_eligible` | Carrying a minor shin injury; competing with Cunha and Zirkzee for striker role. |
| **Obi** | FWD | Out of Contention | 0.00 | `not_role_eligible` | Academy striker outside first team contention. |

#### 17. Newcastle (`NEW`) — 25 players
- **Summary**: Nailed: 1 · Regular: 12 · Rotation: 7 · Cameo: 3 · Out of Contention: 2 | Draft Eligible: 13

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Pope** | GKP | Regular Starter | 0.75 | `eligible` | FPL Meerkat 🟢 starter; senior #1 goalkeeper facing competition from newly signed Hornicek. |
| **Jaouen** | GKP | Cameo | 0.10 | `not_role_eligible` | £18.5m summer signing from Reims; started friendly vs Strasbourg as cup/rotation GKP. |
| **Gillespie** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Reserve goalkeeper behind Pope, Hornicek, and Jaouen. |
| **Thiaw** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed; scored vs Leverkusen in final friendly. |
| **Botman** | DEF | Regular Starter | 0.75 | `eligible` | FFS predicted XI starting center-back; started vs Leverkusen. |
| **Burn** | DEF | Regular Starter | 0.75 | `eligible` | Started vs Strasbourg; versatile CB/LB competing across Newcastle backline. |
| **Hall** | DEF | Regular Starter | 0.75 | `eligible` | FFS predicted XI left-back; started final test vs Leverkusen. |
| **Livramento** | DEF | Regular Starter | 0.75 | `watch` | Meerkat 🟢 nailed right-back; monitored for minor calf issue. |
| **Schär** | DEF | Rotation | 0.40 | `not_role_eligible` | Started vs Strasbourg; veteran CB competing with Thiaw, Botman, and Burn. |
| **A.Murphy** | DEF | Cameo | 0.10 | `not_role_eligible` | Youth defender depth behind Hall, Burn, and Botman. |
| **Bamba** | MID | Regular Starter | 0.75 | `eligible` | £30m summer signing from Monaco; FFS predicted XI starting midfielder; started vs Strasbourg. |
| **Elanga** | MID | Regular Starter | 0.75 | `eligible` | FFS predicted XI winger; started vs Leverkusen and registered assist for Thiaw. |
| **J.Ramsey** | MID | Regular Starter | 0.75 | `eligible` | FFS predicted XI attacking midfielder; started vs Strasbourg. |
| **Joelinton** | MID | Regular Starter | 0.75 | `watch` | Key midfield enforcer; 75% flag due to minor thigh knock in late preseason. |
| **Steur** | MID | Regular Starter | 0.75 | `eligible` | £23m signing from Ajax; FFS predicted XI central midfielder; started vs Leverkusen. |
| **Touré** | MID | Regular Starter | 0.75 | `eligible` | £43m summer signing from Hoffenheim; FFS predicted XI winger; started vs Strasbourg. |
| **Barnes** | MID | Rotation | 0.40 | `not_role_eligible` | Started vs Leverkusen; winger rotation with Elanga, Toure, and J.Murphy. |
| **J.Murphy** | MID | Rotation | 0.40 | `not_role_eligible` | Started vs Strasbourg, assisting Osula; wide attacking rotation. |
| **L.Miley** | MID | Rotation | 0.40 | `exclude_gw1` | Suffered leg knock vs Leverkusen; expected back late August. |
| **Willock** | MID | Rotation | 0.40 | `not_role_eligible` | Started vs Strasbourg; midfield box-to-box depth. |
| **Bruno G.** | MID | Out of Contention | 0.00 | `not_role_eligible` | Transferred to Arsenal in summer 2026 (£75m); awaiting FPL squad update. |
| **Wissa** | FWD | Regular Starter | 0.75 | `eligible` | FFS predicted XI central striker; started vs Leverkusen. |
| **Osula** | FWD | Rotation | 0.40 | `not_role_eligible` | Scored goal vs Strasbourg; striker depth behind Wissa and Woltemade. |
| **Woltemade** | FWD | Rotation | 0.40 | `not_role_eligible` | Started at striker vs Leverkusen; rotating with Wissa and Osula. |
| **Neave** | FWD | Cameo | 0.10 | `not_role_eligible` | Academy forward featured as late substitute in friendlies. |

#### 18. Nott'm Forest (`NFO`) — 27 players
- **Summary**: Nailed: 1 · Regular: 10 · Rotation: 6 · Cameo: 6 · Out of Contention: 4 | Draft Eligible: 11

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Sels** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed; uncontested #1 goalkeeper under Glasner. |
| **John** | GKP | Cameo | 0.10 | `not_role_eligible` | Backup goalkeeper behind Sels. |
| **Aina** | DEF | Regular Starter | 0.75 | `eligible` | FFS predicted XI left wing-back; regular starter in Glasner wingback system. |
| **Jair Cunha** | DEF | Regular Starter | 0.75 | `eligible` | First-team CB challenger in back three alongside Milenkovic and Murillo. |
| **Milenković** | DEF | Regular Starter | 0.75 | `eligible` | FFS predicted XI central defender; established anchor of back-three. |
| **Murillo** | DEF | Regular Starter | 0.75 | `watch` | Key central defender; 75% flag due to slight preseason muscle strain. |
| **N.Williams** | DEF | Regular Starter | 0.75 | `eligible` | FFS predicted XI starting right wing-back in Glasner 3-4-2-1 setup. |
| **Morato** | DEF | Cameo | 0.10 | `not_role_eligible` | Central defensive cover behind Murillo, Milenkovic, Diomande, and Jair Cunha. |
| **Netz** | DEF | Cameo | 0.10 | `not_role_eligible` | Backup left wing-back behind Aina. |
| **Abbott** | DEF | Out of Contention | 0.00 | `not_role_eligible` | Youth defender in reserve pool. |
| **Bindon** | DEF | Out of Contention | 0.00 | `not_role_eligible` | Young defender outside senior rotation. |
| **O.Richards** | DEF | Out of Contention | 0.00 | `not_role_eligible` | Left-back depth outside matchday squad. |
| **Savona** | DEF | Out of Contention | 0.00 | `exclude_gw1-5` | Sidelined with significant knee injury; excluded for early season. |
| **Gibbs-White** | MID | Regular Starter | 0.75 | `eligible` | FFS predicted XI talisman and primary set-piece taker in attacking midfield. |
| **Ndoye** | MID | Regular Starter | 0.75 | `eligible` | FFS predicted XI inside forward / attacking midfielder under Glasner. |
| **Sangaré** | MID | Regular Starter | 0.75 | `eligible` | FFS predicted XI midfield anchor in Glasner double pivot. |
| **Schlager** | MID | Regular Starter | 0.75 | `eligible` | Free transfer from RB Leipzig; FFS predicted XI central midfield starter alongside Sangare. |
| **Dominguez** | MID | Rotation | 0.40 | `not_role_eligible` | Central midfield rotation behind Sangare and Schlager. |
| **Hudson-Odoi** | MID | Rotation | 0.40 | `not_role_eligible` | Attacking rotation option recovering from minor thigh strain. |
| **Hutchinson** | MID | Rotation | 0.40 | `not_role_eligible` | Wide attacker rotating with Ndoye, Bakwa, and Hudson-Odoi. |
| **Yates** | MID | Rotation | 0.40 | `not_role_eligible` | Midfield rotation and leadership option off the bench. |
| **Bakwa** | MID | Cameo | 0.10 | `not_role_eligible` | Wide attacking depth option. |
| **McAtee** | MID | Cameo | 0.10 | `not_role_eligible` | Attacking midfield cover behind Gibbs-White. |
| **Igor Jesus** | FWD | Regular Starter | 0.75 | `eligible` | FFS predicted XI starting forward; top preseason goalscorer with 4 goals. |
| **Kalimuendo** | FWD | Rotation | 0.40 | `not_role_eligible` | Impressed with 3 goals in preseason; primary impact striker sub. |
| **Wood** | FWD | Rotation | 0.40 | `not_role_eligible` | Experienced striker competing with Igor Jesus and Kalimuendo. |
| **Awoniyi** | FWD | Cameo | 0.10 | `not_role_eligible` | Striker depth behind Igor Jesus, Wood, and Kalimuendo. |

#### 19. Spurs (`TOT`) — 36 players
- **Summary**: Nailed: 3 · Regular: 10 · Rotation: 11 · Cameo: 3 · Out of Contention: 9 | Draft Eligible: 13

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Kinsky** | GKP | Regular Starter | 0.75 | `eligible` | FFS predicted XI starting goalkeeper; started majority of preseason friendlies. |
| **Dubravka** | GKP | Rotation | 0.40 | `not_role_eligible` | Free transfer from Burnley as experienced senior backup GKP. |
| **Vicario** | GKP | Rotation | 0.40 | `not_role_eligible` | Senior goalkeeper returning to fitness; competing with Kinsky for #1 shirt. |
| **Austin** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Third/fourth choice goalkeeper; featured in behind-closed-doors match. |
| **Pedro Porro** | DEF | Nailed Starter | 0.90 | `eligible` | Meerkat 🟢 nailed; elite attacking right-back. |
| **Van Hecke** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed; £52m summer signing anchoring defense. |
| **Van de Ven** | DEF | Nailed Starter | 0.90 | `eligible` | Meerkat 🟢 nailed; elite left center-back. |
| **Robertson** | DEF | Regular Starter | 0.75 | `eligible` | Free transfer from Liverpool; FFS predicted XI starting left-back. |
| **Senesi** | DEF | Regular Starter | 0.75 | `eligible` | Free transfer from Bournemouth; FFS predicted XI starting center-back. |
| **Danso** | DEF | Rotation | 0.40 | `not_role_eligible` | Started behind-closed-doors match vs Hoffenheim; CB rotation depth. |
| **Romero** | DEF | Rotation | 0.40 | `not_role_eligible` | Late return after international duty; central defensive rotation behind Van Hecke, Van de Ven, and Senesi. |
| **Udogie** | DEF | Rotation | 0.40 | `not_role_eligible` | Managing fitness after preseason knock; competing with Robertson for left-back spot. |
| **Davies** | DEF | Cameo | 0.10 | `not_role_eligible` | Veteran defender; scored in secondary friendly vs Hoffenheim. |
| **Spence** | DEF | Cameo | 0.10 | `not_role_eligible` | Fullback depth behind Pedro Porro, Robertson, and Gray. |
| **Byfield** | DEF | Out of Contention | 0.00 | `not_role_eligible` | Academy defender outside senior rotation. |
| **Phillips** | DEF | Out of Contention | 0.00 | `not_role_eligible` | Young center-back outside first-team matchday squad. |
| **Rowswell** | DEF | Out of Contention | 0.00 | `not_role_eligible` | Academy defender outside senior rotation. |
| **Souza** | DEF | Out of Contention | 0.00 | `not_role_eligible` | Development defender outside first-team squad. |
| **Fernandes** | MID | Regular Starter | 0.75 | `eligible` | £85m signing from West Ham; FFS predicted XI central midfield starter; featured vs Hoffenheim. |
| **Gallagher** | MID | Regular Starter | 0.75 | `eligible` | FFS predicted XI starting box-to-box midfielder. |
| **Gray** | MID | Regular Starter | 0.75 | `eligible` | FFS predicted XI starting right-back during Pedro Porro's post-World Cup reintegration. |
| **Moore** | MID | Regular Starter | 0.75 | `eligible` | Scored in main friendly vs Hoffenheim; FFS predicted XI starting winger. |
| **Tel** | MID | Regular Starter | 0.75 | `eligible` | FFS predicted XI inside forward; key attacker under De Zerbi. |
| **Tonali** | MID | Regular Starter | 0.75 | `eligible` | £100m marquee midfield signing; FFS predicted XI starting playmaker; started vs Hoffenheim. |
| **Bentancur** | MID | Rotation | 0.40 | `not_role_eligible` | Started secondary friendly vs Hoffenheim; midfield depth behind Tonali, Fernandes, and Gallagher. |
| **Bergvall** | MID | Rotation | 0.40 | `not_role_eligible` | Featured in main matchday squad vs Hoffenheim; creative midfield rotation. |
| **Kudus** | MID | Rotation | 0.40 | `not_role_eligible` | Attacking midfield star carrying thigh knock from preseason. |
| **Maddison** | MID | Rotation | 0.40 | `not_role_eligible` | Returned in secondary friendly vs Hoffenheim after long injury layoff; minutes being built up. |
| **P.M.Sarr** | MID | Rotation | 0.40 | `not_role_eligible` | Featured in secondary friendly vs Hoffenheim; central midfield depth. |
| **Kulusevski** | MID | Out of Contention | 0.00 | `exclude_gw1-5` | Recovering from knee surgery; unavailable for early gameweeks. |
| **Odobert** | MID | Out of Contention | 0.00 | `exclude_gw1-5` | Sidelined with knee injury; out for start of season. |
| **Olusesi** | MID | Out of Contention | 0.00 | `not_role_eligible` | Academy midfielder outside first-team squad. |
| **Xavi** | MID | Out of Contention | 0.00 | `exclude_gw1-5` | Long-term knee injury; excluded from early-season fixtures. |
| **Richarlison** | FWD | Regular Starter | 0.75 | `eligible` | FFS predicted XI central striker; started main friendly vs Hoffenheim. |
| **Solanke** | FWD | Rotation | 0.40 | `not_role_eligible` | Striker rotation challenger competing with Richarlison. |
| **Scarlett** | FWD | Cameo | 0.10 | `not_role_eligible` | Third choice striker behind Richarlison and Solanke. |

#### 20. Sunderland (`SUN`) — 25 players
- **Summary**: Nailed: 7 · Regular: 6 · Rotation: 2 · Cameo: 8 · Out of Contention: 2 | Draft Eligible: 13

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Roefs** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed; uncontested #1 goalkeeper. |
| **Ellborg** | GKP | Cameo | 0.10 | `not_role_eligible` | Third choice goalkeeper. |
| **Patterson** | GKP | Cameo | 0.10 | `not_role_eligible` | Backup goalkeeper behind Roefs. |
| **Ballard** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed; cornerstone central defender. |
| **Reinildo** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed; first-choice left-back. |
| **Alderete** | DEF | Regular Starter | 0.75 | `eligible` | Meerkat 🟢 nailed central defender alongside Ballard. |
| **Hume** | DEF | Regular Starter | 0.75 | `eligible` | FFS predicted XI; scored winning goals in final two preseason friendlies vs Lens and Rennes. |
| **Meunier** | DEF | Regular Starter | 0.75 | `eligible` | Free transfer from Lille; FFS predicted XI right-back. |
| **Mukiele** | DEF | Regular Starter | 0.75 | `eligible` | Meerkat 🟢 nailed; senior international fullback/CB. |
| **O'Nien** | DEF | Regular Starter | 0.75 | `eligible` | FFS predicted XI starter; versatile defensive leader starting at CB/RB. |
| **Masuaku** | DEF | Cameo | 0.10 | `not_role_eligible` | Veteran fullback depth behind Reinildo and Hume. |
| **Seelt** | DEF | Cameo | 0.10 | `not_role_eligible` | Central defensive cover behind Ballard, Alderete, and O'Nien. |
| **Hjelde** | DEF | Out of Contention | 0.00 | `not_role_eligible` | Defensive depth outside matchday squad. |
| **E.Le Fée** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed; primary playmaker and corner taker. |
| **Sadiki** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed; defensive midfield double pivot anchor. |
| **Xhaka** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed; captain and midfield general. |
| **Angulo** | MID | Regular Starter | 0.75 | `eligible` | FFS predicted XI starting winger; regular starter in preseason matches. |
| **Adingra** | MID | Rotation | 0.40 | `not_role_eligible` | Wide attacker rotating with Angulo, Talbi, and Mundle. |
| **Talbi** | MID | Rotation | 0.40 | `not_role_eligible` | Attacking winger option in Le Bris rotation. |
| **Diarra** | MID | Cameo | 0.10 | `not_role_eligible` | Midfield rotation depth behind Xhaka, Sadiki, and Le Fée. |
| **Mundle** | MID | Cameo | 0.10 | `not_role_eligible` | Winger depth off the bench. |
| **Rigg** | MID | Cameo | 0.10 | `not_role_eligible` | Highly rated young midfielder developing behind senior starters. |
| **Jocelin.T** | MID | Out of Contention | 0.00 | `not_role_eligible` | Academy midfielder outside senior rotation. |
| **Brobbey** | FWD | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed; primary striker, scored vs Rennes in final friendly. |
| **Isidor** | FWD | Cameo | 0.10 | `not_role_eligible` | Striker backup behind Brobbey. |


## Decision

**Verdict**: 20-club Expected Role scaffold refreshed from dual live scrape (FFS + Meerkat), 357 contention rows, 227 Draft-eligible players categorized. Identity match uses FPL first/second name so B.Fernandes ≠ Bruno G. and Virgil matches Van Dijk.

---

## Verification & Delivery

- Stage 1 script: `docs/research/gw1-6-preseason-pipeline/01-expected-role-gw1-5/refresh_expected_role.py`.
- Output CSV: `data/research/gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.csv`.

# FPL 2026/27 Expected Role (GW1–5) — 20-Club Audit & Mins Priors

**Updated**: 2026-08-18T15:05:00+07:00  
**Data stamp**: FFS Team News + FPL Meerkat scraped 2026-08-18 (post name-match fix); `players.parquet` 2026-08-18 (590 players; Trafford LEE, Rushworth COV)  
**Season**: 2026/27  
**Status**: Active Research Model  
**Purpose**: Assign fit-conditional Expected Role, dated Draft Availability, and Participation State priors across all 20 clubs for GW1–5 seeding  
**Scope**: XI Contention Set (scaffold + FFS XI injects); Draft Shortlist = Nailed + Regular; Availability Overlay separately applies `eligible`, `watch`, `exclude_gw1`, `exclude_gw1-5`  
**Related**: [Preseason Pipeline Master README](../README.md) · [Expected Stats (Stage 2)](../02-expected-stats-gw1-5/expected-stats-gw1-5.md) · [Canonical Preseason Chip Path (Stage 3)](../03-gw1-6-chip-wc4-squads/gw1-6-chip-wc4-squads.md)  
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
2. **Inject**: FFS XI players missing from scaffold matched via `players.parquet` first/second/web name (rejects `Bruno G.` vs `Bruno Fernandes`; accepts `Van Dijk` vs `Virgil`). Single-token source names match `web_name` or surname last token only (rejects `Nunes`→Vitor Reis, `James`→Trafford).
3. **Expected Role assignment**: unanimous dual-source → Nailed; single-source → Regular; lost both signals → Rotation. Same identity matcher as inject. Incoming transfers on Out of Contention/Cameo floor to Rotation pending new-club FFS/Meerkat.
4. **Availability Overlay**: API chance/status hints, then official overlays. Scoring overlays applied downstream in `availability_priors.py` (Watch haircut; Exclude GW1–5 = GW1–5 only).
5. **Draft Shortlist**: Nailed + Regular with non-`not_role_eligible` availability for human draft / solver ingestion.

---

## Findings

### 1. High-Level Summary & Role Distribution

- Contention set: **575** rows. Roles: Nailed 77 · Regular 157 · Rotation 144 · Cameo 116 · Out of Contention 81.
- Draft Eligible: **234** players (Nailed 77 + Regular 157).
- Availability: eligible 223 · not_role_eligible 264 · exclude_gw1 67 · watch 11 · exclude_gw1-5 10.
- **Injected Starters**: Touré (NEW MID), Steur (NEW MID), Meunier (SUN DEF), Walle Egeli (IPS FWD), Moore (TOT MID), Rushworth (COV GKP).
- **Kinsky (TOT)**: Regular Starter (FFS XI; Meerkat GK not unanimous).
- **Saliba (ARS)**: `exclude_gw1-5`. **Mac Allister (LIV)** / **Saka (ARS)**: `watch`.
- **Bruno Guimarães (ARS)**: transfer overlay applied; Rotation — not in current FFS/Meerkat Arsenal XI. **B.Fernandes (MUN)** and **Virgil (LIV)** nailed (identity match fix; previously swapped/dropped).
- **Vitor Reis (MCI)**: Rotation. Meerkat `Nunes` is Matheus N. (Regular), not Vitor Reis (middle-name false match). **Reece James (CHE)** nailed; Trafford does not match source `James`.
- **NEW GKP**: Pope Regular (Meerkat) + Horníček Regular (FFS). Split-source; neither Nailed. One club, two Regular GKs is honest under conflict rules.

### 2. 20-Club Player Role & Draft Availability Breakdown

Complete roster of all 575 players across the 20 Premier League clubs in the FPL API, showing assigned fit-role, baseline starter probability ($p_{\text{start}}$), Draft Availability overlay, and source signals.

#### 1. Arsenal (`ARS`) — 28 players
- **Summary**: Nailed: 3 · Regular: 9 · Rotation: 10 · Cameo: 3 · Out of Contention: 3 | Draft Eligible: 12

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Raya** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Arrizabalaga** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Reserve/third-choice goalkeeper. |
| **Meslier** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Reserve/third-choice goalkeeper. |
| **Gabriel** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Calafiori** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **J.Timber** | DEF | Regular Starter | 0.75 | `exclude_gw1` | Single-source or non-unanimous starter signal (Meerkat 🟢 / predicted). |
| **Mosquera** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **White** | DEF | Regular Starter | 0.75 | `watch` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Hincapie** | DEF | Rotation | 0.40 | `not_role_eligible` | Confirmed summer signing; Meerkat notes left-CB usage but Scout starts Calafiori, so minutes shared. |
| **Saliba** | DEF | Rotation | 0.40 | `exclude_gw1-5` | Key defender undergoing back rehabilitation, expected to return around GW5-6. |
| **Rice** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Lewis-Skelly** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Madueke** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Saka** | MID | Regular Starter | 0.75 | `watch` | Single-source or non-unanimous starter signal (Meerkat 🟢 / predicted). |
| **Tzolis** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Bruno G.** | MID | Rotation | 0.40 | `not_role_eligible` | Confirmed £75m transfer to Arsenal; not in current FFS/Meerkat Arsenal XI. |
| **Dowman** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Eze** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Martinelli** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Zubimendi** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Ødegaard** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Merino** | MID | Cameo | 0.10 | `not_role_eligible` | Squad rotation/bench option outside primary XI contention. |
| **Nelson** | MID | Cameo | 0.10 | `not_role_eligible` | Fringe squad player with limited minutes. |
| **Nwaneri** | MID | Cameo | 0.10 | `not_role_eligible` | Fringe squad player with limited minutes. |
| **Fábio Vieira** | MID | Out of Contention | 0.00 | `not_role_eligible` | Academy / developmental reserve not in first-team XI contention. |
| **Gyökeres** | FWD | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **G.Jesus** | FWD | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Havertz** | FWD | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |

#### 2. Aston Villa (`AVL`) — 27 players
- **Summary**: Nailed: 4 · Regular: 8 · Rotation: 2 · Cameo: 9 · Out of Contention: 4 | Draft Eligible: 12

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Martinez** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **M.Bizot** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Reserve/third-choice goalkeeper. |
| **Cash** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Konsa** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (Meerkat 🟢 / predicted). |
| **Lindelöf** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Maatsen** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Pau** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **A.García** | DEF | Cameo | 0.10 | `not_role_eligible` | Fringe squad player with limited minutes. |
| **Digne** | DEF | Cameo | 0.10 | `exclude_gw1` | Scout starts Maatsen at LB; Digne is the veteran backup/impact option. |
| **Mings** | DEF | Cameo | 0.10 | `not_role_eligible` | Squad rotation/bench option outside primary XI contention. |
| **Nedeljkovic** | DEF | Out of Contention | 0.00 | `not_role_eligible` | Academy / developmental reserve not in first-team XI contention. |
| **Kamara** | MID | Nailed Starter | 0.90 | `watch` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Barkley** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Buendía** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Garnacho** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **McGinn** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Gomes** | MID | Rotation | 0.40 | `exclude_gw1` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Manzambi** | MID | Rotation | 0.40 | `exclude_gw1` | £50m signing; Meerkat says likely Rogers replace but Scout XI omits him for Barkley/Buendía/McGinn — conservative Rotation. |
| **Alysson** | MID | Cameo | 0.10 | `not_role_eligible` | Fringe squad player with limited minutes. |
| **Bailey** | MID | Cameo | 0.10 | `not_role_eligible` | Not in Scout XI or Meerkat greens; wide rotation behind Buendía/Garnacho/McGinn. |
| **Bogarde** | MID | Cameo | 0.10 | `not_role_eligible` | Squad rotation/bench option outside primary XI contention. |
| **Burrowes** | MID | Cameo | 0.10 | `not_role_eligible` | Fringe squad player with limited minutes. |
| **George Hemmings** | MID | Cameo | 0.10 | `not_role_eligible` | Fringe squad player with limited minutes. |
| **Iling Jr** | MID | Out of Contention | 0.00 | `exclude_gw1` | Academy / developmental reserve not in first-team XI contention. |
| **Onana** | MID | Out of Contention | 0.00 | `exclude_gw1` | Long-term injury absence (Knee injury - Unknown return date). |
| **Watkins** | FWD | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Abraham** | FWD | Cameo | 0.10 | `exclude_gw1` | Injury / fitness concern (Shoulder injury - Expected back 23 Aug). |

#### 3. Bournemouth (`BOU`) — 26 players
- **Summary**: Nailed: 6 · Regular: 7 · Rotation: 3 · Cameo: 7 · Out of Contention: 3 | Draft Eligible: 13

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Petrović** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Dennis** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Reserve/third-choice goalkeeper. |
| **Forster** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Reserve/third-choice goalkeeper. |
| **Hill** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Truffert** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Silva** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Smith** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Diakité** | DEF | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Milosavljević** | DEF | Cameo | 0.10 | `exclude_gw1` | CB depth after Senesi exit; Scout prefers Hill/Diakité pairing for early XI. |
| **Soler** | DEF | Cameo | 0.10 | `not_role_eligible` | Fringe squad player with limited minutes. |
| **J.Araujo** | DEF | Out of Contention | 0.00 | `exclude_gw1` | Academy / developmental reserve not in first-team XI contention. |
| **Rayan** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Scott** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Tavernier** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Adams** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (Meerkat 🟢 / predicted). |
| **Cook** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Kluivert** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Kroupi.Jr** | MID | Regular Starter | 0.75 | `exclude_gw1-5` | Single-source or non-unanimous starter signal (Meerkat 🟢 / predicted). |
| **Christie** | MID | Rotation | 0.40 | `exclude_gw1` | Central midfield rotation; suspended for GW1 opening match. |
| **Adli** | MID | Cameo | 0.10 | `exclude_gw1` | Squad rotation/bench option outside primary XI contention. |
| **Brooks** | MID | Cameo | 0.10 | `not_role_eligible` | Squad rotation/bench option outside primary XI contention. |
| **Gannon-Doak** | MID | Cameo | 0.10 | `not_role_eligible` | Fringe squad player with limited minutes. |
| **Tóth.A** | MID | Cameo | 0.10 | `not_role_eligible` | Fringe squad player with limited minutes. |
| **Evanilson** | FWD | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Rodríguez** | FWD | Rotation | 0.40 | `not_role_eligible` | Confirmed £25.7m striker; Meerkat frames as competing with Evanilson for the No.9 shirt. |
| **Enes Ünal** | FWD | Cameo | 0.10 | `exclude_gw1` | Fringe squad player with limited minutes. |

#### 4. Brentford (`BRE`) — 26 players
- **Summary**: Nailed: 6 · Regular: 5 · Rotation: 4 · Cameo: 9 · Out of Contention: 2 | Draft Eligible: 11

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Kelleher** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Valdimarsson** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Reserve/third-choice goalkeeper. |
| **Collins** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Kayode** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Ajer** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Van den Berg** | DEF | Rotation | 0.40 | `exclude_gw1` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
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
| **Sangaré** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Carvalho** | MID | Rotation | 0.40 | `exclude_gw1` | Attacking midfield rotation recovering from knee issue. |
| **Milambo** | MID | Rotation | 0.40 | `not_role_eligible` | Young midfield signing providing depth behind Janelt and Jensen. |
| **Yarmoliuk** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Anthony** | MID | Cameo | 0.10 | `not_role_eligible` | Confirmed £15m signing; Meerkat explicitly lists Anthony as backup to Schade/Dango band. |
| **Damsgaard** | MID | Cameo | 0.10 | `not_role_eligible` | Creative depth outside Scout XI; competes with Jensen for advanced mid minutes. |
| **Dasilva** | MID | Cameo | 0.10 | `not_role_eligible` | Fringe squad player with limited minutes. |
| **Thiago** | FWD | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Furo** | FWD | Cameo | 0.10 | `not_role_eligible` | Fringe squad player with limited minutes. |
| **Wilson** | FWD | Cameo | 0.10 | `not_role_eligible` | Free signing Callum Wilson; backup to nailed Thiago rather than early draft starter. |

#### 5. Brighton (`BHA`) — 30 players
- **Summary**: Nailed: 4 · Regular: 8 · Rotation: 4 · Cameo: 9 · Out of Contention: 5 | Draft Eligible: 12

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Verbruggen** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Steele** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Reserve/third-choice goalkeeper. |
| **Vuskovic** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Wieffer** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Boscagli** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **De Cuyper** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Dunk** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (Meerkat 🟢 / predicted). |
| **F.Kadıoğlu** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (Meerkat 🟢 / predicted). |
| **Coppola** | DEF | Cameo | 0.10 | `not_role_eligible` | Fringe squad player with limited minutes. |
| **Igor** | DEF | Cameo | 0.10 | `not_role_eligible` | Fringe squad player with limited minutes. |
| **Struijk** | DEF | Cameo | 0.10 | `not_role_eligible` | Confirmed £20m signing from Leeds; Meerkat explicitly benches Struijk behind Dunk/Vuskovic. |
| **Costinha** | DEF | Out of Contention | 0.00 | `not_role_eligible` | Academy / developmental reserve not in first-team XI contention. |
| **Svoboda** | DEF | Out of Contention | 0.00 | `not_role_eligible` | Academy / developmental reserve not in first-team XI contention. |
| **Groß** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Ayari** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Gomez** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Hinshelwood** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Baleba** | MID | Rotation | 0.40 | `exclude_gw1` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Minteh** | MID | Rotation | 0.40 | `exclude_gw1` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Mitoma** | MID | Rotation | 0.40 | `exclude_gw1` | First-team winger sidelined by hamstring injury for GW1. |
| **Buonanotte** | MID | Cameo | 0.10 | `exclude_gw1` | Fringe squad player with limited minutes. |
| **Howell** | MID | Cameo | 0.10 | `exclude_gw1` | Fringe squad player with limited minutes. |
| **O'Riley** | MID | Cameo | 0.10 | `not_role_eligible` | Fringe squad player with limited minutes. |
| **Oriola** | MID | Cameo | 0.10 | `not_role_eligible` | Fringe squad player with limited minutes. |
| **Watson** | MID | Cameo | 0.10 | `exclude_gw1` | Fringe squad player with limited minutes. |
| **Yohanna** | MID | Out of Contention | 0.00 | `not_role_eligible` | Academy / developmental reserve not in first-team XI contention. |
| **Georginio** | FWD | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Tzimas** | FWD | Rotation | 0.40 | `not_role_eligible` | Young striker providing depth behind Georginio Rutter. |
| **Kostoulas** | FWD | Cameo | 0.10 | `not_role_eligible` | Fringe squad player with limited minutes. |
| **Ferguson** | FWD | Out of Contention | 0.00 | `exclude_gw1-5` | Long-term ankle injury keeps him out of opening gameweeks. |

#### 6. Chelsea (`CHE`) — 35 players
- **Summary**: Nailed: 8 · Regular: 4 · Rotation: 11 · Cameo: 8 · Out of Contention: 4 | Draft Eligible: 12

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Sánchez** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Jörgensen** | GKP | Out of Contention | 0.00 | `exclude_gw1` | Backup/reserve goalkeeper behind established starter. |
| **Penders** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Backup/reserve goalkeeper behind established starter. |
| **Colwill** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **James** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Lacroix** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Palestra** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Chalobah** | DEF | Rotation | 0.40 | `exclude_gw1` | Senior squad rotation player for CHE. |
| **Gusto** | DEF | Rotation | 0.40 | `not_role_eligible` | Established squad player for CHE; role Rotation. |
| **Hato** | DEF | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Tosin** | DEF | Rotation | 0.40 | `not_role_eligible` | Established squad player for CHE; role Rotation. |
| **Acheampong** | DEF | Cameo | 0.10 | `not_role_eligible` | Depth / cameo bench player for CHE. |
| **Anselmino** | DEF | Cameo | 0.10 | `not_role_eligible` | Depth / cameo bench player for CHE. |
| **B.Badiashile** | DEF | Cameo | 0.10 | `not_role_eligible` | Depth / cameo bench player for CHE. |
| **Disasi** | DEF | Cameo | 0.10 | `not_role_eligible` | Depth / cameo bench player for CHE. |
| **M.Sarr** | DEF | Cameo | 0.10 | `not_role_eligible` | Depth / cameo bench player for CHE. |
| **Fofana** | DEF | Out of Contention | 0.00 | `exclude_gw1` | Injured/suspended: Suspended until 6 Sep |
| **Caicedo** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Palmer** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Rogers** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Enzo** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (Meerkat 🟢 / predicted). |
| **Lavia** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Neto** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **D.Essugo** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Estêvão** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Gittens** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Quenda** | MID | Rotation | 0.40 | `not_role_eligible` | Established squad player for CHE; role Rotation. |
| **Henderson** | MID | Out of Contention | 0.00 | `not_role_eligible` | Left Brentford as a free agent. |
| **João Pedro** | FWD | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Delap** | FWD | Rotation | 0.40 | `not_role_eligible` | Senior squad rotation player for CHE. |
| **N.Jackson** | FWD | Rotation | 0.40 | `not_role_eligible` | Senior squad rotation player for CHE. |
| **Welbeck** | FWD | Rotation | 0.40 | `not_role_eligible` | Confirmed £5m transfer to Chelsea as forward depth. |
| **Emegha** | FWD | Cameo | 0.10 | `not_role_eligible` | Depth / cameo bench player for CHE. |
| **Marc Guiu** | FWD | Cameo | 0.10 | `not_role_eligible` | Depth / cameo bench player for CHE. |
| **Mheuka** | FWD | Cameo | 0.10 | `not_role_eligible` | Depth / cameo bench player for CHE. |

#### 7. Coventry City (`COV`) — 30 players
- **Summary**: Nailed: 0 · Regular: 10 · Rotation: 10 · Cameo: 8 · Out of Contention: 2 | Draft Eligible: 10

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Rushworth** | GKP | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Wilson** | GKP | Rotation | 0.40 | `not_role_eligible` | Established squad player for COV; role Rotation. |
| **Dovin** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Backup/reserve goalkeeper behind established starter. |
| **Amenda** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Thomas** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **van Ewijk** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Dasilva** | DEF | Rotation | 0.40 | `not_role_eligible` | Established squad player for COV; role Rotation. |
| **Kitching** | DEF | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Bidwell** | DEF | Cameo | 0.10 | `not_role_eligible` | Depth / cameo bench player for COV. |
| **Brau** | DEF | Cameo | 0.10 | `not_role_eligible` | Depth / cameo bench player for COV. |
| **Kesler-Hayden** | DEF | Cameo | 0.10 | `not_role_eligible` | Depth / cameo bench player for COV. |
| **Latibeaudiere** | DEF | Cameo | 0.10 | `not_role_eligible` | Depth / cameo bench player for COV. |
| **Woolfenden** | DEF | Cameo | 0.10 | `not_role_eligible` | Depth / cameo bench player for COV. |
| **Grimes** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Onyeka** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Tchaouna** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Yirenkyi** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Andrews** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Eccles** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Mason-Clark** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Rudoni** | MID | Rotation | 0.40 | `not_role_eligible` | Established squad player for COV; role Rotation. |
| **Sakamoto** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Torp** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Borges Rodrigues** | MID | Cameo | 0.10 | `not_role_eligible` | Depth / cameo bench player for COV. |
| **Shepherd** | MID | Cameo | 0.10 | `not_role_eligible` | Depth / cameo bench player for COV. |
| **Simms** | FWD | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Thomas-Asante** | FWD | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Wright** | FWD | Rotation | 0.40 | `exclude_gw1` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Markelo** | FWD | Cameo | 0.10 | `exclude_gw1` | Established squad player for COV; role Cameo. |
| **Bassette** | FWD | Out of Contention | 0.00 | `exclude_gw1` | Injured/suspended: Has joined KVC Westerlo on loan for the rest of the season |

#### 8. Crystal Palace (`CRY`) — 29 players
- **Summary**: Nailed: 4 · Regular: 8 · Rotation: 7 · Cameo: 7 · Out of Contention: 3 | Draft Eligible: 12

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Henderson** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Benitez** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Backup/reserve goalkeeper behind established starter. |
| **Matthews** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Backup/reserve goalkeeper behind established starter. |
| **Mitchell** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Richards** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Canvot** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Chadi Riad** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Mingueza** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Muñoz** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (Meerkat 🟢 / predicted). |
| **Cardines** | DEF | Rotation | 0.40 | `exclude_gw1` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Sosa** | DEF | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Sarr** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Kamada** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **McNeil** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Wharton** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Devenny** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Lerma** | MID | Rotation | 0.40 | `not_role_eligible` | Established squad player for CRY; role Rotation. |
| **Yeremy** | MID | Rotation | 0.40 | `not_role_eligible` | Established squad player for CRY; role Rotation. |
| **Doucouré** | MID | Cameo | 0.10 | `not_role_eligible` | Depth / cameo bench player for CRY. |
| **Drakes-Thomas** | MID | Cameo | 0.10 | `not_role_eligible` | Depth / cameo bench player for CRY. |
| **Esse** | MID | Cameo | 0.10 | `not_role_eligible` | Established squad player for CRY; role Cameo. |
| **Guessand** | MID | Cameo | 0.10 | `not_role_eligible` | Attacking depth only; neither Scout XI nor Meerkat green for early GW starts. |
| **Hughes** | MID | Cameo | 0.10 | `not_role_eligible` | Depth / cameo bench player for CRY. |
| **J.Rak-Sakyi** | MID | Cameo | 0.10 | `not_role_eligible` | Depth / cameo bench player for CRY. |
| **M.França** | MID | Cameo | 0.10 | `not_role_eligible` | Depth / cameo bench player for CRY. |
| **Strand Larsen** | FWD | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Mateta** | FWD | Rotation | 0.40 | `not_role_eligible` | Established squad player for CRY; role Rotation. |
| **Nketiah** | FWD | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Uche** | FWD | Out of Contention | 0.00 | `exclude_gw1` | Injured/suspended: has returned to Getafe CF |

#### 9. Everton (`EVE`) — 24 players
- **Summary**: Nailed: 4 · Regular: 8 · Rotation: 8 · Cameo: 2 · Out of Contention: 2 | Draft Eligible: 12

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Pickford** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **King** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Backup/reserve goalkeeper behind established starter. |
| **Travers** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Backup/reserve goalkeeper behind established starter. |
| **Tarkowski** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Branthwaite** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Mykolenko** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **O'Brien** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Aznou** | DEF | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Keane** | DEF | Rotation | 0.40 | `not_role_eligible` | Established squad player for EVE; role Rotation. |
| **Patterson** | DEF | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Dewsbury-Hall** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Ndiaye** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Armstrong** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Garner** | MID | Regular Starter | 0.75 | `exclude_gw1` | Single-source or non-unanimous starter signal (Meerkat 🟢 / predicted). |
| **Hackney** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Röhl** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Dibling** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **George** | MID | Rotation | 0.40 | `not_role_eligible` | Established squad player for EVE; role Rotation. |
| **Iroegbunam** | MID | Rotation | 0.40 | `exclude_gw1` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Johnson** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Alcaraz** | MID | Cameo | 0.10 | `not_role_eligible` | Depth / cameo bench player for EVE. |
| **Nørgaard** | MID | Cameo | 0.10 | `not_role_eligible` | Fringe squad player with limited minutes. |
| **Barry** | FWD | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Beto** | FWD | Rotation | 0.40 | `not_role_eligible` | Established squad player for EVE; role Rotation. |

#### 10. Fulham (`FUL`) — 22 players
- **Summary**: Nailed: 4 · Regular: 7 · Rotation: 7 · Cameo: 1 · Out of Contention: 3 | Draft Eligible: 11

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Leno** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Lecomte** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Backup/reserve goalkeeper behind established starter. |
| **McNally** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Backup/reserve goalkeeper behind established starter. |
| **Bassey** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Robinson** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Castagne** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **J.Cuenca** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Sessegnon** | DEF | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Tete** | DEF | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Andersen** | DEF | Out of Contention | 0.00 | `exclude_gw1` | Injured/suspended: Suspended until 29 Aug |
| **Iwobi** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Berge** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Bobb** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **King** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Palacios** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Kevin** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Reed** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Smith Rowe** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Cairney** | MID | Cameo | 0.10 | `exclude_gw1` | Established squad player for FUL; role Cameo. |
| **Gonzalo** | FWD | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Kusi-Asare** | FWD | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Muniz** | FWD | Rotation | 0.40 | `not_role_eligible` | Established squad player for FUL; role Rotation. |

#### 11. Hull City (`HUL`) — 34 players
- **Summary**: Nailed: 0 · Regular: 11 · Rotation: 8 · Cameo: 10 · Out of Contention: 5 | Draft Eligible: 11

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Tzolakis** | GKP | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Butland** | GKP | Rotation | 0.40 | `exclude_gw1` | Signed from Rangers (£3m); in competition with Konstantinos Tzolakis for #1 goalkeeper spot. |
| **Cartwright** | GKP | Out of Contention | 0.00 | `exclude_gw1` | Loaned out to Grimsby Town for the 2026/27 season. |
| **Lo-Tutala** | GKP | Out of Contention | 0.00 | `exclude_gw1` | Third-choice goalkeeper; outside the active matchday squad. |
| **Phillips** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Backup goalkeeper behind Jack Butland and new signings; no first-team starts projected. |
| **Ajayi** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Coyle** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Giles** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Mendy** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Egan** | DEF | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Hughes** | DEF | Rotation | 0.40 | `exclude_gw1` | Centre-back rotation option competing with Egan, Ajayi, and newly signed Nobel Mendy. |
| **Targett** | DEF | Rotation | 0.40 | `not_role_eligible` | Signed on free transfer from Newcastle; experienced competition at left-back. |
| **Drameh** | DEF | Cameo | 0.10 | `exclude_gw1` | Fullback depth providing cover for Coyle and Giles. |
| **Jacob** | DEF | Cameo | 0.10 | `not_role_eligible` | Backup left-back providing cover behind Ryan Giles. |
| **McNair** | DEF | Cameo | 0.10 | `not_role_eligible` | Veteran defensive cover for centre-back and central midfield. |
| **McCarthy** | DEF | Out of Contention | 0.00 | `not_role_eligible` | Fringe youth defender outside senior matchday squad. |
| **Belloumi** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Crooks** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Hjertø-Dahl** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Slater** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Stroud** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Kamara** | MID | Rotation | 0.40 | `exclude_gw1` | Winger and attacking midfield rotation challenger. |
| **Millar** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Morita** | MID | Rotation | 0.40 | `watch` | Free transfer signing from Sporting CP; competing for starting central midfield berth. |
| **Ömür** | MID | Rotation | 0.40 | `not_role_eligible` | Attacking playmaker competing with Crooks, Belloumi, and Millar. |
| **Akintola** | MID | Cameo | 0.10 | `not_role_eligible` | Wide attacking bench option. |
| **Dowell** | MID | Cameo | 0.10 | `not_role_eligible` | Attacking midfield option from the bench. |
| **Gelhardt** | MID | Cameo | 0.10 | `not_role_eligible` | Attacking option providing late substitute minutes. |
| **Gyabi** | MID | Cameo | 0.10 | `exclude_gw1` | Central midfield cover behind Slater and Morita/Crooks. |
| **Zambrano** | MID | Cameo | 0.10 | `exclude_gw1` | Young midfielder signed from Maribor; developmental squad option. |
| **Matazo** | MID | Out of Contention | 0.00 | `exclude_gw1-5` | Sidelined with significant knee injury; unknown return date. |
| **McBurnie** | FWD | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Burstow** | FWD | Cameo | 0.10 | `exclude_gw1` | Young forward providing bench attacking depth. |
| **Destan** | FWD | Cameo | 0.10 | `exclude_gw1` | Backup centre-forward behind McBurnie. |

#### 12. Ipswich Town (`IPS`) — 30 players
- **Summary**: Nailed: 0 · Regular: 11 · Rotation: 11 · Cameo: 5 · Out of Contention: 3 | Draft Eligible: 11

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Scherpen** | GKP | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Van Oevelen** | GKP | Rotation | 0.40 | `not_role_eligible` | New signing from FC Volendam (£3.4m); competing with Scherpen and Walton. |
| **Walton** | GKP | Rotation | 0.40 | `not_role_eligible` | Goalkeeper depth competing with Scherpen and Van Oevelen. |
| **Button** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Veteran 4th choice goalkeeper. |
| **Palmer** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Third-choice goalkeeper. |
| **Davis** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Diop** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Greaves** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **O'Shea** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Furlong** | DEF | Rotation | 0.40 | `not_role_eligible` | Right-back competitor battling Ben Johnson and Dara O'Shea. |
| **Johnson** | DEF | Rotation | 0.40 | `not_role_eligible` | Fullback cover at right-back and wing-back. |
| **Kipré** | DEF | Rotation | 0.40 | `not_role_eligible` | Centre-back rotation option behind Diop, Greaves, and O'Shea. |
| **Fatawu** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Lukić** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Maeda** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Núñez** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Clarke** | MID | Rotation | 0.40 | `not_role_eligible` | High-quality wide rotation option competing with Philogene, Maeda, and Fatawu. |
| **Matusiwa** | MID | Rotation | 0.40 | `exclude_gw1` | Midfield starter candidate sidelined with muscular injury; expected back early season. |
| **Mehmeti** | MID | Rotation | 0.40 | `not_role_eligible` | Attacking midfielder competing for minutes in the creative line. |
| **Philogene** | MID | Rotation | 0.40 | `not_role_eligible` | Attacking winger in close rotation for wide starting spots. |
| **Szmodics** | MID | Rotation | 0.40 | `exclude_gw1` | Attacking midfielder / second-striker sharing minutes with Nunez and wingers. |
| **Burns** | MID | Cameo | 0.10 | `exclude_gw1` | Winger rotation / impact substitute behind Fatawu and Maeda. |
| **McAteer** | MID | Cameo | 0.10 | `not_role_eligible` | Midfield bench option. |
| **Ogbene** | MID | Cameo | 0.10 | `not_role_eligible` | Pacy winger offering late substitution threat. |
| **Taylor** | MID | Out of Contention | 0.00 | `exclude_gw1` | Sidelined with knee injury; out for GW1. |
| **Emersonn** | FWD | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Walle Egeli** | FWD | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Hirst** | FWD | Rotation | 0.40 | `not_role_eligible` | Striker rotation competing with Emersonn and Walle Egeli. |
| **Akpom** | FWD | Cameo | 0.10 | `not_role_eligible` | Experienced forward depth and substitute option. |
| **Al-Hamadi** | FWD | Cameo | 0.10 | `not_role_eligible` | Forward depth option off the bench. |

#### 13. Leeds United (`LEE`) — 24 players
- **Summary**: Nailed: 7 · Regular: 5 · Rotation: 4 · Cameo: 6 · Out of Contention: 2 | Draft Eligible: 12

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Trafford** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Perri** | GKP | Rotation | 0.40 | `not_role_eligible` | In competition with newly signed £45m goalkeeper James Trafford for starting berth. |
| **Muharemović** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Rodon** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Bijol** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Bogle** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Justin** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Gudmundsson** | DEF | Rotation | 0.40 | `exclude_gw1` | Left-back depth competing with James Justin. |
| **Bornauw** | DEF | Cameo | 0.10 | `not_role_eligible` | Centre-back cover behind Rodon, Bijol, and Muharemovic. |
| **Ampadu** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Stach** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Wilson** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Aaronson** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Okafor** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (Meerkat 🟢 / predicted). |
| **Longstaff** | MID | Rotation | 0.40 | `not_role_eligible` | Central midfield depth behind Stach and Ampadu. |
| **Tanaka** | MID | Rotation | 0.40 | `not_role_eligible` | Progressive central midfielder rotating in engine room. |
| **Gnonto** | MID | Cameo | 0.10 | `not_role_eligible` | Winger impact substitute behind Wilson and Okafor. |
| **Gruev** | MID | Cameo | 0.10 | `exclude_gw1` | Defensive midfield cover for Ethan Ampadu. |
| **James** | MID | Cameo | 0.10 | `not_role_eligible` | Pacy wide substitute offering direct attacking threat. |
| **Harrison** | MID | Out of Contention | 0.00 | `exclude_gw1` | Permanent transfer to MLS New England Revolution. |
| **Calvert-Lewin** | FWD | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Nmecha** | FWD | Cameo | 0.10 | `not_role_eligible` | Backup striker behind Calvert-Lewin. |
| **Piroe** | FWD | Cameo | 0.10 | `not_role_eligible` | Forward / second-striker depth providing bench goal threat. |
| **Mateo Joseph** | FWD | Out of Contention | 0.00 | `exclude_gw1` | Sidelined with knee injury; unknown return date. |

#### 14. Liverpool (`LIV`) — 34 players
- **Summary**: Nailed: 7 · Regular: 4 · Rotation: 7 · Cameo: 4 · Out of Contention: 12 | Draft Eligible: 11

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **A.Becker** | GKP | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Mamardashvili** | GKP | Rotation | 0.40 | `not_role_eligible` | Elite backup goalkeeper behind Alisson; cup/rotation keeper. |
| **Davies** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Reserve goalkeeper. |
| **Jaros** | GKP | Out of Contention | 0.00 | `exclude_gw1` | Injured goalkeeper (knee injury); unknown return date. |
| **Pecsi** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Academy goalkeeper outside matchday squad. |
| **Woodman** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Third-choice goalkeeper. |
| **Jacquet** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Kerkez** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Virgil** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Frimpong** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Gomez** | DEF | Rotation | 0.40 | `exclude_gw1` | Versatile defensive rotation option currently nursing muscular injury. |
| **Tsimikas** | DEF | Rotation | 0.40 | `not_role_eligible` | Backup left-back providing cover for Milos Kerkez. |
| **Bradley** | DEF | Cameo | 0.10 | `exclude_gw1` | Right-back challenger behind Frimpong; currently recovering from knee injury. |
| **Leoni** | DEF | Out of Contention | 0.00 | `exclude_gw1` | Youth defender recovering from knee injury. |
| **Lucky** | DEF | Out of Contention | 0.00 | `not_role_eligible` | Academy defender outside senior squad. |
| **Ramsay** | DEF | Out of Contention | 0.00 | `not_role_eligible` | Fringe right-back outside matchday squad. |
| **Gravenberch** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Szoboszlai** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Wirtz** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Gakpo** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Mac Allister** | MID | Regular Starter | 0.75 | `watch` | Single-source or non-unanimous starter signal (Meerkat 🟢 / predicted). |
| **Ngumoha** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **C.Jones** | MID | Rotation | 0.40 | `not_role_eligible` | Central midfield rotation option behind Gravenberch, Szoboszlai, and Mac Allister. |
| **Chiesa** | MID | Rotation | 0.40 | `not_role_eligible` | Experienced forward/winger rotation providing depth across frontline. |
| **Elliott** | MID | Rotation | 0.40 | `not_role_eligible` | Attacking midfield / right wing rotation option. |
| **Endo** | MID | Cameo | 0.10 | `watch` | Veteran defensive midfield cover; 75% flag with ankle knock. |
| **Munoz** | MID | Cameo | 0.10 | `not_role_eligible` | Spanish winger providing attacking depth. |
| **Bajcetic** | MID | Out of Contention | 0.00 | `exclude_gw1` | Hamstring injury; expected back late August. |
| **Koumas** | MID | Out of Contention | 0.00 | `not_role_eligible` | Youth forward outside senior matchday squad. |
| **McConnell** | MID | Out of Contention | 0.00 | `not_role_eligible` | Reserve midfielder. |
| **Nyoni** | MID | Out of Contention | 0.00 | `not_role_eligible` | Young midfield prospect outside primary senior squad. |
| **Isak** | FWD | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Ekitiké** | FWD | Cameo | 0.10 | `exclude_gw1` | Striker challenger behind Isak currently sidelined with Achilles injury. |
| **Danns** | FWD | Out of Contention | 0.00 | `exclude_gw1` | Injured young forward (unspecified injury); out for GW1. |

#### 15. Man City (`MCI`) — 29 players
- **Summary**: Nailed: 5 · Regular: 8 · Rotation: 9 · Cameo: 1 · Out of Contention: 6 | Draft Eligible: 13

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Donnarumma** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Bettinelli** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Third-choice goalkeeper. |
| **Guéhi** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Gvardiol** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Khusanov** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Matheus N.** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (Meerkat 🟢 / predicted). |
| **O'Reilly** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (Meerkat 🟢 / predicted). |
| **Rúben** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Aït-Nouri** | DEF | Rotation | 0.40 | `not_role_eligible` | Left-back / wing-back rotation option competing with Gvardiol and O'Reilly. |
| **Lewis** | DEF | Rotation | 0.40 | `not_role_eligible` | Inverted fullback and midfield utility sub providing depth across backline. |
| **Vitor Reis** | DEF | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Alleyne** | DEF | Out of Contention | 0.00 | `not_role_eligible` | Youth centre-back outside primary senior lineup. |
| **Anderson** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Semenyo** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Doku** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Foden** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Kovačić** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Cherki** | MID | Rotation | 0.40 | `not_role_eligible` | Dynamic attacking playmaker rotating across attacking midfield and wide slots. |
| **Grealish** | MID | Rotation | 0.40 | `watch` | Creative winger / attacking midfield rotation; managing minor foot knock (75% flag). |
| **N.Gonzalez** | MID | Rotation | 0.40 | `not_role_eligible` | Central midfield rotation option behind Reijnders, Anderson, and Rodri. |
| **Reijnders** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Rodrigo** | MID | Rotation | 0.40 | `exclude_gw1` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Savinho** | MID | Rotation | 0.40 | `not_role_eligible` | Winger rotation competing with Doku, Semenyo, and Cherki. |
| **Echeverri** | MID | Out of Contention | 0.00 | `not_role_eligible` | Young Argentine playmaker in developmental phase. |
| **Monga** | MID | Out of Contention | 0.00 | `not_role_eligible` | Academy winger. |
| **Mukasa** | MID | Out of Contention | 0.00 | `not_role_eligible` | Academy midfielder. |
| **Phillips** | MID | Out of Contention | 0.00 | `not_role_eligible` | Out of favour central midfielder outside matchday plans. |
| **Haaland** | FWD | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Marmoush** | FWD | Cameo | 0.10 | `not_role_eligible` | Attacking forward backup behind Haaland and wide starters. |

#### 16. Man Utd (`MUN`) — 33 players
- **Summary**: Nailed: 5 · Regular: 6 · Rotation: 9 · Cameo: 7 · Out of Contention: 6 | Draft Eligible: 11

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Lammens** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Bayindir** | GKP | Cameo | 0.10 | `exclude_gw1` | Reserve goalkeeper behind Lammens and Darlow. |
| **Darlow** | GKP | Cameo | 0.10 | `not_role_eligible` | Signed on free transfer from Leeds as senior backup GKP behind Lammens. |
| **Heaton** | GKP | Out of Contention | 0.00 | `exclude_gw1` | Veteran third/fourth choice goalkeeper outside matchday squad. |
| **Dalot** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Maguire** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Shaw** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Heaven** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Martinez** | DEF | Rotation | 0.40 | `not_role_eligible` | Managing thigh injury recovery; featured as second-half substitute vs AC Milan. |
| **Mazraoui** | DEF | Rotation | 0.40 | `not_role_eligible` | Started at RB in final friendly; versatile fullback cover competing with Dalot and Shaw. |
| **Yoro** | DEF | Rotation | 0.40 | `not_role_eligible` | Central defensive rotation option behind Maguire and Heaven/Martinez. |
| **Amass** | DEF | Cameo | 0.10 | `not_role_eligible` | Youth backup left-back behind Shaw and Mazraoui. |
| **De Ligt** | DEF | Cameo | 0.10 | `exclude_gw1-5` | Sidelined with back injury with unknown return date; CB depth behind Maguire, Heaven, and Yoro. |
| **Fredricson** | DEF | Out of Contention | 0.00 | `not_role_eligible` | Academy center-back depth; outside senior matchday squad. |
| **B.Fernandes** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Amad** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Andrey Santos** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Dorgu** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Mbeumo** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Tielemans** | MID | Regular Starter | 0.75 | `watch` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Cunha** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Mainoo** | MID | Rotation | 0.40 | `not_role_eligible` | Midfield rotation challenger behind Santos and Tielemans. |
| **Mount** | MID | Rotation | 0.40 | `watch` | Attacking midfield and wide rotation option behind Bruno, Amad, and Mbeumo. |
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
- **Summary**: Nailed: 1 · Regular: 11 · Rotation: 9 · Cameo: 3 · Out of Contention: 1 | Draft Eligible: 12

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Horníček** | GKP | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Pope** | GKP | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (Meerkat 🟢 / predicted). |
| **Jaouen** | GKP | Cameo | 0.10 | `not_role_eligible` | £18.5m summer signing from Reims; started friendly vs Strasbourg as cup/rotation GKP. |
| **Gillespie** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Reserve goalkeeper behind Pope, Hornicek, and Jaouen. |
| **Thiaw** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Botman** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Hall** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Livramento** | DEF | Regular Starter | 0.75 | `watch` | Single-source or non-unanimous starter signal (Meerkat 🟢 / predicted). |
| **Burn** | DEF | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Schär** | DEF | Rotation | 0.40 | `not_role_eligible` | Started vs Strasbourg; veteran CB competing with Thiaw, Botman, and Burn. |
| **A.Murphy** | DEF | Cameo | 0.10 | `exclude_gw1` | Youth defender depth behind Hall, Burn, and Botman. |
| **Bamba** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Elanga** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **L.Miley** | MID | Regular Starter | 0.75 | `exclude_gw1` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Steur** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Touré** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Barnes** | MID | Rotation | 0.40 | `not_role_eligible` | Started vs Leverkusen; winger rotation with Elanga, Toure, and J.Murphy. |
| **J.Murphy** | MID | Rotation | 0.40 | `not_role_eligible` | Started vs Strasbourg, assisting Osula; wide attacking rotation. |
| **J.Ramsey** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Joelinton** | MID | Rotation | 0.40 | `exclude_gw1` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Willock** | MID | Rotation | 0.40 | `not_role_eligible` | Started vs Strasbourg; midfield box-to-box depth. |
| **Wissa** | FWD | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Osula** | FWD | Rotation | 0.40 | `not_role_eligible` | Scored goal vs Strasbourg; striker depth behind Wissa and Woltemade. |
| **Woltemade** | FWD | Rotation | 0.40 | `not_role_eligible` | Started at striker vs Leverkusen; rotating with Wissa and Osula. |
| **Neave** | FWD | Cameo | 0.10 | `not_role_eligible` | Academy forward featured as late substitute in friendlies. |

#### 18. Nott'm Forest (`NFO`) — 28 players
- **Summary**: Nailed: 1 · Regular: 10 · Rotation: 7 · Cameo: 6 · Out of Contention: 4 | Draft Eligible: 11

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Sels** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **John** | GKP | Cameo | 0.10 | `not_role_eligible` | Backup goalkeeper behind Sels. |
| **Aina** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Diomande** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Milenković** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Murillo** | DEF | Regular Starter | 0.75 | `watch` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **N.Williams** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Jair Cunha** | DEF | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Morato** | DEF | Cameo | 0.10 | `not_role_eligible` | Central defensive cover behind Murillo, Milenkovic, Diomande, and Jair Cunha. |
| **Netz** | DEF | Cameo | 0.10 | `not_role_eligible` | Backup left wing-back behind Aina. |
| **Abbott** | DEF | Out of Contention | 0.00 | `not_role_eligible` | Youth defender in reserve pool. |
| **Bindon** | DEF | Out of Contention | 0.00 | `not_role_eligible` | Young defender outside senior rotation. |
| **O.Richards** | DEF | Out of Contention | 0.00 | `not_role_eligible` | Left-back depth outside matchday squad. |
| **Savona** | DEF | Out of Contention | 0.00 | `exclude_gw1-5` | Sidelined with significant knee injury; excluded for early season. |
| **Gibbs-White** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Ndoye** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Sangaré** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Schlager** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Dominguez** | MID | Rotation | 0.40 | `not_role_eligible` | Central midfield rotation behind Sangare and Schlager. |
| **Hudson-Odoi** | MID | Rotation | 0.40 | `not_role_eligible` | Attacking rotation option recovering from minor thigh strain. |
| **Hutchinson** | MID | Rotation | 0.40 | `not_role_eligible` | Wide attacker rotating with Ndoye, Bakwa, and Hudson-Odoi. |
| **Yates** | MID | Rotation | 0.40 | `not_role_eligible` | Midfield rotation and leadership option off the bench. |
| **Bakwa** | MID | Cameo | 0.10 | `not_role_eligible` | Wide attacking depth option. |
| **McAtee** | MID | Cameo | 0.10 | `not_role_eligible` | Attacking midfield cover behind Gibbs-White. |
| **Igor Jesus** | FWD | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Kalimuendo** | FWD | Rotation | 0.40 | `not_role_eligible` | Impressed with 3 goals in preseason; primary impact striker sub. |
| **Wood** | FWD | Rotation | 0.40 | `not_role_eligible` | Experienced striker competing with Igor Jesus and Kalimuendo. |
| **Awoniyi** | FWD | Cameo | 0.10 | `not_role_eligible` | Striker depth behind Igor Jesus, Wood, and Kalimuendo. |

#### 19. Spurs (`TOT`) — 36 players
- **Summary**: Nailed: 1 · Regular: 11 · Rotation: 12 · Cameo: 3 · Out of Contention: 9 | Draft Eligible: 12

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Kinsky** | GKP | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Dubravka** | GKP | Rotation | 0.40 | `not_role_eligible` | Free transfer from Burnley as experienced senior backup GKP. |
| **Vicario** | GKP | Rotation | 0.40 | `not_role_eligible` | Senior goalkeeper returning to fitness; competing with Kinsky for #1 shirt. |
| **Austin** | GKP | Out of Contention | 0.00 | `not_role_eligible` | Third/fourth choice goalkeeper; featured in behind-closed-doors match. |
| **Van Hecke** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Pedro Porro** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (Meerkat 🟢 / predicted). |
| **Robertson** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Senesi** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Van de Ven** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (Meerkat 🟢 / predicted). |
| **Danso** | DEF | Rotation | 0.40 | `not_role_eligible` | Started behind-closed-doors match vs Hoffenheim; CB rotation depth. |
| **Romero** | DEF | Rotation | 0.40 | `exclude_gw1` | Late return after international duty; central defensive rotation behind Van Hecke, Van de Ven, and Senesi. |
| **Udogie** | DEF | Rotation | 0.40 | `not_role_eligible` | Managing fitness after preseason knock; competing with Robertson for left-back spot. |
| **Davies** | DEF | Cameo | 0.10 | `not_role_eligible` | Veteran defender; scored in secondary friendly vs Hoffenheim. |
| **Spence** | DEF | Cameo | 0.10 | `not_role_eligible` | Fullback depth behind Pedro Porro, Robertson, and Gray. |
| **Byfield** | DEF | Out of Contention | 0.00 | `not_role_eligible` | Academy defender outside senior rotation. |
| **Phillips** | DEF | Out of Contention | 0.00 | `not_role_eligible` | Young center-back outside first-team matchday squad. |
| **Rowswell** | DEF | Out of Contention | 0.00 | `not_role_eligible` | Academy defender outside senior rotation. |
| **Souza** | DEF | Out of Contention | 0.00 | `not_role_eligible` | Development defender outside first-team squad. |
| **Fernandes** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Gallagher** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Moore** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Tel** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Tonali** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Bentancur** | MID | Rotation | 0.40 | `not_role_eligible` | Started secondary friendly vs Hoffenheim; midfield depth behind Tonali, Fernandes, and Gallagher. |
| **Bergvall** | MID | Rotation | 0.40 | `not_role_eligible` | Featured in main matchday squad vs Hoffenheim; creative midfield rotation. |
| **Gray** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Kudus** | MID | Rotation | 0.40 | `not_role_eligible` | Attacking midfield star carrying thigh knock from preseason. |
| **Maddison** | MID | Rotation | 0.40 | `not_role_eligible` | Returned in secondary friendly vs Hoffenheim after long injury layoff; minutes being built up. |
| **P.M.Sarr** | MID | Rotation | 0.40 | `not_role_eligible` | Featured in secondary friendly vs Hoffenheim; central midfield depth. |
| **Kulusevski** | MID | Out of Contention | 0.00 | `exclude_gw1-5` | Recovering from knee surgery; unavailable for early gameweeks. |
| **Odobert** | MID | Out of Contention | 0.00 | `exclude_gw1-5` | Sidelined with knee injury; out for start of season. |
| **Olusesi** | MID | Out of Contention | 0.00 | `not_role_eligible` | Academy midfielder outside first-team squad. |
| **Xavi** | MID | Out of Contention | 0.00 | `exclude_gw1-5` | Long-term knee injury; excluded from early-season fixtures. |
| **Richarlison** | FWD | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Solanke** | FWD | Rotation | 0.40 | `not_role_eligible` | Striker rotation challenger competing with Richarlison. |
| **Scarlett** | FWD | Cameo | 0.10 | `not_role_eligible` | Third choice striker behind Richarlison and Solanke. |

#### 20. Sunderland (`SUN`) — 25 players
- **Summary**: Nailed: 7 · Regular: 6 · Rotation: 2 · Cameo: 8 · Out of Contention: 2 | Draft Eligible: 13

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Roefs** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Ellborg** | GKP | Cameo | 0.10 | `not_role_eligible` | Third choice goalkeeper. |
| **Patterson** | GKP | Cameo | 0.10 | `exclude_gw1` | Backup goalkeeper behind Roefs. |
| **Ballard** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Reinildo** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Alderete** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (Meerkat 🟢 / predicted). |
| **Hume** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Meunier** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Mukiele** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (Meerkat 🟢 / predicted). |
| **O'Nien** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Masuaku** | DEF | Cameo | 0.10 | `exclude_gw1` | Veteran fullback depth behind Reinildo and Hume. |
| **Seelt** | DEF | Cameo | 0.10 | `not_role_eligible` | Central defensive cover behind Ballard, Alderete, and O'Nien. |
| **Hjelde** | DEF | Out of Contention | 0.00 | `exclude_gw1` | Defensive depth outside matchday squad. |
| **E.Le Fée** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Sadiki** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Xhaka** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Angulo** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Adingra** | MID | Rotation | 0.40 | `not_role_eligible` | Wide attacker rotating with Angulo, Talbi, and Mundle. |
| **Talbi** | MID | Rotation | 0.40 | `not_role_eligible` | Attacking winger option in Le Bris rotation. |
| **Diarra** | MID | Cameo | 0.10 | `not_role_eligible` | Midfield rotation depth behind Xhaka, Sadiki, and Le Fée. |
| **Mundle** | MID | Cameo | 0.10 | `not_role_eligible` | Winger depth off the bench. |
| **Rigg** | MID | Cameo | 0.10 | `not_role_eligible` | Highly rated young midfielder developing behind senior starters. |
| **Jocelin.T** | MID | Out of Contention | 0.00 | `not_role_eligible` | Academy midfielder outside senior rotation. |
| **Brobbey** | FWD | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Isidor** | FWD | Cameo | 0.10 | `not_role_eligible` | Striker backup behind Brobbey. |


## Decision

**Verdict**: 20-club Expected Role scaffold refreshed from dual live scrape (FFS + Meerkat), **575** contention rows, **234** Draft-eligible (Nailed 77 + Regular 157). Identity match uses FPL first/second name so B.Fernandes ≠ Bruno G. and Virgil matches Van Dijk. Single-token source names match `web_name` or surname last token only.

---

## Verification & Delivery

- Stage 1 script: `docs/research/gw1-6-preseason-pipeline/01-expected-role-gw1-5/refresh_expected_role.py`.
- Output CSV: `data/research/gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.csv`.

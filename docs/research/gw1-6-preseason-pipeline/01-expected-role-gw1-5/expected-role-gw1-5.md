# FPL 2026/27 Expected Role (GW1–5) — 20-Club Audit & Mins Priors

**Updated**: 2026-08-10T20:45:00+07:00  
**Data stamp**: FFS Team News + FPL Meerkat scraped 2026-08-10; official overlays 2026-08-10; `players.parquet` 2026-07-29  
**Season**: 2026/27  
**Status**: Active Research Model  
**Purpose**: Assign fit-conditional Expected Role, dated Draft Availability, and Participation State priors across all 20 clubs for GW1–5 seeding  
**Scope**: XI Contention Set (scaffold + FFS XI injects); Draft Shortlist = Nailed + Regular; Availability Overlay separately applies `eligible`, `watch`, `exclude_gw1`, `exclude_gw1-5`  
**Related**: [Preseason Pipeline Master README](../README.md) · [Expected Stats (Stage 2)](../02-expected-stats-gw1-5/expected-stats-gw1-5.md) · [GW1–6 Chip Matrix (Stage 3)](../03-gw1-6-chip-wc4-squads/gw1-6-chip-wc4-squads.md)  
**Artifacts**:
- [Expected Role CSV](../../../data/research/gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.csv)

---

## Sources

- **Primary**: [Fantasy Football Scout Team News](https://www.fantasyfootballscout.co.uk/team-news) — accessed 2026-08-10; predicted XIs (11 per club).
- **Primary**: [FPL GW1 Predicted Line-ups — FPL Meerkat / fpl.page](https://fpl.page/article/fpl-gw1-predicted-lineups-2627) — accessed 2026-08-10; 🟢 nailed markers.
- **Primary**: [Confirmed Summer Transfers — Fantasy Football Scout](https://www.fantasyfootballscout.co.uk/fpl-2026-27-transfer-news-confirmed-summer-signings) via [fpl-summer-transfers.md](../../fpl-preseason-guide/fpl-summer-transfers.md).
- **Primary**: Official club fitness overlays (Saliba, Rodri, Mac Allister, Saka).
- **Repository data**: `data/processed/players.parquet` + `clubs.parquet`.

---

## Agent Prompt

```text
Full redo docs/research/gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.md:

1. Run refresh_expected_role.py (HTTP scrape FFS + Meerkat; inject missing FFS XI; conflict rules; API + official availability).
2. Conflict rules:
   - Nailed Starter: in FFS XI AND Meerkat 🟢 (0.90/0.05/0.05/85/20)
   - Regular Starter: in exactly one starter signal (0.75/0.10/0.15/80/20)
   - Rotation: previously draft-role but absent from both current signals
3. Availability separate from fit-role. Do not demote fit-role for temporary absence.
4. Verify gates.
```

---

## Method

1. **HTTP scrape**: FFS predicted XI names per club; Meerkat first 🟢 line per club (HTML-unescaped).
2. **Inject**: FFS XI players missing from scaffold matched via `players.parquet` and appended.
3. **Expected Role assignment**: unanimous dual-source → Nailed; single-source → Regular; lost both signals → Rotation.
4. **Availability Overlay**: API chance/status hints, then official overlays. Scoring overlays applied downstream in `availability_priors.py` (Watch haircut; Exclude GW1–5 = GW1–5 only).
5. **Draft Shortlist**: Nailed + Regular with non-`not_role_eligible` availability for human draft / solver ingestion.

---

## Findings

### 1. High-Level Summary & Role Distribution

- Contention set: **351** rows after 11 FFS XI injects (was 340). Roles: Nailed 78 · Regular 149 · Rotation 84 · Cameo 40.
- Availability: eligible 214 · not_role_eligible 114 · exclude_gw1 13 · watch 8 · exclude_gw1-5 2.
- **Rushworth (COV)**: injected from FFS XI → Regular Starter, eligible.
- **Kinsky (TOT)**: Regular Starter (FFS XI; Meerkat GK not unanimous).
- **Saliba (ARS)**: `exclude_gw1-5`. **Mac Allister (LIV)** / **Saka (ARS)**: `watch`.
- **Bruno Guimarães (ARS)** / transfer club moves applied before role rebuild.

### 2. 20-Club Player Role & Draft Availability Breakdown

Complete roster of all 351 players across the 20 Premier League clubs in the XI Contention Set, showing assigned fit-role, baseline starter probability ($p_{\text{start}}$), Draft Availability overlay, and source signals.

#### 1. Arsenal (`ARS`) — 20 players
- **Summary**: Nailed: 2 · Regular: 11 · Rotation: 7 · Cameo: 0 | Draft Eligible: 10

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Raya** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Gabriel** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Calafiori** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **J.Timber** | DEF | Regular Starter | 0.75 | `exclude_gw1` | Groin injury - Expected back 21 Aug |
| **Mosquera** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **White** | DEF | Regular Starter | 0.75 | `watch` | Local API says 0%/expected back 21 Aug, while newer training reports describe White back in group work; tre... |
| **Hincapie** | DEF | Rotation | 0.40 | `not_role_eligible` | Confirmed summer signing; Meerkat notes left-CB usage but Scout starts Calafiori, so minutes shared. |
| **Saliba** | DEF | Rotation | 0.40 | `exclude_gw1-5` | Back rehabilitation; out early-season band. |
| **Dowman** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Lewis-Skelly** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Rice** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (Meerkat 🟢 / predicted). |
| **Saka** | MID | Regular Starter | 0.75 | `watch` | Post-tournament fitness management. |
| **Tzolis** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Eze** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Madueke** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Martinelli** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Zubimendi** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Ødegaard** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Gyökeres** | FWD | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Havertz** | FWD | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |

#### 2. Aston Villa (`AVL`) — 17 players
- **Summary**: Nailed: 5 · Regular: 5 · Rotation: 4 · Cameo: 3 | Draft Eligible: 9

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Martinez** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Cash** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Konsa** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Maatsen** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Lindelöf** | DEF | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Pau** | DEF | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Digne** | DEF | Cameo | 0.10 | `not_role_eligible` | Scout starts Maatsen at LB; Digne is the veteran backup/impact option. |
| **Kamara** | MID | Nailed Starter | 0.90 | `watch` | Knee injury - 75% chance of playing |
| **Barkley** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Buendía** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Gomes** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **McGinn** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Garnacho** | MID | Rotation | 0.40 | `not_role_eligible` | Confirmed Chelsea loan; Meerkat explicitly frames as bench/CL rotation, not a locked XI starter. |
| **Manzambi** | MID | Rotation | 0.40 | `not_role_eligible` | £50m signing; Meerkat says likely Rogers replace but Scout XI omits him for Barkley/Buendía/McGinn — conser... |
| **Bailey** | MID | Cameo | 0.10 | `not_role_eligible` | Not in Scout XI or Meerkat greens; wide rotation behind Buendía/Garnacho/McGinn. |
| **Guessand** | MID | Cameo | 0.10 | `not_role_eligible` | Attacking depth only; neither Scout XI nor Meerkat green for early GW starts. |
| **Watkins** | FWD | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |

#### 3. Bournemouth (`BOU`) — 16 players
- **Summary**: Nailed: 7 · Regular: 4 · Rotation: 3 · Cameo: 2 | Draft Eligible: 10

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Petrović** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Hill** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Truffert** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Smith** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Diakité** | DEF | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Milosavljević** | DEF | Cameo | 0.10 | `not_role_eligible` | CB depth after Senesi exit; Scout prefers Hill/Diakité pairing for early XI. |
| **Adams** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Rayan** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Scott** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Tavernier** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Kluivert** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Kroupi.Jr** | MID | Regular Starter | 0.75 | `exclude_gw1-5` | Single-source or non-unanimous starter signal (Meerkat 🟢 / predicted). |
| **Christie** | MID | Rotation | 0.25 | `exclude_gw1` | API status=s; chance=0.0; Suspended until 29 Aug |
| **Cook** | MID | Cameo | 0.10 | `not_role_eligible` | Midfield depth behind Adams/Scott; not in Scout predicted XI. |
| **Evanilson** | FWD | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Rodríguez** | FWD | Rotation | 0.40 | `not_role_eligible` | Confirmed £25.7m striker; Meerkat frames as competing with Evanilson for the No.9 shirt. |

#### 4. Brentford (`BRE`) — 18 players
- **Summary**: Nailed: 5 · Regular: 5 · Rotation: 4 · Cameo: 4 | Draft Eligible: 10

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Kelleher** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Collins** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Kayode** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Ajer** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Van den Berg** | DEF | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Schuster** | DEF | Cameo | 0.10 | `not_role_eligible` | Confirmed May signing; Meerkat lists Schuster as defensive backup, not XI contention starter. |
| **Schade** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Janelt** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Jensen** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Lewis-Potter** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **O.Dango** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (Meerkat 🟢 / predicted). |
| **Carvalho** | MID | Rotation | 0.40 | `exclude_gw1` | API status=i; chance=0.0; Knee injury - Unknown return date |
| **Milambo** | MID | Rotation | 0.40 | `not_role_eligible` | Knee injury - 75% chance of playing |
| **Yarmoliuk** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Anthony** | MID | Cameo | 0.10 | `not_role_eligible` | Confirmed £15m signing; Meerkat explicitly lists Anthony as backup to Schade/Dango band. |
| **Damsgaard** | MID | Cameo | 0.10 | `not_role_eligible` | Creative depth outside Scout XI; competes with Jensen for advanced mid minutes. |
| **Thiago** | FWD | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Wilson** | FWD | Cameo | 0.10 | `not_role_eligible` | Free signing Callum Wilson; backup to nailed Thiago rather than early draft starter. |

#### 5. Brighton (`BHA`) — 16 players
- **Summary**: Nailed: 4 · Regular: 7 · Rotation: 2 · Cameo: 3 | Draft Eligible: 11

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Verbruggen** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Dunk** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Vuskovic** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **De Cuyper** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **F.Kadıoğlu** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (Meerkat 🟢 / predicted). |
| **Wieffer** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (Meerkat 🟢 / predicted). |
| **Struijk** | DEF | Cameo | 0.10 | `not_role_eligible` | Confirmed £20m signing from Leeds; Meerkat explicitly benches Struijk behind Dunk/Vuskovic. |
| **Groß** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Baleba** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Gomez** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Hinshelwood** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Minteh** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Mitoma** | MID | Rotation | 0.40 | `exclude_gw1` | API status=i; chance=0.0; Hamstring injury - Unknown return date |
| **Ayari** | MID | Cameo | 0.10 | `not_role_eligible` | Midfield depth/cameo only; Scout prefers Baleba/Groß/Hinshelwood band for early XI. |
| **Tzimas** | FWD | Rotation | 0.40 | `not_role_eligible` | Knee injury - 75% chance of playing |
| **Georginio** | FWD | Cameo | 0.10 | `not_role_eligible` | Attack rotation depth for the open No.9; neither Scout XI nor Meerkat green. |

#### 6. Chelsea (`CHE`) — 19 players
- **Summary**: Nailed: 6 · Regular: 8 · Rotation: 4 · Cameo: 1 | Draft Eligible: 14

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Sánchez** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Colwill** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Lacroix** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Hato** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **James** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (Meerkat 🟢 / predicted). |
| **Palestra** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Gusto** | DEF | Rotation | 0.40 | `not_role_eligible` | Scout XI RB, but Meerkat has James/Palestra RWB paths. Scout Regular vs formation Rotation → Rotation. |
| **Tosin** | DEF | Rotation | 0.40 | `not_role_eligible` | Scout XI CB; Lacroix arrival and Colwill/James CB options make starts shared. Demote to Rotation. |
| **Caicedo** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Palmer** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Enzo** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (Meerkat 🟢 / predicted). |
| **Gittens** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Lavia** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Neto** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Rogers** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (Meerkat 🟢 / predicted). |
| **Quenda** | MID | Rotation | 0.40 | `not_role_eligible` | Unspecified injury - 75% chance of playing |
| **Estêvão** | MID | Cameo | 0.10 | `not_role_eligible` | Attacking depth behind Palmer/Rogers/Neto; realistic late Sub-in path only GW1–5. |
| **João Pedro** | FWD | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Welbeck** | FWD | Rotation | 0.40 | `not_role_eligible` | Confirmed £5m transfer to Chelsea as forward depth. |

#### 7. Coventry City (`COV`) — 19 players
- **Summary**: Nailed: 0 · Regular: 11 · Rotation: 7 · Cameo: 1 | Draft Eligible: 11

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Rushworth** | GKP | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Wilson** | GKP | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Amenda** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Thomas** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **van Ewijk** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Dasilva** | DEF | Rotation | 0.40 | `not_role_eligible` | Full-back depth competing with van Ewijk/Bidwell for starts. |
| **Kitching** | DEF | Rotation | 0.40 | `not_role_eligible` | CB/LB competition with Amenda/Thomas/Brau; realistic starts but not locked. |
| **Grimes** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Mason-Clark** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Onyeka** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Sakamoto** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Torp** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Eccles** | MID | Rotation | 0.40 | `not_role_eligible` | Central mid depth behind Grimes/Torp/Onyeka. |
| **Rudoni** | MID | Rotation | 0.40 | `not_role_eligible` | Shoulder injury - 75% chance of playing |
| **Tchaouna** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Thomas-Asante** | FWD | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Wright** | FWD | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Simms** | FWD | Rotation | 0.40 | `not_role_eligible` | Forward rotation option behind Wright. |
| **Markelo** | FWD | Cameo | 0.10 | `not_role_eligible` | Attacking depth; late Sub-in path only. |

#### 8. Crystal Palace (`CRY`) — 18 players
- **Summary**: Nailed: 5 · Regular: 6 · Rotation: 4 · Cameo: 3 | Draft Eligible: 10

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Henderson** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Mitchell** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Muñoz** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Richards** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Canvot** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Chadi Riad** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Mingueza** | DEF | Rotation | 0.40 | `not_role_eligible` | Free Celta signing; CB/WB depth as Lacroix replacement candidate vs Canvot. |
| **Sarr** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Johnson** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Kamada** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Wharton** | MID | Regular Starter | 0.75 | `watch` | Ankle injury - 75% chance of playing |
| **Lerma** | MID | Rotation | 0.40 | `not_role_eligible` | Midfield depth behind Wharton/Kamada; shares starts. |
| **Yeremy** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Devenny** | MID | Cameo | 0.10 | `not_role_eligible` | Fringe mid/attacker minutes only. |
| **Esse** | MID | Cameo | 0.10 | `not_role_eligible` | Bench attacker with late Sub-in path. |
| **Strand Larsen** | FWD | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Mateta** | FWD | Rotation | 0.40 | `not_role_eligible` | Club talisman but Scout XI prefers Strand Larsen. Regular history vs Scout Rotation → Rotation. |
| **Nketiah** | FWD | Cameo | 0.10 | `not_role_eligible` | CF depth behind Strand Larsen/Mateta. |

#### 9. Everton (`EVE`) — 17 players
- **Summary**: Nailed: 4 · Regular: 8 · Rotation: 4 · Cameo: 1 | Draft Eligible: 11

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Pickford** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Tarkowski** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Branthwaite** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Mykolenko** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **O'Brien** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Keane** | DEF | Rotation | 0.40 | `not_role_eligible` | Scout XI CB, but Meerkat says only Tarkowski is certain and Keane/Branthwaite/Garner are flexible. → Rotation. |
| **Dewsbury-Hall** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Ndiaye** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Garner** | MID | Regular Starter | 0.75 | `exclude_gw1` | Groin injury - Expected back 22 Aug |
| **Hackney** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Iroegbunam** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Röhl** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **George** | MID | Rotation | 0.40 | `not_role_eligible` | £18m from Chelsea; Meerkat says kept and gains minutes if Ndiaye exits. Contingent Rotation path. |
| **McNeil** | MID | Rotation | 0.40 | `not_role_eligible` | Wide competition with Röhl/Ndiaye/George. |
| **Dibling** | MID | Cameo | 0.10 | `not_role_eligible` | Attacking bench option GW1–5. |
| **Barry** | FWD | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Beto** | FWD | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |

#### 10. Fulham (`FUL`) — 17 players
- **Summary**: Nailed: 4 · Regular: 7 · Rotation: 2 · Cameo: 4 | Draft Eligible: 11

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Leno** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Bassey** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Robinson** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **J.Cuenca** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Tete** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Castagne** | DEF | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Sessegnon** | DEF | Cameo | 0.10 | `not_role_eligible` | LB/wing depth behind Robinson; late Sub-in path. |
| **Iwobi** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Bobb** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Kevin** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Lukić** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Smith Rowe** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Berge** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Cairney** | MID | Cameo | 0.10 | `not_role_eligible` | Veteran mid depth behind Lukić/Berge. |
| **King** | MID | Cameo | 0.10 | `not_role_eligible` | Attacking bench option amid heavy front-line rotation. |
| **Muniz** | FWD | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Kusi-Asare** | FWD | Cameo | 0.10 | `not_role_eligible` | £5.2m Bayern signing; Meerkat flags £4.5m Kusi-Asare as backup ST who could get minutes. |

#### 11. Hull City (`HUL`) — 15 players
- **Summary**: Nailed: 0 · Regular: 11 · Rotation: 4 · Cameo: 0 | Draft Eligible: 11

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Butland** | GKP | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Ajayi** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Coyle** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Egan** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Giles** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Hughes** | DEF | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Targett** | DEF | Rotation | 0.40 | `not_role_eligible` | Free transfer Targett→Hull; Meerkat asks if starter. No Scout XI → Rotation not Regular. |
| **Belloumi** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Crooks** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Millar** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Slater** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Ömür** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Kamara** | MID | Rotation | 0.40 | `not_role_eligible` | CM depth challenger; Meerkat provides no green nailed list for Hull. |
| **Morita** | MID | Rotation | 0.40 | `not_role_eligible` | New/available CM option at £5.0m; unsettled midfield → Rotation. |
| **McBurnie** | FWD | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |

#### 12. Ipswich Town (`IPS`) — 18 players
- **Summary**: Nailed: 0 · Regular: 10 · Rotation: 8 · Cameo: 0 | Draft Eligible: 10

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Scherpen** | GKP | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Van Oevelen** | GKP | Rotation | 0.40 | `not_role_eligible` | New GK (van Oevelen→Ipswich) in three-way fight with Scherpen/Walton; budget-GK note unsettled. No Scout XI. |
| **Davis** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Furlong** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Greaves** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **O'Shea** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Diop** | DEF | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Kipré** | DEF | Rotation | 0.40 | `not_role_eligible` | CB depth behind Diop/O'Shea; Rotation not Regular. |
| **Fatawu** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Maeda** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Mehmeti** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Núñez** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Clarke** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Matusiwa** | MID | Rotation | 0.40 | `exclude_gw1` | API status=i; chance=0.0; Muscular injury - Unknown return date |
| **Philogene** | MID | Rotation | 0.40 | `not_role_eligible` | Wide rotation vs Fatawu/Maeda/Clarke; Meerkat did not nail him. |
| **Szmodics** | MID | Rotation | 0.40 | `not_role_eligible` | Attacking MID/second-striker rotation behind new first-choice attackers. |
| **Emersonn** | FWD | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Hirst** | FWD | Rotation | 0.40 | `not_role_eligible` | Incumbent ST competing with Emersonn; shares early minutes. |

#### 13. Leeds United (`LEE`) — 16 players
- **Summary**: Nailed: 6 · Regular: 7 · Rotation: 2 · Cameo: 1 | Draft Eligible: 13

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Perri** | GKP | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Trafford** | GKP | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (Meerkat 🟢 / predicted). |
| **Muharemović** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Rodon** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Bijol** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Bogle** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Justin** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Gudmundsson** | DEF | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Ampadu** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Stach** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Wilson** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Okafor** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (Meerkat 🟢 / predicted). |
| **Tanaka** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Aaronson** | MID | Rotation | 0.40 | `not_role_eligible` | Scout XI AM; Meerkat nails Wilson/Okafor/DCL front 3 instead → Rotation. |
| **Gnonto** | MID | Cameo | 0.10 | `not_role_eligible` | Wide challenger behind Wilson/Okafor; not in Scout XI or Meerkat green. |
| **Calvert-Lewin** | FWD | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |

#### 14. Liverpool (`LIV`) — 17 players
- **Summary**: Nailed: 6 · Regular: 4 · Rotation: 4 · Cameo: 3 | Draft Eligible: 9

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **A.Becker** | GKP | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Jacquet** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Kerkez** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Frimpong** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Gomez** | DEF | Rotation | 0.40 | `exclude_gw1` | API status=i; chance=0.0; Muscular injury - Unknown return date |
| **Virgil** | DEF | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Bradley** | DEF | Cameo | 0.10 | `exclude_gw1` | API status=i; chance=0.0; Knee injury - Unknown return date |
| **Gravenberch** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Szoboszlai** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Wirtz** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Gakpo** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Mac Allister** | MID | Regular Starter | 0.75 | `watch` | Post-tournament fitness management. |
| **Ngumoha** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **C.Jones** | MID | Rotation | 0.40 | `not_role_eligible` | Meerkat: Jones could come into side if stays; not Scout XI → Rotation. |
| **Munoz** | MID | Cameo | 0.10 | `not_role_eligible` | Victor Munoz→LIV; Meerkat backup option for now. FPL web_name Munoz. |
| **Isak** | FWD | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Ekitiké** | FWD | Cameo | 0.10 | `exclude_gw1` | API status=i; chance=0.0; Achilles injury - Unknown return date |

#### 15. Man City (`MCI`) — 18 players
- **Summary**: Nailed: 4 · Regular: 10 · Rotation: 3 · Cameo: 1 | Draft Eligible: 13

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Donnarumma** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Aït-Nouri** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Guéhi** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (Meerkat 🟢 / predicted). |
| **Gvardiol** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Khusanov** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Matheus N.** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **O'Reilly** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (Meerkat 🟢 / predicted). |
| **Rúben** | DEF | Rotation | 0.40 | `not_role_eligible` | Scout XI CB (Dias); Meerkat CB partner unclear / Guehi nailed lean → Rotation. FPL web_name Rúben. |
| **Anderson** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Semenyo** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Doku** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Foden** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Kovačić** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Rodrigo** | MID | Regular Starter | 0.75 | `exclude_gw1` | Back surgery recovery; miss GW1. |
| **Cherki** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Reijnders** | MID | Rotation | 0.40 | `not_role_eligible` | Scout XI CM; Meerkat nails Anderson/Rodri midfield instead → Rotation. |
| **Haaland** | FWD | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Marmoush** | FWD | Cameo | 0.10 | `not_role_eligible` | ST/wide backup behind Haaland/Semenyo; not Scout or Meerkat XI. |

#### 16. Man Utd (`MUN`) — 18 players
- **Summary**: Nailed: 4 · Regular: 6 · Rotation: 5 · Cameo: 3 | Draft Eligible: 10

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Lammens** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Dalot** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Maguire** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Shaw** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Yoro** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Martinez** | DEF | Rotation | 0.40 | `not_role_eligible` | Thigh injury - 75% chance of playing |
| **De Ligt** | DEF | Cameo | 0.10 | `exclude_gw1` | API status=i; chance=0.0; Back injury - Unknown return date |
| **Mazraoui** | DEF | Cameo | 0.10 | `not_role_eligible` | Fullback cover for Dalot/Shaw; neither Scout XI nor Meerkat green. |
| **Amad** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Andrey Santos** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Cunha** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Mbeumo** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Mount** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **B.Fernandes** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Mainoo** | MID | Rotation | 0.40 | `not_role_eligible` | Scout XI starter demoted: Meerkat explicit rotation — only 2 of Santos/Mainoo/Tielemans start. |
| **Tielemans** | MID | Rotation | 0.40 | `not_role_eligible` | Hamstring injury - 75% chance of playing |
| **Ugarte** | MID | Cameo | 0.10 | `exclude_gw1` | API status=i; chance=0.0; Knee injury - Unknown return date |
| **Šeško** | FWD | Rotation | 0.40 | `not_role_eligible` | Shin injury - 75% chance of playing |

#### 17. Newcastle (`NEW`) — 19 players
- **Summary**: Nailed: 3 · Regular: 9 · Rotation: 5 · Cameo: 2 | Draft Eligible: 10

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Pope** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Thiaw** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Botman** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Hall** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Jacob** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Livramento** | DEF | Regular Starter | 0.75 | `watch` | Calf injury - 75% chance of playing |
| **Burn** | DEF | Rotation | 0.40 | `not_role_eligible` | Meerkat explicit Burn/Botman CB rotation; not Scout XI. |
| **Bruno G.** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Barnes** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Elanga** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Joelinton** | MID | Regular Starter | 0.75 | `eligible` | Thigh injury - 75% chance of playing |
| **L.Miley** | MID | Regular Starter | 0.75 | `exclude_gw1` | API status=i; chance=0.0; Leg injury - Expected back 30 Aug |
| **Bamba** | MID | Rotation | 0.40 | `not_role_eligible` | Meerkat lists Bamba with Touré as Gordon replacement options; shared wide minutes. |
| **J.Ramsey** | MID | Rotation | 0.40 | `not_role_eligible` | Scout XI attacker; not Meerkat green and attack unsettled post-Gordon — Rotation. |
| **Touré** | MID | Rotation | 0.40 | `not_role_eligible` | £43m Hoffenheim signing as Gordon-type replacement; Meerkat flags with Bamba as wing options, not nailed. |
| **Willock** | MID | Rotation | 0.40 | `not_role_eligible` | Scout XI AM; Meerkat few-nailed / midfield flux — conservative demotion to Rotation. |
| **Osula** | FWD | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Wissa** | FWD | Cameo | 0.10 | `not_role_eligible` | ST minefield challenger; not Scout XI. |
| **Woltemade** | FWD | Cameo | 0.10 | `not_role_eligible` | ST minefield challenger; not Scout XI. |

#### 18. Nottingham Forest (`NFO`) — 17 players
- **Summary**: Nailed: 1 · Regular: 10 · Rotation: 4 · Cameo: 2 | Draft Eligible: 10

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Sels** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Aina** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Jair Cunha** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Milenković** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Murillo** | DEF | Regular Starter | 0.75 | `watch` | Muscle injury - 75% chance of playing |
| **N.Williams** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Morato** | DEF | Cameo | 0.10 | `not_role_eligible` | CB cover behind Murillo/Milenkovic/Jair; not Scout XI. |
| **Dominguez** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Gibbs-White** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Sangaré** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Hudson-Odoi** | MID | Rotation | 0.40 | `not_role_eligible` | Thigh injury - 75% chance of playing |
| **Hutchinson** | MID | Rotation | 0.40 | `not_role_eligible` | Scout XI winger demoted: Meerkat wingers rotate (Hudson-Odoi/Ndoye/Bakwa/Hutchinson). |
| **Ndoye** | MID | Rotation | 0.40 | `not_role_eligible` | Wing rotation challenger; not Scout XI. |
| **Schlager** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Bakwa** | MID | Cameo | 0.10 | `not_role_eligible` | Wide depth in Meerkat wing-rotation set; fringe vs Hutchinson/Hudson-Odoi/Ndoye. |
| **Igor Jesus** | FWD | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Wood** | FWD | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |

#### 19. Sunderland (`SUN`) — 17 players
- **Summary**: Nailed: 9 · Regular: 2 · Rotation: 2 · Cameo: 4 | Draft Eligible: 11

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Roefs** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Alderete** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Ballard** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Mukiele** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Reinildo** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Hume** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Meunier** | DEF | Cameo | 0.10 | `not_role_eligible` | Free from Lille; Meerkat backup to Mukiele at RB. |
| **E.Le Fée** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Sadiki** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Xhaka** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Angulo** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Adingra** | MID | Rotation | 0.40 | `not_role_eligible` | Wide rotation challenger outside Scout XI; Meerkat wingers not nailed. |
| **Talbi** | MID | Rotation | 0.40 | `not_role_eligible` | Wide/attack rotation option; not Scout XI. |
| **Diarra** | MID | Cameo | 0.10 | `not_role_eligible` | Midfield depth behind Xhaka/Sadiki/Le Fee. |
| **Mundle** | MID | Cameo | 0.10 | `not_role_eligible` | Wide depth in non-nailed wing pool. |
| **Brobbey** | FWD | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Isidor** | FWD | Cameo | 0.10 | `not_role_eligible` | ST depth behind Brobbey; not Scout XI. |

#### 20. Tottenham Hotspur (`TOT`) — 19 players
- **Summary**: Nailed: 3 · Regular: 8 · Rotation: 6 · Cameo: 2 | Draft Eligible: 10

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Kinsky** | GKP | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Dubravka** | GKP | Rotation | 0.40 | `not_role_eligible` | Confirmed summer free transfer from Burnley; started pre-season friendly (Sydney XI) creating active starte... |
| **Pedro Porro** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Van Hecke** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Van de Ven** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Robertson** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Danso** | DEF | Rotation | 0.40 | `not_role_eligible` | Scout XI CB demoted: Meerkat nails van Hecke and notes Senesi CB competition. |
| **Senesi** | DEF | Rotation | 0.40 | `not_role_eligible` | Free from Bournemouth; Meerkat Senesi competes for CB minutes vs van Hecke/Danso/Romero. |
| **Udogie** | DEF | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Romero** | DEF | Cameo | 0.10 | `not_role_eligible` | Neither Scout XI nor Meerkat green; CB depth behind VDV/van Hecke fight. |
| **Fernandes** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Gallagher** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Kudus** | MID | Regular Starter | 0.75 | `watch` | Thigh injury - 75% chance of playing |
| **Tel** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Tonali** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Bentancur** | MID | Rotation | 0.40 | `not_role_eligible` | Scout XI CM demoted by Meerkat Tonali/Fernandes midfield priority. |
| **Maddison** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Solanke** | FWD | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Richarlison** | FWD | Cameo | 0.10 | `not_role_eligible` | ST depth behind Solanke; not Scout XI. |

---

## Decision

**Verdict**: Automated dual-source rebuild is the Stage 1 Method of record. Unanimous Nailed rule is stricter than prior hand labels (fewer Nailed, more Regular).

**Recommended Action**: Re-scrape before material pre-GW1 news; keep official availability overlays dated.

---

## Risks and unknowns

- Meerkat article dated late July; FFS Team News moves faster — dual-source Nailed can lag.
- Name-matching failures leave some FFS names unmatched (no inject).
- Scaffold still seeds Rotation/Cameo membership; inject adds starters only.
- API `chance_of_playing` soft-hints may over-tag `exclude_gw1` / `watch`.

---

## Verification & Delivery

- CSV: `data/research/gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.csv` (351 rows).

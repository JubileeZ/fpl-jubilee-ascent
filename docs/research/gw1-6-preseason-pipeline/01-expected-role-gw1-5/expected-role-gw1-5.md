# FPL 2026/27 Expected Role (GW1–5) — 20-Club Audit & Mins Priors

**Updated**: 2026-08-12T00:56:00+07:00  
**Data stamp**: FFS Team News + FPL Meerkat scraped 2026-08-12; official overlays 2026-08-12; `players.parquet` 2026-07-29  
**Season**: 2026/27  
**Status**: Active Research Model  
**Purpose**: Assign fit-conditional Expected Role, dated Draft Availability, and Participation State priors across all 20 clubs for GW1–5 seeding  
**Scope**: XI Contention Set (scaffold + FFS XI injects); Draft Shortlist = Nailed + Regular; Availability Overlay separately applies `eligible`, `watch`, `exclude_gw1`, `exclude_gw1-5`  
**Related**: [Preseason Pipeline Master README](../README.md) · [Expected Stats (Stage 2)](../02-expected-stats-gw1-5/expected-stats-gw1-5.md) · [GW1–6 Chip Matrix (Stage 3)](../03-gw1-6-chip-wc4-squads/gw1-6-chip-wc4-squads.md)  
**Artifacts**:
- [Expected Role CSV](../../../data/research/gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.csv)

---

## Sources

- **Primary**: [Fantasy Football Scout Team News](https://www.fantasyfootballscout.co.uk/team-news) — accessed 2026-08-12; predicted XIs (11 per club).
- **Primary**: [FPL GW1 Predicted Line-ups — FPL Meerkat / fpl.page](https://fpl.page/article/fpl-gw1-predicted-lineups-2627) — accessed 2026-08-12; 🟢 nailed markers.
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
2. Synchronize 20-club markdown tables in expected-role-gw1-5.md with the generated CSV.
3. Verification: uv run pytest, uv run ruff check .
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

- Contention set: **357** rows (was 351). Roles: Nailed 77 · Regular 147 · Rotation 99 · Cameo 34.
- Draft Eligible: **224** players (Nailed 77 + Regular 147).
- Availability: eligible 213 · not_role_eligible 121 · exclude_gw1 14 · watch 7 · exclude_gw1-5 2.
- **Injected Starters**: Touré (NEW MID), Steur (NEW MID), Meunier (SUN DEF), Walle Egeli (IPS FWD), Moore (TOT MID), Rushworth (COV GKP).
- **Kinsky (TOT)**: Regular Starter (FFS XI; Meerkat GK not unanimous).
- **Saliba (ARS)**: `exclude_gw1-5`. **Mac Allister (LIV)** / **Saka (ARS)**: `watch`.
- **Bruno Guimarães (ARS)** / transfer club moves applied before role rebuild.

### 2. 20-Club Player Role & Draft Availability Breakdown

Complete roster of all 357 players across the 20 Premier League clubs in the XI Contention Set, showing assigned fit-role, baseline starter probability ($p_{\text{start}}$), Draft Availability overlay, and source signals.

#### 1. Arsenal (`ARS`) — 20 players
- **Summary**: Nailed: 2 · Regular: 11 · Rotation: 7 · Cameo: 0 | Draft Eligible: 13

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Raya** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Gabriel** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Saliba** | DEF | Rotation | 0.40 | `exclude_gw1-5` | Back rehabilitation; out early-season band. |
| **J.Timber** | DEF | Regular Starter | 0.75 | `exclude_gw1` | Groin injury - Expected back 21 Aug |
| **Rice** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (Meerkat 🟢 / predicted). |
| **Saka** | MID | Regular Starter | 0.75 | `watch` | Post-tournament fitness management. |
| **White** | DEF | Regular Starter | 0.75 | `watch` | Local API says 0%/expected back 21 Aug, while newer training reports describe White back in group work; treat as cont... |
| **Mosquera** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Calafiori** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Ødegaard** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Zubimendi** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Eze** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Madueke** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Gyökeres** | FWD | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Martinelli** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Hincapie** | DEF | Rotation | 0.40 | `not_role_eligible` | Confirmed summer signing; Meerkat notes left-CB usage but Scout starts Calafiori, so minutes shared. |
| **Tzolis** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Havertz** | FWD | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Lewis-Skelly** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Dowman** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |

#### 2. Aston Villa (`AVL`) — 17 players
- **Summary**: Nailed: 5 · Regular: 5 · Rotation: 4 · Cameo: 3 | Draft Eligible: 10

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Martinez** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Konsa** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Cash** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Kamara** | MID | Nailed Starter | 0.90 | `watch` | Knee injury - 75% chance of playing |
| **Watkins** | FWD | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Pau** | DEF | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Maatsen** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Lindelöf** | DEF | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **McGinn** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Barkley** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Buendía** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Manzambi** | MID | Rotation | 0.40 | `not_role_eligible` | £50m signing; Meerkat says likely Rogers replace but Scout XI omits him for Barkley/Buendía/McGinn — conservative Rot... |
| **Gomes** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Garnacho** | MID | Rotation | 0.40 | `not_role_eligible` | Confirmed Chelsea loan; Meerkat explicitly frames as bench/CL rotation, not a locked XI starter. |
| **Digne** | DEF | Cameo | 0.10 | `not_role_eligible` | Scout starts Maatsen at LB; Digne is the veteran backup/impact option. |
| **Bailey** | MID | Cameo | 0.10 | `not_role_eligible` | Not in Scout XI or Meerkat greens; wide rotation behind Buendía/Garnacho/McGinn. |
| **Guessand** | MID | Cameo | 0.10 | `not_role_eligible` | Attacking depth only; neither Scout XI nor Meerkat green for early GW starts. |

#### 3. Bournemouth (`BOU`) — 16 players
- **Summary**: Nailed: 7 · Regular: 4 · Rotation: 3 · Cameo: 2 | Draft Eligible: 11

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Petrović** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Hill** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Truffert** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Scott** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Adams** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Kroupi.Jr** | MID | Regular Starter | 0.75 | `exclude_gw1-5` | Single-source or non-unanimous starter signal (Meerkat 🟢 / predicted). |
| **Tavernier** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Rayan** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Smith** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Diakité** | DEF | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Evanilson** | FWD | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Rodríguez** | FWD | Rotation | 0.40 | `not_role_eligible` | Confirmed £25.7m striker; Meerkat frames as competing with Evanilson for the No.9 shirt. |
| **Christie** | MID | Rotation | 0.25 | `exclude_gw1` | API status=s; chance=0.0; Suspended until 29 Aug |
| **Kluivert** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Cook** | MID | Cameo | 0.10 | `not_role_eligible` | Midfield depth behind Adams/Scott; not in Scout predicted XI. |
| **Milosavljević** | DEF | Cameo | 0.10 | `not_role_eligible` | CB depth after Senesi exit; Scout prefers Hill/Diakité pairing for early XI. |

#### 4. Brentford (`BRE`) — 18 players
- **Summary**: Nailed: 5 · Regular: 5 · Rotation: 4 · Cameo: 4 | Draft Eligible: 10

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Kelleher** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Collins** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Kayode** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Schade** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **O.Dango** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (Meerkat 🟢 / predicted). |
| **Thiago** | FWD | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Van den Berg** | DEF | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Lewis-Potter** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Yarmoliuk** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Janelt** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Jensen** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Carvalho** | MID | Rotation | 0.40 | `exclude_gw1` | API status=i; chance=0.0; Knee injury - Unknown return date |
| **Milambo** | MID | Rotation | 0.40 | `not_role_eligible` | Scout ~25% doubt midfielder; API knee at 75% chance — Rotation when available behind Janelt/Yarmoliuk. |
| **Anthony** | MID | Cameo | 0.10 | `not_role_eligible` | Confirmed £15m signing; Meerkat explicitly lists Anthony as backup to Schade/Dango band. |
| **Schuster** | DEF | Cameo | 0.10 | `not_role_eligible` | Confirmed May signing; Meerkat lists Schuster as defensive backup, not XI contention starter. |
| **Damsgaard** | MID | Cameo | 0.10 | `not_role_eligible` | Creative depth outside Scout XI; competes with Jensen for advanced mid minutes. |
| **Wilson** | FWD | Cameo | 0.10 | `not_role_eligible` | Free signing Callum Wilson; backup to nailed Thiago rather than early draft starter. |
| **Ajer** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |

#### 5. Brighton (`BHA`) — 16 players
- **Summary**: Nailed: 5 · Regular: 5 · Rotation: 4 · Cameo: 2 | Draft Eligible: 10

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Verbruggen** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **F.Kadıoğlu** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (Meerkat 🟢 / predicted). |
| **Dunk** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Vuskovic** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Groß** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Wieffer** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Baleba** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **De Cuyper** | DEF | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Gomez** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Hinshelwood** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Minteh** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Mitoma** | MID | Rotation | 0.40 | `exclude_gw1` | API status=i; chance=0.0; Hamstring injury - Unknown return date |
| **Tzimas** | FWD | Rotation | 0.40 | `not_role_eligible` | Scout ~25% doubt for No.9 if Welbeck leaves; API knee at 75% chance — Rotation when available. |
| **Struijk** | DEF | Cameo | 0.10 | `not_role_eligible` | Confirmed £20m signing from Leeds; Meerkat explicitly benches Struijk behind Dunk/Vuskovic. |
| **Georginio** | FWD | Cameo | 0.10 | `not_role_eligible` | Attack rotation depth for the open No.9; neither Scout XI nor Meerkat green. |
| **Ayari** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |

#### 6. Chelsea (`CHE`) — 19 players
- **Summary**: Nailed: 6 · Regular: 8 · Rotation: 4 · Cameo: 1 | Draft Eligible: 14

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Welbeck** | FWD | Rotation | 0.40 | `not_role_eligible` | Confirmed £5m transfer to Chelsea as forward depth. |
| **Sánchez** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Colwill** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Lacroix** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **James** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (Meerkat 🟢 / predicted). |
| **Enzo** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (Meerkat 🟢 / predicted). |
| **Caicedo** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Rogers** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (Meerkat 🟢 / predicted). |
| **Palmer** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **João Pedro** | FWD | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Hato** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Gusto** | DEF | Rotation | 0.40 | `not_role_eligible` | Scout XI RB, but Meerkat has James/Palestra RWB paths. Scout Regular vs formation Rotation → Rotation. |
| **Tosin** | DEF | Rotation | 0.40 | `not_role_eligible` | Scout XI CB; Lacroix arrival and Colwill/James CB options make starts shared. Demote to Rotation. |
| **Palestra** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Lavia** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Neto** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Gittens** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Quenda** | MID | Rotation | 0.40 | `not_role_eligible` | £40m Sporting signing; Meerkat says likelier in back4. API doubt (75% chance) softens early-band lock. |
| **Estêvão** | MID | Cameo | 0.10 | `not_role_eligible` | Attacking depth behind Palmer/Rogers/Neto; realistic late Sub-in path only GW1–5. |

#### 7. Coventry City (`COV`) — 19 players
- **Summary**: Nailed: 0 · Regular: 11 · Rotation: 7 · Cameo: 1 | Draft Eligible: 11

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Wilson** | GKP | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Amenda** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Thomas** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **van Ewijk** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Kitching** | DEF | Rotation | 0.40 | `not_role_eligible` | CB/LB competition with Amenda/Thomas/Brau; realistic starts but not locked. |
| **Dasilva** | DEF | Rotation | 0.40 | `not_role_eligible` | Full-back depth competing with van Ewijk/Bidwell for starts. |
| **Tchaouna** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Torp** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Mason-Clark** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Onyeka** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Grimes** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Sakamoto** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Eccles** | MID | Rotation | 0.40 | `not_role_eligible` | Central mid depth behind Grimes/Torp/Onyeka. |
| **Rudoni** | MID | Rotation | 0.40 | `not_role_eligible` | Key mid when fit; API shoulder doubt (75%) keeps him Rotation not Regular for GW1–5. |
| **Wright** | FWD | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Thomas-Asante** | FWD | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Simms** | FWD | Rotation | 0.40 | `not_role_eligible` | Forward rotation option behind Wright. |
| **Markelo** | FWD | Cameo | 0.10 | `not_role_eligible` | Attacking depth; late Sub-in path only. |
| **Rushworth** | GKP | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |

#### 8. Crystal Palace (`CRY`) — 18 players
- **Summary**: Nailed: 5 · Regular: 6 · Rotation: 5 · Cameo: 2 | Draft Eligible: 11

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Henderson** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Richards** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Mitchell** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Muñoz** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Sarr** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Canvot** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Kamada** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Wharton** | MID | Regular Starter | 0.75 | `watch` | Ankle injury - 75% chance of playing |
| **Yeremy** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Strand Larsen** | FWD | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Mingueza** | DEF | Rotation | 0.40 | `not_role_eligible` | Free Celta signing; CB/WB depth as Lacroix replacement candidate vs Canvot. |
| **Mateta** | FWD | Rotation | 0.40 | `not_role_eligible` | Club talisman but Scout XI prefers Strand Larsen. Regular history vs Scout Rotation → Rotation. |
| **Johnson** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Lerma** | MID | Rotation | 0.40 | `not_role_eligible` | Midfield depth behind Wharton/Kamada; shares starts. |
| **Esse** | MID | Cameo | 0.10 | `not_role_eligible` | Bench attacker with late Sub-in path. |
| **Nketiah** | FWD | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Devenny** | MID | Cameo | 0.10 | `not_role_eligible` | Fringe mid/attacker minutes only. |
| **Chadi Riad** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |

#### 9. Everton (`EVE`) — 17 players
- **Summary**: Nailed: 4 · Regular: 7 · Rotation: 5 · Cameo: 1 | Draft Eligible: 11

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Pickford** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Tarkowski** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Garner** | MID | Regular Starter | 0.75 | `exclude_gw1` | Groin injury - Expected back 22 Aug |
| **Dewsbury-Hall** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Ndiaye** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **O'Brien** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Mykolenko** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Röhl** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Hackney** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Beto** | FWD | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Keane** | DEF | Rotation | 0.40 | `not_role_eligible` | Scout XI CB, but Meerkat says only Tarkowski is certain and Keane/Branthwaite/Garner are flexible. → Rotation. |
| **Branthwaite** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **George** | MID | Rotation | 0.40 | `not_role_eligible` | £18m from Chelsea; Meerkat says kept and gains minutes if Ndiaye exits. Contingent Rotation path. |
| **McNeil** | MID | Rotation | 0.40 | `not_role_eligible` | Wide competition with Röhl/Ndiaye/George. |
| **Barry** | FWD | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Dibling** | MID | Cameo | 0.10 | `not_role_eligible` | Attacking bench option GW1–5. |
| **Iroegbunam** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |

#### 10. Fulham (`FUL`) — 17 players
- **Summary**: Nailed: 4 · Regular: 6 · Rotation: 4 · Cameo: 3 | Draft Eligible: 10

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Leno** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Robinson** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Bassey** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Iwobi** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Castagne** | DEF | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **J.Cuenca** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Lukić** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Berge** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Bobb** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Smith Rowe** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Muniz** | FWD | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Tete** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Kevin** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Sessegnon** | DEF | Cameo | 0.10 | `not_role_eligible` | LB/wing depth behind Robinson; late Sub-in path. |
| **King** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Kusi-Asare** | FWD | Cameo | 0.10 | `not_role_eligible` | £5.2m Bayern signing; Meerkat flags £4.5m Kusi-Asare as backup ST who could get minutes. |
| **Cairney** | MID | Cameo | 0.10 | `not_role_eligible` | Veteran mid depth behind Lukić/Berge. |

#### 11. Hull City (`HUL`) — 15 players
- **Summary**: Nailed: 0 · Regular: 9 · Rotation: 6 · Cameo: 0 | Draft Eligible: 9

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Butland** | GKP | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Egan** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Hughes** | DEF | Rotation | 0.40 | `exclude_gw1` | API status=i; chance=0.0; Groin injury - Unknown return date |
| **Coyle** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Giles** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Targett** | DEF | Rotation | 0.40 | `not_role_eligible` | Free transfer Targett→Hull; Meerkat asks if starter. No Scout XI → Rotation not Regular. |
| **Ajayi** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Slater** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Ömür** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Belloumi** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Millar** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Kamara** | MID | Rotation | 0.40 | `not_role_eligible` | CM depth challenger; Meerkat provides no green nailed list for Hull. |
| **Morita** | MID | Rotation | 0.40 | `not_role_eligible` | New/available CM option at £5.0m; unsettled midfield → Rotation. |
| **McBurnie** | FWD | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Crooks** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |

#### 12. Ipswich Town (`IPS`) — 19 players
- **Summary**: Nailed: 0 · Regular: 10 · Rotation: 9 · Cameo: 0 | Draft Eligible: 10

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Van Oevelen** | GKP | Rotation | 0.40 | `not_role_eligible` | New GK (van Oevelen→Ipswich) in three-way fight with Scherpen/Walton; budget-GK note unsettled. No Scout XI. |
| **Scherpen** | GKP | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Diop** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **O'Shea** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Greaves** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Davis** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Furlong** | DEF | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Kipré** | DEF | Rotation | 0.40 | `not_role_eligible` | CB depth behind Diop/O'Shea; Rotation not Regular. |
| **Fatawu** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Maeda** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Clarke** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Philogene** | MID | Rotation | 0.40 | `not_role_eligible` | Wide rotation vs Fatawu/Maeda/Clarke; Meerkat did not nail him. |
| **Matusiwa** | MID | Rotation | 0.40 | `exclude_gw1` | API status=i; chance=0.0; Muscular injury - Unknown return date |
| **Núñez** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Szmodics** | MID | Rotation | 0.40 | `not_role_eligible` | Attacking MID/second-striker rotation behind new first-choice attackers. |
| **Emersonn** | FWD | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Hirst** | FWD | Rotation | 0.40 | `not_role_eligible` | Incumbent ST competing with Emersonn; shares early minutes. |
| **Mehmeti** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Walle Egeli** | FWD | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |

#### 13. Leeds (`LEE`) — 17 players
- **Summary**: Nailed: 7 · Regular: 5 · Rotation: 4 · Cameo: 1 | Draft Eligible: 12

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Perri** | GKP | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Rodon** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Muharemović** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Bijol** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Gudmundsson** | DEF | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Bogle** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Justin** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Ampadu** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Stach** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Wilson** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Okafor** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (Meerkat 🟢 / predicted). |
| **Aaronson** | MID | Rotation | 0.40 | `not_role_eligible` | Scout XI AM; Meerkat nails Wilson/Okafor/DCL front 3 instead → Rotation. |
| **Tanaka** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Gnonto** | MID | Cameo | 0.10 | `not_role_eligible` | Wide challenger behind Wilson/Okafor; not in Scout XI or Meerkat green. |
| **Calvert-Lewin** | FWD | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Trafford** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Longstaff** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |

#### 14. Liverpool (`LIV`) — 17 players
- **Summary**: Nailed: 6 · Regular: 4 · Rotation: 4 · Cameo: 3 | Draft Eligible: 10

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **A.Becker** | GKP | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Virgil** | DEF | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Kerkez** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Jacquet** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Frimpong** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Gomez** | DEF | Rotation | 0.40 | `exclude_gw1` | API status=i; chance=0.0; Muscular injury - Unknown return date |
| **Bradley** | DEF | Cameo | 0.10 | `exclude_gw1` | API status=i; chance=0.0; Knee injury - Unknown return date |
| **Gravenberch** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Mac Allister** | MID | Regular Starter | 0.75 | `watch` | Post-tournament fitness management. |
| **Wirtz** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Szoboszlai** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Gakpo** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **C.Jones** | MID | Rotation | 0.40 | `not_role_eligible` | Meerkat: Jones could come into side if stays; not Scout XI → Rotation. |
| **Munoz** | MID | Cameo | 0.10 | `not_role_eligible` | Victor Munoz→LIV; Meerkat backup option for now. FPL web_name Munoz. |
| **Isak** | FWD | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Ekitiké** | FWD | Cameo | 0.10 | `exclude_gw1` | API status=i; chance=0.0; Achilles injury - Unknown return date |
| **Ngumoha** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |

#### 15. Man City (`MCI`) — 18 players
- **Summary**: Nailed: 4 · Regular: 10 · Rotation: 3 · Cameo: 1 | Draft Eligible: 14

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Donnarumma** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Matheus N.** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Guéhi** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (Meerkat 🟢 / predicted). |
| **O'Reilly** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (Meerkat 🟢 / predicted). |
| **Gvardiol** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Khusanov** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Rúben** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Anderson** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Rodrigo** | MID | Regular Starter | 0.75 | `exclude_gw1` | Back surgery recovery; miss GW1. |
| **Semenyo** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Reijnders** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Kovačić** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Foden** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Doku** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Cherki** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Marmoush** | FWD | Cameo | 0.10 | `not_role_eligible` | ST/wide backup behind Haaland/Semenyo; not Scout or Meerkat XI. |
| **Haaland** | FWD | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Aït-Nouri** | DEF | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |

#### 16. Man Utd (`MUN`) — 20 players
- **Summary**: Nailed: 5 · Regular: 6 · Rotation: 6 · Cameo: 3 | Draft Eligible: 11

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Lammens** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Shaw** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Maguire** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Dalot** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **B.Fernandes** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Martinez** | DEF | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Mbeumo** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Cunha** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Mount** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Mainoo** | MID | Rotation | 0.40 | `not_role_eligible` | Scout XI starter demoted: Meerkat explicit rotation — only 2 of Santos/Mainoo/Tielemans start. |
| **Amad** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Tielemans** | MID | Rotation | 0.40 | `not_role_eligible` | £35m Villa signing into CM pool; Meerkat only 2 of Santos/Mainoo/Tielemans start. API hamstring 75% — role when fit. |
| **Andrey Santos** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Šeško** | FWD | Rotation | 0.40 | `not_role_eligible` | ST in Meerkat Cunha/Mbeumo/Sesko vs Amad fight; not Scout XI. API shin 75% — role when fit. |
| **De Ligt** | DEF | Cameo | 0.10 | `exclude_gw1` | API status=i; chance=0.0; Back injury - Unknown return date |
| **Ugarte** | MID | Cameo | 0.10 | `exclude_gw1` | API status=i; chance=0.0; Knee injury - Unknown return date |
| **Mazraoui** | DEF | Cameo | 0.10 | `not_role_eligible` | Fullback cover for Dalot/Shaw; neither Scout XI nor Meerkat green. |
| **Bruno G.** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Yoro** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Dorgu** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |

#### 17. Newcastle (`NEW`) — 19 players
- **Summary**: Nailed: 1 · Regular: 11 · Rotation: 6 · Cameo: 1 | Draft Eligible: 12

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Pope** | GKP | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (Meerkat 🟢 / predicted). |
| **Thiaw** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Livramento** | DEF | Regular Starter | 0.75 | `watch` | Calf injury - 75% chance of playing |
| **Botman** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Hall** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Burn** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **L.Miley** | MID | Rotation | 0.40 | `exclude_gw1` | API status=i; chance=0.0; Leg injury - Expected back 30 Aug |
| **Barnes** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Elanga** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Willock** | MID | Rotation | 0.40 | `not_role_eligible` | Scout XI AM; Meerkat few-nailed / midfield flux — conservative demotion to Rotation. |
| **J.Ramsey** | MID | Rotation | 0.40 | `not_role_eligible` | Scout XI attacker; not Meerkat green and attack unsettled post-Gordon — Rotation. |
| **Osula** | FWD | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Touré** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Bamba** | MID | Rotation | 0.40 | `not_role_eligible` | Meerkat lists Bamba with Touré as Gordon replacement options; shared wide minutes. |
| **Woltemade** | FWD | Cameo | 0.10 | `not_role_eligible` | ST minefield challenger; not Scout XI. |
| **Wissa** | FWD | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Joelinton** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Jacob** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Steur** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |

#### 18. Nott'm Forest (`NFO`) — 17 players
- **Summary**: Nailed: 1 · Regular: 10 · Rotation: 4 · Cameo: 2 | Draft Eligible: 11

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Sels** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **N.Williams** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Murillo** | DEF | Regular Starter | 0.75 | `watch` | Muscle injury - 75% chance of playing |
| **Milenković** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Aina** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Sangaré** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Gibbs-White** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Jair Cunha** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Schlager** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Igor Jesus** | FWD | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Dominguez** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Hutchinson** | MID | Rotation | 0.40 | `not_role_eligible` | Scout XI winger demoted: Meerkat wingers rotate (Hudson-Odoi/Ndoye/Bakwa/Hutchinson). |
| **Wood** | FWD | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Hudson-Odoi** | MID | Rotation | 0.40 | `not_role_eligible` | Wing rotation pool; API thigh 75%. Meerkat wingers not nailed. |
| **Ndoye** | MID | Rotation | 0.40 | `not_role_eligible` | Wing rotation challenger; not Scout XI. |
| **Bakwa** | MID | Cameo | 0.10 | `not_role_eligible` | Wide depth in Meerkat wing-rotation set; fringe vs Hutchinson/Hudson-Odoi/Ndoye. |
| **Morato** | DEF | Cameo | 0.10 | `not_role_eligible` | CB cover behind Murillo/Milenkovic/Jair; not Scout XI. |

#### 19. Spurs (`TOT`) — 20 players
- **Summary**: Nailed: 3 · Regular: 8 · Rotation: 8 · Cameo: 1 | Draft Eligible: 11

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Kinsky** | GKP | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Van de Ven** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Pedro Porro** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Van Hecke** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Fernandes** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Tonali** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Udogie** | DEF | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Kudus** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Maddison** | MID | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Tel** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Solanke** | FWD | Rotation | 0.40 | `not_role_eligible` | Previously draft-role but absent from current FFS XI and Meerkat nailed list. |
| **Danso** | DEF | Rotation | 0.40 | `not_role_eligible` | Scout XI CB demoted: Meerkat nails van Hecke and notes Senesi CB competition. |
| **Senesi** | DEF | Rotation | 0.40 | `not_role_eligible` | Free from Bournemouth; Meerkat Senesi competes for CB minutes vs van Hecke/Danso/Romero. |
| **Bentancur** | MID | Rotation | 0.40 | `not_role_eligible` | Scout XI CM demoted by Meerkat Tonali/Fernandes midfield priority. |
| **Gallagher** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Dubravka** | GKP | Rotation | 0.40 | `not_role_eligible` | Confirmed summer free transfer from Burnley; started pre-season friendly (Sydney XI) creating active starter competit... |
| **Romero** | DEF | Cameo | 0.10 | `not_role_eligible` | Neither Scout XI nor Meerkat green; CB depth behind VDV/van Hecke fight. |
| **Robertson** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Richarlison** | FWD | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Moore** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |

#### 20. Sunderland (`SUN`) — 18 players
- **Summary**: Nailed: 7 · Regular: 6 · Rotation: 2 · Cameo: 3 | Draft Eligible: 13

| Player | Pos | Role | $p_{\text{start}}$ | Draft Availability | Evidence / Source Signal |
|---|---|---|---|---|---|
| **Roefs** | GKP | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Mukiele** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (Meerkat 🟢 / predicted). |
| **Ballard** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Alderete** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (Meerkat 🟢 / predicted). |
| **Reinildo** | DEF | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Sadiki** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Xhaka** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **E.Le Fée** | MID | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Brobbey** | FWD | Nailed Starter | 0.90 | `eligible` | Unanimous: FFS predicted XI + Meerkat 🟢 nailed. |
| **Hume** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Angulo** | MID | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Adingra** | MID | Rotation | 0.40 | `not_role_eligible` | Wide rotation challenger outside Scout XI; Meerkat wingers not nailed. |
| **Talbi** | MID | Rotation | 0.40 | `not_role_eligible` | Wide/attack rotation option; not Scout XI. |
| **Meunier** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
| **Isidor** | FWD | Cameo | 0.10 | `not_role_eligible` | ST depth behind Brobbey; not Scout XI. |
| **Diarra** | MID | Cameo | 0.10 | `not_role_eligible` | Midfield depth behind Xhaka/Sadiki/Le Fee. |
| **Mundle** | MID | Cameo | 0.10 | `not_role_eligible` | Wide depth in non-nailed wing pool. |
| **O'Nien** | DEF | Regular Starter | 0.75 | `eligible` | Single-source or non-unanimous starter signal (FFS predicted XI). |
---

## Decision

**Verdict**: 20-club Expected Role scaffold refreshed from dual live scrape (FFS + Meerkat), 357 contention rows, 224 Draft-eligible players categorized.

---

## Verification & Delivery

- Stage 1 script: `docs/research/gw1-6-preseason-pipeline/01-expected-role-gw1-5/refresh_expected_role.py`.
- Output CSV: `data/research/gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.csv`.

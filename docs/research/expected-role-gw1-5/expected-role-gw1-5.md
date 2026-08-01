# FPL 2026/27 Expected Role (GW1–5) — Draft Shortlist & Mins Priors

**Updated**: 2026-08-01T15:59:00+07:00
**Data stamp**: Meerkat predicted XIs 2026-07-28; Scout team-news and official Club evidence checked through 2026-08-01; positional research notes audited 2026-08-01; summer-transfers register through 2026-07-30; local `players.parquet` freshness proxy 2026-07-29; table regenerated 2026-08-01
**Season**: 2026/27  
**Status**: Active · role and availability audit applied; model ingest deferred
**Purpose**: Assign fit-conditional Expected Role, dated Draft Availability, and Participation State priors for GW1–5 mins projection seeding
**Scope**: XI Contention Set for all 20 Clubs; fit-role Draft Shortlist = Nailed Starter + Regular Starter; Draft Availability separately filters current `Eligible`, `Watch`, and `Exclude` rows. No model code wiring in this note.
**Related**: [Summer transfers](../fpl-preseason-guide/fpl-summer-transfers.md) · [Pre-season guide directory](../fpl-preseason-guide/fpl-preseason-guide.md) · `CONTEXT.md` (Expected Role / Role Evidence / Expected Role Table)
**Artifact**: [Expected Role Table CSV](../../../data/research/expected-role-gw1-5/expected-role-gw1-5.csv) — canonical row-level data; this Research Note is its human-readable companion.

> Source claims not independently validated. API club registration may lag confirmed transfers (e.g. Lacroix still CRY, Trafford still MCI in local roster).

## Sources

- **Primary**: [FPL GW1 Predicted Line-ups For ALL Teams — Charlie (FPL Meerkat) / fpl.page](https://fpl.page/article/fpl-gw1-predicted-lineups-2627) — published 2026-07-28; accessed 2026-07-31; role: nailed (🟢) + narrative XI contention
- **Primary**: [FPL 2026/27 Predicted Line-ups — Fantasy Football Scout Team News](https://www.fantasyfootballscout.co.uk/team-news) — club stamps ~2026-07-21/22; accessed 2026-07-31; role: predicted XI + injury/doubt flags (Coventry/Hull/Ipswich absent from page capture)
- **Primary**: [FPL 2026/27 transfer news — Fantasy Football Scout](https://www.fantasyfootballscout.co.uk/fpl-2026-27-transfer-news-confirmed-summer-signings) via [fpl-summer-transfers.md](fpl-summer-transfers.md) — register through 2026-07-30; role: confirmed moves
- **Primary**: [Medical update: William Saliba — Arsenal](https://www.arsenal.com/news/medical-update-william-saliba-aVUca3q2han2) — accessed 2026-07-31; role: official rehabilitation / availability
- **Primary**: [Andoni Iraola's update on World Cup players — Liverpool FC](https://www.liverpoolfc.com/news/andoni-iraolas-update-when-reds-world-cup-players-will-return) — accessed 2026-07-31; role: official late-return guidance
- **Primary**: [England: Saka pleased to finish strongly](https://www.englandfootball.com/articles/2026/Jul/18/bukayo-saka-france-v-england-world-cup-third-place-playoff-match-reaction-20261807) — accessed 2026-07-31; role: tournament participation / post-match fitness evidence
- **Repository data**: `data/processed/players.parquet` + `clubs.parquet` — player_id / web_name / club mapping; cutoff = last refresh

**Source boundary**: Predicted XIs are opinion. Confirmed transfers are source-claimed. No official Club XI verification. Scout page capture missing three promoted Clubs.

## Agent Prompt

```text
Full redo docs/research/expected-role-gw1-5.md and data/research/expected-role-gw1-5.csv

1. Re-fetch Meerkat article + Scout team-news with Playwright if needed; refresh summer-transfers note.
2. Re-export roster from data/processed/players.parquet; resolve web_name/player_id mismatches from transfers.
3. Rebuild XI Contention Set per Club using locked rules in CONTEXT.md / task.md Work Packet.
4. Every row must carry Role Evidence: reason, sources, conflict_rule, confidence.
5. Apply defaults: Nailed 0.90/0.05/85/20; Regular 0.75/0.10/80/20; Rotation 0.40/0.25/70/20; Cameo 0.10/0.35/60/15 unless override=true.
6. Conflicts: Nailed vs Regular → Regular; Regular vs Rotation → Rotation; single source → confidence=low.
7. Add API availability/registration fields and dated Availability Override; keep fit-role priors conditional on availability.
8. Keep Source synthesis separate from Project interpretation.
9. Update Updated, Data stamp, Findings, Decision, Risks; regenerate CSV; delete .tmp/agent scratch.
10. Run uv run ruff check ., uv run pytest, bash tests/verify.sh before Checkpoint.
```

## Method

**Method type**: Multi-source synthesis → Expected Role Table

**Inputs**:
- Meerkat GW1 predicted lineups (🟢 = nailed lean)
- Scout Team News predicted XIs + doubts
- Confirmed summer-transfer register
- Local FPL roster for ids
- Official Club/Federation availability and pre-season team-news updates

**Procedure**:
1. Build XI Contention Set per Club from Scout XI ∪ Meerkat nailed/narrative ∪ key new signings.
2. Assign Expected Role using source priority: confirmed facts → Scout XI → Meerkat → friendlies/notes → secondary.
3. Apply conflict demotion rules; attach Role Evidence on every row.
4. Attach Expected Role Prior defaults; override only when sources clearly diverge.
5. Apply separate API/official-source availability and registration overlays; do not demote fit-role for temporary absence.
6. Emit fit-role Draft Shortlist (Nailed + Regular) per Club; apply Draft Availability separately; footnote Out of Contention.
7. Write Research Note narrative + `data/research/expected-role-gw1-5.csv`.

**Definitions and assumptions**:
- See `CONTEXT.md`: Expected Role, Expected Role Prior, XI Contention Set, Draft Shortlist, Role Evidence, Expected Role Table.
- Horizon = GW1–5 early-season band.
- Injury/doubt/late return: keep Expected Role when fit; API chance / Availability Override handles current Draft Availability.
- `p_start`, `p_sub_in`, and `p_dnp` remain fit-role priors; effective current probabilities require the availability layer.

**Validation boundary**: Opinion synthesis only. Not calibrated against actual minutes. API transfer lag may mis-club players until refresh.

## Source synthesis

### Main claims

- Meerkat (28 Jul) publishes all-20 predicted lineups with 🟢 nailed markers and formation/signing notes.
- Scout Team News (~21–22 Jul) publishes predicted XIs for 17 Clubs (Coventry, Hull, Ipswich absent in capture) plus out/doubt lists.
- Summer-transfer register (through 30 Jul) moves several Scout/Meerkat assumptions (e.g. Lacroix → Chelsea; Anderson → Man City; Tonali → Spurs).
- Official Arsenal evidence confirms Saliba's extended rehabilitation; official Liverpool evidence says Mac Allister's late return may affect the opening fixture; England/Arsenal evidence confirms Saka's tournament participation and short pre-season runway.
- Fresh friendly evidence supports conservative Nailed → Regular changes for Pope and Kinsky, and Regular → Rotation for Perri; no audited Rotation row had enough evidence for promotion.

### Source rationale

- Dual XI sources reduce single-author bias; transfer register overrides stale XI assumptions.
- Conservative demotion protects Draft Shortlist from optimistic Nailed labels.

## Project interpretation

### Decision rules

- Draft Shortlist membership ⇔ Expected Role ∈ {Nailed Starter, Regular Starter}.
- Draft Availability is applied after role assignment: only `eligible` rows are safe for an unqualified current Draft; `watch` rows require recheck; `exclude_gw1` / `exclude_gw1-5` rows stay out for that window.
- `p_dnp = 1 - p_start - p_sub_in`; state probs seed Participation State priors later.
- Prefer Regular over Nailed when Meerkat 🟢 and Scout disagree on start.
- Prefer Rotation over Regular when sources describe sharing/bench risk.
- Keep fit-role priors separate from current availability; never interpret `p_start` as unconditional when an Availability Override exists.

### Practical implications

- Use Draft Shortlist for human Draft construction.
- Use `draft_availability=eligible` for a conservative current Draft; recheck `watch` rows before selection.
- Use full Expected Role Table CSV, including availability fields, for mins prior seeding after the ingest ticket.

## Club-by-club Expected Role Table

The [Expected Role Table CSV](../../data/research/expected-role-gw1-5.csv) is the row-level audit authority. It contains 340 XI Contention Set rows across all 20 Clubs: 90 Nailed Starter, 103 Regular Starter, 100 Rotation, and 47 Cameo. Every row includes `player_id`, fit-role priors, Role Evidence, direct source references, API availability/registration fields, and dated Draft Availability.

**Draft Shortlist** below means fit-role Nailed Starter + Regular Starter. `Draft Availability` can exclude or flag a listed Player for current selection without changing fit-role.

### Arsenal (ARS)

- **Draft Shortlist:** Raya, Gabriel, Saliba, J.Timber, Rice, Saka, White, Mosquera, Calafiori, Ødegaard, Zubimendi, Eze, Madueke, Gyökeres, Martinelli
- **Nailed Starter:** Raya, Gabriel, Saliba
- **Regular Starter:** J.Timber, Rice, Saka, White, Mosquera, Calafiori, Ødegaard, Zubimendi, Eze, Madueke, Gyökeres, Martinelli
- **Rotation:** Hincapie, Tzolis
- **Cameo:** Havertz
- **Current Draft Availability:** Saliba `exclude_gw1-5`; J.Timber `exclude_gw1`; Saka `watch`; White `watch`. See CSV `availability_override` and `availability_reason`.

### Aston Villa (AVL)

- **Draft Shortlist:** Martinez, Konsa, Cash, Kamara, Watkins, Pau, Maatsen, Lindelöf, McGinn, Barkley, Buendía
- **Nailed Starter:** Martinez, Konsa, Cash, Kamara, Watkins
- **Regular Starter:** Pau, Maatsen, Lindelöf, McGinn, Barkley, Buendía
- **Rotation:** Manzambi, Gomes, Garnacho
- **Cameo:** Digne, Bailey, Guessand

### Bournemouth (BOU)

- **Draft Shortlist:** Petrović, Hill, Truffert, Scott, Adams, Kroupi.Jr, Tavernier, Rayan, Smith, Diakité
- **Nailed Starter:** Petrović, Hill, Truffert, Scott, Adams, Kroupi.Jr, Tavernier, Rayan
- **Regular Starter:** Smith, Diakité
- **Rotation:** Evanilson, Rodríguez, Christie
- **Cameo:** Kluivert, Cook, Milosavljević

### Brentford (BRE)

- **Draft Shortlist:** Kelleher, Collins, Kayode, Schade, O.Dango, Thiago, Van den Berg, Lewis-Potter, Yarmoliuk, Janelt, Jensen
- **Nailed Starter:** Kelleher, Collins, Kayode, Schade, O.Dango, Thiago
- **Regular Starter:** Van den Berg, Lewis-Potter, Yarmoliuk, Janelt, Jensen
- **Rotation:** Carvalho, Milambo
- **Cameo:** Anthony, Schuster, Damsgaard, Wilson

### Brighton (BHA)

- **Draft Shortlist:** Verbruggen, F.Kadıoğlu, Dunk, Vuskovic, Groß, Wieffer, Baleba, De Cuyper
- **Nailed Starter:** Verbruggen, F.Kadıoğlu, Dunk, Vuskovic, Groß
- **Regular Starter:** Wieffer, Baleba, De Cuyper
- **Rotation:** Gomez, Hinshelwood, Minteh, Welbeck, Mitoma, Tzimas
- **Cameo:** Struijk, Georginio, Ayari

### Chelsea (CHE)

- **Draft Shortlist:** Sánchez, Colwill, Lacroix, James, Enzo, Caicedo, Rogers, Palmer, João Pedro, Hato
- **Nailed Starter:** Sánchez, Colwill, Lacroix, Caicedo, Rogers, Palmer, João Pedro
- **Regular Starter:** James, Enzo, Hato
- **Rotation:** Gusto, Tosin, Palestra, Lavia, Neto, Gittens, Quenda
- **Cameo:** Estêvão

### Coventry City (COV)

- **Draft Shortlist:** Wilson, Amenda, Thomas, van Ewijk, Tchaouna, Torp, Mason-Clark, Onyeka, Grimes, Wright
- **Nailed Starter:** —
- **Regular Starter:** Wilson, Amenda, Thomas, van Ewijk, Tchaouna, Torp, Mason-Clark, Onyeka, Grimes, Wright
- **Rotation:** Kitching, Dasilva, Sakamoto, Eccles, Rudoni, Thomas-Asante, Simms
- **Cameo:** Markelo

### Crystal Palace (CRY)

- **Draft Shortlist:** Henderson, Richards, Mitchell, Muñoz, Sarr, Canvot, Kamada, Wharton, Yeremy, Strand Larsen
- **Nailed Starter:** Henderson, Richards, Mitchell, Muñoz, Sarr
- **Regular Starter:** Canvot, Kamada, Wharton, Yeremy, Strand Larsen
- **Rotation:** Mingueza, Mateta, Johnson, Lerma
- **Cameo:** Esse, Nketiah, Devenny

### Everton (EVE)

- **Draft Shortlist:** Pickford, Tarkowski, Garner, Dewsbury-Hall, Ndiaye, O'Brien, Mykolenko, Röhl, Hackney, Beto
- **Nailed Starter:** Pickford, Tarkowski, Dewsbury-Hall, Ndiaye
- **Regular Starter:** Garner, O'Brien, Mykolenko, Röhl, Hackney, Beto
- **Rotation:** Keane, Branthwaite, George, McNeil
- **Cameo:** Barry, Dibling, Iroegbunam

### Fulham (FUL)

- **Draft Shortlist:** Leno, Robinson, Bassey, Iwobi, Castagne, J.Cuenca, Lukić, Berge
- **Nailed Starter:** Leno, Robinson, Bassey, Iwobi
- **Regular Starter:** Castagne, J.Cuenca, Lukić, Berge
- **Rotation:** Bobb, Smith Rowe, Muniz, Tete, Kevin
- **Cameo:** Sessegnon, King, Kusi-Asare, Cairney

### Hull City (HUL)

- **Draft Shortlist:** Butland, Egan, Hughes, Coyle, Slater, Ömür, Belloumi, McBurnie
- **Nailed Starter:** —
- **Regular Starter:** Butland, Egan, Hughes, Coyle, Slater, Ömür, Belloumi, McBurnie
- **Rotation:** Giles, Targett, Ajayi, Millar, Kamara, Morita
- **Cameo:** —

### Ipswich Town (IPS)

- **Draft Shortlist:** Diop, O'Shea, Greaves, Fatawu, Maeda, Clarke, Matusiwa, Emersonn
- **Nailed Starter:** —
- **Regular Starter:** Diop, O'Shea, Greaves, Fatawu, Maeda, Clarke, Matusiwa, Emersonn
- **Rotation:** Van Oevelen, Scherpen, Davis, Furlong, Kipré, Philogene, Núñez, Szmodics, Hirst
- **Cameo:** —

### Leeds (LEE)

- **Draft Shortlist:** Rodon, Muharemović, Gudmundsson, Bogle, Justin, Ampadu, Stach, Wilson, Okafor, Calvert-Lewin
- **Nailed Starter:** Rodon, Gudmundsson, Ampadu, Stach, Calvert-Lewin
- **Regular Starter:** Muharemović, Bogle, Justin, Wilson, Okafor
- **Rotation:** Perri, Bijol, Aaronson, Tanaka
- **Cameo:** Gnonto

### Liverpool (LIV)

- **Draft Shortlist:** A.Becker, Virgil, Kerkez, Jacquet, Frimpong, Gomez, Gravenberch, Mac Allister, Wirtz, Szoboszlai, Gakpo, Isak
- **Nailed Starter:** A.Becker, Virgil, Kerkez, Gravenberch, Mac Allister, Wirtz, Szoboszlai, Isak
- **Regular Starter:** Jacquet, Frimpong, Gomez, Gakpo
- **Rotation:** C.Jones
- **Cameo:** Bradley, Munoz, Ekitiké

### Man City (MCI)

- **Draft Shortlist:** Donnarumma, Matheus N., Guéhi, O'Reilly, Gvardiol, Anderson, Rodrigo, Semenyo, Foden, Haaland
- **Nailed Starter:** Donnarumma, Matheus N., Semenyo, Haaland
- **Regular Starter:** Guéhi, O'Reilly, Gvardiol, Anderson, Rodrigo, Foden
- **Rotation:** Khusanov, Rúben, Reijnders, Kovačić, Doku, Cherki
- **Cameo:** Trafford, Marmoush

### Man Utd (MUN)

- **Draft Shortlist:** Lammens, Shaw, Maguire, Dalot, B.Fernandes, Martinez, Mbeumo, Cunha
- **Nailed Starter:** Lammens, Shaw, Maguire, Dalot, B.Fernandes
- **Regular Starter:** Martinez, Mbeumo, Cunha
- **Rotation:** Mount, Mainoo, Amad, Tielemans, Andrey Santos, Šeško
- **Cameo:** De Ligt, Ugarte, Mazraoui

### Newcastle (NEW)

- **Draft Shortlist:** Pope, Thiaw, Livramento, Bruno G.
- **Nailed Starter:** Thiaw, Livramento, Bruno G.
- **Regular Starter:** Pope
- **Rotation:** Botman, Hall, Burn, L.Miley, Barnes, Elanga, Willock, J.Ramsey, Osula, Touré, Bamba
- **Cameo:** Woltemade, Wissa, Joelinton
- **Current Draft Availability:** Livramento `watch` (API 75% next-round chance); Thiaw remains Nailed when fit but needs senior-XI recheck.

### Nott'm Forest (NFO)

- **Draft Shortlist:** Sels, N.Williams, Murillo, Milenković, Aina, Sangaré, Gibbs-White, Jair Cunha, Schlager, Igor Jesus
- **Nailed Starter:** Sels, N.Williams, Murillo, Milenković, Aina, Sangaré, Gibbs-White
- **Regular Starter:** Jair Cunha, Schlager, Igor Jesus
- **Rotation:** Dominguez, Hutchinson, Wood, Hudson-Odoi, Ndoye
- **Cameo:** Bakwa, Morato

### Spurs (TOT)

- **Draft Shortlist:** Kinsky, Van de Ven, Pedro Porro, Van Hecke, Fernandes, Tonali, Udogie, Kudus, Maddison, Tel, Solanke
- **Nailed Starter:** Van de Ven, Pedro Porro
- **Regular Starter:** Kinsky, Van Hecke, Fernandes, Tonali, Udogie, Kudus, Maddison, Tel, Solanke
- **Rotation:** Danso, Senesi, Bentancur, Gallagher, Dubravka
- **Cameo:** Romero, Robertson, Richarlison
- **Current Draft Availability:** Kudus `watch` (API 75% next-round chance).

### Sunderland (SUN)

- **Draft Shortlist:** Roefs, Mukiele, Ballard, Alderete, Reinildo, Sadiki, Xhaka, E.Le Fée, Brobbey
- **Nailed Starter:** Roefs, Mukiele, Ballard, Alderete, Reinildo, Sadiki, Xhaka, E.Le Fée, Brobbey
- **Regular Starter:** —
- **Rotation:** Hume, Angulo, Adingra, Talbi
- **Cameo:** Meunier, Isidor, Diarra, Mundle

## Current Draft Availability Audit

Fit-role Draft Shortlist contains 193 Players after three evidence-backed role changes. Current overlay: 179 `eligible`, 9 `watch`, 4 `exclude_gw1`, and 1 `exclude_gw1-5`. Only `eligible` rows are safe without a further availability decision.

**Exclude GW1–5:**

- **Saliba (ARS, Nailed):** Arsenal medical update confirms extended rehabilitation after back injury; no return date. Keep Nailed when fit; exclude current band pending clearance. [Arsenal medical update](https://www.arsenal.com/news/medical-update-william-saliba-aVUca3q2han2)

**Exclude GW1:**

- **J.Timber (ARS, Regular):** FPL API 0%; groin injury, expected back 21 Aug.
- **Garner (EVE, Regular):** FPL API 0%; groin injury, expected back 22 Aug.
- **Gomez (LIV, Regular):** FPL API 0%; muscular injury, unknown return.
- **Rodrigo (MCI, Regular):** FPL API 0%; back injury, unknown return.

**Watch before GW1:**

- **Saka (ARS, Regular):** England World Cup bronze-match starter; late return and Achilles assessment leave GW1 uncertain. Keep Regular when fit. [England match reaction](https://www.englandfootball.com/articles/2026/Jul/18/bukayo-saka-france-v-england-world-cup-third-place-playoff-match-reaction-20261807)
- **White (ARS, Regular):** stale local API says 0% while newer training evidence says he returned to group work; resolve with fresh official team news.
- **Mac Allister (LIV, Nailed):** Liverpool says late World Cup return may affect the 23 Aug opener; keep Nailed when fit. [Liverpool return update](https://www.liverpoolfc.com/news/andoni-iraolas-update-when-reds-world-cup-players-will-return)
- **Kamara (AVL, Nailed), Wharton (CRY, Regular), Martinez (MUN, Regular), Livramento (NEW, Nailed), Murillo (NFO, Nailed), Kudus (TOT, Regular):** FPL API status `d`, 75% next-round chance; keep fit-role and recheck.

**Role changes applied after fresh friendly evidence:**

- **Perri (LEE):** Regular → Rotation; Cairns started both recent Leeds friendlies while Perri had one second-half appearance and then missed the squad; Torino transfer reporting adds uncertainty. [Leeds Sunderland team news](https://www.leedsunited.com/en/news/team-news-leeds-united-vs-sunderland)
- **Pope (NEW):** Nailed → Regular; shared goalkeeper minutes with Jaouen, who started against Bristol City. [Newcastle confirmed lineup](https://www.newcastleunited.com/en/news/confirmed-line-up-jaouen-starts-at-ashton-gate)
- **Kinsky (TOT):** Nailed → Regular; Austin and Dubravka started later friendlies, including the stronger Sydney XI. [Spurs Sydney lineup](https://www.tottenhamhotspur.com/news/1080518/victory-on-penalties-after-tel-stunner-against-sydney)

No Rotation Player had sufficient fresh evidence for promotion. Thiaw, Botman, Evanilson, Mateta, Lacroix, and Ndiaye remain flagged for recheck but retain current fit-roles.

## Out of Contention Footnotes

These Players are excluded from CSV rows by design; Club depth and exclusion notes are retained here for audit context.

- **ARS:** Arrizabalaga/Meslier backup GK; Merino, Lewis-Skelly, Nwaneri, Dowman, Fábio Vieira, Nelson, Nørgaard, G.Jesus depth. Bruno Guimarães remains Newcastle in FPL; rumour only.
- **AVL:** Onana out with knee issue; Abraham shoulder issue to approximately 23 Aug; Mings, A.García, Nedeljkovic, Bogarde, Iling Jr, Alysson, Burrowes, George Hemmings depth. Rogers/Tielemans sold.
- **BOU:** Senesi sold to Spurs; Forster/Dennis backup GK; Soler, J.Araujo, Brooks, Tóth.A, Adli, Gannon-Doak, Enes Ünal depth. Europa League rotation risk later beyond GW1–5 core.
- **BRE:** Valdimarsson backup GK; Ajer, Henry, Hickey, Pinnock, Ji-soo, Dasilva, Henderson, Furo depth. Onyeka sold to Coventry.
- **BHA:** Rushworth/Steele backup GK; Coppola, Igor, Boscagli, Costinha, Svoboda, Watson, Howell, Oriola, Buonanotte, O'Riley, Kostoulas depth; Ferguson ankle issue; Van Hecke sold to Spurs. Conference League rotation risk.
- **CHE:** Fofana suspended to 6 Sep; Mudryk out; Garnacho loaned to Aston Villa; Cucurella left. Jörgensen/Penders, Disasi, Anselmino, Acheampong, M.Sarr, N.Jackson, Marc Guiu, Emegha, Mheuka, D.Essugo fringe/backup.
- **COV:** No Scout Team News page. Bassette loaned to Westerlo; Dovin backup GK; Bidwell, Latibeaudiere, Woolfenden, Brau, Kesler-Hayden, Borges Rodrigues, Andrews, Shepherd fringe.
- **CRY:** Lacroix moved to Chelsea but remains on local CRY API roster; Uche returned to Getafe. Benitez/Matthews backup GK; Chadi Riad, Sosa, Cardines, Hughes, Doucouré, J.Rak-Sakyi, M.França, Drakes-Thomas fringe.
- **EVE:** Gueye left; Hackney is Meerkat's replacement. Travers/King backup GK; Patterson, Aznou, Alcaraz, Armstrong fringe.
- **FUL:** Andersen suspended to 29 Aug; Diop moved to Ipswich; Harry Wilson moved to Leeds. Lecomte/McNally backup GK; Reed fringe.
- **HUL:** Cartwright loaned to Grimsby; Lo-Tutala, Jacob, McCarthy, Dowell, Crooks, Gyabi, Akintola, Matazo (knee) and Phillips/McNair/Drameh/Destan/Burstow/Zambrano fringe.
- **IPS:** Palmer, Button, Burns, Ogbene, Mehmeti, Taylor, McAteer, Walle Egeli depth/fringe without a first-choice lean; Walton, Johnson, Akpom, Al-Hamadi also fringe.
- **LEE:** Harrison left permanently; Trafford practically confirmed to Leeds but remains MCI in local FPL roster; Gelhardt, James, Gruev, Mateo Joseph, Bornauw, Longstaff, Nmecha, Piroe fringe.
- **LIV:** Woodman, Pecsi, Jaros, Davies, Lucky, Ramsay, Ngumoha, Elliott, Endo, Nyoni, Bajcetic, Koumas, McConnell, Danns depth/injury; Mamardashvili, Tsimikas, Leoni, Chiesa fringe.
- **MCI:** Bettinelli, Alleyne, Lewis, Vitor Reis, N.Gonzalez, Echeverri, Phillips, Monga, Mukasa depth; Aït-Nouri, Savinho, Grealish fringe.
- **MUN:** Bayindir/Darlow/Heaton GK cover; Heaven, Amass, Fredricson youth CBs; Dorgu/Yoro fringe; Rashford, Zirkzee, Obi, Fletcher, Lacey, Collyer, Mantato out of early XI contention. Darlow API doubt.
- **NEW:** Gillespie/Jaouen GK; A.Murphy, Neave, Schär, Steur, J.Murphy depth/fringe. Gordon/Tonali departed. Conservative Draft Shortlist intentionally only four Players.
- **NFO:** John GK cover; Savona, Netz, Richards, Abbott, Bindon fringe DEF; McAtee/Yates CM depth; Awoniyi/Kalimuendo ST depth. Anderson sold to Man City.
- **TOT:** Vicario/Austin behind Kinsky; Dubravka free signing from Burnley added to Spurs XI Contention Set as Rotation GKP; Spence, Phillips, Davies, Byfield, Rowswell, Souza, Bergvall, Sarr, Gray, Moore, Olusesi depth; Kulusevski, Xavi, Odobert injured; Scarlett ST depth. Simons absent from local FPL roster.
- **SUN:** Ellborg/Patterson GK cover; Seelt, Hjelde, O'Nien, Masuaku DEF depth; Rigg, Jocelin.T fringe MID. Europa League may increase rotation beyond GW1–5.

## Findings

### Evidence

- Consolidated table contains 340 rows across all 20 Clubs: 193 fit-role Draft-eligible (90 Nailed Starter + 103 Regular Starter), 100 Rotation, and 47 Cameo.
- Current Draft Availability overlay: 179 eligible, 9 watch, 4 exclude GW1, and 1 exclude GW1–5.
- Highest fit-role Draft Shortlist counts: Arsenal 15, Liverpool 12, Aston Villa/Spurs 11 each; Leeds is now 10 after Perri's demotion.
- Most conservative fit-role Draft Shortlists: Newcastle 4; Brighton/Fulham 8; Hull/Ipswich 8 each with no Nailed Starter due thin promoted-Club evidence.
- Coventry, Hull, and Ipswich receive lower confidence because Scout Team News does not cover them in the captured page; Coventry has no Nailed Starter.
- Transfer-aware exceptions are preserved in Role Evidence: Lacroix is assigned to Chelsea although the local API roster still lists Crystal Palace; Trafford is assigned to Leeds although the local roster still lists Man City.
- Full reasons, direct source references, fit-role priors, API fields, registration status, and Draft Availability are in `data/research/expected-role-gw1-5.csv`.

### Alternatives

- GW1-only snapshot rejected (too brittle for Draft).
- Full price-list labeling rejected (research cost; low Draft value).

## Decision

**Verdict**: Proceed with Research Note + Expected Role Table under locked Expected Role model; model wiring deferred.

**Recommended action**:
- Use only CSV rows with `draft_availability=eligible` for the current Draft
- Recheck every `watch` row before finalizing the Draft; do not consume `p_start` as unconditional when an Availability Override exists
- Use CSV rows for expected-minutes prior seeding after the ingest ticket
- Refresh before GW1 on material transfer/injury news

**Trigger / kill switch**:
- Kill Nailed → Regular/Rotation if friendly/press-conference evidence shows shared starts
- Kill Draft Shortlist membership if Club signs direct positional rival before GW1

## Risks and unknowns

- Scout stamps older than Meerkat (~1 week); friendlies may already shift XIs
- Promoted Clubs (COV/HUL/IPS) thin sources → low confidence
- API roster lag vs confirmed transfers
- API `chance_of_playing_this_round` is null for all rows; status `a` with null chance is not proof of 100% availability
- World Cup late-return decisions remain manager-specific until training and selection evidence arrives
- European competition rotation not fully priced into GW1–5 defaults

## Refresh checklist

- [x] `Updated` uses ISO 8601 timestamp with timezone.
- [x] `Data stamp` identifies current evidence cutoff.
- [x] `Season` and scope remain accurate.
- [x] Source URLs, publication dates, and access dates checked.
- [x] Source synthesis and Project interpretation remain separate.
- [x] Unvalidated claims labeled.
- [x] Agent Prompt remains runnable and points to stable slug.
- [x] Scratch files removed from `.tmp/agent/`.
- [x] CSV regenerated and Draft Shortlist counts audited.

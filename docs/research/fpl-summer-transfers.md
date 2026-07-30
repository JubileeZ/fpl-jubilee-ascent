# FPL 2026/27 Summer Transfers — Fantasy Football Scout Synthesis

**Updated**: 2026-07-31T06:45:00+07:00  
**Data stamp**: Fantasy Football Scout transfer register includes moves announced through 2026-07-30; page reviewed 2026-07-31  
**Season**: 2026/27  
**Status**: Source synthesis · not independently validated  
**Purpose**: Capture confirmed-move register and identify FPL-relevant follow-up questions  
**Scope**: Source-listed Premier League transfers, transfer fees, destination context, and conditional FPL implications. Fees below are reported transfer fees, not FPL player prices. Source text supplied no complete role, minutes, ranking, or projection analysis.  
**Related**: [Pre-season guide directory](fpl-preseason-guide.md)

## Sources

- **Primary**: [FPL 2026/27 transfer news: Confirmed summer signings — Fantasy Football Scout](https://www.fantasyfootballscout.co.uk/fpl-2026-27-transfer-news-confirmed-summer-signings) — page publication date not exposed in fetched text; register current through 2026-07-30; accessed 2026-07-31; role: transfer register and FPL watchlist source

**Source boundary**: Source claims not independently validated. Fetched page exposes publisher introduction and dated transfer register, but no detailed role/minutes or FPL-price data for listed players. Register is grouped below rather than presented as a full source table.

## Agent Prompt

```text
Full redo docs/research/fpl-summer-transfers.md

1. Re-read https://www.fantasyfootballscout.co.uk/fpl-2026-27-transfer-news-confirmed-summer-signings.
2. Confirm page title, publication/update metadata, register cutoff, player names, destinations, and transfer fees.
3. Keep transfer fees separate from FPL prices; do not invent roles, minutes, rankings, or projections.
4. Preserve Source synthesis separately from Project interpretation.
5. Update Updated, Data stamp, Sources, Findings, Decision, and Risks.
6. Keep filename stable; delete .tmp/agent/ scratch before finishing.
```

## Method

**Method type**: Primary-source synthesis / dated transfer-register extraction

**Inputs**:
- Directly fetched Fantasy Football Scout transfer page
- Page introduction and key-transfer register

**Procedure**:
1. Record publisher scope and stated deadline.
2. Extract source-listed moves by announcement date, destination, and fee.
3. Separate confirmed-move claims from conditional FPL follow-up questions.
4. Flag missing FPL prices, positions, minutes, and rankings.

**Definitions and assumptions**:
- **Transfer fee**: Fee or free/undisclosed value stated by source; not FPL purchase price.
- **Confirmed**: Source labels move as confirmed; not independently checked against club or league announcements.
- **FPL implication**: Conditional project question derived from destination and squad change, not an article-validated recommendation.

**Validation boundary**: Transfer-register synthesis only. No official-club verification, FPL API refresh, lineup check, price lookup, or projection run performed.

## Source synthesis

### Publisher scope

- Page says summer window is open for 2026/27 and that it will list confirmed Premier League moves through the Tuesday 1 September deadline.
- Coverage focuses on key first-team trades, with noteworthy arrivals receiving separate Scout Report or Moving Target coverage and other moves receiving shorter round-ups.
- Register snapshot contains moves announced from 15 May through 30 July 2026.

### Confirmed-move register

All amounts below are source-reported transfer fees.

- **30–29 July**: Maxence Lacroix, Crystal Palace → Chelsea (£52m); Kjell Scherpen, Union Saint-Gilloise → Ipswich (£8.5m).
- **25–23 July**: Daizen Maeda, Celtic → Ipswich (£10m); Elliot Anderson, Nottingham Forest → Manchester City (£116m); Xaver Schlager, RB Leipzig → Nottingham Forest (free); Matt Targett, Newcastle → Hull (free); Christos Tzolis, Club Brugge → Arsenal (£34m); Alejandro Garnacho, Chelsea → Aston Villa (loan).
- **22–20 July**: Issa Diop, Fulham → Ipswich (£8.5m); Kayne van Oevelen, FC Volendam → Ipswich (£3.4m); Morgan Rogers, Aston Villa → Chelsea (£117m); Oscar Zambrano, Maribor → Hull (undisclosed); Abdul Fatawu, Leicester City → Ipswich (£20m); Joao Gomes, Wolverhampton Wanderers → Aston Villa (£38m).
- **17–14 July**: Johan Manzambi, Freiburg → Aston Villa (£50m); Tarik Muharemovic, Sassuolo → Leeds (£34.1m); Aurele Amenda, Frankfurt → Coventry (£17m); Thomas Meunier, Lille → Sunderland (free); Alvaro Rodriguez, Elche → Bournemouth (£25.7m); Youri Tielemans, Aston Villa → Manchester United (£35m); Luka Vuskovic, Tottenham → Brighton (£46m); Karl Darlow, Leeds → Manchester United (free).
- **13–9 July**: Andrey Santos, Chelsea → Manchester United (£48m); Loum Tchaouna, Burnley → Coventry (£20m); Emersonn, Toulouse → Ipswich (£26m); Illan Meslier, Leeds → Arsenal (free); Oscar Mingueza, Celta Vigo → Crystal Palace (free); Sean Steur, Ajax → Newcastle (£23m); Callum Wilson, West Ham United → Brentford (free).
- **8–6 July**: Geovany Quenda, Sporting → Chelsea (£40m); Harry Wilson, Fulham → Leeds (free); Jaidon Anthony, Burnley → Brentford (£15m); Tyrique George, Chelsea → Everton (£18m); Merlin Rohl, Freiburg → Everton (£18m); Sandro Tonali, Newcastle → Tottenham (£100m).
- **4–1 July**: Bazoumana Toure, Hoffenheim → Newcastle (£43m); Michael Svoboda, Venezia → Brighton (£4.3m); Mateus Fernandes, West Ham United → Tottenham (£85m); Hayden Hackney, Middlesbrough → Everton (£16m); Jack Butland, Rangers → Hull (£3m); Marco Palestra, Atalanta → Chelsea (£47m).
- **30–24 June**: Pascal Struijk, Leeds → Brighton (£20m); Frank Onyeka, Brentford → Coventry (£6.8m); Jonah Kusi-Asare, Bayern Munich → Fulham (£5.2m); Piero Hincapie, Bayer Leverkusen → Arsenal (£34.5m); Martin Dubravka, Burnley → Tottenham (free).
- **18–5 June**: Victor Munoz, Osasuna → Liverpool (£34.5m); Jan Paul van Hecke, Brighton → Tottenham (£52m); Costinha, Olympiacos → Brighton (£11m); Marcos Senesi, Bournemouth → Tottenham (free); Ewen Jaouen, Reims → Newcastle (£18.5m); Zadok Yohanna, AIK Stockholm → Brighton (£21.5m); Andy Robertson, Liverpool → Tottenham (free).
- **15 May**: Jannik Schuster, RB Salzburg → Brentford (£12m).

### Source rationale

- Register is intended as a current transfer reference, with separate detailed coverage for more noteworthy arrivals.
- Fetched register does not expose the linked reports’ player roles, projected minutes, FPL prices, rankings, or statistics.
- No charts or analytical tables were present in accessible transfer-register text; date register summarized above.

## Project interpretation

### Decision rules

- Treat transfer fee as squad-change context, never as FPL price or expected points.
- Prioritize follow-up checks where a transfer changes a likely starter, goalkeeper succession, or promoted-team depth chart.
- Recheck destination formation, position classification, minutes, and FPL price before adding a new player to model inputs.
- Recheck outgoing-player vacancies and incoming competition before upgrading incumbent assets.

### Practical implications

- **Promoted-team depth**: Ipswich goalkeeper and attack/defence moves, Coventry centre-back and midfield moves, and Hull goalkeeper/defensive moves warrant lineup review.
- **High-impact destination changes**: Chelsea, Tottenham, Brighton, Manchester United, Manchester City, Aston Villa, and Newcastle have multiple listed changes that may alter minutes and roles.
- **Vacancy checks**: Anderson’s departure from Forest, Rogers’ departure from Villa, Tonali’s departure from Newcastle, and multiple outgoing defenders/goalkeepers create source-led follow-up questions, not immediate recommendations.
- **Defensive competition**: Lacroix, Palestra, Quenda, Vuskovic, Struijk, van Hecke, Robertson, and Senesi transfers may change depth charts; source register alone cannot identify starters.

## Findings

### Evidence

- Source register is current through 30 July and lists the latest move as Lacroix to Chelsea.
- Register covers promoted clubs and established Premier League clubs, with fees ranging from free transfers to high-value deals and several undisclosed/loan moves.
- Page’s stated purpose includes impact on existing FPL assets, but accessible register text does not provide detailed impact analysis.
- No FPL prices, minutes evidence, rankings, or useful player-stat tables are available in fetched text.

### Alternatives

- **Use register as watchlist**: fastest way to identify squad changes; requires separate role and price validation.
- **Use official club announcements**: stronger transfer confirmation; outside this source-only note and not performed here.
- **Ignore transfer fees in projection**: avoids false valuation; still requires destination, role, and minutes refresh.

## Decision

**Verdict**: Use Fantasy Football Scout’s dated register as a transfer-change watchlist, not as a standalone FPL player ranking or price source.

**Recommended action**:
- Refresh player positions, FPL prices, expected minutes, and lineup competition after each material move.
- Follow separate Scout Reports or Moving Target articles where source provides them.
- Keep transfer fee and FPL valuation fields distinct in downstream work.

**Trigger / kill switch**:
- Refresh note when the register adds a new move, changes a fee/status, or reaches a new update cutoff.
- Do not operationalize a new-player recommendation without role and minutes evidence.

## Risks and unknowns

- Page is dynamically refreshed; exact publication date is not exposed in fetched text.
- Transfer claims and fees are unvalidated secondary-source claims.
- Register lacks full player positions, FPL prices, expected minutes, rankings, and projections.
- Loans, free transfers, undisclosed fees, and source naming/fee discrepancies require separate confirmation.
- Transfer window remains open until the source-stated 1 September deadline.
- Destination competition and preseason roles can change after register publication.

## Refresh checklist

- [ ] Recheck source page and register cutoff.
- [ ] Confirm title, update metadata, player names, destinations, and fees.
- [ ] Keep transfer fees distinct from FPL prices.
- [ ] Add role/minutes evidence only from separately identified sources.
- [ ] Keep article claims labeled as unvalidated.
- [ ] Update `Updated`, `Data stamp`, and `Risks`.
- [ ] Delete `.tmp/agent/` scratch before finishing.

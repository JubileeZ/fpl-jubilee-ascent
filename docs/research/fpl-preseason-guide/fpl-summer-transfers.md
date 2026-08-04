# FPL 2026/27 Summer Transfers — Fantasy Football Scout Synthesis

**Updated**: 2026-08-04T23:40:00+07:00
**Data stamp**: Fantasy Football Scout transfer register includes moves announced through 2026-08-04; page reviewed 2026-08-04  
**Season**: 2026/27  
**Status**: Source synthesis · not independently validated  
**Purpose**: Capture confirmed-move register and identify FPL-relevant follow-up questions  
**Scope**: Source-listed Premier League transfers, transfer fees, destination context, and conditional FPL implications. Fees below are reported transfer fees, not FPL player prices. Source text supplied no complete role, minutes, ranking, or projection analysis.  
**Related**: [Pre-season guide directory](fpl-preseason-guide.md) · [Expected Role GW1–5](../expected-role-gw1-5/expected-role-gw1-5.md)

## Sources

- **Primary**: [FPL 2026/27 transfer news: Confirmed summer signings — Fantasy Football Scout](https://www.fantasyfootballscout.co.uk/fpl-2026-27-transfer-news-confirmed-summer-signings) — modified 2026-08-04; register current through 2026-08-04; accessed 2026-08-04; role: transfer register and FPL watchlist source

**Source boundary**: Source claims not independently validated. Fetched page exposes publisher intro and dated transfer register, but no detailed role/minutes or FPL-price data for listed players.

## Agent Prompt

```text
Full redo docs/research/fpl-summer-transfers.md

1. Re-read source URL using Playwright headless browser rendering (`wait_until='domcontentloaded'`) to bypass dynamic loading and account truncation.
2. Confirm title, author, publication/update date, prices, roles, and quoted statistics.
3. Extract 100% of full-page rendered text for all covered players (no partial truncation).
4. Dynamically discover, download, and inspect all image assets in article entry content (`.entry-content img`). Exclude promotional banners, ad images, site logos, author avatars, and decorative photos.
5. Extract and transcribe 100% of relevant statistical data images (team metric tables, player stat graphics, DefCon charts, match logs, fixture tickers) into Markdown tables.
6. Keep Source synthesis strictly separate from Project interpretation.
7. If new primary articles appear under 'BEST FPL PLAYERS FOR 2026/27' on the pre-season guide index, generate dedicated research notes for them following this exact process and update docs/research/fpl-preseason-guide.md.
8. Update Updated ISO timestamp, Data stamp, Sources, Findings, Decision, and Risks.
9. Run pre-commit gate checks (`uv run ruff check .`, `uv run pytest`, `bash tests/verify.sh`); delete `.tmp/agent/` scratch files before finishing.
```

## Method

**Method type**: Primary-source synthesis / dated transfer-register extraction

**Inputs**:
- Playwright rendered Fantasy Football Scout transfer page
- Dynamically fetched article image assets in `.entry-content`

**Procedure**:
1. Record publisher scope and stated deadline.
2. Inspect all article `.entry-content` image assets; filter out non-data promotional graphics, ads, site logos, author gravatars, and decorative photos.
3. Extract source-listed moves by announcement date, destination, and fee.
4. Separate confirmed-move claims from conditional FPL follow-up questions.
5. Flag missing FPL prices, positions, minutes, and rankings.

**Definitions and assumptions**:
- **Transfer fee**: Fee or free/undisclosed value stated by source; not FPL purchase price.
- **Confirmed**: Source labels move as confirmed.
- **FPL implication**: Conditional project question derived from destination and squad change.

**Validation boundary**: Transfer-register synthesis only. No official-club verification, FPL API refresh, lineup check, price lookup, or projection run performed.

## Source synthesis

### Publisher scope

- Summer window open for 2026/27; lists confirmed Premier League moves through Tuesday 1 September deadline.
- Register snapshot contains moves announced from 15 May through 4 August 2026.

### Confirmed-move register

Amounts represent source-reported transfer fees.

- **4–1 August**: Carl Rushworth, Brighton → Coventry (£22m); Gonzalo Garcia, Real Madrid → Fulham (£34.2m); César Palacios, Real Madrid → Fulham (£8.6m); Jordan Henderson, Brentford → Chelsea (free); Lukas Hornicek, Braga → Newcastle (£25.7m); Valentin Barco, Strasbourg → Chelsea (£33.6m); Mamadou Sangare, Lens → Brentford (£38.5m); Danny Welbeck, Brighton → Chelsea (£5m); Antonio Silva, Benfica → Bournemouth (£25.7m).
- **30–29 July**: Maxence Lacroix, Crystal Palace → Chelsea (£52m); Kjell Scherpen, Union Saint-Gilloise → Ipswich (£8.5m).
- **25–23 July**: Daizen Maeda, Celtic → Ipswich (£10m); Aladji Bamba, Monaco → Newcastle (£30m); Elliot Anderson, Nottingham Forest → Manchester City (£116m); Xaver Schlager, RB Leipzig → Nottingham Forest (free); Matt Targett, Newcastle → Hull (free); Christos Tzolis, Club Brugge → Arsenal (£34m); Alejandro Garnacho, Chelsea → Aston Villa (loan).
- **22–20 July**: Issa Diop, Fulham → Ipswich (£8.5m); Kayne van Oevelen, FC Volendam → Ipswich (£3.4m); Morgan Rogers, Aston Villa → Chelsea (£117m); Oscar Zambrano, Maribor → Hull (undisclosed); Abdul Fatawu, Leicester City → Ipswich (£20m); Joao Gomes, Wolverhampton Wanderers → Aston Villa (£38m).
- **17–14 July**: Johan Manzambi, Freiburg → Aston Villa (£50m); Tarik Muharemovic, Sassuolo → Leeds (£34.1m); Aurele Amenda, Frankfurt → Coventry (£17m); Thomas Meunier, Lille → Sunderland (free); Alvaro Rodriguez, Elche → Bournemouth (£25.7m); Youri Tielemans, Aston Villa → Manchester United (£35m); Luka Vuskovic, Tottenham → Brighton (£46m); Karl Darlow, Leeds → Manchester United (free).
- **13–9 July**: Andrey Santos, Chelsea → Manchester United (£48m); Loum Tchaouna, Burnley → Coventry (£20m); Emersonn, Toulouse → Ipswich (£26m); Illan Meslier, Leeds → Arsenal (free); Oscar Mingueza, Celta Vigo → Crystal Palace (free); Sean Steur, Ajax → Newcastle (£23m); Callum Wilson, West Ham United → Brentford (free).
- **8–6 July**: Geovany Quenda, Sporting → Chelsea (£40m); Harry Wilson, Fulham → Leeds (free); Jaidon Anthony, Burnley → Brentford (£15m); Tyrique George, Chelsea → Everton (£18m); Merlin Rohl, Freiburg → Everton (£18m); Sandro Tonali, Newcastle → Tottenham (£100m).
- **4–1 July**: Bazoumana Toure, Hoffenheim → Newcastle (£43m); Michael Svoboda, Venezia → Brighton (£4.3m); Mateus Fernandes, West Ham United → Tottenham (£85m); Hayden Hackney, Middlesbrough → Everton (£16m); Jack Butland, Rangers → Hull (£3m); Marco Palestra, Atalanta → Chelsea (£47m).
- **30–24 June**: Pascal Struijk, Leeds → Brighton (£20m); Frank Onyeka, Brentford → Coventry (£6.8m); Jonah Kusi-Asare, Bayern Munich → Fulham (£5.2m); Piero Hincapie, Bayer Leverkusen → Arsenal (£34.5m); Martin Dubravka, Burnley → Tottenham (free).
- **18–5 June**: Victor Munoz, Osasuna → Liverpool (£34.5m); Jan Paul van Hecke, Brighton → Tottenham (£52m); Costinha, Olympiacos → Brighton (£11m); Marcos Senesi, Bournemouth → Tottenham (free); Ewen Jaouen, Reims → Newcastle (£18.5m); Zadok Yohanna, AIK Stockholm → Brighton (£21.5m); Andy Robertson, Liverpool → Tottenham (free).
- **15 May**: Jannik Schuster, RB Salzburg → Brentford (£12m).

### Source rationale

- Serves as transfer reference; does not expose detailed player roles, projected minutes, FPL prices, rankings, or stats.

## Project interpretation

### Decision rules

- Treat transfer fee as squad context, not FPL price or xP.
- Prioritize checks where transfers affect likely starters, goalkeeper depth, or promoted club depth.
- Verify destination formation, position, minutes, and FPL price before updating model inputs.

### Practical implications

- **Promoted depth**: Ipswich GKs/attack/defence, Coventry CBs/midfield/GK (Rushworth), Hull GK/defence require lineup review.
- **High-impact moves**: Chelsea (Welbeck, Henderson, Barco, Lacroix), Tottenham, Brighton (outgoing Rushworth/Welbeck), Man Utd, Man City, Villa, Newcastle (Hornicek, Bamba) multi-player changes alter roles.
- **Vacancy checks**: Anderson (Forest), Rogers (Villa), Tonali (Newcastle), outgoing defenders/GKs require follow-up.
- **Defensive competition**: Lacroix, Barco, Silva, Palestra, Quenda, Vuskovic, Struijk, van Hecke, Robertson, Senesi alter depth charts.
- **Attacking arrivals**: Fulham (Garcia, Palacios), Brentford (Sangare), Chelsea (Welbeck) add forward/midfield competition.

## Findings

### Evidence

- Register current through 4 August (latest: Rushworth to Coventry).
- Nine new moves since prior capture (1–4 August); Aladji Bamba (24 July) backfilled from source.
- Fees range from free transfers to £117m; covers promoted and established PL clubs.
- FPL prices, minutes evidence, rankings, and player-stat tables absent from fetched text.
- Cross-check against [Expected Role GW1–5](../expected-role-gw1-5/expected-role-gw1-5.md) and positional research notes: prior entries through 30 July aligned (54/54); 10 new/backfilled entries pending cross-check.

## Decision

**Verdict**: Use register as transfer watchlist; validate roles and prices separately.

**Recommended action**:
- Refresh positions, FPL prices, expected minutes, and lineup competition post-move.

**Trigger / kill switch**:
- Refresh note when new moves arrive or window closes (1 September).

## Risks and unknowns

- Fees are unvalidated secondary-source reports.
- Register lacks FPL prices, positions, expected minutes, and projections.

## Refresh checklist

- [x] Recheck source page and register cutoff using Playwright.
- [x] Confirm title, update metadata, player names, destinations, and fees.
- [x] Keep transfer fees distinct from FPL prices.
- [x] Add role/minutes evidence only from separately identified sources.
- [x] Keep article claims labeled as unvalidated.
- [x] Update `Updated`, `Data stamp`, and `Risks`.
- [x] Delete `.tmp/agent/` scratch before finishing.

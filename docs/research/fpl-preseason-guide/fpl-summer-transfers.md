# FPL 2026/27 Summer Transfers — Fantasy Football Scout Synthesis

**Updated**: 2026-08-18T15:05:00+07:00
**Data stamp**: Fantasy Football Scout transfer register includes moves announced through 2026-08-15 (modified 2026-08-17T11:55:58Z); page reviewed 2026-08-17  ; Playwright recheck 2026-08-18: article:modified_time unchanged.
**Season**: 2026/27  
**Status**: Source synthesis · not independently validated  
**Purpose**: Capture confirmed-move register and identify FPL-relevant follow-up questions  
**Scope**: Source-listed Premier League transfers, transfer fees, destination context, and conditional FPL implications. Fees below are reported transfer fees, not FPL player prices. Source text supplied no complete role, minutes, ranking, or projection analysis.  
**Related**: [Pre-season guide directory](fpl-preseason-guide.md) · [Expected Role GW1–5](../gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.md)

## Sources

- **Primary**: [FPL 2026/27 transfer news: Confirmed summer signings — Fantasy Football Scout](https://www.fantasyfootballscout.co.uk/fpl-2026-27-transfer-news-confirmed-summer-signings) — modified 2026-08-17T11:55:58Z; register current through 2026-08-15; accessed 2026-08-17; role: transfer register and FPL watchlist source

**Source boundary**: Source claims not independently validated. Fetched page exposes publisher intro and dated transfer register, but no detailed role/minutes or FPL-price data for listed players.

## Agent Prompt

```text
Full redo docs/research/fpl-preseason-guide/fpl-summer-transfers.md

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

**Outputs**:
- Verified transfer register note `docs/research/fpl-preseason-guide/fpl-summer-transfers.md`

**Data stamp / freshness**:
- Register snapshot contains transfers announced 15 May through 15 August 2026.

## Assumptions & Boundaries

### Exclusions & limits

- Reported transfer fee is not FPL price or projected points.
- Missing contract length or salary data.

### Decision rules

- **Confirmed**: Source labels move as confirmed.
- **FPL implication**: Conditional project question derived from destination and squad change.

**Validation boundary**: Transfer-register synthesis only. No official-club verification, FPL API refresh, lineup check, price lookup, or projection run performed.

## Source synthesis

### Publisher scope

- Summer window open for 2026/27; lists confirmed Premier League moves through Tuesday 1 September deadline.
- Register snapshot contains moves announced from 15 May through 15 August 2026.

### Confirmed-move register

Amounts represent source-reported transfer fees.

- **15 August**: Anan Khalaili, Union Saint-Gilloise → Crystal Palace (£21m); Joe Gelhardt, Leeds United → Hull City (£6.5m); Lucas Gourna-Douath, Red Bull Salzburg → Hull City (£3m).
- **12–9 August**: Lucas Harrington, Colorado Rapids → Hull (£12.6m); Nobel Mendy, Rayo Vallecano → Hull (£21m); Geronimo Rulli, Marseille → Man City (£1.7m); Evann Guessand, Aston Villa → Crystal Palace (loan); Pep Chavarria, Rayo Vallecano → Chelsea (£16.3m); Gustavo Hamer, Sheffield United → Coventry (£6m); Ousmane Diomande, Sporting → Nottingham Forest (£34m); Brennan Johnson, Crystal Palace → Everton (swap); Dwight McNeil, Everton → Crystal Palace (swap); Shea Charles, Southampton → Fulham (£30m); Ronald Araujo, Barcelona → Liverpool (loan); Elliot Stroud, Mjallby → Hull (£3.5m).
- **8–6 August**: Bruno Guimaraes, Newcastle → Arsenal (£75m); Sasa Lukic, Fulham → Ipswich (£9m); Jens Hjerto-Dahl, Tromso → Hull (£10m); Caleb Yirenkyi, Nordsjaelland → Coventry (£23m); James Trafford, Manchester City → Leeds (£45m); Juanlu Sanchez, Sevilla → Bournemouth (£10.4m); Christian Norgaard, Arsenal → Everton (£7m).
- **5–1 August**: Konstantinos Tzolakis, Olympiacos → Hull (£20m); Florentino Luis, Burnley → Ipswich (£16m); Carl Rushworth, Brighton → Coventry (£22m); Gonzalo Garcia, Real Madrid → Fulham (£34.2m); César Palacios, Real Madrid → Fulham (£8.6m); Jordan Henderson, Brentford → Chelsea (free); Lukas Hornicek, Braga → Newcastle (£25.7m); Valentin Barco, Strasbourg → Chelsea (£33.6m); Mamadou Sangare, Lens → Brentford (£38.5m); Danny Welbeck, Brighton → Chelsea (£5m); Antonio Silva, Benfica → Bournemouth (£25.7m).
- **30–29 July**: Maxence Lacroix, Crystal Palace → Chelsea (£52m); Kjell Scherpen, Union Saint-Gilloise → Ipswich (£8.5m).
- **25–23 July**: Daizen Maeda, Celtic → Ipswich (£10m); Aladji Bamba, Monaco → Newcastle (£30m); Hidemasa Morita, Sporting → Hull (£free); Elliot Anderson, Nottingham Forest → Manchester City (£116m); Xaver Schlager, RB Leipzig → Nottingham Forest (free); Matt Targett, Newcastle → Hull (free); Christos Tzolis, Club Brugge → Arsenal (£34m); Alejandro Garnacho, Chelsea → Aston Villa (loan).
- **22–20 July**: Issa Diop, Fulham → Ipswich (£8.5m); Kayne van Oevelen, FC Volendam → Ipswich (£3.4m); Morgan Rogers, Aston Villa → Chelsea (£117m); Oscar Zambrano, Maribor → Hull (undisclosed); Abdul Fatawu, Leicester City → Ipswich (£20m); Joao Gomes, Wolverhampton Wanderers → Aston Villa (£38m).
- **17–14 July**: Johan Manzambi, Freiburg → Aston Villa (£50m); Tarik Muharemovic, Sassuolo → Leeds (£34.1m); Aurele Amenda, Frankfurt → Coventry (£17m); Thomas Meunier, Lille → Sunderland (free); Alvaro Rodriguez, Elche → Bournemouth (£25.7m); Youri Tielemans, Aston Villa → Manchester United (£35m); Luka Vuskovic, Tottenham → Brighton (£46m); Karl Darlow, Leeds → Manchester United (free).
- **13–9 July**: Andrey Santos, Chelsea → Manchester United (£48m); Loum Tchaouna, Burnley → Coventry (£20m); Emersonn, Toulouse → Ipswich (£26m); Illan Meslier, Leeds → Arsenal (free); Oscar Mingueza, Celta Vigo → Crystal Palace (free); Sean Steur, Ajax → Newcastle (£23m); Callum Wilson, West Ham United → Brentford (free).
- **8–6 July**: Geovany Quenda, Sporting → Chelsea (£40m); Harry Wilson, Fulham → Leeds (free); Jaidon Anthony, Burnley → Brentford (£15m); Tyrique George, Chelsea → Everton (£18m); Merlin Rohl, Freiburg → Everton (£18m); Sandro Tonali, Newcastle → Tottenham (£100m).
- **4–1 July**: Bazoumana Toure, Hoffenheim → Newcastle (£43m); Michael Svoboda, Venezia → Brighton (£4.3m); Mateus Fernandes, West Ham United → Tottenham (£85m); Hayden Hackney, Middlesbrough → Everton (£16m); Jack Butland, Rangers → Hull (£3m); Marco Palestra, Atalanta → Chelsea (£47m).
- **30–24 June**: Pascal Struijk, Leeds → Brighton (£20m); Frank Onyeka, Brentford → Coventry (£6.8m); Jonah Kusi-Asare, Bayern Munich → Fulham (£5.2m); Piero Hincapie, Bayer Leverkusen → Arsenal (£34.5m); Martin Dubravka, Burnley → Tottenham (free).
- **18–5 June**: Victor Munoz, Osasuna → Liverpool (£34.5m); Jan Paul van Hecke, Brighton → Tottenham (£52m); Costinha, Olympiacos → Brighton (£11m); Marcos Senesi, Bournemouth → Tottenham (free); Ewen Jaouen, Reims → Newcastle (£18.5m); Zadok Yohanna, AIK Stockholm → Brighton (£21.5m); Andy Robertson, Liverpool → Tottenham (free).
- **15 May**: Jannik Schuster, RB Salzburg → Brentford (£12m).

## Project interpretation

### Decision rules

- Treat transfer fee as squad context, not FPL price or xP.
- Prioritize checks where transfers affect likely starters, goalkeeper depth, or promoted club depth.
- Verify destination formation, position, minutes, and FPL price before updating model inputs.

### Practical implications

- **Promoted depth**: Ipswich GKs/attack/defence/MID (Lukic, Florentino Luis, Scherpen, Maeda, Diop), Coventry CBs/midfield/GK (Yirenkyi, Rushworth, Amenda, Tchaouna, Onyeka, Hamer), Hull GK/defence/midfield/attack (Gelhardt, Gourna-Douath, Harrington, Mendy, Stroud, Hjerto-Dahl, Tzolakis, Morita, Targett, Butland, Zambrano) require lineup review.
- **High-impact moves**: Crystal Palace (Khalaili, Guessand loan, McNeil swap, Mingueza), Arsenal (Bruno Guimaraes, Tzolis, Hincapie, Meslier), Chelsea (Welbeck, Henderson, Barco, Lacroix, Rogers, Quenda, Palestra, Chavarria), Leeds (Trafford, Muharemovic, H. Wilson), Tottenham (Tonali, M. Fernandes, Struijk, Senesi, Robertson), Man Utd (Tielemans, Santos, Darlow), Bournemouth (Juanlu Sanchez, A. Silva, A. Rodriguez), Liverpool (Araujo loan, Munoz), Man City (Rulli), Forest (Diomande), Fulham (Shea Charles), Everton (Johnson swap).
- **Vacancy checks**: Bruno Guimaraes / Tonali departures from Newcastle; Anderson departure from Forest; Rogers departure from Villa.
- **Defensive competition**: Trafford at Leeds, Tzolakis at Hull, Rushworth at Coventry, Juanlu at Bournemouth alter starter hierarchies.

## Findings

### Evidence

- Register current through 15 August (latest: Khalaili to Palace, Gelhardt and Gourna-Douath to Hull, Harrington/Mendy to Hull, Rulli to Man City, Chavarria to Chelsea, Hamer to Coventry, Diomande to Forest, Johnson/McNeil swap, Shea Charles to Fulham, Araujo loan to Liverpool, Stroud to Hull).
- Total of 33 August moves recorded (1–15 August).
- Fees range from free transfers to £117m; covers promoted and established PL clubs.
- FPL prices, minutes evidence, rankings, and player-stat tables absent from fetched text.
- Cross-check against [Expected Role GW1–5](../gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.md): starter statuses for Trafford (Leeds #1), Tzolakis (Hull #1), Rushworth (Coventry #1), and Norgaard (Everton pivot) verified.

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

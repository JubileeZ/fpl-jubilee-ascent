# Ownership Value Explorer (Full Season & Early Chip Matrix)

**Updated**: 2026-08-14T19:00:00+07:00  
**Data stamp**: Stage 2 ADR-0014 rates 2026-08-14; fixtures GW1–38; `selected_by_percent` pricing stamp 2026-07-29; Stage 3 MILP S13 winners  
**Season**: 2026/27 · default horizon GW1–38 (GW1–6 toggle)  
**Status**: Active Research Model & Visualization Suite  
**Purpose**: Interactive evaluation of projected rate (xP/90) against ownership popularity across full season and GW1–6 windows, sized by expected minutes, with position/club/price filters and strategic chip overlays.  
**Scope**: XI Contention rates from Stage 2; Ownership = FPL `selected_by_percent` (not EO); full season vs GW1–6 window; overlay markers for S13 (BB2+TC3 Pre-WC winner), WC4 Core (Opt1 optimal post-WC squad), S5 (BB1+TC3), S1 (FH3), and User squad.  
**Related**: [First-Half Chip Strategy](../fpl-first-half-chip-strategy/fpl-first-half-chip-strategy.md) · [Expected Stats (Stage 2)](../gw1-6-preseason-pipeline/02-expected-stats-gw1-5/expected-stats-gw1-5.md) · [GW1–6 Chip Matrix](../gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6-chip-wc4-squads.md) · [Downstream refresh](../gw1-6-preseason-pipeline/refresh_downstream.py) · [Project](project_season_points.py) · [Plot](plot_ownership_value_explorer.py)  
**Artifacts**:
- [Season projections CSV](../../../data/research/ownership-value-explorer/season_projections.csv)
- [Metrics CSV](../../../data/research/ownership-value-explorer/ownership_value_metrics.csv)
- [Interactive HTML](../../../data/research/ownership-value-explorer/ownership_value_explorer.html)

---

## Open & use

### Open the interactive chart

Artifact path (repo root):

`data/research/ownership-value-explorer/ownership_value_explorer.html`

**From terminal** (repo root):

```bash
xdg-open data/research/ownership-value-explorer/ownership_value_explorer.html   # Linux
open data/research/ownership-value-explorer/ownership_value_explorer.html       # macOS
```

**From the IDE**: open that file in Cursor/VS Code → right-click → **Reveal in File Explorer** / **Open with Live Server**, or use editor browser preview.

**From file manager**: double-click `ownership_value_explorer.html` in `data/research/ownership-value-explorer/`.

Requires network on first load (Plotly CDN). Refresh browser tab when HTML regenerated.

### Read the chart

- **X-axis**: FPL ownership % (`selected_by_percent`) — raw ownership, not EO.
- **Y-axis**: xP per 90 for selected horizon (default **GW1–38** full season; toggle to **GW1–6** window).
- **Marker size**: average expected minutes over active horizon.
- **Colour**: position (GKP: blue `#4c78a8` · DEF: orange `#f58518` · MID: green `#54a24b` · FWD: red `#e45756`).
- **Text labels**: player names when avg xMins ≥ 60, or when row matches **Player list** search.
- **Overlay markers**:
  - `★` (gold star / amber border) = **S13 Pre-WC Squad** (BB2 + TC3 Pre-Wildcard sprint; top EV strategy at 340.14 xP).
  - `⬡` (hexagon / sky blue border) = **WC4 Core Squad** (Stage 3 WC4 Opt1 optimal 15 post-WC lineup).
  - `■` (square / purple border) = **S5 Pre-WC Squad** (BB1 + TC3 Pre-Wildcard).
  - `▲` (triangle-up / teal border) = **S1 Pre-FH Squad** (BB1 + FH3).
  - `◆` (diamond / black border) = **User squad** (`data/processed/user_picks.parquet`).
- **Player table**: complete contention list under chart. Search by player name, club, or expected role. **On chart** shows filter status. Off-chart players display reasons (e.g. xMins floor). Search highlights and forces marker onto chart. Squad overlay badges list membership tags (S13, WC4, S5, S1, User).

### Filters

| Control | What it does |
|---------|----------------|
| **Horizon** | `GW1–38 season` (default) or `GW1–6 window` for early-chip sprint comparison |
| **Position** | Checkbox per position GKP / DEF / MID / FWD |
| **Club** | Search box narrows visible clubs; **All** / **None** buttons toggle visible clubs; individual club checkboxes |
| **Price (£m)** | Min / max price band range |
| **Avg xMins floor** | Hide low-minute spikes from chart (default **45.0** mins; slider 0–90). Full table still retains all players. |
| **Overlays** | Toggle checkboxes for ★ S13, ⬡ WC4 Core, ■ S5, ▲ S1, ◆ User squad; **Only overlay players** filters chart to flagged squad members |
| **Player list** | Interactive search filtering table and pinning matching players to chart |

---

## Strategy Integration: Pre-WC Sprint & Post-WC4 Core

The explorer allows managers to evaluate both phases of the **BB2, TC3, WC4** strategy (Scenario 13):

### 1. Pre-WC Sprint Differentials (GW1–3 BB2 + TC3 Target)
- **Concept**: In S13, managers field a 15-man active squad for Bench Boost in GW2, Triple Captain Haaland in GW3 (home vs Coventry), and liquidate short-term picks in GW4 Wildcard.
- **High-Value Differentials**:
  - **Vuskovic (BHA DEF £5.0m, 3.0% own)**: 5.96 season xP/90; 6.02 GW1–6 xP/90; elite entry for GW1–3 Brighton defense.
  - **Wieffer (BHA DEF £5.0m, 0.3% own)**: 5.39 season xP/90; 5.44 GW1–6 xP/90; ultra-low owned enabler.
  - **Maguire (MUN DEF £5.0m, 4.3% own)**: Nailed starter for United opening run (FUL GW1, HUL GW2).
  - **Ballard (SUN DEF £5.0m, 1.4% own)**: High early fixture security for BB2 bench support.
  - **Thomas-Asante (COV FWD £5.0m, 0.4% own)**: GW2 fixture target vs Hull; cheap starting forward.
  - **Schade (BRE MID £6.0m, 1.2% own)** & **O.Dango (BRE MID £6.5m, 0.1% own)**: Low-owned Brentford attackers for early fixture targeting.
  - **E.Le Fée (SUN MID £6.0m, 0.4% own)**: 4.30+ early xP per match.

### 2. Post-WC4 Core Squad Structure (GW4–6 Foundation)
- **Concept**: In GW4 Wildcard (Opt1), squad permanently restructures into Arsenal/Chelsea/Everton/Liverpool fixture swings while shifting bench funds into starting XI fire-power.
- **Core 15 Roster & Ownership Distribution**:
  - **Anchors / Template Premiums**:
    - **Haaland (MCI FWD £15.5m, 75.1% own)**: 6.02 xP/90; indispensable captaincy anchor.
    - **Palmer (CHE MID £9.5m, 47.9% own)**: Chelsea fixture swing (HUL GW4, BRE GW5, BOU GW6).
    - **Gabriel (ARS DEF £8.0m, 25.7% own)**: 6.02 xP/90; Arsenal defensive anchor (SUN GW4, BHA GW5, LEE GW6).
  - **High-Leverage Core Differentials**:
    - **Tzolis (ARS MID £6.5m, 1.6% own)**: 6.34 season xP/90; second-highest rate among regular midfielders.
    - **Sarr (CRY MID £6.5m, 2.3% own)**: 5.22 GW4 xP; Palace talisman.
    - **Ndiaye (EVE MID £6.0m, 2.1% own)**: Everton attack talisman.
    - **Tarkowski (EVE DEF £6.0m, 1.4% own)**: 4.90+ post-WC defensive projections.
    - **Thiaw (NEW DEF £5.0m, 0.5% own)**: Newcastle defensive value.
    - **Raya (ARS GKP £6.0m, 9.4% own)** & **Kinsky (TOT GKP £4.5m, 1.7% own)**: Stage 3 optimal GKP pairing.
    - **Slater (HUL MID £4.5m, 0.2% own)** & **Walle Egeli (IPS FWD £4.5m, 1.7% own)**: Ultra-budget bench enablers freeing capital for starting XI.

---

## Sources

- Rates: `data/research/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/expected-stats-gw1-5.csv`
- Fixtures / clubs / players: `data/processed/`
- Availability priors: `docs/research/gw1-6-preseason-pipeline/availability_priors.py`
- Simulation overlays: `data/research/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6_wc4_simulation.csv`
- Authenticated picks: `data/processed/user_picks.parquet`

---

## Findings

- Default view is **GW1–38** differentials (own% vs season xP/90).
- Contention list contains 357 players; chart default floor 45.0 xMins plots 227 regular starters.
- S13 Pre-WC sprint features high-ceiling low-owned differential assets (Vuskovic 3.0%, Wieffer 0.3%, Thomas-Asante 0.4%, E.Le Fée 0.4%).
- WC4 Core squad pairs massive template anchors (Haaland 75.1%, Palmer 47.9%, Gabriel 25.7%) with low-owned value drivers (Tzolis 1.6%, Sarr 2.3%, Ndiaye 2.1%, Tarkowski 1.4%, Thiaw 0.5%).
- Low-xMins cameo players inflate raw xP/90 — maintain floor ≥ 45 unless explicitly analyzing cameo efficiency.

---

## Decision

**Verdict**: Deploy the Ownership Value Explorer to cross-validate candidate transfers against ownership curves:
1. Target high-xP/90 low-owned stars (★ S13) for GW1–3 pre-WC sprint.
2. Verify structural foundation against ⬡ WC4 Core post-wildcard template.
3. Compare User Squad (◆) against both optimal curves to eliminate dead weight and maximize expected value spread.

---

## Verification & Delivery

- Generated artifacts: `season_projections.csv`, `ownership_value_metrics.csv`, `ownership_value_explorer.html`.
- Automated test validation: `tests/test_ownership_value_explorer.py`.

# Ownership Value Explorer (Full Season)

**Updated**: 2026-08-18T15:05:00+07:00  
**Data stamp**: Stage 2 ADR-0014 rates 2026-08-18 (575 players); FPL API refresh 2026-08-18; Stage 3 GW1 BB + WC4 364.21 xP  
**Season**: 2026/27 · default horizon GW1–38 (GW1–6 toggle)  
**Status**: Active Research Model & Visualization Suite  
**Purpose**: Interactive evaluation of projected rate (xP/90) against ownership popularity across full season and GW1–6 windows, sized by expected minutes, with position/club/price filters and strategic chip overlays.  
**Scope**: 575 FPL players from Stage 2; Ownership = FPL `selected_by_percent` (not EO); full season vs GW1–6 window; overlay markers for GW1 BB (Pre-WC squad), WC4 Core, and User squad.  
**Related**: [First-Half Chip Strategy](../fpl-first-half-chip-strategy/fpl-first-half-chip-strategy.md) · [Expected Stats (Stage 2)](../gw1-6-preseason-pipeline/02-expected-stats-gw1-5/expected-stats-gw1-5.md) · [GW1–6 Chip Strategy](../gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6-chip-wc4-squads.md) · [Downstream refresh](../gw1-6-preseason-pipeline/refresh_downstream.py) · [Project](project_season_points.py) · [Plot](plot_ownership_value_explorer.py)  
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
  - `★` (gold star / amber border) = **GW1 BB Pre-WC Squad** (GW1 Bench Boost sprint; 15 starters scoring, 190.84 xP GW1–3).
  - `⬡` (hexagon / sky blue border) = **WC4 Core Squad** (Stage 3 WC4 optimal 15 post-WC lineup, 173.37 xP GW4–6).
  - `■` (square / purple border) = **S5 Pre-WC Squad** (historical 16-scenario BB1 + TC3; not live Stage 3).
  - `▲` (triangle-up / teal border) = **S1 Pre-FH Squad** (historical 16-scenario BB1 + FH3 tag in the CSV; live Canonical S1 is the ★ GW1 BB overlay).
  - `◆` (diamond / black border) = **User squad** (`data/processed/user_picks.parquet`).
- **Player table**: complete player list (**575** players) under chart. Search by player name, club, or expected role. **On chart** shows filter status. Off-chart players display reasons (e.g. xMins floor). Search highlights and forces marker onto chart. Squad overlay badges list membership tags (GW1 BB, WC4, historical S5/S1, User).

### Filters

| Control | What it does |
|---------|----------------|
| **Horizon** | `GW1–38 season` (default) or `GW1–6 window` for early-chip sprint comparison |
| **Position** | Checkbox per position GKP / DEF / MID / FWD |
| **Club** | Search box narrows visible clubs; **All** / **None** buttons toggle visible clubs; individual club checkboxes |
| **Price (£m)** | Min / max price band range |
| **Avg xMins floor** | Hide low-minute spikes from chart (default **45.0** mins; slider 0–90). Full table retains all **575** players. |
| **Overlays** | Toggle checkboxes for ★ GW1 BB (Pre-WC), ⬡ WC4 Core, ■ S5, ▲ S1, ◆ User squad; **Only overlay players** filters chart to flagged squad members |
| **Player list** | Interactive search filtering table and pinning matching players to chart |

### Metric Definitions & Direction

| Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|---|---|---|---|---|---|
| **Projected Rate** | `xP/90` | $\frac{\text{Horizon xP}}{\text{Expected Minutes}} \times 90$ | Higher is better $\uparrow$ | **$\ge 5.0$** (Enabler) / **$\ge 7.0$** (Premium) | Normalized per-match point generation rate accounting for role and opponents. |
| **Ownership Popularity** | `Ownership %` | `selected_by_percent` from FPL API | Context-dependent | **$< 5.0\%$** (Diff) / **$> 30.0\%$** (Template) | Proportion of FPL managers owning the player. Identifies leverage opportunities. |
| **Differential Leverage** | `Diff Value` | $\text{High } xP/90 \text{ with Low Ownership } (<5\%)$ | Higher is better $\uparrow$ | **$xP/90 \ge 5.5$, Own $< 5\%$** | Assets positioned in the top-left quadrant of the chart providing maximum rank climb potential. |
| **Average Expected Minutes** | `avg_xMins` | $\frac{1}{N}\sum_{t=1}^N \text{Expected Minutes}_t$ | Higher is better $\uparrow$ | **$\ge 75.0\text{ mins}$** (Starter) / **$90.0\text{ mins}$** (Nailed) | Starting security indicator. Low minutes ($<45\text{m}$) filter out per-90 sample distortions. |

---

## Strategy Integration: Pre-WC Sprint & Post-WC4 Core

The explorer allows managers to evaluate both phases of the **GW1 BB + WC4** canonical strategy (Stage 3):

### 1. Pre-WC Sprint Differentials (GW1–3 BB1 Target, 190.84 xP)
- **Concept**: In GW1 Bench Boost, managers field a 15-man active squad scoring across all positions in GW1, lock transfers across GW1–3, and liquidate short-term picks in GW4 Wildcard.
- **High-Value Differentials & Anchors**:
  - **Tzolis (ARS MID £6.5m, 1.4% own)**: 6.31 season xP/90; 6.30 GW1–6 xP/90; elite differential midfielder for Arsenal opening run.
  - **Gabriel (ARS DEF £8.0m, 25.7% own)**: 6.00 season xP/90; 6.00 GW1–6 xP/90; premier defensive anchor.
  - **Vuskovic (BHA DEF £5.0m, 2.8% own)**: 5.89 season xP/90; 5.97 GW1–6 xP/90; elite entry for Brighton defense.
  - **Haaland (MCI FWD £15.5m, 75.1% own)**: 5.87 season xP/90; 5.84 GW1–6 xP/90; essential captaincy anchor.
  - **Isak (LIV FWD £9.0m, 11.6% own)**: 5.48 season xP/90; 5.69 GW1–6 xP/90; Liverpool attack centerpiece.
  - **Wieffer (BHA DEF £5.0m, 0.3% own)**: 5.34 season xP/90; 5.41 GW1–6 xP/90; ultra-low owned Brighton defensive enabler.
  - **Maeda (IPS MID £5.5m, 0.4% own)**: 5.34 season xP/90; 5.42 GW1–6 xP/90; differential Ipswich attacker.
  - **Núñez (IPS MID £5.0m, 0.2% own)**: 4.93 season xP/90; 5.00 GW1–6 xP/90; budget midfield enabler.
  - **Trafford (MCI GKP £5.0m, 1.5% own)**: 4.89 season xP/90; 4.88 GW1–6 xP/90; Manchester City starting goalkeeper.
  - **Schade (BRE MID £6.0m, 2.3% own)** & **O.Dango (BRE MID £6.5m, 1.3% own)**: Low-owned Brentford attackers for early fixture targeting.
  - **Thiago (BRE FWD £8.0m, 15.9% own)**: 4.69 season xP/90; Brentford forward option.
  - **Ballard (SUN DEF £5.0m, 3.2% own)**: 4.60 season xP/90; 4.73 GW1–6 xP/90; Sunderland fixture target.
  - **Maguire (MUN DEF £5.0m, 7.5% own)**: 4.59 season xP/90; 4.72 GW1–6 xP/90; United opening run.
  - **Sels (NFO GKP £5.0m, 1.4% own)**: 4.07 season xP/90; 4.11 GW1–6 xP/90; Forest rotation goalkeeper.

### 2. Post-WC4 Core Squad Structure (GW4–6 Foundation, 173.37 xP)
- **Concept**: In GW4 Wildcard, squad permanently restructures into Arsenal/Chelsea/Everton/Brighton fixture swings while shifting bench funds into starting XI firepower, banking 4 FTs into GW6.
- **Core 15 Roster & Ownership Distribution**:
  - **Anchors / Template Premiums**:
    - **Calafiori (ARS DEF £5.5m, 14.5% own)**: 6.61 season xP/90; top-ranked defender rate across full season.
    - **Gabriel (ARS DEF £8.0m, 25.7% own)**: 6.00 season xP/90; Arsenal defensive pillar.
    - **Haaland (MCI FWD £15.5m, 75.1% own)**: 5.87 season xP/90; essential captaincy anchor.
    - **Isak (LIV FWD £9.0m, 11.6% own)**: 5.48 season xP/90; Liverpool forward anchor.
    - **Sarr (CRY MID £6.5m, 10.5% own)**: 4.86 season xP/90; Palace talisman.
  - **High-Leverage Core Differentials & Enablers**:
    - **Tzolis (ARS MID £6.5m, 1.4% own)**: 6.31 season xP/90; second-highest rate among regular midfielders.
    - **Vuskovic (BHA DEF £5.0m, 2.8% own)** & **Wieffer (BHA DEF £5.0m, 0.3% own)**: Brighton defensive foundation.
    - **Enzo (CHE MID £7.0m, 5.4% own)**: 4.82 season xP/90; Chelsea fixture swing (HUL GW4, BRE GW5, BOU GW6).
    - **Tarkowski (EVE DEF £6.0m, 9.8% own)**: 4.63 season xP/90; 4.81 GW1–6 xP/90; Everton defensive value.
    - **Trafford (MCI GKP £5.0m, 1.5% own)** & **Roefs (SUN GKP £5.0m, 5.4% own)**: Stage 3 optimal GKP pairing.
    - **Walle Egeli (IPS FWD £4.5m, 2.4% own)**, **Andrews (COV MID £4.5m, 0.7% own)**, **Johnson (CRY MID £6.0m, 0.2% own)**: Essential bench enablers freeing capital for starting XI.

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
- Contention list contains **575** players; chart default floor 45.0 xMins plots regular/nailed starters.
- GW1 BB Pre-WC sprint features high-ceiling low-owned differential assets (Tzolis 1.4%, Vuskovic 2.8%, Wieffer 0.3%, Maeda 0.4%, Núñez 0.2%, Ballard 3.2%).
- WC4 Core squad pairs template anchors (Haaland 75.1%, Gabriel 25.7%, Calafiori 14.5%, Isak 11.6%, Sarr 10.5%) with low-owned value drivers (Tzolis 1.4%, Vuskovic 2.8%, Wieffer 0.3%, Enzo 5.4%, Roefs 5.4%, Andrews 0.7%, Johnson 0.2%).
- Low-xMins cameo players inflate raw xP/90 — maintain floor ≥ 45 unless explicitly analyzing cameo efficiency.

---

## Decision

**Verdict**: Deploy the Ownership Value Explorer to cross-validate candidate transfers against ownership curves:
1. Target high-xP/90 low-owned stars (★ GW1 BB) for GW1–3 pre-WC sprint.
2. Verify structural foundation against ⬡ WC4 Core post-wildcard template.
3. Compare User Squad (◆) against both optimal curves to eliminate dead weight and maximize expected value spread.

---

## Verification & Delivery

- Generated artifacts: `season_projections.csv`, `ownership_value_metrics.csv`, `ownership_value_explorer.html`.
- Automated test validation: `tests/test_ownership_value_explorer.py`.

# Research Index & Guidelines

**Updated**: 2026-08-22T17:59:00+07:00
**Status**: Live index. Active topics tracked below.

---

## Active Research Index

- **First-Half GKP Rotation Pairs (GW1–19)**: [Note](gkp-fdr-rotation-gw1-19/gkp-fdr-rotation-gw1-19.md) · [Summary](gkp-fdr-rotation-gw1-19/gkp_rotation_pairs_summary.csv) `total_mod_fdr` · [Starting GKPs](gkp-fdr-rotation-gw1-19/starting_gkps_gw1_19.csv) · [Schedule Picks](gkp-fdr-rotation-gw1-19/gw1_19_rotation_schedule_picks.csv)

---

## Archived (2026/27 preseason)

Moved 2026-08-21. Notes + companions colocated under `docs/archive/<topic-slug>/`. Frozen identities below.

- **Operational First-Half Plan**: [Note](../archive/gw1-19-operational-plan/gw1-19-operational-plan.md) · [Summary](../archive/gw1-19-operational-plan/operational_summary.csv) `frozen_19gw_xi_xp`
- **First-Half Chip Path**: [Note](../archive/gw1-19-first-half-chip-path/gw1-19-first-half-chip-path.md) · [Summary](../archive/gw1-19-first-half-chip-path/first_half_summary.csv) · [Select 11](../archive/gw1-19-first-half-chip-path/first_half_select_11.csv)
- **GW1–6 Preseason Pipeline**:
  - [Master README](../archive/gw1-6-preseason-pipeline/README.md)
  - [Stage 1 Expected Role](../archive/gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.md) · [CSV](../archive/gw1-6-preseason-pipeline/01-expected-role-gw1-5/expected-role-gw1-5.csv) (production Expected Role Prior ingest)
  - [Stage 2 Expected Stats](../archive/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/expected-stats-gw1-5.md)
  - [Stage 3 Canonical Chip Path](../archive/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6-chip-wc4-squads.md) · [Summary](../archive/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6_wc4_summary.csv) `total_6gw_xp` **383.76**
- **Ownership Value Explorer (research HTML)**: [Note](../archive/ownership-value-explorer/ownership-value-explorer.md) · [HTML](../archive/ownership-value-explorer/ownership_value_explorer.html). Product view = dashboard Ownership Explorer.
- **Pre-Season Source Directory**: [Index](../archive/fpl-preseason-guide/fpl-preseason-guide.md)
- **Defensive Architecture (DCS)**: [Note](../archive/defensive-fixture-rotation/defensive-fixture-rotation.md) · [GKP Strategy](../archive/defensive-fixture-rotation/gkp_strategy_comparison.csv)
- **First-Half Chip Strategy (source synthesis)**: [Note](../archive/fpl-first-half-chip-strategy/fpl-first-half-chip-strategy.md)
- **Set-Piece Analysis**: [Note](../archive/fpl-set-piece-analysis/fpl-set-piece-analysis.md)
- Earlier GKP/DEF RQI notes: [gkp-fixture-rotation](../archive/gkp-fixture-rotation/gkp-fixture-rotation.md) · [def-fixture-rotation](../archive/def-fixture-rotation/def-fixture-rotation.md)
- Catalog: [docs/archive/index.md](../archive/index.md)

---

## Research Conventions & Standards

- **Colocate**: note, runners, and companion CSV/HTML live in `docs/research/<topic-slug>/`. No `data/research/`. No research companions under `data/archive/`.
- **Live root**: `docs/research/` holds `INDEX.md`, `template/`, and active topic folders only. No loose notes beside INDEX.
- **Archive**: move the whole topic folder to `docs/archive/<topic-slug>/`. Companions travel with it. Leave a pointer here.
- **Season ingest**: `data/archive/YYYY-YY/` only (raw/processed FPL snapshots). Not research CSVs.
- **Reports**: `data/reports/` for solver/tool execution outputs.
- **Filename**: stable topic slugs; no date prefixes. Start from `docs/research/template/research-note.md`.
- **Required sections**: `Updated`, `Data stamp`, `Season`, `Purpose`, `Sources`, `Agent Prompt`, `Method`, `Findings`, `Decision`, `Risks and unknowns`.
- **Timestamps**: `Updated` = note revision (ISO 8601 + timezone). `Data stamp` = evidence cutoff. No duplicate `Last update`.
- **Artifact**: link companions in the note header; same-folder relative path.
- **Evidence**: keep `Source synthesis` separate from `Project interpretation`. Label unvalidated claims.
- **Metrics**: every quantitative note includes `### Metric Definitions & Direction` (Definition/Formula, Direction, Ideal Benchmark, Description).
- **Agent Prompt**: inputs, refresh steps, stable output path in the topic folder, scratch cleanup.
- **Figures**: caches of named companion CSV cells. Prompt names path + column (e.g. `gw1-6_wc4_summary.csv` `total_6gw_xp`), not a numeric snapshot.

---

## Master Metric Definitions & Interpretation Reference

| Domain / Area | Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|---|---|---|---|---|---|---|
| **Rotation** | **Defensive Composite Score** | `DCS` | $0.60 \times S_{\text{Score}} + 0.40 \times S_{\text{Risk}}$ | Higher is better $\uparrow$ | **$\ge 80.0$ / 100** | Live ranking metric for a Defensive Rotation Set. Replaces RQI / OC-RQI. Not the Canonical Preseason Chip Path 15-man keepers. |
| **Rotation** | **Opportunity-Cost Adjusted Score** | `OC-Score` | $\frac{\text{Rotated xP}}{N} - \gamma \times (\text{Spend} - \text{Floor})$ | Higher is better $\uparrow$ | **$> 6.00$** (GKP) / **$> 18.00$** (DEF) | Points factor inside DCS. $\gamma = 0.2944\text{ xP/£1.0m/GW}$. Floors: GKP £8.5m, DEF £20.0m, backline £28.5m. |
| **Rotation** | **Fixture Overlap Index** | `FOI` | $\frac{1}{T}\sum (1 - p_{\text{cs1}})(1 - p_{\text{cs2}})$ | Lower is better $\downarrow$ | **$< 0.50$** (Min $\approx 0.40$) | Probability of joint clean-sheet failure across paired goalkeepers. Lower values guarantee schedule diversification. |
| **Rotation** | **FDR Schedule Correlation** | $r$ / `avg_corr` | Pearson correlation between club FDR sequences across gameweeks | Lower is better $\downarrow$ (Negative) | **$r \le -0.10$** | Measures fixture alignment. Negative correlation ensures one team has an easy fixture when the other faces a top-6 opponent. |
| **Rotation** | **Zero-Difficult Gameweeks** | `Zero-Diff %` | % of GWs where all started assets face FDR $\le 3$ | Higher is better $\uparrow$ | **$100.0\%$** | Completely avoids fielding starters against FDR $\ge 4$ elite attacks. |
| **Rotation** | **FDR Selection Loss** | `FDR Loss` | $\sum \text{FDR}(\max xP) - \sum \text{FDR}(\min \text{FDR})$ | Lower is better $\downarrow$ | **$0.00$** | Penalty in fixture ease incurred by following unconditional $\max(xP)$ over legacy minimum-FDR heuristic. |
| **Rotation** | **Rotated / Effective FDR** | `Rot FDR` | Average weekly fixture difficulty rating across started slots | Lower is better $\downarrow$ | **$\le 2.40$** | Benchmark baseline for unrotated schedule is $3.00$; rotation targets $\le 2.40$. |
| **Rotation** | **Rotated Expected Points** | `Rotated xP` | $\sum_{t=1}^N \max_{i \in \text{squad}} xP_{i,t}$ | Higher is better $\uparrow$ | Maximized | Sum of weekly projected points under optimal starting selection. |
| **Rotation** | **Expected Clean Sheets** | `Exp CS` / $xCS$ | $\sum_{t=1}^N e^{-\lambda_{i^*,t}}$ where $\lambda$ = expected goals conceded | Higher is better $\uparrow$ | **$\ge 14.0$ / season** (or $\ge 2.20$ in GW1–6) | Poisson-derived clean-sheet expectation for the started goalkeeper or defense. |
| **Chip Strategy** | **Scenario Expected Points** | `Total xP` | Cumulative projected points across GW1–6 under Canonical Preseason Chip Path | Higher is better $\uparrow$ | **383.76 xP** (`gw1-6_wc4_summary.csv` `total_6gw_xp`) | MILP-optimized points under locked GW1–3 Bench Boost, GW4 Wildcard, and GW5 roll. Historical 16-scenario S13 $340.14$ is not this experiment. |
| **Chip Strategy** | **Frozen XI First-Half xP** | `frozen_19gw_xi_xp` | Sum of Operational First-Half Plan week scores (frozen owned 15s; August FH snapshot at GW12) | Higher is better $\uparrow$ | `operational_summary.csv` `frozen_19gw_xi_xp` | User playbook. Not First-Half `total_19gw_xp` (greedy FTs). |
| **Chip Strategy** | **Value Over Chip Baseline** | `VoC` | $xP(\text{Scenario } k) - xP(\text{No Chip Baseline})$ | Higher is better $\uparrow$ | **$\ge +12.0\text{ xP}$** | Net points gained by deploying specific chip combinations early vs holding. |
| **Chip Strategy** | **Auto-Sub Expected Value** | `Auto-sub EV` | $+12\% \times xP(\text{Def 4}) + 3\% \times xP(\text{Def 5})$ | Higher is better $\uparrow$ | Inherent buffer | Expected points harvested from benched defenders when starters are unexpectedly benched or rested. |
| **Ownership** | **Projected Rate** | `xP/90` | Expected points per 90 minutes normalized by role and fixture | Higher is better $\uparrow$ | **$\ge 5.0$** (Enabler) / **$\ge 7.0$** (Premium) | Normalized per-minute scoring potential. |
| **Ownership** | **Ownership Popularity** | `Ownership %` | Game-wide `selected_by_percent` from FPL API | Context-dependent | **$< 5.0\%$** (Diff) / **$> 30.0\%$** (Template) | Raw ownership proportion across all fantasy managers. |
| **Set-Piece** | **Team Set-Piece Net Swing** | `Net Swing` | $\Delta \text{xG}_{\text{set-piece}} - \Delta \text{xGA}_{\text{set-piece}}$ | Higher is better $\uparrow$ | **$> +0.20\text{ xG/game}$** | Net goal expectancy added via set-piece offense minus set-piece defense conceded. |
| **Set-Piece** | **Corner / Dead-Ball Share** | `Share %` | Proportion of club corners/free-kicks taken by specific player | Higher is better $\uparrow$ | **$\ge 70.0\%$** (Monopoly taker) | Set-piece delivery volume and assist potential. |

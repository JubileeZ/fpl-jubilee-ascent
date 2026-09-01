# Research Index & Guidelines

**Updated**: 2026-09-02T00:20:00+07:00
**Status**: Live index. Active research topics tracked below.

---

## Active Research Index

- **Premier League arrival xG/xA translation**: [Note](epl-arrival-xg-xa-adjustment/epl-arrival-xg-xa-adjustment.md) · [Summary](epl-arrival-xg-xa-adjustment/arrival_xg_xa_summary.csv) `npxg_median_ratio` / `xag_median_ratio` · [Before/after](epl-arrival-xg-xa-adjustment/arrival_xg_xa_before_after.csv) `ratio_npxg` · [Literature](epl-arrival-xg-xa-adjustment/literature-sources.md)
- **Set-piece taker vs Defcon**: [Note](set-piece-taker-vs-defcon/set-piece-taker-vs-defcon.md) · [DEF break-even](set-piece-taker-vs-defcon/def_breakeven.csv) `net_sp_vs_high_defcon` / `mean_pts_per_start` · [MID break-even](set-piece-taker-vs-defcon/mid_breakeven.csv) `mean_pts_per_start`
- **Transfer Plan Walk-Forward (2025-26 GW1–19)**: [Note](tp-walkforward-gw1-19-2025-26/tp-walkforward-gw1-19-2025-26.md) · [Summary](tp-walkforward-gw1-19-2025-26/tp_walkforward_summary.csv) `realized_points` (ranked; attack FT / 3-4-3 / Defcon-Floor) · [Club Occupancy](tp-walkforward-gw1-19-2025-26/def_rotation_club_occupancy.csv) `rank_mod_fdr`
- **First-Half 5-DEF Rotation Strategy (GW1–19)**: [Note](def-fdr-rotation-gw1-19/def-fdr-rotation-gw1-19.md) · [Club Occupancy](def-fdr-rotation-gw1-19/def_rotation_club_occupancy.csv) `rank_mod_fdr` / `total_mod_fdr` · [Summary](def-fdr-rotation-gw1-19/def_rotation_5sets_summary.csv) `total_mod_fdr` · [Starting DEFs](def-fdr-rotation-gw1-19/starting_defs_gw1_19.csv) · [Schedule Picks](def-fdr-rotation-gw1-19/gw1_19_def_rotation_schedule_picks.csv)
- **First-Half GKP Rotation Pairs (GW1–19)**: [Note](gkp-fdr-rotation-gw1-19/gkp-fdr-rotation-gw1-19.md) · [Summary](gkp-fdr-rotation-gw1-19/gkp_rotation_pairs_summary.csv) `total_mod_fdr` · [Starting GKPs](gkp-fdr-rotation-gw1-19/starting_gkps_gw1_19.csv) · [Schedule Picks](gkp-fdr-rotation-gw1-19/gw1_19_rotation_schedule_picks.csv)
- **First-Half Chip Strategy (source synthesis)**: [Note](fpl-first-half-chip-strategy/fpl-first-half-chip-strategy.md)

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
- **Figures**: caches of named companion CSV cells. Prompt names path + column (e.g. `gkp_rotation_pairs_summary.csv` `total_mod_fdr`), not a numeric snapshot.

---

## Master Metric Definitions & Interpretation Reference

| Domain / Area | Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|---|---|---|---|---|---|---|
| **Rotation** | **Total Modified FDR** | `total_mod_fdr` | $\sum_{g=1}^{19} \min(\text{Mod FDR}_A(g), \text{Mod FDR}_B(g))$ | Lower is better $\downarrow$ | **$\le 44.00$** | Cumulative rotated fixture difficulty across GW1–19 with home/away weighting. |
| **Rotation** | **Average Modified FDR** | `avg_mod_fdr` | $\frac{\text{total\_mod\_fdr}}{19}$ | Lower is better $\downarrow$ | **$\le 2.30$ / GW** | Mean difficulty of the started goalkeeper each gameweek. Unrotated baseline is $\approx 3.00$. |
| **Rotation** | **Total Base FDR** | `total_base_fdr` | $\sum_{g=1}^{19} \min(\text{Base FDR}_A(g), \text{Base FDR}_B(g))$ | Lower is better $\downarrow$ | **$\le 46.00$** | Unmodified official FPL FDR sum under weekly best-fixture rotation. |
| **Rotation** | **Defensive Composite Score** | `DCS` | $0.60 \times S_{\text{Score}} + 0.40 \times S_{\text{Risk}}$ | Higher is better $\uparrow$ | **$\ge 80.0$ / 100** | Live ranking metric for a Defensive Rotation Set. |
| **Rotation** | **Fixture Overlap Index** | `FOI` | $\frac{1}{T}\sum (1 - p_{\text{cs1}})(1 - p_{\text{cs2}})$ | Lower is better $\downarrow$ | **$< 0.50$** (Min $\approx 0.40$) | Probability of joint clean-sheet failure across paired goalkeepers. |
| **Rotation** | **FDR Schedule Correlation** | $r$ / `avg_corr` | Pearson correlation between club FDR sequences across gameweeks | Lower is better $\downarrow$ (Negative) | **$r \le -0.10$** | Measures fixture alignment. Negative correlation ensures one team has an easy fixture when the other faces a top-6 opponent. |
| **Rotation** | **Zero-Difficult Gameweeks** | `Zero-Diff %` | % of GWs where all started assets face FDR $\le 3$ | Higher is better $\uparrow$ | **$100.0\%$** | Completely avoids fielding starters against FDR $\ge 4$ elite attacks. |
| **Rotation** | **Rotated / Effective FDR** | `Rot FDR` | Average weekly fixture difficulty rating across started slots | Lower is better $\downarrow$ | **$\le 2.40$** | Benchmark baseline for unrotated schedule is $3.00$; rotation targets $\le 2.40$. |
| **Rotation** | **Rotated Expected Points** | `Rotated xP` | $\sum_{t=1}^N \max_{i \in \text{squad}} xP_{i,t}$ | Higher is better $\uparrow$ | Maximized | Sum of weekly projected points under optimal starting selection. |
| **Walk-Forward** | **First-Half Realized Points** | `realized_points` | Scoring-15 Realized Points GW1–19 after autosubs; Hits forbidden | Higher is better $\uparrow$ | Unconstrained baseline | Transfer Plan Walk-Forward ranking object (ADR 0020). |
| **Chip Strategy** | **Scenario Expected Points** | `Total xP` | Cumulative projected points across target window under Chip Path | Higher is better $\uparrow$ | Maximized | MILP-optimized points under chip constraints. |
| **Chip Strategy** | **Value Over Chip Baseline** | `VoC` | $xP(\text{Scenario } k) - xP(\text{No Chip Baseline})$ | Higher is better $\uparrow$ | **$\ge +12.0\text{ xP}$** | Net points gained by deploying specific chip combinations early vs holding. |
| **Ownership** | **Projected Rate** | `xP/90` | Expected points per 90 minutes normalized by role and fixture | Higher is better $\uparrow$ | **$\ge 5.0$** (Enabler) / **$\ge 7.0$** (Premium) | Normalized per-minute scoring potential. |
| **Ownership** | **Ownership Popularity** | `Ownership %` | Game-wide `selected_by_percent` from FPL API | Context-dependent | **$< 5.0\%$** (Diff) / **$> 30.0\%$** (Template) | Raw ownership proportion across all fantasy managers. |
| **Set-Piece** | **Team Set-Piece Net Swing** | `Net Swing` | $\Delta \text{xG}_{\text{set-piece}} - \Delta \text{xGA}_{\text{set-piece}}$ | Higher is better $\uparrow$ | **$> +0.20\text{ xG/game}$** | Net goal expectancy added via set-piece offense minus set-piece defense conceded. |
| **Set-Piece** | **Attack xP per start** | `xp_attack_per_start` | $(\text{goals} \times \text{goal pts} + \text{assists} \times 3) / n_{\ge60}$ | Higher $\uparrow$ | DEF $\ge 1.0$ / MID $\ge 1.5$ | Reconstructed attacking FPL points per 60+ minute appearance. |
| **Set-Piece** | **Defcon hit rate** | `defcon_hit_rate` | Starts reaching CBIT/CBIRT threshold / starts | Higher $\uparrow$ | DEF $\ge 0.45$ | Share of starts that bank the 2 Defcon pts. |
| **Set-Piece** | **Break-even hit-rate gap** | `breakeven_hit_rate_gap` | $\Delta$ attack xP per start / 2 | Context | DEF $\approx 0.34$ (2025-26) | Extra Defcon hits needed to offset a taker's extra attack xP. |
| **Arrival translation** | **npxG retain ratio** | `ratio_npxg` | PL npxG/90 ÷ source-league npxG/90 | Context (1 = unchanged) | `arrival_xg_xa_summary.csv` `pooled_summer_900` `npxg_median_ratio` | First Premier League season vs prior Big 5 season. Use median; mean is skewed. |
| **Arrival translation** | **xAG retain ratio** | `ratio_xag` | PL xAG/90 ÷ source-league xAG/90 | Context (1 = unchanged) | `arrival_xg_xa_summary.csv` `pooled_summer_900` `xag_median_ratio` | Separate from npxG. Not Opta xA; Understat check is `ratio_xa`. |

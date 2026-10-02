# Research Index & Guidelines

**Updated**: 2026-09-29T02:50:00+07:00
**Status**: Live index. Active research topics tracked below.

---

## Eval canon (session-durable)

Agents starting any model / Candidate / Champion work **read this block first**. Topic notes hold evidence; this block holds which metric is primary for which job.

**Leakage / holdout (ADR 0046, 0047, 0048, 0049):** 2025-26 = development season. Promotion = gate PASS on 2025-26 (seed 2024-25; boot P ≥ 0.60) **and** 2024-25 (no seed; confirmation, never tuned; one run per frozen Candidate; boot P ≥ 0.60). 2026-27 GW6+ sealed: no tuning/smoke/ablation; one post-promotion check per Champion. All runs logged in Candidate Ledger. Backtest features without snapshot are point-in-time (price/club from pre-target rows; season-end player columns dropped) — never read `players.parquet` season totals, status, ownership, or set-piece orders in backtest code.

**Before proposing a Candidate lever:** read [Candidate Ledger](candidate-ledger/candidate-ledger.md). Dead lever = no retry until `Revisit after` (evidence date + 1 year); new Champion does not reopen early. Record every attempt there.

### Promotion & model selection (production gate)

| Job | Primary | Guardrails | Authority |
|-----|---------|------------|-----------|
| Historical Promotion Gate / Candidate vs Champion | **Blended Eval Target** `formation_xi_regret` (50/50); delta > 0 (ADR 0049); block-bootstrap P(delta>0) ≥ 0.60 (ADR 0049); ≥2/3 segments | Playable MAE (≤ ×1.01), Playable \|bias\| (≤ +0.01), Captaincy Regret (≤ +0.15), xMins (≤ ×1.01), Spearman (≥ −0.005) | [ADR 0054](../adr/0054-formation-constrained-xi-regret-and-playable-pool-guardrails.md) · [ADR 0049](../adr/0049-gate-bootstrap-060-no-min-effect.md) · [ADR 0046](../adr/0046-point-in-time-backtest-and-statistical-gate.md) · [ADR 0044](../adr/0044-blended-eval-target-promotion-primary.md) · [ADR 0038](../adr/0038-process-points-eval-target.md) |
| Champion Signed Bias gate (Hits / no mean calibrate) | Realized `signed_bias` | `mae`, `minutes_bias` | [ADR 0033](../adr/0033-transfer-plan-hits-until-champion-bias.md) · [champion-signed-bias](champion-signed-bias-2025-26/champion_bias_summary.csv) `signed_bias` |
| Totals context in research companions | Triple-report `realized` \| `process` \| `blend` | — | ADR 0044 |

**Rejected as promotion primary:** Process-only; Blended without Realized/Process guardrails; component MAE; FPL `ep_*`.

### Event Component gap diagnosis (which ledger row to improve)

| Job | Primary | Diagnostics | Authority |
|-----|---------|-------------|-----------|
| Rank gap Event Component | **Realized** `mse_share` = $\mathrm{mean}(e_c\cdot e)/\mathrm{mean}(e^2)$ | Process G/A twins; Poisson-xGC CS/GC twins; `demotion_label` ∈ {`structural`,`variance`,`link-bias`,`no_twin`} | [champion-component-gap](champion-component-gap/champion-component-gap.md) · `component_gap_summary.csv` `mse_share` |
| Demotion thresholds | θ twin shrink ≥ **0.50**; τ \|signed_bias\| ≤ **0.05** | CS/GC shrink + large Realized bias → `link-bias` | Same note Method |
| Pools | `all` primary crown; `mins_60` rate check | Position `ALL` + GKP/DEF/MID/FWD secondary | Grill 2026-09-25 |

**Rejected for component ranking:** component MAE; raw \|bias\| alone; relative bias; Blended/Process as component ledger primary; Extended Process Points (deferred).

**Last crown (2025-26 gate, former Champion `hold_chase_challenger`; not recomputed for `face_value_challenger`, `pool=all` `position=ALL`):** `xp_goals` `structural` — inherited across Comparison Slate. CS/assists often `variance` on `all`; CS `link-bias` on `mins_60`.

### Glossary pointers

`CONTEXT.md`: Realized Points · Process Points · Blended Eval Target · Poisson-xGC Twin · Extended Process Points · Historical Promotion Gate · Model Champion / Candidate / Comparison Slate.

---

## Active Research Index

- **Candidate Ledger (tried / untried levers)**: [Ledger](candidate-ledger/candidate-ledger.md) (Shipped / Dead with `Revisit after` / Open next-lever pool)
- **Face-value Challenger (Champion 2026-09-28)**: [Note](face-value-challenger/face-value-challenger.md) · [Gate](face-value-challenger/face_value_gate_summary.csv) `combined_delta` / `boot_p_gt0` · [Smoke lanes](face-value-challenger/smoke_lane_results.csv) `combined_delta` (face-value xG/xA + minute-pooled finishing + start shrink; 3/3 segs; ADR 0045) · [Point-in-time re-gate](face-value-challenger/point_in_time_regate.csv) `combined_delta` / `boot_p_gt0` (ADR 0046: FAIL, regret tie, accuracy win)
- **Multi-feature event rate (2026-09-28)**: [Note](multi-feature-event-rate/multi-feature-event-rate.md) · [Gate](multi-feature-event-rate/candidate_gate_summary.csv) `combined_delta` / `boot_p_gt0` · [Smoke](multi-feature-event-rate/smoke_results.csv) `combined_delta` · [Confirmation](multi-feature-event-rate/confirmation_gate_summary.csv) `boot_p_gt0` (GLM assist rate dev PASS, 2024-25 P 0.896 passes 0.60 bar → Champion, ADR 0048; passes 0.60 bar both seasons, ADR 0049; goals/GC/stack levers Dead)
- **Dual-lane Candidate search (2026-09-28)**: [Note](dual-lane-candidate-search/dual-lane-candidate-search.md) · [Smoke](dual-lane-candidate-search/smoke_results.csv) `combined_delta` / `boot_p_gt0` (88 variants, no pass; best stack soft P(60) bonus eligibility + learned p_start +1.388 bias fail / +1.198 P 0.928; 11 levers → Dead; `learned_start_challenger` dev PASS +1.198, 2024-25 +0.518 P 0.638 → PASS under ADR 0049 gate (P ≥ 0.60, no min effect) · [Gate](dual-lane-candidate-search/candidate_gate.csv) `pass` → Champion, ADR 0050)
- **Asymmetric finishing challenger & Dual-lane search round 2 (2026-09-28)**: [Note](asymmetric-finishing-challenger/asymmetric-finishing-challenger.md) · [Gate](asymmetric-finishing-challenger/candidate_gate.csv) `pass` / `combined_delta` / `boot_p_gt0` · [Smoke](asymmetric-finishing-challenger/smoke_results.csv) `combined_delta` (18 variants; pos-split goals all negative; penalty taker signal inert; asymmetric finishing dev PASS +0.261 2/3 P 0.989, confirm 2024-25 FAIL -0.231 0/3 P 0.199 -> Dead; Champion `learned_start_challenger` unchanged)
- **Component model ideas (2026-09-28)**: [Note](component-model-ideas/component-model-ideas.md) · [Component list](component-model-ideas/component_list.csv) `champion_form` / `idea_ids` · [Idea queue](component-model-ideas/idea_queue.csv) `order` / `tier` / `status` (29 ideas across 14 components; explore-candidate Queue mode) · [Smoke](component-model-ideas/smoke_results.csv) `combined_delta` / `boot_p_gt0` · [Gate](component-model-ideas/candidate_gate.csv) `pass` (all 29 ideas evaluated and resolved: ATK-05 promoted Champion ADR 0051; 3 confirm-fail ATK-04/DEF-02/MIN-07; 25 dead/failed; queue 100% complete)
- **Formation eval retest (2026-10-01)**: [Note](formation-eval-retest/formation-eval-retest.md) · [Gate](formation-eval-retest/candidate_gate.csv) `pass` · [Smoke](formation-eval-retest/smoke_results.csv) `combined_delta` (past dev winners re-screened under ADR 0054 legal formation XI eval; `def_xg_shrink_challenger` dev PASS +0.793 3/3 P 0.944, confirm 2024-25 PASS +0.594 2/3 P 0.863 → Champion ADR 0055; `cs_exposure_challenger` confirm FAIL; `asymmetric_finishing_challenger` confirm FAIL)
- **Club starting mass redistribution (2026-10-01)**: [Note](club-starting-mass-redistribution/club-starting-mass-redistribution.md) · [Smoke](club-starting-mass-redistribution/smoke_results.csv) `combined_delta` / `boot_p_gt0` (6 variants; pos_cap & form_slot all negative −3.14 … −4.13, 0/3 segs; single-DNP false absence + rotation club compression → Dead)
- **Player projection calibration & tier de-biasing (2026-10-01)**: [Note](player-projection-calibration/player-projection-calibration.md) · [Gate](player-projection-calibration/candidate_gate.csv) `combined_delta` / `boot_p_gt0` · [Smoke](player-projection-calibration/smoke_results.csv) `combined_delta` (15 variants; bonus saturation negative −0.16 … −0.38; natural rates `calibrated_rate_challenger` dev PASS +0.355 2/3 P 0.901, confirm 2024-25 FAIL −0.449 1/3 P 0.237 → Dead; Champion `def_xg_shrink_challenger` unchanged)

- **Champion component gap**: [Note](champion-component-gap/champion-component-gap.md) · [Summary](champion-component-gap/component_gap_summary.csv) `mse_share` · [Totals](champion-component-gap/component_gap_totals.csv) `realized_mae` (Realized `mse_share` primary; Process G/A + Poisson-xGC CS/GC twins; demotion / `link-bias`) · [Segment loss #123](champion-component-gap/segment-loss-121.md) · [segment summary](champion-component-gap/segment_loss_121_summary.csv) `blend_regret_delta_champ_minus_cand` · [AFK segment-fix experiments #124](champion-component-gap/segment_fix_experiments_124.md) · [CS/GC sweep](champion-component-gap/segment_fix_sweep_124.csv) · [bonus sweep](champion-component-gap/bonus_scale_sweep_124.csv) · [Bonus/BPS inventory #125](champion-component-gap/bonus-bps-inventory-125.md) · [Layer diagnosis #133](champion-component-gap/layer-diagnosis-133.md) · [gate](champion-component-gap/layer_diagnosis_133_gate.csv) `late_delta` · [late position](champion-component-gap/layer_diagnosis_133_late_position.csv) `regret_delta`
- **Cross-GW dispersion (2025-26)**: [Note](xp-cross-gw-dispersion/xp-cross-gw-dispersion.md) · [Summary](xp-cross-gw-dispersion/dispersion_summary.csv) `mean_SD` · [Components](xp-cross-gw-dispersion/fixture_component_swing.csv) `mean_SD` (Champion xP ~12.5% of blend swing on `60+`; attack fixture ~zero)
- **Downside attack scale (won scorecard)**: [Note](fixture-downside-scale/fixture-downside-scale.md) · [Summary](fixture-downside-scale/downside_swing_summary.csv) `blend_mae` (downside 0.9960 vs Champion 1.0024; all guardrails hold; pending gate plumbing + admission)
- **Hold vs chase (2025-26)**: [Note](hold-vs-chase-2025-26/hold-vs-chase-2025-26.md) · [Summary](hold-vs-chase-2025-26/hold_chase_summary.csv) `value` (autocorr ~0.09, hauls ~28%, CS 3× easy/hard, 82 nailed; barbell strategy)
- **Matchup share add-on (2025-26)**: [Note](matchup-share-addon-2025-26/matchup-share-addon-2025-26.md) · [Summary](matchup-share-addon-2025-26/matchup_share_summary.csv) `signed_bias` (all-pool worse than neutral; **shipped** Matchup → Strength → neutral, ADR 0037)
- **Champion signed bias (2025-26 GW1–38)**: [Note](champion-signed-bias-2025-26/champion-signed-bias-2025-26.md) · [Summary](champion-signed-bias-2025-26/champion_bias_summary.csv) `signed_bias`
- **Premier League arrival xG/xA translation**: [Note](epl-arrival-xg-xa-adjustment/epl-arrival-xg-xa-adjustment.md) · [Summary](epl-arrival-xg-xa-adjustment/arrival_xg_xa_summary.csv) `npxg_median_ratio` / `xag_median_ratio` · [Before/after](epl-arrival-xg-xa-adjustment/arrival_xg_xa_before_after.csv) `ratio_npxg` · [Literature](epl-arrival-xg-xa-adjustment/literature-sources.md)
- **Set-piece taker vs Defcon**: [Note](set-piece-taker-vs-defcon/set-piece-taker-vs-defcon.md) · [DEF break-even](set-piece-taker-vs-defcon/def_breakeven.csv) `net_sp_vs_high_defcon` / `mean_pts_per_start` · [MID break-even](set-piece-taker-vs-defcon/mid_breakeven.csv) `mean_pts_per_start`
- **Transfer Plan Walk-Forward (2025-26 GW1–19)**: [Note](tp-walkforward-gw1-19-2025-26/tp-walkforward-gw1-19-2025-26.md) · [Summary](tp-walkforward-gw1-19-2025-26/tp_walkforward_summary.csv) `realized_points` (ranked; attack FT / 3-4-3 / Defcon-Floor) · [Club Occupancy](tp-walkforward-gw1-19-2025-26/def_rotation_club_occupancy.csv) `rank_mod_fdr`
- **First-Half 5-DEF Rotation Strategy (GW1–19)**: [Note](def-fdr-rotation-gw1-19/def-fdr-rotation-gw1-19.md) · [Club Occupancy](def-fdr-rotation-gw1-19/def_rotation_club_occupancy.csv) `rank_mod_fdr` / `total_mod_fdr` · [Summary](def-fdr-rotation-gw1-19/def_rotation_5sets_summary.csv) `total_mod_fdr` · [Starting DEFs](def-fdr-rotation-gw1-19/starting_defs_gw1_19.csv) · [Schedule Picks](def-fdr-rotation-gw1-19/gw1_19_def_rotation_schedule_picks.csv)
- **First-Half GKP Rotation Pairs (GW1–19)**: [Note](gkp-fdr-rotation-gw1-19/gkp-fdr-rotation-gw1-19.md) · [Summary](gkp-fdr-rotation-gw1-19/gkp_rotation_pairs_summary.csv) `total_mod_fdr` / `pct_gw_mod_le_2_25` · [Raya partners](gkp-fdr-rotation-gw1-19/raya_rotation_partners.csv) `total_mod_fdr` · [Starting GKPs](gkp-fdr-rotation-gw1-19/starting_gkps_gw1_19.csv) · [Schedule Picks](gkp-fdr-rotation-gw1-19/gw1_19_rotation_schedule_picks.csv)
- **First-Half Chip Strategy (source synthesis)**: [Note](fpl-first-half-chip-strategy/fpl-first-half-chip-strategy.md)

## Closed

- **Wayfinder Transfer Plan dashboard spec**: archived to [../archive/wayfinder-transfer-plan-spec/](../archive/wayfinder-transfer-plan-spec/). Product UI/UX spec retired from active research root per research boundary rule.
- **Fixture-swing candidates** (2026-09-24): both arms dead — multiplicative breached easy cap (+0.681) and lost blend MAE; additive tied MAE with worse easy bias. Champion stands. Note: [fixture-swing-candidates](../archive/fixture-swing-candidates/fixture-swing-candidates.md) · [Summary](../archive/fixture-swing-candidates/candidate_swing_summary.csv) `blend_mae`.
- **Fixture xP scale without Club Strength** (2026-09-22): production [ADR 0037](../adr/0037-fdr-fallback-multiplier-neutral.md) = Matchup Share → Club Strength → neutral. Prior rejected scales: [FDR regime](../archive/dual-vector-fdr-regime-2025-26/dual-vector-fdr-regime-2025-26.md) · [Official xG Dual-Vector](../archive/dual-vector-official-xg-2025-26/dual-vector-official-xg-2025-26.md) · [Team Poisson λ](../archive/team-poisson-lambda-2025-26/team-poisson-lambda-2025-26.md). Gate evidence also [matchup-share](matchup-share-addon-2025-26/matchup_share_summary.csv) `signed_bias`.

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
- **Metrics**: every quantitative note includes `### Metric Definitions & Direction` (Definition/Formula, Direction, Ideal Benchmark, Description). Promotion vs component-gap primary metrics live in **Eval canon** at top of this INDEX — do not invent a competing primary in a topic note.
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
| **Rotation** | **Easy-week coverage** | `pct_gw_mod_le_2_25` | $100 \times n(\min(\text{Mod FDR}_A,\text{Mod FDR}_B) \le 2.25) / 19$ | Higher is better $\uparrow$ | **$100\%$ (19/19)** | Share of GW1–19 where started GKP faces only official FDR 1–2 (away FDR 2 = 2.25 still counts; FDR 3 home = 2.75 fails). |
| **Rotation** | **Rotated / Effective FDR** | `Rot FDR` | Average weekly fixture difficulty rating across started slots | Lower is better $\downarrow$ | **$\le 2.40$** | Benchmark baseline for unrotated schedule is $3.00$; rotation targets $\le 2.40$. |
| **Rotation** | **Rotated Expected Points** | `Rotated xP` | $\sum_{t=1}^N \max_{i \in \text{squad}} xP_{i,t}$ | Higher is better $\uparrow$ | Maximized | Sum of weekly projected points under optimal starting selection. |
| **Walk-Forward** | **Champion signed bias** | `signed_bias` | $\mathrm{mean}(\text{projected\_points} - \text{actual\_points})$ | Near zero (context) | Gate in `champion_bias_summary.csv` `signed_bias` | Model Champion vs Realized Points. Positive = overprediction. Not FPL `ep_*`. |
| **Walk-Forward** | **Component MSE share** | `mse_share` | $\mathrm{mean}(e_c\cdot e)/\mathrm{mean}(e^2)$ on Realized ledger | Context (rank by $\|\,\|$) | `component_gap_summary.csv` `mse_share` | Which Event Component drives Official squared error. Not component MAE. Not promotion primary. |
| **Walk-Forward** | **Twin shrink** | `twin_shrink` | $1 - \|mse\_share\_twin\|/\|mse\_share\|$ | Higher → more finish/link noise | ≥ 0.50 with τ → demotion check | Process G/A or Poisson-xGC twin vs Realized share |
| **Walk-Forward** | **Demotion label** | `demotion_label` | `structural` / `variance` / `link-bias` / `no_twin` | Context | structural = Candidate lever | Gap diagnosis decision label |
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

# Bonus / xp_bonus + BPS Bonus Model inventory (#125)

**Updated**: 2026-09-27T00:30:00+07:00  
**Data stamp**: code HEAD + `component_gap_summary.csv` Champion/Candidate rows; AFK flat-scale kill [segment_fix_experiments_124.md](segment_fix_experiments_124.md)  
**Season**: Multi-season inventory (code surface); residual cells 2025-26 GW1–38 + 2026-27 GW1–5  
**Status**: Active — resolves wayfinder [#125](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/125); no Candidate build  
**Purpose**: Inventory current `xp_bonus` / BPS Bonus Model surface in code + residual companions; list **non-flat** knobs a bonus-arm lever grill can choose among  
**Scope**: Primary sources only (models, features, CONTEXT, ADRs, residual CSV, #124 AFK). **Out:** Candidate implementation; flat global `k_bonus` as intended lever; resolving #126–#128  
**Related**: map [#110](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/110) · route [#124](https://github.com/JubileeZ/fpl-jubilee-ascent/issues/124) · residual [champion-component-gap.md](champion-component-gap.md) · soft/prototype chain #126→#127→#128  
**Artifact**: this note (inventory). Residual cells: [component_gap_summary.csv](component_gap_summary.csv) `component=xp_bonus`. Flat-scale kill: [bonus_scale_sweep_124.csv](bonus_scale_sweep_124.csv) / [bonus_scale_sweep_124.json](bonus_scale_sweep_124.json)

## Sources

- **Primary (code)**: `models/metrics_component_hybrid.py` `_project_event_components` `xbps` + `_allocate_bonus`; `models/participation_state_hybrid.py` eligibility + fixture grouping; `models/calibrated_matchup_hybrid.py` duplicated `xbps`; inheritance `hold_chase_challenger` → `goals_path_challenger` → `defence_link_challenger` (CS/GC only post-link)  
- **Primary (glossary)**: `CONTEXT.md` **BPS Bonus Model**  
- **Primary (design)**: [ADR 0005](../../adr/0005-hybrid-metrics-component-projection-model.md) Competitor-Aware Bonus Proxy; [ADR 0007](../../adr/0007-event-level-empirical-bayes-projection-engine.md) Calibrated Bonus Tier Allocation $T=6.0$  
- **Primary (features)**: `features/builder.py` `per90_bonus`; `features/processor.py` / `vaastav_archive.py` ingest `bonus`/`bps` (not consumed by hybrid `xbps`)  
- **Repository data**: [component_gap_summary.csv](component_gap_summary.csv) `mse_share` / `signed_bias` / `demotion_label` for `xp_bonus`; [segment_fix_experiments_124.md](segment_fix_experiments_124.md) flat `k_bonus` disproven for `late`  
- **Secondary path (not Champion stack)**: `models/component_baseline.py` `per90_bonus` → `xp_bonus` without fixture ranking

**Source boundary**: Inventory of shipped forms. Official FPL BPS weight table not re-derived here (`docs/fpl_scoring_rules_2025-26.md` only names bonus 1–3 via BPS). ADR labels current form a **proxy**, not fitted multinomial.

## Agent Prompt

```text
Full redo docs/research/champion-component-gap/bonus-bps-inventory-125.md

1. Re-open models/metrics_component_hybrid.py _allocate_bonus + xbps; calibrated_matchup_hybrid xbps; participation_state_hybrid eligibility; defence_link_challenger predict (confirm no xp_bonus mutate).
2. Re-read CONTEXT.md BPS Bonus Model; ADR 0005 §5; ADR 0007 §5.
3. Refresh xp_bonus rows from component_gap_summary.csv (Champion + defence_link; pool all + mins_60; position ALL + GKP/DEF/MID/FWD).
4. Re-confirm flat k_bonus OUT via segment_fix_experiments_124.md / bonus_scale_sweep_124.json any_late_win=false.
5. Keep lever list NON-FLAT only; no Candidate build; no model_selection mutate.
6. Scratch under .tmp/agent/ only; delete before finish.
```

## Method

**Method type**: Source synthesis (code + residual companions)

**Inputs**:
- Hybrid bonus pipeline source files above
- `component_gap_summary.csv` filter `component=xp_bonus`
- #124 AFK note + JSON kill cells

**Procedure**:
1. Trace Champion → Candidate inheritance for who computes `xbps` / who calls `_allocate_bonus` / who mutates `xp_bonus`.
2. Extract parameterized constants (weights, $T$, eligibility, pool grain).
3. Summarize residual facts a lever grill needs (rank, bias sign, position splits, `no_twin`).
4. List concrete non-flat lever candidates grounded in existing knobs or ADR-admitted gaps; exclude flat `k_bonus`.

**Definitions and assumptions**:
- **BPS Bonus Model** (`CONTEXT.md`): maps projected BPS totals from event components into expected bonus ∈ {0,1,2,3} (here: continuous $E[\text{bonus}]$ via softmax ranks).
- **Flat `k_bonus`**: post-hoc `xp_bonus *= k` on ledger — **OUT** as Candidate lever ([segment_fix_experiments_124.md](segment_fix_experiments_124.md)).
- Stack base for next Candidate: subclass `defence_link_challenger` (#122/#124).

### Metric Definitions & Direction

| Metric | Symbol | Definition / Formula | Direction | Ideal / Benchmark | Description |
|---|---|---|---|---|---|
| Component MSE share | `mse_share` | $\mathrm{mean}(e_c\cdot e)/\mathrm{mean}(e^2)$ Realized | Context (rank by $\|\,\|$) | INDEX Eval canon | Bonus residual mass vs total Official error |
| Signed bias | `signed_bias` | $\mathrm{mean}(\hat{c}-c)$ | Near 0 | $\|\,\|\le\tau=0.05$ for soft later | Over/under projection of bonus arm |
| Demotion label | `demotion_label` | twin + τ rules | Context | `no_twin` for bonus today | No Process/Poisson twin for bonus |
| Softmax temp | $T$ | `logits = xbps / T` | Context | shipped $T=6.0$ | Ranking sharpness of +3/+2/+1 |

**Validation boundary**: Residual cells from existing companions (not re-run this ticket). Flat-scale kill validated only on 2025-26 archive walk-forward post-hoc algebra (#124).

## Source synthesis

### Code surface (Champion stack)

Inheritance:

`metrics_component_hybrid` → `participation_state_hybrid` → `calibrated_matchup_hybrid` → `hold_chase_challenger` → `goals_path_challenger` → `defence_link_challenger`

| Layer | Bonus role | Source |
|---|---|---|
| `metrics_component_hybrid` | Defines `xbps` linear proxy + `_allocate_bonus` Plackett-Luce softmax over fixture | `models/metrics_component_hybrid.py` |
| `participation_state_hybrid` | Start/sub mixture; weights `xbps`; eligibility = $P(\text{start})\mathbf{1}[\text{mins}_\text{start}\ge45]+P(\text{sub})\mathbf{1}[\text{mins}_\text{sub}\ge45]$; groups by `fixture_id`; calls `_allocate_bonus` | `models/participation_state_hybrid.py` |
| `calibrated_matchup_hybrid` | **Overrides** `_project_event_components`; **duplicates** same `xbps` weights + hard `eligible_bonus = (expected_minutes ≥ 45)` | `models/calibrated_matchup_hybrid.py` |
| `hold_chase` / `goals_path` | No bonus override (participation + matchup `xbps` only) | respective modules |
| `defence_link_challenger` | Post-link scales **only** `xp_clean_sheet` / `xp_conceded`; **`xp_bonus` unchanged** | `models/defence_link_challenger.py` |

Shipped `xbps` (identical in metrics + calibrated):

$$
\text{xbps} = 0.1\cdot\text{mins} + 24\cdot\mathbb{E}[\text{goals}] + 12\cdot\mathbb{E}[\text{assists}] + 12\cdot P(\text{CS}) + 6\cdot P(\text{Defcon}) + 2\cdot\mathbb{E}[\text{saves}]
$$

Allocation (`_allocate_bonus`): within each fixture, eligible players; `logits = xbps / 6.0`; sequential softmax ranks → $E[\text{bonus}] = 3P_1 + 2P_2 + P_3$; adds into `projected_points`. ADR 0007 names this $T=6.0$; ADR 0005: proxy for match-level BPS ties, **not** fitted multinomial.

### Features vs model

- Ingest stores `bonus` / `bps` (`features/processor.py`, archive helpers).
- Feature Contract builds `per90_bonus` (`features/builder.py`).
- Hybrid Champion path **does not** read `bps` or `per90_bonus` for `xp_bonus` — only projected event components into `xbps`.
- `component_baseline` **does** use `per90_bonus` × difficulty → `xp_bonus` (no competitor softmax). Not on Comparison Slate Champion path.

### Residual companions (`xp_bonus`)

Champion `hold_chase_challenger`, Realized, 2025-26 ([component_gap_summary.csv](component_gap_summary.csv)):

| Pool | Position | `mse_share` | `signed_bias` | rank | `demotion_label` |
|---|---|---:|---:|---:|---|
| all | ALL | 0.155 | −0.004 | 3 | `no_twin` |
| mins_60 | ALL | 0.180 | **−0.106** | 3 | `no_twin` |
| mins_60 | DEF | 0.135 | **−0.116** | 3 | `no_twin` |
| mins_60 | MID | 0.203 | **−0.118** | 2 | `no_twin` |
| mins_60 | FWD | 0.257 | −0.067 | 2 | `no_twin` |

- `pool=all` nearly mean-calibrated; **rate pool under-projects** bonus (especially DEF/MID).
- Same component on `defence_link_challenger` / `goals_path_challenger`: identical `mean_projected` / `signed_bias` vs Champion on `all`/`ALL` (defence_link does not touch bonus).
- Parent residual note: after goals/CS twin demotions, `xp_bonus` is next non-twin mass ([champion-component-gap.md](champion-component-gap.md)).

### Flat scale kill (#124)

[bonus_scale_sweep_124.json](bonus_scale_sweep_124.json): `any_late_win=false`, `any_pass=false` for flat `k_bonus` ∈ [0.5, 4] alone or on CS bases. Near-miss dampen `k_bonus=0.75` still loses `late`.

## Project interpretation

### Decision rules

- Route = **bonus-first**; Candidate stack = subclass `defence_link_challenger`.
- Lever grill **must not** propose flat global `xp_bonus`/`k_bonus` as the Candidate lever.
- Prefer knobs that change **relative fixture ranking** or **BPS composition**, not a uniform post-multiply.
- Soft-pre-gate grain/rule for bonus deferred to #128 after lever set (#127).

### Practical implications

- Implementers will override `_project_event_components` and/or `_allocate_bonus` (or post-process ranks) on a `defence_link` subclass — CS/GC scales can stay.
- Twin Sweep if editing `xbps`: constants live in **two** files (`metrics_component_hybrid` + `calibrated_matchup_hybrid`).

## Findings

### Evidence — surface

1. Production BPS Bonus Model = linear `xbps` + fixture softmax tiers ($T=6$, ≥45 mins eligibility, +3/+2/+1). Sources: code + ADR 0005/0007.
2. Champion / goals / defence_link share that form; defence_link leaves `xp_bonus` untouched.
3. Residual: rank-3 `mse_share`, `no_twin`; mins_60 underprediction (DEF/MID worst bias). Source: `component_gap_summary.csv`.
4. Flat `k_bonus` cannot win `late` / gate. Source: #124 companions.

### Non-flat lever candidates (for #127 grill — inventory only)

Concrete knobs grounded in shipped code / ADR gaps (**not** flat `k_bonus`):

1. **`xbps` component weights** — retune $\{0.1, 24, 12, 12, 6, 2\}$ (mins / goals / assists / CS / Defcon / saves); position-specific variants address mins_60 DEF/MID under-prediction without global scale.
2. **Softmax temperature $T$** — shipped $T=6.0$; lower $T$ concentrates +3/+2/+1 on high-`xbps` players (ranking-sensitive); higher $T$ flattens allocation.
3. **Eligibility / pool structure** — ≥45 gate vs participation-weighted eligibility; restrict or reshape fixture competitor set (e.g. starters-only, position-aware pools) — ADR 0005 admits richer match-level BPS / tie handling missing.
4. **Expand `xbps` event set** — hybrid omits cards / own goals / penalties / ICT-style terms that ingest already stores as `bps` history; adding terms changes composition, not a flat `xp_bonus` multiply.
5. **Allocation form** — replace sequential softmax with harder top-$k$, fitted multinomial, or tie-aware rules (ADR 0005 consequence: proxy until richer form).
6. **Baseline-style rate arm (contrast only)** — `per90_bonus` reconstruction (`component_baseline`) is a different family; grill may reject as non-stack or use as diagnostic counterfactual, not default Champion-path lever.

### Alternatives rejected this ticket

- Flat global `k_bonus` — AFK disproven (#124).
- Building Candidate / mutating `model_selection` — out of #125 scope.

## Decision

**Verdict**: Current surface is a **fixture-softmax BPS proxy** (`xbps` weights + $T=6$ + ≥45 eligibility) shared unchanged through `defence_link`; residual is rank-3 `no_twin` with mins_60 under-prediction. Flat scale OUT. Lever grill (#127) should choose among **weight / temperature / eligibility-pool / expanded BPS terms / allocation form**.

**Recommended action**:
- Close #125; hand #126 prototype stub subclassing `defence_link` with a **placeholder non-flat** hook (no tuned lever until #127).
- Feed top non-flat candidates above into #127 grill facts pack.

**Trigger / kill switch**:
- If a proposed lever reduces to `xp_bonus *= k` globally → reject (same class as #124 kill).
- If residual reorders and bonus `mse_share` ceases to matter before build → re-open route (map #110).

## Risks and unknowns

- Official BPS weight table / 2026-27 BPS tweaks not inventoried cell-by-cell here (scoring rules doc is high-level).
- Softmax ranks ≠ discrete {0,1,2,3} realization; Decision Regret may need ranking-sensitive form even when component MAE looks mild (`all`-pool bias ~0).
- Duplicate `xbps` definitions risk drift if only one file is edited.
- Soft bar grain (#128) still unspecified.

## Refresh checklist

- [x] `Updated` ISO 8601 + timezone
- [x] `Data stamp` identifies evidence cutoff
- [x] Season / scope accurate
- [x] Source synthesis vs Project interpretation separated
- [x] Flat `k_bonus` labeled OUT with #124 cite
- [x] Non-flat levers cited to code/ADR
- [x] Agent Prompt runnable
- [x] No Candidate / no `model_selection` mutate
- [x] Scratch cleaned before finish

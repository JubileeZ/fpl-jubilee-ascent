# Calibrate bonus_arm_challenger (#129)

**Updated**: auto from `calibrate_bonus_arm.py`
**Data stamp**: 2025-26 GW1–38 seed 2024-25
**Status**: Active — freezes `_XBPS_WEIGHTS` + `_BONUS_SOFTMAX_T`
**Purpose**: Data-drive bonus-arm levers (#127); no Admission / `--apply`

## Frozen constants

- `_XBPS_WEIGHTS` = `(0.1, 96.0, 48.0, 48.0, 24.0, 8.0)` (event scale k=4.0)
- `_BONUS_SOFTMAX_T` = `8.0`
- Weight-only bias @ T=6 (mins_60/ALL xp_bonus): signed_bias=-0.060630 (τ=0.05; inside=False; best on grid)
- After T=8 freeze remeasure: mins_60 bias=-0.067150 mse_share=0.189538; pool=all bias≈0 (near-calibrated)
- T pick: early_mid_delta=+0.544 late_delta=-1.554 segs=2/3 Δpri=-0.497 (best early_mid+seg among grid; gate fail expected pre-admit)

## Method

1. Grid event scale on (g,a,CS,Defcon,saves); mins fixed 0.1; measure Realized `xp_bonus` bias via component-gap runner.
2. Freeze best |bias| (prefer ≤τ); grid $T$; Blended Decision Regret vs Champion; prefer early_mid/late.

Companion: [calibrate_bonus_arm_129.json](calibrate_bonus_arm_129.json)

## Metric Definitions & Direction

| Metric | Definition / Formula | Direction | Ideal / Benchmark |
|---|---|---|---|
| Signed bias | `mean(xp_bonus − actual_bonus)` on Realized, grain mins_60/ALL | Near 0 | \|bias\|≤τ=0.05 |
| MSE share | `mean(e_c·e)/mean(e²)` for `xp_bonus` | Context | Soft and/or ↓ vs Champion (#128) |
| Blended primary delta | Champion − Candidate Decision Regret (or MAE) on Blended | Higher ↑ | >0 for gate |
| Segment delta | Same per cold_start / early_mid / late | Higher ↑ | Prefer early_mid/late >0 |
| Softmax T | `logits = xbps / T` | Context | Data-driven; shipped ADR default 6.0 |

## Residual

Event-scale grid k≤4 never cleared τ (best −0.061 @ T=6); T=8 trades slight bias for early_mid+2/3 segs. Soft #130 may pass via \|mse_share\|↓ half of and/or.


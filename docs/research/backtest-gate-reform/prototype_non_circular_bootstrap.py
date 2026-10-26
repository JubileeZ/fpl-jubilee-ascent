"""Simulation runner and validation harness for Non-Wrapping Moving Block Bootstrap (L=5),
Active-Gameweek Resampling, and Pooled 2-Season Stratified Bootstrap Gate
(Wayfinder Ticket #171, ADR 0064).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class BootstrapComparisonResult:
    circular_p: float
    mbb_p: float
    circular_wrapping_frequency: float
    active_mbb_p: float | None = None


def circular_block_bootstrap_indices(
    n: int, block: int, draws: int, seed: int = 0
) -> np.ndarray:
    """Legacy circular block bootstrap index matrix with modulo wrapping and truncation."""
    rng = np.random.default_rng(seed)
    size = min(block, n)
    k = -(-n // size)
    starts = rng.integers(0, n, size=(draws, k))
    return ((starts[:, :, None] + np.arange(size)) % n).reshape(draws, -1)[:, :n]


def moving_block_bootstrap_indices(
    n: int, block: int, draws: int, seed: int = 0
) -> np.ndarray:
    """Non-wrapping moving block bootstrap index matrix (Künsch 1989, Lahiri 2003).

    Start indices are strictly restricted to 0 <= s <= n - L.
    All blocks are complete of length L, eliminating final-block truncation.
    """
    if n <= 0:
        return np.empty((draws, 0), dtype=int)
    rng = np.random.default_rng(seed)
    size = min(block, n)
    k = -(-n // size)
    num_starts = n - size + 1
    starts = rng.integers(0, num_starts, size=(draws, k))
    return (starts[:, :, None] + np.arange(size)).reshape(draws, -1)


def non_wrapping_block_bootstrap_win_probability(
    deltas: Sequence[float],
    *,
    draws: int = 20_000,
    block: int = 5,
    seed: int = 0,
    active_mask: Sequence[bool] | None = None,
) -> float:
    """Non-wrapping moving block bootstrap probability of positive mean delta.

    Restricts start indices to 0 <= s <= n - L, eliminating circular wrapping (% n)
    and final-block truncation. If active_mask is provided, evaluates only over
    active gameweeks where the candidate diverges from the champion.
    """
    values = np.asarray(deltas, dtype=float)
    if active_mask is not None:
        mask = np.asarray(active_mask, dtype=bool)
        if len(mask) == len(values):
            values = values[mask]
    n = len(values)
    if n == 0 or np.isnan(values).all():
        return 0.0
    size = min(block, n)
    if size <= 0:
        return 0.0
    rng = np.random.default_rng(seed)
    k = -(-n // size)
    num_starts = n - size + 1
    starts = rng.integers(0, num_starts, size=(draws, k))
    idx = (starts[:, :, None] + np.arange(size)).reshape(draws, -1)
    sample_means = values[idx].mean(axis=1)
    return float((sample_means > 0).mean())


def stratified_block_bootstrap_win_probability(
    strata_deltas: Sequence[Sequence[float]],
    *,
    draws: int = 20_000,
    block: int = 5,
    seed: int = 0,
) -> float:
    """Pooled multi-season stratified block bootstrap probability of positive mean delta.

    Draws non-wrapping moving blocks independently within each season's temporal stratum,
    preventing inter-season index mixing and modulo boundary artifacts, then evaluates
    the combined pooled sample mean across all strata.
    """
    valid_strata = [
        np.asarray(s, dtype=float) for s in strata_deltas if len(s) > 0 and not np.isnan(s).all()
    ]
    if not valid_strata:
        return 0.0

    rng = np.random.default_rng(seed)
    strata_resamples: list[np.ndarray] = []

    for s_vals in valid_strata:
        n = len(s_vals)
        size = min(block, n)
        k = -(-n // size)
        num_starts = n - size + 1
        starts = rng.integers(0, num_starts, size=(draws, k))
        idx = (starts[:, :, None] + np.arange(size)).reshape(draws, -1)
        strata_resamples.append(s_vals[idx])

    pooled_matrix = np.concatenate(strata_resamples, axis=1)
    pooled_means = pooled_matrix.mean(axis=1)
    return float((pooled_means > 0).mean())


def run_bootstrap_simulation() -> dict[str, Any]:
    """Execute comparative validation experiments for ADR 0064 / Ticket #171."""
    n_gws = 38
    draws = 10_000

    # 1. Circular wrapping frequency analysis
    circ_idx_3 = circular_block_bootstrap_indices(n_gws, block=3, draws=draws, seed=42)
    circ_idx_5 = circular_block_bootstrap_indices(n_gws, block=5, draws=draws, seed=42)
    mbb_idx_5 = moving_block_bootstrap_indices(n_gws, block=5, draws=draws, seed=42)

    # Check for wrapping: any step where idx[t] < idx[t-1] within a block
    def count_wrapping_draws(idx_mat: np.ndarray, block_size: int) -> float:
        d = idx_mat.shape[0]
        k = idx_mat.shape[1] // block_size
        blocks = idx_mat[:, : k * block_size].reshape(d, k, block_size)
        diffs = np.diff(blocks, axis=2)
        has_wrap = np.any(diffs < 0, axis=(1, 2))
        return float(np.mean(has_wrap))

    wrap_freq_circ_3 = count_wrapping_draws(circ_idx_3, 3)
    wrap_freq_circ_5 = count_wrapping_draws(circ_idx_5, 5)
    wrap_freq_mbb_5 = count_wrapping_draws(mbb_idx_5, 5)

    # 2. Dormant Fallback Dilution Test
    # Simulate Adaptive Causal ML: GW1-19 fallback (0.0 delta), GW20-38 active mean +0.50, std 1.0
    rng = np.random.default_rng(101)
    active_deltas = rng.normal(0.40, 1.2, size=19)
    dormant_deltas = np.zeros(19)
    full_deltas = np.concatenate([dormant_deltas, active_deltas])
    active_mask = np.concatenate([np.zeros(19, dtype=bool), np.ones(19, dtype=bool)])

    p_circ_diluted = float((np.mean(full_deltas[circ_idx_5] > 0, axis=1) > 0).mean())
    p_mbb_diluted = non_wrapping_block_bootstrap_win_probability(full_deltas, block=5, seed=42)
    p_mbb_active_isolated = non_wrapping_block_bootstrap_win_probability(
        full_deltas, block=5, seed=42, active_mask=active_mask
    )

    # 3. Two-Season Stratified Gate Evaluation
    # Dev season (2025-26): true effect +0.35, std 1.2 (38 GWs)
    # Confirmation season (2024-25, warm-seeded): true effect +0.25, std 1.3 (38 GWs)
    dev_deltas = rng.normal(0.35, 1.2, size=38)
    conf_deltas = rng.normal(0.25, 1.3, size=38)

    p_dev = non_wrapping_block_bootstrap_win_probability(dev_deltas, block=5, seed=42)
    p_conf = non_wrapping_block_bootstrap_win_probability(conf_deltas, block=5, seed=43)
    p_pooled = stratified_block_bootstrap_win_probability(
        [dev_deltas, conf_deltas], block=5, seed=44
    )

    return {
        "wrapping_frequency": {
            "circular_L3": wrap_freq_circ_3,
            "circular_L5": wrap_freq_circ_5,
            "mbb_L5": wrap_freq_mbb_5,
        },
        "max_index": {
            "circular_L5": int(np.max(circ_idx_5)),
            "mbb_L5": int(np.max(mbb_idx_5)),
        },
        "dormant_fallback_dilution": {
            "circular_full_diluted": p_circ_diluted,
            "mbb_full_diluted": p_mbb_diluted,
            "mbb_active_isolated": p_mbb_active_isolated,
        },
        "two_season_gate": {
            "dev_win_p": p_dev,
            "conf_win_p": p_conf,
            "pooled_win_p": p_pooled,
            "thresholds": {"dev_min_p": 0.75, "conf_min_p": 0.65, "pooled_min_p": 0.85},
            "passed_dev": p_dev >= 0.75,
            "passed_conf": p_conf >= 0.65,
            "passed_pooled": p_pooled >= 0.85,
        },
    }


if __name__ == "__main__":
    results = run_bootstrap_simulation()
    print("=== Non-Wrapping Moving Block Bootstrap Simulation ===")
    print(f"Circular L=3 Wrapping Draws: {results['wrapping_frequency']['circular_L3'] * 100:.1f}%")
    print(f"Circular L=5 Wrapping Draws: {results['wrapping_frequency']['circular_L5'] * 100:.1f}%")
    print(f"Non-Wrapping MBB L=5 Wrapping Draws: {results['wrapping_frequency']['mbb_L5'] * 100:.1f}%")
    print(f"Max MBB Index (n=38): {results['max_index']['mbb_L5']} (Strictly < 38)")
    print("\n--- Dormant Fallback Dilution ---")
    print(f"Full-season diluted MBB Win P: {results['dormant_fallback_dilution']['mbb_full_diluted']:.4f}")
    print(f"Active-isolated MBB Win P:     {results['dormant_fallback_dilution']['mbb_active_isolated']:.4f}")
    print("\n--- Two-Season Stratified Bootstrap Gate ---")
    print(f"Dev Season Win P:    {results['two_season_gate']['dev_win_p']:.4f} (Bar: >= 0.75 -> {results['two_season_gate']['passed_dev']})")
    print(f"Confirm Season Win P: {results['two_season_gate']['conf_win_p']:.4f} (Bar: >= 0.65 -> {results['two_season_gate']['passed_conf']})")
    print(f"Pooled Stratified P:  {results['two_season_gate']['pooled_win_p']:.4f} (Bar: >= 0.85 -> {results['two_season_gate']['passed_pooled']})")

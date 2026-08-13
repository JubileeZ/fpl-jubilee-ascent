"""Refresh research artifacts that consume Stage 2 Event Rates (ADR-0014).

Does not scrape Stage 1 (HTTP). When roles change, run run_pipeline.py first
(or refresh_expected_role.py), add CAREER_INDIVIDUAL_RATES for any new Draft
player without a Prior-Season Seed, then run this script.

Order: Stage 2 → Stage 3 → GKP rotation → DEF rotation (incl. WC4 bridges)
→ ownership explorer (needs Stage 3 overlays).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _load(rel: str, attr: str):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, attr)


def main() -> None:
    sys.path.insert(0, str(ROOT))
    print("=== RESEARCH DOWNSTREAM REFRESH (Stage 2 rates → consumers) ===")

    print("\n--- Stage 2: Event Rates + GW1–5 xP ---")
    _load(
        "docs/research/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/build_expected_stats.py",
        "build_expected_stats",
    )()
    _load(
        "docs/research/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/project_expected_points.py",
        "project_gw1_5_points",
    )()

    print("\n--- Stage 3: GW1–6 chip matrix ---")
    _load(
        "docs/research/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/run_wc4_simulation.py",
        "run_full_wc4_study",
    )()

    print("\n--- GKP fixture rotation ---")
    gkp_df = _load(
        "docs/research/gkp-fixture-rotation/run_gkp_rotation_analysis.py",
        "run_analysis",
    )()
    print(f"Wrote {len(gkp_df)} GKP rotation rows")

    print("\n--- DEF fixture rotation (incl. WC4 bridges) ---")
    _load(
        "docs/research/def-fixture-rotation/run_def_rotation_analysis.py",
        "run_def_rotation_pipeline",
    )()

    print("\n--- Ownership Value Explorer ---")
    _load(
        "docs/research/ownership-value-explorer/plot_ownership_value_explorer.py",
        "main",
    )()

    print("\n=== DOWNSTREAM REFRESH COMPLETE ===")
    print("Update Findings tables in Stage 3 / GKP / DEF / ownership notes from the new CSVs.")


if __name__ == "__main__":
    main()

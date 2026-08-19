"""Refresh research artifacts that consume Stage 2 Event Rates (ADR-0014).

Does not scrape Stage 1 (HTTP). When roles change, run run_pipeline.py first
(or refresh_expected_role.py), add CAREER_INDIVIDUAL_RATES for any new Draft
player without a Prior-Season Seed, then run this script.

Order: Stage 2 → Stage 3 Canonical Preseason Chip Path → unified DCS defensive rotation
→ ownership explorer (needs Stage 3 overlays).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from clients.env_loader import configure_utf8_stdio


def _load(rel: str, attr: str):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, attr)


def main() -> None:
    configure_utf8_stdio()
    sys.path.insert(0, str(ROOT))
    print("=== RESEARCH DOWNSTREAM REFRESH (Stage 2 rates → consumers) ===")

    print("\n--- Stage 2: Event Rates + GW1–5 xP ---")
    summaries = list((ROOT / "data/raw").glob("element_summary_*.json"))
    if len(summaries) >= 100:
        _load(
            "docs/research/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/build_expected_stats.py",
            "build_expected_stats",
        )()
    else:
        print(
            f"Skip rate rebuild ({len(summaries)} element summaries). "
            "Using committed expected-stats-gw1-5.csv. Run full refresh_data for a rate rebuild."
        )
    _load(
        "docs/research/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/project_expected_points.py",
        "project_gw1_5_points",
    )()

    print("\n--- Stage 3: Canonical Preseason Chip Path ---")
    _load(
        "docs/research/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/run_wc4_simulation.py",
        "run_full_wc4_study",
    )()

    print("\n--- Defensive Architecture & Fixture Rotation (Unified GKP + DEF) ---")
    _load(
        "docs/research/defensive-fixture-rotation/run_defensive_rotation_analysis.py",
        "run_defensive_rotation_pipeline",
    )()

    print("\n--- Ownership Value Explorer ---")
    _load(
        "docs/research/ownership-value-explorer/plot_ownership_value_explorer.py",
        "main",
    )()

    print("\n=== DOWNSTREAM REFRESH COMPLETE ===")
    _load("docs/research/sync_live_research_figures.py", "sync_all")()
    print("Research figure caches synced from CSVs.")


if __name__ == "__main__":
    main()

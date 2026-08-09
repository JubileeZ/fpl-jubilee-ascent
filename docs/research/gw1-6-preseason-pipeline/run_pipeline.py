"""GW1–6 Preseason Pipeline Master Runner.

Automates the complete 3-stage research pipeline:
Stage 1: Dual-source Expected Role rebuild (FFS + Meerkat scrape)
Stage 2: Expected Stats & Points Projections (availability overlays applied)
Stage 3: 16-scenario chip exploration matrix (BB × FH3|TC3 × Haaland × Bruno × WC4 Opt1)
"""

from __future__ import annotations

import importlib.util

from pathlib import Path
import sys

def main():
    root_dir = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(root_dir))

    print("=== STARTING GW1–6 PRESEASON PIPELINE RUN ===")

    # Stage 1: Expected Role Refresh
    print("\n--- STAGE 1: Refreshing Expected Roles across 20 Premier League Clubs ---")
    stage1_spec = importlib.util.spec_from_file_location(
        "refresh_role",
        root_dir / "docs/research/gw1-6-preseason-pipeline/01-expected-role-gw1-5/refresh_expected_role.py"
    )
    stage1_mod = importlib.util.module_from_spec(stage1_spec)
    stage1_spec.loader.exec_module(stage1_mod)
    stage1_mod.refresh_expected_roles()

    # Stage 2: Expected Stats & Points Projections
    print("\n--- STAGE 2: Building Event Rates & Projecting Points ---")
    stats_spec = importlib.util.spec_from_file_location(
        "build_stats",
        root_dir / "docs/research/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/build_expected_stats.py"
    )
    stats_mod = importlib.util.module_from_spec(stats_spec)
    stats_spec.loader.exec_module(stats_mod)
    stats_mod.build_expected_stats()

    points_spec = importlib.util.spec_from_file_location(
        "project_points",
        root_dir / "docs/research/gw1-6-preseason-pipeline/02-expected-stats-gw1-5/project_expected_points.py"
    )
    points_mod = importlib.util.module_from_spec(points_spec)
    points_spec.loader.exec_module(points_mod)
    points_mod.project_gw1_5_points()

    # Stage 3: GW1-6 Chip & Wildcard Matrix Optimization
    print("\n--- STAGE 3: Executing GW1–6 Chip & Wildcard 3x2 Matrix Optimization ---")
    wc4_spec = importlib.util.spec_from_file_location(
        "run_wc4",
        root_dir / "docs/research/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/run_wc4_simulation.py"
    )
    wc4_mod = importlib.util.module_from_spec(wc4_spec)
    wc4_spec.loader.exec_module(wc4_mod)

    projections_df = wc4_mod.generate_gw1_6_projections()
    projections_path = root_dir / "data/research/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6_projections.csv"
    projections_path.parent.mkdir(parents=True, exist_ok=True)
    projections_df.to_csv(projections_path, index=False)

    wc4_mod.run_full_wc4_study()

    print("\n=== PIPELINE RUN COMPLETE! ALL ARTIFACTS REGENERATED AND SYNCED ===")

if __name__ == "__main__":
    main()

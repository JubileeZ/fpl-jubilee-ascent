"""Run First-Half Chip Path research suite (Dual-Vector seed → xP → chips). Live DCS is defensive-fixture-rotation."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from clients.env_loader import configure_utf8_stdio


def _load(name: str, file: str):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def main() -> None:
    configure_utf8_stdio()
    seed = _load("dv_seed", "build_dual_vector_seed.py")
    proj = _load("dv_proj", "project_gw1_19.py")
    chips = _load("dv_chips", "run_chip_path.py")
    seed.build_dual_vector_seed()
    proj.project_gw1_19()
    chips.run_chip_path()
    xi = _load("dv_select_11", "export_select_11.py")
    xi.export_select_11("WC4")
    sync_spec = importlib.util.spec_from_file_location(
        "sync_live_research_figures",
        Path(__file__).resolve().parents[1] / "sync_live_research_figures.py",
    )
    sync_mod = importlib.util.module_from_spec(sync_spec)
    assert sync_spec.loader is not None
    sync_spec.loader.exec_module(sync_mod)
    sync_mod.sync_all()


if __name__ == "__main__":
    main()

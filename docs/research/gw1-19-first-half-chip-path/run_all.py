"""Run First-Half Chip Path research suite (Dual-Vector seed → xP → chips → DCS)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(name: str, file: str):
    spec = importlib.util.spec_from_file_location(name, HERE / file)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def main() -> None:
    seed = _load("dv_seed", "build_dual_vector_seed.py")
    proj = _load("dv_proj", "project_gw1_19.py")
    chips = _load("dv_chips", "run_chip_path.py")
    dcs = _load("dv_dcs", "run_dual_vector_dcs.py")
    seed.build_dual_vector_seed()
    proj.project_gw1_19()
    chips.run_chip_path()
    dcs.run_dual_vector_dcs()


if __name__ == "__main__":
    main()

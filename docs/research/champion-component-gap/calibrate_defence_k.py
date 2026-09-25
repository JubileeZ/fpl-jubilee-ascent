"""Calibrate ``defence_link_challenger`` ``_CS_SCALE`` / ``_GC_SCALE`` from 2025-26.

Walk-forward with current scales →:
  - ``k_cs`` from ``mins_60`` / ``ALL`` ``xp_clean_sheet``
  - ``k_gc`` from ``mins_60`` GKP+DEF ``xp_conceded`` (sample-weighted)

Smallest move so ``|signed_bias|≤τ`` (else keep scale if already inside).
Patches ``models/defence_link_challenger.py``.

  uv run python docs/research/champion-component-gap/calibrate_defence_k.py
"""

from __future__ import annotations

import importlib.util
import math
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

TOPIC = Path(__file__).resolve().parent
MODEL_PATH = ROOT / "models" / "defence_link_challenger.py"
_BIAS_TAU = 0.05


def _load_runner():  # noqa: ANN201
    spec = importlib.util.spec_from_file_location("component_gap_runner", TOPIC / "runner.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load component-gap runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _patch_scales(*, k_cs: float, k_gc: float) -> None:
    text = MODEL_PATH.read_text(encoding="utf-8")
    patched, n_cs = re.subn(
        r"^(_CS_SCALE\s*=\s*)([0-9.]+)\s*$",
        rf"\g<1>{k_cs:.6f}",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    patched, n_gc = re.subn(
        r"^(_GC_SCALE\s*=\s*)([0-9.]+)\s*$",
        rf"\g<1>{k_gc:.6f}",
        patched,
        count=1,
        flags=re.MULTILINE,
    )
    if n_cs != 1 or n_gc != 1:
        raise RuntimeError(f"failed to patch scales in {MODEL_PATH} (cs={n_cs} gc={n_gc})")
    MODEL_PATH.write_text(patched, encoding="utf-8")


def _next_scale(*, old_k: float, proj: float, actual: float, label: str) -> float:
    bias = proj - actual
    print(
        f"  {label}: mean_proj={proj:.6f} mean_actual={actual:.6f} signed_bias={bias:+.6f}",
        flush=True,
    )
    if abs(bias) <= _BIAS_TAU:
        print(f"  {label}: already inside τ={_BIAS_TAU}; keep k={old_k:.6f}", flush=True)
        return old_k
    if abs(proj) <= 1e-12:
        raise RuntimeError(f"{label}: mean_projected ~0; cannot calibrate")
    target_bias = math.copysign(_BIAS_TAU, bias)
    target_proj = actual + target_bias
    factor = target_proj / proj
    new_k = max(0.0, old_k * factor)
    print(
        f"  {label}: k {old_k:.6f} → {new_k:.6f} (target bias {target_bias:+.2f})",
        flush=True,
    )
    return new_k


def _gkp_def_conceded(rows: list[dict[str, Any]]) -> tuple[float, float]:
    parts = [
        r
        for r in rows
        if r["pool"] == "mins_60"
        and r["position"] in {"GKP", "DEF"}
        and r["component"] == "xp_conceded"
    ]
    if len(parts) != 2:
        raise RuntimeError(f"expected GKP+DEF mins_60 xp_conceded rows, got {len(parts)}")
    n = sum(int(r["sample_count"]) for r in parts)
    if n <= 0:
        raise RuntimeError("GKP+DEF mins_60 xp_conceded sample_count=0")
    proj = sum(int(r["sample_count"]) * float(r["mean_projected"]) for r in parts) / n
    actual = sum(int(r["sample_count"]) * float(r["mean_actual"]) for r in parts) / n
    return proj, actual


def main() -> int:
    runner = _load_runner()
    print("Measuring defence_link_challenger 2025-26 defence bias (current k) …", flush=True)
    rows, _totals = runner.run_window(
        model_name="defence_link_challenger",
        evaluation_season="2025-26",
        seed_season="2024-25",
        gw_start=1,
        gw_end=38,
    )
    cs = next(
        r
        for r in rows
        if r["pool"] == "mins_60"
        and r["position"] == "ALL"
        and r["component"] == "xp_clean_sheet"
    )
    gc_proj, gc_actual = _gkp_def_conceded(rows)

    import models.defence_link_challenger as dlc

    old_cs = float(dlc._CS_SCALE)
    old_gc = float(dlc._GC_SCALE)
    new_cs = _next_scale(
        old_k=old_cs,
        proj=float(cs["mean_projected"]),
        actual=float(cs["mean_actual"]),
        label="k_cs (mins_60/ALL xp_clean_sheet)",
    )
    new_gc = _next_scale(
        old_k=old_gc,
        proj=gc_proj,
        actual=gc_actual,
        label="k_gc (mins_60 GKP+DEF xp_conceded)",
    )

    if abs(new_cs - old_cs) > 1e-9 or abs(new_gc - old_gc) > 1e-9:
        _patch_scales(k_cs=new_cs, k_gc=new_gc)
        print(
            f"Patched {MODEL_PATH} _CS_SCALE={new_cs:.6f} _GC_SCALE={new_gc:.6f}",
            flush=True,
        )
    else:
        print("No patch needed.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

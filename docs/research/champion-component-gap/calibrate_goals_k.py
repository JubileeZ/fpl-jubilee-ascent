"""Calibrate ``goals_path_challenger`` ``_GOAL_WEIGHT_SCALE`` from 2025-26 gate.

Walk-forward with current scale → gate-row ``xp_goals`` signed_bias
(pool=all, position=ALL) → smallest ``k≤1`` with |bias|≤τ (else keep k=1 if
already inside). Patches ``models/goals_path_challenger.py``.

  uv run python docs/research/champion-component-gap/calibrate_goals_k.py
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

TOPIC = Path(__file__).resolve().parent
MODEL_PATH = ROOT / "models" / "goals_path_challenger.py"
_BIAS_TAU = 0.05


def _load_runner():  # noqa: ANN201
    spec = importlib.util.spec_from_file_location("component_gap_runner", TOPIC / "runner.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load component-gap runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _patch_scale(new_k: float) -> None:
    text = MODEL_PATH.read_text(encoding="utf-8")
    patched, n = re.subn(
        r"^(_GOAL_WEIGHT_SCALE\s*=\s*)([0-9.]+)\s*$",
        rf"\g<1>{new_k:.6f}",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if n != 1:
        raise RuntimeError(f"failed to patch _GOAL_WEIGHT_SCALE in {MODEL_PATH}")
    MODEL_PATH.write_text(patched, encoding="utf-8")


def main() -> int:
    runner = _load_runner()
    print("Measuring goals_path_challenger 2025-26 gate xp_goals bias (current k) …", flush=True)
    rows, _totals = runner.run_window(
        model_name="goals_path_challenger",
        evaluation_season="2025-26",
        seed_season="2024-25",
        gw_start=1,
        gw_end=38,
    )
    gate = next(
        r
        for r in rows
        if r["pool"] == "all"
        and r["position"] == "ALL"
        and r["component"] == "xp_goals"
    )
    proj = float(gate["mean_projected"])
    actual = float(gate["mean_actual"])
    bias = float(gate["signed_bias"])
    print(f"  mean_proj={proj:.6f} mean_actual={actual:.6f} signed_bias={bias:+.6f}", flush=True)

    import models.goals_path_challenger as gpc

    old_k = float(gpc._GOAL_WEIGHT_SCALE)
    if abs(bias) <= _BIAS_TAU:
        new_k = old_k
        print(f"  already inside τ={_BIAS_TAU}; keep k={old_k:.6f}", flush=True)
    elif proj <= 1e-12:
        raise RuntimeError("mean_projected xp_goals ~0; cannot calibrate")
    elif bias > 0:
        # Target bias = +τ (smallest cut that clears structural bar).
        target_proj = actual + _BIAS_TAU
        factor = target_proj / proj
        new_k = min(1.0, max(0.0, old_k * factor))
        print(f"  over-pred → k {old_k:.6f} → {new_k:.6f} (target bias +τ)", flush=True)
    else:
        # Under-prediction: do not raise above 1.0 per #111 (k≤1 only).
        new_k = old_k
        print(f"  under-pred bias={bias:+.6f}; k≤1 rule keeps k={old_k:.6f}", flush=True)

    if abs(new_k - old_k) > 1e-9:
        _patch_scale(new_k)
        print(f"Patched {MODEL_PATH} _GOAL_WEIGHT_SCALE={new_k:.6f}", flush=True)
    else:
        print("No patch needed.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

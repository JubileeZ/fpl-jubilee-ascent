"""Readiness note caches use retained companion values."""

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

import pandas as pd
import pytest


def preflight_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    script = Path(__file__).resolve().parents[1] / "docs/research/backtesting-promotion-foundation/smoke_gate_preflight.py"
    spec = importlib.util.spec_from_file_location("smoke_preflight_report", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "TOPIC", tmp_path)
    companions: dict[str, list[dict[str, Any]]] = {
        "summary": [{"historical_pairs": 7, "unique_models": 3, "confirmation_passes": 2, "negative_confirmation_deltas": 4,
                      "positive_confirmation_rejections": 1, "recorded_retrieved_sources": 1, "recorded_missing_rows": 1,
                      "retained_recorded_raw_sources": 0, "inventory_rows": 24}],
        "probe_summary": [{"actual_calls": 4, "optimal_calls": 2, "censored_calls": 2, "elapsed_seconds": 3.25,
                            "matched_action_pairs": 1, "paired_problems": 2, "max_achieved_gap": 0.02}],
        "probe_timings": [{"problem_id": "one"}, {"problem_id": "two"}],
        "data_quality": [{"duplicate_keys": 2, "invalid_numeric_cells": 3}],
        "outcomes": [{"ledger_mismatch_rows": 1, "missing_player_ids": 1, "missing_fixture_ids": 2}],
        "calibration": [{"ar1_rho": 0.0, "true_mean_delta_pts_per_gw": 0.0, "marginal_sd_pts_per_gw": 4.0,
                         "seasons": 2, "gws_per_season": 38, "simulations": 50, "bootstrap_draws": 250,
                         "family_budget": 1, "superiority_rejections": 1, "per_attempt_rejection_rate": 0.02,
                         "wilson95_lower": 0.0035, "wilson95_upper": 0.105}],
    }
    for name, rows in companions.items():
        pd.DataFrame(rows).to_csv(tmp_path / f"smoke_gate_{name}.csv", index=False)
    (tmp_path / "smoke_gate_probe_environment.json").write_text("{}\n")
    return module


def test_report_uses_nondefault_settings_and_observed_results(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = preflight_report(tmp_path, monkeypatch)
    module.render_report()
    text = (tmp_path / "smoke_gate_preflight.md").read_text()
    assert "50 independent trajectory replicates" in text
    assert "250 draws" in text
    assert "2 duplicate inspected table keys" in text
    assert "1 native ledger mismatch" in text
    assert "1/2 paired immediate-action digests matched" in text
    assert "maximum achieved gap 0.02" in text
    assert "All paired immediate-action digests matched" not in text


def test_inconsistent_calibration_settings_do_not_replace_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = preflight_report(tmp_path, monkeypatch)
    path = tmp_path / "smoke_gate_calibration.csv"
    rows = module.read_csv(path)
    pd.DataFrame([rows[0], {**rows[0], "bootstrap_draws": "251"}]).to_csv(path, index=False)
    report = tmp_path / "smoke_gate_preflight.md"
    report.write_text("previous report\n")
    with pytest.raises(ValueError, match="Inconsistent calibration setting: bootstrap_draws"):
        module.render_report()
    assert report.read_text() == "previous report\n"


def test_probe_worker_requires_unused_authorized_attempt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = preflight_report(tmp_path, monkeypatch)
    monkeypatch.setattr(module, "REPORTS", tmp_path)
    (tmp_path / "probe_started.json").write_text("{}\n")
    (tmp_path / "probe_progress.json").write_text("[]\n")
    with pytest.raises(ValueError, match="unused authorized"):
        module.probe_worker()

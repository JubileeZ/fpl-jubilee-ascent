"""Explore-candidate smoke harness: resumable output + single confirm look."""

from __future__ import annotations

import csv
import importlib.util
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pandas as pd
import pytest

from backtesting.walkforward import WalkforwardResult
from backtesting.smoke_diagnostics import versioned_output

SMOKE_PATH = Path(__file__).resolve().parents[1] / ".agents/skills/explore-candidate/smoke.py"


def _smoke() -> ModuleType:
    spec = importlib.util.spec_from_file_location("explore_candidate_smoke", SMOKE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _row(variant: str, season: str = "dev", data_season: str = "2025-26", champion: str = "champ", gw_range: str = "1-38") -> dict[str, str]:
    return {"season": season, "data_season": data_season, "variant": variant, "champion": champion, "gw_range": gw_range}


def test_confirm_blocked_when_any_prior_gate_file_holds_model(tmp_path: Path) -> None:
    smoke, gate = _smoke(), tmp_path / "other-topic" / "candidate_gate.csv"
    gate.parent.mkdir()
    row = _row("zz_frozen_candidate", season="confirm", data_season="2024-25")
    with gate.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
    issues = smoke.confirm_violations(["zz_frozen_candidate"], None, tmp_path / "fresh" / "candidate_gate.csv", True, "2024-25", prior_gates=[gate])
    assert any("already run" in issue for issue in issues)


def _fake_main(smoke: ModuleType, monkeypatch, tmp_path: Path, leaky: set[str]) -> None:
    def fake_run(job: tuple) -> tuple[str, WalkforwardResult]:
        if job[0] in leaky:
            raise smoke.LeakageError(f"{job[0]} leaked")
        name = job[0]
        predictions = [2.0] * 11 + [1.0, 0.0]
        if name == "a":
            predictions = [2.0] * 10 + [1.0, 3.0, 0.0]
        elif name == "b":
            predictions = [2.0] * 10 + [1.0, 0.0, 3.0]
        frame = pd.DataFrame([
            {"gameweek": gw, "player_id": i, "projected_points": prediction, "blended_points": target, "actual_minutes": 90.0}
            for gw in range(1, 39) for i, (prediction, target) in enumerate(zip(predictions, [1.0] * 11 + [2.0, 0.0], strict=True))
        ])
        return name, WalkforwardResult(name, tmp_path, 1, 38, {}, frame, {}, False)

    monkeypatch.setattr(smoke, "resolve_seasons", lambda: ({"dev": smoke.Season("2025-26", tmp_path, None, 38)}, []))
    monkeypatch.setattr(smoke, "load_model_selection", lambda: SimpleNamespace(champion="champ"))
    monkeypatch.setattr(smoke, "ProcessPoolExecutor", ThreadPoolExecutor)
    monkeypatch.setattr(smoke, "_init_worker", lambda _path: None)
    monkeypatch.setattr(smoke, "_run", fake_run)
    monkeypatch.setattr(smoke, "input_identity", lambda *_args: {"test_fixture": "v1"})
    monkeypatch.setattr(smoke, "compare_to_reference", lambda _ref, cand, **_kwargs: SimpleNamespace(
        passed=cand.model_name == "a", combined_primary_delta={"a": 1.0, "b": -1.0, "c": 0.0}[cand.model_name],
        min_effect=0.0, segment_wins=2, bootstrap_p=0.9, guardrails_passed=True, reasons=[]))


def _variants(out: Path) -> list[str]:
    output = versioned_output(out)
    return sorted(r["variant"] for r in csv.DictReader(output.read_text().splitlines()) if r["execution_status"] == "complete" and r["terminal"] == "True") if output.exists() else []


def test_main_variant_leak_keeps_other_rows_and_exits_2(tmp_path: Path, monkeypatch) -> None:
    smoke, out = _smoke(), tmp_path / "smoke.csv"
    _fake_main(smoke, monkeypatch, tmp_path, leaky={"b"})
    monkeypatch.setattr(sys, "argv", ["smoke.py", "--model", "a", "--model", "b", "--model", "c", "--out", str(out), "--workers", "2"])
    assert smoke.main() == 2
    assert _variants(out) == ["a", "c"]


def test_main_champion_leak_exits_2_without_rows(tmp_path: Path, monkeypatch) -> None:
    smoke, out = _smoke(), tmp_path / "smoke.csv"
    _fake_main(smoke, monkeypatch, tmp_path, leaky={"champ"})
    monkeypatch.setattr(sys, "argv", ["smoke.py", "--model", "a", "--out", str(out), "--workers", "1"])
    assert smoke.main() == 2
    assert _variants(out) == []


def test_main_rerun_skips_done_variants(tmp_path: Path, monkeypatch) -> None:
    smoke, out = _smoke(), tmp_path / "smoke.csv"
    _fake_main(smoke, monkeypatch, tmp_path, leaky=set())
    monkeypatch.setattr(sys, "argv", ["smoke.py", "--model", "a", "--out", str(out), "--workers", "1"])
    assert smoke.main() == 0
    monkeypatch.setattr(sys, "argv", ["smoke.py", "--model", "a", "--model", "b", "--out", str(out), "--workers", "1"])
    assert smoke.main() == 0
    assert _variants(out) == ["a", "b"]


def test_confirm_allowed_for_new_model(tmp_path: Path) -> None:
    smoke = _smoke()
    issues = smoke.confirm_violations(["zz_never_confirmed"], None, tmp_path / "fresh" / "candidate_gate.csv", True, "2024-25", prior_gates=[])
    assert issues == []


def test_count_grid_positives_reports_lane_positives_without_blocking_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    smoke, out = _smoke(), tmp_path / "smoke.csv"
    _fake_main(smoke, monkeypatch, tmp_path, leaky=set())

    deltas = {"a": 1.0, "b": -1.0, "c": 0.0}

    def fake_compare(_base: WalkforwardResult, cand: WalkforwardResult, **_k: object) -> SimpleNamespace:
        d = deltas[cand.model_name]
        return SimpleNamespace(
            passed=d > 0,
            combined_primary_delta=d,
            min_effect=0.0,
            segment_wins=2 if d > 0 else 0,
            bootstrap_p=0.82 if d > 0 else 0.10,
            guardrails_passed=True,
            reasons=[],
        )

    monkeypatch.setattr(smoke, "compare_to_reference", fake_compare)
    monkeypatch.setattr(
        sys,
        "argv",
        ["smoke.py", "--model", "a", "--model", "b", "--model", "c", "--out", str(out), "--workers", "1"],
    )
    assert smoke.main() == 0
    captured = capsys.readouterr().out
    assert "grid_positives=1/3" in captured
    assert smoke.count_grid_positives(
        out, season="dev", data_season="2025-26", champion="champ", gw_range="1-38", variants=["a", "b", "c"]
    ) == 1
    rows = {r["variant"]: r for r in csv.DictReader(versioned_output(out).read_text().splitlines())}
    assert rows["a"]["pass"] == "True"


def test_smoke_retains_oracle_success_when_integrated_screen_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from backtesting.metrics import evaluate_predictions
    from backtesting.model_evaluation import compare_to_reference

    smoke, out = _smoke(), tmp_path / "stages.csv"
    _fake_main(smoke, monkeypatch, tmp_path, leaky=set())

    def run(job: tuple) -> tuple[str, WalkforwardResult]:
        name, _season, _start, _end, oracle = job
        frame = pd.DataFrame([
            {"player_id": player, "gameweek": gw, "projected_points": projection,
             "blended_points": target, "actual_minutes": minutes}
            for gw in range(1, 39)
            for player, (projection, target, minutes) in enumerate(zip(
                [8.0] + [2.0] * 9 + [1.0] * 90,
                [5.0] + [2.0] * 9 + [1.0] * 89 + [4.0],
                [90.0] * 10 + [10.0] * 89 + [90.0], strict=True))
        ])
        if name == "a":
            frame["projected_points"] = frame["blended_points"] if oracle else (frame["actual_minutes"] < 30).astype(float) * 10
        metrics = evaluate_predictions(frame, target_column="blended_points")
        metrics.update(oracle_formation_xi_regret=metrics["top_11_regret"], oracle_captain_regret=0.0)
        return name, WalkforwardResult(name, tmp_path, 1, 38, metrics, frame, {}, False)

    monkeypatch.setattr(smoke, "_run", run)
    monkeypatch.setattr(smoke, "compare_to_reference", compare_to_reference)
    monkeypatch.setattr(sys, "argv", ["smoke.py", "--model", "a", "--tier", "2", "--out", str(out), "--workers", "1"])
    assert smoke.main() == 0
    rows = list(csv.DictReader(versioned_output(out).open()))
    assert [(row["stage"], row["pass"]) for row in rows] == [("queued", ""), ("oracle", "True"), ("integrated", "False")]
    assert rows[1]["segs"] == ""
    assert float(rows[1]["combined_delta"]) == 3.0
    assert float(rows[2]["combined_delta"]) < 0
    assert all(row["scientific_verdict"] == "inconclusive" for row in rows)


def test_null_oracle_metric_is_retained_as_invalid_stage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    smoke, out = _smoke(), tmp_path / "null.csv"
    _fake_main(smoke, monkeypatch, tmp_path, leaky=set())
    original = smoke._run

    def run(job: tuple) -> tuple[str, WalkforwardResult]:
        name, result = original(job)
        result.metrics.update(oracle_formation_xi_regret=None, oracle_captain_regret=0.0)
        return name, result

    monkeypatch.setattr(smoke, "_run", run)
    monkeypatch.setattr(sys, "argv", ["smoke.py", "--model", "a", "--tier", "2", "--out", str(out), "--workers", "1"])
    assert smoke.main() == 2
    rows = list(csv.DictReader(versioned_output(out).open()))
    assert rows[-1]["stage"] == "oracle"
    assert rows[-1]["execution_status"] == "partial"
    assert rows[-1]["scientific_verdict"] == "invalid"
    assert rows[-1]["combined_delta"] == ""


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

SMOKE_PATH = Path(__file__).resolve().parents[1] / ".agents/skills/explore-candidate/smoke.py"


def _smoke() -> ModuleType:
    spec = importlib.util.spec_from_file_location("explore_candidate_smoke", SMOKE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _row(variant: str, season: str = "dev", data_season: str = "2025-26", champion: str = "champ", gw_range: str = "1-38") -> dict[str, str]:
    return {"season": season, "data_season": data_season, "variant": variant, "champion": champion, "gw_range": gw_range}


def test_append_row_writes_header_once_and_keeps_rows(tmp_path: Path) -> None:
    smoke, out = _smoke(), tmp_path / "lane" / "smoke.csv"
    smoke.append_row(out, _row("a"))
    smoke.append_row(out, _row("b"))
    rows = list(csv.DictReader(out.read_text().splitlines()))
    assert [r["variant"] for r in rows] == ["a", "b"]


def test_done_variants_matches_run_key_only(tmp_path: Path) -> None:
    smoke, out = _smoke(), tmp_path / "smoke.csv"
    for row in (_row("a"), _row("b", champion="old"), _row("c", gw_range="1-10"), _row("d", season="confirm"), _row("e", data_season="2024-25")):
        smoke.append_row(out, row)
    assert smoke.done_variants(out, season="dev", data_season="2025-26", champion="champ", gw_range="1-38") == {"a"}


def test_done_variants_missing_file_is_empty(tmp_path: Path) -> None:
    assert _smoke().done_variants(tmp_path / "none.csv", season="dev", data_season="2025-26", champion="c", gw_range="1-38") == set()


def test_confirm_blocked_when_any_prior_gate_file_holds_model(tmp_path: Path) -> None:
    smoke, gate = _smoke(), tmp_path / "other-topic" / "candidate_gate.csv"
    smoke.append_row(gate, _row("zz_frozen_candidate", season="confirm", data_season="2024-25"))
    issues = smoke.confirm_violations(["zz_frozen_candidate"], None, tmp_path / "fresh" / "candidate_gate.csv", True, "2024-25", prior_gates=[gate])
    assert any("already run" in issue for issue in issues)


def _fake_main(smoke: ModuleType, monkeypatch, tmp_path: Path, leaky: set[str]) -> None:
    def fake_run(job: tuple) -> tuple[str, str]:
        if job[0] in leaky:
            raise smoke.LeakageError(f"{job[0]} leaked")
        return job[0], job[0]

    verdict = SimpleNamespace(passed=True, combined_primary_delta=0.1, min_effect=0.0, segment_wins=2, bootstrap_p=0.9, guardrails_passed=True, reasons=[])
    monkeypatch.setattr(smoke, "resolve_seasons", lambda: ({"dev": smoke.Season("2025-26", tmp_path, None, 38)}, []))
    monkeypatch.setattr(smoke, "load_model_selection", lambda: SimpleNamespace(champion="champ"))
    monkeypatch.setattr(smoke, "ProcessPoolExecutor", ThreadPoolExecutor)
    monkeypatch.setattr(smoke, "_init_worker", lambda _path: None)
    monkeypatch.setattr(smoke, "_run", fake_run)
    monkeypatch.setattr(smoke, "compare_to_reference", lambda *_a, **_k: verdict)


def _variants(out: Path) -> list[str]:
    return sorted(r["variant"] for r in csv.DictReader(out.read_text().splitlines())) if out.exists() else []


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


def test_oracle_gw_deltas_keyed_by_gameweek(monkeypatch: pytest.MonkeyPatch) -> None:
    smoke = _smoke()
    champ_regrets = pd.Series({1: 5.0, 2: 6.0, 3: 4.0})
    cand_regrets = pd.Series({1: 4.5, 2: 6.5, 3: 3.0})

    def fake_formation_regret(df: pd.DataFrame, *, target_column: str = "actual_points") -> pd.Series:
        if "is_cand" in df.columns:
            return cand_regrets
        return champ_regrets

    monkeypatch.setattr(smoke, "formation_xi_regret_by_gameweek", fake_formation_regret)

    df_champ = pd.DataFrame({"gameweek": [1, 2, 3]})
    df_cand = pd.DataFrame({"gameweek": [1, 2, 3], "is_cand": [True, True, True]})

    all_gws, gw_deltas = smoke.oracle_gw_deltas(df_champ, df_cand, target_column="blended_points")
    assert all_gws == [1, 2, 3]
    assert gw_deltas == pytest.approx([0.5, -0.5, 1.0])


def test_oracle_gw_deltas_mean_matches_oracle_delta(monkeypatch: pytest.MonkeyPatch) -> None:
    smoke = _smoke()
    champ_regrets = pd.Series({1: 10.0, 2: 12.0, 3: 14.0})
    cand_regrets = pd.Series({1: 9.0, 2: 11.5, 3: 13.0})

    monkeypatch.setattr(smoke, "formation_xi_regret_by_gameweek", lambda df, **k: cand_regrets if "is_cand" in df.columns else champ_regrets)

    df_champ = pd.DataFrame({"gameweek": [1, 2, 3]})
    df_cand = pd.DataFrame({"gameweek": [1, 2, 3], "is_cand": [True, True, True]})

    all_gws, gw_deltas = smoke.oracle_gw_deltas(df_champ, df_cand, target_column="blended_points")
    expected_mean = float(champ_regrets.mean() - cand_regrets.mean())
    assert float(pd.Series(gw_deltas).mean()) == pytest.approx(expected_mean)


def test_oracle_gw_deltas_uses_target_column(monkeypatch: pytest.MonkeyPatch) -> None:
    smoke = _smoke()
    recorded_targets: list[str] = []

    def fake_formation_regret(df: pd.DataFrame, *, target_column: str = "actual_points") -> pd.Series:
        recorded_targets.append(target_column)
        return pd.Series({1: 1.0})

    monkeypatch.setattr(smoke, "formation_xi_regret_by_gameweek", fake_formation_regret)

    df_champ = pd.DataFrame({"gameweek": [1]})
    df_cand = pd.DataFrame({"gameweek": [1]})

    smoke.oracle_gw_deltas(df_champ, df_cand, target_column="blended_points")
    assert recorded_targets == ["blended_points", "blended_points"]


def test_count_grid_positives_reports_lane_positives_without_blocking_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    smoke, out = _smoke(), tmp_path / "smoke.csv"
    _fake_main(smoke, monkeypatch, tmp_path, leaky=set())

    deltas = {"a": 0.12, "b": -0.20, "c": -0.05}

    def fake_compare(_base: str, cand: str, **_k: object) -> SimpleNamespace:
        d = deltas[cand]
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
    rows = {r["variant"]: r for r in csv.DictReader(out.read_text().splitlines())}
    assert rows["a"]["pass"] == "True"


import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "docs/research/backtesting-promotion-foundation/acquire_admission_sources.py"
)


def load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("acquisition", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prepare(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    module = load_module()
    monkeypatch.setattr(module, "TOPIC", tmp_path)
    monkeypatch.setattr(module, "OUTPUT", tmp_path / "raw")
    (tmp_path / "acquisition_manifest.csv").write_text(
        "season,origin,kind,status,url,commit,blob,recorded_commit_utc,capture_utc,publication_uncertainty,retrieval_utc,raw_sha256,decompressed_sha256,bytes,parser,path,parent_refs,detail\n2025-26,gw01,opening_bootstrap,missing,,,,,,,,,,,,,,\n",
        encoding="utf-8",
    )
    return module


def test_unknown_option_never_fetches() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--unknown"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 2
    assert "unrecognized arguments" in result.stderr


def test_pilot_hash_failure_is_logged_without_raw_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = prepare(tmp_path, monkeypatch)

    class Response:
        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *args: object) -> bool:
            return False

        def read(self, limit: int) -> bytes:
            return b"incorrect bytes"

    monkeypatch.setattr(module, "urlopen", lambda *args, **kwargs: Response())
    module.pilot()
    attempts = [
        json.loads(line)
        for line in (tmp_path / "raw/retrieval-attempts.jsonl").read_text().splitlines()
    ]
    assert [row["event"] for row in attempts] == ["start", "finish", "start", "finish"]
    assert all(
        "Git blob mismatch" in row["detail"]
        for row in attempts
        if row["event"] == "finish"
    )
    assert not list((tmp_path / "raw").rglob("bootstrap.json.xz"))
    assert (
        "Pilot latest status: 0/2 retrieved"
        in (tmp_path / "acquisition-report.md").read_text()
    )


def test_interrupt_logs_start_and_interrupted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = prepare(tmp_path, monkeypatch)

    def interrupt(*args: object, **kwargs: object) -> None:
        raise KeyboardInterrupt

    monkeypatch.setattr(module, "urlopen", interrupt)
    with pytest.raises(KeyboardInterrupt):
        module.pilot()
    attempts = [
        json.loads(line)
        for line in (tmp_path / "raw/retrieval-attempts.jsonl").read_text().splitlines()
    ]
    assert [row["event"] for row in attempts] == ["start", "interrupted"]
    assert attempts[0]["attempt_id"] == attempts[1]["attempt_id"]


def test_report_counts_by_kind(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = prepare(tmp_path, monkeypatch)
    rows = [
        {
            "kind": "opening_bootstrap",
            "status": "retrieved_unadmitted",
            "season": "test",
            "origin": "gw01",
            "bytes": "",
            "detail": "",
        }
        for _ in range(3)
    ]
    rows += [
        {
            "kind": kind,
            "status": "retrieved_unadmitted",
            "season": "test",
            "origin": "gw02",
            "bytes": "",
            "detail": "",
        }
        for kind in ("origin_bootstrap_pilot", "fixture_pilot")
    ]
    module.report(rows)
    report = (tmp_path / "acquisition-report.md").read_text(encoding="utf-8")
    assert "Opening latest status: 3/3 retrieved" in report
    assert "Pilot latest status: 2/2 retrieved" in report
    rows[-1]["status"] = "failed"
    module.report(rows)
    assert "Pilot latest status: 1/2 retrieved" in (
        tmp_path / "acquisition-report.md"
    ).read_text(encoding="utf-8")

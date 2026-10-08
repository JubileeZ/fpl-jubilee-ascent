import threading
from pathlib import Path
from typing import Any

import pytest

from dashboard.planner_jobs import PlannerJobs


def test_job_survives_new_reader_and_completes_without_poll_limit(tmp_path: Path) -> None:
    entered, release = threading.Event(), threading.Event()

    def worker(request: dict[str, Any]) -> dict[str, Any]:
        entered.set()
        assert release.wait(5)
        return {"plans": {"optimal": {"weeks": [{"gw": 6}]}}}

    jobs = PlannerJobs(tmp_path)
    job_id = jobs.start({"snapshot": "original"}, worker)
    assert entered.wait(5)
    reader = PlannerJobs(tmp_path)
    assert reader.status(job_id)["status"] == "running"
    with pytest.raises(ValueError, match="running"):
        reader.start({}, worker)
    release.set()
    assert jobs.wait(job_id, timeout=5)["status"] == "finished"
    assert reader.status(job_id)["result"]["plans"]["optimal"]["weeks"] == [{"gw": 6}]


def test_failed_job_preserves_other_completed_results(tmp_path: Path) -> None:
    jobs = PlannerJobs(tmp_path)
    completed = jobs.start({}, lambda request: {"plans": {"optimal": "saved"}})
    jobs.wait(completed, timeout=5)

    def failed(request: dict[str, Any]) -> dict[str, Any]:
        raise ValueError("Infeasible manual choices")

    job_id = jobs.start({}, failed)
    assert jobs.wait(job_id, timeout=5)["status"] == "failed"
    assert jobs.status(completed)["result"]["plans"]["optimal"] == "saved"


def test_unchanged_solver_inputs_use_completed_job_cache(tmp_path: Path) -> None:
    jobs = PlannerJobs(tmp_path)
    request = {"kind": "solve", "snapshot": "same", "source_digest": "same-data"}
    job_id = jobs.start(request, lambda payload: {"plans": {"optimal": "saved"}, "errors": {}})
    jobs.wait(job_id, timeout=5)

    def unexpected(request: dict[str, Any]) -> dict[str, Any]:
        raise AssertionError("Unchanged inputs must not re-solve.")

    assert jobs.start(request, unexpected) == job_id

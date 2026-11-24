import shutil
from pathlib import Path

from filelock import FileLock
import pytest

from backtesting.verification_cache import verification_call_scope
from solver.parallelism import recommended_pytest_workers


def pytest_xdist_auto_num_workers(config: pytest.Config) -> int:
    """Size `-n auto` by physical / P-core / cgroup CPU capacity across OSes."""
    del config
    return recommended_pytest_workers()


@pytest.fixture(scope="session")
def retained_template(tmp_path_factory: pytest.TempPathFactory, worker_id: str) -> Path:
    """Generate real forecasts and native replay evidence once across all xdist workers."""
    from promotion_evidence_fixture import build_evidence_fixture

    if worker_id == "master":
        with verification_call_scope():
            return build_evidence_fixture(tmp_path_factory.mktemp("retained-promotion"))

    shared_root = tmp_path_factory.getbasetemp().parent / "retained-promotion-shared"
    shared_root.mkdir(parents=True, exist_ok=True)
    ready_file = shared_root / ".ready"
    with FileLock(str(shared_root.with_suffix(".lock"))):
        if ready_file.is_file():
            return shared_root / ready_file.read_text(encoding="utf-8").strip()
        with verification_call_scope():
            req_path = build_evidence_fixture(shared_root)
        ready_file.write_text(req_path.name, encoding="utf-8")
        return req_path


@pytest.fixture
def retained_request(retained_template: Path, tmp_path: Path) -> Path:
    """Give each test its own registry and evidence files to modify."""
    destination = tmp_path / "evidence"
    shutil.copytree(retained_template.parent, destination)
    return destination / retained_template.name

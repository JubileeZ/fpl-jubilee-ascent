import shutil
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def retained_template(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Generate real forecasts and native replay evidence once per pytest session."""
    from promotion_evidence_fixture import build_evidence_fixture

    return build_evidence_fixture(tmp_path_factory.mktemp("retained-promotion"))


@pytest.fixture
def retained_request(retained_template: Path, tmp_path: Path) -> Path:
    """Give each test its own registry and evidence files to modify."""
    destination = tmp_path / "evidence"
    shutil.copytree(retained_template.parent, destination)
    return destination / retained_template.name

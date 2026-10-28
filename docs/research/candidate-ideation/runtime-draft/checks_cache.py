from __future__ import annotations

import multiprocessing
import os
import pickle
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cache import FeatureCache, install


def _archive(root: Path, season: str, *, finished: bool = True) -> Path:
    processed = root / season / "processed"
    processed.mkdir(parents=True)
    pd.DataFrame({"finished": [finished]}).to_parquet(processed / "fixtures.parquet")
    pd.DataFrame({"value": [1]}).to_parquet(processed / "players.parquet")
    return processed


def _builder(
    processed_dir: Path,
    target_gw: int,
    horizon: int = 1,
    seed_processed_dir: Path | None = None,
    use_archive_seed: bool = False,
    as_of_gw: int | None = 1,
    target_deadline: datetime | str | None = None,
    availability_snapshot_root: Path | None = None,
    require_availability_snapshot: bool = False,
    availability_overrides: Path | None = None,
    xmins_override: Path | str | None = None,
    expected_role_table: Path | None = None,
    minutes_prior_source: str = "seed_state",
    seed_season: str | None = None,
) -> pd.DataFrame:
    count = processed_dir / "calls.txt"
    with count.open("a") as handle:
        handle.write("call\n")
        handle.flush()
        os.fsync(handle.fileno())
    time.sleep(0.02)
    index = pd.Index([7, 2], name="feature_row", dtype="int32")
    out = pd.DataFrame({
        "nullable": pd.array([target_gw, None], dtype="int64[pyarrow]"),
        "label": pd.array(["a", None], dtype="string[pyarrow]"),
        "flag": pd.array([True, None], dtype="boolean[pyarrow]"),
        "object": [{"x": [1, 2]}, {"x": []}],
    }, index=index)
    out.attrs = {"cutoff": as_of_gw, "deadline": target_deadline,
                 "seed": None if seed_processed_dir is None else str(seed_processed_dir),
                 "nested": {"array": np.array([1.0, np.nan])}}
    return out


@pytest.fixture
def setup(tmp_path: Path) -> tuple[FeatureCache, Path, Path, Path]:
    root = tmp_path / "archive"
    data, seed = _archive(root, "2010-11"), _archive(root, "2009-10")
    source = tmp_path / "builder_source.py"
    source.write_text("version = 1\n")
    wrapper = FeatureCache(_builder, allowed_dirs=[data, seed], cache_dir=tmp_path / "frames",
                           archive_root=root, source_paths=[source])
    return wrapper, data, seed, source


def _calls(data: Path) -> int:
    path = data / "calls.txt"
    return len(path.read_text().splitlines()) if path.exists() else 0


def test_bound_arguments_and_point_in_time_isolation(setup: tuple[FeatureCache, Path, Path, Path]) -> None:
    wrapper, data, seed, _ = setup
    deadline = datetime(2010, 8, 1, 12, tzinfo=UTC)
    first = wrapper(data, 5, seed_processed_dir=seed, as_of_gw=5, target_deadline=deadline)
    second = wrapper(processed_dir=data, target_gw=5, horizon=1, seed_processed_dir=seed,
                     use_archive_seed=False, as_of_gw=5, target_deadline=deadline)
    pd.testing.assert_frame_equal(first, second, check_exact=True)
    assert _calls(data) == 1
    for changed in ({"target_gw": 6}, {"as_of_gw": 4}, {"horizon": 2},
                    {"target_deadline": "different"}, {"seed_processed_dir": None}):
        arguments = {"processed_dir": data, "target_gw": 5, "seed_processed_dir": seed,
                     "as_of_gw": 5, "target_deadline": deadline}
        arguments.update(changed)
        wrapper(**arguments)
    assert _calls(data) == 6


def test_exact_arrow_index_attrs_and_mutation_isolation(setup: tuple[FeatureCache, Path, Path, Path]) -> None:
    wrapper, data, _, _ = setup
    first = wrapper(data, 5)
    original = pickle.loads(pickle.dumps(first, protocol=5))
    first.iloc[0, 0] = 999
    first.loc[7, "object"]["x"].append(99)
    first.attrs["nested"]["array"][0] = 99
    second = wrapper(data, 5)
    pd.testing.assert_frame_equal(original, second, check_exact=True, check_dtype=True, check_index_type=True)
    assert pickle.dumps(original.attrs, protocol=5) == pickle.dumps(second.attrs, protocol=5)
    assert str(second["nullable"].dtype) == "int64[pyarrow]"
    assert second.index.dtype == np.dtype("int32")
    assert _calls(data) == 1


def test_source_data_seed_and_new_file_invalidation(setup: tuple[FeatureCache, Path, Path, Path]) -> None:
    wrapper, data, seed, source = setup
    wrapper(data, 5, seed_processed_dir=seed)
    source.write_text("version = 2\n")
    wrapper(data, 5, seed_processed_dir=seed)
    pd.DataFrame({"value": [2, 3]}).to_parquet(data / "players.parquet")
    wrapper(data, 5, seed_processed_dir=seed)
    pd.DataFrame({"value": [4]}).to_parquet(seed / "players.parquet")
    wrapper(data, 5, seed_processed_dir=seed)
    pd.DataFrame({"value": [5]}).to_parquet(data / "additional.parquet")
    wrapper(data, 5, seed_processed_dir=seed)
    assert _calls(data) == 5


@pytest.mark.parametrize("changed", [
    {"availability_snapshot_root": Path("snapshots")}, {"require_availability_snapshot": True},
    {"availability_overrides": Path("overrides")}, {"xmins_override": "minutes.csv"},
    {"expected_role_table": Path("roles.csv")}, {"minutes_prior_source": "expected_role"},
    {"use_archive_seed": True}, {"seed_season": "unresolved"}, {"as_of_gw": None},
])
def test_unsupported_paths_and_modes_bypass(
    setup: tuple[FeatureCache, Path, Path, Path], changed: dict[str, object],
) -> None:
    wrapper, data, _, _ = setup
    wrapper(data, 5, **changed)
    wrapper(data, 5, **changed)
    assert _calls(data) == 2
    assert not wrapper.cache_dir.exists()


def test_live_unrecognized_and_unlisted_seed_bypass(setup: tuple[FeatureCache, Path, Path, Path]) -> None:
    wrapper, data, _, _ = setup
    live = _archive(wrapper.archive_root, "2011-12", finished=False)
    unlisted = _archive(wrapper.archive_root, "2008-09")
    wrapper.allowed = wrapper.allowed | {live}
    for path in (live, unlisted):
        wrapper(path, 5)
        wrapper(path, 5)
        assert _calls(path) == 2
    wrapper(data, 5, seed_processed_dir=unlisted)
    wrapper(data, 5, seed_processed_dir=unlisted)
    assert _calls(data) == 2
    pd.DataFrame({"finished": [False]}).to_parquet(data / "fixtures.parquet")
    wrapper(data, 5)
    wrapper(data, 5)
    assert _calls(data) == 4


def test_operational_path_bypasses_even_if_explicitly_listed(setup: tuple[FeatureCache, Path, Path, Path]) -> None:
    wrapper, _, _, _ = setup
    operational = wrapper.archive_root.parent / "operational" / "processed"
    operational.mkdir(parents=True)
    pd.DataFrame({"finished": [True]}).to_parquet(operational / "fixtures.parquet")
    wrapper.allowed = wrapper.allowed | {operational.resolve()}
    wrapper(operational, 5)
    wrapper(operational, 5)
    assert _calls(operational) == 2


def test_install_is_idempotent_and_changes_only_walkforward_alias(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from backtesting import walkforward
    from features import builder

    original = builder.build_features
    monkeypatch.setattr(walkforward, "build_features", original)
    first = install(allowed_dirs=[], cache_dir=tmp_path / "install-frames")
    second = install(allowed_dirs=[], cache_dir=tmp_path / "other-frames")
    assert first is second is walkforward.build_features
    assert builder.build_features is original
    assert first.original is original


def test_corrupt_payload_rebuilds_without_partial_publication(setup: tuple[FeatureCache, Path, Path, Path]) -> None:
    wrapper, data, _, _ = setup
    expected = wrapper(data, 5)
    payload = next(wrapper.cache_dir.glob("*.pickle"))
    payload.write_bytes(b"partial invalid pickle")
    actual = wrapper(data, 5)
    pd.testing.assert_frame_equal(expected, actual, check_exact=True)
    assert _calls(data) == 2
    assert not list(wrapper.cache_dir.glob("*.pending"))


def _populate_worker(data: str, root: str, source: str, cache_dir: str) -> None:
    wrapper = FeatureCache(_builder, allowed_dirs=[Path(data)], archive_root=Path(root),
                           source_paths=[Path(source)], cache_dir=Path(cache_dir))
    frame = wrapper(Path(data), 5)
    assert frame["nullable"].iloc[0] == 5


def test_cross_process_single_population(setup: tuple[FeatureCache, Path, Path, Path]) -> None:
    wrapper, data, _, source = setup
    context = multiprocessing.get_context("spawn")
    processes = [context.Process(target=_populate_worker,
                                args=(str(data), str(wrapper.archive_root), str(source), str(wrapper.cache_dir)))
                 for _ in range(4)]
    for process in processes:
        process.start()
    for process in processes:
        process.join(timeout=45)
        assert process.exitcode == 0
    assert _calls(data) == 1
    assert len(list(wrapper.cache_dir.glob("*.pickle"))) == 1
    assert not list(wrapper.cache_dir.glob("*.pending"))

from __future__ import annotations

import errno
import functools
import hashlib
import importlib.metadata
import importlib.util
import inspect
import marshal
import os
import pickle
import re
import sys
import tempfile
import time
from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
CACHE_ROOT = Path(__file__).resolve().parent / "frames"
ARCHIVE_ROOT = ROOT / "data" / "archive"


@contextmanager
def key_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        if path.stat().st_size == 0:
            handle.write(b"\0")
            handle.flush()
        if os.name == "nt":
            import msvcrt

            while True:
                try:
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError as exc:
                    if exc.errno not in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                        raise
                    time.sleep(0.05)
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _metadata(directory: Path) -> tuple[tuple[object, ...], ...]:
    records: list[tuple[object, ...]] = []
    for path in sorted(directory.rglob("*.parquet")):
        if not path.resolve().is_relative_to(directory):
            raise ValueError("Parquet symlink outside allowlisted archive")
        stat = path.stat()
        records.append((str(path.relative_to(directory)), stat.st_size, stat.st_mtime_ns,
                        stat.st_ctime_ns, stat.st_dev, stat.st_ino))
    return tuple(records)


def _complete(directory: Path, archive_root: Path) -> bool:
    if directory.name != "processed" or directory.parent.parent != archive_root:
        return False
    if re.fullmatch(r"\d{4}-\d{2}", directory.parent.name) is None:
        return False
    fixture_path = directory / "fixtures.parquet"
    if not fixture_path.is_file() or not fixture_path.resolve().is_relative_to(directory):
        return False
    finished = pd.read_parquet(fixture_path, columns=["finished"])["finished"]
    return bool(len(finished) and finished.notna().all() and finished.eq(True).all())


class FeatureCache:
    """Cache only exact builder calls over explicitly allowed complete archives."""

    _explore_feature_cache = True

    def __init__(
        self,
        original: Callable[..., pd.DataFrame],
        *,
        allowed_dirs: Iterable[Path],
        cache_dir: Path = CACHE_ROOT,
        archive_root: Path = ARCHIVE_ROOT,
        source_paths: Iterable[Path] | None = None,
    ) -> None:
        self.original = original
        self.signature = inspect.signature(original)
        self.allowed = frozenset(Path(path).resolve() for path in allowed_dirs)
        self.cache_dir = cache_dir.resolve()
        self.archive_root = archive_root.resolve()
        self.source_paths = None if source_paths is None else tuple(Path(path).resolve() for path in source_paths)
        self.runtime = (sys.version, *(importlib.metadata.version(name) for name in ("pandas", "numpy", "pyarrow")))
        self.code = hashlib.sha256(marshal.dumps(original.__code__)).hexdigest()
        self.stats = {"hit": 0, "miss": 0, "bypass": 0}
        functools.update_wrapper(self, original)

    def _key(self, arguments: dict[str, Any]) -> str | None:
        rejected = ("availability_snapshot_root", "availability_overrides", "xmins_override", "expected_role_table")
        if any(arguments.get(name) is not None for name in rejected):
            return None
        if arguments.get("require_availability_snapshot", False) or arguments.get("as_of_gw") is None:
            return None
        if arguments.get("minutes_prior_source", "seed_state") != "seed_state":
            return None
        data = Path(arguments["processed_dir"]).resolve()
        seed_value = arguments.get("seed_processed_dir")
        if seed_value is None and (arguments.get("use_archive_seed", True) or arguments.get("seed_season")):
            return None
        directories = (data,) if seed_value is None else (data, Path(seed_value).resolve())
        if any(directory not in self.allowed or not _complete(directory, self.archive_root) for directory in directories):
            return None
        sources = self.source_paths
        if sources is None:
            sources = (*sorted((ROOT / "features").rglob("*.py")), Path(__file__).resolve(), ROOT / "uv.lock")
        source_hashes = tuple((str(path), hashlib.sha256(path.read_bytes()).hexdigest()) for path in sources)
        identity = (
            "exact-feature-cache-v1", self.original.__module__, self.original.__qualname__, self.code,
            self.runtime, tuple(arguments.items()), source_hashes,
            tuple((str(directory), _metadata(directory)) for directory in directories),
        )
        return hashlib.sha256(pickle.dumps(identity, protocol=5)).hexdigest()

    def _safe_key(self, arguments: dict[str, Any]) -> str | None:
        try:
            return self._key(arguments)
        except (OSError, ValueError, TypeError, pickle.PickleError, KeyError):
            return None

    def __call__(self, *args: Any, **kwargs: Any) -> pd.DataFrame:
        try:
            bound = self.signature.bind(*args, **kwargs)
            bound.apply_defaults()
        except TypeError:
            return self.original(*args, **kwargs)
        key = self._safe_key(bound.arguments)
        if key is None:
            self.stats["bypass"] += 1
            return self.original(*args, **kwargs)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        with key_lock(self.cache_dir / f"{key}.lock"):
            if self._safe_key(bound.arguments) != key:
                self.stats["bypass"] += 1
                return self.original(*args, **kwargs)
            target = self.cache_dir / f"{key}.pickle"
            if target.is_file():
                try:
                    restored = pickle.loads(target.read_bytes())
                    if not isinstance(restored, pd.DataFrame):
                        raise TypeError("Cached value is not a DataFrame")
                except (OSError, pickle.PickleError, EOFError, TypeError, ValueError, AttributeError):
                    target.unlink(missing_ok=True)
                else:
                    if self._safe_key(bound.arguments) == key:
                        self.stats["hit"] += 1
                        return restored
                    self.stats["bypass"] += 1
                    return self.original(*args, **kwargs)
            self.stats["miss"] += 1
            frame = self.original(*args, **kwargs)
            if not isinstance(frame, pd.DataFrame):
                return frame
            payload = pickle.dumps(frame, protocol=5)
            restored = pickle.loads(payload)
            pd.testing.assert_frame_equal(frame, restored, check_exact=True, check_dtype=True,
                                          check_index_type=True, check_column_type=True, check_names=True)
            assert pickle.dumps(frame.attrs, protocol=5) == pickle.dumps(restored.attrs, protocol=5)
            if self._safe_key(bound.arguments) != key:
                return frame
            temporary: Path | None = None
            try:
                with tempfile.NamedTemporaryFile(mode="wb", dir=self.cache_dir, suffix=".pending", delete=False) as handle:
                    temporary = Path(handle.name)
                    handle.write(payload)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temporary, target)
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
            return restored


def resolved_archive_dirs() -> frozenset[Path]:
    name = "_explore_feature_cache_seasons"
    path = ROOT / ".agents" / "skills" / "explore-candidate" / "smoke.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load season resolver: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    roles, _ = module.resolve_seasons()
    return frozenset(path.resolve() for season in roles.values()
                     for path in (season.data_dir, season.seed_dir) if path is not None)


def install(*, allowed_dirs: Iterable[Path] | None = None, cache_dir: Path = CACHE_ROOT) -> FeatureCache:
    from backtesting import walkforward
    from features.builder import build_features

    current = walkforward.build_features
    if getattr(current, "_explore_feature_cache", False):
        return current
    if current is not build_features:
        raise RuntimeError("walkforward.build_features already differs from original builder")
    wrapper = FeatureCache(current, allowed_dirs=resolved_archive_dirs() if allowed_dirs is None else allowed_dirs,
                           cache_dir=cache_dir)
    walkforward.build_features = wrapper
    return wrapper

"""Strictly call-scoped stdlib ContextVar verification & replay memoization."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
import hashlib
import json
from typing import Any, Iterator, Mapping

_CACHE: ContextVar[dict[str, dict[Any, Any]] | None] = ContextVar("verification_call_cache", default=None)


def _new_cache() -> dict[str, dict[Any, Any]]:
    return {
        "assess_origins": {},
        "training": {},
        "emp_cov": {},
        "blobs": {},
        "closure": {},
    }


def get_verification_cache() -> dict[str, dict[Any, Any]] | None:
    """Return the active call-scoped cache dictionary, or None outside a scope."""
    return _CACHE.get()


@contextmanager
def verification_call_scope() -> Iterator[dict[str, dict[Any, Any]]]:
    """Activate a call-scoped verification cache, unconditionally clearing on exit."""
    current = _CACHE.get()
    if current is not None:
        yield current
        return
    cache = _new_cache()
    token = _CACHE.set(cache)
    try:
        yield cache
    finally:
        cache.clear()
        _CACHE.reset(token)


def _json_default(obj: Any) -> Any:
    if isinstance(obj, (bytes, bytearray, memoryview)):
        return {"__bytes_hex__": bytes(obj).hex()}
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def json_fingerprint(obj: Any) -> str:
    """Return a deterministic SHA-256 digest of a JSON-compatible object."""
    encoded = json.dumps(obj, sort_keys=True, separators=(",", ":"), default=_json_default).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def catalog_fingerprint(catalog: Mapping[str, bytes]) -> str:
    """Return a tamper-sensitive SHA-256 digest over every catalog key and byte payload."""
    hasher = hashlib.sha256()
    for key in sorted(catalog):
        raw = catalog[key]
        raw_sha = hashlib.sha256(raw).hexdigest()
        hasher.update(f"{key}:{len(raw)}:{raw_sha}\n".encode("utf-8"))
    return hasher.hexdigest()


def request_catalog_fingerprint(request: Mapping[str, Any], catalog: Mapping[str, bytes]) -> tuple[str, str]:
    """Return a pair of content-addressed digests for (request, catalog)."""
    return json_fingerprint(request), catalog_fingerprint(catalog)

"""Tests for call-scoped ContextVar verification cache and tamper sensitivity."""

from __future__ import annotations

import pytest

from backtesting.verification_cache import (
    catalog_fingerprint,
    get_verification_cache,
    json_fingerprint,
    request_catalog_fingerprint,
    verification_call_scope,
)


def test_verification_call_scope_clears_on_exit_and_exception() -> None:
    assert get_verification_cache() is None

    with verification_call_scope() as cache:
        assert get_verification_cache() is cache
        cache["blobs"]["k"] = b"v"
        with verification_call_scope() as inner:
            assert inner is cache
        assert get_verification_cache() is cache

    assert get_verification_cache() is None
    assert cache == {}

    with pytest.raises(RuntimeError, match="boom"):
        with verification_call_scope() as err_cache:
            err_cache["closure"]["k"] = "v"
            raise RuntimeError("boom")

    assert get_verification_cache() is None


def test_fingerprints_detect_single_byte_tampering() -> None:
    cat_a = {"src_1": b"abc", "src_2": b"xyz"}
    cat_b = {"src_1": b"abd", "src_2": b"xyz"}
    req_a = {"season": "2026-27", "origins": [{"gw": 1, "raw": b"123"}]}
    req_b = {"season": "2026-27", "origins": [{"gw": 1, "raw": b"124"}]}

    assert catalog_fingerprint(cat_a) == catalog_fingerprint(dict(cat_a))
    assert catalog_fingerprint(cat_a) != catalog_fingerprint(cat_b)
    assert json_fingerprint(req_a) != json_fingerprint(req_b)
    assert request_catalog_fingerprint(req_a, cat_a) != request_catalog_fingerprint(req_a, cat_b)

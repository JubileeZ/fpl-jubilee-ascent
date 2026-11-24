"""Tests for call-scoped ContextVar verification cache and tamper sensitivity."""

from __future__ import annotations

from pathlib import Path

import pytest

from backtesting.data_admission import assess_origins
from backtesting.portable_evidence import BlobStore
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


def test_verification_cache_isolates_caller_mutations() -> None:
    from test_data_admission import catalog, request

    req = request()
    cat = catalog(req)

    with verification_call_scope():
        first = assess_origins(req, cat, allow_disk_path_fallback=False)
        orig_status = first[0]["status"]
        orig_season = first[0]["season"]
        first[0]["status"] = "tampered"
        first[0]["season"] = "1999-00"
        first[0]["reasons"].append("injected")
        second = assess_origins(req, cat, allow_disk_path_fallback=False)
        assert second[0]["status"] == orig_status
        assert second[0]["season"] == orig_season
        assert "injected" not in second[0]["reasons"]


def test_blob_store_cache_detects_on_disk_tamper_and_delete_within_scope(tmp_path: Path) -> None:
    store = BlobStore(tmp_path)
    digest = store.write_bytes(b"canonical-payload")
    blob_path = tmp_path / "blobs" / digest

    with verification_call_scope():
        assert store.read_bytes(digest) == b"canonical-payload"
        assert store.read_bytes(digest) == b"canonical-payload"

        blob_path.write_bytes(b"tampered-payload-extra")
        with pytest.raises(ValueError, match="checksum mismatch"):
            store.read_bytes(digest)

        blob_path.unlink()
        with pytest.raises(ValueError, match="Missing blob file"):
            store.read_bytes(digest)

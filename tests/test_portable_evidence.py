"""TDD tests for portable checkpoint evidence primitives (#198)."""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import shutil
import tarfile

import pytest

from backtesting.portable_evidence import (
    AdoptionLedger,
    BlobStore,
    ExclusionLedger,
    TamperedLedgerError,
    VerificationScorecard,
    compute_serving_model_closure,
    load_and_verify_scorecard,
    pack_checkpoint_snapshot,
    resolve_model_runtime_identity,
    validate_relative_posix_path,
    verify_chain_extends,
    verify_checkpoint_snapshot_archive,
    write_scorecard,
)


def test_validate_relative_posix_path_normalization_and_rejections() -> None:
    assert validate_relative_posix_path("blobs/abc123") == "blobs/abc123"
    assert validate_relative_posix_path("./traces/trace.json") == "traces/trace.json"
    assert validate_relative_posix_path("forecast_cache//forecasts/abc/manifest.json") == (
        "forecast_cache/forecasts/abc/manifest.json"
    )

    bad_paths = [
        "",
        "   ",
        ".",
        "./",
        "/etc/passwd",
        "/blobs/abc",
        "blobs\\abc",
        "C:\\temp\\bundle.json",
        "C:bundle.json",
        "../secret.json",
        "blobs/../secret.json",
        "archive/2026-27/secret.parquet",
        "data/archive/file.json",
        ".git/config",
        "sub/.git/HEAD",
        ".agents/hooks.json",
        "bad\x00path.json",
        " leading_space.json",
    ]
    for bad in bad_paths:
        with pytest.raises(ValueError):
            validate_relative_posix_path(bad)


def test_blob_store_read_write_verify_and_confinement(tmp_path: Path) -> None:
    store = BlobStore(tmp_path)
    payload = b'{"hello":"world"}'
    digest = store.write_bytes(payload)
    assert digest == hashlib.sha256(payload).hexdigest()
    assert store.relpath(digest) == f"blobs/{digest}"
    assert store.exists(digest) is True
    assert store.read_bytes(digest) == payload
    assert store.read_bytes(f"blobs/{digest}", expected_sha256=digest) == payload
    assert store.verify(digest) == digest

    # Idempotent identical rewrite succeeds; corrupted existing blob raises
    assert store.write_bytes(payload) == digest
    blob_file = tmp_path / "blobs" / digest
    blob_file.write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="checksum|mismatch|digest"):
        store.read_bytes(digest)
    with pytest.raises(ValueError, match="Corrupt"):
        store.write_bytes(payload)

    # Reject path traversal, symlinks, and invalid digests
    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"secret")
    link_digest = hashlib.sha256(b"secret").hexdigest()
    symlink_blob = tmp_path / "blobs" / link_digest
    symlink_blob.symlink_to(outside)
    with pytest.raises(ValueError, match="Symlink|symlink|confined"):
        store.read_bytes(link_digest)

    for bad_ref in ("not-a-digest", "../outside.txt", "/tmp/x", "blobs/" + "a" * 63):
        with pytest.raises(ValueError):
            store.read_bytes(bad_ref)


def _make_minimal_closure_repo(root: Path) -> None:
    (root / "models").mkdir(parents=True)
    (root / "features").mkdir(parents=True)
    (root / "projections").mkdir(parents=True)
    (root / "backtesting").mkdir(parents=True)
    (root / "config").mkdir(parents=True)
    (root / "dashboard").mkdir(parents=True)

    (root / "models" / "__init__.py").write_text("", encoding="utf-8")
    (root / "models" / "base.py").write_text(
        "class BaseModel:\n    @property\n    def name(self) -> str:\n        return 'base'\n",
        encoding="utf-8",
    )
    (root / "models" / "helper_base.py").write_text(
        "from models.base import BaseModel\nclass HelperBase(BaseModel):\n    pass\n",
        encoding="utf-8",
    )
    (root / "models" / "cand_alpha.py").write_text(
        "from models.helper_base import HelperBase\n"
        "class CandAlphaModel(HelperBase):\n"
        "    @property\n"
        "    def name(self) -> str:\n"
        "        return 'cand_alpha'\n",
        encoding="utf-8",
    )
    (root / "models" / "unrelated_cand.py").write_text(
        "from models.base import BaseModel\n"
        "class UnrelatedCandModel(BaseModel):\n"
        "    @property\n"
        "    def name(self) -> str:\n"
        "        return 'unrelated_cand'\n",
        encoding="utf-8",
    )
    (root / "features" / "builder.py").write_text("X = 1\n", encoding="utf-8")
    (root / "projections" / "exporter.py").write_text("Y = 2\n", encoding="utf-8")
    for mod in (
        "native_transfer_solver.py",
        "replay_state.py",
        "season_rules.py",
        "forecast_adapter.py",
        "forecast_export.py",
    ):
        (root / "backtesting" / mod).write_text("Z = 3\n", encoding="utf-8")
    (root / "backtesting" / "promotion_evidence.py").write_text("EVAL = 1\n", encoding="utf-8")
    (root / "config" / "season_lifecycle.json").write_text('{"active_season": "2026-27"}\n', encoding="utf-8")
    (root / "config" / "model_selection.json").write_text('{"champion": "cand_alpha"}\n', encoding="utf-8")
    (root / "dashboard" / "app.py").write_text("UI = 1\n", encoding="utf-8")
    (root / "pyproject.toml").write_text('[project]\nname = "demo"\n', encoding="utf-8")
    (root / "uv.lock").write_text(
        "\n".join(
            [
                "version = 1",
                '[[package]]\nname = "highspy"\nversion = "1.15.0"',
                '[[package]]\nname = "numpy"\nversion = "2.5.0"',
                '[[package]]\nname = "pandas"\nversion = "3.0.4"',
                '[[package]]\nname = "pyarrow"\nversion = "24.0.0"',
                '[[package]]\nname = "scipy"\nversion = "1.18.0"',
                '[[package]]\nname = "streamlit"\nversion = "1.65.0"',
                '[[package]]\nname = "pytest"\nversion = "9.1.1"',
                '[[package]]\nname = "ruff"\nversion = "0.15.20"',
                '[[package]]\nname = "playwright"\nversion = "1.61.0"',
                '[[package]]\nname = "pyright"\nversion = "1.1.414"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_runtime_identity_and_serving_closure_invariance(tmp_path: Path) -> None:
    # Real repo Champion binding works cleanly
    champ = resolve_model_runtime_identity("def_xg_shrink_challenger")
    assert champ.module_name == "models.def_xg_shrink_challenger"
    assert champ.class_qualname == "DefXgShrinkChallengerModel"
    real_closure = compute_serving_model_closure(["def_xg_shrink_challenger"])
    assert "dashboard/" not in " ".join(real_closure.closure_files)
    assert "config/model_selection.json" not in real_closure.closure_files
    assert "models/apex_predator_challenger.py" not in real_closure.closure_files
    assert set(real_closure.package_pins) == {"highspy", "numpy", "pandas", "pyarrow", "scipy"}

    # Isolated repo tests AST transitive closure + UI/dev/unrelated invariance
    repo = tmp_path / "repo"
    _make_minimal_closure_repo(repo)
    base = compute_serving_model_closure(["cand_alpha"], project_root=repo)
    assert base.model_runtime_bindings["cand_alpha"]["module_name"] == "models.cand_alpha"
    assert base.model_runtime_bindings["cand_alpha"]["class_qualname"] == "CandAlphaModel"
    assert "models/helper_base.py" in base.closure_files
    assert "models/unrelated_cand.py" not in base.closure_files
    assert "dashboard/app.py" not in base.closure_files
    assert "config/model_selection.json" not in base.closure_files
    assert set(base.package_pins) == {"highspy", "numpy", "pandas", "pyarrow", "scipy"}

    # Unrelated edits NEVER invalidate serving_model_closure_hash
    (repo / "dashboard" / "app.py").write_text("UI = 999\n", encoding="utf-8")
    (repo / "models" / "unrelated_cand.py").write_text(
        "from models.base import BaseModel\nclass UnrelatedCandModel(BaseModel):\n    X = 9\n",
        encoding="utf-8",
    )
    (repo / "config" / "model_selection.json").write_text('{"champion": "other"}\n', encoding="utf-8")
    (repo / "backtesting" / "promotion_evidence.py").write_text("EVAL = 2\n", encoding="utf-8")
    (repo / "uv.lock").write_text(
        (repo / "uv.lock").read_text(encoding="utf-8").replace('version = "1.65.0"', 'version = "1.66.0"').replace('version = "9.1.1"', 'version = "9.2.0"'),
        encoding="utf-8",
    )
    after_unrelated = compute_serving_model_closure(["cand_alpha"], project_root=repo)
    assert after_unrelated.serving_model_closure_hash == base.serving_model_closure_hash
    assert after_unrelated.evaluator_code_hash != base.evaluator_code_hash

    # Modeling dependency / transitive model file edit DOES invalidate serving_model_closure_hash
    (repo / "models" / "helper_base.py").write_text(
        "from models.base import BaseModel\nclass HelperBase(BaseModel):\n    CHANGED = True\n",
        encoding="utf-8",
    )
    after_dep = compute_serving_model_closure(["cand_alpha"], project_root=repo)
    assert after_dep.serving_model_closure_hash != base.serving_model_closure_hash

    (repo / "uv.lock").write_text(
        (repo / "uv.lock").read_text(encoding="utf-8").replace('version = "1.15.0"', 'version = "1.16.0"'),
        encoding="utf-8",
    )
    after_highs = compute_serving_model_closure(["cand_alpha"], project_root=repo)
    assert after_highs.serving_model_closure_hash != after_dep.serving_model_closure_hash


def test_ledgers_chain_extension_and_scorecard_tamper_and_gaps(tmp_path: Path) -> None:
    excl = ExclusionLedger(tmp_path / "exclusions.jsonl")
    r1 = excl.record_exclusion(
        slate_id="slate-2026",
        season="2026-27",
        candidate_name="cand_1",
        checkpoint_gw=8,
        reason_code="early_harm",
        details="p_harm=0.01 <= 0.025",
    )
    assert excl.is_excluded("cand_1", slate_id="slate-2026") is True
    assert excl.verify_integrity() is True

    # Prefix extension verification
    r2 = excl.record_exclusion(
        slate_id="slate-2026",
        season="2026-27",
        candidate_name="cand_2",
        checkpoint_gw=15,
        reason_code="mandatory_guard_failure",
        details="points_mse FAIL",
    )
    assert verify_chain_extends([r1], [r1, r2]) is True
    with pytest.raises(ValueError, match="extend|shorter|mismatch|chain"):
        verify_chain_extends([r1, r2], [r1])
    rewritten = r1.__class__(**{**r1.to_dict(), "details": "rewritten"})
    with pytest.raises(ValueError, match="mismatch|hash|chain"):
        verify_chain_extends([r1], [rewritten, r2])

    # Tampering JSONL fails closed
    lines = (tmp_path / "exclusions.jsonl").read_text(encoding="utf-8").splitlines()
    lines[0] = lines[0].replace("early_harm", "tampered_reason")
    (tmp_path / "exclusions.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(TamperedLedgerError):
        excl.load_all_records()

    # AdoptionLedger tracks human disposition separately
    adopt_ledger = AdoptionLedger(tmp_path / "adoption_ledger.jsonl")
    a1 = adopt_ledger.record_disposition(
        request_id="req-001",
        slate_id="slate-2026",
        season="2026-27",
        checkpoint_gw=15,
        candidate_name="cand_1",
        expected_champion="def_xg_shrink_challenger",
        bundle_hash="a" * 64,
        disposition="rejected",
        actor="operator",
        reason="Deferred at GW15",
    )
    assert adopt_ledger.latest_for_request("req-001") == a1
    assert adopt_ledger.verify_integrity() is True

    # VerificationScorecard self-hashes and captures gap status + first_blocked_gw
    sc = VerificationScorecard(
        season="2026-27",
        checkpoint_gw=10,
        slate_id="slate-2026",
        slate_sealed=True,
        confirmed_champion="def_xg_shrink_challenger",
        podium_order=("cand_1",),
        provisional_active="cand_1",
        serving_model_closure_hash="b" * 64,
        model_runtime_bindings={"def_xg_shrink_challenger": {"module_name": "models.def_xg_shrink_challenger", "class_qualname": "DefXgShrinkChallengerModel"}},
        evaluator_code_hash="c" * 64,
        producer_git_sha="d" * 40,
        settled_through_gw=9,
        gap_status="transient_gap",
        first_blocked_gw=10,
        reason_codes=("outcomes:premature_settlement_lt_24h",),
        cumulative_net_points={"def_xg_shrink_challenger": 510.0, "cand_1": 518.0},
        weekly_leader="cand_1",
        active_exclusions=(),
        generated_at="2026-10-01T12:00:00+00:00",
    )
    gw_path, latest_path = write_scorecard(tmp_path, sc)
    loaded = load_and_verify_scorecard(gw_path)
    assert loaded == load_and_verify_scorecard(latest_path)
    assert loaded.gap_status == "transient_gap"
    assert loaded.first_blocked_gw == 10

    tampered_sc = json.loads(gw_path.read_text(encoding="utf-8"))
    tampered_sc["weekly_leader"] = "def_xg_shrink_challenger"
    gw_path.write_text(json.dumps(tampered_sc), encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        load_and_verify_scorecard(gw_path)


def test_pack_and_verify_snapshot_archive_fail_closed_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from backtesting import portable_evidence, promotion_evidence
    from backtesting.confirmation_registry import ConfirmationRegistry
    from models.selection import ModelSelection, save_model_selection

    root = tmp_path / "evidence"
    root.mkdir()
    save_model_selection(
        ModelSelection(
            "def_xg_shrink_challenger",
            ("adaptive_causal_challenger",),
            provisional_active="adaptive_causal_challenger",
            podium_frozen_season="2026-27",
            podium_sealed=True,
        ),
        root / "selection.json",
    )
    (root / "protocol.json").write_text('{"windows":{"2025-26":[1,2],"2026-27":[1,2,3]}}', encoding="utf-8")
    (root / "parameters.json").write_text("{}", encoding="utf-8")
    reg = ConfirmationRegistry(root / "registry.jsonl")
    reg.register_finalist(
        candidate_name="adaptive_causal_challenger",
        champion_name="def_xg_shrink_challenger",
        mechanism_family="fam-a",
        model_source_hash="1" * 64,
        parameters_hash="2" * 64,
        dev_selection_record_ref="3" * 64,
        protocol_hash="4" * 64,
        attempt_id="att-1",
        requested_seasons=("2026-27",),
        max_family_attempts=1,
    )
    reg.finalize_early_checkpoint_pass(
        "att-1",
        checkpoint_gw=15,
        completed_gameweeks=tuple(range(1, 16)),
        score_trace_hash="5" * 64,
        bundle_path="bundle.json",
    )
    excl = ExclusionLedger(root / "exclusions.jsonl")
    excl_rec = excl.record_exclusion(
        slate_id="slate-2026",
        season="2026-27",
        candidate_name="other_cand",
        checkpoint_gw=10,
        reason_code="early_harm",
        details="prior exclusion",
    )
    closure = compute_serving_model_closure(["def_xg_shrink_challenger", "adaptive_causal_challenger"])
    blob_store = BlobStore(root)
    blob_ref = blob_store.write_canonical_json({"hello": "blob"})
    trace_dir = root / "traces"
    trace_dir.mkdir()
    trace_file = trace_dir / "t.json"
    trace_file.write_text("{}", encoding="utf-8")

    request = {
        "version": "adr0069-checkpoint-v2",
        "checkpoint_gw": 15,
        "selection_path": "selection.json",
        "registry_path": "registry.jsonl",
        "protocol": {"path": "protocol.json", "sha256": hashlib.sha256((root / "protocol.json").read_bytes()).hexdigest()},
        "parameters": {"path": "parameters.json", "sha256": hashlib.sha256((root / "parameters.json").read_bytes()).hexdigest()},
        "guard_outcome_sources": [{"season": "2026-27", "gameweek": 15, "admission": blob_ref}],
        "development_selections": {},
        "replays": [
            {
                "season": "2026-27",
                "model_name": "def_xg_shrink_challenger",
                "anchor": blob_ref,
                "trace": {"path": "traces/t.json", "sha256": hashlib.sha256(trace_file.read_bytes()).hexdigest()},
                "issues": [],
            }
        ],
    }
    req_bytes = json.dumps(request, sort_keys=True).encode("utf-8")
    (root / "request.json").write_bytes(req_bytes)

    bundle = {
        "version": "adr0069-checkpoint-v2",
        "checkpoint_gw": 15,
        "candidate_name": "adaptive_causal_challenger",
        "former_champion": "def_xg_shrink_challenger",
        "recommended_champion": "adaptive_causal_challenger",
        "scientific_verdict": "pass",
        "execution_status": "complete",
        "empirical_admission": True,
        "confirmation_attempt_id": "att-1",
        "request_path": "request.json",
        "request_sha256": hashlib.sha256(req_bytes).hexdigest(),
        "serving_model_closure_hash": closure.serving_model_closure_hash,
        "model_runtime_bindings": closure.model_runtime_bindings,
        "bundle_hash": "a" * 64,
    }
    bundle_path = root / "bundle.json"
    bundle_path.write_text(json.dumps(bundle, sort_keys=True), encoding="utf-8")

    def fake_verify(bp: Path | str, *, require_finalized: bool = False) -> dict[str, object]:
        assert require_finalized is True
        loaded = json.loads(Path(bp).read_bytes())
        if loaded.get("bundle_hash") != "a" * 64:
            raise ValueError("altered bundle")
        if (Path(bp).parent / blob_ref["path"]).read_bytes() != b'{"hello":"blob"}':
            raise ValueError("altered blob")
        return loaded

    monkeypatch.setattr(promotion_evidence, "verify_checkpoint_recommendation_bundle", fake_verify)
    monkeypatch.setattr(portable_evidence, "_verify_bundle_in_dir", fake_verify)

    packed = pack_checkpoint_snapshot(bundle_path, output_dir=tmp_path / "out")
    archive_path = Path(packed["archive_path"])
    manifest_path = Path(packed["manifest_path"])
    assert archive_path.name == f"checkpoint-2026-27-gw15-{'a' * 12}.tar.gz"
    assert archive_path.is_file() and manifest_path.is_file()

    # Fresh-root verify succeeds
    verified = verify_checkpoint_snapshot_archive(
        archive_path,
        manifest_path=manifest_path,
        expected_champion="def_xg_shrink_challenger",
        canonical_registry_path=root / "registry.jsonl",
        canonical_exclusions_path=root / "exclusions.jsonl",
    )
    assert verified["archive_sha256"] == packed["archive_sha256"]

    # Wrong expected_champion fails closed
    with pytest.raises(ValueError, match="expected_champion|Champion"):
        verify_checkpoint_snapshot_archive(
            archive_path,
            manifest_path=manifest_path,
            expected_champion="wrong_champion",
        )

    # Subsequent exclusion of winner in canonical exclusions.jsonl fails closed
    canon_excl = tmp_path / "canon_exclusions.jsonl"
    shutil.copy2(root / "exclusions.jsonl", canon_excl)
    canon_ledger = ExclusionLedger(canon_excl)
    canon_ledger.record_exclusion(
        slate_id="slate-2026",
        season="2026-27",
        candidate_name="adaptive_causal_challenger",
        checkpoint_gw=18,
        reason_code="early_harm",
        details="excluded after snapshot",
    )
    assert verify_chain_extends([excl_rec], canon_ledger.load_all_records())
    with pytest.raises(ValueError, match="excluded"):
        verify_checkpoint_snapshot_archive(
            archive_path,
            manifest_path=manifest_path,
            expected_champion="def_xg_shrink_challenger",
            canonical_exclusions_path=canon_excl,
        )

    # Altered archive bytes fail archive_sha256 check
    tampered_tar = tmp_path / "tampered.tar.gz"
    tampered_tar.write_bytes(archive_path.read_bytes() + b"x")
    with pytest.raises(ValueError, match="archive_sha256|sha256|mismatch"):
        verify_checkpoint_snapshot_archive(tampered_tar, manifest_path=manifest_path)

    # Symlink / path traversal inside tar fails closed
    evil_tar = tmp_path / "evil.tar.gz"
    with tarfile.open(evil_tar, "w:gz") as tf:
        info = tarfile.TarInfo("../escape.txt")
        data = b"evil"
        info.size = len(data)
        tf.addfile(info, io.BytesIO(data))
    evil_sha = hashlib.sha256(evil_tar.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="relative|traversal|.."):
        verify_checkpoint_snapshot_archive(evil_tar, expected_archive_sha256=evil_sha)

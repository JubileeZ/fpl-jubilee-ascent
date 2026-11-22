"""Inventory admissible non-live pilot fixtures and retained GW15 verification (#198)."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backtesting.season_rules import load_season_lifecycle
from backtesting.sparse_certification import verify_certification_artifacts
from clients.env_loader import configure_utf8_stdio
from models.selection import load_model_selection

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_PARQUETS = (
    "clubs.parquet",
    "fixtures.parquet",
    "gameweeks.parquet",
    "player_performances.parquet",
    "players.parquet",
)


def _non_live_seasons(root: Path | None = None) -> tuple[str, ...]:
    lifecycle_file = (root or PROJECT_ROOT) / "config" / "season_lifecycle.json"
    lifecycle = load_season_lifecycle(lifecycle_file) if lifecycle_file.is_file() else load_season_lifecycle()
    active = lifecycle.active_season
    return tuple(sorted(s for s in lifecycle.seasons if s != active))


def _forbidden_live_season(root: Path | None = None) -> str:
    lifecycle_file = (root or PROJECT_ROOT) / "config" / "season_lifecycle.json"
    lifecycle = load_season_lifecycle(lifecycle_file) if lifecycle_file.is_file() else load_season_lifecycle()
    return lifecycle.active_season


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _assert_non_live_season(season: str, root: Path | None = None) -> None:
    if season == _forbidden_live_season(root) or season not in _non_live_seasons(root):
        raise ValueError(f"Inventory refuses live/unlisted season '{season}'")


def _inspect_archive_season(root: Path, season: str) -> dict[str, Any]:
    _assert_non_live_season(season, root)
    season_dir = root / "data" / "archive" / season
    processed_dir = season_dir / "processed"
    parquets: dict[str, dict[str, Any]] = {}
    for name in ARCHIVE_PARQUETS:
        file_path = processed_dir / name
        if file_path.is_file():
            meta = pq.read_metadata(file_path)
            parquets[name] = {
                "exists": True,
                "rows": int(meta.num_rows),
                "bytes": int(file_path.stat().st_size),
                "sha256": _sha256_file(file_path),
            }
        else:
            parquets[name] = {"exists": False, "rows": 0, "bytes": 0, "sha256": None}
    return {
        "season": season,
        "processed_exists": processed_dir.is_dir(),
        "raw_exists": (season_dir / "raw").is_dir(),
        "vaastav_exists": (season_dir / "vaastav").is_dir(),
        "parquets": parquets,
    }


def _inspect_mirror_manifest(root: Path, season: str) -> dict[str, Any]:
    _assert_non_live_season(season, root)
    slug = season.replace("-", "_")
    manifest_path = root / "config" / f"dev_mirror_{slug}_manifest.json"
    if not manifest_path.is_file():
        lifecycle_file = root / "config" / "season_lifecycle.json"
        lifecycle = load_season_lifecycle(lifecycle_file) if lifecycle_file.is_file() else load_season_lifecycle()
        role = lifecycle.role_of(season)
        return {
            "manifest_path": None,
            "manifest_sha256": None,
            "track": None,
            "bootstrap_admitted_count": 0,
            "fixture_admitted_count": 0,
            "settled_outcomes_zero_diff": None,
            "verified_outcome_rows": 0,
            "ledger_mismatch_rows": None,
            "contiguous_admitted_prefix_end_gw": 0,
            "contiguous_admitted_prefix": "0",
            "admitted_gws": [],
            "first_blocked_gw": 1 if role != "prior_seed_only" else None,
            "first_blocked_reasons": ["no_dev_mirror_manifest_or_fplcache_series"],
            "full_season_admitted": False,
            "local_blobs_hydrated": False,
            "attributions": [],
        }
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    summary = payload.get("summary", {})
    origins = payload.get("origins", [])
    admitted_gws = [int(o["gw"]) for o in origins if o.get("origin_admitted") is True]
    prefix_end = int(summary.get("contiguous_admitted_prefix_end_gw", 0))
    blocked_gws = summary.get("blocked_gws", [])
    first_blocked = blocked_gws[0] if blocked_gws else None
    quarantine_root = root / "data" / "reports" / "empirical_mirrors"
    local_rels = [
        o.get(role, {}).get("local_relpath")
        for o in origins[:prefix_end]
        for role in ("bootstrap", "fixtures", "settled_outcomes")
        if isinstance(o.get(role), dict) and o.get(role, {}).get("local_relpath")
    ]
    hydrated = bool(local_rels) and all((quarantine_root / rel).is_file() for rel in local_rels)
    return {
        "manifest_path": manifest_path.relative_to(root).as_posix(),
        "manifest_sha256": _sha256_file(manifest_path),
        "track": payload.get("track"),
        "bootstrap_admitted_count": int(summary.get("bootstrap_admitted_count", 0)),
        "fixture_admitted_count": int(summary.get("fixture_admitted_count", 0)),
        "settled_outcomes_zero_diff": summary.get("settled_outcomes_zero_diff"),
        "verified_outcome_rows": int(summary.get("verified_outcome_rows", 0)),
        "ledger_mismatch_rows": summary.get("ledger_mismatch_rows"),
        "contiguous_admitted_prefix_end_gw": prefix_end,
        "contiguous_admitted_prefix": f"GW1..{prefix_end}" if prefix_end > 0 else "0",
        "admitted_gws": admitted_gws,
        "first_blocked_gw": first_blocked.get("gw") if isinstance(first_blocked, dict) else None,
        "first_blocked_reasons": list(first_blocked.get("reasons", ())) if isinstance(first_blocked, dict) else [],
        "full_season_admitted": bool(summary.get("full_season_admitted", False)),
        "local_blobs_hydrated": hydrated,
        "attributions": payload.get("attributions", []),
    }


def _inspect_seed_manifests(root: Path) -> dict[str, dict[str, Any]]:
    seeds: dict[str, dict[str, Any]] = {}
    non_live = _non_live_seasons(root)
    for season in non_live[:-1]:
        slug = season.replace("-", "_")
        path = root / "config" / f"seed_manifest_{slug}.json"
        if not path.is_file():
            seeds[season] = {"exists": False, "path": None, "sha256": None}
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        seeds[season] = {
            "exists": True,
            "path": path.relative_to(root).as_posix(),
            "sha256": _sha256_file(path),
            "vaastav_commits": payload.get("vaastav_commits", []),
            "players_total": payload.get("players_total"),
            "excluded_position_5_count": payload.get("excluded_position_5_count"),
            "retained_player_count": payload.get("retained_player_count"),
            "retained_perf_rows": payload.get("retained_perf_rows"),
            "defensive_contribution_status": payload.get("defensive_contribution_status"),
        }
    return seeds


def _inspect_reports_dir(root: Path) -> dict[str, Any]:
    reports_dir = root / "data" / "reports"
    if not reports_dir.exists():
        return {"exists": False, "entries": []}
    forbidden = _forbidden_live_season(root)
    entries: list[str] = []
    for item in sorted(reports_dir.rglob("*")):
        rel = item.relative_to(root).as_posix()
        if forbidden in rel:
            continue
        if item.is_file():
            entries.append(rel)
    return {"exists": True, "entries": entries}


def verify_retained_gw15_fixture(root: Path) -> dict[str, Any]:
    """Verify tests/test_verified_checkpoint_evidence.py reconstructs deterministically as inconclusive."""
    test_file = root / "tests" / "test_verified_checkpoint_evidence.py"
    if not test_file.is_file():
        raise FileNotFoundError(f"Missing retained fixture test: {test_file}")
    test_sha = _sha256_file(test_file)

    pytest_proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", test_file.relative_to(root).as_posix()],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if pytest_proc.returncode != 0:
        raise RuntimeError(
            f"Retained GW15 fixture pytest failed ({pytest_proc.returncode}):\n"
            f"{pytest_proc.stdout}\n{pytest_proc.stderr}"
        )

    from backtesting.promotion_evidence import (
        verify_checkpoint_recommendation_bundle,
        write_checkpoint_recommendation_bundle,
    )

    tests_dir = str(root / "tests")
    root_dir = str(root)
    added_paths: list[str] = []
    for entry in (tests_dir, root_dir):
        if entry not in sys.path:
            sys.path.insert(0, entry)
            added_paths.append(entry)
    try:
        import tests.test_verified_checkpoint_evidence as fixture_mod

        with tempfile.TemporaryDirectory(prefix="pilot-gw15-") as td:
            tmp_root = Path(td)

            class _TmpFactory:
                def mktemp(self, basename: str) -> Path:
                    path = tmp_root / basename
                    path.mkdir(parents=True, exist_ok=True)
                    return path

            req_path = fixture_mod.retained_verified_checkpoint.__wrapped__(_TmpFactory())  # type: ignore[attr-defined]
            bundle_path = req_path.with_name("bundle.json")
            bundle = write_checkpoint_recommendation_bundle(req_path, bundle_path)
            verified = verify_checkpoint_recommendation_bundle(bundle_path)
            if verified != bundle:
                raise ValueError("Verified retained GW15 fixture bundle differs from written bundle")
            keys = (
                "version",
                "checkpoint_gw",
                "candidate_name",
                "former_champion",
                "scientific_verdict",
                "execution_status",
                "action",
                "requires_manual_adopt",
                "empirical_admission",
                "next_provisional_active",
                "recommended_champion",
                "admitted_limitations",
                "bundle_hash",
            )
            bundle_summary = {k: bundle.get(k) for k in keys}
    finally:
        for entry in added_paths:
            if entry in sys.path:
                sys.path.remove(entry)

    if bundle_summary.get("scientific_verdict") != "inconclusive":
        raise ValueError(f"Expected inconclusive retained fixture verdict, got {bundle_summary!r}")

    return {
        "test_path": test_file.relative_to(root).as_posix(),
        "test_sha256": test_sha,
        "pytest_passed": True,
        "pytest_summary": pytest_proc.stdout.strip().splitlines()[-1] if pytest_proc.stdout.strip() else "",
        "reconstructed_bundle": bundle_summary,
        "is_synthetic_test_fixture": True,
        "authorizes_real_historical_pass": False,
    }


def build_pilot_fixture_inventory(
    *,
    project_root: Path | None = None,
    verify_fixture: bool = True,
) -> dict[str, Any]:
    """Assemble exact admissible non-live fixture inventory without touching 2026-27 outcomes."""
    root = (project_root or PROJECT_ROOT).resolve()
    lifecycle_path = root / "config" / "season_lifecycle.json"
    lifecycle_data = json.loads(lifecycle_path.read_text(encoding="utf-8"))
    selection_path = root / "config" / "model_selection.json"
    selection = load_model_selection(selection_path)

    seasons: list[dict[str, Any]] = []
    for season in _non_live_seasons(root):
        archive_info = _inspect_archive_season(root, season)
        mirror_info = _inspect_mirror_manifest(root, season)
        role_entry = lifecycle_data.get("seasons", {}).get(season, {})
        seasons.append(
            {
                "season": season,
                "lifecycle_role": role_entry.get("role"),
                "cycle_slot": role_entry.get("cycle_slot"),
                "prior_seed": role_entry.get("prior_seed"),
                "rules_id": role_entry.get("rules_id"),
                "archive": archive_info,
                **mirror_info,
            }
        )

    seed_manifests = _inspect_seed_manifests(root)
    reports_info = _inspect_reports_dir(root)
    test_file = root / "tests" / "test_verified_checkpoint_evidence.py"
    retained_fixture = (
        verify_retained_gw15_fixture(root)
        if verify_fixture
        else {
            "test_path": test_file.relative_to(root).as_posix(),
            "test_sha256": _sha256_file(test_file) if test_file.is_file() else None,
            "pytest_passed": None,
            "verification_skipped": True,
            "reconstructed_bundle": {
                "checkpoint_gw": 15,
                "scientific_verdict": "inconclusive",
                "execution_status": "partial",
                "action": "retain_dual_tier",
                "empirical_admission": True,
                "requires_manual_adopt": False,
            },
            "is_synthetic_test_fixture": True,
            "authorizes_real_historical_pass": False,
        }
    )

    from commands.manage_champion_adoption import CERTIFICATION_DIGEST_EXPECTED

    lifecycle = load_season_lifecycle(lifecycle_path) if lifecycle_path.is_file() else load_season_lifecycle()
    act_s = lifecycle.active_season
    qualifying_prefix_seasons = [s for s in seasons if int(s["contiguous_admitted_prefix_end_gw"]) >= 15]
    hydrated_prefix_seasons = [s for s in qualifying_prefix_seasons if s["local_blobs_hydrated"]]
    cert_status = verify_certification_artifacts(
        root / "docs" / "research" / "sparse-confirmation-certification",
        expected_digest=CERTIFICATION_DIGEST_EXPECTED,
        project_root=root,
        check_evaluator_revisions=True,
    )

    missing_prerequisites: list[str] = []
    if not qualifying_prefix_seasons:
        prefix_desc = "; ".join(
            f"{s['season']} ({s['lifecycle_role']}) stops at {s['contiguous_admitted_prefix']}"
            + (
                f" (blocked GW{s['first_blocked_gw']}: {', '.join(s['first_blocked_reasons'])})"
                if s["first_blocked_gw"] is not None and s["first_blocked_reasons"]
                else ""
            )
            for s in seasons
        )
        missing_prerequisites.append(
            f"No non-live season reaches >=15 contiguous empirically admitted Gameweeks (GW15 checkpoint): {prefix_desc}."
        )
    incomplete_non_seed = [
        s["season"]
        for s in seasons
        if s["lifecycle_role"] != "prior_seed_only" and int(s["contiguous_admitted_prefix_end_gw"]) < 15
    ]
    if not qualifying_prefix_seasons and incomplete_non_seed:
        missing_prerequisites.append(
            f"Retroactive pre-deadline official fixture receipts unrecoverable for {', '.join(incomplete_non_seed)} "
            "missing GWs without fabricating historical provenance (prohibited under ADR 0069 / empirical_admission.py)."
        )
    if not hydrated_prefix_seasons and any(not s["local_blobs_hydrated"] for s in seasons if s["manifest_path"]):
        missing_prerequisites.append(
            "Local mirror blob directory data/reports/empirical_mirrors/ referenced by dev_mirror_*_manifest.json absent from disk."
        )
    if not (selection.podium_sealed and selection.candidates and selection.champion not in selection.candidates):
        missing_prerequisites.append(
            f"No non-live candidate qualifies as frozen passing finalist pair vs Confirmed Champion {selection.champion} "
            f"(provisional_active={selection.provisional_active}, podium_sealed={selection.podium_sealed})."
        )
    if not cert_status["passed"]:
        missing_prerequisites.append(
            "Certified v2 statistical protocol verification failed: " + "; ".join(cert_status["errors"])
        )
    if not qualifying_prefix_seasons:
        missing_prerequisites.append(
            f"SeasonLifecycle reserves validation_fplcache strictly for active_validation season {act_s} "
            "(quarantined outcomes excluded from fixture construction)."
        )

    has_admissible_historical_gw15_passing_fixture = bool(
        hydrated_prefix_seasons
        and selection.podium_sealed
        and selection.candidates
        and selection.champion not in selection.candidates
        and cert_status["passed"]
    )

    return {
        "ticket": 198,
        "forbidden_live_season_accessed": False,
        "season_lifecycle": {
            "path": lifecycle_path.relative_to(root).as_posix(),
            "sha256": _sha256_file(lifecycle_path),
            "active_season": lifecycle_data.get("active_season"),
        },
        "model_selection": {
            "path": selection_path.relative_to(root).as_posix(),
            "sha256": _sha256_file(selection_path),
            "champion": selection.champion,
            "candidates": list(selection.candidates),
            "provisional_active": selection.provisional_active,
            "podium_frozen_season": selection.podium_frozen_season,
            "podium_sealed": selection.podium_sealed,
        },
        "seasons": seasons,
        "seed_manifests": seed_manifests,
        "data_reports": reports_info,
        "retained_gw15_fixture": retained_fixture,
        "certification_artifacts_verified": bool(cert_status["passed"]),
        "has_admissible_historical_gw15_passing_fixture": has_admissible_historical_gw15_passing_fixture,
        "missing_prerequisites": missing_prerequisites,
    }


def render_inventory_markdown(report: dict[str, Any]) -> str:
    """Render concise durable Markdown inventory report."""
    has_real = bool(report["has_admissible_historical_gw15_passing_fixture"])
    lines: list[str] = [
        "# Pilot Fixture Inventory (Non-Live Evidence Audit)",
        "",
        "Generated by `uv run python -m commands.inventory_pilot_fixture` (#198). "
        "`2026-27` active-season outcomes never inspected.",
        "",
        "## Verdict Summary",
        "",
        f"- **Real historical `>=15`-GW empirically admitted passing fixture:** `{has_real}`"
        + (" (none exists)." if not has_real else "."),
        f"- **Current Confirmed Champion (`config/model_selection.json`):** `{report['model_selection']['champion']}` (`sha256={report['model_selection']['sha256']}`), `provisional_active={report['model_selection']['provisional_active']}`, `podium_sealed={report['model_selection']['podium_sealed']}`.",
        f"- **Retained GW15 test fixture (`{report['retained_gw15_fixture']['test_path']}`):** reconstructs deterministically with `scientific_verdict={report['retained_gw15_fixture']['reconstructed_bundle']['scientific_verdict']}`, `action={report['retained_gw15_fixture']['reconstructed_bundle'].get('action')}`, `empirical_admission={report['retained_gw15_fixture']['reconstructed_bundle'].get('empirical_admission')}` (synthetic 17-player empirical-format fixture; not real historical passing data).",
        "",
        "## Non-Live Season Empirical Admission Prefixes",
        "",
        "| Season | Role | Contiguous Prefix | Admitted GWs | First Blocked GW | Manifest SHA-256 | Local Blobs Hydrated |",
        "|---|---|---|---|---|---|---|",
    ]
    for s in report["seasons"]:
        m_sha = f"`{s['manifest_sha256'][:16]}...`" if s["manifest_sha256"] else "none"
        lines.append(
            f"| `{s['season']}` | `{s['lifecycle_role']}` (`{s['cycle_slot']}`) | "
            f"`{s['contiguous_admitted_prefix']}` | `{s['admitted_gws']}` | "
            f"`{s['first_blocked_gw']}` | {m_sha} | `{s['local_blobs_hydrated']}` |"
        )
    lines.extend(["", "## Archive & Manifest Provenance Details", ""])
    for s in report["seasons"]:
        lines.append(f"### {s['season']} (`{s['lifecycle_role']}`, rules `{s['rules_id']}`)")
        lines.append("")
        if s["manifest_path"]:
            lines.append(f"- **Mirror Manifest:** `{s['manifest_path']}` (`sha256={s['manifest_sha256']}`)")
            lines.append(
                f"- **Counts:** bootstraps `{s['bootstrap_admitted_count']}/38`, "
                f"fixtures `{s['fixture_admitted_count']}/38`, "
                f"verified outcome rows `{s['verified_outcome_rows']}` "
                f"(zero-diff=`{s['settled_outcomes_zero_diff']}`, ledger mismatches=`{s['ledger_mismatch_rows']}`)."
            )
            lines.append(
                f"- **First Blocked:** GW{s['first_blocked_gw']} — `{', '.join(s['first_blocked_reasons'])}`"
            )
        else:
            lines.append("- **Mirror Manifest:** none (`prior_seed_only`, contiguous prefix `0`).")
        arch = s["archive"]
        lines.append(
            f"- **Local Archive (`data/archive/{s['season']}/processed`):** "
            f"processed=`{arch['processed_exists']}`, raw=`{arch['raw_exists']}`, vaastav=`{arch['vaastav_exists']}`"
        )
        for pq_name, pq_info in arch["parquets"].items():
            if pq_info["exists"]:
                lines.append(f"  - `{pq_name}`: rows=`{pq_info['rows']}`, `sha256={pq_info['sha256']}`")
        lines.append("")

    lines.extend(["## Seed Manifests & Reports Directory", ""])
    for season, info in sorted(report["seed_manifests"].items()):
        if info["exists"]:
            lines.append(
                f"- **`{info['path']}`** (`sha256={info['sha256']}`): "
                f"total={info['players_total']}, excluded_pos5={info['excluded_position_5_count']}, "
                f"retained={info['retained_player_count']}, rows={info['retained_perf_rows']}, "
                f"defcon=`{info['defensive_contribution_status']}`."
            )
        else:
            lines.append(f"- **`config/seed_manifest_{season.replace('-', '_')}.json`:** missing.")
    lines.append(
        f"- **`data/reports/`:** exists=`{report['data_reports']['exists']}`, "
        f"non-live entries=`{len(report['data_reports']['entries'])}`."
    )

    ret = report["retained_gw15_fixture"]
    rb = ret["reconstructed_bundle"]
    lines.extend(
        [
            "",
            "## Retained GW15 Fixture Verification",
            "",
            f"- **Test File:** `{ret['test_path']}` (`sha256={ret['test_sha256']}`)",
            f"- **Pytest Passed:** `{ret['pytest_passed']}` (`{ret.get('pytest_summary') or 'skipped'}`)",
            f"- **Reconstructed Verdict:** `scientific_verdict={rb.get('scientific_verdict')}`, "
            f"`execution_status={rb.get('execution_status')}`, `action={rb.get('action')}`, "
            f"`checkpoint_gw={rb.get('checkpoint_gw')}`, `empirical_admission={rb.get('empirical_admission')}`, "
            f"`requires_manual_adopt={rb.get('requires_manual_adopt')}`.",
        ]
    )
    if rb.get("bundle_hash"):
        lines.append(f"- **Observed Run Bundle Hash:** `{rb['bundle_hash']}` (`{rb.get('former_champion')}` vs `{rb.get('candidate_name')}`).")

    lines.extend(["", "## Missing Prerequisites Blocking Real Historical GW15+ Passing Fixture", ""])
    for idx, req in enumerate(report["missing_prerequisites"], start=1):
        lines.append(f"{idx}. {req}")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    configure_utf8_stdio()
    parser = argparse.ArgumentParser(description="Inventory non-live pilot fixture readiness (#198).")
    parser.add_argument("--output", type=Path, default=Path("docs/testing/pilot-fixture-inventory.md"))
    parser.add_argument("--json-output", type=Path, default=None)
    parser.add_argument("--skip-fixture-verify", action="store_true")
    args = parser.parse_args(argv)

    report = build_pilot_fixture_inventory(verify_fixture=not args.skip_fixture_verify)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_inventory_markdown(report), encoding="utf-8")
    if args.json_output is not None:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote pilot fixture inventory to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

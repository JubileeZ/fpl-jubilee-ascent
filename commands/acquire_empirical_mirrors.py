"""Acquire and pin historical development mirrors and prior-season seed manifests under SeasonLifecycle."""

from __future__ import annotations

import argparse
import io
import json
import subprocess
import urllib.request
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from backtesting.empirical_mirrors import (
    SETTLEMENT_MIN_WAIT_SECONDS,
    build_bootstrap_mirror_record,
    build_causal_chip_calendar,
    build_causal_origin_chip_metadata,
    build_fixture_mirror_record,
    build_seed_manifest,
    canonical_json_sha256,
    extract_gw_df_from_merged_csv as _extract_gw_df_from_merged_csv,
    extract_gws_from_merged_csv as _extract_gws_from_merged_csv,
    parse_fixtures_csv_window,
    sha256_bytes,
    validate_mirror_url,
    verify_settled_outcomes_zero_diff,
)
from backtesting.fplcache_ingest import _unpack_bootstrap_xz, _utc
from backtesting.season_rules import get_rules, load_season_lifecycle

UTC = timezone.utc
ROOT = Path(__file__).resolve().parents[1]
QUARANTINE_ROOT = ROOT / "data/reports/empirical_mirrors"
CONFIG_ROOT = ROOT / "config"


def _gh_api(path: str) -> Any:
    raw = subprocess.check_output(["gh", "api", path], text=True)
    return json.loads(raw)


def _fetch_bytes(url: str, cache_path: Path | None = None) -> bytes:
    validate_mirror_url(url)
    if cache_path is not None and cache_path.exists():
        return cache_path.read_bytes()
    req = urllib.request.Request(url, headers={"User-Agent": "fpl-jubilee-ascent-mirror-acquire"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = resp.read()
    if cache_path is not None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(data)
    return data


def _list_fplcache_paths_for_months(
    gh_api_fn: Callable[[str], Any],
    year_months: list[tuple[int, list[int]]],
) -> list[tuple[datetime, str]]:
    branch = gh_api_fn("repos/Randdalf/fplcache/branches/main")
    tree_sha = branch["commit"]["commit"]["tree"]["sha"]
    root_tree = gh_api_fn(f"repos/Randdalf/fplcache/git/trees/{tree_sha}")
    cache_sha = next(x["sha"] for x in root_tree["tree"] if x["path"] == "cache")
    cache_tree = gh_api_fn(f"repos/Randdalf/fplcache/git/trees/{cache_sha}")
    yr_shas = {x["path"]: x["sha"] for x in cache_tree["tree"]}

    snapshots: list[tuple[datetime, str]] = []
    for yr, months in year_months:
        yr_str = str(yr)
        if yr_str not in yr_shas:
            continue
        mt = gh_api_fn(f"repos/Randdalf/fplcache/git/trees/{yr_shas[yr_str]}")
        allowed = {str(m) for m in months}
        for m in mt["tree"]:
            if m["path"] not in allowed:
                continue
            st = gh_api_fn(f"repos/Randdalf/fplcache/git/trees/{m['sha']}?recursive=1")
            for item in st["tree"]:
                if not item["path"].endswith(".json.xz"):
                    continue
                parts = item["path"].split("/")
                if len(parts) == 2 and parts[0].isdigit() and parts[1][:4].isdigit():
                    dt = datetime(
                        yr,
                        int(m["path"]),
                        int(parts[0]),
                        int(parts[1][:2]),
                        int(parts[1][2:4]),
                        tzinfo=UTC,
                    )
                    snapshots.append((dt, f"cache/{yr}/{m['path']}/{item['path']}"))
    snapshots.sort()
    return snapshots


def _commit_for_fplcache_path(gh_api_fn: Callable[[str], Any], repo_path: str) -> tuple[str, datetime]:
    commits = gh_api_fn(f"repos/Randdalf/fplcache/commits?path={repo_path}&per_page=1")
    if not commits:
        raise ValueError(f"No commit found for {repo_path}")
    c = commits[0]
    return str(c["sha"]), _utc(c["commit"]["committer"]["date"])


def _vaastav_commits(gh_api_fn: Callable[[str], Any], path: str) -> list[tuple[datetime, str, str]]:
    out: list[tuple[datetime, str, str]] = []
    page = 1
    while True:
        items = gh_api_fn(f"repos/vaastav/Fantasy-Premier-League/commits?path={path}&per_page=100&page={page}")
        if not items:
            break
        out.extend(
            (_utc(c["commit"]["committer"]["date"]), str(c["sha"]), str(c["commit"]["message"]).splitlines()[0])
            for c in items
        )
        if len(items) < 100:
            break
        page += 1
    out.sort(key=lambda row: row[0])
    return out


def _deadlines_and_max_kickoffs(
    season: str,
    *,
    fplcache_snapshots: list[tuple[datetime, str]],
    gh_api_fn: Callable[[str], Any],
    fetch_fn: Callable[[str, Path | None], bytes],
    quarantine_dir: Path,
) -> tuple[dict[int, datetime], dict[int, datetime], dict[int, dict[str, Any]]]:
    proc_dir = ROOT / "data/archive" / season / "processed"
    fx_proc = pd.read_parquet(proc_dir / "fixtures.parquet")
    max_ko: dict[int, datetime] = {}
    for gw in range(1, 39):
        sub = fx_proc[fx_proc["gameweek_id"] == gw]
        if not sub.empty:
            max_ko[gw] = max(_utc(str(k)) for k in sub["kickoff_time"])

    # Obtain official events array (with deadline_time) from end-of-season fplcache snapshot
    end_year = int(season[:4]) + 1
    end_cutoff = datetime(end_year, 5, 24, 16, 0, tzinfo=UTC)
    if not fplcache_snapshots:
        raise ValueError(f"No fplcache snapshots discovered for {season}")
    end_snaps = [s for s in fplcache_snapshots if s[0] >= end_cutoff]
    ref_snap = end_snaps[0] if end_snaps else fplcache_snapshots[-1]
    ref_sha, _ = _commit_for_fplcache_path(gh_api_fn, ref_snap[1])
    ref_url = f"https://raw.githubusercontent.com/Randdalf/fplcache/{ref_sha}/{ref_snap[1]}"
    ref_raw = fetch_fn(ref_url, quarantine_dir / season / "bootstraps" / "season_events_ref.json.xz")
    _, ref_payload = _unpack_bootstrap_xz(ref_raw)
    deadlines: dict[int, datetime] = {}
    for ev in ref_payload.get("events", []):
        gid = int(ev["id"])
        if 1 <= gid <= 38:
            deadlines[gid] = _utc(ev["deadline_time"])
    if len(deadlines) != 38:
        raise ValueError(f"Expected 38 event deadlines for {season}, got {len(deadlines)}")

    events_meta = {
        int(ev["id"]): {"id": int(ev["id"]), "deadline_time": str(ev["deadline_time"]), "finished": bool(ev.get("finished"))}
        for ev in ref_payload.get("events", [])
        if 1 <= int(ev["id"]) <= 38
    }
    return deadlines, max_ko, events_meta


def _resolve_settlement_commits(
    *,
    season: str,
    merged_commits: list[tuple[datetime, str, str]],
    max_ko: dict[int, datetime],
    quarantine_root: Path,
    fetch_fn: Callable[[str, Path | None], bytes],
) -> tuple[dict[int, tuple[datetime, str]], dict[str, tuple[str, str, bytes]], tuple[datetime, str, bytes]]:
    """Resolve earliest post-(max_ko + 24h) merged_gw commit per GW alongside final settled file."""
    if not merged_commits:
        raise ValueError(f"No vaastav merged_gw.csv commits discovered for {season}")
    final_merged_dt, final_merged_sha, _ = merged_commits[-1]
    final_merged_url = f"https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/{final_merged_sha}/data/{season}/gws/merged_gw.csv"
    final_merged_rel = f"{season}/outcomes/merged_gw_{final_merged_sha[:10]}.csv"
    final_merged_bytes = fetch_fn(final_merged_url, quarantine_root / final_merged_rel)
    merged_meta_by_sha: dict[str, tuple[str, str, bytes]] = {
        final_merged_sha: (final_merged_url, final_merged_rel, final_merged_bytes)
    }
    gw_settlement: dict[int, tuple[datetime, str]] = {}
    for commit_dt, sha, _ in merged_commits:
        rel = f"{season}/outcomes/merged_gw_{sha[:10]}.csv"
        url = f"https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/{sha}/data/{season}/gws/merged_gw.csv"
        raw_c = fetch_fn(url, quarantine_root / rel)
        merged_meta_by_sha[sha] = (url, rel, raw_c)
        for gw in _extract_gws_from_merged_csv(raw_c):
            if gw in max_ko and commit_dt >= max_ko[gw] + timedelta(seconds=SETTLEMENT_MIN_WAIT_SECONDS) and gw not in gw_settlement:
                gw_settlement[gw] = (commit_dt, sha)
    return gw_settlement, merged_meta_by_sha, (final_merged_dt, final_merged_sha, final_merged_bytes)


def _acquire_origin_entry(
    *,
    season: str,
    gw: int,
    dl: datetime,
    prev_dl: datetime | None,
    next_dl: datetime | None,
    ko_dt: datetime,
    all_snaps: list[tuple[datetime, str]],
    fx_commits: list[tuple[datetime, str, str]],
    gw_settlement: dict[int, tuple[datetime, str]],
    final_merged: tuple[datetime, str],
    merged_meta_by_sha: dict[str, tuple[str, str, bytes]],
    proc_perf: pd.DataFrame,
    proc_players: pd.DataFrame,
    quarantine_root: Path,
    gh_api_fn: Callable[[str], Any],
    fetch_fn: Callable[[str, Path | None], bytes],
) -> tuple[dict[str, Any], pd.DataFrame | None, list[dict[str, Any]]]:
    """Acquire and assemble one GW mirror origin entry plus optional opening schedule/chips."""
    pre_snaps = [s for s in all_snaps if s[0] < dl]
    bs_chips: list[dict[str, Any]] = []
    bs_club_ids: set[int] = set(range(1, 21))
    chosen_bs = None
    for _, repo_path in reversed(pre_snaps[-3:]):
        c_sha, c_dt = _commit_for_fplcache_path(gh_api_fn, repo_path)
        if c_dt < dl:
            chosen_bs = (repo_path, c_sha, c_dt)
            break
    if chosen_bs is None:
        bs_record: dict[str, Any] = {"season": season, "gw": gw, "status": "source_missing", "reason": "no_pre_deadline_fplcache"}
    else:
        repo_path, c_sha, c_dt = chosen_bs
        bs_url = f"https://raw.githubusercontent.com/Randdalf/fplcache/{c_sha}/{repo_path}"
        bs_rel = f"{season}/bootstraps/gw{gw:02d}.json.xz"
        bs_bytes = fetch_fn(bs_url, quarantine_root / bs_rel)
        bs_record = build_bootstrap_mirror_record(
            season=season, gw=gw, deadline=dl, prev_deadline=prev_dl, url=bs_url,
            repo_path=repo_path, commit_sha=c_sha, commit_time=c_dt, raw_bytes=bs_bytes, local_relpath=bs_rel,
        )
        _, payload = _unpack_bootstrap_xz(bs_bytes)
        bs_chips = list(payload.get("chips", []))
        bs_club_ids = {int(t["id"]) for t in payload.get("teams", [])}

    pre_fx = [c for c in fx_commits if c[0] < dl]
    opening_fx_df: pd.DataFrame | None = None
    if not pre_fx:
        fx_record: dict[str, Any] = {"season": season, "gw": gw, "status": "source_missing", "reason": "no_pre_deadline_fixtures"}
        window_rows: list[dict[str, Any]] = []
    else:
        fx_dt, fx_sha, _ = pre_fx[-1]
        prev_fx_dt = pre_fx[-2][0] if len(pre_fx) >= 2 else None
        fx_url = f"https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/{fx_sha}/data/{season}/fixtures.csv"
        fx_rel = f"{season}/fixtures/{fx_sha[:10]}.csv"
        fx_bytes = fetch_fn(fx_url, quarantine_root / fx_rel)
        fx_record = build_fixture_mirror_record(
            season=season, gw=gw, deadline=dl, prev_deadline=prev_dl, url=fx_url,
            commit_sha=fx_sha, commit_time=fx_dt, prev_commit_time=prev_fx_dt, raw_bytes=fx_bytes, local_relpath=fx_rel,
        )
        window_rows = parse_fixtures_csv_window(fx_bytes, gw)
        if gw == 1:
            opening_fx_df = pd.read_csv(io.BytesIO(fx_bytes))
            opening_fx_df["event"] = pd.to_numeric(opening_fx_df["event"], errors="coerce")

    final_dt, final_sha = final_merged
    settle_dt, settle_sha = gw_settlement.get(gw, (final_dt, final_sha))
    settle_url, settle_rel, settle_bytes = merged_meta_by_sha[settle_sha]
    gw_va_df = _extract_gw_df_from_merged_csv(settle_bytes, gw)
    gw_table_rows = sorted(gw_va_df.to_dict(orient="records"), key=lambda r: (str(r.get("element", "")), str(r.get("fixture", ""))))
    try:
        gw_zdiff = verify_settled_outcomes_zero_diff(gw_va_df, proc_perf[proc_perf["gameweek_id"] == gw], proc_players, season=season)
        gw_zdiff_ok, gw_ledger_mismatch = bool(gw_zdiff["zero_diff"]), int(gw_zdiff["ledger_mismatch_rows"])
    except ValueError:
        gw_zdiff_ok, gw_ledger_mismatch = False, -1
    lag_sec = (settle_dt - ko_dt).total_seconds()
    settled_meta = {
        "commit_sha": settle_sha,
        "url": settle_url,
        "finalized_at_utc": settle_dt.isoformat(),
        "max_kickoff_utc": ko_dt.isoformat(),
        "settlement_lag_seconds": round(lag_sec, 3),
        "meets_plus_24h": lag_sec >= SETTLEMENT_MIN_WAIT_SECONDS,
        "historical_performance_ready_by_next_gw": settle_dt < next_dl if next_dl is not None else True,
        "zero_diff_verified": gw_zdiff_ok,
        "ledger_mismatch_rows": gw_ledger_mismatch,
        "local_relpath": settle_rel,
        "blob_sha256": sha256_bytes(settle_bytes),
        "table_sha256": canonical_json_sha256(gw_table_rows),
    }
    origin_chips = build_causal_origin_chip_metadata(
        season, gw=gw, bootstrap_chips=bs_chips, horizon_fixtures=window_rows, club_ids=bs_club_ids,
    )
    prior_hist_ready = all(pgw in gw_settlement and gw_settlement[pgw][0] < dl for pgw in range(1, gw))
    origin_admitted = (
        bs_record["status"] == "supported"
        and fx_record["status"] == "supported"
        and settled_meta["meets_plus_24h"]
        and gw_zdiff_ok
        and prior_hist_ready
    )
    entry = {
        "gw": gw,
        "deadline_utc": dl.isoformat(),
        "origin_admitted": origin_admitted,
        "bootstrap": bs_record,
        "fixtures": fx_record,
        "settled_outcomes": settled_meta,
        "causal_chip_metadata": origin_chips,
    }
    return entry, opening_fx_df, bs_chips


def acquire_season_mirror(
    season: str,
    *,
    quarantine_root: Path = QUARANTINE_ROOT,
    gh_api_fn: Callable[[str], Any] = _gh_api,
    fetch_fn: Callable[[str, Path | None], bytes] = _fetch_bytes,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Acquire, verify zero-diff, and assemble dev mirror manifest for one season."""
    get_rules(season)
    lifecycle = load_season_lifecycle()
    lifecycle.assert_access(season, purpose="historical_filter" if lifecycle.role_of(season) == "historical_filter" else "dev")
    start_year = int(season[:4])
    all_snaps = _list_fplcache_paths_for_months(gh_api_fn, [(start_year, [8, 9, 10, 11, 12]), (start_year + 1, [1, 2, 3, 4, 5])])
    deadlines, max_ko, _ = _deadlines_and_max_kickoffs(
        season, fplcache_snapshots=all_snaps, gh_api_fn=gh_api_fn, fetch_fn=fetch_fn, quarantine_dir=quarantine_root
    )
    fx_commits = _vaastav_commits(gh_api_fn, f"data/{season}/fixtures.csv")
    merged_commits = _vaastav_commits(gh_api_fn, f"data/{season}/gws/merged_gw.csv")
    gw_settlement, merged_meta_by_sha, (final_dt, final_sha, final_bytes) = _resolve_settlement_commits(
        season=season, merged_commits=merged_commits, max_ko=max_ko, quarantine_root=quarantine_root, fetch_fn=fetch_fn
    )
    proc_dir = ROOT / "data/archive" / season / "processed"
    proc_perf = pd.read_parquet(proc_dir / "player_performances.parquet")
    proc_players = pd.read_parquet(proc_dir / "players.parquet")
    zero_diff_report = verify_settled_outcomes_zero_diff(pd.read_csv(io.BytesIO(final_bytes), low_memory=False), proc_perf, proc_players, season=season)

    origins: list[dict[str, Any]] = []
    opening_fx_df: pd.DataFrame | None = None
    opening_chips: list[dict[str, Any]] | None = None
    blocked_gws: list[dict[str, Any]] = []
    bootstrap_admitted = 0
    fixture_admitted = 0

    for gw in range(1, 39):
        dl = deadlines[gw]
        entry, gw1_fx, bs_chips = _acquire_origin_entry(
            season=season, gw=gw, dl=dl, prev_dl=deadlines[gw - 1] if gw > 1 else None,
            next_dl=deadlines[gw + 1] if gw < 38 else None, ko_dt=max_ko[gw],
            all_snaps=all_snaps, fx_commits=fx_commits, gw_settlement=gw_settlement,
            final_merged=(final_dt, final_sha), merged_meta_by_sha=merged_meta_by_sha,
            proc_perf=proc_perf, proc_players=proc_players, quarantine_root=quarantine_root,
            gh_api_fn=gh_api_fn, fetch_fn=fetch_fn,
        )
        if gw == 1:
            opening_fx_df, opening_chips = gw1_fx, bs_chips or None
        if entry["bootstrap"]["status"] == "supported":
            bootstrap_admitted += 1
        if entry["fixtures"]["status"] == "supported":
            fixture_admitted += 1
        if not entry["origin_admitted"]:
            reasons = []
            if entry["bootstrap"]["status"] != "supported":
                reasons.append(f"bootstrap:{entry['bootstrap']['status']}:{entry['bootstrap'].get('reason')}")
            if entry["fixtures"]["status"] != "supported":
                reasons.append(f"fixtures:{entry['fixtures']['status']}:{entry['fixtures'].get('reason')}")
            if not entry["settled_outcomes"]["meets_plus_24h"]:
                reasons.append("outcomes:premature_settlement_lt_24h")
            if not entry["settled_outcomes"]["zero_diff_verified"]:
                reasons.append("outcomes:zero_diff_failed")
            missing_prior = [pgw for pgw in range(1, gw) if pgw not in gw_settlement or gw_settlement[pgw][0] >= dl]
            if missing_prior:
                reasons.append(f"historical_performance_delayed:prior_gws={missing_prior}")
            blocked_gws.append({"gw": gw, "reasons": reasons})
        origins.append(entry)

    prefix_end = 0
    for entry in origins:
        if entry["origin_admitted"]:
            prefix_end = entry["gw"]
        else:
            break

    shared_chip_calendar = build_causal_chip_calendar(season, opening_schedule=opening_fx_df, bootstrap_chips=opening_chips)
    calendar_payload = [{"gameweek": gw, "chip": chip} for gw, chip in shared_chip_calendar]

    manifest = {
        "schema_version": 2,
        "season": season,
        "track": "development_mirror",
        "attributions": [
            {"repo": "Randdalf/fplcache", "license": "The Unlicense", "role": "pre-deadline bootstrap-static snapshots"},
            {"repo": "vaastav/Fantasy-Premier-League", "license": "NOASSERTION (provenance cited)", "role": "fixtures.csv & settled GW outcomes"},
        ],
        "summary": {
            "bootstrap_admitted_count": bootstrap_admitted,
            "fixture_admitted_count": fixture_admitted,
            "settled_outcomes_zero_diff": zero_diff_report["zero_diff"],
            "verified_outcome_rows": zero_diff_report["verified_rows"],
            "ledger_mismatch_rows": zero_diff_report["ledger_mismatch_rows"],
            "zero_minute_card_exceptions": zero_diff_report["zero_minute_card_exceptions"],
            "contiguous_admitted_prefix_end_gw": prefix_end,
            "full_season_admitted": prefix_end == 38,
            "partial_prefix_only": 0 < prefix_end < 38,
            "blocked_gw_count": len(blocked_gws),
            "blocked_gws": blocked_gws,
        },
        "shared_chip_calendar": calendar_payload,
        "shared_chip_calendar_sha256": canonical_json_sha256(calendar_payload),
        "origins": origins,
    }
    return manifest, zero_diff_report


def acquire_seed_manifest(
    *,
    season: str | None = None,
    quarantine_root: Path = QUARANTINE_ROOT,
    gh_api_fn: Callable[[str], Any] = _gh_api,
    fetch_fn: Callable[[str, Path | None], bytes] = _fetch_bytes,
) -> dict[str, Any]:
    """Acquire and build pinned prior-season seed commit manifest."""
    lifecycle = load_season_lifecycle()
    target_season = season or lifecycle.season_for_role("historical_filter")
    proc_dir = ROOT / "data/archive" / target_season / "processed"
    items = gh_api_fn(f"repos/vaastav/Fantasy-Premier-League/commits?path=data/{target_season}&per_page=5")
    vaastav_commits = [
        {
            "sha": str(c["sha"]),
            "committed_at_utc": _utc(c["commit"]["committer"]["date"]).isoformat(),
            "message": str(c["commit"]["message"]).splitlines()[0],
        }
        for c in items[:2]
    ]
    pin_sha = vaastav_commits[0]["sha"]
    upstream_digests: dict[str, dict[str, Any]] = {}
    for fname in ("players_raw.csv", "teams.csv", "fixtures.csv", "gws/merged_gw.csv"):
        url = f"https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/{pin_sha}/data/{target_season}/{fname}"
        rel = f"{target_season}/seed/{pin_sha[:10]}/{fname.replace('/', '_')}"
        raw = fetch_fn(url, quarantine_root / rel)
        upstream_digests[fname] = {
            "url": url,
            "commit_sha": pin_sha,
            "sha256": sha256_bytes(raw),
            "bytes": len(raw),
            "local_relpath": rel,
        }
    return build_seed_manifest(
        season=target_season,
        processed_dir=proc_dir,
        vaastav_commits=vaastav_commits,
        upstream_digests=upstream_digests,
    )


def main() -> None:
    lifecycle = load_season_lifecycle()
    dev_season = lifecycle.season_for_role("development")
    filter_season = lifecycle.season_for_role("historical_filter")
    allowed_seasons = [dev_season, filter_season]
    parser = argparse.ArgumentParser(description="Acquire & pin development/filter historical mirrors and seed manifest")
    parser.add_argument("--seasons", nargs="+", default=allowed_seasons, choices=allowed_seasons)
    parser.add_argument("--include-seed", action="store_true", help="Also regenerate prior-season seed manifest")
    args = parser.parse_args()

    QUARANTINE_ROOT.mkdir(parents=True, exist_ok=True)
    CONFIG_ROOT.mkdir(parents=True, exist_ok=True)
    zdiff_path = QUARANTINE_ROOT / "zero_diff_verification.json"
    reports: dict[str, Any] = {}
    if zdiff_path.exists():
        loaded_reports = json.loads(zdiff_path.read_text(encoding="utf-8"))
        if isinstance(loaded_reports, dict):
            reports.update(loaded_reports)

    for season in args.seasons:
        manifest, zdiff = acquire_season_mirror(season)
        reports[season] = zdiff
        out_name = f"dev_mirror_{season.replace('-', '_')}_manifest.json"
        (CONFIG_ROOT / out_name).write_text(json.dumps(manifest, indent=2) + "\n")
        (QUARANTINE_ROOT / f"zero_diff_verification_{season}.json").write_text(json.dumps(zdiff, indent=2) + "\n")
        print(
            f"[{season}] bootstraps={manifest['summary']['bootstrap_admitted_count']}/38 "
            f"fixtures={manifest['summary']['fixture_admitted_count']}/38 "
            f"contiguous_prefix=1..{manifest['summary']['contiguous_admitted_prefix_end_gw']} "
            f"zero_diff={manifest['summary']['settled_outcomes_zero_diff']} "
            f"rows={manifest['summary']['verified_outcome_rows']}"
        )

    zdiff_path.write_text(json.dumps(reports, indent=2) + "\n")
    if filter_season in args.seasons or args.include_seed:
        seed_manifest = acquire_seed_manifest()
        seed_name = f"seed_manifest_{filter_season.replace('-', '_')}.json"
        (CONFIG_ROOT / seed_name).write_text(json.dumps(seed_manifest, indent=2) + "\n")
        print(
            f"[seed {filter_season}] players={seed_manifest['players_total']} excluded_pos5={seed_manifest['excluded_position_5_count']} "
            f"retained={seed_manifest['retained_player_count']} defcon={seed_manifest['defensive_contribution_status']}"
        )


if __name__ == "__main__":
    main()

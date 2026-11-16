"""TDD tests for unified mode='empirical' admission and all 8 fail-closed negative classes (#178, #179)."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import lzma
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest

from backtesting.data_admission import assess_origins, require_admitted, require_input
from backtesting.forecast_adapter import EVENT_RATE_MAP, predict_issue
from backtesting.forecast_inputs import verify_training_bundle
from backtesting.forecast_store import generate_forecast, load_forecast_verified

UTC = timezone.utc


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canon(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _put(catalog: dict[str, bytes], obj: Any) -> str:
    raw = _canon(obj)
    digest = _sha(raw)
    catalog[digest] = raw
    return digest


def _make_bootstrap(
    gw: int, dl: datetime, *, include_manager: bool = False, chance: float | None = None
) -> tuple[bytes, bytes]:
    elements = []
    specs = (
        (1, 1, 50, True, "a", 101, None),
        (2, 1, 45, True, "a", 102, None),
        (3, 2, 50, True, "a", 103, None),
        (4, 2, 50, True, "a", 104, None),
        (5, 2, 50, True, "a", 105, None),
        (6, 2, 50, True, "a", 106, None),
        (7, 2, 50, True, "a", 107, None),
        (8, 3, 70, True, "a", 108, chance),
        (9, 3, 70, True, "d", 109, 75.0),
        (10, 3, 70, True, "a", 110, None),
        (11, 3, 70, True, "a", 111, None),
        (12, 3, 70, True, "a", 112, None),
        (13, 4, 80, True, "a", 113, None),
        (14, 4, 80, True, "a", 114, None),
        (15, 4, 80, True, "a", 115, None),
        (16, 4, 60, False, "u", 116, 0.0),  # purchase_eligible=False registered player
        (17, 3, 55, True, "a", 117, None),  # newcomer mapped via absent:17
    )
    for pid, pos, cost, can_sel, st, code, ch in specs:
        elements.append(
            {
                "id": pid,
                "code": code,
                "first_name": f"First{pid}",
                "second_name": f"Second{pid}",
                "web_name": f"Player{pid}",
                "team": (pid % 5) + 1,
                "element_type": pos,
                "now_cost": cost,
                "selected_by_percent": "10.0",
                "status": st,
                "can_select": can_sel,
                "chance_of_playing_next_round": ch,
                "news": "" if st == "a" else "Unavailable",
                "news_added": None,
            }
        )
    if include_manager:
        elements.append(
            {
                "id": 900,
                "code": 9000,
                "first_name": "Boss",
                "second_name": "Mgr",
                "web_name": "BossMgr",
                "team": 1,
                "element_type": 5,
                "now_cost": 15,
                "selected_by_percent": "2.0",
                "status": "a",
                "can_select": True,
                "chance_of_playing_next_round": None,
                "news": "",
                "news_added": None,
            }
        )
    payload = {
        "events": [{"id": gw, "deadline_time": dl.isoformat().replace("+00:00", "Z"), "is_next": True}],
        "teams": [
            {
                "id": cid,
                "name": f"Club{cid}",
                "short_name": f"C{cid}",
                "strength": 3,
                "strength_overall_home": 1100,
                "strength_overall_away": 1080,
                "strength_attack_home": 1100,
                "strength_attack_away": 1080,
                "strength_defence_home": 1100,
                "strength_defence_away": 1080,
            }
            for cid in range(1, 6)
        ],
        "elements": elements,
        "chips": [{"name": "wildcard", "start_event": 1, "stop_event": 19}],
    }
    raw_json = json.dumps(payload, sort_keys=True).encode("utf-8")
    return lzma.compress(raw_json), raw_json


def _make_fixtures_csv(gw: int, dl: datetime) -> bytes:
    buf = io.StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=["id", "event", "team_h", "team_a", "kickoff_time", "team_h_difficulty", "team_a_difficulty"],
    )
    writer.writeheader()
    for w in range(gw, min(gw + 6, 39)):
        for offset, (h, a) in enumerate(((1, 2), (3, 4), (5, 1)), 1):
            writer.writerow(
                {
                    "id": (w - 1) * 10 + offset,
                    "event": w,
                    "team_h": h,
                    "team_a": a,
                    "kickoff_time": (dl + timedelta(days=1 + 7 * (w - gw))).isoformat().replace("+00:00", "Z"),
                    "team_h_difficulty": 3,
                    "team_a_difficulty": 3,
                }
            )
    return buf.getvalue().encode("utf-8")


def _history_row(
    pid: int,
    gw: int,
    fid: int,
    kickoff: datetime,
    *,
    minutes: int = 90,
    total_points: int = 5,
    yellow_cards: int = 0,
    include_defcon: bool = True,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "player_id": pid,
        "fixture_id": fid,
        "gameweek_id": gw,
        "kickoff_time": kickoff.isoformat(),
        "minutes": minutes,
        "total_points": total_points,
        "starts": 1 if minutes > 0 else 0,
        "was_home": True,
        "opponent_club_id": 2,
    }
    for col, _ in EVENT_RATE_MAP:
        if col == "defensive_contribution" and not include_defcon:
            continue
        row[col] = 0
    row["yellow_cards"] = yellow_cards
    return row


def _build_empirical_bundle(
    *,
    gws: tuple[int, ...] = (1, 2),
    track: str = "development_mirror",
    bootstrap_age_hours: float = 4.0,
    fixtures_age_hours: float = 72.0,
    settlement_lag_hours: float = 30.0,
    disclosed: list[str] | None = None,
    include_gw22_card: bool = False,
    seed_season: str = "2024-25",
    partial_prefix: bool = True,
    with_manager: bool = True,
) -> tuple[dict[str, Any], dict[str, bytes], dict[int, str]]:
    dl1 = datetime(2025, 8, 15, 17, 30, tzinfo=UTC)
    deadlines = {w: dl1 + timedelta(days=7 * (w - 1)) for w in range(1, 39)}
    catalog: dict[str, bytes] = {}
    origins: list[dict[str, Any]] = []
    auth_by_gw: dict[int, str] = {}

    seed_players = [
        {
            "id": 100 + idx,
            "seed_key": f"code:{100 + idx}",
            "code": 100 + idx,
            "club_id": (idx % 5) + 1,
            "position_id": pos,
            "now_cost": 50,
            "first_name": f"First{idx}",
            "second_name": f"Second{idx}",
            "web_name": f"Player{idx}",
        }
        for idx, pos in [
            (1, 1), (2, 1), (3, 2), (4, 2), (5, 2), (6, 2), (7, 2),
            (8, 3), (9, 3), (10, 3), (11, 3), (12, 3), (13, 4), (14, 4), (15, 4), (16, 4),
        ]
    ]
    if with_manager:
        seed_players.append(
            {
                "id": 900,
                "seed_key": "code:9000",
                "code": 9000,
                "club_id": 1,
                "position_id": 5,
                "now_cost": 15,
                "first_name": "Boss",
                "second_name": "Mgr",
                "web_name": "BossMgr",
            }
        )
    seed_ko = datetime(2024, 9, 1, 14, 0, tzinfo=UTC)
    seed_history = []
    seed_fixtures = []
    for w in range(1, 10):
        seed_fixtures.append(
            {
                "id": w,
                "gameweek_id": w,
                "home_club_id": 1,
                "away_club_id": 2,
                "kickoff_time": (seed_ko + timedelta(days=7 * (w - 1))).isoformat(),
                "team_h_difficulty": 3,
                "team_a_difficulty": 3,
            }
        )
        for p in seed_players:
            seed_history.append(
                _history_row(
                    p["id"],
                    w,
                    w,
                    seed_ko + timedelta(days=7 * (w - 1)),
                    include_defcon=(seed_season != "2024-25"),
                )
            )

    seed_obj = {
        "season": seed_season,
        "commit_sha": "a" * 40,
        "defensive_contribution_status": "inapplicable_native" if seed_season == "2024-25" else "native",
        "players": seed_players,
        "history": seed_history,
        "seed_mapping": {str(i): str(100 + i) for i in range(1, 17)} | {"17": "absent:17"},
    }
    seed_bytes = _canon(seed_obj)
    seed_sha = _sha(seed_bytes)
    catalog["seed_2024_25"] = seed_bytes

    settled_history_rows: list[dict[str, Any]] = []
    history_gws: dict[int, datetime] = {}
    past_fixtures: list[dict[str, Any]] = []

    for gw in gws:
        dl = deadlines[gw]
        prev_dl = deadlines[gw - 1] if gw > 1 else None
        max_ko = dl + timedelta(days=2)
        bs_xz, bs_json = _make_bootstrap(gw, dl, include_manager=with_manager, chance=None)
        bs_blob_sha = _sha(bs_xz)
        bs_dec_sha = _sha(bs_json)
        bs_id = f"bootstrap_gw{gw}"
        catalog[bs_id] = bs_xz

        fx_csv = _make_fixtures_csv(gw, dl)
        fx_sha = _sha(fx_csv)
        fx_id = f"fixtures_gw{gw}"
        catalog[fx_id] = fx_csv

        bs_cap_up = dl - timedelta(hours=bootstrap_age_hours)
        bs_cap_lo = bs_cap_up - timedelta(minutes=25)
        fx_cap_up = dl - timedelta(hours=fixtures_age_hours)
        if track == "prospective_receipt":
            fx_cap_lo = fx_cap_up - timedelta(minutes=15)
        else:
            fx_cap_lo = max(prev_dl, fx_cap_up - timedelta(days=2)) if prev_dl else fx_cap_up

        prior_hist = [dict(r) for r in settled_history_rows if history_gws[r["gameweek_id"]] < dl]
        hist_bytes = _canon(prior_hist)
        hist_id = f"history_gw{gw}"
        catalog[hist_id] = hist_bytes

        finalized_at = max_ko + timedelta(hours=settlement_lag_hours)
        gw_outcomes = []
        for pid in range(1, 18):
            is_card = include_gw22_card and pid == 17
            row = _history_row(
                pid,
                gw,
                (gw - 1) * 10 + 1,
                max_ko,
                minutes=0 if is_card else 90,
                total_points=-1 if is_card else 2,
                yellow_cards=1 if is_card else 0,
                include_defcon=True,
            )
            row["appeared"] = not is_card
            gw_outcomes.append(row)
            settled_history_rows.append(row)
        history_gws[gw] = finalized_at
        out_bytes = _canon(gw_outcomes)
        out_id = f"outcomes_gw{gw}"
        catalog[out_id] = out_bytes

        lim = (
            list(disclosed)
            if disclosed is not None
            else (
                ["fplcache_mirror_provenance"] + (["fixture_schedule_gt_48h"] if fixtures_age_hours > 48 else [])
                if track == "development_mirror"
                else []
            )
        )
        origins.append(
            {
                "season": "2025-26",
                "gw": gw,
                "deadline": dl.isoformat(),
                "prev_deadline": prev_dl.isoformat() if prev_dl else None,
                "max_kickoff_utc": max_ko.isoformat(),
                "disclosed_limitations": lim,
                "sources": {
                    "bootstrap": {
                        "source_id": bs_id,
                        "role": "bootstrap",
                        "url": f"https://raw.githubusercontent.com/Randdalf/fplcache/{'a'*40}/cache/2025/8/{15 + gw}/1200.json.xz"
                        if track == "development_mirror"
                        else f"receipt://2025-26/gw{gw}/bootstrap",
                        "commit_sha": "a" * 40,
                        "timing_basis": "bounded_reconstruction" if track == "development_mirror" else "receipt",
                        "capture_lower": bs_cap_lo.isoformat(),
                        "capture_upper": bs_cap_up.isoformat(),
                        "blob_sha256": bs_blob_sha,
                        "decompressed_sha256": bs_dec_sha,
                    },
                    "fixtures": {
                        "source_id": fx_id,
                        "role": "fixtures",
                        "url": f"https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/{'b'*40}/data/2025-26/fixtures.csv"
                        if track == "development_mirror"
                        else f"receipt://2025-26/gw{gw}/fixtures",
                        "commit_sha": "b" * 40,
                        "timing_basis": "bounded_reconstruction" if track == "development_mirror" else "receipt",
                        "capture_lower": fx_cap_lo.isoformat(),
                        "capture_upper": fx_cap_up.isoformat(),
                        "blob_sha256": fx_sha,
                        "decompressed_sha256": fx_sha,
                    },
                    "history": {
                        "source_id": hist_id,
                        "role": "history",
                        "url": f"https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/{'c'*40}/data/2025-26/gws/merged_gw.csv"
                        if track == "development_mirror"
                        else f"receipt://2025-26/gw{gw}/history",
                        "commit_sha": "c" * 40,
                        "timing_basis": "bounded_reconstruction" if track == "development_mirror" else "receipt",
                        "capture_lower": (dl - timedelta(days=2)).isoformat(),
                        "capture_upper": (dl - timedelta(days=1)).isoformat(),
                        "blob_sha256": _sha(hist_bytes),
                        "decompressed_sha256": _sha(hist_bytes),
                    },
                    "outcomes": {
                        "source_id": out_id,
                        "role": "outcomes",
                        "url": f"https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/{'d'*40}/data/2025-26/gws/merged_gw.csv"
                        if track == "development_mirror"
                        else f"receipt://2025-26/gw{gw}/outcomes",
                        "commit_sha": "d" * 40,
                        "timing_basis": "bounded_reconstruction" if track == "development_mirror" else "receipt",
                        "finalized_at": finalized_at.isoformat(),
                        "finished": True,
                        "data_checked": True,
                        "blob_sha256": _sha(out_bytes),
                        "decompressed_sha256": _sha(out_bytes),
                    },
                    "seed": {
                        "source_id": "seed_2024_25",
                        "role": "seed",
                        "url": f"https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/{'a'*40}/data/2024-25/gws/merged_gw.csv"
                        if track == "development_mirror"
                        else "receipt://2024-25/seed",
                        "commit_sha": "a" * 40,
                        "timing_basis": "bounded_reconstruction" if track == "development_mirror" else "receipt",
                        "capture_lower": "2025-06-04T15:20:23+00:00",
                        "capture_upper": "2025-08-01T00:00:00+00:00",
                        "blob_sha256": seed_sha,
                        "decompressed_sha256": seed_sha,
                    },
                },
            }
        )
        # Keep past fixtures updated after outcomes
        past_fixtures.append(
            {
                "id": (gw - 1) * 10 + 1,
                "gameweek_id": gw,
                "home_club_id": 1,
                "away_club_id": 2,
                "kickoff_time": max_ko.isoformat(),
                "team_h_difficulty": 3,
                "team_a_difficulty": 3,
            }
        )

    request = {
        "version": 2,
        "mode": "empirical",
        "track": track,
        "season": "2025-26",
        "eligibility_policy": "empirical-v2",
        "partial_prefix": partial_prefix,
        "full_season_required": not partial_prefix,
        "shared_chip_calendar": [{"gameweek": 3, "chip": "triple_captain"}, {"gameweek": 25, "chip": "wildcard"}],
        "anchor": {"squad_ids": list(range(1, 16))},
        "origins": origins,
    }

    # Build content-addressed training bundle authority for each admitted GW after request input digests are computed
    reports = assess_origins(request, catalog)
    for rep in reports:
        if not rep.get("input_ready"):
            continue
        gw = rep["gw"]
        dl = deadlines[gw]
        bs_cap_up = dl - timedelta(hours=bootstrap_age_hours)
        bs_payload = json.loads(lzma.decompress(catalog[f"bootstrap_gw{gw}"]))
        fx_csv_rows = list(csv.DictReader(io.StringIO(catalog[f"fixtures_gw{gw}"].decode("utf-8"))))
        target_fixtures = [
            {
                "id": int(r["id"]),
                "gameweek_id": int(r["event"]),
                "home_club_id": int(r["team_h"]),
                "away_club_id": int(r["team_a"]),
                "kickoff_time": r["kickoff_time"],
                "team_h_difficulty": int(r["team_h_difficulty"]),
                "team_a_difficulty": int(r["team_a_difficulty"]),
            }
            for r in fx_csv_rows
        ]
        clubs_tbl = [
            {
                "id": c["id"],
                "name": c["name"],
                "short_name": c["short_name"],
                "strength": c["strength"],
                "strength_overall_home": c["strength_overall_home"],
                "strength_overall_away": c["strength_overall_away"],
                "strength_attack_home": c["strength_attack_home"],
                "strength_attack_away": c["strength_attack_away"],
                "strength_defence_home": c["strength_defence_home"],
                "strength_defence_away": c["strength_defence_away"],
            }
            for c in bs_payload["teams"]
        ]
        meta_tbl = [
            {
                "id": e["id"],
                "code": e["code"],
                "club_id": e["team"],
                "position_id": e["element_type"],
                "now_cost": e["now_cost"],
                "first_name": e["first_name"],
                "second_name": e["second_name"],
                "web_name": e["web_name"],
                "status": e["status"],
                "chance_of_playing_next_round": e["chance_of_playing_next_round"],
            }
            for e in bs_payload["elements"]
        ]
        hist_tbl = [dict(r) for r in settled_history_rows if history_gws[r["gameweek_id"]] < dl]
        hist_fx_tbl = [dict(r) for r in past_fixtures if int(r["gameweek_id"]) < gw]
        tables = {
            "clubs": clubs_tbl,
            "player_metadata": meta_tbl,
            "target_fixtures": target_fixtures,
            "history": hist_tbl,
            "history_fixtures": hist_fx_tbl,
            "seed_players": seed_players,
            "seed_history": seed_history,
            "seed_fixtures": seed_fixtures,
        }
        src_obj = {
            "mode": "empirical",
            "track": track,
            "url": origins[0]["sources"]["seed"]["url"],
            "revision": "a" * 40,
            "parser_version": "empirical-v2",
            "captured_at": bs_cap_up.isoformat(),
            "defensive_contribution_status": "inapplicable_native" if seed_season == "2024-25" else "native",
            "disclosed_limitations": origins[gw - 1]["disclosed_limitations"],
            "seed_mapping": seed_obj["seed_mapping"],
            "tables": tables,
        }
        src_digest = _put(catalog, src_obj)
        auth_obj = {
            "version": 2,
            "mode": "empirical",
            "track": track,
            "input_digest": rep["input_digest"],
            "season": "2025-26",
            "gw": gw,
            "seed_identity": f"seed:{seed_season}:{'a'*40}",
            "source_digest": src_digest,
        }
        auth_by_gw[gw] = _put(catalog, auth_obj)
    return request, catalog, auth_by_gw


def test_unified_empirical_two_track_parity_and_forecast_pipeline(tmp_path: Path) -> None:
    for track, fx_h in (("development_mirror", 72.0), ("prospective_receipt", 1.5)):
        req, cat, auth_map = _build_empirical_bundle(
            gws=(1, 2),
            track=track,
            bootstrap_age_hours=1.5 if track == "prospective_receipt" else 4.0,
            fixtures_age_hours=fx_h,
        )
        reports = assess_origins(req, cat)
        assert [r["status"] for r in reports] == ["admitted_empirical", "admitted_empirical"]
        assert all(r["partial_prefix"] is True and r["promotable"] is False for r in reports)

        cap = require_admitted(req, cat, "2025-26", 2)
        assert cap.track == track
        verify_training_bundle(require_input(req, cat, "2025-26", 2), req, cat, auth_map[2])
        inp = require_input(req, cat, "2025-26", 2)
        preds, meta = predict_issue(inp, req, cat, auth_map[2], tmp_path / f"work_{track}")
        assert meta["mode"] == track
        assert preds["chance_of_playing_next_round"].isna().sum() >= 1  # null preserved, never 100-coerced
        assert 900 not in set(preds["player_id"])  # Assistant Manager excluded
        assert meta["defensive_contribution_seed_status"] == "inapplicable_native"

        # Content-addressed forecast store supports empirical mode
        fid, frame, hit = generate_forecast(tmp_path / f"store_{track}", inp, req, cat, auth_map[2])
        assert hit is False and len(frame) == 120 and frame["player_id"].nunique() == 17
        fid2, frame2, hit2 = generate_forecast(tmp_path / f"store_{track}", inp, req, cat, auth_map[2])
        assert hit2 is True and fid2 == fid and len(frame2) == 120
        loaded, mat = load_forecast_verified(tmp_path / f"store_{track}", fid, inp, req, cat, auth_map[2])
        assert mat["mode"] == track and len(loaded) == 120


# --- 8 Mandatory Fail-Closed Negative Test Classes (#178 / #179) ---

def test_neg_class_1_cutoff_future_leak() -> None:
    req, cat, _ = _build_empirical_bundle(gws=(1, 2), bootstrap_age_hours=-0.5)
    reports = assess_origins(req, cat)
    assert reports[0]["status"] == "invalid"
    with pytest.raises(ValueError):
        require_admitted(req, cat, "2025-26", 1)


def test_neg_class_2_stale_mirror_and_prospective_receipt_ceilings() -> None:
    req_m, cat_m, _ = _build_empirical_bundle(gws=(1,), track="development_mirror", bootstrap_age_hours=25.0)
    assert assess_origins(req_m, cat_m)[0]["status"] == "unresolved"
    with pytest.raises(ValueError):
        require_admitted(req_m, cat_m, "2025-26", 1)

    req_p, cat_p, _ = _build_empirical_bundle(
        gws=(1,), track="prospective_receipt", bootstrap_age_hours=7.0, fixtures_age_hours=1.0
    )
    assert assess_origins(req_p, cat_p)[0]["status"] == "unresolved"

    # Mirror disclosures on prospective_receipt -> invalid
    req_leak, cat_leak, _ = _build_empirical_bundle(
        gws=(1,),
        track="prospective_receipt",
        bootstrap_age_hours=1.0,
        fixtures_age_hours=1.0,
        disclosed=["fplcache_mirror_provenance"],
    )
    assert assess_origins(req_leak, cat_leak)[0]["status"] == "invalid"


def test_neg_class_3_digest_tampering_blob_and_decompressed() -> None:
    req, cat, _ = _build_empirical_bundle(gws=(1,))
    req["origins"][0]["sources"]["bootstrap"]["blob_sha256"] = "0" * 64
    assert assess_origins(req, cat)[0]["status"] == "invalid"

    req2, cat2, _ = _build_empirical_bundle(gws=(1,))
    req2["origins"][0]["sources"]["bootstrap"]["decompressed_sha256"] = "f" * 64
    assert assess_origins(req2, cat2)[0]["status"] == "invalid"


def test_neg_class_4_premature_settlement_and_unchecked_prospective() -> None:
    req, cat, _ = _build_empirical_bundle(gws=(1,), settlement_lag_hours=12.0)
    assert assess_origins(req, cat)[0]["status"] == "unresolved"

    req2, cat2, _ = _build_empirical_bundle(gws=(1,), track="prospective_receipt", fixtures_age_hours=1.0)
    req2["origins"][0]["sources"]["outcomes"]["data_checked"] = False
    assert assess_origins(req2, cat2)[0]["status"] == "unresolved"


def test_neg_class_5_unreconciled_ledger_and_zero_min_card_exception() -> None:
    req_ok, cat_ok, _ = _build_empirical_bundle(gws=(1, 2), include_gw22_card=True)
    assert assess_origins(req_ok, cat_ok)[1]["status"] == "admitted_empirical"

    req_bad, cat_bad, _ = _build_empirical_bundle(gws=(1,))
    outcomes = json.loads(cat_bad["outcomes_gw1"])
    outcomes[0]["minutes"] = 0
    outcomes[0]["appeared"] = False
    outcomes[0]["total_points"] = 3
    bad_bytes = _canon(outcomes)
    cat_bad["outcomes_gw1"] = bad_bytes
    req_bad["origins"][0]["sources"]["outcomes"]["blob_sha256"] = _sha(bad_bytes)
    req_bad["origins"][0]["sources"]["outcomes"]["decompressed_sha256"] = _sha(bad_bytes)
    assert assess_origins(req_bad, cat_bad)[0]["status"] == "invalid"


def test_neg_class_6_seed_unmapped_newcomer_and_manager_exclusion() -> None:
    req, cat, _ = _build_empirical_bundle(gws=(1, 2))
    seed_obj = json.loads(cat["seed_2024_25"])
    del seed_obj["seed_mapping"]["17"]
    new_seed = _canon(seed_obj)
    cat["seed_2024_25"] = new_seed
    for o in req["origins"]:
        o["sources"]["seed"]["blob_sha256"] = _sha(new_seed)
        o["sources"]["seed"]["decompressed_sha256"] = _sha(new_seed)
    assert assess_origins(req, cat)[0]["status"] == "invalid"

    # Mapping a current player to position_id==5 seed manager must fail invalid
    req_mgr, cat_mgr, _ = _build_empirical_bundle(gws=(1,))
    so_mgr = json.loads(cat_mgr["seed_2024_25"])
    so_mgr["seed_mapping"]["17"] = "900"
    b_mgr = _canon(so_mgr)
    cat_mgr["seed_2024_25"] = b_mgr
    req_mgr["origins"][0]["sources"]["seed"]["blob_sha256"] = _sha(b_mgr)
    req_mgr["origins"][0]["sources"]["seed"]["decompressed_sha256"] = _sha(b_mgr)
    assert assess_origins(req_mgr, cat_mgr)[0]["status"] == "invalid"

    # Pre-2025-26 seed with imputed defensive_contribution fails invalid
    req_imp, cat_imp, _ = _build_empirical_bundle(gws=(1,))
    so_imp = json.loads(cat_imp["seed_2024_25"])
    so_imp["history"][0]["defensive_contribution"] = 5
    b_imp = _canon(so_imp)
    cat_imp["seed_2024_25"] = b_imp
    req_imp["origins"][0]["sources"]["seed"]["blob_sha256"] = _sha(b_imp)
    req_imp["origins"][0]["sources"]["seed"]["decompressed_sha256"] = _sha(b_imp)
    assert assess_origins(req_imp, cat_imp)[0]["status"] == "invalid"


def test_neg_class_7_anchor_ineligibility_and_null_chance_preserved() -> None:
    req, cat, _ = _build_empirical_bundle(gws=(1,))
    req["anchor"]["squad_ids"] = [*range(1, 15), 16]
    assert assess_origins(req, cat)[0]["status"] == "invalid"


def test_neg_class_8_window_gap_and_partial_prefix_overreach() -> None:
    req_gap, cat_gap, _ = _build_empirical_bundle(gws=(1, 3))
    assert assess_origins(req_gap, cat_gap)[1]["status"] == "unresolved"

    req_full, cat_full, _ = _build_empirical_bundle(gws=(1, 2), partial_prefix=False)
    reports = assess_origins(req_full, cat_full)
    assert all(r["promotable"] is False and r["partial_prefix"] is True for r in reports)
    with pytest.raises(ValueError, match="partial_prefix|full season"):
        require_admitted(req_full, cat_full, "2025-26", 2, require_full_season=True)


def test_pre_deadline_input_ready_decoupled_from_outcomes_and_real_seed_id_link(tmp_path: Path) -> None:
    """Pre-deadline prospective input_ready succeeds without outcomes; seed_id != Opta code still links."""
    req, cat, _ = _build_empirical_bundle(gws=(1,), track="prospective_receipt", bootstrap_age_hours=1.5, fixtures_age_hours=1.0)
    dig_before = assess_origins(req, cat)[0]["input_digest"]
    del req["origins"][0]["sources"]["outcomes"]
    rep_pre = assess_origins(req, cat)[0]
    assert rep_pre["status"] == "unresolved"
    assert rep_pre["input_ready"] is True
    assert rep_pre["input_digest"] == dig_before
    cap_pre = require_input(req, cat, "2025-26", 1)
    assert cap_pre.input_digest == dig_before

    # Arbitrary non-mirror disclosure on prospective_receipt is rejected
    req_arb, cat_arb, _ = _build_empirical_bundle(gws=(1,), track="prospective_receipt", bootstrap_age_hours=1.0, fixtures_age_hours=1.0, disclosed=["late_press"])
    assert assess_origins(req_arb, cat_arb)[0]["status"] == "invalid"

    # Full 38-GW request with downstream GW38 broken blocks promotable=True even on GW1
    req38, cat38, _ = _build_empirical_bundle(gws=tuple(range(1, 39)), partial_prefix=False)
    rep38_ok = assess_origins(req38, cat38)
    assert len(rep38_ok) == 38 and all(r["promotable"] is True and r["partial_prefix"] is False for r in rep38_ok)
    del req38["origins"][-1]["sources"]["outcomes"]
    rep38_broken = assess_origins(req38, cat38)
    assert all(r["promotable"] is False and r["partial_prefix"] is True for r in rep38_broken)

    # Seed id != Opta code links cleanly in empirical forecast_adapter and training cutoff < deadline enforced
    req2, cat2, auth2 = _build_empirical_bundle(gws=(1, 2), partial_prefix=True)
    seed_obj = json.loads(cat2["seed_2024_25"])
    for idx, p in enumerate(seed_obj["players"], 1):
        if int(p["position_id"]) != 5:
            p["code"] = 99000 + idx  # diverge Opta code from seed id
    sb = _canon(seed_obj)
    cat2["seed_2024_25"] = sb
    for o in req2["origins"]:
        o["sources"]["seed"]["blob_sha256"] = _sha(sb)
        o["sources"]["seed"]["decompressed_sha256"] = _sha(sb)
    # Rebuild auth2 with updated seed table + distinct code
    auth_obj = json.loads(cat2[auth2[2]])
    src_obj = json.loads(cat2[auth_obj["source_digest"]])
    src_obj["tables"]["seed_players"] = seed_obj["players"]
    new_src_dig = _put(cat2, src_obj)
    # Refresh input_digest after seed change
    rep2 = assess_origins(req2, cat2)[1]
    auth_obj["input_digest"] = rep2["input_digest"]
    auth_obj["source_digest"] = new_src_dig
    new_auth = _put(cat2, auth_obj)
    preds, _ = predict_issue(require_input(req2, cat2, "2025-26", 2), req2, cat2, new_auth, tmp_path / "seed_diff")
    assert len(preds) > 0

    # Tampering training history with future gw >= capability.gw fails closed
    bad_src = dict(src_obj)
    bad_src["tables"] = dict(src_obj["tables"])
    bad_src["tables"]["history"] = [*src_obj["tables"]["history"], {**src_obj["tables"]["history"][0], "gameweek_id": 2}]
    bad_auth = {**auth_obj, "source_digest": _put(cat2, bad_src)}
    with pytest.raises(ValueError, match="causal|gameweek"):
        verify_training_bundle(require_input(req2, cat2, "2025-26", 2), req2, cat2, _put(cat2, bad_auth))

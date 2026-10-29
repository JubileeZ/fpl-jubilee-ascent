"""Assess causal fixture coverage and independently finalized outcomes."""

from datetime import datetime
from math import isfinite
from typing import Any


def _time(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("Timestamp must be an ISO string")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Invalid timestamp") from exc
    if result.utcoffset() is None:
        raise ValueError("Timestamp must include timezone")
    return result


def _id(value: Any, *, gw: bool = False) -> int:
    if type(value) is not int or value < 1 or (gw and value > 38):
        raise ValueError("Invalid identifier or gameweek")
    return value


def _rows(package: Any, name: str, keys: set[str]) -> list[dict[str, Any]]:
    if not isinstance(package, dict) or not isinstance(package.get(name), list):
        raise ValueError(f"Malformed {name}")
    rows = package[name]
    if any(not isinstance(row, dict) or not keys <= row.keys() for row in rows):
        raise ValueError(f"Malformed {name}")
    return rows


def _fixture(row: dict[str, Any], id_key: str) -> tuple[int, int, int, int]:
    fid, gw, home, away = (
        _id(row[id_key]),
        _id(row["gw"], gw=True),
        _id(row["home_club"]),
        _id(row["away_club"]),
    )
    if home == away:
        raise ValueError("Fixture clubs must differ")
    return fid, gw, home, away


def _issue(
    input_package: dict[str, Any],
    issue_gw: int,
    target_gws: list[int],
    issue_cutoff: str,
) -> tuple[set[str], dict[int, int], dict[int, tuple[int, int, int]]]:
    _time(issue_cutoff)
    _id(issue_gw, gw=True)
    if not isinstance(target_gws, list) or not target_gws:
        raise ValueError("Invalid target gameweeks")
    for gw in target_gws:
        _id(gw, gw=True)
    if len(target_gws) != len(set(target_gws)) or issue_gw not in target_gws:
        raise ValueError("Invalid target gameweeks")
    players = _rows(input_package, "players", {"id", "club"})
    fixtures = _rows(input_package, "fixtures", {"id", "gw", "home_club", "away_club"})
    schedule = _rows(input_package, "schedule", {"player", "gw", "status", "fixture"})
    if not players:
        raise ValueError("Empty player universe")
    player_clubs = {_id(p["id"]): _id(p["club"]) for p in players}
    parsed = [_fixture(row, "id") for row in fixtures]
    fixture_map = {fid: (gw, home, away) for fid, gw, home, away in parsed}
    errors: set[str] = set()
    if len(player_clubs) != len(players) or len(fixture_map) != len(fixtures):
        errors.add("duplicate_identity")
    expected: set[tuple[int, int, int | None]] = set()
    for player, club in player_clubs.items():
        for gw in target_gws:
            matches = [
                fid
                for fid, (fgw, home, away) in fixture_map.items()
                if fgw == gw and club in (home, away)
            ]
            expected.update((player, gw, fid) for fid in matches or [None])
    observed: list[tuple[int, int, int | None]] = []
    for row in schedule:
        player, gw = _id(row["player"]), _id(row["gw"], gw=True)
        status, fixture = row["status"], row["fixture"]
        if (
            not isinstance(status, str)
            or status not in ("fixture", "blank")
            or (status == "blank") != (fixture is None)
        ):
            raise ValueError("Malformed schedule status")
        if fixture is not None:
            _id(fixture)
        observed.append((player, gw, fixture))
    if len(observed) != len(set(observed)) or set(observed) != expected:
        errors.add("schedule_coverage")
    return errors, player_clubs, fixture_map


def assess_issue_fixture_coverage(
    input_package: dict[str, Any],
    *,
    issue_gw: int,
    target_gws: list[int],
    issue_cutoff: str,
) -> tuple[str, ...]:
    errors, _, _ = _issue(input_package, issue_gw, target_gws, issue_cutoff)
    return tuple(sorted(errors))


def assess_fixture_coverage(
    input_package: dict[str, Any],
    outcome_package: dict[str, Any],
    *,
    issue_gw: int,
    target_gws: list[int],
    issue_cutoff: str,
    outcome_cutoff: str,
) -> tuple[str, ...]:
    """Validate issue schedule and event timelines through selected outcome capture."""
    errors, player_clubs, fixtures = _issue(
        input_package, issue_gw, target_gws, issue_cutoff
    )
    cutoff, captured = _time(issue_cutoff), _time(outcome_cutoff)
    if captured <= cutoff:
        raise ValueError("Outcome capture must follow issue cutoff")
    events = _rows(
        outcome_package,
        "fixture_events",
        {
            "fixture",
            "gw",
            "status",
            "home_club",
            "away_club",
            "changed_at",
            "finalized_at",
        },
    )
    outcomes = _rows(
        outcome_package, "outcomes", {"player", "gw", "fixture", "status", "points"}
    )
    by_fixture: dict[int, list[tuple[datetime, dict[str, Any]]]] = {}
    identities = {fid: (home, away) for fid, (_, home, away) in fixtures.items()}
    for row in events:
        fid, _, home, away = _fixture(row, "fixture")
        status = row["status"]
        if not isinstance(status, str) or status not in (
            "final",
            "postponed",
            "introduced",
        ):
            raise ValueError("Malformed event status")
        if fid in identities and identities[fid] != (home, away):
            errors.add("fixture_identity")
        identities.setdefault(fid, (home, away))
        stamp = row["finalized_at"] if status == "final" else row["changed_at"]
        if stamp is None:
            errors.add(
                "event_finalization" if status == "final" else "event_chronology"
            )
            continue
        when = _time(stamp)
        if not cutoff < when <= captured:
            errors.add("event_chronology")
        by_fixture.setdefault(fid, []).append((when, row))
    finals: list[dict[str, Any]] = []
    for fid in set(fixtures) | set(by_fixture):
        original = fixtures.get(fid)
        active = original[0] if original else None
        ever_issue = active == issue_gw
        done = False
        timeline = sorted(by_fixture.get(fid, []), key=lambda item: item[0])
        if len({t for t, _ in timeline}) != len(timeline):
            errors.add("event_chronology")
        for _, row in timeline:
            status, gw = row["status"], row["gw"]
            if done:
                errors.add("event_transition")
            if status == "postponed":
                if active != gw:
                    errors.add("event_transition")
                active = None
            elif status == "introduced":
                if active is not None:
                    errors.add("event_transition")
                active = gw
                ever_issue |= gw == issue_gw
            else:
                if active != gw:
                    errors.add("event_transition")
                done = True
                active = None
                finals.append(row)
        if ever_issue and active == issue_gw and not done:
            errors.add("event_coverage")
    expected = {
        (p, issue_gw, f["fixture"])
        for f in finals
        if f["gw"] == issue_gw
        for p, club in player_clubs.items()
        if club in (f["home_club"], f["away_club"])
    }
    actual: list[tuple[int, int, int]] = []
    for row in outcomes:
        player, gw, fid = (
            _id(row["player"]),
            _id(row["gw"], gw=True),
            _id(row["fixture"]),
        )
        status, points = row["status"], row["points"]
        if (
            not isinstance(status, str)
            or status not in ("played", "dnp")
            or type(points) not in (int, float)
        ):
            raise ValueError("Malformed outcome")
        if isinstance(points, float) and not isfinite(points):
            raise ValueError("Malformed outcome points")
        if isinstance(points, int) and points.bit_length() > 1023:
            raise ValueError("Malformed outcome points")
        if status == "dnp" and points != 0:
            raise ValueError("DNP points must be zero")
        actual.append((player, gw, fid))
    if len(actual) != len(set(actual)) or set(actual) != expected:
        errors.add("outcome_coverage")
    return tuple(sorted(errors))

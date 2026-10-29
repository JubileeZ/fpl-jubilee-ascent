from typing import cast

import pytest

from backtesting.admission_fixtures import assess_fixture_coverage

CUTOFF = "2024-08-01T12:00:00Z"


def packages() -> tuple[dict, dict]:
    return (
        {"players": [{"id": 1, "club": 10}, {"id": 2, "club": 20}],
         "fixtures": [{"id": 100, "gw": 1, "home_club": 10, "away_club": 20}],
         "schedule": [{"player": p, "gw": 1, "status": "fixture", "fixture": 100} for p in (1, 2)]
         + [{"player": p, "gw": 2, "status": "blank", "fixture": None} for p in (1, 2)]},
        {"fixture_events": [{"fixture": 100, "gw": 1, "status": "final", "home_club": 10, "away_club": 20,
                             "changed_at": None, "finalized_at": "2024-08-03T12:00:00Z"}],
         "outcomes": [{"player": p, "gw": 1, "fixture": 100, "status": "played", "points": 2} for p in (1, 2)]},
    )


def check(a: dict, b: dict) -> tuple[str, ...]:
    return assess_fixture_coverage(a, b, issue_gw=1, target_gws=[1, 2], issue_cutoff=CUTOFF, outcome_cutoff="2024-08-10T12:00:00Z")


def test_fixture_and_blank_covered() -> None:
    assert check(*packages()) == ()


def test_missing_is_not_zero() -> None:
    a, b = packages()
    b["outcomes"].pop()
    assert "outcome_coverage" in check(a, b)


def test_postponement_requires_timestamp_and_no_outcome() -> None:
    a, b = packages()
    b["fixture_events"][0].update(status="postponed", changed_at="2024-08-02T12:00:00Z", finalized_at=None)
    b["outcomes"] = []
    assert check(a, b) == ()
    b["fixture_events"][0]["changed_at"] = CUTOFF
    assert "event_chronology" in check(a, b)


def test_unknown_status_is_malformed() -> None:
    a, b = packages()
    a["schedule"][0]["status"] = "unknown"
    with pytest.raises(ValueError):
        check(a, b)


def test_double_gameweek_requires_each_fixture() -> None:
    a, b = packages()
    a["fixtures"].append({"id": 101, "gw": 1, "home_club": 20, "away_club": 10})
    a["schedule"].extend({"player": p, "gw": 1, "status": "fixture", "fixture": 101} for p in (1, 2))
    b["fixture_events"].append({"fixture": 101, "gw": 1, "status": "final", "home_club": 20, "away_club": 10,
                                "changed_at": None, "finalized_at": "2024-08-04T12:00:00Z"})
    assert "outcome_coverage" in check(a, b)
    b["outcomes"].extend({"player": p, "gw": 1, "fixture": 101, "status": "dnp", "points": 0} for p in (1, 2))
    assert check(a, b) == ()


def test_introduced_fixture_requires_post_cutoff_event() -> None:
    a, b = packages()
    a["fixtures"] = []
    a["schedule"] = [{"player": p, "gw": gw, "status": "blank", "fixture": None} for p in (1, 2) for gw in (1, 2)]
    assert "event_transition" in check(a, b)
    b["fixture_events"].append({"fixture": 100, "gw": 1, "status": "introduced", "home_club": 10, "away_club": 20,
                                "changed_at": "2024-08-02T12:00:00Z", "finalized_at": None})
    assert check(a, b) == ()


def test_introduced_fixture_requires_final_or_postponement() -> None:
    a, b = packages()
    b["fixture_events"].append({"fixture": 101, "gw": 1, "status": "introduced", "home_club": 10, "away_club": 20,
                                "changed_at": "2024-08-02T12:00:00Z", "finalized_at": None})
    assert "event_coverage" in check(a, b)


def test_postpone_reintroduce_same_week() -> None:
    a, b = packages()
    base = {"fixture": 100, "gw": 1, "home_club": 10, "away_club": 20, "finalized_at": None}
    b["fixture_events"] += [base | {"status": "postponed", "changed_at": "2024-08-02T12:00:00Z"},
                            base | {"status": "introduced", "changed_at": "2024-08-02T13:00:00Z"}]
    assert check(a, b) == ()
    b["fixture_events"][-1]["changed_at"] = "2024-08-04T12:00:00Z"
    assert "event_transition" in check(a, b)


def test_unknown_fixture_conflicting_identity() -> None:
    a, b = packages()
    base = {"fixture": 101, "gw": 1, "home_club": 10, "away_club": 20, "finalized_at": None}
    b["fixture_events"] += [base | {"status": "introduced", "changed_at": "2024-08-02T12:00:00Z"},
                            base | {"status": "postponed", "home_club": 20, "away_club": 10, "changed_at": "2024-08-02T13:00:00Z"}]
    assert "fixture_identity" in check(a, b)


@pytest.mark.parametrize("mutation", ["bad_id", "bad_gw", "empty", "bad_status", "huge_points", "bad_package"])
def test_malformed_values_raise_value_error(mutation: str) -> None:
    a, b = packages()
    if mutation == "bad_id":
        a["players"][0]["id"] = []
    elif mutation == "bad_gw":
        a["fixtures"][0]["gw"] = 39
    elif mutation == "empty":
        a["players"] = []
    elif mutation == "bad_status":
        b["fixture_events"][0]["status"] = []
    elif mutation == "huge_points":
        b["outcomes"][0]["points"] = 10 ** 1000
    else:
        b = None
    with pytest.raises(ValueError):
        check(a, cast(dict, b))

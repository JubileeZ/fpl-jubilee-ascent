from solver.utils import load_solver_static


def test_load_solver_static_uses_injected_payloads() -> None:
    bootstrap = {"elements": [{"id": 1}]}
    fixtures = [{"event": 1, "team_h": 1, "team_a": 2}]
    got_bootstrap, got_fixtures = load_solver_static(
        {"fpl_bootstrap": bootstrap, "fpl_fixtures": fixtures}
    )
    assert got_bootstrap is bootstrap
    assert got_fixtures is fixtures

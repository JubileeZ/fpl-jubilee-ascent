"""Ownership Explorer dashboard view markers."""

from pathlib import Path


def test_dashboard_html_has_explorer_view() -> None:
    html = Path("dashboard/index.html").read_text(encoding="utf-8")
    assert 'id="explorer-root"' in html
    assert 'id="chart-ownership"' in html
    assert 'id="chart-price"' in html
    assert 'id="explorer-table"' in html
    assert "plotly" in html.lower()
    assert "explorer.js" in html
    assert "xP per Gameweek" in html
    assert 'class="title">Price' in html
    assert 'id="mix-a-list"' in html
    assert 'id="tab-plan"' in html
    assert "Squad Builder" not in html
    assert "First-Half Horizon" not in html
    assert 'value="first_half"' not in html
    assert 'value="all_projection"' not in html


def test_explorer_script_uses_planning_horizon_and_mix() -> None:
    js = Path("dashboard/explorer.js").read_text(encoding="utf-8")
    assert "rate_per_90" in js
    assert "per_gameweek" in js
    assert "mixA" in js
    assert "getViewGws" in js
    assert "Projected Rate" in js
    assert "xP per Gameweek" in js
    assert "realized_points" not in js
    assert "first_half" not in js


def test_plan_controls_include_keep_ban_and_enabled_chips() -> None:
    html = Path("dashboard/index.html").read_text(encoding="utf-8")
    plan = Path("dashboard/plan.js").read_text(encoding="utf-8")
    assert 'id="plan-enabled-chips"' in html
    assert 'id="btn-force-keep"' in html
    assert "force_keep" in plan
    assert "enabled_chips" in plan
    assert "Force Keep" in html
    assert "owned_squad_ids" in plan

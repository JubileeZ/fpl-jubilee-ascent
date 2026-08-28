"""Ownership Explorer dashboard view markers."""

from pathlib import Path


def test_dashboard_html_has_explorer_view() -> None:
    html = Path("dashboard/index.html").read_text(encoding="utf-8")
    js = Path("dashboard/app.js").read_text(encoding="utf-8")
    assert 'id="explorer-root"' in html
    assert 'id="chart-ownership"' in html
    assert 'id="chart-price"' in html
    assert 'id="explorer-table"' in html
    assert "plotly" in html.lower()
    assert "explorer.js" in html
    assert "xP per Gameweek" in html
    assert 'class="title">Price' in html
    assert 'id="mix-a-list"' in html
    assert 'id="horizonStart"' in html
    assert 'id="horizonEnd"' in html
    assert "Horizon begins" in html
    assert "Horizon to" in html
    assert 'id="btn-refresh"' in html
    assert "/api/refresh" in js
    assert 'id="tab-plan"' not in html
    assert "plan.js" not in html
    assert "Squad Builder" not in html
    assert "Transfer Plan" not in html
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


def test_mix_panel_sits_after_charts_before_table() -> None:
    html = Path("dashboard/index.html").read_text(encoding="utf-8")
    assert html.index('class="explorer-charts"') < html.index('class="card mix-panel"')
    assert html.index('class="card mix-panel"') < html.index('id="explorer-table-wrap"')


def test_mix_panel_has_drop_columns_remove_and_full_reason() -> None:
    html = Path("dashboard/index.html").read_text(encoding="utf-8")
    js = Path("dashboard/explorer.js").read_text(encoding="utf-8")
    assert 'data-mix-side="a"' in html
    assert 'data-mix-side="b"' in html
    assert 'id="mix-reason"' in html
    assert "applyMixLetter" in js
    assert "removeMixMember" in js
    assert "moveMixMember" in js
    assert "mix-item-name" in js
    assert "data-mix-remove" in js
    assert "Mix A is full (5)." in js
    assert "mix-on" in js

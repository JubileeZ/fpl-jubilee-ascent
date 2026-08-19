"""Ownership Explorer dashboard view markers."""

from pathlib import Path


def test_dashboard_html_has_explorer_view() -> None:
    html = Path("dashboard/index.html").read_text(encoding="utf-8")
    assert 'id="explorer-root"' in html
    assert 'id="chart-ownership"' in html
    assert 'id="chart-price"' in html
    assert 'id="explorer-table"' in html
    assert 'value="first_half"' in html
    assert 'value="all_projection"' in html
    assert "plotly" in html.lower()
    assert "explorer.js" in html
    assert "First-Half Horizon" in html
    assert "xP per Gameweek" in html
    assert 'class="title">Price' in html
    assert 'data-sort="total"' in html
    assert "squad-only" in html


def test_explorer_script_uses_score_mode_and_shared_y() -> None:
    js = Path("dashboard/explorer.js").read_text(encoding="utf-8")
    assert "rate_per_90" in js
    assert "per_gameweek" in js
    assert "realized_points" in js
    assert "remaining_projection" in js
    assert "selectedPlayerId" in js
    assert "tableSortKey" in js
    assert "applyChartOnly" in js
    assert "avg_minutes >= 60" not in js
    assert "Projected Rate" in js
    assert "xP per Gameweek" in js


def test_squad_controls_hide_on_explorer_view() -> None:
    app = Path("dashboard/app.js").read_text(encoding="utf-8")
    css = Path("dashboard/styles.css").read_text(encoding="utf-8")
    assert "data-view" in app
    assert "squad-only" in css

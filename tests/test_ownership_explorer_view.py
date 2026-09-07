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
    assert "squad.js" in html
    assert "xP per Gameweek" in html
    assert 'id="explorer-assume-90"' in html
    assert html.index('value="per_gameweek"') < html.index('id="explorer-assume-90"')
    assert 'class="title">Price' in html
    assert 'id="horizonStart"' in html
    assert 'id="horizonEnd"' in html
    assert "Horizon begins" in html
    assert "Horizon to" in html
    assert 'id="btn-refresh"' in html
    assert 'id="btn-dream-team"' in html
    assert "/api/refresh" in js
    assert "/api/dream-team" in js
    assert 'id="tab-plan"' not in html
    assert "plan.js" not in html
    assert "Squad Builder" not in html
    assert "Transfer Plan" not in html
    assert "First-Half Horizon" not in html
    assert 'value="first_half"' not in html
    assert 'value="all_projection"' not in html
    assert 'id="mix-a-list"' not in html


def test_explorer_script_uses_planning_horizon_without_mix() -> None:
    js = Path("dashboard/explorer.js").read_text(encoding="utf-8")
    assert "rate_per_90" in js
    assert "per_gameweek" in js
    assert "getViewGws" in js
    assert "Projected Rate" in js
    assert "xP per Gameweek" in js
    assert "realized_points" not in js
    assert "first_half" not in js
    assert "assumeNinetyRow" in js
    assert "explorer-assume-90" in js
    assert "data-mins90" not in js
    assert "toggleAssume90" not in js
    assert "applyMixLetter" not in js
    assert "mixA" not in js


def test_squad_board_sits_before_charts() -> None:
    html = Path("dashboard/index.html").read_text(encoding="utf-8")
    assert html.index('id="squad-board"') < html.index('class="explorer-charts"')
    assert html.index('id="component-profile"') < html.index('class="explorer-charts"')
    assert html.index('class="explorer-charts"') < html.index('id="explorer-table-wrap"')
    assert 'id="squad-reset"' in html
    assert 'id="squad-reload"' in html
    assert 'id="squad-empty-refresh"' in html
    assert 'id="rule-breach-banner"' in html
    assert "No User Squad" in html


def test_squad_board_script_has_what_if_rules() -> None:
    js = Path("dashboard/squad.js").read_text(encoding="utf-8")
    assert "autoCaptain" in js
    assert "squadXp" in js
    assert "Same Position only." in js
    assert "ruleBreaches" in js
    assert "initSquadBoard" in js
    assert "Official Captain:" in js
    assert "FPL C:" not in js
    assert 'effectAllowed = "copy"' not in js
    assert "Already in the 15." in js
    assert "xp_goals" in js
    assert "assumeNinetyRow" in js


def test_reload_rereads_dashboard_json_without_refresh() -> None:
    app = Path("dashboard/app.js").read_text(encoding="utf-8")
    assert "reloadDashboardJson" in app
    assert "loadDashboardJson" in app


def test_player_component_card_and_xmin_profile_labels() -> None:
    html = Path("dashboard/index.html").read_text(encoding="utf-8")
    explorer = Path("dashboard/explorer.js").read_text(encoding="utf-8")
    squad = Path("dashboard/squad.js").read_text(encoding="utf-8")
    app = Path("dashboard/app.js").read_text(encoding="utf-8")
    assert 'id="player-component-card"' in html
    assert 'id="player-component-head"' in html
    assert 'id="player-component-body"' in html
    assert html.index('class="explorer-charts"') < html.index('id="player-component-card"')
    assert html.index('id="player-component-card"') < html.index('id="explorer-table-wrap"')
    assert 'id="explorer-xmins-floor"' in html
    assert 'id="explorer-xmins-floor-val">0</span>' in html
    assert "renderPlayerComponents" in explorer
    assert "PLAYER_COMPONENT_ROWS" in explorer
    assert "setExplorerSelectedPlayer" in explorer
    assert "setExplorerSelectedPlayer" in squad
    assert "setDreamTeamIds" in explorer
    assert "clearDreamTeam" in explorer
    assert "clearDreamTeam" in app
    assert 'dream-badge">Dream' in explorer or "Dream</span>" in explorer
    assert "dreamTeamIds" in explorer
    assert '["xmins", "xMins"]' in squad
    assert '["xp_minutes", "Appearance xP"]' in squad
    assert '["xp_minutes", "Minutes"]' not in squad

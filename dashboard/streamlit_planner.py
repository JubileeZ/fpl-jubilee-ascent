"""Single editable plan with player inspection and automatic legal Starting XI."""

from __future__ import annotations

from collections.abc import Callable
import json
from typing import Any

import streamlit as st

from dashboard.planner import POSITION_NAMES, Planner, PlanStore, digest
from dashboard.planner_jobs import PlannerJobs
from dashboard.planner_service import (PlannerPaths, import_cached_recommendations, load_dataset,
                                       make_solve_request, player_history, refresh_request,
                                       solve_request, source_digest)
from solver.scenarios import ARM_NAMES


def save(planner: Planner, store: PlanStore) -> bool:
    st.session_state["planner"] = planner
    try:
        store.save(planner.state, expected_digest=st.session_state.get("draft_digest", digest(store.load())))
        st.session_state["draft_digest"] = digest(planner.state)
        st.session_state["save_error"] = None
        return True
    except ValueError as exc:
        st.session_state["save_error"] = str(exc)
        st.session_state["stale_browser"] = True
        return False
    except OSError:
        st.session_state["save_error"] = "Draft not saved. Check writable storage and retry saving before closing browser."
        return False


def edit(planner: Planner, store: PlanStore, action: Callable[[], None]) -> None:
    try:
        action()
        save(planner, store)
        st.rerun()
    except ValueError as exc:
        st.error(str(exc))


def confirm_reset(planner: Planner, store: PlanStore, scenario: str | None = None) -> None:
    scenario = st.session_state.get("reset_scenario", scenario)
    planner = st.session_state["planner"]
    st.write(f"Use {ARM_NAMES[scenario or planner.state['scenario']]} and replace manual transfers, chip bookings, and lineup overrides with its solver recommendation or an unsolved hold draft.")
    if st.button("Replace edits", key="confirm-reset", type="primary"):
        planner.reset(scenario)
        st.session_state.pop("reset_scenario", None)
        save(planner, store)
        st.rerun()
    if st.button("Keep my edits", key="cancel-reset", shortcut="Esc"):
        st.session_state.pop("reset_scenario", None)
        st.rerun()


def confirm_new_plan(dataset: dict[str, Any], store: PlanStore) -> None:
    st.write("Your saved draft remains in memory until you confirm. Starting again replaces manual choices with the refreshed User Squad.")
    if st.button("Start new plan", key="confirm-new", type="primary"):
        st.session_state.pop("new_plan_confirmation", None)
        save(Planner(dataset), store)
        st.session_state.pop("selected_player", None)
        st.session_state.pop("replacement", None)
        st.rerun()
    if st.button("Keep saved draft", key="cancel-new", shortcut="Esc"):
        st.session_state.pop("new_plan_confirmation", None)
        st.rerun()


@st.fragment(run_every=2)
def job_status(paths: PlannerPaths, store: PlanStore, jobs: PlannerJobs) -> None:
    planner = st.session_state["planner"]
    job_id = planner.state.get("job_id")
    if not job_id:
        return
    try:
        job = jobs.status(job_id)
    except (ValueError, OSError) as exc:
        st.error(str(exc))
        return
    if job["status"] == "running":
        st.info("Working. Solver jobs can take up to 20 minutes per scenario; you can inspect or edit your draft while waiting.")
        return
    if planner.state.get("handled_job") != job_id:
        if job["status"] == "finished" and job["request"].get("kind") == "solve":
            result = job["result"]
            unchanged = source_digest(paths) == job["request"]["source_digest"]
            accepted = planner.accept_recommendations(result["plans"], job["request"]["snapshot"] if unchanged else "stale",
                                                       job["request"]["data_digest"])
            st.session_state["job_notice"] = "Solver recommendation ready." if accepted else "Draft or data changed during solve. Results retained separately; your current edits were preserved."
            st.session_state["arm_errors"] = result.get("errors", {})
        elif job["status"] == "finished":
            st.session_state["job_notice"] = "Refresh complete. Start a new plan from refreshed User Squad to use updated inputs."
        else:
            st.session_state["job_notice"] = job.get("error") or "Job interrupted; retry when ready."
        planner.state["handled_job"] = job_id
        save(planner, store)
        st.rerun()
    if job["status"] in ("failed", "interrupted"):
        st.error(job.get("error") or "Job failed; last usable plan retained.")


def begin_job(planner: Planner, store: PlanStore, jobs: PlannerJobs, paths: PlannerPaths, refresh: bool = False) -> None:
    try:
        if not save(planner, store):
            return
        request = {"kind": "refresh"} if refresh else make_solve_request(planner, paths)
        worker = (lambda payload: refresh_request(payload, paths)) if refresh else (lambda payload: solve_request(payload, paths))
        job_id = jobs.start(request, worker)
        planner.state["job_id"] = job_id
        planner.state.pop("handled_job", None)
        save(planner, store)
        st.session_state.pop("job_notice", None)
        st.rerun()
    except (ValueError, OSError) as exc:
        st.error(str(exc))


def player_button(planner: Planner, pid: int, gw: int, week: dict[str, Any]) -> None:
    player = planner.players.get(pid)
    if player is None:
        st.warning(f"Player {pid} absent from data. Refresh required.")
        return
    projection = player.get("projections", {}).get(f"gw{gw}", {})
    score = f"{float(projection['total_xp']):.1f} xP" if projection.get("total_xp") is not None else "Projection unavailable"
    role = " · C" if pid == week["captain_id"] else " · V" if pid == week["vice_id"] else ""
    if st.button(f"{player['name']} · {score}{role}", key=f"player-{pid}", width="stretch"):
        st.session_state["selected_player"] = pid
        st.session_state.pop("replacement", None)
        st.rerun()
    st.caption(f"{player.get('team', '')} · {player.get('pos', '')} · £{float(player['price']):.1f}m")


def pitch(planner: Planner, gw: int, week: dict[str, Any]) -> None:
    with st.container(key="pitch"):
        st.subheader("Starting XI")
        for position in (1, 2, 3, 4):
            players = [pid for pid in week["lineup_ids"] if pid in planner.players and planner.players[pid]["pos_id"] == position]
            st.caption(POSITION_NAMES[position])
            if not players:
                st.write("Incomplete selection")
            else:
                for column, pid in zip(st.columns(len(players)), players, strict=True):
                    with column:
                        player_button(planner, pid, gw, week)
    with st.container(key="bench"):
        st.subheader("Bench and replacement slots")
        bench = week["bench_ids"]
        if bench:
            for column, pid in zip(st.columns(len(bench)), bench, strict=True):
                with column:
                    player_button(planner, pid, gw, week)
        for outgoing in week["vacancies"]:
            player = planner.players.get(outgoing)
            if player is None:
                st.warning("Vacant slot's Player missing from current data. Refresh required.")
                continue
            if st.button(f"Add {POSITION_NAMES[player['pos_id']]} · replacing {player['name']}", key=f"vacancy-{outgoing}"):
                origin = next((int(key) for key, moves in planner.state["edits"].items()
                               if any(move["out"] == outgoing and move["in"] is None for move in moves)), gw)
                planner.state["selected_gw"] = origin
                st.session_state["replacement"] = outgoing
                st.session_state.pop("selected_player", None)
                st.rerun()


def replacement_panel(planner: Planner, store: PlanStore, gw: int, outgoing: int) -> None:
    player = planner.players.get(outgoing)
    if player is None:
        st.info("Select a current Player or replacement vacancy.")
        return
    st.subheader(f"Replace {player['name']}")
    query = st.text_input("Find replacement", placeholder="Player or Club", key=f"search-{outgoing}")
    candidates = [pid for pid in planner.candidates(gw, outgoing) if query.casefold() in
                  f"{planner.players[pid]['name']} {planner.players[pid].get('team', '')}".casefold()]
    st.caption("Eligible Players by selected-week projection; Position, budget, uniqueness, and Club limit applied.")
    if not candidates:
        st.info("No eligible replacement. Change search or sell another Player to increase budget.")
    for pid in candidates[:20]:
        candidate = planner.players[pid]
        if st.button(f"Add {candidate['name']} · £{candidate['price']:.1f}m · {planner.xp(pid, gw):.1f} xP", key=f"buy-{pid}", width="stretch"):
            try:
                planner.buy(gw, outgoing, pid)
                save(planner, store)
                st.session_state["selected_player"] = pid
                st.session_state.pop("replacement", None)
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
    if outgoing in planner.week(gw)["vacancies"] and st.button("Undo sale", key="undo-sale"):
        edit(planner, store, lambda: planner.undo_sale(gw, outgoing))
    if st.button("Close replacement search", key="close-search"):
        close_inspection()
        st.rerun()


def details_panel(planner: Planner, store: PlanStore, paths: PlannerPaths, gw: int) -> None:
    if st.session_state.get("replacement") is not None:
        replacement_panel(planner, store, gw, st.session_state["replacement"])
        return
    pid = st.session_state.get("selected_player")
    player = planner.players.get(int(pid)) if pid is not None else None
    if player is None:
        st.subheader("Player details")
        st.info("Click a Player to inspect stats and projections, or a vacant bench slot to add a replacement.")
        return
    pid = int(player["id"])
    st.subheader(player.get("full_name") or player["name"])
    st.caption(f"{player.get('team_full') or player.get('team', '')} · {POSITION_NAMES[player['pos_id']]}")
    projection = player.get("projections", {}).get(f"gw{gw}", {})
    columns = st.columns(2)
    columns[0].metric(f"GW{gw} projected points", f"{projection['total_xp']:.2f}" if projection.get("total_xp") is not None else "Unavailable")
    columns[1].metric("Expected minutes", f"{projection['xmins']:.0f}" if projection.get("xmins") is not None else "Unavailable")
    st.write(f"Purchase Price: £{player['price']:.1f}m")
    if player.get("selling_price") is not None and pid in planner.state["base_ids"]:
        st.write(f"Selling Price: £{player['selling_price']:.1f}m")
    st.write(f"Availability: {player.get('status', 'unavailable')}" + (f" · {player['chance']}%" if player.get("chance") is not None else ""))
    if player.get("news"):
        st.write(player["news"])
    owned = pid in planner.week(gw)["squad_ids"]
    if owned:
        if st.button(f"Sell from GW{gw}", key="sell-player"):
            st.session_state.pop("selected_player", None)
            edit(planner, store, lambda: planner.sell(gw, pid))
        benched = pid in planner.state["overrides"].get(str(gw), {}).get("bench", [])
        if st.button("Clear bench override" if benched else "Bench this week", key="bench-player"):
            edit(planner, store, lambda: planner.override(gw, "bench", pid))
        if st.button("Replace Player", key="replace-player"):
            st.session_state["replacement"] = pid
            st.rerun()
        for label, kind in (("Set captain", "captain"), ("Set vice-captain", "vice")):
            if st.button(label, key=f"set-{kind}"):
                edit(planner, store, lambda kind=kind: planner.override(gw, kind, pid))
        if st.button("Clear captain and vice overrides", key="clear-captains"):
            planner.override(gw, "captain", None)
            edit(planner, store, lambda: planner.override(gw, "vice", None))
    st.write("Upcoming projections")
    rows = [{"GW": week_id, "Fixture": cell.get("fixture_label") or "Unavailable / blank",
             "xP": cell.get("total_xp"), "xMins": cell.get("xmins")}
            for week_id in range(gw, planner.state["end"] + 1)
            for cell in [player.get("projections", {}).get(f"gw{week_id}", {})]]
    st.dataframe(rows, hide_index=True, width="stretch")
    with st.expander("Recent points and minutes"):
        history = player_history(paths, pid)
        if history:
            st.dataframe(history, hide_index=True, width="stretch")
        else:
            st.caption("Recent match history unavailable.")
    with st.expander("Projection components"):
        components = {key.removeprefix("xp_").replace("_", " "): value for key, value in projection.items() if key.startswith("xp_")}
        if components:
            st.dataframe([{"Component": key, "xP": value} for key, value in components.items()], hide_index=True)
        else:
            st.caption("Projection components unavailable for this model.")


def close_inspection() -> None:
    st.session_state.pop("selected_player", None)
    st.session_state.pop("replacement", None)


@st.dialog("Player inspection", width="large", on_dismiss=close_inspection)
def player_inspection(planner: Planner, store: PlanStore, paths: PlannerPaths, gw: int) -> None:
    with st.container(key="player-inspection"):
        if st.button("Back to squad", key="close-details"):
            close_inspection()
            st.rerun()
        details_panel(planner, store, paths, gw)


def load_planner(paths: PlannerPaths, store: PlanStore) -> Planner:
    try:
        dataset = load_dataset(paths)
        previous = st.session_state.get("planner")
        saved = store.load() if previous is None else None
        if previous is None:
            st.session_state["draft_digest"] = digest(saved)
        planner = Planner(dataset, previous.state if previous else saved)
        if import_cached_recommendations(planner, paths):
            save(planner, store)
        st.session_state["planner"] = planner
        return planner
    except (ValueError, OSError) as exc:
        st.error(f"Cannot open saved plan/projections: {exc}")
        st.stop()
        raise


def main(paths: PlannerPaths, store: PlanStore, jobs: PlannerJobs) -> None:
    planner = st.session_state["planner"]
    dataset = planner.dataset
    busy = jobs.active() is not None
    with st.container(key="planner-heading", horizontal=True, vertical_alignment="center"):
        with st.container():
            st.title("Transfer Planner")
            st.caption("Inspect Players, plan transfers, and select a legal XI.")
        if st.button("Refresh", key="refresh-data", disabled=busy):
            begin_job(planner, store, jobs, paths, refresh=True)
    if st.session_state.get("save_error"):
        st.error(st.session_state["save_error"])
        if st.session_state.get("stale_browser") and st.button("Reload latest draft", key="reload-draft"):
            st.session_state.pop("planner", None)
            st.session_state.pop("stale_browser", None)
            st.session_state.pop("save_error", None)
            st.rerun()
        if not st.session_state.get("stale_browser") and st.button("Retry saving draft", key="retry-save"):
            save(planner, store)
            st.rerun()
    if st.session_state.get("job_notice"):
        st.info(st.session_state["job_notice"])
    for arm, error in st.session_state.get("arm_errors", {}).items():
        st.warning(f"{ARM_NAMES[arm]} unavailable: {error}")
    if planner.state.get("unapplied_result"):
        with st.expander("Solver results retained from an earlier draft"):
            st.caption("Computed for different draft/data. Current edits preserved; regenerate to apply current choices.")
            st.download_button("Download retained solver results", data=json.dumps(planner.state["unapplied_result"], indent=2),
                               file_name="retained-solver-results.json", mime="application/json", key="download-retained")
    if not planner.players or len(planner.state["base_ids"]) != 15:
        st.info("Refresh to load projections and your User Squad. FPL_EMAIL and FPL_PASSWORD must be configured for squad ingestion.")
        st.stop()
    if planner.stale:
        st.warning("Saved draft uses older data. Review it, or start from refreshed User Squad before solving.")
        if st.button("Use refreshed User Squad", key="new-plan"):
            st.session_state["new_plan_confirmation"] = True
            st.rerun()
    if st.session_state.get("new_plan_confirmation"):
        with st.container(border=True):
            confirm_new_plan(dataset, store)
    controls = st.columns([1, 1, 2])
    controls[0].write(f"Start: GW{planner.state['start']} · upcoming deadline")
    end = controls[1].number_input("Horizon end", min_value=planner.state["start"], max_value=min(planner.state["start"] + 9, 38),
                                    value=planner.state["end"], step=1, key="horizon-end")
    if end != planner.state["end"]:
        edit(planner, store, lambda: planner.change_horizon(planner.state["start"], end))
    scenario = controls[2].selectbox("Scenario policy", list(ARM_NAMES), index=list(ARM_NAMES).index(planner.state["scenario"]),
                                    format_func=lambda arm: ARM_NAMES[arm], key="scenario-policy")
    if scenario != planner.state["scenario"] and controls[2].button("Use selected scenario", key="switch-scenario"):
        if planner.state["edits"] or planner.state["overrides"]:
            st.session_state["reset_scenario"] = scenario
            st.rerun()
        else:
            edit(planner, store, lambda: planner.reset(scenario))
    gws = list(range(planner.state["start"], planner.state["end"] + 1))
    selected = planner.state.get("selected_gw", gws[0])
    gw = st.selectbox("Gameweek", gws, index=gws.index(selected) if selected in gws else 0,
                      format_func=lambda value: f"GW{value}", key=f"gameweek-{planner.state['start']}-{planner.state['end']}-{selected}")
    if gw != planner.state.get("selected_gw"):
        planner.state["selected_gw"] = gw
        save(planner, store)
    week = planner.week(gw)
    label = "Needs recalculation" if week["needs_recalculation"] else "Draft" if planner.state["edits"] or planner.state["overrides"] else "Solver recommendation" if week["has_recommendation"] else "Unsolved hold draft"
    st.write(f"**{ARM_NAMES[planner.state['scenario']]} · GW{gw} · {label}**")
    active_result = planner.state["recommendations"].get(planner.state["scenario"], {})
    stop_note = active_result.get("plan", {}).get("meta", {}).get("solver_objective_note")
    if stop_note:
        st.caption(stop_note)
    for conflict in dict.fromkeys(week["conflicts"]):
        st.warning(conflict)
    actions = st.columns(3)
    if actions[0].button("Generate plan", key="generate-plan", type="primary", disabled=busy or planner.stale or not all(row["complete"] for row in planner.weeks())):
        begin_job(planner, store, jobs, paths)
    if actions[1].button("Optimize remaining transfers", key="optimize-plan", disabled=busy or planner.stale or not all(row["complete"] for row in planner.weeks())):
        begin_job(planner, store, jobs, paths)
    if actions[2].button("Reset to solver", key="reset-plan", disabled=not planner.recommendation_valid()):
        st.session_state["reset_scenario"] = planner.state["scenario"]
        st.rerun()
    if "reset_scenario" in st.session_state:
        with st.container(border=True):
            confirm_reset(planner, store)
    with st.container(key="workspace"):
        with st.container(key="squad-board"):
            pitch(planner, gw, week)
            st.subheader("Transfers")
            if not week["transfers"]:
                st.caption("No transfers planned for selected Gameweek.")
            for move in week["transfers"]:
                outgoing = planner.players.get(move["out"], {}).get("name", f"Player {move['out']}")
                incoming = planner.players.get(move["in"], {}).get("name", "Replacement pending")
                st.write(f"Sell {outgoing} · Add {incoming}")
            st.write(f"{'Provisional bank' if week['vacancies'] else 'Bank'}: £{week['bank']:.1f}m · Free Transfers: {week['ft']} · Hits: {week['hits']} (−{week['hits'] * 4} points)")
            st.write(f"Projected lineup points after Hits: {week['projected_points']:.2f}")
            if week["complete"]:
                st.caption(f"Expected GW Score, including appearance uncertainty: {planner.expected_score(gw):.2f}")
            chips = [row["chip"] for row in dataset.get("meta", {}).get("transfer_plan_available_chips", []) if gw in row["gws"]]
            options = [None, *dict.fromkeys(chips)]
            chip = st.selectbox("Booked chip", options, index=options.index(week["chip"]) if week["chip"] in options else 0,
                                format_func=lambda value: {None: "None", "wc": "Wildcard", "bb": "Bench Boost", "fh": "Free Hit", "tc": "Triple Captain"}[value], key=f"chip-{gw}-{week['chip']}")
            if chip != week["chip"]:
                edit(planner, store, lambda: planner.set_chip(gw, chip))
    if st.session_state.get("selected_player") is not None or st.session_state.get("replacement") is not None:
        player_inspection(planner, store, paths, gw)

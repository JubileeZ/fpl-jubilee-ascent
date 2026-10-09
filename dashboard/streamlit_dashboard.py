"""One Streamlit dashboard: Transfer Planner, Explorer, Research, Methodology."""

from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.content import get_model_methodology, get_research_topic_detail, get_research_topics
from dashboard.dashboard_jobs import run_tool, strategy_errors
from dashboard.explorer import ExplorerSquad, compare_squads, player_slice, projections
from dashboard.planner import POSITION_NAMES, PlanStore, digest
from dashboard.planner_jobs import PlannerJobs
from dashboard.planner_service import PlannerPaths, PROJECT_ROOT, source_digest
from dashboard import streamlit_planner
from models import get_default_model_name
from projections.explorer_slice import COMPONENT_KEYS
from dashboard.presentation import availability, fixture

PAGES = ("Transfer Planner", "Explorer", "Research", "Model Methodology")


def start_tool(request: dict[str, Any], paths: PlannerPaths, jobs: PlannerJobs) -> None:
    try:
        request["source_digest"] = source_digest(paths)
        job_id = jobs.start(request, lambda payload: run_tool(payload, paths))
        st.session_state["tool_job"] = job_id
        st.rerun()
    except (OSError, ValueError) as exc:
        st.error(str(exc))


@st.fragment(run_every=2)
def shared_job_status(paths: PlannerPaths, jobs: PlannerJobs) -> None:
    try:
        active = jobs.active()
        if active:
            kind = active["request"]["kind"].replace("_", " ")
            st.info(f"{kind.capitalize()} running. You can keep exploring and editing while it finishes.")
            if active["request"]["kind"] in ("dream_team", "strategy"):
                st.session_state["tool_job"] = active["id"]
        job_id = st.session_state.get("tool_job")
        if job_id:
            job = jobs.status(job_id)
            if job["status"] != "running" and st.session_state.get("tool_handled") != job_id:
                st.session_state["tool_handled"] = job_id
                st.rerun()
    except (ValueError, OSError) as exc:
        st.error(str(exc))


def tool_result(kind: str, paths: PlannerPaths, jobs: PlannerJobs) -> dict[str, Any] | None:
    job = jobs.latest(kind)
    if job is None or job["status"] == "running":
        return None
    if job["status"] != "finished":
        st.error(job.get("error") or "Job interrupted. Retry when ready.")
        job = jobs.latest(kind, status="finished")
        if job is None:
            return None
        st.caption("Showing last completed result.")
    if job["result"]["stale"] or job["request"]["source_digest"] != source_digest(paths):
        st.warning("Result uses older inputs. Retained for inspection; solve again for current data.")
    st.download_button("Download result", json.dumps(job, indent=2), f"{kind}-result.json", "application/json", key=f"download-{kind}")
    return job


def explorer_details(player: dict[str, Any], model: str, gws: tuple[int, ...], paths: PlannerPaths) -> None:
    st.subheader(player.get("full_name") or player["name"])
    st.caption(f"{player.get('team_full', player.get('team', ''))} · {POSITION_NAMES[player['pos_id']]} · £{player['price']:.1f}m")
    st.write(availability(player))
    if player.get("news"):
        st.write(player["news"])
    rows = [{"GW": gw, "Fixture": fixture(cell), "Adjusted difficulty": cell.get("difficulty"), "xP": cell.get("total_xp"),
             "xMins": cell.get("xmins"), "Projection": "Unavailable" if cell.get("total_xp") is None else "Available"}
            for gw in gws for cell in [projections(player, model).get(f"gw{gw}", {})]]
    st.dataframe(rows, hide_index=True, width="stretch")
    st.caption("Adjusted difficulty: official 1–5, home −0.25 / away +0.25; lower is easier. Double Gameweeks show mean difficulty.")
    with st.expander("Projection components"):
        st.dataframe([{"GW": gw, **{key.removeprefix("xp_").replace("_", " ").capitalize(): projections(player, model).get(f"gw{gw}", {}).get(key) for key in COMPONENT_KEYS}} for gw in gws], hide_index=True, width="stretch")
        st.caption("Empty cells indicate unavailable components.")
    with st.expander("Season stats and recent history"):
        stats = {key: player.get(key) for key in ("total_points", "minutes", "starts", "pts_per_start", "pts_per_90", "xg_per_90", "xa_per_90", "ict_per_90", "inf_per_90", "cre_per_90", "thr_per_90")}
        st.dataframe([{"Stat": key.replace("_", " "), "Value": str(value) if value is not None else "Unavailable"} for key, value in stats.items()], hide_index=True)
        history = streamlit_planner.player_history(paths, int(player["id"]))
        if history:
            st.dataframe(history, hide_index=True)
    shortlist = st.session_state.get("scout-shortlist", [])
    if st.button("Add to comparison", key="scout-add", disabled=player["id"] in shortlist or len(shortlist) >= 2):
        st.session_state["scout-shortlist"] = [*shortlist, player["id"]]
        st.session_state.pop("scout-compare", None)
        st.rerun()
    st.button("Prepare in Transfer Planner", key="scout-prepare-details", on_click=prepare_transfer, args=(int(player["id"]),))


def prepare_transfer(incoming: int) -> None:
    st.session_state["scout-transfer"] = incoming
    st.session_state["dashboard-page"] = "Transfer Planner"
    close_explorer_inspection()


def scouting_comparison(dataset: dict[str, Any], model: str, gws: tuple[int, ...]) -> None:
    players = {int(player["id"]): player for player in dataset["players"]}
    labels = {pid: f"{player['name']} · {player.get('team') or 'Club unavailable'}" for pid, player in players.items()}
    repeated = {label for label, count in Counter(labels.values()).items() if count > 1}
    labels = {pid: f"{label} · Player {pid}" if label in repeated else label for pid, label in labels.items()}
    st.subheader("Player comparison")
    st.caption(f"{model} · GW{gws[0]}–{gws[-1]}. Select up to two Players; missing projections remain unavailable.")
    ids = st.multiselect("Compare Players", list(players), default=[pid for pid in st.session_state.get("scout-shortlist", []) if pid in players],
                        format_func=lambda pid: labels[pid], max_selections=2, key="scout-compare")
    st.session_state["scout-shortlist"] = ids
    if not ids:
        return
    st.dataframe([{**{key: value for key, value in player_slice(players[pid], model, gws).items() if key in ("Player", "Club", "Position", "Price", "xP", "xP / GW", "xMins / GW", "Projection")},
                   "Availability": availability(players[pid]), "News": players[pid].get("news") or "None supplied"} for pid in ids], hide_index=True, width="stretch")
    st.dataframe([{"GW": gw, **{labels[pid]: f"{fixture(cell)} · xP {cell['total_xp'] if cell.get('total_xp') is not None else 'Unavailable'}"
                                for pid in ids for cell in [projections(players[pid], model).get(f"gw{gw}", {})]}} for gw in gws], hide_index=True, width="stretch")
    incoming = st.selectbox("Player to prepare", ids, format_func=lambda pid: labels[pid], key="scout-incoming")
    st.button("Prepare in Transfer Planner", key="scout-prepare", on_click=prepare_transfer, args=(incoming,))


def close_explorer_inspection() -> None:
    st.session_state.pop("explorer-inspection", None)


@st.dialog("Player inspection", width="large", on_dismiss=close_explorer_inspection)
def explorer_inspection(player: dict[str, Any], model: str, gws: tuple[int, ...], paths: PlannerPaths) -> None:
    with st.container(key="player-inspection"):
        if st.button("Back to Explorer", key="close-explorer-details"):
            close_explorer_inspection()
            st.rerun()
        explorer_details(player, model, gws, paths)


def select_explorer_player(key: str, ids: list[int] | None = None) -> None:
    selection = st.session_state[key]["selection"]
    if ids is not None and selection["rows"]:
        st.session_state["explorer-player"] = ids[selection["rows"][-1]]
    elif ids is None and selection["points"]:
        st.session_state["explorer-player"] = int(selection["points"][-1]["customdata"][0])
    else:
        return
    st.session_state["explorer-inspection"] = True


@st.cache_data(show_spinner="Comparing projected squads…", max_entries=32)
def squad_comparison(dataset: dict[str, Any], model: str, gws: tuple[int, ...], squad: ExplorerSquad) -> list[dict[str, Any]]:
    return compare_squads(dataset, model, gws, squad)


def what_if(dataset: dict[str, Any], model: str, gws: tuple[int, ...]) -> None:
    players = {int(player["id"]): player for player in dataset["players"]}
    source = digest(dataset)
    if st.session_state.get("explorer-source") != source:
        st.session_state["explorer-squad"] = ExplorerSquad.from_dataset(dataset, model, gws)
        st.session_state["explorer-source"] = source
    squad: ExplorerSquad = st.session_state["explorer-squad"]
    st.subheader("Squad What-If")
    st.caption("Explore replacements and lineup choices here. Your saved Transfer Planner draft stays separate.")
    if len(squad.ids) != 15:
        st.info("Refresh to load your User Squad before exploring replacements.")
        return
    def name(pid: int) -> str:
        return players[pid]["name"]
    for warning in squad.warnings(players, float(dataset.get("meta", {}).get("itb", 0))):
        st.warning(warning)
    left, right = st.columns(2)
    outgoing = left.selectbox("Replace Player", squad.ids, format_func=name, key="whatif-out")
    candidates = [pid for pid in players if pid not in squad.ids and players[pid]["pos_id"] == players[outgoing]["pos_id"]]
    candidates.sort(key=lambda pid: -(player_slice(players[pid], model, gws)["xP"] or 0))
    if st.session_state.get("whatif-in") not in candidates:
        st.session_state.pop("whatif-in", None)
    incoming = right.selectbox("With Player", candidates, format_func=name, key="whatif-in") if candidates else None
    if st.button("Replace in What-If", key="whatif-replace", disabled=incoming is None):
        try:
            if incoming is not None:
                squad.replace(outgoing, incoming, players)
            for key in ("whatif-out", "whatif-in", "whatif-in-out", "whatif-starter", "whatif-bench"):
                st.session_state.pop(key, None)
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
    bench = squad.bench_order
    first, second = st.columns(2)
    starter = first.selectbox("Starter to bench", squad.lineup, format_func=name, key="whatif-starter")
    substitute = second.selectbox("Substitute to start", bench, format_func=name, key="whatif-bench")
    if st.button("Swap starting places", key="whatif-swap"):
        try:
            squad.swap(starter, substitute, players)
            st.session_state.pop("whatif-starter", None)
            st.session_state.pop("whatif-bench", None)
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))
    captain, vice = st.columns(2)
    captain_ids = [None, *squad.lineup]
    squad.captain = captain.selectbox("What-If captain", captain_ids, index=captain_ids.index(squad.captain), format_func=lambda pid: name(pid) if pid else "Automatic each Gameweek", key=f"whatif-captain-{digest(squad.lineup)}")
    vice_ids = [None, *(pid for pid in squad.lineup if pid != squad.captain)]
    squad.vice = vice.selectbox("What-If vice-captain", vice_ids, index=vice_ids.index(squad.vice) if squad.vice in vice_ids else 0, format_func=lambda pid: name(pid) if pid else "Automatic each Gameweek", key=f"whatif-vice-{squad.captain}-{digest(squad.lineup)}")
    for key, title, ids in (("explorer-pitch", "Starting XI", squad.lineup), ("explorer-bench", "Bench", bench)):
        with st.container(key=key):
            st.subheader(title)
            for pos in POSITION_NAMES:
                group = [pid for pid in ids if players[pid]["pos_id"] == pos]
                if not group:
                    continue
                st.caption(POSITION_NAMES[pos])
                for column, pid in zip(st.columns(len(group)), group, strict=True):
                    with column:
                        cell = projections(players[pid], model).get(f"gw{gws[0]}", {})
                        label = f"{float(cell['total_xp']):.1f} xP" if cell.get("total_xp") is not None else "Projection unavailable"
                        if st.button(f"{name(pid)} · {label}", key=f"explorer-squad-{pid}", width="stretch"):
                            st.session_state["explorer-player"] = pid
                            st.session_state["explorer-inspection"] = True
                            st.rerun()
                        st.caption(f"{players[pid].get('team', '')} · {POSITION_NAMES[pos]}")
    outfield = [pid for pid in bench if players[pid]["pos_id"] != 1]
    if len(outfield) == 3:
        order = st.selectbox("First substitute", outfield, format_func=name, key=f"whatif-bench-order-{digest(bench)}")
        if st.button("Move to first bench place", key="whatif-order"):
            squad.bench_order = [*(pid for pid in bench if players[pid]["pos_id"] == 1), order, *(pid for pid in outfield if pid != order)]
            st.rerun()
    transfers = len(set(squad.ids) - set(squad.baseline))
    hits = max(0, transfers - int(dataset.get("meta", {}).get("free_transfers", 1)))
    st.write(f"What-If bank: £{squad.bank(players, float(dataset.get('meta', {}).get('itb', 0))):.1f}m · Transfers: {transfers} · Hits: {hits} (−{hits * 4} points)")
    if st.button("Reset What-If to User Squad", key="whatif-reset"):
        st.session_state["explorer-squad"] = ExplorerSquad.from_dataset(dataset, model, gws)
        for key in list(st.session_state):
            if str(key).startswith("whatif-"):
                st.session_state.pop(key, None)
        st.rerun()
    scores = squad_comparison(dataset, model, gws, squad)
    st.dataframe(scores, hide_index=True, width="stretch")
    with st.expander("Squad fixtures and projection components"):
        st.dataframe([{"Player": name(pid), "Role": "Starter" if pid in squad.lineup else "Bench", **{f"GW{gw}": projections(players[pid], model).get(f"gw{gw}", {}).get("fixture_label", "Unavailable") for gw in gws}} for pid in squad.ids], hide_index=True)
        st.dataframe([player_slice(players[pid], model, gws) for pid in squad.ids], hide_index=True)


def explorer(paths: PlannerPaths, jobs: PlannerJobs) -> None:
    dataset = st.session_state["planner"].dataset
    meta = dataset.get("meta", {})
    st.title("Explorer")
    st.caption("Compare Players, inspect projections, and explore your squad.")
    if not dataset["players"]:
        st.info("Refresh in Transfer Planner to load projections.")
        return
    controls = st.columns(3)
    models = meta.get("models") or [meta.get("default_model") or get_default_model_name()]
    model = controls[0].selectbox("Projection model", models, key="explorer-model")
    starts = meta.get("unfinished_gameweeks") or meta.get("gw_ids") or [int(meta.get("transfer_plan_start", 1))]
    start = controls[1].selectbox("Horizon start", starts, format_func=lambda gw: f"GW{gw}", key="explorer-start")
    end = controls[2].selectbox("Horizon end", list(range(start, min(start + 9, 38) + 1)), index=min(5, 38 - start), format_func=lambda gw: f"GW{gw}", key=f"explorer-end-{start}")
    gws = tuple(range(start, end + 1))
    trust = meta.get("champion_trust", {})
    if trust:
        with st.expander("Model provenance"):
            st.json(trust)
    with st.expander("Filters", expanded=True):
        positions, clubs, search = st.columns(3)
        selected_positions = positions.multiselect("Positions", list(POSITION_NAMES), default=list(POSITION_NAMES), format_func=lambda pos: POSITION_NAMES[pos], key="explorer-positions")
        selected_clubs = clubs.multiselect("Clubs", sorted({player.get("team", "Unavailable") for player in dataset["players"]}), key="explorer-clubs")
        query = search.text_input("Find Player", key="explorer-search")
        prices, minutes, metrics = st.columns(3)
        maximum = max(float(player["price"]) for player in dataset["players"])
        price = prices.slider("Price range (£m)", 0.0, max(maximum, 1.0), (0.0, maximum), step=0.1, key="explorer-price")
        minimum_minutes = minutes.slider("Minimum xMins / GW", 0, 180, 0, key="explorer-minutes")
        metric = metrics.radio("Chart points", ("xP / GW", "xP / 90"), horizontal=True, key="explorer-metric")
        assume_ninety = st.checkbox("Assume 90 minutes per projected match (view only)", key="explorer-ninety")
    scouting_comparison(dataset, model, gws)
    owned = set(meta.get("owned_squad_ids", []))
    rows = []
    for player in dataset["players"]:
        row = player_slice(player, model, gws, assume_ninety)
        if player["pos_id"] not in selected_positions or (selected_clubs and row["Club"] not in selected_clubs):
            continue
        if not price[0] <= row["Price"] <= price[1] or (minimum_minutes > 0 and (row["xMins / GW"] is None or row["xMins / GW"] < minimum_minutes)) or query.casefold() not in f"{row['Player']} {row['Club']}".casefold():
            continue
        row["Squad"] = "User Squad" if player["id"] in owned else "Unowned"
        rows.append(row)
    job = jobs.latest("dream_team", status="finished")
    current_dream = bool(job and job["request"].get("model") == model and job["request"].get("start") == start and job["request"].get("horizon") == len(gws) and job["request"].get("source_digest") == source_digest(paths))
    dream_ids = set(job["result"]["payload"].get("player_ids", [])) if current_dream and job else set()
    for row in rows:
        row["Dream Team"] = row["ID"] in dream_ids
    if rows:
        frame = pd.DataFrame(rows).sort_values("xP", ascending=False).reset_index(drop=True)
        with st.container(key="explorer-charts"):
            charts = st.columns(2)
            for column, axis in zip(charts, ("Ownership %", "Price"), strict=True):
                with column:
                    figure = px.scatter(frame, x=axis, y=metric, color="Position", symbol="Squad", hover_name="Player", custom_data=["ID"], hover_data=["Club", "xP", "xMins / GW", "Dream Team"], color_discrete_sequence=["#0066cc", "#5856d6", "#146c43", "#9c3b00"])
                    figure.update_layout(template="plotly_white", margin=dict(l=20, r=20, t=25, b=20), font=dict(family="Segoe UI, sans-serif", color="#1d1d1f"))
                    st.plotly_chart(figure, width="stretch", key=f"chart-{axis}", on_select=lambda key=f"chart-{axis}": select_explorer_player(key), selection_mode="points")
        visible = frame.drop(columns=list(COMPONENT_KEYS))
        essential = ["Player", "Position", "Price", "xP", "xP / GW", "Club"]
        st.dataframe(visible, column_order=[*essential, *(name for name in visible.columns if name not in essential)], hide_index=True, width="stretch", on_select=lambda: select_explorer_player("explorer-table", frame["ID"].tolist()), selection_mode="single-row", key="explorer-table")
        st.download_button("Download filtered Players", visible.to_csv(index=False), "explorer-players.csv", "text/csv")
        pid = st.selectbox("Inspect Player", frame["ID"].tolist(), format_func=lambda pid: next(player["name"] for player in dataset["players"] if player["id"] == pid), index=frame["ID"].tolist().index(st.session_state["explorer-player"]) if st.session_state.get("explorer-player") in frame["ID"].tolist() else 0, key=f"explorer-inspect-{st.session_state.get('explorer-player')}")
        if st.button("View player details", key="explorer-view-details"):
            st.session_state["explorer-player"] = pid
            st.session_state["explorer-inspection"] = True
    else:
        st.info("No Players match these filters. Widen price, minutes, or search.")
    st.divider()
    if st.button("Solve Dream Team", key="dream-team", disabled=jobs.active() is not None):
        start_tool({"kind": "dream_team", "model": model, "start": start, "horizon": len(gws)}, paths, jobs)
    if job := tool_result("dream_team", paths, jobs):
        result = job["result"]["payload"]
        st.caption(f"Dream Team · {result.get('model')} · GW{result.get('horizon_start')} + {result.get('horizon')} weeks · budget £{result.get('budget')}m")
        st.write(", ".join(player["name"] for player in dataset["players"] if player["id"] in result.get("player_ids", [])))
    what_if(dataset, model, gws)
    if st.session_state.get("explorer-inspection"):
        player = next((player for player in dataset["players"] if player["id"] == st.session_state.get("explorer-player")), None)
        if player is not None:
            explorer_inspection(player, model, gws, paths)


def research() -> None:
    st.title("Research")
    st.caption("Research notes and their companion data.")
    query = st.text_input("Find research topic", key="research-search")
    topics = [topic for topic in get_research_topics() if query.casefold() in f"{topic['title']} {topic['slug']}".casefold()]
    if not topics:
        st.info("No matching research topics.")
        return
    by_slug = {str(topic["slug"]): topic for topic in topics}
    slug = st.selectbox("Topic", list(by_slug), format_func=lambda value: str(by_slug[value]["title"]), key="research-topic")
    detail = get_research_topic_detail(slug)
    st.caption(str(by_slug[slug]["title"]))
    st.caption(str(by_slug[slug]["status"]))
    st.download_button("Download note", str(detail["content"]), str(detail["filename"]), "text/markdown")
    st.markdown(str(detail["content"]))
    companions: Any = detail["companions"]
    if companions:
        st.subheader("Companion data")
        filename = str(st.selectbox("CSV file", list(companions), key=f"research-csv-{slug}"))
        companion = companions[filename]
        st.caption(f"Preview: first 100 of {companion['total_rows']} rows")
        st.dataframe(pd.DataFrame(companion["rows"], columns=companion["columns"]), hide_index=True, width="stretch")
        st.download_button("Download full CSV", (PROJECT_ROOT / "docs/research" / slug / filename).read_bytes(), filename, "text/csv")


def methodology() -> None:
    data: Any = get_model_methodology()
    st.title("Model Methodology")
    st.caption(f"Champion: {data['champion']}")
    for layer in data["pipeline_layers"]:
        with st.expander(f"{layer['layer']}. {layer['name']}", expanded=True):
            st.write(layer["summary"])
            st.code(layer["formula"], language=None, wrap_lines=True)
            st.write(layer["details"])
    ledger = data["candidate_ledger_summary"]
    st.subheader("Candidate policy")
    st.write(ledger["policy"])
    st.caption(f"Shipped levers: {ledger['shipped_count']} · Dead levers: {ledger['dead_count']}")
    st.write("Comparison Slate: " + ", ".join(ledger["slate"]))
    with st.expander("Draft a model research prompt"):
        category = st.selectbox("Lever category", ("Minutes & availability", "Rates & shrinkage", "Matchup & fixtures", "Scoring components"))
        hypothesis = st.text_area("Hypothesis")
        targets = st.text_input("Target Players or Positions")
        if hypothesis.strip():
            prompt = f"Explore a Candidate lever in {category}. Hypothesis: {hypothesis.strip()}. Targets: {targets.strip() or 'Playable Pool'}. Read Candidate Ledger first; respect Dead lever revisit_after. Audit point-in-time leakage, compare with Champion {data['champion']}, and use documented dev and confirmation gates. Do not promote without explicit user authorization."
            st.code(prompt, language=None, wrap_lines=True)
            st.download_button("Download research prompt", prompt, "model-research-prompt.txt", "text/plain")


def valid_strategy_settings(inputs: dict[str, Any]) -> bool:
    ranges = {"start": (1, 38), "horizon": (1, 10), "max_def": (1, 3), "hit_limit": (0, 30), "weekly_hit": (0, 15),
              "buffer": (0, 20), "decay": (0, 1), "ft_value": (0, 10), "itb_value": (0, 10), "bench_one": (0, 1), "bench_two": (0, 1)}
    for key, (low, high) in ranges.items():
        if key in inputs and (type(inputs[key]) not in (int, float) or not math.isfinite(inputs[key]) or not low <= inputs[key] <= high):
            return False
    if any(key in inputs and type(inputs[key]) is not int for key in ("start", "horizon", "max_def", "hit_limit", "weekly_hit")):
        return False
    if inputs.get("start", 1) + inputs.get("horizon", 1) > 39:
        return False
    if any(key in inputs and type(inputs[key]) is not bool for key in ("preseason", "double_def")):
        return False
    if "model" in inputs and not isinstance(inputs["model"], str):
        return False
    if inputs.get("opposing", "Allow") not in ("Allow", "Penalty", "Block"):
        return False
    for key in ("locked", "banned"):
        if not isinstance(inputs.get(key, []), list) or any(type(pid) is not int for pid in inputs.get(key, [])):
            return False
    bookings = inputs.get("bookings", {})
    return isinstance(bookings, dict) and all(gw is None or (type(gw) is int and 1 <= gw <= 38) for gw in bookings.values())


def advanced_solver(paths: PlannerPaths, jobs: PlannerJobs) -> None:
    with st.expander("Advanced strategy solve"):
        st.caption("Independent solver experiment. Its result stays separate from your saved transfer draft.")
        planner = st.session_state["planner"]
        settings_store = PlanStore(paths.storage / "strategy-settings.json")
        if "strategy-inputs" not in st.session_state:
            try:
                saved = settings_store.load()
                saved_digest = digest(saved)
                if saved is not None and not valid_strategy_settings(saved):
                    st.error("Saved strategy settings contain invalid values. Download a copy, then use defaults and review before saving a replacement.")
                    st.download_button("Download invalid saved settings", json.dumps(saved, indent=2), "strategy-settings-invalid.json", "application/json", key="strategy-invalid-download")
                    if not st.button("Use default advanced settings", key="strategy-defaults"):
                        return
                st.session_state["strategy-inputs"] = dict(saved or {})
                if saved is not None and not valid_strategy_settings(saved):
                    st.session_state["strategy-inputs"] = {}
                for key in ("buffer", "decay", "ft_value", "itb_value", "bench_one", "bench_two"):
                    if key in st.session_state["strategy-inputs"]:
                        st.session_state["strategy-inputs"][key] = float(st.session_state["strategy-inputs"][key])
                st.session_state["strategy-saved"] = saved
                st.session_state["strategy-settings-digest"] = saved_digest
            except (ValueError, OSError):
                st.error("Saved strategy settings unavailable. Preserve the settings file and restore a valid backup.")
                return
        inputs = st.session_state["strategy-inputs"]
        models = planner.dataset.get("meta", {}).get("models") or [get_default_model_name()]
        model = st.selectbox("Strategy model", models, index=models.index(inputs.get("model")) if inputs.get("model") in models else 0, key="strategy-model")
        columns = st.columns(3)
        start = columns[0].number_input("Strategy start GW", 1, 38, inputs.get("start", planner.state["start"]), key="strategy-start")
        horizon = columns[1].number_input("Strategy horizon", 1, min(10, 39 - start), min(inputs.get("horizon", 6), 39 - start), key=f"strategy-horizon-{start}", help="Inclusive number of Gameweeks, including the start. Start GW6 and horizon 3 means GW6–8.")
        st.caption(f"Strategy window: GW{start}–{start + horizon - 1} ({horizon} Gameweeks).")
        preseason = columns[2].checkbox("Preseason / blank squad", value=inputs.get("preseason", False), key="strategy-preseason")
        names = {int(player["id"]): player["name"] for player in planner.dataset["players"]}
        locked = st.multiselect("Locked Players", list(names), default=[pid for pid in inputs.get("locked", []) if pid in names], format_func=lambda pid: names[pid], key="strategy-locked")
        banned = st.multiselect("Banned Players", list(names), default=[pid for pid in inputs.get("banned", []) if pid in names], format_func=lambda pid: names[pid], key="strategy-banned")
        a, b, c = st.columns(3)
        max_def = a.number_input("Max defenders per Club", 1, 3, inputs.get("max_def", 3), key="strategy-max-def")
        double_def = b.checkbox("Force double defence (zero or at least two GKP/DEF starters per Club)", value=inputs.get("double_def", False), key="strategy-double-def")
        opposing = c.selectbox("Opposing starters", ("Allow", "Penalty", "Block"), index=("Allow", "Penalty", "Block").index(inputs.get("opposing", "Allow")), key="strategy-opposing", help="Allow accepts opposing starters; Penalty reduces their objective value; Block disallows the pairing.")
        a, b, c = st.columns(3)
        hit_limit = a.number_input("Total hit limit", 0, 30, inputs.get("hit_limit", 5), key="strategy-hit-limit", help="Number of paid transfers across the horizon; each costs four points. Zero disallows hits.")
        weekly_hit = b.number_input("Weekly hit limit", 0, 15, inputs.get("weekly_hit", 1), key="strategy-weekly-hit", help="Maximum paid transfers in each Gameweek, in addition to Free Transfers.")
        buffer = c.number_input("Bank buffer (£m)", 0.0, 20.0, inputs.get("buffer", 0.0), step=0.1, key="strategy-buffer", help="Minimum bank in Gameweeks with transfers, in £m. Hold weeks may carry less.")
        a, b, c = st.columns(3)
        decay = a.number_input("Gameweek decay", 0.0, 1.0, inputs.get("decay", 0.85), step=0.01, key="strategy-decay", help="Future-week objective multiplier. 0.85 weights consecutive weeks 1.00, 0.85, 0.72; 1.00 gives equal weight.")
        ft_value = b.number_input("Free Transfer value", 0.0, 10.0, inputs.get("ft_value", 1.5), step=0.1, key="strategy-ft-value", help="Objective points assigned to retaining a Free Transfer. This preference adds no official FPL points.")
        itb_value = c.number_input("Bank value", 0.0, 10.0, inputs.get("itb_value", 0.08), step=0.01, key="strategy-itb-value", help="Objective points per £1m retained in the bank. Adds no official FPL points.")
        a, b = st.columns(2)
        bench_one = a.number_input("First bench weight", 0.0, 1.0, inputs.get("bench_one", 0.21), step=0.01, key="strategy-bench-one", help="Objective fraction of first substitute projection: 0.21 counts 21%. Actual FPL scoring still follows autosub rules.")
        bench_two = b.number_input("Second bench weight", 0.0, 1.0, inputs.get("bench_two", 0.06), step=0.01, key="strategy-bench-two", help="Objective fraction of second substitute projection: 0.06 counts 6%.")
        chips = {}
        bookings = {}
        for column, (chip, label) in zip(st.columns(4), (("wc", "Wildcard"), ("fh", "Free Hit"), ("bb", "Bench Boost"), ("tc", "Triple Captain")), strict=True):
            choices = [None, *range(start, start + horizon)]
            previous = inputs.get("bookings", {}).get(chip)
            if previous is not None and previous not in choices:
                st.warning(f"{label} GW{previous} outside new horizon; booking cleared. Review before saving.")
            gw = column.selectbox(label, choices, index=choices.index(previous) if previous in choices else 0, format_func=lambda value: "Unbooked" if value is None else f"GW{value}", key=f"strategy-chip-{chip}-{start}-{horizon}")
            chips[f"use_{chip}"] = [gw] if gw is not None else []
            bookings[chip] = gw
        inputs = {"model": model, "start": start, "horizon": horizon, "preseason": preseason, "locked": locked, "banned": banned,
                  "max_def": max_def, "double_def": double_def, "opposing": opposing, "hit_limit": hit_limit, "weekly_hit": weekly_hit,
                  "buffer": buffer, "decay": decay, "ft_value": ft_value, "itb_value": itb_value, "bench_one": bench_one, "bench_two": bench_two, "bookings": bookings}
        st.session_state["strategy-inputs"] = inputs
        options = {"datasource": model, "horizon": horizon, "preseason": preseason, "locked": locked, "banned": banned,
                           "max_defenders_per_team": max_def, "double_defense_pick": double_def, "no_opposing_play": {"Allow": False, "Penalty": "penalty", "Block": True}[opposing],
                           "hit_limit": hit_limit, "weekly_hit_limit": weekly_hit, "transfer_itb_buffer": buffer, "decay_base": decay,
                           "ft_value": ft_value, "itb_value": itb_value, "bench_weights": {0: 0.03, 1: bench_one, 2: bench_two, 3: 0.002}, **chips}
        errors = strategy_errors(start, options, names)
        for error in errors:
            st.error(error)
        st.caption("Saved advanced settings restore after reload. Changes remain in this browser until you save them.")
        st.caption("Saved settings match current inputs." if inputs == st.session_state.get("strategy-saved") else "Unsaved changes.")
        if st.session_state.get("strategy-save-error"):
            st.error(st.session_state["strategy-save-error"])
        if st.button("Save advanced settings", key="strategy-save", disabled=bool(errors)):
            try:
                settings_store.save(inputs, expected_digest=st.session_state["strategy-settings-digest"])
                st.session_state["strategy-settings-digest"] = digest(inputs)
                st.session_state["strategy-saved"] = inputs
                st.session_state.pop("strategy-save-error", None)
                st.rerun()
            except (ValueError, OSError) as exc:
                st.session_state["strategy-save-error"] = f"Settings not saved: {exc} Reload latest saved settings or download current inputs before closing."
                st.rerun()
        if st.button("Reload saved advanced settings", key="strategy-reload"):
            for key in list(st.session_state):
                if str(key).startswith("strategy-"):
                    st.session_state.pop(key, None)
            st.rerun()
        st.download_button("Download advanced settings", json.dumps(inputs, indent=2), "strategy-settings.json", "application/json", key="strategy-download")
        if st.button("Run advanced solve", key="strategy-solve", disabled=jobs.active() is not None or bool(errors)):
            start_tool({"kind": "strategy", "start": start, "options": options}, paths, jobs)
        if job := tool_result("strategy", paths, jobs):
            result = job["result"]["payload"]
            def move_name(move: dict[str, Any]) -> str:
                return str(move.get("name") or names.get(int(move["id"]), str(move["id"])))
            for week in result.get("weeks", []):
                st.write(f"**GW{week['gw']}** · sell {', '.join(move_name(move) for move in week.get('sell', [])) or 'None'} · add {', '.join(move_name(move) for move in week.get('buy', [])) or 'None'}")
            with st.expander("Full strategy result"):
                st.json(result)


def main() -> None:
    st.set_page_config(page_title="FPL Jubilee Ascent", layout="wide", initial_sidebar_state="collapsed")
    st.html(Path(__file__).with_name("planner.css"))
    paths = PlannerPaths.configured()
    store, jobs = PlanStore(paths.storage / "draft.json"), PlannerJobs(paths.storage / "jobs")
    streamlit_planner.load_planner(paths, store)
    preferences = PlanStore(paths.storage / "preferences.json")
    if "dashboard-page" not in st.session_state:
        saved = preferences.load() or {}
        st.session_state["dashboard-page"] = saved.get("page") if saved.get("page") in PAGES else PAGES[0]
    with st.sidebar:
        st.header("FPL Jubilee Ascent")
        page = st.radio("Workspace", PAGES, key="dashboard-page")
        try:
            preferences.save({"page": page})
        except OSError:
            st.caption("Workspace choice not saved. Reload may open your previous workspace. Restore writable storage, then retry.")
            if st.button("Retry saving view", key="retry-view-save"):
                st.rerun()
        st.caption("One squad. One transfer plan.")
        backup = PROJECT_ROOT / "data/user_plans.json"
        if backup.exists():
            st.download_button("Download legacy plan backup", backup.read_bytes(), "user_plans.json", "application/json")
    with st.container(key="dashboard-content"):
        shared_job_status(paths, jobs)
        streamlit_planner.job_status(paths, store, jobs)
        if page == "Transfer Planner":
            streamlit_planner.main(paths, store, jobs)
        elif page == "Explorer":
            explorer(paths, jobs)
        elif page == "Research":
            research()
        else:
            methodology()
        if page in ("Transfer Planner", "Explorer"):
            advanced_solver(paths, jobs)

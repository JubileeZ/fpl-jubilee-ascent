"""One Streamlit dashboard: Transfer Planner, Explorer, Research, Methodology."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.content import get_model_methodology, get_research_topic_detail, get_research_topics
from dashboard.dashboard_jobs import run_tool
from dashboard.explorer import ExplorerSquad, player_slice, projections
from dashboard.planner import POSITION_NAMES, PlanStore, digest
from dashboard.planner_jobs import PlannerJobs
from dashboard.planner_service import PlannerPaths, PROJECT_ROOT, source_digest
from dashboard import streamlit_planner
from models import get_default_model_name
from projections.explorer_slice import COMPONENT_KEYS
from projections.expected_gw_score import expected_gw_score, player_gw_from_dashboard

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
    st.write(f"Availability: {player.get('status', 'Unavailable')}" + (f" · {player['chance']}%" if player.get("chance") is not None else ""))
    if player.get("news"):
        st.write(player["news"])
    rows = [{"GW": gw, "Fixture": cell.get("fixture_label", "Unavailable / blank"), "xP": cell.get("total_xp"),
             "xMins": cell.get("xmins"), **{key: cell.get(key) for key in COMPONENT_KEYS}}
            for gw in gws for cell in [projections(player, model).get(f"gw{gw}", {})]]
    st.dataframe(rows, hide_index=True, width="stretch")
    with st.expander("Season stats and recent history"):
        stats = {key: player.get(key) for key in ("total_points", "minutes", "starts", "pts_per_start", "pts_per_90", "xg_per_90", "xa_per_90", "ict_per_90", "inf_per_90", "cre_per_90", "thr_per_90")}
        st.dataframe([{"Stat": key.replace("_", " "), "Value": value} for key, value in stats.items()], hide_index=True)
        history = streamlit_planner.player_history(paths, int(player["id"]))
        if history:
            st.dataframe(history, hide_index=True)


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
    candidates.sort(key=lambda pid: -player_slice(players[pid], model, gws)["xP"])
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
                for column, pid in zip(st.columns(len(group)), group, strict=True):
                    with column:
                        cell = projections(players[pid], model).get(f"gw{gws[0]}", {})
                        if st.button(f"{name(pid)} · {float(cell.get('total_xp') or 0):.1f} xP", key=f"explorer-squad-{pid}", width="stretch"):
                            st.session_state["explorer-player"] = pid
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
    projected = {**dataset, "players": [{**player, "projections": projections(player, model)} for player in dataset["players"]]}
    lookup = player_gw_from_dashboard(projected)
    baseline = ExplorerSquad.from_dataset(dataset, model, gws)
    scores = []
    for gw in gws:
        values = {pid: value for (pid, week), value in lookup.items() if week == gw}
        def score(selected: ExplorerSquad) -> float:
            captain = selected.captain or max((pid for pid in selected.lineup if pid != selected.vice), key=lambda pid: float(projections(players[pid], model).get(f"gw{gw}", {}).get("total_xp") or 0))
            vice = selected.vice or max((pid for pid in selected.lineup if pid != captain), key=lambda pid: float(projections(players[pid], model).get(f"gw{gw}", {}).get("total_xp") or 0))
            return expected_gw_score(lineup_ids=selected.lineup, bench_ids=selected.bench_order, captain_id=captain, vice_id=vice, players=values, hits=hits if selected is squad else 0)
        base_score, new_score = score(baseline), score(squad)
        squad_xp = sum(float(projections(players[pid], model).get(f"gw{gw}", {}).get("total_xp") or 0) for pid in squad.ids)
        scores.append({"GW": gw, "Squad xP": round(squad_xp, 2), "User Squad Expected": base_score, "What-If Expected": new_score, "Difference": round(new_score - base_score, 2)})
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
    owned = set(meta.get("owned_squad_ids", []))
    rows = []
    for player in dataset["players"]:
        row = player_slice(player, model, gws, assume_ninety)
        if player["pos_id"] not in selected_positions or (selected_clubs and row["Club"] not in selected_clubs):
            continue
        if not price[0] <= row["Price"] <= price[1] or row["xMins / GW"] < minimum_minutes or query.casefold() not in f"{row['Player']} {row['Club']}".casefold():
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
        charts = st.columns(2)
        for column, axis in zip(charts, ("Ownership %", "Price"), strict=True):
            with column:
                figure = px.scatter(frame, x=axis, y=metric, color="Position", symbol="Squad", hover_name="Player", custom_data=["ID"], hover_data=["Club", "xP", "xMins / GW", "Dream Team"], color_discrete_sequence=["#0066cc", "#5856d6", "#146c43", "#9c3b00"])
                figure.update_layout(template="plotly_white", margin=dict(l=20, r=20, t=25, b=20), font=dict(family="Segoe UI, sans-serif", color="#1d1d1f"))
                event = st.plotly_chart(figure, width="stretch", key=f"chart-{axis}", on_select="rerun", selection_mode="points")
                if event.selection.points:
                    st.session_state["explorer-player"] = int(event.selection.points[-1]["customdata"][0])
        visible = frame.drop(columns=list(COMPONENT_KEYS))
        event = st.dataframe(visible, hide_index=True, width="stretch", on_select="rerun", selection_mode="single-row", key="explorer-table")
        if event.selection.rows:
            st.session_state["explorer-player"] = int(frame.iloc[event.selection.rows[0]]["ID"])
        st.download_button("Download filtered Players", visible.to_csv(index=False), "explorer-players.csv", "text/csv")
        pid = st.selectbox("Inspect Player", frame["ID"].tolist(), format_func=lambda pid: next(player["name"] for player in dataset["players"] if player["id"] == pid), index=frame["ID"].tolist().index(st.session_state["explorer-player"]) if st.session_state.get("explorer-player") in frame["ID"].tolist() else 0, key=f"explorer-inspect-{st.session_state.get('explorer-player')}")
        with st.container(key="explorer-details"):
            explorer_details(next(player for player in dataset["players"] if player["id"] == pid), model, gws, paths)
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
            st.code(layer["formula"], language=None)
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


def advanced_solver(paths: PlannerPaths, jobs: PlannerJobs) -> None:
    with st.expander("Advanced strategy solve"):
        st.caption("Independent solver experiment. Its result stays separate from your saved transfer draft.")
        planner = st.session_state["planner"]
        model = st.selectbox("Strategy model", planner.dataset.get("meta", {}).get("models") or [get_default_model_name()], key="strategy-model")
        columns = st.columns(3)
        start = columns[0].number_input("Strategy start GW", 1, 38, planner.state["start"], key="strategy-start")
        horizon = columns[1].number_input("Strategy horizon", 1, min(10, 39 - start), min(6, 39 - start), key=f"strategy-horizon-{start}")
        preseason = columns[2].checkbox("Preseason / blank squad", key="strategy-preseason")
        names = {int(player["id"]): player["name"] for player in planner.dataset["players"]}
        locked = st.multiselect("Locked Players", list(names), format_func=lambda pid: names[pid], key="strategy-locked")
        banned = st.multiselect("Banned Players", list(names), format_func=lambda pid: names[pid], key="strategy-banned")
        a, b, c = st.columns(3)
        max_def = a.number_input("Max defenders per Club", 1, 3, 3)
        double_def = b.checkbox("Allow double defence", value=True)
        opposing = c.selectbox("Opposing starters", ("Allow", "Penalty", "Block"))
        a, b, c = st.columns(3)
        hit_limit = a.number_input("Total hit limit", 0, 30, 5)
        weekly_hit = b.number_input("Weekly hit limit", 0, 15, 1)
        buffer = c.number_input("Bank buffer (£m)", 0.0, 20.0, 0.0, step=0.1)
        a, b, c = st.columns(3)
        decay = a.number_input("Gameweek decay", 0.0, 1.0, 0.85, step=0.01)
        ft_value = b.number_input("Free Transfer value", 0.0, 10.0, 1.5, step=0.1)
        itb_value = c.number_input("Bank value", 0.0, 10.0, 0.08, step=0.01)
        a, b = st.columns(2)
        bench_one = a.number_input("First bench weight", 0.0, 1.0, 0.21, step=0.01)
        bench_two = b.number_input("Second bench weight", 0.0, 1.0, 0.06, step=0.01)
        chips = {}
        for column, (chip, label) in zip(st.columns(4), (("wc", "Wildcard"), ("fh", "Free Hit"), ("bb", "Bench Boost"), ("tc", "Triple Captain")), strict=True):
            gw = column.selectbox(label, [None, *range(start, start + horizon)], format_func=lambda value: "Unbooked" if value is None else f"GW{value}", key=f"strategy-chip-{chip}-{start}-{horizon}")
            chips[f"use_{chip}"] = [gw] if gw is not None else []
        if st.button("Run advanced solve", key="strategy-solve", disabled=jobs.active() is not None):
            if set(locked) & set(banned):
                st.error("A Player cannot be both locked and banned.")
            else:
                options = {"datasource": model, "horizon": horizon, "preseason": preseason, "locked": locked, "banned": banned,
                           "max_defenders_per_team": max_def, "double_defense_pick": double_def, "no_opposing_play": {"Allow": False, "Penalty": "penalty", "Block": True}[opposing],
                           "hit_limit": hit_limit, "weekly_hit_limit": weekly_hit, "transfer_itb_buffer": buffer, "decay_base": decay,
                           "ft_value": ft_value, "itb_value": itb_value, "bench_weights": {0: 0.03, 1: bench_one, 2: bench_two, 3: 0.002}, **chips}
                start_tool({"kind": "strategy", "start": start, "options": options}, paths, jobs)
        if job := tool_result("strategy", paths, jobs):
            result = job["result"]["payload"]
            for week in result.get("weeks", []):
                st.write(f"**GW{week['gw']}** · sell {', '.join(names.get(pid, str(pid)) for pid in week.get('sell', [])) or 'None'} · add {', '.join(names.get(pid, str(pid)) for pid in week.get('buy', [])) or 'None'}")
            with st.expander("Full strategy result"):
                st.json(result)


def main() -> None:
    st.set_page_config(page_title="FPL Jubilee Ascent", layout="wide")
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
            st.caption("View preference could not be saved.")
        st.caption("One squad. One transfer plan.")
        backup = PROJECT_ROOT / "data/user_plans.json"
        if backup.exists():
            st.download_button("Download legacy plan backup", backup.read_bytes(), "user_plans.json", "application/json")
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

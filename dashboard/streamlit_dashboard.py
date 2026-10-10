"""One Streamlit dashboard: Transfer Planner, Explorer, Research, Methodology."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

import os

from dashboard.content import get_model_methodology, get_research_topic_detail, get_research_topics
from dashboard.dashboard_jobs import run_tool
from dashboard.explorer import player_slice, projections, watchlist_rows
from dashboard.planner import POSITION_NAMES, PlanStore
from dashboard.planner_jobs import PlannerJobs
from dashboard.planner_service import PlannerPaths, PROJECT_ROOT, load_dataset, player_history, source_digest
from models import get_default_model_name
from projections.explorer_slice import COMPONENT_KEYS
from dashboard.presentation import availability, fixture

PAGES = ("Explorer", "Research", "Model Methodology")


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
        history = player_history(paths, int(player["id"]))
        if history:
            st.dataframe(history, hide_index=True)
    shortlist = st.session_state.get("scout-shortlist", [])
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Add to comparison", key="scout-add", disabled=player["id"] in shortlist or len(shortlist) >= 2):
            st.session_state["scout-shortlist"] = [*shortlist, player["id"]]
            st.session_state.pop("scout-compare", None)
            st.rerun()
    with col_b:
        watchlist = st.session_state.setdefault("watchlist", [])
        in_wl = player["id"] in watchlist
        if st.button("Remove from Watchlist" if in_wl else "Add to Watchlist", key="details-toggle-watchlist"):
            if in_wl:
                watchlist.remove(player["id"])
            else:
                if len(watchlist) < 15:
                    watchlist.append(player["id"])
            st.session_state["watchlist"] = watchlist
            st.rerun()


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
    incoming = st.selectbox("Player for Watchlist", ids, format_func=lambda pid: labels[pid], key="scout-incoming")
    watchlist = st.session_state.setdefault("watchlist", [])
    in_wl = incoming in watchlist
    if st.button("Remove from Watchlist" if in_wl else "Add to Watchlist", key="scout-toggle-watchlist"):
        if in_wl:
            watchlist.remove(incoming)
        else:
            if len(watchlist) < 15:
                watchlist.append(incoming)
        st.session_state["watchlist"] = watchlist
        st.rerun()


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


def render_watchlist(dataset: dict[str, Any], model: str, gws: tuple[int, ...]) -> None:
    players = {int(p["id"]): p for p in dataset.get("players", [])}
    watchlist: list[int] = st.session_state.setdefault("watchlist", [])

    st.subheader("Player Watchlist")
    st.caption(f"Track and compare your transfer targets ({len(watchlist)}/15). Saved in your browser session.")

    left, right = st.columns([3, 1])
    available_to_add = [pid for pid in players if pid not in watchlist]
    available_to_add.sort(key=lambda pid: players[pid]["name"])
    with left:
        to_add = st.selectbox(
            "Add Player to Watchlist",
            [None, *available_to_add],
            format_func=lambda pid: "Select a player to add…" if pid is None else f"{players[pid]['name']} ({players[pid].get('team', '')}) · £{float(players[pid]['price']):.1f}m",
            key="watchlist-add-select",
        )
    with right:
        st.write("")
        st.write("")
        if st.button("Add to Watchlist", key="watchlist-add-btn", disabled=to_add is None or len(watchlist) >= 15):
            if to_add is not None and to_add not in watchlist:
                watchlist.append(to_add)
                st.session_state["watchlist"] = watchlist
                st.rerun()

    if not watchlist:
        st.info("Your watchlist is empty. Add players above, from comparison, or from player inspection.")
        return

    rows = watchlist_rows(dataset, model, gws, watchlist)
    if rows:
        df_wl = pd.DataFrame(rows)
        visible_wl = df_wl.drop(columns=["ID"])
        st.dataframe(visible_wl, hide_index=True, width="stretch")

        col1, col2 = st.columns([1, 1])
        with col1:
            st.download_button(
                "Download Watchlist CSV",
                visible_wl.to_csv(index=False),
                "fpl-watchlist.csv",
                "text/csv",
                key="download-watchlist",
            )
        with col2:
            if st.button("Clear Watchlist", key="clear-watchlist"):
                st.session_state["watchlist"] = []
                st.rerun()


def explorer(paths: PlannerPaths, jobs: PlannerJobs) -> None:
    dataset = st.session_state.get("dataset")
    if dataset is None:
        dataset = load_dataset(paths)
        st.session_state["dataset"] = dataset
    meta = dataset.get("meta", {})
    st.title("Explorer")
    st.caption("Compare Players, inspect projections, and build your watchlist.")
    if not dataset.get("players"):
        st.info("No projections found. Trigger a data refresh to load projections.")
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
        has_user_squad = bool(owned)
        with st.container(key="explorer-charts"):
            charts = st.columns(2)
            for column, axis in zip(charts, ("Ownership %", "Price"), strict=True):
                with column:
                    if has_user_squad:
                        figure = px.scatter(frame, x=axis, y=metric, color="Position", symbol="Squad", hover_name="Player", custom_data=["ID"], hover_data=["Club", "xP", "xMins / GW", "Dream Team"], color_discrete_sequence=["#0066cc", "#5856d6", "#146c43", "#9c3b00"])
                    else:
                        figure = px.scatter(frame, x=axis, y=metric, color="Position", hover_name="Player", custom_data=["ID"], hover_data=["Club", "xP", "xMins / GW", "Dream Team"], color_discrete_sequence=["#0066cc", "#5856d6", "#146c43", "#9c3b00"])
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
    render_watchlist(dataset, model, gws)
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


def _get_secret(key: str, default: str | None = None) -> str | None:
    try:
        if hasattr(st, "secrets") and key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    return os.environ.get(key, default)


def trigger_public_refresh(paths: PlannerPaths) -> tuple[bool, str]:
    try:
        import asyncio
        import base64
        import httpx
        from commands.refresh_data import main as refresh_main
        from commands.export_dashboard import run_dashboard_export

        asyncio.run(refresh_main([]))
        run_dashboard_export(output_path=paths.dataset, with_squad=False)
        msg = "Public data successfully refreshed."

        token = _get_secret("GITHUB_TOKEN")
        repo = _get_secret("GITHUB_REPOSITORY")

        if token and repo and paths.dataset.exists():
            content_bytes = paths.dataset.read_bytes()
            b64_content = base64.b64encode(content_bytes).decode("utf-8")
            url = f"https://api.github.com/repos/{repo}/contents/dashboard/dashboard_data.json"
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            }
            r_get = httpx.get(url, headers=headers, timeout=15.0)
            sha = r_get.json().get("sha") if r_get.status_code == 200 else None
            payload: dict[str, Any] = {
                "message": "chore(data): refresh public dashboard data",
                "content": b64_content,
            }
            if sha:
                payload["sha"] = sha
            r_put = httpx.put(url, headers=headers, json=payload, timeout=30.0)
            if r_put.status_code in (200, 201):
                msg += f" Persisted to GitHub ({repo})."
            else:
                msg += f" (GitHub commit failed: HTTP {r_put.status_code})"
        return True, msg
    except Exception as exc:
        return False, f"Refresh failed: {exc}"


def main() -> None:
    st.set_page_config(page_title="FPL Jubilee Ascent", layout="wide", initial_sidebar_state="collapsed")
    st.html(Path(__file__).with_name("planner.css"))
    paths = PlannerPaths.configured()
    jobs = PlannerJobs(paths.storage / "jobs")
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
            st.caption("Workspace choice not saved.")
        st.caption("Public FPL player & projection analytics.")

        with st.expander("Data Refresh"):
            configured_admin = _get_secret("ADMIN_KEY")
            admin_authorized = True
            if configured_admin:
                entered_key = st.text_input("Admin Key", type="password", key="admin-key-input")
                admin_authorized = entered_key == configured_admin
                if entered_key and not admin_authorized:
                    st.error("Incorrect Admin Key.")

            if admin_authorized:
                if st.button("Refresh Public Data", key="btn-refresh-public", disabled=jobs.active() is not None):
                    with st.spinner("Refreshing public FPL data..."):
                        ok, msg = trigger_public_refresh(paths)
                        if ok:
                            st.success(msg)
                            st.session_state["dataset"] = load_dataset(paths)
                            st.rerun()
                        else:
                            st.error(msg)
            else:
                st.caption("Enter Admin Key to enable public refresh.")

    with st.container(key="dashboard-content"):
        shared_job_status(paths, jobs)
        if page == "Explorer":
            explorer(paths, jobs)
        elif page == "Research":
            research()
        else:
            methodology()

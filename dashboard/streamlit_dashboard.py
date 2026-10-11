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
from models.scoring_matrix import Position, _CLEAN_SHEET_POINTS, _GOAL_POINTS
from projections.explorer_slice import COMPONENT_KEYS
from dashboard.presentation import availability, fixture

PAGES = ("Explorer", "Research", "Model Methodology")
POS_ID_TO_CODE: dict[int, Position] = {1: "GK", 2: "D", 3: "M", 4: "F"}


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


def format_rate_delta(pred: float | None, actual: float | None, baseline_label: str, fallback_label: str = "Model projection") -> str:
    if pred is not None and actual is not None and actual > 0.05:
        delta_pct = (pred - actual) / actual * 100.0
        return f"{delta_pct:+.0f}% vs season {baseline_label}"
    return fallback_label


def explorer_details(player: dict[str, Any], model: str, gws: tuple[int, ...], paths: PlannerPaths, dataset: dict[str, Any] | None = None) -> None:
    st.subheader(player.get("full_name") or player["name"])
    pos_name = POSITION_NAMES.get(player.get("pos_id"), player.get("pos", ""))
    price_val = float(player.get("price", 0.0))
    st.caption(f"{player.get('team_full', player.get('team', ''))} · {pos_name} · £{price_val:.1f}m")

    avail_text = availability(player)
    chance = player.get("chance")
    if chance is not None and int(chance) < 100:
        st.warning(f"⚠️ Availability: {avail_text} — {player.get('news') or 'Reported doubt'}")
    else:
        st.write(avail_text)
        if player.get("news"):
            st.write(player["news"])

    cells = [projections(player, model).get(f"gw{gw}", {}) for gw in gws]
    total_xp = sum(float(cell.get("total_xp") or 0) for cell in cells) if any(cell.get("total_xp") is not None for cell in cells) else None
    total_xmins = sum(float(cell.get("xmins") or 0) for cell in cells) if any(cell.get("xmins") is not None for cell in cells) else None
    avg_xmins = (total_xmins / len(gws)) if total_xmins is not None and len(gws) > 0 else None
    xp_per_m = (total_xp / price_val) if (total_xp is not None and price_val > 0) else None

    rank = None
    pos_total = None
    pos_avg_efficiency = None
    top_peer = None
    if dataset and "players" in dataset:
        pos_players = [p for p in dataset["players"] if p.get("pos_id") == player.get("pos_id")]
        pos_total = len(pos_players)

        def calculate_player_xp(target_player: dict[str, Any]) -> float:
            target_cells = [projections(target_player, model).get(f"gw{gw}", {}) for gw in gws]
            return sum(float(c.get("total_xp") or 0) for c in target_cells)

        sorted_pos = sorted(pos_players, key=calculate_player_xp, reverse=True)
        rank = next((i + 1 for i, p in enumerate(sorted_pos) if p["id"] == player["id"]), None)
        valid_eff = [calculate_player_xp(p) / float(p["price"]) for p in pos_players if float(p.get("price", 0)) > 0 and calculate_player_xp(p) > 0]
        if valid_eff:
            pos_avg_efficiency = sum(valid_eff) / len(valid_eff)

        bracket_peers = [p for p in sorted_pos if p["id"] != player["id"] and abs(float(p.get("price", 0)) - price_val) <= 0.6]
        if not bracket_peers:
            bracket_peers = [p for p in sorted_pos if p["id"] != player["id"] and abs(float(p.get("price", 0)) - price_val) <= 1.1]
        if not bracket_peers:
            bracket_peers = sorted([p for p in sorted_pos if p["id"] != player["id"]], key=lambda p: abs(float(p.get("price", 0)) - price_val))
        top_peer = bracket_peers[0] if bracket_peers else None

    st.markdown("#### Selection Verdict")
    col_xp, col_mins, col_value, col_rank = st.columns(4)
    with col_xp:
        st.metric(
            "Projected xP",
            f"{total_xp:.1f}" if total_xp is not None else "N/A",
            f"{total_xp / len(gws):.2f} / GW" if total_xp is not None and gws else None,
        )
    with col_mins:
        participation_pct = (avg_xmins / 90.0 * 100.0) if avg_xmins is not None else None
        st.metric(
            "xMins",
            f"{avg_xmins:.0f}m / GW" if avg_xmins is not None else "N/A",
            f"{participation_pct:.0f}% participation" if participation_pct is not None else None,
            delta_color="off",
        )
    with col_value:
        diff_str = f"vs {pos_avg_efficiency:.2f} avg" if pos_avg_efficiency is not None else None
        st.metric(
            "xP / £m",
            f"{xp_per_m:.2f}" if xp_per_m is not None else "N/A",
            diff_str,
            delta_color="normal" if pos_avg_efficiency is not None and xp_per_m is not None and xp_per_m >= pos_avg_efficiency else "inverse",
        )
    with col_rank:
        st.metric(
            "Position Rank",
            f"#{rank} of {pos_total}" if rank and pos_total else "—",
            f"{pos_name} by xP",
            delta_color="off",
        )

    verdict_badges = []
    if rank == 1:
        verdict_badges.append("🏆 #1 at Position")
    elif rank is not None and rank <= 3:
        verdict_badges.append(f"⭐ Top 3 {pos_name}")

    if pos_avg_efficiency is not None and xp_per_m is not None:
        if xp_per_m >= pos_avg_efficiency * 1.15:
            verdict_badges.append("💎 High Value Efficiency")
        elif xp_per_m < pos_avg_efficiency * 0.85:
            verdict_badges.append("⚠️ Low Value Efficiency")

    if avg_xmins is not None:
        if avg_xmins >= 75.0:
            verdict_badges.append("🟢 High Minutes Reliability")
        elif avg_xmins >= 50.0:
            verdict_badges.append("🟡 Moderate Minutes Reliability")
        else:
            verdict_badges.append("🔴 Low Minutes Reliability")

    chance = player.get("chance")
    if chance is not None and int(chance) < 100:
        verdict_badges.append(f"⚠️ Availability Risk ({chance}%)")

    if verdict_badges:
        st.caption(" · ".join(f"**{b}**" for b in verdict_badges))

    if top_peer:
        peer_xp = calculate_player_xp(top_peer)
        peer_name = top_peer.get("full_name") or top_peer["name"]
        peer_club = top_peer.get("team_full") or top_peer.get("team", "")
        peer_price = float(top_peer.get("price", 0))
        col_peer_text, col_peer_btn = st.columns([3, 2])
        with col_peer_text:
            st.caption(f"Top alternative at £{price_val:.1f}m: **{peer_name}** ({peer_club} · £{peer_price:.1f}m · {peer_xp:.1f} xP)")
        with col_peer_btn:
            if st.button(f"⚡ Compare with {top_peer['name']}", key="details-compare-peer"):
                st.session_state["scout-shortlist"] = [player["id"], top_peer["id"]]
                st.session_state.pop("scout-compare", None)
                close_explorer_inspection()
                st.rerun()


    st.markdown("#### Projected Point Components & Rate Reality Check")
    comp_sums = {
        "Appearance": sum(float(cell.get("xp_minutes") or 0) for cell in cells),
        "Goals": sum(float(cell.get("xp_goals") or 0) for cell in cells),
        "Assists": sum(float(cell.get("xp_assists") or 0) for cell in cells),
        "Clean Sheet": sum(float(cell.get("xp_clean_sheet") or 0) for cell in cells),
        "Bonus": sum(float(cell.get("xp_bonus") or 0) for cell in cells),
        "Def / Other": sum(float(cell.get("xp_saves") or 0) + float(cell.get("xp_defcon") or 0) + float(cell.get("xp_conceded") or 0) for cell in cells),
    }

    total_positive = sum(max(0.0, v) for v in comp_sums.values())
    bar_rows = []
    if total_positive > 0:
        for k, v in comp_sums.items():
            if v > 0.05:
                share_pct = round((v / total_positive) * 100.0, 1)
                bar_rows.append({"Component": k, "Points": round(v, 2), "Share %": share_pct})
    if bar_rows:
        df_comp = pd.DataFrame(bar_rows)
        fig_comp = px.bar(
            df_comp,
            x="Share %",
            y=["Point Distribution"] * len(df_comp),
            color="Component",
            orientation="h",
            height=130,
            hover_data={"Share %": ":.1f", "Points": ":.2f"},
            color_discrete_sequence=["#0066cc", "#5856d6", "#146c43", "#d97706", "#dc2626", "#475569"],
        )
        fig_comp.update_layout(
            template="plotly_white",
            margin=dict(l=10, r=10, t=10, b=10),
            yaxis=dict(visible=False),
            xaxis_title="Horizon Point Distribution (%)",
            xaxis=dict(ticksuffix="%"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            font=dict(family="Segoe UI, sans-serif"),
        )
        st.plotly_chart(fig_comp, width="stretch", config={"displayModeBar": False}, key="details-comp-bar")

    reality_rows = []
    pos_code: Position = POS_ID_TO_CODE.get(player.get("pos_id", 0), "M")
    goal_mult = float(_GOAL_POINTS.get(pos_code, 4))
    pred_xg_90 = (comp_sums["Goals"] / goal_mult) / (total_xmins / 90.0) if total_xmins and total_xmins > 0 else None
    actual_xg_90 = float(player.get("xg_per_90")) if player.get("xg_per_90") is not None else None
    if comp_sums["Goals"] > 0 or actual_xg_90 is not None:
        reality_rows.append({
            "Component": "Goals",
            "Projected Total": f"{comp_sums['Goals']:.2f} xP",
            "Projected Rate": f"{pred_xg_90:.2f} xG/90" if pred_xg_90 is not None else "—",
            "Season Actual Rate": f"{actual_xg_90:.2f} xG/90" if actual_xg_90 is not None else "—",
            "Reality Check": format_rate_delta(pred_xg_90, actual_xg_90, "xG"),
        })

    pred_xa_90 = (comp_sums["Assists"] / 3.0) / (total_xmins / 90.0) if total_xmins and total_xmins > 0 else None
    actual_xa_90 = float(player.get("xa_per_90")) if player.get("xa_per_90") is not None else None
    if comp_sums["Assists"] > 0 or actual_xa_90 is not None:
        reality_rows.append({
            "Component": "Assists",
            "Projected Total": f"{comp_sums['Assists']:.2f} xP",
            "Projected Rate": f"{pred_xa_90:.2f} xA/90" if pred_xa_90 is not None else "—",
            "Season Actual Rate": f"{actual_xa_90:.2f} xA/90" if actual_xa_90 is not None else "—",
            "Reality Check": format_rate_delta(pred_xa_90, actual_xa_90, "xA"),
        })

    cs_mult = float(_CLEAN_SHEET_POINTS.get(pos_code, 0))
    if cs_mult > 0 and (comp_sums["Clean Sheet"] > 0 or pos_code in ("GK", "D")):
        pred_cs_90 = (comp_sums["Clean Sheet"] / cs_mult) / (total_xmins / 90.0) if total_xmins and total_xmins > 0 else None
        actual_cs_90 = (float(player["clean_sheets"]) / (float(player["minutes"]) / 90.0)) if (player.get("clean_sheets") is not None and player.get("minutes") and float(player["minutes"]) > 0) else None
        reality_rows.append({
            "Component": "Clean Sheets",
            "Projected Total": f"{comp_sums['Clean Sheet']:.2f} xP",
            "Projected Rate": f"{pred_cs_90:.2f} CS/90" if pred_cs_90 is not None else "—",
            "Season Actual Rate": f"{actual_cs_90:.2f} CS/90" if actual_cs_90 is not None else "—",
            "Reality Check": format_rate_delta(pred_cs_90, actual_cs_90, "CS", fallback_label="Defensive matchup projection"),
        })

    finished_count = len((dataset.get("meta") or {}).get("finished_gameweeks", [])) if dataset else 0
    actual_mins_gw = (float(player.get("minutes", 0)) / finished_count) if finished_count > 0 else None
    season_mins_per_start = float(player.get("minutes", 0)) / max(1, int(player.get("starts", 0))) if player.get("starts") else None
    reality_rows.append({
        "Component": "Appearance",
        "Projected Total": f"{comp_sums['Appearance']:.2f} xP",
        "Projected Rate": f"{avg_xmins:.0f} mins / GW" if avg_xmins is not None else "—",
        "Season Actual Rate": f"{actual_mins_gw:.0f} mins / GW" if actual_mins_gw is not None else (f"{season_mins_per_start:.0f} mins / start" if season_mins_per_start else "—"),
        "Reality Check": format_rate_delta(avg_xmins, actual_mins_gw, "mins/GW") if actual_mins_gw is not None else (f"{participation_pct:.0f}% participation share" if participation_pct is not None else "—"),
    })

    if comp_sums["Bonus"] > 0:
        pred_bonus_90 = (comp_sums["Bonus"] / (total_xmins / 90.0)) if total_xmins and total_xmins > 0 else None
        actual_bonus_90 = (float(player["bonus"]) / (float(player["minutes"]) / 90.0)) if (player.get("bonus") is not None and player.get("minutes") and float(player["minutes"]) > 0) else None
        reality_rows.append({
            "Component": "Bonus",
            "Projected Total": f"{comp_sums['Bonus']:.2f} xP",
            "Projected Rate": f"{pred_bonus_90:.2f} bonus/90" if pred_bonus_90 is not None else "—",
            "Season Actual Rate": f"{actual_bonus_90:.2f} bonus/90" if actual_bonus_90 is not None else "—",
            "Reality Check": "BPS expected share",
        })

    if comp_sums["Def / Other"] > 0:
        reality_rows.append({
            "Component": "Def / Other",
            "Projected Total": f"{comp_sums['Def / Other']:.2f} xP",
            "Projected Rate": "—",
            "Season Actual Rate": "—",
            "Reality Check": "Saves & defensive contribution",
        })

    if total_xp is not None:
        pred_rate_90 = (total_xp / (total_xmins / 90.0)) if total_xmins and total_xmins > 0 else None
        actual_pts_90 = float(player.get("pts_per_90")) if player.get("pts_per_90") is not None else None
        reality_rows.append({
            "Component": "Total",
            "Projected Total": f"{total_xp:.2f} xP",
            "Projected Rate": f"{pred_rate_90:.2f} pts/90" if pred_rate_90 is not None else "—",
            "Season Actual Rate": f"{actual_pts_90:.2f} pts/90" if actual_pts_90 is not None else "—",
            "Reality Check": format_rate_delta(pred_rate_90, actual_pts_90, "pts/90", fallback_label="Overall expected point rate"),
        })

    st.dataframe(reality_rows, hide_index=True, width="stretch")


    st.markdown("#### Gameweek Fixtures & Projections")
    rows = [{"GW": gw, "Fixture": fixture(cell), "Adjusted difficulty": cell.get("difficulty"), "xP": cell.get("total_xp"),
             "xMins": cell.get("xmins"), "Projection": "Unavailable" if cell.get("total_xp") is None else "Available"}
            for gw in gws for cell in [projections(player, model).get(f"gw{gw}", {})]]
    st.dataframe(rows, hide_index=True, width="stretch")
    st.caption("Adjusted difficulty: official 1–5, home −0.25 / away +0.25; lower is easier. Double Gameweeks show mean difficulty.")

    with st.expander("Detailed component projections by Gameweek"):
        st.dataframe([{"GW": gw, **{key.removeprefix("xp_").replace("_", " ").capitalize(): projections(player, model).get(f"gw{gw}", {}).get(key) for key in COMPONENT_KEYS}} for gw in gws], hide_index=True, width="stretch")
        st.caption("Empty cells indicate unavailable components.")

    with st.expander("Season stats and recent history"):
        stats = {key: player.get(key) for key in ("total_points", "minutes", "starts", "pts_per_start", "pts_per_90", "xg_per_90", "xa_per_90", "ict_per_90", "inf_per_90", "cre_per_90", "thr_per_90")}
        st.dataframe([{"Stat": key.replace("_", " ").upper() if key in ("ict_per_90", "inf_per_90", "cre_per_90", "thr_per_90") else key.replace("_", " ").capitalize(),
                       "Value": str(value) if value is not None else "Unavailable"} for key, value in stats.items()], hide_index=True)
        raw_history = player_history(paths, int(player["id"]))
        if raw_history:
            recent_pts = [float(h.get("total_points") or 0) for h in raw_history]
            recent_mins = [float(h.get("minutes") or 0) for h in raw_history]
            if recent_pts:
                form_avg = sum(recent_pts) / len(recent_pts)
                form_mins = sum(recent_mins) / len(recent_mins)
                st.caption(f"Recent Form: **{form_avg:.1f} pts / GW** ({form_mins:.0f} mins avg across last {len(recent_pts)} fixtures)")
            history_rows = []
            for h in raw_history:
                row_fmt: dict[str, Any] = {"GW": h.get("gameweek_id"), "Pts": h.get("total_points"), "Mins": h.get("minutes")}
                if "pts_per_90" in h:
                    row_fmt["Pts/90"] = f"{float(h['pts_per_90']):.2f}"
                if "goals_scored" in h:
                    row_fmt["Goals"] = h.get("goals_scored")
                if "assists" in h:
                    row_fmt["Assists"] = h.get("assists")
                if "expected_goals" in h and h.get("expected_goals") is not None:
                    row_fmt["xG"] = f"{float(h['expected_goals']):.2f}"
                if "expected_assists" in h and h.get("expected_assists") is not None:
                    row_fmt["xA"] = f"{float(h['expected_assists']):.2f}"
                if "bonus" in h:
                    row_fmt["Bonus"] = h.get("bonus")
                history_rows.append(row_fmt)
            st.dataframe(history_rows, hide_index=True, width="stretch")

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
def explorer_inspection(player: dict[str, Any], model: str, gws: tuple[int, ...], paths: PlannerPaths, dataset: dict[str, Any] | None = None) -> None:
    with st.container(key="player-inspection"):
        if st.button("Back to Explorer", key="close-explorer-details"):
            close_explorer_inspection()
            st.rerun()
        explorer_details(player, model, gws, paths, dataset=dataset)



def select_explorer_player(key: str, ids: list[int] | None = None) -> None:
    selection = st.session_state[key]["selection"]
    if ids is not None and selection["rows"]:
        st.session_state["explorer-player"] = ids[selection["rows"][-1]]
    elif ids is None and selection["points"]:
        st.session_state["explorer-player"] = int(selection["points"][-1]["customdata"][0])
    else:
        return


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
    default_start = int(meta.get("transfer_plan_start") or meta.get("horizon_start") or starts[0])
    default_index = starts.index(default_start) if default_start in starts else 0
    start = controls[1].selectbox("Horizon start", starts, index=default_index, format_func=lambda gw: f"GW{gw}", key="explorer-start")
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
        scale_bubble = st.checkbox("Scale bubble size by xMins / GW", value=True, key="explorer-bubble-scale")
    scouting_comparison(dataset, model, gws)
    owned = set(meta.get("owned_squad_ids", []))
    rows = []
    for player in dataset["players"]:
        row = player_slice(player, model, gws)
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
        if scale_bubble:
            frame["Bubble Size"] = frame["xMins / GW"].apply(
                lambda val: max(15.0, min(float(val), 180.0)) if val is not None and float(val) > 0 else 15.0
            )
        has_user_squad = bool(owned)
        with st.container(key="explorer-charts"):
            charts = st.columns(2)
            for column, axis in zip(charts, ("Ownership %", "Price"), strict=True):
                with column:
                    size_col = "Bubble Size" if scale_bubble else None
                    hover_fields = {"Club": True, "xP": True, "xMins / GW": True, "Dream Team": True}
                    if scale_bubble:
                        hover_fields["Bubble Size"] = False
                    figure = px.scatter(
                        frame,
                        x=axis,
                        y=metric,
                        color="Position",
                        symbol="Squad" if has_user_squad else None,
                        size=size_col,
                        size_max=18 if scale_bubble else None,
                        hover_name="Player",
                        custom_data=["ID"],
                        hover_data=hover_fields,
                        color_discrete_sequence=["#0066cc", "#5856d6", "#146c43", "#9c3b00"],
                    )
                    figure.update_layout(
                        template="plotly_white",
                        margin=dict(l=20, r=20, t=25, b=20),
                        font=dict(family="Segoe UI, sans-serif", color="#1d1d1f"),
                    )
                    st.plotly_chart(
                        figure,
                        width="stretch",
                        key=f"chart-{axis}",
                        on_select=lambda key=f"chart-{axis}": select_explorer_player(key),
                        selection_mode="points",
                    )
            if scale_bubble:
                st.caption("Bubble size indicates expected minutes per Gameweek (xMins / GW). Larger bubbles represent higher projected minutes.")
        rename_map = {
            "xp_gi": "xP GI",
            "xp_goals": "xP Goals",
            "xp_assists": "xP Assists",
            "xp_clean_sheet": "xP CS",
            "xp_defcon": "xP DefCon",
            "xp_conceded": "xP Conceded",
            "xp_saves": "xP Saves",
            "xp_bonus": "xP Bonus",
        }
        for src, dst in rename_map.items():
            if src in frame.columns:
                frame[dst] = frame[src]
        table_view = st.segmented_control(
            "Table view",
            ["Overview", "Attacking", "Defensive", "All Components"],
            default="Overview",
            key="explorer-table-preset",
            label_visibility="collapsed",
        ) or "Overview"
        preset_cols = {
            "Overview": ["Player", "Club", "Position", "Price", "xP", "xP / GW", "xP GI", "xP CS", "xMins / GW", "Ownership %"],
            "Attacking": ["Player", "Club", "Position", "Price", "xP", "xP GI", "xP Goals", "xP Assists", "xMins / GW", "Ownership %"],
            "Defensive": ["Player", "Club", "Position", "Price", "xP", "xP CS", "xP DefCon", "xP Conceded", "xMins / GW", "Ownership %"],
            "All Components": ["Player", "Club", "Position", "Price", "xP", "xP / GW", "xP GI", "xP Goals", "xP Assists", "xP CS", "xP DefCon", "xP Conceded", "xP Saves", "xP Bonus", "xMins / GW", "Ownership %"],
        }
        cols_for_view = list(preset_cols.get(table_view, preset_cols["Overview"]))
        if has_user_squad and "Squad" in frame.columns and "Squad" not in cols_for_view:
            cols_for_view.insert(3, "Squad")
        if "Dream Team" in frame.columns and "Dream Team" not in cols_for_view:
            cols_for_view.append("Dream Team")
        visible_cols = [c for c in cols_for_view if c in frame.columns]
        visible = frame[visible_cols]
        selected_pid = st.session_state.get("explorer-player")
        selected_player = next((p for p in dataset["players"] if p["id"] == selected_pid), None) if selected_pid else None
        with st.container(key="explorer-action-bar"):
            bar_cols = st.columns([3, 1, 1], vertical_alignment="center")
            if selected_player:
                p_name = selected_player["name"]
                p_club = selected_player.get("team", "")
                p_pos = selected_player.get("pos", "")
                p_price = float(selected_player.get("price", 0.0))
                p_slice = player_slice(selected_player, model, gws)
                xp_disp = f"{p_slice['xP']:.1f}" if p_slice.get("xP") is not None else "—"
                bar_cols[0].markdown(f"**Selected:** {p_name} ({p_club} · {p_pos} · £{p_price:.1f}m) · **xP:** {xp_disp}")
                if bar_cols[1].button("🔍 Inspect Details", key="explorer-inspect-btn", type="primary"):
                    st.session_state["explorer-player"] = selected_pid
                    st.session_state["explorer-inspection"] = True
                    st.rerun()
                wl = st.session_state.get("watchlist", [])
                is_wl = selected_pid in wl
                wl_label = "⭐ Remove" if is_wl else "⭐ Watchlist"
                if bar_cols[2].button(wl_label, key="explorer-bar-watchlist"):
                    if is_wl:
                        st.session_state["watchlist"] = [i for i in wl if i != selected_pid]
                    else:
                        st.session_state["watchlist"] = [*wl, selected_pid]
                    st.rerun()
            else:
                bar_cols[0].caption("💡 Select any player row in the table below to inspect details or manage watchlist.")
        column_config = {
            "Price": st.column_config.NumberColumn("Price", format="£%.1fm"),
            "xP": st.column_config.NumberColumn("xP", format="%.2f"),
            "xP / GW": st.column_config.NumberColumn("xP / GW", format="%.2f"),
            "xP / 90": st.column_config.NumberColumn("xP / 90", format="%.2f"),
            "xP GI": st.column_config.NumberColumn("xP GI", format="%.2f", help="Projected points from goal involvement (goals + assists)"),
            "xP Goals": st.column_config.NumberColumn("xP Goals", format="%.2f", help="Projected points from goals scored"),
            "xP Assists": st.column_config.NumberColumn("xP Assists", format="%.2f", help="Projected points from assists"),
            "xP CS": st.column_config.NumberColumn("xP CS", format="%.2f", help="Projected points from clean sheets"),
            "xP DefCon": st.column_config.NumberColumn("xP DefCon", format="%.2f", help="Projected points from defensive contributions"),
            "xP Conceded": st.column_config.NumberColumn("xP Conceded", format="%.2f", help="Projected deductions from goals conceded"),
            "xP Saves": st.column_config.NumberColumn("xP Saves", format="%.2f", help="Projected points from saves (GKP)"),
            "xP Bonus": st.column_config.NumberColumn("xP Bonus", format="%.2f", help="Projected bonus points"),
            "xMins / GW": st.column_config.NumberColumn("xMins / GW", format="%.1f"),
            "Ownership %": st.column_config.NumberColumn("Ownership %", format="%.1f%%"),
        }
        st.dataframe(
            visible,
            column_config=column_config,
            hide_index=True,
            width="stretch",
            on_select=lambda: select_explorer_player("explorer-table", frame["ID"].tolist()),
            selection_mode="single-row",
            key="explorer-table",
        )
        st.download_button("Download filtered Players", visible.to_csv(index=False), "explorer-players.csv", "text/csv")
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
            explorer_inspection(player, model, gws, paths, dataset=dataset)


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

"""Manager Performance tracking view for Streamlit dashboard."""

from __future__ import annotations

from typing import Any
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from dashboard.performance_analytics import (
    CHIP_SYMBOLS,
    compute_composite_comparison_series,
    compute_kpis,
    compute_manager_series,
    compute_rival_series_dict,
    extract_chip_inventory,
)
from dashboard.performance_service import (
    extract_joined_classic_leagues,
    extract_top_standings_peers,
    load_classic_league_standings,
    load_entry_history,
    load_entry_summary,
    load_global_benchmarks,
)
from dashboard.planner import PlanStore
from dashboard.planner_service import PlannerPaths


def resolve_current_entry_id(paths: PlannerPaths) -> int | None:
    """Resolve Entry ID from URL query param, session state, preferences, or local user picks."""
    # 1. URL Query parameter (?entry_id=...)
    url_param = st.query_params.get("entry_id")
    if url_param:
        try:
            eid = int(url_param)
            if eid > 0:
                st.session_state["performance-entry-id"] = eid
                return eid
        except (ValueError, TypeError):
            pass

    # 2. Session state
    if "performance-entry-id" in st.session_state and st.session_state["performance-entry-id"]:
        return int(st.session_state["performance-entry-id"])

    # 3. Preferences JSON
    preferences = PlanStore(paths.storage / "preferences.json")
    saved = preferences.load() or {}
    if "entry_id" in saved and saved["entry_id"]:
        try:
            eid = int(saved["entry_id"])
            if eid > 0:
                st.session_state["performance-entry-id"] = eid
                return eid
        except (ValueError, TypeError):
            pass

    # 4. user_state.parquet if exists
    state_file = paths.processed / "user_state.parquet"
    if state_file.exists():
        try:
            df_state = pd.read_parquet(state_file)
            if not df_state.empty and "entry_id" in df_state.columns:
                eid = int(df_state.iloc[0]["entry_id"])
                if eid > 0:
                    st.session_state["performance-entry-id"] = eid
                    return eid
        except Exception:
            pass

    return None


def set_active_entry_id(entry_id: int, paths: PlannerPaths) -> None:
    st.session_state["performance-entry-id"] = entry_id
    st.query_params["entry_id"] = str(entry_id)
    preferences = PlanStore(paths.storage / "preferences.json")
    try:
        saved = preferences.load() or {}
        saved["entry_id"] = entry_id
        preferences.save(saved)
    except OSError:
        pass


def clear_active_entry_id(paths: PlannerPaths) -> None:
    st.session_state.pop("performance-entry-id", None)
    if "entry_id" in st.query_params:
        del st.query_params["entry_id"]
    preferences = PlanStore(paths.storage / "preferences.json")
    try:
        saved = preferences.load() or {}
        saved.pop("entry_id", None)
        preferences.save(saved)
    except OSError:
        pass


def render_onboarding_card(paths: PlannerPaths) -> None:
    st.title("Manager Performance")
    st.caption("Track your overall rank and points trajectory, overlay chip timing, and isolate rank movement drivers.")

    with st.container(border=True):
        st.subheader("Load Your FPL Manager Entry")
        st.write(
            "Enter your official FPL Entry ID below to view your season trajectory, rank progression, and mini-league performance. "
            "Data is fetched securely from public FPL endpoints without requiring your email or password."
        )

        col_input, col_btn = st.columns([3, 1], vertical_alignment="bottom")
        with col_input:
            entered_id = st.number_input(
                "FPL Entry ID",
                min_value=1,
                max_value=20_000_000,
                value=None,
                step=1,
                placeholder="e.g. 123456",
                key="onboarding-entry-input",
            )
        with col_btn:
            if st.button("Load Entry", type="primary", key="onboarding-load-btn", disabled=entered_id is None):
                if entered_id:
                    set_active_entry_id(int(entered_id), paths)
                    st.rerun()

        st.caption(
            "How to find your Entry ID: Log in to fantasy.premierleague.com, click the 'Points' tab, "
            "and copy the numeric ID in the URL: `fantasy.premierleague.com/entry/{ENTRY_ID}/event/...`"
        )


def _render_kpi_strip(kpis: dict[str, Any], league_name: str | None = None) -> None:
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        rank_val = f"#{kpis.get('overall_rank', 0):,}"
        rank_delta = kpis.get("rank_delta", 0)
        delta_label = f"{rank_delta:+,} vs prior GW" if rank_delta != 0 else "Unchanged"
        st.metric(
            "Overall Rank",
            rank_val,
            delta=delta_label,
            delta_color="normal" if rank_delta >= 0 else "inverse",
        )
        sub_text = f"Top {kpis.get('percentile', 0.0):.1f}% of active field"
        if kpis.get("league_rank"):
            sub_text = f"#{kpis['league_rank']} in {league_name or 'Mini-League'} · {sub_text}"
        st.caption(sub_text)

    with c2:
        cum_pts = f"{kpis.get('cum_net_points', 0):,} pts"
        leader_gap = kpis.get("league_leader_gap")
        gap_delta = f"-{leader_gap} to leader" if leader_gap is not None else None
        st.metric(
            "Cumulative Points",
            cum_pts,
            delta=gap_delta,
            delta_color="inverse" if leader_gap else "off",
        )
        st.caption("Official total points accumulated")

    with c3:
        swing = kpis.get("chip_swing", 0.0)
        st.metric(
            "Chip Timing Swing",
            f"{swing:+.1f} pts",
            delta=f"{kpis.get('chip_weeks', 0)} chip(s) played",
            delta_color="normal" if swing >= 0 else "inverse",
        )
        st.caption("Net points differential above baseline on chip weeks")

    with c4:
        hits = kpis.get("total_hits_cost", 0)
        bench = kpis.get("total_bench_points", 0)
        st.metric(
            "Hit & Bench Drag",
            f"-{hits} pts hits",
            delta=f"{bench} pts on bench",
            delta_color="off",
        )
        st.caption("Deducted transfer costs & bench points")


def _build_trajectory_figure(
    user_name: str,
    user_df: pd.DataFrame,
    rival_dfs: dict[int, pd.DataFrame],
    rival_labels: dict[int, str],
    metric: str,
    use_log_scale: bool = False,
) -> go.Figure:
    fig = go.Figure()

    rival_palette = ["#5856d6", "#146c43", "#d97706", "#dc2626", "#475569"]
    metric_col_map = {
        "Overall Rank": "overall_rank",
        "Cumulative Points": "total_points",
        "Gameweek Points": "net_points",
    }
    col_name = metric_col_map.get(metric, "overall_rank")

    # Plot rivals first (in background)
    for idx, (rid, rdf) in enumerate(rival_dfs.items()):
        color = rival_palette[idx % len(rival_palette)]
        r_label = rival_labels.get(rid, f"Rival {rid}")
        fig.add_trace(
            go.Scatter(
                x=rdf["gw"],
                y=rdf[col_name],
                name=r_label,
                mode="lines+markers",
                line=dict(color=color, width=1.5, dash="dot"),
                marker=dict(size=4),
                hovertemplate=f"<b>{r_label}</b><br>GW %{{x}}: %{{y:,}}<extra></extra>",
            )
        )
        # Add rival chip markers
        chip_rows = rdf[rdf["chip"].notna()]
        if not chip_rows.empty:
            for _, rrow in chip_rows.iterrows():
                c_symbol = CHIP_SYMBOLS.get(str(rrow["chip"]), "circle")
                fig.add_trace(
                    go.Scatter(
                        x=[rrow["gw"]],
                        y=[rrow[col_name]],
                        mode="markers+text",
                        marker=dict(symbol=c_symbol, size=11, color=color, line=dict(width=1, color="#ffffff")),
                        text=[f"{rrow['chip']}"],
                        textposition="top center",
                        name=f"{r_label} {rrow['chip']}",
                        showlegend=False,
                        hoverinfo="text",
                        hovertext=f"{r_label} played {rrow['chip']} in GW{rrow['gw']}",
                    )
                )

    # Plot user line (foreground, bold blue)
    fig.add_trace(
        go.Scatter(
            x=user_df["gw"],
            y=user_df[col_name],
            name=user_name,
            mode="lines+markers",
            line=dict(color="#0066cc", width=3),
            marker=dict(size=6, color="#0066cc"),
            hovertemplate=f"<b>{user_name}</b><br>GW %{{x}}: %{{y:,}}<extra></extra>",
        )
    )

    # Add user chip markers
    user_chip_rows = user_df[user_df["chip"].notna()]
    if not user_chip_rows.empty:
        for _, urow in user_chip_rows.iterrows():
            c_symbol = CHIP_SYMBOLS.get(str(urow["chip"]), "star")
            fig.add_trace(
                go.Scatter(
                    x=[urow["gw"]],
                    y=[urow[col_name]],
                    mode="markers+text",
                    marker=dict(symbol=c_symbol, size=14, color="#0066cc", line=dict(width=1.5, color="#ffffff")),
                    text=[f"{urow['chip']}"],
                    textposition="top center",
                    textfont=dict(size=12, color="#0066cc", family="Segoe UI, sans-serif"),
                    name=f"You: {urow['chip']}",
                    showlegend=False,
                    hoverinfo="text",
                    hovertext=f"You played {urow['chip']} in GW{urow['gw']}",
                )
            )

    is_rank = metric == "Overall Rank"
    y_axis_dict: dict[str, Any] = dict(
        gridcolor="#f0f0f2",
        zerolinecolor="#d0d0d4",
    )
    if is_rank:
        y_axis_dict["autorange"] = "reversed"
        if use_log_scale:
            y_axis_dict["type"] = "log"

    fig.update_layout(
        template="plotly_white",
        margin=dict(l=20, r=20, t=30, b=20),
        xaxis=dict(title="Gameweek", dtick=1, gridcolor="#f0f0f2"),
        yaxis=dict(title=metric, **y_axis_dict),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        font=dict(family="Segoe UI, -apple-system, sans-serif", color="#1d1d1f"),
        height=380,
    )
    return fig


def _build_delta_figure(
    user_df: pd.DataFrame,
    benchmark_mode: str,
) -> go.Figure:
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    delta_col = "delta_vs_rivals_mean" if benchmark_mode == "Rivals Mean" and "delta_vs_rivals_mean" in user_df.columns else "delta_vs_global"
    cum_col = "cum_delta_vs_rivals_mean" if benchmark_mode == "Rivals Mean" and "cum_delta_vs_rivals_mean" in user_df.columns else "cum_delta_vs_global"
    benchmark_label = "Rivals Mean" if benchmark_mode == "Rivals Mean" else "Global Average"

    deltas = user_df[delta_col].fillna(0)
    bar_colors = ["#146c43" if d >= 0 else "#dc2626" for d in deltas]

    # Weekly Delta Bars
    fig.add_trace(
        go.Bar(
            x=user_df["gw"],
            y=deltas,
            name=f"Weekly Δ vs {benchmark_label}",
            marker_color=bar_colors,
            hovertemplate="GW %{x}<br>Net Δ: %{y:+.1f} pts<extra></extra>",
        ),
        secondary_y=False,
    )

    # Cumulative Delta Line
    if cum_col in user_df.columns:
        fig.add_trace(
            go.Scatter(
                x=user_df["gw"],
                y=user_df[cum_col].fillna(0),
                name=f"Cumulative Δ vs {benchmark_label}",
                mode="lines+markers",
                line=dict(color="#0066cc", width=2.5),
                marker=dict(size=5),
                hovertemplate="GW %{x}<br>Cumulative Δ: %{y:+.1f} pts<extra></extra>",
            ),
            secondary_y=True,
        )

    # Annotate chip weeks on bars
    for _, row in user_df[user_df["chip"].notna()].iterrows():
        val = row[delta_col]
        if pd.notna(val):
            fig.add_annotation(
                x=row["gw"],
                y=val,
                text=str(row["chip"]),
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=1.5,
                arrowcolor="#0066cc",
                ax=0,
                ay=-24 if val >= 0 else 24,
                font=dict(color="#0066cc", size=10, family="Segoe UI, sans-serif"),
                bgcolor="#ffffff",
                bordercolor="#0066cc",
                borderwidth=1,
                borderpad=2,
            )

    fig.update_layout(
        template="plotly_white",
        margin=dict(l=20, r=20, t=30, b=20),
        xaxis=dict(title="Gameweek", dtick=1, gridcolor="#f0f0f2"),
        yaxis=dict(title=f"Weekly Net Δ vs {benchmark_label}", gridcolor="#f0f0f2", zerolinecolor="#86868b"),
        yaxis2=dict(title=f"Cumulative Δ vs {benchmark_label}", showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        font=dict(family="Segoe UI, -apple-system, sans-serif", color="#1d1d1f"),
        height=380,
    )
    return fig


def _build_chip_adoption_figure(
    user_df: pd.DataFrame,
    benchmarks: dict[int, dict[str, Any]],
) -> go.Figure:
    fig = go.Figure()

    gw_ids = sorted(user_df["gw"].tolist())
    chip_colors = {
        "bboost": "#5856d6",
        "3xc": "#d97706",
        "wildcard": "#0066cc",
        "freehit": "#146c43",
    }
    chip_display_names = {
        "bboost": "Bench Boost (BB)",
        "3xc": "Triple Captain (TC)",
        "wildcard": "Wildcard (WC)",
        "freehit": "Free Hit (FH)",
    }

    # Aggregate global chip percentages
    by_chip_series: dict[str, list[float]] = {"bboost": [], "3xc": [], "wildcard": [], "freehit": []}
    for gw in gw_ids:
        b = benchmarks.get(gw, {})
        ranked_count = b.get("ranked_count") or 10_000_000
        chip_plays = b.get("chip_plays") or []
        play_map = {item.get("chip_name"): int(item.get("num_played") or 0) for item in chip_plays}
        for c_key in by_chip_series:
            num = play_map.get(c_key, 0)
            pct = (num / ranked_count) * 100.0 if ranked_count > 0 else 0.0
            by_chip_series[c_key].append(round(pct, 2))

    for c_key, pcts in by_chip_series.items():
        fig.add_trace(
            go.Bar(
                x=gw_ids,
                y=pcts,
                name=chip_display_names[c_key],
                marker_color=chip_colors[c_key],
                hovertemplate=f"<b>{chip_display_names[c_key]}</b><br>GW %{{x}}: %{{y:.1f}}% of managers<extra></extra>",
            )
        )

    # Overlay user chip plays as vertical lines or marker annotations
    for _, row in user_df[user_df["chip"].notna()].iterrows():
        fig.add_vline(
            x=row["gw"],
            line_width=2,
            line_dash="dash",
            line_color="#1d1d1f",
            annotation_text=f"Your {row['chip']}",
            annotation_position="top left",
        )

    fig.update_layout(
        template="plotly_white",
        barmode="stack",
        margin=dict(l=20, r=20, t=30, b=20),
        xaxis=dict(title="Gameweek", dtick=1, gridcolor="#f0f0f2"),
        yaxis=dict(title="Global Managers Playing Chip (%)", ticksuffix="%", gridcolor="#f0f0f2"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        font=dict(family="Segoe UI, -apple-system, sans-serif", color="#1d1d1f"),
        height=260,
    )
    return fig


def performance_view(paths: PlannerPaths) -> None:
    """Main rendering entry point for Performance workspace."""
    entry_id = resolve_current_entry_id(paths)
    if entry_id is None:
        render_onboarding_card(paths)
        return

    # Load manager summary & history
    with st.spinner("Loading manager performance data..."):
        try:
            summary = load_entry_summary(entry_id)
            history = load_entry_history(entry_id)
        except Exception as exc:
            st.error(f"Error loading Entry {entry_id}: {exc}")
            if st.button("Change Entry ID", key="err-change-entry"):
                clear_active_entry_id(paths)
                st.rerun()
            return

    global_benchmarks = load_global_benchmarks(paths=paths)
    raw_user_df = compute_manager_series(history, global_benchmarks=global_benchmarks)
    if raw_user_df.empty:
        st.warning(f"No completed Gameweek history found for Entry {entry_id}.")
        if st.button("Change Entry ID", key="empty-change-entry"):
            clear_active_entry_id(paths)
            st.rerun()
        return

    # Warning if cached snapshot was used due to API rate limit / outage
    if summary.get("_cached_fallback") or history.get("_cached_fallback"):
        st.caption(f"Note: {summary.get('_stale_warning') or history.get('_stale_warning')}")

    # Top Control Bar
    first_name = summary.get("player_first_name", "")
    last_name = summary.get("player_last_name", "")
    entry_name = summary.get("name", f"Entry {entry_id}")
    manager_display = f"{entry_name} ({first_name} {last_name})".strip()

    st.title("Manager Performance")
    ctrl1, ctrl2, ctrl3 = st.columns([4, 1, 1], vertical_alignment="center")
    with ctrl1:
        st.caption(f"**Manager:** {manager_display} · **Entry ID:** `{entry_id}`")
    with ctrl2:
        if st.button("Refresh", key="perf-refresh-btn"):
            load_entry_summary.clear()
            load_entry_history.clear()
            load_classic_league_standings.clear()
            st.rerun()
    with ctrl3:
        if st.button("Switch Entry", key="perf-switch-btn"):
            clear_active_entry_id(paths)
            st.rerun()

    # League & Rival Selection Toolbar
    joined_leagues = extract_joined_classic_leagues(summary)
    league_options = [None, *joined_leagues]

    tcol1, tcol2, tcol3 = st.columns([3, 4, 3])
    with tcol1:
        selected_league = st.selectbox(
            "Classic Mini-League",
            league_options,
            format_func=lambda lg: "Global Benchmark Only" if lg is None else f"{lg['name']} (Rank #{lg['entry_rank']})",
            key="perf-league-select",
        )

    league_standings: dict[str, Any] | None = None
    standings_peers: list[dict[str, Any]] = []
    if selected_league is not None:
        try:
            league_standings = load_classic_league_standings(selected_league["id"])
            standings_peers = extract_top_standings_peers(league_standings, exclude_entry_id=entry_id)
        except Exception as exc:
            st.caption(f"Standings unavailable for {selected_league['name']}: {exc}")

    # Build searchable label map for comparison picker
    peer_labels: dict[int, str] = {
        p["entry_id"]: f"#{p['rank']} {p['player_name']} ({p['entry_name']}) · {p['total']} pts"
        for p in standings_peers
    }

    with tcol2:
        selected_rival_ids = st.multiselect(
            "Compare Rivals (Top 50)",
            list(peer_labels.keys()),
            format_func=lambda pid: peer_labels.get(pid, f"Entry {pid}"),
            max_selections=5,
            key="perf-rivals-multiselect",
            help="Select up to 5 rivals from the mini-league top standings to overlay trajectories and chip timing.",
        )

    # Optional manual Entry ID adder
    with tcol3:
        manual_rival_input = st.text_input(
            "Add Rival by Entry ID",
            placeholder="e.g. 987654",
            key="perf-manual-rival-input",
            help="Compare against any manager even if outside the top 50.",
        )
        if manual_rival_input.strip():
            try:
                manual_eid = int(manual_rival_input.strip())
                if manual_eid not in selected_rival_ids and manual_eid != entry_id:
                    selected_rival_ids.append(manual_eid)
                    peer_labels[manual_eid] = f"Rival Entry {manual_eid}"
            except ValueError:
                pass

    # Load selected rivals' histories lazily (1 call per selected rival)
    rival_histories: dict[int, dict[str, Any]] = {}
    for rid in selected_rival_ids:
        try:
            rival_histories[rid] = load_entry_history(rid)
        except Exception as exc:
            st.caption(f"Could not load Rival {rid}: {exc}")

    rival_dfs = compute_rival_series_dict(rival_histories, global_benchmarks=global_benchmarks)
    user_composite_df = compute_composite_comparison_series(raw_user_df, rival_dfs)

    # Benchmark Toggle
    benchmark_options = ["Global Average"]
    if rival_dfs:
        benchmark_options.append("Rivals Mean")
    b_col1, b_col2 = st.columns([2, 3])
    with b_col1:
        chosen_benchmark = st.radio(
            "Delta Benchmark",
            benchmark_options,
            horizontal=True,
            key="perf-benchmark-choice",
            help="Choose baseline for weekly points delta and net chip swing calculation.",
        )
    with b_col2:
        max_gw = int(raw_user_df["gw"].max())
        gw_slider = st.slider("Gameweek Window", 1, max_gw, (1, max_gw), key="perf-gw-slider")

    # Filter by selected Gameweek window
    user_df = user_composite_df[(user_composite_df["gw"] >= gw_slider[0]) & (user_composite_df["gw"] <= gw_slider[1])].copy()
    filtered_rival_dfs = {
        rid: rdf[(rdf["gw"] >= gw_slider[0]) & (rdf["gw"] <= gw_slider[1])].copy()
        for rid, rdf in rival_dfs.items()
    }

    # Row 2: KPI Strip
    kpis = compute_kpis(
        user_df,
        summary,
        league_standings=league_standings,
        benchmark_col="rivals_mean" if chosen_benchmark == "Rivals Mean" else "global_avg",
    )
    st.divider()
    _render_kpi_strip(kpis, league_name=selected_league["name"] if selected_league else None)
    st.divider()

    # Row 3: Synchronized Visual Suite
    st.subheader("Performance Trajectory")
    chart_view_cols = st.columns([3, 1])
    with chart_view_cols[0]:
        metric_choice = st.segmented_control(
            "Trajectory metric",
            ["Overall Rank", "Cumulative Points", "Gameweek Points"],
            default="Overall Rank",
            key="perf-trajectory-metric",
            label_visibility="collapsed",
        ) or "Overall Rank"
    with chart_view_cols[1]:
        use_log = st.checkbox("Log scale (Rank)", value=False, key="perf-log-scale") if metric_choice == "Overall Rank" else False

    fig_trajectory = _build_trajectory_figure(
        user_name=entry_name,
        user_df=user_df,
        rival_dfs=filtered_rival_dfs,
        rival_labels=peer_labels,
        metric=metric_choice,
        use_log_scale=use_log,
    )
    st.plotly_chart(fig_trajectory, width="stretch", config={"displayModeBar": False}, key="perf-chart-trajectory")

    st.subheader(f"Weekly & Cumulative Points Delta (vs {chosen_benchmark})")
    fig_delta = _build_delta_figure(user_df, benchmark_mode=chosen_benchmark)
    st.plotly_chart(fig_delta, width="stretch", config={"displayModeBar": False}, key="perf-chart-delta")

    st.subheader("Chip Adoption & Field Timing")
    fig_chips = _build_chip_adoption_figure(user_df, benchmarks=global_benchmarks)
    st.plotly_chart(fig_chips, width="stretch", config={"displayModeBar": False}, key="perf-chart-chips")

    # Row 4: Tabular Attributions
    st.divider()
    tab_attr, tab_chips = st.tabs(["Gameweek Attribution Table", "Head-to-Head Chip Inventory"])

    with tab_attr:
        st.caption("Per-Gameweek breakdown of score, benchmark delta, hit penalties, and rank movement.")
        display_cols = [
            "gw",
            "net_points",
            "points",
            "cost",
            "global_avg",
            "delta_vs_global",
            "overall_rank",
            "gw_rank",
            "rank_change",
            "chip",
            "bench_points",
            "team_value",
            "bank",
        ]
        if "rivals_mean" in user_df.columns and user_df["rivals_mean"].notna().any():
            display_cols.insert(6, "rivals_mean")
            display_cols.insert(7, "delta_vs_rivals_mean")

        table_df = user_df[[c for c in display_cols if c in user_df.columns]].copy()
        col_rename = {
            "gw": "GW",
            "net_points": "Net Pts",
            "points": "Gross Pts",
            "cost": "Hits",
            "global_avg": "Global Avg",
            "delta_vs_global": "Δ vs Global",
            "rivals_mean": "Rivals Avg",
            "delta_vs_rivals_mean": "Δ vs Rivals",
            "overall_rank": "Overall Rank",
            "gw_rank": "GW Rank",
            "rank_change": "Rank Movement",
            "chip": "Chip Played",
            "bench_points": "Bench Pts",
            "team_value": "Team Value (£m)",
            "bank": "Bank (£m)",
        }
        table_df = table_df.rename(columns=col_rename)
        st.dataframe(table_df, hide_index=True, width="stretch")
        st.download_button(
            "Download Performance CSV",
            table_df.to_csv(index=False),
            f"fpl-performance-{entry_id}.csv",
            "text/csv",
            key="perf-download-csv",
        )

    with tab_chips:
        st.caption("Chip deployment status across Set 1 (GW1–19) and Set 2 (GW20–38) per official FPL rules.")
        user_inv = extract_chip_inventory(history)
        chip_rows: list[dict[str, Any]] = []
        for chip_code in ("WC", "BB", "FH", "TC"):
            row_dict: dict[str, Any] = {
                "Chip": chip_code,
                f"You ({entry_name}) Set 1": user_inv[chip_code]["Set 1 (GW1–19)"],
                f"You ({entry_name}) Set 2": user_inv[chip_code]["Set 2 (GW20–38)"],
            }
            # Add each rival's inventory
            for rid, rhist in rival_histories.items():
                r_name = peer_labels.get(rid, f"Rival {rid}").split(" (")[0]
                rinv = extract_chip_inventory(rhist)
                row_dict[f"{r_name} Set 1"] = rinv[chip_code]["Set 1 (GW1–19)"]
                row_dict[f"{r_name} Set 2"] = rinv[chip_code]["Set 2 (GW20–38)"]
            chip_rows.append(row_dict)

        st.dataframe(pd.DataFrame(chip_rows), hide_index=True, width="stretch")

(function () {
  const POS_ORDER = ["G", "D", "M", "F"];
  const POS_LABEL = { G: "GKP", D: "DEF", M: "MID", F: "FWD" };
  const POS_COLORS = { G: "#eab308", D: "#3b82f6", M: "#10b981", F: "#ef4444" };
  const WINDOW_GWS = {
    first_half: rangeGws(1, 19),
    second_half: rangeGws(20, 38),
    full_season: rangeGws(1, 38),
  };
  const SCORE_MODES = ["all_projection", "realized_points", "remaining_projection"];
  const PLOT_LAYOUT = {
    margin: { t: 36, r: 16, b: 48, l: 52 },
    paper_bgcolor: "#111827",
    plot_bgcolor: "#111827",
    font: { color: "#f8fafc", family: "Inter, sans-serif", size: 11 },
    legend: { orientation: "h", y: 1.12, font: { size: 11 } },
    hovermode: "closest",
  };

  let ctx = null;
  let seasonWindow = "first_half";
  let scoreMode = "all_projection";
  let yMetric = "rate_per_90";
  let xminsFloor = 45;
  let selectedPlayerId = null;
  let tableSortKey = "total";
  let tableSortAsc = false;
  let bound = false;

  function rangeGws(start, end) {
    const out = [];
    for (let gw = start; gw <= end; gw += 1) out.push(gw);
    return out;
  }

  function players() {
    return ctx && ctx.getPlayers ? ctx.getPlayers() : [];
  }

  function meta() {
    return (ctx && ctx.getMeta && ctx.getMeta()) || {};
  }

  function sliceOf(player) {
    const modelName = ctx && ctx.getPrimaryModel ? ctx.getPrimaryModel() : "";
    const modelData = (player.models && player.models[modelName]) || player;
    const explorer = (modelData && modelData.explorer) || player.explorer || {};
    const windowSlices = explorer[seasonWindow] || {};
    return windowSlices[scoreMode] || null;
  }

  function realizedAvailable() {
    const finished = new Set(meta().finished_gameweeks || []);
    return WINDOW_GWS[seasonWindow].some((gw) => finished.has(gw));
  }

  function yValue(slice) {
    if (!slice) return null;
    const value = slice[yMetric];
    return Number.isFinite(value) ? value : null;
  }

  function bindControls() {
    if (bound) return;
    bound = true;
    const pos = document.getElementById("explorer-pos-checks");
    POS_ORDER.forEach((code) => {
      const lab = document.createElement("label");
      lab.innerHTML = `<input type="checkbox" class="explorer-pos" value="${code}" checked> ${POS_LABEL[code]}`;
      pos.appendChild(lab);
    });
    [
      document.getElementById("explorer-price-min"),
      document.getElementById("explorer-price-max"),
      document.getElementById("explorer-xmins-floor"),
      document.getElementById("explorer-search"),
    ].forEach((el) => el && el.addEventListener("input", render));
    document.querySelectorAll("input[name=season-window]").forEach((el) => {
      el.addEventListener("change", () => {
        seasonWindow = el.value;
        if (scoreMode === "realized_points" && !realizedAvailable()) {
          scoreMode = "all_projection";
          const all = document.querySelector('input[name=score-mode][value="all_projection"]');
          if (all) all.checked = true;
        }
        render();
      });
    });
    document.querySelectorAll("input[name=score-mode]").forEach((el) => {
      el.addEventListener("change", () => {
        if (!SCORE_MODES.includes(el.value)) return;
        scoreMode = el.value;
        render();
      });
    });
    document.querySelectorAll("input[name=y-metric]").forEach((el) => {
      el.addEventListener("change", () => {
        yMetric = el.value;
        render();
      });
    });
    document.getElementById("explorer-xmins-floor").addEventListener("input", (e) => {
      xminsFloor = parseFloat(e.target.value);
      document.getElementById("explorer-xmins-floor-val").textContent = String(xminsFloor);
    });
    document.getElementById("explorer-pos-checks").addEventListener("change", render);
    document.getElementById("explorer-table").addEventListener("click", (e) => {
      const row = e.target.closest("tr[data-player-id]");
      if (!row) return;
      const pid = Number(row.dataset.playerId);
      selectedPlayerId = selectedPlayerId === pid ? null : pid;
      render();
      row.scrollIntoView({ block: "nearest" });
    });
    document.querySelectorAll(".explorer-table thead th[data-sort]").forEach((th) => {
      th.addEventListener("click", () => {
        const key = th.dataset.sort;
        if (tableSortKey === key) {
          tableSortAsc = !tableSortAsc;
        } else {
          tableSortKey = key;
          tableSortAsc = ["name", "club", "pos", "role"].includes(key);
        }
        render();
      });
    });
  }

  function setupClubAndPrice() {
    const clubRoot = document.getElementById("explorer-club");
    const clubFilter = window.mountClubMultiSelect
      ? window.mountClubMultiSelect(clubRoot, { emptyLabel: "All clubs", onChange: render })
      : null;
    if (clubFilter) {
      clubFilter.rebuild(Array.from(new Set(players().map((p) => p.team))).sort());
    }
    const prices = players().map((p) => p.price);
    const minP = prices.length ? Math.floor(Math.min(...prices) * 2) / 2 : 4;
    const maxP = prices.length ? Math.ceil(Math.max(...prices) * 2) / 2 : 15;
    const minEl = document.getElementById("explorer-price-min");
    const maxEl = document.getElementById("explorer-price-max");
    if (!minEl.value) minEl.value = minP.toFixed(1);
    if (!maxEl.value) maxEl.value = maxP.toFixed(1);
  }

  function hideReason(player, slice, needle, applyChartOnly) {
    const posOn = new Set(
      Array.from(document.querySelectorAll(".explorer-pos:checked")).map((el) => el.value)
    );
    const clubFilter = document.getElementById("explorer-club")?._clubMulti;
    const pmin = parseFloat(document.getElementById("explorer-price-min").value);
    const pmax = parseFloat(document.getElementById("explorer-price-max").value);
    if (!posOn.has(player.pos)) return "position";
    if (clubFilter && !clubFilter.allows(player.team)) return "club";
    if (player.price < pmin || player.price > pmax) return "price";
    if (needle && !nameHit(player, needle)) return "search";
    if (!slice) return "no-slice";
    if (applyChartOnly && (slice.avg_minutes || 0) < xminsFloor) return "xmins";
    if (applyChartOnly && yValue(slice) === null) return "y";
    return "";
  }

  function nameHit(player, needle) {
    if (!needle) return false;
    return `${player.name} ${player.team} ${player.expected_role || ""}`.toLowerCase().includes(needle);
  }

  function rankedRows() {
    const needle = (document.getElementById("explorer-search").value || "").trim().toLowerCase();
    const rows = players()
      .map((player) => ({ player, slice: sliceOf(player) }))
      .filter((row) => row.slice)
      .sort((a, b) => (b.slice.total || 0) - (a.slice.total || 0));
    rows.forEach((row, i) => {
      row.rank = i + 1;
    });
    const visible = rows.filter(
      (row) => !hideReason(row.player, row.slice, needle, true)
    );
    const tableRows = rows.filter(
      (row) => !hideReason(row.player, row.slice, needle, false)
    );
    return { rows, visible, tableRows, needle };
  }

  function sortValue(row, key) {
    const player = row.player;
    const slice = row.slice;
    const values = {
      rank: row.rank,
      name: player.name,
      club: player.team,
      pos: player.pos,
      price: player.price,
      own: player.ownership_pct || 0,
      total: slice.total,
      rate_per_90: slice.rate_per_90,
      avg_minutes: slice.avg_minutes,
      xp_minutes: slice.xp_minutes,
      xp_goals: slice.xp_goals,
      xp_assists: slice.xp_assists,
      xp_clean_sheet: slice.xp_clean_sheet,
      xp_conceded: slice.xp_conceded,
      xp_defcon: slice.xp_defcon,
      xp_saves: slice.xp_saves,
      xp_bonus: slice.xp_bonus,
      role: player.expected_role || "",
    };
    return values[key];
  }

  function markerSize(slice, selected) {
    const bonus = selected ? 4 : 0;
    return Math.max(7 + bonus, Math.min(28, 6 + bonus + (slice.avg_minutes || 0) / 4.5));
  }

  function traces(visible, axisX) {
    return POS_ORDER.map((pos) => {
      const subset = visible.filter((row) => row.player.pos === pos);
      return {
        type: "scatter",
        mode: "markers+text",
        name: POS_LABEL[pos],
        x: subset.map((row) => (axisX === "own" ? row.player.ownership_pct : row.player.price)),
        y: subset.map((row) => yValue(row.slice)),
        text: subset.map((row) => (row.player.id === selectedPlayerId ? row.player.name : "")),
        textposition: "top center",
        textfont: { size: 10, color: "#e2e8f0" },
        customdata: subset.map((row) => [
          row.player.id,
          row.player.name,
          row.player.team,
          row.slice.total,
          row.slice.avg_minutes,
        ]),
        marker: {
          size: subset.map((row) => markerSize(row.slice, row.player.id === selectedPlayerId)),
          color: POS_COLORS[pos],
          opacity: subset.map((row) => (selectedPlayerId && row.player.id !== selectedPlayerId ? 0.35 : 0.88)),
          line: {
            width: subset.map((row) => (row.player.id === selectedPlayerId ? 2.5 : 0.5)),
            color: subset.map((row) => (row.player.id === selectedPlayerId ? "#fff" : "#334155")),
          },
        },
        hovertemplate:
          "<b>%{customdata[1]}</b> (%{customdata[2]})<br>" +
          (axisX === "own" ? "Own %: %{x:.1f}%<br>" : "Price: £%{x:.1f}m<br>") +
          "Y: %{y:.2f}<br>Total: %{customdata[3]:.2f} · Avg mins: %{customdata[4]:.1f}<extra></extra>",
      };
    });
  }

  function yAxisTitle() {
    if (yMetric === "per_gameweek") {
      return scoreMode === "realized_points" ? "Pts per Gameweek" : "xP per Gameweek";
    }
    return "Projected Rate";
  }

  let markerClicked = false;

  function onPlotClick(ev) {
    if (!ev.points || !ev.points.length) return;
    markerClicked = true;
    selectedPlayerId = Number(ev.points[0].customdata[0]);
    render();
    const row = document.querySelector(`#explorer-table tr[data-player-id="${selectedPlayerId}"]`);
    if (row) row.scrollIntoView({ block: "nearest" });
  }

  function onPlotBackgroundClick() {
    setTimeout(() => {
      if (markerClicked) {
        markerClicked = false;
        return;
      }
      if (selectedPlayerId == null) return;
      selectedPlayerId = null;
      render();
    }, 0);
  }

  function bindChartClicks() {
    ["chart-ownership", "chart-price"].forEach((id) => {
      const el = document.getElementById(id);
      if (!el) return;
      if (!el._explorerMarkerBound && typeof el.on === "function") {
        el.on("plotly_click", onPlotClick);
        el.addEventListener("click", onPlotBackgroundClick);
        el._explorerMarkerBound = true;
      }
    });
  }

  function renderCharts(visible) {
    if (typeof Plotly === "undefined") return;
    const yTitle = yAxisTitle();
    const ownLayout = {
      ...PLOT_LAYOUT,
      xaxis: { title: "Ownership %", gridcolor: "#1e293b", zeroline: false },
      yaxis: { title: yTitle, gridcolor: "#1e293b", zeroline: false },
    };
    const priceLayout = {
      ...PLOT_LAYOUT,
      xaxis: { title: "Price (£m)", gridcolor: "#1e293b", zeroline: false },
      yaxis: { title: yTitle, gridcolor: "#1e293b", zeroline: false },
    };
    Plotly.react("chart-ownership", traces(visible, "own"), ownLayout, {
      responsive: true,
      displayModeBar: true,
    });
    Plotly.react("chart-price", traces(visible, "price"), priceLayout, {
      responsive: true,
      displayModeBar: true,
    });
    bindChartClicks();
  }

  function renderTable(tableRows) {
    const body = document.getElementById("explorer-table");
    const sorted = tableRows.slice().sort((a, b) => {
      const va = sortValue(a, tableSortKey);
      const vb = sortValue(b, tableSortKey);
      if (va == null && vb == null) return 0;
      if (va == null) return 1;
      if (vb == null) return -1;
      if (typeof va === "string") {
        const cmp = va.localeCompare(vb);
        return tableSortAsc ? cmp : -cmp;
      }
      return tableSortAsc ? va - vb : vb - va;
    });
    body.innerHTML = sorted
      .map((row) => {
        const p = row.player;
        const s = row.slice;
        const selected = p.id === selectedPlayerId ? " selected" : "";
        return `<tr class="${selected}" data-player-id="${p.id}">
          <td>${row.rank}</td>
          <td>${p.name}</td>
          <td>${p.team}</td>
          <td>${POS_LABEL[p.pos] || p.pos}</td>
          <td>${Number(p.price).toFixed(1)}</td>
          <td>${Number(p.ownership_pct || 0).toFixed(1)}</td>
          <td>${Number(s.total).toFixed(2)}</td>
          <td>${s.rate_per_90 == null ? "—" : Number(s.rate_per_90).toFixed(2)}</td>
          <td>${Number(s.avg_minutes).toFixed(1)}</td>
          <td>${Number(s.xp_minutes).toFixed(2)}</td>
          <td>${Number(s.xp_goals).toFixed(2)}</td>
          <td>${Number(s.xp_assists).toFixed(2)}</td>
          <td>${Number(s.xp_clean_sheet).toFixed(2)}</td>
          <td>${Number(s.xp_conceded).toFixed(2)}</td>
          <td>${Number(s.xp_defcon).toFixed(2)}</td>
          <td>${Number(s.xp_saves).toFixed(2)}</td>
          <td>${Number(s.xp_bonus).toFixed(2)}</td>
          <td>${p.expected_role || "—"}</td>
        </tr>`;
      })
      .join("");
  }

  function render() {
    if (!ctx) return;
    bindControls();
    setupClubAndPrice();
    const realizedLabel = document.getElementById("realized-mode-label");
    if (realizedAvailable()) {
      realizedLabel.hidden = false;
    } else {
      realizedLabel.hidden = true;
      if (scoreMode === "realized_points") {
        scoreMode = "all_projection";
        const all = document.querySelector('input[name=score-mode][value="all_projection"]');
        if (all) all.checked = true;
      }
    }
    const { rows, visible, tableRows } = rankedRows();
    document.getElementById("explorer-meta").textContent =
      `Window ${seasonWindow.replaceAll("_", " ")} · ${scoreMode.replaceAll("_", " ")} · chart ${visible.length} / table ${tableRows.length} / ${rows.length}`;
    renderCharts(visible);
    renderTable(tableRows);
  }

  window.initOwnershipExplorer = function (context) {
    ctx = context;
    seasonWindow = (context.getMeta && context.getMeta().default_season_window) || "first_half";
    scoreMode = (context.getMeta && context.getMeta().default_score_mode) || "all_projection";
    const win = document.querySelector(`input[name=season-window][value="${seasonWindow}"]`);
    if (win) win.checked = true;
    render();
  };

  window.renderOwnershipExplorer = render;
})();

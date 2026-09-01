(function () {
  const POS_ORDER = ["G", "D", "M", "F"];
  const POS_LABEL = { G: "GKP", D: "DEF", M: "MID", F: "FWD" };
  const POS_COLORS = { G: "#eab308", D: "#3b82f6", M: "#10b981", F: "#ef4444" };
  const PLOT_LAYOUT = {
    margin: { t: 36, r: 16, b: 48, l: 52 },
    paper_bgcolor: "#111827",
    plot_bgcolor: "#111827",
    font: { color: "#f8fafc", family: "Inter, sans-serif", size: 11 },
    legend: { orientation: "h", y: 1.12, font: { size: 11 } },
    hovermode: "closest",
  };
  const MAX_MIX = 5;

  let ctx = null;
  let yMetric = "rate_per_90";
  let xminsFloor = 45;
  let selectedPlayerId = null;
  let tableSortKey = "total";
  let tableSortAsc = false;
  let bound = false;
  let mixA = [];
  let mixB = [];
  let mixReason = "";
  let assume90 = false;

  function players() {
    return ctx && ctx.getPlayers ? ctx.getPlayers() : [];
  }

  function meta() {
    return (ctx && ctx.getMeta && ctx.getMeta()) || {};
  }

  function viewGws() {
    if (ctx && ctx.getViewGws) return ctx.getViewGws();
    return meta().planning_gw_ids || [];
  }

  function playerProj(player) {
    const modelName = ctx && ctx.getPrimaryModel ? ctx.getPrimaryModel() : "";
    const modelData = (player.models && player.models[modelName]) || player;
    return (modelData && modelData.projections) || player.projections || {};
  }

  function assumeNinetyRow(row) {
    const xmins = Number(row.xmins || 0);
    if (xmins <= 0) return row;
    const total = Number(row.total_xp || 0);
    const xpMinIn = Number(row.xp_minutes || 0);
    const n = Math.max(1, Math.ceil(xmins / 90));
    const target = 90 * n;
    const inferred = xpMinIn > 0 ? xpMinIn : (xmins >= 60 ? 2 * n : 1);
    const scale = target / xmins;
    const newXpMin = 2 * n;
    const scaled = (key) => round(Number(row[key] || 0) * scale, 2);
    return {
      ...row,
      xmins: target,
      xp_minutes: newXpMin,
      total_xp: round((total - inferred) * scale + newXpMin, 2),
      xg_pts: scaled("xg_pts"),
      xa_pts: scaled("xa_pts"),
      xcs_pts: scaled("xcs_pts"),
      xdefcon_pts: scaled("xdefcon_pts"),
      xb_pts: scaled("xb_pts"),
      xp_conceded: scaled("xp_conceded"),
      xp_saves: scaled("xp_saves"),
    };
  }

  function gwProjection(player, gw) {
    const row = playerProj(player)[`gw${gw}`] || {};
    return assume90 ? assumeNinetyRow(row) : row;
  }

  function sliceOf(player) {
    const gws = viewGws();
    let total = 0;
    let minutes = 0;
    const components = {
      xp_minutes: 0, xp_goals: 0, xp_assists: 0, xp_clean_sheet: 0,
      xp_conceded: 0, xp_defcon: 0, xp_saves: 0, xp_bonus: 0,
    };
    const perGw = {};
    gws.forEach((gw) => {
      const row = gwProjection(player, gw);
      const xp = Number(row.total_xp || 0);
      const mins = Number(row.xmins || 0);
      total += xp;
      minutes += mins;
      perGw[gw] = xp;
      Object.keys(components).forEach((key) => {
        components[key] += Number(row[key] || 0);
      });
    });
    const n = gws.length;
    return {
      total: round(total, 2),
      minutes: round(minutes, 1),
      avg_minutes: n ? round(minutes / n, 1) : 0,
      rate_per_90: minutes > 0 ? round(total / (minutes / 90), 4) : null,
      per_gameweek: n ? round(total / n, 4) : 0,
      n_gameweeks: n,
      perGw,
      ...Object.fromEntries(Object.entries(components).map(([k, v]) => [k, round(v, 2)])),
    };
  }

  function round(value, digits) {
    const f = 10 ** digits;
    return Math.round(value * f) / f;
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
    document.querySelectorAll("input[name=y-metric]").forEach((el) => {
      el.addEventListener("change", () => {
        yMetric = el.value;
        render();
      });
    });
    document.getElementById("explorer-assume-90")?.addEventListener("change", (e) => {
      assume90 = e.target.checked;
      render();
    });
    document.getElementById("explorer-xmins-floor").addEventListener("input", (e) => {
      xminsFloor = parseFloat(e.target.value);
      document.getElementById("explorer-xmins-floor-val").textContent = String(xminsFloor);
    });
    document.getElementById("explorer-pos-checks").addEventListener("change", render);
    document.getElementById("explorer-table-wrap")?.addEventListener("click", (e) => {
      const th = e.target.closest("th[data-sort]");
      if (!th) return;
      const key = th.dataset.sort;
      if (tableSortKey === key) {
        tableSortAsc = !tableSortAsc;
      } else {
        tableSortKey = key;
        tableSortAsc = ["name", "club", "pos", "role"].includes(key);
      }
      render();
    });
    document.getElementById("explorer-table").addEventListener("click", (e) => {
      const mixBtn = e.target.closest("button[data-mix]");
      if (mixBtn) {
        applyMixLetter(Number(mixBtn.dataset.playerId), mixBtn.dataset.mix);
        e.stopPropagation();
        render();
        return;
      }
      const row = e.target.closest("tr[data-player-id]");
      if (!row) return;
      const pid = Number(row.dataset.playerId);
      selectedPlayerId = selectedPlayerId === pid ? null : pid;
      render();
      row.scrollIntoView({ block: "nearest" });
    });
    const mixCols = document.querySelector(".mix-columns");
    if (mixCols) {
      mixCols.addEventListener("click", onMixClick);
      mixCols.addEventListener("dragstart", onMixDragStart);
      mixCols.addEventListener("dragover", onMixDragOver);
      mixCols.addEventListener("drop", onMixDrop);
    }
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
    if (minEl && !minEl.value) minEl.value = minP.toFixed(1);
    if (maxEl && !maxEl.value) maxEl.value = maxP.toFixed(1);
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
    return { rows, visible, tableRows };
  }

  function sortValue(row, key) {
    const player = row.player;
    const slice = row.slice;
    if (key === "rank") return row.rank;
    if (key === "name") return player.name;
    if (key === "club") return player.team;
    if (key === "pos") return player.pos;
    if (key === "price") return player.price;
    if (key === "own") return player.ownership_pct;
    if (key === "role") return player.expected_role || "";
    if (key && key.startsWith("gw")) return slice.perGw[Number(key.slice(2))] || 0;
    return slice[key];
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
    return yMetric === "per_gameweek" ? "xP per Gameweek" : "Projected Rate";
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

  function occupyingSide(playerId) {
    if (mixA.includes(playerId)) return "a";
    if (mixB.includes(playerId)) return "b";
    return null;
  }

  function mixFullReason(side) {
    return side === "a" ? "Mix A is full (5)." : "Mix B is full (5).";
  }

  function applyMixLetter(playerId, side) {
    const current = occupyingSide(playerId);
    const nextA = mixA.filter((id) => id !== playerId);
    const nextB = mixB.filter((id) => id !== playerId);
    if (current === side) {
      mixA = nextA;
      mixB = nextB;
      mixReason = "";
      return;
    }
    const dest = side === "a" ? nextA : nextB;
    if (dest.length >= MAX_MIX) {
      mixReason = mixFullReason(side);
      return;
    }
    dest.push(playerId);
    mixA = side === "a" ? dest : nextA;
    mixB = side === "b" ? dest : nextB;
    mixReason = "";
  }

  function removeMixMember(playerId) {
    mixA = mixA.filter((id) => id !== playerId);
    mixB = mixB.filter((id) => id !== playerId);
    mixReason = "";
  }

  function moveMixMember(playerId, dest) {
    const current = occupyingSide(playerId);
    if (current == null || current === dest) return;
    applyMixLetter(playerId, dest);
  }

  function onMixClick(e) {
    const removeBtn = e.target.closest("[data-mix-remove]");
    if (removeBtn) {
      removeMixMember(Number(removeBtn.dataset.playerId));
      render();
      return;
    }
    const name = e.target.closest(".mix-item-name");
    if (!name) return;
    const item = name.closest("[data-player-id]");
    if (!item) return;
    const pid = Number(item.dataset.playerId);
    selectedPlayerId = selectedPlayerId === pid ? null : pid;
    render();
    if (selectedPlayerId == null) return;
    document.querySelector(`#explorer-table tr[data-player-id="${pid}"]`)?.scrollIntoView({
      block: "nearest",
    });
  }

  function onMixDragStart(e) {
    const name = e.target.closest(".mix-item-name");
    if (!name) {
      e.preventDefault();
      return;
    }
    const item = name.closest("[data-player-id]");
    if (!item) return;
    e.dataTransfer.setData("text/plain", item.dataset.playerId);
    e.dataTransfer.effectAllowed = "move";
  }

  function onMixDragOver(e) {
    if (!e.target.closest(".mix-column")) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
  }

  function onMixDrop(e) {
    const col = e.target.closest(".mix-column");
    if (!col) return;
    e.preventDefault();
    moveMixMember(Number(e.dataTransfer.getData("text/plain")), col.dataset.mixSide);
    render();
  }

  function mixBundle(ids) {
    const gws = viewGws();
    const selected = ids.map((id) => players().find((p) => p.id === id)).filter(Boolean);
    if (!selected.length) return null;
    const price = selected.reduce((sum, p) => sum + Number(p.price || 0), 0);
    const perGw = gws.map((gw) => selected.reduce((sum, p) => {
      const row = gwProjection(p, gw);
      return sum + Number(row.total_xp || 0);
    }, 0));
    return {
      names: selected.map((p) => p.name),
      price: round(price, 1),
      perGw: perGw.map((v) => round(v, 2)),
      total: round(perGw.reduce((a, b) => a + b, 0), 2),
    };
  }

  function renderMix() {
    const fill = (id, ids) => {
      const el = document.getElementById(id);
      if (!el) return;
      el.replaceChildren();
      ids.forEach((pid) => {
        const p = players().find((row) => row.id === pid);
        const li = document.createElement("li");
        li.className = "mix-item";
        li.dataset.playerId = String(pid);
        const name = document.createElement("span");
        name.className = "mix-item-name";
        name.draggable = true;
        name.textContent = p ? `${p.name} £${Number(p.price).toFixed(1)}m` : `#${pid}`;
        const remove = document.createElement("button");
        remove.type = "button";
        remove.className = "mix-remove";
        remove.setAttribute("data-mix-remove", "");
        remove.dataset.playerId = String(pid);
        remove.setAttribute("aria-label", "Remove Mix Member");
        remove.textContent = "×";
        li.append(name, remove);
        el.appendChild(li);
      });
    };
    fill("mix-a-list", mixA);
    fill("mix-b-list", mixB);
    const reasonEl = document.getElementById("mix-reason");
    if (reasonEl) reasonEl.textContent = mixReason;
    const compare = document.getElementById("mix-compare");
    if (!compare) return;
    if (!mixA.length && !mixB.length) {
      compare.textContent = "Add the same number of players to Mix A and Mix B (1–5).";
      return;
    }
    if (mixA.length !== mixB.length || mixA.length < 1) {
      compare.textContent = `Mix vs Mix needs the same size (currently ${mixA.length} vs ${mixB.length}).`;
      return;
    }
    const a = mixBundle(mixA);
    const b = mixBundle(mixB);
    const gws = viewGws();
    const gwLine = gws.map((gw, i) => `GW${gw} ${a.perGw[i].toFixed(2)} vs ${b.perGw[i].toFixed(2)}`).join(" · ");
    compare.textContent = `A ${a.names.join(" + ")} £${a.price.toFixed(1)}m total ${a.total.toFixed(2)}  vs  B ${b.names.join(" + ")} £${b.price.toFixed(1)}m total ${b.total.toFixed(2)}. ${gwLine}`;
  }

  function renderHead() {
    const row = document.getElementById("explorer-thead-row");
    if (!row) return;
    const gws = viewGws();
    row.innerHTML = [
      '<th data-sort="rank">#</th>',
      '<th data-sort="name">Player</th>',
      '<th data-sort="club">Club</th>',
      '<th data-sort="pos">Pos</th>',
      '<th data-sort="price">Price</th>',
      '<th data-sort="own">Own%</th>',
      '<th data-sort="total">Total</th>',
      ...gws.map((gw) => `<th data-sort="gw${gw}">GW${gw}</th>`),
      '<th data-sort="rate_per_90">/90</th>',
      '<th data-sort="avg_minutes">Avg mins</th>',
      '<th data-sort="role">Role</th>',
      "<th>Mix</th>",
    ].join("");
  }

  function renderTable(tableRows) {
    const body = document.getElementById("explorer-table");
    const gws = viewGws();
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
        const gwCells = gws.map((gw) => `<td>${Number(s.perGw[gw] || 0).toFixed(2)}</td>`).join("");
        const inA = mixA.includes(p.id);
        const inB = mixB.includes(p.id);
        return `<tr class="${selected}" data-player-id="${p.id}">
          <td>${row.rank}</td>
          <td>${p.name}</td>
          <td>${p.team}</td>
          <td>${POS_LABEL[p.pos] || p.pos}</td>
          <td>${Number(p.price).toFixed(1)}</td>
          <td>${Number(p.ownership_pct || 0).toFixed(1)}</td>
          <td>${Number(s.total).toFixed(2)}</td>
          ${gwCells}
          <td>${s.rate_per_90 == null ? "—" : Number(s.rate_per_90).toFixed(2)}</td>
          <td>${Number(s.avg_minutes).toFixed(1)}</td>
          <td>${p.expected_role || "—"}</td>
          <td>
            <button type="button" data-mix="a" data-player-id="${p.id}" class="${inA ? "mix-on" : ""}" aria-pressed="${inA}">A</button>
            <button type="button" data-mix="b" data-player-id="${p.id}" class="${inB ? "mix-on" : ""}" aria-pressed="${inB}">B</button>
          </td>
        </tr>`;
      })
      .join("");
  }

  function render() {
    if (!ctx) return;
    bindControls();
    setupClubAndPrice();
    renderHead();
    const { rows, visible, tableRows } = rankedRows();
    const gws = viewGws();
    const span = gws.length ? `GW${gws[0]}–GW${gws[gws.length - 1]}` : "—";
    document.getElementById("explorer-meta").textContent =
      `Planning Horizon ${span}${assume90 ? " · Assume 90" : ""} · chart ${visible.length} / table ${tableRows.length} / ${rows.length}`;
    renderCharts(visible);
    renderTable(tableRows);
    renderMix();
  }

  window.initOwnershipExplorer = function (context) {
    ctx = context;
    render();
  };

  window.renderOwnershipExplorer = render;
})();

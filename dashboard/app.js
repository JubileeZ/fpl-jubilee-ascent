function mountClubMultiSelect(root, { emptyLabel = "All clubs", onChange } = {}) {
  if (!root) return null;
  if (root._clubMulti) return root._clubMulti;
  root.classList.add("club-multi");
  const selected = new Set();
  const toggle = document.createElement("button");
  toggle.type = "button";
  toggle.className = "club-multi-toggle select-input";
  toggle.setAttribute("aria-haspopup", "listbox");
  const menu = document.createElement("div");
  menu.className = "club-multi-menu";
  menu.hidden = true;
  root.append(toggle, menu);

  function labelText() {
    if (selected.size === 0) return emptyLabel;
    return Array.from(selected).sort().join("-");
  }

  function syncToggle() {
    const text = labelText();
    toggle.textContent = text;
    toggle.title = text;
  }

  function setOpen(open) {
    menu.hidden = !open;
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
  }

  toggle.addEventListener("click", (event) => {
    event.stopPropagation();
    setOpen(menu.hidden);
  });
  menu.addEventListener("click", (event) => event.stopPropagation());
  document.addEventListener("click", (event) => {
    if (!root.contains(event.target)) setOpen(false);
  });

  function rebuild(clubs) {
    const keep = new Set(Array.from(selected).filter((club) => clubs.includes(club)));
    selected.clear();
    keep.forEach((club) => selected.add(club));
    menu.replaceChildren();
    const clearBtn = document.createElement("button");
    clearBtn.type = "button";
    clearBtn.className = "club-multi-clear";
    clearBtn.textContent = emptyLabel;
    clearBtn.addEventListener("click", () => {
      selected.clear();
      menu.querySelectorAll("input").forEach((input) => { input.checked = false; });
      syncToggle();
      if (onChange) onChange();
    });
    menu.appendChild(clearBtn);
    clubs.forEach((club) => {
      const label = document.createElement("label");
      const input = document.createElement("input");
      input.type = "checkbox";
      input.value = club;
      input.checked = selected.has(club);
      input.addEventListener("change", () => {
        if (input.checked) selected.add(club);
        else selected.delete(club);
        syncToggle();
        if (onChange) onChange();
      });
      label.append(input, document.createTextNode(` ${club}`));
      menu.appendChild(label);
    });
    syncToggle();
  }

  const api = {
    rebuild,
    allows(team) {
      return selected.size === 0 || selected.has(team);
    },
  };
  root._clubMulti = api;
  syncToggle();
  return api;
}

window.mountClubMultiSelect = mountClubMultiSelect;

document.addEventListener("DOMContentLoaded", () => {
  const SEASON_END_GW = 38;
  const MAX_HORIZON = 6;
  let allPlayers = [];
  let metaData = {};
  let primaryModel = "";
  let horizonBound = false;
  let modelBound = false;
  let refreshBound = false;

  function unfinishedGws() {
    const listed = metaData.unfinished_gameweeks;
    if (Array.isArray(listed) && listed.length) {
      return listed.map(Number).filter((gw) => gw >= 1 && gw <= SEASON_END_GW).sort((a, b) => a - b);
    }
    const finished = new Set((metaData.finished_gameweeks || []).map(Number));
    const ids = (metaData.gw_ids || []).map(Number);
    const fromIds = ids.filter((gw) => !finished.has(gw));
    return fromIds.length ? fromIds : [1];
  }

  function maxEndFor(start) {
    return Math.min(start + MAX_HORIZON - 1, SEASON_END_GW);
  }

  function viewGws() {
    const startSel = document.getElementById("horizonStart");
    const endSel = document.getElementById("horizonEnd");
    const start = Number(startSel && startSel.value);
    const end = Number(endSel && endSel.value);
    if (!Number.isFinite(start) || !Number.isFinite(end) || end < start) return [];
    const gws = [];
    for (let gw = start; gw <= end; gw += 1) gws.push(gw);
    return gws;
  }

  function fillStartOptions(preferred) {
    const startSel = document.getElementById("horizonStart");
    if (!startSel) return 1;
    const starts = unfinishedGws();
    const want = Number(preferred);
    const chosen = starts.includes(want) ? want : starts[0];
    startSel.replaceChildren();
    starts.forEach((gw) => {
      const opt = document.createElement("option");
      opt.value = String(gw);
      opt.textContent = `GW${gw}`;
      startSel.appendChild(opt);
    });
    startSel.value = String(chosen);
    return chosen;
  }

  function fillEndOptions(start, preferred) {
    const endSel = document.getElementById("horizonEnd");
    if (!endSel) return start;
    const maxE = maxEndFor(start);
    const want = Number(preferred);
    const chosen = Number.isFinite(want) && want >= start && want <= maxE ? want : Math.min(start + MAX_HORIZON - 1, maxE);
    endSel.replaceChildren();
    for (let gw = start; gw <= maxE; gw += 1) {
      const opt = document.createElement("option");
      opt.value = String(gw);
      opt.textContent = `GW${gw}`;
      endSel.appendChild(opt);
    }
    endSel.value = String(chosen);
    return chosen;
  }

  function rerenderExplorer() {
    if (window.renderOwnershipExplorer) window.renderOwnershipExplorer();
    if (window.Plotly) {
      ["chart-ownership", "chart-price"].forEach((id) => {
        const el = document.getElementById(id);
        if (el) window.Plotly.Plots.resize(el);
      });
    }
  }

  function setupHorizonSelects() {
    const startSel = document.getElementById("horizonStart");
    const endSel = document.getElementById("horizonEnd");
    if (!startSel || !endSel) return;
    const prevStart = Number(startSel.value);
    const prevEnd = Number(endSel.value);
    const start = fillStartOptions(prevStart || metaData.horizon_start || unfinishedGws()[0]);
    fillEndOptions(start, prevEnd || metaData.horizon_end || start + MAX_HORIZON - 1);
    if (horizonBound) return;
    horizonBound = true;
    startSel.addEventListener("change", () => {
      fillEndOptions(Number(startSel.value), Number(endSel.value));
      rerenderExplorer();
    });
    endSel.addEventListener("change", rerenderExplorer);
  }

  function setupModelSelect() {
    const select = document.getElementById("primaryModelSelect");
    if (!select) return;
    const models = metaData.models || [metaData.default_model || "default"];
    primaryModel = metaData.default_model || models[0];
    select.innerHTML = "";
    models.forEach((name) => {
      const opt = document.createElement("option");
      opt.value = name;
      opt.textContent = name === metaData.default_model ? `${name} (Champion)` : name;
      if (name === primaryModel) opt.selected = true;
      select.appendChild(opt);
    });
    if (modelBound) return;
    modelBound = true;
    select.addEventListener("change", () => {
      primaryModel = select.value;
      rerenderExplorer();
    });
  }

  function applyDataset(data) {
    metaData = (data && data.meta) || {};
    allPlayers = (data && data.players) || [];
    setupHorizonSelects();
    setupModelSelect();
    if (window.initOwnershipExplorer) {
      window.initOwnershipExplorer({
        getPlayers: () => allPlayers,
        getMeta: () => metaData,
        getPrimaryModel: () => primaryModel,
        getViewGws: viewGws,
      });
    }
  }

  function setRefreshStatus(text) {
    const el = document.getElementById("refresh-status");
    if (el) el.textContent = text;
  }

  async function loadDashboardJson() {
    const response = await fetch(`dashboard_data.json?t=${Date.now()}`);
    if (!response.ok) throw new Error("No dashboard_data.json yet. Click Refresh.");
    return response.json();
  }

  async function pollRefresh() {
    const response = await fetch("/api/refresh");
    if (!response.ok) throw new Error("Refresh status failed");
    return response.json();
  }

  async function waitForRefresh() {
    let idleTicks = 0;
    for (;;) {
      const state = await pollRefresh();
      if (state.detail) setRefreshStatus(state.detail);
      if (state.status === "running") {
        idleTicks = 0;
        await new Promise((resolve) => setTimeout(resolve, 1000));
        continue;
      }
      if (state.status === "ok") return state;
      if (state.status === "idle") {
        idleTicks += 1;
        if (idleTicks > 5) throw new Error("Refresh did not start");
        await new Promise((resolve) => setTimeout(resolve, 1000));
        continue;
      }
      const err = state.error || "Refresh failed";
      throw new Error(err);
    }
  }

  async function refreshDashboard() {
    const btn = document.getElementById("btn-refresh");
    if (btn) btn.disabled = true;
    setRefreshStatus("Starting Refresh…");
    try {
      const post = await fetch("/api/refresh", { method: "POST" });
      const body = await post.json();
      if (post.status >= 400 && body.status !== "running") {
        throw new Error(body.error || "Refresh failed to start");
      }
      await waitForRefresh();
      const data = await loadDashboardJson();
      applyDataset(data);
      setRefreshStatus("Charts updated.");
    } catch (err) {
      console.error(err);
      setRefreshStatus(err.message || String(err));
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  function setupRefresh() {
    const btn = document.getElementById("btn-refresh");
    if (!btn || refreshBound) return;
    refreshBound = true;
    btn.addEventListener("click", refreshDashboard);
  }

  async function init() {
    setupRefresh();
    try {
      const data = await loadDashboardJson();
      applyDataset(data);
      setRefreshStatus("");
    } catch (err) {
      console.error(err);
      applyDataset({ meta: {}, players: [] });
      setRefreshStatus(err.message || "Click Refresh to pull FPL data and project.");
    }
  }

  init();
});

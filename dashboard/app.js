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
  const DEFAULT_HORIZON = 6;
  const MAX_HORIZON = 10;
  let allPlayers = [];
  let metaData = {};
  let primaryModel = "";
  let horizonBound = false;
  let modelBound = false;
  let refreshBound = false;
  let dreamBound = false;
  let planBound = false;
  let tabsBound = false;
  let activeJobs = 0;

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

  function defaultEndFor(start) {
    return Math.min(start + DEFAULT_HORIZON - 1, maxEndFor(start));
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
    const chosen = Number.isFinite(want) && want >= start && want <= maxE ? want : defaultEndFor(start);
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
    if (window.clearDreamTeam) window.clearDreamTeam();
    if (window.renderSquadBoard) window.renderSquadBoard();
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
    fillEndOptions(start, prevEnd || metaData.horizon_end || defaultEndFor(start));
    if (horizonBound) return;
    horizonBound = true;
    startSel.addEventListener("change", () => {
      fillEndOptions(Number(startSel.value), Number(endSel.value));
      setRefreshStatus("");
      rerenderExplorer();
    });
    endSel.addEventListener("change", () => {
      setRefreshStatus("");
      rerenderExplorer();
    });
  }

  function catalogModels() {
    return Array.isArray(metaData.catalog_models) ? metaData.catalog_models : [];
  }

  function primaryPayload() {
    const catalog = catalogModels();
    if (!primaryModel) return "default";
    if (catalog.length && !catalog.includes(primaryModel)) return "default";
    return primaryModel;
  }

  function setupModelSelect() {
    const select = document.getElementById("primaryModelSelect");
    if (!select) return;
    const catalog = catalogModels();
    let models = (metaData.models && metaData.models.length)
      ? metaData.models.slice()
      : [metaData.default_model].filter(Boolean);
    if (catalog.length) {
      models = models.filter((name) => catalog.includes(name));
      const champion = (metaData.champion_trust && metaData.champion_trust.champion) || metaData.default_model;
      if (!models.length && champion && catalog.includes(champion)) models = [champion];
      if (!models.length) models = catalog.slice(0, 1);
    }
    primaryModel = models.includes(metaData.default_model)
      ? metaData.default_model
      : (models[0] || "");
    if (catalog.length && primaryModel && !catalog.includes(primaryModel)) {
      primaryModel = models[0] || "";
    }
    select.innerHTML = "";
    if (!models.length) {
      const opt = document.createElement("option");
      opt.value = "";
      opt.textContent = "Champion Model";
      select.appendChild(opt);
    }
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
      setRefreshStatus("");
      rerenderExplorer();
    });
  }

  function applyDataset(data) {
    metaData = (data && data.meta) || {};
    allPlayers = (data && data.players) || [];
    setupHorizonSelects();
    setupModelSelect();
    if (window.initSquadBoard) {
      window.initSquadBoard({
        getPlayers: () => allPlayers,
        getMeta: () => metaData,
        getPrimaryModel: () => primaryModel,
        getViewGws: viewGws,
      });
    }
    if (window.initOwnershipExplorer) {
      window.initOwnershipExplorer({
        getPlayers: () => allPlayers,
        getMeta: () => metaData,
        getPrimaryModel: () => primaryModel,
        getViewGws: viewGws,
      });
    }
    if (window.initTransferPlanSurface) {
      window.initTransferPlanSurface({
        getPlayers: () => allPlayers,
        getMeta: () => metaData,
        getPrimaryModel: () => primaryModel,
      });
    }
    renderChampionTrust();
  }

  function renderChampionTrust() {
    function fillTrust(el) {
      if (!el) return;
      const trust = metaData.champion_trust || {};
      if (!trust.champion) {
        el.textContent = "";
        return;
      }
      const parts = [`Champion Trust: ${trust.champion}`];
      if (trust.promotion_status === "provisional") {
        parts.push("provisional");
      }
      el.textContent = parts.join(" · ");
    }
    fillTrust(document.getElementById("champion-trust"));
    fillTrust(document.getElementById("plan-champion-trust"));
  }

  function setRefreshStatus(text) {
    const el = document.getElementById("refresh-status");
    if (el) el.textContent = text;
  }

  function setJobsBusy(busy) {
    const refreshBtn = document.getElementById("btn-refresh");
    const dreamBtn = document.getElementById("btn-dream-team");
    const planBtn = document.getElementById("btn-transfer-plan");
    const modelSelect = document.getElementById("primaryModelSelect");
    if (refreshBtn) refreshBtn.disabled = busy;
    if (dreamBtn) dreamBtn.disabled = busy;
    if (planBtn) planBtn.disabled = busy;
    if (modelSelect) modelSelect.disabled = busy;
  }

  function beginJob() {
    activeJobs += 1;
    setJobsBusy(true);
  }

  function endJob() {
    activeJobs = Math.max(0, activeJobs - 1);
    if (activeJobs === 0) setJobsBusy(false);
  }

  async function loadDashboardJson() {
    const response = await fetch(`dashboard_data.json?t=${Date.now()}`);
    if (!response.ok) throw new Error("No dashboard_data.json yet. Click Refresh.");
    return response.json();
  }

  window.reloadDashboardJson = async function () {
    const data = await loadDashboardJson();
    applyDataset(data);
  };

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
    if (btn && btn.disabled) return;
    beginJob();
    if (window.clearDreamTeam) window.clearDreamTeam();
    setRefreshStatus("Starting Refresh…");
    try {
      const post = await fetch("/api/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model: primaryPayload() }),
      });
      const body = await post.json();
      if (post.status >= 400 && body.status !== "running") {
        throw new Error(body.error || "Refresh failed to start");
      }
      await waitForRefresh();
      const data = await loadDashboardJson();
      applyDataset(data);
      const planLoad = await loadTransferPlanStatus();
      if (planLoad === "stale") {
        setRefreshStatus("Charts updated. Scenarios stale — Solve again.");
      } else if (planLoad !== "running") {
        setRefreshStatus("Charts updated.");
      }
    } catch (err) {
      console.error(err);
      setRefreshStatus(err.message || String(err));
    } finally {
      endJob();
    }
  }

  function setupRefresh() {
    const btn = document.getElementById("btn-refresh");
    if (!btn || refreshBound) return;
    refreshBound = true;
    btn.addEventListener("click", refreshDashboard);
  }

  async function pollDreamTeam() {
    const response = await fetch("/api/dream-team");
    if (!response.ok) throw new Error("Dream Team status failed");
    return response.json();
  }

  async function waitForDreamTeam() {
    let idleTicks = 0;
    for (;;) {
      const state = await pollDreamTeam();
      if (state.detail) setRefreshStatus(state.detail);
      if (state.status === "running") {
        idleTicks = 0;
        await new Promise((resolve) => setTimeout(resolve, 1000));
        continue;
      }
      if (state.status === "ok") return state;
      if (state.status === "idle") {
        idleTicks += 1;
        if (idleTicks > 5) throw new Error("Dream Team Solve did not start");
        await new Promise((resolve) => setTimeout(resolve, 1000));
        continue;
      }
      throw new Error(state.error || "Dream Team Solve failed");
    }
  }

  async function solveDreamTeam() {
    const btn = document.getElementById("btn-dream-team");
    if (btn && btn.disabled) return;
    beginJob();
    setRefreshStatus("Solving Dream Team…");
    try {
      const startSel = document.getElementById("horizonStart");
      const endSel = document.getElementById("horizonEnd");
      const post = await fetch("/api/dream-team", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: primaryPayload(),
          horizon_start: Number(startSel && startSel.value),
          horizon_end: Number(endSel && endSel.value),
        }),
      });
      const body = await post.json();
      if (post.status >= 400 && body.status !== "running") {
        throw new Error(body.error || "Dream Team Solve failed to start");
      }
      const state = await waitForDreamTeam();
      const ids = state.player_ids || [];
      if (window.setDreamTeamIds) window.setDreamTeamIds(ids);
      const leftover = state.leftover != null ? ` · leftover £${Number(state.leftover).toFixed(1)}m` : "";
      const budget = state.budget != null ? `£${Number(state.budget).toFixed(1)}m` : "";
      setRefreshStatus(`Dream Team ${ids.length} players · budget ${budget}${leftover}`);
    } catch (err) {
      console.error(err);
      setRefreshStatus(err.message || String(err));
    } finally {
      endJob();
    }
  }

  function setupDreamTeam() {
    const btn = document.getElementById("btn-dream-team");
    if (!btn || dreamBound) return;
    dreamBound = true;
    btn.addEventListener("click", solveDreamTeam);
  }

  function setView(view) {
    const root = document.querySelector(".app-container");
    if (root) root.setAttribute("data-view", view);
    const planRoot = document.getElementById("plan-root");
    if (planRoot) planRoot.hidden = view !== "plan";
    const explorerTab = document.getElementById("tab-explorer");
    const planTab = document.getElementById("tab-plan");
    if (explorerTab) explorerTab.classList.toggle("active", view === "explorer");
    if (planTab) planTab.classList.toggle("active", view === "plan");
    const subtitle = document.getElementById("view-subtitle");
    if (subtitle) subtitle.textContent = view === "plan" ? "Transfer Plan" : "Explorer";
    if (view === "explorer" && window.Plotly) {
      ["chart-ownership", "chart-price"].forEach((id) => {
        const el = document.getElementById(id);
        if (el) window.Plotly.Plots.resize(el);
      });
    }
  }

  function setupTabs() {
    if (tabsBound) return;
    tabsBound = true;
    document.getElementById("tab-explorer")?.addEventListener("click", () => setView("explorer"));
    document.getElementById("tab-plan")?.addEventListener("click", () => setView("plan"));
  }

  async function loadTransferPlanStatus() {
    try {
      const response = await fetch("/api/transfer-plan");
      if (!response.ok) return "idle";
      const state = await response.json();
      if (state.payload && window.setTransferPlanPayload) {
        window.setTransferPlanPayload(state.payload);
      }
      const metaRunning = state.payload && state.payload.meta && state.payload.meta.status === "running";
      if (state.status === "running" || metaRunning) {
        setRefreshStatus(state.detail || "Solving Transfer Plan Scenarios…");
        setView("plan");
        waitForTransferPlan()
          .then((done) => {
            if (window.setTransferPlanPayload) window.setTransferPlanPayload(done.payload);
            const n = (done.payload && done.payload.scenarios && done.payload.scenarios.length) || 0;
            setRefreshStatus(`Transfer Plan Scenarios ready · ${n} arms ranked by Σ Expected GW Score.`);
          })
          .catch((err) => {
            console.error(err);
            setRefreshStatus(err.message || String(err));
          });
        return "running";
      }
      if (state.payload && state.payload.meta && state.payload.meta.stale) {
        setRefreshStatus("Scenarios stale after Refresh — Solve again for current projections.");
        return "stale";
      }
      return "idle";
    } catch (err) {
      console.error(err);
      return "idle";
    }
  }

  async function pollTransferPlan() {
    const response = await fetch("/api/transfer-plan");
    if (!response.ok) throw new Error("Transfer Plan status failed");
    return response.json();
  }

  async function waitForTransferPlan() {
    let idleTicks = 0;
    for (;;) {
      const state = await pollTransferPlan();
      if (state.detail) setRefreshStatus(state.detail);
      if (state.payload && window.setTransferPlanPayload) {
        window.setTransferPlanPayload(state.payload);
      }
      if (state.status === "running") {
        idleTicks = 0;
        await new Promise((resolve) => setTimeout(resolve, 1000));
        continue;
      }
      if (state.status === "ok") return state;
      if (state.status === "idle") {
        idleTicks += 1;
        if (idleTicks > 5) throw new Error("Transfer Plan Solve did not start");
        await new Promise((resolve) => setTimeout(resolve, 1000));
        continue;
      }
      throw new Error(state.error || "Transfer Plan Solve failed");
    }
  }

  async function solveTransferPlan() {
    const btn = document.getElementById("btn-transfer-plan");
    if (btn && btn.disabled) return;
    beginJob();
    setRefreshStatus("Solving Transfer Plan Scenarios…");
    if (window.resetTransferPlanSelection) window.resetTransferPlanSelection();
    try {
      const body = window.transferPlanRequestBody ? window.transferPlanRequestBody() : { horizon: 6 };
      const post = await fetch("/api/transfer-plan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const payload = await post.json();
      if (post.status >= 400 && payload.status !== "running") {
        throw new Error(payload.error || "Transfer Plan Solve failed to start");
      }
      const state = await waitForTransferPlan();
      if (window.setTransferPlanPayload) window.setTransferPlanPayload(state.payload);
      const n = (state.payload && state.payload.scenarios && state.payload.scenarios.length) || 0;
      setRefreshStatus(`Transfer Plan Scenarios ready · ${n} arms ranked by Σ Expected GW Score.`);
      setView("plan");
    } catch (err) {
      console.error(err);
      setRefreshStatus(err.message || String(err));
    } finally {
      endJob();
    }
  }

  function setupTransferPlan() {
    const btn = document.getElementById("btn-transfer-plan");
    if (!btn || planBound) return;
    planBound = true;
    btn.addEventListener("click", solveTransferPlan);
  }

  async function init() {
    setupRefresh();
    setupDreamTeam();
    setupTransferPlan();
    setupTabs();
    try {
      const data = await loadDashboardJson();
      applyDataset(data);
      const planLoad = await loadTransferPlanStatus();
      if (planLoad === "idle") {
        setRefreshStatus("Projected from processed tables. Click Refresh to ingest live FPL.");
      }
    } catch (err) {
      console.error(err);
      applyDataset({ meta: {}, players: [] });
      setRefreshStatus(err.message || "Click Refresh to pull FPL data and project.");
    }
  }

  init();
});

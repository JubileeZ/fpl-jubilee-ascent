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
  let primaryPicked = false;
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
    if (!primaryModel || !primaryPicked) return "default";
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
      const championName = (metaData.champion_trust && metaData.champion_trust.champion) || metaData.default_model;
      opt.textContent = name === championName ? `${name} (Champion)` : name;
      if (name === primaryModel) opt.selected = true;
      select.appendChild(opt);
    });
    if (modelBound) return;
    modelBound = true;
    select.addEventListener("change", () => {
      primaryModel = select.value;
      primaryPicked = true;
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
    const sbChamp = document.getElementById("sidebar-champion");
    if (sbChamp && metaData.champion_trust && metaData.champion_trust.champion) {
      sbChamp.textContent = metaData.champion_trust.champion;
    }
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

  async function liveChampionMissing() {
    try {
      const response = await fetch("/api/champion");
      if (!response.ok) return null;
      const { champion } = await response.json();
      return champion && !(metaData.models || []).includes(champion) ? champion : null;
    } catch (err) {
      return null;
    }
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
    if (typeof window.setExplorerLoading === "function") window.setExplorerLoading(true);
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
        setRefreshStatus("Charts updated. Scenarios stale. Solve again.");
      } else if (planLoad !== "running") {
        setRefreshStatus("Charts updated.");
      }
    } catch (err) {
      console.error(err);
      setRefreshStatus(err.message || String(err));
      if (typeof window.setExplorerError === "function") {
        window.setExplorerError(err.message || String(err));
      }
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

  let strategyBound = false;
  let strategyControlsInitialized = false;
  let researchTopicsLoaded = false;
  let allResearchTopics = [];
  let methodologyLoaded = false;

  function setView(view) {
    const root = document.querySelector(".app-container");
    if (root) root.setAttribute("data-view", view);

    const planRoot = document.getElementById("plan-root");
    const strategyRoot = document.getElementById("strategy-root");
    const researchRoot = document.getElementById("research-root");
    const methodologyRoot = document.getElementById("methodology-root");

    if (planRoot) planRoot.hidden = view !== "plan";
    if (strategyRoot) strategyRoot.hidden = view !== "strategy";
    if (researchRoot) researchRoot.hidden = view !== "research";
    if (methodologyRoot) methodologyRoot.hidden = view !== "methodology";

    const views = ["explorer", "plan", "research", "methodology"];
    views.forEach((v) => {
      const tab = document.getElementById(`tab-${v}`);
      if (tab) tab.classList.toggle("active", view === v);
    });

    const titleEl = document.getElementById("view-title");
    const subtitle = document.getElementById("view-subtitle");

    const titles = {
      explorer: ["Explorer", "Player pool & What-If squad board"],
      plan: ["Decision Planner", "Multi-scenario decision graph & transfer tree"],
      research: ["Research Explorer", "Evidence notes, evaluation gates & companion data"],
      methodology: ["Model Methodology", "Projection pipeline layers & hypothesis generator"],
    };

    if (titles[view]) {
      if (titleEl) titleEl.textContent = titles[view][0];
      if (subtitle) subtitle.textContent = titles[view][1];
    }

    if (view === "explorer" && window.Plotly) {
      ["chart-ownership", "chart-price"].forEach((id) => {
        const el = document.getElementById(id);
        if (el) window.Plotly.Plots.resize(el);
      });
    }

    if (view === "research") loadResearchTopics();
    if (view === "methodology") loadMethodology();
  }

  function setupTabs() {
    if (tabsBound) return;
    tabsBound = true;
    document.getElementById("tab-explorer")?.addEventListener("click", () => setView("explorer"));
    document.getElementById("tab-plan")?.addEventListener("click", () => setView("plan"));
    document.getElementById("tab-research")?.addEventListener("click", () => setView("research"));
    document.getElementById("tab-methodology")?.addEventListener("click", () => setView("methodology"));

    const sidebar = document.getElementById("app-sidebar");
    const toggleBtn = document.getElementById("sidebar-toggle");
    if (sidebar && toggleBtn) {
      toggleBtn.addEventListener("click", () => {
        const isCollapsed = sidebar.classList.toggle("collapsed");
        toggleBtn.textContent = isCollapsed ? "▶" : "◀";
        toggleBtn.setAttribute("title", isCollapsed ? "Expand sidebar" : "Collapse sidebar");
        toggleBtn.setAttribute("aria-label", isCollapsed ? "Expand sidebar" : "Collapse sidebar");
      });
    }
  }

  function initStrategyControls() {
    if (strategyControlsInitialized) return;
    strategyControlsInitialized = true;

    const targetSel = document.getElementById("strategy-target-gw");
    if (targetSel) {
      targetSel.innerHTML = "";
      const unfin = unfinishedGws();
      unfin.forEach((gw) => {
        const opt = document.createElement("option");
        opt.value = gw;
        opt.textContent = `GW${gw}`;
        targetSel.appendChild(opt);
      });
    }

    const modelSel = document.getElementById("strategy-model");
    if (modelSel) {
      const catalog = metaData.models || [];
      const champ = (metaData.champion_trust && metaData.champion_trust.champion) || metaData.default_model;
      modelSel.innerHTML = `<option value="">${champ ? `${champ} (Champion)` : "Champion Model"}</option>`;
      catalog.forEach((m) => {
        if (m !== champ) {
          const opt = document.createElement("option");
          opt.value = m;
          opt.textContent = m;
          modelSel.appendChild(opt);
        }
      });
    }

    ["strategy-chip-wc", "strategy-chip-fh", "strategy-chip-bb", "strategy-chip-tc"].forEach((id) => {
      const sel = document.getElementById(id);
      if (sel) {
        sel.innerHTML = '<option value="">None</option>';
        const unfin = unfinishedGws().slice(0, 10);
        unfin.forEach((gw) => {
          const opt = document.createElement("option");
          opt.value = gw;
          opt.textContent = `GW${gw}`;
          sel.appendChild(opt);
        });
      }
    });

    const decaySlider = document.getElementById("strategy-decay");
    const decayVal = document.getElementById("strategy-decay-val");
    if (decaySlider && decayVal) {
      decaySlider.addEventListener("input", () => {
        decayVal.textContent = Number(decaySlider.value).toFixed(2);
      });
    }

    const btnSolve = document.getElementById("btn-strategy-solve");
    if (btnSolve && !strategyBound) {
      strategyBound = true;
      btnSolve.addEventListener("click", solveStrategy);
    }
  }

  async function pollStrategy() {
    const res = await fetch("/api/strategy-solve");
    if (!res.ok) throw new Error("Failed to check strategy solve status");
    return res.json();
  }

  async function waitForStrategy() {
    for (;;) {
      const state = await pollStrategy();
      const statusEl = document.getElementById("strategy-status");
      if (statusEl && state.detail) statusEl.textContent = state.detail;
      if (state.status === "running") {
        await new Promise((r) => setTimeout(r, 1000));
        continue;
      }
      if (state.status === "ok") return state;
      throw new Error(state.error || "Strategy Solve failed");
    }
  }

  async function solveStrategy() {
    const btn = document.getElementById("btn-strategy-solve");
    const statusEl = document.getElementById("strategy-status");
    if (btn) btn.disabled = true;
    if (statusEl) statusEl.textContent = "Submitting Strategy Solve…";

    try {
      const targetGw = Number(document.getElementById("strategy-target-gw")?.value || 1);
      const horizon = Number(document.getElementById("strategy-horizon")?.value || 5);
      const model = document.getElementById("strategy-model")?.value || "";
      const preseason = !!document.getElementById("strategy-preseason")?.checked;
      const locked = document.getElementById("strategy-locked")?.value?.trim() || "";
      const banned = document.getElementById("strategy-banned")?.value?.trim() || "";
      const maxDefs = Number(document.getElementById("strategy-max-defs")?.value || 3);
      const doubleDef = !!document.getElementById("strategy-double-def")?.checked;
      const opposing = document.getElementById("strategy-opposing")?.value || "none";
      const hitLimit = document.getElementById("strategy-hit-limit")?.value;
      const weeklyHitLimit = document.getElementById("strategy-weekly-hit-limit")?.value;
      const itbBuffer = Number(document.getElementById("strategy-itb-buffer")?.value || 0);
      const decayBase = Number(document.getElementById("strategy-decay")?.value || 0.85);
      const ftVal = Number(document.getElementById("strategy-ft-val")?.value || 1.5);
      const itbVal = Number(document.getElementById("strategy-itb-val")?.value || 0.08);
      const benchW1 = Number(document.getElementById("strategy-bench-w1")?.value || 0.21);
      const benchW2 = Number(document.getElementById("strategy-bench-w2")?.value || 0.06);

      const wc = document.getElementById("strategy-chip-wc")?.value;
      const fh = document.getElementById("strategy-chip-fh")?.value;
      const bb = document.getElementById("strategy-chip-bb")?.value;
      const tc = document.getElementById("strategy-chip-tc")?.value;

      const payload = {
        target_gw: targetGw,
        horizon: horizon,
        preseason: preseason,
        max_defenders_per_team: maxDefs,
        double_defense_pick: doubleDef,
        transfer_itb_buffer: itbBuffer,
        decay_base: decayBase,
        ft_value: ftVal,
        itb_value: itbVal,
        bench_weights: { 0: 0.03, 1: benchW1, 2: benchW2, 3: 0.002 },
      };

      if (model) payload.datasource = model;
      if (locked) payload.locked = locked;
      if (banned) payload.banned = banned;
      if (opposing === "hard") payload.no_opposing_play = true;
      if (opposing === "penalty") payload.no_opposing_play = "penalty";
      if (hitLimit !== "" && hitLimit != null) payload.hit_limit = Number(hitLimit);
      if (weeklyHitLimit !== "" && weeklyHitLimit != null) payload.weekly_hit_limit = Number(weeklyHitLimit);

      if (wc) payload.use_wc = Number(wc);
      if (fh) payload.use_fh = Number(fh);
      if (bb) payload.use_bb = Number(bb);
      if (tc) payload.use_tc = Number(tc);

      const res = await fetch("/api/strategy-solve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const body = await res.json();
      if (!res.ok) throw new Error(body.error || "Strategy Solve submission rejected");

      const done = await waitForStrategy();
      renderStrategyResult(done.payload);
      if (statusEl) statusEl.textContent = "Strategy Solve complete.";
    } catch (err) {
      console.error(err);
      if (statusEl) statusEl.textContent = err.message || String(err);
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  function renderStrategyResult(plan) {
    if (!plan || !plan.meta) return;
    const card = document.getElementById("strategy-results-card");
    if (!card) return;
    card.hidden = false;

    const objEl = document.getElementById("strategy-obj-val");
    const xpEl = document.getElementById("strategy-xp-val");
    const modEl = document.getElementById("strategy-model-val");

    if (objEl) objEl.textContent = Number(plan.meta.solver_objective || 0).toFixed(2);
    if (xpEl) xpEl.textContent = Number(plan.meta.total_xp || 0).toFixed(2);
    if (modEl) modEl.textContent = plan.meta.model_name || "-";

    const tbody = document.getElementById("strategy-ledger-body");
    if (tbody) {
      tbody.innerHTML = "";
      const playerMap = new Map((allPlayers || []).map((p) => [p.id, p.web_name || p.name]));
      (plan.weeks || []).forEach((w) => {
        const tr = document.createElement("tr");
        const inNames = (w.transfers_in || []).map((id) => playerMap.get(id) || id).join(", ") || "–";
        const outNames = (w.transfers_out || []).map((id) => playerMap.get(id) || id).join(", ") || "–";
        const chip = w.chips || "–";
        const itb = w.itb != null ? `£${(Number(w.itb) / 10).toFixed(1)}m` : "–";
        tr.innerHTML = `
          <td><strong>GW${w.gw}</strong></td>
          <td class="text-accent">+ ${inNames}</td>
          <td class="text-danger">- ${outNames}</td>
          <td>${w.hits || 0}</td>
          <td>${chip}</td>
          <td>${itb}</td>
          <td>${w.ft != null ? w.ft : "–"}</td>
        `;
        tbody.appendChild(tr);
      });
    }

    const weeksCont = document.getElementById("strategy-weeks-container");
    if (weeksCont) {
      weeksCont.innerHTML = "";
      const playerMap = new Map((allPlayers || []).map((p) => [p.id, p]));
      (plan.weeks || []).forEach((w) => {
        const gwCard = document.createElement("div");
        gwCard.className = "strategy-gw-card";
        const captPlayer = playerMap.get(w.captain_id);
        const vcPlayer = playerMap.get(w.vice_captain_id);
        const captName = captPlayer ? (captPlayer.web_name || captPlayer.name) : (w.captain_id || "–");
        const vcName = vcPlayer ? (vcPlayer.web_name || vcPlayer.name) : (w.vice_captain_id || "–");

        const lineupNames = (w.lineup_ids || []).map((id) => {
          const p = playerMap.get(id);
          const name = p ? (p.web_name || p.name) : id;
          if (id === w.captain_id) return `<strong>${name} (C)</strong>`;
          if (id === w.vice_captain_id) return `${name} (V)`;
          return name;
        }).join(" · ");

        const benchNames = (w.bench_ids || []).map((id) => {
          const p = playerMap.get(id);
          return p ? (p.web_name || p.name) : id;
        }).join(" · ");

        gwCard.innerHTML = `
          <div class="strategy-gw-head">
            <span>GW${w.gw}</span>
            <span class="text-accent">${w.chips ? `[${w.chips}]` : ""}</span>
          </div>
          <div><span class="meta-label">Captain:</span> ${captName} · <span class="meta-label">VC:</span> ${vcName}</div>
          <div><span class="meta-label">Starting XI:</span> <span class="plan-hint">${lineupNames}</span></div>
          <div><span class="meta-label">Bench:</span> <span class="plan-hint">${benchNames}</span></div>
        `;
        weeksCont.appendChild(gwCard);
      });
    }
  }

  async function loadResearchTopics() {
    if (researchTopicsLoaded) return;
    try {
      const res = await fetch("/api/research/topics");
      if (!res.ok) throw new Error("Failed to load research topics");
      const data = await res.json();
      allResearchTopics = data.topics || [];
      researchTopicsLoaded = true;
      renderResearchTopicsList(allResearchTopics);

      const searchInput = document.getElementById("research-search");
      if (searchInput) {
        searchInput.addEventListener("input", () => {
          const q = searchInput.value.toLowerCase().trim();
          const filtered = allResearchTopics.filter(
            (t) => t.title.toLowerCase().includes(q) || t.slug.toLowerCase().includes(q)
          );
          renderResearchTopicsList(filtered);
        });
      }

      if (allResearchTopics.length) {
        loadResearchTopic(allResearchTopics[0].slug);
      }
    } catch (err) {
      console.error(err);
    }
  }

  function renderResearchTopicsList(topics) {
    const list = document.getElementById("research-topics-list");
    if (!list) return;
    list.innerHTML = "";
    if (!topics.length) {
      list.innerHTML = '<p class="explorer-meta">No matching research topics.</p>';
      return;
    }
    topics.forEach((t) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "topic-card";
      btn.setAttribute("data-slug", t.slug);
      btn.innerHTML = `
        <div class="topic-card-title">${t.title}</div>
        <div class="topic-card-meta">
          <span>${t.status || "Active"}</span>
          <span>${t.csv_count ? `${t.csv_count} CSVs` : "Note"}</span>
        </div>
      `;
      btn.addEventListener("click", () => {
        document.querySelectorAll(".topic-card").forEach((c) => c.classList.remove("active"));
        btn.classList.add("active");
        loadResearchTopic(t.slug);
      });
      list.appendChild(btn);
    });
  }

  async function loadResearchTopic(slug) {
    try {
      const res = await fetch(`/api/research/topic?slug=${encodeURIComponent(slug)}`);
      if (!res.ok) throw new Error("Failed to load topic note");
      const data = await res.json();

      const titleEl = document.getElementById("research-detail-title");
      const metaEl = document.getElementById("research-detail-meta");
      const statusEl = document.getElementById("research-detail-status");
      const bodyEl = document.getElementById("research-note-body");

      if (titleEl) titleEl.textContent = (data.slug || "").replace(/-/g, " ").toUpperCase();
      if (metaEl) metaEl.textContent = `docs/research/${data.slug}/${data.filename}`;
      if (statusEl) {
        statusEl.hidden = false;
        statusEl.textContent = "Active";
      }

      const csvSec = document.getElementById("research-csv-section");
      const csvTabs = document.getElementById("research-csv-tabs");
      const comps = data.companions || {};
      const compKeys = Object.keys(comps);

      if (csvSec && csvTabs) {
        if (compKeys.length > 0) {
          csvSec.hidden = false;
          csvTabs.innerHTML = "";
          compKeys.forEach((key, idx) => {
            const tabBtn = document.createElement("button");
            tabBtn.type = "button";
            tabBtn.className = `csv-tab-btn ${idx === 0 ? "active" : ""}`;
            tabBtn.textContent = key;
            tabBtn.addEventListener("click", () => {
              csvTabs.querySelectorAll(".csv-tab-btn").forEach((b) => b.classList.remove("active"));
              tabBtn.classList.add("active");
              renderCompanionCsv(comps[key]);
            });
            csvTabs.appendChild(tabBtn);
          });
          renderCompanionCsv(comps[compKeys[0]]);
        } else {
          csvSec.hidden = true;
        }
      }

      if (bodyEl) {
        bodyEl.innerHTML = renderMarkdown(data.content || "");
      }
    } catch (err) {
      console.error(err);
    }
  }

  function renderCompanionCsv(csvData) {
    if (!csvData) return;
    const thead = document.getElementById("research-csv-head");
    const tbody = document.getElementById("research-csv-body");
    if (!thead || !tbody) return;

    thead.innerHTML = `<tr>${(csvData.columns || []).map((c) => `<th>${c}</th>`).join("")}</tr>`;
    tbody.innerHTML = (csvData.rows || [])
      .slice(0, 30)
      .map((row) => `<tr>${row.map((cell) => `<td>${cell}</td>`).join("")}</tr>`)
      .join("");
  }

  function renderMarkdown(md) {
    let html = md
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");

    html = html.replace(/```([\s\S]*?)```/g, (_, code) => `<pre><code>${code.trim()}</code></pre>`);
    html = html.replace(/^### (.*$)/gim, "<h3>$1</h3>");
    html = html.replace(/^## (.*$)/gim, "<h2>$1</h2>");
    html = html.replace(/^# (.*$)/gim, "<h1>$1</h1>");
    html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/\*(.*?)\*/g, "<em>$1</em>");
    html = html.replace(/^\- (.*$)/gim, "<li>$1</li>");
    html = html.replace(/(<li>.*<\/li>)/gim, "<ul>$1</ul>");
    html = html.replace(/\n\n+/g, "<br><br>");

    return html;
  }

  async function loadMethodology() {
    if (methodologyLoaded) return;
    try {
      const res = await fetch("/api/methodology");
      if (!res.ok) throw new Error("Failed to load methodology");
      const data = await res.json();
      methodologyLoaded = true;

      const champEl = document.getElementById("methodology-champion");
      const sbChamp = document.getElementById("sidebar-champion");
      if (champEl) champEl.textContent = data.champion || "-";
      if (sbChamp) sbChamp.textContent = data.champion || "-";

      const select = document.getElementById("methodology-player-select");
      if (select && allPlayers && allPlayers.length) {
        select.innerHTML = '<option value="">Select player to inspect…</option>';
        const sorted = [...allPlayers].sort((a, b) =>
          (a.web_name || a.name || "").localeCompare(b.web_name || b.name || "")
        );
        sorted.forEach((p) => {
          const opt = document.createElement("option");
          opt.value = p.id;
          opt.textContent = `${p.web_name || p.name} (${p.club || "-"} · £${((p.price || 0) / 10).toFixed(1)}m)`;
          select.appendChild(opt);
        });

        select.addEventListener("change", () => {
          const pid = Number(select.value);
          const p = allPlayers.find((x) => x.id === pid);
          renderPlayerMethodology(p);
        });

        if (sorted.length) {
          select.value = sorted[0].id;
          renderPlayerMethodology(sorted[0]);
        }
      }

      const btnIdea = document.getElementById("btn-generate-idea");
      if (btnIdea) {
        btnIdea.addEventListener("click", () => {
          const lever = document.getElementById("idea-lever")?.value || "MIN";
          const hypo = document.getElementById("idea-hypothesis")?.value?.trim() || "";
          const target = document.getElementById("idea-target")?.value?.trim() || "";
          const outWrap = document.getElementById("idea-output-wrap");
          const outText = document.getElementById("idea-output");

          if (!hypo) {
            alert("Please provide a hypothesis description.");
            return;
          }

          const prompt = [
            "/explore-candidate",
            `Lever Category: ${lever}`,
            `Hypothesis: ${hypo}`,
            `Evaluation Target: ${target || "formation_xi_regret under ADR 0054 on 2025-26 dev"}`,
            `Active Champion: ${data.champion || "def_xg_shrink_challenger"}`,
            "Protocol: Follow candidate ledger rules; reject dead levers before revisit_after date.",
          ].join("\n");

          if (outWrap) outWrap.hidden = false;
          if (outText) outText.value = prompt;
        });
      }
    } catch (err) {
      console.error(err);
    }
  }

  function renderPlayerMethodology(player) {
    const disp = document.getElementById("methodology-player-display");
    if (!disp || !player) {
      if (disp) disp.innerHTML = '<p class="explorer-meta">No player selected.</p>';
      return;
    }

    const projs = player.projections || {};
    const gwKeys = Object.keys(projs).sort((a, b) => {
      const na = Number(a.replace("gw", ""));
      const nb = Number(b.replace("gw", ""));
      return na - nb;
    });

    const rows = gwKeys.slice(0, 5).map((k) => {
      const gw = projs[k];
      return `
        <tr>
          <td><strong>${k.toUpperCase()}</strong></td>
          <td>${gw.fixture_label || "–"}</td>
          <td>${gw.xmins != null ? Number(gw.xmins).toFixed(0) : "–"}</td>
          <td>${gw.xp_goals != null ? Number(gw.xp_goals).toFixed(2) : "–"}</td>
          <td>${gw.xp_assists != null ? Number(gw.xp_assists).toFixed(2) : "–"}</td>
          <td>${gw.xp_clean_sheet != null ? Number(gw.xp_clean_sheet).toFixed(2) : "–"}</td>
          <td>${gw.xp_bonus != null ? Number(gw.xp_bonus).toFixed(2) : "–"}</td>
          <td><strong>${gw.total_xp != null ? Number(gw.total_xp).toFixed(2) : "–"}</strong></td>
        </tr>
      `;
    }).join("");

    disp.innerHTML = `
      <div style="margin-top: 0.75rem;">
        <p><strong>${player.web_name || player.name}</strong> · ${player.club || "-"} · ${player.pos || "-"} · £${((player.price || 0) / 10).toFixed(1)}m</p>
        <div class="explorer-table-wrap" style="margin-top: 0.5rem;">
          <table class="data-table">
            <thead>
              <tr>
                <th>GW</th>
                <th>Fixture</th>
                <th>xMins</th>
                <th>xG pts</th>
                <th>xA pts</th>
                <th>CS pts</th>
                <th>BPS pts</th>
                <th>Total xP</th>
              </tr>
            </thead>
            <tbody>
              ${rows}
            </tbody>
          </table>
        </div>
      </div>
    `;
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
        setRefreshStatus("Scenarios stale after Refresh. Solve again for current projections.");
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
      const missingChampion = await liveChampionMissing();
      if (missingChampion) {
        setRefreshStatus(`Champion is now ${missingChampion}. Click Refresh to project it.`);
      }
    } catch (err) {
      console.error(err);
      applyDataset({ meta: {}, players: [] });
      setRefreshStatus(err.message || "Click Refresh to pull FPL data and project.");
      if (typeof window.setExplorerError === "function") {
        window.setExplorerError(err.message || "Failed to load dashboard.json.");
      }
    }
  }

  init();
});

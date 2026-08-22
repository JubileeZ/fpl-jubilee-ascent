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
  let allPlayers = [];
  let metaData = {};
  let primaryModel = "";
  let dashboardData = null;

  function viewHorizon() {
    const sel = document.getElementById("horizonSelect");
    const n = Number(sel && sel.value);
    return Number.isFinite(n) && n >= 1 ? n : (metaData.horizon || 5);
  }

  function viewGws() {
    const gws = metaData.planning_gw_ids || [];
    return gws.slice(0, viewHorizon());
  }

  function setDashboardView(view) {
    const explorer = document.getElementById("explorer-root");
    const plan = document.getElementById("plan-root");
    const app = document.querySelector(".app-container");
    if (app) app.setAttribute("data-view", view);
    if (explorer) explorer.hidden = view !== "explorer";
    if (plan) plan.hidden = view !== "plan";
    document.getElementById("tab-explorer")?.classList.toggle("active", view === "explorer");
    document.getElementById("tab-plan")?.classList.toggle("active", view === "plan");
    if (view === "explorer" && window.renderOwnershipExplorer) {
      window.renderOwnershipExplorer();
      if (window.Plotly) {
        ["chart-ownership", "chart-price"].forEach((id) => {
          const el = document.getElementById(id);
          if (el) window.Plotly.Plots.resize(el);
        });
      }
    }
    if (view === "plan" && window.renderTransferPlan) window.renderTransferPlan();
  }

  function setupHorizonSelect() {
    const sel = document.getElementById("horizonSelect");
    if (!sel) return;
    const maxH = Math.min(5, (metaData.planning_gw_ids || []).length || 5);
    const current = Math.min(metaData.horizon || 5, maxH);
    sel.replaceChildren();
    for (let n = 1; n <= maxH; n += 1) {
      const opt = document.createElement("option");
      opt.value = String(n);
      const gws = (metaData.planning_gw_ids || []).slice(0, n);
      opt.textContent = gws.length ? `${n} · GW${gws[0]}–GW${gws[gws.length - 1]}` : String(n);
      sel.appendChild(opt);
    }
    sel.value = String(current);
    sel.addEventListener("change", () => {
      if (window.renderOwnershipExplorer) window.renderOwnershipExplorer();
      if (window.renderTransferPlan) window.renderTransferPlan(true);
    });
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
    select.addEventListener("change", () => {
      primaryModel = select.value;
      if (window.renderOwnershipExplorer) window.renderOwnershipExplorer();
    });
  }

  async function init() {
    try {
      const response = await fetch("dashboard_data.json");
      if (!response.ok) throw new Error("Failed to load dashboard_data.json");
      dashboardData = await response.json();
      metaData = dashboardData.meta || {};
      allPlayers = dashboardData.players || [];
      setupHorizonSelect();
      setupModelSelect();
      if (window.initOwnershipExplorer) {
        window.initOwnershipExplorer({
          getPlayers: () => allPlayers,
          getMeta: () => metaData,
          getPrimaryModel: () => primaryModel,
          getViewGws: viewGws,
        });
      }
      if (window.initTransferPlan) {
        window.initTransferPlan({
          getPlayers: () => allPlayers,
          getMeta: () => metaData,
          getPlan: () => dashboardData.transfer_plan,
          setPlan: (plan) => { dashboardData.transfer_plan = plan; },
          getViewHorizon: viewHorizon,
          getViewGws: viewGws,
        });
      }
      document.getElementById("tab-explorer")?.addEventListener("click", () => setDashboardView("explorer"));
      document.getElementById("tab-plan")?.addEventListener("click", () => setDashboardView("plan"));
      setDashboardView("plan");
    } catch (err) {
      console.error(err);
      const metaEl = document.getElementById("plan-meta");
      if (metaEl) metaEl.textContent = `Error loading dashboard data: ${err.message}`;
    }
  }

  init();
});

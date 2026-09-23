(function () {
  const POS_ORDER = ["G", "D", "M", "F"];
  const ARM_LABEL = { optimal: "Optimal", no_hit: "No Hit" };
  const CHIP_OPTION = { wc: "use_wc", bb: "use_bb", fh: "use_fh", tc: "use_tc" };
  const CHIP_LABEL = { wc: "Wildcard", bb: "Bench Boost", fh: "Free Hit", tc: "Triple Captain" };
  const STATUS_LABEL = { a: "Avail", d: "Doubt", i: "Inj", s: "Sus", u: "Unav", n: "n/a" };

  let ctx = null;
  let payload = null;
  let selectedId = null;
  let selectedGw = null;
  let bound = false;

  function players() {
    return ctx && ctx.getPlayers ? ctx.getPlayers() : [];
  }

  function meta() {
    return (ctx && ctx.getMeta && ctx.getMeta()) || {};
  }

  function byId(pid) {
    return players().find((p) => Number(p.id) === Number(pid)) || null;
  }

  function playerName(pid) {
    const p = byId(pid);
    return p ? p.name : `#${pid}`;
  }

  function planStart() {
    return Number(meta().transfer_plan_start || meta().horizon_start || 1);
  }

  function planHorizon() {
    const sel = document.getElementById("plan-horizon");
    const n = Number(sel && sel.value);
    return Number.isFinite(n) && n >= 1 ? n : 6;
  }

  function planGws() {
    const start = planStart();
    const len = planHorizon();
    const gws = [];
    for (let gw = start; gw < start + len && gw <= 38; gw += 1) gws.push(gw);
    return gws;
  }

  function availableChips() {
    const listed = meta().transfer_plan_available_chips || meta().available_chips || [];
    const gwSet = new Set(planGws());
    return listed
      .map((row) => ({
        chip: row.chip,
        chip_set: Number(row.chip_set),
        gws: (row.gws || []).map(Number).filter((gw) => gwSet.has(gw)),
      }))
      .filter((row) => row.gws.length);
  }

  function bookedChipsFromUi() {
    const chips = { use_wc: [], use_bb: [], use_fh: [], use_tc: [] };
    document.querySelectorAll("[data-booked-chip]").forEach((sel) => {
      const gw = Number(sel.value);
      const option = CHIP_OPTION[sel.dataset.bookedChip];
      if (option && Number.isFinite(gw) && gw > 0) chips[option].push(gw);
    });
    return chips;
  }

  function enabledChipsFromUi() {
    const bookedKeys = new Set();
    document.querySelectorAll("[data-booked-chip]").forEach((sel) => {
      if (sel.value) bookedKeys.add(`${sel.dataset.bookedChip}:${sel.dataset.chipSet}`);
    });
    const out = [];
    document.querySelectorAll("[data-enabled-chip]:checked").forEach((input) => {
      const chip = input.dataset.enabledChip;
      const chipSet = Number(input.dataset.chipSet);
      if (bookedKeys.has(`${chip}:${chipSet}`)) return;
      out.push({ chip, chip_set: chipSet });
    });
    return out;
  }

  function fillHorizonSelect() {
    const sel = document.getElementById("plan-horizon");
    if (!sel) return;
    const prev = Number(sel.value) || 6;
    sel.replaceChildren();
    const maxH = Number(meta().max_horizon || 10);
    for (let n = 1; n <= maxH; n += 1) {
      const opt = document.createElement("option");
      opt.value = String(n);
      opt.textContent = `${n} GW`;
      sel.appendChild(opt);
    }
    sel.value = String(Math.min(Math.max(prev, 1), maxH));
  }

  function availabilityText(player) {
    if (!player) return "";
    const status = STATUS_LABEL[player.status] || player.status || "";
    const chance = player.chance == null || player.chance === "" ? "" : `${player.chance}%`;
    const news = player.news || "";
    return [status, chance, news].filter(Boolean).join(" · ");
  }

  function fixtureText(player, gw) {
    const row = ((player && player.projections) || {})[`gw${gw}`] || {};
    return row.fixture_label || "";
  }

  function renderChipCalendar() {
    const bookedRoot = document.getElementById("booked-chips");
    const enabledRoot = document.getElementById("enabled-chips");
    if (!bookedRoot || !enabledRoot) return;
    const chips = availableChips();
    bookedRoot.replaceChildren();
    enabledRoot.replaceChildren();
    chips.forEach((row) => {
      const wrap = document.createElement("label");
      wrap.className = "plan-chip-week";
      wrap.append(`${CHIP_LABEL[row.chip] || row.chip} Set ${row.chip_set}`);
      const sel = document.createElement("select");
      sel.className = "select-input";
      sel.dataset.bookedChip = row.chip;
      sel.dataset.chipSet = String(row.chip_set);
      const none = document.createElement("option");
      none.value = "";
      none.textContent = "None";
      sel.appendChild(none);
      row.gws.forEach((gw) => {
        const opt = document.createElement("option");
        opt.value = String(gw);
        opt.textContent = `GW${gw}`;
        sel.appendChild(opt);
      });
      wrap.appendChild(sel);
      bookedRoot.appendChild(wrap);

      const enable = document.createElement("label");
      const input = document.createElement("input");
      input.type = "checkbox";
      input.dataset.enabledChip = row.chip;
      input.dataset.chipSet = String(row.chip_set);
      enable.append(input, ` ${CHIP_LABEL[row.chip] || row.chip} Set ${row.chip_set}`);
      enabledRoot.appendChild(enable);
    });
  }

  function selectedScenario() {
    const rows = (payload && payload.scenarios) || [];
    return rows.find((row) => row.id === selectedId) || rows[0] || null;
  }

  function startWeek(scenario) {
    const weeks = (scenario && scenario.plan && scenario.plan.weeks) || [];
    return weeks[0] || {};
  }

  function weekByGw(scenario, gw) {
    const weeks = (scenario && scenario.plan && scenario.plan.weeks) || [];
    return weeks.find((w) => Number(w.gw) === Number(gw)) || null;
  }

  function resolveSelectedGw(scenario) {
    const weeks = (scenario && scenario.plan && scenario.plan.weeks) || [];
    if (!weeks.length) return null;
    if (selectedGw != null && weeks.some((w) => Number(w.gw) === Number(selectedGw))) {
      return Number(selectedGw);
    }
    return Number(weeks[0].gw);
  }

  function objectiveNote(row) {
    const meta = row && row.plan && row.plan.meta;
    const note = meta && meta.solver_objective_note;
    return note ? String(note) : "";
  }

  function escapeHtml(text) {
    return text.replace(/[&<>"']/g, (ch) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      "\"": "&quot;",
      "'": "&#39;",
    }[ch]));
  }

  function renderScenarios() {
    const root = document.getElementById("plan-scenarios");
    const staleEl = document.getElementById("plan-stale-banner");
    if (staleEl) staleEl.hidden = !(payload && payload.meta && payload.meta.stale);
    if (!root) return;
    const rows = (payload && payload.scenarios) || [];
    const pending = (payload && payload.meta && payload.meta.pending_arms) || [];
    const running = payload && payload.meta && payload.meta.status === "running";
    if (!rows.length && !pending.length) {
      root.innerHTML = '<p class="explorer-meta">Refresh, then Solve scenarios (needs a User Squad).</p>';
      return;
    }
    if (!selectedId || !rows.some((row) => row.id === selectedId)) selectedId = rows[0] ? rows[0].id : null;
    const cards = rows.map((row) => {
      const week = startWeek(row);
      const rankLabel = running ? `Provisional ${row.rank}` : `Rank ${row.rank}`;
      const note = objectiveNote(row);
      const noteHtml = note ? `<div class="meta">${escapeHtml(note)}</div>` : "";
      return `<button type="button" class="scenario-card" data-id="${row.id}" aria-selected="${row.id === selectedId}">
          <div class="rank">${rankLabel}</div>
          <h3>${row.name}</h3>
          <div class="score">${Number(row.horizon_egs || 0).toFixed(1)}</div>
          <div class="meta">Σ Expected GW Score · Start Hits ${week.hits || 0}</div>
          ${noteHtml}
        </button>`;
    });
    pending.forEach((arm) => {
      const label = ARM_LABEL[arm] || arm;
      cards.push(`<div class="scenario-card" aria-busy="true">
          <div class="rank">Solving…</div>
          <h3>${label}</h3>
          <div class="score">—</div>
          <div class="meta">Arm in progress</div>
        </div>`);
    });
    root.innerHTML = cards.join("");
    root.querySelectorAll("[data-id]").forEach((el) => {
      el.addEventListener("click", () => {
        selectedId = el.getAttribute("data-id");
        selectedGw = null;
        root.querySelectorAll("[data-id]").forEach((btn) => {
          btn.setAttribute("aria-selected", btn.getAttribute("data-id") === selectedId ? "true" : "false");
        });
        renderDetail();
      });
    });
  }

  function renderDetail() {
    const scenario = selectedScenario();
    const ledger = document.getElementById("plan-ledger");
    const weeksEl = document.getElementById("plan-weeks");
    const pitch = document.getElementById("plan-pitch");
    const obj = document.getElementById("plan-objective");
    const noteEl = document.getElementById("plan-objective-note");
    const autoEl = document.getElementById("plan-auto-captain");
    const xiHead = document.getElementById("plan-xi-subhead");
    const stripHead = document.getElementById("plan-weeks-subhead");
    if (!scenario) {
      if (ledger) ledger.innerHTML = "";
      if (weeksEl) weeksEl.innerHTML = "";
      if (pitch) pitch.innerHTML = "";
      if (obj) obj.textContent = "—";
      if (noteEl) {
        noteEl.textContent = "";
        noteEl.hidden = true;
      }
      if (autoEl) autoEl.textContent = "Auto Captain · Auto Vice-Captain · Next-best (Plan Start)";
      if (xiHead) xiHead.textContent = "Plan XI · select a week (C = plan captain)";
      if (stripHead) stripHead.textContent = "Expected GW Score by week — click a GW to inspect";
      return;
    }
    const weeks = (scenario.plan && scenario.plan.weeks) || [];
    selectedGw = resolveSelectedGw(scenario);
    const week = weekByGw(scenario, selectedGw) || startWeek(scenario);
    const start = startWeek(scenario);
    const isStart = Number(week.gw) === Number(start.gw);
    const gwLabel = week.gw != null ? `GW${week.gw}` : "Start";
    const buys = (week.buy || []).map((row) => row.name || playerName(row.id));
    const sells = (week.sell || []).map((row) => row.name || playerName(row.id));
    if (ledger) {
      const buyHtml = buys.length ? buys.map((n) => `<span class="buy">+ ${n}</span>`).join(" ") : '<span class="buy">(none)</span>';
      const sellHtml = sells.length ? sells.map((n) => `<span class="sell">− ${n}</span>`).join(" ") : '<span class="sell">(none)</span>';
      ledger.innerHTML = `<div><strong>${gwLabel} buys</strong><br>${buyHtml}</div>
        <div><strong>${gwLabel} sells</strong><br>${sellHtml}</div>
        <div><strong>${gwLabel} Hits</strong><br>${week.hits || 0}</div>
        <div><strong>Σ Expected GW Score</strong><br>${Number(scenario.horizon_egs || 0).toFixed(1)}</div>`;
    }
    if (weeksEl) {
      weeksEl.innerHTML = weeks
        .map((w) => {
          const chip = w.chip ? ` · ${w.chip}` : "";
          const selected = Number(w.gw) === Number(selectedGw);
          return `<button type="button" class="week-cell" data-gw="${w.gw}" aria-selected="${selected ? "true" : "false"}"><strong>GW${w.gw}</strong>EGS ${Number(w.expected_gw_score || 0).toFixed(1)}<br>Hits ${w.hits || 0}${chip}</button>`;
        })
        .join("");
      weeksEl.querySelectorAll("[data-gw]").forEach((el) => {
        el.addEventListener("click", () => {
          selectedGw = Number(el.getAttribute("data-gw"));
          renderDetail();
        });
      });
    }
    if (stripHead) {
      stripHead.textContent = "Expected GW Score by week — click a GW to inspect (rank = sum)";
    }
    if (xiHead) {
      xiHead.textContent = `Plan XI · ${gwLabel}${isStart ? " · Plan Start" : ""} (C = plan captain)`;
    }
    if (obj) obj.textContent = scenario.solver_objective == null ? "—" : Number(scenario.solver_objective).toFixed(1);
    const note = objectiveNote(scenario);
    if (noteEl) {
      noteEl.textContent = note;
      noteEl.hidden = !note;
    }
    const auto = (scenario.plan && scenario.plan.auto_captain) || {};
    const next = (auto.next_best || [])
      .map((row) => `${playerName(row.id)} (${Number(row.xp || 0).toFixed(1)})`)
      .join(", ") || "—";
    const startGw = start.gw;
    const cap = auto.auto_captain_id ? `${playerName(auto.auto_captain_id)} (${xpOf(auto.auto_captain_id, startGw)})` : "—";
    const vice = auto.auto_vice_id ? `${playerName(auto.auto_vice_id)} (${xpOf(auto.auto_vice_id, startGw)})` : "—";
    if (autoEl) {
      autoEl.textContent = `Auto Captain ${cap} · Auto Vice-Captain ${vice} · Next-best ${next} (Plan Start GW${startGw})`;
    }
    if (pitch) pitch.innerHTML = pitchHtml(week);
  }

  function xpOf(pid, gw) {
    const p = byId(pid);
    const row = ((p && p.projections) || {})[`gw${gw}`] || {};
    return Number(row.total_xp || 0).toFixed(1);
  }

  function pitchHtml(week) {
    const gw = week.gw;
    const lineup = (week.lineup_ids || []).map((id) => byId(id)).filter(Boolean);
    const bench = (week.bench_ids || []).map((id) => byId(id)).filter(Boolean);
    const rows = POS_ORDER.map((pos) => {
      const subset = lineup.filter((p) => p.pos === pos);
      if (!subset.length) return "";
      return `<div class="row">${subset.map((p) => shirt(p, week, gw)).join("")}</div>`;
    }).join("");
    const benchRow = bench.length
      ? `<div class="row bench">${bench.map((p) => shirt(p, week, gw, true)).join("")}</div>`
      : "";
    return `${rows}${benchRow}`;
  }

  function shirt(player, week, gw, isBench) {
    const cap = Number(week.captain_id) === Number(player.id);
    const vice = Number(week.vice_id) === Number(player.id);
    const role = cap ? "C" : vice ? "VC" : "";
    const avail = availabilityText(player);
    const fixture = fixtureText(player, gw);
    return `<div class="shirt${cap ? " c" : ""}" title="${avail}">
      <strong>${player.name}${role ? ` (${role})` : ""}</strong>
      <span>${Number((((player.projections || {})[`gw${gw}`] || {}).total_xp) || 0).toFixed(1)}</span>
      <span>${fixture}</span>
      ${avail && !isBench ? `<span>${avail}</span>` : ""}
    </div>`;
  }

  function setPayload(next) {
    // Preserve selectedId / selectedGw across progressive poll updates so a finished
    // arm stays inspectable (week strip + XI) while other arms are still solving.
    payload = next && next.scenarios ? next : null;
    render();
  }

  function resetSelection() {
    selectedId = null;
    selectedGw = null;
    if (payload) render();
  }

  function render() {
    const startEl = document.getElementById("plan-start");
    if (startEl) startEl.textContent = `GW${planStart()}`;
    renderScenarios();
    renderDetail();
  }

  function bind() {
    if (bound) return;
    bound = true;
    document.getElementById("plan-horizon")?.addEventListener("change", () => {
      renderChipCalendar();
    });
  }

  window.initTransferPlanSurface = function (context) {
    ctx = context;
    bind();
    fillHorizonSelect();
    renderChipCalendar();
    render();
  };

  window.renderTransferPlanSurface = render;
  window.setTransferPlanPayload = setPayload;
  window.resetTransferPlanSelection = resetSelection;
  window.transferPlanRequestBody = function () {
    return {
      horizon: planHorizon(),
      booked_chips: bookedChipsFromUi(),
      enabled_chips: enabledChipsFromUi(),
    };
  };
})();

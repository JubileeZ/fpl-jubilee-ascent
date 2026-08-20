(function () {
  const CHIP_OPTIONS = ["", "WC", "BB", "FH", "TC"];
  const CHIP_TO_KEY = { WC: "use_wc", BB: "use_bb", FH: "use_fh", TC: "use_tc" };
  const KEY_TO_CHIP = { use_wc: "WC", use_bb: "BB", use_fh: "FH", use_tc: "TC" };

  let ctx = null;
  let selectedGw = null;
  let bound = false;
  let calendarDirty = false;

  function playersMap() {
    const map = new Map();
    (ctx && ctx.getPlayers ? ctx.getPlayers() : []).forEach((p) => map.set(p.id, p));
    return map;
  }

  function meta() {
    return (ctx && ctx.getMeta && ctx.getMeta()) || {};
  }

  function plan() {
    return (ctx && ctx.getPlan && ctx.getPlan()) || null;
  }

  function horizonGws() {
    const current = plan();
    if (current && current.weeks && current.weeks.length) {
      return current.weeks.map((w) => w.gw);
    }
    const start = intOr(meta().target_gw, 1);
    const horizon = intOr(meta().horizon, 6);
    const out = [];
    for (let gw = start; gw < start + horizon && gw <= 38; gw += 1) out.push(gw);
    return out;
  }

  function intOr(value, fallback) {
    const n = Number(value);
    return Number.isFinite(n) ? n : fallback;
  }

  function bindOnce() {
    if (bound) return;
    bound = true;
    document.getElementById("plan-gw-select")?.addEventListener("change", (event) => {
      selectedGw = Number(event.target.value);
      renderLedgerAndPitch();
    });
    document.getElementById("btn-re-solve")?.addEventListener("click", reSolve);
  }

  function bookedFromCalendar() {
    const booked = { use_wc: [], use_bb: [], use_fh: [], use_tc: [] };
    document.querySelectorAll(".plan-chip-week select").forEach((sel) => {
      const gw = Number(sel.dataset.gw);
      const key = CHIP_TO_KEY[sel.value];
      if (key) booked[key].push(gw);
    });
    return booked;
  }

  function renderCalendar(force) {
    const root = document.getElementById("plan-chip-calendar");
    if (!root) return;
    if (!force && calendarDirty && root.childElementCount) return;
    const booked = (plan() && plan().meta && plan().meta.booked_chips) || {};
    const byGw = {};
    Object.entries(KEY_TO_CHIP).forEach(([key, chip]) => {
      (booked[key] || []).forEach((gw) => { byGw[gw] = chip; });
    });
    root.replaceChildren();
    horizonGws().forEach((gw) => {
      const wrap = document.createElement("label");
      wrap.className = "plan-chip-week";
      wrap.append(`GW${gw}`);
      const sel = document.createElement("select");
      sel.className = "select-input";
      sel.dataset.gw = String(gw);
      CHIP_OPTIONS.forEach((chip) => {
        const opt = document.createElement("option");
        opt.value = chip;
        opt.textContent = chip || "None";
        sel.appendChild(opt);
      });
      sel.value = byGw[gw] || "";
      sel.addEventListener("change", () => { calendarDirty = true; });
      wrap.appendChild(sel);
      root.appendChild(wrap);
    });
  }

  function weekFor(gw) {
    const current = plan();
    if (!current || !current.weeks) return null;
    return current.weeks.find((w) => w.gw === gw) || null;
  }

  function renderHeader() {
    const current = plan();
    const metaEl = document.getElementById("plan-meta");
    const objEl = document.getElementById("plan-objective");
    const xpEl = document.getElementById("plan-xp");
    const m = current && current.meta;
    if (metaEl) {
      if (!m) {
        metaEl.textContent = "No Transfer Plan yet. Book chips and Re-solve (Model Champion, Official Fixture Difficulty, Planning Horizon 6).";
      } else {
        metaEl.textContent = `Champion ${m.champion} · Official Fixture Difficulty · Planning Horizon ${m.horizon} from GW${m.next_gw} · decay ${m.decay_base}`;
      }
    }
    if (objEl) objEl.textContent = m && m.solver_objective != null ? Number(m.solver_objective).toFixed(2) : "—";
    if (xpEl) xpEl.textContent = m && m.total_xp != null ? Number(m.total_xp).toFixed(2) : "—";
  }

  function renderGwSelect() {
    const sel = document.getElementById("plan-gw-select");
    if (!sel) return;
    const gws = horizonGws();
    if (!gws.length) {
      sel.replaceChildren();
      return;
    }
    if (!gws.includes(selectedGw)) selectedGw = gws[0];
    sel.replaceChildren();
    gws.forEach((gw) => {
      const opt = document.createElement("option");
      opt.value = String(gw);
      opt.textContent = `GW ${gw}`;
      sel.appendChild(opt);
    });
    sel.value = String(selectedGw);
  }

  function names(moves) {
    if (!moves || !moves.length) return "—";
    return moves.map((m) => m.name || `#${m.id}`).join(", ");
  }

  function xiNames(week) {
    const map = playersMap();
    const ids = (week && week.lineup_ids) || [];
    if (!ids.length) return "—";
    return ids.map((id) => (map.get(id) && map.get(id).name) || `#${id}`).join(", ");
  }

  function renderLedgerAndPitch() {
    const week = weekFor(selectedGw);
    const ledger = document.getElementById("plan-ledger");
    if (ledger) {
      if (!week) {
        ledger.textContent = "No week in this Transfer Plan. Re-solve to generate one.";
      } else {
        ledger.innerHTML = `
          <div>Chip: <strong>${week.chip || "None"}</strong></div>
          <div>FT ${week.ft ?? "—"} · Hits ${week.hits ?? "—"} · Transfers ${week.transfer_count ?? "—"} · ITB ${week.itb ?? "—"}</div>
          <div>xP (undiscounted): <strong>${week.xp != null ? Number(week.xp).toFixed(2) : "—"}</strong></div>
          <div>Week total (pre-decay): <strong>${week.objective != null ? Number(week.objective).toFixed(2) : "—"}</strong></div>
          <div class="buy">Buy: ${names(week.buy)}</div>
          <div class="sell">Sell: ${names(week.sell)}</div>
          <div>XI: ${xiNames(week)}</div>
        `;
      }
    }
    renderPitch(week);
  }

  function cardHtml(player, captainId, viceId) {
    if (!player) return `<div class="player-card empty-slot"><span class="slot-label">Empty</span></div>`;
    const cap = player.id === captainId ? '<span class="role-badge active-c">C</span>' : "";
    const vc = player.id === viceId ? '<span class="role-badge active-vc">VC</span>' : "";
    return `<div class="player-card">
      <div class="card-header-bar"><span class="pos-tag ${player.pos}">${player.pos}</span></div>
      <div class="card-name">${player.name}</div>
      <div class="card-team-price">${player.team} · £${player.price}m</div>
      <div class="card-role-btns">${cap}${vc}</div>
    </div>`;
  }

  function renderPitch(week) {
    const map = playersMap();
    const lineup = (week && week.lineup_ids) || [];
    const bench = (week && week.bench_ids) || [];
    const captainId = week && week.captain_id;
    const viceId = week && week.vice_id;
    const byPos = { G: [], D: [], M: [], F: [] };
    lineup.forEach((id) => {
      const p = map.get(id);
      if (p && byPos[p.pos]) byPos[p.pos].push(p);
    });
    const setRow = (id, players) => {
      const row = document.getElementById(id);
      if (!row) return;
      row.innerHTML = players.length
        ? players.map((p) => cardHtml(p, captainId, viceId)).join("")
        : `<div class="empty-slot">Empty</div>`;
    };
    setRow("planRowGk", byPos.G);
    setRow("planRowDef", byPos.D);
    setRow("planRowMid", byPos.M);
    setRow("planRowFwd", byPos.F);
    const benchEl = document.getElementById("planBench");
    if (benchEl) {
      const benchPlayers = bench.map((id) => map.get(id)).filter(Boolean);
      benchEl.innerHTML = benchPlayers.length
        ? benchPlayers.map((p) => cardHtml(p, captainId, viceId)).join("")
        : `<div class="empty-slot">Empty</div>`;
    }
  }

  async function reSolve() {
    const status = document.getElementById("plan-status");
    const btn = document.getElementById("btn-re-solve");
    if (status) status.textContent = "Solving Transfer Plan… this can take a while.";
    if (btn) btn.disabled = true;
    try {
      const payload = {
        ...bookedFromCalendar(),
        horizon: intOr(meta().horizon, 6),
        target_gw: intOr(meta().target_gw, 1),
      };
      const response = await fetch("/api/transfer-plan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.error || `Re-solve failed (${response.status})`);
      if (ctx && ctx.setPlan) ctx.setPlan(body);
      calendarDirty = false;
      if (status) status.textContent = "Transfer Plan updated.";
      render(true);
    } catch (err) {
      if (status) status.textContent = err.message || String(err);
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  function render(forceCalendar) {
    bindOnce();
    renderHeader();
    renderCalendar(Boolean(forceCalendar));
    renderGwSelect();
    renderLedgerAndPitch();
  }

  window.initTransferPlan = async function (context) {
    ctx = context;
    try {
      const response = await fetch("/api/transfer-plan");
      if (response.ok) {
        const body = await response.json();
        if (body && body.weeks && ctx.setPlan) ctx.setPlan(body);
      }
    } catch (_err) {
      /* keep export snapshot */
    }
    calendarDirty = false;
    render(true);
  };

  window.renderTransferPlan = render;
})();

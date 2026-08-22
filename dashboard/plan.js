(function () {
  const CHIP_OPTIONS = ["", "WC", "BB", "FH", "TC"];
  const CHIP_TO_KEY = { WC: "use_wc", BB: "use_bb", FH: "use_fh", TC: "use_tc" };
  const KEY_TO_CHIP = { use_wc: "WC", use_bb: "BB", use_fh: "FH", use_tc: "TC" };
  const CHIP_LABEL = { wc: "WC", bb: "BB", fh: "FH", tc: "TC" };

  let ctx = null;
  let selectedGw = null;
  let bound = false;
  let calendarDirty = false;
  let forceKeep = [];
  let forceBan = [];

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
    if (ctx && ctx.getViewGws) return ctx.getViewGws();
    const current = plan();
    if (current && current.weeks && current.weeks.length) {
      return current.weeks.map((w) => w.gw);
    }
    return meta().planning_gw_ids || [];
  }

  function intOr(value, fallback) {
    const n = Number(value);
    return Number.isFinite(n) ? n : fallback;
  }

  function chipSet(gw) {
    return gw <= 19 ? 1 : 2;
  }

  function availableForGw(gw) {
    const setId = chipSet(gw);
    return (meta().available_chips || []).filter((c) => c.chip_set === setId);
  }

  function bindOnce() {
    if (bound) return;
    bound = true;
    document.getElementById("plan-gw-select")?.addEventListener("change", (event) => {
      selectedGw = Number(event.target.value);
      renderLedgerAndPitch();
      renderOverrides();
    });
    document.getElementById("btn-re-solve")?.addEventListener("click", reSolve);
    document.getElementById("btn-force-keep")?.addEventListener("click", () => addOverride("keep"));
    document.getElementById("btn-force-ban")?.addEventListener("click", () => addOverride("ban"));
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

  function enabledFromChecks() {
    return Array.from(document.querySelectorAll("#plan-enabled-chips input:checked")).map((el) => ({
      chip: el.dataset.chip,
      chip_set: Number(el.dataset.chipSet),
    }));
  }

  function renderEnabledChips() {
    const root = document.getElementById("plan-enabled-chips");
    if (!root) return;
    if (root.dataset.built === "1") return;
    const chips = meta().available_chips || [];
    root.replaceChildren();
    root.dataset.built = "1";
    if (!chips.length) {
      root.textContent = "No Available Chips in this Planning Horizon.";
      return;
    }
    chips.forEach((chip) => {
      const lab = document.createElement("label");
      const input = document.createElement("input");
      input.type = "checkbox";
      input.dataset.chip = chip.chip;
      input.dataset.chipSet = String(chip.chip_set);
      lab.append(input, ` ${CHIP_LABEL[chip.chip] || chip.chip} (Set ${chip.chip_set})`);
      root.appendChild(lab);
    });
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
      const allowed = new Set(availableForGw(gw).map((c) => CHIP_LABEL[c.chip]));
      CHIP_OPTIONS.forEach((chip) => {
        if (chip && !allowed.has(chip)) return;
        const opt = document.createElement("option");
        opt.value = chip;
        opt.textContent = chip || "None";
        sel.appendChild(opt);
      });
      const current = byGw[gw] || "";
      sel.value = allowed.has(current) || current === "" ? current : "";
      sel.addEventListener("change", () => { calendarDirty = true; });
      wrap.appendChild(sel);
      root.appendChild(wrap);
    });
  }

  function playerByName(query) {
    const needle = (query || "").trim().toLowerCase();
    if (!needle) return null;
    const players = ctx && ctx.getPlayers ? ctx.getPlayers() : [];
    return players.find((p) => p.name.toLowerCase() === needle)
      || players.find((p) => p.name.toLowerCase().includes(needle));
  }

  function addOverride(kind) {
    const input = document.getElementById("override-search");
    const player = playerByName(input && input.value);
    const gw = selectedGw || horizonGws()[0];
    if (!player || !gw) return;
    const target = kind === "keep" ? forceKeep : forceBan;
    const other = kind === "keep" ? forceBan : forceKeep;
    if (target.some((row) => row.player_id === player.id && row.gw === gw)) return;
    const idx = other.findIndex((row) => row.player_id === player.id && row.gw === gw);
    if (idx >= 0) other.splice(idx, 1);
    target.push({ player_id: player.id, gw, name: player.name });
    if (input) input.value = "";
    renderOverrides();
  }

  function renderOverrides() {
    const list = document.getElementById("override-list");
    const data = document.getElementById("override-players");
    if (data) {
      data.replaceChildren();
      (ctx && ctx.getPlayers ? ctx.getPlayers() : []).forEach((p) => {
        const opt = document.createElement("option");
        opt.value = p.name;
        data.appendChild(opt);
      });
    }
    if (!list) return;
    list.replaceChildren();
    const rows = [
      ...forceKeep.map((row) => ({ ...row, kind: "Keep" })),
      ...forceBan.map((row) => ({ ...row, kind: "Ban" })),
    ].sort((a, b) => a.gw - b.gw || a.name.localeCompare(b.name));
    rows.forEach((row) => {
      const li = document.createElement("li");
      li.textContent = `${row.kind} ${row.name} · GW${row.gw} `;
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "btn btn-danger";
      btn.textContent = "×";
      btn.addEventListener("click", () => {
        forceKeep = forceKeep.filter((item) => !(item.player_id === row.player_id && item.gw === row.gw && row.kind === "Keep"));
        forceBan = forceBan.filter((item) => !(item.player_id === row.player_id && item.gw === row.gw && row.kind === "Ban"));
        renderOverrides();
      });
      li.appendChild(btn);
      list.appendChild(li);
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
    const gws = horizonGws();
    const span = gws.length ? `GW${gws[0]}–GW${gws[gws.length - 1]}` : "";
    if (metaEl) {
      if (!m) {
        metaEl.textContent = `No Transfer Plan yet. Book or Enable chips, Force Keep/Ban, then Re-solve (Model Champion, Official Fixture Difficulty, ${span}).`;
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

  function fallbackSquadWeek() {
    const m = meta();
    const ids = m.owned_squad_ids || [];
    if (!ids.length) return null;
    return {
      squad_ids: ids,
      lineup_ids: ids.slice(0, 11),
      bench_ids: ids.slice(11),
      captain_id: m.owned_captain_id,
      vice_id: m.owned_vice_captain_id,
    };
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
    renderPitch(week || fallbackSquadWeek());
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
        enabled_chips: enabledFromChecks(),
        force_keep: forceKeep.map((row) => ({ player_id: row.player_id, gw: row.gw })),
        force_ban: forceBan.map((row) => ({ player_id: row.player_id, gw: row.gw })),
        horizon: ctx && ctx.getViewHorizon ? ctx.getViewHorizon() : intOr(meta().horizon, 5),
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
    renderEnabledChips();
    renderCalendar(Boolean(forceCalendar));
    renderGwSelect();
    renderLedgerAndPitch();
    renderOverrides();
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

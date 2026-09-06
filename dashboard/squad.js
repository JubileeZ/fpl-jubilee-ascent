(function () {
  const POS_ORDER = ["G", "D", "M", "F"];
  const POS_LABEL = { G: "GKP", D: "DEF", M: "MID", F: "FWD" };
  const XI_MAX = 11;
  const CLUB_CAP = 3;
  const SHAPE = { G: [1, 1], D: [3, 5], M: [2, 5], F: [1, 3] };
  const PROFILE_KEYS = [
    ["xp_minutes", "Minutes"],
    ["xp_goals", "Goals"],
    ["xp_assists", "Assists"],
    ["xp_clean_sheet", "Clean sheets"],
    ["xp_conceded", "Conceded"],
    ["xp_defcon", "Defcon"],
    ["xp_saves", "Saves"],
    ["xp_bonus", "Bonus"],
  ];
  const BREACH_LABEL = {
    club_cap: "Club cap (max 3)",
    itb: "ITB below £0.0m",
    starting_shape: "Illegal Starting Shape",
  };

  let ctx = null;
  let whatIf = [];
  let dropReason = "";
  let bound = false;

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

  function byId(pid) {
    return players().find((p) => p.id === pid) || null;
  }

  function playerProj(player) {
    const modelName = ctx && ctx.getPrimaryModel ? ctx.getPrimaryModel() : "";
    const modelData = (player && player.models && player.models[modelName]) || player;
    return (modelData && modelData.projections) || (player && player.projections) || {};
  }

  function gwRow(player, gw) {
    return playerProj(player)[`gw${gw}`] || {};
  }

  function xminXp(player, gw) {
    return Number(gwRow(player, gw).total_xp || 0);
  }

  function round(value, digits) {
    const f = 10 ** digits;
    return Math.round(Number(value) * f) / f;
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
      xp_goals: scaled("xp_goals"),
      xp_assists: scaled("xp_assists"),
      xp_clean_sheet: scaled("xp_clean_sheet"),
      xp_conceded: scaled("xp_conceded"),
      xp_defcon: scaled("xp_defcon"),
      xp_saves: scaled("xp_saves"),
      xp_bonus: scaled("xp_bonus"),
    };
  }

  function ownedState() {
    const ids = meta().owned_squad_ids || [];
    return ids.map((id, i) => {
      const p = byId(id);
      const lineup = p && p.lineup_index != null ? Number(p.lineup_index) : i + 1;
      return { id: Number(id), lineup_index: lineup };
    });
  }

  function xiOf(state) {
    return state.filter((s) => s.lineup_index >= 1 && s.lineup_index <= XI_MAX);
  }

  function autoCaptain(state, gw) {
    const xi = xiOf(state)
      .map((s) => ({ ...s, player: byId(s.id), xp: xminXp(byId(s.id) || {}, gw) }))
      .filter((s) => s.player);
    if (!xi.length) return null;
    xi.sort((a, b) => b.xp - a.xp || a.lineup_index - b.lineup_index);
    return xi[0];
  }

  function autoVice(state, gw) {
    const cap = autoCaptain(state, gw);
    const xi = xiOf(state)
      .map((s) => ({ ...s, player: byId(s.id), xp: xminXp(byId(s.id) || {}, gw) }))
      .filter((s) => s.player && (!cap || s.id !== cap.id));
    if (!xi.length) return null;
    xi.sort((a, b) => b.xp - a.xp || a.lineup_index - b.lineup_index);
    return xi[0];
  }

  function squadXp(state, gw) {
    const total = state.reduce((sum, s) => sum + xminXp(byId(s.id) || {}, gw), 0);
    const cap = autoCaptain(state, gw);
    const extra = cap ? cap.xp : 0;
    return Math.round((total + extra) * 100) / 100;
  }

  function itbAfter(state) {
    const base = Number(meta().itb || 0);
    const ownedIds = new Set((meta().owned_squad_ids || []).map(Number));
    const nextIds = new Set(state.map((s) => s.id));
    let itb = base;
    ownedIds.forEach((id) => {
      if (!nextIds.has(id)) {
        const p = byId(id);
        itb += Number((p && p.selling_price != null) ? p.selling_price : 0);
      }
    });
    nextIds.forEach((id) => {
      if (!ownedIds.has(id)) {
        const p = byId(id);
        itb -= Number((p && p.price) || 0);
      }
    });
    return Math.round(itb * 10) / 10;
  }

  function transferCount(state) {
    const owned = new Set((meta().owned_squad_ids || []).map(Number));
    return state.filter((s) => !owned.has(s.id)).length;
  }

  function hits(state) {
    const ft = Number(meta().free_transfers || 0);
    return Math.max(0, transferCount(state) - ft);
  }

  function ruleBreaches(state, itb) {
    const breaches = [];
    const clubs = {};
    state.forEach((s) => {
      const p = byId(s.id);
      const club = p ? p.team_id : 0;
      clubs[club] = (clubs[club] || 0) + 1;
    });
    if (Object.values(clubs).some((n) => n > CLUB_CAP)) breaches.push("club_cap");
    if (itb < 0) breaches.push("itb");
    const counts = { G: 0, D: 0, M: 0, F: 0 };
    xiOf(state).forEach((s) => {
      const p = byId(s.id);
      if (p && counts[p.pos] != null) counts[p.pos] += 1;
    });
    const shapeOk = POS_ORDER.every((pos) => {
      const [lo, hi] = SHAPE[pos];
      return counts[pos] >= lo && counts[pos] <= hi;
    }) && xiOf(state).length === XI_MAX;
    if (!shapeOk) breaches.push("starting_shape");
    return breaches;
  }

  function ensureWhatIf() {
    const owned = ownedState();
    if (!owned.length) {
      whatIf = [];
      return;
    }
    if (!whatIf.length || whatIf.some((s) => !byId(s.id))) {
      whatIf = owned.map((s) => ({ ...s }));
    }
  }

  function resetWhatIf() {
    whatIf = ownedState().map((s) => ({ ...s }));
    dropReason = "";
  }

  function occupantAt(lineupIndex) {
    return whatIf.find((s) => s.lineup_index === lineupIndex) || null;
  }

  function replaceSlot(lineupIndex, incomingId) {
    const incoming = byId(incomingId);
    const occ = occupantAt(lineupIndex);
    if (!incoming || !occ) return;
    if (incoming.pos !== (byId(occ.id) || {}).pos) {
      dropReason = "Same Position only.";
      return;
    }
    if (whatIf.some((s) => s.id === incomingId)) {
      dropReason = "Already in the 15.";
      return;
    }
    whatIf = whatIf.map((s) => (s.lineup_index === lineupIndex ? { id: incomingId, lineup_index: lineupIndex } : s));
    dropReason = "";
  }

  function swapLineups(a, b) {
    const left = occupantAt(a);
    const right = occupantAt(b);
    if (!left || !right) return;
    const leftXi = left.lineup_index <= XI_MAX;
    const rightXi = right.lineup_index <= XI_MAX;
    if (leftXi === rightXi) return;
    whatIf = whatIf.map((s) => {
      if (s.id === left.id) return { id: s.id, lineup_index: b };
      if (s.id === right.id) return { id: s.id, lineup_index: a };
      return s;
    });
    dropReason = "";
  }

  function cardHtml(slot, gw) {
    const p = byId(slot.id);
    if (!p) return "";
    const cap = autoCaptain(whatIf, gw);
    const vice = autoVice(whatIf, gw);
    const role = cap && cap.id === p.id ? "C" : vice && vice.id === p.id ? "VC" : "";
    const xp = xminXp(p, gw);
    return `<article class="player-card" draggable="true" data-from="board" data-player-id="${p.id}" data-pos="${p.pos}" data-lineup-index="${slot.lineup_index}">
      <div class="card-header-bar">
        <span class="pos-tag ${p.pos}">${POS_LABEL[p.pos] || p.pos}</span>
        ${role ? `<span class="role-badge ${role === "C" ? "active-c" : "active-vc"}">${role}</span>` : ""}
      </div>
      <div class="card-name">${p.name}</div>
      <div class="card-team-price">${p.team} · £${Number(p.price).toFixed(1)}m</div>
      <div class="card-xp">${xp.toFixed(1)}</div>
    </article>`;
  }

  function bindBoardDnD(root) {
    root.querySelectorAll(".player-card").forEach((card) => {
      card.addEventListener("dragstart", (e) => {
        e.dataTransfer.setData("application/x-fpl-player", JSON.stringify({
          id: Number(card.dataset.playerId),
          pos: card.dataset.pos,
          from: "board",
          lineup_index: Number(card.dataset.lineupIndex),
        }));
        e.dataTransfer.effectAllowed = "move";
      });
      card.addEventListener("dragover", (e) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = "move";
      });
      card.addEventListener("drop", (e) => {
        e.preventDefault();
        let payload;
        try {
          payload = JSON.parse(e.dataTransfer.getData("application/x-fpl-player") || "{}");
        } catch {
          return;
        }
        const targetIndex = Number(card.dataset.lineupIndex);
        if (payload.from === "pool") replaceSlot(targetIndex, Number(payload.id));
        else if (payload.from === "board") swapLineups(Number(payload.lineup_index), targetIndex);
        render();
      });
    });
  }

  function renderPitch(gw) {
    const pitch = document.getElementById("squad-pitch");
    const bench = document.getElementById("squad-bench");
    if (!pitch || !bench) return;
    const xi = xiOf(whatIf);
    pitch.innerHTML = POS_ORDER.map((pos) => {
      const row = xi.filter((s) => (byId(s.id) || {}).pos === pos)
        .sort((a, b) => a.lineup_index - b.lineup_index);
      if (!row.length) return "";
      return `<div class="pitch-row">${row.map((s) => cardHtml(s, gw)).join("")}</div>`;
    }).join("");
    const benchSlots = whatIf.filter((s) => s.lineup_index > XI_MAX).sort((a, b) => a.lineup_index - b.lineup_index);
    bench.innerHTML = benchSlots.map((s) => cardHtml(s, gw)).join("");
    bindBoardDnD(pitch);
    bindBoardDnD(bench);
  }

  function renderStrip(owned, gws) {
    const head = document.getElementById("squad-xp-head");
    const body = document.getElementById("squad-xp-body");
    if (!head || !body) return;
    head.innerHTML = `<tr><th></th>${gws.map((gw) => `<th>GW${gw}</th>`).join("")}</tr>`;
    const cells = gws.map((gw) => {
      const now = squadXp(whatIf, gw);
      const base = squadXp(owned, gw);
      const delta = Math.round((now - base) * 100) / 100;
      const sign = delta > 0 ? "+" : "";
      return `<td>${now.toFixed(2)} <span class="delta ${delta < 0 ? "neg" : "pos"}">(${sign}${delta.toFixed(2)})</span></td>`;
    });
    body.innerHTML = `<tr><th>What-If</th>${cells.join("")}</tr>`;
  }

  function profileSum(state, gw, key, assume90) {
    return state.reduce((sum, s) => {
      const p = byId(s.id);
      if (!p) return sum;
      const row = assume90 ? assumeNinetyRow(gwRow(p, gw)) : gwRow(p, gw);
      return sum + Number(row[key] || 0);
    }, 0);
  }

  function renderProfile(gws) {
    const head = document.getElementById("component-profile-head");
    const body = document.getElementById("component-profile-body");
    if (!head || !body) return;
    head.innerHTML = `<tr><th>Component</th>${gws.map((gw) => `<th>GW${gw}</th>`).join("")}<th>Total</th></tr>`;
    body.innerHTML = PROFILE_KEYS.map(([key, label]) => {
      let totX = 0;
      let totA = 0;
      const cells = gws.map((gw) => {
        const x = profileSum(whatIf, gw, key, false);
        const a = profileSum(whatIf, gw, key, true);
        totX += x;
        totA += a;
        return `<td>${x.toFixed(2)} | ${a.toFixed(2)}</td>`;
      }).join("");
      return `<tr><th>${label}</th>${cells}<td>${totX.toFixed(2)} | ${totA.toFixed(2)}</td></tr>`;
    }).join("");
  }

  function renderHeader(startGw) {
    const itb = itbAfter(whatIf);
    const hitN = hits(whatIf);
    const itbEl = document.getElementById("squad-itb");
    const ftEl = document.getElementById("squad-ft");
    const hitsEl = document.getElementById("squad-hits");
    if (itbEl) itbEl.textContent = `£${itb.toFixed(1)}m`;
    if (ftEl) ftEl.textContent = String(meta().free_transfers ?? "—");
    if (hitsEl) {
      hitsEl.textContent = hitN ? `Hit warning: ${hitN}` : "0";
      hitsEl.classList.toggle("text-danger", hitN > 0);
    }
    const banner = document.getElementById("rule-breach-banner");
    const breaches = ruleBreaches(whatIf, itb);
    if (banner) {
      if (breaches.length) {
        banner.hidden = false;
        banner.textContent = `Rule Breach: ${breaches.map((b) => BREACH_LABEL[b] || b).join(" · ")}`;
      } else {
        banner.hidden = true;
        banner.textContent = "";
      }
    }
    const hint = document.getElementById("official-c-hint");
    const cap = autoCaptain(whatIf, startGw);
    const officialId = meta().owned_captain_id;
    const official = byId(officialId);
    if (hint) {
      if (cap && official && cap.id !== official.id) {
        hint.textContent = `Official Captain: ${official.name} · Auto Captain: ${cap.player.name}`;
      } else {
        hint.textContent = "";
      }
    }
    const dropEl = document.getElementById("squad-drop-reason");
    if (dropEl) dropEl.textContent = dropReason;
  }

  function render() {
    if (!ctx) return;
    const owned = ownedState();
    const empty = document.getElementById("squad-board-empty");
    const live = document.getElementById("squad-board-live");
    if (!owned.length) {
      if (empty) empty.hidden = false;
      if (live) live.hidden = true;
      whatIf = [];
      return;
    }
    if (empty) empty.hidden = true;
    if (live) live.hidden = false;
    ensureWhatIf();
    const gws = viewGws();
    const startGw = gws[0] || 1;
    renderHeader(startGw);
    renderPitch(startGw);
    renderStrip(owned, gws);
    renderProfile(gws);
  }

  function bind() {
    if (bound) return;
    bound = true;
    document.getElementById("squad-reset")?.addEventListener("click", () => {
      resetWhatIf();
      render();
    });
    document.getElementById("squad-reload")?.addEventListener("click", () => {
      if (typeof window.reloadDashboardJson === "function") {
        window.reloadDashboardJson();
        return;
      }
      resetWhatIf();
      render();
    });
    document.getElementById("squad-empty-refresh")?.addEventListener("click", () => {
      document.getElementById("btn-refresh")?.click();
    });
    document.getElementById("explorer-table")?.addEventListener("dragstart", (e) => {
      const tr = e.target.closest("tr[data-player-id]");
      if (!tr) return;
      const id = Number(tr.dataset.playerId);
      const p = byId(id);
      if (!p) return;
      e.dataTransfer.setData("application/x-fpl-player", JSON.stringify({
        id, pos: p.pos, from: "pool",
      }));
      e.dataTransfer.effectAllowed = "move";
    });
  }

  window.initSquadBoard = function (context) {
    ctx = context;
    bind();
    resetWhatIf();
    render();
  };

  window.renderSquadBoard = render;
})();

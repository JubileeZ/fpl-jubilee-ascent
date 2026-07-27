document.addEventListener("DOMContentLoaded", () => {
  let allPlayers = [];
  let playersMap = new Map();
  let metaData = {};

  // Multi-Model View State
  let availableModels = [];
  let primaryModel = "";
  let compareModels = new Set();

  // Squad State: 15 slots (0..10 Starters, 11..14 Bench)
  let squad = Array(15).fill(null);
  let captainId = null;
  let viceCaptainId = null;

  // View state
  let selectedGw = "horizon"; // 'horizon' or 'gw1', 'gw2'...
  let searchQuery = "";
  let posFilter = "ALL";
  let sortKey = "selected_xp";
  let sortAsc = false;

  // DOM Elements
  const primaryModelSelect = document.getElementById("primaryModelSelect");
  const compareModelsContainer = document.getElementById("compareModelsContainer");
  const gwSelect = document.getElementById("gwSelect");
  const searchInput = document.getElementById("searchInput");
  const playersTable = document.getElementById("playersTable");
  const tableBody = document.getElementById("tableBody");
  const posTabs = document.querySelectorAll(".pos-tab");
  const btnLoadMilp = document.getElementById("btnLoadMilp");
  const btnClearSquad = document.getElementById("btnClearSquad");

  // Summary Elements
  const statStartingXp = document.getElementById("statStartingXp");
  const statBenchXp = document.getElementById("statBenchXp");
  const statCost = document.getElementById("statCost");
  const statFormation = document.getElementById("statFormation");
  const validationBanner = document.getElementById("squadValidationAlert");
  const validationText = document.getElementById("validationText");

  // Pitch Rows
  const rowGk = document.getElementById("rowGk");
  const rowDef = document.getElementById("rowDef");
  const rowMid = document.getElementById("rowMid");
  const rowFwd = document.getElementById("rowFwd");
  const benchContainer = document.getElementById("benchContainer");
  const benchCountText = document.getElementById("benchCountText");

  // 1. Load Data
  async function init() {
    try {
      const response = await fetch("dashboard_data.json");
      if (!response.ok) throw new Error("Failed to load dashboard_data.json");
      const data = await response.json();
      metaData = data.meta || {};
      allPlayers = data.players || [];

      allPlayers.forEach(p => playersMap.set(p.id, p));

      setupModelControls();
      setupGwSelect();
      setupEventListeners();

      // Pre-fill squad if MILP IDs available
      if (metaData.prefilled_squad_ids && metaData.prefilled_squad_ids.length > 0) {
        fillSquadFromIds(metaData.prefilled_squad_ids);
      } else {
        autoSelectTopSquad();
      }

      renderAll();
    } catch (err) {
      console.error(err);
      tableBody.innerHTML = `<tr><td colspan="15" style="text-align:center; color:#ef4444; padding:2rem;">
        Error loading dashboard data: ${err.message}. Make sure 'commands.dashboard' export completed.
      </td></tr>`;
    }
  }

  function setupModelControls() {
    availableModels = metaData.models || [metaData.default_model || "default"];
    primaryModel = metaData.default_model || availableModels[0];

    // Populate Primary Model dropdown
    primaryModelSelect.innerHTML = "";
    availableModels.forEach(m => {
      const opt = document.createElement("option");
      opt.value = m;
      opt.textContent = m === metaData.default_model ? `${m} (Champion)` : m;
      if (m === primaryModel) opt.selected = true;
      primaryModelSelect.appendChild(opt);
    });

    // Populate Compare Checkboxes
    renderCompareCheckboxes();
  }

  function renderCompareCheckboxes() {
    compareModelsContainer.innerHTML = "";
    availableModels.forEach(m => {
      if (m === primaryModel) return;
      const label = document.createElement("label");
      label.className = "compare-chip";
      const chk = document.createElement("input");
      chk.type = "checkbox";
      chk.value = m;
      chk.checked = compareModels.has(m);

      chk.addEventListener("change", (e) => {
        if (e.target.checked) compareModels.add(m);
        else compareModels.delete(m);
        renderTable();
      });

      label.appendChild(chk);
      label.appendChild(document.createTextNode(m));
      compareModelsContainer.appendChild(label);
    });
  }

  function setupGwSelect() {
    gwSelect.innerHTML = `<option value="horizon">Full Horizon Total (${metaData.horizon || 5} GWs)</option>`;
    if (metaData.gw_ids) {
      metaData.gw_ids.forEach(gw => {
        gwSelect.innerHTML += `<option value="gw${gw}">Gameweek ${gw}</option>`;
      });
    }
  }

  function setupEventListeners() {
    primaryModelSelect.addEventListener("change", (e) => {
      primaryModel = e.target.value;
      compareModels.delete(primaryModel);
      renderCompareCheckboxes();
      renderAll();
    });

    gwSelect.addEventListener("change", (e) => {
      selectedGw = e.target.value;
      renderAll();
    });

    searchInput.addEventListener("input", (e) => {
      searchQuery = e.target.value.toLowerCase();
      renderTable();
    });

    posTabs.forEach(tab => {
      tab.addEventListener("click", () => {
        posTabs.forEach(t => t.classList.remove("active"));
        tab.classList.add("active");
        posFilter = tab.dataset.pos;
        renderTable();
      });
    });

    btnLoadMilp.addEventListener("click", () => {
      if (metaData.prefilled_squad_ids && metaData.prefilled_squad_ids.length > 0) {
        fillSquadFromIds(metaData.prefilled_squad_ids);
      } else {
        autoSelectTopSquad();
      }
      renderAll();
    });

    btnClearSquad.addEventListener("click", () => {
      squad = Array(15).fill(null);
      captainId = null;
      viceCaptainId = null;
      renderAll();
    });
  }

  function getPlayerProj(player, modelName = primaryModel) {
    if (!player) return {};
    const modelData = (player.models && player.models[modelName]) ? player.models[modelName] : player;
    const projections = modelData.projections || player.projections || {};

    if (selectedGw === "horizon") {
      let xg = 0, xa = 0, xcs = 0, xdef = 0, xb = 0, xmins = 0;
      Object.values(projections).forEach(proj => {
        xg += proj.xg_pts || 0;
        xa += proj.xa_pts || 0;
        xcs += proj.xcs_pts || 0;
        xdef += proj.xdefcon_pts || 0;
        xb += proj.xb_pts || 0;
        xmins += proj.xmins || 0;
      });
      return {
        total_xp: modelData.total_xp_horizon || 0,
        xmins: Math.round(xmins * 10) / 10,
        xg_pts: Math.round(xg * 100) / 100,
        xa_pts: Math.round(xa * 100) / 100,
        xcs_pts: Math.round(xcs * 100) / 100,
        xdefcon_pts: Math.round(xdef * 100) / 100,
        xb_pts: Math.round(xb * 100) / 100,
      };
    }
    return projections[selectedGw] || {};
  }

  function getPlayerXp(player, modelName = primaryModel) {
    return getPlayerProj(player, modelName).total_xp || 0;
  }

  // Auto squad selection algorithm (Budget-constrained greedy xP selection)
  function autoSelectTopSquad() {
    squad = Array(15).fill(null);
    const sorted = [...allPlayers].sort((a, b) => getPlayerXp(b) - getPlayerXp(a));

    const gks = sorted.filter(p => p.pos === "G");
    const defs = sorted.filter(p => p.pos === "D");
    const mids = sorted.filter(p => p.pos === "M");
    const fwds = sorted.filter(p => p.pos === "F");

    let pickedIds = [];
    let clubCounts = {};
    let totalSpent = 0;

    function canAdd(p) {
      if (pickedIds.includes(p.id)) return false;
      if ((clubCounts[p.team] || 0) >= 3) return false;
      return true;
    }

    function pickPlayer(p) {
      pickedIds.push(p.id);
      clubCounts[p.team] = (clubCounts[p.team] || 0) + 1;
      totalSpent += p.price;
    }

    // Pick 2 GKs
    const gk1 = gks.find(canAdd);
    if (gk1) pickPlayer(gk1);
    const gk2 = gks.filter(p => p.price <= 4.5).find(canAdd) || gks.find(canAdd);
    if (gk2) pickPlayer(gk2);

    // Pick 5 DEFs
    for (let i = 0; i < 5; i++) {
      const def = defs.find(canAdd);
      if (def) pickPlayer(def);
    }

    // Pick 5 MIDs
    for (let i = 0; i < 5; i++) {
      const mid = mids.find(canAdd);
      if (mid) pickPlayer(mid);
    }

    // Pick 3 FWDs
    for (let i = 0; i < 3; i++) {
      const fwd = fwds.find(canAdd);
      if (fwd) pickPlayer(fwd);
    }

    // Downgrade if budget > 100.0
    while (totalSpent > 100.0 && pickedIds.length === 15) {
      const outfielders = pickedIds.map(id => playersMap.get(id)).filter(p => p.pos !== "G");
      outfielders.sort((a, b) => b.price - a.price);
      const expensiveP = outfielders[0];
      if (!expensiveP) break;

      const pool = sorted.filter(p => p.pos === expensiveP.pos && p.price < expensiveP.price && canAdd(p));
      if (pool.length > 0) {
        const pIdx = pickedIds.indexOf(expensiveP.id);
        clubCounts[expensiveP.team] -= 1;
        totalSpent -= expensiveP.price;

        const rep = pool[0];
        pickedIds[pIdx] = rep.id;
        clubCounts[rep.team] = (clubCounts[rep.team] || 0) + 1;
        totalSpent += rep.price;
      } else {
        break;
      }
    }

    const pickedPlayers = pickedIds.map(id => playersMap.get(id));
    const pGks = pickedPlayers.filter(p => p.pos === "G");
    const pDefs = pickedPlayers.filter(p => p.pos === "D");
    const pMids = pickedPlayers.filter(p => p.pos === "M");
    const pFwds = pickedPlayers.filter(p => p.pos === "F");

    if (pGks[0]) squad[0] = pGks[0].id;
    [0, 1, 2].forEach(i => { if (pDefs[i]) squad[1 + i] = pDefs[i].id; });
    [0, 1, 2, 3].forEach(i => { if (pMids[i]) squad[4 + i] = pMids[i].id; });
    [0, 1, 2].forEach(i => { if (pFwds[i]) squad[8 + i] = pFwds[i].id; });

    if (pGks[1]) squad[11] = pGks[1].id;
    const remOutfield = [...pDefs.slice(3), ...pMids.slice(4), ...pFwds.slice(3)];
    [0, 1, 2].forEach(i => { if (remOutfield[i]) squad[12 + i] = remOutfield[i].id; });

    autoAssignCaptaincy();
  }

  function fillSquadFromIds(playerIds) {
    squad = Array(15).fill(null);
    const players = playerIds.map(id => playersMap.get(id)).filter(Boolean);

    const gks = players.filter(p => p.pos === "G");
    const defs = players.filter(p => p.pos === "D");
    const mids = players.filter(p => p.pos === "M");
    const fwds = players.filter(p => p.pos === "F");

    if (gks[0]) squad[0] = gks[0].id;
    let sIdx = 1;

    defs.slice(0, 3).forEach(p => { squad[sIdx++] = p.id; });
    mids.slice(0, 4).forEach(p => { squad[sIdx++] = p.id; });
    fwds.slice(0, 3).forEach(p => { squad[sIdx++] = p.id; });

    const remainingStarters = [...defs.slice(3), ...mids.slice(4), ...fwds.slice(3)];
    while (sIdx <= 10 && remainingStarters.length > 0) {
      squad[sIdx++] = remainingStarters.shift().id;
    }

    let bIdx = 11;
    if (gks[1]) squad[bIdx++] = gks[1].id;
    while (bIdx <= 14 && remainingStarters.length > 0) {
      squad[bIdx++] = remainingStarters.shift().id;
    }

    autoAssignCaptaincy();
  }

  function autoAssignCaptaincy() {
    const starters = squad.slice(0, 11).map(id => playersMap.get(id)).filter(Boolean);
    if (starters.length > 0) {
      starters.sort((a, b) => getPlayerXp(b) - getPlayerXp(a));
      captainId = starters[0].id;
      viceCaptainId = starters[1] ? starters[1].id : null;
    }
  }

  function addPlayerToSquad(playerId) {
    const p = playersMap.get(playerId);
    if (!p || squad.includes(playerId)) return;

    let targetSlot = -1;
    if (p.pos === "G") {
      if (squad[0] === null) targetSlot = 0;
      else if (squad[11] === null) targetSlot = 11;
    } else {
      for (let i = 1; i <= 10; i++) {
        if (squad[i] === null) { targetSlot = i; break; }
      }
      if (targetSlot === -1) {
        for (let i = 12; i <= 14; i++) {
          if (squad[i] === null) { targetSlot = i; break; }
        }
      }
    }

    if (targetSlot !== -1) {
      squad[targetSlot] = playerId;
      if (!captainId) captainId = playerId;
      else if (!viceCaptainId && captainId !== playerId) viceCaptainId = playerId;
      renderAll();
    }
  }

  function removePlayerFromSquad(slotIndex) {
    const removedId = squad[slotIndex];
    squad[slotIndex] = null;
    if (captainId === removedId) {
      captainId = viceCaptainId;
      viceCaptainId = null;
    } else if (viceCaptainId === removedId) {
      viceCaptainId = null;
    }
    renderAll();
  }

  function swapSquadSlots(fromIndex, toIndex) {
    if (fromIndex === toIndex) return;
    const temp = squad[fromIndex];
    squad[fromIndex] = squad[toIndex];
    squad[toIndex] = temp;
    renderAll();
  }

  function validateSquad() {
    const selectedPlayers = squad.map(id => playersMap.get(id)).filter(Boolean);
    let totalCost = 0;
    const teamCounts = {};
    const posCounts = { G: 0, D: 0, M: 0, F: 0 };
    const starterPosCounts = { G: 0, D: 0, M: 0, F: 0 };

    selectedPlayers.forEach(p => {
      totalCost += p.price;
      teamCounts[p.team] = (teamCounts[p.team] || 0) + 1;
      posCounts[p.pos] = (posCounts[p.pos] || 0) + 1;
    });

    squad.slice(0, 11).forEach(id => {
      const p = playersMap.get(id);
      if (p) starterPosCounts[p.pos] = (starterPosCounts[p.pos] || 0) + 1;
    });

    const errors = [];
    if (totalCost > 100.0) errors.push(`Budget exceeded (£${totalCost.toFixed(1)}m > £100.0m)`);

    Object.entries(teamCounts).forEach(([team, count]) => {
      if (count > 3) errors.push(`Max 3 players per club exceeded (${team}: ${count})`);
    });

    if (selectedPlayers.length === 15) {
      if (posCounts.G !== 2 || posCounts.D !== 5 || posCounts.M !== 5 || posCounts.F !== 3) {
        errors.push(`Invalid squad composition (${posCounts.G} GK, ${posCounts.D} DEF, ${posCounts.M} MID, ${posCounts.F} FWD)`);
      }
    }

    const starterCount = squad.slice(0, 11).filter(Boolean).length;
    if (starterCount === 11) {
      if (starterPosCounts.G !== 1 || starterPosCounts.D < 3 || starterPosCounts.M < 2 || starterPosCounts.F < 1) {
        errors.push(`Invalid formation (${starterPosCounts.D}-${starterPosCounts.M}-${starterPosCounts.F})`);
      }
    }

    statFormation.textContent = `${starterPosCounts.D}-${starterPosCounts.M}-${starterPosCounts.F}`;
    statCost.textContent = `£${totalCost.toFixed(1)}m / £100.0m`;
    if (totalCost > 100.0) statCost.classList.add("text-danger");
    else statCost.classList.remove("text-danger");

    if (errors.length === 0) {
      validationBanner.className = "validation-banner valid";
      validationText.textContent = `Squad Valid (${selectedPlayers.length}/15 players selected)`;
    } else {
      validationBanner.className = "validation-banner invalid";
      validationText.textContent = errors.join(" • ");
    }

    // Calculate Primary Model xP
    let startingXp = 0;
    squad.slice(0, 11).forEach(id => {
      const p = playersMap.get(id);
      if (p) {
        let xp = getPlayerXp(p, primaryModel);
        if (id === captainId) xp *= 2.0;
        startingXp += xp;
      }
    });

    let benchXp = 0;
    squad.slice(11, 15).forEach(id => {
      const p = playersMap.get(id);
      if (p) benchXp += getPlayerXp(p, primaryModel);
    });

    statStartingXp.textContent = startingXp.toFixed(2);
    statBenchXp.textContent = benchXp.toFixed(2);
  }

  function renderPitch() {
    rowGk.innerHTML = "";
    rowDef.innerHTML = "";
    rowMid.innerHTML = "";
    rowFwd.innerHTML = "";
    benchContainer.innerHTML = "";

    const starters = squad.slice(0, 11);
    const bench = squad.slice(11, 15);

    starters.forEach((id, index) => {
      const card = createPlayerCard(id, index);
      const player = playersMap.get(id);

      if (!player) {
        rowDef.appendChild(card);
      } else if (player.pos === "G") {
        rowGk.appendChild(card);
      } else if (player.pos === "D") {
        rowDef.appendChild(card);
      } else if (player.pos === "M") {
        rowMid.appendChild(card);
      } else if (player.pos === "F") {
        rowFwd.appendChild(card);
      }
    });

    bench.forEach((id, index) => {
      const benchIndex = 11 + index;
      const card = createPlayerCard(id, benchIndex);
      benchContainer.appendChild(card);
    });

    const benchFilled = bench.filter(Boolean).length;
    benchCountText.textContent = `${benchFilled}/4 Substitutes`;
  }

  function createPlayerCard(playerId, slotIndex) {
    const div = document.createElement("div");
    div.className = "player-card";
    div.dataset.slot = slotIndex;

    const player = playersMap.get(playerId);
    if (!player) {
      div.classList.add("empty-slot");
      div.innerHTML = `<span class="slot-label">${slotIndex < 11 ? "Starter" : "Sub"}</span>`;
      div.addEventListener("dragover", e => e.preventDefault());
      div.addEventListener("drop", e => {
        e.preventDefault();
        const fromSlot = parseInt(e.dataTransfer.getData("text/plain"), 10);
        if (!isNaN(fromSlot)) swapSquadSlots(fromSlot, slotIndex);
      });
      return div;
    }

    const xpVal = getPlayerXp(player, primaryModel).toFixed(1);
    const isCap = captainId === player.id;
    const isVc = viceCaptainId === player.id;

    div.draggable = true;
    div.innerHTML = `
      <div class="card-header-bar">
        <span class="pos-tag ${player.pos}">${player.pos}</span>
        <button class="remove-btn" title="Remove player">×</button>
      </div>
      <div class="card-name" title="${player.full_name}">${player.name}</div>
      <div class="card-team-price">${player.team} · £${player.price}m</div>
      <div class="card-xp">${xpVal} xP</div>
      <div class="card-role-btns">
        <button class="role-badge ${isCap ? "active-c" : ""}" data-role="c">C</button>
        <button class="role-badge ${isVc ? "active-vc" : ""}" data-role="vc">VC</button>
      </div>
    `;

    div.querySelector(".remove-btn").addEventListener("click", (e) => {
      e.stopPropagation();
      removePlayerFromSquad(slotIndex);
    });

    div.querySelector('[data-role="c"]').addEventListener("click", (e) => {
      e.stopPropagation();
      if (captainId === player.id) captainId = null;
      else {
        captainId = player.id;
        if (viceCaptainId === player.id) viceCaptainId = null;
      }
      renderAll();
    });

    div.querySelector('[data-role="vc"]').addEventListener("click", (e) => {
      e.stopPropagation();
      if (viceCaptainId === player.id) viceCaptainId = null;
      else {
        viceCaptainId = player.id;
        if (captainId === player.id) captainId = null;
      }
      renderAll();
    });

    div.addEventListener("dragstart", (e) => {
      e.dataTransfer.setData("text/plain", slotIndex.toString());
      div.style.opacity = "0.5";
    });

    div.addEventListener("dragend", () => {
      div.style.opacity = "1.0";
    });

    div.addEventListener("dragover", (e) => e.preventDefault());

    div.addEventListener("drop", (e) => {
      e.preventDefault();
      const fromSlot = parseInt(e.dataTransfer.getData("text/plain"), 10);
      if (!isNaN(fromSlot)) swapSquadSlots(fromSlot, slotIndex);
    });

    return div;
  }

  function renderTableHead() {
    const thead = playersTable.querySelector("thead");
    const activeCompareList = Array.from(compareModels);

    let html = `<tr>
      <th data-sort="name">Player ↕</th>
      <th data-sort="pos">Pos ↕</th>
      <th data-sort="team">Team ↕</th>
      <th data-sort="price" class="num">Price ↕</th>
      <th data-sort="selected_xp" class="num highlight-col">${primaryModel} xP ↕</th>`;

    activeCompareList.forEach(mName => {
      html += `<th data-sort="cmp_xp_${mName}" class="num">${mName} xP ↕</th>`;
      html += `<th data-sort="diff_xp_${mName}" class="num">Diff (${mName}) ↕</th>`;
    });

    html += `
      <th data-sort="selected_xmins" class="num">xMins ↕</th>
      <th data-sort="selected_xg_pts" class="num">xG Pts ↕</th>
      <th data-sort="selected_xa_pts" class="num">xA Pts ↕</th>
      <th data-sort="selected_xcs_pts" class="num">xCS Pts ↕</th>
      <th data-sort="selected_xdefcon_pts" class="num">xDef ↕</th>
      <th data-sort="selected_xb_pts" class="num">xB ↕</th>
      <th data-sort="pts_per_start" class="num">Pts/Start ↕</th>
      <th data-sort="pts_per_90" class="num">Pts/90 ↕</th>
      <th data-sort="ict_per_90" class="num">ICT/90 ↕</th>
      <th class="action-col">Action</th>
    </tr>`;

    thead.innerHTML = html;

    thead.querySelectorAll("th[data-sort]").forEach(th => {
      th.addEventListener("click", () => {
        const key = th.dataset.sort;
        if (sortKey === key) sortAsc = !sortAsc;
        else { sortKey = key; sortAsc = false; }
        renderTable();
      });
    });
  }

  function renderTable() {
    renderTableHead();

    let filtered = allPlayers.filter(p => {
      if (posFilter !== "ALL" && p.pos !== posFilter) return false;
      if (searchQuery) {
        const matchesName = p.name.toLowerCase().includes(searchQuery) || p.full_name.toLowerCase().includes(searchQuery);
        const matchesTeam = p.team.toLowerCase().includes(searchQuery) || p.team_full.toLowerCase().includes(searchQuery);
        if (!matchesName && !matchesTeam) return false;
      }
      return true;
    });

    filtered.sort((a, b) => {
      let valA, valB;
      const projA = getPlayerProj(a, primaryModel);
      const projB = getPlayerProj(b, primaryModel);

      if (sortKey === "selected_xp") { valA = projA.total_xp || 0; valB = projB.total_xp || 0; }
      else if (sortKey === "selected_xmins") { valA = projA.xmins || 0; valB = projB.xmins || 0; }
      else if (sortKey === "selected_xg_pts") { valA = projA.xg_pts || 0; valB = projB.xg_pts || 0; }
      else if (sortKey === "selected_xa_pts") { valA = projA.xa_pts || 0; valB = projB.xa_pts || 0; }
      else if (sortKey === "selected_xcs_pts") { valA = projA.xcs_pts || 0; valB = projB.xcs_pts || 0; }
      else if (sortKey === "selected_xdefcon_pts") { valA = projA.xdefcon_pts || 0; valB = projB.xdefcon_pts || 0; }
      else if (sortKey === "selected_xb_pts") { valA = projA.xb_pts || 0; valB = projB.xb_pts || 0; }
      else if (sortKey.startsWith("cmp_xp_")) {
        const mName = sortKey.replace("cmp_xp_", "");
        valA = getPlayerXp(a, mName);
        valB = getPlayerXp(b, mName);
      } else if (sortKey.startsWith("diff_xp_")) {
        const mName = sortKey.replace("diff_xp_", "");
        valA = getPlayerXp(a, mName) - (projA.total_xp || 0);
        valB = getPlayerXp(b, mName) - (projB.total_xp || 0);
      } else { valA = a[sortKey] || 0; valB = b[sortKey] || 0; }

      if (typeof valA === "string") return sortAsc ? valA.localeCompare(valB) : valB.localeCompare(valA);
      return sortAsc ? valA - valB : valB - valA;
    });

    tableBody.innerHTML = "";
    const activeCompareList = Array.from(compareModels);

    filtered.forEach(p => {
      const proj = getPlayerProj(p, primaryModel);
      const inSquad = squad.includes(p.id);
      const tr = document.createElement("tr");

      let rowHtml = `
        <td><strong>${p.name}</strong> <span class="subtitle">(${p.full_name})</span></td>
        <td><span class="pos-tag ${p.pos}">${p.pos}</span></td>
        <td>${p.team}</td>
        <td class="num">£${p.price.toFixed(1)}m</td>
        <td class="num highlight-col">${(proj.total_xp || 0).toFixed(2)}</td>`;

      activeCompareList.forEach(mName => {
        const cmpXp = getPlayerXp(p, mName);
        const diff = cmpXp - (proj.total_xp || 0);
        const diffSign = diff > 0 ? `+${diff.toFixed(2)}` : diff.toFixed(2);
        const diffClass = diff > 0 ? "text-accent" : (diff < 0 ? "text-danger" : "text-muted");

        rowHtml += `<td class="num">${cmpXp.toFixed(2)}</td>`;
        rowHtml += `<td class="num ${diffClass}">${diffSign}</td>`;
      });

      rowHtml += `
        <td class="num">${(proj.xmins || 0).toFixed(1)}</td>
        <td class="num">${(proj.xg_pts || 0).toFixed(2)}</td>
        <td class="num">${(proj.xa_pts || 0).toFixed(2)}</td>
        <td class="num">${(proj.xcs_pts || 0).toFixed(2)}</td>
        <td class="num">${(proj.xdefcon_pts || 0).toFixed(2)}</td>
        <td class="num">${(proj.xb_pts || 0).toFixed(2)}</td>
        <td class="num">${p.pts_per_start.toFixed(2)}</td>
        <td class="num">${p.pts_per_90.toFixed(2)}</td>
        <td class="num">${p.ict_per_90.toFixed(2)}</td>
        <td class="action-col">
          <button class="add-btn" ${inSquad ? "disabled" : ""} data-id="${p.id}">
            ${inSquad ? "Added" : "+ Add"}
          </button>
        </td>
      `;

      tr.innerHTML = rowHtml;
      tr.querySelector(".add-btn").addEventListener("click", () => addPlayerToSquad(p.id));
      tableBody.appendChild(tr);
    });
  }

  function renderAll() {
    renderPitch();
    validateSquad();
    renderTable();
  }

  init();
});

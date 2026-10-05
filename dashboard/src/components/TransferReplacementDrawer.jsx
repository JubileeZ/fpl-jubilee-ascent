import React, { useState, useMemo } from 'react';
import { usePlanStore, planActions } from '../store/usePlanStore';

function normalizePos(pos) {
  if (!pos) return 'MID';
  const p = String(pos).toUpperCase();
  if (p === 'G' || p === 'GKP' || p === 'GK') return 'GKP';
  if (p === 'D' || p === 'DEF') return 'DEF';
  if (p === 'M' || p === 'MID') return 'MID';
  if (p === 'F' || p === 'FWD') return 'FWD';
  return p;
}

export default function TransferReplacementDrawer({
  isOpen,
  onClose,
  replacedSlot,
  replacedPlayer,
}) {
  const { activeNode, activePlan } = usePlanStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [affordableOnly, setAffordableOnly] = useState(true);
  const [selectedPos, setSelectedPos] = useState(replacedPlayer?.pos ? normalizePos(replacedPlayer.pos) : 'ALL');

  // Reset or initialize filters when replaced player changes
  React.useEffect(() => {
    if (replacedPlayer?.pos) {
      setSelectedPos(normalizePos(replacedPlayer.pos));
    }
  }, [replacedPlayer?.id, replacedPlayer?.pos]);

function parsePrice(val) {
  if (val == null) return 5.0;
  const n = Number(val);
  return n > 25 ? n / 10 : n;
}

  const [allPlayers, setAllPlayers] = useState(() => window.dashboardData?.players || []);

  React.useEffect(() => {
    if (window.dashboardData?.players && allPlayers.length > 0) return;
    if (window.dashboardData?.players) {
      setAllPlayers(window.dashboardData.players);
      return;
    }
    fetch('/dashboard_data.json')
      .then((r) => r.json())
      .then((d) => {
        window.dashboardData = d;
        setAllPlayers(d.players || []);
      })
      .catch(console.error);
  }, []);

  const currentGw = activeNode?.gameweek || activePlan?.startGameweek || 6;
  const horizon = activePlan?.horizonGameweeks || 5;
  const endGw = currentGw + horizon - 1;

  const currentBank = activeNode?.evaluation?.bankRemaining ?? activePlan?.initialBank ?? 0.0;
  const sellingPrice = parsePrice(replacedPlayer?.selling_price ?? replacedPlayer?.price);
  const maxAffordablePrice = Number((sellingPrice + currentBank).toFixed(1));

  // Calculate sum of xP across lookahead horizon for replaced player
  const replacedSumXp = useMemo(() => {
    if (!replacedPlayer) return 0;
    let sum = 0;
    for (let gw = currentGw; gw <= endGw; gw++) {
      sum += replacedPlayer.projections?.[`gw${gw}`]?.total_xp ?? 0;
    }
    return sum;
  }, [replacedPlayer, currentGw, endGw]);

  // Existing players in squad to prevent duplicate transfers
  const currentSquadIds = useMemo(() => {
    const set = new Set();
    if (activeNode?.lineup?.slots) {
      for (const pid of Object.values(activeNode.lineup.slots)) {
        set.add(Number(pid));
      }
    }
    return set;
  }, [activeNode?.lineup?.slots]);

  // Compute candidate replacements
  const candidates = useMemo(() => {
    if (!isOpen || !replacedPlayer) return [];

    const list = [];
    for (const p of allPlayers) {
      // Exclude replaced player and current squad players
      if (p.id === replacedPlayer.id || currentSquadIds.has(p.id)) continue;

      // Position filter
      if (selectedPos !== 'ALL' && normalizePos(p.pos) !== normalizePos(selectedPos)) continue;

      // Search query
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        const match =
          p.name?.toLowerCase().includes(q) ||
          p.full_name?.toLowerCase().includes(q) ||
          p.team?.toLowerCase().includes(q);
        if (!match) continue;
      }

      // Budget filter
      const price = parsePrice(p.price);
      const isAffordable = price <= maxAffordablePrice + 0.001;
      if (affordableOnly && !isAffordable) continue;

      // Horizon xP sum
      let sumXp = 0;
      const fixtures = [];
      for (let gw = currentGw; gw <= endGw; gw++) {
        const proj = p.projections?.[`gw${gw}`] || {};
        sumXp += proj.total_xp ?? 0;
        if (fixtures.length < 5) {
          fixtures.push({
            gw,
            label: proj.fixture_label || p.team,
            diff: proj.difficulty ?? 3.0,
          });
        }
      }

      const deltaXp = sumXp - replacedSumXp;
      const deltaCost = Number((price - sellingPrice).toFixed(1));

      list.push({
        player: p,
        price,
        deltaCost,
        sumXp: Number(sumXp.toFixed(1)),
        deltaXp: Number(deltaXp.toFixed(1)),
        isAffordable,
        fixtures,
      });
    }

    // Default sort by deltaXp descending
    return list.sort((a, b) => b.deltaXp - a.deltaXp);
  }, [
    isOpen,
    allPlayers,
    replacedPlayer,
    selectedPos,
    searchQuery,
    affordableOnly,
    maxAffordablePrice,
    sellingPrice,
    currentGw,
    endGw,
    replacedSumXp,
    currentSquadIds,
  ]);

  const handleApplyTransfer = (candidate) => {
    if (!activeNode || !replacedSlot || !replacedPlayer) return;

    const oldSlots = activeNode.lineup?.slots || {};
    const newSlots = { ...oldSlots };
    newSlots[replacedSlot] = candidate.player.id;
    newSlots[String(replacedSlot)] = candidate.player.id;

    // Record transfer
    const newTransfer = {
      slot: replacedSlot,
      playerOutId: replacedPlayer.id,
      playerOutName: replacedPlayer.name || replacedPlayer.web_name || `P#${replacedPlayer.id}`,
      playerInId: candidate.player.id,
      playerInName: candidate.player.name || candidate.player.web_name || `P#${candidate.player.id}`,
      purchasePrice: candidate.price,
      sellingPrice: sellingPrice,
    };

    const existingTransfers = activeNode.transfers || [];
    const updatedTransfers = [...existingTransfers, newTransfer];

    // Compute economics
    const newBank = Number((currentBank - candidate.deltaCost).toFixed(1));
    const parentNode = activeNode?.parentId && activePlan?.nodes ? activePlan.nodes[activeNode.parentId] : null;
    const availFt = parentNode ? (parentNode.evaluation?.freeTransfersNext ?? 1) : (activePlan?.initialFreeTransfers ?? 1);
    const isFreeChip = activeNode?.chip === 'WC' || activeNode?.chip === 'FH' || activeNode?.chip === 'wildcard' || activeNode?.chip === 'freehit';
    const hitsTaken = isFreeChip ? 0 : Math.max(0, updatedTransfers.length - availFt);
    const remFt = isFreeChip ? 1 : Math.max(0, availFt - updatedTransfers.length);
    const freeTransfersNext = isFreeChip ? 1 : Math.min(5, remFt + 1);

    // Recalculate GW expected points
    let gwTotalXp = 0;
    const isTripleCaptain = activeNode?.chip === 'TC' || activeNode?.chip === 'triplecaptain';
    const isBenchBoost = activeNode?.chip === 'BB' || activeNode?.chip === 'benchboost';
    const maxSlot = isBenchBoost ? 15 : 11;
    for (let s = 1; s <= maxSlot; s++) {
      const pid = newSlots[s] || newSlots[String(s)];
      const pl = allPlayers.find((p) => p.id === pid) || {};
      const xp = pl.projections?.[`gw${currentGw}`]?.total_xp ?? 4.0;
      let multiplier = 1;
      if (s === activeNode.lineup?.captainSlot) {
        multiplier = isTripleCaptain ? 3 : 2;
      }
      gwTotalXp += xp * multiplier;
    }

    const netPoints = Number((gwTotalXp - hitsTaken * 4).toFixed(1));

    planActions.updateNode(activeNode.id, {
      lineup: {
        ...activeNode.lineup,
        slots: newSlots,
      },
      transfers: updatedTransfers,
      evaluation: {
        ...activeNode.evaluation,
        expectedPoints: Number(gwTotalXp.toFixed(1)),
        netPoints,
        bankRemaining: newBank,
        hitsTaken,
        freeTransfersNext,
      },
    }, true);

    onClose();
  };

  if (!isOpen || !replacedPlayer) return null;

  return (
    <div
      className="transfer-replacement-overlay"
      style={{
        position: 'fixed',
        top: 0,
        right: 0,
        bottom: 0,
        width: '460px',
        background: '#0d111c',
        borderLeft: '1.5px solid #1e2538',
        boxShadow: '-8px 0 24px rgba(0,0,0,0.7)',
        zIndex: 50,
        display: 'flex',
        flexDirection: 'column',
        fontFamily: "'Inter', sans-serif",
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '14px 18px',
          background: '#121520',
          borderBottom: '1px solid #1e2538',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div>
          <div style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.06em', color: '#94a3b8', fontWeight: 600 }}>
            Transfer Out
          </div>
          <div style={{ fontSize: '16px', fontWeight: 700, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>{replacedPlayer.name || replacedPlayer.full_name}</span>
            <span style={{ fontSize: '12px', color: '#38bdf8', fontFamily: "'JetBrains Mono', monospace" }}>
              £{sellingPrice.toFixed(1)}m
            </span>
          </div>
          <div style={{ fontSize: '12px', color: '#64748b' }}>
            Bank: £{currentBank.toFixed(1)}m · Max: £{maxAffordablePrice.toFixed(1)}m
          </div>
        </div>

        <button
          type="button"
          onClick={onClose}
          style={{
            background: '#1a202e',
            border: '1px solid #2d3748',
            color: '#cbd5e1',
            borderRadius: '6px',
            width: '32px',
            height: '32px',
            cursor: 'pointer',
            fontSize: '16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
          title="Close drawer"
        >
          ✕
        </button>
      </div>

      {/* Filter & Search Bar */}
      <div style={{ padding: '12px 18px', background: '#0a0b10', borderBottom: '1px solid #1e2538', display: 'flex', flexDirection: 'column', gap: '10px' }}>
        <input
          type="text"
          placeholder="Search candidates by name or team..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          style={{
            background: '#121520',
            border: '1px solid #1e2538',
            borderRadius: '6px',
            padding: '8px 12px',
            color: '#f8fafc',
            fontSize: '13px',
            outline: 'none',
          }}
        />

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          {/* Position Tabs */}
          <div style={{ display: 'flex', gap: '4px' }}>
            {['ALL', 'GKP', 'DEF', 'MID', 'FWD'].map((pos) => (
              <button
                key={pos}
                type="button"
                onClick={() => setSelectedPos(pos)}
                style={{
                  background: selectedPos === pos ? '#1e2538' : 'transparent',
                  color: selectedPos === pos ? '#38bdf8' : '#64748b',
                  border: selectedPos === pos ? '1px solid #38bdf8' : '1px solid #2d3748',
                  borderRadius: '4px',
                  padding: '3px 8px',
                  fontSize: '11px',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                {pos}
              </button>
            ))}
          </div>

          {/* Affordable Toggle */}
          <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: '#94a3b8', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={affordableOnly}
              onChange={(e) => setAffordableOnly(e.target.checked)}
            />
            Affordable only
          </label>
        </div>
      </div>

      {/* Candidates List */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '12px 18px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <div style={{ fontSize: '11px', color: '#64748b', display: 'flex', justifyContent: 'space-between', padding: '0 4px' }}>
          <span>Candidate ({candidates.length})</span>
          <span>Δ Sum xP (GW{currentGw}-{endGw})</span>
        </div>

        {candidates.map((c) => {
          const isPositive = c.deltaXp >= 0;
          return (
            <div
              key={c.player.id}
              style={{
                background: '#121520',
                border: '1px solid #1e2538',
                borderRadius: '8px',
                padding: '10px 12px',
                display: 'flex',
                flexDirection: 'column',
                gap: '6px',
                transition: 'border-color 0.15s ease',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ fontWeight: 700, fontSize: '14px', color: '#f8fafc' }}>
                      {c.player.name || c.player.web_name}
                    </span>
                    <span style={{ fontSize: '11px', color: '#64748b' }}>{c.player.team}</span>
                  </div>
                  <div style={{ fontSize: '11px', color: '#94a3b8', fontFamily: "'JetBrains Mono', monospace" }}>
                    £{c.price.toFixed(1)}m{' '}
                    <span style={{ color: c.deltaCost > 0 ? '#f59e0b' : '#10b981' }}>
                      ({c.deltaCost >= 0 ? `+£${c.deltaCost.toFixed(1)}` : `-£${Math.abs(c.deltaCost).toFixed(1)}`})
                    </span>
                  </div>
                </div>

                <div style={{ textAlign: 'right' }}>
                  <div
                    style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      fontWeight: 700,
                      fontSize: '16px',
                      color: isPositive ? '#10b981' : '#f43f5e',
                    }}
                  >
                    {isPositive ? `+${c.deltaXp}` : `${c.deltaXp}`}{' '}
                    <span style={{ fontSize: '10px', color: '#94a3b8', fontWeight: 400 }}>Δ xP</span>
                  </div>
                  <div style={{ fontSize: '11px', color: '#64748b', fontFamily: "'JetBrains Mono', monospace" }}>
                    {c.sumXp} xP total
                  </div>
                </div>
              </div>

              {/* Fixture preview strip & Action */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid #1a202e', paddingTop: '6px', marginTop: '2px' }}>
                <div style={{ display: 'flex', gap: '4px' }}>
                  {c.fixtures.map((f, fIdx) => (
                    <span
                      key={fIdx}
                      style={{
                        fontSize: '9px',
                        fontFamily: "'JetBrains Mono', monospace",
                        padding: '1px 4px',
                        borderRadius: '3px',
                        background: f.diff <= 2.5 ? 'rgba(16, 185, 129, 0.15)' : 'rgba(56, 189, 248, 0.15)',
                        color: f.diff <= 2.5 ? '#10b981' : '#38bdf8',
                      }}
                    >
                      {f.label}
                    </span>
                  ))}
                </div>

                <button
                  type="button"
                  disabled={!c.isAffordable}
                  onClick={() => handleApplyTransfer(c)}
                  style={{
                    background: c.isAffordable ? 'rgba(56, 189, 248, 0.15)' : '#1a202e',
                    color: c.isAffordable ? '#38bdf8' : '#64748b',
                    border: c.isAffordable ? '1px solid rgba(56, 189, 248, 0.4)' : '1px solid #2d3748',
                    borderRadius: '5px',
                    padding: '4px 10px',
                    fontSize: '11px',
                    fontWeight: 600,
                    cursor: c.isAffordable ? 'pointer' : 'not-allowed',
                  }}
                >
                  {c.isAffordable ? 'Transfer In' : 'Too Expensive'}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

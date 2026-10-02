import React, { useState, useEffect, useMemo } from 'react';
import { usePlanStore, planActions } from '../store/usePlanStore';

// Formation validation rule: GKP: 1, DEF: 3-5, MID: 2-5, FWD: 1-3
function isValidFormation(startersPosCount) {
  return (
    startersPosCount.GKP === 1 &&
    startersPosCount.DEF >= 3 &&
    startersPosCount.DEF <= 5 &&
    startersPosCount.MID >= 2 &&
    startersPosCount.MID <= 5 &&
    startersPosCount.FWD >= 1 &&
    startersPosCount.FWD <= 3
  );
}

export default function SquadPitchDrawer({ onOpenReplacementDrawer }) {
  const { activeNode, activePlan } = usePlanStore();
  const [isExpanded, setIsExpanded] = useState(false);
  const [selectedGw, setSelectedGw] = useState(6);
  const [playersData, setPlayersData] = useState({});
  const [swapSourceSlot, setSwapSourceSlot] = useState(null);
  const [validationError, setValidationError] = useState(null);

  // Sync selected GW with active node when active node changes
  useEffect(() => {
    if (activeNode?.gameweek) {
      setSelectedGw(activeNode.gameweek);
    }
  }, [activeNode?.id, activeNode?.gameweek]);

  // Load players data from /dashboard_data.json
  useEffect(() => {
    if (window.dashboardData?.players) {
      const map = {};
      for (const p of window.dashboardData.players) map[p.id] = p;
      setPlayersData(map);
      return;
    }

    fetch('/dashboard_data.json')
      .then((res) => res.json())
      .then((data) => {
        window.dashboardData = data;
        const map = {};
        for (const p of data.players || []) map[p.id] = p;
        setPlayersData(map);
      })
      .catch((err) => console.error('Failed to load dashboard_data.json:', err));
  }, []);

  const lineup = activeNode?.lineup || {
    slots: {},
    captainSlot: 1,
    viceCaptainSlot: 2,
    benchOrder: [12, 13, 14, 15],
  };

  const slots = lineup.slots || {};
  const captainSlot = lineup.captainSlot || 1;
  const viceCaptainSlot = lineup.viceCaptainSlot || 2;

  // Resolve player objects for each slot
  const squadPlayers = useMemo(() => {
    const list = [];
    for (let slot = 1; slot <= 15; slot++) {
      const pid = slots[slot] || slots[String(slot)];
      const player = playersData[pid] || {
        id: pid,
        name: `Player #${pid}`,
        pos: slot === 1 || slot === 12 ? 'GKP' : slot <= 5 ? 'DEF' : slot <= 10 ? 'MID' : 'FWD',
        price: 5.0,
      };

      const gwKey = `gw${selectedGw}`;
      const proj = player.projections?.[gwKey] || {};
      const xp = proj.total_xp ?? 4.0;
      const fixture = proj.fixture_label || player.team || '-';
      const difficulty = proj.difficulty ?? 3.0;

      list.push({
        slot,
        player,
        xp,
        fixture,
        difficulty,
        isStarter: slot <= 11,
        isCaptain: slot === captainSlot,
        isViceCaptain: slot === viceCaptainSlot,
      });
    }
    return list;
  }, [slots, captainSlot, viceCaptainSlot, playersData, selectedGw]);

  // Group starters by position
  const starters = squadPlayers.filter((p) => p.isStarter);
  const bench = squadPlayers.filter((p) => !p.isStarter);

  const startersByPos = useMemo(() => {
    return {
      GKP: starters.filter((p) => p.player.pos === 'GKP'),
      DEF: starters.filter((p) => p.player.pos === 'DEF'),
      MID: starters.filter((p) => p.player.pos === 'MID'),
      FWD: starters.filter((p) => p.player.pos === 'FWD'),
    };
  }, [starters]);

  // Handle substitution between two slots
  const handleSlotClick = (slot) => {
    setValidationError(null);
    if (!swapSourceSlot) {
      setSwapSourceSlot(slot);
      return;
    }

    if (swapSourceSlot === slot) {
      setSwapSourceSlot(null);
      return;
    }

    // Attempt swap
    const slotA = swapSourceSlot;
    const slotB = slot;

    const playerA = squadPlayers.find((p) => p.slot === slotA);
    const playerB = squadPlayers.find((p) => p.slot === slotB);
    if (!playerA || !playerB) {
      setSwapSourceSlot(null);
      return;
    }

    // Check if swap crosses starter/bench boundary
    if (playerA.isStarter !== playerB.isStarter) {
      // Simulate new starter position counts
      const counts = {
        GKP: startersByPos.GKP.length,
        DEF: startersByPos.DEF.length,
        MID: startersByPos.MID.length,
        FWD: startersByPos.FWD.length,
      };

      const starterPlayer = playerA.isStarter ? playerA : playerB;
      const benchPlayer = playerA.isStarter ? playerB : playerA;

      counts[starterPlayer.player.pos] -= 1;
      counts[benchPlayer.player.pos] = (counts[benchPlayer.player.pos] || 0) + 1;

      if (!isValidFormation(counts)) {
        setValidationError(
          `Invalid formation! Lineup requires 1 GKP, 3-5 DEFs, 2-5 MIDs, 1-3 FWDs.`
        );
        setSwapSourceSlot(null);
        return;
      }
    }

    // Execute swap in lineup
    const newSlots = { ...slots };
    const pidA = slots[slotA] || slots[String(slotA)];
    const pidB = slots[slotB] || slots[String(slotB)];

    newSlots[slotA] = pidB;
    newSlots[slotB] = pidA;
    newSlots[String(slotA)] = pidB;
    newSlots[String(slotB)] = pidA;

    let newCap = captainSlot;
    let newVice = viceCaptainSlot;
    if (captainSlot === slotA) newCap = slotB;
    else if (captainSlot === slotB) newCap = slotA;
    if (viceCaptainSlot === slotA) newVice = slotB;
    else if (viceCaptainSlot === slotB) newVice = slotA;

    const updatedLineup = {
      ...lineup,
      slots: newSlots,
      captainSlot: newCap,
      viceCaptainSlot: newVice,
    };

    // Recalculate expected points for node
    let totalXp = 0;
    for (let s = 1; s <= 11; s++) {
      const pid = newSlots[s] || newSlots[String(s)];
      const pl = playersData[pid];
      const gwXp = pl?.projections?.[`gw${activeNode?.gameweek || selectedGw}`]?.total_xp ?? 4.0;
      const multiplier = s === newCap ? 2 : 1;
      totalXp += gwXp * multiplier;
    }

    if (activeNode) {
      planActions.updateNode(activeNode.id, {
        lineup: updatedLineup,
        evaluation: {
          ...activeNode.evaluation,
          expectedPoints: Number(totalXp.toFixed(1)),
        },
      });
    }

    setSwapSourceSlot(null);
  };

  const handleSetCaptain = (slot, e) => {
    e.stopPropagation();
    if (!activeNode) return;
    let newVice = viceCaptainSlot;
    if (viceCaptainSlot === slot) {
      newVice = captainSlot;
    }
    const updatedLineup = { ...lineup, captainSlot: slot, viceCaptainSlot: newVice };
    planActions.updateNode(activeNode.id, { lineup: updatedLineup });
  };

  const handleSetVice = (slot, e) => {
    e.stopPropagation();
    if (!activeNode) return;
    let newCap = captainSlot;
    if (captainSlot === slot) {
      newCap = viceCaptainSlot;
    }
    const updatedLineup = { ...lineup, captainSlot: newCap, viceCaptainSlot: slot };
    planActions.updateNode(activeNode.id, { lineup: updatedLineup });
  };

  // Positional badge colors per DESIGN.md
  const posColor = {
    GKP: '#eab308',
    DEF: '#38bdf8',
    MID: '#10b981',
    FWD: '#f43f5e',
  };

  const fdrBadgeBg = (diff) => {
    if (diff <= 2.2) return 'rgba(16, 185, 129, 0.2)';
    if (diff <= 3.2) return 'rgba(56, 189, 248, 0.2)';
    if (diff <= 4.0) return 'rgba(245, 158, 11, 0.2)';
    return 'rgba(244, 63, 94, 0.25)';
  };

  const fdrBadgeColor = (diff) => {
    if (diff <= 2.2) return '#10b981';
    if (diff <= 3.2) return '#38bdf8';
    if (diff <= 4.0) return '#f59e0b';
    return '#f43f5e';
  };

  return (
    <div
      className={`planner-pitch-drawer ${isExpanded ? 'pitch-expanded' : 'pitch-docked'}`}
      style={{
        position: 'absolute',
        bottom: 0,
        left: 0,
        width: isExpanded ? '520px' : '420px',
        maxHeight: isExpanded ? '85vh' : '440px',
        background: '#0d111c',
        borderTop: '1.5px solid #1e2538',
        borderRight: '1.5px solid #1e2538',
        borderTopRightRadius: '12px',
        zIndex: 20,
        display: 'flex',
        flexDirection: 'column',
        boxShadow: '0 -8px 24px rgba(0,0,0,0.6)',
        transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
      }}
    >
      {/* Drawer Header & Scrubber */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '8px 14px',
          background: '#121520',
          borderBottom: '1px solid #1e2538',
          borderTopRightRadius: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            type="button"
            onClick={() => setSelectedGw((gw) => Math.max(1, gw - 1))}
            style={{
              background: '#1a202e',
              border: '1px solid #2d3748',
              color: '#f8fafc',
              borderRadius: '5px',
              padding: '4px 8px',
              fontSize: '11px',
              cursor: 'pointer',
            }}
            title="Previous Gameweek"
          >
            ◀
          </button>
          <span
            style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontWeight: 700,
              fontSize: '13px',
              color: '#38bdf8',
              padding: '2px 8px',
              background: '#0a0b10',
              borderRadius: '4px',
              border: '1px solid #1e2538',
            }}
          >
            GW {selectedGw}
          </span>
          <button
            type="button"
            onClick={() => setSelectedGw((gw) => Math.min(38, gw + 1))}
            style={{
              background: '#1a202e',
              border: '1px solid #2d3748',
              color: '#f8fafc',
              borderRadius: '5px',
              padding: '4px 8px',
              fontSize: '11px',
              cursor: 'pointer',
            }}
            title="Next Gameweek"
          >
            ▶
          </button>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {validationError && (
            <span style={{ fontSize: '11px', color: '#f43f5e', fontWeight: 600 }}>{validationError}</span>
          )}
          {swapSourceSlot && (
            <span style={{ fontSize: '11px', color: '#38bdf8', fontStyle: 'italic' }}>
              Select swap player...
            </span>
          )}
          <button
            type="button"
            onClick={() => setIsExpanded(!isExpanded)}
            style={{
              background: '#1a202e',
              border: '1px solid #2d3748',
              color: '#cbd5e1',
              borderRadius: '5px',
              padding: '4px 10px',
              fontSize: '11px',
              cursor: 'pointer',
            }}
            title={isExpanded ? 'Dock pitch drawer' : 'Expand pitch drawer'}
          >
            {isExpanded ? '▼ Dock' : '▲ Expand'}
          </button>
        </div>
      </div>

      {/* Pitch Surface Area */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '12px',
          background: 'linear-gradient(180deg, #061114 0%, #03080a 100%)',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px',
        }}
      >
        {/* Starters Pitch Area */}
        <div
          style={{
            border: '1px solid rgba(56, 189, 248, 0.15)',
            borderRadius: '10px',
            padding: '10px 6px',
            position: 'relative',
            background: 'radial-gradient(ellipse at center, rgba(16, 185, 129, 0.05) 0%, transparent 70%)',
            display: 'flex',
            flexDirection: 'column',
            gap: '10px',
          }}
        >
          {/* Halfway line & center circle aesthetic */}
          <div
            style={{
              position: 'absolute',
              top: '50%',
              left: '10%',
              right: '10%',
              height: '1px',
              background: 'rgba(56, 189, 248, 0.08)',
              pointerEvents: 'none',
            }}
          />

          {/* Positional Rows */}
          {['GKP', 'DEF', 'MID', 'FWD'].map((pos) => {
            const rowPlayers = startersByPos[pos] || [];
            return (
              <div
                key={pos}
                style={{
                  display: 'flex',
                  justifyContent: 'space-around',
                  alignItems: 'center',
                  zIndex: 2,
                }}
              >
                {rowPlayers.map((item) => {
                  const isSelected = swapSourceSlot === item.slot;
                  const finalXp = item.isCaptain ? item.xp * 2 : item.xp;

                  return (
                    <div
                      key={item.slot}
                      onClick={() => handleSlotClick(item.slot)}
                      style={{
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        cursor: 'pointer',
                        padding: '4px',
                        borderRadius: '6px',
                        border: isSelected ? '1.5px solid #38bdf8' : '1px solid transparent',
                        background: isSelected ? 'rgba(56, 189, 248, 0.15)' : 'transparent',
                        transition: 'all 0.15s ease',
                        width: '74px',
                      }}
                    >
                      {/* Kit & Captaincy Badges */}
                      <div style={{ position: 'relative', marginBottom: '2px' }}>
                        <div
                          style={{
                            width: '26px',
                            height: '26px',
                            borderRadius: '50%',
                            background: posColor[pos],
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontWeight: 700,
                            fontSize: '11px',
                            color: '#0a0b10',
                            border: '1.5px solid #f8fafc',
                          }}
                        >
                          {pos[0]}
                        </div>
                        {item.isCaptain && (
                          <span
                            onClick={(e) => handleSetVice(item.slot, e)}
                            style={{
                              position: 'absolute',
                              top: '-4px',
                              right: '-6px',
                              background: '#0a0b10',
                              color: '#38bdf8',
                              border: '1px solid #38bdf8',
                              borderRadius: '50%',
                              width: '14px',
                              height: '14px',
                              fontSize: '9px',
                              fontWeight: 800,
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                            }}
                            title="Captain (Click to make Vice)"
                          >
                            C
                          </span>
                        )}
                        {item.isViceCaptain && (
                          <span
                            onClick={(e) => handleSetCaptain(item.slot, e)}
                            style={{
                              position: 'absolute',
                              top: '-4px',
                              right: '-6px',
                              background: '#0a0b10',
                              color: '#eab308',
                              border: '1px solid #eab308',
                              borderRadius: '50%',
                              width: '14px',
                              height: '14px',
                              fontSize: '9px',
                              fontWeight: 800,
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                            }}
                            title="Vice-Captain (Click to make Captain)"
                          >
                            V
                          </span>
                        )}
                      </div>

                      {/* Player Name */}
                      <div
                        style={{
                          fontSize: '11px',
                          fontWeight: 600,
                          color: '#f8fafc',
                          whiteSpace: 'nowrap',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          maxWidth: '70px',
                          textAlign: 'center',
                        }}
                      >
                        {item.player.name || item.player.web_name || `P#${item.player.id}`}
                      </div>

                      {/* Fixture Pill */}
                      <div
                        style={{
                          fontSize: '9px',
                          fontFamily: "'JetBrains Mono', monospace",
                          padding: '1px 4px',
                          borderRadius: '3px',
                          background: fdrBadgeBg(item.difficulty),
                          color: fdrBadgeColor(item.difficulty),
                          marginBottom: '2px',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {item.fixture}
                      </div>

                      {/* xP Pill & Replace Action */}
                      <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <div
                          style={{
                            fontSize: '11px',
                            fontWeight: 700,
                            fontFamily: "'JetBrains Mono', monospace",
                            color: item.isCaptain ? '#38bdf8' : '#cbd5e1',
                          }}
                        >
                          {finalXp.toFixed(1)}
                        </div>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            if (onOpenReplacementDrawer) {
                              onOpenReplacementDrawer(item.slot, item.player);
                            }
                          }}
                          style={{
                            background: 'rgba(56, 189, 248, 0.1)',
                            border: '1px solid rgba(56, 189, 248, 0.25)',
                            color: '#38bdf8',
                            borderRadius: '3px',
                            padding: '0 3px',
                            fontSize: '9px',
                            cursor: 'pointer',
                          }}
                          title="Transfer replace player"
                        >
                          ⇄
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>

        {/* Bench Area */}
        <div
          style={{
            background: '#0d141e',
            border: '1px dashed #1e2538',
            borderRadius: '8px',
            padding: '8px 10px',
          }}
        >
          <div
            style={{
              fontSize: '10px',
              textTransform: 'uppercase',
              letterSpacing: '0.05em',
              color: '#64748b',
              fontWeight: 600,
              marginBottom: '6px',
            }}
          >
            Substitutes Bench (In Priority Order)
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            {bench.map((item, bIdx) => {
              const isSelected = swapSourceSlot === item.slot;
              return (
                <div
                  key={item.slot}
                  onClick={() => handleSlotClick(item.slot)}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    cursor: 'pointer',
                    padding: '4px',
                    borderRadius: '6px',
                    border: isSelected ? '1.5px solid #38bdf8' : '1px solid transparent',
                    background: isSelected ? 'rgba(56, 189, 248, 0.15)' : 'transparent',
                    width: '68px',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '2px' }}>
                    <span style={{ fontSize: '9px', color: '#64748b', fontWeight: 700 }}>
                      {bIdx === 0 ? 'GK' : `B${bIdx}`}
                    </span>
                    <div
                      style={{
                        width: '18px',
                        height: '18px',
                        borderRadius: '50%',
                        background: posColor[item.player.pos],
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '9px',
                        fontWeight: 700,
                        color: '#0a0b10',
                      }}
                    >
                      {item.player.pos[0]}
                    </div>
                  </div>
                  <div
                    style={{
                      fontSize: '10px',
                      color: '#94a3b8',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      maxWidth: '64px',
                    }}
                  >
                    {item.player.name || item.player.web_name || `P#${item.player.id}`}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <div style={{ fontSize: '10px', fontFamily: "'JetBrains Mono', monospace", color: '#64748b' }}>
                      {item.xp.toFixed(1)}
                    </div>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        if (onOpenReplacementDrawer) {
                          onOpenReplacementDrawer(item.slot, item.player);
                        }
                      }}
                      style={{
                        background: 'rgba(56, 189, 248, 0.1)',
                        border: '1px solid rgba(56, 189, 248, 0.25)',
                        color: '#38bdf8',
                        borderRadius: '3px',
                        padding: '0 3px',
                        fontSize: '9px',
                        cursor: 'pointer',
                      }}
                      title="Transfer replace player"
                    >
                      ⇄
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

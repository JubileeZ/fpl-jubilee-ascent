import React, { useMemo } from 'react';
import { usePlanStore } from '../store/usePlanStore';
import { normalizePos } from './SquadPitchDrawer';

const posColor = {
  GKP: '#eab308',
  DEF: '#38bdf8',
  MID: '#10b981',
  FWD: '#f43f5e',
};

const fdrColor = (diff) => {
  if (diff <= 2.2) return { bg: 'rgba(16, 185, 129, 0.2)', text: '#10b981' };
  if (diff <= 3.2) return { bg: 'rgba(56, 189, 248, 0.2)', text: '#38bdf8' };
  if (diff <= 4.0) return { bg: 'rgba(245, 158, 11, 0.2)', text: '#f59e0b' };
  return { bg: 'rgba(244, 63, 94, 0.25)', text: '#f43f5e' };
};

export default function SquadProjectionsTable({ onSelectPlayer }) {
  const { activeNode, activePlan } = usePlanStore();
  const [playersMap, setPlayersMap] = React.useState(() => {
    const map = {};
    for (const p of window.dashboardData?.players || []) map[p.id] = p;
    return map;
  });

  React.useEffect(() => {
    if (window.dashboardData?.players && Object.keys(playersMap).length > 0) {
      return;
    }
    if (window.dashboardData?.players) {
      const map = {};
      for (const p of window.dashboardData.players) map[p.id] = p;
      setPlayersMap(map);
      return;
    }
    fetch('/dashboard_data.json')
      .then((r) => r.json())
      .then((data) => {
        window.dashboardData = data;
        const map = {};
        for (const p of data.players || []) map[p.id] = p;
        setPlayersMap(map);
      })
      .catch(console.error);
  }, []);

  const lineup = activeNode?.lineup || { slots: {}, captainSlot: 1, viceCaptainSlot: 2 };
  const currentGw = activeNode?.gameweek || activePlan?.startGameweek || 6;
  const horizon = activePlan?.horizonGameweeks || 5;

  const rows = useMemo(() => {
    const list = [];
    const slots = lineup.slots || {};

    for (let slot = 1; slot <= 15; slot++) {
      const pid = slots[slot] || slots[String(slot)];
      const raw = playersMap[pid];
      const defaultPos = slot === 1 || slot === 12 ? 'GKP' : slot <= 5 ? 'DEF' : slot <= 10 ? 'MID' : 'FWD';
      const pos = raw ? normalizePos(raw.pos) : defaultPos;
      const name = raw?.name || raw?.full_name || `Player #${pid}`;
      const team = raw?.team || '-';
      const price = raw?.price || 5.0;

      const gwKey = `gw${currentGw}`;
      const proj = raw?.projections?.[gwKey] || {};
      const xp = proj.total_xp ?? 4.0;
      const fixture = proj.fixture_label || team;
      const difficulty = proj.difficulty ?? 3.0;

      let sumHorizonXp = 0;
      for (let g = currentGw; g < currentGw + horizon; g++) {
        sumHorizonXp += raw?.projections?.[`gw${g}`]?.total_xp ?? 0;
      }

      const isStarter = slot <= 11;
      const isCaptain = slot === lineup.captainSlot;
      const isViceCaptain = slot === lineup.viceCaptainSlot;
      const finalGwXp = isCaptain ? xp * 2 : xp;

      list.push({
        slot,
        pid,
        name,
        team,
        pos,
        price,
        fixture,
        difficulty,
        xp,
        finalGwXp,
        sumHorizonXp,
        isStarter,
        isCaptain,
        isViceCaptain,
        raw,
      });
    }

    return list;
  }, [lineup, playersMap, currentGw, horizon]);

  const starters = rows.filter((r) => r.isStarter);
  const bench = rows.filter((r) => !r.isStarter);

  const startersTotalXp = starters.reduce((acc, r) => acc + r.finalGwXp, 0);
  const benchTotalXp = bench.reduce((acc, r) => acc + r.xp, 0);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Summary KPI Cards */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: '8px',
          padding: '12px 14px',
          background: '#0d111c',
          borderBottom: '1px solid #1e2538',
        }}
      >
        <div style={{ background: '#121520', border: '1px solid #1e2538', borderRadius: '6px', padding: '8px 10px' }}>
          <div style={{ fontSize: '10px', textTransform: 'uppercase', color: '#94a3b8', fontWeight: 600 }}>Starting XI xP</div>
          <div style={{ fontSize: '18px', fontWeight: 700, color: '#38bdf8', fontFamily: "'JetBrains Mono', monospace" }}>
            {startersTotalXp.toFixed(1)} <span style={{ fontSize: '11px', color: '#64748b' }}>pts</span>
          </div>
        </div>

        <div style={{ background: '#121520', border: '1px solid #1e2538', borderRadius: '6px', padding: '8px 10px' }}>
          <div style={{ fontSize: '10px', textTransform: 'uppercase', color: '#94a3b8', fontWeight: 600 }}>Bench Reserve</div>
          <div style={{ fontSize: '18px', fontWeight: 700, color: '#10b981', fontFamily: "'JetBrains Mono', monospace" }}>
            {benchTotalXp.toFixed(1)} <span style={{ fontSize: '11px', color: '#64748b' }}>pts</span>
          </div>
        </div>

        <div style={{ background: '#121520', border: '1px solid #1e2538', borderRadius: '6px', padding: '8px 10px' }}>
          <div style={{ fontSize: '10px', textTransform: 'uppercase', color: '#94a3b8', fontWeight: 600 }}>Bank ITB</div>
          <div style={{ fontSize: '18px', fontWeight: 700, color: '#f8fafc', fontFamily: "'JetBrains Mono', monospace" }}>
            £{(activeNode?.evaluation?.bankRemaining ?? activePlan?.initialBank ?? 0.0).toFixed(1)}m
          </div>
        </div>
      </div>

      {/* Players Data Table */}
      <div style={{ flex: 1, overflowY: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', textAlign: 'left' }}>
          <thead style={{ position: 'sticky', top: 0, background: '#121520', zIndex: 5, borderBottom: '1px solid #1e2538' }}>
            <tr>
              <th style={{ padding: '8px 10px', color: '#94a3b8', fontWeight: 600 }}>Player</th>
              <th style={{ padding: '8px 6px', color: '#94a3b8', fontWeight: 600 }}>Opp</th>
              <th style={{ padding: '8px 6px', color: '#94a3b8', fontWeight: 600, textAlign: 'right' }}>£m</th>
              <th style={{ padding: '8px 6px', color: '#94a3b8', fontWeight: 600, textAlign: 'right' }}>GW{currentGw} xP</th>
              <th style={{ padding: '8px 10px', color: '#94a3b8', fontWeight: 600, textAlign: 'right' }}>{horizon}GW Σ</th>
            </tr>
          </thead>
          <tbody>
            {/* Starters Section Header */}
            <tr style={{ background: 'rgba(56, 189, 248, 0.05)' }}>
              <td colSpan={5} style={{ padding: '5px 10px', fontSize: '10px', fontWeight: 700, color: '#38bdf8', letterSpacing: '0.05em' }}>
                STARTING XI
              </td>
            </tr>

            {starters.map((item) => {
              const fdr = fdrColor(item.difficulty);
              return (
                <tr
                  key={item.slot}
                  onClick={() => onSelectPlayer && onSelectPlayer(item.slot, item.raw)}
                  style={{
                    borderBottom: '1px solid #1a202e',
                    cursor: onSelectPlayer ? 'pointer' : 'default',
                    transition: 'background 0.15s ease',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = '#151a28')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                >
                  <td style={{ padding: '7px 10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span
                      style={{
                        fontSize: '9px',
                        fontWeight: 700,
                        color: '#0a0b10',
                        background: posColor[item.pos] || '#38bdf8',
                        padding: '1px 4px',
                        borderRadius: '3px',
                      }}
                    >
                      {item.pos}
                    </span>
                    <span style={{ fontWeight: 600, color: '#f8fafc' }}>{item.name}</span>
                    {item.isCaptain && (
                      <span style={{ fontSize: '9px', fontWeight: 700, background: '#38bdf8', color: '#0a0b10', padding: '1px 3px', borderRadius: '3px' }}>
                        C
                      </span>
                    )}
                    {item.isViceCaptain && (
                      <span style={{ fontSize: '9px', fontWeight: 700, background: '#1e2538', color: '#94a3b8', padding: '1px 3px', borderRadius: '3px', border: '1px solid #334155' }}>
                        V
                      </span>
                    )}
                  </td>
                  <td style={{ padding: '7px 6px' }}>
                    <span
                      style={{
                        background: fdr.bg,
                        color: fdr.text,
                        padding: '2px 5px',
                        borderRadius: '3px',
                        fontSize: '10px',
                        fontWeight: 600,
                        fontFamily: "'JetBrains Mono', monospace",
                      }}
                    >
                      {item.fixture}
                    </span>
                  </td>
                  <td style={{ padding: '7px 6px', textAlign: 'right', fontFamily: "'JetBrains Mono', monospace", color: '#94a3b8' }}>
                    £{item.price.toFixed(1)}
                  </td>
                  <td style={{ padding: '7px 6px', textAlign: 'right', fontFamily: "'JetBrains Mono', monospace", fontWeight: 700, color: item.isCaptain ? '#38bdf8' : '#f8fafc' }}>
                    {item.finalGwXp.toFixed(1)}
                  </td>
                  <td style={{ padding: '7px 10px', textAlign: 'right', fontFamily: "'JetBrains Mono', monospace", color: '#10b981' }}>
                    {item.sumHorizonXp.toFixed(1)}
                  </td>
                </tr>
              );
            })}

            {/* Bench Section Header */}
            <tr style={{ background: 'rgba(100, 116, 139, 0.08)' }}>
              <td colSpan={5} style={{ padding: '5px 10px', fontSize: '10px', fontWeight: 700, color: '#94a3b8', letterSpacing: '0.05em' }}>
                SUBSTITUTES BENCH
              </td>
            </tr>

            {bench.map((item, bIdx) => {
              const fdr = fdrColor(item.difficulty);
              return (
                <tr
                  key={item.slot}
                  onClick={() => onSelectPlayer && onSelectPlayer(item.slot, item.raw)}
                  style={{
                    borderBottom: '1px solid #1a202e',
                    opacity: 0.85,
                    cursor: onSelectPlayer ? 'pointer' : 'default',
                    transition: 'background 0.15s ease',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = '#151a28')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                >
                  <td style={{ padding: '6px 10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ fontSize: '9px', color: '#64748b', fontWeight: 700 }}>
                      {bIdx === 0 ? 'GK' : `B${bIdx}`}
                    </span>
                    <span
                      style={{
                        fontSize: '9px',
                        fontWeight: 700,
                        color: '#0a0b10',
                        background: posColor[item.pos] || '#38bdf8',
                        padding: '1px 4px',
                        borderRadius: '3px',
                      }}
                    >
                      {item.pos}
                    </span>
                    <span style={{ fontWeight: 500, color: '#cbd5e1' }}>{item.name}</span>
                  </td>
                  <td style={{ padding: '6px 6px' }}>
                    <span
                      style={{
                        background: fdr.bg,
                        color: fdr.text,
                        padding: '2px 5px',
                        borderRadius: '3px',
                        fontSize: '10px',
                        fontWeight: 600,
                        fontFamily: "'JetBrains Mono', monospace",
                      }}
                    >
                      {item.fixture}
                    </span>
                  </td>
                  <td style={{ padding: '6px 6px', textAlign: 'right', fontFamily: "'JetBrains Mono', monospace", color: '#64748b' }}>
                    £{item.price.toFixed(1)}
                  </td>
                  <td style={{ padding: '6px 6px', textAlign: 'right', fontFamily: "'JetBrains Mono', monospace", color: '#94a3b8' }}>
                    {item.xp.toFixed(1)}
                  </td>
                  <td style={{ padding: '6px 10px', textAlign: 'right', fontFamily: "'JetBrains Mono', monospace", color: '#64748b' }}>
                    {item.sumHorizonXp.toFixed(1)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

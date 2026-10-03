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

export default function SquadFixturesTable() {
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

  const lineup = activeNode?.lineup || { slots: {} };
  const currentGw = activeNode?.gameweek || activePlan?.startGameweek || 6;
  const horizon = activePlan?.horizonGameweeks || 5;

  const gameweeks = useMemo(() => {
    const list = [];
    for (let g = currentGw; g < currentGw + horizon; g++) {
      list.push(g);
    }
    return list;
  }, [currentGw, horizon]);

  const squadPlayers = useMemo(() => {
    const list = [];
    const slots = lineup.slots || {};
    for (let slot = 1; slot <= 15; slot++) {
      const pid = slots[slot] || slots[String(slot)];
      const raw = playersMap[pid];
      const defaultPos = slot === 1 || slot === 12 ? 'GKP' : slot <= 5 ? 'DEF' : slot <= 10 ? 'MID' : 'FWD';
      const pos = raw ? normalizePos(raw.pos) : defaultPos;
      const name = raw?.name || raw?.full_name || `Player #${pid}`;
      const team = raw?.team || '-';

      list.push({
        slot,
        pid,
        name,
        team,
        pos,
        raw,
        isStarter: slot <= 11,
      });
    }
    return list;
  }, [lineup, playersMap]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <div style={{ padding: '10px 14px', background: '#0d111c', borderBottom: '1px solid #1e2538' }}>
        <div style={{ fontSize: '13px', fontWeight: 600, color: '#f8fafc' }}>
          Squad Matchup Matrix (GW{currentGw}–GW{currentGw + horizon - 1})
        </div>
        <div style={{ fontSize: '11px', color: '#94a3b8' }}>
          Modified FDR ratings: Green = Favorable (≤2.2), Cyan = Average (≤3.2), Amber = Tough (≤4.0), Rose = Severe (&gt;4.0)
        </div>
      </div>

      <div style={{ flex: 1, overflowX: 'auto', overflowY: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '11px', textAlign: 'left' }}>
          <thead style={{ position: 'sticky', top: 0, background: '#121520', zIndex: 5, borderBottom: '1px solid #1e2538' }}>
            <tr>
              <th style={{ padding: '8px 10px', color: '#94a3b8', fontWeight: 600 }}>Player</th>
              {gameweeks.map((gw) => (
                <th key={gw} style={{ padding: '8px 6px', color: '#38bdf8', fontWeight: 600, textAlign: 'center' }}>
                  GW{gw}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {squadPlayers.map((item) => (
              <tr key={item.slot} style={{ borderBottom: '1px solid #1a202e' }}>
                <td style={{ padding: '6px 10px', display: 'flex', alignItems: 'center', gap: '6px', whiteSpace: 'nowrap' }}>
                  <span
                    style={{
                      fontSize: '9px',
                      fontWeight: 700,
                      color: '#0a0b10',
                      background: posColor[item.pos] || '#38bdf8',
                      padding: '1px 3px',
                      borderRadius: '3px',
                    }}
                  >
                    {item.pos}
                  </span>
                  <span style={{ fontWeight: 600, color: item.isStarter ? '#f8fafc' : '#94a3b8' }}>
                    {item.name}
                  </span>
                  <span style={{ fontSize: '10px', color: '#64748b' }}>({item.team})</span>
                </td>

                {gameweeks.map((gw) => {
                  const proj = item.raw?.projections?.[`gw${gw}`] || {};
                  const fixture = proj.fixture_label || '-';
                  const diff = proj.difficulty ?? 3.0;
                  const fdr = fdrColor(diff);

                  return (
                    <td key={gw} style={{ padding: '4px 6px', textAlign: 'center' }}>
                      <span
                        style={{
                          display: 'inline-block',
                          background: fdr.bg,
                          color: fdr.text,
                          padding: '2px 6px',
                          borderRadius: '4px',
                          fontSize: '10px',
                          fontWeight: 600,
                          fontFamily: "'JetBrains Mono', monospace",
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {fixture}
                      </span>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

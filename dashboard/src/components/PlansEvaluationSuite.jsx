import React, { useState, useMemo, useEffect } from 'react';
import { usePlanStore, planActions } from '../store/usePlanStore';

// Normal distribution PDF: N(mu, sigma^2)
function gaussianPdf(x, mu, sigma) {
  if (sigma <= 0) return 0;
  const factor = 1 / (sigma * Math.sqrt(2 * Math.PI));
  const exp = Math.exp(-Math.pow(x - mu, 2) / (2 * Math.pow(sigma, 2)));
  return factor * exp;
}

// Standard normal CDF approximation (Erf approximation)
function normalCdf(x, mu, sigma) {
  if (sigma <= 0) return 0;
  const z = (x - mu) / sigma;
  const t = 1 / (1 + 0.2316419 * Math.abs(z));
  const d = 0.3989423 * Math.exp((-z * z) / 2);
  let p = d * t * (0.3193815 + t * (-0.3565638 + t * (1.781478 + t * (-1.821256 + t * 1.330274))));
  if (z > 0) p = 1 - p;
  return 1 - p;
}

const PALETTE = ['#38bdf8', '#10b981', '#f59e0b', '#a855f7', '#f43f5e', '#06b6d4'];

const CHIP_BADGES = {
  wildcard: { label: 'WC', bg: 'rgba(239, 68, 68, 0.2)', border: '#ef4444', text: '#fca5a5' },
  freehit: { label: 'FH', bg: 'rgba(59, 130, 246, 0.2)', border: '#3b82f6', text: '#93c5fd' },
  triplecaptain: { label: 'TC', bg: 'rgba(245, 158, 11, 0.2)', border: '#f59e0b', text: '#fcd34d' },
  benchboost: { label: 'BB', bg: 'rgba(16, 185, 129, 0.2)', border: '#10b981', text: '#6ee7b7' },
};

export default function PlansEvaluationSuite() {
  const { plans, activePlanId } = usePlanStore();
  const [subView, setSubView] = useState('comparison'); // 'comparison' | 'scatter' | 'distribution'
  const [scatterXAxis, setScatterXAxis] = useState('hits'); // 'hits' | 'bank' | 'sigma'
  const [hoveredPoint, setHoveredPoint] = useState(null);
  const [playersMap, setPlayersMap] = useState({});

  useEffect(() => {
    fetch('/dashboard_data.json')
      .then((r) => r.json())
      .then((data) => {
        const map = {};
        (data.players || []).forEach((p) => {
          if (p.id) {
            map[p.id] = p.name || p.web_name || `P#${p.id}`;
          }
        });
        setPlayersMap(map);
      })
      .catch((err) => console.warn('Could not load player names for evaluation table:', err));
  }, []);

  // Extract all branch paths and scenarios
  const scenarioOutcomes = useMemo(() => {
    const list = [];
    plans.forEach((plan, planIdx) => {
      const nodes = plan.nodes || {};
      const color = PALETTE[planIdx % PALETTE.length];

      // Find leaf nodes
      const leafNodes = Object.values(nodes).filter(
        (n) => n.parentId && (!n.childIds || n.childIds.length === 0)
      );

      if (leafNodes.length === 0) {
        const root = nodes[plan.rootNodeId];
        if (root) {
          const evalData = root.evaluation || {};
          const transfers = root.transfers || [];
          const captainSlot = root.lineup?.captainSlot || 1;
          const captainId = root.lineup?.slots ? root.lineup.slots[String(captainSlot)] : null;
          list.push({
            planId: plan.id,
            planName: plan.name,
            nodeId: root.id,
            nodeTitle: root.title || plan.name,
            leafTitle: root.title || 'Baseline',
            gameweek: root.gameweek,
            mu: evalData.netPoints ?? evalData.cumulativePoints ?? 0.0,
            sigma: evalData.pointsVariance && evalData.pointsVariance > 0 ? evalData.pointsVariance : 11.5,
            hits: evalData.hitsTaken ?? 0,
            hitCost: (evalData.hitsTaken ?? 0) * 4,
            bank: evalData.bankRemaining ?? 0.0,
            freeTransfers: evalData.freeTransfersNext ?? 1,
            transfers,
            chip: root.chip || null,
            captainSlot,
            captainId,
            color,
            isCurrent: plan.id === activePlanId,
          });
        }
      } else {
        leafNodes.forEach((leaf) => {
          const evalData = leaf.evaluation || {};
          const transfers = leaf.transfers || [];
          const captainSlot = leaf.lineup?.captainSlot || 1;
          const captainId = leaf.lineup?.slots ? leaf.lineup.slots[String(captainSlot)] : null;
          list.push({
            planId: plan.id,
            planName: plan.name,
            nodeId: leaf.id,
            nodeTitle: `${plan.name} · ${leaf.title || `GW${leaf.gameweek}`}`,
            leafTitle: leaf.title || `GW${leaf.gameweek}`,
            gameweek: leaf.gameweek,
            mu: evalData.netPoints ?? evalData.cumulativePoints ?? 0.0,
            sigma: evalData.pointsVariance && evalData.pointsVariance > 0 ? evalData.pointsVariance : 11.5,
            hits: evalData.hitsTaken ?? 0,
            hitCost: (evalData.hitsTaken ?? 0) * 4,
            bank: evalData.bankRemaining ?? 0.0,
            freeTransfers: evalData.freeTransfersNext ?? 1,
            transfers,
            chip: leaf.chip || null,
            captainSlot,
            captainId,
            color,
            isCurrent: plan.id === activePlanId,
          });
        });
      }
    });

    return list;
  }, [plans, activePlanId]);

  // Compute Frontier based on active X-axis
  const frontierPoints = useMemo(() => {
    if (scenarioOutcomes.length === 0) return [];
    if (scatterXAxis === 'hits') {
      // Less hits is better, higher points is better
      const sorted = [...scenarioOutcomes].sort((a, b) => a.hitCost - b.hitCost);
      const frontier = [];
      let maxMu = -Infinity;
      for (const pt of sorted) {
        if (pt.mu > maxMu) {
          frontier.push(pt);
          maxMu = pt.mu;
        }
      }
      return frontier;
    }
    if (scatterXAxis === 'bank') {
      // More bank is better, higher points is better
      const sorted = [...scenarioOutcomes].sort((a, b) => a.bank - b.bank);
      const frontier = [];
      let maxMu = -Infinity;
      for (const pt of sorted) {
        if (pt.mu > maxMu) {
          frontier.push(pt);
          maxMu = pt.mu;
        }
      }
      return frontier;
    }
    // Sigma
    const sorted = [...scenarioOutcomes].sort((a, b) => a.sigma - b.sigma);
    const frontier = [];
    let maxMu = -Infinity;
    for (const pt of sorted) {
      if (pt.mu > maxMu) {
        frontier.push(pt);
        maxMu = pt.mu;
      }
    }
    return frontier;
  }, [scenarioOutcomes, scatterXAxis]);

  // Chart dimensions & scaling
  const width = 640;
  const height = 300;
  const padding = { top: 30, right: 30, bottom: 44, left: 55 };

  const scatterMinMu = Math.min(...scenarioOutcomes.map((p) => p.mu), 30) - 5;
  const scatterMaxMu = Math.max(...scenarioOutcomes.map((p) => p.mu), 80) + 10;

  const getXVal = (pt) => {
    if (scatterXAxis === 'hits') return pt.hitCost;
    if (scatterXAxis === 'bank') return pt.bank;
    return pt.sigma;
  };

  const xVals = scenarioOutcomes.map(getXVal);
  const minX = Math.min(...xVals, 0);
  const maxX = Math.max(...xVals, scatterXAxis === 'hits' ? 8 : (scatterXAxis === 'bank' ? 3.0 : 15.0));

  const scaleX = (val) => {
    const range = maxX - minX || 1.0;
    return padding.left + ((val - minX) / range) * (width - padding.left - padding.right);
  };

  const scaleY = (mu) => {
    const range = scatterMaxMu - scatterMinMu || 1.0;
    return height - padding.bottom - ((mu - scatterMinMu) / range) * (height - padding.top - padding.bottom);
  };

  // Gaussian density curve points
  const distRange = [];
  for (let x = 20; x <= 120; x += 1.5) {
    distRange.push(x);
  }

  const handleSelectScenario = (pt) => {
    planActions.setActivePlan(pt.planId);
    planActions.setActiveNode(pt.nodeId);
  };

  return (
    <div
      className="plans-evaluation-suite"
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        background: '#0d111c',
        color: '#f8fafc',
        fontFamily: "'Inter', sans-serif",
      }}
    >
      {/* Sub-view Navigation */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '12px 18px',
          background: '#121520',
          borderBottom: '1px solid #1e2538',
        }}
      >
        <div style={{ display: 'flex', gap: '6px' }}>
          <button
            type="button"
            onClick={() => setSubView('comparison')}
            style={{
              background: subView === 'comparison' ? '#1e2538' : 'transparent',
              color: subView === 'comparison' ? '#38bdf8' : '#94a3b8',
              border: subView === 'comparison' ? '1px solid #38bdf8' : '1px solid #2d3748',
              borderRadius: '6px',
              padding: '6px 12px',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Multi-Plan Comparison Table
          </button>
          <button
            type="button"
            onClick={() => setSubView('scatter')}
            style={{
              background: subView === 'scatter' ? '#1e2538' : 'transparent',
              color: subView === 'scatter' ? '#38bdf8' : '#94a3b8',
              border: subView === 'scatter' ? '1px solid #38bdf8' : '1px solid #2d3748',
              borderRadius: '6px',
              padding: '6px 12px',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Trade-off Frontier
          </button>
          <button
            type="button"
            onClick={() => setSubView('distribution')}
            style={{
              background: subView === 'distribution' ? '#1e2538' : 'transparent',
              color: subView === 'distribution' ? '#38bdf8' : '#94a3b8',
              border: subView === 'distribution' ? '1px solid #38bdf8' : '1px solid #2d3748',
              borderRadius: '6px',
              padding: '6px 12px',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            Score Distributions (Experimental)
          </button>
        </div>

        <div style={{ fontSize: '11px', color: '#64748b' }}>
          Comparing {scenarioOutcomes.length} scenario outcomes across {plans.length} plan branches
        </div>
      </div>

      {/* Main View Body */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '16px 20px' }}>
        {subView === 'comparison' && (
          <div>
            <div style={{ marginBottom: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
              <div>
                <h3 style={{ fontSize: '15px', fontWeight: 600, margin: '0 0 4px 0', color: '#f8fafc' }}>
                  Multi-Plan Evaluation Matrix
                </h3>
                <p style={{ fontSize: '12px', color: '#94a3b8', margin: 0 }}>
                  Deterministic MILP evaluation across branches: Net Points, Transfer Penalties, Bank, and Tactical Actions.
                </p>
              </div>
            </div>

            <div
              style={{
                background: '#121520',
                border: '1px solid #1e2538',
                borderRadius: '8px',
                overflowX: 'auto',
              }}
            >
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
                <thead>
                  <tr style={{ background: '#0a0b10', borderBottom: '1px solid #1e2538' }}>
                    <th style={{ padding: '10px 14px', color: '#94a3b8', fontWeight: 600, fontSize: '11px' }}>SCENARIO / BRANCH</th>
                    <th style={{ padding: '10px 14px', color: '#94a3b8', fontWeight: 600, fontSize: '11px' }}>NET XP</th>
                    <th style={{ padding: '10px 14px', color: '#94a3b8', fontWeight: 600, fontSize: '11px' }}>HITS TAKEN</th>
                    <th style={{ padding: '10px 14px', color: '#94a3b8', fontWeight: 600, fontSize: '11px' }}>BANK ITB</th>
                    <th style={{ padding: '10px 14px', color: '#94a3b8', fontWeight: 600, fontSize: '11px' }}>NEXT FTS</th>
                    <th style={{ padding: '10px 14px', color: '#94a3b8', fontWeight: 600, fontSize: '11px' }}>CAPTAIN</th>
                    <th style={{ padding: '10px 14px', color: '#94a3b8', fontWeight: 600, fontSize: '11px' }}>TRANSFERS</th>
                    <th style={{ padding: '10px 14px', color: '#94a3b8', fontWeight: 600, fontSize: '11px', textAlign: 'right' }}>ACTION</th>
                  </tr>
                </thead>
                <tbody>
                  {scenarioOutcomes.map((pt, idx) => {
                    const captainName = pt.captainId && playersMap[pt.captainId] ? playersMap[pt.captainId] : `Slot #${pt.captainSlot}`;
                    const chipKey = pt.chip ? String(pt.chip).toLowerCase().replace(/[^a-z]/g, '') : null;
                    const chipBadge = chipKey && CHIP_BADGES[chipKey] ? CHIP_BADGES[chipKey] : (pt.chip ? { label: String(pt.chip).toUpperCase(), bg: 'rgba(56, 189, 248, 0.2)', border: '#38bdf8', text: '#38bdf8' } : null);

                    return (
                      <tr
                        key={idx}
                        style={{
                          borderBottom: '1px solid #1a202e',
                          background: pt.isCurrent ? 'rgba(56, 189, 248, 0.05)' : 'transparent',
                        }}
                      >
                        <td style={{ padding: '10px 14px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: pt.color, flexShrink: 0 }} />
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                              <span style={{ fontWeight: 600, color: '#f8fafc' }}>{pt.planName}</span>
                              <span style={{ color: '#64748b', fontSize: '12px' }}>·</span>
                              <span style={{ color: '#94a3b8', fontSize: '12px' }}>{pt.leafTitle}</span>
                              {chipBadge && (
                                <span
                                  style={{
                                    fontSize: '10px',
                                    fontWeight: 700,
                                    padding: '1px 5px',
                                    borderRadius: '4px',
                                    background: chipBadge.bg,
                                    border: `1px solid ${chipBadge.border}`,
                                    color: chipBadge.text,
                                  }}
                                >
                                  {chipBadge.label}
                                </span>
                              )}
                            </div>
                          </div>
                        </td>
                        <td style={{ padding: '10px 14px', fontFamily: "'JetBrains Mono', monospace", fontWeight: 700, color: '#38bdf8' }}>
                          {pt.mu.toFixed(1)} pts
                        </td>
                        <td style={{ padding: '10px 14px', fontFamily: "'JetBrains Mono', monospace", color: pt.hits > 0 ? '#f43f5e' : '#94a3b8' }}>
                          {pt.hits > 0 ? `-${pt.hitCost} pts (${pt.hits} hit${pt.hits > 1 ? 's' : ''})` : '0 pts'}
                        </td>
                        <td style={{ padding: '10px 14px', fontFamily: "'JetBrains Mono', monospace", color: '#cbd5e1' }}>
                          £{pt.bank.toFixed(1)}m
                        </td>
                        <td style={{ padding: '10px 14px', fontFamily: "'JetBrains Mono', monospace", color: '#cbd5e1' }}>
                          {pt.freeTransfers} FT{pt.freeTransfers > 1 ? 's' : ''}
                        </td>
                        <td style={{ padding: '10px 14px' }}>
                          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                            <span
                              style={{
                                width: '16px',
                                height: '16px',
                                borderRadius: '50%',
                                background: '#f59e0b',
                                color: '#000',
                                fontSize: '10px',
                                fontWeight: 800,
                                display: 'inline-flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                              }}
                            >
                              C
                            </span>
                            <span style={{ color: '#f8fafc', fontSize: '12px' }}>{captainName}</span>
                          </span>
                        </td>
                        <td style={{ padding: '10px 14px', maxWidth: '240px' }}>
                          {pt.transfers.length === 0 ? (
                            <span style={{ color: '#64748b', fontSize: '12px' }}>Roll (0 transfers)</span>
                          ) : (
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                              {pt.transfers.map((t, tIdx) => (
                                <span
                                  key={tIdx}
                                  style={{
                                    fontSize: '11px',
                                    background: '#1a202e',
                                    border: '1px solid #2d3748',
                                    borderRadius: '4px',
                                    padding: '2px 6px',
                                    color: '#cbd5e1',
                                  }}
                                >
                                  <span style={{ color: '#f87171' }}>{t.playerOutName || `P#${t.playerOutId}`}</span>
                                  {' → '}
                                  <span style={{ color: '#4ade80' }}>{t.playerInName || `P#${t.playerInId}`}</span>
                                </span>
                              ))}
                            </div>
                          )}
                        </td>
                        <td style={{ padding: '10px 14px', textAlign: 'right' }}>
                          <button
                            type="button"
                            onClick={() => handleSelectScenario(pt)}
                            style={{
                              background: pt.isCurrent ? '#1e2538' : 'transparent',
                              color: pt.isCurrent ? '#38bdf8' : '#94a3b8',
                              border: pt.isCurrent ? '1px solid #38bdf8' : '1px solid #2d3748',
                              borderRadius: '4px',
                              padding: '4px 10px',
                              fontSize: '11px',
                              fontWeight: 600,
                              cursor: 'pointer',
                            }}
                          >
                            {pt.isCurrent ? 'Viewing' : 'Select Plan'}
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {subView === 'scatter' && (
          <div>
            <div style={{ marginBottom: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h3 style={{ fontSize: '15px', fontWeight: 600, margin: '0 0 4px 0', color: '#f8fafc' }}>
                  Deterministic Trade-off Frontier
                </h3>
                <p style={{ fontSize: '12px', color: '#94a3b8', margin: 0 }}>
                  Compare Net Expected Points against trade-off dimensions. Dashed curve indicates the Pareto non-dominated frontier.
                </p>
              </div>

              {/* X-axis toggle */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', background: '#121520', padding: '4px 8px', borderRadius: '6px', border: '1px solid #1e2538' }}>
                <span style={{ fontSize: '11px', color: '#64748b' }}>X-Axis:</span>
                <button
                  type="button"
                  onClick={() => setScatterXAxis('hits')}
                  style={{
                    background: scatterXAxis === 'hits' ? '#1e2538' : 'transparent',
                    color: scatterXAxis === 'hits' ? '#38bdf8' : '#94a3b8',
                    border: 'none',
                    borderRadius: '4px',
                    padding: '3px 8px',
                    fontSize: '11px',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  Hits (Penalty pts)
                </button>
                <button
                  type="button"
                  onClick={() => setScatterXAxis('bank')}
                  style={{
                    background: scatterXAxis === 'bank' ? '#1e2538' : 'transparent',
                    color: scatterXAxis === 'bank' ? '#38bdf8' : '#94a3b8',
                    border: 'none',
                    borderRadius: '4px',
                    padding: '3px 8px',
                    fontSize: '11px',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  Bank Remaining (£m)
                </button>
                <button
                  type="button"
                  onClick={() => setScatterXAxis('sigma')}
                  style={{
                    background: scatterXAxis === 'sigma' ? '#1e2538' : 'transparent',
                    color: scatterXAxis === 'sigma' ? '#38bdf8' : '#94a3b8',
                    border: 'none',
                    borderRadius: '4px',
                    padding: '3px 8px',
                    fontSize: '11px',
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  Score Risk σ (exp)
                </button>
              </div>
            </div>

            <div
              style={{
                background: '#0a0b10',
                border: '1px solid #1e2538',
                borderRadius: '10px',
                padding: '16px',
                position: 'relative',
              }}
            >
              <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`}>
                {/* Grid Lines */}
                {[0, 0.25, 0.5, 0.75, 1].map((pct, idx) => {
                  const y = padding.top + pct * (height - padding.top - padding.bottom);
                  const muVal = (scatterMaxMu - pct * (scatterMaxMu - scatterMinMu)).toFixed(0);
                  return (
                    <g key={`gy-${idx}`}>
                      <line
                        x1={padding.left}
                        y1={y}
                        x2={width - padding.right}
                        y2={y}
                        stroke="#1e2538"
                        strokeDasharray="3 3"
                      />
                      <text
                        x={padding.left - 8}
                        y={y + 4}
                        fill="#64748b"
                        fontSize="10"
                        fontFamily="'JetBrains Mono', monospace"
                        textAnchor="end"
                      >
                        {muVal}
                      </text>
                    </g>
                  );
                })}

                {/* X-axis labels */}
                {[0, 0.25, 0.5, 0.75, 1].map((pct, idx) => {
                  const x = padding.left + pct * (width - padding.left - padding.right);
                  const val = minX + pct * (maxX - minX);
                  const label = scatterXAxis === 'bank' ? `£${val.toFixed(1)}m` : (scatterXAxis === 'hits' ? `-${val.toFixed(0)}` : `${val.toFixed(1)}σ`);
                  return (
                    <text
                      key={`gx-${idx}`}
                      x={x}
                      y={height - padding.bottom + 18}
                      fill="#64748b"
                      fontSize="10"
                      fontFamily="'JetBrains Mono', monospace"
                      textAnchor="middle"
                    >
                      {label}
                    </text>
                  );
                })}

                {/* Axis Titles */}
                <text
                  x={width / 2}
                  y={height - 6}
                  fill="#94a3b8"
                  fontSize="11"
                  textAnchor="middle"
                >
                  {scatterXAxis === 'hits' ? 'Transfer Hits Cost (pts)' : (scatterXAxis === 'bank' ? 'In the Bank Remaining (£m)' : 'Risk / Uncertainty (Stylized σ)')}
                </text>
                <text
                  x={-height / 2}
                  y={16}
                  fill="#94a3b8"
                  fontSize="11"
                  textAnchor="middle"
                  transform="rotate(-90)"
                >
                  Expected Net Points (xP)
                </text>

                {/* Frontier Path */}
                {frontierPoints.length > 1 && (
                  <path
                    d={frontierPoints.reduce(
                      (acc, pt, i) =>
                        `${acc} ${i === 0 ? 'M' : 'L'} ${scaleX(getXVal(pt))} ${scaleY(pt.mu)}`,
                      ''
                    )}
                    fill="none"
                    stroke="#38bdf8"
                    strokeWidth="2"
                    strokeDasharray="4 4"
                  />
                )}

                {/* Scatter Dots */}
                {scenarioOutcomes.map((pt, idx) => {
                  const cx = scaleX(getXVal(pt));
                  const cy = scaleY(pt.mu);
                  const isHovered = hoveredPoint?.nodeId === pt.nodeId;

                  return (
                    <g
                      key={idx}
                      onMouseEnter={() => setHoveredPoint(pt)}
                      onMouseLeave={() => setHoveredPoint(null)}
                      onClick={() => handleSelectScenario(pt)}
                      style={{ cursor: 'pointer' }}
                    >
                      <circle
                        cx={cx}
                        cy={cy}
                        r={isHovered ? 8 : 6}
                        fill={pt.color}
                        stroke="#0a0b10"
                        strokeWidth="2"
                        opacity={isHovered ? 1 : 0.85}
                      />
                    </g>
                  );
                })}
              </svg>

              {/* Tooltip */}
              {hoveredPoint && (
                <div
                  style={{
                    position: 'absolute',
                    top: '20px',
                    right: '20px',
                    background: '#121520',
                    border: `1.5px solid ${hoveredPoint.color}`,
                    borderRadius: '8px',
                    padding: '8px 12px',
                    fontSize: '12px',
                    boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
                  }}
                >
                  <div style={{ fontWeight: 700, color: hoveredPoint.color, marginBottom: '4px' }}>
                    {hoveredPoint.nodeTitle}
                  </div>
                  <div style={{ color: '#cbd5e1', marginBottom: '2px' }}>
                    Net xP: <strong style={{ color: '#38bdf8' }}>{hoveredPoint.mu.toFixed(1)}</strong>
                  </div>
                  <div style={{ color: '#cbd5e1', marginBottom: '2px' }}>
                    Hits Cost: <strong>-{hoveredPoint.hitCost} pts</strong>
                  </div>
                  <div style={{ color: '#cbd5e1', marginBottom: '2px' }}>
                    Bank: <strong>£{hoveredPoint.bank.toFixed(1)}m</strong>
                  </div>
                  <div style={{ color: '#cbd5e1' }}>
                    Next FTs: <strong>{hoveredPoint.freeTransfers}</strong>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {subView === 'distribution' && (
          <div>
            <div
              style={{
                marginBottom: '12px',
                padding: '10px 14px',
                background: 'rgba(56, 189, 248, 0.08)',
                border: '1px solid rgba(56, 189, 248, 0.25)',
                borderRadius: '6px',
                fontSize: '12px',
                color: '#bae6fd',
              }}
            >
              <strong>Experimental Model Extension:</strong> Gaussian probability curves illustrate continuous outcome distributions under stylized portfolio standard deviation (σ ≈ 11.5). Real FPL point variance is discrete, non-Gaussian, and heavily impacted by captaincy hauls.
            </div>

            <div
              style={{
                background: '#0a0b10',
                border: '1px solid #1e2538',
                borderRadius: '10px',
                padding: '16px',
                marginBottom: '16px',
              }}
            >
              <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`}>
                {/* X-axis ticks */}
                {[30, 45, 60, 75, 90, 105].map((score) => {
                  const x =
                    padding.left +
                    ((score - 20) / (120 - 20)) * (width - padding.left - padding.right);
                  return (
                    <g key={score}>
                      <line
                        x1={x}
                        y1={height - padding.bottom}
                        x2={x}
                        y2={height - padding.bottom + 5}
                        stroke="#64748b"
                      />
                      <text
                        x={x}
                        y={height - padding.bottom + 16}
                        fill="#64748b"
                        fontSize="10"
                        fontFamily="'JetBrains Mono', monospace"
                        textAnchor="middle"
                      >
                        {score}
                      </text>
                    </g>
                  );
                })}

                {/* Bell curves */}
                {scenarioOutcomes.map((pt, idx) => {
                  const points = distRange.map((x) => {
                    const pdf = gaussianPdf(x, pt.mu, pt.sigma);
                    const svgX =
                      padding.left +
                      ((x - 20) / (120 - 20)) * (width - padding.left - padding.right);
                    const svgY = height - padding.bottom - pdf * 3200;
                    return `${svgX},${svgY}`;
                  });

                  return (
                    <path
                      key={idx}
                      d={`M ${points.join(' L ')}`}
                      fill="none"
                      stroke={pt.color}
                      strokeWidth="2"
                      opacity="0.85"
                    />
                  );
                })}
              </svg>
            </div>

            {/* Metrics Breakdown Cards */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                gap: '12px',
              }}
            >
              {scenarioOutcomes.map((pt, idx) => {
                const p60 = (normalCdf(60, pt.mu, pt.sigma) * 100).toFixed(1);
                const p75 = (normalCdf(75, pt.mu, pt.sigma) * 100).toFixed(1);

                return (
                  <div
                    key={idx}
                    style={{
                      background: '#121520',
                      border: '1px solid #1e2538',
                      borderTop: `3px solid ${pt.color}`,
                      borderRadius: '8px',
                      padding: '12px 14px',
                    }}
                  >
                    <div style={{ fontWeight: 600, fontSize: '13px', color: '#f8fafc', marginBottom: '6px' }}>
                      {pt.nodeTitle}
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '4px' }}>
                      <span style={{ color: '#94a3b8' }}>Expected Mean (μ)</span>
                      <span style={{ fontFamily: "'JetBrains Mono', monospace", fontWeight: 700, color: pt.color }}>
                        {pt.mu.toFixed(1)} pts
                      </span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '4px' }}>
                      <span style={{ color: '#94a3b8' }}>Risk / StDev (σ)</span>
                      <span style={{ fontFamily: "'JetBrains Mono', monospace", color: '#cbd5e1' }}>
                        {pt.sigma.toFixed(1)}
                      </span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '4px' }}>
                      <span style={{ color: '#94a3b8' }}>P(Score ≥ 60)</span>
                      <span style={{ fontFamily: "'JetBrains Mono', monospace", color: '#10b981', fontWeight: 600 }}>
                        {p60}%
                      </span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}>
                      <span style={{ color: '#94a3b8' }}>P(Score ≥ 75)</span>
                      <span style={{ fontFamily: "'JetBrains Mono', monospace", color: '#f59e0b', fontWeight: 600 }}>
                        {p75}%
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

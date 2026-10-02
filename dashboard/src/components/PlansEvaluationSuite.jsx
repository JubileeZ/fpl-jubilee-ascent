import React, { useState, useMemo } from 'react';
import { usePlanStore } from '../store/usePlanStore';

// Normal distribution PDF: N(mu, sigma^2)
function gaussianPdf(x, mu, sigma) {
  if (sigma <= 0) return 0;
  const factor = 1 / (sigma * Math.sqrt(2 * Math.PI));
  const exp = Math.exp(-Math.pow(x - mu, 2) / (2 * Math.pow(sigma, 2)));
  return factor * exp;
}

// Standard normal CDF approximation (Erf approximation)
function normalCdf(x, mu, sigma) {
  const z = (x - mu) / sigma;
  const t = 1 / (1 + 0.2316419 * Math.abs(z));
  const d = 0.3989423 * Math.exp((-z * z) / 2);
  let p = d * t * (0.3193815 + t * (-0.3565638 + t * (1.781478 + t * (-1.821256 + t * 1.330274))));
  if (z > 0) p = 1 - p;
  return 1 - p;
}

const PALETTE = ['#38bdf8', '#10b981', '#f59e0b', '#a855f7', '#f43f5e', '#06b6d4'];

export default function PlansEvaluationSuite() {
  const { plans, activePlanId } = usePlanStore();
  const [subView, setSubView] = useState('scatter'); // 'scatter' | 'distribution' | 'comparison'
  const [hoveredPoint, setHoveredPoint] = useState(null);

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
        // Fallback to plan root
        const root = nodes[plan.rootNodeId];
        if (root) {
          list.push({
            planId: plan.id,
            planName: plan.name,
            nodeId: root.id,
            nodeTitle: root.title || plan.name,
            mu: root.evaluation?.netPoints ?? 55.0,
            sigma: root.evaluation?.pointsVariance ?? 11.0,
            hits: root.evaluation?.hitsTaken ?? 0,
            bank: root.evaluation?.bankRemaining ?? 0.0,
            color,
            isCurrent: plan.id === activePlanId,
          });
        }
      } else {
        leafNodes.forEach((leaf) => {
          const evalData = leaf.evaluation || {};
          list.push({
            planId: plan.id,
            planName: plan.name,
            nodeId: leaf.id,
            nodeTitle: `${plan.name} · ${leaf.title || `GW${leaf.gameweek}`}`,
            mu: evalData.netPoints ?? evalData.cumulativePoints ?? 60.0,
            sigma: evalData.pointsVariance ?? 12.0,
            hits: evalData.hitsTaken ?? 0,
            bank: evalData.bankRemaining ?? 0.0,
            color,
            isCurrent: plan.id === activePlanId,
          });
        });
      }
    });

    return list;
  }, [plans, activePlanId]);

  // Compute Efficient Frontier (Pareto non-dominated points)
  const efficientFrontierPoints = useMemo(() => {
    // Sort by sigma ascending
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
  }, [scenarioOutcomes]);

  // Dimensions for scatter plot
  const scatterMinMu = Math.min(...scenarioOutcomes.map((p) => p.mu), 40) - 5;
  const scatterMaxMu = Math.max(...scenarioOutcomes.map((p) => p.mu), 90) + 10;
  const scatterMinSigma = Math.min(...scenarioOutcomes.map((p) => p.sigma), 8) - 2;
  const scatterMaxSigma = Math.max(...scenarioOutcomes.map((p) => p.sigma), 18) + 3;

  const width = 580;
  const height = 300;
  const padding = { top: 30, right: 30, bottom: 40, left: 50 };

  const scaleX = (sigma) =>
    padding.left +
    ((sigma - scatterMinSigma) / (scatterMaxSigma - scatterMinSigma)) *
      (width - padding.left - padding.right);

  const scaleY = (mu) =>
    height -
    padding.bottom -
    ((mu - scatterMinMu) / (scatterMaxMu - scatterMinMu)) *
      (height - padding.top - padding.bottom);

  // Gaussian density curve points across X [30, 110]
  const distRange = [];
  for (let x = 30; x <= 120; x += 1.5) {
    distRange.push(x);
  }

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
            Scatter (Efficient Frontier)
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
            Gaussian Probability Curves
          </button>
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
            Side-by-Side Comparison
          </button>
        </div>

        <div style={{ fontSize: '11px', color: '#64748b' }}>
          Comparing {scenarioOutcomes.length} scenario outcomes across {plans.length} plan branches
        </div>
      </div>

      {/* Main Chart Body */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '16px 20px' }}>
        {subView === 'scatter' && (
          <div>
            <div style={{ marginBottom: '10px' }}>
              <h3 style={{ fontSize: '15px', fontWeight: 600, margin: '0 0 4px 0', color: '#f8fafc' }}>
                Efficient Frontier: Expected Points vs Risk
              </h3>
              <p style={{ fontSize: '12px', color: '#94a3b8', margin: 0 }}>
                Plots expected net points ($\mu$) against outcome standard deviation ($\sigma$). The cyan dashed curve marks the Pareto-optimal frontier.
              </p>
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
                  const sigmaVal = (scatterMinSigma + pct * (scatterMaxSigma - scatterMinSigma)).toFixed(1);
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
                      {sigmaVal}σ
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
                  Risk / Uncertainty (Points Standard Deviation σ)
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

                {/* Efficient Frontier Path */}
                {efficientFrontierPoints.length > 1 && (
                  <path
                    d={efficientFrontierPoints.reduce(
                      (acc, pt, i) =>
                        `${acc} ${i === 0 ? 'M' : 'L'} ${scaleX(pt.sigma)} ${scaleY(pt.mu)}`,
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
                  const cx = scaleX(pt.sigma);
                  const cy = scaleY(pt.mu);
                  const isHovered = hoveredPoint?.nodeId === pt.nodeId;

                  return (
                    <g
                      key={idx}
                      onMouseEnter={() => setHoveredPoint(pt)}
                      onMouseLeave={() => setHoveredPoint(null)}
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
                  <div style={{ fontFamily: "'JetBrains Mono', monospace", color: '#cbd5e1' }}>
                    Net: {hoveredPoint.mu.toFixed(1)} xP · Risk: {hoveredPoint.sigma.toFixed(1)}σ
                  </div>
                  <div style={{ fontSize: '11px', color: '#64748b' }}>
                    Hits: -{hoveredPoint.hits * 4} pts · Bank: £{hoveredPoint.bank.toFixed(1)}m
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {subView === 'distribution' && (
          <div>
            <div style={{ marginBottom: '10px' }}>
              <h3 style={{ fontSize: '15px', fontWeight: 600, margin: '0 0 4px 0', color: '#f8fafc' }}>
                Gaussian Probability Density Distributions
              </h3>
              <p style={{ fontSize: '12px', color: '#94a3b8', margin: 0 }}>
                Normal distribution curve $\mathcal{N}(\mu, \sigma^2)$ modeling the probability distribution of gameweek point outcomes for each plan.
              </p>
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
                {/* Horizontal baseline */}
                <line
                  x1={padding.left}
                  y1={height - padding.bottom}
                  x2={width - padding.right}
                  y2={height - padding.bottom}
                  stroke="#334155"
                  strokeWidth="1.5"
                />

                {/* X-axis score ticks */}
                {[40, 50, 60, 70, 80, 90, 100].map((score) => {
                  const x =
                    padding.left +
                    ((score - 30) / (110 - 30)) * (width - padding.left - padding.right);
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

                {/* Draw bell curves */}
                {scenarioOutcomes.map((pt, idx) => {
                  const points = distRange.map((x) => {
                    const pdf = gaussianPdf(x, pt.mu, pt.sigma);
                    const svgX =
                      padding.left +
                      ((x - 30) / (110 - 30)) * (width - padding.left - padding.right);
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

            {/* Metrics Breakdown Table */}
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

        {subView === 'comparison' && (
          <div>
            <div style={{ marginBottom: '10px' }}>
              <h3 style={{ fontSize: '15px', fontWeight: 600, margin: '0 0 4px 0', color: '#f8fafc' }}>
                Multi-Branch Comparison Matrix
              </h3>
              <p style={{ fontSize: '12px', color: '#94a3b8', margin: 0 }}>
                Side-by-side performance metrics across all planned branches and decision paths.
              </p>
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
                    <th style={{ padding: '10px 14px', color: '#94a3b8', fontWeight: 600, fontSize: '11px' }}>RISK (σ)</th>
                    <th style={{ padding: '10px 14px', color: '#94a3b8', fontWeight: 600, fontSize: '11px' }}>HITS</th>
                    <th style={{ padding: '10px 14px', color: '#94a3b8', fontWeight: 600, fontSize: '11px' }}>BANK</th>
                    <th style={{ padding: '10px 14px', color: '#94a3b8', fontWeight: 600, fontSize: '11px' }}>P(≥ 60 PTS)</th>
                  </tr>
                </thead>
                <tbody>
                  {scenarioOutcomes.map((pt, idx) => {
                    const p60 = (normalCdf(60, pt.mu, pt.sigma) * 100).toFixed(1);
                    return (
                      <tr
                        key={idx}
                        style={{
                          borderBottom: '1px solid #1a202e',
                          background: pt.isCurrent ? 'rgba(56, 189, 248, 0.05)' : 'transparent',
                        }}
                      >
                        <td style={{ padding: '10px 14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: pt.color }} />
                          <span style={{ fontWeight: 600, color: '#f8fafc' }}>{pt.nodeTitle}</span>
                        </td>
                        <td style={{ padding: '10px 14px', fontFamily: "'JetBrains Mono', monospace", fontWeight: 700, color: '#38bdf8' }}>
                          {pt.mu.toFixed(1)}
                        </td>
                        <td style={{ padding: '10px 14px', fontFamily: "'JetBrains Mono', monospace', color: '#cbd5e1" }}>
                          {pt.sigma.toFixed(1)}
                        </td>
                        <td style={{ padding: '10px 14px', fontFamily: "'JetBrains Mono', monospace", color: pt.hits > 0 ? '#f43f5e' : '#cbd5e1' }}>
                          -{pt.hits * 4} pts
                        </td>
                        <td style={{ padding: '10px 14px', fontFamily: "'JetBrains Mono', monospace', color: '#cbd5e1" }}>
                          £{pt.bank.toFixed(1)}m
                        </td>
                        <td style={{ padding: '10px 14px', fontFamily: "'JetBrains Mono', monospace", color: '#10b981', fontWeight: 600 }}>
                          {p60}%
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

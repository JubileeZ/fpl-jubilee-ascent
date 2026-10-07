import React, { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { planActions } from '../../store/usePlanStore';

function PlanNode({ id, data, selected }) {
  const node = data.node || {};
  const isSelected = selected || data.isActive;
  const evalData = node.evaluation || {};
  const transfers = node.transfers || [];
  const chip = node.chip;

  const handleAddChild = (e) => {
    e.stopPropagation();
    planActions.addBranch(id);
  };

  const handleDuplicate = (e) => {
    e.stopPropagation();
    planActions.duplicateBranch(id);
  };

  const handleDelete = (e) => {
    e.stopPropagation();
    planActions.deleteBranch(id);
  };

  const handleSolve = (e) => {
    e.stopPropagation();
    if (data.onSolve) {
      data.onSolve();
    } else if (window.solveFromPlanNode) {
      window.solveFromPlanNode(id);
    }
  };

  const handleResetToSolver = (e) => {
    e.stopPropagation();
    if (data.onResetToSolver) {
      data.onResetToSolver();
    } else {
      planActions.resetNodeToSolver(id);
    }
  };

  const chipColors = {
    WC: '#10b981',
    FH: '#f59e0b',
    TC: '#38bdf8',
    BB: '#a855f7',
  };

  const isCustom = Boolean(node.isCustom);
  const captainPid = node.lineup?.slots?.[String(node.lineup?.captainSlot || 1)] || node.lineup?.slots?.[node.lineup?.captainSlot || 1];
  const capPlayer = window.dashboardData?.players?.find((p) => p.id === captainPid);
  const captainName = capPlayer?.web_name || capPlayer?.name || null;

  return (
    <div
      className={`decision-node plan-node ${isSelected ? 'node-selected' : ''}`}
      style={{
        background: '#121520',
        border: isSelected ? '1.5px solid #38bdf8' : '1px solid #1e2538',
        borderRadius: '10px',
        padding: '12px 14px',
        minWidth: '260px',
        maxWidth: '280px',
        color: '#f8fafc',
        fontFamily: "'Inter', sans-serif",
        boxShadow: isSelected ? '0 0 16px rgba(56, 189, 248, 0.25)' : '0 4px 12px rgba(0, 0, 0, 0.35)',
        cursor: 'pointer',
        transition: 'all 0.15s ease',
        position: 'relative',
      }}
      onClick={() => planActions.setActiveNode(id)}
    >
      <Handle
        type="target"
        position={Position.Left}
        style={{
          background: '#64748b',
          width: '8px',
          height: '8px',
          border: '2px solid #0a0b10',
          left: '-5px',
        }}
      />

      {/* Header: Gameweek & Status Badges */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span
            style={{
              background: '#1e2538',
              color: '#38bdf8',
              padding: '2px 8px',
              borderRadius: '4px',
              fontSize: '12px',
              fontWeight: 700,
              fontFamily: "'JetBrains Mono', monospace",
            }}
          >
            GW{node.gameweek}
          </span>

          <span
            style={{
              background: isCustom ? 'rgba(245, 158, 11, 0.15)' : 'rgba(16, 185, 129, 0.15)',
              color: isCustom ? '#f59e0b' : '#10b981',
              border: `1px solid ${isCustom ? 'rgba(245, 158, 11, 0.35)' : 'rgba(16, 185, 129, 0.35)'}`,
              padding: '1px 5px',
              borderRadius: '4px',
              fontSize: '10px',
              fontWeight: 700,
              fontFamily: "'JetBrains Mono', monospace",
            }}
            title={isCustom ? 'User edited squad' : 'Solver recommended squad'}
          >
            {isCustom ? '✏️ Custom' : '⚡ Solver'}
          </span>

          {chip && (
            <span
              style={{
                background: chipColors[chip] || chipColors[String(chip).toUpperCase()] || '#38bdf8',
                color: '#0a0b10',
                padding: '2px 6px',
                borderRadius: '4px',
                fontSize: '11px',
                fontWeight: 700,
                letterSpacing: '0.04em',
              }}
            >
              {String(chip).toUpperCase()}
            </span>
          )}

          {captainName && (
            <span
              style={{
                background: 'rgba(56, 189, 248, 0.12)',
                color: '#38bdf8',
                border: '1px solid rgba(56, 189, 248, 0.3)',
                padding: '1px 5px',
                borderRadius: '4px',
                fontSize: '10px',
                fontWeight: 700,
                fontFamily: "'JetBrains Mono', monospace",
              }}
              title={`Captain: ${captainName}`}
            >
              (C) {captainName}
            </span>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px' }}>
          <span
            style={{
              fontSize: '17px',
              fontWeight: 700,
              color: '#38bdf8',
              fontFamily: "'JetBrains Mono', monospace",
            }}
          >
            {(evalData.expectedPoints ?? 0.0).toFixed(1)}
          </span>
          <span style={{ fontSize: '11px', color: '#94a3b8' }}>pts</span>
        </div>
      </div>

      {/* Chip Booking Selector */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '3px',
          marginBottom: '8px',
          background: '#0a0b10',
          padding: '2px 5px',
          borderRadius: '5px',
          border: '1px solid #1a202e',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <span style={{ fontSize: '10px', color: '#64748b', fontWeight: 600, marginRight: '2px' }}>Chip:</span>
        {[
          { id: null, label: 'None' },
          { id: 'WC', label: 'WC', color: '#10b981' },
          { id: 'FH', label: 'FH', color: '#f59e0b' },
          { id: 'BB', label: 'BB', color: '#a855f7' },
          { id: 'TC', label: 'TC', color: '#38bdf8' },
        ].map((c) => {
          const isChipSelected = (node.chip ? String(node.chip).toUpperCase() : null) === c.id;
          return (
            <button
              key={c.label}
              type="button"
              onClick={() => {
                const nextChip = isChipSelected ? null : c.id;
                const isFreeChip = nextChip === 'WC' || nextChip === 'FH';
                const nextHits = isFreeChip ? 0 : node.evaluation?.hitsTaken ?? 0;
                planActions.updateNode(
                  id,
                  {
                    chip: nextChip,
                    evaluation: {
                      ...node.evaluation,
                      hitsTaken: nextHits,
                    },
                    isCustom: true,
                  },
                  true
                );
              }}
              style={{
                background: isChipSelected ? (c.color ? `${c.color}25` : '#1e2538') : 'transparent',
                color: isChipSelected ? c.color || '#38bdf8' : '#64748b',
                border: isChipSelected ? `1px solid ${c.color || '#38bdf8'}` : '1px solid transparent',
                borderRadius: '3px',
                padding: '1px 5px',
                fontSize: '10px',
                fontWeight: isChipSelected ? 700 : 500,
                cursor: 'pointer',
                fontFamily: "'JetBrains Mono', monospace",
              }}
              title={c.id ? `Book ${c.label} for GW${node.gameweek}` : 'No chip'}
            >
              {c.label}
            </button>
          );
        })}
      </div>

      {/* Transfers Summary */}
      <div
        style={{
          background: '#0a0b10',
          borderRadius: '6px',
          padding: '8px 10px',
          fontSize: '12px',
          marginBottom: '8px',
          border: '1px solid #1a202e',
          minHeight: '34px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
        }}
      >
        {transfers.length === 0 ? (
          <span style={{ color: '#64748b', fontStyle: 'italic' }}>Roll Free Transfer</span>
        ) : (
          transfers.map((t, idx) => (
            <div
              key={idx}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: '11px',
              }}
            >
              <span style={{ color: '#f43f5e' }}>{t.playerOutName || `Out #${t.playerOutId}`}</span>
              <span style={{ color: '#64748b', margin: '0 4px' }}>→</span>
              <span style={{ color: '#10b981' }}>{t.playerInName || `In #${t.playerInId}`}</span>
            </div>
          ))
        )}
      </div>

      {/* Metrics Row */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          fontSize: '11px',
          fontFamily: "'JetBrains Mono', monospace",
          color: '#94a3b8',
          marginBottom: '10px',
        }}
      >
        <span>£{(evalData.bankRemaining ?? 0.0).toFixed(1)}m · {evalData.freeTransfersNext ?? 1} FT</span>
        {evalData.hitsTaken > 0 ? (
          <span style={{ color: '#f43f5e', fontWeight: 600 }}>
            Cum: {(evalData.cumulativePoints ?? 0.0).toFixed(1)} (-{evalData.hitsTaken * 4})
          </span>
        ) : (
          <span style={{ color: '#64748b' }}>Cum: {(evalData.cumulativePoints ?? 0.0).toFixed(1)}</span>
        )}
      </div>

      {/* Action Buttons */}
      <div
        style={{
          display: 'flex',
          gap: '4px',
          borderTop: '1px solid #1e2538',
          paddingTop: '8px',
          flexWrap: 'wrap',
        }}
      >
        <button
          type="button"
          onClick={handleSolve}
          style={{
            flex: 1,
            minWidth: '56px',
            background: 'rgba(56, 189, 248, 0.15)',
            color: '#38bdf8',
            border: '1px solid rgba(56, 189, 248, 0.35)',
            borderRadius: '5px',
            padding: '4px 6px',
            fontSize: '11px',
            fontWeight: 600,
            cursor: 'pointer',
          }}
          title="Solve from this box to Horizon End"
        >
          ⚡ Solve
        </button>

        {isCustom && node.solverRecommendation && (
          <button
            type="button"
            onClick={handleResetToSolver}
            style={{
              flex: 1,
              minWidth: '60px',
              background: 'rgba(245, 158, 11, 0.15)',
              color: '#f59e0b',
              border: '1px solid rgba(245, 158, 11, 0.35)',
              borderRadius: '5px',
              padding: '4px 6px',
              fontSize: '11px',
              fontWeight: 600,
              cursor: 'pointer',
            }}
            title="Reset squad and transfers to solver recommendation"
          >
            ↩ Revert
          </button>
        )}

        <button
          type="button"
          onClick={handleAddChild}
          style={{
            flex: 1,
            minWidth: '50px',
            background: '#1a202e',
            color: '#cbd5e1',
            border: '1px solid #2d3748',
            borderRadius: '5px',
            padding: '4px 6px',
            fontSize: '11px',
            cursor: 'pointer',
          }}
          title="Split into new decision branch starting at next GW"
        >
          + Split
        </button>

        <button
          type="button"
          onClick={handleDelete}
          style={{
            background: 'rgba(244, 63, 94, 0.1)',
            color: '#f43f5e',
            border: '1px solid rgba(244, 63, 94, 0.25)',
            borderRadius: '5px',
            padding: '4px 6px',
            fontSize: '11px',
            cursor: 'pointer',
          }}
          title="Delete branch"
        >
          Del
        </button>
      </div>

      <Handle
        type="source"
        position={Position.Right}
        style={{
          background: '#38bdf8',
          width: '8px',
          height: '8px',
          border: '2px solid #0a0b10',
          right: '-5px',
        }}
      />
    </div>
  );
}

export default memo(PlanNode);

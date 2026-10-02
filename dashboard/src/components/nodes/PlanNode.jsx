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

  const chipColors = {
    WC: '#10b981',
    FH: '#f59e0b',
    TC: '#38bdf8',
    BB: '#a855f7',
  };

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

      {/* Header: Gameweek & Chip */}
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
          {chip && (
            <span
              style={{
                background: chipColors[chip] || '#38bdf8',
                color: '#0a0b10',
                padding: '2px 6px',
                borderRadius: '4px',
                fontSize: '11px',
                fontWeight: 700,
                letterSpacing: '0.04em',
              }}
            >
              {chip}
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
          <span style={{ color: '#f43f5e', fontWeight: 600 }}>-{evalData.hitsTaken * 4} pts hit</span>
        ) : (
          <span style={{ color: '#64748b' }}>Cum: {(evalData.cumulativePoints ?? 0.0).toFixed(1)}</span>
        )}
      </div>

      {/* Action Buttons */}
      <div
        style={{
          display: 'flex',
          gap: '6px',
          borderTop: '1px solid #1e2538',
          paddingTop: '8px',
        }}
      >
        <button
          type="button"
          onClick={handleAddChild}
          style={{
            flex: 2,
            background: 'rgba(56, 189, 248, 0.12)',
            color: '#38bdf8',
            border: '1px solid rgba(56, 189, 248, 0.3)',
            borderRadius: '5px',
            padding: '4px 8px',
            fontSize: '11px',
            fontWeight: 600,
            cursor: 'pointer',
          }}
          title="Add next GW decision step"
        >
          + Branch
        </button>
        <button
          type="button"
          onClick={handleDuplicate}
          style={{
            flex: 1,
            background: '#1a202e',
            color: '#cbd5e1',
            border: '1px solid #2d3748',
            borderRadius: '5px',
            padding: '4px 6px',
            fontSize: '11px',
            cursor: 'pointer',
          }}
          title="Duplicate this branch"
        >
          Copy
        </button>
        <button
          type="button"
          onClick={handleDelete}
          style={{
            flex: 1,
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

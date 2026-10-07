import React, { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { planActions } from '../../store/usePlanStore';

function RootNode({ id, data, selected }) {
  const node = data.node || {};
  const isSelected = selected || data.isActive;
  const startGw = data.startGameweek || (node.gameweek ? node.gameweek + 1 : 6);

  const handleAddChild = (e) => {
    e.stopPropagation();
    planActions.addBranch(id);
  };

  const handleSolveAll = (e) => {
    e.stopPropagation();
    if (data.onSolve) {
      data.onSolve();
    } else if (window.solveFromPlanNode) {
      window.solveFromPlanNode(id);
    }
  };

  return (
    <div
      className={`decision-node root-node ${isSelected ? 'node-selected' : ''}`}
      style={{
        background: '#121520',
        border: isSelected ? '1.5px solid #38bdf8' : '1px solid #1e2538',
        borderRadius: '10px',
        padding: '14px 16px',
        minWidth: '240px',
        maxWidth: '260px',
        color: '#f8fafc',
        fontFamily: "'Inter', sans-serif",
        boxShadow: isSelected ? '0 0 16px rgba(56, 189, 248, 0.25)' : '0 4px 12px rgba(0, 0, 0, 0.4)',
        cursor: 'pointer',
        transition: 'all 0.15s ease',
      }}
      onClick={() => planActions.setActiveNode(id)}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
        <span style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.06em', color: '#38bdf8', fontWeight: 700 }}>
          Current Squad
        </span>
        <span
          style={{
            background: '#1e2538',
            color: '#38bdf8',
            padding: '2px 8px',
            borderRadius: '4px',
            fontSize: '11px',
            fontFamily: "'JetBrains Mono', monospace",
            fontWeight: 600,
          }}
        >
          Pre-GW{startGw}
        </span>
      </div>

      <div style={{ fontSize: '15px', fontWeight: 600, color: '#f8fafc', marginBottom: '6px' }}>
        Active User Squad
      </div>

      <div
        style={{
          display: 'flex',
          gap: '12px',
          fontSize: '12px',
          fontFamily: "'JetBrains Mono', monospace",
          color: '#94a3b8',
          marginBottom: '12px',
        }}
      >
        <span>£{(node.evaluation?.bankRemaining ?? 0.0).toFixed(1)}m ITB</span>
        <span>·</span>
        <span>{node.evaluation?.freeTransfersNext ?? 1} FT</span>
      </div>

      <div style={{ display: 'flex', gap: '6px', marginTop: '10px', borderTop: '1px solid #1e2538', paddingTop: '10px' }}>
        <button
          type="button"
          onClick={handleSolveAll}
          style={{
            flex: 1,
            background: 'rgba(56, 189, 248, 0.15)',
            color: '#38bdf8',
            border: '1px solid rgba(56, 189, 248, 0.35)',
            borderRadius: '6px',
            padding: '6px 10px',
            fontSize: '12px',
            fontWeight: 600,
            cursor: 'pointer',
            transition: 'all 0.15s ease',
          }}
          title={`Solve transfer plan from GW${startGw} through Horizon End`}
        >
          ⚡ Solve
        </button>
        <button
          type="button"
          onClick={handleAddChild}
          style={{
            flex: 1,
            background: '#1a202e',
            color: '#cbd5e1',
            border: '1px solid #2d3748',
            borderRadius: '6px',
            padding: '6px 10px',
            fontSize: '12px',
            fontWeight: 600,
            cursor: 'pointer',
            transition: 'all 0.15s ease',
          }}
          title="Create child branch"
        >
          + Branch
        </button>
      </div>

      <Handle
        type="source"
        position={Position.Right}
        style={{
          background: '#38bdf8',
          width: '10px',
          height: '10px',
          border: '2px solid #0a0b10',
          right: '-5px',
        }}
      />
    </div>
  );
}

export default memo(RootNode);

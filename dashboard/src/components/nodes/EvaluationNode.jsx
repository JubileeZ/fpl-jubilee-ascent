import React, { memo } from 'react';
import { Handle, Position } from '@xyflow/react';

function EvaluationNode({ data }) {
  const evalData = data.evaluation || {};
  const isTopBranch = data.isTopBranch || false;

  return (
    <div
      className="decision-node evaluation-node"
      style={{
        background: '#121520',
        border: isTopBranch ? '1.5px solid #10b981' : '1px solid #1e2538',
        borderRadius: '10px',
        padding: '12px 14px',
        minWidth: '220px',
        maxWidth: '240px',
        color: '#f8fafc',
        fontFamily: "'Inter', sans-serif",
        boxShadow: isTopBranch ? '0 0 16px rgba(16, 185, 129, 0.2)' : '0 4px 12px rgba(0, 0, 0, 0.35)',
      }}
    >
      <Handle
        type="target"
        position={Position.Left}
        style={{
          background: '#10b981',
          width: '8px',
          height: '8px',
          border: '2px solid #0a0b10',
          left: '-5px',
        }}
      />

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
        <span style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.06em', color: '#94a3b8', fontWeight: 600 }}>
          Branch Outcome
        </span>
        {isTopBranch && (
          <span style={{ background: 'rgba(16, 185, 129, 0.15)', color: '#10b981', padding: '2px 6px', borderRadius: '4px', fontSize: '10px', fontWeight: 700 }}>
            OPTIMAL
          </span>
        )}
      </div>

      <div style={{ marginBottom: '8px' }}>
        <div style={{ fontSize: '20px', fontWeight: 700, color: '#10b981', fontFamily: "'JetBrains Mono', monospace" }}>
          {(evalData.netPoints ?? evalData.cumulativePoints ?? 0.0).toFixed(1)}{' '}
          <span style={{ fontSize: '12px', color: '#94a3b8', fontWeight: 400 }}>net xP</span>
        </div>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '6px',
          background: '#0a0b10',
          padding: '8px',
          borderRadius: '6px',
          fontSize: '11px',
          fontFamily: "'JetBrains Mono', monospace', color: '#94a3b8",
        }}
      >
        <div>
          <span style={{ color: '#64748b', display: 'block', fontSize: '10px' }}>Total xP</span>
          <span style={{ color: '#cbd5e1' }}>{(evalData.cumulativePoints ?? 0.0).toFixed(1)}</span>
        </div>
        <div>
          <span style={{ color: '#64748b', display: 'block', fontSize: '10px' }}>Hits</span>
          <span style={{ color: evalData.hitsTaken > 0 ? '#f43f5e' : '#cbd5e1' }}>
            -{evalData.hitsTaken ? evalData.hitsTaken * 4 : 0} pts
          </span>
        </div>
        <div>
          <span style={{ color: '#64748b', display: 'block', fontSize: '10px' }}>Bank</span>
          <span style={{ color: '#cbd5e1' }}>£{(evalData.bankRemaining ?? 0.0).toFixed(1)}m</span>
        </div>
        <div>
          <span style={{ color: '#64748b', display: 'block', fontSize: '10px' }}>Free Trans</span>
          <span style={{ color: '#cbd5e1' }}>{evalData.freeTransfersNext ?? 1} FT</span>
        </div>
      </div>
    </div>
  );
}

export default memo(EvaluationNode);

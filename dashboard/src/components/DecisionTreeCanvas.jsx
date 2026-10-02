import React, { useMemo, useCallback } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import RootNode from './nodes/RootNode';
import PlanNode from './nodes/PlanNode';
import EvaluationNode from './nodes/EvaluationNode';
import { usePlanStore, planActions } from '../store/usePlanStore';

const nodeTypes = {
  rootNode: RootNode,
  planNode: PlanNode,
  evaluationNode: EvaluationNode,
};

export default function DecisionTreeCanvas() {
  const { plans, activePlan, activePlanId, activeNodeId, isSaving, isLoading, actions } = usePlanStore();
  const [ddpPreset, setDdpPreset] = React.useState('default');
  const [isSolving, setIsSolving] = React.useState(false);

  const handleOptimizeBranch = async () => {
    if (!activePlan || isSolving) return;
    const parentId = activeNodeId || activePlan.rootNodeId;
    const parentNode = activePlan.nodes[parentId];
    const targetGw = parentNode ? parentNode.gameweek + 1 : 6;

    setIsSolving(true);
    try {
      const res = await fetch('/api/solve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          parentNodeId: parentId,
          target_gw: targetGw,
          preset: ddpPreset,
          horizon: 4,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      // Poll until finished
      let attempts = 0;
      while (attempts < 60) {
        await new Promise((r) => setTimeout(r, 600));
        attempts++;
        const pollRes = await fetch('/api/solve');
        if (pollRes.ok) {
          const pollData = await pollRes.json();
          if (pollData.status === 'ok' && pollData.payload?.branch) {
            const branch = pollData.payload.branch;
            if (branch.nodes && branch.rootChildId) {
              const updatedParent = {
                ...parentNode,
                childIds: [...(parentNode.childIds || []), branch.rootChildId],
              };
              planActions.updateNode(parentId, { childIds: updatedParent.childIds });
              for (const [nid, nodeObj] of Object.entries(branch.nodes)) {
                planActions.updateNode(nid, nodeObj);
              }
              planActions.setActiveNode(branch.rootChildId);
            }
            break;
          } else if (pollData.status === 'error') {
            alert(`Optimization error: ${pollData.error || 'Failed'}`);
            break;
          }
        }
      }
    } catch (err) {
      console.error('Failed to optimize branch:', err);
      alert(`Could not start optimization: ${err.message}`);
    } finally {
      setIsSolving(false);
    }
  };

  // Convert hierarchical plan scenario into React Flow layout (x, y)
  const { flowNodes, flowEdges } = useMemo(() => {
    if (!activePlan || !activePlan.nodes) {
      return { flowNodes: [], flowEdges: [] };
    }

    const startGw = activePlan.startGameweek || 6;
    const nodes = [];
    const edges = [];

    // Layout calculation: traverse from root
    const rootId = activePlan.rootNodeId || 'node-root';
    const rootNode = activePlan.nodes[rootId];

    // Compute Y positions per leaf to distribute tree cleanly
    const yTracker = { current: 100 };

    function layoutSubtree(nodeId, depth) {
      const node = activePlan.nodes[nodeId];
      if (!node) return null;

      const children = node.childIds || [];
      const xPos = 40 + depth * 320;

      if (children.length === 0) {
        // Leaf node
        const yPos = yTracker.current;
        yTracker.current += 190;

        const isRoot = node.id === rootId;
        nodes.push({
          id: node.id,
          type: isRoot ? 'rootNode' : 'planNode',
          position: { x: xPos, y: yPos },
          data: {
            node,
            isActive: node.id === activeNodeId,
          },
        });

        // If it's a leaf planNode, add EvaluationNode at the end
        if (!isRoot) {
          const evalId = `eval-${node.id}`;
          nodes.push({
            id: evalId,
            type: 'evaluationNode',
            position: { x: xPos + 320, y: yPos },
            data: {
              evaluation: node.evaluation || {},
              isTopBranch: false,
            },
          });

          edges.push({
            id: `edge-${node.id}-${evalId}`,
            source: node.id,
            target: evalId,
            animated: true,
            style: { stroke: '#10b981', strokeWidth: 2 },
          });
        }

        return yPos;
      }

      // Internal node: layout children first
      const childYPositions = [];
      for (const cid of children) {
        const cY = layoutSubtree(cid, depth + 1);
        if (cY !== null) {
          childYPositions.push(cY);
          edges.push({
            id: `edge-${node.id}-${cid}`,
            source: node.id,
            target: cid,
            style: { stroke: '#38bdf8', strokeWidth: 2 },
            markerEnd: {
              type: MarkerType.ArrowClosed,
              color: '#38bdf8',
            },
          });
        }
      }

      // Center this node vertically among its children
      const yPos =
        childYPositions.length > 0
          ? childYPositions.reduce((a, b) => a + b, 0) / childYPositions.length
          : yTracker.current;

      const isRoot = node.id === rootId;
      nodes.push({
        id: node.id,
        type: isRoot ? 'rootNode' : 'planNode',
        position: { x: xPos, y: yPos },
        data: {
          node,
          isActive: node.id === activeNodeId,
        },
      });

      return yPos;
    }

    if (rootNode) {
      layoutSubtree(rootId, 0);
    }

    return { flowNodes: nodes, flowEdges: edges };
  }, [activePlan, activeNodeId]);

  const [nodes, setNodes, onNodesChange] = useNodesState(flowNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(flowEdges);

  // Sync state changes from memo
  React.useEffect(() => {
    setNodes(flowNodes);
    setEdges(flowEdges);
  }, [flowNodes, flowEdges, setNodes, setEdges]);

  const handleCreatePlan = () => {
    const name = prompt('Enter new scenario name:', `Scenario ${plans.length + 1}`);
    if (name) actions.createPlan(name);
  };

  const handleDuplicateCurrentPlan = () => {
    if (activePlanId) actions.duplicatePlan(activePlanId);
  };

  const handleDeleteCurrentPlan = () => {
    if (plans.length <= 1) {
      alert('Cannot delete the only scenario plan.');
      return;
    }
    if (confirm(`Delete plan "${activePlan?.name}"?`)) {
      actions.deletePlan(activePlanId);
    }
  };

  if (isLoading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#94a3b8' }}>
        Loading decision scenarios...
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', width: '100%', background: '#0a0b10' }}>
      {/* Top Planner Toolbar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '10px 18px',
          background: '#121520',
          borderBottom: '1px solid #1e2538',
          zIndex: 10,
        }}
      >
        {/* Scenario Tabs */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflowX: 'auto' }}>
          <span style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.06em', color: '#94a3b8', fontWeight: 600, marginRight: '4px' }}>
            Scenarios:
          </span>
          {plans.map((p) => {
            const isActive = p.id === activePlanId;
            return (
              <button
                key={p.id}
                type="button"
                onClick={() => actions.setActivePlan(p.id)}
                style={{
                  background: isActive ? '#1e2538' : 'transparent',
                  color: isActive ? '#38bdf8' : '#94a3b8',
                  border: isActive ? '1px solid rgba(56, 189, 248, 0.4)' : '1px solid transparent',
                  borderRadius: '6px',
                  padding: '6px 12px',
                  fontSize: '12px',
                  fontWeight: isActive ? 600 : 400,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  whiteSpace: 'nowrap',
                }}
              >
                <span>{p.name}</span>
                {isActive && <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#38bdf8' }} />}
              </button>
            );
          })}
          <button
            type="button"
            onClick={handleCreatePlan}
            style={{
              background: 'transparent',
              color: '#64748b',
              border: '1px dashed #334155',
              borderRadius: '6px',
              padding: '6px 10px',
              fontSize: '12px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
            title="Create new scenario"
          >
            + New Plan
          </button>
        </div>

        {/* Plan Actions & Sync status */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {/* DDP Solver Preset Selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <label htmlFor="ddp-preset-select" style={{ fontSize: '11px', color: '#94a3b8' }}>
              DDP:
            </label>
            <select
              id="ddp-preset-select"
              value={ddpPreset}
              onChange={(e) => setDdpPreset(e.target.value)}
              style={{
                background: '#0a0b10',
                border: '1px solid #1e2538',
                borderRadius: '5px',
                color: '#38bdf8',
                fontSize: '11px',
                fontFamily: "'JetBrains Mono', monospace",
                padding: '4px 8px',
                outline: 'none',
              }}
            >
              <option value="safe">Safe (75% DDP)</option>
              <option value="default">Default (50% DDP)</option>
              <option value="optimistic">Optimistic (0% DDP)</option>
              <option value="high_risk">High Risk (25% DDP)</option>
            </select>
          </div>

          <button
            type="button"
            disabled={isSolving}
            onClick={handleOptimizeBranch}
            style={{
              background: isSolving ? '#1e2538' : 'rgba(56, 189, 248, 0.15)',
              color: isSolving ? '#64748b' : '#38bdf8',
              border: '1px solid rgba(56, 189, 248, 0.35)',
              borderRadius: '6px',
              padding: '6px 12px',
              fontSize: '12px',
              fontWeight: 600,
              cursor: isSolving ? 'wait' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
            title="Solve branch path from active node using Highs MILP"
          >
            <span>{isSolving ? '⏳ Optimizing...' : '⚡ Optimize Branch'}</span>
          </button>

          <div style={{ fontSize: '12px', color: '#64748b', fontFamily: "'JetBrains Mono', monospace" }}>
            {isSaving ? (
              <span style={{ color: '#f59e0b' }}>● Saving...</span>
            ) : (
              <span style={{ color: '#10b981' }}>✓ Synced</span>
            )}
          </div>

          <button
            type="button"
            onClick={handleDuplicateCurrentPlan}
            style={{
              background: '#1a202e',
              color: '#cbd5e1',
              border: '1px solid #2d3748',
              borderRadius: '6px',
              padding: '6px 10px',
              fontSize: '12px',
              cursor: 'pointer',
            }}
            title="Duplicate selected scenario"
          >
            Duplicate Plan
          </button>

          <button
            type="button"
            onClick={handleDeleteCurrentPlan}
            style={{
              background: 'rgba(244, 63, 94, 0.1)',
              color: '#f43f5e',
              border: '1px solid rgba(244, 63, 94, 0.25)',
              borderRadius: '6px',
              padding: '6px 10px',
              fontSize: '12px',
              cursor: 'pointer',
            }}
            title="Delete selected scenario"
          >
            Delete Plan
          </button>
        </div>
      </div>

      {/* Main Flow Canvas */}
      <div style={{ flex: 1, position: 'relative' }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          fitView
          minZoom={0.2}
          maxZoom={1.5}
          defaultViewport={{ x: 0, y: 0, zoom: 0.85 }}
          proOptions={{ hideAttribution: true }}
        >
          <Background color="#1e2538" gap={20} size={1} />
          <Controls
            style={{
              background: '#121520',
              border: '1px solid #1e2538',
              borderRadius: '8px',
              color: '#f8fafc',
            }}
          />
          <MiniMap
            nodeColor={(n) => {
              if (n.type === 'rootNode') return '#38bdf8';
              if (n.type === 'evaluationNode') return '#10b981';
              return '#64748b';
            }}
            style={{
              background: '#0a0b10',
              border: '1px solid #1e2538',
              borderRadius: '8px',
            }}
          />
        </ReactFlow>
      </div>
    </div>
  );
}

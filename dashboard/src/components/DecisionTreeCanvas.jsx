import React, { useMemo, useCallback, useRef, useEffect, useState } from 'react';
import {
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
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

function DecisionTreeFlow() {
  const { plans, activePlan, activePlanId, activeNodeId, isSaving, isLoading, actions } = usePlanStore();
  const [ddpPreset, setDdpPreset] = useState('default');
  const [isSolving, setIsSolving] = useState(false);
  const containerRef = useRef(null);
  const { fitView } = useReactFlow();

  const handleOptimizeBranch = async () => {
    if (!activePlan || isSolving) return;
    const parentId = activeNodeId || activePlan.rootNodeId;
    const parentNode = activePlan.nodes[parentId];
    const targetGw = parentNode ? parentNode.gameweek + 1 : 6;

    setIsSolving(true);
    try {
      // Collect booked chips across the active plan
      const bookedChips = {
        use_wc: [],
        use_bb: [],
        use_fh: [],
        use_tc: [],
      };
      Object.values(activePlan.nodes || {}).forEach((n) => {
        if (!n.chip || !n.gameweek) return;
        const c = String(n.chip).toUpperCase();
        if (c === 'WC' || c === 'WILDCARD') bookedChips.use_wc.push(n.gameweek);
        else if (c === 'BB' || c === 'BENCH_BOOST' || c === 'BENCHBOOST') bookedChips.use_bb.push(n.gameweek);
        else if (c === 'FH' || c === 'FREE_HIT' || c === 'FREEHIT') bookedChips.use_fh.push(n.gameweek);
        else if (c === 'TC' || c === 'TRIPLE_CAPTAIN' || c === 'TRIPLECAPTAIN') bookedChips.use_tc.push(n.gameweek);
      });

      const res = await fetch('/api/solve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          parentNodeId: parentId,
          target_gw: targetGw,
          preset: ddpPreset,
          horizon: 4,
          use_wc: bookedChips.use_wc,
          use_bb: bookedChips.use_bb,
          use_fh: bookedChips.use_fh,
          use_tc: bookedChips.use_tc,
          parentNode: parentNode ? {
            lineup: parentNode.lineup,
            evaluation: parentNode.evaluation,
            gameweek: parentNode.gameweek,
            chip: parentNode.chip,
          } : null,
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
  useEffect(() => {
    setNodes(flowNodes);
    setEdges(flowEdges);
  }, [flowNodes, flowEdges, setNodes, setEdges]);

  // Auto-fit view when nodes change or on initial render
  useEffect(() => {
    if (nodes.length > 0) {
      const timer = setTimeout(() => {
        fitView({ padding: 0.35, duration: 300 });
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [nodes.length, activePlanId, fitView]);

  // Re-fit view on tab activation or window resize
  useEffect(() => {
    const handleActivated = () => {
      setTimeout(() => {
        fitView({ padding: 0.35, duration: 300 });
      }, 100);
    };
    window.addEventListener('planTabActivated', handleActivated);
    window.addEventListener('resize', handleActivated);
    return () => {
      window.removeEventListener('planTabActivated', handleActivated);
      window.removeEventListener('resize', handleActivated);
    };
  }, [fitView]);

  // Re-fit view when container size changes
  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        if (entry.contentRect.width > 100 && entry.contentRect.height > 100) {
          fitView({ padding: 0.35, duration: 250 });
        }
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, [fitView]);

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
          flexWrap: 'wrap',
          gap: '8px',
          padding: '8px 14px',
          background: '#121520',
          borderBottom: '1px solid #1e2538',
          zIndex: 10,
        }}
      >
        {/* Scenario Tabs */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.06em', color: '#94a3b8', fontWeight: 600 }}>
            Scenario:
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
                  padding: '5px 10px',
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
              padding: '5px 8px',
              fontSize: '11px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
            title="Create new scenario"
          >
            + New
          </button>
        </div>

        {/* Plan Actions & Sync status */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          {/* DDP Solver Preset Selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
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
                padding: '4px 6px',
                outline: 'none',
              }}
            >
              <option value="safe">Safe (75%)</option>
              <option value="default">Default (50%)</option>
              <option value="optimistic">Optimistic (0%)</option>
              <option value="high_risk">High Risk (25%)</option>
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
              padding: '5px 10px',
              fontSize: '11px',
              fontWeight: 600,
              cursor: isSolving ? 'wait' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
            title="Solve branch path from active node using Highs MILP"
          >
            <span>{isSolving ? '⏳ Optimizing...' : '⚡ Optimize'}</span>
          </button>

          <button
            type="button"
            onClick={() => fitView({ padding: 0.25, duration: 300 })}
            style={{
              background: '#1a202e',
              border: '1px solid #2d3748',
              color: '#cbd5e1',
              borderRadius: '6px',
              padding: '5px 8px',
              fontSize: '11px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
            title="Reset view and center all decision tree nodes"
          >
            ⛶ Center
          </button>

          <div style={{ fontSize: '11px', color: '#64748b', fontFamily: "'JetBrains Mono', monospace" }}>
            {isSaving ? (
              <span style={{ color: '#f59e0b' }}>● Saving</span>
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
              padding: '5px 8px',
              fontSize: '11px',
              cursor: 'pointer',
            }}
            title="Duplicate selected scenario"
          >
            Duplicate
          </button>

          <button
            type="button"
            onClick={handleDeleteCurrentPlan}
            style={{
              background: 'rgba(244, 63, 94, 0.1)',
              color: '#f43f5e',
              border: '1px solid rgba(244, 63, 94, 0.25)',
              borderRadius: '6px',
              padding: '5px 8px',
              fontSize: '11px',
              cursor: 'pointer',
            }}
            title="Delete selected scenario"
          >
            Delete
          </button>
        </div>
      </div>

      {/* Main Flow Canvas */}
      <div ref={containerRef} style={{ flex: 1, position: 'relative', width: '100%', height: '100%' }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.35 }}
          minZoom={0.2}
          maxZoom={1.5}
          proOptions={{ hideAttribution: true }}
        >
          <Background color="#1e2538" gap={20} size={1} />
          <Controls
            position="bottom-right"
            style={{
              background: '#121520',
              border: '1px solid #1e2538',
              borderRadius: '8px',
              color: '#f8fafc',
              margin: '12px',
            }}
          />
          <MiniMap
            position="top-right"
            nodeColor={(n) => {
              if (n.type === 'rootNode') return '#38bdf8';
              if (n.type === 'evaluationNode') return '#10b981';
              return '#64748b';
            }}
            style={{
              background: 'rgba(10, 11, 16, 0.85)',
              backdropFilter: 'blur(8px)',
              border: '1px solid #1e2538',
              borderRadius: '8px',
              margin: '12px',
              width: 120,
              height: 80,
            }}
          />
        </ReactFlow>
      </div>
    </div>
  );
}

export default function DecisionTreeCanvas() {
  return (
    <ReactFlowProvider>
      <DecisionTreeFlow />
    </ReactFlowProvider>
  );
}

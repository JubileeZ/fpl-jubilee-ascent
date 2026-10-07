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
  const [solvingDetail, setSolvingDetail] = useState('');
  const containerRef = useRef(null);
  const { fitView } = useReactFlow();

  // Listen for external horizon changes (e.g. from header #plan-horizon select)
  useEffect(() => {
    const handleHorizonEvent = (e) => {
      const h = Number(e.detail?.horizon);
      if (h && h >= 1 && h <= 10) {
        actions.setHorizon(h);
      }
    };
    window.addEventListener('planHorizonChanged', handleHorizonEvent);
    return () => window.removeEventListener('planHorizonChanged', handleHorizonEvent);
  }, [actions]);

  // Per-node solve execution
  const handleOptimizeFromNode = useCallback(async (targetNodeId, opts = {}) => {
    const state = usePlanStore.getState();
    const curPlan = state.plans.find((p) => p.id === state.activePlanId);
    if (!curPlan || isSolving) return;

    const rootId = curPlan.rootNodeId || 'node-root';
    const targetNode = curPlan.nodes[targetNodeId];
    if (!targetNode) return;

    const startGw = curPlan.startGameweek || 6;
    const horizon = curPlan.horizonGameweeks || 5;
    const horizonEnd = startGw + horizon - 1;

    let parentNodeId = targetNode.parentId || rootId;
    let parentNode = curPlan.nodes[parentNodeId];
    let targetGw = targetNode.gameweek;

    if (targetNodeId === rootId) {
      targetGw = startGw;
      parentNodeId = rootId;
      parentNode = curPlan.nodes[rootId];
    }

    const remainingHorizon = Math.max(1, horizonEnd - targetGw + 1);
    const solve3Arms = Boolean(opts.solve3Arms);

    setIsSolving(true);
    setSolvingDetail(`Optimizing from GW${targetGw} to GW${horizonEnd}…`);

    try {
      const bookedChips = {
        use_wc: [],
        use_bb: [],
        use_fh: [],
        use_tc: [],
      };
      Object.values(curPlan.nodes || {}).forEach((n) => {
        if (!n.chip || !n.gameweek) return;
        // Only include chips within the active optimization horizon
        if (n.gameweek < targetGw || n.gameweek > horizonEnd) return;
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
          parentNodeId,
          target_gw: targetGw,
          preset: ddpPreset,
          solve_3_arms: solve3Arms,
          horizon: remainingHorizon,
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

      let attempts = 0;
      while (attempts < 60) {
        await new Promise((r) => setTimeout(r, 600));
        attempts++;
        const pollRes = await fetch('/api/solve');
        if (pollRes.ok) {
          const pollData = await pollRes.json();
          if (pollData.detail) setSolvingDetail(pollData.detail);

          if (pollData.payload?.branch) {
            const branch = pollData.payload.branch;
            if (branch.nodes && Object.keys(branch.nodes).length > 0) {
              const livePlan = usePlanStore.getState().activePlan;
              if (livePlan) {
                if (solve3Arms) {
                  planActions.applyBranchSolve(parentNodeId, branch);
                } else {
                  // Direct straight-line lane update: find path from targetNode down to horizonEnd
                  let existingPath = [];
                  let curr = targetNodeId !== rootId
                    ? livePlan.nodes[targetNodeId]
                    : (livePlan.nodes[rootId]?.childIds?.[0] ? livePlan.nodes[livePlan.nodes[rootId].childIds[0]] : null);
                  while (curr) {
                    existingPath.push(curr.id);
                    if (curr.childIds && curr.childIds.length > 0) {
                      curr = livePlan.nodes[curr.childIds[0]];
                    } else {
                      break;
                    }
                  }

                  const incomingNodeList = Object.values(branch.nodes);
                  if (existingPath.length > 0 && incomingNodeList.length <= existingPath.length) {
                    // Update nodes in-place along this exact straight branch
                    for (let idx = 0; idx < incomingNodeList.length; idx++) {
                      const existId = existingPath[idx];
                      const inc = incomingNodeList[idx];
                      planActions.updateNode(existId, {
                        title: inc.title,
                        lineup: inc.lineup,
                        transfers: inc.transfers,
                        chip: inc.chip,
                        evaluation: inc.evaluation,
                        solverRecommendation: inc.solverRecommendation || {
                          lineup: inc.lineup,
                          transfers: inc.transfers,
                          chip: inc.chip,
                          evaluation: inc.evaluation,
                        },
                        isCustom: false,
                      });
                    }
                  } else {
                    planActions.applyBranchSolve(parentNodeId, branch);
                  }
                }
              }
            }
          }
          if (pollData.status === 'ok') {
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
      setSolvingDetail('');
    }
  }, [activePlan, ddpPreset, isSolving]);

  // Expose on window for external triggers
  useEffect(() => {
    window.solveFromPlanNode = (nodeId, opts) => handleOptimizeFromNode(nodeId, opts);
    return () => {
      delete window.solveFromPlanNode;
    };
  }, [handleOptimizeFromNode]);

  // Strict horizontal straight-line matrix layout
  const { flowNodes, flowEdges } = useMemo(() => {
    if (!activePlan || !activePlan.nodes) {
      return { flowNodes: [], flowEdges: [] };
    }

    const startGw = activePlan.startGameweek || 6;
    const horizon = activePlan.horizonGameweeks || 5;
    const horizonEnd = startGw + horizon - 1;
    const nodes = [];
    const edges = [];

    const rootId = activePlan.rootNodeId || 'node-root';
    const rootNode = activePlan.nodes[rootId];
    if (!rootNode) return { flowNodes: [], flowEdges: [] };

    let nextRow = 0;
    const nodePositions = new Map();

    function layoutBranch(nodeId, row) {
      const node = activePlan.nodes[nodeId];
      if (!node) return;

      const isRoot = node.id === rootId;
      const col = isRoot ? 0 : Math.max(1, node.gameweek - startGw + 1);
      const xPos = 40 + col * 320;
      const yPos = 80 + row * 220;

      nodePositions.set(node.id, { x: xPos, y: yPos });

      const children = (node.childIds || []).filter((cid) => {
        const childNode = activePlan.nodes[cid];
        return childNode && childNode.gameweek <= horizonEnd;
      });

      if (children.length === 0) {
        // Leaf reached
        if (!isRoot) {
          const evalId = `eval-${node.id}`;
          nodes.push({
            id: evalId,
            type: 'evaluationNode',
            position: { x: xPos + 320, y: yPos },
            data: {
              evaluation: node.evaluation || {},
              isTopBranch: row === 0,
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
        return;
      }

      // First child continues along the exact same row (straight horizontal line)
      layoutBranch(children[0], row);
      edges.push({
        id: `edge-${node.id}-${children[0]}`,
        source: node.id,
        target: children[0],
        style: { stroke: '#38bdf8', strokeWidth: 2 },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: '#38bdf8',
        },
      });

      // Split branches drop into separate row lanes below and extend straight horizontally
      for (let i = 1; i < children.length; i++) {
        nextRow += 1;
        const splitRow = nextRow;
        layoutBranch(children[i], splitRow);
        edges.push({
          id: `edge-${node.id}-${children[i]}`,
          source: node.id,
          target: children[i],
          style: { stroke: '#f59e0b', strokeWidth: 2 },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: '#f59e0b',
          },
        });
      }
    }

    layoutBranch(rootId, 0);

    for (const [nid, pos] of nodePositions.entries()) {
      const nodeObj = activePlan.nodes[nid];
      if (!nodeObj) continue;
      const isRoot = nid === rootId;
      nodes.push({
        id: nid,
        type: isRoot ? 'rootNode' : 'planNode',
        position: pos,
        data: {
          node: nodeObj,
          isActive: nid === activeNodeId,
          startGameweek: startGw,
          horizonGameweeks: horizon,
          onSolve: () => handleOptimizeFromNode(nid),
          onResetToSolver: () => planActions.resetNodeToSolver(nid),
        },
      });
    }

    return { flowNodes: nodes, flowEdges: edges };
  }, [activePlan, activeNodeId, handleOptimizeFromNode]);

  const [nodes, setNodes, onNodesChange] = useNodesState(flowNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(flowEdges);

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

  const currentHorizon = activePlan?.horizonGameweeks || 5;

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
          {/* Horizon Selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <label htmlFor="planner-horizon-select" style={{ fontSize: '11px', color: '#94a3b8' }}>
              Horizon:
            </label>
            <select
              id="planner-horizon-select"
              value={currentHorizon}
              onChange={(e) => actions.setHorizon(Number(e.target.value))}
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
              title="Planning Horizon length in gameweeks"
            >
              {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((h) => (
                <option key={h} value={h}>
                  {h} GWs
                </option>
              ))}
            </select>
          </div>

          {/* Risk Preset Selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <label htmlFor="ddp-preset-select" style={{ fontSize: '11px', color: '#94a3b8' }}>
              Risk:
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
              <option value="safe">Safe (0 hits)</option>
              <option value="default">Default (1 hit)</option>
              <option value="optimistic">Optimistic (1 hit)</option>
              <option value="high_risk">High Risk (2 hits)</option>
            </select>
          </div>

          <button
            type="button"
            disabled={isSolving}
            onClick={() => handleOptimizeFromNode(activeNodeId || activePlan?.rootNodeId, { solve3Arms: true })}
            style={{
              background: isSolving ? '#1e2538' : 'rgba(16, 185, 129, 0.15)',
              color: isSolving ? '#64748b' : '#10b981',
              border: '1px solid rgba(16, 185, 129, 0.35)',
              borderRadius: '6px',
              padding: '5px 10px',
              fontSize: '11px',
              fontWeight: 600,
              cursor: isSolving ? 'wait' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
            title="Solve all 3 canonical arms (Optimal, No Hit, Conservative) sequentially from active node"
          >
            <span>{isSolving ? (solvingDetail ? `⏳ ${solvingDetail}` : '⏳ Solving…') : '⚡ Solve 3 Arms'}</span>
          </button>

          <button
            type="button"
            disabled={isSolving}
            onClick={() => handleOptimizeFromNode(activeNodeId || activePlan?.rootNodeId)}
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
            title="Optimize branch path from active box through Horizon End"
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

      {/* Main Flow Canvas with locked nodes */}
      <div ref={containerRef} style={{ flex: 1, position: 'relative', width: '100%', height: '100%' }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable={true}
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

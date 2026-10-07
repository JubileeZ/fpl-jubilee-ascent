import { useEffect, useSyncExternalStore } from 'react';

// In-memory singleton state
let globalState = {
  plans: [],
  activePlanId: null,
  activeNodeId: null,
  isLoading: true,
  isSaving: false,
  error: null,
};

const listeners = new Set();

function emitChange() {
  for (const listener of listeners) {
    listener();
  }
}

let saveTimeout = null;

async function persistPlans(plans, activePlanId) {
  if (saveTimeout) clearTimeout(saveTimeout);
  globalState = { ...globalState, isSaving: true };
  emitChange();

  try {
    const res = await fetch('/api/user-plans', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ plans, activePlanId }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
  } catch (err) {
    console.error('Failed to persist user plans:', err);
    globalState = { ...globalState, error: err.message };
  } finally {
    globalState = { ...globalState, isSaving: false };
    emitChange();
  }
}

function queueSave() {
  if (saveTimeout) clearTimeout(saveTimeout);
  saveTimeout = setTimeout(() => {
    persistPlans(globalState.plans, globalState.activePlanId);
  }, 600);
}

export const planActions = {
  getState() {
    return globalState;
  },

  async init() {
    try {
      globalState = { ...globalState, isLoading: true, error: null };
      emitChange();
      const res = await fetch('/api/user-plans');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const plans = data.plans || [];
      const activePlanId = data.activePlanId || (plans[0] ? plans[0].id : null);
      const activePlan = plans.find((p) => p.id === activePlanId) || plans[0];
      const activeNodeId = activePlan ? (activePlan.activeNodeId || activePlan.rootNodeId) : null;

      globalState = {
        ...globalState,
        plans,
        activePlanId,
        activeNodeId,
        isLoading: false,
      };
      emitChange();

      // Dispatch event to sync external controls (like header select)
      if (activePlan?.horizonGameweeks) {
        window.dispatchEvent(
          new CustomEvent('planHorizonChanged', { detail: { horizon: activePlan.horizonGameweeks } })
        );
      }
    } catch (err) {
      console.error('Failed to load user plans:', err);
      globalState = { ...globalState, isLoading: false, error: err.message };
      emitChange();
    }
  },

  setActivePlan(planId) {
    const plan = globalState.plans.find((p) => p.id === planId);
    if (!plan) return;
    globalState = {
      ...globalState,
      activePlanId: planId,
      activeNodeId: plan.activeNodeId || plan.rootNodeId,
    };
    emitChange();
    queueSave();

    if (plan.horizonGameweeks) {
      window.dispatchEvent(
        new CustomEvent('planHorizonChanged', { detail: { horizon: plan.horizonGameweeks } })
      );
    }
  },

  setActiveNode(nodeId) {
    const activePlan = globalState.plans.find((p) => p.id === globalState.activePlanId);
    if (!activePlan || !activePlan.nodes[nodeId]) return;
    const updatedPlan = { ...activePlan, activeNodeId: nodeId };
    const updatedPlans = globalState.plans.map((p) => (p.id === activePlan.id ? updatedPlan : p));
    globalState = { ...globalState, activeNodeId: nodeId, plans: updatedPlans };
    emitChange();
  },

  setHorizon(horizon) {
    const activePlan = globalState.plans.find((p) => p.id === globalState.activePlanId);
    if (!activePlan) return;
    const clampedHorizon = Math.max(1, Math.min(10, Number(horizon) || 5));
    if (activePlan.horizonGameweeks === clampedHorizon) return;

    const startGw = activePlan.startGameweek || 6;
    const oldHorizonEnd = startGw + (activePlan.horizonGameweeks || 5) - 1;
    const newHorizonEnd = startGw + clampedHorizon - 1;

    let updatedNodes = { ...activePlan.nodes };

    if (newHorizonEnd < oldHorizonEnd) {
      // Prune nodes beyond newHorizonEnd
      const toRemove = new Set();
      Object.values(updatedNodes).forEach((n) => {
        if (n.gameweek > newHorizonEnd && n.parentId) {
          toRemove.add(n.id);
        }
      });
      const filtered = {};
      Object.entries(updatedNodes).forEach(([id, n]) => {
        if (!toRemove.has(id)) {
          filtered[id] = {
            ...n,
            childIds: (n.childIds || []).filter((cid) => !toRemove.has(cid)),
          };
        }
      });
      updatedNodes = filtered;
    } else if (newHorizonEnd > oldHorizonEnd) {
      // Extend every branch ending at a leaf whose gameweek < newHorizonEnd
      const rootId = activePlan.rootNodeId || 'node-root';
      const leafIds = Object.keys(updatedNodes).filter((id) => {
        const n = updatedNodes[id];
        return id !== rootId && (!n.childIds || n.childIds.length === 0);
      });

      for (const leafId of leafIds) {
        let currentParentId = leafId;
        let currentParent = updatedNodes[currentParentId];
        if (!currentParent) continue;

        for (let gw = currentParent.gameweek + 1; gw <= newHorizonEnd; gw++) {
          const newId = `node-gw${gw}-${Math.random().toString(36).slice(2, 7)}`;
          const prevEval = currentParent.evaluation || {};
          const bank = prevEval.bankRemaining ?? activePlan.initialBank ?? 0.0;
          const prevFt = prevEval.freeTransfersNext ?? 1;

          const evalObj = {
            expectedPoints: prevEval.expectedPoints || 55.0,
            pointsVariance: 0.0,
            cumulativePoints: (prevEval.cumulativePoints || 0) + (prevEval.expectedPoints || 55.0),
            hitsTaken: 0,
            netPoints: (prevEval.netPoints || 0) + (prevEval.expectedPoints || 55.0),
            bankRemaining: bank,
            freeTransfersNext: Math.min(5, prevFt + 1),
          };

          const newNode = {
            id: newId,
            parentId: currentParentId,
            childIds: [],
            gameweek: gw,
            title: `GW${gw} (Roll)`,
            lineup: JSON.parse(JSON.stringify(currentParent.lineup)),
            transfers: [],
            chip: null,
            evaluation: evalObj,
            solverRecommendation: {
              lineup: JSON.parse(JSON.stringify(currentParent.lineup || {})),
              transfers: [],
              chip: null,
              evaluation: { ...evalObj },
            },
            isCustom: false,
          };

          updatedNodes[currentParentId] = {
            ...updatedNodes[currentParentId],
            childIds: [...(updatedNodes[currentParentId].childIds || []), newId],
          };
          updatedNodes[newId] = newNode;
          currentParentId = newId;
          currentParent = newNode;
        }
      }
    }

    const nextActiveId = updatedNodes[globalState.activeNodeId]
      ? globalState.activeNodeId
      : activePlan.rootNodeId;

    const updatedPlan = {
      ...activePlan,
      horizonGameweeks: clampedHorizon,
      nodes: updatedNodes,
      activeNodeId: nextActiveId,
    };

    const updatedPlans = globalState.plans.map((p) => (p.id === activePlan.id ? updatedPlan : p));
    globalState = { ...globalState, plans: updatedPlans, activeNodeId: nextActiveId };
    emitChange();
    queueSave();

    window.dispatchEvent(
      new CustomEvent('planHorizonChanged', { detail: { horizon: clampedHorizon } })
    );
  },

  addBranch(parentNodeId) {
    const activePlan = globalState.plans.find((p) => p.id === globalState.activePlanId);
    if (!activePlan) return;
    const parentNode = activePlan.nodes[parentNodeId];
    if (!parentNode) return;

    const startGw = activePlan.startGameweek || 6;
    const horizonEnd = startGw + (activePlan.horizonGameweeks || 5) - 1;
    const nextGw = parentNode.id === activePlan.rootNodeId ? startGw : parentNode.gameweek + 1;
    if (nextGw > horizonEnd) return;

    let updatedNodes = { ...activePlan.nodes };
    let prevId = parentNodeId;
    let prevNode = parentNode;
    let firstNewId = null;

    // Create a full straight-line branch chain from nextGw through horizonEnd
    for (let gw = nextGw; gw <= horizonEnd; gw++) {
      const newId = `node-gw${gw}-${Math.random().toString(36).slice(2, 7)}`;
      if (!firstNewId) firstNewId = newId;

      const prevEval = prevNode.evaluation || {};
      const bank = prevEval.bankRemaining ?? activePlan.initialBank ?? 0.0;
      const prevFt = prevEval.freeTransfersNext ?? 1;

      const evalObj = {
        expectedPoints: prevEval.expectedPoints || 55.0,
        pointsVariance: 0.0,
        cumulativePoints: (prevEval.cumulativePoints || 0) + (prevEval.expectedPoints || 55.0),
        hitsTaken: 0,
        netPoints: (prevEval.netPoints || 0) + (prevEval.expectedPoints || 55.0),
        bankRemaining: bank,
        freeTransfersNext: Math.min(5, prevFt + 1),
      };

      const newNode = {
        id: newId,
        parentId: prevId,
        childIds: [],
        gameweek: gw,
        title: gw === nextGw ? `GW${gw} (Branch)` : `GW${gw} (Roll)`,
        lineup: JSON.parse(JSON.stringify(prevNode.lineup)),
        transfers: [],
        chip: null,
        evaluation: evalObj,
        solverRecommendation: {
          lineup: JSON.parse(JSON.stringify(prevNode.lineup || {})),
          transfers: [],
          chip: null,
          evaluation: { ...evalObj },
        },
        isCustom: false,
      };

      updatedNodes[prevId] = {
        ...updatedNodes[prevId],
        childIds: [...(updatedNodes[prevId].childIds || []), newId],
      };
      updatedNodes[newId] = newNode;
      prevId = newId;
      prevNode = newNode;
    }

    const updatedPlan = {
      ...activePlan,
      nodes: updatedNodes,
      activeNodeId: firstNewId || parentNodeId,
    };

    const updatedPlans = globalState.plans.map((p) => (p.id === activePlan.id ? updatedPlan : p));
    globalState = { ...globalState, plans: updatedPlans, activeNodeId: firstNewId || parentNodeId };
    emitChange();
    queueSave();
  },

  resetNodeToSolver(nodeId) {
    const activePlan = globalState.plans.find((p) => p.id === globalState.activePlanId);
    if (!activePlan) return;
    const node = activePlan.nodes[nodeId];
    if (!node || !node.solverRecommendation) return;

    const rec = node.solverRecommendation;
    const updatedNode = {
      ...node,
      lineup: JSON.parse(JSON.stringify(rec.lineup)),
      transfers: JSON.parse(JSON.stringify(rec.transfers || [])),
      chip: rec.chip,
      evaluation: JSON.parse(JSON.stringify(rec.evaluation || node.evaluation)),
      isCustom: false,
    };

    this.updateNode(nodeId, updatedNode, true);
  },

  applyBranchSolve(parentId, branchData) {
    const activePlan = globalState.plans.find((p) => p.id === globalState.activePlanId);
    if (!activePlan || !branchData) return;
    const parentNode = activePlan.nodes[parentId];
    if (!parentNode) return;

    const incomingNodes = branchData.nodes || {};
    const rootChildIds = branchData.rootChildIds || (branchData.rootChildId ? [branchData.rootChildId] : []);
    if (Object.keys(incomingNodes).length === 0) return;

    let updatedNodes = { ...activePlan.nodes };

    // Update parent childIds
    const combinedChildIds = Array.from(new Set([...(parentNode.childIds || []), ...rootChildIds]));
    updatedNodes[parentId] = {
      ...parentNode,
      childIds: combinedChildIds,
    };

    // Merge incoming nodes
    for (const [nid, nodeObj] of Object.entries(incomingNodes)) {
      updatedNodes[nid] = {
        ...nodeObj,
        solverRecommendation: nodeObj.solverRecommendation || {
          lineup: JSON.parse(JSON.stringify(nodeObj.lineup || {})),
          transfers: JSON.parse(JSON.stringify(nodeObj.transfers || [])),
          chip: nodeObj.chip || null,
          evaluation: JSON.parse(JSON.stringify(nodeObj.evaluation || {})),
        },
        isCustom: false,
      };
    }

    const firstActive = rootChildIds[0] || parentId;
    const updatedPlan = {
      ...activePlan,
      nodes: updatedNodes,
      activeNodeId: firstActive,
    };

    const updatedPlans = globalState.plans.map((p) => (p.id === activePlan.id ? updatedPlan : p));
    globalState = { ...globalState, plans: updatedPlans, activeNodeId: firstActive };
    emitChange();
    queueSave();
  },

  duplicateBranch(nodeId) {
    const activePlan = globalState.plans.find((p) => p.id === globalState.activePlanId);
    if (!activePlan) return;
    const sourceNode = activePlan.nodes[nodeId];
    if (!sourceNode || !sourceNode.parentId) return;

    const parentNode = activePlan.nodes[sourceNode.parentId];
    if (!parentNode) return;

    const cloneSubtree = (srcId, newParentId) => {
      const src = activePlan.nodes[srcId];
      if (!src) return { newNodes: {}, rootCloneId: null };
      const cloneId = `node-gw${src.gameweek}-${Math.random().toString(36).slice(2, 7)}`;
      const clonedNode = {
        ...JSON.parse(JSON.stringify(src)),
        id: cloneId,
        parentId: newParentId,
        childIds: [],
        title: `${src.title || `GW${src.gameweek}`} (Copy)`,
      };
      let combined = { [cloneId]: clonedNode };
      for (const childId of src.childIds || []) {
        const { newNodes, rootCloneId } = cloneSubtree(childId, cloneId);
        clonedNode.childIds.push(rootCloneId);
        combined = { ...combined, ...newNodes };
      }
      return { newNodes: combined, rootCloneId: cloneId };
    };

    const { newNodes, rootCloneId } = cloneSubtree(nodeId, parentNode.id);
    const updatedParent = {
      ...parentNode,
      childIds: [...(parentNode.childIds || []), rootCloneId],
    };

    const updatedNodes = {
      ...activePlan.nodes,
      [parentNode.id]: updatedParent,
      ...newNodes,
    };

    const updatedPlan = {
      ...activePlan,
      nodes: updatedNodes,
      activeNodeId: rootCloneId,
    };

    const updatedPlans = globalState.plans.map((p) => (p.id === activePlan.id ? updatedPlan : p));
    globalState = { ...globalState, plans: updatedPlans, activeNodeId: rootCloneId };
    emitChange();
    queueSave();
  },

  deleteBranch(nodeId) {
    const activePlan = globalState.plans.find((p) => p.id === globalState.activePlanId);
    if (!activePlan) return;
    const targetNode = activePlan.nodes[nodeId];
    if (!targetNode || !targetNode.parentId) return; // Cannot delete root

    const parentNode = activePlan.nodes[targetNode.parentId];
    if (!parentNode) return;

    // Collect all descendants
    const toDelete = new Set();
    const collectDescendants = (id) => {
      toDelete.add(id);
      const n = activePlan.nodes[id];
      if (n && n.childIds) {
        for (const cid of n.childIds) collectDescendants(cid);
      }
    };
    collectDescendants(nodeId);

    const updatedNodes = {};
    for (const [k, v] of Object.entries(activePlan.nodes)) {
      if (!toDelete.has(k)) {
        if (k === parentNode.id) {
          updatedNodes[k] = {
            ...v,
            childIds: (v.childIds || []).filter((cid) => cid !== nodeId),
          };
        } else {
          updatedNodes[k] = v;
        }
      }
    }

    const nextActiveId = toDelete.has(globalState.activeNodeId)
      ? parentNode.id
      : globalState.activeNodeId;

    const updatedPlan = {
      ...activePlan,
      nodes: updatedNodes,
      activeNodeId: nextActiveId,
    };

    const updatedPlans = globalState.plans.map((p) => (p.id === activePlan.id ? updatedPlan : p));
    globalState = { ...globalState, plans: updatedPlans, activeNodeId: nextActiveId };
    emitChange();
    queueSave();
  },

  createPlan(name = 'New Scenario') {
    const activePlan = globalState.plans.find((p) => p.id === globalState.activePlanId) || globalState.plans[0];
    const newPlanId = `plan-${Math.random().toString(36).slice(2, 7)}`;
    const clonedPlan = activePlan
      ? {
          ...JSON.parse(JSON.stringify(activePlan)),
          id: newPlanId,
          name: name.trim() || 'New Scenario',
        }
      : {
          id: newPlanId,
          name: name.trim() || 'New Scenario',
          startGameweek: 6,
          horizonGameweeks: 5,
          initialBank: 0.0,
          initialFreeTransfers: 1,
          rootNodeId: 'node-root',
          activeNodeId: 'node-root',
          nodes: {},
        };

    const updatedPlans = [...globalState.plans, clonedPlan];
    globalState = {
      ...globalState,
      plans: updatedPlans,
      activePlanId: newPlanId,
      activeNodeId: clonedPlan.activeNodeId || clonedPlan.rootNodeId,
    };
    emitChange();
    queueSave();
  },

  duplicatePlan(planId) {
    const srcPlan = globalState.plans.find((p) => p.id === planId);
    if (!srcPlan) return;
    const newPlanId = `plan-${Math.random().toString(36).slice(2, 7)}`;
    const clonedPlan = {
      ...JSON.parse(JSON.stringify(srcPlan)),
      id: newPlanId,
      name: `${srcPlan.name} (Copy)`,
    };
    const updatedPlans = [...globalState.plans, clonedPlan];
    globalState = {
      ...globalState,
      plans: updatedPlans,
      activePlanId: newPlanId,
      activeNodeId: clonedPlan.activeNodeId,
    };
    emitChange();
    queueSave();
  },

  deletePlan(planId) {
    if (globalState.plans.length <= 1) return; // Keep at least one plan
    const updatedPlans = globalState.plans.filter((p) => p.id !== planId);
    const nextPlan = updatedPlans[0];
    globalState = {
      ...globalState,
      plans: updatedPlans,
      activePlanId: nextPlan.id,
      activeNodeId: nextPlan.activeNodeId || nextPlan.rootNodeId,
    };
    emitChange();
    queueSave();
  },

  updateNode(nodeId, updates, propagateDownstream = false) {
    const activePlan = globalState.plans.find((p) => p.id === globalState.activePlanId);
    if (!activePlan) return;
    const node = activePlan.nodes[nodeId];
    if (!node) return;

    // Detect if manual changes were made (transfers/lineup/chip altered)
    let isCustom = updates.isCustom;
    if (isCustom === undefined) {
      if (updates.lineup !== undefined || updates.transfers !== undefined || updates.chip !== undefined) {
        isCustom = true;
      } else {
        isCustom = node.isCustom ?? false;
      }
    }

    // Preserve baseline recommendation if node doesn't already have one
    let solverRec = updates.solverRecommendation !== undefined ? updates.solverRecommendation : node.solverRecommendation;
    if (!solverRec && isCustom) {
      solverRec = {
        lineup: JSON.parse(JSON.stringify(node.lineup || {})),
        transfers: JSON.parse(JSON.stringify(node.transfers || [])),
        chip: node.chip || null,
        evaluation: JSON.parse(JSON.stringify(node.evaluation || {})),
      };
    }

    const updatedNode = { ...node, ...updates, isCustom, solverRecommendation: solverRec };
    const updatedNodes = { ...activePlan.nodes, [nodeId]: updatedNode };

    if (propagateDownstream && node.childIds && node.childIds.length > 0) {
      const queue = [...node.childIds];
      while (queue.length > 0) {
        const cid = queue.shift();
        const child = updatedNodes[cid];
        if (!child) continue;
        const parent = updatedNodes[child.parentId];
        if (!parent) continue;

        const parentBank = parent.evaluation?.bankRemaining ?? activePlan.initialBank ?? 0.0;
        const parentFt = parent.evaluation?.freeTransfersNext ?? 1;
        const childTransfers = child.transfers || [];

        // If child has no manual transfers, inherit parent lineup
        const inheritLineup = childTransfers.length === 0;
        const nextSlots = inheritLineup && parent.lineup?.slots ? { ...parent.lineup.slots } : child.lineup?.slots;

        const isFreeChip = child.chip === 'WC' || child.chip === 'FH' || child.chip === 'wildcard' || child.chip === 'freehit';
        const childHits = isFreeChip ? 0 : Math.max(0, childTransfers.length - parentFt);
        const childRemFt = isFreeChip ? 1 : Math.max(0, parentFt - childTransfers.length);
        const childFtNext = isFreeChip ? 1 : Math.min(5, childRemFt + 1);

        updatedNodes[cid] = {
          ...child,
          lineup: nextSlots ? { ...child.lineup, slots: nextSlots } : child.lineup,
          evaluation: {
            ...child.evaluation,
            bankRemaining: parentBank,
            hitsTaken: childHits,
            freeTransfersNext: childFtNext,
          },
        };

        if (child.childIds && child.childIds.length > 0) {
          queue.push(...child.childIds);
        }
      }
    }

    const updatedPlan = { ...activePlan, nodes: updatedNodes };
    const updatedPlans = globalState.plans.map((p) => (p.id === activePlan.id ? updatedPlan : p));

    globalState = { ...globalState, plans: updatedPlans };
    emitChange();
    queueSave();
  },
};

export function usePlanStore() {
  const state = useSyncExternalStore(
    (callback) => {
      listeners.add(callback);
      return () => listeners.delete(callback);
    },
    () => globalState
  );

  useEffect(() => {
    if (globalState.plans.length === 0 && globalState.isLoading) {
      planActions.init();
    }
  }, []);

  const activePlan = state.plans.find((p) => p.id === state.activePlanId) || null;
  const activeNode = activePlan && state.activeNodeId ? activePlan.nodes[state.activeNodeId] || null : null;

  return {
    ...state,
    activePlan,
    activeNode,
    actions: planActions,
  };
}

usePlanStore.getState = () => globalState;

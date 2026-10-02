import { useState, useEffect, useCallback, useSyncExternalStore } from 'react';

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
  },

  setActiveNode(nodeId) {
    const activePlan = globalState.plans.find((p) => p.id === globalState.activePlanId);
    if (!activePlan || !activePlan.nodes[nodeId]) return;
    const updatedPlan = { ...activePlan, activeNodeId: nodeId };
    const updatedPlans = globalState.plans.map((p) => (p.id === activePlan.id ? updatedPlan : p));
    globalState = { ...globalState, activeNodeId: nodeId, plans: updatedPlans };
    emitChange();
  },

  addBranch(parentNodeId) {
    const activePlan = globalState.plans.find((p) => p.id === globalState.activePlanId);
    if (!activePlan) return;
    const parentNode = activePlan.nodes[parentNodeId];
    if (!parentNode) return;

    const nextGw = parentNode.gameweek + 1;
    const newId = `node-gw${nextGw}-${Math.random().toString(36).slice(2, 7)}`;
    const prevEval = parentNode.evaluation || {};
    const bank = prevEval.bankRemaining ?? activePlan.initialBank ?? 0.0;
    const prevFt = prevEval.freeTransfersNext ?? 1;

    const newNode = {
      id: newId,
      parentId: parentNodeId,
      childIds: [],
      gameweek: nextGw,
      title: `GW${nextGw} Branch`,
      lineup: JSON.parse(JSON.stringify(parentNode.lineup)),
      transfers: [],
      chip: null,
      evaluation: {
        expectedPoints: 57.0,
        pointsVariance: 11.5,
        cumulativePoints: (prevEval.cumulativePoints || 0) + 57.0,
        hitsTaken: 0,
        netPoints: (prevEval.netPoints || 0) + 57.0,
        bankRemaining: bank,
        freeTransfersNext: Math.min(5, prevFt + 1),
      },
    };

    const updatedParent = {
      ...parentNode,
      childIds: [...(parentNode.childIds || []), newId],
    };

    const updatedNodes = {
      ...activePlan.nodes,
      [parentNodeId]: updatedParent,
      [newId]: newNode,
    };

    const updatedPlan = {
      ...activePlan,
      nodes: updatedNodes,
      activeNodeId: newId,
    };

    const updatedPlans = globalState.plans.map((p) => (p.id === activePlan.id ? updatedPlan : p));
    globalState = { ...globalState, plans: updatedPlans, activeNodeId: newId };
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

  updateNode(nodeId, updates) {
    const activePlan = globalState.plans.find((p) => p.id === globalState.activePlanId);
    if (!activePlan) return;
    const node = activePlan.nodes[nodeId];
    if (!node) return;

    const updatedNode = { ...node, ...updates };
    const updatedNodes = { ...activePlan.nodes, [nodeId]: updatedNode };
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

import React, { useState } from 'react';
import DecisionTreeCanvas from './components/DecisionTreeCanvas';
import SquadPitchDrawer from './components/SquadPitchDrawer';
import TransferReplacementDrawer from './components/TransferReplacementDrawer';
import SquadProjectionsTable from './components/SquadProjectionsTable';
import SquadFixturesTable from './components/SquadFixturesTable';
import PlansEvaluationSuite from './components/PlansEvaluationSuite';
import { usePlanStore } from './store/usePlanStore';

export default function DecisionPlannerApp() {
  const [activeTab, setActiveTab] = useState('projections');
  const [replacementDrawer, setReplacementDrawer] = useState({
    isOpen: false,
    slot: null,
    player: null,
  });

  const { activeNode, activePlan } = usePlanStore();

  return (
    <div className="decision-planner-container">
      {/* Main Dual-Viewport Workspace */}
      <div className="planner-split-workspace">
        {/* Left Viewport: Decision Tree Canvas & Pitch Overlay */}
        <section className="planner-canvas-viewport" aria-label="Decision Tree Canvas" style={{ display: 'flex', flexDirection: 'column', height: '100%', position: 'relative' }}>
          <div style={{ flex: 1, height: '100%', width: '100%', position: 'relative', overflow: 'hidden' }}>
            <DecisionTreeCanvas />
          </div>

          {/* Bottom-Left Pitch Overlay */}
          <SquadPitchDrawer
            onOpenReplacementDrawer={(slot, player) =>
              setReplacementDrawer({ isOpen: true, slot, player })
            }
          />

          {/* Transfer Replacement Drawer */}
          <TransferReplacementDrawer
            isOpen={replacementDrawer.isOpen}
            onClose={() => setReplacementDrawer({ isOpen: false, slot: null, player: null })}
            replacedSlot={replacementDrawer.slot}
            replacedPlayer={replacementDrawer.player}
          />
        </section>

        {/* Right Viewport: Tabbed Analytics & Optimizer Panel */}
        <section className="planner-analytics-viewport" aria-label="Analytics & Optimizer Panel" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
          <nav className="analytics-tabs-nav" role="tablist">
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === 'projections'}
              className={`analytics-tab-btn ${activeTab === 'projections' ? 'active' : ''}`}
              onClick={() => setActiveTab('projections')}
            >
              PROJECTIONS
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === 'optimise'}
              className={`analytics-tab-btn ${activeTab === 'optimise' ? 'active' : ''}`}
              onClick={() => setActiveTab('optimise')}
            >
              OPTIMISE
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === 'plans'}
              className={`analytics-tab-btn ${activeTab === 'plans' ? 'active' : ''}`}
              onClick={() => setActiveTab('plans')}
            >
              PLANS
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === 'fixtures'}
              className={`analytics-tab-btn ${activeTab === 'fixtures' ? 'active' : ''}`}
              onClick={() => setActiveTab('fixtures')}
            >
              FIXTURES
            </button>
          </nav>

          <div className="analytics-tab-content" style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            {activeTab === 'projections' && (
              <SquadProjectionsTable
                onSelectPlayer={(slot, player) =>
                  setReplacementDrawer({ isOpen: true, slot, player })
                }
              />
            )}

            {activeTab === 'optimise' && (
              <div className="tab-pane optimise-pane" style={{ padding: '16px', overflowY: 'auto' }}>
                <div className="pane-header" style={{ marginBottom: '14px' }}>
                  <h3 style={{ fontSize: '15px', color: '#f8fafc', fontWeight: 700, margin: 0 }}>MILP Branch Optimizer</h3>
                  <span className="pane-subtitle" style={{ fontSize: '11px', color: '#94a3b8' }}>
                    Stochastic Highs solver tuning · Dynamic Disruption Probability (DDP)
                  </span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                  <div style={{ background: '#0d111c', border: '1px solid #1e2538', borderRadius: '8px', padding: '12px' }}>
                    <div style={{ fontSize: '12px', fontWeight: 600, color: '#f8fafc', marginBottom: '4px' }}>
                      Active Branch Node: <span style={{ color: '#38bdf8' }}>{activeNode?.title || 'GW6 (Start)'}</span>
                    </div>
                    <div style={{ fontSize: '11px', color: '#64748b' }}>
                      Optimization executes downstream from this decision state. Transfers and captaincy lock in prior gameweeks.
                    </div>
                  </div>

                  <div style={{ background: '#0d111c', border: '1px solid #1e2538', borderRadius: '8px', padding: '12px' }}>
                    <div style={{ fontSize: '12px', fontWeight: 600, color: '#f8fafc', marginBottom: '8px' }}>
                      DDP Formulation Presets
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                      <div style={{ background: '#121520', border: '1px solid rgba(56, 189, 248, 0.3)', borderRadius: '6px', padding: '8px' }}>
                        <div style={{ fontSize: '11px', fontWeight: 700, color: '#38bdf8' }}>Default (50% DDP)</div>
                        <div style={{ fontSize: '10px', color: '#94a3b8' }}>decay=0.85 · bench_wt=0.10</div>
                      </div>
                      <div style={{ background: '#121520', border: '1px solid #1e2538', borderRadius: '6px', padding: '8px' }}>
                        <div style={{ fontSize: '11px', fontWeight: 700, color: '#10b981' }}>Safe (75% DDP)</div>
                        <div style={{ fontSize: '10px', color: '#94a3b8' }}>decay=0.75 · bench_wt=0.20</div>
                      </div>
                      <div style={{ background: '#121520', border: '1px solid #1e2538', borderRadius: '6px', padding: '8px' }}>
                        <div style={{ fontSize: '11px', fontWeight: 700, color: '#f59e0b' }}>High Risk (25% DDP)</div>
                        <div style={{ fontSize: '10px', color: '#94a3b8' }}>decay=0.92 · bench_wt=0.05</div>
                      </div>
                      <div style={{ background: '#121520', border: '1px solid #1e2538', borderRadius: '6px', padding: '8px' }}>
                        <div style={{ fontSize: '11px', fontWeight: 700, color: '#a855f7' }}>Optimistic (0% DDP)</div>
                        <div style={{ fontSize: '10px', color: '#94a3b8' }}>decay=1.00 · bench_wt=0.03</div>
                      </div>
                    </div>
                  </div>

                  <div style={{ background: '#0d111c', border: '1px solid #1e2538', borderRadius: '8px', padding: '12px' }}>
                    <div style={{ fontSize: '12px', fontWeight: 600, color: '#f8fafc', marginBottom: '4px' }}>
                      Objective Formulation
                    </div>
                    <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', color: '#38bdf8', background: '#06080e', padding: '8px', borderRadius: '5px' }}>
                      max Σ [ w_t · (xP_start + p_sub · xP_bench) - 4 · Hits + 0.1 · ITB ]
                    </div>
                    <p style={{ fontSize: '11px', color: '#94a3b8', marginTop: '6px', lineHeight: 1.4 }}>
                      Uses Highs interior-point & simplex branch-and-bound solver with sub-1% optimality proof.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'plans' && (
              <div className="tab-pane plans-pane" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                <PlansEvaluationSuite />
              </div>
            )}

            {activeTab === 'fixtures' && <SquadFixturesTable />}
          </div>
        </section>
      </div>
    </div>
  );
}

import React, { useState } from 'react';
import DecisionTreeCanvas from './components/DecisionTreeCanvas';
import SquadPitchDrawer from './components/SquadPitchDrawer';
import TransferReplacementDrawer from './components/TransferReplacementDrawer';

import PlansEvaluationSuite from './components/PlansEvaluationSuite';

export default function DecisionPlannerApp() {
  const [activeTab, setActiveTab] = useState('projections');
  const [replacementDrawer, setReplacementDrawer] = useState({
    isOpen: false,
    slot: null,
    player: null,
  });

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
              <div className="tab-pane projections-pane" style={{ padding: '16px' }}>
                <div className="pane-header">
                  <h3>Player Expected Points</h3>
                  <span className="pane-subtitle">Multi-gameweek projections from Model Champion</span>
                </div>
                <p className="pane-hint">
                  Explore player pool in the left Explorer tab or test candidate transfers via the pitch replacement drawer.
                </p>
              </div>
            )}

            {activeTab === 'optimise' && (
              <div className="tab-pane optimise-pane" style={{ padding: '16px' }}>
                <div className="pane-header">
                  <h3>MILP Branch Optimizer</h3>
                  <span className="pane-subtitle">Highs solver tuning & stochastic risk dials</span>
                </div>
                <div className="preset-selector-row" style={{ display: 'flex', gap: '8px', margin: '14px 0' }}>
                  <span className="preset-chip active" style={{ background: '#1e2538', color: '#38bdf8', padding: '6px 10px', borderRadius: '6px', fontSize: '12px' }}>Default (50% DDP)</span>
                  <span className="preset-chip" style={{ background: '#121520', border: '1px solid #1e2538', padding: '6px 10px', borderRadius: '6px', fontSize: '12px' }}>Safe (75% DDP)</span>
                  <span className="preset-chip" style={{ background: '#121520', border: '1px solid #1e2538', padding: '6px 10px', borderRadius: '6px', fontSize: '12px' }}>High Risk (25% DDP)</span>
                  <span className="preset-chip" style={{ background: '#121520', border: '1px solid #1e2538', padding: '6px 10px', borderRadius: '6px', fontSize: '12px' }}>Optimistic (0% DDP)</span>
                </div>
                <p className="pane-hint">
                  Click "⚡ Optimize Branch" on the decision tree toolbar to run MILP branch generation with chosen DDP preset.
                </p>
              </div>
            )}

            {activeTab === 'plans' && (
              <div className="tab-pane plans-pane" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                <PlansEvaluationSuite />
              </div>
            )}

            {activeTab === 'fixtures' && (
              <div className="tab-pane fixtures-pane">
                <div className="pane-header">
                  <h3>Fixture Ticker</h3>
                  <span className="pane-subtitle">Modified FDR and matchup difficulty matrix</span>
                </div>
                <p className="pane-hint">Club strength and defensive difficulty ratings across the planning horizon.</p>
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

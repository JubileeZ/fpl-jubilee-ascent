import React, { useState } from 'react';

export default function DecisionPlannerApp() {
  const [activeTab, setActiveTab] = useState('projections');
  const [horizon, setHorizon] = useState(8);
  const [selectedGw, setSelectedGw] = useState(6);
  const [pitchExpanded, setPitchExpanded] = useState(false);

  return (
    <div className="decision-planner-container">
      {/* Top Action Bar */}
      <header className="planner-action-bar">
        <div className="action-bar-left">
          <button type="button" className="btn btn-action" title="Create new scenario branch">
            <span>+</span> Create Branch
          </button>
          <button type="button" className="btn btn-action" title="Duplicate selected branch">
            Duplicate
          </button>
          <button type="button" className="btn btn-action btn-danger-action" title="Delete selected branch">
            Delete
          </button>
          <button type="button" className="btn btn-action" title="Configure scenario settings">
            Configure
          </button>
        </div>

        <div className="action-bar-right">
          <label className="horizon-label" htmlFor="planner-horizon-select">
            Lookahead:
            <select
              id="planner-horizon-select"
              className="select-input select-horizon"
              value={horizon}
              onChange={(e) => setHorizon(Number(e.target.value))}
            >
              {[3, 4, 5, 6, 8, 10, 12, 15].map((gws) => (
                <option key={gws} value={gws}>
                  {gws} GWs
                </option>
              ))}
            </select>
          </label>
        </div>
      </header>

      {/* Main Dual-Viewport Workspace */}
      <div className="planner-split-workspace">
        {/* Left Viewport: Decision Tree Canvas & Pitch Overlay */}
        <section className="planner-canvas-viewport" aria-label="Decision Tree Canvas">
          <div className="tree-canvas-placeholder" id="decision-tree-canvas-mount">
            <div className="canvas-watermark">
              <span className="watermark-title">Decision Tree Canvas</span>
              <p className="watermark-desc">
                Branching scenario decision tree powered by React Flow. Select a node to inspect squad, test transfers, or branch paths.
              </p>
            </div>
          </div>

          {/* Bottom-Left Pitch Overlay */}
          <aside className={`planner-pitch-drawer ${pitchExpanded ? 'expanded' : 'docked'}`}>
            <div className="pitch-drawer-header">
              <div className="pitch-stepper">
                <button
                  type="button"
                  className="btn-stepper"
                  onClick={() => setSelectedGw((gw) => Math.max(1, gw - 1))}
                  title="Previous Gameweek"
                >
                  ◀
                </button>
                <span className="current-gw-badge">GW {selectedGw}</span>
                <button
                  type="button"
                  className="btn-stepper"
                  onClick={() => setSelectedGw((gw) => Math.min(38, gw + 1))}
                  title="Next Gameweek"
                >
                  ▶
                </button>
              </div>

              <div className="pitch-drawer-actions">
                <button
                  type="button"
                  className="btn-drawer-toggle"
                  onClick={() => setPitchExpanded(!pitchExpanded)}
                  title={pitchExpanded ? 'Dock Pitch' : 'Expand Pitch'}
                >
                  {pitchExpanded ? '▼ Dock' : '▲ Expand'}
                </button>
              </div>
            </div>

            <div className="pitch-drawer-body">
              <div className="pitch-squad-grid" id="planner-squad-pitch-mount">
                {/* 15 Player formation mounted in Ticket #139 */}
                <div className="pitch-placeholder-note">
                  Interactive Squad Pitch (11 Starters + 4 Bench) · Click a player to swap or open replacement candidate drawer.
                </div>
              </div>

              {/* Points Distribution Gaussian Summary */}
              <div className="pitch-distribution-summary">
                <div className="dist-metric">
                  <span className="metric-label">Mean</span>
                  <span className="metric-value">60.9 pts</span>
                </div>
                <div className="dist-metric">
                  <span className="metric-label">Crowd Avg</span>
                  <span className="metric-value text-muted">53.2 pts</span>
                </div>
                <div className="dist-metric">
                  <span className="metric-label">60+ pts</span>
                  <span className="metric-value text-accent">52.5%</span>
                </div>
              </div>
            </div>
          </aside>
        </section>

        {/* Right Viewport: Tabbed Analytics & Optimizer Panel */}
        <section className="planner-analytics-viewport" aria-label="Analytics & Optimizer Panel">
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

          <div className="analytics-tab-content">
            {activeTab === 'projections' && (
              <div className="tab-pane projections-pane">
                <div className="pane-header">
                  <h3>Player Expected Points</h3>
                  <span className="pane-subtitle">Multi-gameweek projections from Model Champion</span>
                </div>
                <p className="pane-hint">
                  Heatmap-shaded projection matrix with custom belief overrides. (Wired in Ticket #138).
                </p>
              </div>
            )}

            {activeTab === 'optimise' && (
              <div className="tab-pane optimise-pane">
                <div className="pane-header">
                  <h3>MILP Branch Optimizer</h3>
                  <span className="pane-subtitle">Highs solver tuning & stochastic risk dials</span>
                </div>
                <div className="preset-selector-row">
                  <span className="preset-chip active">Default (50% DDP)</span>
                  <span className="preset-chip">Safe (75% DDP)</span>
                  <span className="preset-chip">High Risk (25% DDP)</span>
                  <span className="preset-chip">Optimistic (0% DDP)</span>
                </div>
                <p className="pane-hint">
                  Disruption probability, transfer hit penalties, and natural-language constraint rules. (Wired in Ticket #141).
                </p>
              </div>
            )}

            {activeTab === 'plans' && (
              <div className="tab-pane plans-pane">
                <div className="pane-header">
                  <h3>Multi-Plan Comparison</h3>
                  <span className="pane-subtitle">Side-by-side scenario evaluation & Efficient Frontier</span>
                </div>
                <p className="pane-hint">
                  Gaussian probability distribution curves, scatter plots (Expected Points vs Risk), and EO swing analysis. (Wired in Ticket #142).
                </p>
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

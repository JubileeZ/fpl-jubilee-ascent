import React from 'react';
import { createRoot } from 'react-dom/client';
import DecisionPlannerApp from './App.jsx';

function mountPlanner() {
  const mountEl = document.getElementById('decision-planner-mount');
  if (mountEl && !mountEl.__reactRoot) {
    const root = createRoot(mountEl);
    mountEl.__reactRoot = root;
    root.render(
      <React.StrictMode>
        <DecisionPlannerApp />
      </React.StrictMode>
    );
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', mountPlanner);
} else {
  mountPlanner();
}

export { mountPlanner };

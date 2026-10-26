"""Simulation runner and validation harness for sqrt(n_s)-scaled seasonal segment regression floors
(Wayfinder Ticket #172, ADR 0064).

Demonstrates the statistical normalization of segment regression floors across asymmetric windows:
- cold_start (n=4):  -0.25 pts/GW (max -1.00 cumulative pt, z = -0.227 SE)
- early_mid  (n=15): -0.15 pts/GW (max -2.25 cumulative pts, z = -0.264 SE)
- late       (n=19): -0.13 pts/GW (max -2.47 cumulative pts, z = -0.258 SE)
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np

from backtesting.promotion import (
    COLD_START_PARITY_TOL,
    LATE_SEGMENT_REGRESSION_TOL,
    SEGMENT_REGRESSION_TOL,
)


@dataclass(frozen=True)
class SegmentStat:
    name: str
    n_gws: int
    std_err: float
    legacy_tol: float
    legacy_z: float
    legacy_max_loss: float
    scaled_tol: float
    scaled_z: float
    scaled_max_loss: float
    null_rejection_rate_legacy: float
    null_rejection_rate_scaled: float


def simulate_segment_properties(
    sigma: float = 2.20,
    n_sims: int = 50_000,
    seed: int = 42,
) -> list[SegmentStat]:
    rng = np.random.default_rng(seed)
    configs = [
        ("cold_start", 4, 0.05, COLD_START_PARITY_TOL),
        ("early_mid", 15, 0.15, SEGMENT_REGRESSION_TOL),
        ("late", 19, 0.15, LATE_SEGMENT_REGRESSION_TOL),
    ]

    stats: list[SegmentStat] = []
    for name, n, leg_tol, sc_tol in configs:
        se = sigma / np.sqrt(n)
        # Sample null delta draws: mean 0, variance sigma^2 / n
        sample_means = rng.normal(loc=0.0, scale=se, size=n_sims)
        rej_leg = float((sample_means < -leg_tol).mean())
        rej_sc = float((sample_means < -sc_tol).mean())

        stats.append(
            SegmentStat(
                name=name,
                n_gws=n,
                std_err=float(se),
                legacy_tol=float(leg_tol),
                legacy_z=float(-leg_tol / se),
                legacy_max_loss=float(n * leg_tol),
                scaled_tol=float(sc_tol),
                scaled_z=float(-sc_tol / se),
                scaled_max_loss=float(n * sc_tol),
                null_rejection_rate_legacy=rej_leg,
                null_rejection_rate_scaled=rej_sc,
            )
        )
    return stats


def generate_interactive_html(stats: list[SegmentStat], output_path: Path) -> None:
    data_json = json.dumps([s.__dict__ for s in stats], indent=2)
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>ADR 0064: sqrt(n_s)-Scaled Seasonal Segment Guardrails (Ticket #172)</title>
  <style>
    :root {{
      --bg: #090a0f;
      --card-bg: #13151f;
      --border: #23273a;
      --text: #f0f2f8;
      --text-muted: #8b92ab;
      --accent: #10b981;
      --accent-dim: rgba(16, 185, 129, 0.15);
      --red: #ef4444;
      --red-dim: rgba(239, 68, 68, 0.15);
      --amber: #f59e0b;
      --blue: #3b82f6;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
    body {{ background: var(--bg); color: var(--text); padding: 2rem; line-height: 1.5; }}
    .container {{ max-width: 1040px; margin: 0 auto; }}
    header {{ margin-bottom: 2rem; border-bottom: 1px solid var(--border); padding-bottom: 1rem; }}
    h1 {{ font-size: 1.75rem; font-weight: 600; display: flex; align-items: center; gap: 0.75rem; }}
    .tag {{ background: var(--accent-dim); color: var(--accent); font-size: 0.8rem; padding: 0.25rem 0.5rem; border-radius: 4px; border: 1px solid var(--accent); }}
    p.lead {{ color: var(--text-muted); margin-top: 0.5rem; font-size: 1rem; }}
    
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 1.5rem; margin-bottom: 2rem; }}
    .card {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 8px; padding: 1.25rem; }}
    .card h2 {{ font-size: 1.1rem; margin-bottom: 0.75rem; color: #fff; }}
    
    table {{ width: 100%; border-collapse: collapse; margin-top: 0.5rem; font-size: 0.9rem; }}
    th, td {{ padding: 0.6rem 0.75rem; text-align: left; border-bottom: 1px solid var(--border); }}
    th {{ color: var(--text-muted); font-weight: 500; font-size: 0.8rem; text-transform: uppercase; }}
    .highlight {{ color: var(--accent); font-weight: 600; }}
    .danger {{ color: var(--red); font-weight: 600; }}
    
    .metric-badge {{ display: inline-block; padding: 0.2rem 0.4rem; border-radius: 4px; font-weight: 600; font-family: ui-monospace, monospace; font-size: 0.85rem; }}
    .badge-green {{ background: var(--accent-dim); color: var(--accent); }}
    .badge-red {{ background: var(--red-dim); color: var(--red); }}
    
    .interactive-panel {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 8px; padding: 1.5rem; margin-top: 1.5rem; }}
    .control-row {{ display: flex; gap: 2rem; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; }}
    .control-group {{ display: flex; flex-direction: column; gap: 0.35rem; }}
    label {{ font-size: 0.85rem; color: var(--text-muted); }}
    input[type=range] {{ width: 220px; }}
    
    .visual-comparison {{ display: flex; gap: 1rem; margin-top: 1.5rem; }}
    .seg-col {{ flex: 1; background: #191c2b; border: 1px solid var(--border); border-radius: 6px; padding: 1rem; }}
    .seg-col h3 {{ font-size: 0.95rem; margin-bottom: 0.5rem; display: flex; justify-content: space-between; }}
    .bar-container {{ position: relative; height: 160px; border-left: 2px dashed #4b5563; margin: 1rem 0; display: flex; align-items: center; }}
    .zero-line {{ position: absolute; left: 50%; top: 0; bottom: 0; width: 1px; background: #6b7280; }}
    .tolerance-bar {{ position: absolute; height: 32px; border-radius: 4px; transition: all 0.3s ease; display: flex; align-items: center; padding: 0 0.5rem; font-size: 0.75rem; font-family: monospace; }}
    .bar-legacy {{ top: 25px; background: rgba(239, 68, 68, 0.4); border: 1px solid var(--red); color: #fca5a5; }}
    .bar-scaled {{ top: 85px; background: rgba(16, 185, 129, 0.4); border: 1px solid var(--accent); color: #6ee7b7; }}
  </style>
</head>
<body>
<div class="container">
  <header>
    <h1>Seasonal Segment Floors Calibration <span class="tag">Ticket #172 · ADR 0064</span></h1>
    <p class="lead">Uniform statistical stringency (&approx; -0.25 &times; SE) across asymmetric seasonal windows (n=4, 15, 19).</p>
  </header>

  <div class="grid">
    <div class="card" style="grid-column: 1 / -1;">
      <h2>Statistical Asymmetry & Calibration Table (&sigma; = 2.20 pts/GW)</h2>
      <table>
        <thead>
          <tr>
            <th>Segment</th>
            <th>Window</th>
            <th>n (GWs)</th>
            <th>SE (&sigma;/&radic;n)</th>
            <th>Legacy Floor (ADR 0062)</th>
            <th>Legacy z-score</th>
            <th>Calibrated Floor (ADR 0064)</th>
            <th>Calibrated z-score</th>
            <th>Max Cumulative Loss</th>
          </tr>
        </thead>
        <tbody id="stat-table-body">
        </tbody>
      </table>
    </div>
  </div>

  <div class="interactive-panel">
    <h2>Interactive Tolerance & Stringency Simulator</h2>
    <div class="control-row">
      <div class="control-group">
        <label for="sigma-slider">Weekly Regret Std Dev (&sigma;): <span id="sigma-val">2.20</span> pts/GW</label>
        <input type="range" id="sigma-slider" min="1.0" max="3.5" step="0.05" value="2.20">
      </div>
      <div class="control-group">
        <label for="target-z">Target Stringency Level: <span id="target-z-val">-0.25</span> SE</label>
        <input type="range" id="target-z-slider" min="-0.50" max="-0.10" step="0.01" value="-0.25">
      </div>
    </div>

    <div class="visual-comparison" id="visual-segments">
    </div>
  </div>
</div>

<script>
const statsData = {data_json};

function renderTable() {{
  const tbody = document.getElementById("stat-table-body");
  tbody.innerHTML = "";
  statsData.forEach(s => {{
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><strong>${{s.name}}</strong></td>
      <td>${{s.name === 'cold_start' ? 'GW1–4' : (s.name === 'early_mid' ? 'GW5–19' : 'GW20–38')}}</td>
      <td>${{s.n_gws}}</td>
      <td>${{s.std_err.toFixed(2)}} pts</td>
      <td class="danger">-${{s.legacy_tol.toFixed(2)}}</td>
      <td class="danger">${{s.legacy_z.toFixed(3)}} &sigma;</td>
      <td class="highlight">-${{s.scaled_tol.toFixed(2)}}</td>
      <td class="highlight">${{s.scaled_z.toFixed(3)}} &sigma;</td>
      <td>-${{s.scaled_max_loss.toFixed(2)}} pts</td>
    `;
    tbody.appendChild(tr);
  }});
}}

function renderVisuals() {{
  const container = document.getElementById("visual-segments");
  container.innerHTML = "";
  const sigma = parseFloat(document.getElementById("sigma-slider").value);
  const targetZ = parseFloat(document.getElementById("target-z-slider").value);
  
  document.getElementById("sigma-val").innerText = sigma.toFixed(2);
  document.getElementById("target-z-val").innerText = targetZ.toFixed(2);

  statsData.forEach(s => {{
    const se = sigma / Math.sqrt(s.n_gws);
    const dynamicTol = Math.abs(targetZ * se);
    
    const col = document.createElement("div");
    col.className = "seg-col";
    col.innerHTML = `
      <h3>${{s.name}} <span class="metric-badge badge-green">n=${{s.n_gws}}</span></h3>
      <p style="font-size:0.8rem; color:var(--text-muted);">SE: ${{se.toFixed(2)}} pts/GW</p>
      <div style="margin-top:0.5rem; font-size:0.85rem;">
        <div>Legacy Floor: <span class="danger">-${{s.legacy_tol.toFixed(2)}}</span> (${{( -s.legacy_tol / se ).toFixed(2)}} SE)</div>
        <div style="margin-top:0.25rem;">Calibrated Floor: <span class="highlight">-${{s.scaled_tol.toFixed(2)}}</span> (${{( -s.scaled_tol / se ).toFixed(2)}} SE)</div>
      </div>
    `;
    container.appendChild(col);
  }});
}}

document.getElementById("sigma-slider").addEventListener("input", renderVisuals);
document.getElementById("target-z-slider").addEventListener("input", renderVisuals);

renderTable();
renderVisuals();
</script>
</body>
</html>
"""
    output_path.write_text(html_content, encoding="utf-8")


def main() -> None:
    output_dir = Path(__file__).resolve().parent
    stats = simulate_segment_properties()
    html_path = output_dir / "prototype_sqrt_ns_segment_guardrails.html"
    generate_interactive_html(stats, html_path)
    print(f"Generated prototype visual: {html_path}")
    for s in stats:
        print(
            f"[{s.name:<11}] n={s.n_gws:>2} | SE={s.std_err:.2f} | "
            f"Legacy: tol=-{s.legacy_tol:.2f} (z={s.legacy_z:.3f}, rej_null={s.null_rejection_rate_legacy:.1%}) | "
            f"Scaled: tol=-{s.scaled_tol:.2f} (z={s.scaled_z:.3f}, rej_null={s.null_rejection_rate_scaled:.1%})"
        )


if __name__ == "__main__":
    main()

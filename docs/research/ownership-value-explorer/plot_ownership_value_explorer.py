"""Interactive ownership vs xP/90 explorer (full season + GW1–6 toggle).

Standalone research tool (not part of GW1–6 pipeline Stage sequence).
Axes: ownership % vs xP per 90; size = avg expected minutes.
Filters: position, club, price, avg-xMins floor (default 45).
Overlays: optional preseason S1/S5 picks + user_picks.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
SEASON_CSV = ROOT / "data/research/ownership-value-explorer/season_projections.csv"
SIM_CSV = ROOT / "data/research/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6_wc4_simulation.csv"
USER_PICKS = ROOT / "data/processed/user_picks.parquet"
OUT_DIR = ROOT / "data/research/ownership-value-explorer"
OUT_METRICS = OUT_DIR / "ownership_value_metrics.csv"
OUT_HTML = OUT_DIR / "ownership_value_explorer.html"

DEFAULT_XMINS_FLOOR = 45.0
S1_PREFIX = "S1:"
S5_PREFIX = "S5:"


def build_explorer_frame(
    season: pd.DataFrame,
    simulation: pd.DataFrame | None = None,
    user_picks: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Attach overlays to season projection rows (already includes ownership)."""
    required = {
        "player_id",
        "ownership_pct",
        "xp_per_90_season",
        "avg_xmins_season",
        "total_season_xp",
        "xp_per_90_gw1_6",
        "avg_xmins_gw1_6",
        "total_gw1_6_xp",
        "cost",
        "position",
        "club_short",
        "web_name",
    }
    missing = required - set(season.columns)
    if missing:
        raise ValueError(f"season projections missing columns: {sorted(missing)}")

    frame = season.copy()
    s1_ids: set[int] = set()
    s5_ids: set[int] = set()
    if simulation is not None and not simulation.empty:
        s1_ids = set(
            simulation.loc[simulation["scenario"].astype(str).str.startswith(S1_PREFIX), "player_id"].astype(int)
        )
        s5_ids = set(
            simulation.loc[simulation["scenario"].astype(str).str.startswith(S5_PREFIX), "player_id"].astype(int)
        )
    user_ids: set[int] = set()
    if user_picks is not None and not user_picks.empty and "player_id" in user_picks.columns:
        user_ids = set(user_picks["player_id"].astype(int))

    frame["in_s1"] = frame["player_id"].astype(int).isin(s1_ids)
    frame["in_s5"] = frame["player_id"].astype(int).isin(s5_ids)
    frame["in_user"] = frame["player_id"].astype(int).isin(user_ids)
    frame["xp_per_m_season"] = frame["total_season_xp"] / frame["cost"].replace(0, pd.NA)

    cols = [
        "player_id",
        "web_name",
        "club_short",
        "position",
        "expected_role",
        "draft_availability",
        "cost",
        "ownership_pct",
        "total_season_xp",
        "total_season_xmins",
        "avg_xmins_season",
        "xp_per_90_season",
        "total_gw1_6_xp",
        "total_gw1_6_xmins",
        "avg_xmins_gw1_6",
        "xp_per_90_gw1_6",
        "xp_per_m_season",
        "n_gameweeks",
        "in_s1",
        "in_s5",
        "in_user",
    ]
    keep = [c for c in cols if c in frame.columns]
    return (
        frame[keep]
        .dropna(subset=["ownership_pct", "xp_per_90_season"])
        .sort_values("xp_per_90_season", ascending=False)
        .reset_index(drop=True)
    )


def _records_for_html(frame: pd.DataFrame) -> list[dict]:
    out: list[dict] = []
    for row in frame.itertuples(index=False):
        out.append(
            {
                "player_id": int(row.player_id),
                "web_name": str(row.web_name),
                "club_short": str(row.club_short),
                "position": str(row.position),
                "expected_role": str(getattr(row, "expected_role", "")),
                "cost": float(row.cost),
                "ownership_pct": float(row.ownership_pct),
                "avg_xmins_season": float(row.avg_xmins_season),
                "xp_per_90_season": float(row.xp_per_90_season),
                "total_season_xp": float(row.total_season_xp),
                "avg_xmins_gw1_6": float(row.avg_xmins_gw1_6),
                "xp_per_90_gw1_6": float(row.xp_per_90_gw1_6),
                "total_gw1_6_xp": float(row.total_gw1_6_xp),
                "in_s1": bool(row.in_s1),
                "in_s5": bool(row.in_s5),
                "in_user": bool(row.in_user),
            }
        )
    return out


def write_explorer_html(frame: pd.DataFrame, path: Path, default_xmins_floor: float = DEFAULT_XMINS_FLOOR) -> None:
    """Write standalone Plotly HTML with horizon toggle + filters."""
    records = _records_for_html(frame)
    clubs = sorted({r["club_short"] for r in records})
    positions = ["GKP", "DEF", "MID", "FWD"]
    price_min = min((r["cost"] for r in records), default=4.0)
    price_max = max((r["cost"] for r in records), default=15.0)
    payload = json.dumps(
        {
            "records": records,
            "clubs": clubs,
            "positions": positions,
            "price_min": price_min,
            "price_max": price_max,
            "default_xmins_floor": default_xmins_floor,
            "default_horizon": "season",
        },
        separators=(",", ":"),
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Ownership Value Explorer (GW1–38)</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>
    :root {{ font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif; color: #1a1a1a; }}
    body {{ margin: 0; background: #f6f7f9; }}
    header {{ padding: 1rem 1.25rem 0.5rem; }}
    h1 {{ margin: 0 0 0.25rem; font-size: 1.25rem; }}
    .sub {{ color: #555; font-size: 0.9rem; margin-bottom: 0.75rem; }}
    .panel {{ display: flex; flex-wrap: wrap; gap: 0.75rem 1.25rem; padding: 0.75rem 1.25rem; background: #fff; border-bottom: 1px solid #ddd; }}
    .group {{ display: flex; flex-direction: column; gap: 0.35rem; min-width: 10rem; }}
    .group label.title {{ font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; color: #444; }}
    .checks {{ display: flex; flex-wrap: wrap; gap: 0.4rem 0.75rem; }}
    .checks label, .toggles label {{ font-size: 0.85rem; }}
    select[multiple] {{ min-width: 12rem; min-height: 6.5rem; }}
    .range-row {{ display: flex; align-items: center; gap: 0.4rem; font-size: 0.85rem; }}
    input[type=number] {{ width: 4.5rem; }}
    input[type=range] {{ width: 9rem; }}
    #meta {{ padding: 0.5rem 1.25rem; font-size: 0.85rem; color: #444; }}
    #chart {{ width: 100%; height: calc(100vh - 240px); min-height: 480px; background: #fff; }}
    .note {{ font-size: 0.8rem; color: #666; padding: 0 1.25rem 1rem; }}
  </style>
</head>
<body>
  <header>
    <h1>Ownership Value Explorer</h1>
    <div class="sub">xP per 90 vs Ownership % · marker size = avg expected minutes · default horizon GW1–38</div>
  </header>
  <div class="panel">
    <div class="group">
      <label class="title">Horizon</label>
      <div class="checks">
        <label><input type="radio" name="horizon" value="season" checked/> GW1–38 season</label>
        <label><input type="radio" name="horizon" value="gw1_6"/> GW1–6 window</label>
      </div>
    </div>
    <div class="group">
      <label class="title">Position</label>
      <div class="checks" id="pos-checks"></div>
    </div>
    <div class="group">
      <label class="title">Club</label>
      <select id="club-select" multiple></select>
      <div class="checks"><label><input type="checkbox" id="club-all" checked/> All clubs</label></div>
    </div>
    <div class="group">
      <label class="title">Price (£m)</label>
      <div class="range-row">
        <input type="number" id="price-min" step="0.5" />
        <span>–</span>
        <input type="number" id="price-max" step="0.5" />
      </div>
    </div>
    <div class="group">
      <label class="title">Avg xMins floor</label>
      <div class="range-row">
        <input type="range" id="xmins-floor" min="0" max="90" step="1" />
        <span id="xmins-floor-val"></span>
      </div>
    </div>
    <div class="group">
      <label class="title">Overlays</label>
      <div class="toggles">
        <label><input type="checkbox" id="hl-s1" checked/> Preseason S1</label>
        <label><input type="checkbox" id="hl-s5" checked/> Preseason S5</label>
        <label><input type="checkbox" id="hl-user" checked/> User squad</label>
        <label><input type="checkbox" id="only-overlay"/> Only overlay players</label>
      </div>
    </div>
  </div>
  <div id="meta"></div>
  <div id="chart"></div>
  <p class="note">Ownership is FPL <code>selected_by_percent</code> (not EO). Season xP uses Stage 2 rates × GW1–38 fixtures with availability priors. xP/90 = horizon xP ÷ (Σ xMins / 90). Default floor hides low-minute spikes.</p>
  <script>
    const DATA = {payload};
    const POS_COLORS = {{GKP:'#4c78a8', DEF:'#f58518', MID:'#54a24b', FWD:'#e45756'}};

    function horizon() {{
      const el = document.querySelector('input[name="horizon"]:checked');
      return el ? el.value : 'season';
    }}
    function metrics(r) {{
      if (horizon() === 'gw1_6') {{
        return {{xp90: r.xp_per_90_gw1_6, avgMins: r.avg_xmins_gw1_6, totalXp: r.total_gw1_6_xp, label: 'GW1–6'}};
      }}
      return {{xp90: r.xp_per_90_season, avgMins: r.avg_xmins_season, totalXp: r.total_season_xp, label: 'GW1–38'}};
    }}

    function initControls() {{
      const pos = document.getElementById('pos-checks');
      DATA.positions.forEach(p => {{
        const lab = document.createElement('label');
        lab.innerHTML = `<input type="checkbox" class="pos" value="${{p}}" checked/> ${{p}}`;
        pos.appendChild(lab);
      }});
      const club = document.getElementById('club-select');
      DATA.clubs.forEach(c => {{
        const opt = document.createElement('option');
        opt.value = c; opt.textContent = c; club.appendChild(opt);
      }});
      document.getElementById('price-min').value = DATA.price_min;
      document.getElementById('price-max').value = DATA.price_max;
      const floor = document.getElementById('xmins-floor');
      floor.value = DATA.default_xmins_floor;
      document.getElementById('xmins-floor-val').textContent = DATA.default_xmins_floor;
      [
        ...document.querySelectorAll('.pos'),
        ...document.querySelectorAll('input[name="horizon"]'),
        document.getElementById('club-select'),
        document.getElementById('club-all'),
        document.getElementById('price-min'),
        document.getElementById('price-max'),
        document.getElementById('xmins-floor'),
        document.getElementById('hl-s1'),
        document.getElementById('hl-s5'),
        document.getElementById('hl-user'),
        document.getElementById('only-overlay'),
      ].forEach(el => el.addEventListener('input', render));
      document.getElementById('club-all').addEventListener('change', (e) => {{
        if (e.target.checked) Array.from(club.options).forEach(o => o.selected = false);
        render();
      }});
      club.addEventListener('change', () => {{
        document.getElementById('club-all').checked = Array.from(club.selectedOptions).length === 0;
        render();
      }});
      floor.addEventListener('input', () => {{
        document.getElementById('xmins-floor-val').textContent = floor.value;
      }});
    }}

    function selectedPositions() {{
      return Array.from(document.querySelectorAll('.pos:checked')).map(x => x.value);
    }}
    function selectedClubs() {{
      if (document.getElementById('club-all').checked) return null;
      const vals = Array.from(document.getElementById('club-select').selectedOptions).map(o => o.value);
      return vals.length ? vals : null;
    }}
    function filtered() {{
      const pos = new Set(selectedPositions());
      const clubs = selectedClubs();
      const pmin = parseFloat(document.getElementById('price-min').value);
      const pmax = parseFloat(document.getElementById('price-max').value);
      const floor = parseFloat(document.getElementById('xmins-floor').value);
      const only = document.getElementById('only-overlay').checked;
      const hlS1 = document.getElementById('hl-s1').checked;
      const hlS5 = document.getElementById('hl-s5').checked;
      const hlUser = document.getElementById('hl-user').checked;
      return DATA.records.filter(r => {{
        if (!pos.has(r.position)) return false;
        if (clubs && !clubs.includes(r.club_short)) return false;
        if (r.cost < pmin || r.cost > pmax) return false;
        const m = metrics(r);
        if (m.avgMins < floor) return false;
        if (only) {{
          const hit = (hlS1 && r.in_s1) || (hlS5 && r.in_s5) || (hlUser && r.in_user);
          if (!hit) return false;
        }}
        return Number.isFinite(m.xp90);
      }});
    }}

    function markerStyle(r) {{
      const hlS1 = document.getElementById('hl-s1').checked;
      const hlS5 = document.getElementById('hl-s5').checked;
      const hlUser = document.getElementById('hl-user').checked;
      const m = metrics(r);
      let symbol = 'circle';
      let line = {{width: 0.5, color: '#333'}};
      if (hlUser && r.in_user) {{ symbol = 'diamond'; line = {{width: 2, color: '#111'}}; }}
      else if (hlS5 && r.in_s5) {{ symbol = 'square'; line = {{width: 2, color: '#6f42c1'}}; }}
      else if (hlS1 && r.in_s1) {{ symbol = 'triangle-up'; line = {{width: 2, color: '#0b7285'}}; }}
      const size = Math.max(7, Math.min(28, 6 + m.avgMins / 4.5));
      return {{symbol, size, line, color: POS_COLORS[r.position] || '#888'}};
    }}

    function render() {{
      const rows = filtered();
      const h = metrics(rows[0] || {{avg_xmins_season:0, xp_per_90_season:0, total_season_xp:0, avg_xmins_gw1_6:0, xp_per_90_gw1_6:0, total_gw1_6_xp:0}});
      document.getElementById('meta').textContent =
        `Horizon ${{h.label}} · showing ${{rows.length}} / ${{DATA.records.length}} · diamond=user · square=S5 · triangle=S1`;
      const traces = DATA.positions.map(pos => {{
        const subset = rows.filter(r => r.position === pos);
        const styles = subset.map(markerStyle);
        const ms = subset.map(metrics);
        return {{
          type: 'scatter',
          mode: 'markers+text',
          name: pos,
          x: subset.map(r => r.ownership_pct),
          y: ms.map(m => m.xp90),
          text: subset.map((r, i) => ms[i].avgMins >= 60 ? r.web_name : ''),
          textposition: 'top center',
          textfont: {{size: 10}},
          customdata: subset.map((r, i) => [r.web_name, r.club_short, r.cost, r.expected_role, ms[i].avgMins, ms[i].totalXp, r.in_s1, r.in_s5, r.in_user, ms[i].label]),
          marker: {{
            size: styles.map(s => s.size),
            color: styles.map(s => s.color),
            symbol: styles.map(s => s.symbol),
            line: {{width: styles.map(s => s.line.width), color: styles.map(s => s.line.color)}},
            opacity: 0.85,
          }},
          hovertemplate:
            '<b>%{{customdata[0]}}</b> (%{{customdata[1]}} %{{fullData.name}})<br>' +
            'Own %: %{{x:.1f}}<br>xP/90 (%{{customdata[9]}}): %{{y:.2f}}<br>' +
            'Cost: £%{{customdata[2]:.1f}}m · Role: %{{customdata[3]}}<br>' +
            'Avg xMins: %{{customdata[4]:.1f}} · Horizon xP: %{{customdata[5]:.2f}}<br>' +
            'S1:%{{customdata[6]}} S5:%{{customdata[7]}} User:%{{customdata[8]}}' +
            '<extra></extra>',
        }};
      }});
      const layout = {{
        margin: {{t: 30, r: 20, b: 50, l: 55}},
        xaxis: {{title: 'Ownership % (selected_by_percent)', zeroline: false, gridcolor: '#eee'}},
        yaxis: {{title: h.label + ' xP per 90', zeroline: false, gridcolor: '#eee'}},
        legend: {{orientation: 'h', y: 1.08}},
        plot_bgcolor: '#fff',
        paper_bgcolor: '#fff',
        hovermode: 'closest',
      }};
      Plotly.react('chart', traces, layout, {{responsive: true, displayModeBar: true}});
    }}

    initControls();
    render();
  </script>
</body>
</html>
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


def ensure_season_projections(season_path: Path = SEASON_CSV, rebuild: bool = False) -> Path:
    """Build season projections CSV if missing or rebuild requested."""
    if season_path.exists() and not rebuild:
        return season_path
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "project_season_points",
        Path(__file__).resolve().parent / "project_season_points.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    mod.project_season_points(out_csv=season_path)
    return season_path


def run_ownership_value_explorer(
    season_path: Path = SEASON_CSV,
    simulation_path: Path = SIM_CSV,
    user_picks_path: Path = USER_PICKS,
    out_metrics: Path = OUT_METRICS,
    out_html: Path = OUT_HTML,
    default_xmins_floor: float = DEFAULT_XMINS_FLOOR,
    rebuild_season: bool = False,
) -> pd.DataFrame:
    """Build metrics CSV + interactive HTML from season projections."""
    ensure_season_projections(season_path, rebuild=rebuild_season)
    season = pd.read_csv(season_path)
    simulation = pd.read_csv(simulation_path) if simulation_path.exists() else None
    user_picks = pd.read_parquet(user_picks_path) if user_picks_path.exists() else None
    frame = build_explorer_frame(season, simulation=simulation, user_picks=user_picks)
    out_metrics.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(out_metrics, index=False)
    write_explorer_html(frame, out_html, default_xmins_floor=default_xmins_floor)
    n_floor = int((frame["avg_xmins_season"] >= default_xmins_floor).sum())
    print(f"Ownership explorer: {len(frame)} players → {out_metrics}")
    print(f"Interactive HTML ({n_floor} at season xMins>={default_xmins_floor}): {out_html}")
    return frame


def main() -> None:
    run_ownership_value_explorer(rebuild_season=True)


if __name__ == "__main__":
    main()

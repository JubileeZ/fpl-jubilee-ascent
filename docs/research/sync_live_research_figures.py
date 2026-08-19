"""Rewrite research-note figure caches from named companion CSVs.

Identity is artifact path + column, not a numeric snapshot. Call after topic runners.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
POS_ORDER = {"GKP": 0, "DEF": 1, "MID": 2, "FWD": 3}
POS_LABEL = {"GKP": "Goalkeepers", "DEF": "Defenders", "MID": "Midfielders", "FWD": "Forwards"}

SUMMARY = ROOT / "data/research/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6_wc4_summary.csv"
SIM = ROOT / "data/research/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6_wc4_simulation.csv"
SELECT11 = ROOT / "data/research/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6_select_11.csv"
STAGE3_MD = ROOT / "docs/research/gw1-6-preseason-pipeline/03-gw1-6-chip-wc4-squads/gw1-6-chip-wc4-squads.md"
PIPELINE_MD = ROOT / "docs/research/gw1-6-preseason-pipeline/README.md"
INDEX_MD = ROOT / "docs/research/INDEX.md"
CURRENT_STATE = ROOT / "docs/agents/current-state.md"
FH_SUMMARY = ROOT / "data/research/gw1-19-first-half-chip-path/first_half_summary.csv"
FH_SELECT = ROOT / "data/research/gw1-19-first-half-chip-path/first_half_select_11.csv"
FH_SQUADS = ROOT / "data/research/gw1-19-first-half-chip-path/first_half_squads.csv"
FH_MD = ROOT / "docs/research/gw1-19-first-half-chip-path/gw1-19-first-half-chip-path.md"
FH_README = ROOT / "docs/research/gw1-19-first-half-chip-path/README.md"
OWN_MD = ROOT / "docs/research/ownership-value-explorer/ownership-value-explorer.md"
DCS_GKP = ROOT / "data/research/defensive-fixture-rotation/gkp_strategy_comparison.csv"
DCS_PART = ROOT / "data/research/defensive-fixture-rotation/def_club_partitions_matrix.csv"
DCS_BACK = ROOT / "data/research/defensive-fixture-rotation/backline_gw1_19_lineups.csv"
DCS_MD = ROOT / "docs/research/defensive-fixture-rotation/defensive-fixture-rotation.md"


def _now() -> str:
    dt = datetime.now(ZoneInfo("Asia/Bangkok"))
    return dt.strftime("%Y-%m-%dT%H:%M:%S") + "+07:00"


def _fmt(val: float) -> str:
    return f"{float(val):.2f}"


def _names(df: pd.DataFrame, pos: str) -> str:
    hit = df[df["position"] == pos].sort_values("web_name")
    return ", ".join(
        f"{r.web_name} ({r.club_short}, £{float(r.cost):.1f}m)" for r in hit.itertuples()
    )


def _keepers(sim: pd.DataFrame, phase_pat: str) -> str:
    gkp = sim[sim["phase"].str.contains(phase_pat) & (sim["position"] == "GKP")]
    return " + ".join(gkp.sort_values("cost", ascending=False)["web_name"].tolist())


def _squad_md(sim: pd.DataFrame, phase_pat: str, title: str, spend: float, itb: float) -> str:
    squad = sim[sim["phase"].str.contains(phase_pat)].copy()
    lines = [f"#### {title} (£{spend:.1f}m Spend, £{itb:.1f}m ITB)"]
    for pos in ("GKP", "DEF", "MID", "FWD"):
        lines.append(f"- **{POS_LABEL[pos]}**: {_names(squad, pos)}")
    return "\n".join(lines)


def _select11_gw(sel: pd.DataFrame, gw: int, chip_label: str) -> str:
    g = sel[sel["gw"] == gw].copy()
    g["_pos"] = g["position"].map(POS_ORDER)
    g = g.sort_values(["_pos", "xp"], ascending=[True, False])
    cap = str(g["captain"].iloc[0])
    form = str(g["formation"].iloc[0])
    week = _fmt(g["week_xp"].iloc[0])

    def _xi(pos: str) -> str:
        names: list[str] = []
        for r in g[g["position"] == pos].itertuples():
            names.append(f"**{r.web_name} (C)**" if str(r.is_captain).lower() in {"true", "1"} else str(r.web_name))
        return ", ".join(names) if names else "—"

    if gw == 1:
        lines = [
            f"#### GW1 Bench Boost — all 15 score — {form} — **{week}** — C {cap}",
            "",
            "| Pos | XI (xP order) |",
            "|---|---|",
        ]
        for pos in ("GKP", "DEF", "MID", "FWD"):
            lines.append(f"| {pos} | {_xi(pos)} |")
        lines.extend(["", "No bench. Formation label `BB-15`."])
        return "\n".join(lines)
    bench = str(g["bench"].iloc[0]) if "bench" in g.columns else "—"
    lines = [
        f"#### GW{gw}{chip_label} — {form} — **{week}** — C {cap}",
        "",
        "| Pos | XI | Bench |",
        "|---|---|---|",
    ]
    first = True
    for pos in ("GKP", "DEF", "MID", "FWD"):
        xi = _xi(pos)
        if pos != "GKP" and xi == "—":
            continue
        lines.append(f"| {pos} | {xi} | {bench if first else '—'} |")
        first = False
    return "\n".join(lines)


def render_stage3_findings(summary: pd.Series, sim: pd.DataFrame, sel: pd.DataFrame) -> str:
    s = summary
    haaland_pre = bool(
        ((sim["phase"].str.contains("Pre-WC")) & (sim["web_name"] == "Haaland")).any()
    )
    haaland_line = (
        "Haaland is in the pre-WC 15."
        if haaland_pre
        else "Haaland is **not** in the pre-WC 15."
    )
    dcs_pair = "live DCS pair"
    if DCS_GKP.exists():
        gkp = pd.read_csv(DCS_GKP)
        top = gkp[(gkp["horizon"] == "gw1_19")].sort_values("dcs", ascending=False)
        if len(top):
            dcs_pair = str(top.iloc[0]["pairing"])
    pre_gkp = _keepers(sim, "Pre-WC")
    post_gkp = _keepers(sim, "Post-WC")
    traj = f"""### 1. Canonical Scenario Trajectory (GW1 BB + WC4)

| Gameweek | Phase / Chip | Captain | Total GW xP | Transfers | Banked FTs |
| :---: | :--- | :--- | :---: | :---: | :---: |
| **GW1** | **Pre-WC (Bench Boost Active)** | {s['gw1_captain']} | **{_fmt(s['gw1_xp'])}** | 0 (Initial) | 1 |
| **GW2** | **Pre-WC (Locked Squad)** | {s['gw2_captain']} | **{_fmt(s['gw2_xp'])}** | 0 (Roll) | 2 |
| **GW3** | **Pre-WC (Locked Squad)** | {s['gw3_captain']} | **{_fmt(s['gw3_xp'])}** | 0 (Roll) | 3 |
| **GW1–3 Subtotal** | **Pre-Wildcard Sprint** | — | **{_fmt(s['gw1_3_xp'])}** | — | — |
| **GW4** | **Post-WC (Wildcard Active)** | {s['gw4_captain']} | **{_fmt(s['gw4_xp'])}** | WC Active | 3 (Preserved) |
| **GW5** | **Post-WC (Hold Squad)** | {s['gw5_captain']} | **{_fmt(s['gw5_xp'])}** | 0 (Roll) | 4 |
| **GW6** | **Post-WC (Enter Post-IB)** | {s['gw6_captain']} | **{_fmt(s['gw6_xp'])}** | 0 (Roll) | **4 (Max)** |
| **GW4–6 Subtotal** | **Post-Wildcard Rebuild** | — | **{_fmt(s['gw4_6_xp'])}** | — | — |
| **Total Horizon** | **GW1–6 Preseason Strategy** | — | **{_fmt(s['total_6gw_xp'])}** | — | **4 Banked FTs** |

Saves and defcon scale with `defence_multiplier` (ADR 0005). Totals are Prior-Season Dual-Vector Seed xP (`gw1-6_wc4_summary.csv` `total_6gw_xp`). Production `_fixture_maps` still FDR fallback.

### 2. Optimal Squad Rosters

{_squad_md(sim, "Pre-WC", "Phase 1: GW1 Bench Boost Squad", float(s["pre_spend"]), round(100.0 - float(s["pre_spend"]), 1))}

{haaland_line}

{_squad_md(sim, "Post-WC", "Phase 2: GW4 Wildcard Rebuild Squad", float(s["post_spend"]), float(s["itb_gw6"]))}

### 3. Select 11 plan (GW1–6)

Legal XI from the 15 above. Week xP matches `gw1-6_wc4_summary.csv` (parts sum to {_fmt(s["total_6gw_xp"])}).

{_select11_gw(sel, 1, "")}

{_select11_gw(sel, 2, "")}

{_select11_gw(sel, 3, "")}

{_select11_gw(sel, 4, " Wildcard")}

{_select11_gw(sel, 5, "")}

{_select11_gw(sel, 6, "")}
"""
    decision = f"""**Verdict**: The **GW1 Bench Boost + GW4 Wildcard** strategy achieves **{_fmt(s['total_6gw_xp'])} xP** across GW1–6 (`gw1-6_wc4_summary.csv` `total_6gw_xp`) while preserving **4 Banked Free Transfers** into GW6. Pre-WC keepers **{pre_gkp}** are the MILP 15-man pick, not the DCS GW1–19 pair (**{dcs_pair}**). Post-WC keepers **{post_gkp}**.
"""
    return traj.rstrip() + "\n\n## Decision\n\n" + decision


def _patch_updated(text: str) -> str:
    return re.sub(r"\*\*Updated\*\*: [^\n]+", f"**Updated**: {_now()}", text, count=1)


def sync_stage3_note() -> None:
    if not (SUMMARY.exists() and SIM.exists() and SELECT11.exists() and STAGE3_MD.exists()):
        return
    s = pd.read_csv(SUMMARY).iloc[0]
    sim = pd.read_csv(SIM)
    sel = pd.read_csv(SELECT11)
    text = STAGE3_MD.read_text(encoding="utf-8")
    text = _patch_updated(text)
    text = re.sub(
        r"\*\*Data stamp\*\*: [^\n]+",
        "**Data stamp**: Stage 2 rates 2026-08-18; Prior-Season Dual-Vector Seed; FPL API clubs/fixtures 2026-08-19; Champion saves/defcon × defence_multiplier",
        text,
        count=1,
    )
    body = render_stage3_findings(s, sim, sel)
    text = re.sub(
        r"## Findings\n.*?\n## Risks and unknowns\n",
        "## Findings\n\n" + body.rstrip() + "\n\n## Risks and unknowns\n",
        text,
        count=1,
        flags=re.S,
    )
    total = _fmt(s["total_6gw_xp"])
    gw1 = _fmt(s["gw1_xp"])
    text = re.sub(
        r"(\| \*\*Scenario Expected Points\*\* \| `Total xP` \|[^\n]+\| )\*\*[^\|]+",
        rf"\1**{total}** (`gw1-6_wc4_summary.csv`) ",
        text,
        count=1,
    )
    text = re.sub(
        r"(\| \*\*Select-11 week xP\*\* \| XI \+ C \| .* \| Higher \$\\uparrow\$ \| )GW1 \*\*[^*]+\*\*",
        rf"\1GW1 **{gw1}**",
        text,
        count=1,
    )
    text = re.sub(
        r"(\| \*\*Bench Boost Active Score\*\* \| `BB Score` \| .* \| Higher \$\\uparrow\$ \| )\*\*[^*]+\*\*",
        rf"\1**{gw1}**",
        text,
        count=1,
    )
    text = text.replace("do not mix frozen S13 340.14 with 356.61.", "do not mix frozen S13 340.14 with live `total_6gw_xp`.")
    text = text.replace(" (`gw1-6_wc4_summary.csv`) (S1)", " (`gw1-6_wc4_summary.csv`)")
    STAGE3_MD.write_text(text, encoding="utf-8")


def sync_pipeline_readme() -> None:
    if not (SUMMARY.exists() and PIPELINE_MD.exists()):
        return
    s = pd.read_csv(SUMMARY).iloc[0]
    t = _fmt(s["total_6gw_xp"])
    gw1 = _fmt(s["gw1_xp"])
    g13 = _fmt(s["gw1_3_xp"])
    g46 = _fmt(s["gw4_6_xp"])
    cap1 = s["gw1_captain"]
    text = PIPELINE_MD.read_text(encoding="utf-8")
    text = _patch_updated(text)
    core = (
        f"**Strategy Core**: **GW1 BB + WC4 Canonical ({t} xP)**. 15 fit starters score in GW1 Bench Boost "
        f"({gw1} xP), locked transfers across GW1-3 ({g13} xP), Wildcard rebuild in GW4 ({g46} GW4-6 xP), "
        "and 4 banked Free Transfers preserved into GW6 post-international break."
    )
    text = re.sub(r"\*\*Strategy Core\*\*: .*", core, text, count=1)
    gw2 = _fmt(s["gw2_xp"])
    gw3 = _fmt(s["gw3_xp"])
    gw4 = _fmt(s["gw4_xp"])
    gw5 = _fmt(s["gw5_xp"])
    gw6 = _fmt(s["gw6_xp"])
    ascii_block = f"""```
Canonical Preseason Strategy Trajectory (GW1 BB + WC4):
┌───────────────────────────────────────────────────────────────────────────────┐
│ GW1: Bench Boost (BB1 {gw1} xP; 15 fit starters score, £{float(s['pre_spend']):.1f}m spend)         │
│ └─ Captures 15 fit starters with zero bench capital penalty pre-Wildcard      │
├───────────────────────────────────────────────────────────────────────────────┤
│ GW2–3: Locked Pre-WC Squad ({gw2} xP in GW2; {gw3} xP in GW3; 0 transfers)    │
│ └─ {g13} xP Pre-Wildcard sprint; {s['gw3_captain']} captain in GW3                         │
├───────────────────────────────────────────────────────────────────────────────┤
│ GW4: Wildcard Rebuild (£{float(s['post_spend']):.1f}m spend, {gw4} xP in GW4)                        │
│ └─ Seed xP rebuild; keepers from `gw1-6_wc4_simulation.csv`                   │
├───────────────────────────────────────────────────────────────────────────────┤
│ GW5: Free Transfer Rolled (gw5_transfers=0; {gw5} xP)                         │
│ └─ Banked FTs preserved through Wildcard under 2026/27 rules                  │
├───────────────────────────────────────────────────────────────────────────────┤
│ GW6: Enter Post-International Break with 4 Banked Free Transfers ({gw6} xP)  │
│ └─ {t} Total 6-GW xP (`gw1-6_wc4_summary.csv` `total_6gw_xp`)                 │
├───────────────────────────────────────────────────────────────────────────────┤
│ GW7–19: Hold Free Hit & Triple Captain as Emergency / Double GW Reserves      │
└───────────────────────────────────────────────────────────────────────────────┘
```"""
    text = re.sub(
        r"```\nCanonical Preseason Strategy Trajectory.*?\n```",
        ascii_block,
        text,
        count=1,
        flags=re.S,
    )
    text = re.sub(
        r"\| \*\*S1\*\* \| \*\*GW1 BB \+ WC4 Canonical \(Locked GW1-3, Roll GW5\)\*\* \| \*\*GW1\*\* \| \*\*GW4\*\* \| \*\*[^*]+\*\* \| \*\*[^*]+\*\* \| \*\*[^*]+\*\* \| £[0-9.]+m \| £[0-9.]+m \| £[0-9.]+m \| \*\*4\*\* \|",
        f"| **S1** | **GW1 BB + WC4 Canonical (Locked GW1-3, Roll GW5)** | **GW1** | **GW4** | **{g13}** | **{g46}** | **{t}** | £{float(s['pre_spend']):.1f}m | £{float(s['post_spend']):.1f}m | £{float(s['itb_gw6']):.1f}m | **4** |",
        text,
        count=1,
    )
    text = re.sub(
        r"1\. \*\*Canonical Strategy Implementation\*\*:.*",
        f"1. **Canonical Strategy Implementation**: **S1 (GW1 BB + WC4 Canonical, {t} xP)**. Deploys Bench Boost in GW1 (all 15 players score, {gw1} xP with {cap1} captain), locks transfers across GW1–3 sprint ({g13} xP), executes complete Wildcard rebuild in GW4 ({g46} xP across GW4–6), rolls the GW5 free transfer, and enters GW6 post-international break with **4 banked Free Transfers**.",
        text,
        count=1,
    )
    text = text.replace(
        "Then update Findings tables in Stage 3 / GKP / DEF / ownership notes from CSVs.",
        "Then `uv run python docs/research/sync_live_research_figures.py` (CSV cells → note caches).",
    )
    PIPELINE_MD.write_text(text, encoding="utf-8")


def sync_index() -> None:
    if not (SUMMARY.exists() and INDEX_MD.exists()):
        return
    t = _fmt(pd.read_csv(SUMMARY).iloc[0]["total_6gw_xp"])
    text = INDEX_MD.read_text(encoding="utf-8")
    text = _patch_updated(text)
    text = re.sub(
        r"Sibling of Canonical [0-9.]+. Does not replace it. Production `_fixture_maps` unchanged.",
        "Sibling calendar of Canonical (same Prior-Season Dual-Vector Seed). Does not replace GW1–6 BB1+WC4. Production `_fixture_maps` unchanged.",
        text,
        count=1,
    )
    text = re.sub(
        r"(\| \*\*Chip Strategy\*\* \| \*\*Scenario Expected Points\*\* \| `Total xP` \|[^\n]+\| )\*\*[^\|]+",
        rf"\1**{t} xP** (`gw1-6_wc4_summary.csv` `total_6gw_xp`) ",
        text,
        count=1,
    )
    INDEX_MD.write_text(text.replace("(S1: $356.61\\text{ xP}$)", "").replace("(S1: $356.61\\text{ xP}$) ", ""), encoding="utf-8")


def sync_current_state() -> None:
    if not (SUMMARY.exists() and CURRENT_STATE.exists()):
        return
    s = pd.read_csv(SUMMARY).iloc[0]
    t = _fmt(s["total_6gw_xp"])
    gw1 = _fmt(s["gw1_xp"])
    g13 = _fmt(s["gw1_3_xp"])
    g46 = _fmt(s["gw4_6_xp"])
    fh = ""
    if FH_SUMMARY.exists():
        wc4 = pd.read_csv(FH_SUMMARY)
        wc4 = wc4[wc4["path"] == "WC4"].iloc[0] if "path" in wc4.columns else wc4.iloc[-1]
        fh = (
            f"First-Half sibling WC4 **{_fmt(wc4['total_19gw_xp'])}** Dual-Vector xP "
            f"(BB{int(wc4['bb'])}, WC{int(wc4['wc'])}, TC{int(wc4['tc'])}, FH{int(wc4['fh'])}). "
            "FT-timed XI: `first_half_select_11.csv`."
        )
    dcs = ""
    if DCS_GKP.exists():
        g = pd.read_csv(DCS_GKP)
        top = g[g["horizon"] == "gw1_19"].sort_values("dcs", ascending=False).iloc[0]
        dcs = (
            f"GKP DCS GW1–19 #1: {top['pairing']} **{_fmt(top['tot_rot_xp'])} xP / DCS {_fmt(top['dcs'])}**."
        )
    fdr_min = ""
    if DCS_PART.exists():
        part = pd.read_csv(DCS_PART)
        five = part[(part["horizon"] == "gw1_19") & (part["num_unique_clubs"] == 5)]
        if len(five):
            row = five.sort_values("rot_avg_fdr").iloc[0]
            fdr_min = f"Club Seed-FDR-min #1: `{row['clubs']}` **{float(row['rot_avg_fdr']):.4f}**."
    next_work = (
        f"Live Canonical `gw1-6_wc4_summary.csv` `total_6gw_xp` = **{t}** (Prior-Season Dual-Vector Seed; BB1+WC4). "
        f"Select 11: `gw1-6_select_11.csv`. {fh} Live DCS on Seed under `data/research/defensive-fixture-rotation/`. "
        "Production `_fixture_maps` FDR fallback when API attack/defence = 0."
    )
    text = CURRENT_STATE.read_text(encoding="utf-8")
    text = re.sub(
        r"## Next work — start here\n\n.*?\n\nDesign decisions:",
        "## Next work — start here\n\n" + next_work + "\n\nDesign decisions:",
        text,
        count=1,
        flags=re.S,
    )
    bullets = f"""- Live chip path = Canonical Preseason Chip Path S1 **{t} xP** (`gw1-6_wc4_summary.csv` `total_6gw_xp`). GW1 **{gw1}** {s['gw1_captain']}; GW1–3 **{g13}**; GW4–6 **{g46}**. Select 11: `gw1-6_select_11.csv`.
- **Official Fixture Difficulty** = opponent Club Strength Vector overall at focal venue. Live API attack/defence = 0. Dual-Vector Strength (rolling npxG) not in production Python. Research Canonical / DCS use Prior-Season Dual-Vector Seed in-memory.
- {fh or 'First-Half Chip Path sibling: see `first_half_summary.csv`.'} Live DCS CSVs on Seed; no first-half `dcs/` copy.
- Ranking metric = **DCS** (ADR 0015). RQI historical.
- {dcs} {fdr_min}
- Stage 3 keepers = MILP 15-man pick, not the DCS pair.
"""
    text = re.sub(
        r"## Research truth \(19 Aug\)\n\n(?:- .*\n)+",
        "## Research truth (19 Aug)\n\n" + bullets + "\n",
        text,
        count=1,
    )
    CURRENT_STATE.write_text(text, encoding="utf-8")


def _fh_phase_names(squads: pd.DataFrame, wc: int, phase: str) -> str:
    hit = squads[(squads["wc"] == wc) & (squads["phase"] == phase)]
    if hit.empty:
        return ""
    parts = []
    for pos in ("GKP", "DEF", "MID", "FWD"):
        names = hit[hit["position"] == pos]["web_name"].tolist()
        if names:
            parts.append(", ".join(names))
    return "; ".join(parts)


def _fh_select_table(sel: pd.DataFrame) -> str:
    lines = [
        "| GW | Chip | Form | GKP | DEF | MID | FWD | Bench | xP |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for gw, g in sel.groupby("gw"):
        g = g.copy()
        g["_pos"] = g["position"].map(POS_ORDER)
        g = g.sort_values(["_pos", "xp"], ascending=[True, False])
        chip = "" if pd.isna(g["chip"].iloc[0]) else str(g["chip"].iloc[0])
        form = str(g["formation"].iloc[0])
        week = _fmt(g["week_xp"].iloc[0])
        raw_bench = g["bench"].iloc[0] if "bench" in g.columns else ""
        bench = "—" if pd.isna(raw_bench) or str(raw_bench) in {"", "nan"} else str(raw_bench)

        def _col(pos: str) -> str:
            names = []
            for r in g[g["position"] == pos].itertuples():
                names.append(f"**{r.web_name} (C)**" if str(r.is_captain).lower() in {"true", "1"} else r.web_name)
            return ", ".join(names)

        lines.append(
            f"| {int(gw)} | {chip} | {form} | {_col('GKP')} | {_col('DEF')} | {_col('MID')} | {_col('FWD')} | {bench} | {week} |"
        )
    return "\n".join(lines)


def sync_first_half_note() -> None:
    if not (FH_SUMMARY.exists() and FH_MD.exists()):
        return
    sm = pd.read_csv(FH_SUMMARY)
    wc4 = sm[sm["path"] == "WC4"].iloc[0]
    wc3 = sm[sm["path"] == "WC3"].iloc[0]
    canon = _fmt(pd.read_csv(SUMMARY).iloc[0]["total_6gw_xp"]) if SUMMARY.exists() else ""
    text = FH_MD.read_text(encoding="utf-8")
    text = _patch_updated(text)
    text = re.sub(
        r"\*\*Status\*\*: [^\n]+",
        "**Status**: Active sibling calendar of Canonical Preseason Chip Path (same Prior-Season Dual-Vector Seed; does not replace GW1–6 BB1+WC4)",
        text,
        count=1,
    )
    text = text.replace("5. Do not overwrite Canonical 356.61.", "5. Do not replace Canonical chip calendar (BB1+WC4, GW1–6). Totals live in named CSVs.")
    text = text.replace("Do not promote over Canonical 356.61 until Dual-Vector xP is accepted as the live scale.", "Canonical GW1–6 total lives in `gw1-6_wc4_summary.csv` `total_6gw_xp`. This note ranks GW1–19 calendars.")
    t19 = _fmt(wc4["total_19gw_xp"])
    t3 = _fmt(wc3["total_19gw_xp"])
    delta = round(float(wc3["total_19gw_xp"]) - float(wc4["total_19gw_xp"]), 2)
    findings = f"""### Evidence

- **WC4 winner**: BB{int(wc4['bb'])}, WC{int(wc4['wc'])}, TC{int(wc4['tc'])}, FH{int(wc4['fh'])}. **{t19} xP**. {int(wc4['n_fts'])} FTs, {int(wc4['hits'])} hits. Spend £{float(wc4['pre_spend']):.1f} / £{float(wc4['fh_spend']):.1f} FH / £{float(wc4['post_spend']):.1f} post. Source: `first_half_summary.csv`.
- **WC3 runner-up**: BB{int(wc3['bb'])}, WC{int(wc3['wc'])}, FH{int(wc3['fh'])}, TC{int(wc3['tc'])}. **{t3} xP** ({delta:+.2f} vs WC4).
"""
    if FH_SQUADS.exists():
        sq = pd.read_csv(FH_SQUADS)
        findings += f"- **WC4 pre-WC 15**: {_fh_phase_names(sq, 4, 'pre-WC')}.\n"
        findings += f"- **WC4 rebuild**: {_fh_phase_names(sq, 4, 'WC rebuild')}.\n"
        findings += f"- **WC4 FH{int(wc4['fh'])}**: {_fh_phase_names(sq, 4, 'FH')}.\n"
    findings += "- **DCS**: live topic `docs/research/defensive-fixture-rotation/` (same Seed). This calendar does not write a sibling `dcs/` folder.\n"
    text = re.sub(
        r"### Evidence\n.*?\n### Select 11",
        findings.rstrip() + "\n\n### Select 11",
        text,
        count=1,
        flags=re.S,
    )
    if FH_SELECT.exists():
        table = _fh_select_table(pd.read_csv(FH_SELECT))
        text = re.sub(
            r"(\| GW \| Chip \| Form \| GKP \| DEF \| MID \| FWD \| Bench \| xP \|\n\|---\|.*?\n)(?:\|.*\n)+",
            r"\1" + table.split("\n", 2)[2] + "\n",
            text,
            count=1,
        )
    if canon:
        text = re.sub(
            r"Canonical \*\*[0-9.]+\*\* stays the live GW1–6 FDR-xP number.",
            f"Canonical GW1–6 Seed total is **{canon}** (`gw1-6_wc4_summary.csv` `total_6gw_xp`).",
            text,
            count=1,
        )
        text = re.sub(
            r"at \*\*[0-9.]+ Dual-Vector xP\*\*\.",
            f"at **{t19} Dual-Vector xP** (`first_half_summary.csv` `total_19gw_xp`).",
            text,
            count=1,
        )
    text = text.replace(
        "Haaland in the GW1 BB 15 under Dual-Vector (Canonical FDR path delayed him to WC4).",
        "Haaland in the GW1 BB 15 on Seed (Canonical Stage 3 also drafts him pre-WC).",
    )
    text = text.replace(
        "Do not mix FDR-xP 356.61 with these Dual-Vector week totals.",
        "Canonical GW1–6 totals live in `gw1-6_wc4_summary.csv` `total_6gw_xp`.",
    )
    text = text.replace("not comparable to 356.61", "not comparable to Canonical 6GW `total_6gw_xp`")
    text = text.replace("vs 356.61 FDR-xP", "vs Canonical `total_6gw_xp`")
    text = re.sub(
        r"- \*\*DCS \(this topic only\)\*\*:.*\n",
        "- **DCS**: live topic `docs/research/defensive-fixture-rotation/` (same Seed). This calendar does not write a sibling `dcs/` folder.\n",
        text,
        count=1,
    )
    FH_MD.write_text(text, encoding="utf-8")
    if FH_README.exists():
        readme = FH_README.read_text(encoding="utf-8")
        readme = re.sub(
            r"Live Canonical remains GW1 BB \+ WC4 \*\*[^*]+\*\* FDR-xP.",
            f"Sibling GW1–19 calendar. Canonical GW1–6 is `gw1-6_wc4_summary.csv` `total_6gw_xp` (**{canon}** Seed xP)."
            if canon
            else "Sibling GW1–19 calendar. Canonical GW1–6 lives in `gw1-6_wc4_summary.csv`.",
            readme,
            count=1,
        )
        FH_README.write_text(readme, encoding="utf-8")


def _gkp_rows(df: pd.DataFrame, horizon: str, extra: bool) -> str:
    h = df[df["horizon"] == horizon]
    chunks: list[pd.DataFrame] = []
    chunks.append(h[h["strategy"].str.contains("Active", na=False)].sort_values("dcs", ascending=False).head(4))
    for strat in h["strategy"].unique():
        if "Active" in str(strat):
            continue
        chunks.append(h[h["strategy"] == strat].sort_values("dcs", ascending=False).head(1))
    tab = pd.concat(chunks).drop_duplicates(subset=["pairing"])
    lines = []
    for r in tab.itertuples():
        if extra:
            lines.append(
                f"| **{r.strategy}** | **{r.pairing}** | **£{float(r.total_price):.1f}m** | **{_fmt(r.tot_rot_xp)}** | "
                f"**{_fmt(r.rot_xp_per_gw)}** | **{_fmt(r.oc_score)}** | **{_fmt(r.dcs)}** | "
                f"**{_fmt(r.rot_avg_fdr)}** | **{float(r.no_diff_pct):.1f}%** |"
            )
        else:
            lines.append(
                f"| **{r.strategy}** | **{r.pairing}** | **£{float(r.total_price):.1f}m** | **{_fmt(r.tot_rot_xp)}** | "
                f"**{_fmt(r.oc_score)}** | **{_fmt(r.dcs)}** | **{_fmt(r.rot_avg_fdr)}** |"
            )
    return "\n".join(lines)


def sync_dcs_note() -> None:
    if not (DCS_GKP.exists() and DCS_MD.exists()):
        return
    gkp = pd.read_csv(DCS_GKP)
    text = DCS_MD.read_text(encoding="utf-8")
    text = _patch_updated(text)
    text = re.sub(
        r"\*\*Data stamp\*\*: [^\n]+",
        "**Data stamp**: Prior-Season Dual-Vector Seed effective FDR (`defence_multiplier × 3`); Stage 2 rates 2026-08-18; FPL API 2026-08-19",
        text,
        count=1,
    )
    gw19 = _gkp_rows(gkp, "gw1_19", extra=True)
    gw13 = _gkp_rows(gkp, "gw1_3", extra=False)
    text = re.sub(
        r"(#### 1\. Full First Half \(GW1–19\)\n\n\| Strategy Archetype \|.*\n\|---.*\n)(?:\|.*\n)+",
        r"\1" + gw19 + "\n",
        text,
        count=1,
    )
    text = re.sub(
        r"(#### 2\. Pre-Wildcard Sprint with GW1 Bench Boost \(GW1–3 BB1\)\n\n\| Strategy Archetype \|.*\n\|---.*\n)(?:\|.*\n)+",
        r"\1" + gw13 + "\n",
        text,
        count=1,
    )
    top19 = gkp[gkp["horizon"] == "gw1_19"].sort_values("dcs", ascending=False).iloc[0]
    top13 = gkp[gkp["horizon"] == "gw1_3"].sort_values("dcs", ascending=False).iloc[0]
    text = re.sub(
        r"> - \*\*In GW1–3 Bench Boost\*\*:.*\n",
        f"> - **In GW1–3 Bench Boost**: `{top13['pairing']}` DCS **{_fmt(top13['dcs'])}**, **{_fmt(top13['tot_rot_xp'])} xP**. Source: `gkp_strategy_comparison.csv`.\n",
        text,
        count=1,
    )
    text = re.sub(
        r"> - \*\*In GW1–19 Long-Term\*\*:.*\n",
        f"> - **In GW1–19 Long-Term**: `{top19['pairing']}` **{_fmt(top19['tot_rot_xp'])} xP**, DCS **{_fmt(top19['dcs'])}**, rot FDR **{_fmt(top19['rot_avg_fdr'])}**. Source: `gkp_strategy_comparison.csv`.\n",
        text,
        count=1,
    )
    if DCS_PART.exists():
        part = pd.read_csv(DCS_PART)
        five = part[(part["horizon"] == "gw1_19") & (part["num_unique_clubs"] == 5)].sort_values("rot_avg_fdr")
        if len(five):
            row = five.iloc[0]
            text = re.sub(
                r"§2 FDR-min #1 `[A-Z-]+` \(rot FDR \*\*[0-9.]+\*\*",
                f"§2 Seed-FDR-min #1 `{row['clubs']}` (rot FDR **{float(row['rot_avg_fdr']):.4f}**",
                text,
                count=1,
            )
    if DCS_BACK.exists():
        back = pd.read_csv(DCS_BACK).sort_values("dcs", ascending=False).head(5)
        blines = []
        for i, r in enumerate(back.itertuples(), start=1):
            blines.append(
                f"| **{i}** | **{r.gkp_pairing}** | **{r.def_lineup}** | **£{float(r.total_price):.1f}m** | "
                f"**{_fmt(r.dcs)}** | **{_fmt(getattr(r, 'oc_score', 0))}** | **{_fmt(r.tot_rot_xp)}** | "
                f"**{_fmt(r.rot_avg_fdr)}** |"
            )
        text = re.sub(
            r"(\| \*\*1\*\* \| \*\*[^*]+\*\* \| \*\*[^*]+\*\* \| \*\*£[^*]+\*\* \| \*\*[0-9.]+\*\* \|.*\n)(?:\| \*\*[1-5]\*\* \|.*\n)+",
            blines[0] + "\n" + "\n".join(blines[1:]) + "\n" if blines else r"\1",
            text,
            count=1,
        )
        if len(back):
            b0 = back.iloc[0]
            text = re.sub(
                r"- \*\*[^*]+ \+ [^*]+\*\* with \*\*[^*]+\*\* \(\*\*[0-9.]+ xP\*\*, DCS \*\*[0-9.]+\*\*\).*",
                f"- **{b0['gkp_pairing']}** with **{b0['def_lineup']}** (**{_fmt(b0['tot_rot_xp'])} xP**, DCS **{_fmt(b0['dcs'])}**). Rot FDR **{_fmt(b0['rot_avg_fdr'])}**. Source: `backline_gw1_19_lineups.csv`. This is a Defensive Rotation Set, not a reprint of the Stage 3 15.",
                text,
                count=1,
            )
    DCS_MD.write_text(text, encoding="utf-8")


def sync_ownership_stamp() -> None:
    if not (SUMMARY.exists() and OWN_MD.exists()):
        return
    s = pd.read_csv(SUMMARY).iloc[0]
    t = _fmt(s["total_6gw_xp"])
    g13 = _fmt(s["gw1_3_xp"])
    g46 = _fmt(s["gw4_6_xp"])
    text = OWN_MD.read_text(encoding="utf-8")
    text = _patch_updated(text)
    text = re.sub(
        r"Stage 3 GW1 BB \+ WC4 [0-9.]+ xP",
        f"Stage 3 GW1 BB + WC4 {t} xP (`gw1-6_wc4_summary.csv` `total_6gw_xp`)",
        text,
        count=1,
    )
    text = re.sub(
        r"### 1\. Pre-WC Sprint Differentials \(GW1–3 BB1 Target, [0-9.]+ xP\)",
        f"### 1. Pre-WC Sprint Differentials (GW1–3 BB1 Target, {g13} xP)",
        text,
        count=1,
    )
    text = re.sub(
        r"### 2\. Post-WC4 Core Squad Structure \(GW4–6 Foundation, [0-9.]+ xP\)",
        f"### 2. Post-WC4 Core Squad Structure (GW4–6 Foundation, {g46} xP)",
        text,
        count=1,
    )
    OWN_MD.write_text(text, encoding="utf-8")


def sync_canonical_rescore_csv() -> None:
    path = ROOT / "data/research/gw1-19-first-half-chip-path/canonical_s1_dual_vector_rescore.csv"
    if not SUMMARY.exists():
        return
    s = pd.read_csv(SUMMARY).iloc[0]
    total = float(s["total_6gw_xp"])
    pd.DataFrame([{
        "note": "Canonical S1 15s on Prior-Season Dual-Vector Seed (live Canonical score world)",
        "total_6gw_xp_dv": total,
        "captains": {i: s[f"gw{i}_captain"] for i in range(1, 7)},
        "canonical_total_xp": total,
    }]).to_csv(path, index=False)


def sync_all() -> None:
    sync_canonical_rescore_csv()
    sync_stage3_note()
    sync_pipeline_readme()
    sync_index()
    sync_first_half_note()
    sync_dcs_note()
    sync_ownership_stamp()
    sync_current_state()
    print("Synced research figure caches from CSVs.")


if __name__ == "__main__":
    sync_all()

"""Research catalog and model methodology for dashboard surfaces."""

import logging
from pathlib import Path

import pandas as pd

from models import get_default_model_name, list_model_names

PROJECT_ROOT = Path(__file__).resolve().parents[1]
logger = logging.getLogger(__name__)


def get_research_topics() -> list[dict[str, object]]:
    research_dir = PROJECT_ROOT / "docs" / "research"
    if not research_dir.exists():
        return []
    topics = []
    for item in sorted(research_dir.iterdir()):
        if not item.is_dir() or item.name in ("template", ".tmp"):
            continue
        md_files = list(item.glob("*.md"))
        if not md_files:
            continue
        main_md = item / f"{item.name}.md"
        if not main_md.exists():
            main_md = md_files[0]
        title = item.name.replace("-", " ").title()
        status = "Active"
        try:
            content = main_md.read_text(encoding="utf-8")
            for line in content.splitlines()[:25]:
                if line.startswith("# "):
                    title = line[2:].strip()
                elif "**Status**:" in line:
                    status = line.split("**Status**:", 1)[1].strip()
        except Exception:
            pass
        csv_files = [f.name for f in item.glob("*.csv")]
        topics.append({
            "slug": item.name,
            "title": title,
            "status": status,
            "file": main_md.name,
            "csv_count": len(csv_files),
            "csv_files": csv_files,
        })
    return topics


def get_research_topic_detail(slug: str) -> dict[str, object]:
    if slug not in {topic["slug"] for topic in get_research_topics()}:
        return {"error": "Research topic not found"}
    topic_dir = PROJECT_ROOT / "docs" / "research" / slug
    if not topic_dir.exists() or not topic_dir.is_dir():
        return {"error": f"Topic '{slug}' not found"}
    md_files = list(topic_dir.glob("*.md"))
    if not md_files:
        return {"error": "No markdown file in topic"}
    main_md = topic_dir / f"{slug}.md"
    if not main_md.exists():
        main_md = md_files[0]
    content = main_md.read_text(encoding="utf-8")

    companions: dict[str, object] = {}
    for csv_path in sorted(topic_dir.glob("*.csv")):
        try:
            full_df = pd.read_csv(csv_path)
            total_rows = len(full_df)
            df = full_df.head(100)
            companions[csv_path.name] = {
                "columns": list(df.columns),
                "rows": df.fillna("").values.tolist(),
                "total_rows": total_rows,
            }
        except Exception as exc:
            logger.warning("Failed to read CSV %s: %s", csv_path, exc)

    return {
        "slug": slug,
        "filename": main_md.name,
        "content": content,
        "companions": companions,
    }


def get_model_methodology() -> dict[str, object]:
    champion = get_default_model_name()
    comparison_slate = [m for m in list_model_names() if m != champion]

    ledger_path = PROJECT_ROOT / "docs" / "research" / "candidate-ledger" / "candidate_ledger.csv"
    shipped_levers: list[str] = []
    dead_levers: list[str] = []
    if ledger_path.exists():
        try:
            df = pd.read_csv(ledger_path)
            if "status" in df.columns and "lever" in df.columns:
                shipped_levers = list(dict.fromkeys(str(row["lever"]) for row in df.to_dict("records") if row["status"] == "shipped" and pd.notna(row["lever"])))
                dead_levers = list(dict.fromkeys(str(row["lever"]) for row in df.to_dict("records") if row["status"] == "dead" and pd.notna(row["lever"])))
        except Exception as exc:
            logger.warning("Could not read candidate ledger: %s", exc)

    return {
        "champion": champion,
        "pipeline_layers": [
            {
                "layer": 1,
                "name": "Minutes & Availability",
                "summary": "Stochastic start and sub probability estimation with DNP suppression.",
                "formula": "xMins = p_start * E[mins|start] + p_sub * E[mins|sub] - dnp_penalty",
                "details": "Models player appearance rates using trailing start windows (ADR 0035), rolling minutes, news status, and official chance-of-playing flags.",
            },
            {
                "layer": 2,
                "name": "Rates & Shrinkage",
                "summary": "Per-90 event rate regression with defensive xG empirical shrinkage.",
                "formula": "shrunk_rate = (sum_stat + K * mean) / (sum_mins + K)",
                "details": f"Champion '{champion}' applies pseudo-minutes shrinkage (K=2400 for DEF xG per ADR 0055). Poisson clean sheet rate is derived from expected goals conceded.",
            },
            {
                "layer": 3,
                "name": "Matchup & Fixture Multipliers",
                "summary": "Opponent strength scaling via Modified FDR and Calibrated Matchup Share.",
                "formula": "scaled_rate = base_rate * matchup_share(club, opp)",
                "details": "Uses Modified FDR (difficulty rating 1.0-5.0) and Calibrated Matchup Share (ADR 0040) to dynamically adjust clean sheet and attacking probabilities.",
            },
            {
                "layer": 4,
                "name": "Scoring Matrix & Component Deconstruction",
                "summary": "Translates scaled rates into 8 distinct FPL scoring components.",
                "formula": "Total xP = xp_mins + xp_goals + xp_assists + xp_cs - xp_gc + xp_defcon + xp_saves + xp_bonus",
                "details": "Guarantees exact traceability across position-specific rules (e.g. DEF goal = 6 pts, MID goal = 5 pts, FWD goal = 4 pts).",
            },
        ],
        "candidate_ledger_summary": {
            "policy": "Hard Rule: Dead levers can never be retried before revisit_after (1 year). Log all attempts in candidate_ledger.csv.",
            "champion": champion,
            "slate": comparison_slate,
            "shipped_count": len(shipped_levers),
            "dead_count": len(dead_levers),
        },
    }



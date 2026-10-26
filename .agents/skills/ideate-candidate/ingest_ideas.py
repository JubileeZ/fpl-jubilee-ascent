"""Ingest candidate proposals from external model responses into idea_queue.csv.

Parses external LLM ideation proposals, checks for dead-lever matches against
the Candidate Ledger, and appends structured rows to the candidate work queue.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import re
import sys

import pandas as pd


def find_repo_root() -> Path:
    current = Path(__file__).resolve().parent
    for p in [current, *current.parents]:
        if (p / "pyproject.toml").exists():
            return p
    return Path(__file__).resolve().parents[3]


REPO_ROOT = find_repo_root()
QUEUE_PATH = REPO_ROOT / "docs" / "research" / "candidate-ideation" / "idea_queue.csv"
LEDGER_PATH = REPO_ROOT / "docs" / "research" / "candidate-ledger" / "candidate_ledger.csv"

QUEUE_COLUMNS = [
    "order",
    "idea_id",
    "tier",
    "component",
    "name",
    "mechanism",
    "inputs",
    "replaces",
    "nearest_ledger_row",
    "confirm_informative",
    "grid",
    "conflicts_with",
    "status",
    "ledger_result",
]

# Dead lever signature triggers
DEAD_LEVER_KEYWORDS: list[tuple[set[str], str]] = [
    ({"11", "conservation"}, "ARCH-01: Club 11-man mass conservation"),
    ({"mass", "conservation"}, "ARCH-01: Club 11-man mass conservation"),
    ({"unregularized", "ridge"}, "ARCH-02: Unregularized in-season ridge refits"),
    ({"relaxing", "defender"}, "ARCH-03: Relaxing defender xG shrinkage"),
    ({"k_def", "relax"}, "ARCH-03: Relaxing defender xG shrinkage"),
    ({"bonus", "saturation"}, "ARCH-04: Bonus pool saturation caps"),
    ({"b_max", "cap"}, "ARCH-04: Bonus pool saturation caps"),
    ({"raw", "matchup"}, "ARCH-05: Raw/unshrunk opponent matchup multipliers"),
    ({"unshrunk", "matchup"}, "ARCH-05: Raw/unshrunk opponent matchup multipliers"),
    ({"congestion", "logit"}, "ARCH-06: Static schedule congestion shifts"),
    ({"congestion", "shift"}, "ARCH-06: Static schedule congestion shifts"),
    ({"latent", "hmm"}, "ARCH-07: Latent HMM participation modeling"),
    ({"step", "early", "ml"}, "ARCH-08: Step-function early ML activation"),
    ({"transfer", "churn", "dnp"}, "ARCH-09: Transfer churn / price momentum hazard"),
    ({"absence", "redistribution"}, "ARCH-10: Teammate absence share redistribution"),
    ({"yellow", "card", "bayes"}, "ARCH-11: Empirical Bayes yellow card rates"),
    ({"defcon", "dispersion"}, "ARCH-12: Defcon over-dispersion mixture"),
    ({"defcon", "beta"}, "ARCH-12: Defcon beta-binomial hit rate"),
    ({"natural", "rate", "unsharp"}, "ARCH-13: Natural rate calibration"),
    ({"gkp", "softmax"}, "ARCH-14: GKP starting slot softmax"),
]

_SECTION_STOP = (
    r"(?=\n\s*(?:\d+\.\s*|\-\s*)?\*{0,2}(?:"
    r"Concept|Football Hypothesis|Hypothesis|Mechanism|Mathematical Formulation|"
    r"Decoupled Architecture|Architecture Placement|Replaces|Integration Hook|"
    r"Parameter Sweep Grid|Sweep Grid|Grid|Small-Sample|Cold-Start|"
    r"Budget-Constrained|Optimizer Interaction|Point-in-Time|Feature|Inputs|Covariates|"
    r"Python Code"
    r")|\n#{2,4}\s|\Z)"
)


def load_dead_levers() -> list[str]:
    if not LEDGER_PATH.exists():
        return []
    try:
        df = pd.read_csv(LEDGER_PATH)
        return df[df["status"] == "dead"]["lever"].dropna().tolist()
    except Exception:
        return []


def check_dead_lever_match(name: str, mechanism_text: str, dead_levers: list[str]) -> str:
    combined = f"{name} {mechanism_text}".lower()
    combined_tokens = set(re.split(r"[^a-z0-9_]+", combined))

    # 1. Check known signature triggers
    for kw_set, label in DEAD_LEVER_KEYWORDS:
        if kw_set.issubset(combined_tokens):
            return label

    # 2. Check token overlap with dead levers from CSV
    for dead in dead_levers:
        dead_tokens = [w for w in re.split(r"[^a-z0-9_]+", dead.lower()) if len(w) > 4]
        if dead_tokens and sum(1 for t in dead_tokens if t in combined_tokens) >= 3:
            return dead

    return ""


def clean_markdown_field(text: str) -> str:
    """Clean markdown formatting and bold prefixes while preserving underscores."""
    cleaned = re.sub(r"^\s*(?:\d+\.\s*)?[*#\-:]+\s*", "", text)
    cleaned = re.sub(r"[*`]", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _extract_field(body: str, label_pattern: str) -> str:
    pattern = re.compile(
        rf"(?:^|\n)\s*(?:\d+\.\s*|\-\s*)?\*{{0,2}}(?:{label_pattern})[^:\n]*\*{{0,2}}[:\-\s]+\n*(.+?){_SECTION_STOP}",
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(body)
    return clean_markdown_field(match.group(1)) if match else ""


def _resolve_component(placement_text: str, body: str) -> str:
    combined = f"{placement_text} {body}".lower()
    for explicit in (
        "xp_minutes",
        "xp_goals",
        "xp_assists",
        "xp_clean_sheets",
        "xp_saves",
        "xp_defcon",
        "xp_bonus",
    ):
        if explicit in placement_text.lower():
            return explicit
    if "m_{\\text{mins}}" in combined or "m_{mins}" in combined or "minutes" in placement_text.lower() or "participation" in placement_text.lower():
        return "xp_minutes"
    if "assist" in placement_text.lower() or "xa" in placement_text.lower():
        return "xp_assists"
    if "goal" in placement_text.lower() or "xg" in placement_text.lower():
        return "xp_goals"
    if "save" in placement_text.lower() or "goalkeeper" in placement_text.lower():
        return "xp_saves"
    if "clean sheet" in placement_text.lower() or "defcon" in placement_text.lower() or "defense" in placement_text.lower():
        return "xp_clean_sheets"
    if "bonus" in placement_text.lower() or "bps" in placement_text.lower():
        return "xp_bonus"
    if "m_{mins}" in combined or "minutes" in combined or "participation" in combined:
        return "xp_minutes"
    return "all"


def parse_markdown_response(content: str) -> list[dict[str, str]]:
    """Parse candidate ideas from markdown text."""
    ideas: list[dict[str, str]] = []
    header_pattern = re.compile(
        r"(?:^|\n)#{2,4}\s+(?:(?:Candidate|Idea|Proposal)(?:\s+Model)?\s*(?:(\d+|[A-Za-z0-9_-]+))?[:\.\-\s]+|(\d+)[\.\)\:\-\s]+)(.+?)(?=\n)",
        re.IGNORECASE,
    )
    matches = list(header_pattern.finditer(content))

    for i, match in enumerate(matches):
        raw_id = match.group(1) or match.group(2) or f"EXT-{i + 1:02d}"
        idea_id = (
            raw_id.upper()
            if raw_id.upper().startswith(("EXT-", "MIN-", "ATK-", "DEF-", "BON-"))
            else f"EXT-{i + 1:02d}"
        )
        name = clean_markdown_field(match.group(3))

        start_pos = match.end()
        end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        body = content[start_pos:end_pos].strip()

        concept = _extract_field(body, r"Concept|Football Hypothesis|Hypothesis|Mechanism")
        math_form = _extract_field(body, r"Mathematical Formulation")
        if concept and math_form:
            mechanism = f"{concept} | Math: {math_form}"[:400]
        elif concept:
            mechanism = concept[:400]
        elif math_form:
            mechanism = math_form[:400]
        else:
            mechanism = clean_markdown_field(body[:300])[:400]

        placement = _extract_field(body, r"Decoupled Architecture|Architecture Placement")
        comp = _resolve_component(placement, body)

        replaces = _extract_field(body, r"Replaces|Integration Hook") or "Champion component"
        grid = _extract_field(body, r"Parameter Sweep Grid|Sweep Grid|Grid") or "default"
        raw_inputs = _extract_field(body, r"Point-in-Time Feature|Feature|Inputs|Covariates")
        inputs = raw_inputs.replace("\n", "; ")[:200] if raw_inputs else "history.minutes; features.position_id"

        ideas.append({
            "idea_id": idea_id,
            "tier": "P1",
            "component": comp,
            "name": name,
            "mechanism": mechanism,
            "inputs": inputs,
            "replaces": replaces[:200],
            "nearest_ledger_row": "",
            "confirm_informative": "informative",
            "grid": grid[:200],
            "conflicts_with": "",
            "status": "untested",
            "ledger_result": "",
        })

    return ideas


def ingest_file(input_path: Path, queue_path: Path = QUEUE_PATH) -> int:
    if not input_path.exists():
        print(f"Error: input file {input_path} does not exist", file=sys.stderr)
        return 1

    content = input_path.read_text(encoding="utf-8")
    dead_levers = load_dead_levers()

    next_order = 1
    existing_ideas = set()
    if queue_path.exists() and queue_path.stat().st_size > 0:
        try:
            existing_df = pd.read_csv(queue_path)
            if not existing_df.empty and "order" in existing_df.columns:
                next_order = int(pd.to_numeric(existing_df["order"], errors="coerce").dropna().max() or 0) + 1
            if "idea_id" in existing_df.columns:
                existing_ideas = set(existing_df["idea_id"].astype(str).tolist())
        except Exception:
            next_order = 1

    parsed_ideas = parse_markdown_response(content)
    if not parsed_ideas:
        print(f"Warning: no candidate ideas matched in {input_path}. Expecting markdown headers like '### Candidate 1: <Name>'.")
        return 0

    new_rows: list[dict[str, str | int]] = []
    for idea in parsed_ideas:
        matched_dead = check_dead_lever_match(idea["name"], idea["mechanism"], dead_levers)
        if matched_dead:
            print(f"  [!] Warning: Idea '{idea['name']}' matches dead lever: {matched_dead}")
            idea["nearest_ledger_row"] = matched_dead
            idea["status"] = "dead-match"

        orig_id = idea["idea_id"]
        counter = 1
        while idea["idea_id"] in existing_ideas:
            idea["idea_id"] = f"{orig_id}_{counter}"
            counter += 1
        existing_ideas.add(idea["idea_id"])

        idea["order"] = next_order
        next_order += 1
        new_rows.append(idea)

    file_exists = queue_path.exists() and queue_path.stat().st_size > 0
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    with open(queue_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=QUEUE_COLUMNS)
        if not file_exists:
            writer.writeheader()
        for row in new_rows:
            writer.writerow(row)

    print(f"Successfully ingested {len(new_rows)} candidate ideas into: {queue_path}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest external candidate ideas into idea_queue.csv.")
    parser.add_argument("response_file", type=Path, help="Path to raw markdown response file.")
    parser.add_argument("--queue", type=Path, default=QUEUE_PATH, help="Path to idea_queue.csv.")
    args = parser.parse_args()

    sys.exit(ingest_file(args.response_file, queue_path=args.queue))


if __name__ == "__main__":
    main()

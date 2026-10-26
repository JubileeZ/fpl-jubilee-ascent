"""Ingest candidate proposals from external model responses into idea_queue.csv.

Parses external LLM ideation proposals, checks for dead-lever matches against
the Candidate Ledger, and appends structured rows to the candidate work queue.
"""

from __future__ import annotations

import argparse
import csv
import keyword
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
    "spec_path",
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


def slugify(text: str) -> str:
    """Generate clean URL-safe kebab-case slug from text."""
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower())
    return cleaned.strip("-") or "idea"


def _yaml_escape(val: str) -> str:
    """Format value for YAML frontmatter safely quoting special characters."""
    val = val.strip()
    if not val:
        return '""'
    if val.lower() == "null":
        return "null"
    needs_quotes = (
        any(c in val for c in (':', '{', '}', '[', ']', '&', '*', '#', '?', '|', '<', '>', '=', '!', '%', '@', '\\', '"', "'", '\n'))
        or val.startswith(('-', '+', '@'))
        or val.lower() in ("yes", "no", "true", "false", "on", "off")
    )
    if needs_quotes:
        import json
        return json.dumps(val)
    return val


def _scaffold_python_skeleton(idea: dict[str, str]) -> str:
    """Synthesize a starting AdaptiveCausalChallengerModel subclass skeleton."""
    name = idea.get("name", "Candidate")
    words = [w for w in re.split(r"[^a-zA-Z0-9]+", name) if w]
    camel = "".join(w.capitalize() for w in words)
    if not camel or camel[0].isdigit():
        camel = f"Candidate{camel}"
    if camel.endswith("ChallengerModel"):
        class_name = camel
    elif camel.endswith("Model"):
        class_name = f"{camel[:-5]}ChallengerModel"
    else:
        class_name = f"{camel}ChallengerModel"

    raw_grid = idea.get("grid", "")
    first_variant = raw_grid.split(";")[0].strip() if raw_grid else ""
    params: list[tuple[str, float]] = []
    if first_variant:
        for pair in re.split(r"[,;]\s*", first_variant):
            if "=" in pair:
                k, v = pair.split("=", 1)
                k_clean = re.sub(r"[^a-zA-Z0-9_]", "", k.strip().lower())
                if not k_clean:
                    continue
                if k_clean[0].isdigit():
                    k_clean = f"p_{k_clean}"
                if keyword.iskeyword(k_clean):
                    k_clean = f"{k_clean}_"
                try:
                    v_clean = float(re.sub(r"[^0-9\.\-eE]", "", v.strip()))
                    params.append((k_clean, v_clean))
                except ValueError:
                    continue

    init_args = [f"{k}: float = {v}" for k, v in params]
    init_sig = f", {', '.join(init_args)}" if init_args else ""
    assignments = "\n".join(f"        self.{k} = float({k})" for k, _ in params)
    if not assignments:
        assignments = "        pass"

    replaces = idea.get("replaces", "")
    hook_match = re.search(r"(_[a-zA-Z0-9_]+)", replaces)
    hook_name = hook_match.group(1) if hook_match else "_project_event_components"
    if not hook_name.isidentifier():
        hook_name = "_project_event_components"

    return (
        "```python\n"
        "from __future__ import annotations\n\n"
        "from models.adaptive_causal_challenger import AdaptiveCausalChallengerModel\n\n\n"
        f"class {class_name}(AdaptiveCausalChallengerModel):\n"
        f'    """Auto-scaffolded skeleton for {name}."""\n\n'
        f"    def __init__(self{init_sig}, **kwargs: object) -> None:\n"
        "        super().__init__(**kwargs)\n"
        f"{assignments}\n\n"
        f"    def {hook_name}(self, *args: object, **kwargs: object) -> object:\n"
        f"        # Hook target: {replaces}\n"
        f"        parent_method = getattr(super(), '{hook_name}', None)\n"
        "        if callable(parent_method):\n"
        f"            return parent_method(*args, **kwargs)\n"
        f"        raise NotImplementedError('{hook_name} mechanism not yet implemented')\n"
        "```"
    )


def build_dossier_markdown(idea: dict[str, str], matched_dead: str = "") -> str:
    """Generate structured markdown dossier with YAML frontmatter."""
    raw_body = idea.get("raw_body", "").strip()

    # Format numbered list sections (e.g. '1. **Concept**:') into standard markdown headings
    heading_pattern = re.compile(
        r"(?m)^([1-9])\.\s*(?:\*\*)?(Concept[^*\n:]*|Mathematical Formulation[^*\n:]*|Decoupled Architecture[^*\n:]*|Replaces[^*\n:]*|Parameter Sweep Grid[^*\n:]*|Small-Sample[^*\n:]*|Budget-Constrained[^*\n:]*|Point-in-Time[^*\n:]*|Python Code Skeleton[^*\n:]*)(?:\*\*)?[:\s]*(?=\n|[^\s])",
        re.IGNORECASE,
    )
    formatted_body = heading_pattern.sub(r"## \1. \2\n\n", raw_body)

    # Check if section 9 contains a valid python code block
    code_section_pattern = re.compile(
        r"## 9\.\s*Python Code Skeleton[^\n]*\n*(.+?)(?=\n## |\Z)", re.DOTALL | re.IGNORECASE
    )
    code_match = code_section_pattern.search(formatted_body)
    has_code = False
    if code_match:
        sec9_text = code_match.group(1)
        has_code = bool(
            re.search(r"```(?:python|py)?\s*\n.*?(?:class\s+|def\s+)", sec9_text, re.DOTALL | re.IGNORECASE)
        )

    if not has_code:
        skeleton = _scaffold_python_skeleton(idea)
        scaffold_block = f"## 9. Python Code Skeleton (Auto-Scaffolded)\n\n{skeleton}\n"
        if code_match:
            start, end = code_match.span()
            formatted_body = formatted_body[:start] + scaffold_block + formatted_body[end:]
        else:
            formatted_body = formatted_body.rstrip() + f"\n\n{scaffold_block}"

    frontmatter = (
        "---\n"
        f"idea_id: {_yaml_escape(str(idea['idea_id']))}\n"
        f"name: {_yaml_escape(str(idea['name']))}\n"
        f"tier: {_yaml_escape(str(idea['tier']))}\n"
        f"component: {_yaml_escape(str(idea['component']))}\n"
        f"status: {_yaml_escape(str(idea['status']))}\n"
        f"replaces: {_yaml_escape(str(idea['replaces']))}\n"
        f"grid: {_yaml_escape(str(idea['grid']))}\n"
        f"inputs: {_yaml_escape(str(idea['inputs']))}\n"
        f"nearest_ledger_row: {_yaml_escape(str(idea.get('nearest_ledger_row') or 'null'))}\n"
        f"spec_path: {_yaml_escape(str(idea['spec_path']))}\n"
        "---\n\n"
        f"# {idea['idea_id']}: {idea['name']}\n\n"
        f"{formatted_body}\n"
    )
    if matched_dead:
        frontmatter += (
            "\n## Ledger Audit & Revisit Justification\n"
            f"- **Flagged Match**: `{matched_dead}`\n"
            "- **Audit Status**: Pending Review\n"
            "- **Rationale**: [Document why this proposal is structurally distinct from the flagged dead lever before promoting to status: untested]\n"
        )
    return frontmatter


def parse_markdown_response(content: str) -> list[dict[str, str]]:
    """Parse candidate ideas from markdown text."""
    ideas: list[dict[str, str]] = []
    header_pattern = re.compile(
        r"(?:^|\n)(?:(?:#{2,4}\s+)?(?:Candidate|Idea|Proposal)(?:\s+Model)?\s*(?:(\d+|[A-Za-z0-9_-]+))?[:\.\-\s]+|#{2,4}\s+(\d+)[\.\)\:\-\s]+)(.+?)(?=\n|$)",
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
        inputs = raw_inputs.replace("\n", "; ") if raw_inputs else "history.minutes; features.position_id"

        ideas.append({
            "idea_id": idea_id,
            "tier": "P1",
            "component": comp,
            "name": name,
            "mechanism": mechanism,
            "inputs": inputs,
            "replaces": replaces,
            "nearest_ledger_row": "",
            "confirm_informative": "informative",
            "grid": grid,
            "conflicts_with": "",
            "status": "untested",
            "spec_path": "",
            "ledger_result": "",
            "raw_body": body,
        })

    return ideas


def ingest_file(
    input_path: Path,
    queue_path: Path = QUEUE_PATH,
    ideas_dir: Path | None = None,
) -> int:
    if not input_path.exists():
        print(f"Error: input file {input_path} does not exist", file=sys.stderr)
        return 1

    content = input_path.read_text(encoding="utf-8")
    dead_levers = load_dead_levers()

    if ideas_dir is None:
        ideas_dir = queue_path.parent / "ideas"
    ideas_dir.mkdir(parents=True, exist_ok=True)

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

        slug = slugify(idea["name"])
        spec_filename = f"{idea['idea_id']}-{slug}.md"
        spec_path = f"ideas/{spec_filename}"
        idea["spec_path"] = spec_path

        dossier_content = build_dossier_markdown(idea, matched_dead=matched_dead)
        dossier_file = ideas_dir / spec_filename
        dossier_file.write_text(dossier_content, encoding="utf-8")

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
            csv_row = {col: row.get(col, "") for col in QUEUE_COLUMNS}
            writer.writerow(csv_row)

    print(f"Successfully ingested {len(new_rows)} candidate ideas into: {queue_path}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest external candidate ideas into idea_queue.csv.")
    parser.add_argument("response_file", type=Path, help="Path to raw markdown response file.")
    parser.add_argument("--queue", type=Path, default=QUEUE_PATH, help="Path to idea_queue.csv.")
    parser.add_argument("--ideas-dir", type=Path, default=None, help="Directory for idea dossiers.")
    args = parser.parse_args()

    sys.exit(ingest_file(args.response_file, queue_path=args.queue, ideas_dir=args.ideas_dir))


if __name__ == "__main__":
    main()

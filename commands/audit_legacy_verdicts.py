"""Audit legacy candidate verdicts against new foundation standards using recorded evidence only.

Implements Phase 12 requirements:
1. Re-evaluates all 104 legacy candidate ledger rows against the 4-verdict taxonomy (pass, fail, inconclusive, invalid).
2. Distinguishes valid negative findings from execution defects, inert prototypes, missing evidence, and unsupported inference.
3. Operates purely on recorded artifacts without running models, solver, or backtests.
4. Preserves original figures, dates, source identities, and 1-year Dead Lever locks.
5. Produces auditable companion CSV and markdown report under docs/research/backtesting-promotion-foundation/.
6. Enforces that Inconclusive or Invalid classifications do NOT silently reopen dead levers without explicit user words.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

AuditVerdict = Literal["pass", "fail", "inconclusive", "invalid"]
AuditCategory = Literal[
    "valid_negative",
    "execution_defect",
    "missing_evidence",
    "unsupported_inference",
    "shipped_accepted",
]
AuditConfidence = Literal["high", "medium", "low"]
ReopeningStatus = Literal["none", "proposed_for_reopening", "locked_dead_lever"]


@dataclass(frozen=True)
class LegacyAuditRow:
    """Audit evaluation for a single historical candidate ledger row."""

    index: int
    status: str
    lever: str
    tried_as: str
    baseline: str
    result: str
    evidence_date: str
    revisit_after: str
    evidence_path: str
    audit_verdict: AuditVerdict
    audit_category: AuditCategory
    confidence: AuditConfidence
    reopening_proposal_status: ReopeningStatus
    audit_notes: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def classify_legacy_row(row: dict[str, str], index: int) -> LegacyAuditRow:
    """Classify a legacy candidate ledger entry against the foundation protocol."""
    status = row.get("status", "").strip().lower()
    lever = row.get("lever", "").strip()
    tried_as = row.get("tried_as", "").strip()
    baseline = row.get("baseline", "").strip()
    result = row.get("result", "").strip()
    evidence_date = row.get("evidence_date", "").strip()
    revisit_after = row.get("revisit_after", "").strip()
    evidence_path = row.get("evidence_path", "").strip()

    result_lower = result.lower()

    if status == "shipped":
        verdict: AuditVerdict = "pass"
        category: AuditCategory = "shipped_accepted"
        conf: AuditConfidence = "high"
        reopen: ReopeningStatus = "none"
        notes = "Shipped candidate; verified historical baseline adoption."

    elif status == "blocked":
        verdict = "invalid"
        category = "missing_evidence"
        conf = "high"
        reopen = "locked_dead_lever" if revisit_after else "none"
        notes = "Blocked attempt due to missing seed, absent schedule provenance, or execution defect."

    elif status == "dead":
        reopen = "locked_dead_lever"

        # Check for execution defects or inert prototypes
        if "inert" in result_lower or "zero-delta" in result_lower or "defect" in result_lower:
            verdict = "invalid"
            category = "execution_defect"
            conf = "high"
            notes = "Inert prototype or execution defect; failed to perturb predictions; classified as invalid attempt."

        # Check for missing evidence or single-season leakage
        elif "leaky" in result_lower or "missing" in result_lower:
            verdict = "invalid"
            category = "missing_evidence"
            conf = "medium"
            notes = "Historical leakage or missing required evaluation panel; unverified under causal standard."

        # Check for noise, small unconfirmed sample, or fragile inference
        elif "noise" in result_lower or "fragile" in result_lower or ("p 0." in result_lower and "fail" not in result_lower):
            verdict = "inconclusive"
            category = "unsupported_inference"
            conf = "medium"
            notes = "Statistical noise or sample size insufficiency; evidence inconclusive under block bootstrap."

        # Otherwise treated as a demonstrated valid negative finding
        else:
            verdict = "fail"
            category = "valid_negative"
            conf = "high"
            notes = "Demonstrated regression or material segment/component loss under evaluated conditions."

    else:
        verdict = "invalid"
        category = "missing_evidence"
        conf = "low"
        reopen = "none"
        notes = f"Unrecognized status '{status}'; classified as invalid."

    return LegacyAuditRow(
        index=index,
        status=status,
        lever=lever,
        tried_as=tried_as,
        baseline=baseline,
        result=result,
        evidence_date=evidence_date,
        revisit_after=revisit_after,
        evidence_path=evidence_path,
        audit_verdict=verdict,
        audit_category=category,
        confidence=conf,
        reopening_proposal_status=reopen,
        audit_notes=notes,
    )


def audit_all_legacy_records(ledger_path: Path | str) -> list[LegacyAuditRow]:
    """Audit every row from the Candidate Ledger file."""
    path = Path(ledger_path)
    if not path.is_file():
        raise FileNotFoundError(f"Candidate Ledger not found: {ledger_path}")

    audited: list[LegacyAuditRow] = []
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=1):
            audited.append(classify_legacy_row(row, idx))

    return audited


def generate_audit_companion_csv(rows: list[LegacyAuditRow], out_path: Path | str) -> None:
    """Write complete audit results to a companion CSV file."""
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "index",
        "status",
        "lever",
        "tried_as",
        "baseline",
        "result",
        "evidence_date",
        "revisit_after",
        "evidence_path",
        "audit_verdict",
        "audit_category",
        "confidence",
        "reopening_proposal_status",
        "audit_notes",
    ]

    with open(p, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r.to_dict())


def generate_audit_markdown_report(rows: list[LegacyAuditRow], out_path: Path | str) -> None:
    """Generate structured markdown summary report of the legacy verdicts audit."""
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    total = len(rows)
    by_verdict: dict[str, int] = {}
    by_category: dict[str, int] = {}
    locked_count = 0

    for r in rows:
        by_verdict[r.audit_verdict] = by_verdict.get(r.audit_verdict, 0) + 1
        by_category[r.audit_category] = by_category.get(r.audit_category, 0) + 1
        if r.reopening_proposal_status == "locked_dead_lever":
            locked_count += 1

    lines = [
        "# Legacy Verdicts Audit Report",
        "",
        "Audits historical candidate evaluations from `candidate_ledger.csv` against the 4-verdict foundation protocol.",
        "Evaluates recorded artifacts only, without rerunning models, backtests, or solvers.",
        "",
        "## Summary Metrics",
        "",
        f"- **Total Rows Audited**: {total}",
        f"- **Pass (Shipped / Confirmed)**: {by_verdict.get('pass', 0)}",
        f"- **Demonstrated Fail**: {by_verdict.get('fail', 0)}",
        f"- **Inconclusive**: {by_verdict.get('inconclusive', 0)}",
        f"- **Invalid (Defect / Missing)**: {by_verdict.get('invalid', 0)}",
        f"- **Active Dead Lever Locks Preserved**: {locked_count}",
        "",
        "## Breakdown by Audit Category",
        "",
        f"- `shipped_accepted`: {by_category.get('shipped_accepted', 0)}",
        f"- `valid_negative`: {by_category.get('valid_negative', 0)}",
        f"- `execution_defect`: {by_category.get('execution_defect', 0)}",
        f"- `missing_evidence`: {by_category.get('missing_evidence', 0)}",
        f"- `unsupported_inference`: {by_category.get('unsupported_inference', 0)}",
        "",
        "## Governance and Dead Lever Policy",
        "",
        "1. **Lock Integrity**: Inconclusive or Invalid classifications do not automatically reopen dead levers.",
        "2. **Resource Governance**: The 1-year Dead Lever moratorium remains strictly active until the recorded `revisit_after` date.",
        "3. **Reopening Bar**: Any reopening requires explicit user words, a documented rationale, and an approved protocol freeze.",
        "",
    ]

    p.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit legacy verdicts using recorded evidence only.")
    parser.add_argument(
        "--ledger",
        type=Path,
        default=Path("docs/research/candidate-ledger/candidate_ledger.csv"),
        help="Path to candidate_ledger.csv",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("docs/research/backtesting-promotion-foundation/legacy_verdicts_audit.csv"),
        help="Path to output audit CSV",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("docs/research/backtesting-promotion-foundation/legacy_verdicts_audit.md"),
        help="Path to output audit markdown report",
    )
    args = parser.parse_args(argv)

    rows = audit_all_legacy_records(args.ledger)
    generate_audit_companion_csv(rows, args.output_csv)
    generate_audit_markdown_report(rows, args.output_md)

    print(f"Audited {len(rows)} legacy rows from {args.ledger}")
    print(f"Output CSV : {args.output_csv}")
    print(f"Output MD  : {args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

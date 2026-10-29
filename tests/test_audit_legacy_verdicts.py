"""Unit tests for Phase 12 legacy verdicts audit."""

from pathlib import Path

from commands.audit_legacy_verdicts import (
    audit_all_legacy_records,
    classify_legacy_row,
    generate_audit_companion_csv,
    generate_audit_markdown_report,
    main,
)


def test_classify_legacy_row_shipped() -> None:
    row = {
        "status": "shipped",
        "lever": "Test Shipped Lever",
        "tried_as": "cand_a",
        "baseline": "champ",
        "result": "gate PASS 3/3",
        "evidence_date": "2026-09-28",
        "revisit_after": "",
        "evidence_path": "path/to/evidence.csv",
    }
    audited = classify_legacy_row(row, 1)
    assert audited.audit_verdict == "pass"
    assert audited.audit_category == "shipped_accepted"
    assert audited.reopening_proposal_status == "none"


def test_classify_legacy_row_dead_fail() -> None:
    row = {
        "status": "dead",
        "lever": "Assist finishing offsets",
        "tried_as": "off_k1800",
        "baseline": "hold_chase",
        "result": "no gain vs goals-only; off_k1800 late -0.54",
        "evidence_date": "2026-09-28",
        "revisit_after": "2027-09-28",
        "evidence_path": "path/to/evidence.csv",
    }
    audited = classify_legacy_row(row, 2)
    assert audited.audit_verdict == "fail"
    assert audited.audit_category == "valid_negative"
    assert audited.reopening_proposal_status == "locked_dead_lever"


def test_classify_legacy_row_dead_defect() -> None:
    row = {
        "status": "dead",
        "lever": "Inert prototype attempt",
        "tried_as": "inert_v1",
        "baseline": "champ",
        "result": "Inert prototype with zero-delta",
        "evidence_date": "2026-10-20",
        "revisit_after": "2027-10-20",
        "evidence_path": "path/to/evidence.csv",
    }
    audited = classify_legacy_row(row, 3)
    assert audited.audit_verdict == "invalid"
    assert audited.audit_category == "execution_defect"
    assert audited.reopening_proposal_status == "locked_dead_lever"


def test_classify_legacy_row_dead_noise() -> None:
    row = {
        "status": "dead",
        "lever": "Player per90 GC log-shrink",
        "tried_as": "a3_test",
        "baseline": "champ",
        "result": "FAIL / noise",
        "evidence_date": "2026-09-28",
        "revisit_after": "2027-09-28",
        "evidence_path": "path/to/evidence.csv",
    }
    audited = classify_legacy_row(row, 4)
    assert audited.audit_verdict == "inconclusive"
    assert audited.audit_category == "unsupported_inference"
    assert audited.reopening_proposal_status == "locked_dead_lever"


def test_audit_all_legacy_records_matches_ledger_counts() -> None:
    ledger_path = Path("docs/research/candidate-ledger/candidate_ledger.csv")
    rows = audit_all_legacy_records(ledger_path)
    assert len(rows) == 104
    # All dead rows must have locked_dead_lever status
    for r in rows:
        if r.status == "dead":
            assert r.reopening_proposal_status == "locked_dead_lever"


def test_generate_audit_companion_artifacts(tmp_path: Path) -> None:
    csv_out = tmp_path / "test_audit.csv"
    md_out = tmp_path / "test_audit.md"

    ledger_path = Path("docs/research/candidate-ledger/candidate_ledger.csv")
    rows = audit_all_legacy_records(ledger_path)

    generate_audit_companion_csv(rows, csv_out)
    generate_audit_markdown_report(rows, md_out)

    assert csv_out.is_file()
    assert md_out.is_file()

    csv_text = csv_out.read_text(encoding="utf-8")
    assert "audit_verdict" in csv_text
    assert "locked_dead_lever" in csv_text

    md_text = md_out.read_text(encoding="utf-8")
    assert "Total Rows Audited**: 104" in md_text


def test_main_cli_execution(tmp_path: Path) -> None:
    csv_out = tmp_path / "cli_audit.csv"
    md_out = tmp_path / "cli_audit.md"

    ret = main(["--output-csv", str(csv_out), "--output-md", str(md_out)])
    assert ret == 0
    assert csv_out.is_file()
    assert md_out.is_file()

from datetime import date
from pathlib import Path

import pandas as pd

ROOT: Path = Path(__file__).resolve().parents[1]
LEDGER: Path = ROOT / "docs/research/candidate-ledger/candidate_ledger.csv"


def _ledger() -> pd.DataFrame:
    return pd.read_csv(LEDGER, dtype=str, keep_default_na=False)


def test_ledger_statuses_and_evidence_exist() -> None:
    df = _ledger()
    assert set(df["status"]) <= {"shipped", "dead", "open"}
    assert not df["lever"].duplicated().any()
    missing = [p for p in df["evidence_path"] if not (ROOT / p).exists()]
    assert missing == []


def test_dead_levers_locked_one_year_from_evidence() -> None:
    dead = _ledger().query("status == 'dead'")
    assert len(dead) > 0
    for _, row in dead.iterrows():
        if row["revisit_after"] == "never":
            continue
        evidence = date.fromisoformat(row["evidence_date"])
        assert date.fromisoformat(row["revisit_after"]) >= evidence.replace(year=evidence.year + 1), row["lever"]


def test_only_dead_levers_carry_revisit_date() -> None:
    df = _ledger()
    assert (df.loc[df["status"] != "dead", "revisit_after"] == "").all()

"""Refresh research-note caches from completed exploration smoke rows."""

from __future__ import annotations

import csv
import argparse
import re
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from backtesting.smoke_diagnostics import DiagnosticStore

TOPIC = Path(__file__).resolve().parent
START = "<!-- exploration-results:start -->"
END = "<!-- exploration-results:end -->"


def evidence_block(all_rows: list[dict[str, str]], source_name: str) -> tuple[str, int]:
    rows_by_identity: dict[tuple[str, ...], dict[str, str]] = {}
    for row in all_rows:
        if row["season"] != "dev" or "[invalid:" in row.get("reasons", ""):
            continue
        if row.get("schema_version") and row.get("execution_status") != "complete":
            continue
        stage = row.get("stage") or ("oracle" if row.get("reasons", "").startswith("tier2_oracle_fail:") else "legacy_integrated_or_minutes")
        identity = row.get("run_id") or f"unknown:{row.get('date', '')}:{row.get('source', '')}"
        key = (row["data_season"], row["champion"], row["variant"], row["gw_range"], stage, identity)
        rows_by_identity[key] = {**row, "stage": stage, "identity": identity}
    rows = list(rows_by_identity.values())
    lines = [
        START, "## Completed development evidence", "",
        f"Generated from [{source_name}]({source_name}); separate season, Champion, variant, range, stage and run identity. Legacy identities unknown; dates/source paths do not certify code versions. Diagnostic screen outcomes hold no promotion or Dead Lever authority. Partial grids do not imply whole-lane verdicts.", "",
    ]
    for row in rows:
        verdict = "SCREEN_PASS" if row["pass"] == "True" else "SCREEN_NOT_PASSED"
        segments = "segments unassessed" if row["stage"] == "oracle" or not row.get("segs") else f"{row['segs']}/3 segments"
        probability = f"{float(row['boot_p_gt0']):.5f}" if row.get("boot_p_gt0") else "unassessed"
        lines.append(
            f"- `{row['variant']}` vs `{row['champion']}`: {verdict}; {row['stage']}; dev {row['data_season']} GW{row['gw_range']}; "
            f"delta {float(row['combined_delta']):+.6f} points/GW; {segments}; "
            f"bootstrap P {probability}; guardrails {row['guardrails_passed']}; identity `{row['identity']}`."
        )
    lines.extend(["", END])
    return "\n".join(lines), len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", type=Path, default=TOPIC / "smoke_results.csv")
    args = parser.parse_args()
    with args.smoke.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    if rows and rows[0].get("schema_version"):
        store = DiagnosticStore(args.smoke)
        rows = store.rows()
        for row in rows:
            store.verify(row)
    block, count = evidence_block(rows, args.smoke.name)
    path = TOPIC / "candidate-ideation.md"
    text = path.read_text(encoding="utf-8")
    if START in text:
        text = re.sub(re.escape(START) + ".*?" + re.escape(END), lambda _: block, text, flags=re.DOTALL)
    else:
        anchor = "## Agent Ideation Review"
        index = text.index(anchor)
        text = text[:index] + block + "\n\n" + text[index:]
    path.write_text(text, encoding="utf-8")
    print(f"Refreshed {count} stage/identity-specific development rows")


if __name__ == "__main__":
    main()

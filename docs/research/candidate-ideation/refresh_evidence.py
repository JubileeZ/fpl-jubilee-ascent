"""Refresh research-note caches from completed exploration smoke rows."""

from __future__ import annotations

import csv
import re
from pathlib import Path

TOPIC = Path(__file__).resolve().parent
START = "<!-- exploration-results:start -->"
END = "<!-- exploration-results:end -->"


def main() -> None:
    with (TOPIC / "smoke_results.csv").open(newline="", encoding="utf-8-sig") as handle:
        rows = [row for row in csv.DictReader(handle) if row["lane"] in {"ext_07", "ext_08", "ext_09", "ext_11", "ext_12"} and row["season"] == "dev"]
    lines = [
        START, "## Completed development evidence", "",
        "Generated from [smoke_results.csv](smoke_results.csv), keyed by `variant`; cached columns `combined_delta`, `segs`, `boot_p_gt0`, `guardrails_passed`, `pass`. Full failed-mechanism reasons retained in companion. Partial grid rows never imply whole-lane verdict.", "",
    ]
    for row in rows:
        verdict = "PASS" if row["pass"] == "True" else "FAIL"
        lines.append(
            f"- `{row['variant']}`: {verdict}; dev {row['data_season']} GW{row['gw_range']}; "
            f"delta {float(row['combined_delta']):+.6f} points/GW; {row['segs']}/3 segments; "
            f"bootstrap P {float(row['boot_p_gt0']):.5f}; guardrails {row['guardrails_passed']}."
        )
    lines.extend(["", END])
    block = "\n".join(lines)
    path = TOPIC / "candidate-ideation.md"
    text = path.read_text(encoding="utf-8")
    if START in text:
        text = re.sub(re.escape(START) + ".*?" + re.escape(END), lambda _: block, text, flags=re.DOTALL)
    else:
        anchor = "## Agent Ideation Review"
        index = text.index(anchor)
        text = text[:index] + block + "\n\n" + text[index:]
    path.write_text(text, encoding="utf-8")
    print(f"Refreshed {len(rows)} completed development rows")


if __name__ == "__main__":
    main()

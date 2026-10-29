"""Generate hypothetical workload costs without running models or solvers."""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCENARIOS: tuple[tuple[str, int, int, int], ...] = (
    ("development_candidate_only", 1, 1, 1),
    ("minimal_two_season_candidate_only", 1, 2, 1),
    ("single_anchor_champion_and_candidate", 2, 2, 1),
    ("three_start_candidate_only", 1, 2, 3),
    ("three_start_champion_and_candidate", 2, 2, 3),
    ("three_start_champion_and_two_candidates", 3, 2, 3),
)
SECONDS_PER_CALL: tuple[int, ...] = (10, 30, 60, 120)
BEGIN = "<!-- workload-estimates:start -->"
END = "<!-- workload-estimates:end -->"


def main() -> None:
    rows: list[dict[str, str | int | float]] = []
    summaries: list[str] = []
    for scenario_id, models, seasons, starts in SCENARIOS:
        calls = models * seasons * starts * 38
        costs: list[str] = []
        for seconds in SECONDS_PER_CALL:
            solver_seconds = calls * seconds
            rows.append({
                "scenario_id": scenario_id,
                "model_count": models,
                "season_count": seasons,
                "start_count": starts,
                "deadlines_per_path": 38,
                "arm_count": 1,
                "iterations_per_deadline": 1,
                "optimizer_calls": calls,
                "assumed_seconds_per_call": seconds,
                "solver_seconds": solver_seconds,
                "solver_minutes": solver_seconds / 60,
            })
            hours, remainder = divmod(solver_seconds, 3600)
            minutes, remaining_seconds = divmod(remainder, 60)
            costs.append(f"{seconds}s/call: {hours}h {minutes:02d}m {remaining_seconds:02d}s")
        summaries.append(f"- `{scenario_id}`: **{calls} calls**; " + "; ".join(costs) + ".")
    companion = ROOT / "workload_scenarios.csv"
    with companion.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    note = ROOT / "backtesting-promotion-foundation.md"
    source = note.read_text(encoding="utf-8")
    prefix, separator, remainder = source.partition(BEGIN)
    _, closing, suffix = remainder.partition(END)
    if not separator or not closing:
        raise ValueError("Research note missing workload cache markers")
    note.write_text(prefix + BEGIN + "\n" + "\n".join(summaries) + "\n" + END + suffix, encoding="utf-8")
    print(f"Generated {len(rows)} hypothetical workload rows: {companion}")


if __name__ == "__main__":
    main()

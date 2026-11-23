"""Score EXT-38 xG inputs from strict as-of forecasts against settled fixture xG."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
import pandas as pd

from prototypes import PROTOTYPES, TwoPartFixtureXgChallengerModel
from run_deadline_research import ARCHIVE, KEYS, load_staged, forecast

XG_COLUMNS = ("champion_xg", "single_mean_xg", "candidate_xg")
OUTFIELD = (2, 3, 4)


def attacked_quartile(past: pd.DataFrame, position: pd.Series) -> pd.Index:
    """Identify the issue-time upper xG/90 quartile in each official position."""
    minutes = pd.to_numeric(past["minutes"], errors="coerce")
    xg = pd.to_numeric(past["expected_goals"], errors="coerce")
    valid = np.isfinite(minutes) & minutes.gt(0.0) & np.isfinite(xg) & xg.ge(0.0)
    totals = (
        pd.DataFrame({"player_id": past["player_id"], "minutes": minutes, "xg": xg})
        .loc[valid]
        .groupby("player_id")[["minutes", "xg"]]
        .sum()
    )
    totals = totals[totals["minutes"].ge(360.0)].assign(position_id=position)
    totals = totals[totals["position_id"].isin(OUTFIELD)]
    rates = 90.0 * totals["xg"] / totals["minutes"]
    boundary = rates.groupby(totals["position_id"]).transform("quantile", q=0.75)
    return rates.index[rates.ge(boundary)]


def settled_labels(archive: Path, *, announce: bool = False) -> pd.DataFrame:
    labels = pd.read_parquet(
        archive / "player_performances.parquet",
        columns=[*KEYS, "expected_goals", "minutes"],
    )
    if labels.duplicated(KEYS).any():
        raise ValueError("Settled xG requires unique player/Gameweek/fixture labels")
    labels = labels.rename(
        columns={"expected_goals": "actual_xg", "minutes": "actual_minutes"}
    )
    for col in ("actual_xg", "actual_minutes"):
        labels[col] = pd.to_numeric(labels[col], errors="coerce")
    if announce:
        print(
            f"Settled source: {len(labels)} rows; fields={list(labels.columns)}; "
            f"sample={labels.iloc[0].to_dict()}",
            flush=True,
        )
    return labels


def issue_xg(
    work: Path,
    out: Path,
    constructor: type[TwoPartFixtureXgChallengerModel],
    seed: Path,
    gw: int,
    deadline: str,
    labels: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, int]]:
    model = constructor()
    model.capture_xg = True
    forecast(work, out, lambda: model, seed, gw, deadline)
    projections = pd.read_parquet(out / "projections" / f"gw{gw:02d}.parquet")
    values = model.xg_diagnostics(projections)
    stage = work / "verified_inputs" / f"gw{gw:02d}"
    position = pd.read_parquet(
        stage / "market.parquet", columns=["player_id", "position_id"]
    ).set_index("player_id")["position_id"]
    past = pd.read_parquet(
        stage / "player_performances.parquet",
        columns=[*KEYS, "minutes", "expected_goals"],
    )
    if not past["gameweek_id"].lt(gw).all() or past.duplicated(KEYS).any():
        raise ValueError(f"Invalid pre-deadline input keys at GW{gw}")
    high_attack = attacked_quartile(past, position)
    values["position_id"] = values["player_id"].map(position)
    values = values[values["position_id"].isin(OUTFIELD)].copy()
    values["high_attack"] = values["player_id"].isin(high_attack)
    values["issue_gameweek"] = gw
    values["lead"] = values["gameweek_id"] - gw
    if not np.isfinite(values[list(XG_COLUMNS)].to_numpy()).all():
        raise ValueError(f"Nonfinite forecast input at GW{gw}")

    # Settle only after forecasts and the pre-deadline cohort have been recorded.
    settled = values.merge(
        labels, on=KEYS, how="left", validate="one_to_one", indicator=True
    )
    matched = settled["_merge"].eq("both")
    actual_xg, actual_minutes = settled["actual_xg"], settled["actual_minutes"]
    valid = (
        matched
        & np.isfinite(actual_xg)
        & actual_xg.ge(0.0)
        & np.isfinite(actual_minutes)
        & actual_minutes.ge(0.0)
    )
    counts = {
        "issue_gameweek": gw,
        "issued_outfield_rows": len(values),
        "unmatched_rows": int((~matched).sum()),
        "invalid_matched_rows": int((matched & ~valid).sum()),
        "scored_rows": int(valid.sum()),
        "scored_dnp_rows": int((valid & actual_minutes.eq(0.0)).sum()),
    }
    return settled.loc[valid].drop(columns="_merge"), counts


def summarize(variant: str, rows: pd.DataFrame) -> pd.DataFrame:
    metrics: list[dict[str, str | int | float]] = []
    for cohort, cohort_rows in (
        ("all", rows),
        ("high_attack", rows[rows["high_attack"]]),
    ):
        groups = [("all", "all", cohort_rows)]
        groups.extend(
            (int(lead), "all", group) for lead, group in cohort_rows.groupby("lead")
        )
        groups.extend(
            ("all", int(pos), group)
            for pos, group in cohort_rows.groupby("position_id")
        )
        groups.extend(
            (int(lead), int(pos), group)
            for (lead, pos), group in cohort_rows.groupby(["lead", "position_id"])
        )
        for lead, position, group in groups:
            if group.empty:
                continue
            for model in XG_COLUMNS:
                error = group[model] - group["actual_xg"]
                metrics.append(
                    {
                        "variant": variant,
                        "forecast_input": model,
                        "cohort": cohort,
                        "lead": lead,
                        "position_id": position,
                        "rows": len(group),
                        "mse": float(error.pow(2).mean()),
                        "signed_bias": float(error.mean()),
                    }
                )
    return pd.DataFrame(metrics)


def save_issue(
    work: Path,
    run: Path,
    variant: str,
    seed: Path,
    gw: int,
    deadline: str,
) -> dict[str, int | str]:
    """Persist one issue's matches and a digest-bound coverage record."""
    variant_dir = run / variant
    matches = variant_dir / "issues" / f"gw{gw:02d}.parquet"
    coverage = matches.with_suffix(".json")
    if coverage.is_file():
        record = json.loads(coverage.read_text())
        if (
            record["variant"] != variant
            or record["issue_gameweek"] != gw
            or record["matches_sha256"] != sha256(matches.read_bytes()).hexdigest()
        ):
            raise ValueError(f"Mismatched cached {variant} GW{gw} xG diagnostic")
        return record

    rows, counts = issue_xg(
        work,
        variant_dir,
        PROTOTYPES[variant],
        seed,
        gw,
        deadline,
        settled_labels(ARCHIVE),
    )
    matches.parent.mkdir(parents=True, exist_ok=True)
    rows.to_parquet(matches, index=False)
    record = {
        "variant": variant,
        **counts,
        "matches_sha256": sha256(matches.read_bytes()).hexdigest(),
    }
    staging = coverage.with_suffix(".tmp")
    staging.write_text(json.dumps(record) + "\n")
    staging.replace(coverage)
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()
    if not 1 <= args.workers <= 4:
        parser.error("--workers must be 1–4")
    work, out = args.work.resolve(), args.out.resolve()
    manifest, seed, protocol = load_staged(work)
    settled_labels(ARCHIVE, announce=True)
    prototype_source = Path(__file__).with_name("prototypes.py")
    run_identity = sha256(
        protocol.encode() + prototype_source.read_bytes() + Path(__file__).read_bytes()
    ).hexdigest()
    run = out / run_identity
    origins = [
        (int(origin["gw"]), origin["deadline_utc"]) for origin in manifest["origins"]
    ]
    trace = [
        (work, run, variant, seed, gw, deadline)
        for gw, deadline in origins
        for variant in PROTOTYPES
    ]
    if args.workers == 1:
        quality = [save_issue(*task) for task in trace]
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            quality = [
                job.result()
                for job in as_completed(
                    [pool.submit(save_issue, *task) for task in trace]
                )
            ]
    quality.sort(key=lambda row: (str(row["variant"]), int(row["issue_gameweek"])))
    results: list[pd.DataFrame] = []
    for variant in PROTOTYPES:
        variant_dir = run / variant
        matched = pd.concat(
            [
                pd.read_parquet(variant_dir / "issues" / f"gw{gw:02d}.parquet")
                for gw, _ in origins
            ],
            ignore_index=True,
        )
        matched.to_parquet(variant_dir / "settled_xg_matches.parquet", index=False)
        results.append(summarize(variant, matched))

    summary = pd.concat(results, ignore_index=True)
    summary.to_csv(out / "xg_comparison.csv", index=False)
    pd.DataFrame(quality).to_csv(out / "xg_match_coverage.csv", index=False)
    (out / "diagnostic_identity.txt").write_text(run_identity + "\n")
    print(
        summary.query(
            "cohort == 'all' and lead == 'all' and position_id == 'all'"
        ).to_string(index=False)
    )


if __name__ == "__main__":
    main()

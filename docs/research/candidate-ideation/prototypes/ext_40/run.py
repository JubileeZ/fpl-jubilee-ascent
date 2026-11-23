"""Run the preregistered EXT-40 historical GW1–4 development experiment."""

from __future__ import annotations

import argparse
from datetime import datetime
from functools import partial
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd

from backtesting.empirical_mirrors import load_empirical_manifest_bundle
from backtesting.ownership_anchor import UniverseSchema, solve_ownership_anchor
from backtesting.rolling_replay import (
    DEFAULT_CERTIFIED_TIME_LIMIT_SECONDS,
    QualityPolicy,
    run_rolling_replay,
)
from backtesting.season_rules import Chip, load_season_lifecycle
from commands.run_stage_a_and_b import CONFIG_ROOT, REPO, _outcomes_for_gw
from evaluate_deadline_formation_xi import lineup
from features.availability_snapshots import resolve_latest_snapshot
from features.builder import completed_performance_rows, history_before_target
import historical_replay_inputs
from historical_replay_inputs import SEASON, _checked_bytes
from models.scoring_matrix import event_points
from prototypes.ext_40.panel import (
    IssueContext,
    SourcePanel,
    annotate_history,
    build_predictors,
    count_targets,
    eligible_issue_history,
    issue_fixture_rows,
    load_source_panel,
    performance_rows,
    roster_identity,
    training_examples,
    unique_season_identity,
)
from prototypes.ext_40.prototypes import (
    COUNT_COLUMNS,
    EVENT,
    GRID,
    KEYS,
    OUTFIELD,
    POSITIONS,
    Component,
    Mode,
    fit_count_head,
    score_fixture_component,
)
from run_s1_replay import (
    champion_factory,
    core_closure_hash,
    forecast,
    model_version_hash,
    s1_protocol_hash,
)

ISSUES = range(1, 5)
HORIZON = 6
CHAMPION = "champion"
STRATEGY_MARKET_COLUMNS = [
    "player_id",
    "position_id",
    "club_id",
    "now_cost",
    "purchase_eligible",
]


def variant_name(component: Component, penalty: float, mode: Mode) -> str:
    return f"ext_40_{component}_l{round(100 * penalty):02d}_{mode}"


VARIANTS = {variant_name(*item): item for item in GRID}


def source_panel(work: Path, manifest: dict[str, Any]) -> SourcePanel:
    lifecycle = load_season_lifecycle()
    season = lifecycle.season_for_role("development")
    seed = lifecycle.seasons[season].prior_seed
    if manifest["season"] != season or seed is None:
        raise ValueError(
            "EXT-40 runner requires the lifecycle development and its authorized seed"
        )
    config_suffix = seed.replace("-", "_")
    seed_manifest = CONFIG_ROOT / f"seed_manifest_{config_suffix}.json"
    # Different official FPL assist rules warrant a process-only source bridge.
    source = load_source_panel(
        work / "mirror",
        CONFIG_ROOT / f"dev_mirror_{config_suffix}_manifest.json",
        REPO / "data/archive" / seed / "processed",
        seed_manifest,
        soft_assists=True,
    )
    return source


def _issue_input(
    work: Path,
    manifest: dict[str, Any],
    origin: dict[str, Any],
    source: SourcePanel,
    previous: dict[int, dict[Component, pd.DataFrame]],
) -> tuple[IssueContext, pd.DataFrame, pd.DataFrame]:
    gw = int(origin["gw"])
    deadline = datetime.fromisoformat(origin["deadline_utc"])
    directory = work / "verified_inputs" / f"gw{gw:02d}"
    if not origin["origin_admitted"]:
        raise ValueError(f"Unadmitted development issue GW{gw}")
    if source.last_available >= deadline:
        raise ValueError(f"Source labels are not published before development GW{gw}")
    snapshot = resolve_latest_snapshot(
        directory / "snapshots", SEASON, gw, deadline.isoformat()
    )
    if (
        snapshot is None
        or datetime.fromisoformat(snapshot["metadata"]["captured_at"]) >= deadline
    ):
        raise ValueError(f"Missing pre-deadline availability at GW{gw}")
    versions = snapshot["metadata"]["source_endpoint_versions"]
    if (
        versions["fixtures_sha256"] != origin["fixtures"]["blob_sha256"]
        or versions["bootstrap_sha256"] != origin["bootstrap"]["blob_sha256"]
    ):
        raise ValueError(f"Wrong development fixture or roster receipt at GW{gw}")
    market = pd.read_parquet(directory / "market.parquet")
    bootstrap = origin["bootstrap"]
    raw_path = work / "mirror" / bootstrap["local_relpath"]
    _checked_bytes(raw_path, bootstrap["blob_sha256"])
    verified_market, _ = historical_replay_inputs._bootstrap_players_and_clubs(
        raw_path, capture_upper=datetime.fromisoformat(bootstrap["capture_upper_utc"])
    )
    pd.testing.assert_frame_equal(
        market.reset_index(drop=True),
        verified_market.loc[verified_market["position_id"].between(1, 4)].reset_index(
            drop=True
        ),
    )
    history = pd.read_parquet(directory / "player_performances.parquet")
    if gw == 1 and not history.empty:
        raise ValueError("Opening issue has current-season labels")
    receipt_digest = "opening_empty"
    if gw > 1:
        previous_receipt = manifest["origins"][gw - 2]["settled_outcomes"]
        receipt_digest = previous_receipt["blob_sha256"]
        historical_replay_inputs.MIRROR_ROOT = work / "mirror"
        strict = historical_replay_inputs._admitted_history(gw, manifest, history)
        strict = completed_performance_rows(
            history_before_target(strict, gw, deadline.isoformat(), True),
            snapshot["fixtures"],
        )
        pd.testing.assert_frame_equal(
            history.reset_index(drop=True), strict.reset_index(drop=True)
        )
    return (
        IssueContext(
            SEASON,
            gw,
            deadline,
            source.digest,
            receipt_digest,
            snapshot["fixtures"],
            performance_rows(history),
            previous.copy(),
        ),
        market,
        history,
    )


def _load_outcomes() -> pd.DataFrame:
    labels = pd.read_parquet(
        REPO / "data/archive" / SEASON / "processed/player_performances.parquet",
        columns=KEYS + ["goals_scored", "assists", "total_points", "minutes"],
    )
    labels = labels.loc[labels["gameweek_id"].isin(ISSUES)].copy()
    if labels.duplicated(KEYS).any() or not labels["minutes"].ge(0).all():
        raise ValueError("Invalid native evaluation fixture keys or minutes")
    for _, target in EVENT.values():
        values = labels[target].dropna().to_numpy(dtype=float)
        if (
            not np.isfinite(values).all()
            or (values < 0).any()
            or not np.equal(values, np.floor(values)).all()
        ):
            raise ValueError(f"Invalid native evaluation labels for {target}")
    return labels


def _metrics(
    issued: pd.DataFrame,
    actual: pd.DataFrame,
    result: pd.DataFrame,
    diagnostic: pd.DataFrame,
    component: Component,
    gw: int,
    name: str,
    champion_points: pd.Series,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    _, target = EVENT[component]
    column = f"xp_{component}"
    rows = issued[KEYS + ["position_id"]].merge(
        result[KEYS + [column]], on=KEYS, validate="one_to_one"
    )
    rows = rows.merge(diagnostic, on=KEYS, validate="one_to_one")
    rows["champion_points"] = champion_points.to_numpy()
    primary = rows.loc[
        rows["gameweek_id"].eq(gw)
        & rows["fixture_id"].gt(0)
        & rows["position_id"].isin(OUTFIELD)
    ]
    common = primary.merge(
        actual[KEYS + [target, "minutes"]], on=KEYS, validate="one_to_one"
    ).dropna(subset=[target, "minutes"])
    # Include recorded zero-minute player-fixtures and distinguish any zero
    # probability on the observed class from its finite-clipped diagnostic.
    counts = np.minimum(common[target].to_numpy(dtype=int), 3)
    probabilities = common[COUNT_COLUMNS].to_numpy(dtype=float)[
        np.arange(len(common)), counts
    ]
    with np.errstate(divide="ignore"):
        losses = -np.log(probabilities)
    clipped_losses = -np.log(np.maximum(probabilities, np.finfo(float).tiny))
    truth = [
        event_points(component, POSITIONS[p], y, rules_version=SEASON)
        for p, y in zip(common["position_id"], common[target], strict=True)
    ]
    error = common[column] - truth
    metric = {
        "component": component,
        "arm": name,
        "gameweek": gw,
        "paired": len(common),
        "played": int(common["minutes"].gt(0).sum()),
        "zero_minute": int(common["minutes"].eq(0).sum()),
        "unmatched": len(primary) - len(common),
        "error_sum": float(error.sum()),
        "squared_error_sum": float(np.square(error).sum()),
        "log_loss_sum": float(losses.sum()),
        "clipped_log_loss_sum": float(clipped_losses.sum()),
        "zero_probability_observations": int((probabilities == 0).sum()),
        "changed_component_rows": int(
            (primary[column] - primary["champion_points"]).abs().gt(1e-9).sum()
        ),
    }
    by_lead = []
    for target_gw, part in rows.groupby("gameweek_id"):
        support = part["support"].value_counts().to_dict()
        by_lead.append(
            {
                "component": component,
                "arm": name,
                "gameweek": gw,
                "lead": target_gw - gw,
                "rows": len(part),
                **support,
            }
        )
    return metric, by_lead


def _staged_champion(work: Path, manifest: dict[str, Any], baseline: Path) -> None:
    _, factory, _ = champion_factory()
    seed = work / "seed/seed_2024-25"
    for origin in manifest["origins"][: len(ISSUES)]:
        gw = origin["gw"]
        forecast(work, baseline, factory, seed, gw, origin["deadline_utc"])


def _experiment_identity(work: Path, baseline: Path) -> dict[str, Any]:
    files = [
        Path(__file__).with_name(filename)
        for filename in ("prototypes.py", "panel.py", "run.py")
    ]
    recipe = sha256(b"".join(path.read_bytes() for path in files)).hexdigest()
    issues = {}
    for gw in ISSUES:
        key = f"gw{gw:02d}"
        base = work / "verified_inputs" / key
        issue_files = [
            base / "market.parquet",
            base / "player_performances.parquet",
            *sorted(base.glob("snapshots/**/*.*")),
        ]
        issue_hash = sha256(
            b"".join(sha256(path.read_bytes()).digest() for path in issue_files)
        ).hexdigest()
        issues[key] = {
            "staged_inputs": issue_hash,
            "champion_forecast": sha256(
                (baseline / "projections" / f"{key}.parquet").read_bytes()
            ).hexdigest(),
        }
    return {
        "recipe": recipe,
        "core": core_closure_hash(),
        "s1": s1_protocol_hash(work / "seed/seed_2024-25"),
        "issues": issues,
    }


def run_forecasts(work: Path, manifest: dict[str, Any], baseline: Path) -> None:
    source = source_panel(work, manifest)
    results = work / "attack"
    results.mkdir(parents=True, exist_ok=True)
    source.inventory.to_csv(results / "source_origins.csv", index=False)
    prior_targets = {
        component: count_targets(rows, soft=(component == "assists"))
        for component, rows in source.training.items()
    }
    coverage = []
    for component, training in source.training.items():
        for position in POSITIONS:
            subset = training["position_id"].eq(position)
            coverage.append(
                {
                    "component": component,
                    "position_id": position,
                    "rows": int(subset.sum()),
                    "weeks": training.loc[subset, "gameweek_id"].nunique(),
                    **dict(
                        zip(
                            COUNT_COLUMNS,
                            prior_targets[component][subset].sum(axis=0),
                            strict=True,
                        )
                    ),
                }
            )
    pd.DataFrame(coverage).to_csv(results / "source_category_support.csv", index=False)
    priors = {
        (component, penalty, mode): fit_count_head(
            source.training[component],
            prior_targets[component],
            penalty=penalty,
            dynamic=(mode != "static"),
        )
        for component, penalty, mode in GRID
        if mode != "prior"
    }
    _staged_champion(work, manifest, baseline)
    actual = _load_outcomes()
    records: dict[int, dict[Component, pd.DataFrame]] = {}
    roster_prefix = []
    weekly = []
    by_lead = []
    provenance = []
    for origin in manifest["origins"][: len(ISSUES)]:
        gw = origin["gw"]
        context, market, raw_history = _issue_input(
            work, manifest, origin, source, records
        )
        roster_prefix.append(roster_identity(market).assign(gameweek_id=gw))
        dated = unique_season_identity(pd.concat(roster_prefix, ignore_index=True))
        prior_history = eligible_issue_history(context)
        current = annotate_history(prior_history, dated, 38)
        issued = issue_fixture_rows(
            dated.loc[dated["gameweek_id"].eq(gw)], context.fixtures, gw, HORIZON
        )
        base = pd.read_parquet(baseline / "projections" / f"gw{gw:02d}.parquet")
        actual_gw = actual.loc[actual["gameweek_id"].eq(gw)]
        settled = actual_gw.groupby("player_id", as_index=False)[
            ["total_points", "minutes"]
        ].sum()
        champion_xi = lineup(market, base, settled, gw)
        current_labels = {}
        records[gw] = {}
        for component in EVENT:
            predictors = build_predictors(
                issued, source.carry, current, 38 + gw, component
            )
            records[gw][component] = predictors.loc[
                predictors["gameweek_id"].eq(gw)
            ].copy()
            previous = [parts[component] for parts in context.previous_issues.values()]
            prior_predictions = (
                pd.concat(previous, ignore_index=True)
                if previous
                else predictors.iloc[:0]
            )
            labels = training_examples(
                prior_predictions.dropna(subset=["rate"]),
                prior_history,
                component,
                soft=False,
            )
            current_labels[f"{component}_current_label_rows"] = len(labels)
            current_labels[f"{component}_current_label_gws"] = labels[
                "gameweek_id"
            ].nunique()
            targets = count_targets(labels, soft=False)
            positions = frozenset(source.training[component]["position_id"].astype(int))
            designs = [(CHAMPION, None, None)]
            for name, (target_component, penalty, mode) in VARIANTS.items():
                if target_component == component:
                    prior = priors[
                        component, penalty, "dynamic" if mode == "prior" else mode
                    ]
                    fitted = (
                        prior
                        if mode == "prior"
                        else fit_count_head(
                            labels,
                            targets,
                            penalty=penalty,
                            dynamic=(mode != "static"),
                            prior=prior,
                        )
                    )
                    designs.append((name, mode, fitted))
            for name, mode, coefficients in designs:
                result, diag = score_fixture_component(
                    base,
                    predictors,
                    component,
                    coefficients,
                    SEASON,
                    dynamic=(mode != "static"),
                    source_positions=positions,
                )
                champion_points = issued[KEYS].merge(
                    base[KEYS + [f"xp_{component}"]], on=KEYS, validate="one_to_one"
                )[f"xp_{component}"]
                metric, coverage_rows = _metrics(
                    issued,
                    actual_gw,
                    result,
                    diag,
                    component,
                    gw,
                    name,
                    champion_points,
                )
                if name == CHAMPION:
                    xi = champion_xi
                else:
                    out = results / name
                    out.mkdir(exist_ok=True)
                    forecast_path = out / f"gw{gw:02d}.parquet"
                    result.to_parquet(forecast_path, index=False)
                    diag.to_parquet(out / f"gw{gw:02d}_counts.parquet", index=False)
                    xi = lineup(market, result, settled, gw)
                    metric["forecast_sha256"] = sha256(
                        forecast_path.read_bytes()
                    ).hexdigest()
                metric["credited_xi_points"] = xi["credited_xi_points"]
                metric["credited_xi_delta"] = int(xi["credited_xi_points"]) - int(
                    champion_xi["credited_xi_points"]
                )
                metric["xi_changed"] = set(
                    cast(tuple[int, ...], xi["starting_ids"])
                ) != set(cast(tuple[int, ...], champion_xi["starting_ids"]))
                weekly.append(metric)
                by_lead.extend(coverage_rows)
        provenance.append(
            {
                "gameweek": gw,
                "deadline": context.cutoff.isoformat(),
                "source_panel_digest": context.source_digest,
                "settled_receipt_digest": context.receipt_digest,
                "history_rows": len(raw_history),
                **current_labels,
            }
        )
        print(f"EXT-40 forecasts evaluated at GW{gw}", flush=True)
    weekly_frame = pd.DataFrame(weekly)
    weekly_frame.to_csv(results / "by_issue.csv", index=False)
    pd.DataFrame(by_lead).fillna(0).to_csv(
        results / "fixture_lead_coverage.csv", index=False
    )
    pd.DataFrame(provenance).to_csv(results / "issue_provenance.csv", index=False)
    pooled = weekly_frame.groupby(["component", "arm"], as_index=False)[
        [
            "paired",
            "squared_error_sum",
            "error_sum",
            "log_loss_sum",
            "clipped_log_loss_sum",
            "zero_probability_observations",
            "credited_xi_points",
            "credited_xi_delta",
            "xi_changed",
        ]
    ].sum()
    pooled["component_mse"] = pooled["squared_error_sum"] / pooled["paired"]
    pooled["signed_bias"] = pooled["error_sum"] / pooled["paired"]
    pooled["categorical_log_loss"] = pooled["log_loss_sum"] / pooled["paired"]
    pooled["clipped_categorical_log_loss"] = (
        pooled["clipped_log_loss_sum"] / pooled["paired"]
    )
    gw1 = weekly_frame.loc[
        weekly_frame["gameweek"].eq(1), ["component", "arm", "changed_component_rows"]
    ]
    pooled = pooled.merge(
        gw1.rename(columns={"changed_component_rows": "gw1_changed_rows"}),
        on=["component", "arm"],
        validate="one_to_one",
    )
    indices = pooled.set_index(["component", "arm"])["component_mse"]
    for name, (component, penalty, mode) in VARIANTS.items():
        if mode == "dynamic":
            row = pooled["arm"].eq(name)
            pooled.loc[row, "mse_delta_vs_champion"] = (
                indices[component, name] - indices[component, CHAMPION]
            )
            pooled.loc[row, "mse_delta_vs_static"] = (
                indices[component, name]
                - indices[component, variant_name(component, penalty, "static")]
            )
    pooled.to_csv(results / "summary.csv", index=False)
    identity = _experiment_identity(work, baseline)
    identity["source_panel"] = source.digest
    identity["bound_reports"] = {
        name: sha256((results / name).read_bytes()).hexdigest()
        for name in (
            "issue_provenance.csv",
            "by_issue.csv",
            "summary.csv",
            "source_origins.csv",
            "source_category_support.csv",
        )
    }
    (results / "run_identity.json").write_text(
        json.dumps(identity, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(pooled.to_string(index=False), flush=True)


def run_replay(
    work: Path, manifest: dict[str, Any], variant: str, baseline: Path
) -> None:
    if variant not in VARIANTS:
        raise ValueError(f"Unregistered EXT-40 arm: {variant}")
    attack = work / "attack"
    forecasts = attack / variant
    anchor = solve_ownership_anchor(
        pd.read_parquet(work / "verified_inputs/gw01/market.parquet"),
        SEASON,
        gameweek=1,
        anchor_type="opening",
        schema=UniverseSchema(eligibility_col="purchase_eligible"),
    )
    calendar = tuple(
        (row["gameweek"], cast(Chip, row["chip"]))
        for row in manifest["shared_chip_calendar"]
    )
    raw_identity = (attack / "run_identity.json").read_bytes()
    identity = json.loads(raw_identity)
    actual_identity = _experiment_identity(work, baseline)
    if {key: identity[key] for key in actual_identity} != actual_identity:
        raise ValueError(
            "EXT-40 replay recipe, baseline or issue inputs diverge from forecast generation"
        )
    for name, digest in identity["bound_reports"].items():
        _checked_bytes(attack / name, digest)
    protocol = sha256(raw_identity).hexdigest()
    digest = model_version_hash(variant, identity["recipe"], identity["core"])
    out = attack / "replays" / f"{variant}-{digest[:8]}-{protocol[:8]}"
    recorded_points = pd.read_csv(attack / "by_issue.csv").set_index(
        ["arm", "gameweek"]
    )["forecast_sha256"]

    def forecaster(gw: int, _state: object) -> pd.DataFrame:
        path = forecasts / f"gw{gw:02d}.parquet"
        _checked_bytes(path, recorded_points[variant, gw])
        projected = pd.read_parquet(path)
        reference = pd.read_parquet(baseline / "projections" / f"gw{gw:02d}.parquet")
        pd.testing.assert_frame_equal(
            projected[KEYS + ["projected_minutes"]],
            reference[KEYS + ["projected_minutes"]],
        )
        by_player_gw = projected.groupby(["player_id", "gameweek_id"])[
            ["projected_points", "projected_minutes"]
        ].sum()
        market = pd.read_parquet(
            work / "verified_inputs" / f"gw{gw:02d}" / "market.parquet",
            columns=STRATEGY_MARKET_COLUMNS,
        )
        for target in range(gw, gw + HORIZON):
            aggregate = by_player_gw.xs(target, level="gameweek_id")
            market[f"{target}_Pts"] = market["player_id"].map(
                aggregate["projected_points"]
            )
            market[f"{target}_xMins"] = market["player_id"].map(
                aggregate["projected_minutes"]
            )
        return market

    trajectory = run_rolling_replay(
        variant,
        SEASON,
        anchor,
        forecaster,
        partial(_outcomes_for_gw, SEASON),
        horizon=HORIZON,
        end_gw=ISSUES.stop - 1,
        chip_calendar=calendar,
        policy=QualityPolicy(
            mode="certified",
            target_gap=0.0,
            time_limit_seconds=DEFAULT_CERTIFIED_TIME_LIMIT_SECONDS,
        ),
        checkpoint_dir=out,
        model_version_hash=digest,
        protocol_hash=protocol,
    )
    total = trajectory.audit_reconstructed_net_score()
    if len(trajectory.records) != len(ISSUES) or any(
        record.execution_status != "SUCCESS" for record in trajectory.records
    ):
        raise ValueError("EXT-40 trajectory did not complete the certified prefix")
    rows = []
    for record in trajectory.records:
        decision = record.decision
        if decision is None:
            raise ValueError("Certified trajectory has no applied decision")
        rows.append(
            {
                "arm": variant,
                "gameweek": record.deadline,
                "gross": record.total_gross_points,
                "hits": record.hit_penalty,
                "net": record.net_points,
                "anchor_id": anchor.anchor_id,
                "captain": decision.lineup.captain,
                "starters": json.dumps(decision.lineup.starters),
                "bench": json.dumps(decision.lineup.bench),
                "transfers": json.dumps(
                    [(sold, bought.player_id) for sold, bought in decision.transfers]
                ),
                "forecast_hash": record.forecast_hash,
                "checkpoint_id": record.checkpoint_id,
            }
        )
    pd.DataFrame(rows).to_csv(out / "decisions.csv", index=False)
    print(f"{variant} certified GW1–4 net {total} in {out}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("work", type=Path)
    parser.add_argument("--champion-dir", type=Path)
    parser.add_argument("--replay", choices=tuple(VARIANTS))
    args = parser.parse_args()
    work = args.work.resolve()
    baseline = args.champion_dir or work / "attack_champion"
    manifest = json.loads(
        (CONFIG_ROOT / "dev_mirror_2025_26_manifest.json").read_bytes()
    )
    if args.replay is None:
        load_empirical_manifest_bundle(
            CONFIG_ROOT / "dev_mirror_2025_26_manifest.json",
            quarantine_root=work / "mirror",
            prefix_end_gw=ISSUES.stop - 1,
            require_admitted=True,
        )
        run_forecasts(work, manifest, baseline)
    else:
        run_replay(work, manifest, args.replay, baseline)


if __name__ == "__main__":
    main()

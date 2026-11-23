"""Run fixed EXT-41 comparisons on admitted S-1 development issues."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, replace
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, cast

import numpy as np
import pandas as pd

from backtesting.empirical_mirrors import load_empirical_manifest_bundle
from backtesting.forecast_export import REQUIRED_COMPONENTS, validate_components
from evaluate_deadline_formation_xi import lineup
from features.builder import completed_performance_rows, history_before_target
import historical_replay_inputs
from prototypes.ext_40.panel import (
    IssueContext,
    SourcePanel,
    annotate_history,
    build_predictors,
    count_targets,
    eligible_issue_history,
    issue_fixture_rows,
    roster_identity,
    training_examples,
    unique_season_identity,
)
from prototypes.ext_40.prototypes import EVENT, KEYS, OUTFIELD, Component, FloatArray
from prototypes.ext_40.prototypes import fit_count_head, score_fixture_component
from prototypes.ext_40.run import (
    CHAMPION,
    CONFIG_ROOT,
    HORIZON,
    ISSUES,
    REPO,
    SEASON,
    _experiment_identity,
    _issue_input,
    _metrics,
    _staged_champion,
    source_panel,
    variant_name,
)
from prototypes.ext_41.prototypes import (
    ARMS,
    PENALTY,
    Arm,
    ChampionFeatureScale,
    arm_features,
    attach_champion_components,
)
from run_s1_replay import champion_factory

TOPIC = Path(__file__).resolve().parents[2]
SOURCE_ONLY = "c_source"


@dataclass(frozen=True)
class Issued:
    gw: int
    market: pd.DataFrame
    fixtures: pd.DataFrame
    champion: pd.DataFrame
    champion_digest: str
    market_digest: str
    forecasts: dict[tuple[Component, str], tuple[Path, pd.DataFrame]]


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _source_examples(
    work: Path, source: SourcePanel
) -> tuple[dict[Component, pd.DataFrame], dict[str, object]]:
    location = work / "ext41_source"
    coverage_path = location / "coverage.csv"
    coverage = pd.read_csv(coverage_path, keep_default_na=False)
    retained = pd.read_csv(TOPIC / "ext41-source-coverage.csv", keep_default_na=False)
    stable = list(
        retained.columns.difference(["forecast_sha256", "model_sha256"], sort=False)
    )
    pd.testing.assert_frame_equal(coverage[stable], retained[stable], check_exact=True)
    champion, _, model_digest = champion_factory()
    if (
        not coverage["champion"].eq(champion).all()
        or not coverage["model_sha256"].eq(model_digest).all()
    ):
        raise ValueError(
            "Source Champion identity differs from the configured comparator"
        )
    model_bytes = (REPO / "models" / f"{champion}.py").read_bytes()
    canonical = model_bytes.replace(b"\r\n", b"\n")
    platform_digests = {
        sha256(canonical).hexdigest(),
        sha256(canonical.replace(b"\n", b"\r\n")).hexdigest(),
    }
    if not retained["model_sha256"].isin(platform_digests).all():
        raise ValueError("Original source Champion code differs from fresh preflight")
    forecasts = {}
    examples: dict[Component, list[pd.DataFrame]] = {
        component: [] for component in EVENT
    }
    for row in coverage.to_dict(orient="records"):
        gw = int(row["gameweek"])
        if any(row[f"{component}_examples"] for component in EVENT):
            path = location / "projections" / f"gw{gw:02d}.parquet"
            digest = _digest(path)
            if digest != row["forecast_sha256"]:
                raise ValueError(f"Source Champion vector digest mismatch at GW{gw}")
            original = pd.read_parquet(path)
            validate_components(original, source.season)
            lead_zero = original.loc[
                original["gameweek_id"].eq(gw) & original["fixture_id"].gt(0)
            ]
            forecasts[f"gw{gw:02d}"] = digest
        else:
            lead_zero = pd.DataFrame(columns=[*KEYS, *REQUIRED_COMPONENTS])
        for component, training in source.training.items():
            expected = training.loc[training["gameweek_id"].eq(gw)]
            if (
                len(expected) != row[f"{component}_examples"]
                or len(expected) != row[f"{component}_matched"]
            ):
                raise ValueError(f"Wrong {component} source cohort at GW{gw}")
            if not expected.empty:
                examples[component].append(
                    attach_champion_components(expected, lead_zero, exact=False)
                )
    return (
        {
            component: pd.concat(parts, ignore_index=True)
            for component, parts in examples.items()
        },
        {"coverage_sha256": _digest(coverage_path), "champion_forecasts": forecasts},
    )


def _verify_label_boundary(
    context: IssueContext, manifest: dict[str, Any], raw: pd.DataFrame
) -> None:
    """Perturb target/later rows in the local frame and verify receipt isolation."""
    gw = context.gameweek
    exemplar = raw.iloc[:1]
    if exemplar.empty:
        exemplar = pd.DataFrame([dict.fromkeys(raw.columns, 0)]).astype(
            raw.dtypes.to_dict()
        )
    decoys = pd.concat([exemplar, exemplar], ignore_index=True)
    decoys["gameweek_id"] = [gw, gw + 1]
    for _, label in EVENT.values():
        decoys[label] = 50
    polluted = pd.concat([raw, decoys], ignore_index=True)
    admitted = historical_replay_inputs._admitted_history(gw, manifest, polluted)
    admitted = completed_performance_rows(
        history_before_target(admitted, gw, context.cutoff.isoformat(), True),
        context.fixtures,
    )
    pd.testing.assert_frame_equal(
        admitted.reset_index(drop=True), raw.reset_index(drop=True), check_exact=True
    )
    poison = context.current_history.iloc[:0].reindex(range(2))
    poison["gameweek_id"] = [gw, gw + 1]
    for _, label in EVENT.values():
        poison[label] = 50
    try:
        eligible_issue_history(replace(context, current_history=poison))
    except ValueError as error:
        if "target or future Gameweek" not in str(error):
            raise
    else:
        raise ValueError(f"EXT-41 label cutoff accepted a poisoned issue at GW{gw}")


def _forecast_issue(
    work: Path,
    manifest: dict[str, Any],
    origin: dict[str, Any],
    source: SourcePanel,
    previous: dict[int, dict[Component, pd.DataFrame]],
    rosters: list[pd.DataFrame],
    source_scale: dict[Component, ChampionFeatureScale],
    priors: dict[tuple[Component, Arm], FloatArray],
    baseline: Path,
    results: Path,
) -> tuple[Issued, dict[str, object]]:
    gw = int(origin["gw"])
    context, market, raw = _issue_input(work, manifest, origin, source, previous)
    _verify_label_boundary(context, manifest, raw)
    rosters.append(roster_identity(market).assign(gameweek_id=gw))
    roster = unique_season_identity(pd.concat(rosters, ignore_index=True))
    history = eligible_issue_history(context)
    current = annotate_history(history, roster, 38)
    fixtures = issue_fixture_rows(
        roster.loc[roster["gameweek_id"].eq(gw)], context.fixtures, gw, HORIZON
    )
    original_path = baseline / "projections" / f"gw{gw:02d}.parquet"
    base = pd.read_parquet(original_path)
    validate_components(base, SEASON)
    paths = {}
    previous[gw] = {}
    provenance: dict[str, object] = {
        "gameweek": gw,
        "deadline": context.cutoff.isoformat(),
        "source_panel_digest": context.source_digest,
        "settled_receipt_digest": context.receipt_digest,
        "history_rows": len(raw),
        "target_and_later_label_mutation_invariant": True,
    }
    for component in EVENT:
        predictors = build_predictors(
            fixtures, source.carry, current, 38 + gw, component
        )
        predictors = attach_champion_components(predictors, base, exact=True)
        predictors = source_scale[component].transform(predictors)
        previous[gw][component] = predictors.loc[
            predictors["gameweek_id"].eq(gw)
        ].copy()
        past = [parts[component] for parts in context.previous_issues.values()]
        issued_training = (
            pd.concat(past, ignore_index=True) if past else predictors.iloc[:0]
        )
        labels = training_examples(
            issued_training.dropna(subset=["rate"]), history, component, soft=False
        )
        provenance[f"{component}_current_label_rows"] = len(labels)
        provenance[f"{component}_current_label_gws"] = labels["gameweek_id"].nunique()
        targets = count_targets(labels, soft=False)
        positions = frozenset(source.training[component]["position_id"].astype(int))
        designs: list[tuple[str, tuple[str, ...], FloatArray | None]] = [
            (CHAMPION, (), None)
        ]
        for arm in ARMS:
            features = arm_features(arm, component)
            prior = priors[component, arm]
            fitted = fit_count_head(
                labels,
                targets,
                penalty=PENALTY,
                dynamic=False,
                prior=prior,
                extra_features=features,
            )
            if gw == 1:
                if not labels.empty:
                    raise ValueError("Opening fit must use zero destination labels")
                np.testing.assert_array_equal(fitted, prior)
            designs.append((arm, features, fitted))
        designs.append(
            (SOURCE_ONLY, arm_features("c", component), priors[component, "c"])
        )
        for name, features, coefficient in designs:
            result, diagnostic = score_fixture_component(
                base,
                predictors,
                component,
                coefficient,
                SEASON,
                dynamic=False,
                source_positions=positions,
                extra_features=features,
            )
            unchanged = base.columns.difference([f"xp_{component}", "projected_points"])
            pd.testing.assert_frame_equal(
                result[unchanged], base[unchanged], check_exact=True
            )
            nonactive = base["fixture_id"].eq(-1) | base["p_dnp"].eq(1)
            pd.testing.assert_series_equal(
                result.loc[nonactive, f"xp_{component}"],
                base.loc[nonactive, f"xp_{component}"],
                check_exact=True,
            )
            path = original_path
            if name != CHAMPION:
                path = results / f"{component}_{name}" / f"gw{gw:02d}.parquet"
                path.parent.mkdir(exist_ok=True)
                result.to_parquet(path, index=False)
            paths[component, name] = path, diagnostic
    market_digest = _digest(work / "verified_inputs" / f"gw{gw:02d}" / "market.parquet")
    return Issued(
        gw, market, fixtures, base, _digest(original_path), market_digest, paths
    ), provenance


def _settled_outcomes() -> pd.DataFrame:
    columns = [*KEYS, "goals_scored", "assists", "minutes", "total_points"]
    labels = pd.read_parquet(
        REPO / "data/archive" / SEASON / "processed/player_performances.parquet",
        columns=columns,
    )
    labels = labels.loc[
        labels["gameweek_id"].between(ISSUES.start, ISSUES.stop + HORIZON - 2)
    ]
    if labels.duplicated(KEYS).any() or not labels["minutes"].ge(0).all():
        raise ValueError("Duplicate settled fixture keys or invalid outcome minutes")
    for _, column in EVENT.values():
        counts = labels[column].dropna().to_numpy(dtype=float)
        if (
            not np.isfinite(counts).all()
            or (counts < 0).any()
            or not np.equal(counts, np.floor(counts)).all()
        ):
            raise ValueError(f"Invalid native event counts for {column}")
    return labels


def _evaluate_issue(
    issued: Issued, actual: pd.DataFrame, source: SourcePanel
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    gw = issued.gw
    settled = (
        actual.loc[actual["gameweek_id"].eq(gw)]
        .groupby("player_id", as_index=False)[["total_points", "minutes"]]
        .sum()
    )
    champion_xi = lineup(issued.market, issued.champion, settled, gw)
    rows, leads = [], []
    new_outfield = (
        issued.fixtures["gameweek_id"].eq(gw)
        & issued.fixtures["fixture_id"].gt(0)
        & issued.fixtures["position_id"].isin(OUTFIELD)
        & ~issued.fixtures["identity"].isin(source.carry["identity"].dropna())
    )
    for (component, name), (path, diagnostic) in issued.forecasts.items():
        forecast = issued.champion if name == CHAMPION else pd.read_parquet(path)
        xi = (
            champion_xi
            if name == CHAMPION
            else lineup(issued.market, forecast, settled, gw)
        )
        column = f"xp_{component}"
        champion_points = issued.fixtures[KEYS].merge(
            issued.champion[[*KEYS, column]], on=KEYS, validate="one_to_one"
        )[column]
        candidate_points = issued.fixtures[KEYS].merge(
            forecast[[*KEYS, column]], on=KEYS, validate="one_to_one"
        )[column]
        for lead in range(HORIZON):
            metric, coverage = _metrics(
                issued.fixtures,
                actual,
                forecast,
                diagnostic,
                component,
                gw + lead,
                name,
                champion_points,
            )
            by_lead = {int(row["lead"]): row for row in coverage}
            support = {
                key: value for key, value in by_lead[0].items() if key not in metric
            }
            leads.append(
                {
                    **support,
                    **metric,
                    "gameweek": gw,
                    "lead": lead,
                    "target_gameweek": gw + lead,
                    "component_mse": metric["squared_error_sum"] / metric["paired"]
                    if metric["paired"]
                    else np.nan,
                }
            )
            if lead == 0:
                metric["forecast_sha256"] = (
                    issued.champion_digest if name == CHAMPION else _digest(path)
                )
                metric["market_sha256"] = issued.market_digest
                metric["credited_xi_points"] = int(xi["credited_xi_points"])
                metric["credited_xi_delta"] = int(xi["credited_xi_points"]) - int(
                    champion_xi["credited_xi_points"]
                )
                metric["xi_changed"] = set(
                    cast(tuple[int, ...], xi["starting_ids"])
                ) != set(cast(tuple[int, ...], champion_xi["starting_ids"]))
                metric["changed_without_source_identity"] = int(
                    (
                        (candidate_points - champion_points).abs().gt(1e-9)
                        & new_outfield
                    ).sum()
                )
                rows.append(metric)
    return rows, leads


def _summarize(weekly: pd.DataFrame) -> pd.DataFrame:
    numeric = [
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
    pooled = weekly.groupby(["component", "arm"], as_index=False)[numeric].sum()
    for target, numerator in (
        ("component_mse", "squared_error_sum"),
        ("signed_bias", "error_sum"),
        ("categorical_log_loss", "log_loss_sum"),
        ("clipped_categorical_log_loss", "clipped_log_loss_sum"),
    ):
        pooled[target] = pooled[numerator] / pooled["paired"]
    changed = weekly.loc[
        weekly["gameweek"].eq(ISSUES.start),
        [
            "component",
            "arm",
            "changed_component_rows",
            "changed_without_source_identity",
        ],
    ]
    pooled = pooled.merge(
        changed.rename(
            columns={
                "changed_component_rows": "gw1_changed_rows",
                "changed_without_source_identity": "gw1_changed_without_source_identity",
            }
        ),
        on=["component", "arm"],
        validate="one_to_one",
    )
    mse = pooled.set_index(["component", "arm"])["component_mse"]
    for comparator in (CHAMPION, "a", "b"):
        pooled[f"mse_delta_vs_{comparator}"] = [
            row.component_mse - mse[row.component, comparator]
            for row in pooled.itertuples(index=False)
        ]
    c_better = (
        pooled[["mse_delta_vs_champion", "mse_delta_vs_a", "mse_delta_vs_b"]]
        .lt(0)
        .all(axis=1)
    )
    # A needs a prior legal-XI change; the final C decision can change in replay.
    pooled["forecast_eligible"] = (
        pooled["arm"].eq("a")
        & pooled["mse_delta_vs_champion"].lt(0)
        & pooled["xi_changed"].gt(0)
    ) | (pooled["arm"].eq("c") & c_better)
    nonbaseline = pooled["arm"].isin(ARMS)
    if not pooled.loc[nonbaseline, "gw1_changed_rows"].gt(0).all():
        raise ValueError(
            "An EXT-41 arm made no opening outfield fixture forecast changes"
        )
    return pooled


def _static_control_parity(summary: pd.DataFrame) -> pd.DataFrame:
    retained = pd.read_csv(TOPIC / "prototypes/ext_40/evidence/summary.csv").set_index(
        ["component", "arm"]
    )
    static = summary.set_index(["component", "arm"])
    parity = []
    for component in EVENT:
        observed = static.loc[component, "a"]
        old = retained.loc[component, variant_name(component, PENALTY, "static")]
        np.testing.assert_allclose(
            observed[["component_mse", "signed_bias"]].to_numpy(dtype=float),
            old[["component_mse", "signed_bias"]].to_numpy(dtype=float),
            rtol=0,
            atol=1e-12,
        )
        exact = ["paired", "credited_xi_points", "xi_changed", "gw1_changed_rows"]
        pd.testing.assert_series_equal(
            observed[exact],
            old[exact],
            check_names=False,
            check_dtype=False,
            check_exact=True,
        )
        parity.append(
            {
                "component": component,
                "paired": int(observed["paired"]),
                "ext40_component_mse": float(old["component_mse"]),
                "ext41_arm_a_component_mse": float(observed["component_mse"]),
                "component_mse_delta": float(
                    observed["component_mse"] - old["component_mse"]
                ),
                "xi_and_opening_coverage_match": True,
            }
        )
    return pd.DataFrame(parity)


def run(work: Path, results: Path) -> None:
    manifest_path = CONFIG_ROOT / f"dev_mirror_{SEASON.replace('-', '_')}_manifest.json"
    load_empirical_manifest_bundle(
        manifest_path,
        quarantine_root=work / "mirror",
        prefix_end_gw=ISSUES.stop - 1,
        require_admitted=True,
    )
    manifest = json.loads(manifest_path.read_bytes())
    source = source_panel(work, manifest)
    training, source_identity = _source_examples(work, source)
    scales, priors = {}, {}
    for component, examples in training.items():
        scales[component] = ChampionFeatureScale.fit(examples)
        prepared = scales[component].transform(examples)
        targets = count_targets(prepared, soft=component == "assists")
        for arm in ARMS:
            priors[component, arm] = fit_count_head(
                prepared,
                targets,
                penalty=PENALTY,
                dynamic=False,
                extra_features=arm_features(arm, component),
            )
    baseline = work / "ext41_champion"
    _staged_champion(work, manifest, baseline)
    previous: dict[int, dict[Component, pd.DataFrame]] = {}
    rosters: list[pd.DataFrame] = []
    forecasts = []
    provenance = []
    for origin in manifest["origins"][: len(ISSUES)]:
        issued, info = _forecast_issue(
            work,
            manifest,
            origin,
            source,
            previous,
            rosters,
            scales,
            priors,
            baseline,
            results,
        )
        forecasts.append(issued)
        provenance.append(info)
        print(f"EXT-41 issued GW{issued.gw}", flush=True)
    # Read target outcomes only after all forecasts have been issued and written.
    actual = _settled_outcomes()
    weekly_records, lead_records = [], []
    for issued in forecasts:
        rows, leads = _evaluate_issue(issued, actual, source)
        weekly_records.extend(rows)
        lead_records.extend(leads)
    weekly, by_lead = pd.DataFrame(weekly_records), pd.DataFrame(lead_records)
    common = by_lead.groupby(["component", "gameweek", "lead"])[
        ["paired", "unmatched"]
    ].nunique()
    if not common.eq(1).all().all() or not weekly["unmatched"].eq(0).all():
        raise ValueError(
            "EXT-41 comparisons did not preserve common evaluation populations"
        )
    summary = _summarize(weekly)
    reports = {
        "by_issue.csv": weekly,
        "by_lead.csv": by_lead,
        "summary.csv": summary,
        "issue_provenance.csv": pd.DataFrame(provenance),
        "static_control_parity.csv": _static_control_parity(summary),
    }
    for name, report in reports.items():
        report.to_csv(results / name, index=False, lineterminator="\n")
    identity = _experiment_identity(work, baseline)
    identity["ext40_recipe"] = identity["recipe"]
    identity["recipe"] = sha256(
        b"".join(
            Path(__file__).with_name(name).read_bytes()
            for name in ("prototypes.py", "run.py")
        )
    ).hexdigest()
    identity.update(
        {
            "source_panel": source.digest,
            "source_features": source_identity,
            "penalty": PENALTY,
            "bound_reports": {name: _digest(results / name) for name in reports},
        }
    )
    (results / "run_identity.json").write_text(
        json.dumps(identity, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        summary[
            ["component", "arm", "component_mse", "xi_changed", "forecast_eligible"]
        ].to_string(index=False)
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("work", type=Path)
    args = parser.parse_args()
    work = args.work.resolve()
    results = work / "ext41"
    if results.exists():
        raise FileExistsError(f"Retained EXT-41 results already exist at {results}")
    with TemporaryDirectory(prefix="ext41-", dir=work) as temporary:
        staged = Path(temporary) / "forecasts"
        staged.mkdir()
        run(work, staged)
        staged.rename(results)


if __name__ == "__main__":
    main()

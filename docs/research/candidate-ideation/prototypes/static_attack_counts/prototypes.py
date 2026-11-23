"""Replay the fixed EXT-41 Arm A event-count models on earlier issued observations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from functools import cache
from hashlib import sha256
import json
from os import environ
from pathlib import Path
from typing import ClassVar

import pandas as pd
import numpy as np

from backtesting.season_rules import load_season_lifecycle
from commands.run_stage_a_and_b import CONFIG_ROOT, MIRROR_ROOT, REPO
from models.def_xg_shrink_challenger import DefXgShrinkChallengerModel
from prototypes.ext_40.panel import (
    REQUIRED_ISSUE,
    ROSTER,
    SourcePanel,
    annotate_history,
    build_predictors,
    count_targets,
    load_source_panel,
    performance_rows,
    roster_identity,
    training_examples,
    unique_season_identity,
)
from prototypes.ext_40.prototypes import FEATURES as COUNT_FEATURES
from prototypes.ext_40.prototypes import (
    KEYS,
    Component,
    FloatArray,
    fit_count_head,
    score_fixture_component,
)

PENALTY = 0.03
FEATURES = (*COUNT_FEATURES, "features.club_id", "local.identity")
_ROSTER_ID = [*ROSTER, "identity"]
_SEASON_WEEKS = 38


@dataclass(frozen=True)
class BoundCountHead:
    """Authorized source panel and prior for one destination and component."""

    destination: str
    source: SourcePanel
    coefficients: FloatArray
    positions: frozenset[int]


def _bind_head(
    destination: str, source: SourcePanel, component: Component, *, soft_assists: bool
) -> BoundCountHead:
    examples = source.training[component]
    targets = count_targets(examples, soft=(soft_assists and component == "assists"))
    coefficients = fit_count_head(examples, targets, penalty=PENALTY, dynamic=False)
    coefficients.setflags(write=False)
    return BoundCountHead(
        destination,
        source,
        coefficients,
        frozenset(examples["position_id"].astype(int)),
    )


@cache
def load_development_head(component: Component, source_digest: str) -> BoundCountHead:
    """Verify pinned source inputs outside the prototype's fit/predict boundary."""
    lifecycle = load_season_lifecycle()
    development = lifecycle.season_for_role("development")
    seed = lifecycle.seasons[development].prior_seed
    if seed is None:
        raise ValueError("Static attack needs the authorized Development source season")
    suffix = seed.replace("-", "_")
    mirror = Path(environ.get("STATIC_ATTACK_MIRROR_ROOT", str(MIRROR_ROOT))).resolve()
    source = load_source_panel(
        mirror,
        CONFIG_ROOT / f"dev_mirror_{suffix}_manifest.json",
        REPO / "data/archive" / seed / "processed",
        CONFIG_ROOT / f"seed_manifest_{suffix}.json",
        soft_assists=True,
    )
    if source.digest != source_digest:
        raise ValueError("Static attack source panel differs from reviewed source")
    target_manifest = (
        CONFIG_ROOT / f"dev_mirror_{development.replace('-', '_')}_manifest.json"
    )
    opening = json.loads(target_manifest.read_bytes())["origins"][0]
    if opening["gw"] != 1 or source.last_available >= datetime.fromisoformat(
        opening["deadline_utc"]
    ):
        raise ValueError(
            "Static attack training panel was unavailable at Development opening"
        )
    if len(source.training[component]) != 9294:
        raise ValueError("Static attack source panel differs from the Arm A cohort")
    return _bind_head(development, source, component, soft_assists=True)


@cache
def _load_filter_source(root: Path, source_digest: str, seed: str) -> SourcePanel:
    origins = root / "filter_training_origins.json"
    seed_manifest = root / "filter_training_seed.json"
    mirror = root / "mirror"
    if (
        not origins.is_file()
        or not seed_manifest.is_file()
        or not (mirror / seed).is_dir()
        or any(
            not path.resolve().is_relative_to(root)
            for path in (origins, seed_manifest, mirror / seed)
        )
    ):
        raise ValueError(f"Incomplete Filter training-source inventory at {root}")
    # Validate manifest bytes before using the receipt paths declared inside them.
    if (
        sha256(origins.read_bytes() + seed_manifest.read_bytes() + b"\x00").hexdigest()
        != source_digest
    ):
        raise ValueError("Filter training-source manifests differ from reviewed inputs")
    source = load_source_panel(
        mirror,
        origins,
        REPO / "data/archive" / seed / "processed",
        seed_manifest,
        soft_assists=False,
    )
    if source.digest != source_digest or any(
        len(rows) != 10033 for rows in source.training.values()
    ):
        raise ValueError(
            "Filter training-source panel differs from the reviewed cohort"
        )
    return source


def _roster_prefix(
    features: pd.DataFrame,
    prior_forecasts: list[tuple[int, pd.DataFrame]],
    issue: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    origin_roster = roster_identity(features[ROSTER].drop_duplicates())
    origin_roster["gameweek_id"] = issue
    prior_rosters = [
        rows[[*_ROSTER_ID, "gameweek_id"]].drop_duplicates()
        for _, rows in prior_forecasts
    ]
    roster = unique_season_identity(
        pd.concat([*prior_rosters, origin_roster], ignore_index=True)
    )
    return origin_roster, roster


class StaticAttackCountsModel(DefXgShrinkChallengerModel):
    """Native count head for one attack component, using original Champion states."""

    component: ClassVar[Component]
    development_head: ClassVar[BoundCountHead]
    historical_filter_head: ClassVar[BoundCountHead | None] = None
    penalty: ClassVar[float] = PENALTY

    @classmethod
    def load_optional_historical_filter_source(cls, source_digest: str) -> None:
        """Load the reviewed Filter source only when its inventory root is explicit."""
        configured_root = environ.get("STATIC_ATTACK_FILTER_SOURCE_ROOT")
        if configured_root is None:
            return
        root = Path(configured_root).resolve(strict=True)
        lifecycle = load_season_lifecycle()
        destination = lifecycle.season_for_role("historical_filter")
        seed = lifecycle.seasons[destination].prior_seed
        if seed is None:
            raise ValueError("Missing authorized Historical Filter training season")
        suffix = destination.replace("-", "_")
        manifest = json.loads(
            (CONFIG_ROOT / f"dev_mirror_{suffix}_manifest.json").read_bytes()
        )
        opening = manifest["origins"][0]
        if manifest["season"] != destination or opening["gw"] != 1:
            raise ValueError("Invalid Historical Filter opening deadline")
        cls.bind_historical_filter_source(
            destination,
            _load_filter_source(root, source_digest, seed),
            source_digest,
            datetime.fromisoformat(opening["deadline_utc"]),
            soft_assists=False,
        )

    @classmethod
    def bind_historical_filter_source(
        cls,
        destination: str,
        source: SourcePanel,
        pinned_digest: str,
        opening_deadline: datetime,
        *,
        soft_assists: bool,
    ) -> None:
        """Bind a separately admitted and reserved pre-Historical-Filter inventory."""
        lifecycle = load_season_lifecycle()
        if (
            destination != lifecycle.season_for_role("historical_filter")
            or source.season != lifecycle.seasons[destination].prior_seed
            or destination != cls.development_head.source.season
            or source.digest != pinned_digest
            or source.last_available >= opening_deadline
        ):
            raise ValueError("Invalid frozen Historical Filter training-source panel")
        if cls.historical_filter_head is not None:
            raise ValueError("Historical Filter training source already bound")
        cls.historical_filter_head = _bind_head(
            destination, source, cls.component, soft_assists=soft_assists
        )

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        raise ValueError("Static attack requires the historical issue context")

    def predict_with_prior_forecasts(
        self,
        features: pd.DataFrame,
        horizon: int,
        history: pd.DataFrame,
        prior_forecasts: list[tuple[int, pd.DataFrame]],
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        issue = int(features.attrs["issue_gameweek"])
        (season,) = features["native_rules_version"].unique()
        head = self.development_head
        if season != head.destination:
            head = self.historical_filter_head
            if head is None or season != head.destination:
                raise ValueError(
                    "No reserved pre-season count panel for this destination"
                )
        if not history["gameweek_id"].lt(issue).all() or [
            gw for gw, _ in prior_forecasts
        ] != list(range(1, issue)):
            raise ValueError("Static attack requires strictly earlier issue history")
        for gw, observation in prior_forecasts:
            if (
                not observation["gameweek_id"].eq(gw).all()
                or observation.duplicated(KEYS).any()
            ):
                raise ValueError("Invalid earlier issued fixture predictors")
        origin_roster, roster = _roster_prefix(features, prior_forecasts, issue)
        identity = roster.loc[
            roster["gameweek_id"].eq(issue), ["player_id", "identity"]
        ]
        issued = features[REQUIRED_ISSUE].merge(
            identity, on="player_id", how="left", validate="many_to_one"
        )
        settled = performance_rows(history)
        current = annotate_history(settled, roster, _SEASON_WEEKS)
        predictors = build_predictors(
            issued, head.source.carry, current, _SEASON_WEEKS + issue, self.component
        )
        earlier = (
            pd.concat(
                [rows[predictors.columns] for _, rows in prior_forecasts],
                ignore_index=True,
            )
            if prior_forecasts
            else predictors.iloc[:0]
        )
        labels = training_examples(
            earlier.dropna(subset=["rate"]), settled, self.component, soft=False
        )
        fitted = fit_count_head(
            labels,
            count_targets(labels, soft=False),
            penalty=self.penalty,
            dynamic=False,
            prior=head.coefficients,
        )
        if issue == 1:
            np.testing.assert_array_equal(fitted, head.coefficients)
        champion = super().predict(features, horizon)
        projected, _ = score_fixture_component(
            champion,
            predictors,
            self.component,
            fitted,
            str(season),
            dynamic=False,
            source_positions=head.positions,
        )
        observation = predictors.loc[predictors["gameweek_id"].eq(issue)].merge(
            origin_roster[["player_id", "code", "club_id", "identity"]],
            on="player_id",
            how="left",
            validate="many_to_one",
        )
        return projected, observation

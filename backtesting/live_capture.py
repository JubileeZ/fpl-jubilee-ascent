"""Prospective pre-deadline capture, shadow replay, and live operational review.

Implements Phase 10 requirements:
1. Scheduled pre-deadline capture strictly verified before deadline cutoff (`capture_time <= deadline_time`).
2. Rejection of late or missed captures without retrospective prospective fabrication.
3. Dual shadow replay state maintaining independent squads, finances, and decisions for
   provisionally adopted Candidate versus former Champion.
4. Operational tracking with outcome-finalization delay checks.
5. Fixed review points enforcing minimum evaluation horizon and peeking prevention.
6. Material-harm rollback recommendation citing bundle hash and requiring explicit human approval.
7. Strict sealed holdout protection (2026-27 GW6+).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Literal

ModelRole = Literal["adopted_candidate", "former_champion"]


class LiveCaptureError(Exception):
    """Base exception for prospective live capture and review errors."""


class LateCaptureError(LiveCaptureError):
    """Raised when capture occurs after official deadline; late captures cannot be prospective."""


class OutcomeNotFinalizedError(LiveCaptureError):
    """Raised when attempting to score a gameweek before match outcomes are final."""


class InsufficientLiveEvidenceError(LiveCaptureError):
    """Raised when evaluating a live review before minimum fixed horizon gameweeks have elapsed."""


class SealedLiveSeasonError(LiveCaptureError):
    """Raised when live capture attempts to read or target sealed holdout data."""


@dataclass(frozen=True)
class PlayerForecastSnapshot:
    """Player-level prospective forecast snapshot captured before deadline."""

    player_id: int
    player_name: str
    team_code: int
    position: str
    expected_minutes: float
    projected_points: float
    goals: float = 0.0
    assists: float = 0.0
    clean_sheets: float = 0.0
    goals_conceded: float = 0.0
    saves: float = 0.0
    bonus: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LiveDeadlineCapture:
    """Immutable prospective pre-deadline capture artifact."""

    capture_id: str
    season: str
    gameweek: int
    deadline_time_utc: str
    capture_time_utc: str
    model_name: str
    model_version_hash: str
    policy_settings_hash: str
    forecasts: list[PlayerForecastSnapshot]
    is_late: bool = False
    capture_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "capture_id": self.capture_id,
            "season": self.season,
            "gameweek": self.gameweek,
            "deadline_time_utc": self.deadline_time_utc,
            "capture_time_utc": self.capture_time_utc,
            "model_name": self.model_name,
            "model_version_hash": self.model_version_hash,
            "policy_settings_hash": self.policy_settings_hash,
            "forecasts": [f.to_dict() for f in self.forecasts],
            "is_late": self.is_late,
            "capture_hash": self.capture_hash,
        }

    def compute_hash(self) -> str:
        """Compute cryptographic SHA256 digest of forecast capture."""
        payload = {
            "capture_id": self.capture_id,
            "season": self.season,
            "gameweek": self.gameweek,
            "deadline_time_utc": self.deadline_time_utc,
            "capture_time_utc": self.capture_time_utc,
            "model_name": self.model_name,
            "model_version_hash": self.model_version_hash,
            "policy_settings_hash": self.policy_settings_hash,
            "forecasts": [f.to_dict() for f in sorted(self.forecasts, key=lambda x: x.player_id)],
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class ShadowReplayState:
    """Independent shadow replay state for live tracking."""

    model_role: ModelRole
    season: str
    gameweek: int
    owned_fifteen: tuple[int, ...]
    bank_tenths: int
    free_transfers: int
    transfers_made: int
    hit_cost: int
    lineup_starters: tuple[int, ...]
    captain_id: int
    vice_id: int
    gross_points: float
    net_points: float
    chip_used: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["owned_fifteen"] = list(self.owned_fifteen)
        data["lineup_starters"] = list(self.lineup_starters)
        return data


@dataclass(frozen=True)
class LiveReviewPoint:
    """Evaluation at a fixed live review horizon."""

    review_point_id: str
    season: str
    gameweeks_included: tuple[int, ...]
    adopted_total_net: float
    former_champion_total_net: float
    net_delta: float
    should_rollback: bool
    rollback_reasons: list[str]
    requires_human_approval: bool = True
    human_approval_ref: str | None = None
    bundle_hash: str = ""
    reviewed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["gameweeks_included"] = list(self.gameweeks_included)
        return data


class LiveCaptureManager:
    """Coordinates prospective deadline captures, shadow replays, and review milestones."""

    def __init__(self, storage_dir: Path | str | None = None) -> None:
        self.storage_dir = Path(storage_dir or "data/reports/live_shadow_capture")

    def _ensure_dir(self) -> None:
        (self.storage_dir / "captures").mkdir(parents=True, exist_ok=True)
        (self.storage_dir / "shadow_states").mkdir(parents=True, exist_ok=True)
        (self.storage_dir / "reviews").mkdir(parents=True, exist_ok=True)

    def record_deadline_capture(
        self,
        season: str,
        gameweek: int,
        deadline_time_utc: str,
        capture_time_utc: str,
        model_name: str,
        model_version_hash: str,
        policy_settings_hash: str,
        forecasts: Sequence[PlayerForecastSnapshot],
        *,
        capture_id: str | None = None,
    ) -> LiveDeadlineCapture:
        """Capture and validate pre-deadline player forecasts."""
        self._ensure_dir()

        # Sealed data protection
        if season == "2026-27" and gameweek >= 6:
            raise SealedLiveSeasonError(
                "Access to sealed 2026-27 GW6+ prohibited in live capture without explicit protocol amendment"
            )

        # Parse timestamps with timezone awareness
        dl_dt = datetime.fromisoformat(deadline_time_utc.replace("Z", "+00:00"))
        cap_dt = datetime.fromisoformat(capture_time_utc.replace("Z", "+00:00"))

        if cap_dt > dl_dt:
            diff_sec = (cap_dt - dl_dt).total_seconds()
            raise LateCaptureError(
                f"Capture at {capture_time_utc} is {diff_sec:.1f}s after deadline {deadline_time_utc}. "
                f"Late captures cannot be admitted as prospective evidence."
            )

        cid = capture_id or f"capture-{season}-gw{gameweek}-{model_name}"
        initial_cap = LiveDeadlineCapture(
            capture_id=cid,
            season=season,
            gameweek=gameweek,
            deadline_time_utc=deadline_time_utc,
            capture_time_utc=capture_time_utc,
            model_name=model_name,
            model_version_hash=model_version_hash,
            policy_settings_hash=policy_settings_hash,
            forecasts=list(forecasts),
            is_late=False,
        )
        digest = initial_cap.compute_hash()
        final_cap = LiveDeadlineCapture(
            **{**initial_cap.to_dict(), "forecasts": list(forecasts), "capture_hash": digest}
        )

        out_path = self.storage_dir / "captures" / f"{cid}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(final_cap.to_dict(), f, indent=2)

        return final_cap

    def step_shadow_state(
        self,
        prior_state: ShadowReplayState,
        new_transfers_in: Sequence[int],
        new_transfers_out: Sequence[int],
        lineup_starters: Sequence[int],
        captain_id: int,
        vice_id: int,
        outcomes_by_player: dict[int, float],
        *,
        chip_used: str | None = None,
        outcomes_finalized: bool = True,
    ) -> ShadowReplayState:
        """Advance a single model's shadow replay state by one gameweek."""
        if not outcomes_finalized:
            raise OutcomeNotFinalizedError(
                f"Cannot advance shadow state for GW{prior_state.gameweek + 1}: outcomes not finalized"
            )

        # Validate transfer balance
        if len(new_transfers_in) != len(new_transfers_out):
            raise ValueError("Transfers in and out count must match")

        current_squad = set(prior_state.owned_fifteen)
        for out_id in new_transfers_out:
            if out_id not in current_squad:
                raise ValueError(f"Player {out_id} transferred out but not owned")
            current_squad.remove(out_id)
        for in_id in new_transfers_in:
            current_squad.add(in_id)

        num_transfers = len(new_transfers_in)
        free_allowed = prior_state.free_transfers
        hits_count = max(0, num_transfers - free_allowed)
        hit_deduction = hits_count * 4

        # Next FTs: 1 added, capped at 5
        next_fts = min(5, max(1, free_allowed - num_transfers + 1))

        # Score lineup
        gross_pts = 0.0
        for pid in lineup_starters:
            pts = outcomes_by_player.get(pid, 0.0)
            if pid == captain_id:
                pts *= 2.0
            gross_pts += pts

        net_pts = gross_pts - hit_deduction

        return ShadowReplayState(
            model_role=prior_state.model_role,
            season=prior_state.season,
            gameweek=prior_state.gameweek + 1,
            owned_fifteen=tuple(sorted(current_squad)),
            bank_tenths=prior_state.bank_tenths,
            free_transfers=next_fts,
            transfers_made=num_transfers,
            hit_cost=hit_deduction,
            lineup_starters=tuple(lineup_starters),
            captain_id=captain_id,
            vice_id=vice_id,
            gross_points=float(gross_pts),
            net_points=float(net_pts),
            chip_used=chip_used,
        )

    def evaluate_live_review(
        self,
        season: str,
        gameweeks: Sequence[int],
        adopted_history: Sequence[ShadowReplayState],
        champion_history: Sequence[ShadowReplayState],
        *,
        material_loss_limit: float = 8.0,
        min_gameweeks: int = 4,
        review_point_id: str | None = None,
    ) -> LiveReviewPoint:
        """Evaluate fixed live review horizon and generate rollback recommendations if regressed."""
        if len(gameweeks) < min_gameweeks:
            raise InsufficientLiveEvidenceError(
                f"Evaluation at {len(gameweeks)} GWs is below minimum fixed horizon of {min_gameweeks} GWs. "
                f"Continuous peeking on isolated weekly noise is prohibited."
            )

        adopted_by_gw = {s.gameweek: s for s in adopted_history if s.gameweek in gameweeks}
        champ_by_gw = {s.gameweek: s for s in champion_history if s.gameweek in gameweeks}

        if len(adopted_by_gw) != len(gameweeks) or len(champ_by_gw) != len(gameweeks):
            raise ValueError("Shadow history does not cover all requested gameweeks")

        adopted_net = sum(s.net_points for s in adopted_by_gw.values())
        champ_net = sum(s.net_points for s in champ_by_gw.values())
        delta = adopted_net - champ_net

        should_rollback = False
        reasons: list[str] = []

        if delta < -material_loss_limit:
            should_rollback = True
            reasons.append(
                f"Adopted candidate lagged former champion by {abs(delta):.1f} net pts over {len(gameweeks)} GWs, "
                f"exceeding live material loss limit of {material_loss_limit:.1f} pts"
            )

        rid = review_point_id or f"review-{season}-gw{max(gameweeks)}"
        bundle_hash = hashlib.sha256(
            f"{season}:{list(gameweeks)}:{adopted_net}:{champ_net}".encode("utf-8")
        ).hexdigest()

        return LiveReviewPoint(
            review_point_id=rid,
            season=season,
            gameweeks_included=tuple(gameweeks),
            adopted_total_net=float(adopted_net),
            former_champion_total_net=float(champ_net),
            net_delta=float(delta),
            should_rollback=should_rollback,
            rollback_reasons=reasons,
            requires_human_approval=True,
            human_approval_ref=None,
            bundle_hash=bundle_hash,
            reviewed_at=datetime.now(timezone.utc).isoformat(),
        )


def evaluate_live_review(
    season: str,
    gameweeks: Sequence[int],
    adopted_history: Sequence[ShadowReplayState],
    champion_history: Sequence[ShadowReplayState],
    *,
    material_loss_limit: float = 8.0,
    min_gameweeks: int = 4,
    review_point_id: str | None = None,
    storage_dir: Path | str | None = None,
) -> LiveReviewPoint:
    """Evaluate fixed live review horizon and generate rollback recommendations if regressed."""
    manager = LiveCaptureManager(storage_dir=storage_dir)
    return manager.evaluate_live_review(
        season=season,
        gameweeks=gameweeks,
        adopted_history=adopted_history,
        champion_history=champion_history,
        material_loss_limit=material_loss_limit,
        min_gameweeks=min_gameweeks,
        review_point_id=review_point_id,
    )

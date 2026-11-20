"""Weekly Transfer Planner model selection, remote protected main freshness, and injury-audit rerun pinning (#192, #197, #200, ADR 0070)."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
import json
import logging
import os
from pathlib import Path
import subprocess
from typing import Any, Literal

import pandas as pd

from backtesting.portable_evidence import (
    ExclusionLedger,
    TamperedLedgerError,
    VerificationScorecard,
    load_and_verify_scorecard,
    validate_relative_posix_path,
)
from models.selection import dual_tier_models, load_model_selection

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FreshnessStatus = Literal["verified_current", "stale_remote_changed", "unverified"]

STALE_CHECKOUT_MESSAGE = (
    "Remote Champion selection on protected main has changed; "
    "run manual 'git pull' before generating a fresh Transfer Plan (auto-pull is disabled)."
)


class StaleCheckoutError(ValueError):
    """Raised when remote protected main selection has changed and local checkout requires manual sync."""


@dataclass(frozen=True)
class RemoteFreshnessResult:
    """Result of checking local config/model_selection.json against protected main."""

    status: FreshnessStatus
    local_champion: str
    local_candidates: tuple[str, ...]
    local_podium_sealed: bool
    local_podium_frozen_season: str | None
    remote_champion: str | None = None
    remote_candidates: tuple[str, ...] | None = None
    remote_podium_sealed: bool | None = None
    remote_podium_frozen_season: str | None = None
    remote_adoption_receipt: dict[str, Any] | None = None
    detail: str = ""
    checked: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PlannerSelectionPreflight:
    """Preflight summary of Weekly Transfer Planner model selection and freshness checks."""

    effective_model: str
    selection_reason: str
    freshness_status: FreshnessStatus
    comparable_scores: dict[str, float]
    eligible_models: tuple[str, ...]
    excluded_models: tuple[str, ...]
    latest_settled_gw: int
    verified_prefix_end_gw: int
    scorecard_hash: str | None = None
    fallback_reason: str | None = None
    override_applied: bool = False
    pinned_for_rerun: bool = False
    slate_id: str | None = None
    confirmed_champion: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def format_preflight_lines(self) -> list[str]:
        score_parts = [f"{model}={pts:.1f}" for model, pts in self.comparable_scores.items()]
        scores_str = ", ".join(score_parts) if score_parts else "none"
        prefix_str = f"GW1..GW{self.verified_prefix_end_gw}" if self.verified_prefix_end_gw > 0 else "none"
        settled_str = f"GW{self.latest_settled_gw}" if self.latest_settled_gw > 0 else "GW0"
        lines = [
            "TRANSFER PLANNER SELECTION PREFLIGHT",
            f"• Serving Model: {self.effective_model} (reason: {self.selection_reason})",
            f"• Freshness Status: {self.freshness_status}",
            f"• Confirmed Champion: {self.confirmed_champion or self.effective_model}",
            f"• Eligible Slate: {', '.join(self.eligible_models) if self.eligible_models else self.effective_model}",
            f"• Excluded Finalists: {', '.join(self.excluded_models) if self.excluded_models else 'none'}",
            f"• Latest Settled Gameweek: {settled_str} (verified prefix: {prefix_str})",
            f"• Comparable Cumulative Net Points: {scores_str}",
        ]
        if self.fallback_reason:
            lines.append(f"• Fallback Reason: {self.fallback_reason}")
        if self.override_applied:
            lines.append(f"• One-Plan Override: active ({self.effective_model})")
        if self.pinned_for_rerun:
            lines.append(f"• Injury-Audit Rerun Pin: active ({self.effective_model})")
        return lines


def _fetch_remote_main_selection_via_git(
    project_root: Path,
    *,
    timeout_secs: float = 5.0,
    remote_name: str = "origin",
    branch_name: str = "main",
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Read-only git fetch + git show of config/model_selection.json on origin/main. Never pulls."""
    subprocess.run(
        ["git", "fetch", "--no-tags", remote_name, branch_name],
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=timeout_secs,
        check=True,
    )
    sel_proc = subprocess.run(
        ["git", "show", f"{remote_name}/{branch_name}:config/model_selection.json"],
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=timeout_secs,
        check=True,
    )
    remote_sel = json.loads(sel_proc.stdout)
    if not isinstance(remote_sel, dict):
        raise ValueError("Remote config/model_selection.json is not a JSON object")

    remote_receipt: dict[str, Any] | None = None
    try:
        rec_proc = subprocess.run(
            ["git", "show", f"{remote_name}/{branch_name}:config/model_selection.adoption.json"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=timeout_secs,
            check=True,
        )
        parsed_rec = json.loads(rec_proc.stdout)
        if isinstance(parsed_rec, dict):
            remote_receipt = parsed_rec
    except (subprocess.SubprocessError, OSError, json.JSONDecodeError, ValueError):
        remote_receipt = None
    return remote_sel, remote_receipt


def check_remote_main_freshness(
    selection_path: Path | None = None,
    *,
    remote_loader: Callable[[], Mapping[str, Any] | None] | None = None,
    remote_selection_payload: Mapping[str, Any] | None = None,
    remote_main_path: Path | None = None,
    check_remote: bool | None = None,
    project_root: Path | None = None,
    timeout_secs: float = 5.0,
    raise_on_stale: bool = True,
) -> RemoteFreshnessResult:
    """Compare local ModelSelection against merged protected main without auto-pulling."""
    selection = load_model_selection(selection_path)
    root = (project_root or PROJECT_ROOT).resolve()

    remote_payload: Mapping[str, Any] | None = None
    remote_receipt: dict[str, Any] | None = None
    checked = True

    if remote_selection_payload is not None:
        remote_payload = remote_selection_payload
    elif remote_main_path is not None:
        target = Path(remote_main_path)
        if target.is_dir():
            cand = target / "config" / "model_selection.json"
            target = cand if cand.is_file() else (target / "model_selection.json")
            rec_path = target.with_name("model_selection.adoption.json")
            if rec_path.is_file():
                try:
                    loaded_rec = json.loads(rec_path.read_text(encoding="utf-8"))
                    if isinstance(loaded_rec, dict):
                        remote_receipt = loaded_rec
                except (OSError, json.JSONDecodeError):
                    pass
        try:
            loaded = json.loads(target.read_text(encoding="utf-8"))
            if not isinstance(loaded, dict):
                raise ValueError("Remote selection payload must be a JSON object")
            remote_payload = loaded
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            return RemoteFreshnessResult(
                status="unverified",
                local_champion=selection.champion,
                local_candidates=selection.candidates,
                local_podium_sealed=selection.podium_sealed,
                local_podium_frozen_season=selection.podium_frozen_season,
                detail=f"github_unreachable_unverified_champion_only:{exc}",
                checked=True,
            )
    elif remote_loader is not None:
        try:
            remote_payload = remote_loader()
            if remote_payload is None:
                raise ValueError("Remote loader returned None")
        except Exception as exc:
            return RemoteFreshnessResult(
                status="unverified",
                local_champion=selection.champion,
                local_candidates=selection.candidates,
                local_podium_sealed=selection.podium_sealed,
                local_podium_frozen_season=selection.podium_frozen_season,
                detail=f"github_unreachable_unverified_champion_only:{exc}",
                checked=True,
            )
    else:
        env_flag = os.environ.get("FPL_CHECK_REMOTE_MAIN", "").strip().lower() in ("1", "true", "yes")
        should_check = check_remote if check_remote is not None else env_flag
        if not should_check:
            return RemoteFreshnessResult(
                status="verified_current",
                local_champion=selection.champion,
                local_candidates=selection.candidates,
                local_podium_sealed=selection.podium_sealed,
                local_podium_frozen_season=selection.podium_frozen_season,
                remote_champion=selection.champion,
                remote_candidates=selection.candidates,
                remote_podium_sealed=selection.podium_sealed,
                remote_podium_frozen_season=selection.podium_frozen_season,
                detail="offline_local_default",
                checked=False,
            )
        try:
            remote_payload, remote_receipt = _fetch_remote_main_selection_via_git(
                root, timeout_secs=timeout_secs
            )
        except Exception as exc:
            return RemoteFreshnessResult(
                status="unverified",
                local_champion=selection.champion,
                local_candidates=selection.candidates,
                local_podium_sealed=selection.podium_sealed,
                local_podium_frozen_season=selection.podium_frozen_season,
                detail=f"github_unreachable_unverified_champion_only:{exc}",
                checked=True,
            )

    try:
        if remote_payload is None:
            raise ValueError("Remote selection payload missing")
        remote_champ = str(remote_payload["champion"])
        remote_cands = tuple(str(x) for x in remote_payload.get("candidates", ()))
        remote_sealed = bool(remote_payload.get("podium_sealed", False))
        raw_season = remote_payload.get("podium_frozen_season")
        remote_season = str(raw_season).strip() if isinstance(raw_season, str) and raw_season.strip() else None
    except (KeyError, TypeError, ValueError) as exc:
        return RemoteFreshnessResult(
            status="unverified",
            local_champion=selection.champion,
            local_candidates=selection.candidates,
            local_podium_sealed=selection.podium_sealed,
            local_podium_frozen_season=selection.podium_frozen_season,
            detail=f"github_unreachable_unverified_champion_only:{exc}",
            checked=checked,
        )

    matches = (
        remote_champ == selection.champion
        and remote_cands == selection.candidates
        and remote_sealed == selection.podium_sealed
        and remote_season == selection.podium_frozen_season
    )
    if not matches:
        result = RemoteFreshnessResult(
            status="stale_remote_changed",
            local_champion=selection.champion,
            local_candidates=selection.candidates,
            local_podium_sealed=selection.podium_sealed,
            local_podium_frozen_season=selection.podium_frozen_season,
            remote_champion=remote_champ,
            remote_candidates=remote_cands,
            remote_podium_sealed=remote_sealed,
            remote_podium_frozen_season=remote_season,
            remote_adoption_receipt=remote_receipt,
            detail=(
                f"remote_main_selection_changed:local={selection.champion}"
                f"(sealed={selection.podium_sealed})!=remote={remote_champ}(sealed={remote_sealed})"
            ),
            checked=checked,
        )
        if raise_on_stale:
            raise StaleCheckoutError(STALE_CHECKOUT_MESSAGE)
        return result

    return RemoteFreshnessResult(
        status="verified_current",
        local_champion=selection.champion,
        local_candidates=selection.candidates,
        local_podium_sealed=selection.podium_sealed,
        local_podium_frozen_season=selection.podium_frozen_season,
        remote_champion=remote_champ,
        remote_candidates=remote_cands,
        remote_podium_sealed=remote_sealed,
        remote_podium_frozen_season=remote_season,
        remote_adoption_receipt=remote_receipt,
        detail="remote_main_matches_local",
        checked=checked,
    )


def sync_validation_evidence_readonly(
    selection_path: Path | None = None,
    *,
    evidence_dir: Path | None = None,
    project_root: Path | None = None,
    timeout_secs: float = 5.0,
    remote_name: str = "origin",
    branch_name: str = "validation-evidence",
) -> bool:
    """Fail-soft read-only fetch of scorecards and exclusions from validation-evidence into gitignored cache."""
    try:
        selection = load_model_selection(selection_path)
    except (OSError, ValueError, KeyError):
        return False
    if not selection.podium_sealed or not selection.podium_frozen_season:
        return False

    season = selection.podium_frozen_season
    root = (project_root or PROJECT_ROOT).resolve()
    dest_root = (
        Path(evidence_dir).resolve()
        if evidence_dir is not None
        else (root / "data" / "reports" / "validation_evidence" / season).resolve()
    )
    try:
        subprocess.run(
            ["git", "fetch", "--no-tags", remote_name, branch_name],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=timeout_secs,
            check=True,
        )
        ls_proc = subprocess.run(
            ["git", "ls-tree", "-r", "--name-only", f"{remote_name}/{branch_name}", f"{season}/"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=timeout_secs,
            check=True,
        )
        rel_files: list[str] = []
        for raw_line in ls_proc.stdout.splitlines():
            clean = raw_line.strip()
            if not clean.startswith(f"{season}/"):
                continue
            sub = validate_relative_posix_path(clean[len(season) + 1 :])
            if sub in ("latest_scorecard.json", "exclusions.jsonl") or (
                sub.startswith("scorecards/gw") and sub.endswith(".json")
            ):
                rel_files.append(sub)
        if not rel_files:
            return False
        for sub in rel_files:
            show_proc = subprocess.run(
                ["git", "show", f"{remote_name}/{branch_name}:{season}/{sub}"],
                cwd=root,
                capture_output=True,
                timeout=timeout_secs,
                check=True,
            )
            dest = (dest_root / sub).resolve()
            if not dest.is_relative_to(dest_root):
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp = dest.with_suffix(dest.suffix + ".tmp")
            tmp.write_bytes(show_proc.stdout)
            os.replace(tmp, dest)
        return True
    except (subprocess.SubprocessError, OSError, ValueError) as exc:
        logger.debug("Read-only validation-evidence sync skipped: %s", exc)
        return False


def resolve_latest_officially_settled_gw(
    processed_dir: Path | None = None,
    *,
    settled_gw: int | None = None,
    now_utc: datetime | None = None,
) -> int:
    """Determine latest officially settled Gameweek (finished=True, data_checked=True, >= last kickoff + 24h)."""
    if settled_gw is not None:
        return max(0, int(settled_gw))
    if processed_dir is None:
        return 0
    gw_path = Path(processed_dir) / "gameweeks.parquet"
    if not gw_path.is_file():
        return 0
    try:
        df_gw = pd.read_parquet(gw_path)
    except Exception:
        return 0
    if df_gw.empty or "id" not in df_gw.columns or "finished" not in df_gw.columns:
        return 0

    has_data_checked_col = "data_checked" in df_gw.columns
    bootstrap_checked: dict[int, bool] = {}
    if not has_data_checked_col:
        for cand_boot in (
            Path(processed_dir).parent / "raw" / "bootstrap_static.json",
            PROJECT_ROOT / "data" / "raw" / "bootstrap_static.json",
        ):
            if cand_boot.is_file():
                try:
                    boot = json.loads(cand_boot.read_text(encoding="utf-8"))
                    for ev in boot.get("events", ()):
                        if isinstance(ev, Mapping) and "id" in ev and "data_checked" in ev:
                            bootstrap_checked[int(ev["id"])] = bool(ev.get("data_checked", False))
                    break
                except Exception:
                    pass

    fix_path = Path(processed_dir) / "fixtures.parquet"
    df_fix: pd.DataFrame | None = None
    if fix_path.is_file():
        try:
            df_fix = pd.read_parquet(fix_path)
        except Exception:
            df_fix = None

    effective_now = now_utc.astimezone(UTC) if now_utc is not None else None
    settled_ids: list[int] = []
    for row in df_gw.to_dict(orient="records"):
        try:
            gw_id = int(row["id"])
        except (TypeError, ValueError, KeyError):
            continue
        if not bool(row.get("finished", False)):
            continue
        if has_data_checked_col:
            val = row.get("data_checked")
            if val is None or bool(pd.isna(val)) or not bool(val):
                continue
        elif gw_id in bootstrap_checked and not bootstrap_checked[gw_id]:
            continue

        if df_fix is not None and not df_fix.empty and "gameweek_id" in df_fix.columns:
            fix_rows = [
                r for r in df_fix.to_dict(orient="records") if int(r.get("gameweek_id", -1)) == gw_id
            ]
            if fix_rows:
                if "finished" in df_fix.columns and not all(
                    bool(r.get("finished", False)) and not bool(pd.isna(r.get("finished")))
                    for r in fix_rows
                ):
                    continue
                if effective_now is not None and "kickoff_time" in df_fix.columns:
                    parsed_ko: list[datetime] = []
                    for r in fix_rows:
                        raw_ko = r.get("kickoff_time")
                        if raw_ko is not None and not bool(pd.isna(raw_ko)):
                            ts = pd.to_datetime(str(raw_ko), utc=True, errors="coerce")
                            if not bool(pd.isna(ts)):
                                parsed_ko.append(ts.to_pydatetime())
                    if parsed_ko and effective_now < max(parsed_ko) + timedelta(hours=24):
                        continue
        settled_ids.append(gw_id)

    return max(settled_ids, default=0)


def _extract_prior_reviewed_model_and_state(
    prior_solution_path: Path | None,
) -> tuple[str | None, int | None, str | None, str | None]:
    """Read (reviewed_base_model, next_gw, target_gw_deadline, confirmed_champion) from prior solution.json."""
    if prior_solution_path is None or not Path(prior_solution_path).is_file():
        return None, None, None, None
    try:
        payload = json.loads(Path(prior_solution_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, None, None, None
    if not isinstance(payload, Mapping):
        return None, None, None, None
    meta = payload.get("meta")
    if not isinstance(meta, Mapping):
        return None, None, None, None
    raw_model = meta.get("reviewed_base_model") or meta.get("base_model") or meta.get("champion")
    base_model = str(raw_model).strip() if isinstance(raw_model, str) and raw_model.strip() else None
    if base_model and base_model.endswith("_external_xmins"):
        base_model = base_model[: -len("_external_xmins")]
    raw_gw = meta.get("next_gw")
    next_gw = int(raw_gw) if isinstance(raw_gw, int) or (isinstance(raw_gw, str) and raw_gw.isdigit()) else None
    raw_dl = meta.get("target_gw_deadline") or meta.get("transfer_plan_deadline")
    deadline = str(raw_dl).strip() if isinstance(raw_dl, str) and raw_dl.strip() else None
    raw_champ = meta.get("confirmed_champion")
    confirmed_champ = str(raw_champ).strip() if isinstance(raw_champ, str) and raw_champ.strip() else None
    return base_model, next_gw, deadline, confirmed_champ


def _is_target_gw_deadline_invalidated(
    processed_dir: Path | None,
    *,
    target_gw: int | None,
    prior_next_gw: int | None,
    prior_deadline: str | None,
    now_utc: datetime | None,
) -> bool:
    """Return True when target GW changed or its transfer deadline changed/expired."""
    if target_gw is not None and prior_next_gw is not None and int(target_gw) != int(prior_next_gw):
        return True
    check_gw = target_gw if target_gw is not None else prior_next_gw
    if processed_dir is None or check_gw is None:
        return False
    gw_path = Path(processed_dir) / "gameweeks.parquet"
    if not gw_path.is_file():
        return False
    try:
        df_gw = pd.read_parquet(gw_path)
    except Exception:
        return False
    if df_gw.empty or "id" not in df_gw.columns:
        return False
    rows = df_gw[df_gw["id"] == int(check_gw)]
    if rows.empty:
        return False
    row = rows.iloc[0]
    if "finished" in rows.columns and pd.notna(row.get("finished")) and bool(row.get("finished")):
        return True
    if "deadline_passed" in rows.columns and pd.notna(row.get("deadline_passed")) and bool(row.get("deadline_passed")):
        return True
    if "deadline_time" in rows.columns and pd.notna(row.get("deadline_time")):
        cur_dl_str = str(row["deadline_time"]).strip()
        cur_dl = pd.to_datetime(cur_dl_str, utc=True, errors="coerce")
        if prior_deadline is not None:
            prior_dl = pd.to_datetime(prior_deadline, utc=True, errors="coerce")
            if pd.notna(cur_dl) and pd.notna(prior_dl):
                if cur_dl != prior_dl:
                    return True
            elif cur_dl_str != prior_deadline:
                return True
        if now_utc is not None and pd.notna(cur_dl) and cur_dl <= pd.Timestamp(now_utc):
            return True
    return False


def resolve_weekly_planner_model(
    selection_path: Path | None = None,
    *,
    evidence_dir: Path | None = None,
    processed_dir: Path | None = None,
    settled_gw: int | None = None,
    override_model: str | None = None,
    force_champion: bool = False,
    pinned_review_model: str | None = None,
    is_rerun: bool = False,
    target_gw: int | None = None,
    prior_solution_path: Path | None = None,
    remote_freshness: RemoteFreshnessResult | None = None,
    remote_loader: Callable[[], Mapping[str, Any] | None] | None = None,
    remote_selection_payload: Mapping[str, Any] | None = None,
    remote_main_path: Path | None = None,
    check_remote: bool | None = None,
    sync_evidence: bool = False,
    now_utc: datetime | None = None,
) -> PlannerSelectionPreflight:
    """Resolve Weekly Transfer Planner serving model under ADR 0070 rules."""
    selection = load_model_selection(selection_path)
    if remote_freshness is not None:
        freshness = remote_freshness
        if freshness.status == "stale_remote_changed":
            raise StaleCheckoutError(STALE_CHECKOUT_MESSAGE)
    else:
        freshness = check_remote_main_freshness(
            selection_path,
            remote_loader=remote_loader,
            remote_selection_payload=remote_selection_payload,
            remote_main_path=remote_main_path,
            check_remote=check_remote,
            raise_on_stale=True,
        )

    if sync_evidence and selection.podium_sealed and freshness.status == "verified_current":
        sync_validation_evidence_readonly(selection_path, evidence_dir=evidence_dir)

    season = selection.podium_frozen_season
    if evidence_dir is not None:
        resolved_evidence_dir: Path | None = Path(evidence_dir)
    elif season:
        resolved_evidence_dir = PROJECT_ROOT / "data" / "reports" / "validation_evidence" / season
    else:
        resolved_evidence_dir = None

    excluded_set: set[str] = set()
    ledger_tampered = False
    if resolved_evidence_dir is not None:
        excl_file = resolved_evidence_dir / "exclusions.jsonl"
        if excl_file.is_file():
            try:
                excluded_set = ExclusionLedger(excl_file).excluded_candidates(season=season)
            except TamperedLedgerError:
                ledger_tampered = True

    if selection.podium_sealed:
        eligible_models = tuple(
            dict.fromkeys([selection.champion, *(c for c in selection.candidates if c not in excluded_set)])
        )
        excluded_models = tuple(c for c in selection.candidates if c in excluded_set)
    else:
        eligible_models = tuple(dual_tier_models(selection_path))
        excluded_models = ()

    latest_settled_gw = resolve_latest_officially_settled_gw(
        processed_dir, settled_gw=settled_gw, now_utc=now_utc
    )

    # Evaluate scorecard and prefix completeness
    scorecard: VerificationScorecard | None = None
    scorecard_hash: str | None = None
    slate_id: str | None = None
    verified_prefix_end_gw = 0
    comparable_scores: dict[str, float] = {}
    fallback_reason: str | None = None

    if resolved_evidence_dir is not None and (resolved_evidence_dir / "latest_scorecard.json").is_file():
        try:
            scorecard = load_and_verify_scorecard(resolved_evidence_dir / "latest_scorecard.json")
            scorecard_hash = scorecard.scorecard_hash
            slate_id = scorecard.slate_id
            verified_prefix_end_gw = scorecard.settled_through_gw
        except (TamperedLedgerError, OSError, ValueError, KeyError, json.JSONDecodeError):
            scorecard = None
            fallback_reason = "scorecard_invalid"

    if freshness.status == "unverified":
        fallback_reason = "github_unreachable_unverified_champion_only"
    elif not selection.podium_sealed:
        fallback_reason = "slate_unsealed"
    elif ledger_tampered:
        fallback_reason = "exclusion_ledger_tampered"
    elif scorecard is None:
        if fallback_reason is None:
            fallback_reason = "scorecard_missing"
    else:
        if (
            not scorecard.slate_sealed
            or scorecard.confirmed_champion != selection.champion
            or tuple(scorecard.podium_order) != tuple(selection.candidates)
            or (season is not None and scorecard.season != season)
        ):
            fallback_reason = "scorecard_slate_mismatch"
        else:
            if scorecard.active_exclusions:
                excl_file = (resolved_evidence_dir / "exclusions.jsonl") if resolved_evidence_dir else None
                if excl_file is None or not excl_file.is_file():
                    fallback_reason = "exclusion_ledger_missing"
            if fallback_reason is None:
                required_gw = latest_settled_gw if latest_settled_gw > 0 else scorecard.settled_through_gw
                if latest_settled_gw == 0 and settled_gw is None:
                    latest_settled_gw = scorecard.settled_through_gw
                if required_gw <= 0 or scorecard.settled_through_gw <= 0:
                    fallback_reason = "no_settled_gameweeks"
                elif scorecard.settled_through_gw < required_gw:
                    fallback_reason = f"missing_settled_gw:{required_gw}"
                elif scorecard.gap_status != "complete" or scorecard.first_blocked_gw is not None:
                    blocked = scorecard.first_blocked_gw or (scorecard.settled_through_gw + 1)
                    fallback_reason = f"incomplete_settled_prefix:gw{blocked}:{scorecard.gap_status}"
                else:
                    missing_models = [
                        m for m in eligible_models if m not in scorecard.cumulative_net_points
                    ]
                    if missing_models:
                        fallback_reason = "missing_comparable_model_scores"
                    else:
                        comparable_scores = {
                            m: float(scorecard.cumulative_net_points[m]) for m in eligible_models
                        }

    # 1. Explicit One-Plan Override (--champion / --model)
    cleaned_override = "" if override_model is None else str(override_model).strip()
    if force_champion or cleaned_override.lower() == "champion":
        return PlannerSelectionPreflight(
            effective_model=selection.champion,
            selection_reason="explicit_override_champion",
            freshness_status=freshness.status,
            comparable_scores=comparable_scores,
            eligible_models=eligible_models,
            excluded_models=excluded_models,
            latest_settled_gw=latest_settled_gw,
            verified_prefix_end_gw=verified_prefix_end_gw,
            scorecard_hash=scorecard_hash,
            fallback_reason=fallback_reason,
            override_applied=True,
            pinned_for_rerun=False,
            slate_id=slate_id,
            confirmed_champion=selection.champion,
        )

    if cleaned_override and cleaned_override.lower() != "default":
        if cleaned_override in excluded_set or (
            scorecard is not None and cleaned_override in scorecard.active_exclusions
        ):
            raise ValueError(
                f"Cannot override Transfer Planner with terminally excluded finalist '{cleaned_override}'."
            )
        if ledger_tampered and cleaned_override != selection.champion:
            raise TamperedLedgerError(
                "Cannot override Transfer Planner with finalist while ExclusionLedger integrity verification failed."
            )
        return PlannerSelectionPreflight(
            effective_model=cleaned_override,
            selection_reason=f"explicit_override:{cleaned_override}",
            freshness_status=freshness.status,
            comparable_scores=comparable_scores,
            eligible_models=eligible_models,
            excluded_models=excluded_models,
            latest_settled_gw=latest_settled_gw,
            verified_prefix_end_gw=verified_prefix_end_gw,
            scorecard_hash=scorecard_hash,
            fallback_reason=fallback_reason,
            override_applied=True,
            pinned_for_rerun=False,
            slate_id=slate_id,
            confirmed_champion=selection.champion,
        )

    # 2. Injury-Audit Rerun Model Pinning
    prior_model, prior_next_gw, prior_deadline, prior_champ = _extract_prior_reviewed_model_and_state(
        prior_solution_path
    )
    candidate_pin = (
        pinned_review_model.strip()
        if isinstance(pinned_review_model, str) and pinned_review_model.strip()
        else (prior_model if is_rerun else None)
    )
    if candidate_pin and candidate_pin.endswith("_external_xmins"):
        candidate_pin = candidate_pin[: -len("_external_xmins")]

    if candidate_pin:
        pin_valid = True
        if freshness.status == "unverified" and candidate_pin != selection.champion:
            pin_valid = False
        elif ledger_tampered and candidate_pin != selection.champion:
            pin_valid = False
        elif candidate_pin in excluded_set or (
            scorecard is not None and candidate_pin in scorecard.active_exclusions
        ):
            pin_valid = False
        elif candidate_pin not in eligible_models:
            pin_valid = False
        elif prior_champ is not None and prior_champ != selection.champion:
            pin_valid = False
        elif _is_target_gw_deadline_invalidated(
            processed_dir,
            target_gw=target_gw,
            prior_next_gw=prior_next_gw,
            prior_deadline=prior_deadline,
            now_utc=now_utc,
        ):
            pin_valid = False

        if pin_valid:
            return PlannerSelectionPreflight(
                effective_model=candidate_pin,
                selection_reason=f"pinned_for_rerun:{candidate_pin}",
                freshness_status=freshness.status,
                comparable_scores=comparable_scores,
                eligible_models=eligible_models,
                excluded_models=excluded_models,
                latest_settled_gw=latest_settled_gw,
                verified_prefix_end_gw=verified_prefix_end_gw,
                scorecard_hash=scorecard_hash,
                fallback_reason=fallback_reason,
                override_applied=False,
                pinned_for_rerun=True,
                slate_id=slate_id,
                confirmed_champion=selection.champion,
            )

    # 3. Automatic Weekly Selection on Verified Common Settled Prefix
    if fallback_reason is not None or not comparable_scores:
        return PlannerSelectionPreflight(
            effective_model=selection.champion,
            selection_reason=f"fallback_confirmed_champion:{fallback_reason or 'no_comparable_scores'}",
            freshness_status=freshness.status,
            comparable_scores=comparable_scores,
            eligible_models=eligible_models,
            excluded_models=excluded_models,
            latest_settled_gw=latest_settled_gw,
            verified_prefix_end_gw=verified_prefix_end_gw,
            scorecard_hash=scorecard_hash,
            fallback_reason=fallback_reason or "no_comparable_scores",
            override_applied=False,
            pinned_for_rerun=False,
            slate_id=slate_id,
            confirmed_champion=selection.champion,
        )

    ranked = sorted(
        enumerate(eligible_models),
        key=lambda item: (-comparable_scores[item[1]], item[0]),
    )
    winner = ranked[0][1]
    top_score = comparable_scores[winner]
    tied_at_top = [m for m in eligible_models if comparable_scores[m] == top_score]
    if len(tied_at_top) > 1:
        if selection.champion in tied_at_top:
            reason = "tie_break_confirmed_champion"
        else:
            reason = "tie_break_frozen_podium_rank"
    else:
        reason = "verified_scorecard_leader"

    return PlannerSelectionPreflight(
        effective_model=winner,
        selection_reason=reason,
        freshness_status=freshness.status,
        comparable_scores=comparable_scores,
        eligible_models=eligible_models,
        excluded_models=excluded_models,
        latest_settled_gw=latest_settled_gw,
        verified_prefix_end_gw=verified_prefix_end_gw,
        scorecard_hash=scorecard_hash,
        fallback_reason=None,
        override_applied=False,
        pinned_for_rerun=False,
        slate_id=slate_id,
        confirmed_champion=selection.champion,
    )

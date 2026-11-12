"""Development Screen: retained prototype diagnostics against Champion.

    uv run python .agents/skills/explore-candidate/smoke.py --show_seasons
    uv run python .agents/skills/explore-candidate/smoke.py <prototypes.py> [--gw_range 1-N] [--workers 4]
    uv run python .agents/skills/explore-candidate/smoke.py --model <registered_name>
    uv run python .agents/skills/explore-candidate/smoke.py <prototypes.py> --audit_only
    uv run python .agents/skills/explore-candidate/smoke.py --model <frozen_name> --season confirm --out docs/research/<slug>/candidate_gate.csv

Season roles resolve from ``data/archive/YYYY-YY`` (complete = every fixture finished; seed = prior archive season if present):
``dev`` = latest complete season, ``confirm`` = second-latest complete season (ADR 0047), incomplete seasons = sealed live
holdout (never run here). ``--season confirm``: registered models only, full season, durable ``--out``, one run per model
(refused when ``--out``, any ``docs/{research,archive}/*/candidate_gate.csv``, or Candidate Ledger already holds it).
New records append to a separate ``*.v2.csv`` beside requested ``--out``; legacy files remain unchanged.
Each stage retains paired frames, weekly scores and pool metrics. Resume requires matching source/data/protocol identity
and intact artifacts; oracle success remains recorded even if integrated evaluation fails. Oracle segment wins unassessed.
Prototype file exports ``PROTOTYPES: dict[str, type[BaseModel]]`` and ``FEATURES: dict[str, tuple[str, ...]]``
(entries ``features.<col>`` / ``history.<col>`` / ``local.<key>``). Exit 2 = invalid execution, audit, or confirm-protocol failure.
"""

from __future__ import annotations

import argparse
import ast
import csv
import importlib.util
import re
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from types import ModuleType

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from backtesting import walkforward  # noqa: E402
from backtesting.model_evaluation import compare_to_reference  # noqa: E402
from backtesting import promotion  # noqa: E402
from backtesting.promotion import (  # noqa: E402
    BOOTSTRAP_MIN_P,
    CONFIRMATION_BOOTSTRAP_MIN_P,
    PLAYABLE_MINUTES_THRESHOLD,
    PLAYABLE_XP_THRESHOLD,
    identify_active_gameweeks,
)
from backtesting.smoke_diagnostics import DiagnosticStore, digest, input_identity, oracle_event_screen, paired_weekly_regret  # noqa: E402
from backtesting.walkforward import LEDGER_COMPONENTS, WalkforwardConfig, WalkforwardResult, run_walkforward_backtest  # noqa: E402
from commands.evaluate_minutes import evaluate_minutes_from_eval_frames  # noqa: E402
from features.builder import TERMINAL_PLAYER_COLUMNS  # noqa: E402
from models import get_model  # noqa: E402
from models.base import BaseModel  # noqa: E402
from models.selection import load_model_selection  # noqa: E402

ARCHIVE = ROOT / "data/archive"
SEASON_NAME = re.compile(r"\d{4}-\d{2}")
ROLES = ("dev", "confirm")
LEDGER_CSV = ROOT / "docs/research/candidate-ledger/candidate_ledger.csv"
DEFAULT_OUT = ROOT / ".tmp/agent/explore-candidate/smoke_results.csv"
BANNED_SOURCE = ("players.parquet", "read_parquet", "read_csv", "open(", "data/archive")
EVAL_TARGET = "blended_points"


@dataclass(frozen=True)
class Season:
    name: str
    data_dir: Path
    seed_dir: Path | None
    last_gw: int


def resolve_seasons(archive: Path = ARCHIVE) -> tuple[dict[str, Season], list[str]]:
    """Role -> Season for latest two complete archive seasons; plus incomplete (live holdout) season names."""
    names = sorted(d.name for d in archive.iterdir() if SEASON_NAME.fullmatch(d.name) and (d / "processed/fixtures.parquet").exists())
    fixtures = {name: pd.read_parquet(archive / name / "processed/fixtures.parquet", columns=["gameweek_id", "finished"]) for name in names}
    complete = [name for name in names if fixtures[name]["finished"].all()]
    seed = {name: archive / prior / "processed" for prior, name in zip(names, names[1:])}
    roles = {
        role: Season(name, archive / name / "processed", seed.get(name), int(fixtures[name]["gameweek_id"].max()))
        for role, name in zip(ROLES, reversed(complete))
    }
    return roles, [name for name in names if name not in complete]
SOURCES = {"features", "history", "local"}
ALLOWED_LITERALS = {"player_id", "fixture_id", "gameweek_id", "projected_points", "projected_minutes", "external_xmins", *LEDGER_COMPONENTS}
COLUMN_KEYWORDS = {"columns", "subset", "on", "by"}


class LeakageError(RuntimeError):
    pass


class InertPrototypeError(RuntimeError):
    pass


def max_playable_pool_shift(reference_df: pd.DataFrame, candidate_df: pd.DataFrame) -> float:
    """Return max |cand_xp - champ_xp| across the Exogenous Playable Pool (mins >= 30 or champ_xp >= 2.0)."""
    cols = ["gameweek", "player_id", "projected_points"]
    champ_cols = [*cols, "actual_minutes"] if "actual_minutes" in reference_df.columns else cols
    merged = pd.merge(
        reference_df[champ_cols].rename(columns={"projected_points": "champ_xp"}),
        candidate_df[cols].rename(columns={"projected_points": "cand_xp"}),
        on=["gameweek", "player_id"],
        how="inner",
    )
    if merged.empty:
        return 0.0
    mins = merged["actual_minutes"] if "actual_minutes" in merged.columns else pd.Series(0.0, index=merged.index)
    playable = (merged["champ_xp"] >= PLAYABLE_XP_THRESHOLD) | (mins >= PLAYABLE_MINUTES_THRESHOLD)
    subset = merged.loc[playable]
    if subset.empty:
        return 0.0
    return float((subset["cand_xp"] - subset["champ_xp"]).abs().max())


def check_inert_prototype(
    name: str,
    reference: WalkforwardResult,
    candidate: WalkforwardResult,
    *,
    combined_delta: float,
    min_playable_shift: float = 0.01,
) -> None:
    """Raise InertPrototypeError if prototype produces no active GWs or negligible playable shift with zero delta."""
    active_gws = identify_active_gameweeks(reference.df_eval, candidate.df_eval)
    if not active_gws:
        raise InertPrototypeError(f"{name}: zero active gameweeks (max |cand_xp - champ_xp| <= 1e-6)")
    max_shift = max_playable_pool_shift(reference.df_eval, candidate.df_eval)
    if max_shift < min_playable_shift and abs(combined_delta) < 1e-9:
        raise InertPrototypeError(
            f"{name}: inert on Exogenous Playable Pool (max |delta_xp| = {max_shift:.6f} < {min_playable_shift:.2f}) "
            f"with combined_delta = {combined_delta:+.6f}"
        )


def load_prototypes(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("explore_candidate_prototypes", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _column_literals(tree: ast.AST) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(tree):
        targets: list[ast.AST] = []
        if isinstance(node, ast.Subscript):
            targets = [node.slice]
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and node.func.attr == "get" and node.args:
                targets = [node.args[0]]
            targets += [kw.value for kw in node.keywords if kw.arg in COLUMN_KEYWORDS]
        found |= {c.value for t in targets for c in ast.walk(t) if isinstance(c, ast.Constant) and isinstance(c.value, str)}
    return found


def audit(path: Path, module: ModuleType) -> list[str]:
    source = path.read_text()
    issues = [f"banned source token {token!r}" for token in BANNED_SOURCE if token in source]
    issues += [f"season literal {s!r} (prototypes stay season-agnostic)" for s in sorted(set(SEASON_NAME.findall(source)))]
    prototypes, manifest = getattr(module, "PROTOTYPES", None), getattr(module, "FEATURES", None)
    if not isinstance(prototypes, dict) or not prototypes:
        return [*issues, "PROTOTYPES dict missing or empty"]
    if not isinstance(manifest, dict):
        return [*issues, "FEATURES manifest missing"]
    for name, cls in prototypes.items():
        if name not in manifest:
            issues.append(f"{name}: no FEATURES entry")
        if not (isinstance(cls, type) and issubclass(cls, BaseModel)) or cls().name != name:
            issues.append(f"{name}: must be BaseModel subclass whose .name == key")
        try:
            get_model(name)
            issues.append(f"{name}: collides with registered model name")
        except ValueError:
            pass
    declared: set[str] = set()
    for name, entries in manifest.items():
        for entry in entries:
            kind, _, column = entry.partition(".")
            if kind not in SOURCES or not column:
                issues.append(f"{name}: bad manifest entry {entry!r} (use features.|history.|local.)")
            elif kind == "features" and column in TERMINAL_PLAYER_COLUMNS:
                issues.append(f"{name}: terminal column {column!r} banned as feature (ADR 0046)")
            declared.add(column)
    undeclared = _column_literals(ast.parse(source)) - declared - ALLOWED_LITERALS
    return issues + [f"undeclared column literal {column!r}" for column in sorted(undeclared)]


def guard(model: BaseModel) -> BaseModel:
    fit, predict, state = getattr(model, "fit", None), model.predict, {"max_gw": 0}

    def guarded_fit(history_df: pd.DataFrame) -> None:
        gws = history_df.get("gameweek_id", pd.Series(dtype=float))
        state["max_gw"] = int(gws.max()) if len(gws.dropna()) else 0
        if fit is not None:
            fit(history_df)

    def guarded_predict(features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        leaked = set(TERMINAL_PLAYER_COLUMNS) & set(features_df.columns)
        if leaked:
            raise LeakageError(f"{model.name}: terminal columns in features {sorted(leaked)}")
        target = int(features_df["gameweek_id"].min())
        if state["max_gw"] >= target:
            raise LeakageError(f"{model.name}: fit history reaches GW {state['max_gw']} >= target GW {target}")
        return predict(features_df, horizon=horizon)

    model.fit, model.predict = guarded_fit, guarded_predict
    return model


def _init_worker(prototype_path: str | None) -> None:
    prototypes = load_prototypes(Path(prototype_path)).PROTOTYPES if prototype_path else {}
    walkforward.get_model = lambda name: guard(prototypes[name]() if name in prototypes else get_model(name))


def _run(job: tuple[str, Season, int, int] | tuple[str, Season, int, int, bool]) -> tuple[str, WalkforwardResult]:
    name, season, start_gw, end_gw, *rest = job
    oracle_minutes = bool(rest[0]) if rest else False
    config = WalkforwardConfig(
        model_name=name,
        data_dir=season.data_dir,
        start_gw=start_gw,
        end_gw=end_gw,
        seed_processed_dir=season.seed_dir,
        eval_target=EVAL_TARGET,
        oracle_minutes=oracle_minutes,
    )
    return name, run_walkforward_backtest(config)


def resolve_candidate_component(name: str, lane: str | None, module: ModuleType | None) -> str:
    if module is not None and hasattr(module, "COMPONENTS"):
        comps = getattr(module, "COMPONENTS")
        if isinstance(comps, dict) and name in comps:
            return str(comps[name])
    idea_queue_path = ROOT / "docs/research/candidate-ideation/idea_queue.csv"
    if idea_queue_path.exists():
        try:
            queue_rows = list(csv.DictReader(idea_queue_path.read_text().splitlines()))
            for row in queue_rows:
                idea_lane = row.get("idea_id", "").lower().replace("-", "_")
                metric = row.get("component") or row.get("target_metric", "")
                if (lane and lane == idea_lane) or name.startswith(idea_lane):
                    return str(metric)
        except Exception:
            pass
    return "all"


def resolve_candidate_tier(tier_arg: str, name: str, lane: str | None, module: ModuleType | None, season_role: str) -> str:
    if season_role == "confirm" or tier_arg == "3":
        return "3"
    if tier_arg in {"1", "2"}:
        return tier_arg
    comp = resolve_candidate_component(name, lane, module)
    if comp == "xp_minutes":
        return "1"
    if comp in {"xp_goals", "xp_assists", "xp_clean_sheet", "xp_clean_sheets", "xp_saves", "xp_defcon", "xp_bonus"}:
        return "2"
    return "3"


def _read_rows(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(path.read_text().splitlines())) if path.exists() else []


def count_grid_positives(
    out: Path,
    *,
    season: str,
    data_season: str,
    champion: str,
    gw_range: str,
    variants: list[str] | tuple[str, ...] | set[str] | None = None,
    identities: dict[str, dict[str, object]] | None = None,
) -> int:
    key = (season, data_season, champion, gw_range)
    allowed = set(variants) if variants is not None else None
    latest: dict[str, float] = {}
    store = DiagnosticStore(out)
    for row in store.rows():
        if (row.get("season"), row.get("data_season"), row.get("champion"), row.get("gw_range")) != key:
            continue
        variant = row.get("variant", "")
        if allowed is not None and variant not in allowed:
            continue
        if identities is not None and (variant not in identities or row["run_id"] != digest(identities[variant])):
            continue
        if row["stage"] not in {"integrated", "minutes"} or row["execution_status"] != "complete":
            continue
        store.verify(row)
        try:
            latest[variant] = float(row.get("combined_delta", 0.0))
        except (TypeError, ValueError):
            latest[variant] = 0.0
    return sum(1 for delta in latest.values() if delta > 0.0)


def confirm_violations(
    models: list[str], prototypes: Path | None, out: Path, full_season: bool, season: str, prior_gates: list[Path] | None = None
) -> list[str]:
    issues = ["confirm season takes registered --model only, no prototypes"] if prototypes or not models else []
    if not full_season:
        issues.append("confirm season runs full season only")
    if ".tmp" in out.resolve().parts:
        issues.append("confirm season needs durable --out (docs/research/<slug>/...), not .tmp")
    if prior_gates is None:
        prior_gates = [*ROOT.glob("docs/research/*/candidate_gate*.csv"), *ROOT.glob("docs/archive/*/candidate_gate*.csv")]
    rows = [r for path in {out, DiagnosticStore(out).output, *prior_gates} for r in _read_rows(path)]
    done_out = {r["variant"] for r in rows if r.get("season") == "confirm" and r.get("data_season") == season}
    ledger = list(csv.DictReader(LEDGER_CSV.read_text().splitlines()))
    for name in models:
        if name in done_out or any(name in r["tried_as"] and f"confirm {season}" in r["result"].lower() for r in ledger):
            issues.append(f"{name}: confirm {season} already run (ADR 0047: one run per frozen Candidate)")
    return issues


def run_identities(args: argparse.Namespace, season: Season, champion: str, challengers: list[str], module: ModuleType | None) -> dict[str, dict[str, object]]:
    shared = input_identity(ROOT, season.data_dir, season.seed_dir, args.prototypes)
    protocol = {name: value for name, value in vars(promotion).items() if name.isupper() and isinstance(value, (str, int, float, bool, dict, tuple))}
    return {
        name: {"input_identity": shared, "season": args.season, "data_season": season.name, "champion": champion,
               "variant": name, "gw_range": args.gw_range or f"1-{season.last_gw}",
               "initial_tier": resolve_candidate_tier(args.tier, name, args.lane, module, args.season),
               "component": resolve_candidate_component(name, args.lane, module), "protocol": protocol,
               "eval_target": EVAL_TARGET, "blend_weight": 0.5, "seed_season": season.seed_dir.parent.name if season.seed_dir else "none",
               "scoring_context": "legacy_default_2025-26; no native_rules_version injection"}
        for name in challengers
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Development Screen diagnostics; retained final evidence requires --evidence_request.")
    parser.add_argument("--season", choices=ROLES, default="dev")
    parser.add_argument("--show_seasons", action="store_true")
    parser.add_argument("prototypes", nargs="?", type=Path)
    parser.add_argument("--model", action="append", default=[], help="Registered model name (repeatable)")
    parser.add_argument("--gw_range", default=None, help="Default: full season")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--lane", default="")
    parser.add_argument("--tier", choices=("1", "2", "3", "auto"), default="auto", help="Evaluation tier: 1, 2, 3, or auto")
    parser.add_argument("--audit_only", action="store_true")
    parser.add_argument("--evidence_request", type=Path, default=None, help="Evaluate retained rolling evidence through shared final recommendation protocol")
    parser.add_argument("--output_bundle", type=Path, default=None)
    args = parser.parse_args()

    if args.evidence_request is not None:
        from backtesting.promotion_evidence import write_recommendation_bundle

        output = args.output_bundle or args.evidence_request.with_name("recommendation_bundle.json")
        bundle = write_recommendation_bundle(args.evidence_request, output)
        print(f"Scientific verdict: {bundle['scientific_verdict']}; bundle hash: {bundle['bundle_hash']}; {output}")
        return 0
    print("Legacy smoke diagnostics only: scientific verdict inconclusive; no promotion or Dead Lever authority.")

    roles, live = resolve_seasons()
    if args.show_seasons:
        for role, s in roles.items():
            print(f"{role:8} {s.name}  GW1-{s.last_gw}  seed {s.seed_dir.parent.name if s.seed_dir else 'none'}")
        print(f"{'holdout':8} {', '.join(live) or 'none'}  (sealed live season; never run here)")
        return 0
    if args.season not in roles:
        print(f"SEASON FAIL: no complete archive season for role {args.season!r} (have {[s.name for s in roles.values()]})")
        return 2
    season = roles[args.season]

    prototype_names: list[str] = []
    module: ModuleType | None = None
    if args.prototypes:
        module = load_prototypes(args.prototypes.resolve())
        issues = audit(args.prototypes, module)
        print("AUDIT", "FAIL" if issues else "PASS", *[f"\n  - {issue}" for issue in issues])
        if issues:
            return 2
        prototype_names = list(module.PROTOTYPES)
    if args.audit_only:
        return 0
    challengers = prototype_names + args.model
    if not challengers:
        parser.error("give a prototypes file and/or --model")
    gw_range = args.gw_range or f"1-{season.last_gw}"
    start_gw, end_gw = map(int, gw_range.split("-"))
    if not 1 <= start_gw <= end_gw <= season.last_gw:
        parser.error("Requested gameweeks must fit selected completed season")
    if args.season == "confirm":
        full = (start_gw, end_gw) == (1, season.last_gw)
        issues = confirm_violations(args.model, args.prototypes, args.out, full, season.name)
        print("CONFIRM PROTOCOL", "FAIL" if issues else "PASS", *[f"\n  - {issue}" for issue in issues])
        if issues:
            return 2

    champion = load_model_selection().champion
    print(f"Season {args.season} = {season.name} GW{gw_range}, seed {season.seed_dir.parent.name if season.seed_dir else 'none'}")
    store = DiagnosticStore(args.out)
    identities = run_identities(args, season, champion, challengers, module)
    done = store.completed(identities)
    if done:
        print(f"Skipping verified complete identities in {store.output}: {', '.join(sorted(done))}")
    pending = [name for name in challengers if name not in done]
    if not pending:
        print(f"Wrote 0 rows -> {store.output} (all identities complete)")
        return 0
    path_arg = str(args.prototypes.resolve()) if args.prototypes else None
    bar = CONFIRMATION_BOOTSTRAP_MIN_P if args.season == "confirm" else BOOTSTRAP_MIN_P
    written, leaked = 0, False

    def retain(name: str, stage: str, *, terminal: bool, status: str = "complete", reference: WalkforwardResult | None = None,
               candidate: WalkforwardResult | None = None, weekly: pd.DataFrame | None = None, **values: object) -> bool:
        nonlocal written, leaked
        if status == "complete" and input_identity(ROOT, season.data_dir, season.seed_dir, args.prototypes) != identities[name]["input_identity"]:
            status, terminal = "partial", True
            values = {"reasons": "Source or input bytes changed during execution; retained identity invalid"}
        summary = {
            "date": date.today().isoformat(), "season": args.season, "data_season": season.name,
            "lane": args.lane, "variant": name, "champion": champion, "gw_range": gw_range,
            "stage": stage, "terminal": terminal, "participation_mode": "oracle" if stage == "oracle" else "predicted",
            "scoring_context": identities[name]["scoring_context"], "eval_target": EVAL_TARGET,
            "seed_season": identities[name]["seed_season"], "execution_status": status,
            "source": str(args.prototypes or "registered"), **values,
        }
        try:
            store.record(identities[name], summary, reference=reference.df_eval if reference is not None else None,
                         candidate=candidate.df_eval if candidate is not None else None, weekly=weekly)
        except (ValueError, OSError) as error:
            if status != "complete":
                raise
            store.record(identities[name], {**summary, "execution_status": "partial", "terminal": True,
                                           "pass": None, "reasons": f"Evidence invalid: {error}"})
            status = "partial"
        written += 1
        leaked = leaked or status == "partial"
        return status == "complete"

    for name in pending:
        retain(name, "queued", terminal=False, status="not_run", reasons="Diagnostic attempt queued")

    needs_oracle = any(
        resolve_candidate_tier(args.tier, name, args.lane, module, args.season) == "2"
        for name in pending
    )

    with ProcessPoolExecutor(args.workers, initializer=_init_worker, initargs=(path_arg,)) as pool:
        reference = pool.submit(_run, (champion, season, start_gw, end_gw, False))
        oracle_reference = pool.submit(_run, (champion, season, start_gw, end_gw, True)) if needs_oracle else None

        active_futures = {}
        for name in pending:
            eff_tier = resolve_candidate_tier(args.tier, name, args.lane, module, args.season)
            if eff_tier == "2":
                f = pool.submit(_run, (name, season, start_gw, end_gw, True))
                active_futures[f] = (name, eff_tier, True)
            else:
                f = pool.submit(_run, (name, season, start_gw, end_gw, False))
                active_futures[f] = (name, eff_tier, False)

        base: WalkforwardResult | None = None
        base_oracle: WalkforwardResult | None = None

        while active_futures:
            done_future = next(as_completed(list(active_futures)))
            name, eff_tier, is_oracle = active_futures.pop(done_future)
            try:
                _, result = done_future.result()
            except Exception as error:
                retain(name, "oracle" if is_oracle else "integrated", terminal=True, status="partial", reasons=f"{type(error).__name__}: {error}")
                print(f"EXECUTION INVALID: {error}")
                leaked = True
                continue

            if is_oracle:
                if base_oracle is None:
                    assert oracle_reference is not None
                    try:
                        base_oracle = oracle_reference.result()[1]
                    except Exception as error:
                        retain(name, "oracle", terminal=True, status="partial", reasons=f"Champion reference: {type(error).__name__}: {error}")
                        leaked = True
                        continue

                try:
                    t2_verdict, weekly = oracle_event_screen(base_oracle, result, target=EVAL_TARGET)
                    if name in prototype_names:
                        c_delta = float(weekly["delta"].to_numpy(dtype=float).mean())
                        check_inert_prototype(name, base_oracle, result, combined_delta=c_delta)
                except ValueError as error:
                    retain(name, "oracle", terminal=True, status="partial", reasons=str(error))
                    leaked = True
                    continue
                except InertPrototypeError as error:
                    retain(name, "oracle", terminal=True, status="partial", reasons=str(error))
                    leaked = True
                    continue
                reasons_str = "; ".join(t2_verdict.reasons)
                retained = retain(name, "oracle", terminal=not t2_verdict.passed, reference=base_oracle, candidate=result, weekly=weekly,
                       **{"pass": t2_verdict.passed, "combined_delta": t2_verdict.oracle_delta, "min_effect": 0.0,
                          "segs": None, "boot_p_gt0": t2_verdict.bootstrap_p, "guardrails_passed": t2_verdict.passed,
                          "reasons": reasons_str})
                if not retained:
                    continue

                if not t2_verdict.passed:
                    reasons_str = "tier2_oracle_fail: " + "; ".join(t2_verdict.reasons)
                    boot_str = "n/a" if t2_verdict.bootstrap_p is None else f"{t2_verdict.bootstrap_p:.3f}"
                    print(f"{name}: ORACLE_SCREEN_NOT_PASSED delta {t2_verdict.oracle_delta:+.4f} segments unassessed boot P {boot_str} {reasons_str}", flush=True)
                else:
                    print(f"{name}: Tier 2 Oracle Event Gate PASSED (delta {t2_verdict.oracle_delta:+.4f}, P={t2_verdict.bootstrap_p}); queueing Tier 3 walkforward...", flush=True)
                    f3 = pool.submit(_run, (name, season, start_gw, end_gw, False))
                    active_futures[f3] = (name, "3", False)
            else:
                if base is None:
                    try:
                        base = reference.result()[1]
                    except Exception as error:
                        retain(name, "integrated", terminal=True, status="partial", reasons=f"Champion reference: {type(error).__name__}: {error}")
                        leaked = True
                        continue

                try:
                    weekly = paired_weekly_regret(base.df_eval, result.df_eval, EVAL_TARGET)
                    verdict = compare_to_reference(base, result, bootstrap_min_p=bar)
                    if name in prototype_names:
                        check_inert_prototype(
                            name,
                            base,
                            result,
                            combined_delta=verdict.combined_primary_delta,
                        )
                except (ValueError, InertPrototypeError) as error:
                    retain(name, "integrated", terminal=True, status="partial", reasons=str(error))
                    leaked = True
                    continue

                is_pass = verdict.passed
                reasons_list = list(verdict.reasons)

                if eff_tier == "1":
                    try:
                        t1_verdict = evaluate_minutes_from_eval_frames(base.df_eval, result.df_eval)
                    except (ValueError, TypeError) as error:
                        retain(name, "minutes", terminal=True, status="partial", reasons=str(error))
                        continue
                    if not t1_verdict.passed:
                        is_pass = False
                        reasons_list = [f"tier1_minutes_fail: {r}" for r in t1_verdict.reasons] + reasons_list

                retain(name, "minutes" if eff_tier == "1" else "integrated", terminal=True, reference=base, candidate=result, weekly=weekly,
                       **{"pass": is_pass, "combined_delta": verdict.combined_primary_delta,
                          "min_effect": verdict.min_effect, "segs": verdict.segment_wins, "boot_p_gt0": verdict.bootstrap_p,
                          "guardrails_passed": verdict.guardrails_passed, "reasons": "; ".join(reasons_list)})
                boot = "n/a" if verdict.bootstrap_p is None else f"{verdict.bootstrap_p:.3f}"
                print(f"{name}: {'SCREEN_PASS' if is_pass else 'SCREEN_NOT_PASSED'} delta {verdict.combined_primary_delta:+.4f} "
                      f"(min {verdict.min_effect:.4f}) segs {verdict.segment_wins}/3 boot P {boot} {'; '.join(reasons_list)}", flush=True)
    pos = count_grid_positives(args.out, season=args.season, data_season=season.name, champion=champion, gw_range=gw_range, variants=challengers, identities=identities)
    print(f"Wrote {written} stage/attempt rows -> {store.output} (integrated_grid_positives={pos}/{len(challengers)})")
    return 2 if leaked else 0


if __name__ == "__main__":
    raise SystemExit(main())

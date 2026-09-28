"""Explore-candidate smoke harness: prototypes vs Champion on 2025-26 dev season through real gate code.

    uv run python .agents/skills/explore-candidate/smoke.py <prototypes.py> [--gw_range 1-38] [--workers 4]
    uv run python .agents/skills/explore-candidate/smoke.py --model <registered_name>
    uv run python .agents/skills/explore-candidate/smoke.py <prototypes.py> --audit_only

Prototype file exports ``PROTOTYPES: dict[str, type[BaseModel]]`` and ``FEATURES: dict[str, tuple[str, ...]]``
(entries ``features.<col>`` / ``history.<col>`` / ``local.<key>``). Exit 2 = audit or leakage failure.
"""

from __future__ import annotations

import argparse
import ast
import csv
import importlib.util
import sys
from concurrent.futures import ProcessPoolExecutor
from datetime import date
from pathlib import Path
from types import ModuleType

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from backtesting import walkforward  # noqa: E402
from backtesting.model_evaluation import compare_to_reference  # noqa: E402
from backtesting.walkforward import LEDGER_COMPONENTS, WalkforwardConfig, WalkforwardResult, run_walkforward_backtest  # noqa: E402
from features.builder import TERMINAL_PLAYER_COLUMNS  # noqa: E402
from models import get_model  # noqa: E402
from models.base import BaseModel  # noqa: E402
from models.selection import load_model_selection  # noqa: E402

DEV_DATA = ROOT / "data/archive/2025-26/processed"
DEV_SEED = ROOT / "data/archive/2024-25/processed"
DEFAULT_OUT = ROOT / ".tmp/agent/explore-candidate/smoke_results.csv"
BANNED_SOURCE = ("players.parquet", "read_parquet", "read_csv", "open(", "2026-27", "data/archive")
SOURCES = {"features", "history", "local"}
ALLOWED_LITERALS = {"player_id", "fixture_id", "gameweek_id", "projected_points", "projected_minutes", *LEDGER_COMPONENTS}
COLUMN_KEYWORDS = {"columns", "subset", "on", "by"}


class LeakageError(RuntimeError):
    pass


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


def _run(job: tuple[str, int, int]) -> tuple[str, WalkforwardResult]:
    name, start_gw, end_gw = job
    config = WalkforwardConfig(
        model_name=name, data_dir=DEV_DATA, start_gw=start_gw, end_gw=end_gw, seed_processed_dir=DEV_SEED, eval_target="blended_points"
    )
    return name, run_walkforward_backtest(config)


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke prototypes vs Champion (2025-26 dev season, real gate).")
    parser.add_argument("prototypes", nargs="?", type=Path)
    parser.add_argument("--model", action="append", default=[], help="Registered model name (repeatable)")
    parser.add_argument("--gw_range", default="1-38")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--lane", default="")
    parser.add_argument("--audit_only", action="store_true")
    args = parser.parse_args()

    prototype_names: list[str] = []
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

    start_gw, end_gw = map(int, args.gw_range.split("-"))
    champion = load_model_selection().champion
    jobs = [(name, start_gw, end_gw) for name in (champion, *challengers)]
    path_arg = str(args.prototypes.resolve()) if args.prototypes else None
    try:
        with ProcessPoolExecutor(args.workers, initializer=_init_worker, initargs=(path_arg,)) as pool:
            results = dict(pool.map(_run, jobs))
    except LeakageError as error:
        print(f"LEAKAGE FAIL: {error}")
        return 2

    rows = []
    for name in challengers:
        verdict = compare_to_reference(results[champion], results[name])
        rows.append({
            "date": date.today().isoformat(), "lane": args.lane, "variant": name, "champion": champion,
            "gw_range": args.gw_range, "pass": verdict.passed, "combined_delta": verdict.combined_primary_delta,
            "min_effect": verdict.min_effect, "segs": verdict.segment_wins, "boot_p_gt0": verdict.bootstrap_p,
            "guardrails_passed": verdict.guardrails_passed, "reasons": "; ".join(verdict.reasons),
            "source": str(args.prototypes or "registered"),
        })
        boot = "n/a" if verdict.bootstrap_p is None else f"{verdict.bootstrap_p:.3f}"
        print(f"{name}: {'PASS' if verdict.passed else 'FAIL'} delta {verdict.combined_primary_delta:+.4f} "
              f"(min {verdict.min_effect:.4f}) segs {verdict.segment_wins}/3 boot P {boot} {'; '.join(verdict.reasons)}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    new_file = not args.out.exists()
    with args.out.open("a", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        if new_file:
            writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

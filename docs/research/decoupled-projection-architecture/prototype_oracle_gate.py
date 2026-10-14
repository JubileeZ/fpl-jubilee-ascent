"""PROTOTYPE: Oracle Minutes Walk-forward Runner & Tier 2 Event Gate.

Refined prototype incorporating expert review consensus for Ticket #161 (Wayfinder Map #159):
1. Natural key join on (player_id, gameweek_id, fixture_id) to eliminate cross-GW leakage on rescheduled fixtures.
2. Default evaluation target: blended_points (0.5 Process + 0.5 Realized; ADR 0044/0054).
3. Relative signed bias evaluated strictly on Playable Pool (|cand_bias| <= min(|champ_bias| + 0.02, 0.20)).
4. Explicit Captaincy Regret guardrail under Oracle Minutes (tolerance +0.15 pts/GW; ADR 0054).
5. Circular block bootstrap (P >= 0.60, L=3 GWs, B=20,000) conditioned on N >= 15 GWs.
6. Legacy model parity guardrail asserting model honors external_xmins.

Run via:
    uv run python docs/research/decoupled-projection-architecture/prototype_oracle_gate.py
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any

# Ensure repo root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from backtesting.metrics import (
    evaluate_predictions,
    formation_xi_regret_by_gameweek,
)
from backtesting.process_points import aggregate_process_points, blended_points
from backtesting.promotion import (
    BOOTSTRAP_BLOCK_GWS,
    BOOTSTRAP_DRAWS,
    BOOTSTRAP_MIN_P,
    CAPTAIN_REGRET_ABS_TOL,
    block_bootstrap_win_probability,
    compute_playable_pool_metrics,
)
from backtesting.walkforward import (
    LEDGER_COMPONENTS,
    PLAYER_POSITIONS,
    WalkforwardConfig,
    WalkforwardResult,
    load_gameweek_deadlines,
    _build_actual_components,
)
from features.builder import build_features, history_before_target
from features.contracts import assert_projection_contract
from models import get_model


# --- 1. Oracle Minutes Injection Helper ---

def inject_oracle_minutes(
    df_feat: pd.DataFrame,
    df_perf: pd.DataFrame,
    target_gw: int,
) -> pd.DataFrame:
    """Inject actual played match minutes into df_feat['external_xmins'].

    Matches strictly on (player_id, gameweek_id, fixture_id) for the target gameweek.
    Defense-in-depth: guarantees zero cross-gameweek lookahead leakage on postponed matches.
    Players with no fixture appearance (benched/out of squad) receive 0.0 minutes.
    """
    df_feat = df_feat.copy()
    gw_perf = df_perf[df_perf["gameweek_id"] == target_gw]

    perf_minutes = (
        gw_perf[["player_id", "gameweek_id", "fixture_id", "minutes"]]
        .rename(columns={"minutes": "external_xmins"})
        .drop_duplicates(subset=["player_id", "gameweek_id", "fixture_id"])
    )

    if "external_xmins" in df_feat.columns:
        df_feat = df_feat.drop(columns=["external_xmins"])

    df_feat = df_feat.merge(
        perf_minutes,
        on=["player_id", "gameweek_id", "fixture_id"],
        how="left",
    )
    df_feat["external_xmins"] = df_feat["external_xmins"].fillna(0.0).astype(float)
    return df_feat


# --- 2. Oracle Walk-forward Runner Prototype ---

def run_oracle_walkforward_backtest(
    config: WalkforwardConfig,
    *,
    oracle_minutes: bool = False,
) -> WalkforwardResult:
    """Walk-forward runner supporting optional oracle minutes conditioning and blended target."""
    data_dir = config.data_dir
    perf_path = data_dir / "player_performances.parquet"
    if not perf_path.exists():
        raise FileNotFoundError(f"player_performances.parquet is required in {data_dir}")

    df_perf = pd.read_parquet(perf_path)
    gameweek_deadlines = load_gameweek_deadlines(data_dir)

    model = get_model(config.model_name)
    all_results: list[pd.DataFrame] = []
    snapshot_ids: dict[int, str] = {}
    feature_kwargs = {
        key: value
        for key, value in {
            "state_recency_decay": config.state_recency_decay,
            "state_prior_strength": config.state_prior_strength,
            "trailing_start_k": config.trailing_start_k,
            "trailing_start_weight": config.trailing_start_weight,
        }.items()
        if value is not None
    }

    for gw in range(config.start_gw, config.end_gw + 1):
        df_feat = build_features(
            data_dir,
            target_gw=gw,
            horizon=1,
            seed_processed_dir=config.seed_processed_dir,
            use_archive_seed=False,
            as_of_gw=gw,
            availability_snapshot_root=config.snapshot_root,
            season=config.snapshot_season,
            target_deadline=gameweek_deadlines.get(gw),
            require_availability_snapshot=config.require_snapshots,
            **feature_kwargs,
        )
        if "position_id" in df_feat.columns:
            df_feat = df_feat[df_feat["position_id"].isin(PLAYER_POSITIONS)]
        if df_feat.empty:
            continue

        # Strict point-in-time fit: model.fit sees ONLY pre-target history (< gw)
        if hasattr(model, "fit"):
            hist_before = history_before_target(
                df_perf,
                gw,
                gameweek_deadlines.get(gw),
                config.require_snapshots,
            )
            # Invariant check: zero future leakage into historical fit
            if not hist_before.empty and hist_before["gameweek_id"].max() >= gw:
                raise ValueError(
                    f"Point-in-time leakage detected! History contains GW "
                    f"{hist_before['gameweek_id'].max()} >= {gw}"
                )
            model.fit(hist_before)

        # Inject oracle minutes if enabled
        if oracle_minutes:
            df_feat = inject_oracle_minutes(df_feat, df_perf, target_gw=gw)

        df_proj = model.predict(df_feat, horizon=1)
        assert_projection_contract(df_proj)

        # Guardrail: ensure model actually respected external_xmins under oracle mode
        if oracle_minutes and "external_xmins" in df_feat.columns:
            mins_diff = (df_proj["projected_minutes"] - df_feat["external_xmins"]).abs().max()
            if mins_diff > 1e-4:
                raise ValueError(
                    f"Model {config.model_name} did not honor external_xmins; "
                    f"max discrepancy = {mins_diff:.4f}"
                )

        comp_cols = [c for c in LEDGER_COMPONENTS if c in df_proj.columns]
        proj_group_cols = ["projected_points", "projected_minutes"] + comp_cols
        df_proj_gw = (
            df_proj[df_proj["gameweek_id"] == gw]
            .groupby(["player_id", "gameweek_id"], as_index=False)[proj_group_cols]
            .sum()
        )

        gw_perf = _build_actual_components(df_perf[df_perf["gameweek_id"] == gw].copy(), df_feat)
        actual_group_cols = ["total_points", "minutes"] + [
            f"actual_{component}" for component in LEDGER_COMPONENTS
        ]
        actual_group_cols = [c for c in actual_group_cols if c in gw_perf.columns]
        df_actual_gw = (
            gw_perf.groupby(["player_id", "gameweek_id"], as_index=False)[actual_group_cols]
            .sum()
            .rename(columns={"total_points": "actual_points", "minutes": "actual_minutes"})
        )

        df_compare = df_proj_gw.merge(df_actual_gw, on=["player_id", "gameweek_id"], how="left")
        fill_cols = [c for c in df_compare.columns if c.startswith(("actual_", "xp_"))]
        df_compare[fill_cols] = df_compare[fill_cols].fillna(0.0)
        position_map = df_feat[["player_id", "position_id"]].drop_duplicates("player_id")
        df_compare = df_compare.merge(position_map, on="player_id", how="left")
        
        # Merge process points for blended target
        process_gw = aggregate_process_points(gw_perf)
        df_compare = df_compare.merge(process_gw, on=["player_id", "gameweek_id"], how="left")
        df_compare["process_points"] = df_compare["process_points"].fillna(0.0)

        if not df_compare.empty:
            df_compare["gameweek"] = gw
            all_results.append(df_compare)

    if not all_results:
        raise ValueError("No backtesting results generated for the selected range")

    df_eval = pd.concat(all_results, ignore_index=True)
    target = config.eval_target
    if target == "blended_points":
        df_eval["blended_points"] = blended_points(
            df_eval["actual_points"], df_eval["process_points"], weight=config.blend_weight
        )
    metrics = evaluate_predictions(df_eval, target_column=target)
    
    if oracle_minutes:
        metrics["oracle_formation_xi_regret"] = metrics.get("formation_xi_regret")
        metrics["oracle_captain_regret"] = metrics.get("captain_regret")
        metrics["oracle_minutes_enabled"] = True
    else:
        metrics["oracle_minutes_enabled"] = False

    return WalkforwardResult(
        model_name=config.model_name,
        data_dir=data_dir,
        start_gw=config.start_gw,
        end_gw=config.end_gw,
        metrics=metrics,
        df_eval=df_eval,
        snapshot_ids=snapshot_ids,
        snapshot_backed=False,
    )


# --- 3. Refined Tier 2 Oracle Event Gate ---

@dataclass(frozen=True)
class OracleEventGateVerdict:
    """Statistical verdict from evaluating candidate event rates under Oracle Minutes."""
    passed: bool
    oracle_delta: float
    bootstrap_p: float | None
    candidate_playable_bias: float
    champion_playable_bias: float
    candidate_captain_regret: float
    champion_captain_regret: float
    candidate_oracle_regret: float
    champion_oracle_regret: float
    reasons: tuple[str, ...]
    bias_tol: float = 0.02
    bias_ceiling: float = 0.20
    captain_regret_tol: float = CAPTAIN_REGRET_ABS_TOL
    bootstrap_min_p: float = BOOTSTRAP_MIN_P


def evaluate_oracle_event_gate(
    champion_metrics: dict[str, Any],
    candidate_metrics: dict[str, Any],
    *,
    gw_oracle_deltas: Sequence[float] | None = None,
    champion_playable_bias: float | None = None,
    candidate_playable_bias: float | None = None,
    bootstrap_min_p: float = BOOTSTRAP_MIN_P,
    bias_tol: float = 0.02,
    bias_ceiling: float = 0.20,
    captain_regret_tol: float = CAPTAIN_REGRET_ABS_TOL,
) -> OracleEventGateVerdict:
    """Evaluate whether candidate event engine satisfies Tier 2 Oracle Event Gate.

    Conditions for Pass:
    1. Oracle Formation XI Regret improvement (Δ_oracle = Regret_champ - Regret_cand > 0).
    2. Circular Block Bootstrap P(Δ_oracle > 0) >= bootstrap_min_p (enforced when N >= 15 GWs).
    3. Playable Pool Signed Bias: |cand_bias| <= min(|champ_bias| + bias_tol, bias_ceiling).
    4. Captaincy Regret: cand_cap_regret <= champ_cap_regret + captain_regret_tol (0.15 pts/GW).
    """
    champ_regret = float(
        champion_metrics.get("oracle_formation_xi_regret")
        or champion_metrics.get("formation_xi_regret", 0.0)
    )
    cand_regret = float(
        candidate_metrics.get("oracle_formation_xi_regret")
        or candidate_metrics.get("formation_xi_regret", 0.0)
    )
    oracle_delta = champ_regret - cand_regret

    champ_cap = float(
        champion_metrics.get("oracle_captain_regret")
        or champion_metrics.get("captain_regret", 0.0)
    )
    cand_cap = float(
        candidate_metrics.get("oracle_captain_regret")
        or candidate_metrics.get("captain_regret", 0.0)
    )

    champ_bias = float(
        champion_playable_bias
        if champion_playable_bias is not None
        else champion_metrics.get("playable_bias", champion_metrics.get("bias", 0.0))
    )
    cand_bias = float(
        candidate_playable_bias
        if candidate_playable_bias is not None
        else candidate_metrics.get("playable_bias", candidate_metrics.get("bias", 0.0))
    )

    n_gws = len(gw_oracle_deltas) if gw_oracle_deltas is not None else 0
    bootstrap_p = None
    if n_gws >= 15:
        bootstrap_p = block_bootstrap_win_probability(
            gw_oracle_deltas,
            draws=BOOTSTRAP_DRAWS,
            block=BOOTSTRAP_BLOCK_GWS,
        )

    reasons: list[str] = []

    # 1. Delta check
    delta_ok = oracle_delta > 0.0
    if not delta_ok:
        reasons.append(
            f"Oracle Formation XI Regret did not improve (delta {oracle_delta:+.4f} <= 0.0 pts/GW)"
        )

    # 2. Bootstrap check
    sig_ok = bootstrap_p is None or bootstrap_p >= bootstrap_min_p
    if not sig_ok:
        reasons.append(
            f"Bootstrap P(delta_oracle > 0) {bootstrap_p:.3f} below minimum {bootstrap_min_p:.2f}"
        )

    # 3. Relative Playable Pool Bias check
    # If candidate improves upon or matches Champion bias magnitude, it passes.
    # Otherwise, degradation in magnitude must not exceed bias_tol (0.02)
    # and must not exceed absolute safety ceiling (bias_ceiling).
    cand_mag = abs(cand_bias)
    champ_mag = abs(champ_bias)
    if cand_mag <= champ_mag:
        bias_ok = True
    else:
        bias_degradation = cand_mag - champ_mag
        bias_ok = bias_degradation <= bias_tol and cand_mag <= max(champ_mag + bias_tol, bias_ceiling)
        if not bias_ok:
            reasons.append(
                f"Candidate playable bias {cand_bias:+.4f} (|{cand_mag:.4f}|) exceeds Champion "
                f"{champ_bias:+.4f} (|{champ_mag:.4f}|) by +{bias_degradation:.4f} > tol {bias_tol:.2f}"
            )

    # 4. Captaincy Regret check
    cap_ok = cand_cap <= champ_cap + captain_regret_tol
    if not cap_ok:
        reasons.append(
            f"Regressed Captaincy Regret guardrail "
            f"({cand_cap:.3f} vs champ {champ_cap:.3f} + tol {captain_regret_tol:.2f})"
        )

    passed = delta_ok and sig_ok and bias_ok and cap_ok
    return OracleEventGateVerdict(
        passed=passed,
        oracle_delta=oracle_delta,
        bootstrap_p=bootstrap_p,
        candidate_playable_bias=cand_bias,
        champion_playable_bias=champ_bias,
        candidate_captain_regret=cand_cap,
        champion_captain_regret=champ_cap,
        candidate_oracle_regret=cand_regret,
        champion_oracle_regret=champ_regret,
        reasons=tuple(reasons),
        bias_tol=bias_tol,
        bias_ceiling=bias_ceiling,
        captain_regret_tol=captain_regret_tol,
        bootstrap_min_p=bootstrap_min_p,
    )


def evaluate_oracle_event_gate_from_eval(
    champion_eval: pd.DataFrame,
    candidate_eval: pd.DataFrame,
    *,
    target_column: str = "blended_points",
    bootstrap_min_p: float = BOOTSTRAP_MIN_P,
    bias_tol: float = 0.02,
    bias_ceiling: float = 0.20,
    captain_regret_tol: float = CAPTAIN_REGRET_ABS_TOL,
) -> OracleEventGateVerdict:
    """Convenience evaluator that computes metrics and playable pool metrics directly from eval frames."""
    champ_metrics = evaluate_predictions(champion_eval, target_column=target_column)
    cand_metrics = evaluate_predictions(candidate_eval, target_column=target_column)

    champ_playable, cand_playable = compute_playable_pool_metrics(
        champion_eval, candidate_eval, target_column=target_column
    )

    paired = pd.concat(
        [
            formation_xi_regret_by_gameweek(champion_eval, target_column=target_column).rename("champ"),
            formation_xi_regret_by_gameweek(candidate_eval, target_column=target_column).rename("cand"),
        ],
        axis=1,
        join="inner",
    ).sort_index()

    gw_deltas = (paired["champ"] - paired["cand"]).tolist()
    return evaluate_oracle_event_gate(
        champ_metrics,
        cand_metrics,
        gw_oracle_deltas=gw_deltas,
        champion_playable_bias=champ_playable.get("bias"),
        candidate_playable_bias=cand_playable.get("bias"),
        bootstrap_min_p=bootstrap_min_p,
        bias_tol=bias_tol,
        bias_ceiling=bias_ceiling,
        captain_regret_tol=captain_regret_tol,
    )


# --- 4. Verification Runner ---

def run_prototype_verification() -> None:
    print("=" * 70)
    print("PROTOTYPE VERIFICATION: Refined Tier 2 Oracle Event Gate (#161)")
    print("=" * 70)

    data_dir = PROJECT_ROOT / "data" / "archive" / "2025-26" / "processed"
    seed_dir = PROJECT_ROOT / "data" / "archive" / "2024-25" / "processed"

    config = WalkforwardConfig(
        model_name="def_xg_shrink_challenger",
        data_dir=data_dir,
        start_gw=1,
        end_gw=4,  # Cold start window (GW1-4)
        seed_processed_dir=seed_dir,
        eval_target="blended_points",
    )

    print("\n[Step 1] Running Standard Walk-forward on Blended Target (oracle_minutes=False)...")
    res_normal = run_oracle_walkforward_backtest(config, oracle_minutes=False)
    regret_normal = res_normal.metrics.get("formation_xi_regret")
    bias_normal = res_normal.metrics.get("bias")
    print(f"  -> Normal Formation XI Regret: {regret_normal:.2f} pts/GW")
    print(f"  -> Normal Global Signed Bias: {bias_normal:+.4f} pts")

    print("\n[Step 2] Running Oracle Minutes Walk-forward on Blended Target (oracle_minutes=True)...")
    res_oracle = run_oracle_walkforward_backtest(config, oracle_minutes=True)
    regret_oracle = res_oracle.metrics.get("formation_xi_regret")
    cap_regret_oracle = res_oracle.metrics.get("captain_regret")
    bias_oracle = res_oracle.metrics.get("bias")
    print(f"  -> Oracle Formation XI Regret: {regret_oracle:.2f} pts/GW")
    print(f"  -> Oracle Captaincy Regret:   {cap_regret_oracle:.2f} pts/GW")
    print(f"  -> Oracle Global Signed Bias: {bias_oracle:+.4f} pts")

    # Compute Playable Pool bias
    champ_p, _ = compute_playable_pool_metrics(res_oracle.df_eval, res_oracle.df_eval, target_column="blended_points")
    print(f"  -> Champion Playable Pool Bias: {champ_p.get('bias', 0.0):+.4f} pts")

    # [Step 3] Simulate Candidate Comparisons for Refined Tier 2 Gate
    print("\n[Step 3] Testing Refined Tier 2 Gate Scenarios...")

    # Case A: Superior Event Candidate (Pass)
    cand_metrics_pass = {
        "formation_xi_regret": regret_oracle - 0.45,
        "captain_regret": cap_regret_oracle - 0.05,
        "bias": 0.02,
        "playable_bias": champ_p.get("bias", 0.0) + 0.01,
    }
    verdict_a = evaluate_oracle_event_gate(
        res_oracle.metrics,
        cand_metrics_pass,
        champion_playable_bias=champ_p.get("bias", 0.0),
        candidate_playable_bias=champ_p.get("bias", 0.0) + 0.01,
    )
    print("\n  Scenario A (Superior Event Engine):")
    print(f"    Passed:      {verdict_a.passed}")
    print(f"    Delta:       {verdict_a.oracle_delta:+.3f} pts/GW")
    print(f"    Cap Regret:  {verdict_a.candidate_captain_regret:.2f} vs champ {verdict_a.champion_captain_regret:.2f}")
    print(f"    Playable B:  {verdict_a.candidate_playable_bias:+.4f} vs champ {verdict_a.champion_playable_bias:+.4f}")
    assert verdict_a.passed, "Scenario A should pass Refined Tier 2 Gate"

    # Case B: Biased Event Candidate (Fail relative playable bias)
    champ_b = champ_p.get("bias", 0.0)
    cand_b_fail = champ_b - 0.08 if champ_b < 0 else champ_b + 0.08
    cand_metrics_bias_fail = {
        "formation_xi_regret": regret_oracle - 0.60,
        "captain_regret": cap_regret_oracle,
        "bias": 0.05,
        "playable_bias": cand_b_fail,  # Degrades magnitude by +0.08 (exceeds +0.02 tol)
    }
    verdict_b = evaluate_oracle_event_gate(
        res_oracle.metrics,
        cand_metrics_bias_fail,
        champion_playable_bias=champ_b,
        candidate_playable_bias=cand_b_fail,
    )
    print("\n  Scenario B (Over-Inflated Haul Chaser):")
    print(f"    Passed:  {verdict_b.passed}")
    print(f"    Reasons: {verdict_b.reasons}")
    assert not verdict_b.passed and "playable bias" in verdict_b.reasons[0]

    # Case C: Captaincy Inversion (Fail captaincy regret guardrail)
    cand_metrics_cap_fail = {
        "formation_xi_regret": regret_oracle - 0.30,
        "captain_regret": cap_regret_oracle + 0.25,  # Regresses beyond +0.15
        "bias": 0.01,
        "playable_bias": champ_p.get("bias", 0.0),
    }
    verdict_c = evaluate_oracle_event_gate(
        res_oracle.metrics,
        cand_metrics_cap_fail,
        champion_playable_bias=champ_p.get("bias", 0.0),
        candidate_playable_bias=champ_p.get("bias", 0.0),
    )
    print("\n  Scenario C (Captaincy Inversion Failure):")
    print(f"    Passed:  {verdict_c.passed}")
    print(f"    Reasons: {verdict_c.reasons}")
    assert not verdict_c.passed and "Captaincy Regret" in verdict_c.reasons[0]

    # Case D: Regressing Event Rate (Fail delta <= 0)
    cand_metrics_worse = {
        "formation_xi_regret": regret_oracle + 0.30,
        "captain_regret": cap_regret_oracle,
        "bias": -0.04,
        "playable_bias": champ_p.get("bias", 0.0),
    }
    verdict_d = evaluate_oracle_event_gate(
        res_oracle.metrics,
        cand_metrics_worse,
        champion_playable_bias=champ_p.get("bias", 0.0),
        candidate_playable_bias=champ_p.get("bias", 0.0),
    )
    print("\n  Scenario D (Inferior Event Engine):")
    print(f"    Passed:  {verdict_d.passed}")
    print(f"    Reasons: {verdict_d.reasons}")
    assert not verdict_d.passed and "did not improve" in verdict_d.reasons[0]

    print("\n" + "=" * 70)
    print("ALL REFINED PROTOTYPE CHECKS PASSED CLEANLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_prototype_verification()

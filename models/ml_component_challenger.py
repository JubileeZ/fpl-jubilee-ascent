"""ML Component Champion Model Candidate (ml_component_challenger).

Implements the zero-leakage decoupled architecture from:
docs/research/ml-component-champion-blueprint/ml-component-champion-blueprint.md

Features:
- Decoupled 3-head M_mins (p_start, p_sub_in, xmins_if_start) with mass preservation & horizon decay.
- Decoupled 4-group M_events (Goals, Assists, Defense, Baseline Non-Scoring BPS).
- 5 rare/discipline components frozen at Champion Empirical Bayes priors.
- Cold-start ramp protecting GW1-3 with 100% Champion fallback.
- Operational Hard DNP (ADR 0056) and Oracle Minutes bypass (ADR 0054).
- Modular ablation toggles for all heads.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from features.contracts import assert_projection_contract
from models.base import (
    cap_projected_minutes,
    resolve_asof_target_gw,
)
from models.def_xg_shrink_challenger import (
    DefXgShrinkChallengerModel,
)
from models.learned_start_challenger import (
    _BONUS_TEMPERATURE,
    _MIN_WEIGHT,
    _weighted_plackett_luce,
    preserve_mass,
)
from models.metrics_component_hybrid import _number
from models.ml_panel_features import (
    CausalFeatureScaler,
    build_causal_panel,
    compute_continuous_neff_alpha,
)
from models.participation_state_hybrid import target_to_states


# --- Numerical Solvers (Track 1 IRLS) ---

def _ridge_linear_solve(X: np.ndarray, y: np.ndarray, lam: float = 20.0) -> np.ndarray:
    """Closed-form Ridge regression with unpenalized intercept."""
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    D = X.shape[1]
    penalty = lam * np.eye(D)
    penalty[0, 0] = 0.0
    return np.linalg.solve(X.T @ X + penalty, X.T @ y)


def _ridge_logistic_irls(
    X: np.ndarray,
    y: np.ndarray,
    offset: np.ndarray | None = None,
    lam: float = 10.0,
    max_iter: int = 20,
) -> np.ndarray:
    """L2-penalized Newton-IRLS logistic regression with unpenalized intercept."""
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    N, D = X.shape
    if offset is None:
        offset = np.zeros(N)
    else:
        offset = np.asarray(offset, dtype=float)
    beta = np.zeros(D)
    penalty = lam * np.eye(D)
    penalty[0, 0] = 0.0

    for _ in range(max_iter):
        eta = np.clip(X @ beta + offset, -15.0, 15.0)
        p = 1.0 / (1.0 + np.exp(-eta))
        w = np.clip(p * (1.0 - p), 1e-5, 0.25)
        grad = X.T @ (y - p) - penalty @ beta
        H = X.T @ (w[:, None] * X) + penalty
        try:
            step = np.linalg.solve(H, grad)
        except np.linalg.LinAlgError:
            step = np.linalg.lstsq(H, grad, rcond=None)[0]
        beta += step
        if np.max(np.abs(step)) < 1e-5:
            break
    return beta


def _ridge_poisson_irls(
    X: np.ndarray,
    y: np.ndarray,
    offset: np.ndarray,
    lam: float = 25.0,
    max_iter: int = 25,
) -> np.ndarray:
    """L2-penalized Newton-IRLS Poisson regression with unpenalized intercept."""
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    offset = np.asarray(offset, dtype=float)
    D = X.shape[1]
    beta = np.zeros(D)
    penalty = lam * np.eye(D)
    penalty[0, 0] = 0.0

    for _ in range(max_iter):
        eta = np.clip(X @ beta + offset, -10.0, 5.0)
        mu = np.exp(eta)
        grad = X.T @ (y - mu) - penalty @ beta
        H = X.T @ (mu[:, None] * X) + penalty
        try:
            step = np.linalg.solve(H, grad)
        except np.linalg.LinAlgError:
            step = np.linalg.lstsq(H, grad, rcond=None)[0]
        beta += step
        if np.max(np.abs(step)) < 1e-5:
            break
    return beta


class MLComponentChallengerModel(DefXgShrinkChallengerModel):
    """Next-generation ML Component Candidate model combining M_mins and M_events.

    Greedy Stacking Configuration:
    - enable_mins_h1: True  (Tier 1 PASS: Δ_MAE = +0.5334 mins, boot P = 0.9963)
    - enable_mins_h2: False (Tier 1 FAIL: Δ_MAE = -0.0559 mins, boot P = 0.0000; dropped)
    - enable_mins_h3: True  (Tier 1 PASS: Δ_MAE = +0.0533 mins, boot P = 1.0000, +1.59% recall)
    - enable_goals:   True  (Tier 2 PASS: Δ_oracle = +0.5286 pts/GW, boot P = 0.9034)
    - enable_assists: True  (Tier 2 PASS: Δ_oracle = +0.0699 pts/GW, boot P = 0.6361)
    - enable_defense: False (Tier 2 FAIL: Δ_oracle = -0.1139 pts/GW, boot P = 0.3260; dropped)
    - enable_bonus:   False (Tier 2 FAIL: Δ_oracle = -0.0391 pts/GW, boot P = 0.4736; dropped)
    """

    def __init__(
        self,
        *,
        enable_mins_h1: bool = True,
        enable_mins_h2: bool = False,
        enable_mins_h3: bool = True,
        enable_goals: bool = True,
        enable_assists: bool = True,
        enable_defense: bool = False,
        enable_bonus: bool = False,
        ramp_span: float = 4.0,
        enable_congestion: bool = False,
        use_neff_alpha: bool = False,
        n_min: float = 3500.0,
        n_full: float = 7500.0,
        n_seed: int = 0,
    ) -> None:
        super().__init__()
        self.enable_mins_h1 = enable_mins_h1
        self.enable_mins_h2 = enable_mins_h2
        self.enable_mins_h3 = enable_mins_h3
        self.enable_goals = enable_goals
        self.enable_assists = enable_assists
        self.enable_defense = enable_defense
        self.enable_bonus = enable_bonus
        self.ramp_span = float(ramp_span)
        self.enable_congestion = enable_congestion
        self.use_neff_alpha = bool(use_neff_alpha)
        self.n_min = float(n_min)
        self.n_full = float(n_full)
        self.n_seed = int(n_seed)

        self._history_df = pd.DataFrame()
        self._last_kickoff_by_player: dict[int, pd.Timestamp] = {}

    @property
    def name(self) -> str:
        return "ml_component_challenger"

    def fit(self, history_df: pd.DataFrame) -> None:
        super().fit(history_df)
        self._history_df = history_df
        if self.enable_congestion and not history_df.empty and "kickoff_time" in history_df.columns:
            valid = history_df.dropna(subset=["kickoff_time", "player_id"])
            if not valid.empty:
                times = pd.to_datetime(valid["kickoff_time"], utc=True, errors="coerce")
                mask = times.notna()
                if mask.any():
                    self._last_kickoff_by_player = (
                        times[mask].groupby(valid.loc[mask, "player_id"].astype(int)).max().to_dict()
                    )
                    return
        self._last_kickoff_by_player = {}

    def predict(self, features_df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        if features_df.empty:
            return super().predict(features_df, horizon)

        orig_index = features_df.index
        features_df = features_df.reset_index(drop=True)

        target_gw = resolve_asof_target_gw(features_df, self._history_df)

        # 1. Cold-start ramp check: GW1-3 or insufficient training rows -> 100% Champion fallback
        n_history_rows = len(self._history_df) if not self._history_df.empty else 0
        if target_gw < 4 or n_history_rows < 500:
            return super().predict(features_df, horizon)

        if self.use_neff_alpha:
            w_ml = compute_continuous_neff_alpha(
                n_in_season=n_history_rows,
                n_seed=self.n_seed,
                n_min=self.n_min,
                n_full=self.n_full,
            )
            if w_ml <= 0.0:
                return super().predict(features_df, horizon)
        else:
            w_ml = min(1.0, max(0.0, (target_gw - 3.0) / self.ramp_span))

        # 2. Check for Oracle Minutes bypass (ADR 0054 / Ticket #161 / Ticket #165)
        has_external_xmins = "external_xmins" in features_df.columns and features_df["external_xmins"].notna().any()

        # 3. Base Champion prediction (provides anchor priors and components)
        champ_proj = super().predict(features_df, horizon)
        if not (self.enable_mins_h1 or self.enable_mins_h2 or self.enable_mins_h3 or
                self.enable_goals or self.enable_assists or self.enable_defense or self.enable_bonus):
            return champ_proj

        # 4. Generate Causal Panel Features
        train_panel, pred_panel = build_causal_panel(self._history_df, features_df, min_train_gw=4)
        if train_panel.empty or pred_panel.empty:
            return champ_proj

        feature_cols = [
            c for c in pred_panel.columns
            if not c.startswith("target_") and c not in ("player_id", "gameweek_id", "fixture_id")
        ]
        scaler = CausalFeatureScaler().fit(train_panel, feature_cols)
        train_scaled = scaler.transform(train_panel)
        pred_scaled = scaler.transform(pred_panel)

        # 5. --- M_mins: 3-Head Participation Modeling ---
        final_p_start = champ_proj["p_start"].to_numpy(dtype=float).copy()
        final_p_sub = champ_proj["p_sub_in"].to_numpy(dtype=float).copy()
        final_p_dnp = champ_proj["p_dnp"].to_numpy(dtype=float).copy()
        final_start_m = champ_proj["xmins_if_start"].to_numpy(dtype=float).copy()
        final_sub_m = champ_proj["xmins_if_sub_in"].to_numpy(dtype=float).copy()
        final_p60_start = champ_proj["p_60_if_start"].to_numpy(dtype=float).copy()
        final_p60_sub = champ_proj["p_60_if_sub_in"].to_numpy(dtype=float).copy()
        final_xmins = champ_proj["projected_minutes"].to_numpy(dtype=float).copy()

        if has_external_xmins:
            # Deterministic Oracle bypass
            for i, (_, row) in enumerate(features_df.iterrows()):
                ext = row.get("external_xmins")
                if pd.notna(ext):
                    p_st, p_sb, p_dn, st_m, sb_m = target_to_states(float(ext))
                    final_p_start[i] = p_st
                    final_p_sub[i] = p_sb
                    final_p_dnp[i] = p_dn
                    final_start_m[i] = st_m
                    final_sub_m[i] = sb_m
                    final_p60_start[i] = min(1.0, max(0.0, (st_m - 45.0) / 30.0))
                    final_p60_sub[i] = min(1.0, max(0.0, (sb_m - 45.0) / 30.0))
                    final_xmins[i] = float(ext)
        else:
            # Head 1: p_start
            if self.enable_mins_h1:
                h1_cols = [
                    "s_lag1", "s_lag2", "s_lag3", "s_lag4", "s_lag5", "s_lag6",
                    "min3", "starts6", "since_start", "club_frac",
                    "pos_gk", "pos_def", "pos_mid", "short_turnaround",
                    "transfer_momentum", "price_rel_pos",
                ]
                X_tr = np.column_stack([np.ones(len(train_scaled)), train_scaled[h1_cols].to_numpy()])
                y_tr = train_panel["target_starts"].to_numpy(dtype=float)
                beta_h1 = _ridge_logistic_irls(X_tr, y_tr, lam=10.0)

                X_pr = np.column_stack([np.ones(len(pred_scaled)), pred_scaled[h1_cols].to_numpy()])
                raw_logits = X_pr @ beta_h1
                if self.enable_congestion and self._last_kickoff_by_player and "kickoff_time" in features_df.columns:
                    ko_times = pd.to_datetime(features_df["kickoff_time"], utc=True, errors="coerce")
                    pids = features_df["player_id"].astype(int).values
                    for i_k, pid in enumerate(pids):
                        if pid in self._last_kickoff_by_player and pd.notna(ko_times.iloc[i_k]):
                            diff_days = (ko_times.iloc[i_k] - self._last_kickoff_by_player[pid]).total_seconds() / 86400.0
                            if 0.0 < diff_days < 3.5:
                                raw_logits[i_k] -= 0.20
                raw_p_start = 1.0 / (1.0 + np.exp(-np.clip(raw_logits, -10.0, 10.0)))

                # Mass preservation & horizon decay per gameweek
                for gw, group in pred_panel.groupby("gameweek_id"):
                    idx = group.index.to_numpy()
                    target_mass = float(np.sum(final_p_start[idx]))
                    p_preserved = preserve_mass(raw_p_start[idx], target=target_mass, cap=0.99)
                    h = max(0.0, float(gw - target_gw))
                    decay = 0.5 ** h
                    final_p_start[idx] = final_p_start[idx] + w_ml * decay * (p_preserved - final_p_start[idx])

            # Head 2: p_sub_in
            if self.enable_mins_h2:
                non_starts_tr = train_panel["target_starts"] == 0
                if np.sum(non_starts_tr) > 50:
                    h2_cols = ["sub_lag1", "sub_lag2", "sub_lag3", "s_lag1", "min3", "pos_gk", "pos_def", "pos_mid", "price_rel_pos"]
                    X_tr_sub = np.column_stack([np.ones(np.sum(non_starts_tr)), train_scaled.loc[non_starts_tr, h2_cols].to_numpy()])
                    y_tr_sub = train_panel.loc[non_starts_tr, "target_sub"].to_numpy(dtype=float)
                    beta_h2 = _ridge_logistic_irls(X_tr_sub, y_tr_sub, lam=10.0)

                    X_pr_sub = np.column_stack([np.ones(len(pred_scaled)), pred_scaled[h2_cols].to_numpy()])
                    raw_sub_p = 1.0 / (1.0 + np.exp(-np.clip(X_pr_sub @ beta_h2, -10.0, 10.0)))

                    for gw, group in pred_panel.groupby("gameweek_id"):
                        idx = group.index.to_numpy()
                        h = max(0.0, float(gw - target_gw))
                        decay = 0.5 ** h
                        champ_sub_ratio = champ_proj.loc[idx, "p_sub_in"] / np.maximum(1.0 - champ_proj.loc[idx, "p_start"], 1e-4)
                        blended_sub_ratio = champ_sub_ratio + w_ml * decay * (raw_sub_p[idx] - champ_sub_ratio)
                        blended_sub_ratio = np.clip(blended_sub_ratio, 0.0, 0.85)

                        final_p_sub[idx] = (1.0 - final_p_start[idx]) * blended_sub_ratio
                        final_p_dnp[idx] = 1.0 - final_p_start[idx] - final_p_sub[idx]

            # Head 3: xmins_if_start
            if self.enable_mins_h3:
                starts_tr = train_panel["target_starts"] == 1
                if np.sum(starts_tr) > 50:
                    h3_cols = ["shrunk_mins_if_start", "early_hook_rate", "short_turnaround", "pos_gk", "pos_def", "pos_mid", "price_rel_pos"]
                    X_tr_dur = np.column_stack([np.ones(np.sum(starts_tr)), train_scaled.loc[starts_tr, h3_cols].to_numpy()])
                    base_mins_tr = train_panel.loc[starts_tr, "shrunk_mins_if_start"].to_numpy()
                    y_tr_dur = train_panel.loc[starts_tr, "target_minutes"].to_numpy() - base_mins_tr
                    beta_h3 = _ridge_linear_solve(X_tr_dur, y_tr_dur, lam=25.0)

                    X_pr_dur = np.column_stack([np.ones(len(pred_scaled)), pred_scaled[h3_cols].to_numpy()])
                    delta_start_m = np.clip(X_pr_dur @ beta_h3, -12.0, 8.0)
                    for gw, group in pred_panel.groupby("gameweek_id"):
                        idx = group.index.to_numpy()
                        h = max(0.0, float(gw - target_gw))
                        decay = 0.5 ** h
                        final_start_m[idx] = np.clip(final_start_m[idx] + w_ml * decay * delta_start_m[idx], 60.0, 90.0)
                        final_p60_start[idx] = np.clip((final_start_m[idx] - 45.0) / 30.0, 0.50, 1.0)

            # Operational Hard DNP (ADR 0056)
            for i, (_, row) in enumerate(features_df.iterrows()):
                is_imm = bool(row.get("is_immediate_next_gw", False))
                has_snap = bool(row.get("has_availability_snapshot", False))
                chance = _number(row, "chance_of_playing", 100.0)
                status = str(row.get("status", "")).lower()
                if is_imm and (
                    (has_snap and chance <= 0.0)
                    or (not has_snap and (chance <= 0.0 or status in {"i", "s", "u", "n"}))
                ):
                    final_p_dnp[i] = 1.0
                    final_p_start[i] = 0.0
                    final_p_sub[i] = 0.0

            # Reconcile expected minutes
            raw_xmins = final_p_start * final_start_m + final_p_sub * final_sub_m
            for i, (_, row) in enumerate(features_df.iterrows()):
                final_xmins[i] = cap_projected_minutes(row, raw_xmins[i])

        # 6. --- M_events: 4-Group Scoring Models ---
        out_df = champ_proj.copy().reset_index(drop=True)
        out_df["p_dnp"] = final_p_dnp
        out_df["p_start"] = final_p_start
        out_df["p_sub_in"] = final_p_sub
        out_df["xmins_if_start"] = final_start_m
        out_df["xmins_if_sub_in"] = final_sub_m
        out_df["p_60_if_start"] = final_p60_start
        out_df["p_60_if_sub_in"] = final_p60_sub
        out_df["projected_minutes"] = final_xmins

        p60_plus = final_p_start * final_p60_start + final_p_sub * final_p60_sub
        xp_mins = final_p_start * (1.0 + final_p60_start) + final_p_sub * (1.0 + final_p60_sub)
        out_df["xp_minutes"] = xp_mins

        pos_ids = pred_panel["pos_gk"] * 1 + pred_panel["pos_def"] * 2 + pred_panel["pos_mid"] * 3 + pred_panel["pos_fwd"] * 4

        # Group A: Goals Multiplier
        if self.enable_goals:
            g_cols = ["shrunk_xg90", "shot_quality_ratio", "club_xg_share", "finishing_offset_90", "team_att_ratio", "opp_def_ratio", "is_home"]
            mask_tr_g = (train_panel["target_minutes"] > 0) & (train_panel["target_expected_goals"] > 0)
            if np.sum(mask_tr_g) > 50:
                X_tr_g = np.column_stack([np.ones(np.sum(mask_tr_g)), train_scaled.loc[mask_tr_g, g_cols].to_numpy()])
                offset_tr = np.log(np.maximum(train_panel.loc[mask_tr_g, "target_minutes"] / 90.0 * np.maximum(train_panel.loc[mask_tr_g, "shrunk_xg90"], 0.01), 1e-4))
                y_tr_g = train_panel.loc[mask_tr_g, "target_goals_blend"].to_numpy()
                beta_g = _ridge_poisson_irls(X_tr_g, y_tr_g, offset_tr, lam=25.0)

                X_pr_g = np.column_stack([np.ones(len(pred_scaled)), pred_scaled[g_cols].to_numpy()])
                raw_mult_g = np.exp(np.clip(X_pr_g @ beta_g, -0.4, 0.4))

                for gw, group in pred_panel.groupby("gameweek_id"):
                    idx = group.index.to_numpy()
                    mean_m = float(np.mean(raw_mult_g[idx])) if len(idx) > 0 else 1.0
                    norm_mult = raw_mult_g[idx] / max(mean_m, 1e-4)

                    # Clamp per position
                    for i_idx, p_idx in enumerate(idx):
                        pos = int(pos_ids.iloc[p_idx])
                        if pos == 1:
                            m_val = 1.0
                        elif pos == 2:
                            m_val = float(np.clip(norm_mult[i_idx], 0.90, 1.10))
                        else:
                            m_val = float(np.clip(norm_mult[i_idx], 0.75, 1.35))
                        out_df.loc[p_idx, "xp_goals"] *= m_val

        # Group B: Assists Multiplier
        if self.enable_assists:
            loo_mult = pred_panel["loo_teammate_finishing"].to_numpy()
            out_df["xp_assists"] *= loo_mult

        # Group C: Defense Multipliers
        if self.enable_defense:
            # GK Saves
            save_mult = pred_panel["opp_save_multiplier"].to_numpy()
            out_df["xp_saves"] *= save_mult
            # Defcon
            defcon_mult = np.clip(pred_panel["opp_pressure_ratio"].to_numpy() ** 0.20, 0.88, 1.15)
            out_df["xp_defcon"] *= defcon_mult

        # Group D: Baseline Non-Scoring BPS
        if self.enable_bonus:
            bps_tr_mask = (train_panel["target_minutes"] >= 30)
            if np.sum(bps_tr_mask) > 50:
                b_cols = ["shrunk_base_bps90", "shrunk_influence90", "team_att_ratio", "opp_def_ratio", "pos_gk", "pos_def", "pos_mid"]
                X_tr_b = np.column_stack([np.ones(np.sum(bps_tr_mask)), train_scaled.loc[bps_tr_mask, b_cols].to_numpy()])
                y_tr_b = train_panel.loc[bps_tr_mask, "target_bps_base"].to_numpy() / (train_panel.loc[bps_tr_mask, "target_minutes"].to_numpy() / 90.0)
                beta_b = _ridge_linear_solve(X_tr_b, y_tr_b, lam=20.0)

                X_pr_b = np.column_stack([np.ones(len(pred_scaled)), pred_scaled[b_cols].to_numpy()])
                pred_base_bps90 = np.clip(X_pr_b @ beta_b, 4.0, 22.0)

                # Recompute xbps
                out_df["xbps"] = (
                    out_df["projected_minutes"] / 90.0 * pred_base_bps90
                    + 24.0 * (out_df["xp_goals"] / 4.0)
                    + 12.0 * (out_df["xp_assists"] / 3.0)
                    + 12.0 * (out_df["xp_clean_sheet"] / 4.0)
                    + 6.0 * (out_df["xp_defcon"] / 2.0)
                    + 2.0 * out_df["xp_saves"]
                )

                # Reallocate bonus fixture by fixture using Plackett-Luce
                for fid, fgroup in out_df.groupby("fixture_id"):
                    if fid is not None and fid >= 0:
                        idx = fgroup.index.to_numpy()
                        mass = np.exp((out_df.loc[idx, "xbps"].to_numpy() - out_df.loc[idx, "xbps"].max()) / _BONUS_TEMPERATURE) * p60_plus[idx]
                        if mass.sum() > _MIN_WEIGHT:
                            allocated = _weighted_plackett_luce(mass)
                            out_df.loc[idx, "xp_bonus"] = allocated

        # Reconcile projected points
        component_cols = [c for c in out_df.columns if c.startswith("xp_")]
        out_df["projected_points"] = out_df[component_cols].sum(axis=1)

        out_df.index = orig_index
        assert_projection_contract(out_df)
        return out_df

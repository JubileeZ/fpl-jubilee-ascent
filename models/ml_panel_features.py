"""Zero-Leakage Causal Panel Feature Engine & Fit-Only Scaler.

Implements Step 1 of ML Component Champion Blueprint (docs/research/ml-component-champion-blueprint/):
1. Single code path for historical training rows and forward prediction rows.
2. Strict causal horizon H_{<g}: every feature for row g uses exclusively data before g.
3. Market / transfer momentum lag invariant: reads price, selected, transfers strictly from H_{<g}.
4. In-memory club ID reconstruction: eliminates external disk lookup.
5. Fit-only standardization and winsorization (CausalFeatureScaler).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import numpy as np
import pandas as pd


_DECAY = 0.95
_MIDFIELDER = 3
_LEAGUE_XG_DEFAULT = 1.35
_PSEUDO_MATCHES = 4.0
_EB_K_PRIOR_DEFAULT = 12.0
_BASE_K = 1080.0  # 12.0 matches * 90 mins (Ticket #168 EB prior strength)
_POSITION_K: dict[int, float] = {1: 1080.0, 2: 2400.0, 3: 1080.0, 4: 1080.0}
_TS_CACHE: dict[object, pd.Timestamp] = {}
_TRAIN_GW_CACHE: dict[tuple[int, int, int], pd.DataFrame] = {}


def _to_timestamp(val: object) -> pd.Timestamp:
    ts = _TS_CACHE.get(val)
    if ts is None:
        ts = pd.to_datetime(val)  # type: ignore[arg-type]
        if len(_TS_CACHE) < 10_000:
            _TS_CACHE[val] = ts
    return ts

# Default position baselines
_START_MINS_PRIOR = {1: 89.0, 2: 82.0, 3: 76.0, 4: 75.0}
_HOOK_RATE_PRIOR = {1: 0.01, 2: 0.12, 3: 0.28, 4: 0.30}
_XG90_PRIOR = {1: 0.00, 2: 0.04, 3: 0.18, 4: 0.35}
_XA90_PRIOR = {1: 0.01, 2: 0.08, 3: 0.18, 4: 0.14}
_CREATIVITY90_PRIOR = {1: 1.0, 2: 12.0, 3: 25.0, 4: 18.0}
_BASE_BPS90_PRIOR = {1: 12.0, 2: 14.0, 3: 13.0, 4: 10.0}
_INFLUENCE90_PRIOR = {1: 18.0, 2: 16.0, 3: 18.0, 4: 20.0}

# Positional price-tier Empirical Bayes priors (cost in 0.1m FPL units, e.g. 50 = £5.0m)
_TIER_PRIORS_XG90: dict[int, dict[int, float]] = {
    1: {40: 0.00, 45: 0.00, 50: 0.00, 55: 0.00},
    2: {40: 0.02, 45: 0.03, 50: 0.05, 55: 0.07, 60: 0.10},
    3: {45: 0.06, 50: 0.09, 55: 0.14, 65: 0.20, 75: 0.26, 85: 0.32, 100: 0.42, 125: 0.52},
    4: {50: 0.18, 55: 0.22, 65: 0.30, 75: 0.38, 85: 0.45, 115: 0.60, 140: 0.72},
}

_TIER_PRIORS_XA90: dict[int, dict[int, float]] = {
    1: {40: 0.00, 45: 0.01, 50: 0.01, 55: 0.01},
    2: {40: 0.03, 45: 0.05, 50: 0.08, 55: 0.12, 60: 0.18},
    3: {45: 0.06, 50: 0.09, 55: 0.13, 65: 0.18, 75: 0.22, 85: 0.26, 100: 0.30, 125: 0.34},
    4: {50: 0.06, 55: 0.08, 65: 0.11, 75: 0.14, 85: 0.16, 115: 0.20, 140: 0.22},
}

_TIER_PRIORS_START_FRAC: dict[int, dict[int, float]] = {
    1: {40: 0.05, 45: 0.65, 50: 0.85, 55: 0.92},
    2: {40: 0.15, 45: 0.60, 50: 0.78, 55: 0.85, 60: 0.90},
    3: {45: 0.15, 50: 0.45, 55: 0.65, 65: 0.78, 75: 0.84, 85: 0.88, 100: 0.92, 125: 0.95},
    4: {50: 0.15, 55: 0.45, 65: 0.70, 75: 0.82, 85: 0.88, 115: 0.92, 140: 0.95},
}


def positional_price_tier_prior(
    position_id: int,
    cost: float,
    metric: str = "xg90",
) -> float:
    """Resolve Empirical Bayes baseline for a player's position and price tier."""
    if metric == "xg90":
        table = _TIER_PRIORS_XG90
        fallback = _XG90_PRIOR.get(position_id, 0.15)
    elif metric == "xa90":
        table = _TIER_PRIORS_XA90
        fallback = _XA90_PRIOR.get(position_id, 0.12)
    elif metric == "start_frac":
        table = _TIER_PRIORS_START_FRAC
        fallback = 0.65
    else:
        return 0.0

    pos_tiers = table.get(int(position_id))
    if not pos_tiers:
        return float(fallback)
    tier_costs = list(pos_tiers.keys())
    closest = min(tier_costs, key=lambda c: abs(c - float(cost)))
    return float(pos_tiers[closest])


def empirical_bayes_shrinkage(
    raw_val: float,
    n_obs: float,
    position_id: int,
    cost: float,
    *,
    k_prior: float = _EB_K_PRIOR_DEFAULT,
    metric: str = "xg90",
) -> float:
    """Shrink a short-panel sample estimate toward its positional price-tier prior."""
    t_obs = max(0.0, float(n_obs))
    k = max(0.0, float(k_prior))
    mu_prior = positional_price_tier_prior(position_id, cost, metric=metric)
    if t_obs + k <= 0.0:
        return mu_prior
    w_sample = t_obs / (t_obs + k)
    return float(w_sample * float(raw_val) + (1.0 - w_sample) * mu_prior)


def compute_effective_sample_size(
    n_in_season: int | float,
    n_seed: int | float = 0,
    *,
    seed_weight: float = 0.5,
) -> float:
    """Compute effective sample size N_eff,g = seed_weight * N_seed + N_in_season,<g."""
    return float(seed_weight * max(0.0, float(n_seed)) + max(0.0, float(n_in_season)))


def compute_continuous_neff_alpha(
    n_in_season: int | float,
    n_seed: int | float = 0,
    *,
    n_min: float = 3500.0,
    n_full: float = 7500.0,
    seed_weight: float = 0.5,
) -> float:
    """Compute continuous sample-size blend weight alpha_g in [0.0, 1.0]."""
    if n_full <= n_min:
        return 1.0
    n_eff = compute_effective_sample_size(n_in_season, n_seed, seed_weight=seed_weight)
    return float(np.clip((n_eff - n_min) / (n_full - n_min), 0.0, 1.0))


@dataclass
class CausalFeatureScaler:
    """Fit-only standardization, percentile winsorization, and short-panel EB shrinkage."""

    clip_quantiles: tuple[float, float] = (0.01, 0.99)
    k_prior: float = _EB_K_PRIOR_DEFAULT
    sparse_threshold: float = 15.0
    feature_cols: list[str] | None = None
    q01_: np.ndarray | None = None
    q99_: np.ndarray | None = None
    means_: np.ndarray | None = None
    stds_: np.ndarray | None = None

    def fit(self, train_df: pd.DataFrame, feature_cols: Sequence[str]) -> CausalFeatureScaler:
        self.feature_cols = list(feature_cols)
        X = train_df[self.feature_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0).to_numpy(dtype=float)
        self.q01_ = np.percentile(X, self.clip_quantiles[0] * 100, axis=0)
        self.q99_ = np.percentile(X, self.clip_quantiles[1] * 100, axis=0)
        X_clipped = np.clip(X, self.q01_, self.q99_)
        self.means_ = np.mean(X_clipped, axis=0)
        std = np.std(X_clipped, axis=0)
        self.stds_ = np.where(std < 1e-6, 1.0, std)
        return self

    def transform(
        self,
        df: pd.DataFrame,
        obs_counts: np.ndarray | pd.Series | None = None,
    ) -> pd.DataFrame:
        if self.feature_cols is None or self.q01_ is None or self.means_ is None or self.stds_ is None:
            raise RuntimeError("Scaler must be fit before calling transform()")
        out = df.copy()
        X = out[self.feature_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0).to_numpy(dtype=float)
        X_clipped = np.clip(X, self.q01_, self.q99_)
        X_scaled = (X_clipped - self.means_) / self.stds_
        if obs_counts is not None:
            t_arr = np.maximum(0.0, np.asarray(obs_counts, dtype=float)).reshape(-1, 1)
            k = max(0.0, float(self.k_prior))
            shrink_w = np.where(t_arr < self.sparse_threshold, t_arr / np.maximum(t_arr + k, 1e-6), 1.0)
            X_scaled = X_scaled * shrink_w
        out[self.feature_cols] = X_scaled
        return out

    def fit_transform(
        self,
        train_df: pd.DataFrame,
        feature_cols: Sequence[str],
        obs_counts: np.ndarray | pd.Series | None = None,
    ) -> pd.DataFrame:
        return self.fit(train_df, feature_cols).transform(train_df, obs_counts=obs_counts)


def _clean_numeric_history(hist: pd.DataFrame) -> pd.DataFrame:
    """Ensure all performance statistics and IDs are properly typed numeric arrays."""
    df = hist.copy()
    num_cols = [
        "minutes", "starts", "goals_scored", "expected_goals", "assists",
        "expected_assists", "creativity", "threat", "influence", "bps",
        "clean_sheets", "goals_conceded", "saves", "price", "transfers_in", "transfers_out"
    ]
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0).astype(float)
    for id_col in ("player_id", "gameweek_id", "fixture_id", "opponent_club_id", "club_id"):
        if id_col in df.columns:
            df[id_col] = pd.to_numeric(df[id_col], errors="coerce").fillna(-1).astype(int)
    return df


def _reconstruct_club_id(hist: pd.DataFrame) -> pd.DataFrame:
    """Reconstruct own club_id in-memory by opposing fixture match."""
    df = _clean_numeric_history(hist)
    if "club_id" in df.columns and (df["club_id"] >= 0).any():
        return df
    if "fixture_id" not in df.columns or "opponent_club_id" not in df.columns or "was_home" not in df.columns:
        return df

    sides = df[["fixture_id", "was_home", "opponent_club_id"]].drop_duplicates(subset=["fixture_id", "was_home"])
    sides = sides.assign(was_home=~sides["was_home"].astype(bool)).rename(columns={"opponent_club_id": "club_id"})
    return df.merge(sides, on=["fixture_id", "was_home"], how="left")


def _build_gw_panel(
    hist_prior: pd.DataFrame,
    target_rows: pd.DataFrame,
    target_gw: int,
    positions: pd.Series,
) -> pd.DataFrame:
    """Build causal feature vector for player-fixtures at target_gw using strictly hist_prior (H_{<target_gw})."""
    out = target_rows.copy().reset_index(drop=True)
    N = len(out)
    if N == 0:
        return out

    # Ensure position_id is mapped
    if "position_id" not in out.columns:
        out["position_id"] = out["player_id"].map(positions).fillna(_MIDFIELDER).astype(int)
    pos_s = out["position_id"].astype(int)

    # 1. League & Club Attack/Defense Priors over H_{<target_gw}
    if not hist_prior.empty and "fixture_id" in hist_prior.columns:
        fx_agg = hist_prior.groupby(["fixture_id", "club_id"], as_index=False).agg(
            xg_for=("expected_goals", "sum"),
            xg_against=("expected_goals", "sum"),  # will join below
            g_for=("goals_scored", "sum"),
            creativity=("creativity", "sum"),
            threat=("threat", "sum"),
            gameweek_id=("gameweek_id", "first"),
        )
        # Match opponent stats
        opp_side = fx_agg[["fixture_id", "club_id", "xg_for", "g_for"]].rename(
            columns={"club_id": "opp_club", "xg_for": "xg_conceded", "g_for": "g_conceded"}
        )
        club_matches = fx_agg.merge(opp_side, on="fixture_id", how="left")
        club_matches = club_matches[club_matches["club_id"] != club_matches["opp_club"]]

        league_xg = float(club_matches["xg_for"].mean()) if not club_matches.empty else _LEAGUE_XG_DEFAULT
        if not np.isfinite(league_xg) or league_xg <= 0:
            league_xg = _LEAGUE_XG_DEFAULT

        # Own club aggression & concession rates
        club_stats = club_matches.groupby("club_id").agg(
            matches=("fixture_id", "count"),
            xg_for=("xg_for", "sum"),
            xg_against=("xg_conceded", "sum"),
            g_against=("g_conceded", "sum"),
            g_for=("g_for", "sum"),
            creativity=("creativity", "sum"),
            threat=("threat", "sum"),
        )
        pseudo = _PSEUDO_MATCHES * league_xg
        denom = club_stats["matches"] + _PSEUDO_MATCHES
        club_att_rate = ((club_stats["xg_for"] + pseudo) / denom).to_dict()
        club_def_rate = ((club_stats["xg_against"] + pseudo) / denom).to_dict()
        club_blend_gc = (((0.65 * club_stats["xg_against"] + 0.35 * club_stats["g_against"]) + pseudo) / denom).to_dict()
        club_crea_match = ((club_stats["creativity"] + _PSEUDO_MATCHES * 20.0) / denom).to_dict()
        club_threat_match = ((club_stats["threat"] + _PSEUDO_MATCHES * 35.0) / denom).to_dict()

        # Opponent recent 3-match trend
        recent_matches = club_matches.sort_values("gameweek_id").groupby("club_id").tail(3)
        recent_stats = recent_matches.groupby("club_id").agg(
            matches=("fixture_id", "count"),
            xg_against=("xg_conceded", "sum"),
        )
        opp_recent_trend = {}
        for c in club_stats.index:
            full_rate = club_def_rate.get(c, league_xg)
            rec_n = recent_stats.loc[c, "matches"] if c in recent_stats.index else 0
            rec_xg = recent_stats.loc[c, "xg_against"] if c in recent_stats.index else 0.0
            rec_rate = (rec_xg + 2.0 * league_xg) / (rec_n + 2.0)
            opp_recent_trend[c] = float(np.clip(rec_rate / max(full_rate, 1e-4), 0.5, 2.0))
    else:
        league_xg = _LEAGUE_XG_DEFAULT
        club_att_rate = {}
        club_def_rate = {}
        club_blend_gc = {}
        club_crea_match = {}
        club_threat_match = {}
        opp_recent_trend = {}

    # 2. Player-level cumulative features over H_{<target_gw}
    player_history = hist_prior[hist_prior["player_id"].isin(out["player_id"])].copy() if not hist_prior.empty else pd.DataFrame()

    # Price / Selected / Transfers baseline
    pos_prices = {}
    if not hist_prior.empty and "price" in hist_prior.columns:
        last_prices = hist_prior.drop_duplicates("player_id", keep="last")
        last_prices = last_prices.assign(pos=last_prices["player_id"].map(positions).fillna(_MIDFIELDER))
        pos_prices = last_prices.groupby("pos")["price"].mean().to_dict()

    # Build feature arrays
    s_lag1 = np.zeros(N)
    s_lag2 = np.zeros(N)
    s_lag3 = np.zeros(N)
    s_lag4 = np.zeros(N)
    s_lag5 = np.zeros(N)
    s_lag6 = np.zeros(N)
    sub_lag1 = np.zeros(N)
    sub_lag2 = np.zeros(N)
    sub_lag3 = np.zeros(N)
    min3 = np.zeros(N)
    since_start = np.full(N, 6.0)
    club_frac = np.zeros(N)
    rest_days = np.full(N, 7.0)
    transfer_momentum = np.zeros(N)
    price_rel_pos = np.zeros(N)
    shrunk_mins_if_start = np.array([_START_MINS_PRIOR.get(p, 78.0) for p in pos_s])
    early_hook_rate = np.array([_HOOK_RATE_PRIOR.get(p, 0.20) for p in pos_s])
    shrunk_xg90 = np.array([_XG90_PRIOR.get(p, 0.15) for p in pos_s])
    shot_quality_ratio = np.ones(N)
    club_xg_share = np.array([_XG90_PRIOR.get(p, 0.15) / _LEAGUE_XG_DEFAULT for p in pos_s])
    finishing_offset_90 = np.zeros(N)
    shrunk_xa90 = np.array([_XA90_PRIOR.get(p, 0.12) for p in pos_s])
    shrunk_creativity90 = np.array([_CREATIVITY90_PRIOR.get(p, 15.0) for p in pos_s])
    creativity_share = np.ones(N)
    loo_teammate_finishing = np.ones(N)
    shrunk_base_bps90 = np.array([_BASE_BPS90_PRIOR.get(p, 12.0) for p in pos_s])
    shrunk_influence90 = np.array([_INFLUENCE90_PRIOR.get(p, 18.0) for p in pos_s])

    # Populate player-specific features
    pids = out["player_id"].to_numpy()
    pos_arr = pos_s.to_numpy()
    if "price" in out.columns:
        now_costs = out["price"].to_numpy(dtype=float)
    elif "now_cost" in out.columns:
        now_costs = out["now_cost"].to_numpy(dtype=float)
    else:
        now_costs = np.full(N, 50.0)
    kickoff_times = out["kickoff_time"].to_numpy() if "kickoff_time" in out.columns else None

    # Pre-extract player summary stats from contiguous sorted numpy arrays for fast O(1) lookup
    player_stats_cache = {}
    if not player_history.empty:
        sort_col = "kickoff_time" if "kickoff_time" in player_history.columns else "gameweek_id"
        player_history = player_history.sort_values(sort_col).sort_values("player_id", kind="mergesort")
        ph_pids = player_history["player_id"].to_numpy()
        unique_pids, split_indices = np.unique(ph_pids, return_index=True)
        end_indices = np.append(split_indices[1:], len(ph_pids))

        ph_starts = player_history["starts"].to_numpy(dtype=float)
        ph_mins = player_history["minutes"].to_numpy(dtype=float)
        ph_gws = player_history["gameweek_id"].to_numpy(dtype=float)
        ph_weights = _DECAY ** np.clip(target_gw - 1 - ph_gws, 0, 38)
        ph_tin = player_history["transfers_in"].to_numpy(dtype=float) if "transfers_in" in player_history.columns else None
        ph_tout = player_history["transfers_out"].to_numpy(dtype=float) if "transfers_out" in player_history.columns else None
        ph_price = player_history["price"].to_numpy(dtype=float) if "price" in player_history.columns else None
        ph_kickoff = player_history["kickoff_time"].to_numpy() if "kickoff_time" in player_history.columns else None
        n_ph = len(ph_pids)
        ph_xg = player_history["expected_goals"].to_numpy(dtype=float) if "expected_goals" in player_history.columns else np.zeros(n_ph)
        ph_g = player_history["goals_scored"].to_numpy(dtype=float) if "goals_scored" in player_history.columns else np.zeros(n_ph)
        ph_xa = player_history["expected_assists"].to_numpy(dtype=float) if "expected_assists" in player_history.columns else np.zeros(n_ph)
        ph_a = player_history["assists"].to_numpy(dtype=float) if "assists" in player_history.columns else np.zeros(n_ph)
        ph_crea = player_history["creativity"].to_numpy(dtype=float) if "creativity" in player_history.columns else np.zeros(n_ph)
        ph_inf = player_history["influence"].to_numpy(dtype=float) if "influence" in player_history.columns else np.zeros(n_ph)
        ph_bps = player_history["bps"].to_numpy(dtype=float) if "bps" in player_history.columns else np.zeros(n_ph)
        ph_cs = player_history["clean_sheets"].to_numpy(dtype=float) if "clean_sheets" in player_history.columns else np.zeros(n_ph)
        ph_saves = player_history["saves"].to_numpy(dtype=float) if "saves" in player_history.columns else np.zeros(n_ph)
        ph_base_bps = ph_bps - (24.0 * ph_g + 12.0 * ph_a + 12.0 * ph_cs + 2.0 * ph_saves)
        ph_club = player_history["club_id"].to_numpy() if "club_id" in player_history.columns else None

        for u_i, pid in enumerate(unique_pids):
            s_i = split_indices[u_i]
            e_i = end_indices[u_i]
            starts = ph_starts[s_i:e_i]
            mins = ph_mins[s_i:e_i]
            n_apps = e_i - s_i
            weights = ph_weights[s_i:e_i]
            eff_mins = float(np.sum(mins * weights))

            tin = float(ph_tin[e_i - 1]) if ph_tin is not None else 0.0
            tout = float(ph_tout[e_i - 1]) if ph_tout is not None else 0.0
            price = float(ph_price[e_i - 1]) if ph_price is not None else 50.0
            initial_price = float(ph_price[s_i]) if ph_price is not None else price

            sl1 = float(starts[-1] >= 1) if n_apps >= 1 else 0.0
            sl2 = float(starts[-2] >= 1) if n_apps >= 2 else 0.0
            sl3 = float(starts[-3] >= 1) if n_apps >= 3 else 0.0
            sl4 = float(starts[-4] >= 1) if n_apps >= 4 else 0.0
            sl5 = float(starts[-5] >= 1) if n_apps >= 5 else 0.0
            sl6 = float(starts[-6] >= 1) if n_apps >= 6 else 0.0

            subl1 = float(mins[-1] > 0 and starts[-1] == 0) if n_apps >= 1 else 0.0
            subl2 = float(mins[-2] > 0 and starts[-2] == 0) if n_apps >= 2 else 0.0
            subl3 = float(mins[-3] > 0 and starts[-3] == 0) if n_apps >= 3 else 0.0

            m3 = float(np.sum(mins[-3:])) / 90.0 if n_apps > 0 else 0.0

            since = 0
            found_start = False
            for s in reversed(starts):
                if s >= 1:
                    found_start = True
                    break
                since += 1
            s_since = float(min(6.0, since if found_start else 6.0))
            c_frac = float(np.clip(float(np.sum(starts)) / max(float(n_apps), 1.0), 0.0, 1.0))
            last_kickoff = ph_kickoff[e_i - 1] if ph_kickoff is not None and n_apps > 0 else None

            start_mask = starts >= 1
            if np.any(start_mask):
                st_mins = mins[start_mask]
                st_weights = weights[start_mask]
                sum_st_w = float(np.sum(st_weights))
                weighted_st_mins = float(np.sum(st_mins * st_weights))
                hooks = ((st_mins >= 45.0) & (st_mins < 70.0)).astype(float)
                weighted_hooks = float(np.sum(hooks * st_weights))
            else:
                sum_st_w = 0.0
                weighted_st_mins = 0.0
                weighted_hooks = 0.0

            xg_arr = ph_xg[s_i:e_i]
            g_arr = ph_g[s_i:e_i]
            xa_arr = ph_xa[s_i:e_i]
            crea_arr = ph_crea[s_i:e_i]
            inf_arr = ph_inf[s_i:e_i]
            base_bps_arr = ph_base_bps[s_i:e_i]

            weighted_xg = float(np.sum(xg_arr * weights))
            tot_g = float(np.sum(g_arr))
            tot_xg = float(np.sum(xg_arr))
            tot_m = float(np.sum(mins))
            weighted_xa = float(np.sum(xa_arr * weights))
            weighted_crea = float(np.sum(crea_arr * weights))
            weighted_inf = float(np.sum(inf_arr * weights))
            weighted_base_bps = float(np.sum(base_bps_arr * weights))

            player_stats_cache[pid] = {
                "tin": tin, "tout": tout, "price": price, "initial_price": initial_price,
                "n_apps": float(n_apps), "last_kickoff": last_kickoff,
                "sl1": sl1, "sl2": sl2, "sl3": sl3, "sl4": sl4, "sl5": sl5, "sl6": sl6,
                "subl1": subl1, "subl2": subl2, "subl3": subl3, "m3": m3,
                "s_since": s_since, "c_frac": c_frac, "eff_mins": eff_mins,
                "sum_st_w": sum_st_w, "weighted_st_mins": weighted_st_mins, "weighted_hooks": weighted_hooks,
                "weighted_xg": weighted_xg, "tot_g": tot_g, "tot_xg": tot_xg, "tot_m": tot_m,
                "weighted_xa": weighted_xa, "weighted_crea": weighted_crea, "weighted_inf": weighted_inf,
                "weighted_base_bps": weighted_base_bps,
                "club_arr": ph_club[s_i:e_i] if ph_club is not None else None,
                "weights_arr": weights,
                "g_arr": g_arr,
                "xg_arr": xg_arr,
            }

    for idx in range(N):
        pid = pids[idx]
        pos = int(pos_arr[idx])
        pdata = player_stats_cache.get(pid)

        if pdata is not None:
            init_cost = pdata["initial_price"]
            n_apps_val = pdata["n_apps"]
            # Transfer momentum & price
            transfer_momentum[idx] = np.clip(np.log((pdata["tin"] + 100.0) / (pdata["tout"] + 100.0)), -3.0, 3.0)
            price_rel_pos[idx] = (pdata["price"] - pos_prices.get(pos, 50.0)) / 10.0

            # Lags & Participation
            s_lag1[idx] = pdata["sl1"]
            s_lag2[idx] = pdata["sl2"]
            s_lag3[idx] = pdata["sl3"]
            s_lag4[idx] = pdata["sl4"]
            s_lag5[idx] = pdata["sl5"]
            s_lag6[idx] = pdata["sl6"]

            sub_lag1[idx] = pdata["subl1"]
            sub_lag2[idx] = pdata["subl2"]
            sub_lag3[idx] = pdata["subl3"]

            min3[idx] = pdata["m3"]
            since_start[idx] = pdata["s_since"]
            if n_apps_val < 15.0:
                club_frac[idx] = empirical_bayes_shrinkage(
                    pdata["c_frac"],
                    n_apps_val,
                    pos,
                    init_cost,
                    k_prior=_EB_K_PRIOR_DEFAULT,
                    metric="start_frac",
                )
            else:
                club_frac[idx] = pdata["c_frac"]

            if kickoff_times is not None and pdata["last_kickoff"] is not None:
                try:
                    diff_days = (_to_timestamp(kickoff_times[idx]) - _to_timestamp(pdata["last_kickoff"])).total_seconds() / 86400.0
                    rest_days[idx] = float(np.clip(diff_days, 2.0, 14.0))
                except Exception:
                    pass

            eff_mins = pdata["eff_mins"]
            if pdata["sum_st_w"] > 0:
                mu_start = _START_MINS_PRIOR.get(pos, 78.0)
                shrunk_mins_if_start[idx] = (pdata["weighted_st_mins"] + 4.0 * mu_start) / (pdata["sum_st_w"] + 4.0)
                pi_hook = _HOOK_RATE_PRIOR.get(pos, 0.20)
                early_hook_rate[idx] = (pdata["weighted_hooks"] + 4.0 * pi_hook) / (pdata["sum_st_w"] + 4.0)

            # Event rates with positional price-tier Empirical Bayes priors (Ticket #168)
            k_xg = _POSITION_K.get(pos, _BASE_K)
            prior_xg = positional_price_tier_prior(pos, init_cost, metric="xg90")
            shrunk_xg90[idx] = (pdata["weighted_xg"] + k_xg * prior_xg / 90.0) / (eff_mins + k_xg) * 90.0
            finishing_offset_90[idx] = (pdata["tot_g"] - pdata["tot_xg"]) * 90.0 / (pdata["tot_m"] + 1800.0)

            prior_xa = positional_price_tier_prior(pos, init_cost, metric="xa90")
            shrunk_xa90[idx] = (pdata["weighted_xa"] + _BASE_K * prior_xa / 90.0) / (eff_mins + _BASE_K) * 90.0

            prior_crea = _CREATIVITY90_PRIOR.get(pos, 15.0)
            shrunk_creativity90[idx] = (pdata["weighted_crea"] + _BASE_K * prior_crea / 90.0) / (eff_mins + _BASE_K) * 90.0

            # Base BPS & Influence
            shrunk_base_bps90[idx] = (pdata["weighted_base_bps"] + 450.0 * _BASE_BPS90_PRIOR.get(pos, 12.0) / 90.0) / (eff_mins + 450.0) * 90.0
            shrunk_influence90[idx] = (pdata["weighted_inf"] + 450.0 * _INFLUENCE90_PRIOR.get(pos, 18.0) / 90.0) / (eff_mins + 450.0) * 90.0
        else:
            fallback_cost = float(now_costs[idx])
            price_rel_pos[idx] = (fallback_cost - pos_prices.get(pos, 50.0)) / 10.0
            club_frac[idx] = positional_price_tier_prior(pos, fallback_cost, metric="start_frac")
            shrunk_xg90[idx] = positional_price_tier_prior(pos, fallback_cost, metric="xg90")
            shrunk_xa90[idx] = positional_price_tier_prior(pos, fallback_cost, metric="xa90")

    # 3. Matchup & Context Ratios
    team_att_ratio = np.ones(N)
    opp_def_ratio = np.ones(N)
    opp_xgc_trend_3gw = np.ones(N)
    club_blended_xgc = np.full(N, 1.35)
    opp_blended_xg = np.full(N, 1.35)
    opp_save_multiplier = np.ones(N)
    opp_pressure_ratio = np.ones(N)

    club_ids = out["club_id"].to_numpy() if "club_id" in out.columns else np.full(N, -1)
    opp_col = "opponent_id" if "opponent_id" in out.columns else "opponent_club_id"
    opp_ids = out[opp_col].to_numpy() if opp_col in out.columns else np.full(N, -1)

    for idx in range(N):
        cid = club_ids[idx]
        oid = opp_ids[idx]

        if cid in club_att_rate:
            team_att_ratio[idx] = float(np.clip(club_att_rate[cid] / league_xg, 0.5, 2.0))
            club_blended_xgc[idx] = float(club_blend_gc.get(cid, 1.35))
        if oid in club_def_rate:
            opp_def_ratio[idx] = float(np.clip(club_def_rate[oid] / league_xg, 0.5, 2.0))
            opp_xgc_trend_3gw[idx] = float(opp_recent_trend.get(oid, 1.0))
            opp_blended_xg[idx] = float(club_blend_gc.get(oid, 1.35))
            opp_threat = club_threat_match.get(oid, 35.0)
            opp_crea = club_crea_match.get(oid, 20.0)
            opp_xg = club_def_rate.get(oid, 1.35)
            V = opp_threat / 35.0
            D = (opp_xg / max(opp_threat, 1.0)) / (league_xg / 35.0)
            opp_save_multiplier[idx] = float(np.clip((V ** 0.45) * (D ** -0.25), 0.70, 1.45))
            opp_pressure_ratio[idx] = float(np.clip((opp_threat + opp_crea) / 55.0, 0.60, 1.60))

    # 4. Leave-one-out teammate finishing (Ticket #164)
    if not hist_prior.empty and "fixture_id" in hist_prior.columns:
        club_perf = hist_prior.groupby(["club_id", "gameweek_id"]).size().groupby("club_id").count()
        qualified_clubs = set(club_perf[club_perf >= 3].index)

        # Pre-sum club total goals and xg with weights
        club_g_totals = {}
        club_xg_totals = {}
        player_gw_g = {}
        player_gw_xg = {}

        for cid in qualified_clubs:
            c_rows = hist_prior[hist_prior["club_id"] == cid]
            if not c_rows.empty:
                gws = c_rows["gameweek_id"].to_numpy(dtype=float)
                w = _DECAY ** np.clip(target_gw - 1 - gws, 0, 38)
                g_arr = c_rows["goals_scored"].to_numpy(dtype=float)
                xg_arr = c_rows["expected_goals"].to_numpy(dtype=float)
                club_g_totals[cid] = float(np.sum(g_arr * w))
                club_xg_totals[cid] = float(np.sum(xg_arr * w))

        for pid, pdata in player_stats_cache.items():
            player_gw_g[pid] = pdata["tot_g"]
            player_gw_xg[pid] = pdata["weighted_xg"]

        phi_raw = np.ones(N)
        for idx in range(N):
            cid = club_ids[idx]
            pid = pids[idx]
            if cid in qualified_clubs:
                tot_g = club_g_totals.get(cid, 0.0)
                tot_xg = club_xg_totals.get(cid, 0.0)
                # Subtract player's own contribution
                pdata = player_stats_cache.get(pid)
                if pdata is not None and pdata["club_arr"] is not None:
                    c_mask = pdata["club_arr"] == cid
                    if np.any(c_mask):
                        p_w = pdata["weights_arr"][c_mask]
                        p_g = float(np.sum(pdata["g_arr"][c_mask] * p_w))
                        p_xg = float(np.sum(pdata["xg_arr"][c_mask] * p_w))
                        g = tot_g - p_g
                        xg = tot_xg - p_xg
                    else:
                        g, xg = tot_g, tot_xg
                else:
                    g, xg = tot_g, tot_xg
                phi_raw[idx] = 1.0 + (g - xg) / (xg + 25.0)
        phi_mean = float(np.mean(phi_raw)) if N > 0 else 1.0
        loo_teammate_finishing = np.clip(phi_raw / max(phi_mean, 1e-4), 0.88, 1.15)

    # 5. Assemble all features
    if "is_home" in out.columns:
        is_home = out["is_home"].astype(bool).astype(float).to_numpy()
    elif "was_home" in out.columns:
        is_home = out["was_home"].astype(bool).astype(float).to_numpy()
    else:
        is_home = np.ones(N)

    if "difficulty" in out.columns:
        difficulty = pd.to_numeric(out["difficulty"], errors="coerce").fillna(3.0).to_numpy()
    else:
        difficulty = np.full(N, 3.0)

    features_dict = {
        "s_lag1": s_lag1,
        "s_lag2": s_lag2,
        "s_lag3": s_lag3,
        "s_lag4": s_lag4,
        "s_lag5": s_lag5,
        "s_lag6": s_lag6,
        "sub_lag1": sub_lag1,
        "sub_lag2": sub_lag2,
        "sub_lag3": sub_lag3,
        "min3": min3,
        "starts6": s_lag1 + s_lag2 + s_lag3 + s_lag4 + s_lag5 + s_lag6,
        "since_start": since_start,
        "club_frac": club_frac,
        "rest_days": rest_days,
        "short_turnaround": (rest_days < 3.75).astype(float) * (pos_s != 1).astype(float),
        "transfer_momentum": transfer_momentum,
        "price_rel_pos": price_rel_pos,
        "shrunk_mins_if_start": shrunk_mins_if_start,
        "early_hook_rate": early_hook_rate,
        "shrunk_xg90": shrunk_xg90,
        "shot_quality_ratio": shot_quality_ratio,
        "club_xg_share": club_xg_share,
        "finishing_offset_90": finishing_offset_90,
        "shrunk_xa90": shrunk_xa90,
        "shrunk_creativity90": shrunk_creativity90,
        "creativity_share": creativity_share,
        "loo_teammate_finishing": loo_teammate_finishing,
        "team_att_ratio": team_att_ratio,
        "opp_def_ratio": opp_def_ratio,
        "opp_xgc_trend_3gw": opp_xgc_trend_3gw,
        "club_blended_xgc": club_blended_xgc,
        "opp_blended_xg": opp_blended_xg,
        "opp_save_multiplier": opp_save_multiplier,
        "opp_pressure_ratio": opp_pressure_ratio,
        "shrunk_base_bps90": shrunk_base_bps90,
        "shrunk_influence90": shrunk_influence90,
        "pos_gk": (pos_s == 1).astype(float),
        "pos_def": (pos_s == 2).astype(float),
        "pos_mid": (pos_s == 3).astype(float),
        "pos_fwd": (pos_s == 4).astype(float),
        "is_home": is_home,
        "difficulty": difficulty,
    }

    feature_df = pd.DataFrame(features_dict)
    core_cols = ["player_id", "gameweek_id", "fixture_id"]
    for c in core_cols:
        if c in out.columns:
            feature_df[c] = out[c].to_numpy()

    return feature_df


def _col_series(df: pd.DataFrame, col: str) -> np.ndarray:
    if col in df.columns:
        return pd.to_numeric(df[col], errors="coerce").fillna(0.0).to_numpy()
    return np.zeros(len(df), dtype=float)


def build_causal_panel(
    history_df: pd.DataFrame,
    features_df: pd.DataFrame,
    *,
    min_train_gw: int = 4,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Single pure code path generating causal features for training and prediction.

    Guarantees:
    - Zero lookahead: gameweek g features strictly use rows with gameweek_id < g.
    - Zero disk lookups: club IDs reconstructed purely in-memory.
    - Zero terminal player columns.
    """
    hist = _reconstruct_club_id(history_df)

    # Resolve positions mapping from features_df and history
    positions = pd.Series(dtype=int)
    if "position_id" in features_df.columns:
        positions = features_df.drop_duplicates("player_id").set_index("player_id")["position_id"]

    # Target gameweek for prediction frame
    target_gw = int(pd.to_numeric(features_df["gameweek_id"]).min()) if not features_df.empty else 1

    # 1. Build Prediction Panel at target_gw (using H_{<target_gw})
    pred_prior = hist[hist["gameweek_id"] < target_gw] if not hist.empty else pd.DataFrame()
    pred_panel = _build_gw_panel(pred_prior, features_df, target_gw, positions)

    # 2. Build Historical Training Panel for g in [min_train_gw, target_gw - 1]
    train_dfs: list[pd.DataFrame] = []
    if not hist.empty:
        max_hist_gw = int(pd.to_numeric(hist["gameweek_id"]).max())
        upper_train_gw = min(target_gw - 1, max_hist_gw)
        pos_hash = int(pd.util.hash_pandas_object(positions, index=True).sum()) if not positions.empty else 0

        for gw in range(min_train_gw, upper_train_gw + 1):
            gw_rows = hist[hist["gameweek_id"] == gw]
            if gw_rows.empty:
                continue

            hist_le_gw = hist[hist["gameweek_id"] <= gw]
            cache_key = (gw, int(pd.util.hash_pandas_object(hist_le_gw, index=False).sum()), pos_hash)
            cached_gw = _TRAIN_GW_CACHE.get(cache_key)
            if cached_gw is not None:
                train_dfs.append(cached_gw.copy())
                continue

            h_prior = hist[hist["gameweek_id"] < gw]
            # Rename opponent_club_id to opponent_id for standard format
            gw_input = gw_rows.copy()
            if "opponent_club_id" in gw_input.columns and "opponent_id" not in gw_input.columns:
                gw_input["opponent_id"] = gw_input["opponent_club_id"]
            if "was_home" in gw_input.columns and "is_home" not in gw_input.columns:
                gw_input["is_home"] = gw_input["was_home"]

            gw_panel = _build_gw_panel(h_prior, gw_input, gw, positions)

            # Attach training targets
            mins = _col_series(gw_rows, "minutes")
            starts = _col_series(gw_rows, "starts")
            g = _col_series(gw_rows, "goals_scored")
            xg = _col_series(gw_rows, "expected_goals")
            a = _col_series(gw_rows, "assists")
            xa = _col_series(gw_rows, "expected_assists")
            bps = _col_series(gw_rows, "bps")
            cs = _col_series(gw_rows, "clean_sheets")
            gc = _col_series(gw_rows, "goals_conceded")
            saves = _col_series(gw_rows, "saves")

            pos_arr = gw_panel["pos_gk"].to_numpy() * 1 + gw_panel["pos_def"].to_numpy() * 2 + gw_panel["pos_mid"].to_numpy() * 3 + gw_panel["pos_fwd"].to_numpy() * 4
            is_cs_pos = np.isin(pos_arr, (1, 2, 3)).astype(float)
            bps_base = bps - (24.0 * g + 12.0 * a + 12.0 * is_cs_pos * cs + 2.0 * saves)

            gw_panel["target_starts"] = (starts >= 1).astype(float)
            gw_panel["target_sub"] = ((mins > 0) & (starts == 0)).astype(float)
            gw_panel["target_dnp"] = (mins == 0).astype(float)
            gw_panel["target_minutes"] = mins
            gw_panel["target_goals_scored"] = g
            gw_panel["target_expected_goals"] = xg
            gw_panel["target_goals_blend"] = 0.5 * g + 0.5 * xg
            gw_panel["target_assists"] = a
            gw_panel["target_expected_assists"] = xa
            gw_panel["target_assists_blend"] = 0.5 * a + 0.5 * xa
            gw_panel["target_gc"] = gc
            gw_panel["target_cs"] = cs
            gw_panel["target_saves"] = saves
            gw_panel["target_bps"] = bps
            gw_panel["target_bps_base"] = bps_base

            if len(_TRAIN_GW_CACHE) < 256:
                _TRAIN_GW_CACHE[cache_key] = gw_panel.copy()
            train_dfs.append(gw_panel)

    train_panel = pd.concat(train_dfs, ignore_index=True) if train_dfs else pd.DataFrame(columns=pred_panel.columns)

    return train_panel, pred_panel

"""Offline native-season MILP using issue-time prices and a fixed shared chip calendar.

The product solver assumes modern FT rules. This adapter shares its Strategic
objective while expressing historical FT transitions from the native rule table.
"""

from typing import Any, TYPE_CHECKING, cast
import math

import highspy
import pandas as pd

from backtesting.replay_state import Decision, Lineup, Player, ReplayState, state_hash, validate_squad
from backtesting.season_rules import Chip, chip_window, get_rules, next_free_transfers, selling_price, validate_chip_calendar
from models.scoring_matrix import Position

if TYPE_CHECKING:
    from backtesting.rolling_replay import SolverCertificate


def _forecast_universe(state: ReplayState, horizon: int, forecasts: pd.DataFrame) -> tuple[dict[int, Player], dict[tuple[int, int], float], dict[tuple[int, int], float]]:
    weeks = range(state.deadline, state.deadline + horizon)
    required = {"player_id", "position_id", "club_id", "now_cost", "purchase_eligible"}
    required.update(f"{gw}_{suffix}" for gw in weeks for suffix in ("Pts", "xMins"))
    if not required <= set(forecasts.columns) or forecasts.empty:
        raise ValueError("Native transfer solve requires complete issue metadata and every target Pts/xMins column")
    players: dict[int, Player] = {}
    points: dict[tuple[int, int], float] = {}
    minutes: dict[tuple[int, int], float] = {}
    positions: dict[int, Position] = {1: "GK", 2: "D", 3: "M", 4: "F"}
    for row in forecasts.to_dict(orient="records"):
        for key in ("player_id", "position_id", "club_id", "now_cost"):
            if type(row[key]) is not int or row[key] <= 0:
                raise ValueError("Native metadata must use positive integer IDs and tenths")
        pid = row["player_id"]
        if pid in players or row["position_id"] not in positions or type(row["purchase_eligible"]) is not bool:
            raise ValueError("Duplicate player or invalid native metadata")
        players[pid] = Player(pid, positions[row["position_id"]], row["club_id"], row["now_cost"], row["now_cost"], row["purchase_eligible"])
        for gw in weeks:
            xp, mins = row[f"{gw}_Pts"], row[f"{gw}_xMins"]
            if isinstance(xp, bool) or isinstance(mins, bool) or not math.isfinite(float(xp)) or not math.isfinite(float(mins)) or not 0 <= float(mins) <= 270:
                raise ValueError("Invalid issue forecast")
            points[pid, gw], minutes[pid, gw] = float(xp), float(mins)
    for owned in state.squad:
        if owned.player_id not in players:
            raise ValueError("Owned player missing from issue forecast universe")
        current = players[owned.player_id]
        if (current.position, current.club, current.market, current.purchase_eligible) != (owned.position, owned.club, owned.market, owned.purchase_eligible):
            raise ValueError("Owned metadata requires admitted deadline refresh before solving")
    return players, points, minutes


def _dominates_unowned(
    a: int,
    b: int,
    players: dict[int, Player],
    xp: dict[tuple[int, int], float],
    xmins: dict[tuple[int, int], float],
    weeks: list[int],
    floor: float,
    bcover: float,
) -> bool:
    """Return True if unowned eligible player `a` strictly or tie-break dominates `b` across all horizon weeks."""
    if players[a].market > players[b].market:
        return False
    if any(xp[a, gw] < xp[b, gw] for gw in weeks):
        return False
    if any((xmins[a, gw] >= floor) < (xmins[b, gw] >= floor) for gw in weeks):
        return False
    if any((xmins[a, gw] >= bcover) < (xmins[b, gw] >= bcover) for gw in weeks):
        return False
    identical = (
        players[a].market == players[b].market
        and all(xp[a, gw] == xp[b, gw] for gw in weeks)
        and all((xmins[a, gw] >= floor) == (xmins[b, gw] >= floor) for gw in weeks)
        and all((xmins[a, gw] >= bcover) == (xmins[b, gw] >= bcover) for gw in weeks)
    )
    return (not identical) or (a < b)


def _exact_undominated_ids(
    state: ReplayState,
    players: dict[int, Player],
    xp: dict[tuple[int, int], float],
    xmins: dict[tuple[int, int], float],
    weeks: list[int],
    options: dict[str, Any],
) -> list[int]:
    """Prune unowned purchase-ineligible and same-(pos, club) k-dominated candidates with 0% loss."""
    k_by_pos: dict[Position, int] = {"GK": 2, "D": 3, "M": 3, "F": 3}
    floor = float(options["starter_xmins_floor"])
    bcover = float(options["bench_cover_xmins"])
    owned_set = {p.player_id for p in state.squad}
    by_pc: dict[tuple[Position, int], list[int]] = {}
    for p, pl in players.items():
        by_pc.setdefault((pl.position, pl.club), []).append(p)
    kept: list[int] = []
    for (pos, _), group in by_pc.items():
        k = k_by_pos[pos]
        elig = sorted(p for p in group if p not in owned_set and players[p].purchase_eligible)
        for p in group:
            if p in owned_set:
                kept.append(p)
                continue
            if not players[p].purchase_eligible:
                continue
            if sum(1 for a in elig if a != p and _dominates_unowned(a, p, players, xp, xmins, weeks, floor, bcover)) < k:
                kept.append(p)
    return sorted(kept)


_SEED_MIN_CANDIDATES = 85
_SEED_MIN_BUDGET_SECONDS = 15.0
_SEED_TOP_NAILED = 25
_SEED_TOP_EV = 45
_LP_KERNEL_TOP_EV = 10
_LP_KERNEL_TOP_RC_PER_POS = 5
_LP_KERNEL_GAP = 0.0
_HEURISTIC_SEED_GAP = 0.05
_LP_TIME_FRACTION = 0.15
_LP_TIME_CAP = 6.0
_SEED_AFTER_LP_FRACTION = 0.22
_SEED_AFTER_LP_MIN = 1.5
_SEED_AFTER_LP_CAP = 13.0
_SEED_TIME_FRACTION = 0.2
_SEED_TIME_CAP = 9.5


def _seed_candidate_ids(
    state: ReplayState,
    ids: list[int],
    players: dict[int, Player],
    xp: dict[tuple[int, int], float],
    xmins: dict[tuple[int, int], float],
    weeks: list[int],
    options: dict[str, Any],
) -> list[int]:
    """Select deterministic compact warm-start pool covering owned squad, cheapest nailed enablers, and top EV."""
    owned_set = {p.player_id for p in state.squad}
    floor = float(options["starter_xmins_floor"])
    tot_ev = {p: sum(xp[p, gw] for gw in weeks) for p in ids}
    nailed_cnt = {p: sum(1 for gw in weeks if xmins[p, gw] >= floor) for p in ids}
    all_nailed = sorted(
        (p for p in ids if nailed_cnt[p] == len(weeks)),
        key=lambda p: (players[p].market, -tot_ev[p], p),
    )[:_SEED_TOP_NAILED]
    top_ev = sorted(ids, key=lambda p: (-tot_ev[p], p))[:_SEED_TOP_EV]
    return sorted(owned_set | set(all_nailed) | set(top_ev))


def _set_highs_heuristics(model: highspy.Highs, *, enabled: bool) -> None:
    """Configure primal sub-MIP heuristics consistently for cold vs warm-started solves."""
    if enabled:
        model.setOptionValue("mip_heuristic_effort", 0.05)
    else:
        model.setOptionValue("mip_heuristic_effort", 0.0)
    for opt in (
        "mip_heuristic_run_rens",
        "mip_heuristic_run_rins",
        "mip_heuristic_run_feasibility_jump",
        "mip_heuristic_run_shifting",
        "mip_heuristic_run_zi_round",
    ):
        model.setOptionValue(opt, enabled)
    if not enabled:
        model.setOptionValue("mip_heuristic_run_root_reduced_cost", True)


def _build_native_milp(
    state: ReplayState,
    weeks: list[int],
    players: dict[int, Player],
    xp: dict[tuple[int, int], float],
    xmins: dict[tuple[int, int], float],
    ids: list[int],
    options: dict[str, Any],
    chip_by_gw: dict[int, Chip],
    *,
    target_gap: float,
    time_limit: float,
    disable_submip: bool,
) -> tuple[highspy.Highs, dict[str, Any], float]:
    """Assemble compact exact native MILP returning (model, variable_handles, assembly_time_seconds)."""
    import time

    rules = get_rules(state.rules_version)
    asm_t0 = time.perf_counter()
    gks = [p for p in ids if players[p].position == "GK"]
    outfield = [p for p in ids if players[p].position != "GK"]
    owned = {p.player_id: p for p in state.squad}
    owned_ids = [p for p in ids if p in owned]

    model = highspy.Highs()
    model.setOptionValue("output_flag", False)
    model.setOptionValue("threads", 1)
    model.setOptionValue("random_seed", 42)
    model.setOptionValue("mip_rel_gap", target_gap)
    model.setOptionValue("mip_abs_gap", 1e-7)
    model.setOptionValue("time_limit", max(1e-3, time_limit))
    if disable_submip:
        _set_highs_heuristics(model, enabled=False)
    total = model.qsum

    def binary(name: str, *sets: Any) -> Any:
        return model.addVariables(*sets, lb=0, ub=1, type=highspy.HighsVarType.kInteger, name_prefix=name)

    nonfirst_bb_weeks = {gw for gw in weeks[1:] if chip_by_gw.get(gw) == "bench_boost"}
    non_bb_bench_weeks = [gw for gw in weeks if gw not in nonfirst_bb_weeks]
    start, captain, vice = binary("start_", ids, weeks), binary("captain_", ids, weeks), binary("vice_", ids, weeks)
    bench0 = binary("bench0_", gks, non_bb_bench_weeks) if non_bb_bench_weeks else {}
    bench_out = binary("bencho_", outfield, non_bb_bench_weeks, (1, 2, 3)) if non_bb_bench_weeks else {}
    old, sell_old = binary("old_", owned_ids, weeks), binary("sold_", owned_ids, weeks)
    new, buy, sell_new = binary("new_", ids, weeks), binary("buy_", ids, weeks), binary("snew_", ids, weeks)
    fh_weeks = [gw for gw in weeks if chip_by_gw.get(gw) == "free_hit"]
    active_old_fh = binary("aold_", owned_ids, fh_weeks) if fh_weeks else {}
    active_new_fh = binary("anew_", ids, fh_weeks) if fh_weeks else {}

    bank = model.addVariables(weeks, lb=0)
    ft_states = list(range(rules.free_transfer_cap + 1))
    ft = model.addVariables([*weeks, weeks[-1] + 1], ft_states, lb=0, ub=1, type=highspy.HighsVarType.kInteger)
    joints: dict[int, dict[tuple[int, int], Any]] = {}
    cover_vars: dict[int, Any] = {}
    slack_vars: dict[tuple[int, int], Any] = {}
    week_objectives: list[Any] = []
    ft_value = {f: sum(float(options["ft_value_list"].get(str(n), 1.5)) for n in range(f + 1)) for f in ft_states}
    ft_scale = float(options.get("horizon_scale") or 1.0) or 1.0
    spare_ft_hold_weight = float(options.get("spare_ft_hold_weight", 0.325))
    ft_hold_weights = {
        f: spare_ft_hold_weight * max(0.0, ft_value[f] - ft_value[1]) / ft_scale
        for f in ft_states
    }
    clubs = sorted({p.club for p in players.values()})
    hit_lim = int(options["weekly_hit_limit"])
    cum_nonfree_buys: list[Any] = []
    max_ft = state.free_transfers
    block_cap = state.free_transfers
    has_free_so_far = False
    weights = (0.03, 0.21, 0.06, 0.002)

    for gw in weeks:
        chip = chip_by_gw.get(gw)
        free = chip in ("wildcard", "free_hit")
        if free:
            has_free_so_far = True
        prior_bank = state.bank if gw == state.deadline else bank[gw - 1]
        active: dict[int, Any] = {}
        for p in ids:
            prev_n = 0 if gw == state.deadline else new[p, gw - 1]
            prev_o = (1 if gw == state.deadline else old[p, gw - 1]) if p in owned else 0
            if gw == 1 or not players[p].purchase_eligible:
                model.addConstr(buy[p, gw] == 0)
            if gw == state.deadline:
                model.addConstr(sell_new[p, gw] == 0)
                if p in owned:
                    model.addConstr(buy[p, gw] == 0)
            if gw == 1 and p in owned:
                model.addConstr(sell_old[p, gw] == 0)
            model.addConstr(sell_new[p, gw] <= prev_n)
            a_new_expr = prev_n - sell_new[p, gw] + buy[p, gw]
            if chip == "free_hit":
                model.addConstr(active_new_fh[p, gw] == a_new_expr)
                model.addConstr(new[p, gw] == prev_n)
                a_new = active_new_fh[p, gw]
            else:
                model.addConstr(new[p, gw] == a_new_expr)
                a_new = new[p, gw]
            if p in owned:
                model.addConstr(sell_old[p, gw] <= prev_o)
                a_old_expr = prev_o - sell_old[p, gw]
                if chip == "free_hit":
                    model.addConstr(active_old_fh[p, gw] == a_old_expr)
                    model.addConstr(old[p, gw] == prev_o)
                    a_old = active_old_fh[p, gw]
                else:
                    model.addConstr(old[p, gw] == a_old_expr)
                    a_old = old[p, gw]
                model.addConstr(buy[p, gw] + prev_o + prev_n <= 1)
                active[p] = a_old + a_new
                model.addConstr(active[p] <= 1)
            else:
                model.addConstr(buy[p, gw] + prev_n <= 1)
                active[p] = a_new
            if gw in nonfirst_bb_weeks:
                model.addConstr(start[p, gw] <= active[p])
            elif players[p].position == "GK":
                model.addConstr(start[p, gw] + bench0[p, gw] == active[p])
            else:
                model.addConstr(start[p, gw] + bench_out[p, gw, 1] + bench_out[p, gw, 2] + bench_out[p, gw, 3] == active[p])
            model.addConstr(captain[p, gw] + vice[p, gw] <= start[p, gw])

        cash = prior_bank + total(selling_price(owned[p].purchase, owned[p].market) * sell_old[p, gw] for p in owned_ids)
        cash += total(players[p].market * (sell_new[p, gw] - buy[p, gw]) for p in ids)
        model.addConstr(cash >= 0)
        model.addConstr(bank[gw] == (prior_bank if chip == "free_hit" else cash))
        for position, count in (("GK", 2), ("D", 5), ("M", 5), ("F", 3)):
            model.addConstr(total(active[p] for p in ids if players[p].position == position) == count)
        for club in clubs:
            model.addConstr(total(active[p] for p in ids if players[p].club == club) <= 3)
        for position, low, high in (("GK", 1, 1), ("D", 3, 5), ("M", 2, 5), ("F", 1, 3)):
            count = total(start[p, gw] for p in ids if players[p].position == position)
            model.addConstr(count >= low)
            model.addConstr(count <= high)
        model.addConstr(total(start[p, gw] for p in ids) == 11)
        model.addConstr(total(captain[p, gw] for p in ids) == 1)
        model.addConstr(total(vice[p, gw] for p in ids) == 1)
        if gw not in nonfirst_bb_weeks:
            model.addConstr(total(bench0[p, gw] for p in gks) == 1)
            for slot in (1, 2, 3):
                model.addConstr(total(bench_out[p, gw, slot] for p in outfield) == 1)

        model.addConstr(total(ft[gw, f] for f in ft_states) == 1)
        if gw == state.deadline:
            model.addConstr(ft[gw, state.free_transfers] == 1)
        valid_ft = [0] if gw == 1 else list(range(1, rules.free_transfer_cap + 1))
        choices = [(f, n) for f in valid_ft for n in range(1 if gw == 1 else 16) if free or max(n - f, 0) <= hit_lim]
        jvars = {(f, n): model.addVariable(lb=0, ub=1, type=highspy.HighsVarType.kInteger) for f, n in choices}
        joints[gw] = jvars
        model.addConstr(total(jvars.values()) == 1)
        gw_buys = total(buy[p, gw] for p in ids)
        model.addConstr(total(n * v for (_, n), v in jvars.items()) == gw_buys)
        if not free and not has_free_so_far:
            if gw > 1:
                model.addConstr(gw_buys <= min(15, rules.free_transfer_cap + hit_lim, max_ft + hit_lim))
                cum_nonfree_buys.append(gw_buys)
                if hit_lim == 0:
                    model.addConstr(total(cum_nonfree_buys) <= block_cap)
            if gw == 1:
                max_ft = 1
                block_cap = 1
                cum_nonfree_buys.clear()
            elif rules.afcon_gw15_topup and gw == 15:
                max_ft = 5
                block_cap = 5
                cum_nonfree_buys.clear()
            else:
                max_ft = min(rules.free_transfer_cap, max_ft + 1)
                block_cap += 1
        for f in ft_states:
            model.addConstr(total(v for (previous, _), v in jvars.items() if previous == f) == ft[gw, f])
            model.addConstr(ft[gw + 1, f] == total(v for (previous, n), v in jvars.items() if next_free_transfers(rules, previous, n, chip, gw) == f))

        paid = total((0 if free else max(n - f, 0)) * v for (f, n), v in jvars.items())
        ft_use = total(n * v for (_, n), v in jvars.items()) if not free else 0
        scoring_lineup = {p: active[p] if chip == "bench_boost" else start[p, gw] for p in ids}
        floor_penalty = abs(float(options["starter_xmins_penalty"])) * total(
            scoring_lineup[p] for p in outfield if xmins[p, gw] < float(options["starter_xmins_floor"])
        )
        cover = model.addVariable(lb=0)
        cover_vars[gw] = cover
        model.addConstr(cover + total(active[p] for p in ids if xmins[p, gw] >= float(options["bench_cover_xmins"])) >= int(options["bench_cover_min"]))
        stack: list[Any] = []
        for club in clubs:
            slack = model.addVariable(lb=0)
            model.addConstr(total(scoring_lineup[p] for p in ids if players[p].club == club and players[p].position in ("GK", "D")) <= int(options["def_stack_cap"]) + slack)
            stack.append(slack)
            slack_vars[gw, club] = slack
        gk_cost = 0 if free else float(options["gk_transfer_friction"]) * total(buy[p, gw] for p in gks)
        if chip == "bench_boost":
            score = total(xp[p, gw] * (active[p] + captain[p, gw] + 0.1 * vice[p, gw]) for p in ids)
        else:
            score = total(
                xp[p, gw]
                * (
                    start[p, gw]
                    + (2 if chip == "triple_captain" else 1) * captain[p, gw]
                    + 0.1 * vice[p, gw]
                    + (weights[0] * bench0[p, gw] if players[p].position == "GK" else total(weights[b] * bench_out[p, gw, b] for b in (1, 2, 3)))
                )
                for p in ids
            )
        ft_gain = total(ft_value[f] * ft[gw + 1, f] for f in ft_states) - total(ft_value[f] * ft[gw, f] for f in ft_states)
        if options.get("ft_value_list") and gw < weeks[-1]:
            ft_gain += total(ft_hold_weights[f] * ft[gw + 1, f] for f in ft_states if f >= 2)
        objective = score - float(options["hit_hurdle"]) * paid - float(options["ft_use_penalty"]) * ft_use
        objective += ft_gain + 0.008 * bank[gw] - floor_penalty - abs(float(options["bench_cover_penalty"])) * cover
        objective -= abs(float(options["def_stack_penalty"])) * total(stack) + gk_cost
        week_objectives.append(float(options["decay_base"]) ** (gw - state.deadline) * objective)

    model.setObjective(total(week_objectives), sense=highspy.ObjSense.kMaximize)
    asm_elapsed = round(time.perf_counter() - asm_t0, 6)
    handles = {
        "start": start, "captain": captain, "vice": vice,
        "bench0": bench0, "bench_out": bench_out, "old": old, "sell_old": sell_old,
        "new": new, "buy": buy, "sell_new": sell_new, "active_old_fh": active_old_fh,
        "active_new_fh": active_new_fh, "bank": bank, "ft": ft,
        "cover": cover_vars, "slack": slack_vars, "j": joints,
    }
    return model, handles, asm_elapsed


def _lp_kernel_candidate_ids(
    state: ReplayState,
    ids: list[int],
    weeks: list[int],
    players: dict[int, Player],
    xp: dict[tuple[int, int], float],
    xmins: dict[tuple[int, int], float],
    options: dict[str, Any],
    chip_by_gw: dict[int, Chip],
    *,
    time_limit: float,
) -> tuple[list[int], float, float]:
    """Solve 1s root LP relaxation on exact universe and extract active kernel players."""
    lp_model, lp_vars, lp_asm = _build_native_milp(
        state, weeks, players, xp, xmins, ids, options, chip_by_gw,
        target_gap=0.0, time_limit=time_limit, disable_submip=False,
    )
    lp_model.setOptionValue("solve_relaxation", True)
    lp_model.run()
    lp_run = float(lp_model.getRunTime())
    owned_set = {p.player_id for p in state.squad}
    lp_sol_obj = lp_model.getSolution()
    if not lp_sol_obj.value_valid:
        return _seed_candidate_ids(state, ids, players, xp, xmins, weeks, options), lp_run, lp_asm
    lp_sol = lp_sol_obj.col_value
    active_lp: set[int] = set()
    for p in ids:
        activity = 0.0
        for gw in weeks:
            if (p, gw) in lp_vars["new"]:
                activity += float(lp_sol[lp_vars["new"][p, gw].index])
            if (p, gw) in lp_vars["buy"]:
                activity += float(lp_sol[lp_vars["buy"][p, gw].index])
            if (p, gw) in lp_vars["start"]:
                activity += float(lp_sol[lp_vars["start"][p, gw].index])
        if activity > 1e-4:
            active_lp.add(p)
    extras: set[int] = set(owned_set) | active_lp
    tot_ev = {p: sum(xp[p, gw] for gw in weeks) for p in ids}
    # Add per-position LP reduced-cost runner-ups so budget/bench enablers omitted by global EV remain in the seed kernel.
    if lp_sol_obj.dual_valid and len(lp_sol_obj.col_dual) == lp_model.getNumCol():
        col_dual = lp_sol_obj.col_dual
        rc_sum: dict[int, float] = {
            p: sum(float(col_dual[lp_vars["new"][p, gw].index]) for gw in weeks if (p, gw) in lp_vars["new"])
            for p in ids
            if p not in extras
        }
        for pos in sorted({players[p].position for p in rc_sum}):
            pos_cands = sorted(
                (p for p in rc_sum if players[p].position == pos),
                key=lambda p: (-rc_sum[p], -tot_ev[p], p),
            )
            extras.update(pos_cands[:_LP_KERNEL_TOP_RC_PER_POS])
    top_ev = sorted(ids, key=lambda p: (-tot_ev[p], p))[:_LP_KERNEL_TOP_EV]
    return sorted(extras | set(top_ev)), lp_run, lp_asm


def _inject_mip_start(seed_model: highspy.Highs, seed_vars: dict[str, Any], target_model: highspy.Highs, target_vars: dict[str, Any]) -> bool:
    """Copy a feasible incumbent solution from the compact seed solve into the full MILP."""
    if not seed_model.getSolution().value_valid or seed_model.getInfo().primal_solution_status != highspy.SolutionStatus.kSolutionStatusFeasible:
        return False
    s_sol = seed_model.getSolution().col_value
    col_vals = [0.0] * target_model.getNumCol()
    for key_group in ("start", "captain", "vice", "bench0", "bench_out", "old", "sell_old", "new", "buy", "sell_new", "active_old_fh", "active_new_fh", "bank", "ft", "cover", "slack"):
        s_map, t_map = seed_vars[key_group], target_vars[key_group]
        for key, s_var in s_map.items():
            if key in t_map:
                col_vals[t_map[key].index] = s_sol[s_var.index]
    for gw, s_j in seed_vars["j"].items():
        t_j = target_vars["j"][gw]
        for fn, s_var in s_j.items():
            if fn in t_j:
                col_vals[t_j[fn].index] = s_sol[s_var.index]
    return target_model.setSolution(len(col_vals), list(range(len(col_vals))), col_vals) == highspy.HighsStatus.kOk


def native_strategic_solve(state: ReplayState, horizon: int, forecast_df: pd.DataFrame, options: dict[str, Any]) -> tuple[Decision, "SolverCertificate"]:
    """Optimize all horizon weeks; return the immediate native decision and real HiGHS certificate."""
    import time
    from backtesting.rolling_replay import SolverCertificate, UncertifiedSolveError

    rules = get_rules(state.rules_version)
    validate_squad(state.squad)
    if type(horizon) is not int or not 1 <= horizon <= 6 or state.deadline + horizon > 39:
        raise ValueError("Native replay horizon must contain one to six in-season deadlines")
    if state.rules_id != rules.rules_id or options.get("rules_version") != rules.version:
        raise ValueError("Native solver rule identity mismatch")
    if options.get("arm") != "strategic":
        raise ValueError("Native replay requires frozen Strategic options")
    calendar = cast(tuple[tuple[int, Chip], ...], tuple(tuple(item) for item in options.get("chip_calendar", ())))
    validate_chip_calendar(rules, calendar)
    for gw, chip in calendar:
        if gw >= state.deadline and any(c == chip and window == chip_window(rules, chip, gw) for _, c, window in state.chip_history):
            raise ValueError("Shared calendar consumes an already used chip")
        if chip == "free_hit" and any(c == chip and abs(gw - prior_gw) == 1 for prior_gw, c, _ in state.chip_history):
            raise ValueError("Consecutive Free Hits unsupported")
    chip_by_gw = dict(calendar)

    solve_t0 = time.perf_counter()
    players, xp, xmins = _forecast_universe(state, horizon, forecast_df)
    weeks = list(range(state.deadline, state.deadline + horizon))
    ids = _exact_undominated_ids(state, players, xp, xmins, weeks, options)
    target_gap = float(options.get("target_gap", 0.0))
    total_limit = float(options.get("time_limit_seconds", 60.0))

    seed_run_time = 0.0
    total_assembly_seconds = 0.0
    seed_model: highspy.Highs | None = None
    seed_vars: dict[str, Any] | None = None
    has_start = False
    if len(ids) > _SEED_MIN_CANDIDATES and total_limit >= _SEED_MIN_BUDGET_SECONDS:
        has_free_chip = any(chip_by_gw.get(gw) in ("wildcard", "free_hit") for gw in weeks)
        if has_free_chip:
            seed_ids, lp_run_time, lp_asm = _lp_kernel_candidate_ids(
                state, ids, weeks, players, xp, xmins, options, chip_by_gw,
                time_limit=min(_LP_TIME_CAP, _LP_TIME_FRACTION * total_limit),
            )
            seed_run_time += lp_run_time
            total_assembly_seconds += lp_asm
            seed_gap = max(target_gap, _LP_KERNEL_GAP)
            seed_budget = min(_SEED_AFTER_LP_CAP, max(_SEED_AFTER_LP_MIN, _SEED_AFTER_LP_FRACTION * (total_limit - seed_run_time)))
        else:
            seed_ids = _seed_candidate_ids(state, ids, players, xp, xmins, weeks, options)
            seed_gap = max(target_gap, _HEURISTIC_SEED_GAP)
            seed_budget = min(_SEED_TIME_CAP, _SEED_TIME_FRACTION * total_limit)
        seed_model, seed_vars, seed_asm = _build_native_milp(
            state, weeks, players, xp, xmins, seed_ids, options, chip_by_gw,
            target_gap=seed_gap, time_limit=seed_budget, disable_submip=False,
        )
        total_assembly_seconds += seed_asm
        seed_model.run()
        seed_run_time += float(seed_model.getRunTime())
        has_start = seed_model.getSolution().value_valid and seed_model.getInfo().primal_solution_status == highspy.SolutionStatus.kSolutionStatusFeasible

    elapsed_wall = time.perf_counter() - solve_t0
    remaining_budget = max(1e-3, min(total_limit - seed_run_time - 0.5, total_limit - elapsed_wall)) if seed_model is not None else max(1e-3, total_limit)
    model, hvars, full_asm = _build_native_milp(
        state, weeks, players, xp, xmins, ids, options, chip_by_gw,
        target_gap=target_gap, time_limit=remaining_budget, disable_submip=has_start,
    )
    assembly_time_seconds = round(total_assembly_seconds + full_asm, 6)
    if has_start and seed_model is not None and seed_vars is not None:
        if not _inject_mip_start(seed_model, seed_vars, model, hvars):
            _set_highs_heuristics(model, enabled=True)
    model.run()

    info = model.getInfo()
    status = model.getModelStatus()
    if not model.getSolution().value_valid or info.primal_solution_status != highspy.SolutionStatus.kSolutionStatusFeasible:
        raise UncertifiedSolveError(f"Native multi-period solve has no feasible incumbent: {model.modelStatusToString(status)}")

    def selected(values: Any, gw: int) -> tuple[int, ...]:
        return tuple(p for p in ids if model.val(values[p, gw]) > 0.5)

    gks = [p for p in ids if players[p].position == "GK"]
    outfield = [p for p in ids if players[p].position != "GK"]
    owned_ids = {p.player_id for p in state.squad}
    ft_states = list(range(rules.free_transfer_cap + 1))
    plans: list[dict[str, Any]] = []
    for gw in weeks:
        outgoing = tuple(
            p for p in ids
            if model.val(hvars["sell_new"][p, gw]) + (model.val(hvars["sell_old"][p, gw]) if p in owned_ids else 0.0) > 0.5
        )
        incoming = selected(hvars["buy"], gw)
        plans.append(
            {
                "gw": gw,
                "transfers_out": outgoing,
                "transfers_in": incoming,
                "bank": round(model.val(hvars["bank"][gw])),
                "free_transfers": next(f for f in ft_states if model.val(hvars["ft"][gw, f]) > 0.5),
                "post_free_transfers": next(f for f in ft_states if model.val(hvars["ft"][gw + 1, f]) > 0.5),
                "chip": chip_by_gw.get(gw),
            }
        )
    first = weeks[0]
    starters = selected(hvars["start"], first)
    bench0_gk = next(p for p in gks if model.val(hvars["bench0"][p, first]) > 0.5)
    bench_slots = tuple(next(p for p in outfield if model.val(hvars["bench_out"][p, first, slot]) > 0.5) for slot in (1, 2, 3))
    bench_order = (bench0_gk, *bench_slots)
    lineup = Lineup(starters, bench_order, selected(hvars["captain"], first)[0], selected(hvars["vice"], first)[0])
    decision = Decision(
        tuple(zip(plans[0]["transfers_out"], (players[p] for p in plans[0]["transfers_in"]), strict=True)),
        lineup, state_hash(state), state.deadline, chip_by_gw.get(first),
    )
    objective_value, bound = model.getObjectiveValue(), float(info.mip_dual_bound)
    status_str = (
        "OPTIMAL"
        if status == highspy.HighsModelStatus.kOptimal
        else ("TIME_LIMIT" if status == highspy.HighsModelStatus.kTimeLimit else model.modelStatusToString(status).upper().replace(" ", "_"))
    )
    certificate = SolverCertificate(
        True,
        objective_value,
        bound,
        abs(bound - objective_value),
        float(info.mip_gap),
        status_str,
        round(seed_run_time + float(model.getRunTime()), 6),
        1,
        42,
        f"highs-{model.version()}-native-v1",
        "certified" if status == highspy.HighsModelStatus.kOptimal else "time_capped",
        {**options, "native_adapter": "native-v1", "price_assumption": "issue_prices_constant", "assembly_time_seconds": assembly_time_seconds, "plans": plans},
    )
    return decision, certificate

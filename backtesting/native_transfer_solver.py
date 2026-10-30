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


def native_strategic_solve(state: ReplayState, horizon: int, forecast_df: pd.DataFrame, options: dict[str, Any]) -> tuple[Decision, "SolverCertificate"]:
    """Optimize all horizon weeks; return the immediate native decision and real HiGHS certificate."""
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
    players, xp, xmins = _forecast_universe(state, horizon, forecast_df)
    ids = sorted(players)
    weeks = list(range(state.deadline, state.deadline + horizon))
    owned = {p.player_id: p for p in state.squad}
    model = highspy.Highs()
    model.setOptionValue("output_flag", False)
    model.setOptionValue("threads", 1)
    model.setOptionValue("random_seed", 42)
    model.setOptionValue("mip_rel_gap", float(options.get("target_gap", 0.0)))
    model.setOptionValue("mip_abs_gap", 1e-7)
    model.setOptionValue("time_limit", float(options.get("time_limit_seconds", 60.0)))
    total = model.qsum

    def binary(name: str) -> Any:
        return model.addVariables(ids, weeks, lb=0, ub=1, type=highspy.HighsVarType.kInteger, name_prefix=name)

    old, new = binary("old_"), binary("new_")
    active_old, active_new = binary("active_old_"), binary("active_new_")
    buy, sell_old, sell_new = binary("buy_"), binary("sell_old_"), binary("sell_new_")
    start, captain, vice = binary("start_"), binary("captain_"), binary("vice_")
    bench = model.addVariables(ids, weeks, range(4), lb=0, ub=1, type=highspy.HighsVarType.kInteger)
    bank = model.addVariables(weeks, lb=0)
    ft_states = list(range(rules.free_transfer_cap + 1))
    ft = model.addVariables([*weeks, weeks[-1] + 1], ft_states, lb=0, ub=1, type=highspy.HighsVarType.kInteger)
    joints: dict[int, list[tuple[int, int, Any]]] = {}
    week_objectives: list[Any] = []
    active = {(p, gw): active_old[p, gw] + active_new[p, gw] for p in ids for gw in weeks}
    ft_value = {f: sum(float(options["ft_value_list"].get(str(n), 1.5)) for n in range(f + 1)) for f in ft_states}

    for gw in weeks:
        chip = chip_by_gw.get(gw)
        free = chip in ("wildcard", "free_hit")
        prior_bank = state.bank if gw == state.deadline else bank[gw - 1]
        prev_old = {p: int(p in owned) if gw == state.deadline else old[p, gw - 1] for p in ids}
        prev_new = {p: 0 if gw == state.deadline else new[p, gw - 1] for p in ids}
        for p in ids:
            model.addConstr(active_old[p, gw] == prev_old[p] - sell_old[p, gw])
            model.addConstr(active_new[p, gw] == prev_new[p] - sell_new[p, gw] + buy[p, gw])
            model.addConstr(sell_old[p, gw] <= prev_old[p])
            model.addConstr(sell_new[p, gw] <= prev_new[p])
            model.addConstr(buy[p, gw] + prev_old[p] + prev_new[p] <= 1)
            model.addConstr(buy[p, gw] <= int(players[p].purchase_eligible))
            model.addConstr(active[p, gw] <= 1)
            model.addConstr(old[p, gw] == (prev_old[p] if chip == "free_hit" else active_old[p, gw]))
            model.addConstr(new[p, gw] == (prev_new[p] if chip == "free_hit" else active_new[p, gw]))
            if gw == 1:
                model.addConstr(buy[p, gw] == 0)
                model.addConstr(sell_old[p, gw] == 0)
            model.addConstr(start[p, gw] + total(bench[p, gw, b] for b in range(4)) == active[p, gw])
            model.addConstr(captain[p, gw] + vice[p, gw] <= start[p, gw])

        cash = prior_bank + total(
            selling_price(owned[p].purchase, owned[p].market) * sell_old[p, gw] for p in ids if p in owned)
        cash += total(players[p].market * (sell_new[p, gw] - buy[p, gw]) for p in ids)
        model.addConstr(cash >= 0)
        model.addConstr(bank[gw] == (prior_bank if chip == "free_hit" else cash))
        for position, count in (("GK", 2), ("D", 5), ("M", 5), ("F", 3)):
            model.addConstr(total(active[p, gw] for p in ids if players[p].position == position) == count)
        for club in {p.club for p in players.values()}:
            model.addConstr(total(active[p, gw] for p in ids if players[p].club == club) <= 3)
        for position, low, high in (("GK", 1, 1), ("D", 3, 5), ("M", 2, 5), ("F", 1, 3)):
            count = total(start[p, gw] for p in ids if players[p].position == position)
            model.addConstr(count >= low)
            model.addConstr(count <= high)
        model.addConstr(total(start[p, gw] for p in ids) == 11)
        model.addConstr(total(captain[p, gw] for p in ids) == 1)
        model.addConstr(total(vice[p, gw] for p in ids) == 1)
        for slot in range(4):
            model.addConstr(total(bench[p, gw, slot] for p in ids) == 1)
            model.addConstr(total(bench[p, gw, slot] for p in ids if players[p].position == "GK") == int(slot == 0))

        model.addConstr(total(ft[gw, f] for f in ft_states) == 1)
        if gw == state.deadline:
            model.addConstr(ft[gw, state.free_transfers] == 1)
        valid_ft = [0] if gw == 1 else list(range(1, rules.free_transfer_cap + 1))
        choices = [(f, n) for f in valid_ft for n in range(1 if gw == 1 else 16)]
        joints[gw] = [(f, n, model.addVariable(lb=0, ub=1, type=highspy.HighsVarType.kInteger)) for f, n in choices]
        model.addConstr(total(v for _, _, v in joints[gw]) == 1)
        model.addConstr(total(n * v for _, n, v in joints[gw]) == total(buy[p, gw] for p in ids))
        for f in ft_states:
            model.addConstr(total(v for previous, _, v in joints[gw] if previous == f) == ft[gw, f])
            model.addConstr(ft[gw + 1, f] == total(v for previous, n, v in joints[gw] if next_free_transfers(rules, previous, n, chip, gw) == f))
        paid = total((0 if free else max(n - f, 0)) * v for f, n, v in joints[gw])
        model.addConstr(paid <= int(options["weekly_hit_limit"]))
        ft_use = total(n * v for _, n, v in joints[gw]) if not free else 0
        scoring_lineup = {p: active[p, gw] if chip == "bench_boost" else start[p, gw] for p in ids}
        floor_penalty = abs(float(options["starter_xmins_penalty"])) * total(scoring_lineup[p] for p in ids if players[p].position != "GK" and xmins[p, gw] < float(options["starter_xmins_floor"]))
        cover = model.addVariable(lb=0)
        model.addConstr(cover + total(active[p, gw] for p in ids if xmins[p, gw] >= float(options["bench_cover_xmins"])) >= int(options["bench_cover_min"]))
        stack: list[Any] = []
        for club in {p.club for p in players.values()}:
            slack = model.addVariable(lb=0)
            model.addConstr(total(scoring_lineup[p] for p in ids if players[p].club == club and players[p].position in ("GK", "D")) <= int(options["def_stack_cap"]) + slack)
            stack.append(slack)
        gk_cost = 0 if free else float(options["gk_transfer_friction"]) * total(buy[p, gw] for p in ids if players[p].position == "GK")
        weights = (0.03, 0.21, 0.06, 0.002)
        score = total(xp[p, gw] * ((active[p, gw] if chip == "bench_boost" else start[p, gw])
                      + (2 if chip == "triple_captain" else 1) * captain[p, gw] + 0.1 * vice[p, gw]
                      + (0 if chip == "bench_boost" else total(weights[b] * bench[p, gw, b] for b in range(4)))) for p in ids)
        ft_gain = total(ft_value[f] * ft[gw, f] for f in ft_states)
        if gw != state.deadline:
            ft_gain -= total(ft_value[f] * ft[gw - 1, f] for f in ft_states)
        objective = score - float(options["hit_hurdle"]) * paid - float(options["ft_use_penalty"]) * ft_use
        objective += ft_gain + 0.008 * bank[gw] - floor_penalty - abs(float(options["bench_cover_penalty"])) * cover
        objective -= abs(float(options["def_stack_penalty"])) * total(stack) + gk_cost
        week_objectives.append(float(options["decay_base"]) ** (gw - state.deadline) * objective)

    model.maximize(total(week_objectives))
    info = model.getInfo()
    status = model.getModelStatus()
    if not model.getSolution().value_valid or info.primal_solution_status != highspy.SolutionStatus.kSolutionStatusFeasible:
        raise UncertifiedSolveError(f"Native multi-period solve has no feasible incumbent: {model.modelStatusToString(status)}")

    def selected(values: Any, gw: int) -> tuple[int, ...]:
        return tuple(p for p in ids if model.val(values[p, gw]) > 0.5)

    plans: list[dict[str, Any]] = []
    for gw in weeks:
        outgoing = tuple(p for p in ids if model.val(sell_old[p, gw] + sell_new[p, gw]) > 0.5)
        incoming = selected(buy, gw)
        plans.append({"gw": gw, "transfers_out": outgoing, "transfers_in": incoming, "bank": round(model.val(bank[gw])),
                      "free_transfers": next(f for f in ft_states if model.val(ft[gw, f]) > 0.5), "chip": chip_by_gw.get(gw)})
    first = weeks[0]
    starters = selected(start, first)
    bench_order = tuple(next(p for p in ids if model.val(bench[p, first, slot]) > 0.5) for slot in range(4))
    lineup = Lineup(starters, bench_order, selected(captain, first)[0], selected(vice, first)[0])
    decision = Decision(tuple(zip(plans[0]["transfers_out"], (players[p] for p in plans[0]["transfers_in"]), strict=True)),
                        lineup, state_hash(state), state.deadline, chip_by_gw.get(first))
    objective_value, bound = model.getObjectiveValue(), float(info.mip_dual_bound)
    certificate = SolverCertificate(True, objective_value, bound, abs(bound - objective_value), float(info.mip_gap),
                                    "OPTIMAL" if status == highspy.HighsModelStatus.kOptimal else model.modelStatusToString(status).upper().replace(" ", "_"),
                                    model.getRunTime(), 1, 42, f"highs-{model.version()}-native-v1",
                                    "certified" if status == highspy.HighsModelStatus.kOptimal else "time_capped",
                                    {**options, "native_adapter": "native-v1", "price_assumption": "issue_prices_constant", "plans": plans})
    return decision, certificate

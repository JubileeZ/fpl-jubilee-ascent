# Conservative Transfer Plan Scenario and Horizon Recovery

Must arms on the Transfer Plan Surface expand from two to three arms: **Optimal**, **No Hit**, and **Conservative**. **Conservative** enforces risk-protected stability for users not tracking pre-deadline press conferences: sets `weekly_hit_limit=0` (zero paid hits), forbids purchasing any unowned player with an active FPL injury or availability flag (`status != 'a'` or `chance < 100` via `banned_next_gw`), and locks regular starters who missed only a single match from panic sales (`locked_next_gw`). In parallel, multi-week learned start projections apply exponential horizon mean-reversion ($h \ge 1$ with decay $\gamma = 0.5$) toward baseline $p_{\text{champ}}$: single-step backtests ($h=0$) stay 100% bit-for-bit identical to the Champion model while future horizon weeks naturally recover from single-match rest events.

**Status:** Accepted. Amends ADR 0042.

**Considered:** Relying solely on manual CLI flags (`--banned`, `--force_keep_gws`); hardcoding availability flag penalties into historical backtest models (rejected: ADR 0046 terminal leakage guard); keeping only two arms and applying safety bans globally (rejected: removes aggressive optimal comparison).

**Consequences:** `solver/scenarios.py` arms = `optimal` / `no_hit` / `conservative`. `LearnedStartChallengerModel` applies horizon decay for $h \ge 1$. Dashboard Transfer Plan surface renders all three arms concurrently and displays inline status badges, warning banners, and 1-click squad locks.

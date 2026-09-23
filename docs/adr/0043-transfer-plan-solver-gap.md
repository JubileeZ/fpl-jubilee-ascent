# Live Transfer Plans stop within 1% of the Solver Objective

Horizon 10 with a zero gap hits the 20-minute HiGHS clock proving the Solver Objective. Live Transfer Plans (CLI `commands.solve` and Surface Optimal / No Hit, horizons 1–10) stop at a 1% relative gap on that objective. The 20-minute clock stays the backstop and returns the best plan. A proven arm shows nothing. An arm inside 1% shows “Within 1% of the best Solver Objective.” A clock stop with a wider gap shows “Stopped at 20 min, {gap}% from the best Solver Objective.” `--gap` overrides. Dream Team and Transfer Plan Walk-Forward stay on a full proof.

**Status:** Accepted.

**Considered:** Keep gap 0 and shrink the model first; gap only past horizon 6; 0.1% or 0.5%; apply 1% to Dream Team and Walk-Forward; hide the mark. Rejected: a smaller model can drop a legal buy; a split horizon rule surprises a 6-week solve; a tighter gap may still miss the few-minute bar; Dream Team’s frozen 15 and Walk-Forward rankings need a proven objective; a silent gap can change the Transfer Plan Start buy.

**Consequences:** Solver default gap stays 0. The live plan sets 0.01. `secs` stays 20 minutes. The sentence is stored on the plan so a Surface reload still shows it. Model shrink waits until a 10-week Optimal arm, one thread, Hits allowed, no chips, still takes more than about 3 minutes.

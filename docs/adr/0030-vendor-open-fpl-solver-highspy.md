# Vendor current open-fpl-solver; planning stays our layer

sasoptpy-era `solver/solver.py` lagged [open-fpl-solver](https://github.com/solioanalytics/open-fpl-solver) `main` (highspy-native model, 3 Aug 2026 #63). Pin upstream `2ff829fff2a4740e71e637f2c5823dbb2fb0a93d`. Keep `solver/planning.py` and `solver/transfer_plan.py` as the Transfer Plan / Force Keep / Enabled Chip layer. Re-apply: `load_solver_static`, player-`code` merge, `force_keep_gws` / `force_ban_gws`, `enabled_chip_windows`, HiGHS `parallel`/`threads`. Drop sasoptpy.

**Status:** Accepted.

**Considered:** Stay on sasoptpy fork; git submodule of full upstream repo. Rejected: fork missed locked+FH, missing-CSV, AFCON-GW16; submodule would pull Solio CSV readers we do not use.

**Consequences:** `solver/vendor.py` records SHA. `--preseason` ITB is £100.0m (`itb=100`), matching upstream. Dream Team serial HiGHS unchanged.

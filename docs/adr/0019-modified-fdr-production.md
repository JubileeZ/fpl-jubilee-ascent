# 0019: Production scoring uses Modified FDR

Official Fixture Difficulty stays the API 1–5 ticks on `fixtures.parquet` (`team_h_difficulty` / `team_a_difficulty`). Production Feature Contract `difficulty`, FDR-fallback multipliers, Champion xP, Transfer Plan, Ownership Explorer, FDR report, and backtests use Modified FDR: official − 0.25 focal home, + 0.25 focal away. Missing official tick or blank gameweek stays 3.0 with no overlay. No clamp to 1–5.

**Status:** Accepted. Supersedes ADR 0018 solver-score sentence (Official Fixture Difficulty) and ADR 0005 clause 4 fallback naming.

Rejected: invert home/away mapping; overwrite parquet with 3.75/5.25; live-only overlay; Dual-Vector effective FDR as production difficulty.

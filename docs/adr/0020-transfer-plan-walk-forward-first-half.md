# 0020: Transfer Plan Walk-Forward for 2025-26 First-Half strategy

2025-26 First-Half playbook evidence is a Transfer Plan Walk-Forward scored on scoring-15 Realized Points, not model MAE and not a hindsight oracle. No chips after GW1, no Hits, Free Transfer Bank to 5. Unconstrained baseline plus Locked Starting Shape, Transfer Target Policy, and Defcon-Floor / Attack-Ceiling tilts, one factor at a time, then one winner cross. Prior-Season Seed from `data/archive/2024-25/processed`. Exploratory: no Availability Snapshots.

**Status:** Accepted.

**Considered:** Hindsight 15 from Realized Points; `commands.backtest` MAE; chips on; Hits allowed; full factorial; Expected Role Table for 2025-26 minutes; FPL-Core Opta dump; GW1–5 of 2025-26 as fake prior. Rejected: oracle leaks the future; MAE does not rank squad policy; chips and Hits confound shape and FT policy; factorial is 45 arms; 2026/27 Expected Role Table is the wrong season; FPL-Core lacks FPL minutes/starts; same-season GW1–5 is current-season history not Prior-Season Seed.

**Consequences:** Ranking object is Transfer Plan Walk-Forward. Companion Club Occupancy is diagnostic only. Live FPL API cannot snapshot 2024-25. Ingest: vaastav 2024-25 CSVs via `commands.snapshot_season --from-vaastav-dir`, or FPL raw JSON via `--from-raw-dir`. MILP Free Transfer variable ub is 5, so GW1 empty-squad construction forces solver Wildcard (`use_wc=[1]`); later GWs chips remain off. Ranking does not spend BB/FH/TC or Hits.

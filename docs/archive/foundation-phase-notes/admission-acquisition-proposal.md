# Replay admission acquisition proposal

Status: Checkpoint B bounded acquisition scope approved by user 2026-10-29; execution tracked separately. Approval covers source acquisition only; empirical admission and Phase 8 quantitative protocol pending. Inventory describes evidence, not replay feasibility.

## Bounded scope

- Seasons: 2023-24, 2024-25, 2025-26 only. Exclude entire sealed 2026-27 season, including pre-GW6. No Candidate work, outcome analysis, optimizer, backtest, or archive modification.
- Store immutable, versioned research source packages outside `data/archive/`: e.g. `data/reports/replay-admission/v1/<season>/opening/`, `origins/gwNN/` and `outcomes/gwNN/`. Keep finalized outcome packages causally separate and inaccessible to forecast construction; do not treat report files as Season Archive.
- Opening package: deadline, full available player universe including blank-GW players, ownership, market price, club, position, eligibility and source capture/commit metadata. Preserve raw payload, manifest, hashes, source identity, capture and publication times.
- Each deadline package: issue-time complete universe, prices, club and position, availability, eligibility, deadline, fixture schedule through six GWs clipped at GW38, stable player and club ID mappings, and accessible pre-origin seed/training history. Preserve postponements and announcement timestamps, not later realized schedules. Record missing fields and chronology explicitly; no silent fallback to terminal metadata. Ownership is required once for the GW1 anchor; later origins reference its frozen identity and do not require fresh ownership.
- Finalized outcome packages: realized player-fixture points, minutes, appearance and card information, measurable native event components, fixture and player IDs, finalization status, provenance and hashes. Retain historical assist and bonus semantics; mark missing or unsupported components rather than reconstructing them from current rules. Acquisition and coverage validation only: no model evaluation, solver, outcome comparisons or outcome analysis. Existing coverage summaries do not establish these fields at any origin.

## Review and admission

- Compare capture and trustworthy source-publication timestamps to issue deadline; require immutable content hashes and reproducible lineage. Git author/committer timestamps corroborate timing, not independent proof of capture, freshness or completeness.
- Measure snapshot age and observed capture gaps per field and season. Propose a maximum gap after inspecting coverage and source behavior; record rationale and seek human review before accepting a threshold. Reject post-deadline, unverifiable or incomplete inputs; retain blocked origins explicitly.
- Define eligibility from contemporaneous source semantics, including unavailable and blank-GW players; review position, club and player ID changes. Never infer eligibility from end-of-season metadata.
- Audit season-native scoring, FT, chip and event-definition rules separately. Documentary sources do not prove implementation. Missing native component definitions or measurements remain unassessed; no fabricated historical assists or bonus.
- Identify available public sources, immutable versions, access constraints and provenance before any acquisition. Coverage and reconstruction cannot be guaranteed. Record source-level gaps and failed retrievals without narrowing the requested window.
- Review of this acquisition scope does not approve empirical admission. Admission requires independent evidence and validation; numerical approval remains Phase 8. No Champion configuration changes.

## Reproduction

Run `.venv/Scripts/python.exe docs/research/backtesting-promotion-foundation/build_admission_inventory.py`. Inputs: `ownership_local_coverage.csv`, `ownership_snapshot_samples.csv`, `ownership_snapshot_provenance.csv`. Output: `replay_admission_inventory.csv`, 38 origins per season; all evidence statuses conservative until separately admitted. Opening samples do not certify even GW1 admission, and cannot establish later origin coverage. Deadline price and membership require independent evidence at every origin; ID mappings are part of membership and component coverage.

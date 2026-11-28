# Active Task: Internal Minutes Baseline v2 & Layer 1 Pure-History Minutes Diagnostics

- **Status:** In Progress
- **Objective:** Execute Wayfinder Map #256 sequentially (Track A #257 -> Track B #258 -> Track C #259) under ADR 0073.
- **Acceptance:** Tracks #257 and #258 pass Q1 Two-Stage Dual-Win Gate on S-1 + untuned S-2 and merge to main with CLI/Dashboard parity; Track #259 completes Track B S-1 screen + bounded pure-history Layer 1 screening logged in candidate_ledger.csv.
- **Issue/Ticket:** Wayfinder Map #256 (Tracks #257, #258, #259; ADR 0073)

## Work Packet (SFDBN)

- **Status:** `/grill-with-docs` Q1–Q7 complete; ADR 0073, CONTEXT.md, and GitHub issues #256–#259 ready; implementation unstarted.
- **Files:** `docs/adr/0073-internal-minutes-baseline-v2-and-causal-availability-history.md`, `docs/adr/README.md`, `CONTEXT.md`, `docs/agents/current-state.md`, `ROADMAP.md`, `.agents/handoff-pointer`
- **Decisions:** Path 1 (Layer 2 `v2` first -> Layer 1 pure-history screen). Q1 Two-Stage Dual-Win Gate (`t=0..5` state-stratified xMins + `false_start_pct` AND certified `S-1`/`S-2` rolling MILP > `2,207`/`2,308`, preserving ADR 0072; `2026-27` Solio diagnostic read-only). Q2/Q2-rev Buckets A+B+C (`50.8%` of `8.81m` Solio MAE; GKP `M1` `0.48m`) + isolated downward-only `>900m` overflow cap toggle (D-lite). Q3/Q5 causal `< target_gw` availability history (`availability_history.parquet` synced from `origin/availability-snapshots` + live captures, `S-1`/`S-2` `gw*.json.xz`, single-snapshot fallback). Q4 Track C screens up to 3 pure-history Layer 1 levers (`xmins_if_start`, `Trailing Start Window`, `0.5^h` decay) via Track B `S-1` before `ADR 0071`.
- **Blocked:** None
- **Next:** On updated `main`, branch `git checkout -b feat/availability-history-and-shield-fixes` and execute Track A (#257) via TDD + two-axis `/code-review` + `bash tests/verify.sh`.

## Todo

- [ ] Track A (#257): Causal Availability History cache (`data/processed/availability_history.parquet`) + Bucket C `SP_Soft_Shield` fixes
- [ ] Track B (#258): Injury-aware outfield starter floor (A), documented-injury return recovery (B), optional downward overflow cap (D-lite), Q1 Dual-Win certification
- [ ] Track C (#259): Phase 2 Layer 1 Track B `S-1` screen + up to 3 pure-history levers (`ADR 0071`, `candidate_ledger.csv`)

## Blockers / Notes

- Local Solio diagnostic `data/external/solio/2026-27/gw13_2026-11-28T2323.csv` is gitignored and local-only (not synced via git); `S-1`/`S-2` empirical mirrors and `origin/availability-snapshots` are authoritative sources across devices.
- Pre-existing local `data/archive/2026-27/` working-tree updates on source device were intentionally left unstaged/uncommitted.

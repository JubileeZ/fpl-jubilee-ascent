# Active Task: refresh-concurrency-pipeline

- **Status:** In Progress
- **Objective:** Streamline FPL data refresh and snapshot season ingestion into a single asyncio.gather pipeline governed by an asyncio.Semaphore(concurrency=20 by default, CLI-configurable) without sequential batch chunking or sleeps.
- **Acceptance:**
  - `commands.refresh_data` and `commands.snapshot_season` pull all player summaries in a single pipeline without `chunk_size = 50` or `sleep(0.5)`.
  - Both commands support `--concurrency` flag (default 20).
  - CLI logs milestone progress every 100 players and final elapsed time.
  - `features.processor.process_directory` sorts `summary_files` deterministically.
  - Tests verify concurrency flag, milestone progress, pipeline completion, and deterministic parquet output.
  - `uv run ruff check .`, `uv run pytest`, and `bash tests/verify.sh` pass.
- **Issue/Ticket:** N/A

## Work Packet (SFDBN)

- **Status:** In Progress
- **Files:** `commands/refresh_data.py`, `commands/snapshot_season.py`, `features/processor.py`, `tests/test_refresh_data.py`, `tests/test_snapshot_season.py`, `tests/test_processor.py`
- **Decisions:** Concurrency default 20 with CLI override; single gather pipeline with Semaphore; milestone log every 100 players; sort summary files in processor.
- **Blocked:** None
- **Next:** User review and acceptance.

## Todo
- [x] Add unit tests for `--concurrency` argument and pipeline execution in `test_refresh_data.py` and `test_snapshot_season.py`
- [x] Add unit test for deterministic `summary_files` sorting in `test_processor.py`
- [x] Update `commands/refresh_data.py` with `--concurrency`, single pipeline, `httpx.Limits`, and milestone logger
- [x] Update `commands/snapshot_season.py` with `--concurrency`, single pipeline, `httpx.Limits`, and milestone logger
- [x] Update `features/processor.py` to sort `summary_files`
- [x] Run test suite, verify delivery gate, and review
- [ ] User review and verification

## Blockers / Notes
- None

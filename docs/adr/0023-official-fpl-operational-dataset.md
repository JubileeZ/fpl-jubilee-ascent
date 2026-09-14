# Operational Dataset is Official FPL plus Season Archive

Production ingest, Feature Contract, Model Champion, Transfer Plan, and Ownership Explorer use only Official FPL API responses and git-tracked Season Archives of those responses. Research-Only Evidence (FBref, Understat, editorial XI, literature) may live in Research Notes and frozen constants; it must not write Raw Cache, Season Archive ingest, Feature Contract, or Champion inputs. Dual-Source Lineup Signals are not an operational source. `--from-vaastav-dir` stays only as a frozen reconstruct of the existing 2024-25 Season Archive, not a live pull. Live Raw Cache and `data/processed/` stay gitignored. Live-season pin cadence, Official-only pin contents, and hash-gated git commits: ADR 0032.

**Status:** Accepted. Pin cadence and pin-everything copy superseded by ADR 0032. ADR 0009 / 0010 no-third-party-xP still stand. ADR 0020 vaastav 2024-25 reconstruct still allowed; new seasons use `--from-raw-dir` or live snapshot.

**Considered:** Live API only (drops 2024-25 seed); ongoing vaastav as FPL-field dump; un-ignore live Raw Cache on every refresh; Research fetch writing Feature Contract. Rejected: live API cannot re-snapshot 2024-25; vaastav is other-source maintenance; refresh-commit noise; Q4 forbids other-source production ingest.

**Consequences:** `clients/` stay FPL-only. Season 2026-27 git backup is the Live Season Pin under `data/archive/2026-27/` (ADR 0032), not `data/raw/` in git. `data/session_token.json` stays ignored.

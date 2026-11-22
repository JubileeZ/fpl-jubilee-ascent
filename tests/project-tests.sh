#!/usr/bin/env bash
set -euo pipefail

uv run --locked ruff check .
uv run --locked pytest -q 'tests/test_projection_parity.py::test_dashboard_csv_parity[near-term]'

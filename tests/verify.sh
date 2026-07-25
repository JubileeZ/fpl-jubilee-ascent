#!/usr/bin/env bash
# tests/verify.sh — Portable delivery gate (harness integrity + project validation)
#
# Invoked by commit-gate, IDE adapters, and CI. Exit 0 only when all checks pass.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

PASS=0
FAIL=0

pass() {
  printf "  \033[0;32m✓\033[0m %s\n" "$1"
  PASS=$((PASS + 1))
}

fail() {
  printf "  \033[0;31m✗\033[0m %s\n" "$1"
  FAIL=$((FAIL + 1))
}

check_file() {
  local file="$1"
  if [ -f "${file}" ]; then
    pass "File exists: ${file}"
  else
    fail "File missing: ${file}"
  fi
}

check_executable() {
  local file="$1"
  if [ -x "${file}" ]; then
    pass "Executable: ${file}"
  else
    fail "Not executable: ${file}"
  fi
}

echo "Running Alpha-Zero-G verify (portable gate)..."

# --- Harness integrity ---
check_file "AGENTS.md"
check_file "ROADMAP.md"
check_file "docs/agents/current-state.md"
check_file "docs/agents/progress.md"
check_file "docs/agents/issue-tracker.md"
check_file "docs/agents/triage-labels.md"
check_file "docs/agents/domain.md"
check_file ".agents/hooks.json"
check_file ".agents/spawn-budget.json"

for hook in \
  block-destructive-ops.sh \
  commit-gate.sh \
  checkpoint.sh \
  spawn-budget.sh \
  pre-compact.sh
do
  check_file ".agents/hooks/${hook}"
  check_executable ".agents/hooks/${hook}"
done

check_file "tests/test-harness.sh"
check_executable "tests/test-harness.sh"
check_file "tests/verify.sh"
check_executable "tests/verify.sh"

# --- No leaked test temp dirs at project root ---
shopt -s nullglob
_azg_leaks=(tmp_azg*)
shopt -u nullglob
if [ "${#_azg_leaks[@]}" -gt 0 ]; then
  fail "Leaked temp dirs at project root: ${_azg_leaks[*]} (delete; tests must use TMPDIR)"
else
  pass "No tmp_azg* leaks at project root"
fi

# --- Work Packet (required when task.md present) ---
if [ -f "task.md" ]; then
  for marker in \
    "**Objective:**" \
    "**Acceptance:**" \
    "## Work Packet (SFDBN)" \
    "**Status:**" \
    "**Files:**" \
    "**Decisions:**" \
    "**Blocked:**" \
    "**Next:**"
  do
    if grep -qF "${marker}" task.md; then
      pass "Work Packet has ${marker}"
    else
      fail "Work Packet missing ${marker}"
    fi
  done
fi

# --- Project validation (optional until configured) ---
project_test_cmd=""
if [ -x "tests/project-tests.sh" ]; then
  project_test_cmd="tests/project-tests.sh"
elif [ -n "${AZG_PROJECT_TEST_CMD:-}" ]; then
  project_test_cmd="${AZG_PROJECT_TEST_CMD}"
elif [ -f ".azg/project-test-cmd" ]; then
  project_test_cmd="$(tr -d '\r\n' < .azg/project-test-cmd)"
fi

if [ -n "${project_test_cmd}" ]; then
  echo "Running project validation: ${project_test_cmd}"
  if eval "${project_test_cmd}"; then
    pass "Project validation passed"
  else
    fail "Project validation failed"
  fi
else
  echo "  – No project validation configured (tests/project-tests.sh or .azg/project-test-cmd)"
fi

echo ""
echo "Verify results: ${PASS} passed, ${FAIL} failed."

if [ "${FAIL}" -gt 0 ]; then
  exit 1
fi
exit 0

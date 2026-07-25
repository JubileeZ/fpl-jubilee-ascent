#!/usr/bin/env bash
# tests/test-harness.sh — Verifies the integrity of the Alpha-Zero-G project harness

set -euo pipefail

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
    if [ -f "$file" ]; then
        pass "File exists: $file"
    else
        fail "File missing: $file"
    fi
}

check_executable() {
    local file="$1"
    if [ -x "$file" ]; then
        pass "Executable check: $file is executable"
    else
        fail "Executable check: $file is NOT executable"
    fi
}

echo "Running Alpha-Zero-G Project Harness Self-Check..."

# 1. Check core documentation files
check_file "AGENTS.md"
check_file "ROADMAP.md"

# task.md is transient; it is required if any active session files exist
if [ -f "implementation_plan.md" ] || [ -f "walkthrough.md" ] || [ -f "task.md" ]; then
    check_file "task.md"
fi

# 2. Check agent guides
check_file "docs/agents/current-state.md"
check_file "docs/agents/progress.md"
check_file "docs/agents/issue-tracker.md"
check_file "docs/agents/triage-labels.md"
check_file "docs/agents/domain.md"

# 3. Check configuration and hooks
check_file ".agents/hooks.json"
check_file ".agents/spawn-budget.json"
check_file ".agents/hooks/block-destructive-ops.sh"
check_executable ".agents/hooks/block-destructive-ops.sh"

# 4. Check hook scripts (check if present, then check if executable)
if [ -f ".agents/hooks/commit-gate.sh" ]; then
    check_executable ".agents/hooks/commit-gate.sh"
fi
if [ -f ".agents/hooks/checkpoint.sh" ]; then
    check_executable ".agents/hooks/checkpoint.sh"
fi

# 5. Shellcheck verification (if installed)
if command -v shellcheck >/dev/null 2>&1; then
    if shellcheck .agents/hooks/*.sh; then
        pass "Shellcheck passed for all hook scripts"
    else
        fail "Shellcheck failed for one or more hook scripts"
    fi
else
    echo "  – Shellcheck not installed (skipping lint check)"
fi

echo ""
echo "Harness check results: $PASS passed, $FAIL failed."

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
exit 0

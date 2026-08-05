#!/usr/bin/env bash
# Cursor adapter: checkpoint via followup_message (agy checkpoint.sh uses decision continue)
set -euo pipefail

input=$(cat)
: "${input}"

CHECKPOINT_REASON='Code changes without Work Packet / continuity update. Update task.md (SFDBN), docs/agents/current-state.md, or .agents/session-handoff.md, then Checkpoint before stopping.'
LOOP_LIMIT=3

loop_count=0
status="completed"
loop_count=$(printf '%s' "${input}" | jq -r '.loop_count // 0' 2>/dev/null || echo 0)
status=$(printf '%s' "${input}" | jq -r '.status // "completed"' 2>/dev/null || echo completed)

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  printf '{}\n'
  exit 0
fi

_hook_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../.agents/hooks/checkpoint-scan.sh
source "${_hook_dir}/../../.agents/hooks/checkpoint-scan.sh"
azg_checkpoint_scan_porcelain

if [ "${AZG_CHECKPOINT_HAS_CODE}" = true ] && [ "${AZG_CHECKPOINT_HAS_WORKSTATE}" = false ] \
  && [ "${status}" = "completed" ] && [ "${loop_count}" -lt "${LOOP_LIMIT}" ]; then
  jq -n --arg m "${CHECKPOINT_REASON}" '{followup_message: $m}'
  exit 0
fi

printf '{}\n'
exit 0

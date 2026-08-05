#!/usr/bin/env bash
# checkpoint.sh — Stop hook: require Work Packet / continuity update with code
# Stop schema: decision "continue" + reason; any other value allows stop
set -euo pipefail

input=$(cat)
: "${input}"

CHECKPOINT_REASON='Code changes without Work Packet / continuity update. Update task.md (SFDBN), docs/agents/current-state.md, or .agents/session-handoff.md, then Checkpoint before stopping.'

_hook_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=checkpoint-scan.sh
source "${_hook_dir}/checkpoint-scan.sh"
azg_checkpoint_scan_porcelain

if [ "${AZG_CHECKPOINT_HAS_CODE}" = true ] && [ "${AZG_CHECKPOINT_HAS_WORKSTATE}" = false ]; then
  jq -n --arg r "${CHECKPOINT_REASON}" '{decision: "continue", reason: $r}'
  exit 0
fi

printf '{"decision":"allow"}\n'
exit 0

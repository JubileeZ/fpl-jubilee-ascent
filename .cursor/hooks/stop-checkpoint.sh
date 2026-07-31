#!/usr/bin/env bash
# Cursor adapter: remind to Checkpoint via Work Packet (stop cannot hard-deny)
# Accept same workstate set as Antigravity checkpoint.sh
set -euo pipefail

input=$(cat)
: "${input}"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  printf '{}\n'
  exit 0
fi

has_code_changes=false
has_workstate_update=false

while IFS= read -r line; do
  [ -z "${line}" ] && continue
  file_path=$(printf '%s' "${line}" | cut -c 4-)
  file_path="${file_path#\"}"
  file_path="${file_path%\"}"
  case "${file_path}" in
    .agents/spawn-state.json|.agents/session-handoff.md.tmpl) continue ;;
  esac
  case "${file_path}" in
    task.md|docs/agents/current-state.md|.agents/session-handoff.md)
      has_workstate_update=true
      ;;
    ROADMAP.md) ;;
    *)
      has_code_changes=true
      ;;
  esac
done < <(git status --porcelain 2>/dev/null)

if [ "${has_code_changes}" = true ] && [ "${has_workstate_update}" = false ]; then
  printf '{"followup_message":"Code changes without Work Packet / continuity update. Update task.md (SFDBN), docs/agents/current-state.md, or .agents/session-handoff.md, then Checkpoint before stopping."}\n'
  exit 0
fi

printf '{}\n'
exit 0

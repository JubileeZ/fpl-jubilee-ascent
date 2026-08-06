#!/usr/bin/env bash
# checkpoint-scan.sh — shared porcelain scan for Stop checkpoint hooks
# After azg_checkpoint_scan_porcelain: AZG_CHECKPOINT_HAS_CODE, AZG_CHECKPOINT_HAS_WORKSTATE (true/false)

azg_checkpoint_scan_porcelain() {
  AZG_CHECKPOINT_HAS_CODE=false
  AZG_CHECKPOINT_HAS_WORKSTATE=false

  if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    return 0
  fi

  while IFS= read -r line; do
    [ -z "${line}" ] && continue
    local file_path
    file_path=$(printf '%s' "${line}" | cut -c 4-)
    file_path="${file_path#\"}"
    file_path="${file_path%\"}"
    case "${file_path}" in
      .agents/session-handoff.md.tmpl) continue ;;
    esac
    case "${file_path}" in
      task.md|docs/agents/current-state.md|.agents/session-handoff.md)
        AZG_CHECKPOINT_HAS_WORKSTATE=true
        ;;
      ROADMAP.md) ;;
      *)
        AZG_CHECKPOINT_HAS_CODE=true
        ;;
    esac
  done < <(git status --porcelain 2>/dev/null)
}

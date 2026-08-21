#!/usr/bin/env bash
# commit-scan.sh — classify staged/commit paths for Checkpoint (commit-gate)
# After azg_commit_classify_paths: AZG_COMMIT_HAS_CODE, AZG_COMMIT_HAS_PACKET (true/false)
# Packet = any path under .agents/work-packets/ (add/modify/delete).
# Not code: ROADMAP, docs/agents/*, handoff pointer, leftover task.md / session-handoff.md

azg_commit_classify_paths() {
  AZG_COMMIT_HAS_CODE=false
  AZG_COMMIT_HAS_PACKET=false
  local f
  while IFS= read -r f; do
    [ -z "${f}" ] && continue
    f="${f#\"}"
    f="${f%\"}"
    case "${f}" in
      .agents/work-packets/*)
        AZG_COMMIT_HAS_PACKET=true
        ;;
      ROADMAP.md|docs/agents/*|.agents/session-handoff.md|.agents/handoff-pointer|task.md)
        ;;
      *)
        AZG_COMMIT_HAS_CODE=true
        ;;
    esac
  done
}

# Finished = at least one checked box and no open checkbox.
# No checkboxes: not finished (abandoned / imported packets stay).
azg_packet_is_finished() {
  local pkt="$1"
  [ -f "${pkt}" ] || return 1
  grep -q -E '\- \[[xX]\]' "${pkt}" || return 1
  if grep -q -E '\- \[[[:space:]]*\]' "${pkt}"; then
    return 1
  fi
  return 0
}

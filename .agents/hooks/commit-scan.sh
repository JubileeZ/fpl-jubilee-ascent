#!/usr/bin/env bash
# commit-scan.sh — classify staged/commit paths for Checkpoint (commit-gate)
# After azg_commit_classify_paths: AZG_COMMIT_HAS_CODE, AZG_COMMIT_HAS_PACKET (true/false)
# Packet = markdown files under .agents/work-packets/ (*.md) (add/modify/delete).
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
      .agents/work-packets/*.md)
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

# Finished = explicit complete/done status OR (at least one checked box and no open checkbox).
# No checkboxes and not marked complete: not finished (parked/abandoned stay).
azg_packet_is_finished() {
  local pkt="$1"
  [ -f "${pkt}" ] || return 1

  # Explicit status declaration (Complete, Completed, Done, Finished)
  if grep -qiE '^[[:space:]]*(-[[:space:]]+)?(\*\*)?[Ss]tatus:?(\*\*)?[[:space:]]*(complete|completed|done|finished)[[:space:]]*(\*\*)?[[:space:]]*$' "${pkt}"; then
    return 0
  fi

  grep -q -E '\- \[[xX]\]' "${pkt}" || return 1
  if grep -q -E '\- \[[[:space:]]*\]' "${pkt}"; then
    return 1
  fi
  return 0
}

azg_packet_is_in_progress() {
  local pkt="$1"
  [ -f "${pkt}" ] || return 1
  grep -qiE '^[[:space:]]*(-[[:space:]]+)?(\*\*)?[Ss]tatus:?(\*\*)?[[:space:]]*in[-[:space:]]+progress' "${pkt}"
}

azg_count_in_progress_packets() {
  local dir="${1:-.agents/work-packets}"
  AZG_IN_PROGRESS_COUNT=0
  AZG_IN_PROGRESS_PKTS=""
  shopt -s nullglob
  local pkt
  for pkt in "${dir}"/*.md; do
    if azg_packet_is_in_progress "${pkt}"; then
      AZG_IN_PROGRESS_COUNT=$((AZG_IN_PROGRESS_COUNT + 1))
      AZG_IN_PROGRESS_PKTS="${AZG_IN_PROGRESS_PKTS} ${pkt}"
    fi
  done
  shopt -u nullglob
}

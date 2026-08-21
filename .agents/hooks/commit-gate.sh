#!/usr/bin/env bash
# commit-gate.sh — block commit until harness test passes
input=$(cat)

tool_name=$(printf '%s' "$input" | jq -r '.toolCall.name // empty' 2>/dev/null)
cmd=$(printf '%s' "$input" | jq -r '.toolCall.args.CommandLine // empty' 2>/dev/null)

# Only intercept git commit commands
if [ "$tool_name" = "run_command" ] || [ -n "$cmd" ]; then
  if echo "$cmd" | grep -qE '^git[[:space:]]+commit'; then
    _hook_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    # shellcheck source=commit-scan.sh
    source "${_hook_dir}/commit-scan.sh"
    # Finished Work Packet still on disk → delete it (do not leave stubs)
    shopt -s nullglob
    for pkt in .agents/work-packets/*.md; do
      if azg_packet_is_finished "$pkt"; then
        reason="Finished Work Packet still present: ${pkt}. Delete it in this Checkpoint (do not leave empty stubs)."
        jq -n --arg r "$reason" '{decision: "deny", reason: $r}'
        shopt -u nullglob
        exit 0
      fi
    done
    shopt -u nullglob
    if azg_packet_is_finished "task.md"; then
      reason="Legacy task.md is complete. Delete task.md (azg apply migrates it to .agents/work-packets/) plus implementation_plan.md / walkthrough.md if present."
      jq -n --arg r "$reason" '{decision: "deny", reason: $r}'
      exit 0
    fi
    if [ -f "implementation_plan.md" ] || [ -f "walkthrough.md" ]; then
      open_pkt=false
      shopt -s nullglob
      for pkt in .agents/work-packets/*.md; do
        if grep -q -E '\- \[[[:space:]]*\]' "$pkt"; then
          open_pkt=true
        fi
      done
      shopt -u nullglob
      if [ "$open_pkt" = false ]; then
        reason="Delete implementation_plan.md and walkthrough.md when no open Work Packet remains."
        jq -n --arg r "$reason" '{decision: "deny", reason: $r}'
        exit 0
      fi
    fi

    verify_script="tests/verify.sh"
    if [ ! -x "${verify_script}" ]; then
      reason="Missing executable tests/verify.sh — portable delivery gate required."
      jq -n --arg r "$reason" '{decision: "deny", reason: $r}'
      exit 0
    fi

    verify_output=$(bash "${verify_script}" 2>&1)
    verify_status=$?
    if [ $verify_status -ne 0 ]; then
      reason="verify.sh failed:\n$verify_output"
      jq -n --arg r "$reason" '{decision: "deny", reason: $r}'
      exit 0
    fi

    # Checkpoint: code commits must stage a Work Packet path
    if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
      file_list=""
      if echo "$cmd" | grep -qE '(^|[[:space:]])(-a|--all)([[:space:]]|$)'; then
        file_list=$(git status --porcelain 2>/dev/null | cut -c 4- | sed 's/^"//;s/"$//')
      else
        file_list=$(git diff --cached --name-only 2>/dev/null)
      fi
      azg_commit_classify_paths <<EOF
${file_list}
EOF
      if [ "${AZG_COMMIT_HAS_CODE}" = true ] && [ "${AZG_COMMIT_HAS_PACKET}" = false ]; then
        reason="Checkpoint requires Work Packet: stage a file under .agents/work-packets/ (update or delete) with the code changes, then commit."
        jq -n --arg r "$reason" '{decision: "deny", reason: $r}'
        exit 0
      fi
    fi
  fi
fi

printf '{"decision":"allow"}\n'
exit 0

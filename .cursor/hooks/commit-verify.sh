#!/usr/bin/env bash
# Cursor adapter: run portable verify.sh before git commit
set -euo pipefail

input=$(cat)
cmd=$(printf '%s' "${input}" | jq -r '.command // .tool_input.command // empty' 2>/dev/null || true)

if ! echo "${cmd}" | grep -qE 'git[[:space:]]+commit'; then
  printf '{"permission":"allow"}\n'
  exit 0
fi

if [ ! -x tests/verify.sh ]; then
  printf '{"permission":"deny","user_message":"Missing tests/verify.sh","agent_message":"Portable delivery gate tests/verify.sh is missing or not executable."}\n'
  exit 0
fi

if ! out=$(bash tests/verify.sh 2>&1); then
  jq -n --arg msg "$(printf '%s' "${out}" | tr '\n' ' ')" \
    '{permission: "deny", user_message: "verify.sh failed", agent_message: ("verify.sh failed: " + $msg)}'
  exit 0
fi

_hook_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=../../.agents/hooks/commit-scan.sh
source "${_hook_dir}/../../.agents/hooks/commit-scan.sh"

# Finished Work Packet still on disk → delete it
shopt -s nullglob
for pkt in .agents/work-packets/*.md; do
  if azg_packet_is_finished "${pkt}"; then
    jq -n --arg p "${pkt}" '{permission:"deny",user_message:"Finished Work Packet still present",agent_message:("Delete " + $p + " in this Checkpoint.")}'
    shopt -u nullglob
    exit 0
  fi
done
shopt -u nullglob
if azg_packet_is_finished "task.md"; then
  printf '{"permission":"deny","user_message":"Legacy task.md is complete","agent_message":"Delete task.md (azg apply migrates it) plus implementation_plan.md / walkthrough.md if present."}\n'
  exit 0
fi

# Checkpoint freshness (same contract as Antigravity commit-gate)
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  file_list=""
  if echo "${cmd}" | grep -qE '(^|[[:space:]])(-a|--all)([[:space:]]|$)'; then
    file_list=$(git status --porcelain 2>/dev/null | cut -c 4- | sed 's/^"//;s/"$//')
  else
    file_list=$(git diff --cached --name-only 2>/dev/null)
  fi
  azg_commit_classify_paths <<EOF
${file_list}
EOF
  if [ "${AZG_COMMIT_HAS_CODE}" = true ] && [ "${AZG_COMMIT_HAS_PACKET}" = false ]; then
    printf '{"permission":"deny","user_message":"Checkpoint requires Work Packet","agent_message":"Stage a file under .agents/work-packets/ (update or delete) with the code changes, then commit."}\n'
    exit 0
  fi
fi

printf '{"permission":"allow"}\n'
exit 0

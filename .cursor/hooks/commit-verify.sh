#!/usr/bin/env bash
# Cursor adapter: run portable verify.sh before git commit
set -euo pipefail

input=$(cat)
cmd=""
if command -v jq >/dev/null 2>&1; then
  cmd=$(printf '%s' "${input}" | jq -r '.command // .tool_input.command // empty' 2>/dev/null || true)
fi
if [ -z "${cmd}" ]; then
  cmd=$(printf '%s' "${input}" | sed -n 's/.*"command"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n1)
fi

if ! echo "${cmd}" | grep -qE 'git[[:space:]]+commit'; then
  printf '{"permission":"allow"}\n'
  exit 0
fi

if [ ! -x tests/verify.sh ]; then
  printf '{"permission":"deny","user_message":"Missing tests/verify.sh","agent_message":"Portable delivery gate tests/verify.sh is missing or not executable."}\n'
  exit 0
fi

if ! out=$(bash tests/verify.sh 2>&1); then
  # Escape for JSON without requiring jq
  esc=$(printf '%s' "${out}" | tr '\n' ' ' | sed 's/"/\\"/g')
  printf '{"permission":"deny","user_message":"verify.sh failed","agent_message":"verify.sh failed: %s"}\n' "${esc}"
  exit 0
fi

# Checkpoint freshness (same contract as Antigravity commit-gate)
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  has_code=false
  has_packet=false
  file_list=""
  if echo "${cmd}" | grep -qE '(^|[[:space:]])(-a|--all)([[:space:]]|$)'; then
    file_list=$(git status --porcelain 2>/dev/null | cut -c 4- | sed 's/^"//;s/"$//')
  else
    file_list=$(git diff --cached --name-only 2>/dev/null)
  fi
  while IFS= read -r f; do
    [ -z "$f" ] && continue
    case "$f" in
      task.md) has_packet=true ;;
      ROADMAP.md|docs/agents/*|.agents/session-handoff.md) ;;
      *) has_code=true ;;
    esac
  done <<< "${file_list}"
  if [ "$has_code" = true ] && [ "$has_packet" = false ]; then
    printf '{"permission":"deny","user_message":"Checkpoint requires Work Packet","agent_message":"Stage an updated task.md Work Packet with the code changes, then commit."}\n'
    exit 0
  fi
fi

printf '{"permission":"allow"}\n'
exit 0

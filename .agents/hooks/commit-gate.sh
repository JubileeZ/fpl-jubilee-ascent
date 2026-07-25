#!/usr/bin/env bash
# commit-gate.sh — block commit until harness test passes
input=$(cat)

tool_name=""
cmd=""

if command -v jq >/dev/null 2>&1; then
  tool_name=$(printf '%s' "$input" | jq -r '.toolCall.name // empty' 2>/dev/null)
  cmd=$(printf '%s' "$input" | jq -r '.toolCall.args.CommandLine // empty' 2>/dev/null)
else
  tool_name=$(printf '%s' "$input" | sed -n 's/.*"name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n1)
  cmd=$(printf '%s' "$input" | sed -n 's/.*"CommandLine"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n1)
fi

# Only intercept git commit commands
if [ "$tool_name" = "run_command" ] || [ -n "$cmd" ]; then
  if echo "$cmd" | grep -qE '^git[[:space:]]+commit'; then
    # Verify no transient file leftovers if the task is complete
    if [ -f "task.md" ] && ! grep -q -E '\- \[[[:space:]]*\]' task.md; then
      if [ -f "implementation_plan.md" ] || [ -f "walkthrough.md" ] || [ -s "task.md" ]; then
        reason="Task is complete (no unchecked items in task.md). Please delete task.md, implementation_plan.md, and walkthrough.md (or clear task.md) to avoid leaving transient files in the repository."
        if command -v jq >/dev/null 2>&1; then
          jq -n --arg r "$reason" '{decision: "deny", reason: $r}'
        else
          escaped_reason=$(printf '%s' "$reason" | sed 's/"/\"/g' | tr '\n' ' ')
          printf '{"decision":"deny","reason":"%s"}\n' "$escaped_reason"
        fi
        exit 0
      fi
    fi

    # Portable delivery gate (harness integrity + optional project validation)
    verify_script="tests/verify.sh"
    if [ ! -x "${verify_script}" ]; then
      reason="Missing executable tests/verify.sh — portable delivery gate required."
      if command -v jq >/dev/null 2>&1; then
        jq -n --arg r "$reason" '{decision: "deny", reason: $r}'
      else
        escaped_reason=$(printf '%s' "$reason" | sed 's/"/\\"/g' | tr '\n' ' ')
        printf '{"decision":"deny","reason":"%s"}\n' "$escaped_reason"
      fi
      exit 0
    fi

    verify_output=$(bash "${verify_script}" 2>&1)
    verify_status=$?
    if [ $verify_status -ne 0 ]; then
      reason="verify.sh failed:\n$verify_output"
      if command -v jq >/dev/null 2>&1; then
        jq -n --arg r "$reason" '{decision: "deny", reason: $r}'
      else
        escaped_reason=$(printf '%s' "$reason" | sed 's/"/\\"/g' | tr '\n' ' ')
        printf '{"decision":"deny","reason":"%s"}\n' "$escaped_reason"
      fi
      exit 0
    fi

    # Checkpoint freshness: code commits must include Work Packet (task.md)
    if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
      has_code=false
      has_packet=false
      file_list=""
      if echo "$cmd" | grep -qE '(^|[[:space:]])(-a|--all)([[:space:]]|$)'; then
        file_list=$(git status --porcelain 2>/dev/null | cut -c 4- | sed 's/^"//;s/"$//')
      else
        file_list=$(git diff --cached --name-only 2>/dev/null)
      fi
      while IFS= read -r f; do
        [ -z "$f" ] && continue
        case "$f" in
          task.md)
            has_packet=true
            ;;
          ROADMAP.md|docs/agents/*|.agents/session-handoff.md)
            ;;
          *)
            has_code=true
            ;;
        esac
      done <<< "${file_list}"

      if [ "$has_code" = true ] && [ "$has_packet" = false ]; then
        reason="Checkpoint requires Work Packet: stage an updated task.md with the code changes (objective/acceptance/SFDBN), then commit."
        if command -v jq >/dev/null 2>&1; then
          jq -n --arg r "$reason" '{decision: "deny", reason: $r}'
        else
          escaped_reason=$(printf '%s' "$reason" | sed 's/"/\\"/g' | tr '\n' ' ')
          printf '{"decision":"deny","reason":"%s"}\n' "$escaped_reason"
        fi
        exit 0
      fi
    fi
  fi
fi

printf '{"decision":"allow"}\n'
exit 0

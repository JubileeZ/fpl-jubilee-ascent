#!/usr/bin/env bash
# block-destructive-ops.sh
input=$(cat)

tool_name=""
cmd=""
target_file=""

if command -v jq >/dev/null 2>&1; then
  tool_name=$(printf '%s' "$input" | jq -r '.toolCall.name // empty' 2>/dev/null)
  cmd=$(printf '%s' "$input" | jq -r '.toolCall.args.CommandLine // .command // empty' 2>/dev/null)
  target_file=$(printf '%s' "$input" | jq -r '.toolCall.args.TargetFile // .toolCall.args.path // .toolCall.args.file // empty' 2>/dev/null)
fi

# Fallback parsing in case jq is not present or parsing failed
if [ -z "$tool_name" ]; then
  tool_name=$(printf '%s' "$input" | sed -n 's/.*"name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n1)
fi
if [ -z "$cmd" ]; then
  cmd=$(printf '%s' "$input" | sed -n 's/.*"CommandLine"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n1)
fi
if [ -z "$target_file" ]; then
  target_file=$(printf '%s' "$input" | sed -n 's/.*"TargetFile"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n1)
  [ -z "$target_file" ] && target_file=$(printf '%s' "$input" | sed -n 's/.*"path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n1)
  [ -z "$target_file" ] && target_file=$(printf '%s' "$input" | sed -n 's/.*"file"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n1)
fi

# 1. Protect hooks and .agents configuration from being modified via file writing tools
if [[ "$tool_name" =~ ^(write_to_file|replace_file_content|multi_replace_file_content|write_file|edit_file)$ ]]; then
  # Deny direct modifications to hook scripts or configurations
  if [[ "$target_file" =~ (hooks\.json|hooks/|\.cursor/hooks) ]]; then
    printf '{"decision":"deny","reason":"Modifying safety-gate configuration or hooks is not allowed. Apply edits to these files manually if needed."}\n'
    exit 0
  fi
  # Whitelist strictly .agents/work-packets/*.md and .agents/handoff-pointer under .agents/
  if [[ "$target_file" =~ \.agents ]]; then
    if ! [[ "$target_file" =~ (^|/)\.agents/(work-packets/[a-zA-Z0-9_.-]+\.md|handoff-pointer)$ ]]; then
      printf '{"decision":"deny","reason":"Modifying safety-gate configuration or non-packet files in .agents is not allowed. Only .agents/work-packets/*.md and .agents/handoff-pointer may be edited by agents."}\n'
      exit 0
    fi
  fi
fi

# 2. Protect hooks and .agents configuration from being modified via command line
if [ "$tool_name" = "run_command" ] || [ -n "$cmd" ]; then
  # Block chmod under .agents or .cursor
  if printf '%s' "$cmd" | grep -qE '(^|[[:space:]])chmod[[:space:]]+.*(\.agents|\.cursor)'; then
    printf '{"decision":"deny","reason":"Modifying permissions under .agents or .cursor is not allowed."}\n'
    exit 0
  fi

  # Block executing scripts from .agents/work-packets
  if printf '%s' "$cmd" | grep -qE '(^|[[:space:]])(\./\.agents/work-packets/|(bash|sh|zsh|python|python3|node|perl|ruby)[[:space:]]+.*\.agents/work-packets)'; then
    printf '{"decision":"deny","reason":"Executing scripts from .agents/work-packets is not allowed."}\n'
    exit 0
  fi

  # Block modifying safety hooks, hook configs, or .cursor hooks
  if printf '%s' "$cmd" | grep -qE '(^|[[:space:]])((rm|mv|cp|sed|echo|tee|chmod|write|overwrite|touch)[[:space:]]+|>|>>|git[[:space:]]+(checkout|reset|clean|revert)[[:space:]]+).*(hooks\.json|hooks/|\.cursor)'; then
    printf '{"decision":"deny","reason":"Modifying safety-gate configuration or hooks is not allowed. Apply edits to these files manually if needed."}\n'
    exit 0
  fi

  # Block modifying .agents generally, unless strictly targeting .agents/work-packets/*.md or .agents/handoff-pointer
  if printf '%s' "$cmd" | grep -qE '(^|[[:space:]])((rm|mv|cp|sed|echo|tee|chmod|write|overwrite|touch)[[:space:]]+|>|>>|git[[:space:]]+(checkout|reset|clean|revert)[[:space:]]+).*\.agents'; then
    if printf '%s' "$cmd" | grep -qE 'rm[[:space:]]+.*(-[a-zA-Z]*[rR]|--recursive).*\.agents'; then
      printf '{"decision":"deny","reason":"Modifying safety-gate configuration or hooks is not allowed. Apply edits to these files manually if needed."}\n'
      exit 0
    fi
    stripped=$(printf '%s' "$cmd" | sed -E 's/\.agents\/(work-packets\/[a-zA-Z0-9_.-]+\.md|handoff-pointer)//g')
    if printf '%s' "$stripped" | grep -q '\.agents'; then
      printf '{"decision":"deny","reason":"Modifying safety-gate configuration or hooks is not allowed. Apply edits to these files manually if needed."}\n'
      exit 0
    fi
  fi
fi

haystack="$cmd $input"

patterns=(
  'rm[[:space:]]+(-[a-zA-Z]*[rRfF][a-zA-Z]*|--recursive|--force)[[:space:]]+.*(/[[:space:]]*(\{| |$)|~|\$HOME|\./)'
  'git[[:space:]]+push([[:space:]].*)?--force'
  'git[[:space:]]+push([[:space:]].*)?[[:space:]]-f([[:space:]]|$)'
  'git[[:space:]]+reset[[:space:]]+--hard'
  'git[[:space:]]+branch[[:space:]]+-D'
  'git[[:space:]]+clean[[:space:]]+.*-f'
  'chmod[[:space:]]+-?R?[[:space:]]*777'
  '(curl|wget)[^|]+\|[[:space:]]*(bash|sh)([[:space:]]|$)'
  'dd[[:space:]]+.*of=/dev/'
  'mkfs(\.[a-zA-Z0-9]+)?([[:space:]]|$)'
  'shred[[:space:]]'
  ':[[:space:]]*\([[:space:]]*\)[[:space:]]*\{[[:space:]]*:[[:space:]]*\|[[:space:]]*:[[:space:]]*&[[:space:]]*\}[[:space:]]*;[[:space:]]*:'
)

for p in "${patterns[@]}"; do
  if printf '%s' "$haystack" | grep -qE "$p"; then
    printf '{"decision":"deny","reason":"Destructive operation blocked by safety-gate policy. Run this command manually in a terminal if you need to proceed."}\n'
    exit 0
  fi
done

printf '{"decision":"allow"}\n'

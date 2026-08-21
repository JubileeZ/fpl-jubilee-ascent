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
  if [[ "$target_file" =~ (\.agents|hooks\.json|hooks/) ]]; then
    printf '{"decision":"deny","reason":"Modifying safety-gate configuration or hooks is not allowed. Apply edits to these files manually if needed."}\n'
    exit 0
  fi
fi

# 2. Protect hooks and .agents configuration from being modified via command line
if [ "$tool_name" = "run_command" ] || [ -n "$cmd" ]; then
  if printf '%s' "$cmd" | grep -qE '(\b(rm|mv|cp|sed|echo|tee|chmod|write|overwrite)\b|>|>>|\bgit\s+(checkout|reset|clean|revert)\b).*(hooks\.json|\.agents)'; then
    printf '{"decision":"deny","reason":"Modifying safety-gate configuration or hooks is not allowed. Apply edits to these files manually if needed."}\n'
    exit 0
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

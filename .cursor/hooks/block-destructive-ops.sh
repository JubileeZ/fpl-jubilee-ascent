#!/usr/bin/env bash
# Cursor adapter: block-destructive-ops via permission (agy uses decision)
set -euo pipefail

input=$(cat)
_hook_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
POLICY="${_hook_dir}/../../.agents/hooks/block-destructive-ops.sh"

emit_deny() {
  local reason="$1"
  if command -v jq >/dev/null 2>&1; then
    jq -n --arg r "${reason}" '{permission:"deny",user_message:$r,agent_message:$r}'
  else
    printf '{"permission":"deny","user_message":"Destructive operation blocked.","agent_message":"Destructive operation blocked."}\n'
  fi
}

payload="${input}"
if command -v jq >/dev/null 2>&1; then
  if ! printf '%s' "${input}" | jq -e '.toolCall' >/dev/null 2>&1; then
    cmd=$(printf '%s' "${input}" | jq -r '.command // .tool_input.command // empty' 2>/dev/null || true)
    payload=$(jq -n --arg c "${cmd}" '{toolCall:{name:"run_command",args:{CommandLine:$c}}}')
  fi
fi

out=$(printf '%s' "${payload}" | bash "${POLICY}")
decision=""
if command -v jq >/dev/null 2>&1; then
  decision=$(printf '%s' "${out}" | jq -r '.decision // empty' 2>/dev/null || true)
else
  decision=$(printf '%s' "${out}" | sed -n 's/.*"decision"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n1)
fi

if [ "${decision}" = "deny" ]; then
  reason="Destructive operation blocked."
  if command -v jq >/dev/null 2>&1; then
    reason=$(printf '%s' "${out}" | jq -r '.reason // "Destructive operation blocked."' 2>/dev/null || echo "Destructive operation blocked.")
  fi
  emit_deny "${reason}"
  exit 0
fi
if [ "${decision}" = "allow" ]; then
  printf '{"permission":"allow"}\n'
  exit 0
fi
# Unparseable policy output → fail closed (ADR 0002; hooks.json failClosed)
emit_deny "Safety adapter could not parse policy output."
exit 0

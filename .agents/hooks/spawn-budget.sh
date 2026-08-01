#!/usr/bin/env bash
# spawn-budget.sh — enforce active concurrent spawn limits and recursion depth
STATE_FILE=".agents/spawn-state.json"
mkdir -p .agents

if [ "${1:-}" = "--reset" ]; then
  printf '{"active_spawns": 0, "total_spawns": 0, "sessions": {}}' > "$STATE_FILE"
  printf '{"decision":"allow"}\n'
  exit 0
fi

max_spawns=5
max_depth=1
mode="concurrent"
max_cumulative=0

if [ -f .agents/spawn-budget.json ]; then
  if command -v jq >/dev/null 2>&1; then
    max_spawns=$(jq -r '.max_spawns // .max_concurrent // 5' .agents/spawn-budget.json 2>/dev/null)
    max_depth=$(jq -r '.max_depth // 1' .agents/spawn-budget.json 2>/dev/null)
    mode=$(jq -r '.mode // "concurrent"' .agents/spawn-budget.json 2>/dev/null)
    max_cumulative=$(jq -r '.max_cumulative // 0' .agents/spawn-budget.json 2>/dev/null)
  fi
fi

if [ ! -f "$STATE_FILE" ]; then
  printf '{"active_spawns": 0, "total_spawns": 0, "sessions": {}}' > "$STATE_FILE"
fi

input=$(cat)

if [ "${1:-}" = "--finish" ]; then
  subagent_id=""
  if command -v jq >/dev/null 2>&1; then
    subagent_id=$(printf '%s' "$input" | jq -r '.subagent_id // .subagent.session_id // empty' 2>/dev/null)
  fi
  if [ -n "$subagent_id" ] && [ -f "$STATE_FILE" ]; then
    if command -v jq >/dev/null 2>&1; then
      jq --arg sid "$subagent_id" '
        if .sessions[$sid] and .sessions[$sid].status != "finished" then
          .sessions[$sid].status = "finished" |
          .active_spawns = ([.active_spawns - 1, 0] | max)
        else . end
      ' "$STATE_FILE" > "${STATE_FILE}.tmp" 2>/dev/null && mv "${STATE_FILE}.tmp" "$STATE_FILE"
    fi
  fi
  printf '{"decision":"allow"}\n'
  exit 0
fi

session_id=""
subagent_id=""

if command -v jq >/dev/null 2>&1; then
  session_id=$(printf '%s' "$input" | jq -r '.session_id // empty' 2>/dev/null)
  subagent_id=$(printf '%s' "$input" | jq -r '.subagent_id // .subagent.session_id // empty' 2>/dev/null)
fi

if [ -z "$session_id" ]; then
  session_id="${AGY_SESSION_ID:-${SESSION_ID:-default}}"
fi

if [ -z "$subagent_id" ]; then
  subagent_id="subagent_$(date +%s)_$RANDOM"
fi

parent_depth=0
active_spawns=0
total_spawns=0
if command -v jq >/dev/null 2>&1; then
  parent_depth=$(jq -r --arg sid "$session_id" '.sessions[$sid].depth // 0' "$STATE_FILE" 2>/dev/null)
  active_spawns=$(jq -r '[.sessions[]? | select(.status != "finished")] | length' "$STATE_FILE" 2>/dev/null)
  total_spawns=$(jq -r '.total_spawns // 0' "$STATE_FILE" 2>/dev/null)
fi

child_depth=$((parent_depth + 1))

check_count="$active_spawns"
if [ "$mode" = "cumulative" ]; then
  check_count="$total_spawns"
fi

if [ "$check_count" -ge "$max_spawns" ]; then
  printf '{"decision":"deny","reason":"Spawn budget exceeded: maximum %s subagents (%d) reached"}\n' "$mode" "$max_spawns"
  exit 0
fi

if [ "$max_cumulative" -gt 0 ] && [ "$total_spawns" -ge "$max_cumulative" ]; then
  printf '{"decision":"deny","reason":"Spawn budget exceeded: maximum cumulative session subagents (%d) reached"}\n' "$max_cumulative"
  exit 0
fi

if [ "$child_depth" -gt "$max_depth" ]; then
  printf '{"decision":"deny","reason":"Spawn budget exceeded: maximum depth (%d) reached"}\n' "$max_depth"
  exit 0
fi

# ponytail: no flock on jq RMW — parallel PreToolUse can briefly overshoot max_spawns; add flock if hosts fire spawn hooks concurrently
if command -v jq >/dev/null 2>&1; then
  new_active=$((active_spawns + 1))
  new_total=$((total_spawns + 1))
  jq --argjson act "$new_active" --argjson tot "$new_total" \
     --arg sid "$subagent_id" --argjson cd "$child_depth" \
     '.active_spawns = $act | .total_spawns = $tot | .sessions[$sid] = {depth: $cd, status: "running"}' \
     "$STATE_FILE" > "${STATE_FILE}.tmp" 2>/dev/null && mv "${STATE_FILE}.tmp" "$STATE_FILE"
fi

printf '{"decision":"allow"}\n'
exit 0

#!/bin/sh
# memory guard. POSIX sh so it always parses. Reads PreToolUse JSON on stdin.
# Guarded actions: `memory doubt --network` (contacts every URL cited in pages)
# and `memory approve` (accepts a page's check command for this machine).
# Both get an approval prompt. Everything else is allowed.
input=$(cat)
cmd=$(printf '%s' "$input" | sed -n 's/.*"command":[[:space:]]*"\(.*\)".*/\1/p' | head -c 4000)
case "$cmd" in
  *memory*doubt*--n*|*memory*--n*doubt*)
    printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"memory doubt --network contacts every URL cited in memory pages. Approve only if you agreed to that."}}'
    ;;
  *memory*approve*)
    printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"memory approve runs a page'"'"'s check command and approves it on this machine. Approve only if the agent showed you the command and you agreed."}}'
    ;;
esac
exit 0

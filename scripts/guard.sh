#!/bin/sh
# memory guard. POSIX sh so it always parses. Reads PreToolUse JSON on stdin.
# The only guarded action: `memory doubt --network`, which contacts every URL
# cited in memory pages. Ask the creator to approve it. Everything else: allow.
input=$(cat)
case "$input" in
  *memory*doubt*--network*|*memory*--network*doubt*)
    printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"memory doubt --network contacts every URL cited in memory pages. Approve only if you agreed to that."}}'
    ;;
esac
exit 0

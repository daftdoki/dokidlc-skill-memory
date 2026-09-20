#!/bin/sh
# memory guard. POSIX sh so it always parses. Reads PreToolUse JSON on stdin.
# Asks before `memory doubt --network` (contacts every URL cited in pages) and
# `memory approve` (accepts a page's check command for this machine).
# Denies cat, head, sed, less, and more on a page file: `memory read` prints the
# page with its trust markers and ends with the commands that fix it; cat loses both.
# Everything else is allowed.
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
# a page read with a pager: cat, head, sed, tail, less, or more starts a simple command (at the
# start, or after ; & | ( or a newline) and a .memory/*.md path other than index.md follows it
page=$(printf '%s' "$cmd" | sed -En 's/.*(^|[;&|(]|\\n)[[:space:]]*(cat|head|sed|less|more|tail)[[:space:]]+([^>;|&]*[[:space:]])?([^[:space:]|;&>]*\.memory\/[a-z0-9-]+\.md).*/\4/p')
case "$page" in
  ""|*/index.md) ;;
  *)
    name=${page##*/}
    printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s is a memory page. Read it with: memory read %s. That prints its trust markers and ends with the commands that fix it; cat loses both."}}\n' "$page" "$name"
    ;;
esac
exit 0

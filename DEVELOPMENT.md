# Developing memory

## Layout

```
.claude-plugin/plugin.json   manifest; no version field, the commit is the version
bin/memory                   the command; Python under uv run --script, PyYAML inline
memory.pin                   memoryfield-tool commit and the embedding model
skills/memory/SKILL.md       the agent's rules
hooks/hooks.json             SessionStart and SubagentStart: doctor --brief; UserPromptSubmit and PostToolUse(Failure): recall; Stop: nudge; PreToolUse: guard
tests/                       pytest; nothing needs ollama or memoryfield-tool
```

`bin/memory` is a thin layer over memoryfield-tool, used as published at the
commit in `memory.pin`. It generates the tool's per-machine config from the
repository location, guards the embedding host with a two-second probe,
reindexes synchronously after writes, filters `index.md` from results, and
computes suspicion. It never reimplements storage, search, or indexing.

## Run it from a checkout

```
claude --plugin-dir /path/to/dokidlc-skill-memory
```

Outside a session:

```
CLAUDE_PROJECT_DIR=/path/to/repo OLLAMA_HOST=127.0.0.1:11434 bin/memory search "query"
```

## Search

`hybrid_search()` fuses `search_json()` (the tool's semantic search) with
`string_search()` (a local exact-text loop over name, title, summary, and
body). Ranking: both paths, then semantic by distance, then string-only
by term count with title hits ahead of body hits. In string mode only the
local loop runs and the tool is never called for search.

## Search mode and embedding host

Semantic search is on unless `semantic = false` in the setup file.
`OLLAMA_HOST` exported always means semantic. In string mode the wrapper points the tool at
a closed port so its client fails at once and falls back, and it skips
reindexing. The host, when semantic is on, is resolved in this order: `OLLAMA_HOST` in the environment, then
`embedding_host` in `~/.config/dokidlc-memory/config.toml` (written by
`memory setup`; `XDG_CONFIG_HOME` is honoured), then `127.0.0.1:11434`.
`doctor` names the source. `doctor --fix` installs ollama only for a local
host.

## Tests

```
uv run --quiet pytest
claude plugin validate .
```

CI runs both on ubuntu and macos.

## The tool pin

memoryfield-tool is installed from a git commit because its PyPI release
lags main, and with an overrides file that drops `pysqlite3-binary`, which
ships only Linux x86_64 wheels while the tool falls back to stdlib sqlite3.
`memory doctor --fix` does both. To bump: change `tool_rev` in
`memory.pin`, run `memory doctor --fix`, run the tests, commit.

## Format and compatibility

The generated half of `.memory/index.md` carries `memory format N` and the
plugin commit. `FORMAT` in `bin/memory` is what the code understands. Older
data is migrated by regenerating the index; newer data is refused with
exit 2. Bump `FORMAT` only with a migration.

## Release

Commit to main, let CI pass, then change the `sha` for `memory` in
`dokidlc-plugins/.claude-plugin/marketplace.json`.

## Hook channels

Only SessionStart and UserPromptSubmit inject plain stdout. SubagentStart,
PostToolUse, PostToolUseFailure, and Stop need
`hookSpecificOutput.additionalContext`; PreCompact has no context channel
at all, so the compaction reminder rides on SessionStart with
`source: compact`. `doctor --brief` reads `hook_event_name` from stdin to
pick the framing. Host probes are cached in the state dir for ten
minutes so a dead host costs one probe, not one per prompt.

## Approved checks

`write` and `verify` record the sha256 of a page's check in
`~/.local/state/dokidlc-memory/checks.json`. `doubt` runs only approved
checks and lists the rest. `memory approve PAGE` runs one and records it.

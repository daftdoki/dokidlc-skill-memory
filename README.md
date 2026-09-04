# dokidlc-skill-memory

A Claude Code plugin that gives your agent a memory of its own, so what one
session learns the next one can find. Pages are markdown files in
`.memory/` in the [memoryfield](https://github.com/calpaterson/memoryfield-spec)
format, searched semantically through
[memoryfield-tool](https://github.com/calpaterson/memoryfield-tool). A page
is trusted until there is evidence against it: a cited file changed since
it was cited, a self-check failed, or a contradiction was met in use. Age
alone is only a hint.

With it enabled, the agent will on its own: search memory before it
investigates, installs, configures, or debugs anything; write a page when
it learns something a future session would otherwise rediscover; correct
or delete a page it finds wrong, in the same turn; and re-check a page
that search marks as suspect. Nothing in memory needs your approval, and
nothing the creator asked for goes there. Memory is what the agent learned
by itself; documents you review stay in `docs/`.

## Usage

Mostly you do nothing. The agent searches and writes as it works. You can
steer it:

- "Do you remember anything about installing this?" The agent runs
  `memory search "installing memoryfield-tool"` and reads you the matches.
- "Remember that the NAS keeps its live firmware version in
  /etc/default_config, not /etc/config." The agent writes a page with a
  title, a one-line summary, topics, a kind, and a Sources section.
- "What in memory might be out of date?" The agent runs `memory doubt`
  and lists pages with evidence against them.
- "That page about the tailnet host is wrong now, the host is gone." The
  agent rewrites or deletes it.
- "How much context does memory cost?" `memory cost`.

The commands, for reference:

```
memory search "why does install fail on a mac"     ranked pages, with markers
memory pull "embedding host"                        full text of matching pages
memory read ollama-host-silent-hang.md
memory doubt                                        pages with evidence they may be wrong
memory verify ollama-host-silent-hang.md            re-confirmed; refresh its refs
memory delete stale-page.md
memory cost                                         bytes and tokens of index and search
```

Writing a page, body on stdin:

```
printf 'The tool hangs 75s on a silent host.\n\n## Sources\n\n- timed 2026-09-01\n' | \
  memory write ollama-host-silent-hang.md \
    --title "A silent OLLAMA_HOST hangs the tool" \
    --summary "Why the wrapper probes the host with a two-second timeout" \
    --topics ollama,memoryfield-tool \
    --kind finding \
    --ref docs/research.md \
    --check "curl -s localhost:11434 >/dev/null"
```

`--kind` is `environment`, `procedure`, `finding`, or `decision`, and sets
how soon an unverified page earns a "glance" hint. `--ref` cites a file at
its current commit; search marks the page `suspect` if that file changes.
`--check` is a read-only command that `doubt` runs; a failure marks the
page suspect.

## Requirements

- Claude Code 2.1.195 or later
- `uv` on PATH (https://docs.astral.sh/uv/)
- [ollama](https://ollama.com) with the `nomic-embed-text` model, for
  semantic search. Without it, search falls back to substring matching.
- A git repository

## Installation

From the `dokidlc` marketplace, once per machine:

```
/plugin marketplace add daftdoki/dokidlc-plugins
claude plugin install memory@dokidlc
```

Then in each repository:

```
memory init            creates .memory/ and a short paragraph in CLAUDE.md
memory doctor --fix    installs memoryfield-tool at the pinned commit; on macOS
                       also ollama and the model, on Linux prints the command
```

Commit `.memory/`. The vector index lives in the machine's cache and is
rebuilt from the pages, so git carries only markdown.

To have a repository declare the plugin for everyone who clones it, add to
`.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": { "dokidlc": { "source": { "source": "github", "repo": "daftdoki/dokidlc-plugins" } } },
  "enabledPlugins": { "memory@dokidlc": true }
}
```

The plugin still needs the `claude plugin install` line once per machine.

Manual install, without the marketplace: clone this repository and start
Claude Code with `claude --plugin-dir /path/to/dokidlc-skill-memory`.

## Built on memoryfields

This plugin is a thin layer over memoryfields, Cal Paterson's format and
tools for agent memory. The idea, the page format, and the search engine
are his; this plugin adds the per-repository configuration, the host guard,
the suspicion model, and the Claude Code packaging.

- The article that started it: https://calpaterson.com/memoryfields.html
- The format specification: https://github.com/calpaterson/memoryfield-spec (MIT)
- The engine, memoryfield-tool: https://github.com/calpaterson/memoryfield-tool (AGPL-3.0-or-later)
- His skill for agents, which informed ours: https://github.com/calpaterson/memoryfield-skill (MIT)

memoryfield-tool is used as published, installed by `memory doctor --fix`
at the commit in `memory.pin`. Nothing from it is copied into this
repository. Fields written by this plugin are ordinary memoryfields and can
be read, searched, exported, or served with his tool directly.

See `DEVELOPMENT.md` to work on the plugin itself.

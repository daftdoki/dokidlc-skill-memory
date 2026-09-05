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

## Why this, when Claude Code has a memory

Claude Code's own memory lives in a directory under your home, outside the
repository. It is per machine and per user, git never carries it, and it
loads its index into every session. That is the right place for facts about
the machine and preferences about you: which host this is, where the tools
are installed, how you like to be spoken to.

This plugin is for what the agent learns about the project: a quirk of a
tool, a procedure that worked, a finding about the domain, a decision and
its reason. That knowledge belongs with the code, in git, so it travels to
every clone, every machine, and every collaborator, and so it can be
diffed, reviewed, and rolled back like anything else in the repository. It
is found by semantic search rather than loaded whole, so it stays cheap as
it grows. And it can cite files at a commit, which is what lets a page be
marked suspect when the thing it describes changes.

The two coexist by content, not by mechanism:

| Belongs in | Examples |
|---|---|
| Claude Code's memory | this machine's hostname, local paths, the creator's tone preference, a fact true only here |
| `.memory/` (this plugin) | the tool that fails to install on macOS and the fix, the port a service listens on and why, the trust model the creator chose |
| `docs/` | anything the creator asked for or reviewed: designs, research, decisions with their reasoning |

A memory page may cite a document in `docs/`. A document never cites
memory. When the agent finds something in memory that the creator should
review, it proposes a document and the page cites it.

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
- "Set up memory" or "switch memory to string search, ollama can't run here." The agent asks
  its questions and runs `memory setup`, `init`, and `doctor --fix`.

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

### What a page looks like

The agent writes pages with `memory write`; you rarely will. Each page is
one topic, under 8KB, with frontmatter the search and the trust rules read:

```
---
title: A silent OLLAMA_HOST hangs the tool
summary: Why the wrapper probes the host with a two-second timeout   # what search prints
topics: [ollama, memoryfield-tool]                                    # feed the index
kind: finding                # environment, procedure, finding, or decision
refs: [docs/research.md@61b6f00]   # a file at a commit; if it changes, the page is suspect
check: curl -s localhost:11434 >/dev/null   # optional; if it fails, the page is suspect
verified: '2026-09-04T22:42:52Z'            # when the agent last re-confirmed it
---
The tool hangs about 75 seconds on a host that accepts a connection and
goes silent, because the client has no timeout.

## Sources

- timed against /api/embed, 2026-09-01
```

`kind` sets how soon an unverified page earns a "glance" hint in search:
30 days for `environment`, 90 for `procedure`, 180 for `finding`, never for
`decision`. A glance is a suggestion to skim; only a changed ref, a failed
check, or a contradiction makes a page suspect. `index.md` is the one page
the agent does not write: its top half is yours, its bottom half is a
generated topic list.

## Requirements

- Claude Code 2.1.195 or later
- `uv` on PATH (https://docs.astral.sh/uv/)
- [ollama](https://ollama.com) with the `nomic-embed-text` model, on this
  machine or on a host you can reach. Without it, string search still
  works as a fallback.
- A git repository

## Installation

One command per machine, in Claude Code:

```
/plugin marketplace add daftdoki/dokidlc-plugins
claude plugin install memory@dokidlc
```

Then start a session in a repository and say "set up memory." The agent
asks whether the embedding model runs on this machine or on a remote
host, or, if ollama cannot run where you are, sets string search as a
fallback. It then runs the setup, creates `.memory/` with a short paragraph in
`CLAUDE.md`, and installs what is missing: memoryfield-tool at the pinned
commit, and for a local model on macOS, ollama and the model itself. On
Linux it tells you the one ollama command to run. It stages `.memory/` and
the `CLAUDE.md` paragraph and checks that they, and
`.claude/settings.json`, are tracked and not ignored, since memory only
persists if they are committed. You commit.

Your choices are saved in `~/.config/dokidlc-memory/config.toml`. To
change them later, say so; the agent runs `memory setup` again with your
answer. An `OLLAMA_HOST` exported in the shell turns semantic search on and
overrides the host.

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

## Two ways to search

If the terms are new to you: string search looks for the exact characters
you typed, the way a text editor's find does. Semantic search turns your
query and every page into numbers that stand for meaning and returns the
pages whose meaning is closest, whether or not they share a word with the
query.

**Semantic search** is the default. You search the way you would ask a
colleague: "why does install fail on a mac" finds the page about a
missing wheel even though it shares no words with the query. It needs an
embedding model, `nomic-embed-text`, served by ollama on this machine or
on a host you can reach. It costs about half a second per search on Apple
Silicon and a little more over the network, and results are ranked by a
distance score rather than an exact hit, so a page can appear that is
merely near the subject.

**String search** is the fallback, for an environment where ollama cannot
run and cannot be reached: a locked-down container, a host with no
network, a machine you cannot install on. It needs nothing. A query
matches pages whose filename, title, or summary contain the text you
typed, so you search the way you would grep, with the exact term you
expect to be there: "pysqlite3" finds the missing-wheel page, "why does
install fail on a mac" finds nothing. Memory still works, less well.
Choose it with `memory setup --substring`; switch back with
`memory setup --local` or `memory setup --host URL`. If a semantic host
stops answering, search falls back to string matching for that query and
says so.

**The index.** Semantic search reads a vector index, one SQLite file per
field, that memoryfield-tool builds from the pages. It lives in the
machine's cache, `~/.cache/memoryfield-tool/indexes/` on Linux and
`~/Library/Caches/memoryfield-tool/indexes/` on macOS, never in the
repository. The pages in `.memory/` are the only source of truth. After
every `memory write`, `verify`, or `delete` the wrapper rebuilds the index
before returning, embedding only pages whose content changed. A fresh
clone has no index; the first `memory index` or the first write builds it
from scratch in a few seconds. Deleting the cache loses nothing. In
string mode no index exists and no embedding host is ever contacted.

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

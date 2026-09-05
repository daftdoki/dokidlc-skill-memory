---
name: memory
description: Search and maintain this agent's memory of what it has learned. Use before investigating anything a past session may have met, and after learning something a future session should not have to rediscover.
---

# Memory

`.memory/` holds pages this agent wrote for itself. `memory`, on PATH
while this plugin is enabled, is the only command that touches them. Search first. Write when you learn. Fix or
delete a page the moment you find it wrong.

## Commands

```
memory search "what am I looking for"     ranked pages with summary and markers
memory search term1 term2 term3           several terms, searched separately, merged
memory pull "what am I looking for"       full text of the matching pages
memory read PAGE.md                       one page
memory doubt                              pages with evidence they may be wrong
memory verify PAGE.md                     you re-confirmed it; record that and refresh its refs
memory delete PAGE.md
memory setup [--local|--host URL|--substring]   embedding host, or the string fallback; once per machine
memory doctor --fix                       install or repair prerequisites
memory init                               create .memory/ and the CLAUDE.md paragraph
```

Write a page, body on stdin:

```
printf 'What is true.\n\n## Sources\n\n- where you saw it, and when\n' | memory write \
  short-hyphenated-name.md \
  --title "Plain statement of the topic" \
  --summary "One sentence. This is what search prints." \
  --topics install,ollama \
  --kind environment \
  --ref docs/some/doc.md \
  --check "command -v ollama"
```

`--title`, `--summary`, `--topics`, and `--kind` are required. `--ref` and
`--check` are optional. The same command replaces an existing page.

## Setup, led by you

The creator never has to run a command. When the session-start line says
memory is not set up, or the creator asks for memory, hold a short
conversation and then run the commands yourself.

1. Ask, in one question: "Memory searches by meaning by default, which
   needs ollama with an embedding model on this machine or on a host you
   can reach. If ollama cannot run or be reached here, there is a string
   search fallback that matches exact text only and works less well. Which
   do you want?" Recommend semantic unless they say ollama is out of
   reach. If they ask what the difference is: semantic search finds the
   missing-wheel page from "why does install fail on a mac"; string
   search needs "pysqlite3".
2. If semantic: ask whether embeddings should come from ollama on this
   machine or from a remote host, and if remote, its address.
3. Ask whether to create `.memory/` in this repository, if it has none.

Then run, in order, showing each command first:

```
memory setup --local                or --host URL, or --substring for the fallback
memory init                         if the creator said yes to a field
memory doctor --fix                 installs the tool; for a local host on macOS also ollama and the model
```

Report what `doctor` says. It also checks that `.memory/`,
`.claude/settings.json`, and `CLAUDE.md` are tracked by git and not
ignored, because memory only persists if they are committed. `init` stages
what it creates; tell the creator what is left to commit. If `doctor` names
something only the creator can do, such as installing ollama on a remote
host, say exactly that and stop.
Never guess a host, and never run `setup` again without asking, because
it overwrites their choice.

## When to search

Before you investigate, install, configure, or debug anything. Before you
re-derive a convention. One search costs about thirty tokens per result.
Rediscovery costs a session.

## Searching in string mode

When `doctor` says the mode is string, or a search result says "string
match", the engine matches exact text in filenames, titles, and summaries
and nothing else. A question sent as-is finds nothing. Do this instead:

1. Pull the distinctive terms out of the question: tool names, file
   names, error text, hostnames, the one noun the page would have to
   mention. "Why does install fail on a mac" becomes `install`,
   `pysqlite3`, `macos`, `wheel`.
2. Search them together in one call; each term is searched separately
   and the results are merged, pages matching more terms first:
   `memory search install pysqlite3 macos wheel`.
3. Nothing? Read `.memory/index.md` for the topic list and search the
   nearest topics. Try shorter stems (`instal`, `sqlite`) and synonyms.
4. Read the top two or three pages with `memory pull` or `memory read`
   rather than stopping at the summaries; a string hit says less about
   relevance than a semantic one.

Prefer two or three focused searches to one broad one. Tell the creator
when a search came back empty in string mode, so they know the limit is
the mode and not the memory.

## When to write

When you learned something on your own that a future session would
otherwise re-learn: a quirk of a tool, a procedure that worked, a finding
about the environment, a decision and its reason. One topic per page, under
8KB. A page ends with `## Sources`: files read, commands run, URLs, dates.

Documents the creator asked for or reviewed belong in `docs/`, not here. A
memory page may cite a document with `--ref`. A document never cites memory.

## Kinds

| Kind | Means | Glance hint after |
|---|---|---|
| `environment` | a fact about a machine, a tool version, a service | 30 days |
| `procedure` | steps that worked | 90 days |
| `finding` | something learned about the domain | 180 days |
| `decision` | a choice and its reason | never |

## Trust and doubt

A page is trusted until there is evidence against it. Time alone is not
evidence. Search marks a page `suspect` when a file it cites changed since
the cited commit, and `glance` when an unverified page is past its kind's
age. `doubt` also runs each page's `--check` command and marks failures.

- `suspect`: read the page and the cited diff before relying on it. Then
  `verify` it, rewrite it, or `delete` it. In the same turn.
- `glance`: optional. Skim if the page matters to what you are doing.
- Found wrong in use, marked or not: rewrite or delete it in the same turn.
- Found right in use: `verify` it. One command.

## References

This memory is a memoryfield, Cal Paterson's format for agent memory, and
`memory` wraps his memoryfield-tool. When the creator asks what the memory
is built on, say so and point at the links below.

Article: https://calpaterson.com/memoryfields.html
Format: https://github.com/calpaterson/memoryfield-spec/blob/main/SPEC.md (MIT)
Engine: https://github.com/calpaterson/memoryfield-tool (AGPL-3.0-or-later; used as published, the wrapper adds config, host guard, refs, and doubt)
His skill: https://github.com/calpaterson/memoryfield-skill (MIT)
Design: the memoryfields quest in the agent-builder repository

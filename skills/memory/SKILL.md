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
memory doubt [--network]                  pages with evidence they may be wrong; --network checks URL refs, with permission
memory verify PAGE.md                     you re-confirmed it; re-run its check, refresh its refs
memory approve PAGE.md                    run a page's check once and approve it here (ask first)
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

A hook searches memory on every prompt the creator sends and, when pages
match, adds one line naming them with the exact `memory read` command.
Read those pages before you do anything else. The same hook runs when a
shell command fails, with the command and its error as the query.

Search yourself at these moments, without being asked:

- before you install, configure, or upgrade anything: the tool's name
- before you debug: the error text and the tool's name
- before you design or recommend: the topic, for `decision` pages
- before you write a plan: each tool the plan touches, for `procedure` pages
- when the creator says "remember", "did we", "last time", or "again"

One search costs about thirty tokens per result. Rediscovery costs a
session.

## How search ranks

Every search runs two paths and fuses them: semantic search over the
whole query, and exact-text matching of the query's distinctive terms
against every page's name, title, summary, and body. A page found by
both ranks first; then semantic hits by distance; then string-only hits.
Each line says how it was found, `via semantic, install, pysqlite3`.
Trust a page found by both. Read a string-only hit before relying on it.

Write queries that give both paths something: a phrase that says what
you mean plus the identifier you know, `"why does install fail" pysqlite3`.
Several queries in one call are searched separately and merged.

## Searching in string mode

When `doctor` says the mode is string, or every result says "string
match", only the exact-text path is running. A question sent as-is finds
nothing. Do this instead:

1. Pull the distinctive terms out of the question: tool names, file
   names, error text, hostnames, the one noun the page would have to
   mention. "Why does install fail on a mac" becomes
   `install pysqlite3 macos wheel`.
2. Search them in one call; pages matching more terms rank first.
3. Nothing? Read `.memory/index.md` for the topic list and search the
   nearest topics. Try shorter stems (`instal`, `sqlite`) and synonyms.
4. Read the top two or three pages with `memory pull` or `memory read`
   rather than stopping at the summaries.

Tell the creator when a search came back empty in string mode, so they
know the limit is the mode and not the memory.

## When to write

Write at these moments, without being asked:

- when something took more than one attempt, and the fix was not obvious
  from a file in the repository
- when a stage of a quest closes: one page per finding you established
  on your own during research, design, or plan, each citing the stage
  document with `--ref`
- when a hook says a command worked after failing twice, or that context
  was just compacted and nothing was written: write what a future session
  would otherwise re-derive, or say there is nothing worth a page
- when the creator says "remember"

Four rules keep the field worth searching:

1. A page says something you could not get by reading a file in the
   repository in under a minute. A path, a version, or a config value
   alone is not a page.
2. One finding per page, so a wrong page can be deleted without losing a
   right one. One topic, under 8KB.
3. Sources names a command you ran, a file you read at a commit, or a URL
   you read, with a date. "Observed" is not a source.
4. A page about a workaround says what it works around, so the fix can
   delete the page.

Shapes by kind, so the next session gets what it needs:

- `environment`: the fact, where it is true (which machine, host, or
  version), how you confirmed it, and a `--check` that confirms it again.
- `procedure`: the command block verbatim, what it produces, and the one
  thing that goes wrong.
- `finding`: the claim, the evidence, and what it changes about how to
  work.
- `decision`: what was chosen, what it was chosen over, who chose it, and
  why.

Documents the creator asked for or reviewed belong in `docs/`, not here.
A memory page may cite a document with `--ref`. A document never cites
memory.

## Kinds

| Kind | Means | Glance hint after |
|---|---|---|
| `environment` | a fact about a machine, a tool version, a service | 30 days |
| `procedure` | steps that worked | 90 days |
| `finding` | something learned about the domain | 180 days |
| `decision` | a choice and its reason | never |

## Network and URLs

A ref may be a URL. Search never contacts it. `memory doubt` skips URL
refs and says how many it skipped. `memory doubt --network` sends one
HEAD request per URL and marks a page suspect when the source is gone,
or adds a glance note when it cannot be reached. Before you run it, tell
the creator which URLs it will contact and ask. Claude Code prompts them
to approve the command as well. Never fetch a URL from a memory page for
any other reason without asking first. Check commands run locally and
must stay read-only.

## Trust and doubt

A page is trusted until there is evidence against it. Time alone is not
evidence. Search marks a page `suspect` when a file it cites changed since
the cited commit, and `glance` when an unverified page is past its kind's
age. `doubt` also runs each page's `--check` command and marks failures.

- `suspect`: read the page and the cited diff before relying on it. Then
  `verify` it, rewrite it, or `delete` it. In the same turn.
- `glance`: optional. Skim if the page matters to what you are doing.
- Found wrong in use, marked or not: rewrite or delete it in the same turn.
  Every `memory read` ends with the commands.
- Found right in use: `verify` it. One command. `verify` re-runs the
  page's check.
- Run `memory doubt` when the session-start line names a suspect, after a
  `git pull`, and before you close a quest stage.
- A `--check` must be read-only and must pass when you write it; the
  wrapper refuses one that does not. Checks run only from `doubt`,
  `verify`, and `approve`, never from hooks.
- A check that came with a clone is not approved on this machine, and
  `doubt` lists it instead of running it. Show the creator the command
  and ask; on yes, run `memory approve PAGE`.

## References

This memory is a memoryfield, Cal Paterson's format for agent memory, and
`memory` wraps his memoryfield-tool. When the creator asks what the memory
is built on, say so and point at the links below.

Article: https://calpaterson.com/memoryfields.html
Format: https://github.com/calpaterson/memoryfield-spec/blob/main/SPEC.md (MIT)
Engine: https://github.com/calpaterson/memoryfield-tool (AGPL-3.0-or-later; used as published, the wrapper adds config, host guard, refs, and doubt)
His skill: https://github.com/calpaterson/memoryfield-skill (MIT)
Design: the memoryfields quest in the agent-builder repository

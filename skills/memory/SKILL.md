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
memory pull "what am I looking for"       full text of the matching pages
memory read PAGE.md                       one page
memory doubt                              pages with evidence they may be wrong
memory verify PAGE.md                     you re-confirmed it; record that and refresh its refs
memory delete PAGE.md
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

## When to search

Before you investigate, install, configure, or debug anything. Before you
re-derive a convention. One search costs about thirty tokens per result.
Rediscovery costs a session.

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

Format: https://github.com/calpaterson/memoryfield-spec/blob/main/SPEC.md
Engine: https://github.com/calpaterson/memoryfield-tool (used as published; the wrapper adds config, host guard, refs, and doubt)
Design: the memoryfields quest in the agent-builder repository

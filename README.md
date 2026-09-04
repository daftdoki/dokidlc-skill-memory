# dokidlc-skill-memory

A Claude Code plugin that gives an agent a memory of its own: markdown
pages in `.memory/` in the [memoryfield](https://github.com/calpaterson/memoryfield-spec)
format, searched semantically through
[memoryfield-tool](https://github.com/calpaterson/memoryfield-tool), used
as published at the commit in `memory.pin`. Pages are trusted until there is
evidence against them: a cited file changed, a self-check failed, or a
contradiction was met in use. Time alone is only a hint.

The command is `memory`, on PATH while the plugin is enabled. Run
`memory search QUERY` before investigating anything. The `memory` skill has
the rules.

Requires `uv`. `memory doctor --fix` installs memoryfield-tool at the pinned
commit and, on macOS, ollama and the embedding model; on Linux it prints the
ollama install command.

Install from the `dokidlc` marketplace, then once per machine:

```
/plugin marketplace add daftdoki/dokidlc-plugins
claude plugin install memory@dokidlc
memory init
memory doctor --fix
```

Develop against a local checkout:

```
claude --plugin-dir ../dokidlc-skill-memory
```

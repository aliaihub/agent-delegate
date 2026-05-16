# Canonical rule snippets

These markdown files are the **content** that `agent-delegate install` injects into AI tool config files. They tell each tool — Claude Code, Codex CLI, Claude desktop, Codex web — when and how to use `agent-delegate`.

Every snippet is wrapped in idempotent marker comments:

```markdown
<!-- agent-delegate:begin v0.1.0 -->
... body ...
<!-- agent-delegate:end -->
```

The installer locates these markers, replaces the span on re-install, or appends to the target file if no markers are present. Uninstall removes the span. Editing the body outside the markers is the user's space — never touched.

## File → target

| File | Target |
|---|---|
| `claude_code.md` | `~/.claude/CLAUDE.md` (auto-injected) |
| `codex_cli.md`   | `~/.codex/AGENTS.md` (auto-injected) |
| `claude_desktop.md` | Manual paste into Claude desktop "Project instructions" UI |
| `codex_app.md` | Manual paste into Codex web "Project instructions" UI |

The two desktop variants are printed to stdout (and copied to clipboard with `--copy`) since those apps store instructions in their own DB / cloud sync rather than on the local filesystem.

## Versioning

The marker `v0.2.0` tracks the rule schema, not necessarily every patch release. Bumping the rule version makes `agent-delegate install` re-inject and overwrite the old managed block. Users can see whether the block is installed via `agent-delegate status`.

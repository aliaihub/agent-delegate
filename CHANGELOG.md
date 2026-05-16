# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] — 2026-05-16

### Added
- Stable `--json` output envelopes for `ask`, `write`, and `summarize`, including command metadata, content, targets, usage, and structured errors.
- Directory and glob expansion for `ask --paths` and `write --context`.
- Deterministic corpus ordering, deduplication, default generated-directory excludes, and `AGENT_DELEGATE_MAX_CORPUS_BYTES`.
- Safer `write` modes: `--stdout`, `--target-root`, `--diff`, `--strip-fences`, and `--no-strip-fences`.
- Manager/delegator rule snippets now require cheap/local worker models, model transparency, and end-of-task delegation summaries.
- Rule snippets now require a short visible note when Codex/Claude delegates to an `agent-delegate` worker, including profile, model, and task.
- `ledger` command to show delegated worker calls from the usage log, including profile, backend, model, tokens, duration, and summary counts.
- Tests covering JSON output, safer write behavior, and corpus expansion.
- Dependabot configuration is intentionally omitted from the initial public repo to avoid bot-authored PRs in contributor metadata.

### Changed
- `write` strips one outer Markdown code fence by default before writing generated file content.
- Command JSON helpers now live outside the CLI dispatcher for cleaner command module boundaries.
- CLI docs now describe implemented installer/status/doctor commands instead of marking them as stubs.
- `status` now shows the default backend, model, and host.

## [0.1.0] — 2026-05-15

### Added
- Initial release.
- Backend protocol with `OpenAICompatBackend` (Ollama, LM Studio, OpenRouter, OpenAI, vLLM, llama.cpp, Groq, Cerebras, …) and `AnthropicBackend` (Haiku).
- TOML profile config at `~/.agent-delegate/profiles.toml` with four built-in profiles: `ollama`, `lmstudio`, `openrouter`, `haiku`.
- CLI subcommands: `ask`, `write`, `summarize`, `install`, `uninstall`, `status`, `doctor`, `profiles {list,show,init}`.
- Idempotent installer that injects rule snippets into Claude Code (`~/.claude/CLAUDE.md`) and Codex CLI (`~/.codex/AGENTS.md`), bounded by `<!-- agent-delegate:begin vX.Y.Z -->` markers.
- Optional per-call JSONL usage log via `AGENT_DELEGATE_LOG_DIR`, compatible with the token-meter dashboard.
- Short alias `ad` for `agent-delegate`.
- Zero runtime dependencies; Python 3.11+.
- MIT license.

[0.2.0]: https://github.com/aliaihub/agent-delegate/releases/tag/v0.2.0
[0.1.0]: https://github.com/aliaihub/agent-delegate/releases/tag/v0.1.0

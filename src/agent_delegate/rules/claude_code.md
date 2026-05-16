<!-- agent-delegate:begin v0.2.0 -->
## Delegation policy (managed by agent-delegate)

This block is auto-managed. Run `agent-delegate install` to update it, `agent-delegate uninstall` to remove. Edit outside the markers freely — your edits survive re-install.

### What to delegate

You are the high-reasoning manager. Route the following to `agent-delegate` instead of doing it yourself or spawning another high-reasoning worker. Local/cheap models are good enough for these tasks, and delegation preserves your token budget for reasoning and review:

- **Bulk file reads**: reading 3+ files to answer a narrow question
- **Boilerplate code generation**: scaffolding, type definitions, CRUD endpoints, test fixtures, config files, glue code
- **Summarization**: long log/transcript condensation
- **Fact extraction**: pulling specific values, identifiers, or structure from a corpus

### What NOT to delegate

Always handle these yourself — they require judgment, security context, or tight feedback loops:

- Secrets, credentials, API keys, customer data, PII
- Auth/security decisions, threat modeling, crypto choices
- Root-cause debugging where you need to follow live signal across files
- Database migrations, anything that mutates production state
- Single-line exact edits (the round-trip cost exceeds the benefit)
- Code review of the delegate's own output (you do the review)

### Commands

```
agent-delegate ask --json --paths <file1> <file2> ... --question "..."
agent-delegate write --json --context <file1> ... --spec "..." --target <path> --target-root .
<command-with-long-output> | agent-delegate summarize --json
```

Override profile or model per call:

```
agent-delegate --profile haiku --model claude-haiku-4-5 ask ...
agent-delegate --profile openrouter ask ...
```

### Workflow

1. **You plan** — decide what needs to exist, where it lives, what interface.
2. **You spec** — write a precise spec including exact signatures, behaviors, output format.
3. **Delegate generates** — `agent-delegate write --context <relevant-files> --spec "..." --target <draft-path>`.
4. **You review** — read the output, fix bugs, integrate. Watch for: hallucinated imports, missing edge cases, security gaps, style drift from the surrounding codebase.
5. **You explain** — describe what was built and why to the user.

### Profile selection

`agent-delegate profiles list` shows what's configured. Default profile is the cheapest available (typically `ollama` for local, `openrouter` for cloud). Fall back to `haiku` (Claude Haiku via Anthropic API) when local quality is insufficient.

Run `agent-delegate status` or `agent-delegate profiles show <profile>` when the active worker model is unclear. When you delegate, show the user a short visible note before or immediately after the call:

`Delegating to agent-delegate worker: profile=<profile> model=<model> task="<short task>"`

In your final response after using delegation, report the profile/model used and estimate the delegation split, for example: `delegated implementation: ~70%; worker profile=ollama model=qwen3-coder:480b-cloud`.

### Token tracking (optional)

Set `AGENT_DELEGATE_LOG_DIR` (or `TOKEN_METER_HOME`) to enable per-call usage logging in a token-meter-compatible JSONL file.
<!-- agent-delegate:end -->

<!-- agent-delegate:begin v0.2.0 -->
## Delegation policy (managed by agent-delegate)

This block is auto-managed by `agent-delegate install`. Edits outside the markers are preserved.

### When to delegate

You are the high-reasoning manager. Use `agent-delegate` for bulk, low-reasoning work that's expensive in upstream tokens but appropriate for a cheap or local worker model. Do not use another high-reasoning subagent for these tasks when `agent-delegate` is available.

- Reading 3+ files to answer a specific question
- Generating boilerplate: tests, types, scaffolding, config files
- Summarizing long command output or logs before reasoning over it
- Drafting commit messages or PR descriptions from a diff

### When NOT to delegate

- Secrets, credentials, customer data — never leaves Codex
- Security decisions, auth flows, crypto
- Live debugging that needs tight iteration
- Database migrations or destructive state changes
- Surgical single-line edits

### Commands

```
agent-delegate ask --json --paths <file1> <file2> --question "..."
agent-delegate write --json --context <file1> --spec "..." --target <path> --target-root .
<long-output> | agent-delegate summarize --json
```

Profile + model overrides:

```
agent-delegate --profile haiku ask ...
agent-delegate --profile openrouter --model meta-llama/llama-3.3-70b-instruct ask ...
```

Before delegating, run `agent-delegate status` or `agent-delegate profiles show <profile>` when the active worker model is unclear. When you delegate, show the user a short visible note before or immediately after the call:

`Delegating to agent-delegate worker: profile=<profile> model=<model> task="<short task>"`

The final answer should also name the delegated profile/model, for example `profile=ollama model=qwen3-coder:480b-cloud`.

### Sandbox approval

If your Codex sandbox requires approval for new commands, add `agent-delegate` to your allowed list:

```
codex sandbox allow agent-delegate
codex sandbox allow ad
```

### Workflow

Codex decides → spec → delegate to cheap/local model → Codex reviews → Codex integrates. Never trust delegated output without reading it. At the end of any task that used delegation, include a short delegation summary: delegated slices, local/review slices, approximate delegated implementation percentage, and the profile/model used.

### Usage tracking

Set `AGENT_DELEGATE_LOG_DIR` to log every delegate call in a token-meter-compatible JSONL format.
<!-- agent-delegate:end -->

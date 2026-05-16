<!-- agent-delegate:begin v0.2.0 -->
## Delegation policy

When working in this project, act as the high-reasoning manager and route low-reasoning bulk work to `agent-delegate` (a local CLI) instead of doing it in your own context window or another high-reasoning worker. This preserves my token budget for reasoning and review.

### Delegate these

- Reading 3+ files to answer a focused question
- Generating boilerplate code (tests, types, scaffolding, configs)
- Summarizing long logs/transcripts
- Extracting facts or identifiers from a corpus

### Never delegate

- Secrets, credentials, customer data, PII
- Security decisions, auth, crypto
- Root-cause debugging that requires tight iteration
- Migrations or destructive state changes
- One-line exact edits

### How to invoke

If you have shell access in this project, run:

```
agent-delegate ask --json --paths <files> --question "..."
agent-delegate write --json --context <files> --spec "..." --target <path> --target-root .
<command> | agent-delegate summarize --json
```

If you don't have shell access, tell me which task you would have delegated and what the spec would be — I'll run it on my side and paste the result.

### Workflow

1. You design + spec.
2. Delegate generates (cheap/local model).
3. You review + integrate (your job, not the delegate's).
4. You explain the result, including the delegated profile/model and an approximate delegation split.

When delegating, show a short visible note:

`Delegating to agent-delegate worker: profile=<profile> model=<model> task="<short task>"`
<!-- agent-delegate:end -->

<!-- agent-delegate:begin v0.2.0 -->
## Delegation policy

For this project, act as the high-reasoning manager and route low-reasoning bulk work to `agent-delegate` (a local/cloud CLI). Keep my budget for reasoning and review. Do not use another high-reasoning subagent for these tasks when `agent-delegate` is available.

### Delegate

- 3+ file reads for a specific question
- Boilerplate generation (tests, types, scaffolds, configs)
- Long log/transcript summarization
- Fact extraction from a corpus

### Don't delegate

- Secrets, credentials, customer data
- Security or auth decisions
- Root-cause debugging
- Migrations, destructive operations
- Single-line surgical edits

### Commands

```
agent-delegate ask --json --paths <files> --question "..."
agent-delegate write --json --context <files> --spec "..." --target <path> --target-root .
<output> | agent-delegate summarize --json
```

Override profile or model per call:

```
agent-delegate --profile haiku ask ...
agent-delegate --profile openrouter ask ...
```

### Workflow

I plan + spec → cheap/local model generates → I review + integrate → I explain. Delegated output is always reviewed. When delegating, show a short visible note:

`Delegating to agent-delegate worker: profile=<profile> model=<model> task="<short task>"`

Final responses should name the delegated profile/model and include an approximate delegation split.
<!-- agent-delegate:end -->

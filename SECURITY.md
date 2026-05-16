# Security policy

## Supported versions

Until v1.0 ships, only the latest published 0.x release receives security fixes.

| Version | Supported |
|---|---|
| 0.x latest | ✅ |
| older 0.x | ❌ |

## Reporting a vulnerability

**Do not open a public issue for security problems.**

Email `security@<maintainer-domain>` or use [GitHub private security advisories](https://github.com/aliaihub/agent-delegate/security/advisories/new).

Include:
- Affected version(s)
- Reproduction steps or PoC
- Expected vs. actual behavior
- Suggested fix if you have one

You'll get an acknowledgement within 7 days. Disclosure timeline is coordinated — a typical embargo is 90 days or until a fix ships, whichever is sooner.

## Threat model

`agent-delegate` is a CLI that:
- Reads local files into prompts and forwards them to an external LLM endpoint
- Writes to the local filesystem (config files via `install`, draft files via `write`)
- Stores configuration in `~/.agent-delegate/profiles.toml` (may contain API keys if the user inlined them)

**In scope:**
- Path traversal in `install` / `uninstall` (must only touch known config paths)
- Arbitrary file write outside the user-specified `--target` (must not happen)
- Leakage of API keys into logs or stderr (must not happen)
- Idempotent block-injection breaking on adversarial input in target files

**Out of scope:**
- What you choose to send to a delegate model (don't send secrets — the bundled rules say so)
- Security of the third-party LLM endpoints you configure
- Plaintext API keys in `profiles.toml` (use `api_key_env` instead — it's the documented best practice)

## Hardening recommendations for users

- Prefer `api_key_env = "..."` over inline `api_key = "..."` in `profiles.toml`.
- Set `chmod 600 ~/.agent-delegate/profiles.toml` if you do store inline keys.
- Audit `AGENT_DELEGATE_LOG_DIR` logs before sharing — they include cwd and parent PID.
- Run `agent-delegate doctor` after install to confirm endpoints are what you expect.

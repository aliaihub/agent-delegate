# Contributing to agent-delegate

Thanks for your interest. PRs and issues welcome.

## Quick rules

- **Zero runtime dependencies.** `agent-delegate` is intentionally stdlib-only. Anything that requires `pip install <foo>` at runtime is rejected. Dev-only tooling (pytest, ruff) goes under `[project.optional-dependencies] dev`.
- **Python 3.11+.** Use modern typing (`list[str]`, `X | None`).
- **Cross-platform.** macOS, Linux, Windows. Use `pathlib`, never hard-code separators. Atomic writes via temp file + `os.replace`.
- **Idempotent file changes.** The installer's marker-block contract must be preserved — `inject_block` followed by `strip_block` should restore the original byte-for-byte (within whitespace normalization).
- **Security mindset.** Never write code that hands secrets / API keys to a delegate model. The rule snippets in `src/agent_delegate/rules/` are the source of truth for that policy.

## Local setup

```bash
git clone https://github.com/aliaihub/agent-delegate.git
cd agent-delegate
pip install -e ".[dev]"
```

Run tests:

```bash
pytest -q
```

Lint:

```bash
ruff check src tests
ruff format src tests   # to fix
```

## Adding a new backend

1. Implement the `Backend` protocol (see `src/agent_delegate/backends/base.py`).
2. Register it in `src/agent_delegate/backends/__init__.py` `get_backend()` factory.
3. Add a default profile in `src/agent_delegate/profiles.py` `DEFAULT_PROFILES`.
4. Add a row to the Backends table in `README.md`.
5. Add a test that constructs the backend and asserts the protocol conformance.

## Adding a rule for a new AI tool

1. Create `src/agent_delegate/rules/<tool-slug>.md` bounded by the marker comments.
2. Add a `ToolTarget` entry in `src/agent_delegate/detect.py` `_tools_catalog()`.
3. Add a row to the install matrix in `README.md`.
4. Test via `agent-delegate install --dry-run --tool <slug>`.

## Commit style

- Imperative subject ≤ 70 chars.
- Body wraps at 80 cols, explains *why*.
- Reference issues with `Fixes #123`.

## Releasing

Maintainers only:

```bash
# Bump version in pyproject.toml and src/agent_delegate/__init__.py
# Update CHANGELOG.md
git commit -am "Release v0.X.0"
git tag v0.X.0
git push --follow-tags
```

CI publishes to PyPI on tag push via trusted publishing.

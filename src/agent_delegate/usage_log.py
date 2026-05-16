"""JSONL usage log — compatible with token-meter ingester.

Activated when AGENT_DELEGATE_LOG_DIR is set (or OLLAMA_DELEGATE_USAGE_LOG / TOKEN_METER_HOME
for backward compat). Silent on all errors — logging never breaks delegation.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Optional

from .backends.base import ChatResult
from .profiles import Profile


_LOG_FILENAME = "agent-delegate.log"


def _resolve_log_path() -> Optional[Path]:
    """Return the log file path, or None if no log destination is configured."""
    # Explicit override wins.
    explicit = os.environ.get("AGENT_DELEGATE_LOG")
    if explicit:
        return Path(explicit)
    # Directory env var.
    log_dir = os.environ.get("AGENT_DELEGATE_LOG_DIR")
    if log_dir:
        return Path(log_dir) / _LOG_FILENAME
    # Back-compat with the ollama-delegate script: log into token-meter home.
    legacy = os.environ.get("OLLAMA_DELEGATE_USAGE_LOG")
    if legacy:
        return Path(legacy)
    tm_home = os.environ.get("TOKEN_METER_HOME")
    if tm_home:
        # Write a new file (don't reuse old ollama-delegate.log; that one stays
        # for the old script if user hasn't migrated yet).
        return Path(tm_home) / _LOG_FILENAME
    return None


def _iso_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def log_call(command: str, profile: Profile, model: str, result: ChatResult, *, target: str | None = None) -> None:
    """Append one JSONL record for a delegate call. Never raises."""
    try:
        path = _resolve_log_path()
        if not path:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "ts": _iso_now(),
            "command": command,
            "profile": profile.name,
            "backend": result.backend,
            "model": model,
            # token-meter-compatible field names (mirrors old ollama-delegate schema):
            "prompt_eval_count": result.prompt_tokens,
            "eval_count": result.completion_tokens,
            # extras:
            "cached_tokens": result.cached_tokens,
            "reasoning_tokens": result.reasoning_tokens,
            "total_duration_ms": result.total_duration_ms,
            "cwd": os.getcwd(),
            "claude_session_id": os.environ.get("CLAUDE_SESSION_ID", ""),
            "codex_session_id": os.environ.get("CODEX_SESSION_ID", ""),
            "parent_pid": os.getppid(),
            "host": profile.base_url,
        }
        if target is not None:
            record["target"] = target
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    except Exception:
        # Never break delegation because of a logging failure.
        pass

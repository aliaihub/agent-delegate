"""Read and summarize agent-delegate usage logs."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from .usage_log import _resolve_log_path


def read_entries(path: Path | None = None) -> list[dict[str, Any]]:
    """Read JSONL usage entries, skipping malformed lines."""
    log_path = path or _resolve_log_path()
    if not log_path or not log_path.exists():
        return []

    entries: list[dict[str, Any]] = []
    with log_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                entries.append(value)
    return entries


def summarize_entries(entries: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Return aggregate stats for usage-log entries."""
    rows = list(entries)
    prompt_tokens = sum(int(row.get("prompt_eval_count") or 0) for row in rows)
    completion_tokens = sum(int(row.get("eval_count") or 0) for row in rows)
    cached_tokens = sum(int(row.get("cached_tokens") or 0) for row in rows)
    reasoning_tokens = sum(int(row.get("reasoning_tokens") or 0) for row in rows)
    duration_ms = sum(int(row.get("total_duration_ms") or 0) for row in rows)

    return {
        "total_calls": len(rows),
        "total_prompt_tokens": prompt_tokens,
        "total_completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "cached_tokens": cached_tokens,
        "reasoning_tokens": reasoning_tokens,
        "total_duration_ms": duration_ms,
        "by_command": dict(Counter(str(row.get("command") or "") for row in rows)),
        "by_profile": dict(Counter(str(row.get("profile") or "") for row in rows)),
        "by_model": dict(Counter(str(row.get("model") or "") for row in rows)),
        "by_backend": dict(Counter(str(row.get("backend") or "") for row in rows)),
    }


def recent_entries(entries: list[dict[str, Any]], limit: int | None) -> list[dict[str, Any]]:
    """Return the most recent entries while preserving chronological order."""
    if limit is None or limit <= 0 or len(entries) <= limit:
        return entries
    return entries[-limit:]


def print_text(entries: list[dict[str, Any]], *, limit: int | None = None) -> None:
    """Print a compact human-readable ledger."""
    visible = recent_entries(entries, limit)
    if not visible:
        print("No delegation calls found.")
        return

    print("Delegated worker calls:")
    for index, row in enumerate(visible, 1):
        tokens = int(row.get("prompt_eval_count") or 0) + int(row.get("eval_count") or 0)
        session = row.get("codex_session_id") or row.get("claude_session_id") or "-"
        target = row.get("target") or "-"
        print(
            f"{index:>3}. {row.get('ts', '-')}  "
            f"command={row.get('command', '-')}  "
            f"profile={row.get('profile', '-')}  "
            f"backend={row.get('backend', '-')}  "
            f"model={row.get('model', '-')}  "
            f"tokens={tokens}  "
            f"duration_ms={row.get('total_duration_ms', '-')}  "
            f"target={target}  "
            f"session={session}"
        )

    summary = summarize_entries(entries)
    print()
    print("Delegation summary:")
    print(f"  total calls: {summary['total_calls']}")
    print(f"  total tokens: {summary['total_tokens']}")
    print(f"  prompt/completion: {summary['total_prompt_tokens']}/{summary['total_completion_tokens']}")
    print(f"  total duration ms: {summary['total_duration_ms']}")
    print(f"  by command: {_format_counts(summary['by_command'])}")
    print(f"  by profile: {_format_counts(summary['by_profile'])}")
    print(f"  by model: {_format_counts(summary['by_model'])}")


def _format_counts(counts: dict[str, int]) -> str:
    visible = {key: value for key, value in counts.items() if key}
    if not visible:
        return "-"
    return ", ".join(f"{key}={value}" for key, value in sorted(visible.items()))

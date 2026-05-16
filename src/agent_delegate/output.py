"""Shared command output helpers."""

from __future__ import annotations

import json
from typing import Any

from .backends.base import BackendError, ChatResult


def _usage(result: ChatResult) -> dict[str, Any]:
    return {
        "prompt_tokens": result.prompt_tokens,
        "completion_tokens": result.completion_tokens,
        "cached_tokens": result.cached_tokens,
        "reasoning_tokens": result.reasoning_tokens,
        "total_duration_ms": result.total_duration_ms,
    }


def _profile_name(profile) -> str | None:
    if profile is None:
        return None
    if isinstance(profile, str):
        return profile
    return profile.name


def json_success(
    *,
    command: str,
    profile,
    model: str,
    content: Any,
    target: str | None = None,
    usage: ChatResult | None = None,
) -> None:
    envelope: dict[str, Any] = {
        "ok": True,
        "command": command,
        "model": model,
        "content": content,
    }
    profile_name = _profile_name(profile)
    if profile_name is not None:
        envelope["profile"] = profile_name
    if target is not None:
        envelope["target"] = target
    if usage is not None:
        envelope["usage"] = _usage(usage)
    print(json.dumps(envelope, ensure_ascii=False))


def json_error(
    *,
    command: str,
    profile,
    model: str | None,
    message: str,
    error_type: str,
    target: str | None = None,
    backend_error: BackendError | None = None,
) -> None:
    error: dict[str, Any] = {
        "type": error_type,
        "message": message,
    }
    if backend_error is not None:
        if backend_error.backend:
            error["backend"] = backend_error.backend
        if backend_error.status is not None:
            error["status"] = backend_error.status
        if backend_error.body:
            error["body"] = backend_error.body
    envelope: dict[str, Any] = {
        "ok": False,
        "command": command,
        "error": error,
    }
    profile_name = _profile_name(profile)
    if profile_name is not None:
        envelope["profile"] = profile_name
    if model is not None:
        envelope["model"] = model
    if target is not None:
        envelope["target"] = target
    print(json.dumps(envelope, ensure_ascii=False))

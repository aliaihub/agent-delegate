"""summarize command — condense stdin for a coding agent."""

from __future__ import annotations

import sys

from ..backends import Backend, Message
from ..backends.base import BackendError
from ..output import json_error, json_success
from ..profiles import Profile
from ..usage_log import log_call
from ._prompts import SUMMARIZE_SYSTEM


def run(
    backend: Backend,
    profile: Profile,
    model: str,
    temperature: float = 0.1,
    json_output: bool = False,
) -> int:
    text = sys.stdin.read()
    if not text.strip():
        if json_output:
            json_error(
                command="summarize",
                profile=profile,
                model=model,
                message="stdin was empty",
                error_type="empty_stdin",
            )
        else:
            print("stdin was empty", file=sys.stderr)
        return 2

    messages = [
        Message("system", SUMMARIZE_SYSTEM),
        Message("user", text),
    ]
    try:
        result = backend.chat(
            messages, model, temperature=temperature, timeout=profile.timeout
        )
    except BackendError as e:
        if json_output:
            json_error(
                command="summarize",
                profile=profile,
                model=model,
                message=str(e),
                error_type="backend_error",
                backend_error=e,
            )
        else:
            print(f"delegation failed: {e}", file=sys.stderr)
        return 1

    log_call("summarize", profile, model, result)
    if json_output:
        json_success(
            command="summarize",
            profile=profile,
            model=model,
            content=result.content,
            usage=result,
        )
    else:
        print(result.content)
    return 0

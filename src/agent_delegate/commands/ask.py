"""ask command — answer a question using one or more files as context."""

from __future__ import annotations

import sys
from typing import Iterable

from ..backends import Backend, Message
from ..backends.base import BackendError
from ..output import json_error, json_success
from ..profiles import Profile
from ..usage_log import log_call
from ._corpus import corpus
from ._prompts import ASK_SYSTEM


def run(
    backend: Backend,
    profile: Profile,
    model: str,
    paths: Iterable[str],
    question: str,
    temperature: float = 0.1,
    json_output: bool = False,
) -> int:
    try:
        corpus_text = corpus(paths)
    except SystemExit as e:
        message = str(e)
        if json_output:
            json_error(
                command="ask",
                profile=profile,
                model=model,
                message=message,
                error_type="corpus_error",
            )
        else:
            print(message, file=sys.stderr)
        return 2

    messages = [
        Message("system", ASK_SYSTEM),
        Message("user", f"<corpus>\n{corpus_text}\n</corpus>"),
        Message("user", question),
    ]
    try:
        result = backend.chat(
            messages, model, temperature=temperature, timeout=profile.timeout
        )
    except BackendError as e:
        if json_output:
            json_error(
                command="ask",
                profile=profile,
                model=model,
                message=str(e),
                error_type="backend_error",
                backend_error=e,
            )
        else:
            print(f"delegation failed: {e}", file=sys.stderr)
        return 1

    log_call("ask", profile, model, result)
    if json_output:
        json_success(
            command="ask",
            profile=profile,
            model=model,
            content=result.content,
            usage=result,
        )
    else:
        print(result.content)
    return 0
